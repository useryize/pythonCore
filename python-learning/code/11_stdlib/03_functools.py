"""
================================================================================
 03_functools.py  ——  functools：函数的高阶工具箱
================================================================================

【演示的语法点】
 1. lru_cache：记忆化缓存，maxsize / typed / cache_info / cache_clear
 2. cache：无上限版本的 lru_cache(maxsize=None)（3.9+）
 3. partial / partialmethod：冻结部分参数
 4. reduce：二元函数归约（初版放在 operator 里，后迁入 functools）
 5. wraps：装饰器元信息保留，WRAPPER_ASSIGNMENTS / UPDATES
 6. cmp_to_key：用比较函数配合排序（functools 最后的纯 Python 工具）
 7. singledispatch：函数泛型（按【第一个参数的类型】分派）
 8. total_ordering：根据单个比较方法补齐其余
 9. 实战：递归优化、连接池、命令注册表、LRU 统计

【预期输出摘要】
 - "lru_cache" 小节：cache_info() 输出 hits/misses 与命中率
 - "singledispatch" 小节：同一个函数按参数类型返回不同结果
 - "cmp_to_key" 小节：自定义排序规则的输出顺序
================================================================================

"""

from __future__ import annotations

import functools
import time
from functools import cache, cmp_to_key, lru_cache, partial, partialmethod, reduce, singledispatch, total_ordering, wraps


# ===== 语法解析 =====
# 【1】lru_cache：把"算过的结果"存下来，避免重复计算
#   语法规则：@lru_cache(maxsize=128, typed=False)
#     - maxsize=None 表示【无上限缓存】；给整数则用 LRU 淘汰
#     - typed=True 时区分参数类型（f(1) 与 f(1.0) 视为不同键）
#   实现原理：装饰器把原函数换成"包装函数"，内部用 dict + 双向链表
#             记录 key → value，调用时先查缓存，命中直接返回。
#   设计意图：把"缓存"这一横切关注点从业务代码中抽离。
#   ⚠ 坑：
#     1. 只能缓存【可哈希】的参数（列表不行，会 TypeError）
#     2. 参数顺序不同算不同键：f(1,2) 与 f(2,1) 不共享缓存
#     3. 不能手动改可变参数后又期望缓存失效
def demo_lru_cache() -> None:
    calls = 0

    @lru_cache(maxsize=128)
    def slow_pow(base: int, exp: int) -> int:
        """计算幂，故意用循环模拟耗时。"""
        nonlocal calls
        calls += 1
        result = 1
        for _ in range(exp):
            result *= base
        return result

    print(f"  slow_pow(2, 10) = {slow_pow(2, 10)}")
    print(f"  slow_pow(2, 10) = {slow_pow(2, 10)}   ← 第二次直接命中缓存")
    print(f"  实际执行次数 calls = {calls}   ← 只算了 1 次")
    print(f"  缓存信息：{slow_pow.cache_info()}")

    # cache_clear 清空后又要重算
    slow_pow.cache_clear()
    slow_pow(2, 10)
    print(f"  cache_clear() 后再调用，calls = {calls}")

    # 缓存原函数：访问 .__wrapped__ 可拿到未装饰版本
    print(f"  .__wrapped__ 是原函数：{slow_pow.__wrapped__.__name__}")

    # typed=True：区分 int 与 float
    @lru_cache(maxsize=None, typed=True)
    def identity(x: object) -> object:
        return x

    identity(1)
    identity(1.0)
    print(f"  typed=True 时 1 与 1.0 分别缓存：{identity.cache_info()}")
    print(f"  未使用的缓存键（内部状态）：{list(identity.cache_parameters().items())}")

    # 实战：斐波那契递归 —— 朴素写法是指数级复杂度，加上缓存变线性
    @lru_cache(maxsize=None)
    def fib(n: int) -> int:
        if n < 2:
            return n
        return fib(n - 1) + fib(n - 2)

    t0 = time.perf_counter()
    result = fib(40)                       # 无缓存时几乎跑不完
    t_with = time.perf_counter() - t0

    def fib_plain(n: int) -> int:         # 无缓存版本，仅算 n=25 做对比
        if n < 2:
            return n
        return fib_plain(n - 1) + fib_plain(n - 2)

    t0 = time.perf_counter()
    fib_plain(25)
    t_without = time.perf_counter() - t0

    print(f"  fib(40) 带缓存 = {result}，耗时 {t_with * 1000:.3f} ms")
    print(f"  fib(25) 无缓存耗时 {t_without * 1000:.3f} ms  ← n 大 15 倍却快得多")
    print(f"  fib 缓存信息：{fib.cache_info()}")


