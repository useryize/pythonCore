# -*- coding: utf-8 -*-
"""
04_functools.py —— functools 函数式工具箱

【演示的语法点】
1. lru_cache / cache：记忆化缓存，maxsize 淘汰策略与命中率的真实权衡
2. partial / partialmethod：偏应用（预置部分参数）
3. reduce：把二元归约累积成多参函数；与 loop 的等价性
4. wraps：保留被装饰函数的元信息（__name__/__doc__/注解），为什么必须写
5. cmp_to_key：把「比较函数」适配成「排序键」，Python 3 已移除 cmp 参数后的官方解法
6. singledispatch：基于【第一个参数类型】的多态分派
7. 多重装饰器组合：叠加顺序 = 套娃顺序（自下而上）
8. 装饰器带参数的三层写法：装饰器本身也是高阶函数
9. reduce 构建「表达式求值器」的完整过程（后移到 06 文件详述）
10. cached_property：把「方法」变成「属性」，惰性 + 自动缓存 + 无需锁（3.8+）
11. 缓存的三大坑：可变对象做 key、缓存了错误结果、内存无限增长

【预期输出摘要】
- lru_cache 的 cache_info() 显示 hits/misses/currsize/maxsize
- 故意传可变 list 做 key 会抛 TypeError（unhashable）
- functools.wraps 前后 __name__/__doc__ 的对比
- singledispatch 按类型分发，同一函数名支持 int/str/list
- 多装饰器叠加的调用顺序实测输出
"""
import functools
import operator
import time


# ======================================================================
# 语法解析 1：lru_cache —— 记忆化
# ======================================================================
#
# 语法规则：
#   @lru_cache(maxsize=None)   无界缓存（等价于 @cache）
#   @lru_cache(maxsize=128)    有限容量，满了按 LRU 淘汰
#   @lru_cache                 不带括号也行（此时 cache 的是「函数对象」本身）
#
# 原理：把「参数元组 -> 结果」存在一个【双向链表 + 字典】里（LRU）；
#       命中时直接返回，未命中时算一次并写入。
#
# 适用前提（必须同时满足）：
#   1. 纯函数：同样的输入永远同样的输出，且不依赖可变全局状态
#   2. 计算成本 >> 哈希成本（否则缓存本身成为瓶颈）
#
# 关键限制：key 是参数的哈希组合，所以【不可变类型】才能做 key。
#          list/dict/set 做 key 会直接抛 TypeError: unhashable type。


@functools.lru_cache(maxsize=128)
def fib(n: int) -> int:
    """经典递归斐波那契 —— 没有缓存是 O(2^n)，有缓存是 O(n)。"""
    return n if n < 2 else fib(n - 1) + fib(n - 2)


@functools.cache                      # 无界缓存的语法糖（3.9+）
def slow_square(x: float) -> float:
    """模拟一个耗时计算（这里用循环代替真实耗时操作）。"""
    acc = 0.0
    for _ in range(1000):
        acc += x ** 0.5
    return acc


@functools.lru_cache(maxsize=2)
def tiny_cache(x: int) -> int:
    return x * 10


