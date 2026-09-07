# -*- coding: utf-8 -*-
# ==================================================================
# 【step4】流式输出（stream）—— 让回答"蹦"出来
# 之前是"等模型全部生成完，一次性返回"。生成一段长文可能要等几十秒，
# 用户只能干瞪眼。流式 = 服务器生成一个字、发一个字，我们边收边显示。
# 你平时用豆包 / DeepSeek 看到字一个一个蹦出来，就是流式。
# ==================================================================

import os
import json
import httpx
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")

API_KEY = os.getenv("LLM_API_KEY")
BASE_URL = os.getenv("LLM_BASE_URL", "https://api.deepseek.com")
MODEL = os.getenv("LLM_MODEL", "deepseek-chat")

if not API_KEY:
    print("还没有配置 LLM_API_KEY！请先看 README.md 的『配置 API Key』部分。")
    exit(1)

payload = {
    "model": MODEL,
    "messages": [
        {"role": "system", "content": "你是一个乐于助人的助手。"},
        {"role": "user", "content": "写一段 50 字左右的小故事，介绍什么是 AI Agent。"},
    ],
    # 【关键】stream: True 就是告诉服务器：请边生成边发，不要等我全部完成。
    "stream": True,
}

headers = {"Authorization": f"Bearer {API_KEY}"}

# 【语法】httpx.stream("POST", ...) 建立流式连接。
# 注意：这里不能用 httpx.post —— stream 版本不会等服务器返回完，而是允许我们逐行读取。
with httpx.stream("POST", f"{BASE_URL}/chat/completions",
                  json=payload, headers=headers, timeout=120) as resp:

    # 【核心概念】SSE（Server-Sent Events）：服务器推送消息的文本格式。
    # 流式返回的每一块长这样：
    #   data: {"choices":[{"delta":{"content":"你"}}]}
    #   data: {"choices":[{"delta":{"content":"好"}}]}
    #   ... 最后来一个：
    #   data: [DONE]
    # 所以我们要做的就是：逐行读 → 只处理 data: 开头的内容 → 把 content 拼起来。
    for line in resp.iter_lines():
        if not line or not line.startswith("data:"):
            continue  # 跳过空行和 SSE 协议里的注释行

        data_str = line[len("data:"):].strip()  # 去掉开头的 "data:" 和空白
        if data_str == "[DONE]":
            break  # 服务器说：发完了，收工

        obj = json.loads(data_str)
        # 【概念】delta 是"增量"：这一行新增的那一小段文字（可能是空字符串）。
        delta = obj["choices"][0]["delta"].get("content", "")
        # 【语法】print(delta, end="", flush=True)：不换行、不攒缓冲，立刻输出。
        # flush=True 很重要——不加它，Python 会把输出攒起来，看起来就不"流"了。
        print(delta, end="", flush=True)

print()  # 换行收尾

# 【对比实验】把上面 payload 里的 "stream": True 改成 False 再跑一次，
# 感受一下"等很久然后一次性全出来"和"一个字一个字蹦出来"的区别。
# 这就是为什么所有大模型产品都默认开流式——体验差距非常大。
