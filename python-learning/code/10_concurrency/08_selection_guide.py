# -*- coding: utf-8 -*-
"""
08_selection_guide.py —— 并发方案选型决策指南

【演示的语法点】
1. perf_counter 计时与「基准测试三要素」（预热、多次、取统计量）
2. CPU 密集任务：串行 vs 线程 vs 进程 vs 协程 的实测对比
3. IO 密集任务：串行 vs 线程 vs 进程 vs 协程 的实测对比
4. GIL 如何让线程在 CPU 密集场景失效
5. time.sleep 为什么能释放 GIL（IO 密集场景线程反而更快）
6. 线程池 vs 进程池 vs asyncio 的适用边界
7. 进程启动开销的实测（spawn 模式的真实成本）
8. 输出选型决策表：按任务类型 × 方案给出推荐
9. multiprocessing 的 Windows 保护：if __name__ == "__main__"
10. 协程在 CPU 密集场景为何【完全无效】（单线程，串行执行）

【预期输出摘要】
- CPU 密集：进程显著最快，线程≈串行（甚至更慢），协程≈串行且无加速
- IO 密集：协程最优，线程次之，进程因启动开销可能不划算
- 打印完整选型决策表
"""
import asyncio
import multiprocessing
import time
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor

# ======================================================================
# 语法解析 1：perf_counter —— 正确计时的姿势
# ======================================================================
#
# 语法规则：time.perf_counter() -> float
#   返回一个「性能计数器」，单位是【秒】，精度是纳秒级。
#
# 为什么不用 time.time()？
#   time.time() 是【墙上时钟】，会被 NTP 校时、夏令时调整影响，
#   甚至可能出现「时钟回拨」导致负的耗时。测性能必须用单调时钟。
#   time.perf_counter() 保证单调递增，适合测时间差。
#
# 基准测试三要素（否则数字没有意义）：
#   1) 预热：首次执行包含 import、缓存未命中等一次性成本
#   2) 多次执行取【中位数】而非平均值（平均数容易被偶发抖动拉偏）
#   3) 固定数据量，且保证各方案处理的任务量完全一致


