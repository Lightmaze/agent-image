from __future__ import annotations

import pytest

from agent_image.adapters.dsh_witness import build_witness, compare_witness, parse_dump_non_evaluating


def test_identical_raw_is_identical_semantically() -> None:
    data = b"- id: x\n  config: {value: one}\n"
    result = compare_witness(data, data)
    assert result["raw_equal"] is True
    assert result["semantic_equal"] is True
    assert result["diff"] == []


def test_comments_whitespace_line_endings_and_mapping_order_are_semantic_only() -> None:
    expected = b"# layer: C:/source/cordis.patch.yml\r\n- id: system-prompt\r\n  config:\r\n    persona: hello\r\n    temperature: 1\r\n"
    actual = b"# layer: D:/target/cordis.patch.yml\n- config: {temperature: 1, persona: hello}\n  id: system-prompt\n"
    result = compare_witness(expected, actual)
    assert result["raw_equal"] is False
    assert result["semantic_equal"] is True
    assert result["diff"] == []


def test_list_order_is_semantic() -> None:
    expected = b"- id: a\n- id: b\n"
    actual = b"- id: b\n- id: a\n"
    result = compare_witness(expected, actual)
    assert result["semantic_equal"] is False
    assert result["diff"]


def test_scalar_value_change_is_semantic_and_values_are_not_reported() -> None:
    expected = b"- id: x\n  config: {secretish: alpha}\n"
    actual = b"- id: x\n  config: {secretish: beta}\n"
    result = compare_witness(expected, actual)
    assert result["semantic_equal"] is False
    assert result["diff"] == [
        {
            "path": "$[0].config.secretish",
            "kind": "value_changed",
            "expected_type": "string",
            "actual_type": "string",
        }
    ]
    rendered = repr(result)
    assert "alpha" not in rendered
    assert "beta" not in rendered


def test_js_is_non_evaluating_and_exact_source_is_semantic() -> None:
    expected = b"- id: x\n  config:\n    f: !!js '() => 1'\n"
    same = b"# comment\n- config: {f: !!js '() => 1'}\n  id: x\n"
    changed = b"- id: x\n  config:\n    f: !!js '() => 2'\n"
    assert compare_witness(expected, same)["semantic_equal"] is True
    assert compare_witness(expected, changed)["semantic_equal"] is False


def test_duplicate_mapping_key_fails_closed() -> None:
    with pytest.raises(ValueError, match="fail-closed parseable YAML"):
        parse_dump_non_evaluating(b"- id: x\n  config:\n    a: 1\n    a: 2\n")


def test_unknown_tag_fails_closed() -> None:
    with pytest.raises(ValueError, match="fail-closed parseable YAML"):
        parse_dump_non_evaluating(b"- id: x\n  config: {x: !danger foo}\n")


def test_non_string_mapping_key_fails_closed() -> None:
    with pytest.raises(ValueError, match="fail-closed parseable YAML"):
        parse_dump_non_evaluating(b"- id: x\n  config: {1: value}\n")


def test_non_finite_float_fails_closed() -> None:
    with pytest.raises(ValueError, match="non-finite float"):
        build_witness(b"- id: x\n  config: {value: .nan}\n")


def test_parse_failure_is_reported_without_relaxing_raw_mismatch() -> None:
    result = compare_witness(
        b"- id: x\n  config: {value: one}\n",
        b"- id: x\n  config: {value: !danger two}\n",
    )
    assert result["raw_equal"] is False
    assert result["semantic_equal"] is None
    assert result["parser_status"] == "rejected"
    assert result["diff"] == []