# ===== 语法解析 =====
# 【2】cache：lru_cache(maxsize=None) 的语法糖（3.9+）
#   语法规则：@cache  等价于  @lru_cache(maxsize=None)
#   设计意图：既然"缓存全部"是更常见的诉求，就给它一个更短的名字。
def demo_cache() -> None:
    @cache
    def parse_config(text: str) -> dict[str, str]:
        """模拟解析配置（耗时操作）。"""
        time.sleep(0.001)                  # 故意加延迟，让缓存效果可见
        return dict(line.split("=", 1) for line in text.splitlines())

    raw = "host=localhost\nport=8080"
    t0 = time.perf_counter()
    parse_config(raw)
    cold = time.perf_counter() - t0

    t0 = time.perf_counter()
    for _ in range(1000):                 # 重复调用 1000 次
        parse_config(raw)
    hot = time.perf_counter() - t0

    print(f"  首次调用 {cold * 1000:.3f} ms；随后 1000 次共 {hot * 1000:.3f} ms")
    print(f"  缓存命中后每次约 {(hot / 1000) * 1e6:.2f} μs，比首次快约 "
          f"{cold / (hot / 1000):.0f} 倍")
    print(f"  {parse_config.cache_info()}")
    parse_config.cache_clear()
    print(f"  clear 后：{parse_config.cache_info()}")


# ===== 语法解析 =====
# 【3】partial / partialmethod：参数预绑定
#   语法规则：partial(func, *args, **keywords)
#     - 冻结【前面的位置参数】和【任意关键字参数】
#     - 调用 partial 对象时只需补剩下的参数
#   partialmethod：用在类里，自动把 self 补到最前
#   设计意图：替代 lambda 的"函数式闭包"，更快（无闭包帧开销）且可 pickle。
def demo_partial() -> None:
    def connect(host: str, port: int, *, timeout: float = 1.0, ssl: bool = False) -> str:
        return f"连接 {host}:{port} timeout={timeout} ssl={ssl}"

    # 冻结 host，之后只需传 port
    conn_db = partial(connect, "db.internal")
    print(f"  conn_db(5432) = {conn_db(5432)}")

    # 再叠加关键字参数
    conn_slow = partial(connect, "cache.internal", timeout=5.0)
    print(f"  conn_slow(6379) = {conn_slow(6379)}")
    # 调用时仍可覆盖被冻结的关键字
    print(f"  conn_slow(6379, timeout=9.9) = {conn_slow(6379, timeout=9.9)}   ← 覆盖生效")

    # 用于 map：把"二元操作"变成可 map 的一元调用（bound 部分参数后只剩 1 个参数）
    def tag(name: str, tagname: str) -> str:
        return f"<{tagname}>{name}</a>"

    make_span = partial(tag, tagname="b")        # 冻结关键字，只剩 name 一个参数
    result_html = list(map(make_span, ["标题", "正文"]))
    print(f"  map(partial(...)) = {result_html}")
    print(f"  三者 func 属性相同：{conn_db.func is connect}")

    # partialmethod：类中预绑定 self
    class Database:
        def __init__(self, dsn: str) -> None:
            self.dsn = dsn

        def _execute(self, sql: str, *, fetch: bool = False) -> str:
            return f"[{self.dsn}] 执行: {sql} (fetch={fetch})"

        run = partialmethod(_execute)                      # 冻结 self
        run_fast = partialmethod(_execute, fetch=True)     # 冻结 self + fetch

    db = Database("mysql://localhost")
    print(f"  db.run('SELECT 1') = {db.run('SELECT 1')}")
    print(f"  db.run_fast('SELECT 1') = {db.run_fast('SELECT 1')}")
    # ⚠ partialmethod 定义的是【描述符】，只能用于实例，不能 db.run(db, ...) 这样直接调

    # 实战：命令注册表 —— 把"配置好的操作"存起来后续统一调用
    commands = {
        "备份": partial(connect, "backup01", 22, timeout=30.0),
        "迁移": partial(connect, "db-primary", 5432, ssl=True),
    }
    for name, cmd in commands.items():
        print(f"    执行任务「{name}」→ {cmd()}")


