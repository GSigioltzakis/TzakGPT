import sys
import time
import random
import json
import os
import readchar
from datetime import datetime

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table
from rich.live import Live
from rich.spinner import Spinner
from rich.text import Text

from clients import ask_deepseek, ask_deepseek_stream, set_model, get_model_display
from soul import build_payload, classify_action, GREETINGS, SYSTEM_PROMPT
from tools import read_file, write_file, run_command, list_directory
from display import show_diff, show_action, show_result, confirm_command

from prompt_toolkit import prompt
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.styles import Style
from prompt_toolkit.completion import Completer, Completion

import session

try:
    import msvcrt

    def check_stop_key() -> bool:
        """Return True if the user pressed X to interrupt thinking."""
        while msvcrt.kbhit():
            key = msvcrt.getch().lower()
            if key == b"x":
                while msvcrt.kbhit():
                    msvcrt.getch()
                return True
        return False

except ImportError:
    def check_stop_key() -> bool:
        return False


console = Console()

SESSION_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sessions")

CONTEXT_WARNING_THRESHOLD = 1_500_000
MAX_CONTEXT_TOKENS = 3_000_000

_BELL_ENABLED = os.getenv("TZAK_BELL", "").strip().lower() in ("true", "1", "yes")


def _ring_bell():
    """Ring the terminal bell if enabled."""
    if _BELL_ENABLED:
        sys.stdout.write("\a")
        sys.stdout.flush()


SLASH_COMMANDS = {
    "/help":   "Show this help message",
    "/clear":  "Reset conversation history (with confirmation)",
    "/status": "Show session activity log",
    "/tokens": "Show token usage statistics",
    "/save":   "Save session checkpoint to disk",
    "/load":   "Load a saved session",
    "/model":  "Switch model: /model pro  or  /model flash",
    "/bell":   "Toggle completion bell on / off",
}


_SPINNER_TEXTS = [
    "Thinking...\n",
    "Reading your files...\n",
    "Consulting DeepSeek...\n",
    "Almost done...\n",
    "Working on it...\n",
]
_spinner_idx = 0


def _next_spinner_text() -> str:
    global _spinner_idx
    text = _SPINNER_TEXTS[_spinner_idx % len(_SPINNER_TEXTS)]
    _spinner_idx += 1
    return text


class _CyclingSpinner:
    """A renderable that cycles spinner text from the pool as it animates."""

    def __init__(self, spinner_name: str = "dots"):
        self._spinner = Spinner(spinner_name, text="")
        self._text_idx = 0
        self._texts = _SPINNER_TEXTS
        self._frame_count = 0
        self._frames_per_text = 40

    def __rich_console__(self, console, options):
        self._frame_count += 1
        if self._frame_count >= self._frames_per_text:
            self._frame_count = 0
            self._text_idx = (self._text_idx + 1) % len(self._texts)
        self._spinner._text = Text.from_markup(
            f"[dim]{self._texts[self._text_idx]}[/dim]"
        )
        yield from self._spinner.__rich_console__(console, options)


class SlashCompleter(Completer):
    """Prompt-toolkit completer that activates only when input starts with '/'."""

    def get_completions(self, document, complete_event):
        text = document.text_before_cursor
        if not text.startswith("/"):
            return
        for cmd, desc in SLASH_COMMANDS.items():
            if cmd.startswith(text):
                yield Completion(
                    cmd,
                    start_position=-len(text),
                    display_meta=desc,
                )


def get_header_text() -> str:
    logo = r"""
████████╗███████╗ █████╗ ██╗  ██╗ ██████╗ ██████╗ ████████╗
╚══██╔══╝╚══███╔╝██╔══██╗██║ ██╔╝██╔════╝ ██╔══██╗╚══██╔══╝
   ██║     ███╔╝ ███████║█████╔╝ ██║  ███╗██████╔╝   ██║
   ██║    ███╔╝  ██╔══██║██╔═██╗ ██║   ██║██╔═══╝    ██║
   ██║   ███████╗██║  ██║██║  ██╗╚██████╔╝██║        ██║
   ╚═╝   ╚══════╝╚═╝  ╚═╝╚═╝  ╚═╝ ╚═════╝ ╚═╝        ╚═╝
    """
    greeting = random.choice(GREETINGS)
    return (
        f"[bold dodger_blue2]{logo}[/bold dodger_blue2]\n"
        f"[bold cyan]Welcome to TzakGPT AI agent CLI.[/bold cyan]\n"
        f"[italic pale_green1]{greeting}[/]\n"
        "[dim]Type 'exit' or 'quit' to close the app.[/dim]"
    )


