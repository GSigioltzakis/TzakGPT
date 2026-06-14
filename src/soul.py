import os

FILE_TRIGGER_KEYWORDS = [
    "file", "files", "directory", "folder", "read", "open", "look at",
    "show me", "what's in", "whats in", "list", "ls", "dir", ".py",
    ".txt", ".bat", ".json", ".csv", ".md", ".env"
]

def needs_file_context(prompt: str) -> bool:
    """Returns True if the user's message seems to be about files."""
    lowered = prompt.lower()
    return any(keyword in lowered for keyword in FILE_TRIGGER_KEYWORDS)

def build_system_context() -> dict:
    """
    Scans the current working directory and builds a system message.
    Injected into the payload only when the user asks about files.
    """
    cwd = os.getcwd()
    try:
        entries = os.listdir(cwd)
        files = [e for e in entries if os.path.isfile(os.path.join(cwd, e))]
        dirs  = [e for e in entries if os.path.isdir(os.path.join(cwd, e))]

        file_list = "\n".join(f"  - {f}" for f in sorted(files)) or "  (none)"
        dir_list  = "\n".join(f"  - {d}/" for d in sorted(dirs))  or "  (none)"

        content = (
            f"You are TzakGPT, a helpful CLI assistant running locally on the user's machine.\n\n"
            f"IMPORTANT: The following file information was collected directly from the user's filesystem "
            f"by the TzakGPT application itself — you do NOT need to access anything. It has already been "
            f"done for you and the results are below. This is real, live data. Use it confidently.\n\n"
            f"Working directory: {cwd}\n\n"
            f"Files in this directory:\n{file_list}\n\n"
            f"Subdirectories:\n{dir_list}\n\n"
            f"When the user asks about files or the directory, answer using the information above directly. "
            f"Do not say you cannot see files — you already have the listing."
        )
    except Exception:
        content = "You are TzakGPT, a helpful CLI assistant."

    return {"role": "system", "content": content}

def build_payload(conversation_history: list, user_prompt: str) -> list:
    """
    Returns the final message list to send to the API.
    Prepends the file-aware system message only when the prompt warrants it.
    """
    if needs_file_context(user_prompt):
        return [build_system_context()] + conversation_history
    return conversation_history