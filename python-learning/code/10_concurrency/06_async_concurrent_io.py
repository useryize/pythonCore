# -*- coding: utf-8 -*-
"""
06_async_concurrent_io.py —— 异步 IO 并发实测（不依赖任何第三方库）

【演示的语法点】
1. 用 asyncio.start_server + StreamReader/StreamWriter 手写一个最小 HTTP/1.1 服务端
2. 手写 HTTP 客户端（原生 socket 同步版 / asyncio 异步版各一份）
3. 串行 / 线程池 / 协程 三种方案在【真实本地 HTTP 服务】上的耗时对比
4. asyncio.Semaphore 限流；asyncio.gather 并发聚合
5. asyncio.to_thread：把阻塞库接入 async 世界，以及它的性能代价
6. asyncio.to_thread / run_in_executor 与默认线程池容量的关系
7. 关键陷阱：服务端与阻塞客户端【不能放在同一个事件循环里】

【预期输出摘要】
- 150 个请求，服务端每请求 0.05s（串行理论需 7.5s）
- 串行≈ 7.5s；线程池(20) ≈ 0.6s；协程(150) ≈ 0.2s
- 并发上限 1/5/20/50/150 的耗时呈明显「拐点」
- to_thread 版比原生协程慢，且受默认线程池容量限制
"""
import asyncio
import time
import socket
import threading
from concurrent.futures import ThreadPoolExecutor

# ======================================================================
# 配置
# ======================================================================

HOST = "127.0.0.1"
N_REQUESTS = 150# 请求总数（控制整体运行时间）
SERVER_DELAY = 0.05# 服务端每请求的处理耗时（模拟真实 IO 等待）
MAX_THREADS = 20            # 线程池大小
CONCURRENCY_LEVELS = (1, 5, 20, 50, 150)


# ======================================================================
# 语法解析 1：手写一个最小异步 HTTP 服务端
# ======================================================================


async def handle_client(reader: asyncio.StreamReader,
                         writer: asyncio.StreamWriter) -> None:
    """处理一个 HTTP 请求。

    语法解析：StreamReader / StreamWriter 是 asyncio 的流式接口，
    对应同步 socket 里 recv/send 的异步版本：
      · await reader.readline()  ≈ 阻塞版的 conn.recv()，但不会卡住事件循环
      · writer.write(data) 只是【写入缓冲区】，必须 await writer.drain()
        才能保证数据真正发到网卡
    """
    try:
        # 读请求行：形如 b"GET / HTTP/1.1\r\n"
        request_line = await reader.readline()
        if not request_line:
            return

        # 把请求头读完，直到遇到空行 b"\r\n"
        while True:
            line = await reader.readline()
            if line in (b"\r\n", b"\n", b""):
                break

        # 模拟服务端处理耗时。
        # ⚠️ 关键：这里必须是 await asyncio.sleep()，绝不能写 time.sleep()。
        #    time.sleep 会把整个事件循环卡住 0.05s，
        #    导致所有并发请求排成队 -> 协程优势完全消失。
        await asyncio.sleep(SERVER_DELAY)

        body = b"Hello from async server"
        # 手写 HTTP/1.1 响应。
        # Content-Length 必须正确，否则客户端无法判断消息边界会挂起；
        # Connection: close 让客户端读到 EOF 就知道结束了。
        response = (
            b"HTTP/1.1 200 OK\r\n"
            b"Content-Type: text/plain\r\n"
            + f"Content-Length: {len(body)}\r\n".encode()
            + b"Connection: close\r\n"
            + b"\r\n"
            + body
        )
        writer.write(response)
        await writer.drain()
    except (ConnectionResetError, BrokenPipeError):
        # 客户端提前断开是正常现象，不要让异常刷屏
        pass
    finally:
        writer.close()
        try:
            await writer.wait_closed()
        except Exception:
            pass