def _next_sequential_name() -> str:
    """Return the next session_NNN.json filename by scanning existing saves."""
    os.makedirs(SESSION_DIR, exist_ok=True)
    highest = 0
    for f in os.listdir(SESSION_DIR):
        if f.startswith("session_") and f.endswith(".json"):
            try:
                num = int(f[len("session_"):-len(".json")])
                if num > highest:
                    highest = num
            except ValueError:
                pass
    return f"session_{highest + 1:03d}.json"


def _unique_path(filename: str) -> str:
    """Return a unique save path, auto-incrementing a counter if the file exists."""
    base, ext = os.path.splitext(filename)
    if ext != ".json":
        ext = ".json"
    candidate = os.path.join(SESSION_DIR, f"{base}{ext}")
    if not os.path.exists(candidate):
        return candidate
    counter = 1
    while True:
        candidate = os.path.join(SESSION_DIR, f"{base}_{counter:03d}{ext}")
        if not os.path.exists(candidate):
            return candidate
        counter += 1


def save_session(conversation_history, filename=None):
    os.makedirs(SESSION_DIR, exist_ok=True)
    if filename:
        save_path = _unique_path(filename)
    else:
        save_path = os.path.join(SESSION_DIR, _next_sequential_name())

    data = {
        "timestamp": datetime.now().isoformat(),
        "working_directory": os.getcwd(),
        "conversation_history": conversation_history,
        "session_log": session._log,
        "token_totals": session.get_token_totals(),
    }
    with open(save_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, default=str)

    console.print(f"[dim]Session saved: {os.path.basename(save_path)}[/dim]")
    session.record("save_session", os.path.basename(save_path))
    return True


def _relative_time(ts_str: str) -> str:
    """Return a human-friendly relative time from an ISO timestamp."""
    try:
        dt = datetime.fromisoformat(ts_str)
        diff = datetime.now() - dt
        if diff.days > 0:
            return f"{diff.days}d ago"
        hours = diff.seconds // 3600
        if hours > 0:
            return f"{hours}h ago"
        minutes = diff.seconds // 60
        if minutes > 0:
            return f"{minutes}m ago"
        return "just now"
    except Exception:
        return ""


def _parse_session_metadata(filepath: str) -> dict:
    """Extract lightweight metadata from a session file without loading full history."""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        turns = data.get("token_totals", {}).get("turns", 0)
        model = "flash"
        for entry in data.get("session_log", []):
            if entry.get("action") == "model_change":
                detail = entry.get("detail", "")
                if "pro" in detail.lower():
                    model = "pro"
                elif "flash" in detail.lower():
                    model = "flash"
        ts_str = data.get("timestamp", "")
        return {"turns": turns, "model": model, "timestamp": ts_str}
    except Exception:
        return {"turns": 0, "model": "?", "timestamp": ""}


