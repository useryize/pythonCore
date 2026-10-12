# -*- coding: utf-8 -*-
"""
05_context_managers.py —— 上下文管理器（with 语句）

【演示的语法点】
1. with 语句的完整语义展开（__enter__ / __exit__ / 异常传递）
2. contextmanager 装饰器：用 yield 把生成器变成上下文管理器
3. 手写 __enter__/__exit__ 类式实现
4. __exit__ 的三种返回值语义：返回 True=抑制异常 / None或False=传播 / 返回新异常=替换
5. 抑制异常 vs 传播异常 vs 替换异常，三种实测
6. 异常信息如何拿到：sys.exc_info()（必须用参数形式，因为 e 可能为 None）
7. contextlib.suppress：只吞指定异常（比裸 except 更安全）
8. contextlib.redirect_stdout / redirect_stderr：输出重定向
9. contextlib.nullcontext：可空的上下文（写通用代码的必备）
10. contextlib.ExitStack：动态管理多个资源，替代嵌套 with
11. 多个 with 的合并写法：单行 with A() as a, B() as b
12. 异步上下文管理器（async with）与 @asynccontextmanager 的区别
13. 易错点：__exit__ 里 return 会吞掉异常；except 块里再 raise 会覆盖

【预期输出摘要】
- with 展开的伪码对比
- contextmanager 装饰的函数在异常时会收到异常并决定是否 re-raise
- 抑制/传播/替换三种 __exit__ 返回值各自实测
- ExitStack 比 3 层嵌套 with 更扁平
"""
import contextlib
import io
import sys
import time
from types import TracebackType


# ======================================================================
# 语法解析 1：with 语句的完整语义展开
# ======================================================================
#
# 语法规则：
#   with EXPR as VAR:
#       BODY
#
# 等价的伪码（这是理解 with 的唯一正确方式）：
#   mgr = EXPR
#   VAR  = mgr.__enter__()        # 【可能抛异常，此时 __exit__ 不会被调用】
#   try:
#       BODY
#   except BaseException as e:   # 注意是 BaseException，不是 Exception！
#       suppress = mgr.__exit__(type(e), e, e.__traceback__)
#       if not suppress:
#           raise                # 原样抛出，保留原始 traceback
#   else:
#       mgr.__exit__(None, None, None)     # 没异常时也要调用（传三个 None）
#
# 三个要点：
#   1. __enter__ 抛异常 -> __exit__ 【不会】被调用（因为还没进入保护范围）
#   2. 正常路径也会调 __exit__(None, None, None) -> 所以清理代码写在里面总会被执行
#   3. 捕获的是 BaseException -> 连 KeyboardInterrupt / SystemExit 都会先进 __exit__


def demo_with_semantics() -> None:
    print("=" * 68)
    print("【1】with 语句语义与展开")
    print("=" * 68)

    trace: list[str] = []

    class Tracer:
        def __enter__(self) -> "Tracer":
            trace.append("__enter__ 被调用")
            print("  __enter__：进入上下文，返回值绑定给 as 目标")
            return self                    # as 后面的名字就是这个返回值

        def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
            if exc_type is None:
                trace.append("__exit__(None,None,None)")
                print("  __exit__：没有异常，正常清理")
            else:
                trace.append(f"__exit__({exc_type.__name__})")
                print(f"  __exit__：捕获到 {exc_type.__name__}，"
                      f"返回 False -> 不抑制，继续传播")
            return False                     # False/None 都表示「不抑制」

    print("正常路径：")
    with Tracer() as t:
        print(f"  with 体内，t 就是 __enter__ 的返回值: {type(t).__name__}")
    print(f"  退出后 trace = {trace}\n")

    trace.clear()
    print("异常路径：")
    try:
        with Tracer():
            print("  with 体内...")
            raise ValueError("业务异常")
    except ValueError as e:
        print(f"  with 外捕获到: {e}")
    print(f"  trace = {trace}")

    print("\n关键点复盘：")
    print("  1) __exit__ 返回 False/None -> 异常【继续向上传播】")
    print("  2) with 捕获的是 BaseException -> KeyboardInterrupt 也会走 __exit__")
    print("  3) 正常路径也会调 __exit__(None, None, None) -> 清理代码必然执行")

    # 验证第 2 点：BaseException 而非 Exception
    print("\n验证：__exit__ 收到的是 BaseException（SystemExit 也会进来）")
    seen = []

    class CatchBase:
        def __enter__(self):
            return self

        def __exit__(self, t, v, tb):
            seen.append(t.__name__ if t else None)
            return False

    try:
        with CatchBase():
            raise SystemExit(1)
    except SystemExit:
        print(f"  抛 SystemExit 时 __exit__ 收到 exc_type={seen[-1]}")
    print("  ^ 如果 with 内部写的是 `except Exception`，就【抓不到】SystemExit 了")