class AsyncServerThread:
    """把异步服务端跑在一个【独立线程】里，用自己的事件循环。

    为什么必须单独开线程？这是本文件最关键的坑：

      如果服务端和阻塞客户端共用同一个事件循环，那么：
        客户端调用 time.sleep() / 阻塞 socket.recv()
          -> 整个事件循环被卡住
          -> 服务端根本没机会被调度
          -> 服务端不回包-> 客户端一直等
          -> 互相等待，直接死锁（表现为 socket timeout）

      结论：要对比「同步阻塞方案」和「异步方案」，
            被测对象必须放在同一个线程里，而服务端必须隔离出去。
    """

    def __init__(self, host: str, delay: float):
        self.host = host
        self.delay = delay
        self.port: int = 0
        self._loop: asyncio.AbstractEventLoop | None = None
        self._thread: threading.Thread | None = None
        self._ready = threading.Event()     # 用于等待服务就绪

    async def _serve(self) -> None:
        """在新线程的事件循环中启动服务。"""
        # ⚠️ 绝不能写 time.sleep()，否则同样会卡住这个事件循环
        await asyncio.sleep(self.delay)
        server = await asyncio.start_server(handle_client, self.host, 0)
        # port=0 让 OS 分配空闲端口，随后读出真实端口号
        self.port = server.sockets[0].getsockname()[1]
        self._loop = asyncio.get_running_loop()
        self._ready.set()                   # 通知主线程「我准备好了」
        async with server:
            await server.serve_forever()     # 永久运行，直到被取消

    def start(self) -> int:
        """启动服务并阻塞等待其就绪，返回端口号。"""
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        # 必须等待就绪，否则主线程可能在服务起来前就开始连接
        if not self._ready.wait(timeout=10):
            raise RuntimeError("服务端启动超时")
        return self.port

    def _run(self) -> None:
        """线程入口：创建独立事件循环并运行。"""
        asyncio.run(self._serve())

    def stop(self) -> None:
        """停止服务并等待线程退出。"""
        if self._loop and self._thread:
            # call_soon_threadsafe 是「从其他线程安全地」操作事件循环的方式
            self._loop.call_soon_threadsafe(self._loop.stop)
            self._thread.join(timeout=5)


# ======================================================================
# 语法解析 2：两种客户端
# ======================================================================


def blocking_fetch(host: str, port: int) -> int:
    """同步阻塞客户端：用普通 socket，供串行/线程池方案调用。

    语法解析：用 with 语句管理 socket，
    退出代码块时会自动 close()，即使中途抛异常也能释放文件描述符。
    """
    with socket.create_connection((host, port), timeout=10) as sock:
        sock.sendall(
            f"GET / HTTP/1.1\r\nHost: {host}\r\nConnection: close\r\n\r\n"
            .encode()
        )
        chunks = []
        while True:
            data = sock.recv(4096)
            if not data:
                break                    # 读到 EOF 说明服务端关闭了连接
            chunks.append(data)
        return sum(len(c) for c in chunks)


async def async_fetch(host: str, port: int) -> int:
    """异步客户端：用 asyncio.open_connection，零阻塞。"""
    reader, writer = await asyncio.open_connection(host, port)
    try:
        writer.write(
            f"GET / HTTP/1.1\r\nHost: {host}\r\nConnection: close\r\n\r\n"
            .encode()
        )
        await writer.drain()
        data = await reader.read()         # 一直读到 EOF
        return len(data)
    finally:
        writer.close()
        try:
            await writer.wait_closed()
        except Exception:
            pass


# ======================================================================
# 语法解析 3：四种并发方案
# ======================================================================


def run_serial(port: int) -> float:
    """方案A：串行。发一个等一个，完全不重叠。"""
    t0 = time.perf_counter()
    for _ in range(N_REQUESTS):
        blocking_fetch(HOST, port)
    return time.perf_counter() - t0


def run_threadpool(port: int, workers: int = MAX_THREADS) -> float:
    """方案B：线程池。每个线程独立处理若干请求。"""
    t0 = time.perf_counter()
    with ThreadPoolExecutor(max_workers=workers) as pool:
        # list(...) 必须消费全部 Future，否则 with 退出时会等待，
        # 造成「看起来是并发，其实还是串行」的错觉
        results = list(pool.map(lambda _: blocking_fetch(HOST, port),
                                range(N_REQUESTS)))
    assert all(r > 0 for r in results), "有请求失败"
    return time.perf_counter() - t0


