import os
import subprocess
import difflib

def read_file(path: str) -> str:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        return f"ERROR: {e}"

def write_file(path: str, new_content: str) -> list:
    old_content = ""
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            old_content = f.read()

    with open(path, "w", encoding="utf-8") as f:
        f.write(new_content)

    diff = list(difflib.unified_diff(
        old_content.splitlines(),
        new_content.splitlines(),
        lineterm=""
    ))
    return diff

def run_command(cmd: str) -> str:
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, timeout=60
        )
        output = result.stdout + result.stderr
        return output.strip() or "(no output)"
    except subprocess.TimeoutExpired:
        return "ERROR: Command timed out after 60 seconds."
    except Exception as e:
        return f"ERROR: {e}"

def list_directory(path: str = ".") -> dict:
    try:
        entries = os.listdir(path)
        files = sorted(e for e in entries if os.path.isfile(os.path.join(path, e)))
        dirs  = sorted(e for e in entries if os.path.isdir(os.path.join(path, e)))
        return {"files": files, "dirs": dirs}
    except Exception as e:
        return {"files": [], "dirs": [], "error": str(e)}