# ===== 语法解析 =====
# 【4】reduce：把序列折叠成一个值
#   语法规则：reduce(function, iterable[, initializer])
#     - function 必须接收【两个】参数：f(累加值, 新元素)
#     - initializer 是可选初值：给了就从它开始，不给就用首元素
#   设计意图：表达"归约"（reduce）这一计算范式。
#   ⚠ 没有 initializer 时序列为空会 TypeError；有 initializer 则返回它。
#   ★ 现在多数场景内置 sum/max/min 更快，reduce 主要用于自定义归约。
def demo_reduce() -> None:
    nums = [1, 2, 3, 4, 5]

    print(f"  reduce(lambda a,b: a+b, {nums}) = {reduce(lambda a, b: a + b, nums)}")
    print(f"  带初值 100：{reduce(lambda a, b: a + b, nums, 100)}   ← 从 100 起累加")
    print(f"  空列表无初值 → 会抛 TypeError")
    try:
        reduce(lambda a, b: a + b, [])
    except TypeError as e:
        print(f"     实际报错：{type(e).__name__}: {e}")
    print(f"  空列表带初值 = {reduce(lambda a, b: a + b, [], 0)}   ← 返回初值本身")

    # 实战 1：计算矩阵的转置（reduce + zip 的组合）
    matrix = [[1, 2, 3], [4, 5, 6], [7, 8, 9]]
    transposed = list(map(list, zip(*matrix)))
    print(f"  矩阵 {matrix} 转置 = {transposed}")

    # 实战 2：批量合并字典（reduce 累加 dict）
    def merge(acc: dict[str, int], item: tuple[str, int]) -> dict[str, int]:
        acc[item[0]] = acc.get(item[0], 0) + item[1]      # ★ 注意要 return
        return acc

    data = [("a", 1), ("b", 2), ("a", 3)]
    print(f"  reduce 合并字典 = {reduce(merge, data, {})}")
    # ★ 经典坑：回调里忘记 return acc，返回 None 会导致下一轮崩溃

    # 实战 3：找出所有元素的交集
    sets = [{1, 2, 3}, {2, 3, 4}, {3, 4, 5}]
    inter = reduce(lambda a, b: a & b, sets)
    print(f"  {sets} 的交集 = {inter}")

    # 对比 operator 里的 C 层实现（更快）
    import operator
    print(f"  operator.add + reduce = {reduce(operator.add, nums)}   ← C 层实现")
    print(f"  直接 sum = {sum(nums)}  ← 更快，单纯求和别用 reduce")


