from __future__ import annotations

from typing import Any, Dict

from . import bp_timer, bpsr_logs

AdapterResult = Dict[str, Any]


def apply_adapter(source: str, payload: Dict[str, Any]) -> AdapterResult:
    if source == "bp_timer":
        return bp_timer.normalize(payload)
    if source == "bpsr_logs":
        return bpsr_logs.normalize(payload)
    return {}
