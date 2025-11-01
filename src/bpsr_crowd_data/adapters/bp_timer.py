from __future__ import annotations

from typing import Any, Dict


KNOWN_COMBAT_EVENTS = {"damage", "heal", "boss_spawn", "boss_defeat"}


def normalize(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize BP Timer payloads to core fields for hash computation and storage.
    
    Extracts: boss_id/name, hp%, timestamp for idempotency and querying.
    """
    meta: Dict[str, Any] = {}

    # Boss identification
    boss_name = payload.get("boss") or payload.get("boss_name")
    boss_id = payload.get("boss_id")
    if boss_name:
        meta["boss_name"] = boss_name
    if boss_id:
        meta["boss_id"] = boss_id

    # HP percentage (if available)
    hp_percent = payload.get("hp_percent") or payload.get("hp%")
    if hp_percent is not None:
        meta["hp_percent"] = hp_percent

    # Timestamp (required for hash)
    timestamp = payload.get("timestamp") or payload.get("time")
    if timestamp:
        meta["timestamp"] = timestamp

    # Additional metadata
    region = payload.get("region") or payload.get("server")
    if region:
        meta["region"] = region

    event_type = str(payload.get("event", "")).lower()
    if event_type in KNOWN_COMBAT_EVENTS:
        if event_type == "heal":
            meta["category"] = "heal"
        elif event_type == "damage":
            meta["category"] = "combat"
        else:
            meta["category"] = "boss_event"

    return meta
