# -*- coding: utf-8 -*-
"""
04_multiprocessing.py —— 多进程编程

【演示的语法点】
1. multiprocessing.Process：start / join / is_alive / terminate / pid
2. ProcessPoolExecutor：map / submit / as_completed / initializer
3. spawn vs fork 启动方式的差异（Windows 只支持 spawn，macOS/Linux 默认 fork）
4. Windows 上 `if __name__ == "__main__"` 的必要性（真实演示递归爆炸的报错）
5. pickle 限制：进程间传参必须可序列化；局部函数/lambda 不可用
6. multiprocessing.Queue / Pipe / Value / Array / Manager 做进程间通信（IPC）
7. shared_memory：真正的零拷贝共享内存（标准库 multiprocessing.shared_memory）
8. 进程池的 chunksize 参数（ProcessPoolExecutor 专有）

【预期输出摘要】
- 主进程与子进程各有独立的 pid，互不相同
- 子进程修改全局变量不会影响主进程（进程内存隔离）
- 传lambda 会抛 AttributeError: Can't pickle local object
- Queue 能跨进程收发，Value 能共享数值
- shared_memory 实测：读写 1MB 数据比 Queue 传输快很多
"""
import sys
import os
import time
import array
import pickle
import platform
import multiprocessing as mp
from multiprocessing import shared_memory
from concurrent.futures import ProcessPoolExecutor, as_completed

# ======================================================================
# 语法解析 1：Process 的基本用法与内存隔离
# ======================================================================

# 模块级全局变量：每个进程都有【自己独立的一份】
GLOBAL_COUNTER = 0


def child_process(name: str, delay: float) -> None:
    """子进程要执行的函数。

    ⚠️ 必须定义在模块【顶层】！
       原因：spawn 方式下，子进程会重新 import 这个模块，
             并通过 pickle 拿到函数名去模块里查找这个函数。
             局部函数（定义在别的函数内部）无法被 pickle，也找不到。
    """
    global GLOBAL_COUNTER
    GLOBAL_COUNTER += 100          # 只改子进程自己的副本
    time.sleep(delay)
    print(f"  [{name}] pid={os.getpid()}，"
          f"我的 GLOBAL_COUNTER={GLOBAL_COUNTER}（父进程看不到这个改动）")


def demo_process_basic() -> None:
    print("=" * 70)
    print("【1】Process 基本用法与内存隔离")
    print("=" * 70)

    print(f"主进程 pid = {os.getpid()}")
    print(f"启动方式 = {mp.get_start_method()}（Windows 固定为 spawn）")
    print(f"平台 = {platform.system()} {platform.machine()}")
    print("进程与线程的根本区别：进程有【独立内存空间】，线程共享同一份。")

    # Process 的参数与 Thread 类似：target / args / name / daemon
    p = Process_class(target=child_process, args=("子进程A", 0.1))
    p.start()                    # 启动
    print(f"  子进程A 已启动，p.pid = {p.pid}（≠ 主进程 pid，说明确实是新进程）")
    p.join()                # 等待结束
    print(f"  子进程A 结束，exitcode = {p.exitcode}（0 表示正常退出）")

    # 同时跑三个。每个任务本身只睡 0.3s，但 Windows 上 spawn 每个进程
    # 都要重新启动一个 Python 解释器（约 0.3s），所以这里总耗时 ≈ 1s。
    # ⚠️ 这正是多进程在 Windows 上的【固定成本】：任务粒度不够大时，
    #    多进程会「启动比干活还久」。生产上必须复用进程池来摊薄它。
    t0 = time.perf_counter()
    ps = [Process_class(target=child_process, args=(f"P{i}", 0.3))
          for i in range(3)]
    for p in ps:
        p.start()
    for p in ps:
        p.join()
    elapsed = time.perf_counter() - t0
    print(f"  3 个各睡 0.3s 的子进程，总耗时 {elapsed:.2f}s")
    print(f"  说明：不是3x0.3=0.9s 的串行，也没快到 0.3s —— "
          f"因为 Windows 上每个子进程都要重新加载解释器（spawn 固定开销）。")
    print(f"  注意这 3 个进程的 pid 各不相同：{[p.pid for p in ps]}")

    print(f"主进程自己的 GLOBAL_COUNTER 仍是 {GLOBAL_COUNTER}，"
          f"子进程的 +100 没有传回来。")

    # Process 的其他控制方法
    q = Process_class(target=time.sleep, args=(10,))
    q.daemon = True              # 守护进程：主进程退出时它也会被终止
    q.start()
    time.sleep(0.1)
    print(f"  q.is_alive() = {q.is_alive()}")
    q.terminate()                # 强制终止（相当于 kill -9，粗暴但立即生效）
    q.join()
    print(f"  terminate() 后 is_alive() = {q.is_alive()}")
    print("  提示：terminate 不会执行清理逻辑，等于直接杀进程。")


