"""L12 可迭代对象与生成器 —— 配套教案示例。

运行：python examples/L12_iterable_generator.py

本脚本演示十一件事：
    1. 迭代器协议：iter() 与 next()，for 循环背后到底在做什么
    2. 可迭代对象 vs 迭代器，以及「一次性消费」的本质
    3. 迭代器的 __iter__ 返回 self 的含义（为什么能反复 for 同一个生成器不行）
    4. 自定义迭代器类：实现 __iter__ 和 __next__
    5. 生成器函数：用 yield「一次算一个」
    6. 生成器表达式：与列表推导式的区别（惰性 vs 立即）
    7. 惰性求值的威力：处理「无限序列」和「用不完的数据」
    8. map / filter 与推导式的对比：速度、内存、可读性
    9. any / all / sum 等聚合函数，以及三元表达式
   10. itertools：chain / islice / groupby / accumulate / zip_longest
   11. 什么时候用生成器、什么时候用列表（决策树）

⚠️ 纯标准库，可直接运行。
"""

import sys                                    # 标准库：getsizeof 内存对比
import time                                   # 标准库：性能对比
from itertools import (accumulate, chain, groupby, islice,   # 标准库：组合工具
                       product, zip_longest)

# ============================================================
# 模块级常量
# ============================================================
BIG = 1_000_000                              # 百万级数据的内存对比
PERF_SIZE = 200_000                          # 性能对比的数据规模


# ============================================================
# 第 1 部分：迭代器协议
# ============================================================
def demo_protocol() -> None:
    """iter() 与 next()：for 循环背后的真实动作。"""
    print("【迭代器协议】\n")

    data = [10, 20, 30]

    # iter(可迭代对象) → 返回一个【迭代器】
    it = iter(data)
    print(f"  type(iter([10,20,30])) = {type(it).__name__}")
    print(f"  iter(list) 本身不是 list: {isinstance(it, list)}")

    # next(迭代器) → 取下一个元素，取完抛 StopIteration
    print("\n  用 next() 手动迭代（for 循环内部就是在做这件事）：")
    for i in range(3):
        print(f"    第 {i + 1} 次 next() = {next(it)}")

    try:
        next(it)
    except StopIteration:
        print("    再取一次 → StopIteration   ⚠️ 这是迭代器的「正常结束」信号")

    # ⭐ for 循环等价于这段代码
    print("\n  ⭐ for 循环的本质等价于：")
    print("    it = iter(data)")
    print("    while True:")
    print("        try:")
    print("            value = next(it)")
    print("        except StopIteration:")
    print("            break")
    print("        # 处理 value")
    print("    ↑ 所以 for 能自动处理「结束」，而手写 next 必须自己接异常")

    # 可迭代对象 vs 迭代器
    print("\n  【可迭代对象 vs 迭代器】")
    print(f"    [1,2,3] 有 __iter__ : {hasattr([1,2,3], '__iter__')}   （可迭代对象）")
    print(f"    iter([1,2,3]) 有 __iter__ : {hasattr(iter([1,2,3]), '__iter__')}   （迭代器也是可迭代的）")
    print(f"    iter([1,2,3]) 有 __next__ : {hasattr(iter([1,2,3]), '__next__')}   （只有迭代器有）")
    print(f"    [1,2,3] 有 __next__  : {hasattr([1,2,3], '__next__')}   ❌ 列表本身不是迭代器")


