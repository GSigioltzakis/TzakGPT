import re
import random
import readchar
from rich.console import Console
from rich.panel import Panel
from rich import box

console = Console()

_BOX_COLORS = [
    "red", "green", "yellow", "blue", "magenta", "cyan",
    "bright_red", "bright_green", "bright_yellow", "bright_blue",
    "bright_magenta", "bright_cyan", "orange1", "purple4",
    "spring_green2", "deep_sky_blue1", "salmon1", "plum1",
]


def _random_border_style():
    return random.choice(_BOX_COLORS)


def show_diff(diff: list):
    if not diff:
        console.print("[dim]  No changes.[/dim]")
        return

    old_line = 0
    new_line = 0
    lines = []
    for line in diff:
        if line.startswith("---") or line.startswith("+++"):
            continue
        if line.startswith("@@"):
            match = re.search(r"-(\d+)(?:,\d+)? \+(\d+)", line)
            if match:
                old_line = int(match.group(1))
                new_line = int(match.group(2))
            continue
        if line.startswith("-"):
            lines.append(f"[bold red]{old_line:>4} - {line[1:]}[/bold red]")
            old_line += 1
        elif line.startswith("+"):
            lines.append(f"[bold green]{new_line:>4} + {line[1:]}[/bold green]")
            new_line += 1
        else:
            old_line += 1
            new_line += 1

    if lines:
        content = "\n".join(lines)
        panel = Panel(content, border_style=_random_border_style(), padding=(0, 1), width=80, box=box.SQUARE)
        console.print(panel)


def show_action(label: str, detail: str = ""):
    detail_str = f" [dim]{detail}[/dim]" if detail else ""
    console.print(f"[bold cyan]  {label}[/bold cyan]{detail_str}")


def show_result(output: str):
    console.print(Panel(f"[dim]{output}[/dim]", border_style="dim", padding=(0, 1)))


def confirm_command(cmd: str) -> str:
    console.print(f"\n[bold yellow]  Run command:[/bold yellow] [white]{cmd}[/white]")
    console.print("[dim]  [Y] Run   [N] Skip   [E] Edit[/dim]  ", end="")
    while True:
        key = readchar.readkey().lower()
        if key == "y":
            console.print("[bold green]Y[/bold green]")
            return "y"
        elif key == "n":
            console.print("[bold red]N[/bold red]")
            return "n"
        elif key == "e":
            console.print("[bold yellow]E[/bold yellow]")
            edited = console.input(f"  [bold yellow]Edit command:[/bold yellow] ")
            return ("e", edited.strip())
