# -*- coding: utf-8 -*-
# ==================================================================
# 【step8 · 完整版】第一个里程碑项目：一个真正能用的"流式聊天接口"！
# 串起前七步的全部知识：
#   step2 POST 请求    → 请求体格式
#   step3 调用大模型   → OpenAI 兼容接口
#   step4 流式输出     → SSE 边收边发
#   step5 pydantic     → 请求参数自动校验
#   step6 FastAPI      → 暴露成 HTTP 接口
#   step7 asyncio      → 异步流式不阻塞
# 你之后可以用前端老本行（fetch + ReadableStream）直接接这个接口。
# ==================================================================

import os
import json
import httpx
from pathlib import Path
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

load_dotenv(Path(__file__).parent / ".env")

API_KEY = os.getenv("LLM_API_KEY")
BASE_URL = os.getenv("LLM_BASE_URL", "https://api.deepseek.com")
MODEL = os.getenv("LLM_MODEL", "deepseek-chat")

if not API_KEY:
    print("还没有配置 LLM_API_KEY！请先看 README.md 的『配置 API Key』部分。")
    exit(1)

app = FastAPI(title="我的第一个 Agent 聊天接口")


# 【语法】继承 BaseModel 定义"请求体"结构（step5 的知识用上了）。
# 前端 POST 过来的 JSON 会被自动校验：
#   message 必须有，且是字符串；system 可选，不传就用默认值。
# 校验不过 → FastAPI 直接返回 422 错误，不会执行到我们的代码。
class ChatRequest(BaseModel):
    message: str
    system: str = "你是一个乐于助人的 AI 助手"


# 【核心】异步生成器：一步一步地"挤出"模型的回答。
# 【语法】async def + yield：这是"异步生成器"——每次 yield 吐出一段文字。
# StreamingResponse 会把吐出来的片段连续不断地发给前端（SSE 格式）。
async def stream_llm(payload):
    # step4（流式）+ step7（异步）合体：
    async with httpx.AsyncClient(timeout=120) as client:
        async with client.stream("POST", f"{BASE_URL}/chat/completions",
                                 json=payload, headers={"Authorization": f"Bearer {API_KEY}"}) as resp:
            # 【语法】async for 异步遍历：逐行读取服务器推送的内容。
            async for line in resp.aiter_lines():
                if not line or not line.startswith("data:"):
                    continue  # 跳过空行和协议注释行
                data = line[len("data:"):].strip()
                if data == "[DONE]":
                    break  # 服务器说发完了
                obj = json.loads(data)
                delta = obj["choices"][0]["delta"].get("content", "")
                if delta:
                    yield delta  # 吐出一小段，立刻交给 StreamingResponse 发给前端


@app.post("/chat")
async def chat(req: ChatRequest):
    # 组装发给大模型的请求（step3 的结构 + 打开流式开关）
    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": req.system},
            {"role": "user", "content": req.message},
        ],
        "stream": True,
    }
    # 【语法】StreamingResponse(生成器, media_type=...)：
    # 把异步生成器输出的片段，以 SSE 流的方式返回给调用方。
    # 前端收到后可以一个字一个字地渲染 —— 这正是大模型产品的标准交互。
    return StreamingResponse(stream_llm(payload), media_type="text/event-stream")


@app.get("/")
def root():
    return {
        "message": "里程碑项目已启动！",
        "docs": "http://127.0.0.1:8000/docs",
    }


# 【运行方法】（在 pythonCore 根目录执行）：
#   1. 先激活虚拟环境：.venv\Scripts\Activate.ps1
#   2. 启动服务：python -m uvicorn agent_steps.step8_full_agent_api:app --reload
#   3. 浏览器打开 http://127.0.0.1:8000/docs
#   4. 在 docs 页找到 /chat → Try it out → 请求体里输入 {"message": "给我讲个笑话"}
#   5. 点 Execute，你会看到回答一个字一个字地流出来（SSE）
#
# 这就是你第一个月学习的毕业作品 —— 它已经是一个"Agent 应用的后端雏形"：
# 前端接上这个接口，就是一个能流式对话的 AI 应用。
# 第 4 个月我们会给它加上 Agent 编排（LangGraph）和前端控制台，那时它就叫"Agent"了。