# ============================================================
# 第 2 部分：一次性消费
# ============================================================
def demo_one_shot() -> None:
    """为什么生成器只能遍历一次，而列表可以反复。"""
    print("\n【一次性消费】\n")

    # 列表：可以反复遍历
    lst = [1, 2, 3]
    print(f"  列表第 1 次遍历: {[x for x in lst]}")
    print(f"  列表第 2 次遍历: {[x for x in lst]}   ✅ 每次都创建新迭代器")

    # ⭐ 关键：for 循环每次都调用 iter()
    it1 = iter(lst)
    it2 = iter(lst)
    print(f"  两次 iter(list) 是同一个对象吗: {it1 is it2}   → False")
    print("  所以「反复 for 同一个列表」每次都拿到【全新的】迭代器")

    # 生成器：只有一个迭代器，只能消费一次
    gen = (x * 2 for x in [1, 2, 3])
    print(f"\n  生成器第 1 次: {list(gen)}")
    print(f"  生成器第 2 次: {list(gen)}   ⚠️ 空！已被耗尽")

    # ⚠️ 更隐蔽：for 循环里消耗生成器
    def count_twice() -> None:
        gen2 = (x for x in range(3))
        first = [x for x in gen2]               # 第一次消费
        second = [x for x in gen2]              # 第二次 → 空
        print(f"\n  ⚠️ 同一生成器被 for 两次: 第一次={first}, 第二次={second}")
        print("     → 这是生成器最常见的坑：它【只能遍历一次】")

    count_twice()

    # ⚠️ enumerate + 生成器的组合陷阱
    print("\n  ⚠️ 陷阱：把生成器传给两个函数")
    gen3 = (x for x in range(5))
    total = sum(gen3)                            # 第一个函数消费完了
    count = len(list(gen3))                      # 第二个函数拿到空
    print(f"     sum(gen3) = {total}, 之后 list(gen3) = {count}   ⚠️ 后者永远是空")


# ============================================================
# 第 3 部分：自定义迭代器
# ============================================================
class Countdown:
    """自定义迭代器：从 10 数到 1，演示 __iter__ 与 __next__。"""

    def __init__(self, start: int) -> None:
        self.current = start

    def __iter__(self) -> "Countdown":
        """返回迭代器本身——这是「迭代器也是可迭代对象」的实现方式。

        ⚠️ 为什么返回 self 而不是新对象？
           因为迭代器的协议要求：迭代器必须有 __iter__，
           这样 for 循环才能对它用 iter()。返回 self 让它「自己就是迭代器」。
        """
        return self

    def __next__(self) -> int:
        """返回下一个值；没有值了抛 StopIteration。"""
        if self.current <= 0:
            raise StopIteration                 # ⭐ 结束信号，必须抛这个异常
        self.current -= 1
        return self.current + 1


def demo_custom_iterator() -> None:
    """自定义迭代器的两个要素，以及它的「一次性」特性。"""
    print("\n【自定义迭代器】\n")

    c = Countdown(5)
    print(f"  for x in Countdown(5): {[x for x in c]}")

    # ⚠️ 但自定义迭代器也是一次性的
    c2 = Countdown(3)
    print(f"  第一次遍历: {list(c2)}")
    print(f"  第二次遍历: {list(c2)}   ⚠️ 空！状态已经被消耗了")

    # ⭐ 关键区别：可迭代对象每次 iter() 得到「新状态」
    print("\n  ⭐ 对比：可迭代对象 vs 迭代器")
    print("  ┌─────────────────┬──────────────────┬──────────────────┐")
    print("  │                 │ 可迭代对象        │ 迭代器            │")
    print("  ├─────────────────┼──────────────────┼──────────────────┤")
    print("  │ 有 __iter__     │ ✅                │ ✅                │")
    print("  │ 有 __next__     │ ❌                │ ✅                │")
    print("  │ iter() 的结果   │ 新的迭代器        │ 它自己(self)      │")
    print("  │ 能反复遍历      │ ✅ 每次都新建      │ ❌ 只能一次        │")
    print("  └─────────────────┴──────────────────┴──────────────────┘")

    # 其他内置的可迭代对象
    print("\n  其他「可迭代但不是迭代器」的内置类型：")
    for name, obj in [("list", [1]), ("tuple", (1,)), ("str", "a"),
                      ("dict", {}), ("set", {1}), ("range", range(1))]:
        print(f"    {name:<8} 可迭代={hasattr(obj, '__iter__')}  "
              f"是迭代器={hasattr(obj, '__next__')}")

    # ⚠️ 但字符串的迭代结果是「单个字符」
    print(f"\n  ⚠️ 遍历字符串得到的是单字符: {list('abc')}")
    print(f"     而 range 遍历得到数字: {list(range(3))}")


