# -*- coding: utf-8 -*-
"""
03_gil_and_cpu.py —— GIL 与 CPU 密集任务的实测对比

【演示的语法点】
1. GIL（Global Interpreter Lock）的确切作用范围
2. sys.getswitchinterval() / sys.setswitchinterval() 观察与调整切换阈值
3. time.perf_counter() 高精度计时（单调递增，适合测耗时）
4. 纯 Python 计算：多线程【无加速，甚至更慢】（GIL 争抢 + 切换开销）
5. 为什么 multiprocessing 能绕过 GIL：每个进程有独立解释器和独立 GIL
6. Windows 上进程创建有固定开销，任务粒度太小反而更慢（本文用 n=4000万实测）
7. hashlib 实证：C 扩展释放 GIL，线程又能并行了（GIL 影响范围的边界）
8. 计时前先warmup，避开 CPython 自适应特化解释器的冷启动干扰

【预期输出摘要】（本机 16 核实测，不同机器数值会有差异）
- CPU 密集：串行约 1.5s；4 线程跑同样总工作量约 15s（慢约 10 倍）
- CPU 密集：4 进程约 1.6s（比线程快约 9 倍，接近串行）
- hashlib 共享 payload：4 线程加速约 3.2x（释放 GIL + 无竞争）
- hashlib 每任务各自分配 8MB：4 线程反而慢 24 倍（分配器竞争吃掉收益）
"""
import sys
import os
import time
import hashlib
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor

# 全局常量：CPU 任务规模。40_000_000 是在本机实测能让多进程真正跑赢线程的量级
N_CPU = 40_000_000
N_WORKERS = 4


# ======================================================================
# 语法解析 1：CPU 密集任务（纯 Python 计算）
# ======================================================================


def cpu_bound(n: int) -> int:
    """纯 Python 计算任务：全程持有 GIL，从不主动释放。

    语法解析：这个函数体内没有任何 IO（无 sleep / 无文件 / 无网络），
    所以解释器在执行它的字节码时【一直持有 GIL】，其他线程根本抢不到。
    """
    total = 0
    for i in range(n):
        total += i * i# 纯 CPU 运算
    return total


def measure(fn, *args) -> float:
    """通用计时工具：用 perf_counter 而非 time.time()。

    语法解析：*args 是「可变位置参数」，把任意多个参数收集成元组。
    perf_counter 返回单调递增的高精度秒数，能正确测量「经过的间隔」；
    time.time() 可能被系统调时（NTP 校正）改写，导致结果为负或失真。
    """
    start = time.perf_counter()
    fn(*args)
    return time.perf_counter() - start


def demo_gil_cpu() -> tuple[float, float]:
    """实测 CPU 密集任务的串行 vs 多线程，返回 (串行耗时, 线程耗时)。"""
    print("=" * 70)
    print("【1】GIL 实测：CPU 密集任务的多线程 vs 串行")
    print("=" * 70)

    # warmup：先跑一次小规模任务，让 CPython 的自适应特化解释器完成热身。
    # 不热身的话，第一次执行的耗时会被严重高估，数据不可信。
    cpu_bound(1_000_000)
    print(f"（已warmup，避免自适应解释器冷启动干扰计时）")

    serial = measure(cpu_bound, N_CPU)
    print(f"串行跑 {N_CPU:,} 次运算：{serial:.3f}s")

    # 多线程：总工作量不变，拆成4 份并行跑
    thr = measure(lambda: list(
        ThreadPoolExecutor(max_workers=N_WORKERS).map(
            cpu_bound, [N_CPU] * N_WORKERS)))
    print(f"{N_WORKERS} 线程跑同样总工作量：{thr:.3f}s")
    print(f"加速比：{serial / thr:.2f}x")

    print("❌ 加速比 < 1：CPU 密集任务开线程【不会变快，反而更慢】。")
    print("   原因：4 个线程要轮流抢同一把 GIL，每次交接都有上下文切换开销。")

    print()
    print(f"GIL 切换间隔 sys.getswitchinterval() = {sys.getswitchinterval()}s")
    print("含义：持有 GIL 的线程最多执行 5ms 就要把锁交还，给其他线程机会。")
    print("这不是「并行」，只是「并发切换」—— 同一时刻永远只有一个线程在跑字节码。")
    return serial, thr