def demo_lru_cache() -> None:
    print("=" * 68)
    print("【1】lru_cache / cache 记忆化")
    print("=" * 68)

    fib.cache_clear()                  # 清空缓存，得到干净的统计
    print("场景：斐波那契递归（记忆化的教科书案例）")
    result = fib(30)
    info = fib.cache_info()
    print(f"  fib(30) = {result}")
    print(f"  cache_info() = {info}")
    print(f"  hits={info.hits} misses={info.misses} "
          f"命中率={info.hits / (info.hits + info.misses):.1%}")
    print(f"  实际缓存条目数={info.currsize}（maxsize=128，本次没触发淘汰）")

    # 缓存带来的加速实测
    fib.cache_clear()
    t0 = time.perf_counter()
    fib(25)
    cold = time.perf_counter() - t0

    fib.cache_clear()
    fib(25)                          # 预热
    t0 = time.perf_counter()
    fib(25)
    warm = time.perf_counter() - t0
    print(f"\n  冷启动 fib(25): {cold * 1000:.2f} ms")
    print(f"  命中缓存 fib(25): {warm * 1000:.2f} ms  （快 {cold / warm:.0f} 倍）")

    # 有限缓存的 LRU 淘汰
    print("\n场景：maxsize=2 的 LRU 淘汰（观察 currsize 不超过 2）")
    tiny_cache.cache_clear()
    for v in (1, 2, 3):
        tiny_cache(v)
        print(f"  调用 tiny_cache({v}) 后: {tiny_cache.cache_info()}")
    print(f"  ^ maxsize=2 时缓存条目数被限制为 {tiny_cache.cache_info().currsize}")

    # 坑1：可变对象不能做 key
    print("\n坑1：可变对象做 key 直接报 unhashable")
    try:
        fib([1, 2])                   # type: ignore[arg-type]
    except TypeError as e:
        print(f"  fib([1,2]) -> TypeError: {e}")
    print("  解法：把 key 转成元组 fib(tuple([1,2]))，或先算好再传入")

    # 坑2：哈希碰撞会「误命中」
    print("\n坑2：注意 1.0 == 1 且 hash 相同 -> 缓存会误命中")
    fib.cache_clear()
    fib(10)
    print(f"  fib(10) 之后调用 fib(10.0): {fib(10.0)}  "
          f"（命中了 fib(10) 的缓存！）")
    print("  如果你的函数【真的】区分 int/float，就要把类型编进 key")

    # 坑3：缓存不会自动失效
    print("\n坑3：lru_cache 【不会】因为被装饰函数内部状态变化而失效")
    print("  所以：缓存只适合纯函数；依赖数据库/配置/时间的函数【绝不能】直接缓存。")


# ======================================================================
# 语法解析 2：partial —— 偏应用
# ======================================================================
#
# 语法规则：new_func = partial(func, *args, **keywords)
#   把 func 的一部分参数【提前绑定】，返回一个新可调用对象。
#   调用 new_func(其余参数) 等价于 func(*args, 其余参数, **keywords)
#
# 用途：
#   - 适配不同签名（把 func(a,b,c) 变成适配 handler(msg) 的形式）
#   - 简化调用（固定「会话/租户/trace_id」这类上下文参数）
#   - 配合 map/filter：partial(f, 固定参数) 直接进 map


def send_request(method: str, url: str, *, timeout: float = 5.0,
                 retries: int = 1, **extra) -> str:
    """模拟发请求：method/url 必填，timeout/retries 是关键字参数。"""
    return (f"{method} {url} timeout={timeout} retries={retries} "
            f"extra={extra}")


def demo_partial() -> None:
    print()
    print("=" * 68)
    print("【2】partial 偏应用")
    print("=" * 68)

    # 绑定最常用的 method，把「读接口」固定下来
    get = functools.partial(send_request, "GET")
    print("场景：把固定的 method 提前绑定")
    print(f"  get('/api/users')            -> {get('/api/users')}")
    print(f"  get('/api/users', timeout=1) -> {get('/api/users', timeout=1)}")
    print(f"  ^ timeout 是 keyword-only，必须在调用时【按名】传")

    # 绑定上下文参数：每个请求都要带 trace_id
    def traced(trace_id: str, url: str) -> str:
        return f"[trace={trace_id}] {url}"

    for tid in ("t-001", "t-002"):
        # 每次生成一个「已绑定 trace_id」的新函数
        request = functools.partial(traced, tid)
        print(f"  {request('/api/orders')}")

    # partial + map：这是最优雅的组合
    print("\n场景：partial 直接进 map（省掉 lambda）")
    urls = ["/a", "/b", "/c"]
    post = functools.partial(send_request, "POST")
    for r in map(post, urls):
        print(f"  {r}")
    print("  ^ 等价于 map(lambda u: post(u), urls)，但少一层 lambda 调用开销")

    # partial 的属性
    print("\npartial 对象本身是可调用对象，且可查看其信息：")
    print(f"  func     = {get.func.__name__}")
    print(f"  args     = {get.args}")
    print(f"  keywords = {get.keywords}")
    print(f"  可调用?  {callable(get)}")

    # partialmethod：类方法版本
    class Repository:
        def __init__(self, conn) -> None:
            self.conn = conn

        def _query(self, sql: str, *, timeout: float) -> str:
            return f"[conn={id(self.conn) & 0xFFFF}] {sql} (t={timeout})"

        # partialmethod 让【每个实例调用时】自动带上 self
        quick = functools.partialmethod(_query, timeout=1.0)

    print("\npartialmethod（类里的偏应用，会自动带 self）：")
    repo = Repository("fake-conn")
    print(f"  repo.quick('SELECT 1')        -> {repo.quick('SELECT 1')}")
    print(f"  repo._query('SELECT 1', timeout=9) -> "
          f"{repo._query('SELECT 1', timeout=9)}")
    print("  ^ partialmethod 让方法在类层面就固定一部分参数，比在 __init__ 里"
          "存 partial 更清爽")


