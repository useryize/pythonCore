# -*- coding: utf-8 -*-
"""
01_generators.py —— 生成器（Generator）原理与实战

【演示的语法点】
1. 生成器的定义：函数体含 yield -> 调用返回「生成器对象」而非执行函数体
2. yield vs return 的本质差异：yield 挂起函数、return 终止函数
3. 生成器的四段状态：创建 -> 首次 next() 才开始执行 -> 每次 next() 恢复到 yield 处 -> StopIteration 结束
4. send(value)：把值「发送」回 yield 表达式本身的返回值（双向通信，协程的基础）
5. throw(exc)：从生成器内部「抛入」异常，等价于在该 yield 处触发 raise
6. close()：在 yield 处抛入 GeneratorExit，触发 finally 清理
7. yield from：把子生成器的所有产出「委托」给父生成器（yield from 的返回值 = 子生成器的 return 值）
8. 生成器表达式 (expr for x in it) 与列表推导 [expr for x in it] 的差异
9. 惰性求值：生成器不消费就不计算（对比列表推导的立即全量计算）
10. 内存占用实测：tracemalloc 峰值对比 + sys.getsizeof 浅层对比
11. 生成器是「单次消费」对象：耗尽后再遍历为空；用 itertools.tee 可多次消费
12. 协程 vs 生成器：同一个 yield 关键字，语义由「谁调用 next/send」决定

【预期输出摘要】
- yield vs return：yield 让函数产出多个值；return 只能一个
- send() 双向通信演示：求「逐步输入、逐步平均」的在线平均数
- throw() 在 yield 处被捕获，生成器可选择继续或终止
- close() 触发 finally，打印清理日志
- yield from 委托子生成器，并拿到其 return 值（斐波那契之和）
- 惰性/内存实测：生成器峰值内存远小于列表；1000000 元素场景下差距通常在 10 倍以上
- 生成器耗尽后第二次遍历输出空列表
"""
import gc
import sys
import time
import tracemalloc
from collections.abc import Generator, Iterator


# ======================================================================
# 语法解析 1：yield 与 return 的本质差异
# ======================================================================
#
# 语法规则：
#   def f(): ...          普通函数，调用即执行，返回 None 或一个值
#   def f(): yield v      生成器函数，【调用时不执行】，返回一个生成器对象
#   return v              立即结束函数，把 v 作为返回值交给调用方
#   yield v               「挂起」函数，把 v 产出给调用方，保存现场等待下次恢复
#
# 关键理解：
#   return 是「函数 -> 调用方」的单向数据流，函数栈帧被销毁。
#   yield  是「函数 <-> 调用方」的可反复双向通道，函数栈帧被【保存在生成器对象里】。
#   所以生成器的「状态」不是靠返回值传递的，而是靠堆上那个被冻结的栈帧。


def gen_with_yield(n: int) -> Generator[int, None, None]:
    """用 yield 产出 0..n-1。注意：函数体此刻【一行都没有执行】。"""
    for i in range(n):
        # yield 表达式在语法上是「一个表达式」，它的值是下次 send() 进来的东西
        yield i
    # 函数体自然结束 -> 生成器自动 StopIteration，相当于隐式 return


def gen_with_return_list() -> list[int]:
    """对比：普通函数一次性构造完整列表，内存中同时存在 n 个 int。"""
    return list(range(10))


def demo_yield_vs_return() -> None:
    print("=" * 68)
    print("【1】yield vs return")
    print("=" * 68)

    # 调用生成器函数 -> 得到【生成器对象】，此时函数体尚未执行
    g = gen_with_yield(3)
    # 验证「函数体没执行」：用一个带副作用的探针
    print(f"刚创建时 g = {g!r}")
    print(f"isinstance(g, Iterator) = {isinstance(g, Iterator)}  "
          f"（生成器本质就是迭代器）")

    # next() 才会真正开始执行，并在第一个 yield 处停下
    print(f"第 1 次 next(g) = {next(g)}")
    print(f"第 2 次 next(g) = {next(g)}")
    print(f"第 3 次 next(g) = {next(g)}")

    # 第四次：生成器已耗尽，抛出 StopIteration（for 循环就是靠捕获它来结束的）
    try:
        next(g)
    except StopIteration:
        print("第 4 次 next(g) -> StopIteration（生成器已耗尽）")

    # 普通函数：一次性算完，内存里 10 个元素全在
    lst = gen_with_return_list()
    print(f"普通函数返回 list = {lst}，sys.getsizeof = "
          f"{sys.getsizeof(lst)} 字节")

    print("结论：yield 把「算出全部」推迟成「算出一个给一个」，")
    print("      return 必须先把全部结果装进一个容器才能交出去。")


