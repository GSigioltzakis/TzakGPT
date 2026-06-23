# TzakGPT — Local AI Agent CLI

![Image](./image.png)

*A local, terminal-based AI assistant powered by DeepSeek. It streams responses with live Markdown rendering, reads files, edits code with visual diffs, runs shell commands, and remembers your sessions.*

## How It Works

### Streaming with Interrupt
Responses stream token-by-token into a live-updating panel. Press **X** at any time during thinking or tool execution to interrupt — useful when you realize the model is heading down the wrong path.

### Agentic Tool Execution
TzakGPT isn't just a conversational wrapper. It is equipped with tools to read files, write to files, list directories, and execute shell commands.
* **Safe Execution:** Shell commands pause the loop and require explicit `[Y] Run`, `[N] Skip`, or `[E] Edit` confirmation.
* **Visual Diffs:** File writes instantly output a color-coded, line-numbered diff to the console so you can verify exactly what changed.
* **Status Spinners:** Non-interactive tool executions show an animated spinner with cycling status text so you know what's happening.

### Model Switching
Choose between **Flash** (fast, default) and **Pro** (more capable) models at startup or anytime via `/model`. The current model tag is shown in every prompt.

### Intelligent Context & Memory
The model is continuously fed your current working directory and a summary of recent actions. To prevent token bloat during long sessions, a **sliding window** algorithm automatically kicks in after 6 turns, seamlessly summarizing older context while keeping recent messages intact. Token usage is tracked with a colour-coded progress bar displayed below every response.

### Interactive Slash Commands
Hitting `/` opens a sleek, auto-completing dropdown menu to manage your session:
* `/help` — Show all commands
* `/clear` — Reset conversation history (with confirmation)
* `/status` — Show session activity log
* `/tokens` — Show token usage statistics
* `/save [name]` — Save session checkpoint to disk
* `/load [name]` — Load a saved session (or pick from the visual startup menu)
* `/model [pro|flash]` — Switch models on the fly
* `/bell` — Toggle terminal bell on response completion

### Session Persistence
Sessions are saved as JSON files in `src/sessions/` with auto-increment naming. On startup you'll see recent sessions with turn counts, model used, and relative timestamps. Pick one to resume or start fresh.

## Project Structure

| File | Role |
|---|---|
| `src/main.py` | UI loop, agent orchestration, slash commands, streaming display, model selection |
| `src/clients.py` | DeepSeek API integration via OpenAI client, streaming and non-streaming calls |
| `src/soul.py` | System prompt, tool schemas, sliding window context logic, greeting pool |
| `src/tools.py` | Local file reading, writing (with diff generation), and secure shell execution |
| `src/session.py` | Telemetry, action logging, token counting, session restore |
| `src/display.py` | TUI components: visual diffs, action labels, command confirmation prompts |
| `web/` | Landing page assets |

## Setup

### Requirements
- Python 3.10+
- A DeepSeek API key

### Quick Start
```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Create your .env file
cp .env.example .env

# 3. Edit .env — add your DeepSeek API key
# DEEP_KEY=your_deepai_api_key_here

# 4. Optional: enable the terminal bell on response completion
# TZAK_BELL=true

# 5. Launch
tzak
```

### Environment Variables
| Variable | Purpose |
|---|---|
| `DEEP_KEY` | Your DeepSeek API key (required) |
| `TZAK_BELL` | Enable terminal bell on response completion — set to `true`, `1`, or `yes` (optional) |