# ======================================================================
# 语法解析 3：reduce —— 归约
# ======================================================================
#
# 语法规则：functools.reduce(function, iterable[, initializer])
#   function 必须是【二元】函数：function(acc, x) -> acc'
#   等价的循环：
#       acc = initializer
#       for x in iterable:
#           acc = function(acc, x)
#       return acc
#
# 注意：reduce 是【左折叠】（left fold），有初始值时长度 n 的序列会调用 n 次。
#       无初始值时会【取第一个元素作为初始 acc】，只调用 n-1 次，且要求序列非空。


def demo_reduce() -> None:
    print()
    print("=" * 68)
    print("【3】reduce 左折叠")
    print("=" * 68)

    nums = [1, 2, 3, 4, 5]

    # 手写循环 vs reduce 的等价性
    manual = 0
    for n in nums:
        manual = manual + n

    with_init = functools.reduce(operator.add, nums, 0)
    no_init = functools.reduce(operator.add, nums)
    print(f"数据 {nums}")
    print(f"  手写循环求和        : {manual}")
    print(f"  reduce(..., 初始0)  : {with_init}")
    print(f"  reduce(...) 无初始值: {no_init}   <- 用 nums[0]=1 当初始 acc")
    print(f"  三者一致: "
          f"{manual == with_init == no_init}")

    # 空序列 + 有初始值 vs 无初始值
    print("\n空序列的差异（这是常见线上 Bug）：")
    print(f"  reduce(add, [], 0)   -> {functools.reduce(operator.add, [], 0)}  安全")
    try:
        functools.reduce(operator.add, [])
    except TypeError as e:
        print(f"  reduce(add, [])     -> TypeError: {e}")

    # 常用 operator 组合
    print("\n常用组合（比 lambda 快，因为是 C 函数）：")
    words = ["apple", "banana", "cherry"]
    print(f"  连接:  reduce(operator.add, {words}) "
          f"-> {functools.reduce(operator.add, words)!r}")
    print(f"  求积:  reduce(operator.mul, {nums}) "
          f"-> {functools.reduce(operator.mul, nums)}")
    print(f"  最大:  reduce(max, {nums}) -> {functools.reduce(max, nums)}")
    matrix = [[1, 2], [3, 4], [5, 6]]
    # 矩阵转置：reduce(lambda a, b: [x + y for x, y in zip(a, b)], ...)
    transposed = functools.reduce(lambda acc, row: [a + b for a, b in zip(acc, row)],
                                  matrix[1:], matrix[0])
    print(f"  矩阵转置 {matrix} -> {transposed}")
    print("  ^ 「列表相加 = zip 后逐对相加」，reduce 让这个模式极简")

    # 与 functools.reduce 配合实现「按字段聚合」
    transactions = [("a", 10), ("b", 20), ("a", 5), ("c", 3), ("a", 1)]
    totals = functools.reduce(
        lambda acc, item: {**acc, item[0]: acc.get(item[0], 0) + item[1]},
        transactions, {})
    print(f"\n按 key 聚合（注意这个 reduce 写法是 O(n²)，仅用于演示）: {totals}")
    print("  ^ 生产代码请用 collections.defaultdict(int)，才是 O(n)")


