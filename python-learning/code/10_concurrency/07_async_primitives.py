# -*- coding: utf-8 -*-
"""
07_async_primitives.py —— 异步编程的同步原语

【演示的语法点】
1. asyncio.Lock：异步锁。acquire/release 可 await；支持 async with
2. asyncio.Event：事件标志，用于「一个协程通知其他协程」
3. asyncio.Condition：条件变量，wait() 必须配合 notify + 循环检查
4. asyncio.Semaphore：信号量，限制并发数
5. asyncio.Queue：异步队列（注意区别于 queue.Queue 与 multiprocessing.Queue）
6. asyncio.BoundedSemaphore：带上界的信号量，用于检测超发
7. wait_for / timeout / gather(return_exceptions=True) / as_completed
8. Task.cancel() 与 shield()：取消与「不被取消」
9. 取消风暴：gather 中一个失败导致其余全被取消
10. 生产者-消费者模式（async Queue）的完整实现

【预期输出摘要】
- 8 个协程并发自增，Lock 保护后结果严格等于 8 x 1000
- Event 演示「等待初始化完成再放行」
- Condition 演示「队列非空才 notify」的正确写法
- Semaphore 把并发限制为 3，观测到最多同时 3 个在跑
- Queue 演示生产者-消费者，并展示 queue.join() 的用法
"""
import asyncio
import time
import random


# ======================================================================
# 语法解析 1：asyncio.Lock
# ======================================================================


shared_counter = 0


async def unsafe_increase(n: int) -> None:
    """无锁并发自增：会丢更新。

    原理与线程里的竞态完全一样 —— 协程在 await 处被切换，
    「读-改-写」三步之间可能被打断。
    """
    global shared_counter
    for _ in range(n):
        temp = shared_counter
        # 关键：这里放一个 await 强制发生切换，让竞态稳定复现。
        # 协程是单线程，但依然可能有竞态！
        await asyncio.sleep(0)
        shared_counter = temp + 1


async def safe_increase(n: int, lock: asyncio.Lock) -> None:
    """有锁并发自增：结果精确。"""
    global shared_counter
    for _ in range(n):
        async with lock:            # 异步版的 with：acquire/release 都是 await
            shared_counter += 1


async def demo_lock() -> None:
    print("=" * 70)
    print("【1】asyncio.Lock —— 协程也需要锁")
    print("=" * 70)

    # 【重要概念】协程是单线程，为什么还会有竞态？
    # 因为协程在 await 处会「主动让出控制权」，
    # 如果两个协程都在读-改-写同一个共享变量，
    # 它们可能在中间被切换，从而丢失更新。
    # 也就是说：单线程 ≠ 无竞态，只要发生上下文切换就可能中断原子性。

    global shared_counter
    tasks_n = 8
    each = 1000

    shared_counter = 0
    await asyncio.gather(*(unsafe_increase(each) for _ in range(tasks_n)))
    print(f"无锁：期望 {tasks_n * each}，实际 {shared_counter}"
          f"（丢了 {tasks_n * each - shared_counter} 次更新）")

    shared_counter = 0
    lock = asyncio.Lock()
    await asyncio.gather(
        *(safe_increase(each, lock) for _ in range(tasks_n)))
    print(f"有锁：期望 {tasks_n * each}，实际 {shared_counter} ✅")

    print()
    print("asyncio.Lock 与 threading.Lock 的区别：")
    print(" · asyncio.Lock.acquire() 是【协程】（await 它会挂起当前协程），")
    print("   不是阻塞整个线程 —— 所以不会卡死事件循环。")
    print(" · asyncio.Lock【不能跨事件循环使用】，")
    print("   所以不能把它作为模块级全局变量在多次 asyncio.run 之间复用。")
    print(" · 必须在【同一个协程内】创建（通常是 async 函数的局部变量）。")


# ======================================================================
# 语法解析 2：asyncio.Event
# ======================================================================