# ============================================================
# 第 4 部分：生成器函数（yield）
# ============================================================
def fibonacci(n: int):
    """⭐ 经典的生成器函数：用 yield 逐个产出斐波那契数。

    ⭐ 核心机制：函数里有 yield，调用它就【不会执行函数体】，
       而是返回一个生成器对象；每次 next() 才执行到下一个 yield 处。
    """
    a, b = 0, 1
    for _ in range(n):
        yield a                                # ⭐ 产出 a，然后暂停在这里
        a, b = b, a + b                        # 下次 next() 时从这里继续


def demo_yield() -> None:
    """生成器函数的执行时机：调用时什么都不做，迭代时才执行。"""
    print("\n【生成器函数 yield】\n")

    # ⭐ 调用函数【不会执行函数体】
    gen = fibonacci(5)
    print(f"  调用 fibonacci(5) 得到: {type(gen).__name__}   ← 函数体还没执行！")
    print(f"  生成器对象大小: {sys.getsizeof(gen)} 字节（几乎不占空间）")

    # 迭代时才真正计算
    result = [x for x in fibonacci(5)]
    print(f"  迭代后得到: {result}   ← 现在才真正算出这些数")

    # ⭐ 惰性验证：无限生成器
    def infinite() -> None:
        """无限序列——只有生成器才能处理，因为不需要全部物化。"""
        n = 0
        while True:                           # 永不停止
            yield n
            n += 1

    inf = infinite()
    print(f"\n  ⭐ 无限生成器取前 5 个: {[next(inf) for _ in range(5)]}")
    print("     如果用列表推导式写，会试图把无限序列全部算出来 → 内存耗尽/死循环")

    # 演示「yield 使函数变成生成器」
    def has_yield():
        return 1
        yield                                  # 永远执行不到，但让函数成为生成器

    def no_yield():
        return 1

    print(f"\n  含 yield 的函数 is generator function: "
          f"{hasattr(has_yield(), '__next__')}")
    print(f"  不含 yield 的函数 is generator function: "
          f"{hasattr(no_yield(), '__next__')}")


# ============================================================
# 第 5 部分：生成器表达式
# ============================================================
def demo_generator_exp() -> None:
    """生成器表达式 vs 列表推导式：惰性 vs 立即。"""
    print("\n【生成器表达式】\n")

    # 语法上只差括号
    list_comp = [x * 2 for x in range(5)]       # 方括号 → 立即求值成列表
    gen_exp = (x * 2 for x in range(5))        # 圆括号 → 惰性生成器
    print(f"  [x*2 for x in range(5)] → {type(list_comp).__name__}: {list_comp}")
    print(f"  (x*2 for x in range(5)) → {type(gen_exp).__name__}: {list(gen_exp)}")

    # ⭐ 内存对比（这是最直观的差距）
    print(f"\n  ⭐ 百万级数据的内存占用：")
    gen_big = (i * 2 for i in range(BIG))
    lst_big = [i * 2 for i in range(BIG)]
    gen_size = sys.getsizeof(gen_big)
    lst_size = sys.getsizeof(lst_big)
    print(f"    生成器表达式: {gen_size:,} 字节")
    print(f"    列表推导式  : {lst_size:,} 字节  （是生成器的 {lst_size / gen_size:,.0f} 倍）")
    print("    ⭐ 生成器只保存「当前状态」，所以大小和元素数量【无关】")
    _ = list(gen_big)                          # 消费掉，避免影响后面的内存测量

    # ⭐ 惰性的三个好处
    print("\n  ⭐ 惰性求值的三个好处：")
    # 1. 处理无限序列
    inf_gen = (i for i in range(10**12))
    print(f"    1. 处理「无限」序列：取前 3 个 → {list(islice(inf_gen, 3))}")
    # 2. 只取需要的前几个（短路）
    print(f"    2. 只取前 3 个就停（不处理剩余）：{list(islice((i*i for i in range(100)), 3))}")
    # 3. 流式处理，不占用中间存储
    def read_lines_stream(path: str):
        """逐行读取并产出非空行——真实的大文件处理场景。"""
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    yield line
    print("    3. 流式处理大文件：内存占用与文件大小【无关】")


