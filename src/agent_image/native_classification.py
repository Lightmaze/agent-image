from __future__ import annotations

from collections.abc import Iterable


PRIVACY_CLASSES = {"public", "private", "unknown", "secret"}
PORTABILITY_CLASSES = {"portable", "adapter-specific", "opaque"}
STRUCTURED_NATIVE_EFFECTIVE_PORTABILITY = "adapter-specific"


class NativeClassificationError(ValueError):
    pass


def require_structured_native_portability(value: object) -> str:
    """Validate the final exported unit portability for v0.1 structured-native."""
    if not isinstance(value, str) or value not in PORTABILITY_CLASSES:
        raise NativeClassificationError(f"invalid portability class: {value!r}")
    if value != STRUCTURED_NATIVE_EFFECTIVE_PORTABILITY:
        raise NativeClassificationError(
            "structured-native v0.1 final output must use portability=adapter-specific; "
            "portable projections require a separate portable layer and uninterpreted byte custody is opaque"
        )
    return value


def require_finalized_privacy_homogeneity(
    outer_privacy: object,
    embedded_effective_privacy: Iterable[object],
) -> tuple[str, tuple[str, ...]]:
    """Validate effective privacy after producer finalization."""
    if not isinstance(outer_privacy, str) or outer_privacy not in PRIVACY_CLASSES:
        raise NativeClassificationError(f"invalid outer privacy class: {outer_privacy!r}")
    embedded: list[str] = []
    for value in embedded_effective_privacy:
        if not isinstance(value, str) or value not in PRIVACY_CLASSES:
            raise NativeClassificationError(f"invalid embedded privacy class: {value!r}")
        embedded.append(value)
    classes = tuple(sorted(set(embedded)))
    if classes and classes != (outer_privacy,):
        raise NativeClassificationError(
            "finalized structured-native capsule is not effective-privacy homogeneous: "
            f"outer={outer_privacy!r}, embedded={list(classes)!r}"
        )
    return outer_privacy, classes
