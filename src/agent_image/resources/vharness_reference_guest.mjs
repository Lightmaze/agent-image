import { createHash } from 'node:crypto'
import { readFile, rename, writeFile } from 'node:fs/promises'
import { createInterface } from 'node:readline'

const STATE_API = 'agent-image.reference-guest/v1'
const statePath = argument('--fixture')
let previousRegime = null

const input = createInterface({ input: process.stdin, crlfDelay: Infinity })
input.on('line', (line) => void dispatchLine(line))

async function dispatchLine(line) {
  let request
  try {
    request = JSON.parse(line)
  } catch (error) {
    process.stderr.write(`Invalid driver request: ${String(error)}\n`)
    process.exitCode = 2
    return
  }
  try {
    const result = await dispatch(request.method, request.params ?? {})
    await respond({ id: request.id, ok: true, result })
    if (request.method === 'shutdown') process.exit(0)
  } catch (error) {
    await respond({
      id: request.id,
      ok: false,
      error: {
        code: error.code ?? 'VH_REFERENCE_GUEST_ERROR',
        message: error.message ?? String(error),
      },
    })
  }
}

async function dispatch(method, params) {
  const state = await loadState()
  switch (method) {
    case 'probe':
      return evidence(state, 'persistent-state-observed', params.transitionId)
    case 'quiesce':
      return {
        checkpointRef: `sha256:${digest(state.items)}`,
        consistency: 'quiescent',
        boundary: `generation:${state.generation}`,
        stateClaims: state.items.map((item) => stateClaim(state, item)),
      }
    case 'flush':
      await persist(state)
      return {
        boundary: `generation:${state.generation}`,
        evidence: [`file://${statePath}`, `sha256:${digest(state.items)}`],
      }
    case 'captureTransfer': {
      const allowed = new Set(params.allowedTypes ?? [])
      const transferred = state.items.filter((item) => allowed.has(item.transferType))
      const omitted = state.items.filter((item) => !allowed.has(item.transferType))
      return {
        envelope: {
          apiVersion: 'vharness.dev/v1alpha1',
          kind: 'TransferEnvelope',
          id: `envelope-${String(params.transitionId)}`,
          transitionId: String(params.transitionId),
          sourceRegime: String(params.sourceRegime),
          targetRegime: String(params.targetRegime),
          createdAt: new Date().toISOString(),
          items: transferred.map((item) => ({
            id: `transfer-${item.id}`,
            type: item.transferType,
            stateClaim: stateClaim(state, item),
            payload: item.value,
            provenance: [
              `reference-guest://${state.instanceId}/${item.id}`,
              `agent-image:${state.provenance.sourceImageDigest}`,
            ],
            guestVisibility: 'full',
          })),
        },
        lossReport: {
          complete: true,
          sourceStateClasses: state.items.map((item) => item.semanticClass),
          mappedStateClasses: transferred.map((item) => item.semanticClass),
          losses: omitted.map((item) => ({
            path: `/items/${item.id}`,
            class: 'capability',
            severity: 'blocking',
            sourceSemantics: item.semanticClass,
            targetSemantics: 'not transferred',
            reason: `${item.transferType} is absent from the target edge transfer policy.`,
          })),
        },
      }
    }
    case 'remountReadOnly':
      return evidence(state, 'host-world-remounted-read-only', params.transitionId)
    case 'enterRegime':
      previousRegime = state.currentRegime
      state.currentRegime = String(params.targetRegime)
      await persist(state)
      return evidence(state, `entered:${state.currentRegime}:quarantine`, params.transitionId)
    case 'verify': {
      const observed = await loadState()
      if (observed.currentRegime !== String(params.targetRegime)) {
        throw coded('VH_REFERENCE_STATE_MISMATCH', 'Persistent Guest regime does not match the Host target.')
      }
      return evidence(observed, `verified:${observed.currentRegime}`, params.transitionId)
    }
    case 'rollbackTarget':
      if (previousRegime !== null) {
        state.currentRegime = previousRegime
        await persist(state)
      }
      return evidence(state, 'target-rollback-ack', params.transitionId)
    case 'resumeSource':
      return evidence(state, 'source-resume-ack', params.transitionId)
    case 'shutdown':
      return { closed: true }
    default:
      throw coded('VH_DRIVER_METHOD_UNSUPPORTED', `Unsupported Guest Driver method ${method}.`)
  }
}

