import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

def ask_deepseek(history):
    """Sends the conversation history to DeepSeek using its OpenAI-compatible API."""
    try:
        api_key = os.getenv("DEEP_KEY")
        if not api_key:
            return "DeepSeek Error: DEEP_KEY not found in environment. Add it to your .env file."

        client = OpenAI(
            base_url="https://api.deepseek.com",
            api_key=api_key,
        )
        completion = client.chat.completions.create(
            model="deepseek-chat",
            messages=history
        )
        return completion.choices[0].message.content
    except Exception as e:
        return f"DeepSeek Error: {e}"