# ======================================================================
# 语法解析 2：spawn vs fork
# ======================================================================


def demo_start_method() -> None:
    print()
    print("=" * 70)
    print("【2】spawn vs fork 启动方式")
    print("=" * 70)

    print("两种启动方式：")
    print("  fork（仅Linux/macOS）：")
    print("    复制父进程的整个内存快照，子进程【继承】父进程所有状态，")
    print("    启动快；但不安全—— 继承的锁/线程可能处于不一致状态。")
    print("  spawn（Windows 默认，macOS 需显式开启）：")
    print("    启动一个全新的 Python 解释器，再通过 pickle 传参。")
    print("    启动慢（重新加载模块），但干净、可预测，也是 Python 3.14 的默认方向。")

    print()
    print(f"当前平台可用方式：{mp.get_all_start_methods()}")
    print(f"当前使用方式：{mp.get_start_method()}")

    # 演示：显式创建上下文
    #语法解析：get_context('spawn') 得到一个独立上下文对象，
    # 可以为「不同环节」指定不同启动方式，互不干扰
    ctx_spawn = mp.get_context("spawn")
    print(f"spawn 上下文可用：{ctx_spawn.get_start_method()}")

    # 不同平台的差异
    if sys.platform == "win32":
        print("⚠️ Windows 只支持 spawn。所以本文件所有演示都按 spawn 写法，")
        print("   并且 if __name__ == '__main__' 保护是【强制】的。")
    else:
        print("当前系统同时支持 fork 与 spawn，行为可能与 Windows 不同。")


# ======================================================================
# 语法解析 3：pickle 限制
# ======================================================================


def demo_pickle_limits() -> None:
    print()
    print("=" * 70)
    print("【3】pickle 限制：进程间传参的硬性要求")
    print("=" * 70)

    # 可序列化的对象
    print("✅ 可以 pickle 的：基本类型、列表、字典、元组、集合、")
    print("   模块级函数、模块级类实例、bytes")

    ok = {"name": "Alice", "scores": [1, 2, 3]}
    data = pickle.dumps(ok)          # 序列化成 bytes
    print(f"   dict -> bytes：{data[:40]}...")
    print(f"   反序列化：{pickle.loads(data)}")

    # 不可序列化的对象
    print("❌ 不能 pickle 的：")
    print("   · lambda 表达式")
    print("   · 定义在函数内部的局部函数")
    print("   · 文件对象、socket、threading.Lock")
    print("   · 生成器对象")

    # 真实演示：把 lambda 丢给 pickle
    try:
        pickle.dumps(lambda x: x)
    except AttributeError as e:
        print(f"   实测 lambda：{type(e).__name__}: {e}")

    def local_func(x: int) -> int:
        return x
    try:
        pickle.dumps(local_func)
    except AttributeError as e:
        print(f"   实测局部函数：{type(e).__name__}: {e}")

    # 为什么有这些限制？
    print()
    print("原理：pickle 只能记录「对象在哪里」而不是「对象是什么」。")
    print("   它保存的是 模块名 + 函数名，接收端 import 该模块后按名字查找。")
    print("   lambda 和局部函数没有「可被找到的名字」，自然无法还原。")
    print("   文件/socket/锁则持有操作系统句柄，无法跨进程重建。")


# ======================================================================
# 语法解析 4：进程间通信 IPC
# ======================================================================


def queue_producer(q, count: int) -> None:
    """向队列写数据。q 是进程间队列，能自动跨进程。"""
    for i in range(count):
        q.put({"id": i, "payload": "x" * 10})
    q.put(None)             # 毒丸（poison pill）作为结束信号


def pipe_child(conn) -> None:
    """Pipe 的子进程端。注意：必须定义在模块顶层，否则无法 pickle。"""
    conn.send("来自子进程的消息")
    conn.close()               # 用完记得关闭，否则父进程会一直等EOF


def bump(value_obj, arr_obj) -> None:
    """修改共享内存中的数值。Value 访问必须加锁，否则有竞态。"""
    for _ in range(100):
        with value_obj.get_lock():     # get_lock() 返回该Value 配套的锁
            value_obj.value += 1
    arr_obj[0] = 99.0