# ======================================================================
# 语法解析 2：@contextmanager —— 用生成器写上下文管理器
# ======================================================================
#
# 语法规则：
#   @contextlib.contextmanager
#   def func(args):
#       前置代码              # yield 之前 = __enter__
#       yield 资源            # 产出 = as 后拿到的值
#       后置代码              # yield 之后 = __exit__
#
# 转换机制（contextlib._GeneratorContextManager）：
#   __enter__ -> next(gen)                 跑到 yield，返回 yield 的值
#   __exit__  -> gen.throw(异常)  或 gen.close()
#
# 所以「yield 之后收不到异常」是新手最常见的误解 —— 实际会【抛出】进 yield 那一行，
# 于是 yield 后面的代码就在 try/except 里写处理逻辑即可。
#
# 硬性要求：
#   - 函数体必须【恰好 yield 一次】（yield 0 次 -> 报错；yield 2 次 -> 报 RuntimeError）


@contextlib.contextmanager
def managed_resource(name: str):
    """标准模板：前置 -> yield -> 后置。"""
    print(f"    [打开 {name}]")
    try:
        yield f"{name}-handle"           # 交给 with 块使用
        print(f"    [正常关闭 {name}]")
    except Exception as e:
        print(f"    [{name} 因 {type(e).__name__} 异常关闭]")
        raise                            # 必须显式 re-raise 才能让异常继续传播
    finally:
        print(f"    [最终清理 {name}]（一定会执行）")


@contextlib.contextmanager
def timer(label: str):
    """计时上下文管理器：真实项目里最常用的形态之一。"""
    start = time.perf_counter()
    try:
        yield                            # 不用 yield 任何值也可以
    finally:
        # 放finally 里，保证【即使业务抛异常】也记录耗时
        print(f"    [{label}] 耗时 {(time.perf_counter() - start) * 1000:.2f} ms")


def demo_contextmanager() -> None:
    print()
    print("=" * 68)
    print("【2】@contextmanager 装饰器")
    print("=" * 68)

    print("正常路径：")
    with managed_resource("数据库连接") as handle:
        print(f"    业务代码使用 handle = {handle}")

    print("\n异常路径（异常会被【抛进】yield 那一行）：")
    try:
        with managed_resource("文件") as _:
            raise RuntimeError("处理失败")
    except RuntimeError as e:
        print(f"    外层捕获: {e}")
    print("  ^ 注意：一定要在 yield 后写 try/except 并【重新 raise】，")
    print("    否则异常会被静默吞掉 —— 这是 contextmanager 最大的坑")

    print("\n计时器 demo（finally 里统计，异常也不丢数据）：")
    with timer("正常调用"):
        time.sleep(0.01)
    try:
        with timer("异常调用"):
            time.sleep(0.005)
            raise ValueError("boom")
    except ValueError:
        print("    异常已被外层处理，但计时依然被记录")

    # 硬性要求：必须恰好 yield 一次
    print("\n约束验证：函数体必须 yield 恰好一次")

    @contextlib.contextmanager
    def no_yield():
        print("    这个函数体里没有 yield")

    try:
        with no_yield():
            pass
    except (RuntimeError, TypeError) as e:
        print(f"  没有 yield -> {type(e).__name__}: {e}")
        print("  ^ 因为「无 yield」的函数体根本不是生成器，contextmanager 拿不到"
              "可迭代对象（内部就是 next(gen)）")

    @contextlib.contextmanager
    def two_yields():
        yield 1
        yield 2

    cm = two_yields()
    # __enter__ 内部已经执行了第一个 next()，拿到第 1 个 yield 的值
    v1 = cm.__enter__()
    print(f"  第一次 __enter__ 返回 {v1}")
    try:
        # 正常路径下 __exit__ 会 close() 生成器，
        # 而此时生成器里还剩一个 yield -> 触发 RuntimeError
        cm.__exit__(None, None, None)
    except RuntimeError as e:
        print(f"  yield 两次 -> RuntimeError: {e}")
    print("  ^ 规则：__enter__ 之后如果生成器【还没结束】，__exit__ 会报"
          "「generator didn't stop」")


