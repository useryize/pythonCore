# -*- coding: utf-8 -*-
"""
01_threading_basics.py —— threading 基础

【演示的语法点】
1. threading.Thread 的两种构造方式（位置参数 / 关键字参数）
2. start() 与 join() 的语义；join(timeout) 超时等待
3. daemon 守护线程：主线程退出时被强杀
4. thread name / ident / daemon 属性、enumerate()、active_count()
5. threading.local() 线程局部存储：同名变量互不干扰
6. 竞态条件（Race Condition）的复现：read-modify-write 丢失更新
7. 用 threading.Lock 修复竞态条件；lock.acquire() / release() / with 上下文管理器
8. 可重入锁 RLock 与普通锁的区别
9. Event / Condition / Semaphore 的极简用法（在 07 中展开）
10. 线程中的异常不会自动传播到主线程

【预期输出摘要】
- 两个线程交替打印（实际顺序不保证）
- daemon 线程在主线程结束后被直接终止，输出被截断
- 竞态演示：8 个线程各累加 100000 次，最终结果 < 800000（丢失更新）
- 加锁后结果稳定 == 800000
"""
import threading
import time
import random

# ======================================================================
# 语法解析 1：Thread 的构造与生命周期
# ======================================================================


def worker(name: str, count: int) -> None:
    """普通工作线程函数。

    语法解析：def 语句定义函数；参数 name: str 是类型注解（仅提示，不做运行时校验），
    返回值注解 -> None 表示无返回。函数体内的变量作用域为「局部作用域」。
    """
    for i in range(count):
        # time.sleep 会释放 GIL，所以其他线程能获得执行机会
        time.sleep(random.uniform(0.001, 0.005))
        print(f"[{name}] 第 {i + 1} 次执行")


def demo_thread_lifecycle() -> None:
    """演示 Thread 的创建、启动、等待。"""
    print("=" * 60)
    print("【1】Thread 启动与 join")
    print("=" * 60)

    # 关键字参数写法：target=函数, args=位置参数元组, name=线程名, daemon=是否守护
    # args 必须是「元组」，所以单个参数也要写成 (x,)
    t1 = threading.Thread(target=worker, args=("线程A", 3), name="T-A")
    # 位置参数写法：Thread(group, target, name, args, kwargs)
    # 注意：Python 3.13 起 daemon 已是「仅关键字参数」，不能再按第 6 个位置参数传
    t2 = threading.Thread(None, worker, "T-B", ("线程B", 3), None)

    print(f"启动前：active_count={threading.active_count()}")

    # start() 才是真正开始执行；未 start 的线程处于 NEW 状态，什么都不会发生
    t1.start()
    t2.start()
    print("两个线程已启动，join 之前主线程可以继续往下跑：")
    print(f"主线程 name={threading.current_thread().name}，"
          f"active_count={threading.active_count()}")

    # join() 会阻塞当前线程直到目标线程结束 —— 主线程在这里「等」
    t1.join()
    # 带超时的 join：最多等 0.5 秒就返回，避免永久阻塞
    t2.join(timeout=0.5)

    # is_alive() 判断线程是否还活着
    print(f"join 后：t1.is_alive()={t1.is_alive()}，"
          f"t2.is_alive()={t2.is_alive()}")
    print(f"t1.name={t1.name}  t1.ident={t1.ident}  t1.daemon={t1.daemon}")
    # enumerate() 返回所有【存活】线程对象
    print(f"当前存活线程：{[t.name for t in threading.enumerate()]}")


# ======================================================================
# 语法解析 2：daemon 守护线程
# ======================================================================


def daemon_worker(msg: str, loops: int) -> None:
    """工作线程，打印自己跑到第几轮。"""
    for i in range(loops):
        time.sleep(0.05)
        print(f"[{msg}] 第 {i + 1}/{loops} 轮")


def demo_daemon() -> None:
    """守护线程：主线程结束即被强杀，不管是否跑完。"""
    print()
    print("=" * 60)
    print("【2】daemon 守护线程")
    print("=" * 60)

    # 守护线程计划跑 20 轮（约 1 秒），但主线程只等 0.3 秒就返回
    d = threading.Thread(target=daemon_worker, args=("守护", 20), daemon=True)
    d.start()

    # 普通线程只跑 4 轮就结束；因为我们 join 了它，所以它一定会跑完
    normal = threading.Thread(target=daemon_worker, args=("普通", 4), daemon=False)
    normal.start()

    time.sleep(0.3)
    print(f">>> 主线程只跑到这里：守护线程仍在运行 is_alive={d.is_alive()}")
    # 只 join 普通线程；守护线程故意不 join —— 它会被强行丢弃
    normal.join()
    print(f"普通线程已结束（is_alive={normal.is_alive()}）")
    print(f"此刻守护线程 is_alive={d.is_alive()}（还差好几轮没跑完）")
    print("main() 返回后守护线程被直接杀死 —— 对比看：守护线程的输出停在半路，"
          "普通线程完整跑到了第 4 轮")


# ======================================================================
# 语法解析 3：threading.local 线程局部存储
# ======================================================================

# 模块级定义一个线程局部存储对象，所有线程共用「这一个对象」，
# 但每个线程在里面读写的是【各自独立】的子命名空间
tls = threading.local()


def set_and_get(value: str) -> str:
    # 第一次访问 tls.xxx 会在当前线程内创建属性；其他线程看不到
    tls.data = value
    time.sleep(0.01)  # 故意在这里制造交错，验证互不干扰
    return tls.data


