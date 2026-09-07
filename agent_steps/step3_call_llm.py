# -*- coding: utf-8 -*-
# ==================================================================
# 【step3】第一次真正调用大模型！
# 现在几乎所有国产大模型（DeepSeek、豆包、通义、Kimi…）都提供
# 与 OpenAI 完全兼容的接口——学会一个，全都会用。
# ==================================================================

import os
import httpx
from pathlib import Path
from dotenv import load_dotenv

# 【语法】load_dotenv() 读取 .env 文件，把里面的 "名字=值" 变成环境变量。
# 为什么用文件而不是写死在代码里？
#   1. API Key 是密钥，写进代码 = 泄露风险（尤其要提交 GitHub 时）
#   2. 换 Key / 换模型时改文件就行，不用动代码
# Path(__file__).parent 表示"和本文件同目录"，这样从任何地方运行都能找到 .env。
load_dotenv(Path(__file__).parent / ".env")

# 【语法】os.getenv("名字", 默认值)：读取环境变量，读不到就用默认值。
API_KEY = os.getenv("LLM_API_KEY")
BASE_URL = os.getenv("LLM_BASE_URL", "https://api.deepseek.com")  # 默认 DeepSeek
MODEL = os.getenv("LLM_MODEL", "deepseek-chat")

# 【防呆】没配 Key 就直接退出，并提示怎么做（而不是带着空 Key 去请求报错）。
if not API_KEY:
    print("还没有配置 LLM_API_KEY！请先看 README.md 的『配置 API Key』部分。")
    exit(1)

# ==================================================================
# 【核心概念】大模型聊天接口的请求格式（OpenAI 兼容，记住这个结构）：
#   {
#     "model":    模型名字,
#     "messages": 对话历史列表,
#     "stream":   是否流式返回（默认 False）
#   }
#
# messages 里的每条消息有 role 和 content：
#   system    系统设定：告诉模型"你是谁、该怎么回答"（可选但强烈推荐）
#   user      用户说的话
#   assistant 模型之前说过的话（多轮对话时要把历史带上）
# ==================================================================
payload = {
    "model": MODEL,
    "messages": [
        {"role": "system", "content": "你是一个耐心的 Python 学习助手，回答要简洁、给例子。"},
        {"role": "user", "content": "用一句话说明：什么是 AI Agent？"},
    ],
}

# 【语法】headers 请求头：Authorization 是"身份凭证"。
# "Bearer 后面跟你的 Key" 是 OpenAI 兼容接口的统一写法，别拼错格式。
headers = {"Authorization": f"Bearer {API_KEY}"}

# 【语法】timeout=60 是超时时间（秒）：60 秒没返回就报错，防止程序一直卡死。
resp = httpx.post(f"{BASE_URL}/chat/completions", json=payload, headers=headers, timeout=60)

print("状态码:", resp.status_code)

# 【防呆】非 200 就打印服务器返回的错误信息，方便排查（Key 错了、欠费了都会在这里显示）。
if resp.status_code != 200:
    print("请求失败：", resp.text)
    exit(1)

# 【核心概念】解析返回结果。OpenAI 兼容接口的返回结构是固定的：
#   data["choices"][0]["message"]["content"]   ← 模型回答的正文
# choices 是列表（一般只有 1 个），[0] 取第一个。
data = resp.json()
answer = data["choices"][0]["message"]["content"]
print("模型的回答：", answer)
