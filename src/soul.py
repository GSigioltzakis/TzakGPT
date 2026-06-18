import os
import json
import session
import clients

SHELL_ACTIONS = {"run_command"}
FILE_ACTIONS = {"read_file", "write_file", "list_directory"}

TOOLS_DEFINITION = [
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read the contents of a file.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Path to the file."}
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Write or overwrite a file with new content.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Path to the file."},
                    "content": {
                        "type": "string",
                        "description": "Full new content of the file.",
                    },
                },
                "required": ["path", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_command",
            "description": "Run a shell command. Always ask the user before running.",
            "parameters": {
                "type": "object",
                "properties": {
                    "cmd": {
                        "type": "string",
                        "description": "The shell command to run.",
                    }
                },
                "required": ["cmd"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_directory",
            "description": "List files and subdirectories in a given path.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Directory path. Defaults to current directory.",
                    }
                },
                "required": [],
            },
        },
    },
]

SYSTEM_PROMPT = """You are TzakGPT, a local CLI coding assistant running directly on the user's machine.

You have access to tools: read_file, write_file, run_command, list_directory.
Use them whenever the user asks you to do something that requires file access or running commands.
Do not describe what you would do — just do it using the tools.
For edits, always read the file first, then write the full updated content.
Never run shell commands without being instructed to.

NARRATION AND SELF-VERIFICATION RULES:
- Before starting any task that requires more than one tool call, state the plan in one or two sentences before calling the first tool.
- Before each individual tool call, say one sentence describing what you are about to do and why.
- After writing a file, always call read_file on the same path to verify the content is correct before reporting completion.
- Never tell the user something is done unless a tool was actually used to accomplish it. If no tool was called, do not claim the action happened.
- If the result of a tool call contains an error string (starting with "ERROR:"), stop, report the error to the user clearly, and ask how to proceed. Do not continue the task silently after an error."""


def _apply_sliding_window(conversation_history: list) -> list:
    """Collapse old turns into a summary when the conversation grows too long.

    Uses a dynamic keep window: for N user turns, keeps from floor(N/2)+1 onward.
    Conversations with 6 or fewer user turns are left untouched.
    """
    user_turns = [m for m in conversation_history if m.get("role") == "user"]
    n = len(user_turns)

    # Don't collapse small conversations
    if n <= 6:
        return conversation_history

    # Keep from floor(n/2)+1 onward (1-based user-turn index)
    keep_from_turn = n // 2 + 1
    # Convert to 0-based message index: user turns alternate starting at index 0
    split_index = (keep_from_turn - 1) * 2

    if split_index <= 0:
        return conversation_history

    old_part = conversation_history[:split_index]
    recent_part = conversation_history[split_index:]

    summary_messages = [
        {"role": "system", "content": "Summarize this conversation in one paragraph. Be factual and brief."},
        {"role": "user", "content": json.dumps(old_part)},
    ]

    try:
        kind, message, _ = clients.ask_deepseek(summary_messages)
        if kind == "text" and message:
            summary_text = message.strip()
        else:
            raise ValueError("Unexpected response from summary call")
    except Exception as e:
        session.record("window_summary", f"Failed: {e}", error=True)
        return conversation_history

    summary_msg = {"role": "system", "content": f"Summary of earlier conversation: {summary_text}"}
    session.record("window_summary", f"Collapsed {len(old_part)//2} turns into summary")
    return [summary_msg] + recent_part


def classify_action(tool_name: str) -> str:
    if tool_name in SHELL_ACTIONS:
        return "shell"
    return "file"


def build_payload(conversation_history: list) -> tuple:
    cwd = os.getcwd()
    entries = os.listdir(cwd)
    files = sorted(e for e in entries if os.path.isfile(os.path.join(cwd, e)))
    dirs = sorted(e for e in entries if os.path.isdir(os.path.join(cwd, e)))

    file_list = "\n".join(f"  - {f}" for f in files) or "  (none)"
    dir_list = "\n".join(f"  - {d}/" for d in dirs) or "  (none)"

    session_summary = session.get_summary_for_prompt()
    windowed_history = _apply_sliding_window(conversation_history)

    system_content = (
        f"{SYSTEM_PROMPT}\n\n"
        f"Working directory: {cwd}\n"
        f"Files:\n{file_list}\n"
        f"Subdirectories:\n{dir_list}"
    )
    if session_summary:
        system_content += f"\n\nSession activity so far:\n{session_summary}"

    system_msg = {"role": "system", "content": system_content}
    return [system_msg] + windowed_history, TOOLS_DEFINITION
