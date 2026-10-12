#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
pdb 断点调试、traceback 解析与 bug 定位
================================================

【重要说明：本文件可非交互运行】
pdb 的交互式断点会阻塞等待输入，因此本文件采用以下策略演示：
  1. 用 pdb.Pdb(stdin=..., stdout=...) 注入自定义输入流，以「脚本化命令」驱动 pdb，
     既真实走一遍 pdb 的命令解析流程，又不会卡住终端。
  2. 真实 breakpoint() / pdb.set_trace() 的写法在注释中给出，并说明交互用法。
  3. 用 sys.settrace / 帧对象手工模拟断点，不依赖 pdb。

【演示的语法点】
1. traceback 模块：format_exc / format_exception / format_tb / TracebackException
2. traceback 的阅读顺序：从上往下读，最后一行才是真正的错误点
3. 异常链（__cause__ / __context__）在 traceback 里的呈现
4. pdb 脚本化驱动：l / p / w / bt / n / s / c 等命令的真实执行
5. breakpoint() 内置函数与 pdb.set_trace() 的关系
6. 手工模拟断点：sys.settrace / sys._getframe
7. 常见 bug 定位思路：可变默认值、闭包延迟绑定、浮点精度、遍历时修改容器
8. dis 模块查看字节码辅助定位

