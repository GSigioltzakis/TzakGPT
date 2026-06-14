import os
import json

SHELL_ACTIONS = {"run_command"}
FILE_ACTIONS  = {"read_file", "write_file", "list_directory"}

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
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Write or overwrite a file with new content.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path":    {"type": "string", "description": "Path to the file."},
                    "content": {"type": "string", "description": "Full new content of the file."}
                },
                "required": ["path", "content"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "run_command",
            "description": "Run a shell command. Always ask the user before running.",
            "parameters": {
                "type": "object",
                "properties": {
                    "cmd": {"type": "string", "description": "The shell command to run."}
                },
                "required": ["cmd"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_directory",
            "description": "List files and subdirectories in a given path.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Directory path. Defaults to current directory."}
                },
                "required": []
            }
        }
    }
]

SYSTEM_PROMPT = """You are TzakGPT, a local CLI coding assistant running directly on the user's machine.

You have access to tools: read_file, write_file, run_command, list_directory.
Use them whenever the user asks you to do something that requires file access or running commands.
Do not describe what you would do — just do it using the tools.
For edits, always read the file first, then write the full updated content.
Never run shell commands without being instructed to."""

def classify_action(tool_name: str) -> str:
    if tool_name in SHELL_ACTIONS:
        return "shell"
    return "file"

def build_payload(conversation_history: list, user_prompt: str) -> tuple:
    cwd = os.getcwd()
    entries = os.listdir(cwd)
    files = sorted(e for e in entries if os.path.isfile(os.path.join(cwd, e)))
    dirs  = sorted(e for e in entries if os.path.isdir(os.path.join(cwd, e)))

    file_list = "\n".join(f"  - {f}" for f in files) or "  (none)"
    dir_list  = "\n".join(f"  - {d}/" for d in dirs)  or "  (none)"

    system_content = (
        f"{SYSTEM_PROMPT}\n\n"
        f"Working directory: {cwd}\n"
        f"Files:\n{file_list}\n"
        f"Subdirectories:\n{dir_list}"
    )

    system_msg = {"role": "system", "content": system_content}
    return [system_msg] + conversation_history, TOOLS_DEFINITION