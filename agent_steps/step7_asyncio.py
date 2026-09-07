# -*- coding: utf-8 -*-
# ==================================================================
# 【step7】asyncio 异步编程 —— Agent 性能的核心秘密
# 场景：Agent 要同时查 3 个东西（查天气、搜资料、读文件）。
#   同步写法：查完第 1 个 → 干等 → 查第 2 个 → 干等 → 查第 3 个。总耗时 = 三个加起来。
#   异步写法：同时发出 3 个请求，各自等各自的。总耗时 ≈ 最慢的那一个。
# 关键理解：异步不是"干活更快"，而是"等待结果的时候不傻等，先去干别的"。
# ==================================================================

import asyncio
import httpx


# 【语法】async def 定义"协程"（异步函数）。
# 注意：调用 async 函数并不会立刻执行，而是返回一个"协程对象"，要等它被调度。
# 【语法】await 的意思是：在这里等这个异步操作完成；
# 等待期间，事件循环（Python 的总调度员）会趁机去执行别的协程。
async def fetch(client, name, delay):
    print(f"  {name} 开始，预计 {delay} 秒")
    # 模拟一个耗时的网络请求（真实场景里这一行会换成 client.get(...)）
    await asyncio.sleep(delay)
    print(f"  {name} 完成！")
    return f"{name} 的结果"


async def main():
    # 【语法】async with + httpx.AsyncClient()：异步版的 HTTP 客户端。
    # 所有请求共用一个连接池，比每次都新建连接快得多。
    async with httpx.AsyncClient() as client:
        # 【语法】asyncio.gather(协程1, 协程2, ...)：同时启动多个协程，等全部完成再继续。
        # 三个任务总耗时 ≈ 3 秒（最慢的那个），而不是 1+2+3 = 6 秒。
        results = await asyncio.gather(
            fetch(client, "查天气", 3),
            fetch(client, "搜资料", 1),
            fetch(client, "读文件", 2),
        )
    print("\n全部完成，结果：", results)


# 【语法】asyncio.run(协程) 是总入口：创建事件循环 → 运行 main → 结束后关闭。
# 记住固定套路：最外层永远用 asyncio.run() 启动，不要在脚本顶层直接写 await。
asyncio.run(main())

# 【对比实验】把上面三个 fetch 从"放进 gather"改成"依次 await"：
#   r1 = await fetch(client, "查天气", 3)
#   r2 = await fetch(client, "搜资料", 1)
#   r3 = await fetch(client, "读文件", 2)
# 观察总耗时从 ~3 秒变成 ~6 秒 —— 这就是异步的价值。
# 真实 Agent 常常要并行调用多个工具，异步就是它的"同时做多件事"的能力。
