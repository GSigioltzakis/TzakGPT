import re
import shutil
import readchar
from rich.console import Console
from rich.panel import Panel
from rich import box

console = Console()


# ---------------------------------------------------------------------------
# Diff / action border colours — tied to action type, not random
# ---------------------------------------------------------------------------
def _diff_border_style(action: str = "write"):
    """Return a border colour keyed to the action type.

    Writes  → green   (creating / changing)
    Reads   → blue    (inspecting)
    Shell   → yellow  (caution)
    """
    styles = {
        "write": "bright_green",
        "read":  "bright_blue",
        "shell": "bright_yellow",
    }
    return styles.get(action, "bright_green")


# ---------------------------------------------------------------------------
# Action colours per tool type
# ---------------------------------------------------------------------------
_ACTION_STYLES = {
    "Reading": "bold bright_blue",
    "Writing": "bold bright_yellow",
    "Listing": "bold cyan",
    "Running": "bold yellow",
}


def show_diff(diff: list, action: str = "write"):
    if not diff:
        console.print("[dim]    No changes.[/dim]")
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
        # Adaptive width: fit the terminal, capped at 120
        term_width = shutil.get_terminal_size().columns
        diff_width = min(term_width - 10, 120)
        if diff_width < 40:
            diff_width = 40

        content = "\n".join(lines)
        panel = Panel(
            content,
            border_style=_diff_border_style(action),
            padding=(0, 1),
            width=diff_width,
            box=box.SQUARE,
        )
        console.print(panel)


def show_action(label: str, detail: str = ""):
    style = _ACTION_STYLES.get(label, "bold cyan")
    detail_str = f" [dim]{detail}[/dim]" if detail else ""
    # Subtle indent so actions nest visually under the assistant's response
    console.print(f"  [{style}]{label}[/{style}]{detail_str}")


def show_result(output: str):
    console.print(Panel(f"[dim]{output}[/dim]", border_style="dim", padding=(0, 1)))


def confirm_command(cmd: str) -> str:
    console.print(f"\n[bold yellow]  About to run:[/bold yellow] [white]{cmd}[/white]")
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