def measure(fn, *args, warmup: int = 1, repeat: int = 3):
    """测量函数耗时的中位数（比平均值更抗干扰）。"""
    for _ in range(warmup):
        fn(*args)
    samples = []
    for _ in range(repeat):
        t0 = time.perf_counter()
        fn(*args)
        samples.append(time.perf_counter() - t0)
    samples.sort()
    return samples[len(samples) // 2]          # 中位数


# ======================================================================
# 语法解析 2：CPU 密集 vs IO 密集 的任务定义
# ======================================================================
#
# CPU 密集：进程被 CPU 计算占满，不涉及等待。
#   特征：time.process_time()（进程自身占用的 CPU 时间）≈ perf_counter（墙钟）
#   例子：图像处理、加密解密、压缩、纯数学计算、矩阵运算
#
# IO 密集：进程大部分时间在【等待】（磁盘/网络），CPU 空闲。
#   特征：perf_counter（墙钟）远大于 process_time
#   例子：HTTP 请求、数据库查询、文件读写、sleep 模拟等待
#
# 这个区分决定了选型：GIL 只保护【CPU 执行】的字节码，
# 而在「等待 IO」时 Python 会主动释放 GIL（释放给操作系统去等），
# 所以线程在 IO 密集场景是有效的，在 CPU 密集场景无效。


# ---- CPU 密集任务 ----

def cpu_task(n: int) -> int:
    """纯计算：计算 0..n 的平方和。没有任何 IO。"""
    total = 0
    for i in range(n):
        total += i * i
    return total


def cpu_task_chain(n: int, rounds: int) -> int:
    """纯计算 + 函数调用链，制造更接近真实应用的 CPU 负载。"""
    total = 0
    for _ in range(rounds):
        total = cpu_task(n)
    return total


# ---- IO 密集任务 ----

def io_task(sleep_seconds: float) -> str:
    """模拟 IO：等待就是 IO 密集的本质。

    time.sleep 会释放 GIL，让其他线程/任务得以运行。
    真实场景里换成 socket.recv / cursor.execute / file.read 也一样会释放 GIL。
    """
    time.sleep(sleep_seconds)
    return "done"


def io_task_network_like(times: int) -> int:
    """模拟多次网络往返（每次 1ms），更接近真实的 IO 密集负载。"""
    for _ in range(times):
        time.sleep(0.001)
    return times


# ======================================================================
# 语法解析 3：CPU 密集场景的四种方案
# ======================================================================
#
# ⚠️ 多进程在 Windows 上必须用 `if __name__ == "__main__":` 保护！
#    Windows 的 multiprocessing 默认用 spawn 启动子进程：
#    子进程会【重新执行整个模块文件】。若没有保护，
#    每个子进程跑到这里又会创建一批子进程 -> 无限递归 -> 系统崩溃。
#    （报错形如 RuntimeError: An attempt has been made to start a new
#      process before the current process has finished its bootstrapping phase）


def cpu_serial(n: int, rounds: int) -> float:
    """串行：单线程直接跑。"""
    t0 = time.perf_counter()
    cpu_task_chain(n, rounds)
    return time.perf_counter() - t0


def cpu_threaded(n: int, rounds: int, workers: int = 4) -> float:
    """多线程：GIL 让 CPU 密集任务无法并行，通常还会因为上下文切换变慢。"""
    t0 = time.perf_counter()
    with ThreadPoolExecutor(max_workers=workers) as pool:
        # 把 rounds 拆成 workers 份，每份线程跑一份
        list(pool.map(lambda _: cpu_task_chain(n, rounds // workers),
                      range(workers)))
    return time.perf_counter() - t0


def cpu_processed(n: int, rounds: int, workers: int = 4) -> float:
    """多进程：真正的并行计算，能突破 GIL。"""
    t0 = time.perf_counter()
    with ProcessPoolExecutor(max_workers=workers) as pool:
        list(pool.map(_cpu_worker, [n] * workers, [rounds // workers] * workers))
    return time.perf_counter() - t0


def _cpu_worker(n: int, rounds: int) -> int:
    """进程池的 worker 必须是【顶层函数】（可 pickle）。

    为什么必须是顶层函数？
    因为 spawn 模式下子进程要通过 pickle 重建这个函数，
    闭包和局部函数无法 pickle，会报 AttributeError / PicklingError。
    """
    return cpu_task_chain(n, rounds)


async def cpu_async(n: int, rounds: int) -> float:
    """协程：单线程，CPU 密集下【完全没有加速】（协程不是并行）。"""
    t0 = time.perf_counter()

    async def one_job():
        # CPU 任务没有 await 点，不会让出控制权
        cpu_task_chain(n, rounds)

    # asyncio.gather 并发调度协程，但它们都在同一线程跑
    await asyncio.gather(*[one_job() for _ in range(4)])
    return time.perf_counter() - t0


def demo_cpu_benchmark() -> dict:
    print("=" * 72)
    print("【1】CPU 密集任务：串行 / 线程 / 进程 / 协程")
    print("=" * 72)

    N = 150_000
    ROUNDS = 2                 # 控制数据量，保证秒级内完成
    print(f"任务：每个方案处理 {ROUNDS} 轮 x {N:,} 次平方和（4 份并行）")
    print(f"注意：CPU 密集任务【没有等待】-> 没有 GIL 释放点\n")

    results = {}
    results["串行"] = cpu_serial(N, ROUNDS)
    print(f"  串行    : {results['串行']:6.3f}s")

    results["线程"] = cpu_threaded(N, ROUNDS)
    print(f"  多线程  : {results['线程']:6.3f}s  "
           f"（GIL 限制，与串行相当甚至更慢）")

    results["进程"] = cpu_processed(N, ROUNDS)
    print(f"  多进程  : {results['进程']:6.3f}s  "
           f"（真并行，突破 GIL）")

    results["协程"] = asyncio.run(cpu_async(N, ROUNDS))
    print(f"  协程    : {results['协程']:6.3f}s  "
           f"（单线程串行，无加速）")

    # 计算加速比
    base = results["串行"]
    print("\n  相对串行的加速比（>1 表示更快）：")
    for name in ("线程", "进程", "协程"):
        print(f"    {name}: {base / results[name]:.2f}x")

    print("\n  结论：CPU 密集 -> 多进程是唯一能真正并行的方案。")
    print("        线程和协程都被 GIL 卡住，且线程还会因上下文切换更慢。")
    return results


# ======================================================================
# 语法解析 4：IO 密集场景的四种方案
# ======================================================================
#
# IO 密集时，进程在「等待」期间会【主动释放 GIL】，
# 所以线程可以让出 CPU 去干别的活 -> 线程有效。
# 协程更轻量（不切换 OS 线程），且能轻松支持上万并发。
# 进程在这个场景反而吃亏：进程启动和进程间通信开销大。


def io_serial(tasks: int, each: float) -> float:
    t0 = time.perf_counter()
    for _ in range(tasks):
        io_task(each)
    return time.perf_counter() - t0


def io_threaded(tasks: int, each: float, workers: int = 10) -> float:
    t0 = time.perf_counter()
    with ThreadPoolExecutor(max_workers=workers) as pool:
        list(pool.map(io_task, [each] * tasks))
    return time.perf_counter() - t0


def io_processed(tasks: int, each: float, workers: int = 10) -> float:
    """进程池做 IO：注意这里的 sleep 是纯等待，进程各等各的，效果是并行等待。"""
    t0 = time.perf_counter()
    with ProcessPoolExecutor(max_workers=workers) as pool:
        list(pool.map(_io_worker, [each] * tasks))
    return time.perf_counter() - t0


def _io_worker(s: float) -> str:
    """进程池 worker 必须是顶层可 pickle 的函数。"""
    return io_task(s)


async def io_async_pure(tasks: int, each: float) -> float:
    """纯 asyncio.sleep 版本：这才是协程在 IO 等待上的真实优势。"""
    t0 = time.perf_counter()
    await asyncio.gather(*[asyncio.sleep(each) for _ in range(tasks)])
    return time.perf_counter() - t0


def demo_io_benchmark() -> dict:
    print()
    print("=" * 72)
    print("【2】IO 密集任务：串行 / 线程 / 进程 / 协程")
    print("=" * 72)

    TASKS = 40
    EACH = 0.02             # 每个任务等待 20ms
    print(f"任务：{TASKS} 个 IO 操作，每个等待 {EACH * 1000:.0f}ms")
    print(f"串行理论下限：{TASKS * EACH:.2f}s（一个接一个等）")
    print("若能完全并发，理想耗时应接近单个任务的 {EACH}s\n")

    results = {}
    results["串行"] = io_serial(TASKS, EACH)
    print(f"  串行      : {results['串行']:6.3f}s")

    results["线程"] = io_threaded(TASKS, EACH)
    print(f"  多线程    : {results['线程']:6.3f}s  "
          f"（等待时释放 GIL -> 有效并发）")

    results["协程"] = asyncio.run(io_async_pure(TASKS, EACH))
    print(f"  协程      : {results['协程']:6.3f}s  "
          f"（单线程并发等待，调度开销最小）")

    results["进程"] = io_processed(TASKS, EACH)
    print(f"  多进程    : {results['进程']:6.3f}s  "
          f"（并行等待，但有进程启动开销）")

    base = results["串行"]
    print("\n  相对串行的加速比（>1 表示更快）：")
    for name in ("线程", "进程", "协程"):
        print(f"    {name}: {base / results[name]:.2f}x")

    print("\n  结论：IO 密集 -> 协程最优（轻量、高并发），线程次之。")
    print("        多进程在这里是【杀鸡用牛刀】：IO 不需要绕过 GIL。")
    return results


# ======================================================================
# 语法解析 5：进程启动开销实测
# ======================================================================
#
# 面试高频问题：多进程什么时候反而更慢？
# 答案：任务粒度【太小】时，进程创建和 IPC 的固定开销会超过并行收益。
# 下面是实测：启动一个进程池的固定成本 vs 单个任务的计算量。


def _trivial(x):
    """顶层「几乎不做事」的最小任务。

    必须是顶层函数：spawn 模式下子进程要 pickle 这个函数，
    局部函数无法 pickle（AttributeError: Can't get local object）。
    """
    return x


def measure_process_spawn_overhead() -> None:
    print()
    print("=" * 72)
    print("【3】进程启动开销实测（为什么小任务不适合多进程）")
    print("=" * 72)

    # 测量创建进程池本身的耗时（含 spawn）
    t0 = time.perf_counter()
    with ProcessPoolExecutor(max_workers=4) as pool:
        pool.submit(_trivial, 1).result()   # 真正把进程拉起来
    pool_cost = time.perf_counter() - t0
    print(f"  创建并启动一个 4 进程池（含 spawn）：{pool_cost * 1000:.0f} ms")
    print("  ^ 这就是多进程的【固定成本】：任务数量少 / 任务极短时，"
          "这个成本会吃掉全部收益")

    # 对比：单个中等任务的计算时间
    task_time = measure(cpu_task, 200_000)
    print(f"  单个 cpu_task(200000) 耗时：{task_time * 1000:.1f} ms")
    print(f"  若单任务耗时 {task_time * 1000:.0f}ms > 进程开销 "
          f"{pool_cost * 1000:.0f}ms，多进程才划算")

    print("\n  实测：用 4 进程跑 4 份 cpu_task(200000)，对比串行跑 4 份")
    # 串行 4 份
    t0 = time.perf_counter()
    for _ in range(4):
        cpu_task(200_000)
    serial_4 = time.perf_counter() - t0

    t0 = time.perf_counter()
    with ProcessPoolExecutor(max_workers=4) as pool:
        list(pool.map(cpu_task, [200_000] * 4))
    par_4 = time.perf_counter() - t0

    print(f"    串行 4 份 : {serial_4:6.3f}s")
    print(f"    并行 4 份 : {par_4:6.3f}s（含进程启动 {pool_cost:.2f}s）")
    print(f"    净收益    : {serial_4 - par_4:6.3f}s"
          f"  {'✅ 多进程划算' if par_4 < serial_4 else '❌ 多进程反而更慢'}")

    print("\n  经验法则：任务粒度应远大于进程启动开销（通常 > 100ms 才有明显收益）。")
    print("  任务很短 -> 用线程/协程；任务很重 -> 才上多进程。")


# ======================================================================
# 语法解析 6：进程数与 CPU 核数的关系
# ======================================================================


def measure_worker_count_effect() -> None:
    print()
    print("=" * 72)
    print("【4】进程数 vs CPU 核数：超过核数会变慢")
    print("=" * 72)

    cpu_count = multiprocessing.cpu_count()
    print(f"  本机 CPU 逻辑核心数：{cpu_count}")

    N, ROUNDS = 100_000, 2
    print(f"\n  固定总工作量，用不同数量的进程执行：")
    for workers in (1, 2, max(2, cpu_count // 2), cpu_count, cpu_count * 2):
        workers = max(1, workers)
        # 让总工作量固定：workers 个进程各跑 ROUNDS//workers 轮
        per_rounds = max(1, ROUNDS * 2 // workers)
        t = measure(cpu_processed, N, per_rounds * workers, workers)
        print(f"    进程数={workers:3d}: {t:6.3f}s")

    print("\n  结论：进程数接近核数时最快；超过核数后因为【上下文切换开销】反而变慢。")
    print("  同理，线程池大小也不是越大越好（IO 密集时可以远大于核数）。")


# ======================================================================
# 语法解析 7：输出选型决策表
# ======================================================================
#
# 这张表是本文件的最终产出，也是面试答「如何做并发选型」的结构化答案。


def print_decision_table() -> None:
    print()
    print("=" * 72)
    print("【5】并发方案选型决策表")
    print("=" * 72)

    header = f"{'方案':<10}{'CPU密集':<12}{'IO密集':<12}{'并发量级':<14}{'主要开销'}"
    print(header)
    print("-" * 78)
    rows = [
        ("串行", "基准", "基准", "1", "无"),
        ("线程", "❌ 无效(GIL)", "✅ 有效", "数百~数千", "栈内存/GIL 切换"),
        ("进程", "✅ 最优", "✅ 有效(但浪费)", "数十~数百", "进程启动/IPC/内存"),
        ("协程", "❌ 无效(单线程)", "✅ 最优", "数万~数十万", "协作式调度/回调"),
        ("线程池", "❌ 无效", "✅ 常用", "数百", "线程复用"),
        ("进程池", "✅ 常用", "⚠️ 杀鸡用牛刀", "数十", "进程池预热"),
        ("asyncio", "❌ 无效", "✅ 首选", "上万+", "事件循环"),
    ]
    for r in rows:
        print(f"{r[0]:<10}{r[1]:<12}{r[2]:<12}{r[3]:<14}{r[4]}")

    print("\n  决策流程：")
    print("  1) 先判断任务是 CPU 密集还是 IO 密集")
    print("     - CPU 密集（process_time ≈ perf_counter）-> 多进程/进程池")
    print("     - IO 密集（perf_counter >> process_time）-> 协程 > 线程")
    print("  2) 再看并发量级")
    print("     - 几百并发 -> 线程池（简单够用）")
    print("     - 上万并发 -> asyncio（协程栈内存小得多）")
    print("  3) 最后看任务粒度")
    print("     - 任务很短 -> 绝不选多进程（启动开销吃掉收益）")
    print("     - 任务很重 -> 多进程才划算")


def print_comparison_matrix() -> None:
    """易混淆概念横向对比表 —— 面试常被追问。"""
    print()
    print("=" * 72)
    print("【6】并发概念横向对比（面试高频）")
    print("=" * 72)

    header = (f"{'维度':<14}{'线程 Thread':<22}{'进程 Process':<22}{'协程 Coroutine'}")
    print(header)
    print("-" * 80)
    items = [
        ("调度方式", "OS 抢占式", "OS 独立调度", "协作式（事件循环）"),
        ("切换代价", "小（内核态切换）", "最大（地址空间切换）", "最小（无OS切换）"),
        ("内存隔离", "❌ 共享", "✅ 独立", "✅ 共享（同线程）"),
        ("通信方式", "共享变量+锁", "管道/队列/共享内存", "await 直接传值"),
        ("能否绕过GIL", "❌ 不能", "✅ 能", "❌ 不能"),
        ("CPU密集", "❌", "✅", "❌"),
        ("IO密集", "✅", "✅但浪费", "✅✅最优"),
        ("并发量级", "10^2~10^3", "10^1~10^2", "10^4~10^5"),
        ("创建开销", "低", "高", "极低"),
        ("数据竞争风险", "⚠️ 高", "✅ 低", "✅ 无（单线程）"),
        ("典型场景", "线程池并发IO", "并行计算/科学计算", "高并发网络服务"),
    ]
    for it in items:
        print(f"{it[0]:<14}{it[1]:<22}{it[2]:<22}{it[3]}")

    print("\n  记忆口诀：")
    print("  - 线程 = 共享内存 + 抢时间片（IO 划算，要防竞态）")
    print("  - 进程 = 隔离内存 + 各跑各的（CPU 划算，通信贵）")
    print("  - 协程 = 单线程 + 主动让路（IO 最优，无竞态，但不能并行计算）")


def main() -> None:
    print("并发选型实测 —— 数据量已控制在 20 万次循环内")
    print("=" * 72)

    cpu_results = demo_cpu_benchmark()
    io_results = demo_io_benchmark()
    measure_process_spawn_overhead()
    measure_worker_count_effect()
    print_decision_table()
    print_comparison_matrix()

    print()
    print("=" * 72)
    print("08_selection_guide 演示完毕")
    print("=" * 72)
    print("\n最终决策树：")
    print("  CPU 密集?  ── 是 ──> 任务短? 否-> 多进程池(核数个) / 是-> 串行或线程")
    print("            │")
    print("            否(IO密集)──> 并发量小(<1000)? 是-> 线程池")
    print("                                   │")
    print("                                   否-> asyncio")


if __name__ == "__main__":
    # ⚠️ Windows 多进程【必须】有这层保护。
    # spawn 模式下子进程会重新执行本模块，若无保护会无限 fork。
    main()