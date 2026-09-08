import os
import httpx
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
    "model": model,
    "messages": [
        {"role": "system", "content": "你是一个耐心的 Python 学习助手，回答要简洁、给例子。"},
        {"role": "user", "content": "用一句话说明：什么是 AI Agent？"},
    ],
}

headers = {"Authorization": f"Bearer {api_key}"}

resp = httpx.post(f"{base_url}/chat/completions",
                  json=payload, headers=headers, timeout=60)

print("状态码:", resp.status_code)

if resp.status_code != 200:
    print("请求失败", resp.text)
    exit(1)
data = resp.json()
print("返回内容:", data)
