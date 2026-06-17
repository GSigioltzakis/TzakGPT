# TzakGPT — Local AI Agent CLI

![Image](./image.png)

*A local, terminal-based AI assistant powered by DeepSeek. It doesn't just chat; it reads files, edits code with visual diffs, runs shell commands, and remembers your sessions.*
 
## How It Works
 
### Agentic Tool Execution
TzakGPT isn't just a conversational wrapper. It is equipped with tools to read files, write to files, list directories, and execute shell commands. 
* **Safe Execution:** Shell commands pause the loop and require explicit `[Y] Run`, `[N] Skip`, or `[E] Edit` confirmation. 
* **Visual Diffs:** File writes instantly output a color-coded, line-numbered diff to the console so you can verify exactly what changed.

### Intelligent Context & Memory
The model is continuously fed your current working directory and a summary of recent actions. To prevent token bloat during long sessions, a **sliding window** algorithm automatically kicks in after 10 turns, seamlessly summarizing older context while keeping recent messages intact. Token usage is tracked and displayed below every response.

### Interactive Slash Commands
Hitting `/` opens a sleek, auto-completing dropdown menu to manage your session:
* `/help` - Show all commands
* `/clear` - Reset conversation history
* `/status` - Show session activity log
* `/tokens` - Show token usage statistics
* `/save [name]` - Save session to disk
* `/load [name]` - Load a saved session (or pick from the visual startup menu)
 
## Project Structure
 
| File | Role |
|---|---|
| `main.py` | UI loop, agent orchestration, interactive prompt handling |
| `clients.py` | DeepSeek API integration and token extraction |
| `soul.py` | System prompt, tool schemas, and sliding window context logic |
| `tools.py` | Local file reading, writing, and secure shell execution |
| `session.py` | Telemetry, action logging, and token counting |
| `display.py` | TUI components, red/green visual diffs, and confirmation prompts |
 
## Setup
 
### Requirements
- Python 3.10+
- A DeepSeek API key

### Install dependencies
```bash
pip install -r requirements.txt