# ======================================================================
# 语法解析 3：手写类式 —— __exit__ 的三种返回值语义
# ======================================================================
#
# 语法规则：def __exit__(self, exc_type, exc_val, exc_tb) -> bool | None
#   __exit__ 的返回值用【真值判断】，不是身份判断（实测见下）：
#     假值（None / False / 0 / ""）-> 异常【传播】（原样 re-raise）
#     真值（True / 1 / 任何对象） -> 异常【被抑制】
#     「返回异常实例」不会替换异常！—— 因为 ValueError 实例是真值 -> 会被【当作 True 抑制】
#     真正替换异常的唯一办法是：在 __exit__ 里【raise 新异常】
#
# 参数含义（务必用参数形式，不要用 except 变量）：
#   exc_type  异常类（没有异常时是 None）
#   exc_val   异常实例
#   exc_tb    traceback 对象


class Suppressor:
    """__exit__ 返回 True -> 抑制异常。"""

    def __init__(self, target_exc: type[BaseException] = Exception) -> None:
        self.target_exc = target_exc

    def __enter__(self) -> "Suppressor":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None and issubclass(exc_type, self.target_exc):
            print(f"    [Suppressor] 抑制了 {exc_type.__name__}，"
                  f"with 块将正常结束")
            return True                     # 抑制
        return False                        # 不该抑制的类型，继续传播


class ErrorReplacer:
    """__exit__ 返回一个【新异常实例】-> 替换原异常。"""

    def __enter__(self) -> "ErrorReplacer":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            return False
        # 关键：必须 raise，而【不能 return】异常实例 —— return 只接受 True/False/None
        # 正确做法是 raise 出去
        raise RuntimeError(f"业务异常 {exc_type.__name__} 已被包装为系统错误") \
            from exc_val


class ConditionalSuppressor:
    """精细化控制：只抑制白名单里的异常，其他照常传播。"""

    def __init__(self, *allowed: type[BaseException]) -> None:
        self.allowed = allowed or (Exception,)

    def __enter__(self) -> "ConditionalSuppressor":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        # sys.exc_info() 在 __exit__ 内部也能拿到当前异常（更简洁的写法之一）
        cur_type = exc_type if exc_type is not None else sys.exc_info()[0]
        if cur_type is not None and issubclass(cur_type, self.allowed):
            print(f"    [白名单] {cur_type.__name__} 在允许列表中，抑制")
            return True
        print(f"    [白名单] {cur_type.__name__ if cur_type else '?'} "
              f"不在允许列表，传播")
        return False