async def demo_event() -> None:
    print()
    print("=" * 70)
    print("【2】asyncio.Event —— 广播式「状态变更」通知")
    print("=" * 70)

    print("典型场景：需要「等初始化完成后再开始干活」。")
    print("Event 提供两个方法：")
    print("  · set()    —— 设置为 True，唤醒所有等待者")
    print("  · clear()  —— 重置为 False")
    print("  · is_set() —— 查询当前状态")
    print("  · wait()   —— await 等待它变成 True")

    ready = asyncio.Event()

    async def worker(name: str) -> None:
        await ready.wait()                # 在这里挂起，直到 ready 被 set
        print(f"  {name} 开始工作（收到 ready 信号）")

    async def initializer() -> None:
        await asyncio.sleep(0.3)          # 模拟耗时的初始化
        print("  初始化完成，调用 ready.set()")
        ready.set()                       # 唤醒所有等待者

    print("先启动 3 个 worker，它们会卡在 wait()：")
    await asyncio.gather(
        worker("worker-1"), worker("worker-2"), worker("worker-3"),
        initializer(),
    )
    print("可见：3 个 worker 都在 initializer 完成后才继续。")

    # set() 之后不会自动重置，需要手动 clear()
    print()
    print(f"ready.is_set() = {ready.is_set()}（set 后保持 True，需手动 clear）")
    ready.clear()
    print(f"clear() 后 ready.is_set() = {ready.is_set()}")

    # Event.wait() 也支持超时
    print()
    try:
        await asyncio.wait_for(ready.wait(), timeout=0.2)
    except asyncio.TimeoutError:
        print("Event 配合 wait_for：0.2s 内没等到 set，抛 TimeoutError ✅")


# ======================================================================
# 语法解析 3：asyncio.Condition
# ======================================================================


async def demo_condition() -> None:
    print()
    print("=" * 70)
    print("【3】asyncio.Condition —— 「条件满足才继续」")
    print("=" * 70)

    print("Condition = Lock + 等待队列，比 Event 更灵活。")
    print("关键点：wait() 必须写在【循环里】！")
    print("      因为可能被「虚假唤醒」（spurious wakeup），")
    print("      或者被其他协程抢先满足条件。")

    queue = []
    condition = asyncio.Condition()

    async def consumer(name: str) -> None:
        for _ in range(3):
            async with condition:
                # ✅ 正确写法：循环 + 检查条件
                while not queue:
                    print(f"    {name}: 队列空，进入等待...")
                    await condition.wait()   # 释放锁并挂起
                item = queue.pop(0)
            print(f"    {name}: 取到 {item}")

    async def producer() -> None:
        for i in range(1, 7):
            await asyncio.sleep(0.05)
            async with condition:
                queue.append(f"item-{i}")
                print(f"    生产者: 放入 item-{i}，唤醒等待者")
                condition.notify()   # 唤醒 1 个等待者（notify_all 唤醒全部）

    await asyncio.gather(producer(), consumer("C1"), consumer("C2"))

    print()
    print("要点：")
    print(" · await condition.wait() 会【释放锁并挂起】，")
    print("   被notify 唤醒后【重新获取锁】再继续 —— 所以前后的锁操作是原子的。")
    print(" · notify() 唤醒一个；notify_all() 唤醒全部。")
    print(" · 忘记写 while 而写成 if 是经典 bug，会丢失唤醒。")
    print(" · 因为 wait() 会释放锁，所以必须在 async with condition 里调用。")


# ======================================================================
# 语法解析 4：asyncio.Semaphore
# ======================================================================

running_now = 0
max_observed = 0


async def limited_task(i: int, sem: asyncio.Semaphore) -> None:
    """受信号量限制的并发任务。"""
    global running_now, max_observed
    async with sem:                     # 获取许可（拿不到就挂起）
        running_now += 1
        max_observed = max(max_observed, running_now)
        print(f"    任务{i} 开始（当前并发 {running_now}）")
        await asyncio.sleep(0.1)        # 模拟 IO 等待
        running_now -= 1
        # 注意：这里已经减过了，所以直接打印 running_now，不能再减 1
        print(f"    任务{i} 结束（当前并发 {running_now}）")


async def demo_semaphore() -> None:
    print()
    print("=" * 70)
    print("【4】asyncio.Semaphore —— 限制并发数")
    print("=" * 70)

    global running_now, max_observed
    running_now = 0
    max_observed = 0

    sem = asyncio.Semaphore(3)      # 最多 3 个同时执行
    print("创建 Semaphore(3)，提交 8 个任务：")
    await asyncio.gather(*(limited_task(i, sem) for i in range(1, 9)))
    print(f"观测到的最大并发数 = {max_observed}（恰好等于 3）✅")
    print("Semaphore 是生产环境的标配：")
    print(" · 限流保护下游服务")
    print(" · 控制连接池大小")
    print(" · 控制内存中同时存在的缓冲区数量")

    # BoundedSemaphore：检测「超发」
    print()
    print("BoundedSemaphore：多释放时会抛 ValueError（用于检测 bug）")
    bs = asyncio.BoundedSemaphore(1)
    await bs.acquire()
    bs.release()
    try:
        bs.release()                # 已经没有许可了，多释放一次
    except ValueError as e:
        print(f"  捕获到 {type(e).__name__}: {e} ✅")