# ===== 语法解析 =====
# 【5】★ wraps：装饰器的"元信息保留"
#   语法规则：@functools.wraps(被包装函数)
#     - 把 __name__ __doc__ __qualname__ __module__ __dict__ 复制到包装函数
#     - 并把包装函数的 __wrapped__ 指向原函数（inspect/signature 依赖它）
#   为什么重要：
#     - 没有它，help()/日志/框架的路由注册都会显示成 "wrapper" 或 "inner"
#     - inspect.signature 会拿不到真实签名
def demo_wraps() -> None:
    def my_decorator(func):
        """一个统计耗时的装饰器。"""

        @wraps(func)                     # ★ 必须写，否则下面 name/doc 都拿不到
        def wrapper(*args, **kwargs):
            t0 = time.perf_counter()
            result = func(*args, **kwargs)
            elapsed = (time.perf_counter() - t0) * 1000
            print(f"    [计时] {func.__name__} 耗时 {elapsed:.3f} ms")
            return result

        return wrapper

    @my_decorator
    def calculate_sales(price: float, quantity: int) -> float:
        """计算销售额。"""
        return price * quantity

    # 有 wraps 时：名字、文档都是原函数的
    print(f"  装饰后 __name__ = {calculate_sales.__name__}")
    print(f"  装饰后 __doc__   = {calculate_sales.__doc__}")
    print(f"  装饰后 __wrapped__ 是原函数：{calculate_sales.__wrapped__.__name__}")
    # inspect 能穿透装饰器拿到真实签名
    import inspect
    print(f"  inspect.signature 看到：{inspect.signature(calculate_sales)}")
    print(f"  调用结果：{calculate_sales(price=19.9, quantity=3)}")

    # 对比：没有 wraps 的错误示范
    def bad_decorator(func):
        def inner(*args, **kwargs):      # 故意不写 @wraps
            return func(*args, **kwargs)
        return inner

    @bad_decorator
    def original() -> None:
        """原始文档。"""

    print(f"  未用 wraps 时 __name__ = {original.__name__}   ← 变成了 'inner'")
    print(f"  未用 wraps 时 __doc__ = {original.__doc__}")
    # ★ 结论：写装饰器时 @wraps 是【必选项】，不是可选项

    # wraps 的常量：显式传参可自定义属性名
    def custom(func):
        @wraps(func, assigned=functools.WRAPPER_ASSIGNMENTS,
               updated=functools.WRAPPER_UPDATES)
        def w(*a, **k):
            return func(*a, **k)
        return w

    print(f"  WRAPPER_ASSIGNMENTS 包含：{functools.WRAPPER_ASSIGNMENTS}")


# ===== 语法解析 =====
# 【6】cmp_to_key：把"比较函数"适配成"排序键"
#   语法规则：sorted(iterable, key=cmp_to_key(cmp_func))
#     - cmp_func(a, b) 返回负数/0/正数，表示 a<b / a==b / a>b
#   历史背景：Python 2 的 sort 直接接受比较函数，Python 3 改成了 key 函数。
#             cmp_to_key 就是给"老式比较逻辑"准备的迁移适配器。
#   设计意图：key 方案只调用一次 key()，而 cmp 要调用 O(n log n) 次，
#             所以现代代码应优先用 key。
def demo_cmp_to_key() -> None:
    users = [
        {"name": "张三", "age": 30, "city": "北京"},
        {"name": "李四", "age": 25, "city": "上海"},
        {"name": "王五", "age": 30, "city": "广州"},
        {"name": "赵六", "age": 20, "city": "北京"},
    ]

    # ✅ 推荐：key 函数（只计算一次 key）
    by_age = sorted(users, key=lambda u: u["age"])
    print(f"  key=lambda age：{[(u['name'], u['age']) for u in by_age]}")

    # 多级排序：先城市再年龄
    by_city_age = sorted(users, key=lambda u: (u["city"], u["age"]))
    print(f"  多级排序：{[(u['name'], u['city'], u['age']) for u in by_city_age]}")

    # cmp_to_key：复杂规则（注意返回值的符号）
    def compare(a: dict, b: dict) -> int:
        """按城市字典序，城市相同则年龄小的在前。"""
        if a["city"] != b["city"]:
            return -1 if a["city"] < b["city"] else 1     # 返回负/正，不返回 True/False
        return (a["age"] > b["age"]) - (a["age"] < b["age"])  # 巧妙写法：True-False 得 -1/0/1

    by_cmp = sorted(users, key=cmp_to_key(compare))
    print(f"  cmp_to_key：{[(u['name'], u['city'], u['age']) for u in by_cmp]}")

    # 验证 cmp_to_key 的对象确实重载了 < 等运算符
    k1 = cmp_to_key(compare)(users[0])
    k2 = cmp_to_key(compare)(users[1])
    print(f"  cmp_to_key 对象类型 = {type(k1).__name__}，支持 < 比较 = {k1 < k2}")

    # ⚠ 坑：cmp 函数直接返回布尔值也能"工作"，但语义是错的
    #   return a < b  → False(0) 与 True(1)，会把所有"不相等"都当成相等处理
    print("  ⚠ cmp 必须返回负/0/正数，直接返回 bool 会导致排序结果错误")