def demo_exit_semantics() -> None:
    print()
    print("=" * 68)
    print("【3】__exit__ 三种返回值语义")
    print("=" * 68)

    print("① 返回 None/False —— 传播异常（默认行为）")
    class Propagate:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False
    try:
        with Propagate():
            raise ValueError("原样抛出")
    except ValueError as e:
        print(f"  外部捕获到: {e}  <- 异常未被改动\n")

    print("② 返回 True —— 抑制异常（外部完全看不到）")
    with Suppressor():
        print("  with 块内：准备抛异常")
        raise KeyError("被吃掉了")
    print("  with 块【正常结束】，继续往下走 <- 异常被抑制\n")

    print("③ 在 __exit__ 里 raise —— 替换异常")
    try:
        with ErrorReplacer():
            raise ValueError("原始业务错误")
    except RuntimeError as e:
        print(f"  外部捕获到: {type(e).__name__}: {e}")
        print(f"  __cause__ = {type(e.__cause__).__name__} <- 原异常被挂为 cause")

    print("\n【实测】__exit__ 返回值的真值表（很多人以为 return 异常实例能替换异常）")
    class Ret:
        def __init__(self, v):
            self.v = v

        def __enter__(self):
            return self

        def __exit__(self, t, val, tb):
            return self.v

    for val in (True, 1, "yes", ValueError("实例"), 0, None, False):
        try:
            with Ret(val):
                raise TypeError("原始异常")
            outcome = "异常被【抑制】（没逃出去）"
        except Exception as e:
            outcome = f"异常【传播】：{type(e).__name__}: {e}"
        print(f"  返回 {val!r:<22} -> {outcome}")
    print("  ^ 结论：判断用的是【真值】不是 `is True`；")
    print("    所以 return ValueError(...) 会【抑制】异常，而不是替换它 ——")
    print("    这是个非常隐蔽的坑。替换异常只能在 __exit__ 里 raise。")

    print("\n④ 白名单式控制（推荐的生产写法）")
    with ConditionalSuppressor(KeyError, IndexError):
        raise KeyError("白名单内 -> 抑制")
    try:
        with ConditionalSuppressor(KeyError):
            raise ZeroDivisionError("白名单外 -> 传播")
    except ZeroDivisionError as e:
        print(f"  外部捕获到: {e}")
    print("\n⚠️ 但注意：suppress 异常会【丢失错误信息】，生产环境请配合 logging 记录。")
    print("   推荐：@contextlib.contextmanager + try/except + logger.exception() + raise")


# ======================================================================
# 语法解析 4：contextlib 工具箱
# ======================================================================
#
# 语法规则：
#   with contextlib.suppress(ExcType): ...        只吞指定异常
#   with contextlib.redirect_stdout(io.StringIO()): ...   重定向 stdout
#   with contextlib.redirect_stderr(...): ...     重定向 stderr
#   with contextlib.nullcontext(default): ...     可空的上下文（统一分支用）
#   with contextlib.ExitStack() as stack: ...     动态资源栈


def demo_contextlib_tools() -> None:
    print()
    print("=" * 68)
    print("【4】contextlib 工具箱")
    print("=" * 68)

    # --- suppress ---
    print("① contextlib.suppress：只吞指定异常")
    with contextlib.suppress(FileNotFoundError):
        # 这个文件不存在，会抛 FileNotFoundError
        open("绝对不存在的文件.txt", encoding="utf-8")
    print("  FileNotFoundError 被吞掉了\n")

    try:
        with contextlib.suppress(FileNotFoundError):
            raise PermissionError("类型不匹配 -> 不吞")
    except PermissionError as e:
        print(f"  白名单外的异常正常传播: {e}")
    print("  ^ 比 `try: ... except: pass` 强：意图明确，且不吞白名单外的错误\n")

    # --- redirect_stdout ---
    print("② contextlib.redirect_stdout：捕获 print 输出")
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        print("这些内容不会出现在终端")
        print("它们被写进了缓冲区")
    captured = buf.getvalue()
    print(f"  缓冲区里捕获到 {len(captured.splitlines())} 行:")
    for line in captured.splitlines():
        print(f"    {line!r}")
    print("  ^ 这是单测里「断言日志/输出内容」的常用手法")
    print(f"  真实场景：把 print 的调试输出定向到日志文件，getvalue() 后写入日志\n")

    # --- redirect_stderr ---
    print("③ contextlib.redirect_stderr：捕获错误输出")
    err_buf = io.StringIO()
    with contextlib.redirect_stderr(err_buf):
        print("这是 stderr 内容", file=sys.stderr)
    print(f"  捕获到 stderr: {err_buf.getvalue()!r}\n")

    # --- nullcontext ---
    print("④ contextlib.nullcontext：可空上下文，消除 if/else 分支")

    def process(data, validator=None):
        # 统一写法：validator 没有传时，用 nullcontext 顶一个「什么都不做」的上下文
        with validator if validator is not None else contextlib.nullcontext():
            return [x for x in data if x > 0]

    print(f"  不传 validator: {process([-1, 2, -3, 4])}")

    class PositiveOnly:
        def __enter__(self):
            return self

        def __exit__(self, t, v, tb):
            return False

    print(f"  传了 validator: {process([-1, 2, -3, 4], PositiveOnly())}")
    print("  ^ nullcontext 的价值：让「可选参数」不必写两份函数体")
    print(f"  nullcontext(default) 可携带值: "
          f"{contextlib.nullcontext('默认值').__enter__()}")