# ============================================================
# 第 6 部分：map / filter 与推导式对比
# ============================================================
def demo_map_filter() -> None:
    """map/filter 与推导式的速度、内存对比。"""
    print("\n【map / filter 与推导式】\n")

    data = list(range(PERF_SIZE))

    # 功能对比
    print("  功能完全等价的三种写法：")
    print(f"    list(map(str, [1, 2]))       = {list(map(str, [1, 2]))}")
    print(f"    [str(x) for x in [1, 2]]      = {[str(x) for x in [1, 2]]}")
    print(f"    list(map(lambda x: x*2, [1,2])) = {list(map(lambda x: x*2, [1, 2]))}")
    print(f"    [x*2 for x in [1, 2]]        = {[x*2 for x in [1, 2]]}")
    print(f"    list(filter(None, [1, 0, 2]))  = {list(filter(None, [1, 0, 2]))}")
    print(f"    [x for x in [1, 0, 2] if x]  = {[x for x in [1, 0, 2] if x]}")

    # ⭐ map/filter 返回的是【迭代器】，不是列表
    m = map(str, [1, 2])
    f = filter(None, [1, 0])
    print(f"\n  ⭐ type(map(...)) = {type(m).__name__}, type(filter(...)) = {type(f).__name__}")
    print(f"     它们是【惰性】的：不消费就不会真的计算")
    print(f"     map 是生成器吗? {hasattr(m, '__next__')}   → True（是迭代器）")

    # ⭐ 性能对比
    print(f"\n  ⭐ 性能对比（{PERF_SIZE:,} 个元素，各跑 5 次取平均）：")
    rounds = 5

    t0 = time.perf_counter()
    for _ in range(rounds):
        _ = [x * 2 for x in data]
    t1 = time.perf_counter()
    for _ in range(rounds):
        _ = list(map(lambda x: x * 2, data))
    t2 = time.perf_counter()
    for _ in range(rounds):
        _ = (x * 2 for x in data)
    t3 = time.perf_counter()

    list_t = (t1 - t0) / rounds
    map_t = (t2 - t1) / rounds
    gen_t = (t3 - t2) / rounds
    print(f"    列表推导式      : {list_t * 1000:.2f} ms   （最快）")
    print(f"    map + lambda   : {map_t * 1000:.2f} ms   慢 {map_t / list_t:.2f}×")
    print(f"    生成器表达式   : {gen_t * 1000:.2f} ms   （只创建对象，不计算）")
    print("    ⭐ 结论：推导式最快（省去函数调用开销）；map 慢是因为有 lambda 调用；")
    print("       生成器表达式【根本没计算】，所以「最快」是没有意义的。")

    # map 的真正优势：多序列
    print("\n  ⭐ map 的真正优势：同时处理【多个序列】")
    a, b = [1, 2, 3], [10, 20, 30]
    print(f"    map(lambda x,y: x+y, a, b) = {list(map(lambda x, y: x + y, a, b))}")
    print(f"    等价推导式 [x+y for x,y in zip(a,b)] = {[x + y for x, y in zip(a, b)]}")
    print("       推导式也能做，但 map 的多参数形式更直观。")


