import os
from google import genai
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

def ask_gemini(history):
    """Translates the shared memory bank into Gemini's specific dictionary format."""
    try:
        client = genai.Client()
        
        gemini_history = []
        for msg in history:
            role = "model" if msg["role"] == "assistant" else "user"
            gemini_history.append({"role": role, "parts": [{"text": msg["content"]}]})
            
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=gemini_history,
        )
        return response.text
    except Exception as e:
        return f"Gemini Error: {e}"

def ask_openrouter_free(history):
    try:
        client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=os.getenv("OPENROUTER_API_KEY"),
        )
        completion = client.chat.completions.create(
            extra_headers={
                "HTTP-Referer": "https://github.com/your-username/multi-ai-cli",
                "X-Title": "Student CLI App",
            },
            model="openrouter/free",
            messages=history
        )
        return completion.choices[0].message.content
    except Exception as e:
        return f"OpenRouter Error: {e}"