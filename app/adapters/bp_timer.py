from __future__ import annotations

from typing import Any, Dict


KNOWN_COMBAT_EVENTS = {"damage", "heal", "boss_spawn", "boss_defeat"}


def normalize(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Light-touch parsing for BP Timer payloads."""

    meta: Dict[str, Any] = {}

    boss_name = payload.get("boss") or payload.get("boss_name")
    if boss_name:
        meta["boss_name"] = boss_name

    region = payload.get("region") or payload.get("server")
    if region:
        meta["region"] = region

    event_type = str(payload.get("event", "")).lower()
    if event_type in KNOWN_COMBAT_EVENTS:
        if event_type == "heal":
            meta.setdefault("category", "heal")
        elif event_type == "damage":
            meta.setdefault("category", "combat")
        else:
            meta.setdefault("category", "boss_event")

    timestamp = payload.get("timestamp") or payload.get("time")
    if timestamp:
        meta.setdefault("payload_metadata", {})
        meta["payload_metadata"]["timestamp"] = timestamp

    return meta