# ===== 语法解析 =====
# 【7】singledispatch：函数泛型（按第一个参数的类型分派）
#   语法规则：@singledispatch 装饰"通用版本"，再为各类型注册实现
#     @func.register(int) / @func.register 或 func.register([类型, ...])
#   分派规则：取【第一个位置参数】的类型 → 找最匹配的实现
#   设计意图：替代 hasattr + 一长串 if/elif isinstance 的样板代码，
#             属于"单分派"（single dispatch）而非 C++ 的多重分派。
#   ⚠ 类型分派依据是【运行时】实际类型，不是静态注解 —— 所以父类和子类会匹配注册类。
def demo_singledispatch() -> None:
    @singledispatch
    def describe(obj: object) -> str:
        """通用兜底版本。"""
        return f"未识别类型：{type(obj).__name__}"

    @describe.register(int)
    def _(obj: int) -> str:
        return f"整数：{obj}，二进制 {obj:0b}"

    @describe.register(float)
    def _(obj: float) -> str:
        return f"浮点数：{obj:.2f}"

    # register 也能接受类型列表
    @describe.register(list)
    @describe.register(tuple)
    def _(obj) -> str:
        return f"{type(obj).__name__} 含 {len(obj)} 个元素"

    @describe.register(str)
    def _(obj: str) -> str:
        return f"字符串：{obj!r}，长度 {len(obj)}"

    # 也可以注册"抽象基类"，让所有子类自动命中（★ 很强大）
    import collections.abc as abc

    @describe.register(abc.Mapping)
    def _(obj: abc.Mapping) -> str:
        return f"映射类型：{len(obj)} 个键"

    # 注册优先级：dispatch 的内部字典按"类型在 MRO 中的距离"自动选最具体的
    describe.register(complex)

    print(f"  describe(42)      → {describe(42)}")
    print(f"  describe(3.14)    → {describe(3.14)}")
    print(f"  describe('hi')    → {describe('hi')}")
    print(f"  describe([1,2])   → {describe([1, 2])}")
    print(f"  describe((1,))    → {describe((1,))}")
    print(f"  describe({'a':1}) → {describe({'a': 1})}   ← 命中 Mapping 注册")
    print(f"  describe(None)    → {describe(None)}   ← 走兜底")

    print(f"  注册表：{list(describe.registry.keys())}")
    print(f"  分派到的实现：{describe.dispatch(int).__name__}")

    # 实战：统一"转 JSON 字符串"的接口
    @singledispatch
    def to_json(obj: object) -> str:
        raise TypeError(f"不支持的类型：{type(obj).__name__}")

    @to_json.register(str)
    def _(s: str) -> str:
        import json
        return json.dumps(s, ensure_ascii=False)

    @to_json.register(int)
    @to_json.register(float)
    @to_json.register(bool)
    def _(n) -> str:
        return str(n).lower() if isinstance(n, bool) else str(n)

    @to_json.register(list)
    def _(lst: list) -> str:
        import json
        return json.dumps(lst, ensure_ascii=False)

    print(f"  to_json('中文') = {to_json('中文')}")
    print(f"  to_json(True)  = {to_json(True)}")
    print(f"  to_json([1, 'a']) = {to_json([1, 'a'])}")