# ======================================================================
# 语法解析 5：asyncio.Queue 与生产者-消费者
# ======================================================================


async def producer_worker(q: asyncio.Queue, count: int,
                          sentinels: int = 1) -> None:
    """生产者：往队列里放数据。

    ⚠️ 哨兵的数量必须和消费者数量一致！
       每个消费者只退出一次，如果只放 1 个哨兵给 2 个消费者，
       另一个消费者会永远阻塞在 q.get() 上 —— 整个 gather 死等。
       这是「生产者-消费者」模式最经典的坑之一。
    """
    for i in range(count):
        await q.put(f"消息{i}")
        print(f"  [生产者] 放入 消息{i}（队列长度 {q.qsize()}）")
        await asyncio.sleep(0.05)
    # 放哨兵，告诉消费者「我完了」—— 每个消费者一个
    for _ in range(sentinels):
        await q.put(None)


async def consumer_worker(name: str, q: asyncio.Queue) -> None:
    """消费者：从队列取数据直到收到哨兵。"""
    while True:
        item = await q.get()
        if item is None:            # 收到结束信号
            q.task_done()           # 必须调用，否则 q.join() 会永久挂起
            break
        print(f"  [{name}] 消费 {item}")
        await asyncio.sleep(0.03)  # 模拟处理耗时
        q.task_done()               # 标记「这一项处理完了」


async def demo_queue() -> None:
    print()
    print("=" * 70)
    print("【5】asyncio.Queue —— 生产者-消费者")
    print("=" * 70)

    print("三种 Queue 的区别（面试常考）：")
    print(" · queue.Queue        —— 多线程安全，阻塞式（用 lock+condition）")
    print(" · multiprocessing.Queue —— 多进程安全，内部用管道 + 锁")
    print(" · asyncio.Queue      —— 单线程事件循环内使用，无锁但可 await")

    q: asyncio.Queue = asyncio.Queue(maxsize=3)   # 容量 3，满了 put 会挂起
    print()
    print(f"创建容量为 3 的 asyncio.Queue，1 个生产者 + 2 个消费者：")

    t0 = time.perf_counter()
    await asyncio.gather(
        producer_worker(q, 5, sentinels=2),   # ⚠️ 2 个哨兵对应 2 个消费者
        consumer_worker("消费者A", q),
        consumer_worker("消费者B", q),
    )
    print(f"总耗时 {time.perf_counter() - t0:.2f}s")
    print("⚠️ 坑：哨兵数量必须等于消费者数量，否则会有消费者永久阻塞。")

    # q.join() 的用法：等待所有 task_done
    print()
    print("演示 q.join()：等待队列被处理完")
    q2: asyncio.Queue = asyncio.Queue()
    for i in range(3):
        q2.put_nowait(i)       # 立即放入，不等待（队列无限制时不会阻塞）

    async def drain() -> None:
        while not q2.empty():
            v = q2.get()
            q2.task_done()

    await drain()
    await q2.join()             # 等所有 task_done 都调用完
    print("  q2.join() 已返回，说明所有任务都 task_done() 了 ✅")

    print()
    print("⚠️ 常见坑：get() 之后【必须】调用 task_done()，")
    print("   否则 q.join() 会永远等下去。")


# ======================================================================
# 语法解析 6：取消、超时与异常处理
# ======================================================================


async def sometimes_fail(i: int) -> str:
    await asyncio.sleep(random.uniform(0.02, 0.1))
    if i == 2:
        raise ValueError(f"任务{i} 故意失败")
    return f"任务{i}成功"


async def slow(i: int) -> str:
    try:
        await asyncio.sleep(1.0)
        return f"任务{i}完成"
    except asyncio.CancelledError:
        # 清理逻辑放这里，然后【必须重新抛出】
        print(f"    任务{i} 收到取消信号，正在清理...")
        raise