# ======================================================================
# 语法解析 5：ExitStack —— 动态数量的资源
# ======================================================================


@contextlib.contextmanager
def resource(name: str):
    """简化版的资源上下文，用于演示 ExitStack。"""
    print(f"    -> 打开 {name}")
    try:
        yield name
    finally:
        print(f"    <- 关闭 {name}")


def demo_exit_stack() -> None:
    print()
    print("=" * 68)
    print("【5】ExitStack：动态数量的资源管理")
    print("=" * 68)

    # 场景 1：数量固定时的嵌套 with（可读性尚可）
    print("场景1：数量固定 —— 嵌套 with")
    with resource("DB"):
        with resource("缓存"):
            with resource("HTTP"):
                print("      业务逻辑")
    print()

    # 场景 2：数量【动态】 —— 嵌套 with 写不出来，只能用 ExitStack
    print("场景2：数量动态（比如根据配置打开 1~5 个连接）")
    names = ["连接A", "连接B", "连接C"]
    with contextlib.ExitStack() as stack:
        # enter_context 每次压入一个上下文，返回它的 __enter__ 结果
        handles = [stack.enter_context(resource(n)) for n in names]
        print(f"      已打开 {len(handles)} 个: {handles}")
    print("  ^ ExitStack 保证【按相反顺序】关闭（后进先出），与嵌套 with 一致")
    print("    数量为 0 时也不报错，是它的关键优势")

    # 场景 3：ExitStack 的其他注册方法
    print("\n场景3：ExitStack 还能注册回调和文件")
    with contextlib.ExitStack() as stack:
        # callback 注册一个退出时执行的函数（cleanup 惯用法）
        stack.callback(lambda: print("    [callback] 退出时执行"))
        # push 把对象的 __exit__ 压栈（等价 enter_context 但不返回 __enter__ 的值）
        f = stack.enter_context(open(__file__, encoding="utf-8"))
        first_line = f.readline().strip()
        stack.callback(lambda: print(f"    [callback] 首行是: {first_line[:30]}..."))
        print("      文件已打开，读到内容")
    print("  ^ 回调按【注册的逆序】执行：后注册的先执行")


# ======================================================================
# 语法解析 6：单行多上下文与 with 的组合形式
# ======================================================================