# ============================================================
# 第 7 部分：三元表达式与聚合函数
# ============================================================
def demo_ternary_and_aggregate() -> None:
    """三元表达式、any/all、sum 的正确用法。"""
    print("\n【三元表达式与聚合函数】\n")

    # 三元表达式
    print("  三元表达式（条件表达式）：")
    for x in (5, -3):
        print(f"    {'偶数' if x % 2 == 0 else '奇数'} ← x={x}")
    print(f"    注意：'偶数' if ... else '奇数' 的条件表达式，返回【值】而不是布尔")

    # 三元 vs if-else 块
    def classify(n: int) -> str:
        if n < 0:
            return "负数"
        elif n == 0:
            return "零"
        else:
            return "正数"
    print(f"\n  ⭐ 三元表达式 vs if-else 块：")
    print(f"    简单二选一 → 用三元: {'负' if -1 > 0 else '非负'}")
    print(f"    多分支     → 用 if-else 块: {[classify(v) for v in (-5, 0, 5)]}")

    # any / all
    print("\n  【any / all】—— 短路求值：找到就停")
    data = [0, 0, 3, 0]
    print(f"    any([0,0,3,0]) = {any(data)}   至少一个为真")
    print(f"    all([0,0,3,0]) = {all(data)}   全部为真")
    print(f"    any([]) = {any([])}   ⚠️ 空列表返回 False")
    print(f"    all([]) = {all([])}   ⚠️ 空列表返回 True（数学上的「空真」）")

    # 短路演示
    calls: list[int] = []

    def side_effect(x: int) -> bool:
        calls.append(x)
        return x > 2

    calls.clear()
    any(side_effect(x) for x in [1, 2, 5, 9])
    print(f"    any 短路演示：只处理了 {calls} → 找到 True 就停")

    calls.clear()
    all(side_effect(x) for x in [5, 6, 1, 9])
    print(f"    all 短路演示：只处理了 {calls} → 找到 False 就停")

    # sum 与聚合
    print("\n  【sum 等聚合函数】")
    nums = [1, 2, 3, 4]
    print(f"    sum(nums) = {sum(nums)}")
    print(f"    sum(nums, 10) = {sum(nums, 10)}   带起始值（等价于 10 + sum(nums)）")
    print(f"    max/min = {max(nums)} / {min(nums)}")
    print(f"    sum 与生成器：sum(x*x for x in range(5)) = {sum(x * x for x in range(5))}")
    print(f"    ⭐ 生成器版本【不占用内存】，数据量大时优先用")


# ============================================================
# 第 8 部分：itertools
# ============================================================
def demo_itertools() -> None:
    """itertools 的核心工具：chain / islice / groupby 等。"""
    print("\n【itertools 入门】\n")

    # chain：连接多个可迭代对象
    print("  【chain】—— 连接多个序列，不用写嵌套循环：")
    print(f"    list(chain([1,2], [3,4], [5])) = {list(chain([1, 2], [3, 4], [5]))}")
    print(f"    嵌套写法则需要 [[1,2],[3,4],[5]] 这样的中间列表 → 浪费内存")

    # islice：切片一个迭代器（不物化）
    print("\n  【islice】—— 给迭代器「切片」，不物化整个序列：")
    print(f"    islice(range(10), 3)      = {list(islice(range(10), 3))}")
    print(f"    islice(range(10), 3, 7)   = {list(islice(range(10), 3, 7))}")
    print(f"    islice(range(10), 2, 9, 2) = {list(islice(range(10), 2, 9, 2))}")
    print(f"    ⭐ 关键：对无限生成器也有效！list(islice(inf_gen, 5)) 不会死循环")

    # groupby：⚠️ 必须先排序！
    print("\n  【groupby】—— 分组，⚠️⚠️ 必须先排序才正确：")
    sorted_data = [("a", 1), ("a", 2), ("b", 3), ("b", 4), ("c", 5)]
    groups = [(k, [v for _, v in g]) for k, g in groupby(sorted_data, key=lambda x: x[0])]
    print(f"    排序后 groupby: {groups}   ✅ 正确")

    unsorted_data = [("b", 1), ("a", 2), ("b", 3)]
    wrong = [(k, len(list(g))) for k, g in groupby(unsorted_data, key=lambda x: x[0])]
    print(f"    未排序 groupby: {wrong}   ⚠️⚠️ 'b' 分成了【两组】！")
    print("       原因：groupby 只比较【相邻元素】，相同才归一组，不扫描全局。")

    # accumulate：累积
    print("\n  【accumulate】—— 累积求和/累积乘积：")
    print(f"    accumulate([1,2,3,4]) = {list(accumulate([1, 2, 3, 4]))}")
    print(f"    accumulate([1,2,3], lambda a,b: a*b) = "
          f"{list(accumulate([1, 2, 3], lambda a, b: a * b))}")

    # zip_longest：不等长时补 None
    print("\n  【zip_longest】—— 不等长时用指定值补齐：")
    a, b = [1, 2, 3], ["x", "y"]
    print(f"    zip_longest(a, b)         = {list(zip_longest(a, b))}")
    print(f"    zip_longest(a, b, fillvalue=0) = {list(zip_longest(a, b, fillvalue=0))}")

    # product：笛卡尔积
    print("\n  【product】—— 笛卡尔积：")
    print(f"    product('AB', repeat=2) = {list(product('AB', repeat=2))}")