# ======================================================================
# 语法解析 2：send() —— 双向通信与「协程」的雏形
# ======================================================================
#
# 语法规则：expr = yield default
#   这个表达式整体求值为「下一次 send 进来的值」。
#   若生成器还没启动就先 send，抛 TypeError（除非写了 default）。
#   写了 default 之后，【首次】next() 返回 default，之后才接受 send。


def running_avg() -> Generator[float, float, None]:
    """在线平均数：每次 send 一个新数，产出截至当前的平均值。

    这是「协程」最朴素的形态：外部驱动，内部有状态。
    """
    total = 0.0
    count = 0
    # 第一次 send 的值会被丢弃（因为本次是启动帧），用 value = yield None 接收并忽略
    value = yield None
    while True:
        # 如果外部 send 了 None，视为结束信号（常见的协程关闭协议）
        if value is None:
            break
        total += value
        count += 1
        # 这里 yield 出去的是「平均值」，同时【接收】下一次 send 的数
        value = yield total / count


def echo_gen() -> Generator[str, str, str]:
    """最小双向通道：把 send 进来的原样吐回去，收到 "stop" 则结束。"""
    received = yield "ready"          # 启动帧：产出 "ready"，接收第一次 send
    while received != "stop":
        received = yield received      # 产出旧值，接收新值
    return "bye"                       # return 值可被 StopIteration.value 取到


def demo_send() -> None:
    print()
    print("=" * 68)
    print("【2】send() 双向通信")
    print("=" * 68)

    # 启动协程：next() 等价于 send(None)，拿到第一次 yield 的值
    avg = running_avg()
    print(f"启动后拿到 {next(avg)}（首帧产出 None，等待数据）")

    for x in (10, 20, 30, 40):
        # send 的返回值 = 生成器在【下一次 yield】处产出的值
        print(f"send({x}) -> 当前平均 {avg.send(x):.2f}")

    # send(None) 触发 break，生成器结束
    try:
        avg.send(None)
    except StopIteration:
        print("send(None) 后生成器正常结束")

    # 看 StopIteration 里带回的 return 值
    e = echo_gen()
    print(f"\nnext()  -> {next(e)}")
    print(f"send('你好') -> {e.send('你好')}")
    print(f"send('世界') -> {e.send('世界')}")
    try:
        e.send("stop")
    except StopIteration as exc:
        # StopIteration.value 就是生成器里 return 的值
        print(f"send('stop') -> StopIteration, value={exc.value!r}")

    print("结论：send 让【调用方】的值进入生成器的 yield 表达式，")
    print("      这正是 asyncio 协程（async def + await）的语言基础。")


# ======================================================================
# 语法解析 3：throw() 与 close() —— 把异常「注入」生成器
# ======================================================================
#
# 语法规则：
#   gen.throw(ExcType)   在【当前挂起点】执行 raise ExcType
#   gen.close()          在挂起点抛 GeneratorExit（BaseException，不是 Exception）
#
# 设计原理：生成器把「栈帧所有权」交给了调用方，
#          如果调用方想终止它，就必须通过一个受控通道 —— 这就是 throw/close。


def echo_with_cleanup() -> Generator[str, str, None]:
    """演示 close() 触发 finally 的清理逻辑。"""
    try:
        while True:
            received = yield "ready"
            if received is None:
                break
            print(f"    [生成器] 收到 {received!r}")
            yield f"echo: {received}"
    except GeneratorExit:
        # GeneratorExit 继承自 BaseException，
        # 所以如果想在这里 return，会被解释器转成 RuntimeError（详见易错点）
        print("    [生成器] 捕获 GeneratorExit -> 执行 finally 清理")
        raise
    finally:
        print("    [生成器] finally 块执行（资源释放点）")