【预期输出摘要】
- 输出被捕获并格式化的 traceback（不产生真实崩溃）
- pdb 脚本会话的逐条命令输出（l / p / w / bt 真实生效）
- 手工断点实现打印变量快照
- 4 个真实 bug 的复现与定位
"""


import dis
import functools
import io
import pdb
import sys
import traceback


# ===== 语法解析 =====
# 【1】breakpoint() 的本质
#   breakpoint() 是 Python 3.7+ 内置函数（可通过 PYTHONBREAKPOINT 环境变量替换行为）。
#   它内部做三件事：
#     1) 检查 sys.breakpointhook 是否被用户覆盖
#     2) 默认调用 pdb.set_trace()
#     3) 返回 None
#   交互用法（不能在脚本中直接跑，会卡住等待输入）：
#       breakpoint()
#       # 停在这里，输入 n 步进、p 打印变量、c 继续、q 退出
#
# 【2】breakpoint() 与 pdb.set_trace() 的关系
#   breakpoint() 是 set_trace() 的「可配置封装」：
#   - 允许通过 sys.breakpointhook 替换调试器（如 pytest 的 --pdb 插件就替换了它）
#   - 支持 PYTHONBREAKPOINT 环境变量指定自定义函数
#   所以新代码优先用 breakpoint()，老代码用 pdb.set_trace()，两者效果一致。
#
# 【3】自动化调试的核心技巧
#   pdb.Pdb(stdin=..., stdout=...) 允许注入输入输出流：
#   - stdin  是一个「有 readline() 方法」的对象，用它提供命令序列
#   - stdout 是接收调试输出的流
#   这样 pdb 就能在内存中跑完，不依赖真实终端。


class ScriptedCommands:
    """脚本化的 stdin：把命令列表当作「用户输入」喂给 pdb。

    pdb.Pdb(stdin=...) 只要求 stdin 对象提供 readline() 方法，
    因此可以用任意实现了 readline 的对象替换交互终端，
    这样自动化运行脚本化调试时不会阻塞等待输入。
    """

    def __init__(self, commands):
        # 转成迭代器，readline 每次消费一条命令
        self._iter = iter(list(commands))

    def readline(self):
        try:
            return next(self._iter) + "\n"   # 补上换行符，模拟真实终端输入
        except StopIteration:
            # 命令用完后不断返回 continue，而不是空字符串（EOF）：
            # pdb 遇到 EOF 会抛出 BdbQuit 中断程序。
            # 反复返回 c 可让程序自然跑完，等价于「用户一路按到底」。
            return "c\n"

    def read_history(self):
        # pdb 在某些路径下会调用 read_history，提供空实现避免 AttributeError
        return []


def dump_pdb_output(text):
    """整理 pdb 输出：去掉命令行回显的 (Pdb) 前缀，保留源码列表与变量值。

    注意：pdb 打印变量值时也会带上 (Pdb) 提示符前缀（如 "(Pdb) 21"），
    所以不能简单地「跳过含 (Pdb) 的行」，否则会把真正的结果一起丢掉。
    """
    for line in text.rstrip().split("\n"):
        stripped = line.strip()
        if stripped.startswith("(Pdb)"):
            stripped = stripped[len("(Pdb)"):].strip()
            if not stripped:
                continue      # 纯提示符，跳过
            print(f"   {stripped}")
        else:
            print(f"   {line}")


def demo_1_traceback_reading():
    """traceback 的阅读方法与格式化 API。"""
    print("=" * 70)
    print("【1】traceback 阅读与格式化 API")
    print("=" * 70)

    # ===== 语法解析 =====
    # 制造一个三级调用栈的异常，用于观察 traceback 结构
    def level_c():
        # 真实 bug：对 None 调用方法
        x = None
        return x.bit_length()

    def level_b():
        # 中间层：做了一点数据转换，增加了干扰信息
        data = {"length": None}
        return level_c()

    def level_a():
        # 顶层调用
        return level_b()

    # ===== 语法解析 =====
    # traceback 各 API 的区别：
    #   format_exc()                       返回完整 traceback 字符串（不写 stderr）
    #   print_exc()                        直接写到 stderr，会污染终端
    #   format_exception_only(type, value) 只要「异常类型 + 消息」两行
    #   format_tb(tb, limit)               只要栈帧部分，limit=-1 表示全部
    print("① 完整 traceback（format_exc）：")
    try:
        level_a()
    except Exception:
        tb_text = traceback.format_exc()
        print("   " + "\n   ".join(tb_text.rstrip().split("\n")))
    print()

    print("② 阅读顺序说明：")
    print("   - traceback 中「最近的调用帧在最上面」（新调用栈在顶）")
    print("   - 最后一行才是真正的报错位置与原因")
    print("   - 上面每一帧是「是谁一路调用下来的」，用于定位调用链")
    print()

    print("③ 只看最后两行（format_exception_only）：")
    try:
        level_a()
    except Exception as e:
        for line in traceback.format_exception_only(type(e), e):
            print(f"   {line.rstrip()}")
    print()

    print("④ 只看栈帧部分（format_tb，limit=2 只取最近 2 层）：")
    try:
        level_a()
    except Exception:
        frames = traceback.format_tb(sys.exc_info()[2], limit=2)
        print("   " + "\n   ".join("".join(frames).rstrip().split("\n")))
    print()

    print("⑤ TracebackException：面向对象的方式，适合程序化处理")
    try:
        level_a()
    except Exception:
        # 从当前异常构造，会自动解析出栈帧与代码行
        tbe = traceback.TracebackException.from_exception(sys.exc_info()[1])
        print(f"   类型: {tbe.exc_type.__name__}")
        print(f"   消息: {str(tbe)}")
        print(f"   栈帧数: {len(tbe.stack)}")
        for frame in tbe.stack:
            # StackSummary 是命名元组，可按字段名访问
            filename = frame.filename.split("\\")[-1]
            print(f"     文件={filename} 行号={frame.lineno} 函数={frame.name}")
        # format() 返回的是「生成器」，需要先转成 list 才能取长度
        formatted = list(tbe.format())
        print(f"   format() 返回 {type(tbe.format()).__name__}，"
              f"共 {len(formatted)} 行")
    print()
    print("【要点】永远先看最后一行确定「哪里错、为什么错」，再往上追「谁调用的」。")
    print("【要点】format_exc 返回字符串便于入库/上报，print_exc 写 stderr 便于本地看。")


def demo_2_cause_in_traceback():
    """异常链在 traceback 中的呈现。"""
    print("=" * 70)
    print("【2】异常链在 traceback 中的呈现")
    print("=" * 70)

    def load():
        # 底层：int 转换失败直接抛出
        return int("abc")

    def parse():
        try:
            load()
        except ValueError as e:
            # 显式因果链 -> traceback 显示 "The above exception was the direct cause"
            raise RuntimeError("解析配置文件失败") from e

    def run_implicit():
        try:
            load()
        except ValueError:
            # 隐式上下文 -> traceback 显示 "During handling of the above exception"
            raise RuntimeError("解析配置文件失败（隐式）")

    print("① 显式异常链 raise ... from e：")
    try:
        parse()
    except RuntimeError:
        print("   " + "\n   ".join(traceback.format_exc().rstrip().split("\n")))
    print()

    print("② 隐式异常上下文（不写 from）：")
    try:
        run_implicit()
    except RuntimeError:
        print("   " + "\n   ".join(traceback.format_exc().rstrip().split("\n")))
    print()

    print("【要点】'direct cause' 表示设计上的因果；'During handling' 表示执行上的意外。")
    print("【要点】排查问题时两种链都要看：显式链给原因，隐式链给「当时正在干什么」。")


def demo_3_pdb_scripted():
    """用脚本化 pdb 驱动真实断点，不阻塞终端。"""
    print("=" * 70)
    print("【3】pdb 脚本化驱动（真实执行 pdb 命令，但不阻塞）")
    print("=" * 70)

    # ===== 语法解析 =====
    # pdb 常用命令（真实语义）：
    #   n / next  执行下一行（不进入函数调用）
    #   s / step  执行下一行（若该行有函数调用则进入）
    #   c / cont   继续执行到下一个断点或程序结束
    #   p expr     打印表达式（自动使用当前作用域）
    #   pp expr    pretty print（自动换行缩进，便于看嵌套结构）
    #   l          列出当前位置附近的源码
    #   ll         列出当前函数的全部源码
    #   w          显示「调用栈」（where）
    #   u / d      在栈中上移/下移
    #   bt         打印完整调用栈回溯
    #   b 行号     在指定行设断点
    #   tbreak     临时断点（执行一次后自动删除）
    #   q          退出调试

    def calculation(numbers, hook=None):
        """带调试钩子的计算函数。"""
        total = 0
        for i, num in enumerate(numbers):
            if hook is not None:
                # hook 是回调，用来实现「在函数内部打断点」。
                # 直接调用 dbg.set_trace 即可停在这一行。
                hook()
            total += num
            print(f"     [运行] 第{i + 1}轮 total={total}")
        average = total / len(numbers)
        return total, average

    print("① 进入 pdb，看源码上下文与局部变量（命令：l / p）")
    print("-" * 60)
    commands = [
        "l",          # list：显示当前行附近的源码
        "p numbers",  # print：打印局部变量（参数）
        "p i, num",   # print：打印循环变量
        "c",           # continue：继续跑完
    ]
    out = io.StringIO()
    # stdin/stdout 注入：让 pdb 完全在内存中运行，不会阻塞终端
    dbg = pdb.Pdb(stdin=ScriptedCommands(commands), stdout=out)
    # set_trace 作为回调传入，在函数内部触发，
    # 这样 p 命令打印的才是函数内的局部变量（而非外层函数的）
    result = calculation([10, 20, 30, 40], hook=dbg.set_trace)
    dump_pdb_output(out.getvalue())
    print("-" * 60)
    print(f"   函数正常返回: {result}")
    print()

    print("② 观察调用栈（命令：w / bt）")
    print("-" * 60)

    def inner_target():
        value = 42
        if dbg_stack is not None:
            # 注意：Pdb 实例本身不可调用，必须调用它的 set_trace 方法
            dbg_stack.set_trace()
        return value

    def middle_layer():
        return inner_target()

    def outer_layer():
        return middle_layer()

    out2 = io.StringIO()
    dbg_stack = pdb.Pdb(stdin=ScriptedCommands(["w", "bt", "p value", "c"]),
                        stdout=out2)
    v = outer_layer()
    dump_pdb_output(out2.getvalue())
    print("-" * 60)
    print(f"   四层嵌套调用中调试，最内层返回: {v}")
    print()

    print("③ 单步执行：n（next）不进入函数调用，整行执行完再停")
    print("-" * 60)

    def helper_square(n):
        result = n * n
        print(f"     [进入 helper_square] n={n}, result={result}")
        return result

    def compute(hook=None):
        a = 5
        if hook is not None:
            hook()          # 在 a 与 b 都已赋值后停下，方便执行 n / s
        b = a * 3
        # n 命令会整行执行完（跳过函数调用），s 则会进入 helper_square
        c = helper_square(b)
        print(f"     [回到 compute] c={c}")
        return a + b + c

    out3 = io.StringIO()
    # 命令序列：n 步进 -> p 打印 a -> n 再步进（跳过函数调用）-> p 打印 b -> c 继续
    dbg3 = pdb.Pdb(stdin=ScriptedCommands(["n", "p a", "n", "p b", "c"]),
                   stdout=out3)
    total = compute(hook=dbg3.set_trace)
    dump_pdb_output(out3.getvalue())
    dump_pdb_output(out3.getvalue())
    print("-" * 60)
    print(f"   compute() 返回: {total}")
    print()
    print("【要点】交互式用法：")
    print("   breakpoint()                     # Python 3.7+，推荐")
    print("   import pdb; pdb.set_trace()      # 老写法，效果一致")
    print("   breakpoint()                     # 在 except 块内可带出异常上下文")
    print("【要点】自动化/测试环境下，用 pdb.Pdb(stdin=...) 注入命令，避免阻塞。")


def demo_4_manual_breakpoint():
    """手工模拟断点：不依赖 pdb，用标准库实现断点功能。"""
    print("=" * 70)
    print("【4】手工模拟断点（sys.settrace / 帧对象）")
    print("=" * 70)

    # ===== 语法解析 =====
    # 方法一：sys._getframe() 获取当前调用帧，直接读取局部变量。
    #   sys._getframe(depth) —— 下划线开头表示「内部 API」，但调试用途广泛使用。
    #   帧对象 f 的主要属性：
    #     f.f_locals   当前局部变量字典
    #     f.f_globals  模块全局变量
    #     f.f_lineno   当前行号
    #     f.f_code.co_name    函数名
    #     f.f_back     上一层帧（调用者），沿它可遍历整个调用栈
    def snapshot_frame(depth=1):
        """获取调用者的帧对象并输出变量快照。"""
        # sys._getframe(0) 是自己，1 是调用者
        frame = sys._getframe(depth)
        print(f"   [手工断点] 当前函数: {frame.f_code.co_name} "
              f"第 {frame.f_lineno} 行")
        items = ", ".join(f"{k}={v!r}" for k, v in frame.f_locals.items()
                          if not k.startswith("__"))
        print(f"   [手工断点] 局部变量: {items}")
        return frame.f_code.co_name

    def frame_inspector():
        a = 10
        b = 32
        c = a + b
        # 手工断点：在这一行查看局部变量
        return snapshot_frame()

    print("① 用 sys._getframe() 取变量快照：")
    print(f"   计算结果 c = 42，快照来自函数: {frame_inspector()}")
    print()

    # ===== 语法解析 =====
    # 方法二：sys.settrace(trace_func) 注册全局追踪函数。
    # 追踪函数签名固定为 (frame, event, arg)，event 取值：
    #   'call'      进入函数
    #   'line'      即将执行一行
    #   'return'    函数返回
    #   'exception' 发生了异常
    # 返回值：返回局部 trace_func 则继续追踪该帧；返回 None 则停止追踪。
    def make_tracer(target_function, interesting_lines):
        """构造追踪函数，只在特定函数的特定行打印快照。"""
        def tracer(frame, event, arg):
            if frame.f_code.co_name != target_function:
                return None   # 不追踪其他函数，性能友好
            if event == "line" and frame.f_lineno in interesting_lines:
                print(f"   [TRACE] {frame.f_code.co_name}:{frame.f_lineno}  "
                      f"变量={dict(frame.f_locals)}")
            elif event == "exception":
                exc_type = arg[0].__name__ if arg[0] else "None"
                print(f"   [TRACE] 异常事件: {exc_type} @ 第{frame.f_lineno}行")
            return tracer    # 返回自己表示「继续追踪这个帧」
        return tracer

    def target_func(x, y):
        step1 = x * 2
        step2 = step1 + y
        step3 = step2 - x
        return step3

    print("② 用 sys.settrace() 追踪指定函数的指定行：")
    # 用 try/finally 保证 tracer 一定被清理，否则后续代码全都会被追踪
    try:
        sys.settrace(make_tracer("target_func", {2, 3, 4}))
        r = target_func(10, 5)
        print(f"   target_func 返回: {r}")
    finally:
        # 必须恢复为 None，否则后续所有代码都会被追踪，性能暴跌
        sys.settrace(None)
    print()

    # 方法三：用装饰器实现局部追踪（更接近工程用法）
    def trace_function(func):
        """装饰器形式：只追踪被装饰的函数，退出时自动恢复全局状态。"""
        @functools.wraps(func)   # 保留原函数元信息，否则 help() 会显示错
        def wrapper(*args, **kwargs):
            name = func.__name__

            def local_tracer(frame, event, arg):
                if event == "line":
                    print(f"   [DECORATOR-TRACE] {name}:{frame.f_lineno} "
                          f"-> {frame.f_locals}")
                return local_tracer

            old = sys.gettrace()   # 保存原有 tracer
            sys.settrace(local_tracer)
            try:
                return func(*args, **kwargs)
            finally:
                sys.settrace(old)  # 恢复，保证不污染其他代码
        return wrapper

    @trace_function
    def decorated_func(n):
        acc = 0
        for i in range(n):
            acc += i * i
        return acc

    print("③ 用装饰器实现局部追踪（更接近工程用法）：")
    print(f"   计算结果 0²+1²+2²+3² = {decorated_func(4)}")
    print()
    print("【要点】sys.settrace 是全局开关，性能开销大（约慢 10-100 倍），")
    print("       只能用于开发调试，绝不能留在生产代码里。")


def demo_5_common_bugs():
    """常见 bug 的制造、定位与修复。"""
    print("=" * 70)
    print("【5】常见 bug 定位思路（4 个真实 bug）")
    print("=" * 70)

    print("① Bug1：可变默认参数（最隐蔽的 Python bug）")
    # ===== 语法解析 =====
    # 陷阱原理：默认参数在函数定义时求值一次，之后所有调用共享同一个列表对象。
    # 正确写法用 None 作哨兵，在函数体内新建列表。
    def buggy_append(item, target=[]):      # BUG：默认值是共享的可变对象
        target.append(item)
        return target

    def fixed_append(item, target=None):    # 正确
        if target is None:
            target = []
        target.append(item)
        return target

    print(f"   bug 版 第一次: {buggy_append('a')}")
    print(f"   bug 版 第二次: {buggy_append('b')}  <- 第一次的结果被污染！")
    print(f"   修复版 第一次: {fixed_append('a')}")
    print(f"   修复版 第二次: {fixed_append('b')}  <- 互不影响")
    print(f"   验证: buggy_append.__defaults__ = {buggy_append.__defaults__}")
    print("   定位思路：打印 id() 与 len()，发现同一 id 且 len 持续增长")
    print()

    print("② Bug2：闭包延迟绑定（循环里定义函数）")
    # ===== 语法解析 =====
    # 陷阱原理：for 循环不会为每轮创建独立作用域，lambda 捕获的是变量本身而非当时的值，
    # 等到真正调用时循环早已结束，所有闭包都看到同一个变量的最终值 3。
    funcs_buggy = [lambda: i for i in range(4)]
    # 修复：默认参数把当前值固化下来
    funcs_fixed = [lambda i=i: i for i in range(4)]

    print(f"   bug 版:  {[f() for f in funcs_buggy]}   <- 全部是循环结束后的值")
    print(f"   修复版: {[f() for f in funcs_fixed]}")
    print("   定位思路：理解 Python 无块级作用域，闭包捕获的是变量引用不是值")
    print()

    print("③ Bug3：浮点数精度与边界")
    print(f"   0.1 + 0.2 = {0.1 + 0.2}")
    print(f"   0.1 + 0.2 == 0.3 ? {0.1 + 0.2 == 0.3}")
    # 正确做法一：用 decimal 模块做精确十进制运算
    from decimal import Decimal
    sum_dec = Decimal("0.1") + Decimal("0.2")
    print(f"   用 Decimal: {sum_dec} == {Decimal('0.3')} ? "
          f"{sum_dec == Decimal('0.3')}")
    # 正确做法二：用 math.isclose 做容差比较
    import math
    print(f"   用 math.isclose(0.1+0.2, 0.3): {math.isclose(0.1 + 0.2, 0.3)}")
    # 整数除法的坑：/ 永远返回 float，// 才是整除
    print(f"   7 / 2 = {7 / 2} (float), 7 // 2 = {7 // 2} (int)")
    print("   定位思路：打印 repr() 而非 print()，看清类型；用 f'{x!r}'")
    print()

    print("④ Bug4：遍历时修改容器")
    # ===== 语法解析 =====
    # 迭代器持有容器的「内部版本号」。修改容器会使版本号变化，
    # 下一次 __next__ 时检测到不一致，抛出 RuntimeError:
    #   "dictionary changed size during iteration" / "list changed size..."
    def buggy_loop_remove(items, target):
        # BUG：边遍历边删除。若要删多个元素，会漏删甚至直接报错
        for x in items:
            if x == target:
                items.remove(x)

    def fixed_loop_listcomp(items, target):
        # 正确：构建新列表（列表推导式有独立作用域，天然安全）
        return [x for x in items if x != target]

    def fixed_loop_copy(items, target):
        # 正确：遍历副本（切片产生新列表）
        result = []
        for x in items[:]:
            if x != target:
                result.append(x)
        return result

    # 注意：只有一个目标元素时 remove 恰好不会越界，但依然会「漏删」——
    # 因为迭代器索引不会因删除而回退，会跳过紧邻的元素。
    data = [1, 2, 3, 2, 4]
    buggy_loop_remove(data, 2)
    print(f"   bug 版结果: {data}   <- 第二个 2 没被删掉（迭代器索引不回退）")

    data2 = [1, 2, 3, 2, 4, 2]
    # 连续删除多个目标元素时会直接抛 RuntimeError
    try:
        for _ in range(5):
            buggy_loop_remove(data2, 2)
        print(f"   最终结果: {data2}")
    except RuntimeError as e:
        print(f"   连续删除时: RuntimeError: {e}")
    print(f"   修复版(推导式): {fixed_loop_listcomp(data, 2)}")
    print(f"   修复版(遍历副本): {fixed_loop_copy(data, 2)}")
    print("   定位思路：元素「漏删」= 迭代器索引问题；报错 = 容器版本号变化")
    print()

    print("【定位方法论】")
    print("   1. 复现：让 bug 稳定出现，不要凭想象改代码")
    print("   2. 二分：注释掉一半代码缩小范围（git bisect 更快）")
    print("   3. 打印：用 print(f'{x!r}') 打印类型与 repr，而不是 str")
    print("   4. 断点：pdb 的 s/n/w/bt，必要时用 dis 看字节码")
    print("   5. 最小化：写一个 10 行内能复现的最小用例")


def demo_6_dis_bytecode():
    """用 dis 查看字节码辅助定位。"""
    print("=" * 70)
    print("【6】用 dis 模块查看字节码")
    print("=" * 70)

    # ===== 语法解析 =====
    # dis.dis(obj) 反汇编函数的字节码。Python 源码 -> 字节码 -> 字节码解释器执行。
    # 字节码是「栈式指令」：LOAD_CONST、LOAD_FAST、LOAD_GLOBAL、BINARY_OP 等。
    # 常见用途：
    #   - 验证「Python 如何实现可变默认参数」（默认值在 MAKE_FUNCTION 时求值一次）
    #   - 确认某个语法糖展开成了什么
    #   - 排查「为什么性能慢」（看有多少次属性查找）
    def mutable_default(x, acc=[]):
        acc.append(x)
        return acc

    print("① 可变默认参数的字节码（观察默认值如何被绑定）：")
    dis.dis(mutable_default)
    print("   解读：defaults 元组（acc=[] 中的那个 []）在函数对象创建时")
    print("         （MAKE_FUNCTION）就已构造好，存进函数对象的 __defaults__，")
    print("         之后每次调用都从 __defaults__ 取同一个列表对象。")
    print(f"   验证: mutable_default.__defaults__ = {mutable_default.__defaults__}")
    print(f"   id 保持不变: {id(mutable_default.__defaults__[0])}")
    print()

    print("② 查看常量折叠（compile 阶段优化）：")
    def const_folding():
        return 2 * 3 + 4 * 5   # 常量表达式在编译期就被算好

    dis.dis(const_folding)
    print("   解读：直接返回 26，说明 CPython 编译器做了常量折叠；")
    print("         因此浮点精度问题不是编译器引起的，而是二进制浮点表示本身。")
    print()

    print("③ 局部变量 vs 全局变量的字节码依据：")
    def local_vs_global():
        x = 1
        return x + 1

    dis.dis(local_vs_global)
    print("   解读：局部变量用 LOAD_FAST（直接读栈），全局变量用 LOAD_GLOBAL")
    print("         （要查字典），因此循环内应把频繁访问的对象提到局部变量。")
    print()
    print("【要点】dis.dis() 是理解 Python 执行机制的终极工具；")
    print("       面试问「可变默认参数为什么是坑」时，能从字节码层面解释就是加分项。")


def demo_7_pdb_recipes():
    """pdb 的实际使用配方。"""
    print("=" * 70)
    print("【7】pdb 使用配方")
    print("=" * 70)

    print("① 交互式断点（人工调试时的标准写法）：")
    print("-" * 60)
    print("""
   # 方式A（推荐，Python 3.7+）：
   breakpoint()            # 等价于 import pdb; pdb.set_trace()

   # 方式B（老写法，兼容所有版本）：
   import pdb
   pdb.set_trace()

   # 方式C：在 except 块内使用，pdb 会带出异常上下文，
   #        输入 q 退出时可看到 raise 时的调用栈
   try:
       risky_operation()
   except ValueError:
       breakpoint()
       # 在 pdb 里输入：u / d 切换栈帧，查看异常从哪抛出
   """)
    print("-" * 60)

    print("② 条件断点的脚本化模拟：")
    print("-" * 60)

    def search_loop(data, target, on_hit=None):
        found = None
        for i, item in enumerate(data):
            # 模拟「条件断点」：只有满足条件时才进入调试器
            if on_hit is not None and item == target:
                on_hit()
            if item == target:
                found = i
                break
        return found

    out = io.StringIO()
    commands = [
        "p i, item",       # print：确认断在了正确的位置
        "p found",         # 此时 found 尚未赋值
        "c",                       # continue：继续执行
        "p found",         # 退出后 found 已被赋值
        "c",                       # 继续
    ]
    dbg = pdb.Pdb(stdin=ScriptedCommands(commands), stdout=out)
    # 把 set_trace 作为回调传入，实现「按条件打断点」，比按行号设断点更稳定
    result = search_loop([10, 20, 30, 20, 40], 20, on_hit=dbg.set_trace)
    dump_pdb_output(out.getvalue())
    print("-" * 60)
    print(f"   search_loop 返回索引: {result}（第一个 20 的位置）")
    print()

    print("③ 断点命令语法说明：")
    print("   b <行号>            普通断点，每次执行到该行都停")
    print("   b <行号> <条件>      条件断点，条件为真才停")
    print("   b <函数名>          在函数入口设断点")
    print("   tbreak <行号>       临时断点，命中一次后自动删除")
    print("   cl / clear          清除全部断点")
    print("   disable / enable    临时禁用 / 启用断点")
    print("   r <新名>            重命名当前帧的变量")
    print()

    print("④ 不用 pdb 的替代调试方案：")
    print("   - assert：把不变量写成断言，失败立即报错（注意 -O 会禁用）")
    print("   - logging：记录关键变量，比 print 更可控可追溯")
    print("   - traceback：让异常自然传播，用 --tb=long 提升可读性")
    print("   - python -X dev：开启开发模式，显示更多诊断警告")
    print("   - faulthandler：段错误/无响应时自动 dump 栈，比 pdb 更适合线上")
    print()
    print("   带完整 traceback 与栈转储运行：")
    print("     python -X dev -X faulthandler your_script.py")
    print()
    print("   线上无响应时手动转储栈（Linux/Mac）：")
    print("     kill -SIGUSR1 <pid>        # faulthandler 注册的信号")
    print("   线上无响应时用第三方工具：")
    print("     py-spy dump --pid <pid>    # 不需要改代码即可采样")


def main():
    """主入口。"""
    print("=" * 70)
    print("pdb 调试 / traceback 解析 / bug 定位")
    print("=" * 70)
    demo_1_traceback_reading()
    print()
    demo_2_cause_in_traceback()
    print()
    demo_3_pdb_scripted()
    print()
    demo_4_manual_breakpoint()
    print()
    demo_5_common_bugs()
    print()
    demo_6_dis_bytecode()
    print()
    demo_7_pdb_recipes()
    print()
    print("=" * 70)
    print("演示结束：记住「先看 traceback 最后一行，再用 pdb 看上下文」")
    print("=" * 70)


if __name__ == "__main__":
    main()