# ======================================================================
# 语法解析 4：wraps —— 保留函数元信息
# ======================================================================
#
# 语法规则：
#   @functools.wraps(target)
#   def wrapper(*args, **kwargs):
#       return func(*args, **kwargs)
#
# 为什么必须写：
#   装饰器返回的是 wrapper 本身，不写 wraps 的话：
#       func.__name__ == 'wrapper'      -> 日志/报错全显示错名字
#       func.__doc__  == wrapper 的文档 -> 丢失
#       func.__annotations__ == {}      -> 类型信息全丢，mypy 直接罢工
#       inspect.signature(func) 会暴露 *args, **kwargs -> 签名失真
#
# 面试高频：「装饰器怎么写才规范」= 带参数 + wraps + 返回泛型。


def bad_decorator(func):
    """❌ 反面教材：没有 wraps，函数元信息全丢。"""
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)
    return wrapper


def good_decorator(func):
    """✅ 正面教材：@wraps(func) 把原函数的元信息复制到 wrapper。"""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)
    return wrapper


@bad_decorator
def sample_api(user_id: int, verbose: bool = False) -> str:
    """查询用户信息的 API。"""
    return f"user:{user_id} verbose={verbose}"


@good_decorator
def sample_api_good(user_id: int, verbose: bool = False) -> str:
    """查询用户信息的 API。"""
    return f"user:{user_id} verbose={verbose}"


def demo_wraps() -> None:
    import inspect

    print()
    print("=" * 68)
    print("【4】functools.wraps —— 为什么每个装饰器都要写")
    print("=" * 68)

    print(f"{'属性':<18}{'没有 wraps':<34}{'有 wraps'}")
    print("-" * 86)
    print(f"{'__name__':<18}{sample_api.__name__:<34}{sample_api_good.__name__}")
    print(f"{'__doc__':<18}{str(sample_api.__doc__):<34}"
          f"{sample_api_good.__doc__}")
    print(f"{'__annotations__':<18}{str(sample_api.__annotations__):<34}"
          f"{str(sample_api_good.__annotations__)}")
    print(f"{'signature':<18}{str(inspect.signature(sample_api)):<34}"
          f"{str(inspect.signature(sample_api_good))}")
    print(f"{'__qualname__':<18}{sample_api.__qualname__:<34}"
          f"{sample_api_good.__qualname__}")

    print("\n实际调用结果一致：")
    print(f"  sample_api(1)      -> {sample_api(1)}")
    print(f"  sample_api_good(1) -> {sample_api_good(1)}")
    print("\n影响：没有 wraps 时，日志里会全是 'wrapper'，")
    print("      pydantic/FastAPI 依赖签名的框架会直接拒绝注册。")

    # wraps 也能自定义自己的元信息
    def with_version(version: str):
        def deco(func):
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                return func(*args, **kwargs)
            wrapper.__version__ = version      # 附加自定义属性
            return wrapper
        return deco

    @with_version("v2.1")
    def api_v2() -> str:
        return "ok"

    print(f"\n自定义元信息: api_v2.__name__={api_v2.__name__}, "
          f"__version__={api_v2.__version__}")


# ======================================================================
# 语法解析 5：cmp_to_key —— 把比较函数变回排序键
# ======================================================================
#
# 语法规则：key = functools.cmp_to_key(my_cmp)
#   my_cmp(a, b) -> -1 (a排前面) / 0 (相等) / 1 (a排后面)
#   sorted(data, key=cmp_to_key(my_cmp))
#
# 历史背景：Python 2 的 list.sort(cmp=fn) 在 Python 3 被移除，
#           因为 cmp 要用 Python 写、返回 int，【无法被 C 加速】；
#           而 key 只需一次「取键」函数调用，之后全是 C 层比较。
#
# 所以现代做法是：用 key 而不是 cmp_to_key。cmp_to_key 只在「必须三方比较」时用。