async def run_asyncio(port: int, limit: int, n: int | None = None) -> float:
    """方案C：原生协程并发。用 Semaphore 限流 + gather 聚合。

    限流的必要性：
    · 同时开10 万个连接会耗尽文件描述符，也可能打爆对端
    · Semaphore 就是「协程版的连接池」，语义类似线程池的 max_workers

    参数 n：本次要发多少个请求。默认用模块级的 N_REQUESTS，
            这样既能跑主对比（固定量），也能跑并发扫描（少量）。
    """
    n = N_REQUESTS if n is None else n
    sem = asyncio.Semaphore(limit)

    async def one(_: int) -> int:
        # async with 自动 acquire/release。
        # 即便fetch 抛异常，许可也一定释放，不会泄漏成死锁。
        async with sem:
            return await async_fetch(HOST, port)

    t0 = time.perf_counter()
    results = await asyncio.gather(*(one(i) for i in range(n)))
    cost = time.perf_counter() - t0

    # 断言防止「假并发」：确认每个请求真的拿到了响应
    assert all(r > 0 for r in results), "有请求失败"
    return cost


async def run_asyncio_to_thread(port: int, limit: int) -> float:
    """方案D：协程调度 + to_thread 执行阻塞代码。

    适用场景：手上只有阻塞库（老的 HTTP 客户端、同步 DB 驱动），
             但想接入 asyncio 框架，用 to_thread 就把它「包」成非阻塞的。

    性能代价的根源：
      · 阻塞 socket 仍要走内核态，且每个任务要经历
        「协程 -> 线程 -> 内核 -> 再切回协程」两次调度
      · asyncio.to_thread 用的是【默认线程池】，
        默认容量 min(32, cpu_count + 4)，是个硬上限。
        本例 16 核 -> 默认线程池约 20 个线程，
        所以并发上限开到 150 也没法真正跑满。
    """
    sem = asyncio.Semaphore(limit)

    async def one(_: int) -> int:
        async with sem:
            return await asyncio.to_thread(blocking_fetch, HOST, port)

    t0 = time.perf_counter()
    await asyncio.gather(*(one(i) for i in range(N_REQUESTS)))
    return time.perf_counter() - t0


# ======================================================================
# 语法解析 4：并发量影响
# ======================================================================


async def measure_by_concurrency(port: int, n: int) -> None:
    """固定请求总数，用不同并发上限跑，观察耗时的「拐点」。"""
    print()
    print("=" * 70)
    print(f"【2】并发上限对耗时的影响（请求总量固定为 {n}）")
    print("=" * 70)
    print(f"{'并发上限':<16}{'耗时(s)':<14}{'吞吐(req/s)':<14}")
    print("-" * 44)

    for limit in CONCURRENCY_LEVELS:
        cost = await run_asyncio(port, limit, n)
        # 中文字符占两个终端列，用 ljust 会短一格，这里手动补2 格
        print(f"{limit:<12}{'':<4}{cost:<14.3f}{n / cost:<14.1f}")

    print()
    print("解读：")
    print(f" · 并发=1 就是串行，耗时 ≈ {n} x {SERVER_DELAY} = "
          f"{n * SERVER_DELAY:.1f}s")
    print(f" · 并发够大时，耗时收敛到单次请求耗时 ≈ {SERVER_DELAY}s")
    print(" · 线程池的 max_workers 也有同样的「拐点」效果，")
    print("   区别是线程有明显内存与内核调度成本，协程几乎为 0。")
    print(f" · 耗时下界就是单次请求耗时 {SERVER_DELAY}s，不可能更低。")


# ======================================================================
# 主流程
# ======================================================================


def print_table(results: dict[str, float]) -> None:
    """打印汇总表。

    注意：f-string 的 :<24 是按【字符个数】对齐的，
    而中文字符占两个终端列，中文列会看起来短一格，
    所以这里自己算显示宽度来对齐。
    """
    def disp_width(text: str) -> int:
        return sum(2 if ord(c) > 0x2E80 else 1 for c in text)

    print()
    print("=" * 70)
    print("性能对比汇总")
    print("=" * 70)
    serial_cost = results["串行"]
    print(f"{'方案':<22}{'耗时(s)':<12}{'vs 串行':<12}{'吞吐(req/s)'}")
    print("-" * 64)
    for name, cost in results.items():
        pad = " " * max(0, 22 - disp_width(name))
        print(f"{name}{pad}{cost:<12.3f}"
              f"{f'{serial_cost / cost:.1f}x':<12}{N_REQUESTS / cost:.1f}")


