from __future__ import annotations

from typing import Any, Dict


def normalize(payload: Dict[str, Any]) -> Dict[str, Any]:
    meta: Dict[str, Any] = {}

    if isinstance(payload.get("boss"), dict):
        boss_name = payload["boss"].get("name")
    else:
        boss_name = payload.get("boss_name")
    if boss_name:
        meta["boss_name"] = boss_name

    region = payload.get("region") or payload.get("shard")
    if region:
        meta["region"] = region

    category = payload.get("category") or payload.get("type")
    if isinstance(category, str):
        lowered = category.lower()
        if lowered in {"combat", "damage"}:
            meta.setdefault("category", "combat")
        elif lowered in {"heal", "healing"}:
            meta.setdefault("category", "heal")
        elif lowered in {"trade", "trade_center"}:
            meta.setdefault("category", "trade")
        else:
            meta.setdefault("category", "boss_event")

    tick = payload.get("tick") or payload.get("timestamp")
    if tick:
        meta.setdefault("payload_metadata", {})
        meta["payload_metadata"]["tick"] = tick

    return meta
