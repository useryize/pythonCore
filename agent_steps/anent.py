import os
import httpx
import json
from dotenv import load_dotenv
from pathlib import Path

load_dotenv(Path(__file__).parent / ".env")
api_key = os.getenv("LLM_API_KEY")
base_url = os.getenv("LLM_BASE_URL", "https://api.deepseek.com")
model = os.getenv("LLM_MODEL", "deepseek-v4-flash")

if not api_key:
    print("api_key 为空")
    exit(1)

payload = {
    "thinking": {
        "type": "disabled"
    },
    "model": model,
    "messages": [
        {"role": "user", "content": "你好"},
    ],
    "stream": True,
}

headers = {"Authorization": f"Bearer {api_key}"}

with httpx.stream("post", f"{base_url}/chat/completions",
                  json=payload, headers=headers, timeout=120) as resp:

    for chunk in resp.iter_lines():
        if not chunk or not chunk.startswith("data:"):
            continue
        data = chunk[len('data:'):].strip()
        if data == "[DONE]":
            break
        obj = json.loads(data)
        text = obj["choices"][0]["delta"].get("content", "")
        print(text, end="", flush=True)
print()
