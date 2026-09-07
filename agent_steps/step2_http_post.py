# -*- coding: utf-8 -*-
# ==================================================================
# 【step2】POST 请求：向网络提交数据
# 调大模型 API 用的全是 POST——这一步必须吃透。
# ==================================================================

import httpx

# ==================================================================
# 【概念】GET vs POST
#   GET  ：适合"取数据"，参数拼在网址里（?a=1&b=2），有长度限制。
#   POST ：适合"提交数据"，数据放在请求体（body）里，可以很大、很复杂。
# 调用大模型要发送"一长段对话"，所以必须用 POST。
# ==================================================================

# 【语法】httpx.post(网址, json=字典)
# json= 这个参数会自动把你的字典转成 JSON 字符串，
# 并且自动加上请求头 Content-Type: application/json。
# 这一步和前端 axios.post(url, data) 是完全对应的。
payload = {
    "name": "易文轩",
    "message": "你好，我是一名前端开发，正在学 Python 转 Agent！",
}

resp = httpx.post("https://httpbin.org/post", json=payload, timeout=30)

print("状态码:", resp.status_code)

# httpbin.org/post 会把我们提交的内容原样返回（叫"回显"），方便验证。
result = resp.json()
print("服务器收到的 json：", result["json"])

# 【概念】请求头 headers：服务器通过它知道"你是什么客户端、传的是什么格式"。
# 调大模型 API 时，我们要在 headers 里放"身份凭证"（API Key），第三步就会用到。
print("请求头 Content-Type：", result["headers"].get("Content-Type"))