def main() -> None:
    print("=" * 70)
    print("【1】真实本地 HTTP 服务：串行 vs 线程 vs 协程")
    print("=" * 70)

    server = AsyncServerThread(HOST, SERVER_DELAY)
    port = server.start()
    print(f"本地异步服务已在独立线程中启动：http://{HOST}:{port}")
    print(f"配置：{N_REQUESTS} 个请求，服务端每请求耗时 {SERVER_DELAY}s")
    print(f"      串行理论耗时 = {N_REQUESTS} x {SERVER_DELAY} = "
          f"{N_REQUESTS * SERVER_DELAY:.1f}s")
    print()

    try:
        # 连通性验证
        probe_len = asyncio.run(async_fetch(HOST, port))
        print(f"连通性验证通过，收到 {probe_len} 字节响应。")
        print()

        results: dict[str, float] = {}

        print(f"▶ 方案A：串行（同步阻塞 socket，{N_REQUESTS} 次）")
        results["串行"] = run_serial(port)
        print(f"   耗时 {results['串行']:.3f}s")

        print(f"▶ 方案B：线程池（{MAX_THREADS} 线程）")
        results[f"线程池({MAX_THREADS})"] = run_threadpool(port)
        print(f"   耗时 {results[f'线程池({MAX_THREADS})']:.3f}s")

        print(f"▶ 方案C：原生协程（并发上限 {N_REQUESTS}）")
        results["协程(原生)"] = asyncio.run(run_asyncio(port, N_REQUESTS))
        print(f"   耗时 {results['协程(原生)']:.3f}s")

        print("▶ 方案D：协程调度 + to_thread 执行阻塞代码")
        results["协程+to_thread"] = asyncio.run(
            run_asyncio_to_thread(port, N_REQUESTS))
        print(f"   耗时 {results['协程+to_thread']:.3f}s")

        print_table(results)

        print()
        print("结论：")
        print(f"  · 串行 {results['串行']:.2f}s"
              f"  ->  线程池 {results[f'线程池({MAX_THREADS})']:.2f}s"
              f"  ->  原生协程 {results['协程(原生)']:.2f}s")
        print("  · 原生协程最快：没有线程创建/销毁、没有内核态调度、"
              "没有 GIL 争抢。")
        print("  · to_thread 版明显更慢：阻塞 socket 仍要走内核，")
        print("    且受默认线程池容量限制（一般只有十几个线程）。")
        print("  · 工程建议：能用原生 async 库就别用 to_thread 兜底；")
        print("    实在只有阻塞库时，to_thread + Semaphore 是务实的过渡方案。")

        # 并发量扫描（用较少的请求数，避免整体耗时过长）
        asyncio.run(measure_by_concurrency(port, 60))

        print()
        print("=" * 70)
        print("【3】内存开销对比（为什么协程能开十万、线程只能上千）")
        print("=" * 70)
        n = 10_000
        # Linux 上线程默认 8MB 虚拟栈（Windows 上通常 1MB 保留）
        thread_stack_mb = 8
        print(f"{n} 个并发任务时：")
        print(f"  线程方案：约 {n} x {thread_stack_mb}MB = "
              f"{n * thread_stack_mb / 1024:.0f}GB 虚拟栈"
              f"（多数页不实际驻留，但仍是地址空间压力）")
        print(f"  协程方案：每个 Task 约 1~2KB，总计约 {n * 2 / 1024:.0f}MB")
        print("  这就是 asyncio 能支撑十万级并发而线程只能上千的根本原因。")

    finally:
        server.stop()
        print()
        print(f"本地服务已关闭，端口 {port} 已释放。")


if __name__ == "__main__":
    # 本文件不涉及多进程，但保留 main 保护是好习惯：
    # 否则被 import 时会立刻启动服务跑完整轮压测。
    main()
    print()
    print("=" * 70)
    print("06_async_concurrent_io 演示完毕")
    print("=" * 70)