def demo_cmp_to_key() -> None:
    print()
    print("=" * 68)
    print("【5】cmp_to_key：三方比较的适配器")
    print("=" * 68)

    people = [
        {"name": "张三", "age": 30, "score": 85},
        {"name": "李四", "age": 25, "score": 95},
        {"name": "王五", "age": 30, "score": 70},
    ]

    def cmp_by_score_then_age(a, b) -> int:
        """先按分数降序；分数相同则按年龄升序。"""
        if a["score"] != b["score"]:
            return -1 if a["score"] > b["score"] else 1    # 分数降序
        return -1 if a["age"] < b["age"] else 1            # 年龄升序

    by_cmp = sorted(people, key=functools.cmp_to_key(cmp_by_score_then_age))
    print("用 cmp_to_key（支持任意比较逻辑）：")
    for p in by_cmp:
        print(f"  {p['name']} 分数={p['score']} 年龄={p['age']}")

    # 现代推荐写法：key 返回元组，天然支持多级排序且能被 C 加速
    by_key = sorted(people, key=lambda p: (-p["score"], p["age"]))
    print("\n现代推荐：key 返回元组（负号实现降序）")
    for p in by_key:
        print(f"  {p['name']} 分数={p['score']} 年龄={p['age']}")

    print(f"\n结果一致: {[p['name'] for p in by_cmp] == [p['name'] for p in by_key]}")

    # 三方比较才能表达的场景：自定义「距离」
    def cmp_cyclic(a: str, b: str) -> int:
        """按字母在 "cab" 这个环上的位置排序（a 在 c 前，c 在 a 前）"""
        order = "cab"
        pa, pb = order.index(a), order.index(b)
        return -1 if pa < pb else (1 if pa > pb else 0)

    print(f"\ncmp_to_key 的不可替代场景（环状顺序）:")
    print(f"  sorted('abc', key=cmp_to_key(cmp_cyclic)) = "
          f"{sorted('abc', key=functools.cmp_to_key(cmp_cyclic))}")
    print("  ^ 这种关系不是【全序】（a<b 但 b>a 的依据不是简单大小），用 key 表达不了")
    print("\n面试怎么问：Python 3 为什么砍掉 sort(cmp=...)？")
    print("答：cmp 必须用 Python 写且返回 int，sort 的比较阶段无法进入 C 循环；")
    print("    key 函数只调用 n 次拿到「键」，之后 n log n 次比较全在 C 里，快数倍。")


# ======================================================================
# 语法解析 6：singledispatch —— 基于类型的多态分发
# ======================================================================
#
# 语法规则：
#   @functools.singledispatch
#   def func(arg): ...            # 默认实现（必须是第一个，名为 func 本身）
#
#   @func.register
#   def _(arg: int): ...         # 按类型注册
#   @func.register
#   def _(arg: str): ...
#   func.register(list)           # 另一种写法：直接注册
#
# 分派规则：
#   1. 精确类型匹配
#   2. 走 MRO（继承）找最近的实现
#   3. 都找不到 -> 用默认实现
#
# 设计目的：把「if isinstance(arg, X): ...」的散落判断收敛到一个函数里。
#          常用于「格式化输出」这类函数：同一逻辑，不同类型不同行为。


@functools.singledispatch
def serialize(value) -> str:
    """默认实现：未知类型走这里。"""
    return f"<{type(value).__name__}: {value!r}>"


@serialize.register(int)
def _serialize_int(value: int) -> str:
    # if-else 表达式替代 if/else，输出二进制位宽（0 单独处理）
    return (f"INT:{value}（{value.bit_length()} 位二进制）"
            if value.bit_length() else "INT:0（无二进制位）")


@serialize.register(float)
def _serialize_float(value: float) -> str:
    return f"FLOAT:{value:.3f}"


@serialize.register(str)
def _serialize_str(value: str) -> str:
    return f"STR[utf-8 长度={len(value.encode('utf-8'))}]:{value!r}"


@serialize.register(list)
def _serialize_list(value: list) -> str:
    return f"LIST[长度={len(value)}]:{serialize(value[0]) if value else '空'}"


# 精确类型 vs 子类：singledispatch 对子类会沿 MRO 查找
class MyList(list):
    pass