def demo_thread_local() -> None:
    print()
    print("=" * 60)
    print("【3】threading.local() 线程局部存储")
    print("=" * 60)

    results = {}
    lock = threading.Lock()

    def run(name: str) -> None:
        got = set_and_get(name)
        # 向共享字典写入需要加锁，否则字典本身也可能损坏
        with lock:
            results[name] = got

    threads = [threading.Thread(target=run, args=(f"值{i}",)) for i in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    print(f"各线程读回自己的值：{results}")
    print("结论：每个线程看到 tls.data 都是自己刚写进去的那个，没有串味。")
    # 设计原理：tls 内部用「线程标识 -> 独立命名空间」的字典做分发，
    # 本质是 contextvars 之前的老写法，速度比 contextvars 慢。


# ======================================================================
# 语法解析 4：竞态条件的复现
# ======================================================================

# 不加锁的全局共享变量 —— 演示竞态条件的「受害者」
unsafe_counter = 0


def unsafe_increase() -> None:
    """不做同步的累加：read-modify-write 三步不是原子操作。"""
    global unsafe_counter  # 修改全局变量必须声明 global
    for _ in range(100_000):
        # 关键：这三行之间随时可能被线程切换打断
        temp = unsafe_counter       # ① 读
        temp += 1                    # ② 算
        time.sleep(0)                # ③ 强制线程切换（让竞态更稳定复现）
        unsafe_counter = temp       # ④ 写（可能把别人的新值覆盖掉）


def demo_race_condition() -> None:
    print()
    print("=" * 60)
    print("【4】竞态条件复现：8 线程 x 100000 次累加")
    print("=" * 60)

    global unsafe_counter
    unsafe_counter = 0
    threads = [threading.Thread(target=unsafe_increase) for _ in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    expected = 8 * 100_000
    print(f"期望结果：{expected}")
    print(f"实际结果：{unsafe_counter}")
    print(f"丢失更新：{expected - unsafe_counter} 次")
    print("原因：GIL 只保证【单条字节码】原子，不保证上面 4 行的整体原子性。")


# ======================================================================
# 语法解析 5：用 Lock 修复竞态条件
# ======================================================================

safe_counter = 0
safe_lock = threading.Lock()       # 互斥锁：同一时刻只允许一个线程持有
rlock = threading.RLock()          # 可重入锁：同一线程可重复获取


def safe_increase() -> None:
    global safe_counter
    for _ in range(100_000):
        # with 语句形式：进入时 acquire()，退出时自动 release()（即使中途抛异常）
        # 为什么推荐 with？避免「acquire 后忘记 release」造成死锁
        with safe_lock:
            safe_counter += 1


def demo_lock_fix() -> None:
    print()
    print("=" * 60)
    print("【5】用 Lock 修复竞态条件")
    print("=" * 60)

    global safe_counter
    safe_counter = 0
    threads = [threading.Thread(target=safe_increase) for _ in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    print(f"期望结果：{8 * 100_000}")
    print(f"实际结果：{safe_counter}")
    print("✅ 结果精确一致。锁把「读-改-写」整体变成临界区（Critical Section）。")


def demo_lock_semantics() -> None:
    """对比 Lock 与 RLock。"""
    print()
    print("=" * 60)
    print("【6】Lock vs RLock")
    print("=" * 60)

    plain = threading.Lock()
    # 普通锁不可重入：同一线程 acquire 两次 -> 直接死锁
    plain.acquire()
    print(f"普通锁已获取，再取一次会死锁（这里用 try 演示）：")
    acquired = plain.acquire(blocking=False)   # blocking=False = 非阻塞尝试
    print(f"  非阻塞重复获取成功？{acquired}")
    if acquired:
        plain.release()
    plain.release()

    # RLock 可重入：内部维护 (线程标识, 重入次数) 计数
    rl = threading.RLock()
    rl.acquire()
    rl.acquire()      # 同一线程再取一次，不会死锁
    print(f"RLock 重入两次成功，计数状态：{rl._is_owned()}")
    rl.release()
    rl.release()
    print("RLock 必须 release 与 acquire 次数相同，否则永久占用。")


# ======================================================================
# 语法解析 6：线程中的异常不会传播
# ======================================================================


def error_worker() -> None:
    raise ValueError("这个异常不会被主线程自动捕获到！")


def demo_thread_exception() -> None:
    print()
    print("=" * 60)
    print("【7】线程异常隔离")
    print("=" * 60)

    t = threading.Thread(target=error_worker, name="会崩的线程")
    t.start()
    t.join()
    print("主线程照常运行，未受影响。")
    print(f"但线程已死：is_alive={t.is_alive()}")
    print("原因：子线程有自己的栈，异常对象不会跨越线程边界传播。")
    print("生产做法：用 threading.excepthook 或在线程内部 try/except 收集日志。")


def main() -> None:
    demo_thread_lifecycle()
    demo_thread_local()
    demo_race_condition()
    demo_lock_fix()
    demo_lock_semantics()
    demo_thread_exception()
    # 守护线程演示放在最后：这样后续演示的耗时不会让它「意外跑完」，
    # 才能清楚地看到主线程一结束，它就被拦腰截断
    demo_daemon()
    time.sleep(0.1)
    print()
    print("=" * 60)
    print("01_threading_basics 演示完毕")
    print("=" * 60)


if __name__ == "__main__":
    # 为什么必须有这一行？
    # ① 当本文件被「当作模块 import」时，主逻辑不该执行
    # ② Windows 下 multiprocessing 用 spawn 启动子进程时会重新执行本文件
    main()