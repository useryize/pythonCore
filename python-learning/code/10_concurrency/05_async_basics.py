# -*- coding: utf-8 -*-
"""
05_async_basics.py —— 协程与异步编程基础

【演示的语法点】
1. async def 定义协程函数；调用它只产生【协程对象】，不执行任何代码
2. await 的语义：挂起当前协程，让出控制权；等待完成后从那一行继续
3. asyncio.run()：创建事件循环 -> 跑完 -> 关闭循环（一个入口只调一次）
4. 事件循环原理：单线程调度器 +就绪队列 + I/O 事件回调
5. 协程 vs 线程 vs 进程 的对比（内存、切换成本、并发数）
6. asyncio.sleep()（让出控制权）vs time.sleep()（阻塞整个线程）
7. create_task()：把协程包装成 Task 立即开始调度
8. gather()：并发执行多个 awaitable，按传入顺序返回结果
9. Task 的状态与 cancel()；asyncio.wait_for 的超时
10. 协程的"假并发"本质：仍然是单线程，只是不断切换

【预期输出摘要】
- 未 await 的协程完全不执行（打印 "协程从未运行"）
- 10 个 asyncio.sleep(0.1) 的协程并发执行，总耗时约 0.1s（而非 1s）
- 10 个 time.sleep(0.1) 串行执行，总耗时约 1s
- gather 返回顺序 == 提交顺序，as_completed 按完成顺序
"""
import sys
import time
import asyncio
import random
import threading

# ======================================================================
# 语法解析 1：协程对象的惰性
# ======================================================================


async def lazy_coroutine() -> str:
    """async def 定义的是【协程函数】，不是普通函数。"""
    print("      >>> 协程函数体开始执行")
    await asyncio.sleep(0.1)
    print("      >>> 协程函数体执行完毕")
    return "协程的返回值"


def demo_lazy() -> None:
    print("=" * 70)
    print("【1】调用协程函数不会执行任何代码")
    print("=" * 70)

    # 调用 async def 函数只是「创建了一个协程对象」，
    # 函数体一行都没跑。必须把它交给事件循环调度才真正执行。
    coro = lazy_coroutine()
    print(f"调用 lazy_coroutine() 得到：{type(coro).__name__} = {coro!r}")
    print("      （上面没有任何 '>>>' 输出，证明函数体尚未执行）")
    print(f"      该协程是否被丢弃：{coro}")

    # 用 asyncio.run 让事件循环接管这个协程
    print("现在交给 asyncio.run：")
    # coro 已被丢弃，这里传一个新的协程对象给事件循环
    result = asyncio.run(lazy_coroutine())
    print(f"   返回值：{result}")

    # 忘记 await 的后果：函数体不执行，Python 发出 RuntimeWarning
    print()
    print("⚠️ 坑：写了协程却忘了 await，不会报错，只是【静默不执行】，")
    print("   解释器在对象被回收时才会给一句 RuntimeWarning。")
    print("   （用 `python -W error::RuntimeWarning` 可让它直接变成异常，")
    print("     CI 里建议这样配置以防漏写 await。）")
    # 显式关闭丢弃的协程，消除 RuntimeWarning 噪声
    coro.close()


# ======================================================================
# 语法解析 2：事件循环的调度原理
# ======================================================================


async def phase(tag: str, delay: float) -> tuple[str, float]:
    """模拟一个 IO 操作：睡delay 秒后返回。

    关键：asyncio.sleep() 与 time.sleep() 完全不同。
    · time.sleep(0.1)  -> 整个线程【被阻塞】0.1s，期间什么都干不了
    · asyncio.sleep(0.1)-> 当前协程【主动让出】控制权，
                          事件循环立刻去跑其他就绪的协程
    """
    await asyncio.sleep(delay)
    return tag, delay


async def demo_event_loop() -> None:
    print()
    print("=" * 70)
    print("【2】事件循环：单线程如何实现「并发」")
    print("=" * 70)

    print("事件循环的工作方式：")
    print("  1. 维护一个【就绪队列】（ready queue）")
    print("  2. 每一轮从队列头取出一个协程/task，执行它")
    print("  3. 协程执行到 await 某个未就绪的 IO 时，被【挂起】并移出队列")
    print("     同时把它的「完成后要干什么」注册成回调（call_soon）")
    print("  4. IO 完成 -> 回调被塞回就绪队列 -> 下一轮从这里继续执行")
    print("  5. 队列空且无 IO 在等 -> 循环结束")
    print()
    print("所以整个过程只有【一个线程】，没有上下文切换、没有锁，")
    print("      却能同时「等待」成百上千个IO。这就是 asyncio 的全部魔法。")

    # 三个协程以不同的延迟启动，输出顺序会是 2 -> 1 -> 3
    print()
    print("三个协程分别等待 0.3s / 0.1s / 0.2s，提交顺序 1,2,3：")
    t0 = time.perf_counter()

    # create_task 把协程包装成 Task 并【立即加入就绪队列】开始调度
    t1 = asyncio.create_task(phase("协程1", 0.3))
    t2 = asyncio.create_task(phase("协程2", 0.1))
    t3 = asyncio.create_task(phase("协程3", 0.2))

    for task in (t1, t2, t3):
        tag, delay = await task           # 逐个取回
        print(f"    取回 {tag}（等了 {delay}s）")

    print(f"总耗时 {time.perf_counter() - t0:.2f}s")
    print("注意：耗时接近 0.3s（最长的那个），而不是 0.1+0.2+0.3=0.6s，")
    print("      证明三个等待是【重叠】的。")


