#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
with 语句与上下文管理器
================================================

【演示的语法点】
1. with 语句的语法与底层原理（__enter__ / __exit__ 协议）
2. 文件上下文管理器：自动 close 的真实验证
3. 自定义上下文管理器类（完整实现 __enter__ / __exit__）
4. __exit__ 的三种返回值语义：True / False / None（异常屏蔽的真相）
5. 嵌套 with：多个资源同时管理、执行顺序
6. with A() as a, B() as b：单行多上下文语法
7. contextlib.contextmanager 装饰器实现生成器式上下文管理器
8. contextlib.ExitStack：动态管理任意数量的上下文
9. contextlib.suppress：上下文内抑制指定异常
10. contextlib.redirect_stdout / redirect_stderr：临时重定向输出
11. contextlib.closing：给没有 __enter__ 的对象补上上下文能力
12. 不用 with 的后果：异常导致文件不关闭（真实演示）

【预期输出摘要】
- 每个演示都打印进入/退出的执行轨迹
- __exit__ 三种返回值分别导致「屏蔽异常 / 传播异常 / 抛新异常」
- 嵌套 with 的执行顺序（后进先出）
- 异常导致文件未关闭的证据（缓冲区数据丢失）

【配套文件】
本文件是 09_functional/05_context_managers.py 的上半部分，
后者侧重 @contextmanager 与 contextlib 工具集的组合应用。
"""

import contextlib
import io
import os
import sys
import tempfile
from pathlib import Path


WORK_DIR = Path(__file__).parent / "_tmp_with"
WORK_DIR.mkdir(exist_ok=True)


# ===== 语法解析 =====
# 【1】with 语句的完整语法
#   with <表达式> as <变量>, <表达式> as <变量>:
#       <语句块>
#
# 【2】编译后的等价形式
#   编译器会把 with 语句改写成 try/finally：
#       manager = <表达式>
#       try:
#           <变量> = manager.__enter__()
#           <语句块>
#       except <异常类型> as e:      # 仅当 __exit__ 可能抑制异常时才生成
#           if not manager.__exit__(type(e), e, e.__traceback__):
#               raise
#       else:
#           manager.__exit__(None, None, None)
#
# 【3】关键结论
#   with 语句「不保证」__exit__ 一定被调用一次：
#   - 正常结束 -> __exit__(None, None, None)
#   - 抛异常   -> __exit__(异常类型, 异常实例, traceback)
#   - __enter__ 本身抛异常 -> __exit__ 根本不会被调用（对象还没被接管）
#
# 【4】设计意图
#   with 解决的问题是「资源获取与释放的配对」。
#   它把「释放」从开发者需要手动书写的责任，变成了语言层面的保证。
def demo_1_file_with_basics():
    """with 管理文件：自动关闭的真实验证。"""
    print("=" * 74)
    print("【1】with 管理文件 —— 自动关闭验证")
    print("=" * 74)

    test_file = WORK_DIR / "basic.txt"

    # ===== 语法解析 =====
    # with 语句的两步：
    #   1) 调用 __enter__()，其返回值绑定到 as 后面的变量
    #   2. 把整个代码块包在 try 里，退出时调用 __exit__()
    #
    # 对文件对象而言：
    #   __enter__() 返回文件对象自身（并检查 closed 状态）
    #   __exit__() 调用 close()
    with open(test_file, "w", encoding="utf-8") as f:
        print(f"   块内：closed = {f.closed}")
        f.write("写入的内容")
    print(f"   块外：closed = {f.closed}  -> 离开 with 自动关闭")
    print(f"   文件内容 = {test_file.read_text(encoding='utf-8')!r}")
    print()

    # ===== 语法解析 =====
    # 即使块内抛异常，__exit__ 依然会被调用 —— 这是 with 的核心价值。
    print("② 块内抛异常时，文件依然被关闭：")
    try:
        with open(test_file, "w", encoding="utf-8") as f:
            f.write("部分内容")
            raise RuntimeError("块内故意抛异常")
    except RuntimeError as e:
        print(f"   捕获到 {e}")
        print(f"   异常后文件内容 = {test_file.read_text(encoding='utf-8')!r}")
        print("   -> 内容已写入磁盘，说明 close() 在异常传播前被调用了")
    print()

    print("③ 对比：不用 with 时异常导致数据丢失：")
    bad_file = WORK_DIR / "no_with.txt"
    # 不使用 with，异常时文件不会被关闭，缓冲区内容丢失
    f = open(bad_file, "w", encoding="utf-8", buffering=4096)
    try:
        f.write("这段内容会丢失")
        raise RuntimeError("抛异常")
    except RuntimeError:
        pass      # 捕获了异常，但文件仍然开着
    print(f"   异常后立即检查大小 = {bad_file.stat().st_size} 字节（缓冲区未刷盘）")
    f.close()
    print(f"   手动 close 后大小 = {bad_file.stat().st_size} 字节")
    print("   -> 对比：with 场景下异常时数据已落盘，因为 __exit__ 立即 close 了")
    print()

    print("④ with 中可以访问文件对象的全部方法：")
    with open(test_file, "r+", encoding="utf-8") as f:
        content = f.read()
        f.seek(0)
        f.write(content.upper())
    print(f"   转为大写后: {test_file.read_text(encoding='utf-8')!r}")
    print("   -> with 里的变量就是文件对象本身，不是包装对象")
    print()
    print("【要点】with 块结束后对象一定被关闭；不使用 with 则要手动 finally 保证。")


class Timer:
    """自定义上下文管理器：演示 __enter__ / __exit__ 的完整协议。"""

    def __init__(self, name, verbose=True):
        self.name = name
        self.verbose = verbose
        self.start_time = None
        self.elapsed = None

    # ===== 语法解析 =====
    # __enter__ 的约定：
    #   - 必须是「获取资源」的动作（打开文件、建立连接、进入临界区）
    #   - 返回值会绑定给 as 后的名字
    #   - 可以直接 return self（这样链式写法方便）
    def __enter__(self):
        import time
        self.start_time = time.perf_counter()
        if self.verbose:
            print(f"   [ENTER] 资源 {self.name} 获取成功")
        return self      # 返回 self 让调用方能访问实例属性

    # ===== 语法解析 =====
    # __exit__(exc_type, exc_value, traceback) 的三个参数：
    #   exc_type   异常类，若无异常则为 None
    #   exc_value  异常实例，若无异常则为 None
    #   traceback  traceback 对象，若无异常则为 None
    #
    # 返回值的语义（极易混淆，重点记忆）：
    #   True       -> 抑制异常：异常被「吃掉」，with 语句正常返回
    #   False / None -> 不抑制：异常继续向上传播（等价于默认行为）
    #   其他对象     -> 抛出 TypeError（必须是 bool 或 None）
    #
    # 注意：返回 True 是「吞掉异常」，不是「记录异常」。
    # 生产代码里滥用会导致 bug 被静默隐藏。
    def __exit__(self, exc_type, exc_value, traceback):
        import time
        self.elapsed = time.perf_counter() - self.start_time
        if self.verbose:
            if exc_type is not None:
                print(f"   [EXIT] 资源 {self.name} 释放（因 {exc_type.__name__} 而执行，"
                      f"耗时 {self.elapsed:.6f}s）")
            else:
                print(f"   [EXIT] 资源 {self.name} 正常释放"
                      f"（耗时 {self.elapsed:.6f}s）")
        # 返回 None 表示「不抑制异常」，异常会继续传播
        return None


def demo_2_custom_context_manager():
    """自定义上下文管理器与执行轨迹。"""
    print("=" * 74)
    print("【2】自定义上下文管理器：执行轨迹")
    print("=" * 74)

    print("① 正常路径：__enter__ -> 代码块 -> __exit__(None, None, None)")
    with Timer("数据库连接") as t:
        print("   [块内] 做一些事情")
    print(f"   块外仍可访问变量 t，其 elapsed = {t.elapsed:.6f}")
    print()

    print("② 异常路径：__exit__ 收到异常参数，但依然传播异常")
    try:
        with Timer("网络请求"):
            raise ValueError("请求失败")
    except ValueError as e:
        print(f"   块外捕获到 {type(e).__name__}: {e}  -> 异常未被抑制")
    print()

    print("③ 观察 __exit__ 的三个参数：")
    class ArgInspector:
        def __enter__(self):
            print("   __enter__ 被调用")
            return self

        def __exit__(self, exc_type, exc_value, traceback):
            print(f"   __exit__ 收到: exc_type={exc_type}, "
                  f"exc_value={exc_value!r}")
            print(f"                traceback 类型="
                  f"{type(traceback).__name__ if traceback else None}")
            return False      # 显式返回 False，不抑制
    print("   正常情况：")
    with ArgInspector():
        pass
    print("   异常情况：")
    # 异常会继续传播（__exit__ 返回 False），所以必须自己捕获
    try:
        with ArgInspector():
            raise KeyError("出错了")
    except KeyError:
        pass
    print()

    print("④ as 后面的变量其实可以不写：")
    with Timer("临时资源", verbose=False):
        pass
    print("   -> with 表达式:  合法（不需要返回值时）")
    print("   -> with 表达式 as x:  把 __enter__ 的返回值绑定给 x")
    print()


def demo_3_exit_return_semantics():
    """__exit__ 三种返回值语义的完整演示。"""
    print("=" * 74)
    print("【3】__exit__ 返回值的三种语义（关键知识点）")
    print("=" * 74)

    # ===== 语法解析 =====
    # 这三种返回值对应三种截然不同的控制流：
    #   True       -> 异常被抑制，程序从 with 语句之后继续（像什么都没发生）
    #   False/None -> 异常继续向上传播到外层 try
    #   抛新异常    -> 原异常被「替换」为新异常（chaining）
    class Swallowing:
        """返回 True：吞掉异常。"""
        def __enter__(self):
            print("   进入 Swallowing")
            return self
        def __exit__(self, *args):
            print(f"   离开 Swallowing，返回 True -> 异常被抑制")
            return True       # 关键：吞掉异常

    class Propagating:
        """返回 False：异常照常传播。"""
        def __enter__(self):
            print("   进入 Propagating")
            return self
        def __exit__(self, *args):
            print(f"   离开 Propagating，返回 False -> 异常继续传播")
            return False      # 或者不写 return（默认 None）

    class Raiser:
        """__exit__ 中抛出新异常：替换原异常。"""
        def __enter__(self):
            print("   进入 Raiser")
            return self
        def __exit__(self, exc_type, exc_value, tb):
            print(f"   离开 Raiser，抛出新异常替换原异常")
            # 在 __exit__ 中抛异常，会自动形成异常链：
            # 新异常.__context__ = 原异常
            raise RuntimeError("这是清理过程中发现的新问题") from exc_value

    print("① 返回 True —— 异常被完全吞掉：")
    with Swallowing():
        raise ValueError("这个异常会被吞掉")
    print("   -> 程序正常往下走，调用方完全不知道出过异常")
    print()

    print("② 返回 False —— 异常继续传播：")
    try:
        with Propagating():
            raise ValueError("这个异常会传播出去")
    except ValueError as e:
        print(f"   -> 外层捕获到 {type(e).__name__}: {e}")
    print()

    print("③ 在 __exit__ 中抛新异常 —— 替换原异常：")
    try:
        with Raiser():
            raise ValueError("原始异常")
    except RuntimeError as e:
        print(f"   -> 外层捕获到 {type(e).__name__}: {e}")
        print(f"   -> __cause__ = {e.__cause__}（from 指定的）")
    print()

    print("④ 返回非法值会怎样？")
    class BadReturn:
        def __enter__(self):
            return self
        def __exit__(self, *args):
            return "非布尔值"      # 非法返回值
    try:
        with BadReturn():
            pass
    except TypeError as e:
        print(f"   TypeError: {e}")
    print()
    print("【要点】返回 True 会「静默吞掉」异常，是异常处理中的头号陷阱。")
    print("       __exit__ 里抛新异常是合法的资源清理失败上报方式。")
    print("       返回值必须是 bool 或 None，否则抛 TypeError。")
    print("【面试常问】with 语句如何保证异常被抛出？答：__exit__ 返回 False/None 时，"
          "编译器生成的代码会执行裸 raise 重新抛出。")


def demo_4_nested_with():
    """嵌套 with 与单行多上下文。"""
    print("=" * 74)
    print("【4】嵌套 with 与单行多上下文语法")
    print("=" * 74)

    # ===== 语法解析 =====
    # 单行写法（Python 2.7+ / 3.1+ 支持）：
    #   with open(f) as f1, open(g) as g2:
    # 等价于嵌套，但只在第一个 with 的块内部再嵌套一个 with。
    # **重要**：单行多上下文的退出顺序是「从右到左」（后进先出），
    #           与嵌套写法一致。
    trace = []

    class Tracker:
        def __init__(self, name):
            self.name = name
        def __enter__(self):
            trace.append(f"enter {self.name}")
            return self
        def __exit__(self, *a):
            trace.append(f"exit{self.name}")
            return None

    print("① 嵌套 with（进入：外->内，退出：内->外）：")
    with Tracker("外层"):
        trace.append("外层代码")
        with Tracker("内层"):
            trace.append("内层代码")
        trace.append("回到外层")
    for step in trace:
        print(f"   {step}")
    print()

    trace.clear()
    print("② 单行多上下文（等价写法，退出顺序同样是内->外）：")
    with Tracker("A"), Tracker("B"), Tracker("C"):
        trace.append("所有上下文都已进入")
    for step in trace:
        print(f"   {step}")
    print()
    print("   等价的嵌套写法：")
    trace.clear()
    with Tracker("A"):
        with Tracker("B"):
            with Tracker("C"):
                trace.append("所有上下文都已进入")
    for step in trace:
        print(f"   {step}")
    print()

    print("③ 实际文件操作：单行写法同时读写两个文件")
    f1 = WORK_DIR / "nested1.txt"
    f2 = WORK_DIR / "nested2.txt"
    with open(f1, "w", encoding="utf-8") as src, \
         open(f2, "w", encoding="utf-8") as dst:
        src.write("源文件内容")
        dst.write("目标文件内容")
    print(f"   文件1 = {f1.read_text(encoding='utf-8')!r}")
    print(f"   文件2 = {f2.read_text(encoding='utf-8')!r}")
    print()

    print("④ 行长限制时用反斜杠续行（Python 3.10+ 也可用括号包裹）：")
    # 现代写法：用括号把多个 with 子句包起来，避免反斜杠
    with (open(f1, "r", encoding="utf-8") as a,
          open(f2, "r", encoding="utf-8") as b):
        print(f"   a={a.read()!r}, b={b.read()!r}")
    print("   -> 括号包裹的写法更清晰，推荐使用")
    print()


def demo_5_contextmanager_decorator():
    """contextlib.contextmanager 装饰器。"""
    print("=" * 74)
    print("【5】@contextlib.contextmanager 装饰器")
    print("=" * 74)

    # ===== 语法解析 =====
    # @contextmanager 把一个「只 yield 一次的生成器函数」包装成上下文管理器。
    # 规则：
    #   - yield 之前的代码 相当于 __enter__
    #   - yield 的值      相当于 __enter__ 的返回值
    #   - yield 之后的代码 相当于 __exit__
    #   - try/finally 是必需的：finally 里做清理，保证异常时也执行
    #
    # 陷阱：如果清理代码不放在 finally 里，异常时就完全不会被执行。
    @contextlib.contextmanager
    def resource(name):
        """用生成器写的上下文管理器。"""
        print(f"   [前置] 打开资源 {name}")
        try:
            # yield 之前不能有返回值，yield 的值就是 __enter__ 的返回值
            yield f"资源对象({name})"
        except Exception as e:
            # 异常会「注入」到 yield 处，except 可以捕获它
            print(f"   [异常] 捕获到 {type(e).__name__}: {e}")
            # 若在这里 return（不 raise），异常会被抑制
            raise     # 重新抛出，保持异常传播
        finally:
            # finally 保证无论正常/异常都会执行清理
            print(f"   [清理] 释放资源 {name}")

    print("① 正常路径：")
    with resource("数据库") as res:
        print(f"   [块内] 拿到的对象 = {res}")
    print()

    print("② 异常路径（finally 依然执行，异常继续传播）：")
    try:
        with resource("文件句柄"):
            raise KeyError("块内出错")
    except KeyError as e:
        print(f"   外层捕获到 {e}")
    print()

    print("③ 计时器（真实场景）：")
    @contextlib.contextmanager
    def timed(name):
        """统计 with 块内的执行耗时。"""
        import time
        start = time.perf_counter()
        try:
            yield
        finally:
            elapsed = time.perf_counter() - start
            print(f"   {name} 耗时 {elapsed * 1000:.3f} ms")

    with timed("数据计算"):
        sum(range(100000))
    print()

    print("④ 陷阱演示：清理代码不放finally 会怎样：")
    @contextlib.contextmanager
    def bad_resource():
        print("   [前置] 打开资源")
        yield
        # 这个 print 在 finally 外面
        print("   [清理] 这个永远不会被打印（因为异常时不会走到这里）")

    try:
        with bad_resource():
            raise RuntimeError("出错")
    except RuntimeError as e:
        print(f"   外层捕获到 {e}")
    print("   -> 对比上面 ② 的 finally 版本，清理代码完全没有执行")
    print()
    print("【要点】@contextmanager 的清理代码必须放在 finally 中。")
    print("       一个 @contextmanager 函数只能 yield 一次（yield 多次会报错）。")


def demo_6_exitstack():
    """contextlib.ExitStack：动态数量的上下文管理。"""
    print("=" * 74)
    print("【6】contextlib.ExitStack —— 管理数量不确定的资源")
    print("=" * 74)

    # ===== 语法解析 =====
    # ExitStack 的价值：当资源数量在运行时才确定时，
    # 无法用固定数量的 with 语句，但可以：
    #   with contextlib.ExitStack() as stack:
    #       for f in files:
    #           stack.enter_context(open(f))    # 逐个注册
    #   退出 with 时，栈会按「后进先出」依次关闭所有已注册的资源。
    #
    # 典型场景：批量处理 N 个文件、N 个数据库连接，数量由输入决定。
    files = [WORK_DIR / f"batch_{i}.txt" for i in range(4)]
    for i, f in enumerate(files):
        f.write_text(f"内容{i}", encoding="utf-8")

    print("① 用 ExitStack 批量打开多个文件：")
    with contextlib.ExitStack() as stack:
        # enter_context 返回被 __enter__ 的返回值（即文件对象）
        handles = [stack.enter_context(open(f, "r", encoding="utf-8"))
                   for f in files]
        for i, h in enumerate(handles):
            print(f"   文件{i} = {h.read()!r}")
        # 退出 with 时，ExitStack 逆序关闭所有文件
    print(f"   退出后所有文件都已关闭: {[h.closed for h in handles]}")
    print()

    print("② ExitStack 的通用回调（callback）：")
    # push() 可以注册任意清理函数，不必是上下文管理器
    log = []
    with contextlib.ExitStack() as stack:
        # 回调在栈销毁时按后进先出执行，且不接收 __exit__ 参数
        stack.callback(lambda: log.append("清理步骤2"))
        stack.callback(lambda: log.append("清理步骤1"))
        stack.callback(lambda: log.append("清理步骤3"))
    print(f"   执行顺序: {log}  -> 与注册顺序相反（后进先出）")
    print()

    print("③ push 与 enter_context 的区别：")
    print("   enter_context(cm) -> 调用 __enter__ 并返回其结果，注册 __exit__")
    print("   push(exit_func)  -> 只注册 __exit__ 回调，不接收返回值")
    print("   push(exit_func, *args) -> 注册带参数的回调")
    print()
    print("   典型用法：把已有对象也纳入栈管理")
    with contextlib.ExitStack() as stack:
        # contextlib.closing 可以给只有 .close() 的对象补上上下文能力
        import tempfile
        tmp = stack.enter_context(
            contextlib.closing(tempfile.NamedTemporaryFile(delete=False)))
        print(f"   临时文件: {tmp.name}")
    print()


def demo_7_suppress_and_redirect():
    """contextlib 的其他实用工具。"""
    print("=" * 74)
    print("【7】suppress / redirect_stdout / closing 工具")
    print("=" * 74)

    # ===== 语法解析 =====
    # suppress(exc1, exc2, ...)：在上下文内忽略指定的异常。
    # 内部实现就是一个「返回 True 的 __exit__」，
    # 所以它本质上就是 __exit__ 返回 True 的语法糖。
    print("① suppress：抑制指定异常")
    with contextlib.suppress(FileNotFoundError):
        # 这个文件不存在，会抛 FileNotFoundError
        open(WORK_DIR / "not_exist.txt", "r", encoding="utf-8")
    print("   -> 异常被抑制，程序继续")
    print()

    # 只抑制指定的异常，其他异常照常抛出
    print("② suppress 只抑制列出的异常：")
    try:
        with contextlib.suppress(FileNotFoundError):
            raise ValueError("这个不在抑制列表里")
    except ValueError as e:
        print(f"   -> 未被抑制，传播出来: {e}")
    print()

    # ===== 语法解析 =====
    # redirect_stdout(new_target)：把 sys.stdout 临时换成指定对象。
    # 原理是「保存旧值 -> 替换 -> finally 恢复」。
    print("③ redirect_stdout：临时重定向输出")
    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer):
        print("   这行不会显示在终端，而是写进了 buffer")
    # 退出 with 后自动恢复
    print(f"   buffer 内容 = {buffer.getvalue().strip()!r}")
    print("   -> 单元测试中捕获被测函数的输出，就用这个")
    print()

    print("④ redirect_stdout 的嵌套：")
    b1, b2 = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(b1):
        print("进入最内层前")
        with contextlib.redirect_stdout(b2):
            print("最内层")
        print("退出最内层后")
    print(f"   b1 = {b1.getvalue().strip()!r}")
    print(f"   b2 = {b2.getvalue().strip()!r}")
    print("   -> 内层结束后自动恢复到外层的重定向目标")
    print()

    # redirect_stderr 同理，用于捕获错误输出
    print("⑤ redirect_stderr：重定向标准错误")
    err_buffer = io.StringIO()
    with contextlib.redirect_stderr(err_buffer):
        print("这条会写到 stderr", file=sys.stderr)
    print(f"   err_buffer = {err_buffer.getvalue().strip()!r}")
    print()

    # ===== 语法解析 =====
    # closing(obj)：给「只有 close() 方法、没有 __enter__/__exit__」的对象
    # 补上上下文管理器能力。
    class SimpleResource:
        def __init__(self, name):
            self.name = name
            self.closed = False
        def close(self):
            self.closed = True

    print("⑥ closing：给普通对象补上上下文能力")
    r = SimpleResource("普通资源")
    # 直接用 with 会报错：TypeError: 'SimpleResource' object does not support
    # the context manager protocol
    with contextlib.closing(SimpleResource("普通资源")) as res:
        print(f"   使用中，closed = {res.closed}")
    print(f"   退出后 closed = {res.closed}")
    print()

    # nullcontext：Python 3.7+ 的「空上下文」，用于条件性使用 with
    print("⑦ nullcontext：可选的上下文（3.7+）")
    def process(strict):
        with (contextlib.nullcontext(open(WORK_DIR / "opt.txt", "w",
                                          encoding="utf-8"))
              if strict else contextlib.nullcontext()):
            if strict:
                print("   严格模式：文件已打开")
            else:
                print("   宽松模式：不做任何事")
    process(strict=True)
    process(strict=False)
    print("   -> 让「有时需要、有时不需要」的资源管理变得优雅")
    print()


def demo_8_without_with():
    """不用 with 的后果：完整对照。"""
    print("=" * 74)
    print("【8】不用 with 的三种典型错误")
    print("=" * 74)

    print("① 错误一：异常导致文件不关闭")
    f1 = WORK_DIR / "leak1.txt"
    f = open(f1, "w", encoding="utf-8", buffering=4096)
    try:
        f.write("重要数据")
        raise RuntimeError("中间出错")
    except RuntimeError:
        print("   异常被捕获，但 f 仍未关闭")
    print(f"   文件大小 = {f1.stat().st_size}（数据还在缓冲区，未落盘）")
    f.close()
    print(f"   手动 close 后 = {f1.stat().st_size} 字节（数据落盘）")
    print()

    print("② 错误二：多个文件时容易漏关其中一个")
    # 典型场景：打开两个文件，处理第二个时出错，第一个泄漏了
    f_a = open(WORK_DIR / "leak_a.txt", "w", encoding="utf-8")
    f_b = open(WORK_DIR / "leak_b.txt", "w", encoding="utf-8")
    try:
        f_a.write("A")
        f_b.write("B")
        raise ValueError("第二个文件处理出错")
    except ValueError:
        print("   出错了")
    # 开发者往往只记得关掉最后打开的那个
    f_b.close()
    print(f"   只关 b 后：a.closed={f_a.closed}, b.closed={f_b.closed}")
    print("   -> a 泄漏了！嵌套 with 会自动处理这种情况")
    f_a.close()    # 补救
    print()

    print("③ 错误三：文件句柄未释放 —— Windows 上无法移动/删除该文件")
    target = WORK_DIR / "locked.txt"
    renamed = WORK_DIR / "locked_renamed.txt"
    f_lock = open(target, "w", encoding="utf-8")
    f_lock.write("内容")
    f_lock.flush()      # 强制刷盘，确保文件确实有内容
    # 用「重命名」来验证文件是否被占用（比删除更安全，失败也不丢数据）
    try:
        os.rename(target, renamed)
        print("   重命名成功（当前环境允许操作已打开文件）")
        os.rename(renamed, target)      # 改回来，保持后续清理逻辑一致
    except OSError as e:
        # Windows 上会抛 PermissionError：文件被其他进程/句柄占用
        print(f"   重命名失败: {type(e).__name__}")
        print("      -> Windows 上这正是「文件被其他程序占用」的典型表现")
        print("      -> 根因：文件句柄未释放，同一文件被独占")
    f_lock.close()
    if renamed.exists():
        renamed.rename(target)
    print(f"   close 后可正常重命名: ", end="")
    try:
        os.rename(target, renamed)
        os.rename(renamed, target)
        print("是")
    except OSError:
        print("否")
    print()

    print("④ 正确写法的三种等价形式：")
    # 形式1：with（推荐）
    with open(WORK_DIR / "form1.txt", "w", encoding="utf-8") as f:
        f.write("x")
    # 形式2：try/finally
    f = open(WORK_DIR / "form2.txt", "w", encoding="utf-8")
    try:
        f.write("x")
    finally:
        f.close()
    # 形式3：contextlib.closing
    with contextlib.closing(open(WORK_DIR / "form3.txt", "w",
                                  encoding="utf-8")) as f:
        f.write("x")
    print("   三种方式都正确，with 最简洁")
    print()
    print("【要点】with 是「资源管理」的语言保证，finally 是「手写补偿」，")
    print("       前者不会因为开发者忘记写而失效。")


def cleanup():
    """清理临时文件。"""
    for f in WORK_DIR.iterdir():
        try:
            f.unlink()
        except OSError:
            pass
    try:
        WORK_DIR.rmdir()
    except OSError:
        pass


def main():
    """主入口。"""
    print("=" * 74)
    print("with 语句与上下文管理器")
    print("=" * 74)
    try:
        demo_1_file_with_basics()
        print()
        demo_2_custom_context_manager()
        print()
        demo_3_exit_return_semantics()
        print()
        demo_4_nested_with()
        print()
        demo_5_contextmanager_decorator()
        print()
        demo_6_exitstack()
        print()
        demo_7_suppress_and_redirect()
        print()
        demo_8_without_with()
    finally:
        cleanup()
    print()
    print("=" * 74)
    print("演示结束：with 只需记住「__enter__ 拿资源，__exit__ 还资源」")
    print("=" * 74)


if __name__ == "__main__":
    main()