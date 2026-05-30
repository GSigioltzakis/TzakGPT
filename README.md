# TzakGPT — Multi AI CLI

![Image](./image.png)

*A terminal-based chat application that races multiple AI models against each other on every prompt and returns the fastest valid response. Built with Python, Rich, and concurrent threading.*


## How It Works?

### The Thread Race

Every time you send a message, TzakGPT fires off requests to **two AI models simultaneously** using Python's `concurrent.futures.ThreadPoolExecutor`. Both models receive the full conversation history and begin generating a response at the same time — in parallel, not sequentially.
Each call is wrapped in a timing function that records exactly how long the model took to respond. The model that finishes first wins the round. The winning response is what gets displayed to you, along with the time it took and how many seconds it beat the other model by.

### Automatic Fallback

The race includes a failure-handling layer. If one model returns an error (quota exhausted, API failure, rate limit), it is disqualified and the other model's response is used automatically — no crash, no interruption. The fallback logic covers three cases:

1) **Both models fail** — a message is shown and the turn is skipped.
2) **Gemini fails** — OpenRouter's response is shown, with a note that Gemini's quota was exhausted.
3) **OpenRouter fails** — Gemini's response is shown, with a note that OpenRouter failed.

This means the app keeps working even if one provider goes down or runs out of credits mid-session.

### Conversation Memory

All responses — regardless of which model produced them — are saved to a shared `conversation_history` list in the unified format `{"role": ..., "content": ...}`. This history is passed to both models on every new prompt, so context is preserved across the entire session. Each client module translates this shared format into the API-specific structure its model expects before making the request.

## Models Used

| Model | Provider | Notes |
|---|---|---|
| Gemini 2.5 Flash | Google AI (via `google-genai`) | Fast, capable, free tier available |
| Free model | OpenRouter (via OpenAI/Deepseek-compatible API) | Routes to available free models |

---

## Setup

### Requirements

- Python 3.10+
- A Google AI API key (for Gemini)
- An OpenRouter API key

### Install dependencies

```bash
pip install requirements.txt
```

### Run

```bash
python main.py
```

Type `exit` or `quit` to close the app.


## Notes

- The app displays responses as rendered Markdown inside a Rich panel.
- The subtitle of each panel shows the winning model's response time and, in a normal race, how many seconds faster it was than the losing model.
