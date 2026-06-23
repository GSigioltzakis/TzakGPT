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


def get_model() -> str:
    """Return the current model key (e.g. 'deepseek-v4-pro')."""
    return _model


def get_model_display() -> str:
    """Return a short display name for the current model ('Pro' or 'Flash')."""
    if "pro" in _model.lower():
        return "Pro"
    return "Flash"


def ask_deepseek(history, tools=None):
    """Non-streaming call — used for summaries and internal tasks."""
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


def ask_deepseek_stream(history, tools=None):
    """Stream tokens from DeepSeek. Generator yields (event, data) tuples.

    Events:
        ("text", str)              — text chunk to display as it arrives
        ("tool_calls", list, dict) — accumulated tool calls + usage dict
        ("done", str, dict)        — final full text + usage dict
        ("error", str)             — error message
    """
    api_key = os.getenv("DEEP_KEY")
    if not api_key:
        yield ("error", "DeepSeek Error: DEEP_KEY not found in environment.")
        return

    client = OpenAI(base_url="https://api.deepseek.com", api_key=api_key)

    kwargs = {"model": _model, "messages": history, "stream": True}
    if tools:
        kwargs["tools"] = tools
        kwargs["tool_choice"] = "auto"

    try:
        stream = client.chat.completions.create(**kwargs)
    except Exception as e:
        yield ("error", f"DeepSeek Error: {e}")
        return

    collected_content = ""
    collected_tool_calls = []
    usage = {"input": 0, "output": 0}

    try:
        for chunk in stream:
            delta = chunk.choices[0].delta if chunk.choices else None
            if delta is None:
                continue

            # Usage info (usually in the last chunk)
            if hasattr(chunk, "usage") and chunk.usage:
                usage["input"] = getattr(chunk.usage, "prompt_tokens", 0) or usage.get("input", 0)
                usage["output"] = getattr(chunk.usage, "completion_tokens", 0) or usage.get("output", 0)

            # Text content
            if delta.content:
                collected_content += delta.content
                yield ("text", delta.content)

            # Tool calls — accumulate across chunks
            if delta.tool_calls:
                for tc_delta in delta.tool_calls:
                    idx = tc_delta.index
                    while len(collected_tool_calls) <= idx:
                        collected_tool_calls.append({
                            "id": "",
                            "type": "function",
                            "function": {"name": "", "arguments": ""}
                        })
                    if tc_delta.id:
                        collected_tool_calls[idx]["id"] = tc_delta.id
                    if tc_delta.function:
                        if tc_delta.function.name:
                            collected_tool_calls[idx]["function"]["name"] = tc_delta.function.name
                        if tc_delta.function.arguments:
                            collected_tool_calls[idx]["function"]["arguments"] += tc_delta.function.arguments
    except Exception as e:
        yield ("error", f"Stream error: {e}")
        return

    if collected_tool_calls:
        yield ("tool_calls", collected_tool_calls, usage)
    else:
        yield ("done", collected_content, usage)