def demo_throw_and_close() -> None:
    print()
    print("=" * 68)
    print("【3】throw() 与 close()")
    print("=" * 68)

    # --- throw：在挂起点注入异常 ---
    def guarded() -> Generator[str, str, None]:
        try:
            yield "start"
        except ValueError as exc:
            # 捕获注入的异常，并决定「继续」还是「终止」
            print(f"    [生成器] 捕获注入的 ValueError: {exc}")
            yield "recovered"        # 吞掉异常后还能继续产出
        yield "after"

    g1 = guarded()
    print(f"next() -> {next(g1)}")
    print(f"throw(ValueError('外部注入')) -> {g1.throw(ValueError('外部注入'))}")
    print(f"继续 next() -> {next(g1)}  （异常被吞掉，生成器仍在运行）")

    # --- close：触发 finally ---
    print("\nclose() 演示：")
    g2 = echo_with_cleanup()
    print(f"next() -> {next(g2)}")
    g2.send("第一条")
    print("调用 close() ...")
    g2.close()
    # close 之后再 next 会抛 StopIteration（生成器已被置为关闭状态）
    print(f"close 后 next() -> ", end="")
    try:
        next(g2)
    except StopIteration:
        print("StopIteration（已关闭）")

    print("易错点：close() 注入的是 GeneratorExit(BaseException)，")
    print("        所以『except Exception』【抓不到】它，必须让 finally 干活。")


# ======================================================================
# 语法解析 4：yield from —— 生成器委托
# ======================================================================
#
# 语法规则：result = yield from iterable
#   等价于手写的 for + 逐个 yield，但额外做两件事：
#     1. 把子可迭代对象的 __iter__/__next__ 直接【委托】（不逐层传帧，性能更好）
#     2. result 拿到子生成器的 return 值（普通可迭代对象则是 None）
#
# 对比：yield from 是【转发】；for x in sub: yield x 是【重新迭代+转发】。
#       前者对生成器少一层栈帧，异常传播也更快。


def fib_gen() -> Generator[int, None, int]:
    """斐波那契生成器，return 的值是「前 n 项之和」。"""
    a, b = 0, 1
    total = 0
    for _ in range(10):
        yield a
        total += a
        a, b = b, a + b
    return total          # 这个值会被 yield from 的接收方拿到


def delegate() -> Generator[int, None, int]:
    """用 yield from 委托 fib_gen，并把子生成器的 return 值向上返回。"""
    result = yield from fib_gen()      # result == fib_gen 的 return 值
    yield -1                            # 证明委托结束后本函数仍在运行
    return result


def demo_yield_from() -> None:
    print()
    print("=" * 68)
    print("【4】yield from 委托")
    print("=" * 68)

    print("子生成器 fib_gen 的产出:", list(fib_gen()))

    d = delegate()
    print(f"委托产出: {list(d)}")

    # 单独演示：如何拿到子生成器的 return 值
    sub = fib_gen()
    total = yield from sub
    print(f"yield from 拿到的 return 值（斐波那契前 10 项之和）= {total}")

    # yield from 对比手写转发：两者结果一致，但 yield from 只压一层栈
    def manual() -> Generator[int, None, int]:
        for x in fib_gen():
            yield x

    print(f"手写转发结果一致: {list(manual()) == list(fib_gen())}")
    print("yield from 的额外能力：接收子生成器的 return 值 —— 这是手写转发做不到的。")


# ======================================================================
# 语法解析 5：生成器表达式 vs 列表推导
# ======================================================================
#
# 语法规则：
#   [expr for x in it]        列表推导：立即全量计算，得到 list
#   (expr for x in it)        生成器表达式：得到生成器，惰性求值
#   {k: v for ...} / {expr for ...}   字典/集合推导（没有生成器版本）
#
# 关键区别只有一个：【求值时机】。表达式写法几乎一样，性能特征完全不同。
# 判据：结果【只用一次】且【数据量大】-> 生成器表达式；
#      结果【要重复遍历 / 索引 / len / 切片】-> 必须用列表推导。


