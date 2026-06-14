import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

def ask_deepseek(history, tools=None):
    try:
        api_key = os.getenv("DEEP_KEY")
        if not api_key:
            return None, "DeepSeek Error: DEEP_KEY not found in environment."

        client = OpenAI(
            base_url="https://api.deepseek.com",
            api_key=api_key,
        )

        kwargs = {
            "model": "deepseek-chat",
            "messages": history,
        }
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"

        completion = client.chat.completions.create(**kwargs)
        message = completion.choices[0].message

        if message.tool_calls:
            return "tool_call", message
        return "text", message.content

    except Exception as e:
        return None, f"DeepSeek Error: {e}"