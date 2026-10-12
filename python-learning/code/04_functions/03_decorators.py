"""
================================================================================
 03_decorators.py  ——  装饰器
================================================================================

【演示的语法点】
 1. 装饰器的本质：func = wrapper(func)，一个"接收函数、返回新函数"的高阶函数
 2. 函数可作为参数传递（高阶函数），装饰器只是它的语法糖
 3. functools.wraps：复制 __name__/__doc__/__qualname__ 等元信息，避免元信息丢失
 4. 带参数的装饰器：需要"三层嵌套"(装饰器工厂 → 包装器 → 函数)
 5. 类装饰器：类也是对象，@dec 直接改写类名绑定
 6. 多装饰器顺序：自下而上应用（等价于 f = d1(d2(f))）
 7. 装饰器计时器：with 语句 + time.perf_counter
 8. functools.lru_cache / cache：记忆化，靠哈希缓存
 9. 参数校验装饰器：装饰器最常见的实际用途 —— 门卫模式
10. 装饰器自身的"透明性"陷阱：被装饰函数的签名会被替换

【预期输出摘要】
 - "本质拆解" 打印出装饰前后的 __name__ 变化，说明 wraps 的必要性
 - "顺序" 小节明确打印 自下而上 的结论
 - "计时" 小节打印两次调用的耗时（会略有差异）
 - "lru_cache" 小节打印命中/未命中信息与 cache_info
================================================================================
"""

import functools
import inspect
import time
from typing import Any, Callable, TypeVar

# 类型变量：让装饰器在类型检查器眼里保持"透明"，不改变原函数的类型
F = TypeVar("F", bound=Callable[..., Any])


# ===== 语法解析 =====
# 【1】最简单的装饰器：揭示本质
#   语法等价关系（务必记住）：
#       @log_time
#       def f(): ...
#   完全等价于：
#       def f(): ...
#       f = log_time(f)
#   注意执行时机：装饰器表达式在【定义时】执行一次，把 f 替换成新函数。
#   函数体依然在【调用时】才执行。
def simple_decorator(func: F) -> F:
    """接收函数，返回一个新函数。这是装饰器的唯一契约。"""
    def wrapper(*args, **kwargs):
        # 用 *args/**kwargs 接收任意实参 → 保证装饰器"透明"，不改变被装饰函数语义
        print(f"    [进入] {func.__name__} 收到参数: args={args}, kwargs={kwargs}")
        result = func(*args, **kwargs)      # 调用真正的原函数
        print(f"    [离开] {func.__name__} 返回: {result!r}")
        return result                       # ★ 必须把返回值透传出去，否则外部拿到 None
    return wrapper


@simple_decorator
def add(a: int, b: int) -> int:
    """两数相加。"""
    return a + b


# ===== 语法解析 =====
# 【2】functools.wraps：解决装饰器的"元信息丢失"问题
#   问题：加装饰后，add.__name__ 变成 'wrapper'，add.__doc__ 变成 None，
#        help()、调试器、日志、框架路由全都会认错函数。
#   解决：@functools.wraps(func) 把原函数的 __module__/__name__/__qualname__/
#        __doc__/__dict__ 等属性复制到 wrapper 上。
#   原理：wraps 自身也是一个【装饰器】，它操作的"被装饰对象"是函数，
#        内部用 update_wrapper + WRAPPER_ASSIGNMENTS 常量做属性搬运。
#   补充：wraps 还设置 wrapper.__wrapped__ = func，
#        这让 inspect.signature 能"穿透"看到原函数签名（并可解包）。
def logging_decorator(func: F) -> F:
    @functools.wraps(func)                 # ← 必须放在 wrapper 的上一行
    def wrapper(*args, **kwargs):
        print(f"  [日志] 调用 {func.__name__}")
        result = func(*args, **kwargs)
        print(f"  [日志] {func.__name__} 执行完毕")
        return result
    return wrapper


@logging_decorator
def compute_area(r: float) -> float:
    """计算圆面积。这个 docstring 只有加 wraps 才能保留。"""
    return 3.14159 * r * r