def demo_generator_expression() -> None:
    print()
    print("=" * 68)
    print("【5】生成器表达式 vs 列表推导")
    print("=" * 68)

    data = range(10)

    lc = [x * x for x in data]           # 立即算出全部 10 个
    ge = (x * x for x in data)           # 只得到一个「待办」

    print(f"列表推导类型: {type(lc).__name__}, 内容: {lc}")
    print(f"生成器表达式类型: {type(ge).__name__}，此刻还未计算")
    print(f"迭代生成器后: {list(ge)}")

    # 【重要陷阱】生成器是一次性的
    gen2 = (x * x for x in data)
    print(f"第一次消费: {list(gen2)}")
    print(f"第二次消费: {list(gen2)}  <- 空了！生成器【不可重复遍历】")

    # 带条件的生成器表达式（if 写在 for 之后，且可以有多个）
    even_sq = (x * x for x in range(20) if x % 2 == 0)
    print(f"带 if 的生成器表达式: {list(even_sq)}")

    # 嵌套 for 的顺序等价于嵌套 for 循环
    grid = (f"{r},{c}" for r in range(2) for c in range(3))
    print(f"嵌套 for（外层在前）: {list(grid)}")


# ======================================================================
# 语法解析 6：惰性求值与内存占用【实测】
# ======================================================================
#
# 实测方法：
#   tracemalloc.start() / get_traced_memory()  -> Python 层【真实分配】峰值，单位字节
#   sys.getsizeof()                            -> 只是对象【头部+槽位】，不含元素（list 的坑）
#
# 因此：
#   - 测「整体新增内存」必须用 tracemalloc
#   - sys.getsizeof([1]*1000000) 永远是 8MB 左右（只算指针数组），
#     但里面 100 万个 int 对象的内存它【一个字都没算】


def measure_peak(fn, *args) -> tuple[int, float]:
    """测量函数执行期间 tracemalloc 捕获的峰值内存与耗时。"""
    gc.collect()                       # 先回收垃圾，排除干扰
    tracemalloc.start()                # 开始追踪 Python 内存分配
    base, _ = tracemalloc.get_traced_memory()
    t0 = time.perf_counter()           # perf_counter 分辨率比 time.time 更高
    result = fn(*args)
    current, peak = tracemalloc.get_traced_memory()
    elapsed = time.perf_counter() - t0
    tracemalloc.stop()
    # 防止 result 被提前回收（这里只是防告警）
    del result
    return peak - base, elapsed


def build_list(n: int) -> list[int]:
    """列表方式：一次性持有 n 个 int 对象。"""
    return [i * 2 for i in range(n)]


def build_gen(n: int):
    """生成器方式：同一时刻只存在 1 个 int（外加生成器栈帧）。"""
    for i in range(n):
        yield i * 2


