import sys
import time
import random
import json

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel

from clients import ask_deepseek
from soul import build_payload, classify_action
from tools import read_file, write_file, run_command, list_directory
from display import show_diff, show_action, show_result, confirm_command

console = Console()

def print_header():
    logo = r"""
████████╗███████╗ █████╗ ██╗  ██╗ ██████╗ ██████╗ ████████╗
╚══██╔══╝╚══███╔╝██╔══██╗██║ ██╔╝██╔════╝ ██╔══██╗╚══██╔══╝
   ██║     ███╔╝ ███████║█████╔╝ ██║  ███╗██████╔╝   ██║   
   ██║    ███╔╝  ██╔══██║██╔═██╗ ██║   ██║██╔═══╝    ██║   
   ██║   ███████╗██║  ██║██║  ██╗╚██████╔╝██║        ██║   
   ╚═╝   ╚══════╝╚═╝  ╚═╝╚═╝  ╚═╝ ╚═════╝ ╚═╝        ╚═╝                                               
    """
    greetings = [
        "Today is a beautiful day full of happiness. Let's build something great!",
        "The flowers are blooming, the sky is shining, and the code is running.",
        "The top of the mountain awaits, one step at a time.",
        "Clear skies ahead. What shall we discover today?",
        "A fresh start, a blank terminal, and infinite possibilities."
    ]
    console.print(f"[bold dodger_blue2]{logo}[/bold dodger_blue2]")
    console.print("[bold cyan]Welcome to the TzakGPT Multi-AI CLI.[/bold cyan]")
    console.print(f"\n[italic pale_green1]{random.choice(greetings)}[/]")
    console.print("[dim]Type 'exit' or 'quit' to close the app.[/dim]")

def handle_tool_call(tool_call, conversation_history) -> str:
    name = tool_call.function.name
    args = json.loads(tool_call.function.arguments)
    action_type = classify_action(name)

    if name == "read_file":
        show_action("Reading", args["path"])
        result = read_file(args["path"])

    elif name == "write_file":
        show_action("Writing", args["path"])
        diff = write_file(args["path"], args["content"])
        show_diff(diff)
        result = f"File written: {args['path']}"

    elif name == "list_directory":
        path = args.get("path", ".")
        show_action("Listing", path)
        data = list_directory(path)
        result = json.dumps(data)

    elif name == "run_command":
        cmd = args["cmd"]
        choice = confirm_command(cmd)

        if isinstance(choice, tuple) and choice[0] == "e":
            cmd = choice[1]
            choice = confirm_command(cmd)

        if choice == "n":
            result = "User declined to run the command."
        else:
            show_action("Running", cmd)
            result = run_command(cmd)
            show_result(result)
    else:
        result = f"Unknown tool: {name}"

    return json.dumps({
        "tool_call_id": tool_call.id,
        "name": name,
        "result": result
    })

def agent_loop(conversation_history, payload, tools, panel_color):
    max_iterations = 10
    iteration = 0

    while iteration < max_iterations:
        iteration += 1

        with console.status("[bold cyan]Tzak is thinking...[/bold cyan]", spinner="dots"):
            kind, message = ask_deepseek(payload, tools)

        if kind is None:
            console.print(f"[bold red]{message}[/bold red]")
            return None

        if kind == "text":
            return message

        # Tool call
        assistant_msg = {
            "role": "assistant",
            "content": message.content or "",
            "tool_calls": [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments
                    }
                }
                for tc in message.tool_calls
            ]
        }
        payload.append(assistant_msg)

        for tool_call in message.tool_calls:
            result_json = handle_tool_call(tool_call, conversation_history)
            result_data = json.loads(result_json)
            payload.append({
                "role": "tool",
                "tool_call_id": result_data["tool_call_id"],
                "content": result_data["result"]
            })

    return "Reached maximum tool iterations."

def main():
    print_header()
    conversation_history = []
    panel_color = "dodger_blue2"

    while True:
        user_prompt = console.input(f"\n[bold {panel_color}](O__o) You ❯[/bold {panel_color}] ")

        if user_prompt.lower() in ['exit', 'quit']:
            console.print(f"[bold {panel_color}]Ciao![/bold {panel_color}]")
            sys.exit()

        if user_prompt.startswith("!d "):
            panel_color = "gold1"
            user_prompt = user_prompt[3:]
        elif user_prompt.startswith("!f "):
            panel_color = "dodger_blue2"
            user_prompt = user_prompt[3:]

        if not user_prompt.strip():
            continue

        conversation_history.append({"role": "user", "content": user_prompt})
        payload, tools = build_payload(conversation_history, user_prompt)

        start = time.time()
        response = agent_loop(conversation_history, payload, tools, panel_color)
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
            padding=(1, 2)
        )
        console.print(panel)

if __name__ == "__main__":
    main()