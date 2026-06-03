import sys
import time
import random
import concurrent.futures

# Import the UI components from the Rich library
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Prompt

# Create a console object to handle the beautiful printing
console = Console()

from clients import ask_gemini, ask_openrouter_free

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

        #spinner
        with console.status("[bold cyan]Tzak is thinking... (Racing Models)[/bold cyan]", spinner="dots"):
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future_gemini = executor.submit(track_ai_speed, ask_gemini, conversation_history)
                future_openrouter = executor.submit(track_ai_speed, ask_openrouter_free, conversation_history)

                gemini_res, gemini_time = future_gemini.result()
                openrouter_res, openrouter_time = future_openrouter.result()

        openrouter_res = openrouter_res.replace("</assistant>", "").strip()

        # Determine the winner, disqualifying errors
        gemini_failed = gemini_res.startswith("Gemini Error:")
        openrouter_failed = openrouter_res.startswith("OpenRouter Error:")

        if gemini_failed and openrouter_failed:
            console.print("[bold red]AI models (Gemini/OpenRouter) failed to respond.(tokens filled)[/bold red]")
            continue
        elif gemini_failed:
            winner_name = "OpenRouter"
            winner_res = openrouter_res
            time_str = f"{openrouter_time:.2f}s (Gemini quota exhausted)"
        elif openrouter_failed:
            winner_name = "Gemini 2.5 Flash"
            winner_res = gemini_res
            time_str = f"{gemini_time:.2f}s (OpenRouter failed)"
        #Start of the normal race:
        elif gemini_time < openrouter_time:
            winner_name = "Gemini 2.5 Flash"
            winner_res = gemini_res
            time_saved = openrouter_time - gemini_time
            time_str = f"{gemini_time:.2f}s | {time_saved:.2f}s faster"
        else:
            winner_name = "OpenRouter"
            winner_res = openrouter_res
            time_saved = gemini_time - openrouter_time
            time_str = f"{openrouter_time:.2f}s | {time_saved:.2f}s faster"

        #Save to memory bank
        conversation_history.append({"role": "assistant", "content": winner_res})
        
        #output to markdown panel
        rendered_markdown = Markdown(winner_res)
        panel = Panel(
            rendered_markdown, 
            title=f"[bold {panel_color}] TzakGPT (via {winner_name})[/bold {panel_color}]", 
            subtitle=f"[dim]{time_str}[/dim]",
            border_style=panel_color,
            padding=(1, 2)
        )
        
        console.print(panel)
if __name__ == "__main__":
    main()