def demo_lazy_memory() -> None:
    print()
    print("=" * 68)
    print("【6】惰性求值与内存占用实测")
    print("=" * 68)

    N = 200_000

    # --- 实测 1：构建但不消费 ---
    print(f"\n[实测1] 构建 {N:,} 个元素，仅构建不消费（模拟真实管道流）")
    peak_list, t_list = measure_peak(lambda: build_list(N))
    peak_gen, t_gen = measure_peak(lambda: build_gen(N))
    print(f"  列表方式峰值新增内存: {peak_list:>10,} 字节  耗时 {t_list * 1000:6.2f} ms")
    print(f"  生成器峰值新增内存:   {peak_gen:>10,} 字节  耗时 {t_gen * 1000:6.2f} ms")
    print(f"  内存比: {peak_list / max(peak_gen, 1):.1f} 倍")

    # --- 实测 2：惰性 —— 生成器根本不需要真的造完 ---
    print(f"\n[实测2] 只要前 10 个：")
    peak_list2, t_list2 = measure_peak(lambda: [x for x in build_list(N)][:10])
    peak_gen2, t_gen2 = measure_peak(lambda: [x for x in build_gen(N)][:10])
    print(f"  列表: 峰值 {peak_list2:>10,} 字节, {t_list2 * 1000:6.2f} ms  <- 白算了 {N - 10:,} 个")
    print(f"  生成器: 峰值 {peak_gen2:>10,} 字节, {t_gen2 * 1000:6.2f} ms  <- 只算了 10 个")

    # --- 惰性求值的可观察副作用 ---
    print("\n[实测3] 惰性求值的副作用是「执行被推迟」：")
    calls: list[int] = []

    def spy(x: int) -> int:
        calls.append(x)                # 记录被真正计算过的元素
        return x

    lazy = (spy(x) for x in range(5))
    print(f"  创建生成器后，calls = {calls}  <- 空！还没算任何东西")
    first = next(lazy)
    print(f"  next() 一次后，calls = {calls}  <- 只算了 1 个")
    rest = list(lazy)
    print(f"  消费完剩余后，calls = {calls}")

    # --- sys.getsizeof 的局限（必须讲清楚，否则是常见误区）---
    print("\n[实测4] 为什么 sys.getsizeof 单独用会骗人：")
    big = [0] * 100_000                # 100000 个引用，指向【同一个】 int 对象 0（小整数缓存）
    uniq = list(range(100_000))        # 100000 个【不同的】 int 对象
    print(f"  sys.getsizeof([0]*100000)      = {sys.getsizeof(big):,} 字节（全是共享的小整数）")
    print(f"  sys.getsizeof(list(range(N))) = {sys.getsizeof(uniq):,} 字节（每个都是新对象）")
    print("  两者 getsizeof 几乎相同，但真实内存差 ~2.8MB（100000 个 int * 28 字节）。")
    print("  结论：getsizeof 只算【容器自身】，元素对象的内存必须用 tracemalloc 或 sys.getrefcount 侧写。")
    del big, uniq

    # --- 工程结论 ---
    print("\n[工程结论] 什么时候必须用生成器：")
    print("  1) 数据量超过内存预算（如日志逐行处理、CSV 大文件流式读取）")
    print("  2) 数据是无穷/流式的（如分页游标、Kafka consumer）")
    print("  3) 管道中段（map/filter 链），避免中间列表的峰值")
    print("  什么时候【不能】用：需要 len()/索引/多次遍历/随机访问 —— 生成器都不支持。")


# ======================================================================
# 语法解析 7：单次消费的坑与 tee
# ======================================================================
#
# 语法规则：from itertools import tee
#   a, b = tee(it, 2)   -> 用「对象池 + 计数器」把一个可迭代对象变成 N 个独立迭代器
#   本质是【有状态缓存】：tee 的每个分支各自记住自己读到哪了
#   代价：分支之间「落后」的量会被缓存下来 —— 分支消费越不均衡，缓存越大


def demo_single_consumption() -> None:
    print()
    print("=" * 68)
    print("【7】单次消费陷阱与 itertools.tee")
    print("=" * 68)

    # 常见错误：把生成器传给多个消费者
    def gen() -> Generator[int, None, None]:
        yield from range(5)

    g = gen()
    total = sum(g)          # 第一次消费
    print(f"sum(g) = {total}")
    print(f"再次 list(g) = {list(g)}  <- 生成器已耗尽，什么都没有")
    print("这就是「把生成器当可复用资源」的经典 Bug。")
    print("解法：(a) 传 list(g) 而不是 g；(b) 调用方各自新建；(c) 用 tee。")

    from itertools import tee

    a, b = tee(gen(), 2)
    print(f"\ntee 后可以独立消费: 支线A=list(a)={list(a)}  支线B=list(b)={list(b)}")

    # tee 的代价演示：分支不均衡时会产生缓存
    src = tee(iter(range(5)), 2)
    fast, slow = src
    _ = list(fast)          # fast 全部读完
    # slow 还没读，此时 slow 背后的缓存里存着 5 个元素
    print(f"慢分支随后读取: {list(slow)}  （期间 tee 帮它缓存了数据）")
    print("易错点：tee 并不复制数据，落后分支的量会被【一直缓存】到它追上为止，")
    print("        所以 tee 不是『随便用多少次都行』的银弹。")


# ======================================================================
# 语法解析 8：生成器 vs 协程 —— 同一个 yield，两种身份
# ======================================================================
#
# 语法规则：yield 的身份由【驱动方】决定
#   驱动方是「取数据的代码」（for/next）-> 生成器：产出值，没人关心谁在算
#   驱动方是「控制流」（send 决定下一步）    -> 协程：状态机，外部驱动内部决策
#
# 记忆法：
#   生成器 = 我不知道要产出什么，你问我要
#   协程   = 我有状态，你喂我什么我算什么
#   async def + await = 语言级的协程，由事件循环 send/schedule，无需手工 next()


