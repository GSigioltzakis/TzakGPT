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

from clients import ask_deepseek
from soul import build_payload, classify_action
from tools import read_file, write_file, run_command, list_directory
from display import show_diff, show_action, show_result, confirm_command

from prompt_toolkit import prompt
from prompt_toolkit.completion import WordCompleter
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.styles import Style

import session

console = Console()

SESSION_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sessions")

CONTEXT_WARNING_THRESHOLD = 50000


def get_header_text() -> str:
    logo = r"""
████████╗███████╗ █████╗ ██╗  ██╗ ██████╗ ██████╗ ████████╗
╚══██╔══╝╚══███╔╝██╔══██╗██║ ██╔╝██╔════╝ ██╔══██╗╚══██╔══╝
   ██║     ███╔╝ ███████║█████╔╝ ██║  ███╗██████╔╝   ██║   
   ██║    ███╔╝  ██╔══██║██╔═██╗ ██║   ██║██╔═══╝    ██║   
   ██║   ███████╗██║  ██║██║  ██╗╚██████╔╝██║        ██║   
   ╚═╝   ╚══════╝╚═╝  ╚═╝╚═╝  ╚═╝ ╚══════╝╚═╝        ╚═╝
    """
    greetings = [
        "Today is a beautiful day full of happiness. Let's build something great!",
        "The flowers are blooming, the sky is shining, and the code is running.",
        "The top of the mountain awaits, one step at a time.",
        "Clear skies ahead. What shall we discover today?",
        "A fresh start, a blank terminal, and infinite possibilities.",
    ]
    return (
        f"[bold dodger_blue2]{logo}[/bold dodger_blue2]\n"
        "[bold cyan]Welcome to TzakGPT AI agent CLI.[/bold cyan]\n"
        f"[italic pale_green1]{random.choice(greetings)}[/]\n"
        "[dim]Type 'exit' or 'quit' to close the app.[/dim]"
    )


def save_session(conversation_history, filename=None):
    os.makedirs(SESSION_DIR, exist_ok=True)
    if filename:
        save_path = os.path.join(SESSION_DIR, filename)
        if not save_path.endswith(".json"):
            save_path += ".json"
    else:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        save_path = os.path.join(SESSION_DIR, f"{timestamp}.json")

    if os.path.exists(save_path):
        console.print(f"[yellow]  File '{os.path.basename(save_path)}' already exists. Overwrite? [Y/N][/yellow] ", end="")
        key = readchar.readkey().lower()
        if key != "y":
            console.print("[dim]Cancelled.[/dim]")
            return False
        console.print("[bold green]Y[/bold green]")

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
            console.print(f"  [{i}] {sf}")
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
    max_iterations = 10
    iteration = 0
    turn_input = 0
    turn_output = 0

    while iteration < max_iterations:
        iteration += 1

        with console.status(
            "[bold cyan]Tzak is thinking...[/bold cyan]", spinner="dots"
        ):
            kind, message, usage = ask_deepseek(payload, tools)

        session.add_tokens(usage["input"], usage["output"])
        turn_input += usage["input"]
        turn_output += usage["output"]

        if kind is None:
            console.print(f"[bold red]{message}[/bold red]")
            return None, None

        if kind == "text":
            return message, (turn_input, turn_output)

        assistant_msg = {
            "role": "assistant",
            "content": message.content or "",
            "tool_calls": [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments,
                    },
                }
                for tc in message.tool_calls
            ],
        }
        payload.append(assistant_msg)

        for tool_call in message.tool_calls:
            result_json = handle_tool_call(tool_call, conversation_history)
            result_data = json.loads(result_json)
            payload.append(
                {
                    "role": "tool",
                    "tool_call_id": result_data["tool_call_id"],
                    "content": result_data["result"],
                }
            )

    return "Reached maximum tool iterations.", (turn_input, turn_output)


def show_token_line(turn_input: int, turn_output: int):
    turn_total = turn_input + turn_output
    totals = session.get_token_totals()
    console.print(
        f"[dim]  tokens: {turn_total} this turn / {totals['total']} session  ({totals['turns']} turns)[/dim]"
    )
    if totals["total"] > CONTEXT_WARNING_THRESHOLD:
        console.print(
            "[yellow]  context filling up — consider /clear or /save before continuing[/yellow]"
        )


def handle_slash_command(cmd_line: str, conversation_history, panel_color) -> bool:
    parts = cmd_line.strip().split()
    command = parts[0].lower()
    arg = " ".join(parts[1:]) if len(parts) > 1 else ""

    if command == "/help":
        table = Table(title="Slash Commands", title_style="bold cyan", box=None)
        table.add_column("Command", style="bold dodger_blue2", width=10)
        table.add_column("Description", style="dim")
        table.add_row("/help", "Show this help message")
        table.add_row("/clear", "Reset conversation history (with confirmation)")
        table.add_row("/status", "Show session activity log")
        table.add_row("/tokens", "Show token usage statistics")
        table.add_row("/save", "Save session checkpoint to disk")
        table.add_row("/load", "Load a saved session")
        console.print(table)
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
        console.print(f"[bold]Token Usage[/bold]")
        console.print(f"  [dim]Turns:   [/dim]{totals['turns']}")
        console.print(f"  [dim]Input:   [/dim]{totals['input']}")
        console.print(f"  [dim]Output:  [/dim]{totals['output']}")
        console.print(f"  [dim]Total:   [/dim]{totals['total']}")
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

    console.print("[yellow]Unknown command. Type /help for available commands.[/yellow]")
    return True


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
            sessions_text += f"{sf}\n"

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

    slash_commands = ["/help", "/clear", "/status", "/tokens", "/save", "/load"]
    command_completer = WordCompleter(slash_commands, ignore_case=True)
    tza_style = Style.from_dict(
        {
            "completion-menu.completion": "bg:#0f2b4a fg:#ffffff",
            "completion-menu.completion.current": "bg:#1c86ee fg:#ffffff bold",
        }
    )

    while True:
        pt_color = "dodgerblue" if panel_color == "dodger_blue2" else "gold"
        print()
        user_prompt = prompt(
            HTML(f'<b><style color="{pt_color}">(O__o) You ❯</style></b> '),
            completer=command_completer,
            style=tza_style,
        )

        if user_prompt.lower() in ["exit", "quit"]:
            console.print(f"[bold {panel_color}]Ciao![/bold {panel_color}]")
            sys.exit()

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
        response, turn_usage = agent_loop(
            conversation_history, payload, tools, panel_color
        )
        elapsed = time.time() - start

        if response is None:
            conversation_history.pop()
            continue

        conversation_history.append({"role": "assistant", "content": response})

        rendered_markdown = Markdown(response)
        panel = Panel(
            rendered_markdown,
            title=f"[bold {panel_color}] TzakGPT (via DeepSeek)[/bold {panel_color}]",
            subtitle=f"[dim]{elapsed:.2f}s[/dim]",
            border_style=panel_color,
            padding=(1, 2),
        )
        console.print(panel)
        if turn_usage:
            show_token_line(turn_usage[0], turn_usage[1])


if __name__ == "__main__":
    main()