# ============================================================
# 第 9 部分：什么时候用生成器，什么时候用列表
# ============================================================
def demo_when_to_use() -> None:
    """生成器 vs 列表的决策树。"""
    print("\n【什么时候用生成器，什么时候用列表】\n")

    print("  ┌────────────────────────────────────────────────────────┐")
    print("  │ 用【列表】当：                                        │")
    print("  │   • 数据量小（全都要）                                 │")
    print("  │   • 需要【反复遍历】（len、索引、切片）                │")
    print("  │   • 需要传入接受 list 的函数                           │")
    print("  │   • 需要排序（sorted）、反转、join                     │")
    print("  │                                                        │")
    print("  │ 用【生成器】当：                                     │")
    print("  │   • 数据量【大】且只要遍历一次（省内存）               │")
    print("  │   • 处理【无限序列】                                 │")
    print("  │   • 只需要【前几个】（islice / next）                 │")
    print("  │   • 【流式处理】：边读边算，不要中间结果               │")
    print("  │   • 嵌套生成器，避免多层中间列表                     │")
    print("  └────────────────────────────────────────────────────────┘")

    # 实际对比
    print("\n  【实际对比】查找前 5 个大于 100 万的平方：")
    data = range(1_000_000)

    # 用列表：要算完全部 100 万个
    t0 = time.perf_counter()
    squares_list = [x * x for x in data if x * x > 1_000_000]
    t1 = time.perf_counter()
    list_total = sum(squares_list)

    # 用生成器 + islice：只算到第 5 个就停
    t2 = time.perf_counter()
    squares_gen = islice((x * x for x in data if x * x > 1_000_000), 5)
    gen_total = sum(squares_gen)
    t3 = time.perf_counter()

    print(f"    列表版   : 算了 {len(squares_list):,} 个，耗时 {(t1 - t0) * 1000:.1f} ms")
    print(f"    生成器版 : 只算 5 个，耗时 {(t3 - t2) * 1000:.2f} ms")
    print(f"    ⭐ 快 {(t1 - t0) / max(t3 - t2, 1e-9):,.0f} 倍！只要 5 个却算了 100 万个，")
    print("       这就是「按需计算」的威力。")


