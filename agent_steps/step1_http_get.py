# -*- coding: utf-8 -*-
# ==================================================================
# 【step1】认识 HTTP：向网络要数据
# 调大模型之前，先学会最基本的"网络请求"。
# ==================================================================

# 【语法】import 导入第三方库 httpx。
# httpx 是 Python 里最主流的 HTTP 客户端库（比 requests 更现代，天生支持异步）。
# 它就是你在前端用的 fetch / axios 的 Python 版本。
import httpx

# ==================================================================
# 【概念】HTTP 是什么？
# HTTP 是"网页世界的快递协议"：
#   - 客户端（你写的程序）发出一个"请求 request"：我要 GET 某个网址
#   - 服务器处理完，返回一个"响应 response"：状态码 + 数据
# 你每天打开网页，浏览器其实就在不停地发 GET 请求。
# ==================================================================

# 【语法】httpx.get(网址) 发一个 GET 请求，返回一个 Response 对象。
# httpbin.org 是专门用来练习 HTTP 的公共测试网站（不用登录、不用 Key）。
# 路径 /json 会返回一段固定的 JSON 数据，方便我们验证。
resp = httpx.get("https://httpbin.org/json", timeout=30)

# 【概念】resp.status_code 是"状态码"：
#   200 = 成功；404 = 找不到页面；500 = 服务器出错。
# 以后调任何接口，第一步永远是检查状态码，确认请求真的成功了。
print("状态码:", resp.status_code)

# 【概念】resp.json()：把服务器返回的文本解析成 Python 的字典/列表。
# 现在服务器传数据几乎统一用 JSON 格式——它长得就和 Python 的字典一样。
data = resp.json()
print("返回的 JSON：", data)

# 【练习】data 是一个字典，试试打印它有哪些键
print("有哪些键：", list(data.keys()))

# 【提示】如果 httpbin.org 访问超时（国外网站偶尔慢），
# 可以把网址换成 https://api.github.com/users/octocat 再试（GitHub 官方接口，同样不用 Key）。
# 换成它之后，data["login"] 就是用户名字符串。
