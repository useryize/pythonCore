# -*- coding: utf-8 -*-
"""
02_thread_pool.py —— 线程池 concurrent.futures

【演示的语法点】
1. ThreadPoolExecutor 的创建与 with 语句（自动 shutdown）
2. submit() 提交单个任务，返回 Future 对象
3. Future：result() / done() / exception() / cancel() / cancelled() / add_done_callback()
4. map() 批量映射：返回惰性迭代器，按提交顺序产出结果
5. as_completed()：按「完成顺序」迭代，天然适合异构耗时任务
6. 异常处理：worker 内 try/except vs 统一捕获 Future.exception()
7. 超时控制：Future.result(timeout=...) 与 wait(timEOUT, return_when=...)
8. initializer 初始化钩子 + initargs（每个工作线程跑一次）
9. map 的 chunksize 在线程池中无效（那是 ProcessPoolExecutor 的参数）
10. 常见坑：executor 只能复用，不能中途修改 max_workers

【预期输出摘要】
- 8 个耗时任务并发执行，总耗时 ≈ 单个任务耗时（而非 8 倍）
- map 保持输入顺序；as_completed 按完成顺序返回
- 任务 3 故意抛异常，被捕获后其余任务不受影响
- result(timeout=0.5) 抛出 concurrent.futures.TimeoutError
"""
import time
import random
import threading
from concurrent import futures
from concurrent.futures import ThreadPoolExecutor, as_completed, wait, FIRST_COMPLETED

# ======================================================================
# 语法解析 1：被池管理的任务函数
# ======================================================================


def io_task(task_id: int) -> str:
    """模拟一个 IO 密集任务：主要时间在「等待」而非计算。

    语法解析：f-string 的 {task_id:03d} 是格式说明符，03d = 宽度 3 的十进制、左侧补 0。
    """
    delay = random.uniform(0.1, 0.4)
    time.sleep(delay)          # 关键：sleep 会释放 GIL，其他线程可并发推进
    return f"任务{task_id:03d}完成，用时{delay:.2f}s"


def flaky_task(task_id: int) -> str:
    """模拟一个会失败的任务。"""
    if task_id == 3:
        # 故意抛出业务异常，演示异常隔离
        raise RuntimeError(f"任务{task_id}炸了：下游服务返回 502")
    time.sleep(0.1)
    return f"任务{task_id}成功"


# ======================================================================
# 语法解析 2：submit + Future
# ======================================================================


def demo_submit() -> None:
    print("=" * 60)
    print("【1】submit() 提交单个任务")
    print("=" * 60)

    # with 语句：退出代码块时自动调用 executor.shutdown(wait=True)
    with ThreadPoolExecutor(max_workers=4, thread_name_prefix="Pool1") as pool:
        # submit 返回一个 Future 对象（此时任务还没开始跑）
        f1 = pool.submit(io_task, 1)
        f2 = pool.submit(io_task, 2)

        print(f"提交后立刻检查 done()：f1.done()={f1.done()}（大概率 False）")
        # result() 会「阻塞」直到任务完成并返回其返回值
        r1 = f1.result()
        print(f"f1.result() -> {r1}")
        print(f"现在 f1.done()={f1.done()}")
        # done() 为 True 后可用 exception() 取异常，没有异常返回 None
        print(f"f1.exception() -> {f1.exception()}")

        # add_done_callback：任务完成时自动回调（回调可能运行在工作线程里）
        f2.add_done_callback(lambda fut: print(f"回调收到结果：{fut.result()}"))
        print(f"f2.result() -> {f2.result()}")

        # cancel() 只能取消「还没开始」的任务，已在队列里的通常取消失败
        f3 = pool.submit(io_task, 99)
        cancelled = f3.cancel()
        print(f"能否取消排队中的任务？{cancelled}，cancelled()={f3.cancelled()}")
        if not cancelled:
            print(f"  那就正常取结果：{f3.result()}")


