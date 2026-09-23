from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Any

import yaml

from agent_image.canonical import canonical_json_bytes, sha256_bytes


_JS_TAG = "tag:yaml.org,2002:js"
_MAX_DIFFS = 32


@dataclass(frozen=True)
class TaggedScalar:
    tag: str
    source: str


@dataclass(frozen=True)
class DshWitness:
    raw_digest: str
    semantic_digest: str
    canonical: bytes
    value: Any


class DshWitnessLoader(yaml.SafeLoader):
    """Fail-closed, non-evaluating loader for DSH dump-config diagnostics."""


def _construct_js(loader: DshWitnessLoader, node: yaml.Node) -> TaggedScalar:
    if not isinstance(node, yaml.ScalarNode):
        raise yaml.constructor.ConstructorError(
            None,
            None,
            "DSH !!js witness values must be scalar expressions.",
            node.start_mark,
        )
    return TaggedScalar(_JS_TAG, loader.construct_scalar(node))


def _construct_mapping_no_duplicates(
    loader: DshWitnessLoader,
    node: yaml.MappingNode,
    deep: bool = False,
) -> dict[str, Any]:
    if not isinstance(node, yaml.MappingNode):
        raise yaml.constructor.ConstructorError(None, None, "expected a mapping node", node.start_mark)
    result: dict[str, Any] = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if not isinstance(key, str):
            raise yaml.constructor.ConstructorError(
                None,
                None,
                "DSH witness mapping keys must be strings.",
                key_node.start_mark,
            )
        if key in result:
            raise yaml.constructor.ConstructorError(
                None,
                None,
                f"duplicate DSH witness mapping key: {key!r}",
                key_node.start_mark,
            )
        result[key] = loader.construct_object(value_node, deep=deep)
    return result


DshWitnessLoader.add_constructor(_JS_TAG, _construct_js)
DshWitnessLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
    _construct_mapping_no_duplicates,
)


def _normalize(value: Any) -> Any:
    if isinstance(value, TaggedScalar):
        return {"$yaml_tag": value.tag, "$scalar": value.source}
    if value is None or isinstance(value, (bool, int, str)):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("non-finite float in DSH restore witness")
        return value
    if isinstance(value, list):
        return [_normalize(item) for item in value]
    if isinstance(value, dict):
        if not all(isinstance(key, str) for key in value):
            raise ValueError("non-string mapping key in DSH restore witness")
        return {key: _normalize(item) for key, item in value.items()}
    raise ValueError(f"unsupported DSH restore-witness value type: {type(value).__name__}")


def parse_dump_non_evaluating(data: bytes) -> Any:
    try:
        text = data.decode("utf-8", errors="strict")
    except UnicodeDecodeError as error:
        raise ValueError("DSH restore witness is not UTF-8") from error
    try:
        value = yaml.load(text, Loader=DshWitnessLoader)
    except yaml.YAMLError as error:
        raise ValueError("DSH restore witness is not fail-closed parseable YAML") from error
    return _normalize(value)


def build_witness(data: bytes) -> DshWitness:
    value = parse_dump_non_evaluating(data)
    canonical = canonical_json_bytes(value)
    return DshWitness(
        raw_digest=sha256_bytes(data),
        semantic_digest=sha256_bytes(canonical),
        canonical=canonical,
        value=value,
    )


def _type_name(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "bool"
    if isinstance(value, int):
        return "int"
    if isinstance(value, float):
        return "float"
    if isinstance(value, str):
        return "string"
    if isinstance(value, list):
        return "list"
    if isinstance(value, dict):
        return "object"
    return type(value).__name__


def _diff_values(expected: Any, actual: Any, path: str, output: list[dict[str, str]]) -> None:
    if len(output) >= _MAX_DIFFS:
        return
    if type(expected) is not type(actual):
        output.append(
            {
                "path": path,
                "kind": "type_changed",
                "expected_type": _type_name(expected),
                "actual_type": _type_name(actual),
            }
        )
        return
    if isinstance(expected, dict):
        expected_keys = set(expected)
        actual_keys = set(actual)
        for key in sorted(expected_keys - actual_keys):
            if len(output) >= _MAX_DIFFS:
                return
            output.append(
                {
                    "path": f"{path}.{key}",
                    "kind": "missing_actual",
                    "expected_type": _type_name(expected[key]),
                    "actual_type": "missing",
                }
            )
        for key in sorted(actual_keys - expected_keys):
            if len(output) >= _MAX_DIFFS:
                return
            output.append(
                {
                    "path": f"{path}.{key}",
                    "kind": "missing_expected",
                    "expected_type": "missing",
                    "actual_type": _type_name(actual[key]),
                }
            )
        for key in sorted(expected_keys & actual_keys):
            _diff_values(expected[key], actual[key], f"{path}.{key}", output)
            if len(output) >= _MAX_DIFFS:
                return
        return
    if isinstance(expected, list):
        if len(expected) != len(actual):
            output.append(
                {
                    "path": path,
                    "kind": "length_changed",
                    "expected_type": f"list[{len(expected)}]",
                    "actual_type": f"list[{len(actual)}]",
                }
            )
            if len(output) >= _MAX_DIFFS:
                return
        for index, (left, right) in enumerate(zip(expected, actual, strict=False)):
            _diff_values(left, right, f"{path}[{index}]", output)
            if len(output) >= _MAX_DIFFS:
                return
        return
    if expected != actual:
        output.append(
            {
                "path": path,
                "kind": "value_changed",
                "expected_type": _type_name(expected),
                "actual_type": _type_name(actual),
            }
        )


def compare_witness(expected: bytes, actual: bytes) -> dict[str, Any]:
    details: dict[str, Any] = {
        "raw_equal": expected == actual,
        "expected_raw_digest": sha256_bytes(expected),
        "actual_raw_digest": sha256_bytes(actual),
    }
    try:
        left = build_witness(expected)
        right = build_witness(actual)
    except ValueError as error:
        details.update(
            semantic_equal=None,
            parser_status="rejected",
            parser_error=str(error),
            diff=[],
            diff_truncated=False,
        )
        return details

    diffs: list[dict[str, str]] = []
    _diff_values(left.value, right.value, "$", diffs)
    details.update(
        semantic_equal=left.canonical == right.canonical,
        parser_status="parsed",
        expected_semantic_digest=left.semantic_digest,
        actual_semantic_digest=right.semantic_digest,
        diff=diffs,
        diff_truncated=len(diffs) >= _MAX_DIFFS,
    )
    return details