async def demo_cancel_and_errors() -> None:
    print()
    print("=" * 70)
    print("【6】取消、超时与异常聚合")
    print("=" * 70)

    # --- gather + return_exceptions ---
    print("【gather(return_exceptions=True)】")
    results = await asyncio.gather(
        *(sometimes_fail(i) for i in range(1, 5)),
        return_exceptions=True,
    )
    for i, r in enumerate(results, 1):
        if isinstance(r, Exception):
            print(f"  任务{i}: 异常 {type(r).__name__}: {r}")
        else:
            print(f"  任务{i}: {r}")
    print("  → 全部 4 个都跑完了，异常被当作结果返回。")

    # --- gather 默认：一个失败全取消 ---
    print()
    print("【gather 默认行为】不传 return_exceptions：")
    try:
        await asyncio.gather(sometimes_fail(1), sometimes_fail(2),
                             sometimes_fail(3))
    except ValueError as e:
        print(f"  捕获到 {type(e).__name__}: {e}")
    print("  → 第一个异常立刻抛出，其余 Task 被取消。")

    # --- wait_for 超时 ---
    print()
    print("【wait_for 超时】")
    t0 = time.perf_counter()
    try:
        await asyncio.wait_for(slow(99), timeout=0.2)
    except asyncio.TimeoutError:
        print(f"  {time.perf_counter() - t0:.2f}s 后超时，任务被自动取消")
    print("  → wait_for 超时时会先 cancel 内部任务，再抛 TimeoutError。")

    # --- 手动 cancel + 清理 ---
    print()
    print("【手动 cancel + 清理】")
    task = asyncio.create_task(slow(1))
    await asyncio.sleep(0.1)
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        print(f"  task.cancelled() = {task.cancelled()} ✅")

    # --- shield：保护任务不被外层取消 ---
    print()
    print("【shield】让内部任务不被外层取消打断")
    inner = asyncio.create_task(slow(2))
    protected = asyncio.create_task(asyncio.shield(inner))
    protected.cancel()            # 取消外层
    await asyncio.sleep(0.05)
    print(f"  外层已取消，inner.done() = {inner.done()}（inner 仍在运行）")
    await asyncio.sleep(1.1)
    print(f"  等待完成：inner.done() = {inner.done()}，"
          f"inner 结果 = {inner.result() if inner.done() and not inner.cancelled() else 'N/A'}")
    print("  → shield 适用于「写库 + 通知」这类不能被中断的关键操作。")

    # --- 超时的两种写法对比 ---
    print()
    print("【超时写法对比】")
    print(" · asyncio.wait_for(awaitable, timeout)—— 超时抛 TimeoutError")
    print(" · await asyncio.wait_for(...)              —— 同上，惯用写法")
    print(" · asyncio.timeout() 上下文管理器          —— 3.11+ 新增，更灵活")
    print()
    try:
        async with asyncio.timeout(0.2):
            await slow(3)
    except TimeoutError:
        print("  asyncio.timeout() 同样生效 ✅（注意 TimeoutError 是内置的）")


# ======================================================================
# 语法解析 7：结构化并发的超时上下文
# ======================================================================


async def demo_structured_concurrency() -> None:
    print()
    print("=" * 70)
    print("【7】TaskGroup（3.11+）—— 结构化并发")
    print("=" * 70)

    print("asyncio.TaskGroup 是 3.11 引入的新特性，解决「协程逃逸」问题：")
    print(" · 所有子任务被打包管理，不会漏掉 await")
    print(" · 任何一个子任务抛异常，会自动取消同组的其他任务")
    print(" · 退出 with 块时，保证所有任务都已结束")
    print(" · 多个异常会被聚合成 ExceptionGroup 抛出")

    async def ok_task(i: int) -> str:
        await asyncio.sleep(0.05)
        return f"ok-{i}"

    async def bad_task() -> None:
        await asyncio.sleep(0.05)
        raise RuntimeError("子任务失败了")

    # 全部成功
    print()
    print("① 全部成功的场景：")
    async with asyncio.TaskGroup() as tg:
        for i in range(3):
            tg.create_task(ok_task(i))     # 用 tg.create_task 而不是全局 create_task
    print("   正常退出，没有异常。")

    # 有失败
    print()
    print("② 有一个子任务失败的场景：")
    try:
        async with asyncio.TaskGroup() as tg:
            tg.create_task(ok_task(1))
            tg.create_task(bad_task())
            tg.create_task(ok_task(2))
    except* RuntimeError as eg:
        # except* 是 3.11 的异常组语法，只捕获匹配的异常类型
        print(f"   捕获到 ExceptionGroup: {eg.exceptions}")
    print("   → 同组其他任务会被自动取消并等待结束。")
    print("   → 对比 gather：这里不需要手动 gather，作用域结束即收敛。")


def main() -> None:
    random.seed(2024)
    # 语法解析：这些 demo 都是纯异步函数，统一由一次 asyncio.run 驱动。
    # 这样整个文件只创建一个事件循环，也避免 asyncio.Lock
    # 「不能跨事件循环复用」的坑。
    async def run_all() -> None:
        await demo_lock()
        await demo_event()
        await demo_condition()
        await demo_semaphore()
        await demo_queue()
        await demo_cancel_and_errors()
        await demo_structured_concurrency()

    asyncio.run(run_all())
    print()
    print("=" * 70)
    print("07_async_primitives 演示完毕")
    print("=" * 70)


if __name__ == "__main__":
    main()