def demo_singledispatch() -> None:
    print()
    print("=" * 68)
    print("【6】singledispatch 基于类型的多态")
    print("=" * 68)

    print("场景：同一份「序列化」逻辑，按参数类型走不同实现")
    samples = [42, 3.14159, "中文abc", [1, 2, 3], (1, 2), {"k": 1}, None]
    for s in samples:
        print(f"  {type(s).__name__:<6} -> {serialize(s)}")

    print("\n分派表（registry）：")
    for t, impl in sorted(serialize.registry.items(),
                          key=lambda kv: getattr(kv[0], '__name__', str(kv[0]))):
        name = getattr(t, "__name__", str(t))
        print(f"  {name:<10} -> {impl.__name__}")

    print(f"\n子类的行为：")
    sub = MyList([9, 9])
    print(f"  MyList 是 list 的子类 -> {serialize(sub)}")
    print("  ^ singledispatch 沿 MRO 找最近的注册实现，所以命中了 list 版本")
    print("\n面试怎么问：singledispatch 和 isinstance 分支有什么区别？")
    print("答：(1) 它把分散的 isinstance 判断【收敛】到一处；(2) 支持第三方为自己的")
    print("    类型【注册】实现（鸭子类型可扩展）；(3) 缺点是分发发生在【调用时】，")
    print("    不是编译/导入时，且第一个参数的调用方看不到具体实现。")


# ======================================================================
# 语法解析 7：多重装饰器组合与调用顺序
# ======================================================================
#
# 语法规则：
#   @outer
#   @inner
#   def f(): ...
#   等价于 f = outer(inner(f))
#
# 所以「调用时」的执行顺序是【自外向内】进入，自内向外返回：
#   outer 的前置 -> inner 的前置 -> f 本体 -> inner 的后置 -> outer 的后置
#   （像剥洋葱：最外层最先开始、最后结束）
#
# 装饰顺序的语义（面试常问）：
#   @log 写在 @cache 【上面】 -> 日志会打印「缓存命中」的所有调用（含命中），
#                               但看不到缓存内部细节
#   @cache 写在 @log 【上面】 -> 缓存【整体】包住日志，只有未命中才打日志


def make_tracer(name: str):
    """返回一个「带名字的追踪装饰器」—— 装饰器的工厂函数。"""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            print(f"  -> 进入 [{name}]")
            result = func(*args, **kwargs)
            print(f"  <- 离开 [{name}] 结果={result}")
            return result
        return wrapper
    return decorator


def demo_decorator_stack() -> None:
    print()
    print("=" * 68)
    print("【7】多重装饰器：调用顺序与组合")
    print("=" * 68)

    @make_tracer("计时")
    @make_tracer("日志")
    def business(a: int, b: int) -> int:
        return a + b

    print("定义：@计时 在上，@日志 在下  =>  business = 计时(日志(business))")
    print("调用：")
    result = business(3, 4)
    print(f"结果 = {result}")
    print("顺序解读：最外层『计时』先进入，『日志』后进入，business 最后执行。")

    print("\n等价的手写形式（完全不看语法糖）：")
    def business_raw(a: int, b: int) -> int:
        return a + b
    step1 = make_tracer("日志")(business_raw)
    step2 = make_tracer("计时")(step1)
    print("手写等价：")
    step2(3, 4)

    # 缓存装饰器的顺序对比
    calls = {"n": 0}

    @functools.lru_cache(maxsize=None)
    def cached_task(x: int) -> int:
        calls["n"] += 1
        return x * 2

    def counted_task(x: int) -> int:
        calls["n"] += 1
        return x * 2

    @make_tracer("缓存层-外")
    @functools.lru_cache(maxsize=None)
    def task(x: int) -> int:
        calls["n"] += 1
        return x * 2

    calls["n"] = 0
    for v in (1, 1, 2):
        task(v)
    print(f"\n缓存装饰器在【内】：命中后不会触发外层追踪")
    print(f"  实际函数被调用 {calls['n']} 次（传了 3 个参数，只有 2 个是新的）")

    print("\n装饰器栈的三条实践准则：")
    print("  1) 顺序 = 「谁先拿到调用」，写之前先想清楚日志要打几次")
    print("  2) 带参数的装饰器必须写三层：factory(参数) -> decorator(func) -> wrapper(...)")
    print("  3) 每个装饰器都必须 @wraps，否则 __name__ 会被覆盖成 'wrapper'")


