import sys
import time
import random

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from clients import ask_deepseek
from soul import build_payload

console = Console()


def track_ai_speed(ai_function, history):
    start_time = time.time()
    response = ai_function(history)
    end_time = time.time()
    return response, end_time - start_time

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
    selected_greeting = random.choice(greetings)

    console.print(f"[bold dodger_blue2]{logo}[/bold dodger_blue2]")
    console.print("[bold cyan]Welcome to the TzakGPT Multi-AI CLI.[/bold cyan]")
    console.print(f"\n[italic pale_green1]{selected_greeting}[/]")
    console.print("[dim]Type 'exit' or 'quit' to close the app.[/dim]")

def main():
    print_header()
    conversation_history = []

    panel_color = "dodger_blue2"

    while True:
        user_prompt = console.input(f"\n[bold {panel_color}]You ❯[/bold {panel_color}] ")

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
        payload = build_payload(conversation_history, user_prompt)

        #Spinner
        with console.status("[bold cyan]Tzak is thinking...[/bold cyan]", spinner="dots"):
            response, elapsed_time = track_ai_speed(ask_deepseek, payload)

        if response.startswith("DeepSeek Error:"):
            console.print(f"[bold red]{response}[/bold red]")
            conversation_history.pop()
            continue

        time_str = f"{elapsed_time:.2f}s"

        conversation_history.append({"role": "assistant", "content": response})

        #markdown panel
        rendered_markdown = Markdown(response)
        panel = Panel(
            rendered_markdown,
            title=f"[bold {panel_color}] TzakGPT (via DeepSeek)[/bold {panel_color}]",
            subtitle=f"[dim]{time_str}[/dim]",
            border_style=panel_color,
            padding=(1, 2)
        )

        console.print(panel)

if __name__ == "__main__":
    main()