# ============================================================
# 第 10 部分：自检断言
# ============================================================
def verify_iterable() -> None:
    """用断言验证本课所有关键结论。"""
    print("【自检断言】")

    # 迭代器协议
    data = [10, 20, 30]
    it = iter(data)
    assert next(it) == 10 and next(it) == 20
    try:
        next(it)
        next(it)                            # 再取一次 → 应抛
        raise AssertionError("耗尽后应该抛 StopIteration")
    except StopIteration:
        pass
    assert hasattr(data, "__iter__") and not hasattr(data, "__next__")
    assert hasattr(it, "__iter__") and hasattr(it, "__next__")
    assert iter(data) is not iter(data)     # 每次 iter 都是新对象

    # 一次性消费
    lst = [1, 2, 3]
    assert [x for x in lst] == [1, 2, 3]
    assert [x for x in lst] == [1, 2, 3]     # 列表可反复遍历
    gen = (x for x in [1, 2, 3])
    assert list(gen) == [1, 2, 3]
    assert list(gen) == []                   # ⚠️ 生成器只能一次

    # 自定义迭代器
    c = Countdown(3)
    assert list(c) == [1, 2, 3]
    assert list(c) == []                     # ⚠️ 也是一次性的
    assert c.__iter__() is c                 # __iter__ 返回 self

    # 生成器函数
    assert list(fibonacci(7)) == [0, 1, 1, 2, 3, 5, 8]
    gen_f = fibonacci(5)
    assert sys.getsizeof(gen_f) < 300        # ⭐ 生成器对象几乎不占空间

    # 惰性：无限序列
    inf = infinite()
    assert [next(inf) for _ in range(3)] == [0, 1, 2]

    # 生成器表达式 vs 列表推导式
    assert type([x for x in range(3)]).__name__ == "list"
    assert type((x for x in range(3))).__name__ == "generator"
    assert sys.getsizeof(i for i in range(10**6)) < 300

    # map/filter 返回迭代器
    assert isinstance(map(str, [1]), type(map(str, [2])))
    assert hasattr(map(str, [1]), "__next__")
    assert list(map(str, [1, 2])) == ["1", "2"]
    assert list(filter(None, [0, 1, 2])) == [1, 2]
    # 多序列 map
    assert list(map(lambda x, y: x + y, [1, 2], [10, 20])) == [11, 22]

    # 三元表达式
    assert ("偶" if 2 % 2 == 0 else "奇") == "偶"
    assert ("偶" if 3 % 2 == 0 else "奇") == "奇"

    # any / all：空集合的边界
    assert any([0, 1]) is True
    assert all([1, 1]) is True
    assert all([1, 0]) is False
    assert any([]) is False                   # ⚠️ 空列表 → False
    assert all([]) is True                    # ⚠️ 空列表 → True

    # 短路
    seen: list[int] = []
    any(seen.append(x) or x > 2 for x in [1, 2, 5, 9])
    assert seen == [1, 2, 5]                 # 找到 5 就停，没看 9

    # sum
    assert sum([1, 2, 3]) == 6
    assert sum([1, 2], 10) == 13              # start 参数
    assert sum(x * x for x in range(5)) == 30  # 生成器版本

    # itertools
    assert list(chain([1, 2], [3])) == [1, 2, 3]
    assert list(islice(range(10), 3)) == [0, 1, 2]
    assert list(islice(range(10), 3, 7)) == [3, 4, 5, 6]
    assert list(accumulate([1, 2, 3])) == [1, 3, 6]

    # ⚠️ groupby 必须先排序
    raw = [("b", 1), ("a", 2), ("b", 3)]
    naive = [(k, len(list(g))) for k, g in groupby(raw, key=lambda x: x[0])]
    assert len(naive) == 3                    # ⚠️ 'b' 被分成了两组
    ordered = sorted(raw)
    correct = [(k, len(list(g))) for k, g in groupby(ordered, key=lambda x: x[0])]
    assert len(correct) == 2                  # ✅ 排序后正确合并

    assert list(zip_longest([1, 2, 3], ["x"], fillvalue=0)) == \
        [(1, "x"), (2, 0), (3, 0)]

    print("✅ verify_iterable 全部断言通过")


# ============================================================
# 程序入口
# ============================================================
def main() -> None:
    """按教学顺序调用全部演示函数。"""
    print("=" * 64)
    print("L12 · 可迭代对象与生成器")
    print("=" * 64)
    demo_protocol()
    demo_one_shot()
    demo_custom_iterator()
    demo_yield()
    demo_generator_exp()
    demo_map_filter()
    demo_ternary_and_aggregate()
    demo_itertools()
    demo_when_to_use()
    print("\n" + "-" * 64)
    verify_iterable()
    print("\n🎉 L12 演示结束")


# 标准入口约定：直接运行本文件执行 main()，被 import 时不执行
if __name__ == "__main__":
    main()