# ===== 语法解析 =====
# 【8】total_ordering：用一个比较方法补齐全部
#   语法规则：@total_ordering + 至少定义 __eq__ 和其中一个 (__lt__ __le__ __gt__ __ge__)
#   作用：类只需定义"小于"，Python 自动生成 大于/小于等于/大于等于
#   设计意图：四则比较逻辑冗长且易错，用装饰器消除重复。
def demo_total_ordering() -> None:
    @total_ordering
    class Version:
        def __init__(self, major: int, minor: int) -> None:
            self.major, self.minor = major, minor

        def __eq__(self, other: object) -> bool:
            if not isinstance(other, Version):
                return NotImplemented        # ★ 必须返回 NotImplemented 而不是 False
            return (self.major, self.minor) == (other.major, other.minor)

        def __lt__(self, other: object) -> bool:
            if not isinstance(other, Version):
                return NotImplemented
            return (self.major, self.minor) < (other.major, other.minor)

        def __repr__(self) -> str:
            return f"v{self.major}.{self.minor}"

    a, b = Version(1, 2), Version(1, 10)
    print(f"  只定义了 __eq__ 和 __lt__，但可以：")
    print(f"    a={a} b={b}")
    print(f"    a < b  → {a < b}    # 1.2 < 1.10（按数值比较，10 > 2）")
    print(f"    a > b  → {a > b}    ← 由 total_ordering 自动生成")
    print(f"    a <= b → {a <= b}")
    print(f"    a >= b → {a >= b}")
    print(f"    a == Version(1,2) → {a == Version(1, 2)}")
    print(f"    排序：{sorted([b, a, Version(1, 5)])}")


def main() -> None:
    print("=" * 60)
    print("【1】lru_cache 记忆化缓存")
    print("=" * 60)
    demo_lru_cache()

    print()
    print("=" * 60)
    print("【2】cache 无上限缓存")
    print("=" * 60)
    demo_cache()

    print()
    print("=" * 60)
    print("【3】partial / partialmethod 参数绑定")
    print("=" * 60)
    demo_partial()

    print()
    print("=" * 60)
    print("【4】reduce 归约")
    print("=" * 60)
    demo_reduce()

    print()
    print("=" * 60)
    print("【5】wraps：装饰器元信息保留")
    print("=" * 60)
    demo_wraps()

    print()
    print("=" * 60)
    print("【6】cmp_to_key 比较函数适配")
    print("=" * 60)
    demo_cmp_to_key()

    print()
    print("=" * 60)
    print("【7】singledispatch 函数泛型")
    print("=" * 60)
    demo_singledispatch()

    print()
    print("=" * 60)
    print("【8】total_ordering 补齐比较运算")
    print("=" * 60)
    demo_total_ordering()

    print()
    print("=" * 60)
    print("小结")
    print("=" * 60)
    print("  1. lru_cache 用 dict+链表缓存结果，把递归从指数降到线性")
    print("  2. 参数必须可哈希；参数顺序不同不共享缓存；typed 控制是否区分类型")
    print("  3. partial 冻结参数比 lambda 快且可 pickle；partialmethod 用于类方法")
    print("  4. reduce 的回调【必须 return 累加值】，否则下一轮 TypeError")
    print("  5. @wraps 是装饰器的必选项：保住 __name__/__doc__/签名")
    print("  6. cmp_to_key 适配老式比较逻辑，现代代码应优先用 key")
    print("  7. singledispatch 按第一个参数运行时类型分派，可注册 ABC")
    print("  8. total_ordering 只写 __eq__+__lt__，务必返回 NotImplemented")


if __name__ == "__main__":
    main()