def load_session(conversation_history, filename=None):
    os.makedirs(SESSION_DIR, exist_ok=True)
    session_files = sorted(
        [f for f in os.listdir(SESSION_DIR) if f.endswith(".json")],
        reverse=True,
    )
    if not session_files:
        console.print("[yellow]No saved sessions found.[/yellow]")
        return False

    if not filename:
        console.print("\n[bold]Available sessions:[/bold]")
        for i, sf in enumerate(session_files[:10], 1):
            filepath = os.path.join(SESSION_DIR, sf)
            meta = _parse_session_metadata(filepath)
            rel_time = _relative_time(meta["timestamp"])
            console.print(
                f"  [{i}] [bold]{sf}[/bold]"
                f"  [dim]{meta['turns']} turns   {meta['model']}   {rel_time}[/dim]"
            )
        console.print("[dim]  Select [1-N] or press Enter to cancel: [/dim]", end="")
        key = readchar.readkey()
        if key in ("\r", "\n", ""):
            console.print("[dim]Cancelled.[/dim]")
            return False
        try:
            idx = int(key) - 1
            if idx < 0 or idx >= len(session_files[:10]):
                console.print("[yellow]Invalid selection.[/yellow]")
                return False
            filename = session_files[idx]
        except ValueError:
            console.print("[dim]Cancelled.[/dim]")
            return False

    load_path = os.path.join(SESSION_DIR, filename)
    if not os.path.exists(load_path):
        console.print(f"[yellow]File not found: {filename}[/yellow]")
        return False

    with open(load_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    conversation_history.clear()
    conversation_history.extend(data.get("conversation_history", []))

    session._log = data.get("session_log", [])
    token_data = data.get("token_totals", {})
    session._input_tokens = token_data.get("input", 0)
    session._output_tokens = token_data.get("output", 0)
    session._turns = token_data.get("turns", 0)

    console.print(f"[dim]Session restored: {filename}[/dim]")
    session.record("load_session", filename)
    return True


def handle_tool_call(tool_call, conversation_history) -> str:
    """Execute a single tool call and return the JSON result string for the API."""
    name = tool_call.function.name
    args = json.loads(tool_call.function.arguments)

    if name == "read_file":
        show_action("Reading", args["path"])
        result = read_file(args["path"])
        session.record("read_file", args["path"])
    elif name == "write_file":
        show_action("Writing", args["path"])
        diff = write_file(args["path"], args["content"])
        show_diff(diff)
        result = f"File written: {args['path']}"
        session.record("write_file", args["path"])
    elif name == "list_directory":
        path = args.get("path", ".")
        show_action("Listing", path)
        data = list_directory(path)
        result = json.dumps(data)
        session.record("list_directory", path)
    elif name == "run_command":
        cmd = args["cmd"]
        choice = confirm_command(cmd)
        if isinstance(choice, tuple) and choice[0] == "e":
            cmd = choice[1]
            choice = confirm_command(cmd)
        if choice == "n":
            result = "User declined to run the command."
            session.record("run_command", cmd, error=False)
        else:
            show_action("Running", cmd)
            result = run_command(cmd)
            show_result(result)
            is_error = result.startswith("ERROR:")
            session.record("run_command", cmd, error=is_error)
    else:
        result = f"Unknown tool: {name}"

    return json.dumps(
        {"tool_call_id": tool_call.id, "name": name, "result": result}
    )


def agent_loop(conversation_history, payload, tools, panel_color):
    """Streaming chat loop. Returns (response_text, usage_tuple, tool_count)."""
    max_iterations = 100
    iteration = 0
    turn_input = 0
    turn_output = 0
    tool_count = 0

    prev_tool_signature = None
    repeat_count = 0

    while iteration < max_iterations:
        if check_stop_key():
            console.print("[dim]  Interrupted.[/dim]")
            return "[Interrupted by user]", (turn_input, turn_output), tool_count

        iteration += 1

        stream = ask_deepseek_stream(payload, tools)
        collected_text = ""
        tool_calls_received = None
        stream_usage = {"input": 0, "output": 0}
        error_msg = None

        title = f"[bold {panel_color}] TzakGPT (via DeepSeek)[/bold {panel_color}]"

        with Live(console=console, refresh_per_second=15, transient=True) as live:
            thinking_spinner = _CyclingSpinner("dots")
            live.update(Panel(
                thinking_spinner,
                title=title,
                border_style=panel_color,
                padding=(0, 2),
            ))
            time.sleep(0.15)

            for event in stream:
                if check_stop_key():
                    live.update(Panel(
                        "[dim]Interrupted.[/dim]",
                        title=title,
                        border_style=panel_color,
                    ))
                    return "[Interrupted by user]", (turn_input, turn_output), tool_count

                if event[0] == "error":
                    error_msg = event[1]
                    break
                elif event[0] == "text":
                    collected_text += event[1]
                    md = Markdown(collected_text)
                    live.update(Panel(
                        md,
                        title=title,
                        border_style=panel_color,
                        padding=(1, 2),
                    ))
                elif event[0] == "tool_calls":
                    tool_calls_received = event[1]
                    stream_usage = event[2]
                    if collected_text.strip():
                        md = Markdown(collected_text)
                        live.update(Panel(
                            md,
                            title=title,
                            border_style=panel_color,
                            padding=(1, 2),
                        ))
                    break
                elif event[0] == "done":
                    collected_text = event[1]
                    stream_usage = event[2]
                    if collected_text.strip():
                        md = Markdown(collected_text)
                        live.update(Panel(
                            md,
                            title=title,
                            border_style=panel_color,
                            padding=(1, 2),
                        ))
                    break

        if error_msg:
            console.print(f"[bold red]{error_msg}[/bold red]")
            return None, None, tool_count

        session.add_tokens(stream_usage["input"], stream_usage["output"])
        turn_input += stream_usage["input"]
        turn_output += stream_usage["output"]

        if tool_calls_received:
            tool_count += len(tool_calls_received)

            current_signature = json.dumps(
                [{"name": tc["function"]["name"], "args": tc["function"]["arguments"]}
                 for tc in tool_calls_received],
                sort_keys=True
            )
            if current_signature == prev_tool_signature:
                repeat_count += 1
                if repeat_count >= 3:
                    console.print("[dim]  Repeated same tool calls 3 times — stopping.[/dim]")
                    return "Reached maximum tool iterations (repeated calls).", (turn_input, turn_output), tool_count
            else:
                repeat_count = 0
                prev_tool_signature = current_signature

            assistant_msg = {
                "role": "assistant",
                "content": collected_text or "",
                "tool_calls": tool_calls_received,
            }
            payload.append(assistant_msg)

            for tc in tool_calls_received:
                if check_stop_key():
                    return "[Interrupted by user]", (turn_input, turn_output), tool_count

                name = tc["function"]["name"]
                args = json.loads(tc["function"]["arguments"])
                tc_id = tc["id"]

                if name == "run_command":
                    cmd = args["cmd"]
                    choice = confirm_command(cmd)
                    if isinstance(choice, tuple) and choice[0] == "e":
                        cmd = choice[1]
                        choice = confirm_command(cmd)
                    if choice == "n":
                        result = "User declined to run the command."
                        session.record("run_command", cmd, error=False)
                    else:
                        tool_start = time.time()
                        spinner_text = _next_spinner_text()
                        with console.status(
                            f"[bold cyan]{spinner_text}[/bold cyan]",
                            spinner="dots",
                        ):
                            show_action("Running", cmd)
                            result = run_command(cmd)
                            show_result(result)
                            elapsed = time.time() - tool_start
                            if elapsed > 2:
                                console.print(f"[dim]  Took {elapsed:.1f}s[/dim]")
                        is_error = result.startswith("ERROR:")
                        session.record("run_command", cmd, error=is_error)
                        if elapsed > 2:
                            _ring_bell()
                else:
                    tool_start = time.time()
                    spinner_text = _next_spinner_text()
                    with console.status(
                        f"[bold cyan]{spinner_text}[/bold cyan]",
                        spinner="dots",
                    ):
                        if name == "read_file":
                            show_action("Reading", args["path"])
                            result = read_file(args["path"])
                            session.record("read_file", args["path"])
                        elif name == "write_file":
                            show_action("Writing", args["path"])
                            diff = write_file(args["path"], args["content"])
                            show_diff(diff)
                            result = f"File written: {args['path']}"
                            session.record("write_file", args["path"])
                        elif name == "list_directory":
                            path = args.get("path", ".")
                            show_action("Listing", path)
                            data = list_directory(path)
                            result = json.dumps(data)
                            session.record("list_directory", path)
                        else:
                            result = f"Unknown tool: {name}"
                        elapsed = time.time() - tool_start
                        if elapsed > 2:
                            console.print(f"[dim]  Took {elapsed:.1f}s[/dim]")
                        if elapsed > 2:
                            _ring_bell()

                result_data = json.dumps(
                    {"tool_call_id": tc_id, "name": name, "result": result}
                )
                payload.append({
                    "role": "tool",
                    "tool_call_id": tc_id,
                    "content": result_data,
                })

            continue

        return collected_text, (turn_input, turn_output), tool_count

    return "Reached maximum tool iterations.", (turn_input, turn_output), tool_count


def _build_token_bar(total_tokens: int, max_tokens: int = MAX_CONTEXT_TOKENS) -> str:
    """Return a 10-character progress bar showing context usage."""
    fill = min(total_tokens / max_tokens, 1.0)
    filled_blocks = int(fill * 10)
    return "\u2588" * filled_blocks + "\u2591" * (10 - filled_blocks)


def _token_bar_style(total_tokens: int, max_tokens: int = MAX_CONTEXT_TOKENS) -> str:
    """Return a Rich style string for the token bar based on usage percentage."""
    pct = min(total_tokens / max_tokens * 100, 100)
    if pct < 10:
        return "dim"
    elif pct < 30:
        return "green"
    elif pct < 60:
        return "bright_yellow"
    elif pct < 85:
        return "orange1"
    else:
        return "bold bright_red"


def show_token_line(turn_input: int, turn_output: int):
    turn_total = turn_input + turn_output
    totals = session.get_token_totals()
    pct = min(totals["total"] / MAX_CONTEXT_TOKENS * 100, 100)
    style = _token_bar_style(totals["total"])

    if pct < 10 and totals["turns"] < 3:
        return

    bar = _build_token_bar(totals["total"])
    console.print(
        f"[{style}]  [{bar}] {pct:>3.0f}%  {totals['total']:>6,} / {MAX_CONTEXT_TOKENS:,} tokens  "
        f"({totals['turns']} turn{'s' if totals['turns'] != 1 else ''})[/{style}]"
    )
    if totals["total"] > CONTEXT_WARNING_THRESHOLD:
        console.print(
            "[yellow]  ⚠  context filling up — consider /clear or /save before continuing[/yellow]"
        )


def _slash_command_table() -> Table:
    """Return a Rich Table listing all slash commands."""
    table = Table(title="Slash Commands", title_style="bold cyan", box=None)
    table.add_column("Command", style="bold dodger_blue2", width=10)
    table.add_column("Description", style="dim")
    for cmd, desc in SLASH_COMMANDS.items():
        table.add_row(cmd, desc)
    return table


def handle_slash_command(cmd_line: str, conversation_history, panel_color) -> bool:
    """Handle a slash command. Returns True if consumed, False to pass through to AI."""
    stripped = cmd_line.strip()
    parts = stripped.split()
    command = parts[0].lower() if parts else ""
    arg = " ".join(parts[1:]) if len(parts) > 1 else ""

    if stripped == "/":
        console.print(_slash_command_table())
        return True

    if command == "/help":
        console.print(_slash_command_table())
        return True

    if command == "/clear":
        console.print("[dim]  Clear conversation history? [Y/N] [/dim]", end="")
        key = readchar.readkey().lower()
        console.print("[bold green]Y[/bold green]" if key == "y" else "")
        if key != "y":
            console.print("[dim]Cancelled.[/dim]")
            return True
        conversation_history.clear()
        console.print("[dim]History cleared.[/dim]")
        os.makedirs(SESSION_DIR, exist_ok=True)
        existing = sorted(
            [f for f in os.listdir(SESSION_DIR) if f.endswith(".json")],
            reverse=True,
        )
        if existing:
            latest = existing[0]
            console.print(
                f"[dim]  Also delete saved file '{latest}'? [Y/N] [/dim]", end=""
            )
            key2 = readchar.readkey().lower()
            if key2 == "y":
                console.print("[bold green]Y[/bold green]")
                os.remove(os.path.join(SESSION_DIR, latest))
                console.print(f"[dim]Deleted: {latest}[/dim]")
            else:
                console.print("[dim]Save file kept.[/dim]")
        return True

    if command == "/status":
        log_text = session.get_log_as_text()
        console.print(Panel(log_text, title="Session Activity", border_style="dim"))
        return True

    if command == "/tokens":
        totals = session.get_token_totals()
        pct = min(totals["total"] / MAX_CONTEXT_TOKENS * 100, 100)
        style = _token_bar_style(totals["total"])
        bar = _build_token_bar(totals["total"])
        console.print(f"[bold]Token Usage[/bold]")
        console.print(f"  [dim]Turns:   [/dim]{totals['turns']}")
        console.print(f"  [dim]Input:   [/dim]{totals['input']:>6,}")
        console.print(f"  [dim]Output:  [/dim]{totals['output']:>6,}")
        console.print(f"  [dim]Total:   [/dim]{totals['total']:>6,}")
        console.print(f"  [dim]Context: [/dim][{style}][{bar}] {pct:.0f}%  ({totals['total']:,} / {MAX_CONTEXT_TOKENS:,})[/{style}]")
        return True

    if command == "/save":
        name = arg if arg else None
        save_session(conversation_history, filename=name)
        return True

    if command == "/load":
        name = arg if arg else None
        if conversation_history:
            console.print(
                "[dim]  Loading a session will replace current history. Continue? [Y/N] [/dim]",
                end="",
            )
            key = readchar.readkey().lower()
            if key != "y":
                console.print("[dim]Cancelled.[/dim]")
                return True
            console.print("[bold green]Y[/bold green]")
        load_session(conversation_history, filename=name)
        return True

    if command == "/model":
        choice = arg.strip().lower() if arg else ""
        if not choice:
            console.print(
                "[bold]Switch model:[/bold] [bold dodger_blue2][F][/bold dodger_blue2]lash or "
                "[bold dodger_blue2][P][/bold dodger_blue2]ro? [dim](Esc to cancel, Enter default Flash)[/dim] ",
                end="",
            )
            key = readchar.readkey().lower()
            if key in ("\x1b",):
                console.print("[dim]Cancelled.[/dim]")
                return True
            elif key == "p":
                choice = "pro"
                console.print("[bold dodger_blue2]Pro[/bold dodger_blue2]")
            elif key == "f":
                choice = "flash"
                console.print("[bold dodger_blue2]Flash[/bold dodger_blue2]")
            elif key in ("\r", "\n"):
                choice = "flash"
                console.print("[bold dodger_blue2]Flash  (default)[/bold dodger_blue2]")
            else:
                console.print("[dim]Unrecognised — no change.[/dim]")
                return True

        if choice == "pro":
            set_model("deepseek-v4-pro")
            console.print("[dim]Model switched to: deepseek-v4-pro[/dim]")
            session.record("model_change", "deepseek-v4-pro")
        elif choice == "flash":
            set_model("deepseek-v4-flash")
            console.print("[dim]Model switched to: deepseek-v4-flash[/dim]")
            session.record("model_change", "deepseek-v4-flash")
        else:
            console.print(f"[yellow]Unknown model: {choice}. Use 'pro' or 'flash'.[/yellow]")
        return True

    if command == "/bell":
        global _BELL_ENABLED
        _BELL_ENABLED = not _BELL_ENABLED
        status = "ON" if _BELL_ENABLED else "OFF"
        console.print(f"[dim]Completion bell: [bold]{status}[/bold][/dim]")
        if _BELL_ENABLED:
            _ring_bell()
        return True

    return False


def _choose_model() -> tuple:
    """Prompt the user to choose a model. Returns (model_key, display_name)."""
    console.print(
        "\n[bold]Choose model:[/bold] [bold dodger_blue2][F][/bold dodger_blue2]lash or "
        "[bold dodger_blue2][P][/bold dodger_blue2]ro? [dim](default: Flash)[/dim] ",
        end="",
    )
    key = readchar.readkey().lower()
    if key == "f":
        console.print("[bold dodger_blue2]Flash[/bold dodger_blue2]")
        return "deepseek-v4-flash", "Flash"
    elif key == "p":
        console.print("[bold dodger_blue2]Pro[/bold dodger_blue2]")
        return "deepseek-v4-pro", "Pro"
    elif key in ("\r", "\n"):
        console.print("[dim]Flash  (default)[/dim]")
        return "deepseek-v4-flash", "Flash"
    else:
        console.print(f"[dim]Unrecognised input — using default (Flash)[/dim]")
        return "deepseek-v4-flash", "Flash"


def main():
    conversation_history = []
    panel_color = "dodger_blue2"

    os.makedirs(SESSION_DIR, exist_ok=True)
    session_files = sorted(
        [f for f in os.listdir(SESSION_DIR) if f.endswith(".json")], reverse=True
    )

    header_content = get_header_text()

    if session_files:
        sessions_text = ""
        for sf in session_files[:10]:
            filepath = os.path.join(SESSION_DIR, sf)
            meta = _parse_session_metadata(filepath)
            rel_time = _relative_time(meta["timestamp"])
            sessions_text += (
                f"[bold]{sf}[/bold]"
                f"  [dim]{meta['turns']} turns   {meta['model']}   {rel_time}[/dim]\n"
            )

        sessions_panel = Panel(
            sessions_text.rstrip(),
            title="[bold]Available sessions[/bold]",
            border_style="dodger_blue2",
            padding=(0, 2),
        )

        grid = Table.grid()
        grid.add_column(justify="left", width=75)
        grid.add_column(justify="left")
        grid.add_row(header_content, sessions_panel)
        console.print(grid)

        console.print(
            "\n[dim]Enter session filename or press Enter to start fresh: [/dim]",
            end="",
        )
        user_input = input().strip()
        if user_input:
            filename = user_input if user_input.endswith(".json") else user_input + ".json"
            load_path = os.path.join(SESSION_DIR, filename)
            if os.path.exists(load_path):
                with open(load_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                conversation_history.extend(data.get("conversation_history", []))
                session._log = data.get("session_log", [])
                token_data = data.get("token_totals", {})
                session._input_tokens = token_data.get("input", 0)
                session._output_tokens = token_data.get("output", 0)
                session._turns = token_data.get("turns", 0)
                console.print(f"[dim]Session restored: {os.path.basename(load_path)}[/dim]")
            else:
                console.print(f"[yellow]Session file not found: {filename}[/yellow]")
                console.print("[dim]Starting fresh.[/dim]")
    else:
        console.print(header_content)

    model_key, model_name = _choose_model()
    set_model(model_key)
    console.print(f"[dim]Model: deepseek-v4-{model_name.lower()}[/dim]")

    if _BELL_ENABLED:
        console.print("[dim]Completion bell: ON[/dim]")

    tza_style = Style.from_dict(
        {
            "completion-menu.completion": "bg:#0f2b4a fg:#ffffff",
            "completion-menu.completion.current": "bg:#1c86ee fg:#ffffff bold",
            "prompt-model": "fg:#888888",
        }
    )

    slash_completer = SlashCompleter()

    while True:
        pt_color = "dodgerblue" if panel_color == "dodger_blue2" else "gold"
        model_tag = get_model_display()
        print()
        user_prompt = prompt(
            HTML(
                f'<style color="#888888">[{model_tag}]</style> '
                f'<b><style color="{pt_color}">You ❯</style></b> '
            ),
            style=tza_style,
            completer=slash_completer,
        )

        if user_prompt.lower() in ["exit", "quit"]:
            console.print(f"[bold {panel_color}]Ciao![/bold {panel_color}]")
            sys.exit()

        if user_prompt is not None and user_prompt.strip() == "/":
            console.print(_slash_command_table())
            continue

        if user_prompt.startswith("/"):
            handled = handle_slash_command(user_prompt, conversation_history, panel_color)
            if handled:
                continue

        if user_prompt.startswith("!d") or user_prompt.startswith("!f"):
            prefix = user_prompt[:2]
            rest = user_prompt[2:]
            panel_color = "gold1" if prefix == "!d" else "dodger_blue2"
            if rest.strip() == "":
                console.print(f"[dim]Color: {panel_color}[/dim]")
                continue
            else:
                user_prompt = rest.strip()

        if not user_prompt.strip():
            continue

        conversation_history.append({"role": "user", "content": user_prompt})
        payload, tools = build_payload(conversation_history)

        start = time.time()
        response, turn_usage, tool_count = agent_loop(
            conversation_history, payload, tools, panel_color
        )
        elapsed = time.time() - start

        if response is None:
            conversation_history.pop()
            continue

        conversation_history.append({"role": "assistant", "content": response})

        subtitle_parts = [f"[dim]{elapsed:.2f}s[/dim]"]
        if tool_count > 0:
            subtitle_parts.append(f"[dim]{tool_count} tool{'s' if tool_count != 1 else ''} used[/dim]")
        subtitle = " — ".join(subtitle_parts)

        rendered_markdown = Markdown(response)
        panel = Panel(
            rendered_markdown,
            title=f"[bold {panel_color}] TzakGPT (via DeepSeek)[/bold {panel_color}]",
            subtitle=subtitle,
            border_style=panel_color,
            padding=(1, 2),
        )
        console.print(panel)
        if turn_usage:
            show_token_line(turn_usage[0], turn_usage[1])

        _ring_bell()


if __name__ == "__main__":
    main()
