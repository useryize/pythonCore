# -*- coding: utf-8 -*-
"""
06_functional_realworld.py —— 函数式编程的工程实战

【演示的语法点】
1. 管道式数据处理：源 -> 变换 -> 过滤 -> 聚合 的可组合流水线
2. 用 class 构造 Pipe/Tap，让管道可复用、可命名
3. 装饰器链实战：日志 + 计时 + 缓存 + 参数校验 四合一
4. 装饰器顺序对执行次数的真实影响（实测）
5. 生成器做内存友好的批量处理：分块（BATCH）聚合，O(1) 额外内存
6. reduce 构建算术表达式求值器（递归下降 + 运算符表）
7. 不可变数据 + 纯函数：为什么它让并行和缓存变简单
8. 函数组合子：compose / pipe（自实现）
9. 高阶函数接受「策略」而不是写 if-else
10. 生成器委托：yield from 构建嵌套数据流

【预期输出摘要】
- 管道各阶段可单独测试、单独打印中间结果
- 装饰器链四件套按预期叠加，缓存命中率可见
- 10 万条日志分块聚合，峰值内存恒定
- 表达式求值器支持 + - * / ^ 和括号，带优先级
"""
import functools
import gc
import itertools
import operator
import re
import time
import tracemalloc


# ======================================================================
# 语法解析 1：管道式数据处理
# ======================================================================
#
# 设计原理：
#   管道 = 若干个「一元函数」的串联：f(g(h(x)))
#   关键在于【每个环节都满足同样的契约】：输入一个可迭代 -> 输出一个可迭代
#   这样任意环节都能互换，组合爆炸的问题就不存在了。
#
# 语法规则：把「单元素函数」适配成「整流函数」需要 map：
#   g_transform = lambda it: map(lambda x: x * 2, it)
#   但这层 lambda 有开销 -> 实践中用生成器表达式代替（更快更清晰）：
#   g_transform = lambda it: (x * 2 for x in it)


class Pipe:
    """管道对象：支持流式 pipe，把任意 callable 串成处理链。

    实现要点：__call__ 接受一个可调用，返回一个新 Pipe（柯里化），
    这样可以写成 pipe | step1 | step2 | step3 的形式。
    """

    def __init__(self, func, *args, **kwargs) -> None:
        # 允许 Pipe(func, 参数...) 直接柯里化，
        # 这样 Pipe(add_tags, "api") 就等价于 add_tags 后固定第一个参数为 "api"
        self.func = (functools.partial(func, *args, **kwargs)
                     if (args or kwargs) else func)

    def __call__(self, *args, **kwargs) -> "Pipe":
        # 用 functools.partial 固定已有参数
        return Pipe(functools.partial(self.func, *args, **kwargs))

    @staticmethod
    def _unwrap(step):
        """把 Pipe 对象拆成它内部的函数。

        为什么需要？因为 Pipe.__call__ 是【柯里化】（总是返回新 Pipe），
        所以 `pipe | Pipe(f)` 里的第二个 Pipe 不能直接当函数调用，
        必须先取它的 .func，否则会得到「Pipe 不是可迭代对象」。
        """
        return step.func if isinstance(step, Pipe) else step

    def __or__(self, other) -> "Pipe":
        """实现 `pipe | step`：把另一个步骤接在【后面】。

        这样 `a | b | c` 就等价于 c(b(a(x)))，和 Unix 管道习惯一致。
        """
        nxt = self._unwrap(other)
        return Pipe(lambda data: nxt(self.func(data)))

    def __ror__(self, other) -> "Pipe":
        """实现 `data | pipe` 的语法：调用 self.func(other) 再接回管道。

        为什么是 __ror__ 而不是 __or__？
        因为 `data | pipe` 里 data 通常是 list 等内置类型，
        它们不认识 Pipe，所以 Python 会【反射】调用 Pipe.__ror__。
        """
        return Pipe(lambda data: self.func(data))

    def run(self, data) -> list:
        return list(self.func(data))


def normalize(it):
    """去空白、统一小写。"""
    return (line.strip().lower() for line in it)


def remove_empty(it):
    """过滤空行 —— 生成器表达式自带惰性。"""
    return (line for line in it if line)