# ======================================================================
# 语法解析 8：cached_property —— 惰性缓存属性
# ======================================================================
#
# 语法规则：@functools.cached_property
#          def name(self): ...     # 无参数，只能用于【类】的实例
#
# 原理：第一次访问时执行方法并把结果写进实例 __dict__（同名 key），
#       之后属性查找直接命中 __dict__，【不再执行方法】。
#       因为写的是实例自己的字典，所以【线程安全】（不同于类级单例缓存）。
#
# 适用：昂贵但不变的派生属性（如 ORM 模型的关联查询结果）


class UserProfile:
    """演示 cached_property 的典型场景：ORM 关联对象惰性加载。"""

    def __init__(self, name: str) -> None:
        self.name = name
        self.load_count = 0

    @functools.cached_property
    def permissions(self) -> set:
        # 模拟一次昂贵的数据库查询
        self.load_count += 1
        print(f"    [DB] 查询 {self.name} 的权限（耗时操作）")
        return {f"{self.name}:read", f"{self.name}:write"}

    def _slow_method(self) -> str:
        self.load_count += 1
        return f"{self.name}-computed"


def demo_cached_property() -> None:
    print()
    print("=" * 68)
    print("【8】cached_property 惰性缓存属性")
    print("=" * 68)

    u = UserProfile("alice")
    print("创建对象后（还没访问属性）：")
    print(f"  u.load_count = {u.load_count}")
    print(f"  'permissions' in u.__dict__ = {'permissions' in u.__dict__}")

    print("\n第 1 次访问 u.permissions：")
    first = u.permissions
    print(f"  结果 = {first}")

    print("\n第 2、3 次访问（已缓存，不再查库）：")
    second = u.permissions
    third = u.permissions
    print(f"  三次访问是同一对象吗: {first is second is third}")
    print(f"  实际查库次数 = {u.load_count}")
    print(f"  'permissions' in u.__dict__ = {'permissions' in u.__dict__} "
          f"（已写入实例字典）")

    print("\n与 property 的对比（关键：描述符的类型决定缓存能否生效）：")
    # 描述符分两类：
    #   数据描述符（有 __set__）-> 【优先于】实例 __dict__，普通 property 是这一类
    #   非数据描述符（无 __set__）-> 实例 __dict__ 优先，所以缓存能生效
    # cached_property 属于【后者】，这正是它「把结果写进实例字典后就不再执行方法」的原因。
    print(f"  cached_property 是数据描述符吗: "
          f"{hasattr(UserProfile.permissions, '__set__')}  "
          f"（False = 非数据描述符 -> 实例字典优先 -> 缓存生效）")
    print(f"  普通 property 是数据描述符吗   : "
          f"{hasattr(property(lambda s: 0), '__set__')}  "
          f"（True = 数据描述符 -> 每次访问都执行 getter）")
    print(f"  类型: {type(UserProfile.permissions).__name__}")
    print("  ^ 因此普通 property 想缓存必须【自己】写缓存；")
    print("    cached_property 自动缓存，且缓存在实例 __dict__，天然线程安全。")

    print("\n删除缓存（重新加载）：")
    del u.permissions
    print(f"  del 后 'permissions' in __dict__ = "
          f"{'permissions' in u.__dict__}")
    _ = u.permissions
    print(f"  再次访问后查库次数 = {u.load_count}")


def main() -> None:
    demo_lru_cache()
    demo_partial()
    demo_reduce()
    demo_wraps()
    demo_cmp_to_key()
    demo_singledispatch()
    demo_decorator_stack()
    demo_cached_property()
    print()
    print("=" * 68)
    print("04_functools 演示完毕")
    print("核心一句话：functools 是「把函数当数据处理」的标准库工具箱。")
    print("=" * 68)


if __name__ == "__main__":
    main()