from __future__ import annotations

from collections.abc import Iterable


PRIVACY_CLASSES = frozenset({"public", "private", "unknown", "secret"})
STRUCTURED_NATIVE_PORTABILITY = "adapter-specific"


class NativeClassificationError(ValueError):
    pass


def require_structured_native_portability(value: object) -> str:
    if value != STRUCTURED_NATIVE_PORTABILITY:
        raise NativeClassificationError(
            "structured native capsule layers must use portability=adapter-specific in v0.1"
        )
    return STRUCTURED_NATIVE_PORTABILITY


def require_finalized_privacy_homogeneity(
    outer_privacy: object,
    embedded_privacy: Iterable[object],
) -> str:
    if outer_privacy not in PRIVACY_CLASSES:
        raise NativeClassificationError(f"invalid outer privacy: {outer_privacy!r}")
    values = set(embedded_privacy)
    invalid = sorted(repr(value) for value in values if value not in PRIVACY_CLASSES)
    if invalid:
        raise NativeClassificationError(
            f"invalid embedded privacy classes: {', '.join(invalid)}"
        )
    if values and values != {outer_privacy}:
        raise NativeClassificationError(
            "finalized structured native layer must be privacy-homogeneous "
            f"(outer={outer_privacy!r}, embedded={sorted(values)!r})"
        )
    return str(outer_privacy)