def demo_ipc() -> None:
    print()
    print("=" * 70)
    print("【4】IPC：Queue / Pipe / Value / Array")
    print("=" * 70)

    # ---- Queue：最通用的进程间队列 ----
    q = mp.Queue()           # 只能通过 Process 传参传进去（可 pickle）
    prod = Process_class(target=queue_producer, args=(q, 5))
    prod.start()
    received = []
    # 用 timeout 做保护：万一生产者异常退出，也不会永久卡死在这里
    for _ in range(5):
        item = q.get(timeout=5)     # 阻塞等待，跨进程安全
        received.append(item["id"])
    prod.join()
    print(f"Queue 收到 id 列表：{received}")
    print("坑：Queue 的 get() 建议总是带 timeout，否则对端崩溃时你会永久阻塞。")

    # ---- Pipe：点对点双向通信，延迟更低 ----
    parent_conn, child_conn = mp.Pipe(duplex=True)   # duplex=True 双向
    pc = Process_class(target=pipe_child, args=(child_conn,))
    pc.start()
    child_conn.close()              # 父进程也要关掉自己这端
    msg = parent_conn.recv()
    pc.join()
    print(f"Pipe 收到：{msg}")

    # ---- Value / Array：共享内存中的简单变量 ----
    shared = mp.Value('i', 0)      # 'i' 是 C 的 int 类型代码，共享一个整数
    arr = mp.Array('d', [1.0, 2.0, 3.0])   # 共享一个 double 数组

    wp = Process_class(target=bump, args=(shared, arr))
    wp.start()
    wp.join()
    print(f"共享 Value 结果 = {shared.value}（子进程自增 100 次，主进程可见）")
    print(f"共享 Array 结果 = {list(arr)}")

    print("要点：Value/Array 内部自带锁，适合「少量简单数值」；")
    print("     复杂对象请用 Queue，或用下面的 shared_memory。")


# ======================================================================
# 语法解析 5：shared_memory 零拷贝共享
# ======================================================================


def shm_reader(name: str) -> tuple[float, float]:
    """子进程：直接读写父进程创建的共享内存。

    ⚠️ 必须顶层定义 —— spawn 下要 pickle 这个函数。
    """
    s = shared_memory.SharedMemory(name=name)   # 用 name 附着，而非 create
    try:
        # 关键：frombytes() 是【拷贝】出一份新的 array，改它并不会写回共享内存。
        # 要真正修改共享内存，必须显式写回：s.buf[:n] = b.tobytes()
        b = array.array('d')
        b.frombytes(s.buf[:s.size])
        old_first, last = b[0], b[-1]

        b[0] = -1.0
        # 把改动写回共享内存（这一步才是真正的「共享」生效）
        s.buf[:s.size] = b.tobytes()
        return old_first, last
    finally:
        s.close()      # 只关闭【当前进程】的映射，不要 unlink（删除权归创建者）


def demo_shared_memory() -> None:
    print()
    print("=" * 70)
    print("【5】shared_memory：真正的共享内存")
    print("=" * 70)

    size = 2 * 1024 * 1024# 2MB

    # ===== 父进程：创建并写入 =====
    # ⚠️ Windows 上创建共享内存时【不能自己指定名字】，
    #    CPython 会自动生成一个形如 'wnsm_6fc6f52c' 的全局唯一名。
    #    所以必须用 create=True 创建后，再读 shm.name 传给子进程；
    #    自己拼一个名字去附着会直接FileNotFoundError。
    #    （Linux 上可以用 name='myshm' 自行指定）
    shm = shared_memory.SharedMemory(create=True, size=size)
    name = shm.name
    try:
        # 结构化数组视图：把裸字节解释成 float64 数组
        buf = array.array('d')
        buf.frombytes(shm.buf[:shm.size])
        for i in range(len(buf)):
            buf[i] = i * 1.5

        # ⚠️ 关键一步：array.frombytes() 只是【读出】一份副本，
        #    改完必须显式写回 shm.buf，否则共享内存里仍然是 0。
        shm.buf[:shm.size] = buf.tobytes()
        print(f"父进程写入 {len(buf)} 个 double 并写回共享内存："
              f"首个={buf[0]:.1f}，末个={buf[-1]:.1f}")

        # 子进程直接操作【同一块物理内存】
        rp = Process_class(target=shm_reader, args=(name,))
        rp.start()
        rp.join()

        # 父进程这里也必须【重新从 shm.buf 读一遍】！
        # 因为上文的 buf = array.frombytes(...) 只是一份本地副本，
        # 子进程改的是 shm.buf，buf 并不会自动跟着变。这是一个很容易踩的坑。
        buf2 = array.array('d')
        buf2.frombytes(shm.buf[:shm.size])
        print(f"父进程重新读取共享内存：首元素={buf2[0]:.1f}（已被子进程改成 -1.0），"
              f"末元素={buf2[-1]:.1f}（保持不变）")
        print("全程【零拷贝】、零序列化，比 Queue 传大数据快得多。")
        print("⚠️ 坑：array.frombytes() 产生的是【副本】，")
        print("   任何一方改动后都必须重新读取 / 写回，否则会读到脏数据。")
        print("⚠️ 坑2：Windows 上共享内存的名字由系统生成，必须用 shm.name 传递。")
    finally:
        shm.close()
        shm.unlink()             # ⚠️ unlink 是删除共享内存对象！
        # 漏掉 unlink 会残留共享内存段（Linux 上可用 ipcs 查看），
        # 必须写在 finally 里做异常保护
    print(f"已 unlink，共享内存 {name} 已清理。")