# ======================================================================
# 语法解析 3：map 批量映射
# ======================================================================


def demo_map() -> None:
    print()
    print("=" * 60)
    print("【2】map() 批量映射")
    print("=" * 60)

    tasks = list(range(1, 6))

    start = time.perf_counter()
    with ThreadPoolExecutor(max_workers=5) as pool:
        # map 返回一个【惰性迭代器】，必须真正迭代（或 list()）才会等所有任务完成
        # 注意：只要有一个任务抛异常，迭代到该位置就会抛出
        lazy = pool.map(io_task, tasks)
        print(f"map() 返回对象的类型：{type(lazy).__name__}（惰性，未执行）")
        results = list(lazy)                 # 这里才真正等待所有结果
    elapsed = time.perf_counter() - start

    for r in results:
        print(f"  {r}")
    print(f"串行总耗时≈{sum(0.25 for _ in tasks):.2f}s，"
          f"线程池实际耗时={elapsed:.2f}s")

    # map 的特性：结果顺序 == 提交顺序（不依赖实际完成顺序）


# ======================================================================
# 语法解析 4：as_completed 按完成顺序
# ======================================================================


def demo_as_completed() -> None:
    print()
    print("=" * 60)
    print("【3】as_completed() 按完成顺序迭代")
    print("=" * 60)

    # 让第一个任务最慢，以便看到「完成顺序」与「提交顺序」不同
    def ordered_task(i: int) -> str:
        time.sleep((6 - i) * 0.08)
        return f"任务{i}"

    with ThreadPoolExecutor(max_workers=6) as pool:
        futs = {pool.submit(ordered_task, i): i for i in range(1, 6)}
        # 语法解析：字典推导式 {k: v for ...}；key 是 Future 对象，value 是任务号
        print("提交顺序：1 2 3 4 5")

        for fut in as_completed(futs):
            # as_completed 每次产出一个「刚完成」的 Future
            task_id = futs[fut]
            print(f"  完成顺序 -> 任务{task_id}：{fut.result()}")


# ======================================================================
# 语法解析 5：异常处理
# ======================================================================


def demo_exception() -> None:
    print()
    print("=" * 60)
    print("【4】批量任务的异常隔离")
    print("=" * 60)

    # 方案 A：worker 内部自己 try/except，向上返回「降级结果」（推荐）
    def safe_task(task_id: int) -> tuple[bool, str]:
        try:
            return True, flaky_task(task_id)
        except RuntimeError as e:
            # 就地降级：把异常转成「失败标记」，不让它穿出线程
            return False, f"降级：{e}"

    with ThreadPoolExecutor(max_workers=5) as pool:
        print("方案A —— worker 内部捕获，返回降级值：")
        for ok, msg in pool.map(safe_task, range(1, 6)):
            print(f"  [{'OK' if ok else 'FAIL'}] {msg}")

        # 方案 B：让异常自然抛出，用 exception() 逐个检查
        # 关键：不能直接 list(pool.map(...))，否则会中断整个迭代
        print("方案B —— 异常穿出，用 Future.exception() 检查：")
        futs = {pool.submit(flaky_task, i): i for i in range(1, 6)}
        for fut in as_completed(futs):
            task_id = futs[fut]
            exc = fut.exception()      # 不阻塞地取异常（任务已完成）
            if exc is not None:
                print(f"  [任务{task_id} 失败] {type(exc).__name__}: {exc}")
            else:
                print(f"  [任务{task_id} 成功] {fut.result()}")

    print("要点：单个任务失败绝不能拖垮整个批量任务。")


# ======================================================================
# 语法解析 6：超时控制
# ======================================================================


