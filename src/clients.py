import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()


def ask_deepseek(history, tools=None):
    try:
        api_key = os.getenv("DEEP_KEY")
        if not api_key:
            return None, "DeepSeek Error: DEEP_KEY not found in environment.", {"input": 0, "output": 0}

        client = OpenAI(base_url="https://api.deepseek.com", api_key=api_key)

        kwargs = {"model": "deepseek-chat", "messages": history}
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