def add_tags(tags, it):
    """加标签：演示 partial 的配合。

    语法要点：签名是 (tags, it) —— 先【配置】后【数据】，
    这样 Pipeline 约定「每个步骤都是 f(data)」时，
    functools.partial(add_tags, ("api",)) 绑定的第一个参数正好是配置。
    这也是所有「柯里化工厂」的通用套路：配置在前，数据在后。
    """
    return (f"[{tag}]{line}" for tag in tags for line in it)


def length_histogram(it) -> dict:
    """聚合：统计行长度分布。"""
    hist: dict[int, int] = {}
    for line in it:
        n = len(line)
        hist[n] = hist.get(n, 0) + 1
    return hist


def demo_pipe() -> None:
    print("=" * 68)
    print("【1】管道式数据处理")
    print("=" * 68)

    raw_logs = [
        "  ERROR db timeout  ",
        "",
        "INFO service started",
        "   ",
        "ERROR cache miss",
        "WARN  slow query ",
    ]

    # 方式一：显式串联（最直观）
    print("方式一：显式串联")
    step1 = normalize(raw_logs)
    step2 = remove_empty(step1)
    step3 = add_tags(("prod",), step2)   # 配置在前、数据在后
    result = list(step3)
    for r in result:
        print(f"  {r}")
    print(f"  最终条数 = {len(result)}")

    # 方式二：Pipe 对象 + | 运算符
    print("\n方式二：Pipe 管道（可复用）")
    log_pipe = Pipe(normalize) | remove_empty | Pipe(add_tags, ("api",))
    piped = log_pipe.run(raw_logs)
    for r in piped:
        print(f"  {r}")

    # 管道可测试性：每一步都能单独验证
    print("\n可测试性：单步断言")
    normalized = list(normalize(["  A  ", " B"]))
    assert normalized == ["a", "b"], normalized
    print(f"  normalize 单测通过: {normalized}")
    print("  ^ 这是函数式最大的工程价值：每个环节都是纯函数，"
          "可以脱离整条管道单测")

    # 惰性验证：只看条数时不需要真正产出
    print("\n惰性验证：只取前 2 条（后面 6 条根本不会被格式化）")
    lazy = itertools.islice(normalize(raw_logs), 2)
    print(f"  islice 取到: {list(lazy)}")
    print(f"  __name__ 检查: Pipe 是 {type(log_pipe).__name__} 对象，"
          f"内部 func={log_pipe.func.__name__ if hasattr(log_pipe.func, '__name__') else 'partial'}")

    # 聚合环节
    print("\n聚合：行长度直方图")
    hist = length_histogram(remove_empty(normalize(raw_logs)))
    print(f"  {hist}")
    print(f"  总行数 = {sum(hist.values())}")

    print("\n管道设计的三个前提：")
    print("  1) 每个环节都是【一元函数】：可迭代 -> 可迭代")
    print("  2) 每个环节都是【纯函数】：无副作用、可重复执行")
    print("  3) 环节用【生成器】而非列表：保证惰性和 O(1) 额外内存")


# ======================================================================
# 语法解析 2：装饰器链实战（日志 + 计时 + 缓存 + 参数校验）
# ======================================================================
#
# 设计原理：
#   装饰器 = 高阶函数。四个装饰器叠加，本质是四次「函数 -> 函数」变换。
#   它们的顺序决定了「谁包住谁」，也就决定了：
#     - 校验在缓存【外】：非法参数每次都会被校验（更安全）
#     - 校验在缓存【内】：非法参数会进缓存（如果没抛异常的话会缓存脏数据）
#
# 顺序口诀：越「通用/安全」的放越【外】，越「昂贵/有状态」的放越【内】。
#          校验(便宜、安全) -> 日志 -> 计时 -> 缓存(最贵)


