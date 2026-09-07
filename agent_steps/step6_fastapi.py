# -*- coding: utf-8 -*-
# ==================================================================
# 【step6】FastAPI —— 把代码变成"别人能访问的接口"
# 到目前为止，我们的程序都是自己跑给自己看。
# FastAPI 是一个 Web 框架：它启动一个服务，别人（或你的 Vue 前端）就能通过网址调用你的函数。
# 这是把"Agent 能力暴露出去"的关键一环。
# ==================================================================

# 【语法】from fastapi import FastAPI 导入框架。
from fastapi import FastAPI

# 【语法】FastAPI(title=...) 创建应用实例，title 会显示在自动文档里。
app = FastAPI(title="我的第一个 API")


# 【语法】@app.get("/") 是"装饰器"：把下面这个函数"注册"到 GET / 这个网址上。
# 之后访问 http://127.0.0.1:8000/ 就会执行这个函数，返回值自动转成 JSON 发出去。
# 装饰器可以理解为"贴标签"：给函数贴上"你负责 / 这个地址"的标签。
@app.get("/")
def hello():
    return {"message": "hello agent"}


# 【语法】函数参数 a: int, b: int —— FastAPI 会自动把网址里的 ?a=3&b=5 解析成整数传进来。
# 这就是"查询参数"：前端传小数据最常用的方式。
# 访问 http://127.0.0.1:8000/add?a=3&b=5 试试。
@app.get("/add")
def add(a: int, b: int):
    return {"result": a + b}


# 【运行方法】（在 pythonCore 根目录执行）：
#   python -m uvicorn agent_steps.step6_fastapi:app --reload
#
#   解释一下这条命令：
#     python -m uvicorn     用 python 运行 uvicorn（服务器）
#     agent_steps.step6_fastapi:app   找哪个文件里的哪个变量 —— agent_steps/step6_fastapi.py 里的 app
#     --reload              改代码自动重启（开发神器）
#
#   然后浏览器打开：
#     http://127.0.0.1:8000/              看到 JSON
#     http://127.0.0.1:8000/add?a=3&b=5   看到计算
#     http://127.0.0.1:8000/docs          自动生成的接口文档（FastAPI 白送的大礼！）
#
# 按 Ctrl+C 停止服务。