function stateClaim(state, item) {
  return {
    id: item.id,
    semanticClass: item.semanticClass,
    completeness: { mode: 'complete', boundary: `generation:${state.generation}` },
    consistency: { mode: 'quiescent', boundary: `generation:${state.generation}` },
    capture: { mode: 'embedded', digest: `sha256:${digest(item.value)}` },
    restore: { mode: 'exact' },
    authorityAfterRestore: { mode: 'none' },
    sensitivity: { class: item.sensitivity },
    evidence: {
      adapter: 'agent-image-reference-persistent-guest',
      source: `reference-guest://${state.instanceId}/${item.id}`,
    },
  }
}

function evidence(state, fact, transitionId) {
  return {
    source: `reference-guest://${state.instanceId}`,
    facts: [
      fact,
      `state-items-sha256:${digest(state.items)}`,
      `source-image:${state.provenance.sourceImageDigest}`,
      ...(transitionId === undefined ? [] : [`transition:${String(transitionId)}`]),
    ],
    enforcement: {
      mode: 'logical',
      ambientOsAccess: true,
      controls: ['vhd-authority-ledger', 'separate-process-boundary', 'persistent-state-validation'],
      evidence: ['Authority is granted only by vhd; this reference Guest cannot mint Host grants.'],
    },
  }
}

async function loadState() {
  const state = JSON.parse(await readFile(statePath, 'utf8'))
  if (state.apiVersion !== STATE_API || typeof state.instanceId !== 'string' || !Array.isArray(state.items)) {
    throw coded('VH_REFERENCE_STATE_INVALID', 'Reference Guest state is malformed.')
  }
  if (!['wake', 'audit'].includes(state.currentRegime)) {
    throw coded('VH_REFERENCE_STATE_INVALID', 'Reference Guest currentRegime is unsupported.')
  }
  if (!Number.isSafeInteger(state.generation) || state.generation < 0) {
    throw coded('VH_REFERENCE_STATE_INVALID', 'Reference Guest generation is invalid.')
  }
  for (const item of state.items) {
    if (
      typeof item.id !== 'string' || typeof item.semanticClass !== 'string' ||
      !['ContextTransfer', 'MemoryTransfer', 'PendingIntentTransfer', 'PlasticityDelta'].includes(item.transferType) ||
      !['public', 'internal', 'private'].includes(item.sensitivity)
    ) {
      throw coded('VH_REFERENCE_STATE_INVALID', 'Reference Guest item metadata is invalid.')
    }
    rejectSecretKeys(item.value, `/items/${item.id}/value`)
  }
  if (
    typeof state.provenance !== 'object' || state.provenance === null ||
    typeof state.provenance.sourceImageDigest !== 'string'
  ) {
    throw coded('VH_REFERENCE_STATE_INVALID', 'Reference Guest provenance is invalid.')
  }
  return state
}

function rejectSecretKeys(value, path) {
  if (Array.isArray(value)) {
    value.forEach((entry, index) => rejectSecretKeys(entry, `${path}/${index}`))
    return
  }
  if (typeof value !== 'object' || value === null) return
  for (const [key, entry] of Object.entries(value)) {
    if (/(?:secret|token|password|api[_-]?key|credential|private[_-]?key)/i.test(key)) {
      throw coded('VH_REFERENCE_SECRET_REJECTED', `Secret-like key is forbidden at ${path}/${key}.`)
    }
    rejectSecretKeys(entry, `${path}/${key}`)
  }
}

async function persist(state) {
  const temporary = `${statePath}.${process.pid}.tmp`
  await writeFile(temporary, `${JSON.stringify(state, null, 2)}\n`, 'utf8')
  await rename(temporary, statePath)
}

function digest(value) {
  return createHash('sha256').update(canonicalize(value), 'utf8').digest('hex')
}

function canonicalize(value) {
  if (value === null || typeof value !== 'object') return JSON.stringify(value)
  if (Array.isArray(value)) return `[${value.map(canonicalize).join(',')}]`
  return `{${Object.keys(value).sort().map((key) => `${JSON.stringify(key)}:${canonicalize(value[key])}`).join(',')}}`
}

function argument(name) {
  const index = process.argv.indexOf(name)
  const value = index >= 0 ? process.argv[index + 1] : undefined
  if (!value) throw new Error(`Missing ${name}.`)
  return value
}

function coded(code, message) {
  return Object.assign(new Error(message), { code })
}

function respond(response) {
  return new Promise((resolve, reject) => {
    process.stdout.write(`${JSON.stringify(response)}\n`, 'utf8', (error) => error ? reject(error) : resolve())
  })
}