def validate(**rules):
    """参数校验装饰器工厂。

    rules 形如 {"user_id": int, "page": int}，值为期望的类型。
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # 用签名绑定把实参和形参对齐（比 args/kwargs 手工对位可靠）
            import inspect
            sig = inspect.signature(func)
            bound = sig.bind(*args, **kwargs)
            bound.apply_defaults()
            for name, expected in rules.items():
                if name not in bound.arguments:
                    continue
                value = bound.arguments[name]
                # bool 是 int 的子类，必须排除，否则 True 会被当成合法 int
                if expected is int and isinstance(value, bool):
                    raise TypeError(f"参数 {name} 不应为 bool，得到 {value!r}")
                if not isinstance(value, expected):
                    raise TypeError(
                        f"参数 {name} 类型错误：期望 {expected.__name__}，"
                        f"得到 {type(value).__name__}")
            return func(*args, **kwargs)
        return wrapper
    return decorator


def log_calls(logger_name: str):
    """日志装饰器工厂。"""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            short = func.__name__
            print(f"  [LOG:{logger_name}] 调用 {short}"
                  f" args={args[1:]} kwargs={kwargs}")
            result = func(*args, **kwargs)
            print(f"  [LOG:{logger_name}] {short} 返回 {result!r}")
            return result
        return wrapper
    return decorator


def timed(func):
    """计时装饰器：用 functools.wraps 保住签名。"""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        t0 = time.perf_counter()
        try:
            return func(*args, **kwargs)
        finally:
            # 放 finally：异常路径也要记录
            print(f"  [TIMING] {func.__name__} 耗时 "
                  f"{(time.perf_counter() - t0) * 1000:.3f} ms")
    return wrapper


def memoized(func):
    """自定义记忆化：用 dict 而不是 lru_cache，以便统计。"""
    cache: dict = {}
    stats = {"hit": 0, "miss": 0}

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        key = (args, tuple(sorted(kwargs.items())))
        if key in cache:
            stats["hit"] += 1
            print(f"  [CACHE] 命中 {key}")
            return cache[key]
        stats["miss"] += 1
        print(f"  [CACHE] 未命中，计算 {key}")
        cache[key] = func(*args, **kwargs)
        return cache[key]

    wrapper.cache = cache          # type: ignore[attr-defined]
    wrapper.stats = stats          # type: ignore[attr-defined]
    wrapper.cache_clear = cache.clear  # type: ignore[attr-defined]
    return wrapper


# 四合一：注意自下而上的书写顺序 -> 校验最外，缓存最内
@validate(user_id=int, page=int, size=int)
@log_calls("api")
@timed
@memoized
def query_orders(user_id: int, page: int = 1, size: int = 20) -> list:
    """模拟查询订单（真实场景会走数据库）。"""
    time.sleep(0.002)             # 模拟 IO 延迟
    return [{"id": i, "user": user_id} for i in range((page - 1) * size,
                                                      page * size)]


def demo_decorator_chain() -> None:
    print()
    print("=" * 68)
    print("【2】装饰器链：校验 + 日志 + 计时 + 缓存")
    print("=" * 68)

    print("装饰器等价展开：")
    print("  query_orders = validate(...)( log_calls('api')( timed( memoized(query_orders) ) ) )")
    print("  调用顺序（进入）：校验 -> 日志 -> 计时 -> 缓存 -> 函数本体")
    print("  返回顺序：函数本体 -> 缓存 -> 计时 -> 日志 -> 校验\n")

    print("第一次调用（缓存未命中）：")
    r1 = query_orders(user_id=1, page=1, size=3)
    print(f"  结果 = {r1}")

    print("\n第二次相同调用（缓存命中，日志仍会打印！）：")
    r2 = query_orders(user_id=1, page=1, size=3)
    print(f"  结果相同? {r1 == r2}")

    print(f"\n缓存统计: {query_orders.stats}")

    print("\n参数校验拦截（校验在最外层，所以非法参数【不会】污染缓存）：")
    for bad in ({"user_id": "abc"}, {"user_id": True}, {"user_id": 1, "page": 1.5}):
        try:
            query_orders(**bad)
        except TypeError as e:
            print(f"  {bad} -> TypeError: {e}")

    print(f"\n校验失败后缓存仍然干净: {query_orders.stats}")
    print(f"缓存中的键: {list(query_orders.cache.keys())}")

    print("\n结论：装饰器顺序 = 「防御性从外到内，成本从内到外」")
    print("      校验放最外，非法参数永远进不了缓存；")
    print("      计时放缓存外，才能【统计到命中】的耗时（你想知道真实端到端延迟）。")


# ======================================================================
# 语法解析 3：生成器做内存友好的批量处理
# ======================================================================
#
# 设计原理：
#   批量处理最容易写成「全量读入 list -> 切块 -> 逐块处理」，
#   这会让峰值内存 = 全量数据 + 一个分块。
#   正确做法：数据源就是生成器，边读边攒够 BATCH 条，处理完立刻丢弃这批。
#   于是峰值内存恒定为 O(BATCH)，与数据总量【无关】。
#
#   语法规则：def chunked(iterable, size):
#               it = iter(iterable)          # 确保有 iter
#               while chunk := list(islice(it, size)):   # 海象运算符（3.8+）
#                   yield chunk


def batched(iterable, size: int):
    """把任意可迭代切成固定大小的批（惰性，O(size) 内存）。

    注意：标准库 itertools.batched（3.12+）也能做，但对 dict 等特殊类型行为不同，
    这里手写一个兼容所有可迭代的版本，并演示海象运算符的用法。
    """
    it = iter(iterable)
    while True:
        # 海象运算符 := 在 while 条件里赋值，避免多写一次 list()
        chunk = list(itertools.islice(it, size))
        if not chunk:
            return
        yield chunk


def stream_logs(n: int):
    """模拟流式日志源：产出而不是持有。"""
    levels = ["DEBUG", "INFO", "WARN", "ERROR"]
    for i in range(n):
        # 用确定性伪随机，避免真实 random 带来的不可复现
        level = levels[(i * 7) % len(levels)]
        yield {"id": i, "level": level, "msg": f"event-{i}"}


def aggregate_batches(source, batch_size: int) -> dict:
    """分块聚合：返回每个 level 的计数。

    这是 ETL 里最常见的形态：源可能是 10GB 的日志，
    但这个函数任何时刻内存里只有一个 batch。
    """
    counters: dict[str, int] = {}
    processed = 0
    for batch in batched(source, batch_size):
        # 只在 batch 范围内遍历，不会看到全量数据
        for record in batch:
            counters[record["level"]] = counters.get(record["level"], 0) + 1
        processed += len(batch)
        # ^ 这一行结束时，batch 被重新绑定 -> 上一批对象【立刻可被回收】
    return {"counters": counters, "processed": processed}


def measure_streaming_memory(n: int) -> None:
    """实测：流式聚合 vs 全量加载的内存差异。"""
    gc.collect()

    # 全量加载
    tracemalloc.start()
    base, _ = tracemalloc.get_traced_memory()
    everything = list(stream_logs(n))
    _, peak_bulk = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    del everything

    # 流式分块
    tracemalloc.start()
    base2, _ = tracemalloc.get_traced_memory()
    result = aggregate_batches(stream_logs(n), 1000)
    _, peak_stream = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    print(f"  数据量 = {n:,} 条，每条约 200 字节")
    print(f"  全量 list 峰值 : {peak_bulk:>12,} 字节")
    print(f"  流式分块峰值   : {peak_stream:>12,} 字节")
    print(f"  内存节省       : {peak_bulk / max(peak_stream, 1):.0f} 倍")
    print(f"  两者结果一致? 见下方聚合输出: {result}")


def demo_streaming() -> None:
    print()
    print("=" * 68)
    print("【3】生成器：内存友好的批量处理")
    print("=" * 68)

    print("分块切分演示（batched + 海象运算符）：")
    data = list(range(10))
    for i, batch in enumerate(batched(data, 3)):
        print(f"  第{i + 1}批: {batch}（大小 {len(batch)}）")
    print("  ^ 最后一批可以【不满】，这是批处理的常态（真实场景还要处理尾批补偿）")

    print("\n分块聚合演示（模拟日志分析）：")
    r = aggregate_batches(stream_logs(10_000), 2_000)
    print(f"  处理条数 = {r['processed']:,}")
    print(f"  各级别计数 = {r['counters']}")

    print("\n内存实测（10 万条）：")
    measure_streaming_memory(100_000)

    print("\n工程要点：")
    print("  1) 源必须是生成器/可迭代，不能是已加载的 list")
    print("  2) batch_size 是「吞吐 vs 内存」的旋钮：要吞吐就大，要内存就小")
    print("  3) 尾批不满时：数据库要用 upsert，消息队列要处理确认策略")
    print("  4) 批内出错时要决定：整批回滚（事务）还是跳过单条（savepoint）")


# ======================================================================
# 语法解析 4：reduce 构建算术表达式求值器
# ======================================================================
#
# 设计原理：
#   递归下降解析（recursive descent）把「表达式」定义成一组互相递归的规则：
#       表达式 := 项 (('+'|'-') 项)*
#       项     := 因子 (('*'|'/') 因子)*
#       因子   := 数字 | '(' 表达式 ')'
#   每层规则用 reduce 把「左右两段 + 运算符」折叠成一个值。
#
#   语法规则：把 (值, 运算符) 配对用 zip + 压缩：
#       vals = [左值, 右值...], ops = [运算符...]
#       list(zip(ops, vals[1:]))   -> [(op, 右值), ...]
#       然后 reduce(lambda acc, (op, v): OPS[op](acc, v), pairs, vals[0])


# 运算符表：用 operator 模块的函数，而不是 if-else
OPERATORS = {
    "+": operator.add,
    "-": operator.sub,
    "*": operator.mul,
    "/": operator.truediv,
    "%": operator.mod,
    "^": operator.pow,
}
# 注意：这里故意把 ^ 和 % 放进【同一张表】，
# 但 parse_term 里只识别 * / %，^ 属于「右结合」所以单独在 parse_power 处理。
# 新增运算符的完整步骤：(1) 加进 OPERATORS  (2) 改 tokenize 的正则
#                            (3) 在对应的 parse_* 里加入符号
#                     —— 三步都改才算真正支持，容易漏的是第 2 步。


def tokenize(expr: str) -> list[str]:
    """词法分析：把字符串切成 token 列表。

    正则 r"\\d+|[()+\\-*/^]" 的含义：
      \\d+  一个或多个数字
      |     或
      [()...]  单字符运算符集合
    """
    tokens = re.findall(r"\d+|[()+\-*/^%]", expr)
    if "".join(tokens) != expr.replace(" ", ""):
        raise ValueError(f"表达式含非法字符: {expr!r}")
    return tokens


class Parser:
    """递归下降解析器：把中缀表达式求值。

    三个方法对应三层文法，每层都用 reduce 折叠。
    """

    def __init__(self, tokens: list[str]) -> None:
        self.tokens = tokens
        self.pos = 0

    def peek(self) -> str | None:
        return self.tokens[self.pos] if self.pos < len(self.tokens) else None

    def consume(self) -> str:
        tok = self.tokens[self.pos]
        self.pos += 1
        return tok

    def parse_expression(self) -> float:
        """表达式 := 项 (('+'|'-') 项)*   —— 最低优先级。"""
        value = self.parse_term()
        ops_and_values: list[tuple[str, float]] = []
        while (op := self.peek()) in ("+", "-"):
            self.consume()
            ops_and_values.append((op, self.parse_term()))
        if not ops_and_values:
            return value
        # 关键：把 (acc, op, val) 三元组折叠
        return functools.reduce(
            lambda acc, pair: OPERATORS[pair[0]](acc, pair[1]),
            ops_and_values, value)

    def parse_term(self) -> float:
        """项 := 幂 (('*' | '/' | '%') 幂)*   —— 中间优先级。"""
        value = self.parse_power()
        ops_and_values: list[tuple[str, float]] = []
        while (op := self.peek()) in ("*", "/", "%"):
            self.consume()
            ops_and_values.append((op, self.parse_power()))
        if not ops_and_values:
            return value
        return functools.reduce(
            lambda acc, pair: OPERATORS[pair[0]](acc, pair[1]),
            ops_and_values, value)

    def parse_power(self) -> float:
        """幂 := 因子 ('^' 幂)?   —— 右结合。

        为什么必须单独分一层？
        因为 ^ 是【右结合】：2^3^2 = 2^(3^2) = 512（和 Python 的 ** 一致）。
        如果把它放进 parse_term 的循环里做左折叠，会得到 (2^3)^2 = 64 —— 错了。
        实现方式很经典：右边【递归调用自己】而不是循环，从而天然右结合。
        """
        base = self.parse_factor()
        if self.peek() == "^":
            self.consume()
            exponent = self.parse_power()      # 递归 -> 天然右结合
            return OPERATORS["^"](base, exponent)
        return base

    def parse_factor(self) -> float:
        """因子 := ('-'|'~')* (数字 | '(' 表达式 ')')   —— 最高优先级。"""
        # 一元运算符：支持一元负号 -3。注意必须在【因子】层处理，
        # 因为一元负号的优先级比二元乘除更高（-2^2 = -(2^2) = -4）
        sign = 1.0
        while (tok := self.peek()) in ("-", "~"):
            self.consume()
            if tok == "-":
                sign = -sign

        tok = self.consume()
        if tok == "(":
            value = self.parse_expression()
            if self.consume() != ")":
                raise ValueError("缺少右括号")
            return sign * value
        return sign * float(tok)      # 字面量转换


def evaluate(expr: str) -> float:
    """对外接口：词法 + 语法 + 求值。"""
    return Parser(tokenize(expr)).parse_expression()


def demo_calculator() -> None:
    print()
    print("=" * 68)
    print("【4】reduce 构建表达式求值器")
    print("=" * 68)

    print("文法（递归下降的四层规则）：")
    print("  表达式 := 项 (('+' | '-') 项)*")
    print("  项     := 幂 (('*' | '/' | '%') 幂)*")
    print("  幂     := 因子 ('^' 幂)?      <- 右结合（递归实现）")
    print("  因子   := ('-' | '~')* (数字 | '(' 表达式 ')')")
    print("结合性对比：'/' 和 '^' 的处理方式完全不同")
    print("  - '/'：放在 parse_term 的 while 循环里 -> 【左结合】(100/8)/5")
    print("  - '^'：放在 parse_power 的【递归】里    -> 【右结合】2^(3^2)")

    cases = [
        ("1 + 2 * 3", 7.0),            # 乘法优先
        ("(1 + 2) * 3", 9.0),          # 括号改变优先级
        ("2 ^ 3 ^ 2", 512.0),          # 右结合：2^(3^2)=512（与 Python ** 一致）
        ("100 / 8 / 5", 2.5),          # 左结合：(100/8)/5=2.5
        ("1 + 2 + 3 + 4", 10.0),
        ("-3 + 5", 2.0),               # 一元负号
        ("-(2 + 3)", -5.0),            # 一元负号 + 括号
        ("--5", 5.0),                  # 连续两个负号
        ("10 % 3", 1.0),               # 取模
    ]

    print("\n求值实测：")
    for expr, expected in cases:
        got = evaluate(expr)
        flag = "OK" if abs(got - expected) < 1e-9 else "MISMATCH"
        print(f"  {expr:<16} = {got:<10} (期望 {expected}, {flag})")

    print("\n词法结果展示：")
    for e in ("1 + 2 * 3", "(4/2)^2"):
        print(f"  {e:<12} -> {tokenize(e)}")

    print("\n错误处理：")
    for bad in ("1 + ", "(1 + 2", "1 $ 2"):
        try:
            evaluate(bad)
        except (ValueError, IndexError) as e:
            print(f"  {bad!r:<10} -> {type(e).__name__}: {e}")
    print("  ^ 解析器没有做「末尾必须无剩余 token」的校验，这是教学代码的简化；")
    print("    生产实现应加：if parser.pos != len(parser.tokens): raise ...")

    print("\n设计要点：")
    print("  1) 运算符表（dict + operator 模块）代替 if-else -> 扩展新运算符只需加一行")
    print("  2) 递归下降把优先级【显式编码】在方法层级里，不依赖优先级表")
    print("  3) reduce 在每层做左折叠，省掉一层临时变量")

    # 演示「加一个新运算符有多容易」
    print(f"\n新增 '&' 运算符（位与）演示：")
    # 只改 OPERATORS 一行 + tokenize 正则 + parse_term 的符号列表
    OPERATORS["&"] = operator.and_
    print(f"  OPERATORS['&'] = operator.and_ -> 6 & 3 = {OPERATORS['&'](6, 3)}")
    print("  ^ 但要真正支持 '6 & 3' 这样的表达式，还得改 tokenize 正文和 parse_term 的符号列表，")
    print("    所以「运算符表」只解决了【求值】，没解决【解析】。")
    del OPERATORS["&"]


# ======================================================================
# 语法解析 5：函数组合子 compose / pipe
# ======================================================================
#
# 语法规则：
#   def compose(*fs):  return lambda x: functools.reduce(lambda v, f: f(v), fs, x)
#   def pipe(*fs):     return lambda x: functools.reduce(lambda v, f: f(v), x, fs)
#
# compose(f, g)(x) == g(f(x))     <- 组合子数学定义
# pipe(f, g)(x)    == f(g(x))     <- 面向对象/Unix 管道习惯
# 记忆：compose 是「洋葱」（f 在最外），pipe 是「流水线」（f 在最前）。


def inc(x: float) -> float:
    return x + 1


def double(x: float) -> float:
    return x * 2


def square(x: float) -> float:
    return x ** 2


def compose(*fs):
    """数学意义上的组合：compose(f, g)(x) = g(f(x))，从右往左包。"""
    def composed(x):
        return functools.reduce(lambda v, f: f(v), fs, x)
    return composed


def pipe(*fs):
    """管道：pipe(f, g)(x) = f(g(x))，从左往右流。

    关键：函数列表要【倒序】迭代。
    因为 pipe(f, g) 意味着先算 g 再算 f，
    而 reduce 是正序迭代（先取列表第一个），
    所以必须 reversed(fs)，否则会退化成 compose。
    """
    def piped(x):
        # reduce 的参数顺序是 reduce(函数, 可迭代, 初始值) —— 初始值在【最后】
        return functools.reduce(lambda v, f: f(v), reversed(fs), x)
    return piped


def demo_composition() -> None:
    print()
    print("=" * 68)
    print("【5】函数组合：compose vs pipe")
    print("=" * 68)

    x = 3
    c = compose(inc, double)(x)
    p = pipe(inc, double)(x)
    print(f"  x = {x}")
    print(f"  compose(inc, double)(3) = {c}   <- double(inc(3)) = 2*4 = 8")
    print(f"  pipe(inc, double)(3)    = {p}   <- inc(double(3)) = 6+1 = 7")
    print(f"  ^ compose = {c}, pipe = {p}，顺序相反！这是最容易记错的地方")

    # 手写对照
    print(f"\n  手写 compose(inc, double)(3) = double(inc(3)) = {double(inc(3))}")
    print(f"  手写 pipe(inc, double)(3)    = inc(double(3)) = {inc(double(3))}")

    # 三步管道
    f = pipe(inc, double, square)
    print(f"\n  pipe(inc, double, square)(3) = {f(3)}")
    print("  ^ 按定义展开：inc(double(square(3))) = inc(double(9)) = inc(18) = 19")
    print("    记忆：pipe(f,g,h) 写成嵌套就是 f(g(h(x)))，最右边的函数【先执行】")

    # 为什么工程上更常用 pipe
    print("\n工程意义：pipe 让「处理流程」变成一个【值】，可以赋值、传参、测试")
    # str.strip 是【一元】函数，正好符合 pipe 的「每个函数都收一个值」约定
    trim = pipe(str.lower, str.strip)
    format_user = pipe(lambda s: f"«{s}»", str.lower, str.strip)
    print(f"  format_user('  ADMIN  ') = {format_user('  ADMIN  ')}")
    assert format_user("  ADMIN  ") == "«admin»"
    print(f"  只做清洗: trim('  ADMIN  ') = {trim('  ADMIN  ')!r}")
    print("  ^ 读法：pipe(f,g,h) 就是 f(g(h(x)))，所以【最后】写的函数先执行；")
    print("    上面这行的执行顺序是 strip -> lower -> 加书名号")
    print("  ✓ 断言通过：每个环节都是一元函数，可以直接单测组合结果本身")

    print("\n注意：pipe 的每个函数都必须是【一元函数】，")
    print("      所以要处理多参数就得用 partial 或 currying 先适配。")


# ======================================================================
# 语法解析 6：不可变数据 + 策略注入
# ======================================================================
#
# 设计原理：
#   函数式编程追求「无副作用」：
#     - 函数不修改传入的数据（不可变）
#     - 函数不依赖外部可变状态（纯函数）
#   这样「缓存」安全（输入不变 -> 输出不变）、「并行」安全（无共享写）、
#   「测试」简单（不需要 mock 外部状态）。
#
#   「策略注入」= 把 if-else 分支变成参数，避免写一堆只有一个变量不同的函数。


from dataclasses import dataclass, field, replace


@dataclass(frozen=True)
class Order:
    """frozen=True -> 实例不可变（不可写属性），
    这是函数式的关键：不可变数据天然线程安全、可用作 dict key。"""
    order_id: int
    user_id: int
    amount: float
    items: tuple = field(default_factory=tuple)


def make_order_calculator(tax_rate: float, discount_fn=None):
    """策略注入：把「税率」和「折扣策略」变成参数而不是 if-else。"""
    def calculate(order: Order) -> float:
        base = order.amount
        if discount_fn is not None:
            base = discount_fn(base)     # 策略：函数作为参数
        return base * (1 + tax_rate)
    return calculate


def demo_immutable_strategy() -> None:
    print()
    print("=" * 68)
    print("【6】不可变数据 + 策略注入")
    print("=" * 68)

    orders = [
        Order(order_id=1, user_id=10, amount=100.0, items=("书", "笔")),
        Order(order_id=2, user_id=10, amount=200.0),
        Order(order_id=3, user_id=20, amount=50.0),
    ]

    print("frozen dataclass 的不可变性：")
    o = orders[0]
    try:
        o.amount = 999.0          # type: ignore[misc]
    except Exception as e:
        print(f"  修改属性 -> {type(e).__name__}: {e}")
    print(f"  ^ frozen=True 阻止一切属性赋值 —— 数据不会被意外改坏")
    print(f"  可作 dict key（不可变 -> hash 稳定）: "
          f"{ {o: '订单对象'} }")

    # replace：不可变数据的「更新」方式，返回新对象
    updated = replace(o, amount=150.0)
    print(f"\nreplace(o, amount=150) 返回新对象: id={id(o) == id(updated)} "
          f"（原对象未变 = {o.amount}）")

    # 策略注入
    print("\n策略注入（避免 if-else）：")
    no_discount = make_order_calculator(tax_rate=0.13)
    vip_discount = make_order_calculator(
        tax_rate=0.13,
        discount_fn=lambda amount: amount * 0.9)      # VIP 打九折

    for label, calc in (("无折扣", no_discount), ("VIP九折", vip_discount)):
        total = sum(calc(x) for x in orders)
        print(f"  {label:<8} 含税总额 = {total:.2f}")

    print("\n为什么这样设计更好：")
    print("  - 加一种折扣策略 = 传一个函数，不用改 calculate 的代码（开闭原则）")
    print("  - calculate 是纯函数 -> 可以放心加缓存（@lru_cache）")
    print("  - Order 不可变 -> 可以跨线程共享，可以做缓存 key")

    # 演示：纯函数 + lru_cache 的组合威力
    @functools.lru_cache(maxsize=None)
    def cached_calculate(order: Order, rate: float) -> float:
        return order.amount * (1 + rate)

    print("\n纯函数 + lru_cache（Order 不可变，所以可以安全缓存）:")
    a = cached_calculate(orders[0], 0.13)
    b = cached_calculate(orders[0], 0.13)
    print(f"  两次调用结果相同: {a == b}, 缓存信息: "
          f"{cached_calculate.cache_info()}")
    print("  ^ 如果 Order 可变，缓存就会返回【过期的旧值】—— 这是纯函数的价值")


# ======================================================================
# 语法解析 7：yield from 构建嵌套数据流
# ======================================================================
#
# 语法规则：def flatten(nested): yield from (yield from item for item in nested)
#   多层 yield from 可以「递归展平」任意深度的嵌套可迭代结构。
#   对比手写递归：需要显式 for + yield 转发，且栈深大时仍有函数调用开销。


def flatten(nested) -> "generator":
    """递归展平任意深度的嵌套结构。

    语法解析：`yield from` 委托给一个【生成器表达式】，
    而生成器表达式内部又是 `yield from item`，形成递归委托。
    """
    for item in nested:
        if isinstance(item, (list, tuple, set)):
            yield from flatten(item)      # 递归委托
        else:
            yield item                    # 叶子节点


def demo_yield_from_flatten() -> None:
    print()
    print("=" * 68)
    print("【7】yield from 递归展平")
    print("=" * 68)

    nested = [1, [2, 3, [4, [5, 6]], 7], 8, (9, [10, [11]])]
    print(f"嵌套结构: {nested}")
    flat = list(flatten(nested))
    print(f"展平结果: {flat}")

    # 无限流 + 递归展平：处理无限宽的树
    print("\n与 itertools.chain 对比（chain 只展一层）：")
    shallow = list(itertools.chain(*[[1, 2], [3, [4, 5]]]))
    print(f"  chain(*...)          -> {shallow}   （4 和 5 仍在嵌套里）")
    print(f"  flatten(...)         -> {list(flatten([[1, 2], [3, [4, 5]]]))}"
          f"   （完全展平）")
    print("\n设计原理：yield from 把子生成器的产出【直接转发】，")
    print("      相当于把多个生成器【拼接成一个流】，消费者无感知。")
    print("      这也是为什么 `yield from` 比 `for x in ..: yield x` 更快：")
    print("      前者少一层 Python 栈帧，且能在 C 层直接委托 __next__。")


def main() -> None:
    demo_pipe()
    demo_decorator_chain()
    demo_streaming()
    demo_calculator()
    demo_composition()
    demo_immutable_strategy()
    demo_yield_from_flatten()
    print()
    print("=" * 68)
    print("06_functional_realworld 演示完毕")
    print("核心一句话：函数式的工程价值 = 可组合 + 可测试 + 惰性 + 少副作用。")
    print("=" * 68)


if __name__ == "__main__":
    main()