# ======================================================================
# 语法解析 6：ProcessPoolExecutor
# ======================================================================


def square(x: int) -> int:
    """模块级函数：必须能被 pickle。"""
    return x * x


def double(x: int) -> int:
    time.sleep((10 - x) * 0.02)     # 制造不同的完成顺序
    return x * 2


def demo_pool() -> None:
    print()
    print("=" * 70)
    print("【6】ProcessPoolExecutor")
    print("=" * 70)

    data = list(range(1, 11))

    # 预热，把进程启动开销排除在计时之外
    with ProcessPoolExecutor(max_workers=4) as pool:
        list(pool.map(square, [1, 2, 3, 4]))

        # map：保序返回；chunksize 是 ProcessPoolExecutor 【专有】参数，
        # 表示把任务按块打包发给子进程，减少 IPC 次数
        print(f"chunksize=1 : {list(pool.map(square, data, chunksize=1))}")
        print(f"chunksize=5 : {list(pool.map(square, data, chunksize=5))}")
        print("chunksize 越大 -> IPC 次数越少 -> 越快，但【负载不均衡】风险越高。")

        # submit + as_completed：按完成顺序
        futs = {pool.submit(double, x): x for x in range(1, 6)}
        print("提交 1~5，按完成顺序返回：")
        for fut in as_completed(futs):
            print(f"  任务{futs[fut]} -> {fut.result()}")

        # initializer：每子进程初始化一次
        with ProcessPoolExecutor(max_workers=3, initializer=init_worker,
                                 initargs=()) as p2:
            list(p2.map(square, [1, 2]))

    print("注意：上面 as_completed 的打印顺序会随机器负载变化，属于正常现象。")


def init_worker() -> None:
    """initializer 钩子：每个子进程启动后执行一次。"""
    print(f"  [initializer] 子进程 {os.getpid()} 初始化完成")


# ======================================================================
# 语法解析 7：Windows 上 __main__ 保护的必要性
# ======================================================================


def demo_main_guard() -> None:
    print()
    print("=" * 70)
    print("【7】为什么必须有 if __name__ == '__main__'")
    print("=" * 70)

    print("spawn 启动流程：")
    print("  1. 父进程创建一个新的 Python 子进程")
    print("  2. 子进程启动时，会【从头执行整个主模块文件】")
    print("  3. 如果没有 main 保护，子进程执行到创建进程的代码时")
    print("     又会创建一批子进程 -> 无限递归")
    print()
    print("真实报错长这样：")
    print("  RuntimeError: An attempt has been made to start a new process")
    print("  before the current process has finished its bootstrapping phase.")
    print("  This probably means that you are not using fork() to start your")
    print("  child processes and you have forgotten to use the proper idiom")
    print('  in the main module: if __name__ == \'__main__\': ...')
    print()
    print(f"本文件当前运行模式：{__name__}")
    if __name__ == "__main__":
        print("✅ 处于 main 模式 —— 主逻辑只会执行一次。")


# ======================================================================
# 兼容层：Process 类的引用
# ======================================================================
# 说明：这里统一用 mp.Process。之所以封装成别名，
# 是为了让上面所有示例代码读起来更简洁，同时保留 mp. 前缀的可追溯性。
Process_class = mp.Process


def main() -> None:
    demo_process_basic()
    demo_start_method()
    demo_pickle_limits()
    demo_ipc()
    demo_shared_memory()
    demo_pool()
    demo_main_guard()
    print()
    print("=" * 70)
    print("04_multiprocessing 演示完毕")
    print("=" * 70)


if __name__ == "__main__":
    #⚠️ 本文件所有多进程逻辑都收敛在 main() 里，由这行保护。
    #   删掉这行 -> Windows 上会无限递归直到崩溃。
    main()