def demo_combined_with() -> None:
    print()
    print("=" * 68)
    print("【6】单行多上下文与常见组合写法")
    print("=" * 68)

    print("① 单行写法：with A() as a, B() as b  （等价于两层嵌套）")
    with resource("外层") as outer, resource("内层") as inner:
        print(f"  outer={outer}, inner={inner}")
    print("  ^ 反斜杠续行也能写，但 3.10+ 官方支持【括号包裹】的多上下文，"
          "可读性更好：")
    print("      with (")
    print("          resource('A') as a,")
    print("          resource('B') as b,")
    print("      ):")

    print("\n② 真实项目最常见的组合：文件 + 锁 + 计时")
    import threading
    lock = threading.Lock()
    buf = io.StringIO()
    with contextlib.ExitStack() as stack:
        stack.enter_context(resource("文件"))
        stack.enter_context(lock)
        stack.enter_context(contextlib.redirect_stdout(buf))
        print("  这行被重定向了")
    print(f"  实际缓冲区内容: {buf.getvalue().strip()}")

    print("\n③ 条件性进入上下文：最简洁的写法")
    verbose = False
    # nullcontext 让「可选的调试模式」不需要写 if
    with contextlib.nullcontext() if not verbose else resource("调试模式"):
        print("  业务逻辑（verbose=False 时没有任何额外开销）")
    with contextlib.nullcontext() if not verbose else resource("调试模式"):
        pass
    print("\n④ 易错点清单：")
    print("  ❌ 在 __exit__ 里 except 后不 raise -> 异常被静默吞掉")
    print("  ❌ 用 `except Exception` 期望抓到 KeyboardInterrupt -> 抓不到")
    print("  ❌ 在 __enter__ 里做耗时/可能失败的操作 -> 失败时 __exit__ 不会被调用")
    print("  ❌ 忘记 finally -> 异常路径下资源泄漏")
    print("  ✅ 正确：前置在 yield 前，清理在 finally，异常处理写 try/except + raise")


# ======================================================================
# 语法解析 7：异步上下文管理器
# ======================================================================
#
# 语法规则：
#   class C:
#       async def __aenter__(self): return self
#       async def __aexit__(self, exc_type, exc_val, exc_tb): return False
#       # 用法：async with C() as c: ...
#
#   @contextlib.asynccontextmanager
#   async def f():
#       yield value
#
# 与同步版的区别：__enter__/__exit__ 被换成可等待的 __aenter__/__aexit__。
# 典型场景：异步连接池、异步锁（asyncio.Lock 必须在 async with 里用）、
#           aiohttp 的 ClientSession（必须在 with 里用，否则连接不会关闭）。
#
# 本文件为纯标准库同步演示，异步部分在 10_concurrency/05~07 中展开。


def demo_async_context_note() -> None:
    print()
    print("=" * 68)
    print("【7】异步上下文管理器（语法对照，不实际运行）")
    print("=" * 68)

    print("同步版：")
    print("  class CM:")
    print("      def __enter__(self): ...      -> with CM() as x: ...")
    print("      def __exit__(self, t, v, tb): ...")
    print()
    print("异步版（方法名多一个 a，返回的是协程，必须 await）：")
    print("  class ACM:")
    print("      async def __aenter__(self): ...  -> async with ACM() as x: ...")
    print("      async def __aexit__(self, t, v, tb): ...")
    print()
    print("@asynccontextmanager 装饰器同样支持异步 yield：")
    print("  @contextlib.asynccontextmanager")
    print("  async def conn():")
    print("      s = await get_session()")
    print("      try:")
    print("          yield s")
    print("      finally:")
    print("          await s.close()")
    print()
    print("为什么必须用异步版：")
    print("  - 获取/释放连接是【IO 操作】，需要让出事件循环，不能阻塞")
    print("  - asyncio.Lock / asyncio.Semaphore 只支持 async with")
    print("  - aiohttp.ClientSession 不在 with 里关闭会一直占用连接池")
    print()
    print("本文件演示同步版；异步实战见 10_concurrency/05_async_basics.py")


def main() -> None:
    demo_with_semantics()
    demo_contextmanager()
    demo_exit_semantics()
    demo_contextlib_tools()
    demo_exit_stack()
    demo_combined_with()
    demo_async_context_note()
    print()
    print("=" * 68)
    print("05_context_managers 演示完毕")
    print("核心一句话：with = try/finally 的语法糖 + 「进入/退出」两个钩子。")
    print("=" * 68)


if __name__ == "__main__":
    main()