# ===== 语法解析 =====
# 【3】带参数的装饰器 —— 为什么要"三层嵌套"
#   需求：@retry(max_times=3) 这类"带配置"的装饰器。
#   语法分析：@retry(max_times=3) 等价于 f = retry(max_times=3)(f)
#   也就是说 retry(max_times=3) 必须【先返回一个真正的装饰器】，
#   再由这个装饰器接收 f。所以必须拆成两层：
#       第 1 层 retry(...)  —— 工厂，接收配置，返回装饰器
#       第 2 层 装饰器       —— 接收函数，返回 wrapper
#   这是"装饰器工厂(factory)模式"，和面向对象的"工厂方法"同构。
def retry(times: int = 3, delay: float = 0.01):
    """装饰器工厂：接收配置，返回装饰器。"""
    if times < 1:
        raise ValueError("times 必须 >= 1")   # 配置校验应该在最外层做，尽早失败

    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_exc: Exception | None = None
            for attempt in range(1, times + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as exc:     # 宽泛捕获是有意的：重试器语义
                    last_exc = exc
                    print(f"  [重试] 第 {attempt}/{times} 次失败：{exc!r}")
                    if attempt < times:
                        time.sleep(delay)
            # 全部失败：把最后一次异常抛出去，保持原异常类型
            raise last_exc                   # type: ignore[misc]
        return wrapper
    return decorator


@retry(times=3, delay=0.001)
def flaky_task() -> str:
    """内部有 40% 概率失败的脆弱任务。"""
    if time.perf_counter_ns() % 100 < 40:
        raise RuntimeError("随机故障")
    return "任务成功"


# ===== 语法解析 =====
# 【4】类装饰器
#   语法：@dec 作用在 class 上，等价于 MyClass = dec(MyClass)。
#   语义：类本身也是对象（一个 type 实例），所以任何"接收对象返回对象"的函数
#        都能当类装饰器用。
#   典型用途：给类注入方法、添加属性、实现单例、做注册（如 Django 的 @register）。
#   注意：类装饰器返回【新的对象】时，原类名会被永久替换。
def add_version(cls):
    """类装饰器：为类添加版本号属性，并记录注册日志。"""
    cls.__version__ = "2.0"                # 直接给类对象打属性
    print(f"  [类装饰器] 已装饰类 {cls.__name__}")
    return cls


@add_version
class Database:
    """一个普通的数据库访问类。"""

    def query(self) -> str:
        return "查询完成"


# ===== 语法解析 =====
# 【5】装饰器计时器 —— 用 contextlib 的计时上下文管理器
#   为什么用上下文管理器而不是直接 time.time()：
#     - 异常安全（即使函数抛异常也能记录耗时）
#     - 代码复用（Timer 可用于任何代码块）
#   注意用 perf_counter 而非 time.time：前者是【单调钟】，不受系统时间调整影响，
#   专门用于计时。
class Timer:
    """计时上下文管理器：with Timer() as t: ... 后读 t.elapsed。"""

    # __slots__ 必须【列出所有要用的属性】，少写一个就会在赋值时 AttributeError
    __slots__ = ("label", "elapsed", "_start")   # 节省内存并禁止随意加属性

    def __init__(self, label: str = "代码块") -> None:
        self.label = label
        self.elapsed: float = 0.0

    def __enter__(self) -> "Timer":         # 进入 with 块时调用，返回值绑定给 as 目标
        self._start = time.perf_counter()   # 记录起点
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
        # 返回 False（不写等价于返回 None）→ 异常继续向上抛，不会被吞掉
        self.elapsed = time.perf_counter() - self._start
        return False


def timeit(func: F) -> F:
    """装饰器形式的计时器：包装后自动打印耗时。"""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        with Timer(func.__name__) as t:
            result = func(*args, **kwargs)
        print(f"  [计时] {t.label} 耗时 {t.elapsed:.6f} 秒")
        return result
    return wrapper


@timeit
def slow_sum(n: int) -> int:
    """故意用循环做重活，好让耗时可测量。"""
    return sum(range(n))


# ===== 语法解析 =====
# 【6】functools.lru_cache —— 记忆化装饰器
#   语法：@lru_cache(maxsize=128) 或无参的 @functools.cache
#   原理：以 (args, sorted(kwargs.items())) 为键算哈希，查字典命中则直接返回缓存值，
#        不再执行函数体。这就是"空间换时间"。
#   ★ 前提：函数必须是【纯函数】—— 同样输入永远同样输出、无副作用。
#     有副作用的函数加缓存 = 缓存中毒。
#   易错点：
#     a) 参数必须可哈希（list、dict 不行）；
#     b) maxsize=None 表示无上限，会吃内存；
#     c) 缓存不区分关键字传参与位置传参 —— f(2) 和 f(x=2) 是两个不同的缓存项。
@functools.lru_cache(maxsize=64)
def fib_cached(n: int) -> int:
    """记忆化斐波那契：复杂度从指数级 O(2^n) 降到 O(n)。"""
    if n < 2:
        return n
    return fib_cached(n - 1) + fib_cached(n - 2)


# ===== 语法解析 =====
# 【7】参数校验装饰器 —— 门卫 / 断言前置
#   设计模式：把"使用前置条件"从函数体中抽离，函数体只关心核心逻辑（关注点分离）。
#   实现要点：
#     a) 用 *args/**kwargs 保证通用性；
#     b) 校验失败要抛【有意义的异常类型】而不是 assert（assert 在 -O 模式下会被优化掉）；
#     c) 用 @functools.wraps 保持签名。
def validate_positive(func: F) -> F:
    """门卫装饰器：所有位置实参必须为正数。"""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        for i, value in enumerate(args):
            # 报错的 message 里带上【参数下标】和【期望】，这是可诊断错误的关键
            if not isinstance(value, (int, float)) or value <= 0:
                raise ValueError(f"第 {i + 1} 个位置参数必须是正数，收到 {value!r}")
        for key, value in kwargs.items():
            if not isinstance(value, (int, float)) or value <= 0:
                raise ValueError(f"关键字参数 {key!r} 必须是正数，收到 {value!r}")
        return func(*args, **kwargs)
    return wrapper


@validate_positive
def rectangle_area(width: float, height: float, /, **opts: float) -> float:
    # 注意这里的 / 和 **opts：
    #   / 使 width/height 成为"仅位置"参数 → 装饰器里用** kwargs 传同名关键字会 TypeError，
    #     正好演示"装饰器透传并不会改变原函数的参数约束"；
    #   **opts 让调用方可以附加任意额外选项（如 unit=...），演示装饰器对额外参数的兼容。
    return width * height * opts.get("unit", 1.0)


# ===== 语法解析 =====
# 【8】多装饰器的执行顺序（本节重点易错）
#   书写顺序：
#       @d1
#       @d2
#       def f(): ...
#   等价于：f = d1(d2(f))
#   因此：
#     - 【应用顺序】自下而上：先 d2，再 d1
#     - 【调用顺序】自内而外：先调用 d2 的 wrapper，再 d1 的 wrapper
#   类比：像穿衣服 —— 先套内层（d2），再套外层（d1）。
def trace(tag: str):
    """打印执行轨迹的装饰器工厂，用来观察嵌套顺序。"""
    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            print(f"    → 进入 {tag}")
            result = func(*args, **kwargs)
            print(f"    ← 离开 {tag}")
            return result
        return wrapper
    return decorator


@trace("外层A")
@trace("内层B")
@trace("最内C")
def layered() -> str:
    print("      执行原始函数体")
    return "done"


# ===== 语法解析 =====
# 【设计原理】装饰器为什么必须"三明治"结构？
#   装饰器要满足两个约束：
#     (a) 在【定义时】运行，返回一个替换后的函数 → 需要外层函数
#     (b) 在【调用时】运行，要能包裹原始调用     → 需要内层 wrapper
#   所以标准形态永远是两层；而"带参数"再多一层做配置接收。
#   记忆：配置层 → 装饰器层 → 包装层（自外向内 3 层，最内层才是 wrapper）。


def main() -> None:
    print("=" * 60)
    print("【1】装饰器的本质：func = decorator(func)")
    print("=" * 60)
    # 注意：模块顶部的 add 已经被装饰过了，名字早已被替换成 wrapper。
    # 要对比"装饰前"，必须去看 __closure__ 里的原函数（真实业务代码里应保留原函数引用）
    original = add.__closure__[0].cell_contents if add.__closure__ else None
    print(f"原函数 __name__ = {original.__name__!r}   ← 真正的函数体")
    print(f"装饰后 add.__name__ = {add.__name__!r}   ← 名字被 wrapper 顶替，元信息丢失！")
    print(f"原函数对象：{original}")
    print(f"装饰后对象：{add}")
    print(f"两者相同吗：{original is add}   ← 否，说明装饰器确实换了函数对象")
    print(f"想拿回原函数可以访问：add.__closure__[0].cell_contents")
    print("调用过程：")
    result = add(3, 4)
    print(f"返回值：{result}")
    print("可以看到：先打印『进入/离开』日志，再执行真实计算。")

    print()
    print("=" * 60)
    print("【2】functools.wraps 的作用")
    print("=" * 60)
    print(f"compute_area.__name__ = {compute_area.__name__}          ← 正确保留")
    print(f"compute_area.__doc__  = {compute_area.__doc__}")
    print(f"存在 __wrapped__ 属性：{hasattr(compute_area, '__wrapped__')}")
    # inspect.signature 会沿着 __wrapped__ 逐层穿透，得到"逻辑上真实"的签名
    print(f"inspect.signature 看到：{inspect.signature(compute_area)}")
    print(f"带注解签名：{inspect.signature(compute_area, eval_str=True)}")
    with Timer("圆面积计算") as t:
        area = compute_area(2.0)
    print(f"结果 area = {area:.4f}，耗时 {t.elapsed:.8f}s（装饰器未污染返回值）")

    print()
    print("=" * 60)
    print("【3】带参数的装饰器（装饰器工厂）")
    print("=" * 60)
    print("等价关系：@retry(times=3) f  →  f = retry(times=3)(f)")
    for i in range(1, 4):
        try:
            print(f"第 {i} 次尝试 flaky_task()：{flaky_task()}")
            break
        except RuntimeError as exc:
            print(f"  最终失败：{exc}")
    print("重试装饰器透传的是【原始异常类型】，不会把异常类型搞乱。")

    print()
    print("=" * 60)
    print("【4】类装饰器")
    print("=" * 60)
    print(f"Database.__version__ = {Database.__version__}   ← 由类装饰器注入")
    db = Database()
    print(f"实例调用 query()：{db.query()}")
    print("类装饰器返回什么，类名就绑定为什么；也可以返回全新的类。")

    print()
    print("=" * 60)
    print("【5】装饰器计时器")
    print("=" * 60)
    print(f"slow_sum(1_000_000) = {slow_sum(1_000_000)}")
    print(f"再次调用            = {slow_sum(1_000_000)}")
    print("上下文管理器保证即使抛异常也能记录耗时。")
    print(f"Timer 用了 __slots__，不可随意加新属性：", end=" ")
    tm = Timer("测试")
    try:
        tm.任意属性 = 1
    except AttributeError as exc:
        print(f"AttributeError: {exc}")

    print()
    print("=" * 60)
    print("【6】functools.lru_cache 记忆化")
    print("=" * 60)
    fib_cached.cache_clear()
    t0 = time.perf_counter()
    print(f"fib_cached(80) = {fib_cached(80)}")
    print(f"首次（冷缓存）耗时：{time.perf_counter() - t0:.6f}s")
    t1 = time.perf_counter()
    print(f"再次 fib_cached(80) = {fib_cached(80)}")
    print(f"二次（热缓存）耗时：{time.perf_counter() - t1:.6f}s  ← 快了天文数字倍")
    print(f"缓存统计：{fib_cached.cache_info()}")
    print("★ 前提是纯函数；对有副作用的函数使用会导致缓存中毒。")

    print()
    print("=" * 60)
    print("【7】参数校验装饰器（门卫模式）")
    print("=" * 60)
    print(f"rectangle_area(3, 4) = {rectangle_area(3, 4)}")
    print(f"附加 **opts：rectangle_area(3, 4, unit=2) = "
          f"{rectangle_area(3, 4, unit=2)}   # 额外关键字被装饰器一并校验")
    try:
        # 装饰器用 **kwargs 接收了 unit=-1，但 value<=0 依然会被门卫拦下
        rectangle_area(3, 4, unit=-2)
    except ValueError as exc:
        print(f"附加参数也受校验：ValueError: {exc}")
    try:
        # 绕过装饰器想传非法参数 → 但 width/height 是仅位置参数，TypeError
        rectangle_area(width=3, height=4)
    except TypeError as exc:
        print(f"装饰器不会改变原函数的参数规则：TypeError: {exc}")
    try:
        rectangle_area(3, -1)
    except ValueError as exc:
        print(f"校验拦截：ValueError: {exc}")
    try:
        rectangle_area(3, "四")     # 类型也不对
    except ValueError as exc:
        print(f"类型拦截：ValueError: {exc}")

    print()
    print("=" * 60)
    print("【8】★ 多装饰器顺序：自下而上应用，自内而外调用")
    print("=" * 60)
    print("代码书写顺序：")
    print("  @trace('外层A')   ← 第 1 个应用（最外层）")
    print("  @trace('内层B')   ← 第 2 个应用")
    print("  @trace('最内C')   ← 第 3 个应用（最内层，最先执行）")
    print("  def layered()")
    print("实际运行轨迹：")
    layered()
    print("结论：应用顺序自下而上；调用时最内层 wrapper 先被进入。")


if __name__ == "__main__":
    main()