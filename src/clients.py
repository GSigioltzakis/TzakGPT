import os
from openai import OpenAI
from dotenv import load_dotenv

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(SCRIPT_DIR, "../.env"))

# Default model — can be changed at runtime via set_model()
_model = "deepseek-v4-flash"


def set_model(model: str):
    """Dynamically change the model used for all subsequent API calls."""
    global _model
    _model = model


def ask_deepseek(history, tools=None):
    try:
        api_key = os.getenv("DEEP_KEY")
        if not api_key:
            return None, "DeepSeek Error: DEEP_KEY not found in environment.", {"input": 0, "output": 0}

        client = OpenAI(base_url="https://api.deepseek.com", api_key=api_key)

        kwargs = {"model": _model, "messages": history}
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"

        completion = client.chat.completions.create(**kwargs)
        message = completion.choices[0].message

        usage = {"input": 0, "output": 0}
        if hasattr(completion, "usage") and completion.usage:
            usage = {
                "input": getattr(completion.usage, "prompt_tokens", 0),
                "output": getattr(completion.usage, "completion_tokens", 0),
            }

        if message.tool_calls:
            return "tool_call", message, usage
        return "text", message.content, usage

    except Exception as e:
        return None, f"DeepSeek Error: {e}", {"input": 0, "output": 0}
