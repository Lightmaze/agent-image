from __future__ import annotations

import copy
from dataclasses import dataclass
from typing import Any, Iterable, Mapping


PRIVACY = {"public", "private", "unknown", "secret"}


class NativePrivacyPlanError(ValueError):
    pass


@dataclass(frozen=True)
class NativePrivacyItem:
    item_id: str
    source_privacy: str

    def __post_init__(self) -> None:
        if not self.item_id:
            raise NativePrivacyPlanError("item_id must be non-empty")
        if self.source_privacy not in PRIVACY:
            raise NativePrivacyPlanError(f"invalid privacy: {self.source_privacy}")


@dataclass(frozen=True)
class AtomicNativePrivacyPlan:
    unit_id: str
    requested_policy: str
    effective_privacy: str
    action: str
    exact_native_bytes_preserved: bool
    public_subset_requires_profile_projection: bool
    outcomes: tuple[dict[str, Any], ...]

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema": "agent-image-native-privacy-plan/v0.1",
            "unit_id": self.unit_id,
            "requested_policy": self.requested_policy,
            "effective_privacy": self.effective_privacy,
            "action": self.action,
            "exact_native_bytes_preserved": self.exact_native_bytes_preserved,
            "public_subset_requires_profile_projection": self.public_subset_requires_profile_projection,
            "outcomes": [dict(x) for x in self.outcomes],
        }


def conservative_join(items: Iterable[NativePrivacyItem]) -> str:
    items = tuple(items)
    if not items:
        raise NativePrivacyPlanError("atomic native restore unit must contain at least one classified item")
    ids = [x.item_id for x in items]
    if len(ids) != len(set(ids)):
        raise NativePrivacyPlanError("duplicate item_id in native privacy inventory")
    values = {x.source_privacy for x in items}
    if "secret" in values:
        raise NativePrivacyPlanError("secret material cannot be transported inside an Agent Image native layer")
    if "unknown" in values:
        return "unknown"
    if "private" in values:
        return "private"
    return "public"


def plan_atomic_restore_unit(
    unit_id: str,
    items: Iterable[NativePrivacyItem],
    *,
    requested_policy: str = "private",
) -> AtomicNativePrivacyPlan:
    if not unit_id:
        raise NativePrivacyPlanError("unit_id must be non-empty")
    if requested_policy not in {"private", "public"}:
        raise NativePrivacyPlanError("requested_policy must be private or public")
    items = tuple(items)
    effective = conservative_join(items)
    keep = requested_policy == "private" or effective == "public"
    action = "preserve-whole" if keep else "redact-whole"
    outcomes = []
    for item in items:
        promoted = item.source_privacy != effective
        outcomes.append({
            "id": item.item_id,
            "action": "preserved" if keep else "redacted",
            "source_privacy": item.source_privacy,
            "effective_privacy": effective,
            "privacy_promoted": promoted,
            "reason": (
                f"atomic native restore unit conservatively classified as {effective}"
                if keep
                else f"public policy removes atomic native restore unit classified as {effective}"
            ),
        })
    has_public = any(x.source_privacy == "public" for x in items)
    return AtomicNativePrivacyPlan(
        unit_id=unit_id,
        requested_policy=requested_policy,
        effective_privacy=effective,
        action=action,
        exact_native_bytes_preserved=keep,
        public_subset_requires_profile_projection=(not keep and has_public),
        outcomes=tuple(outcomes),
    )


def coarsen_capsule_index_privacy(
    index: Mapping[str, Any],
    plan: AtomicNativePrivacyPlan,
) -> dict[str, Any]:
    if plan.action != "preserve-whole":
        raise NativePrivacyPlanError("cannot coarsen a unit that is being redacted")
    result = copy.deepcopy(dict(index))
    for item in result.get("authoritative", []):
        item["privacy"] = plan.effective_privacy
    for item in result.get("derived", []):
        if "path" in item:
            item["privacy"] = plan.effective_privacy
    return result
