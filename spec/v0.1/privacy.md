# Privacy and Secret Policy

## Defaults

| Source material | Default class/action |
|---|---|
| Identity/config without personal data | `unknown` until adapter classification |
| Sessions and transcripts | `private` |
| User/profile memory | `private` |
| Unknown files | `private` |
| Credentials, tokens, private keys | `secret`, reject |

Private policy may include public and explicitly classified private items. It
MUST reject secret items. Public policy includes public items only; private and
unknown items are redacted and recorded.

## Minimum secret controls

Filename matching is case-insensitive and rejects `.env`, `auth.json`,
`credentials*`, names containing `token`, `*.pem`, `*.key`, `id_rsa`, and
`id_ed25519`. JSON and YAML objects are recursively scanned for keys equivalent
to `api_key`, `apikey`, `token`, `access_token`, `refresh_token`, `secret`,
`password`, `credential`, or `private_key` after punctuation normalization.

The scanner is deliberately not described as universal DLP. Arbitrary text can
contain secrets. Adapters and users MUST be able to exclude items, and public
publication requires review of the inventory and redaction report.

`inspect` and `diff` output metadata only and MUST NOT print layer payloads.

