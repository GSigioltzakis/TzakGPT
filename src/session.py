from datetime import datetime

_log = []
_input_tokens = 0
_output_tokens = 0
_turns = 0


def record(action: str, detail: str = "", error: bool = False):
    _log.append({"timestamp": datetime.now(), "action": action, "detail": detail, "error": error})


def _format_ts(ts, fmt: str) -> str:
    if isinstance(ts, datetime):
        return ts.strftime(fmt)
    return str(ts)


def get_log_as_text() -> str:
    if not _log:
        return "Nothing recorded yet."
    lines = []
    for entry in _log:
        ts = _format_ts(entry["timestamp"], "%H:%M:%S")
        status = "ERR" if entry["error"] else "OK "
        line = f"[{ts}] {status}  {entry['action']}"
        if entry["detail"]:
            line += f"  {entry['detail']}"
        lines.append(line)
    return "\n".join(lines)


def get_summary_for_prompt() -> str:
    if not _log:
        return ""
    parts = []
    for entry in _log:
        ts = _format_ts(entry["timestamp"], "%H:%M")
        action = entry["action"]
        detail = entry["detail"]
        suffix = f" ({ts}, error)" if entry["error"] else f" ({ts})"
        parts.append(f"{action} {detail}{suffix}" if detail else f"{action}{suffix}")
    return "Actions this session: " + ", ".join(parts)


def get_token_totals() -> dict:
    return {
        "turns": _turns,
        "input": _input_tokens,
        "output": _output_tokens,
        "total": _input_tokens + _output_tokens,
    }


def add_tokens(input_tokens: int, output_tokens: int):
    global _input_tokens, _output_tokens, _turns
    _input_tokens += input_tokens
    _output_tokens += output_tokens
    _turns += 1


def restore_log(entries: list):
    global _log
    _log = entries


def restore_tokens(totals: dict):
    global _input_tokens, _output_tokens, _turns
    _input_tokens = totals.get("input", 0)
    _output_tokens = totals.get("output", 0)
    _turns = totals.get("turns", 0)
