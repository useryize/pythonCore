# 第一个月 · Python 工程基础（全栈 Agent 方向）

> 学习目标：把"调大模型"这条链路完整打通 —— HTTP 请求 → 调用 LLM API → 流式输出 → 数据校验 → 用 FastAPI 暴露成接口。
> 风格沿用 snake_steps：step1 → step8 渐进，每一步都能独立运行，全程中文注释。

## 8 个步骤总览

| 步骤 | 文件 | 学什么 | 关键产出 |
|---|---|---|---|
| step1 | `step1_http_get.py` | HTTP 基础、GET 请求、JSON 解析 | 第一次向网络要数据 |
| step2 | `step2_http_post.py` | POST 请求、请求体、请求头 | 学会"提交数据"（调大模型全是 POST） |
| step3 | `step3_call_llm.py` | OpenAI 兼容接口、API Key、messages 结构 | **第一次真正调用大模型** |
| step4 | `step4_stream.py` | 流式输出、SSE 协议 | 回答一个字一个字蹦出来 |
| step5 | `step5_pydantic.py` | pydantic 数据校验、字段约束 | 让模型返回的数据"靠谱" |
| step6 | `step6_fastapi.py` | FastAPI 路由、查询参数、自动文档 | 第一个 Web 接口 |
| step7 | `step7_asyncio.py` | async/await、事件循环、并发 | Agent 性能的核心 |
| step8 | `step8_full_agent_api.py` | 以上全部串起来 | **里程碑：流式聊天接口** |

## 环境准备（一次性）

在项目根目录 `C:\code\github\pythonCore` 下执行：

```powershell
# 1. 创建虚拟环境（把依赖装进项目自己的小房间，不影响系统）
python -m venv .venv

# 2. 激活虚拟环境（如果 PowerShell 提示"禁止运行脚本"，用下面第二行替代）
.venv\Scripts\Activate.ps1
# 或者不激活，直接每次用完整路径调用（推荐，最省事）：
#   .venv\Scripts\python.exe 你的命令

# 3. 安装依赖（本目录的 requirements.txt）
pip install -r agent_steps\requirements.txt
```

## 配置 API Key（必做，step3 开始需要）

大模型接口需要"身份凭证"。任选一家，都是 OpenAI 兼容接口，代码不用改。

**方式一：DeepSeek（推荐入门，便宜）**
1. 打开 https://platform.deepseek.com 注册登录
2. 左侧「API Keys」→ 创建 API Key，复制（形如 `sk-xxxx`）
3. 充值几块钱就够了（很便宜）

**方式二：豆包 / 火山方舟（你已经在用豆包）**
1. 打开 https://console.volcengine.com/ark 注册（火山引擎控制台）
2. 开通方舟、创建 API Key
3. 在「在线推理」里创建推理接入点，得到一个 `ep-xxxx` 格式的接入点 ID 作为模型名

**写入配置：**

```powershell
# 在 agent_steps 目录下，把 .env.example 复制一份改名为 .env，填入你的 Key
Copy-Item agent_steps\.env.example agent_steps\.env
# 然后用记事本打开 agent_steps\.env，把 LLM_API_KEY= 后面填上你的 Key
```

## 怎么运行

```powershell
# step1 ~ step5、step7 直接运行（普通脚本）：
python agent_steps\step1_http_get.py

# step6、step8 是 Web 服务，需要启动 uvicorn（从 pythonCore 根目录执行）：
python -m uvicorn agent_steps.step6_fastapi:app --reload
# 然后浏览器打开 http://127.0.0.1:8000/docs 看自动文档

python -m uvicorn agent_steps.step8_full_agent_api:app --reload
# 打开 http://127.0.0.1:8000/docs → /chat → Try it out → 输入消息 → Execute
```

## 里程碑验收标准（第 1 个月毕业）

- [ ] step3：命令行里能看到模型的回答
- [ ] step4：回答是"流式"蹦出来的（不是等半天一次性出现）
- [ ] step5：能看懂 pydantic 的报错信息
- [ ] step6：浏览器 /docs 能看到自动生成的接口文档
- [ ] step7：理解"并发比串行快"的实验对比
- [ ] step8：POST /chat 能流式返回回答 —— 这就是你第一个 Agent 应用的后端雏形
