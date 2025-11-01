from __future__ import annotations

from typing import Any, Dict


def normalize(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize bpsr_logs (WinJ) payloads to core fields for hash computation and storage.
    
    Extracts: fight_id, player_id, damage/mitigation summary, timestamp for idempotency.
    """
    meta: Dict[str, Any] = {}

    # Fight and player identification
    fight_id = payload.get("fight_id") or payload.get("fight")
    if fight_id:
        meta["fight_id"] = fight_id

    player_id = payload.get("player_id") or payload.get("player")
    if player_id:
        meta["player_id"] = player_id

    # Damage/mitigation summary
    damage = payload.get("damage") or payload.get("dmg")
    if damage is not None:
        meta["damage"] = damage

    mitigation = payload.get("mitigation") or payload.get("mit")
    if mitigation is not None:
        meta["mitigation"] = mitigation

    # Timestamp (required for hash)
    timestamp = payload.get("tick") or payload.get("timestamp")
    if timestamp:
        meta["timestamp"] = timestamp

    # Additional metadata
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
            meta["category"] = "combat"
        elif lowered in {"heal", "healing"}:
            meta["category"] = "heal"
        elif lowered in {"trade", "trade_center"}:
            meta["category"] = "trade"
        else:
            meta["category"] = "boss_event"

    return meta