def demo_timeout() -> None:
    print()
    print("=" * 60)
    print("【5】超时控制")
    print("=" * 60)

    with ThreadPoolExecutor(max_workers=3) as pool:
        # 提交一个 2 秒的任务，立刻用 0.5 秒超时去取
        fut = pool.submit(time.sleep, 2)
        try:
            fut.result(timeout=0.5)
        except futures.TimeoutError:
            # result 超时【不会】取消任务，它还在后台跑
            print(f"result(timeout=0.5) 抛出 TimeoutError；"
                  f"任务实际仍在跑：done()={fut.done()}")

        # submit 支持 timeout 参数：超时后任务根本不会进队列执行
        fut2 = pool.submit(time.sleep, 2)
        if fut2.cancel():
            print("cancel() 成功：还没开始的任务被丢弃，不会浪费资源")

        # wait()：等待一组 Future，带总超时
        futs = [pool.submit(time.sleep, t) for t in (0.1, 0.3, 0.5)]
        start = time.perf_counter()
        done, not_done = wait(futs, timeout=0.35, return_when=FIRST_COMPLETED)
        # FIRST_COMPLETED：只要有一个完成就返回；ALL_COMPLETED 要全完成
        print(f"wait(timeout=0.35, FIRST_COMPLETED) 耗时 "
              f"{time.perf_counter() - start:.2f}s："
              f"完成 {len(done)} 个，未完成 {len(not_done)} 个")
        pool.shutdown(wait=True)


# ======================================================================
# 语法解析 7：initializer 初始化钩子
# ======================================================================

# 每个工作线程的初始化结果放进 threading.local()，
# 这样每个线程只能看到自己 initializer 里写的那份，互不干扰
_thread_local_conn = threading.local()


def init_conn(pool_size: int) -> None:
    """initializer：为每个工作线程做一次性初始化。"""
    # 故意 sleep，让 3 个工作线程有机会被【分别】创建，
    # 从而直观看到 initializer 被调用了 3 次（每线程一次），而不是 3 次调用共享一份
    time.sleep(0.05)
    _thread_local_conn.pool_size = pool_size
    _thread_local_conn.tid = threading.current_thread().name


def use_conn(n: int) -> str:
    time.sleep(0.08)
    return f"{_thread_local_conn.tid} 处理 {n}（池容量{_thread_local_conn.pool_size}）"


def demo_initializer() -> None:
    print()
    print("=" * 60)
    print("【6】initializer 初始化钩子")
    print("=" * 60)

    with ThreadPoolExecutor(max_workers=3, initializer=init_conn,
                             initargs=(8,)) as pool:
        for r in pool.map(use_conn, range(4)):
            print(f"  {r}")
    print("initializer 的价值：把「建连接池 / 加载模型」等昂贵一次性操作"
          "放到每个工作线程自己的上下文里。")


# ======================================================================
# 语法解析 8：并发生效的直观对比
# ======================================================================


def demo_speedup() -> None:
    print()
    print("=" * 60)
    print("【7】串行 vs 线程池 耗时对比")
    print("=" * 60)

    n = 10
    # 串行
    start = time.perf_counter()
    for i in range(n):
        time.sleep(0.1)
    serial = time.perf_counter() - start

    # 线程池
    start = time.perf_counter()
    with ThreadPoolExecutor(max_workers=10) as pool:
        list(pool.map(time.sleep, [0.1] * n))
    parallel = time.perf_counter() - start

    print(f"{n} 个各 0.1s 的等待型任务：")
    print(f"  串行：{serial:.3f}s")
    print(f"  线程池：{parallel:.3f}s")
    print(f"  加速比：{serial / parallel:.1f}x")
    print("原理：time.sleep 期间 GIL 被释放，工作线程可以真正并行等待。")


def main() -> None:
    random.seed(42)          # 固定随机种子，让每次运行结果可复现
    demo_submit()
    demo_map()
    demo_as_completed()
    demo_exception()
    demo_timeout()
    demo_initializer()
    demo_speedup()
    print()
    print("=" * 60)
    print("02_thread_pool 演示完毕")
    print("=" * 60)


if __name__ == "__main__":
    main()