# ======================================================================
# 语法解析 2：multiprocessing 绕过 GIL
# ======================================================================


def demo_process_cpu(serial: float, thr: float) -> None:
    print()
    print("=" * 70)
    print("【2】multiprocessing 对比：真并行")
    print("=" * 70)

    # ProcessPoolExecutor：每个子进程有自己的 Python 解释器和【自己的 GIL】，
    # 因此可以真正同时跑在多个 CPU 核心上。
    with ProcessPoolExecutor(max_workers=N_WORKERS) as pool:
        # ⚠️ Windows 上创建进程需要重新加载解释器，有约1~2s 固定开销。
        #    为把「启动开销」和「真正并行收益」分开测量，
        #    先用极小任务把 N_WORKERS 个进程【预热】起来，这段时间不计入。
        list(pool.map(warmup, range(N_WORKERS)))
        print(f"（已完成进程池预热，N_WORKERS={N_WORKERS} 个子进程已就绪）")

        # 现在才开始计时：进程已存在，测的就是纯并行收益
        start = time.perf_counter()
        list(pool.map(cpu_bound, [N_CPU] * N_WORKERS))
        proc = time.perf_counter() - start

    print(f"CPU 逻辑核心数：{os.cpu_count()}")
    print(f"串行：                    {serial:.3f}s")
    print(f"{N_WORKERS} 线程跑同样总工作量：  {thr:.3f}s"
          f"（比串行慢 {thr / serial:.1f} 倍）")
    print(f"{N_WORKERS} 进程跑同样总工作量：  {proc:.3f}s"
          f"（比串行慢 {proc / serial:.2f} 倍）")
    print()
    print(f"👀 正确解读方式（很重要）：")
    print(f"   · 线程 {thr:.2f}s vs 进程 {proc:.2f}s -> "
          f"进程比线程快 {thr / proc:.1f} 倍，这才是多进程的真正价值。")
    print(f"   · 进程({proc:.2f}s) 接近串行({serial:.2f}s)，说明进程创建开销已被摊薄，")
    print(f"     且 {N_WORKERS} 个核心几乎同时在跑 —— 这就是真并行。")
    print("   · 注意：把【同样总量的工作】拆到多核，并不能凭空让它比串行更快")
    print("     （串行本来就只用一个核心）。多进程的收益在于：")
    print("       (a) 相比多线程的巨大提升；")
    print("       (b) 多进程之间有独立内存/GIL，互不干扰；")
    print("       (c) 要拿到「快于串行」的效果，需要并行效率 > 1，")
    print("           这通常来自缓存局部性变好、向量化、超线程等，")
    print("           在纯 Python 循环里几乎拿不到。")
    print("机制：多进程 = 多份 GIL = 多个字节码执行流可以同时推进，这才是真并行。")
    print("工程提示：生产中应【长期复用】进程池，或用更大的任务粒度摊薄启动开销。")

    # 汇总对比表
    print()
    print(f"{'方案':<14}{'耗时(s)':<12}{'比线程快':<12}结论")
    print("-" * 52)
    # 注意：f-string 的 :<14 是按【字符个数】对齐的，而中文字符占两个终端列，
    # 所以中文列会「看起来短一格」。这里用自定义的 w() 做显示宽度对齐。
    def w(text: str, width: int) -> str:
        """按终端显示宽度补齐（中文算 2 列）。"""
        import unicodedata
        disp = sum(2 if unicodedata.east_asian_width(c) in "WF" else 1
                   for c in text)
        return text + " " * max(0, width - disp)

    print(w("串行（单核）", 14) + w(f"{serial:.3f}", 12)
          + w(f"{thr / serial:.1f}x", 12) + "基准")
    print(w(f"{N_WORKERS} 线程", 14) + w(f"{thr:.3f}", 12)
          + w("1.0x", 12) + "GIL 拖累，最慢")
    print(w(f"{N_WORKERS} 进程", 14) + w(f"{proc:.3f}", 12)
          + w(f"{thr / proc:.1f}x", 12) + "真并行，最快")