def classify_greeter() -> Generator[str, str, None]:
    """既是生成器又是协程的写法 —— 二进制皆由调用方视角决定。"""
    while True:
        who = yield "请说出你的名字"
        if who is None:
            return
        print(f"    [greeter] 打招呼给 {who}")


def demo_gen_vs_coroutine() -> None:
    print()
    print("=" * 68)
    print("【8】生成器 vs 协程：同一关键字，两种身份")
    print("=" * 68)

    # 当生成器用：for 循环驱动，只关心产出
    print("作为【生成器】使用（for 只取产出）：")
    for name in classify_greeter():
        if name == "请说出你的名字":
            # 第一次 yield 的值不是名字，本轮跳过，只为展示驱动方式
            break
    print("  for 循环只会 next()，无法 send，所以它【永远问第二遍同一个问题】。")

    # 当协程用：send 驱动，关注状态
    print("\n作为【协程】使用（send 驱动状态）：")
    g = classify_greeter()
    next(g)
    for name in ("小明", "小红", None):
        try:
            g.send(name)
        except StopIteration:
            break
    print("  send 让它每次都推进到下一个状态 —— 这就是协程的本质。")

    print("\n结论：yield 表达式是【双向】的。忽略返回值方向，它就是生成器；")
    print("      读取并使用返回值方向，它就是协程。asyncio 正是把这件事标准化了。")


# ======================================================================
# 语法解析 9：生成器的运行时检查工具
# ======================================================================
#
# inspect 模块可以告诉你「生成器现在停在哪一行」—— 调试协程利器
# gi_frame.f_lineno  -> 当前挂起的源码行号
# gi_running         -> 是否正在运行（False 表示已挂起或已结束）


def demo_inspect_generator() -> None:
    print()
    print("=" * 68)
    print("【9】用 inspect 观察生成器内部状态")
    print("=" * 68)
    import inspect

    def probe() -> Generator[str, None, None]:
        yield "第一步"
        yield "第二步"
        yield "第三步"

    g = probe()
    print(f"创建后: gi_frame={g.gi_frame!r}")
    print(f"创建后: gi_running={g.gi_running}, gi_yieldfrom={g.gi_yieldfrom}")

    for i in range(3):
        val = next(g)
        # gi_frame 非 None 说明还有挂起的栈帧
        line = g.gi_frame.f_lineno if g.gi_frame else "已结束"
        print(f"  第{i + 1}次 next -> {val!r}，挂起在源码第 {line} 行，"
              f"gi_running={g.gi_running}")

    # 状态机是四态：GEN_CREATED -> GEN_SUSPENDED -> GEN_CLOSED
# 注意：产出【最后一个】 yield 时它【仍然是 SUSPENDED】，
# 只有再 next() 一次（撞到函数体结尾）才会真正转成 GEN_CLOSED。
    try:
        next(g)                                   # 第 4 次 next：函数体结束 -> GEN_CLOSED
    except StopIteration:
        pass
    print(f"再 next() 一次（函数体结束）后: getgeneratorstate -> "
          f"{inspect.getgeneratorstate(g)!r}")
    print(f"        gi_frame 被释放为 None: {g.gi_frame is None}"
          f"  <- 真正耗尽后【可以】用这个判据")
    print("可靠判据（不消费）：gi_frame is None，或 getgeneratorstate(g)=='GEN_CLOSED'")
    print("           gi_running 为 True 表示正在运行中。")


def main() -> None:
    demo_yield_vs_return()
    demo_send()
    demo_throw_and_close()
    demo_yield_from()
    demo_generator_expression()
    demo_lazy_memory()
    demo_single_consumption()
    demo_gen_vs_coroutine()
    demo_inspect_generator()
    print()
    print("=" * 68)
    print("01_generators 演示完毕")
    print("核心一句话：生成器 = 被冻结的函数栈帧，yield = 挂起/恢复指令。")
    print("=" * 68)


if __name__ == "__main__":
    main()