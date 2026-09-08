import os
import httpx
import json
from dotenv import load_dotenv
from pathlib import Path
from pydantic import BaseModel, Field

from fastapi import FastAPI
import uvicorn

import asyncio


def main():

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


def modal_seint():
    class StudyPlan(BaseModel):
        name: str
        days: int = Field(ge=1, le=30)
    json = '{"name": "FastAPI", "days": 3}'
    json = '{"name": "FastAPI", "day2": 2}'
    json = '{"name": "FastAPI", "day3": 1}'
    try:
        plan = StudyPlan.model_validate_json(json)
    except ValueError as e:
        print("Error:", e)
        return

    print("主题:", plan.name)
    print("天数:", plan.days)


def getWebApp():
    app = FastAPI(title='webView:')

    @app.get('/')
    def hello():
        return {"name": "web"}

    @app.get('/add')
    def add(a: int, b: int):
        return {"res": a + b}
    return app

# 异步


def asyncMain():
    async def fetch(client, name, delay):
        print(f"{name}开始：，预计{delay}秒")
        await asyncio.sleep(delay)
        print(f"{name}完成")
        return f"{name}完成"

    async def fun():
        async with httpx.AsyncClient() as client:
            res = await asyncio.gather(
                fetch(client, "查数据", 3),
                fetch(client, "查资料", 2),
                fetch(client, "查天气", 1)
            )
        print("全部查完:", res)
    asyncio.run(fun())


if __name__ == "__main__":
    # app = getWebApp()
    # # uvicorn.run(app, host='127.0.0.1', port=8787, reload=True)
    # uvicorn.run(app, host='127.0.0.1', port=8787)

    asyncMain()