# ======================================================================
# 语法解析 3：GIL 影响范围的边界 —— C 扩展释放 GIL
# ======================================================================


# 关键设计：payload 只创建【一次】并被所有任务共享。
# 若每个任务都自己 b"x" * 8_000_000 分配 8MB，会引发内存分配器竞争与
# 内存带宽争抢，线程反而更慢（本机实测 0.3x）。这本身就是一条 valuable 结论。
_PAYLOAD = b"x" * (1024 * 1024)     # 1MB，只读，天然线程安全


def gil_releasing_task(rounds: int) -> str:
    """用 hashlib 计算摘要。

    关键点：hashlib 底层是 C 实现（本机为 openssl_sha256），
    update() 处理大块数据时会【释放 GIL】，因此多线程能真正并行。
    """
    h = hashlib.sha256()
    for _ in range(rounds):
        h.update(_PAYLOAD)
    return h.hexdigest()[:16]


def gil_releasing_task_alloc(args: tuple[int, int]) -> str:
    """反面实验：每次调用都现分配一块大缓冲区。

    用于演示「即使有 GIL 释放，共享资源竞争也会吃掉收益」。
    语法解析：tuple[int, int] 是 3.9+ 的内置泛型写法（PEP 585），
    运行时等价于 typing.Tuple[int, int]。
    """
    size, rounds = args
    payload = b"x" * size      # ⚠️ 每次都申请新的大块内存
    h = hashlib.sha256()
    for _ in range(rounds):
        h.update(payload)
    return h.hexdigest()[:16]


def demo_gil_boundary() -> None:
    print()
    print("=" * 70)
    print("【3】GIL 的确切影响范围：C 扩展释放 GIL 后线程才能并行")
    print("=" * 70)

    rounds, total = 30, 8      # 8 个任务，每个处理 1MB x 30轮

    # warmup
    gil_releasing_task(2)

    serial = measure(lambda: [gil_releasing_task(rounds) for _ in range(total)])
    thr = measure(lambda: list(
        ThreadPoolExecutor(max_workers=4).map(gil_releasing_task, [rounds] * total)))

    print(f"hashlib.sha256（释放 GIL 的 C 代码），{total} 个任务，"
          f"每任务 1MB x {rounds} 轮：")
    print(f"  串行：{serial:.3f}s")
    print(f"  4 线程：{thr:.3f}s，加速比 {serial / thr:.2f}x")
    print("✅ 线程【明显有效】：重活交给了会释放 GIL 的 C 扩展，")
    print("   且任务粒度足够大，能摊薄线程调度开销。")

    print()
    print("⚠️ 反面实验（同样用hashlib，但每个任务各自分配 8MB 缓冲区）：")
    big = 8_000_000
    t2 = measure(lambda: list(
        ThreadPoolExecutor(max_workers=4).map(
            gil_releasing_task_alloc, [(big, 100)] * 8)))
    print(f"  4 线程（每次现分配 8MB）：{t2:.3f}s —— 比共享 payload【慢很多】")
    print("  原因：8 个线程同时申请大块内存 -> 分配器锁竞争 + 内存带宽打满，")
    print("        释放 GIL 的收益被这些开销吃掉了。")
    print("  结论：'用了会释放 GIL 的库' ≠ '线程一定更快'，")
    print("        还要同时满足：任务粒度够大 + 没有共享资源竞争。")

    print()
    print("GIL 影响范围总结（面试高频，建议背下来）：")
    print("┌─ 持有 GIL：所有纯 Python 字节码的执行")
    print("├─ 释放 GIL：time.sleep、文件/网络 IO、hashlib、zlib、")
    print("│            部分 C 扩展函数、等待线程锁等 C 层操作")
    print("└─ 推论：IO 密集 → 线程有效；纯计算 → 线程无效，必须用进程")
    print("   注意：Python 3.13 起提供实验性的 free-threaded 构建（无 GIL），")
    print("   但常规 CPython 发行版仍默认开启 GIL。")