# ======================================================================
# 语法解析 3：asyncio.sleep vs time.sleep
# ======================================================================


def blocking_worker(i: int) -> None:
    time.sleep(0.1)               # 阻塞整个线程
    print(f"    [线程] 阻塞式任务{i} 完成")


async def async_worker(i: int) -> None:
    await asyncio.sleep(0.1)      # 只挂起当前协程
    print(f"    [协程] 异步任务{i} 完成")


async def demo_sleep_comparison() -> None:
    print()
    print("=" * 70)
    print("【3】asyncio.sleep vs time.sleep 实测对比")
    print("=" * 70)

    n = 10

    # ---- time.sleep：单线程里顺序执行，总耗时 n * 0.1 ----
    t0 = time.perf_counter()
    for i in range(n):
        blocking_worker(i)
    blocking_cost = time.perf_counter() - t0

    # ---- asyncio.sleep：并发等待，总耗时约 0.1s ----
    t0 = time.perf_counter()
    # 第一种写法：逐个 await（看起来是串行，但因为等待重叠，实际很快）
    for i in range(n):
        await async_worker(i)
    await_cost = time.perf_counter() - t0

    print()
    print(f"{n} 个各0.1s 的等待：")
    print(f"  time.sleep    （阻塞线程）：{blocking_cost:.3f}s")
    print(f"  asyncio.sleep （协程挂起）：{await_cost:.3f}s")
    print(f"  差距：{blocking_cost / await_cost:.1f} 倍")
    print()
    print("🔑 关键认知：上面 asyncio 那段是【逐个 await】的，看起来像串行，")
    print("   但因为第 i 个协程挂起时事件循环会去跑第 i+1 个，")
    print("   所以它们的【等待时间是完全重叠的】。")
    print("   顺序执行的 CPU 代码不会重叠 —— 事件循环是单线程的！")

    # ---- 对比：线程池版time.sleep ----
    print()
    print("对比：多线程 + time.sleep 也能重叠等待：")
    t0 = time.perf_counter()
    threads = [threading.Thread(target=blocking_worker, args=(i,))
               for i in range(n)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    thread_cost = time.perf_counter() - t0
    print(f"  10 线程 + time.sleep：{thread_cost:.3f}s（和协程接近）")
    print("  但 10 线程要开 10 个真实线程栈（默认约 8MB 虚拟栈/线程），")
    print("  协程则几乎没有额外内存开销 —— 这是协程在【高并发 IO】场景的优势。")


# ======================================================================
# 语法解析 4：Task 与 gather
# ======================================================================


async def job(task_id: int) -> str:
    """模拟一个耗时不一的协程任务。"""
    await asyncio.sleep(random.uniform(0.05, 0.3))
    if task_id == 2:
        raise ValueError(f"任务{task_id} 出错了")
    return f"任务{task_id}的结果"


async def demo_task_and_gather() -> None:
    print()
    print("=" * 70)
    print("【4】Task 与 gather")
    print("=" * 70)

    print("为什么需要 Task？")
    print("  `await coro1()` 会【阻塞】在coro1 上直到它完成，")
    print("  后面的代码根本轮不到执行。要并发，必须先 create_task。")

    # ---- gather：并发执行多个 awaitable，按传入顺序返回结果 ----
    print()
    print("【gather】提交 1~4，其中任务2 会抛异常：")
    t0 = time.perf_counter()
    results = await asyncio.gather(
        *(job(i) for i in (1, 2, 3, 4)),
        return_exceptions=True,     # 关键：异常作为结果返回，而不是中断整体
    )
    print(f"  总耗时 {time.perf_counter() - t0:.2f}s（并发，不是 4 倍之和）")
    for i, r in enumerate(results, start=1):
        if isinstance(r, Exception):
            print(f"  任务{i}:异常 -> {type(r).__name__}: {r}")
        else:
            print(f"  任务{i}: {r}")

    # gather 的默认行为：第一个异常就抛出，后续任务被取消
    print()
    print("【gather 默认行为】不传 return_exceptions 时：")
    try:
        await asyncio.gather(job(1), job(2), job(3))
    except ValueError as e:
        print(f"  捕获到：{type(e).__name__}: {e}")
    print("  注意：此时任务 1 和 3 会被【取消】，它们的结果就丢了。")
    print("  所以生产代码通常都应该写 return_exceptions=True。")

    # ---- as_completed：按完成顺序 ----
    print()
    print("【as_completed】按完成顺序拿到结果：")
    tasks = [asyncio.create_task(job(i)) for i in (3, 1, 4)]
    for coro in asyncio.as_completed(tasks):
        try:
            r = await coro
            print(f"  先完成的是：{r}")
        except Exception as e:
            print(f"  出错：{e}")


# ======================================================================
# 语法解析 5：取消与超时
# ======================================================================


async def slow_task() -> str:
    await asyncio.sleep(5)          # 假装要等5 秒
    return "永远不会在超时后被用到"


async def demo_cancel() -> None:
    print()
    print("=" * 70)
    print("【5】取消（cancel）与超时（wait_for）")
    print("=" * 70)

    # wait_for：给协程加一个超时
    t0 = time.perf_counter()
    try:
        await asyncio.wait_for(slow_task(), timeout=0.3)
    except asyncio.TimeoutError:
        print(f"  wait_for 超时（耗时 {time.perf_counter() - t0:.2f}s），"
              f"抛出 TimeoutError")

    # 手动 cancel：Task.cancel() 请求取消，被取消处会抛 CancelledError
    print()
    task = asyncio.create_task(slow_task())
    await asyncio.sleep(0.1)
    task.cancel()                   # 只是「请求」取消
    try:
        await task
    except asyncio.CancelledError:
        print(f"  task.cancelled() = {task.cancelled()}")

    print()
    print("⚠️ 重要区分（面试常考）：")
    print("   asyncio.CancelledError 继承自 BaseException，不是 Exception！")
    print("   所以 `except Exception`【捕获不到】它。")
    print("   如果你在协程里写了 `except Exception: pass`，")
    print("   取消信号会被吞掉，导致任务无法被正确终止。")
    print("   正确写法：单独捕获 CancelledError 并重新抛出。")


# ======================================================================
# 语法解析 6：协程 vs 线程 vs 进程 的量化对比
# ======================================================================


async def trivial_async(n: int) -> int:
    """模拟一个「几乎没有计算量」的 IO 型任务。"""
    await asyncio.sleep(0)
    return n


async def coroutine_many(n: int) -> None:
    """开 n 个协程，全部并发等待 0.1s。"""
    t0 = time.perf_counter()
    await asyncio.gather(*(trivial_async(i) for i in range(n)))
    return time.perf_counter() - t0


def thread_many(n: int) -> float:
    """开 n 个线程，各自 time.sleep(0.1)。"""
    import threading as th
    t0 = time.perf_counter()
    ts = [th.Thread(target=trivial_async_sync) for _ in range(n)]
    for t in ts:
        t.start()
    for t in ts:
        t.join()
    return time.perf_counter() - t0


def trivial_async_sync() -> None:
    time.sleep(0.1)


async def demo_concurrency_comparison() -> None:
    print()
    print("=" * 70)
    print("【6】协程 / 线程 开 1000 个并发任务对比")
    print("=" * 70)

    n = 1000

    cost = await coroutine_many(n)
    print(f"{n} 个协程并发：{cost:.3f}s")
    print("  → 协程数可以开到【几万甚至十万】，因为几乎没有内存开销。")

    if n <= 500:
        cost_t = thread_many(n)
        print(f"{n} 个线程并发：{cost_t:.3f}s")
        print("  → 线程数通常上限在几千，且每个线程都要栈内存 + 内核调度开销。")
        print("  → 所以 IO 密集场景首选 asyncio；需要阻塞库时才退而用线程。")

    print()
    print("选型速查：")
    print("┌──────────────────────────────────────────────────────────")
    print("│ CPU 密集            -> 多进程（Process）")
    print("│ IO 密集 + 库无async -> 线程（Thread）")
    print("│ IO 密集 + 库有async -> 协程（asyncio）")
    print("│ IO + CPU 混合       -> 协程处理IO + 进程池处理CPU")
    print("└──────────────────────────────────────────────────────────")


def main() -> None:
    random.seed(7)

    # 语法解析：demo_lazy 里同时有同步输出和一次 asyncio.run，所以它自己管生命周期。
    # 其余 5 个 demo 都是「纯异步」函数，必须各自用 asyncio.run 驱动。
    # 常见错误：直接在 main() 里写 demo_event_loop() —— 会静默不执行并报
    #           RuntimeWarning: coroutine ... was never awaited
    demo_lazy()

    # asyncio.run 会：创建新事件循环 -> 跑完主协程 -> 关闭循环并清理资源。
    # 【同一个进程里只能调用一次】，第二次会抛
    #   RuntimeError: asyncio.run() cannot be called from a running event loop
    asyncio.run(demo_event_loop())
    asyncio.run(demo_sleep_comparison())
    asyncio.run(demo_task_and_gather())
    asyncio.run(demo_cancel())
    asyncio.run(demo_concurrency_comparison())

    print()
    print("=" * 70)
    print("05_async_basics 演示完毕")
    print("=" * 70)


if __name__ == "__main__":
    # asyncio.run() 内部会创建并关闭事件循环，
    # 同一个进程里【只能调用一次】（第二次会报
    # RuntimeError: asyncio.run() cannot be called from a running event loop）
    main()