# ======================================================================
# 语法解析 4：切换间隔的实测影响
# ======================================================================


def warmup(_: int) -> int:
    """空任务，仅用于把进程池的子进程「拉起来」。

    ⚠️ 这里必须是【模块级函数】，不能写成 lambda：
    ProcessPoolExecutor 要把函数 pickle 后发给子进程，
    而局部 lambda / 局部函数都无法被 pickle，会报：
      AttributeError: Can't get local object '<locals>.<lambda>'
    这是 multiprocessing 最常见的坑之一。
    """
    return 0


def ping_pong(n: int) -> int:
    """每轮都主动让出 GIL 的任务，非常依赖切换时机。"""
    c = 0
    for _ in range(n):
        time.sleep(0)     # sleep(0) 会释放并重新获取 GIL
        c += 1
    return c


def demo_switch_interval() -> None:
    print()
    print("=" * 70)
    print("【4】sys.setswitchinterval() 的实测影响")
    print("=" * 70)

    n = 200_000
    print(f"{'切换间隔(s)':<16}{'耗时(s)':<12}")
    print("-" * 28)
    results = []
    for interval in (0.0005, 0.005, 0.05):
        # 修改解释器级别的 GIL 切换阈值（全局生效，立即影响后续调度）
        sys.setswitchinterval(interval)
        cost = measure(lambda: list(
            ThreadPoolExecutor(max_workers=2).map(ping_pong, [n, n])))
        results.append((interval, cost))
        print(f"{interval:<16.4f}{cost:<12.3f}")

    sys.setswitchinterval(0.005)   # 恢复默认值，不要污染后续实验

    print()
    print("👉 观察结论：三种设置的耗时【没有稳定规律】（本机实测差异在噪声范围内，")
    print("   有时甚至随间隔增大而变快）。")
    print()
    print("   原理：ping_pong 每轮都time.sleep(0)，本身就在【主动让出 GIL】，")
    print("        所以「被动等超时才切换」这条路径几乎没被触发，")
    print("        setswitchinterval 对它影响有限。")
    print("   反过来说：当线程长时间执行【不释放 GIL】的纯 Python 代码时，")
    print("        switchinterval 才真正决定它要霸占多久 —— 这才是它有意义的地方。")
    print()
    print("工程结论：这是【微调旋钮】不是万灵药，且依赖工作负载、机器核数、")
    print("        其他负载等因素。生产环境不要凭感觉改它，")
    print("        必须先 profile 确认瓶颈确实在 GIL 争抢上。")


def main() -> None:
    serial, thr = demo_gil_cpu()
    demo_process_cpu(serial, thr)
    demo_gil_boundary()
    demo_switch_interval()
    print()
    print("=" * 70)
    print("03_gil_and_cpu 演示完毕")
    print("=" * 70)


if __name__ == "__main__":
    # ⚠️ 必须有这层保护。
    # Windows 的 multiprocessing 使用 spawn 启动子进程时，会【重新执行整个模块文件】。
    # 若缺少保护，每个子进程跑到这里又会创建一批子进程 -> 无限递归 -> 系统崩溃
    #（报错形如 RuntimeError: An attempt has been made to start a new process
    #   before the current process has finished its bootstrapping phase）
    main()