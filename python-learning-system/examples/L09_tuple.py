"""L09 元组：不可变性与命名元组 —— 配套教案示例。

运行：python examples/L09_tuple.py

本脚本演示九件事：
    1. 元组的创建，以及「单元素元组必须带逗号」这个头号陷阱
    2. 元组的不可变性：为什么不能增删改，以及它带来的三个好处
    3. 元组与列表的取舍：内存、哈希性、能否当字典键
    4. 元组与列表的互相转换
    5. 元组作为字典键 / 集合元素，以及「哈希性」的判定规则
    6. 函数返回多值：返回元组并解包
    7. 解包语法：位置解包、星号解包、下划线占位、嵌套结构
    8. 命名元组 collections.namedtuple：既有可读性又不可变
    9. 常见坑：元组「不可变」但元素可能可变、单元素忘逗号、命名元组不能改字段

⚠️ 纯标准库，可直接运行。
"""

import copy                                   # 标准库：deepcopy 对比
import sys                                    # 标准库：getsizeof 内存对比
import time                                   # 标准库：创建速度对比
from collections import namedtuple            # 标准库：命名元组

# ============================================================
# 模块级常量
# ============================================================
BENCH_SIZE = 200_000                          # 性能对比的数据规模


# ============================================================
# 第 1 部分：创建与单元素元组的逗号陷阱
# ============================================================
def demo_create() -> None:
    """元组的创建方式，重点是单元素元组必须带逗号。"""
    print("【创建与单元素元组】\n")

    # 空元组：必须有逗号，否则 () 是空括号
    empty = ()
    empty2 = tuple()
    print(f"  () 的类型: {type(empty).__name__}, 长度 {len(empty)}")
    print(f"  tuple() 的类型: {type(empty2).__name__}   两者等价")

    # 单元素元组：⚠️ 必须带逗号！
    single = (1,)                             # ✅ 带逗号 = 单元素元组
    not_single = (1)                          # ❌ 带括号但没逗号 = 就是整数 1
    print(f"\n  (1,)  的类型: {type(single).__name__}, 长度 {len(single)}, 值 {single}")
    print(f"  (1)   的类型: {type(not_single).__name__}, 值 {not_single}   ⚠️ 它不是元组！")
    print(f"  (1) == 1 吗? {not_single == 1}   ← 所以判断元组别用 ==，要用 isinstance")

    # 为什么单元素元组必须带逗号：这是 Python 语法为了兼容括号表达式的遗留设计
    # (1) 在绝大多数语言里就是「加括号」，所以 Python 不能改变这个含义
    print("\n  为什么必须带逗号：")
    print("    在 C/Java 里 (1) 就是整数 1，Python 必须保持这个兼容性，")
    print("    所以 (1) 只能是整数；要表示「一个元素的元组」就必须用 (1,) 引入逗号。")

    # 多元素元组
    multi = (1, 2, 3)
    print(f"\n  多元素 (1, 2, 3) 的类型: {type(multi).__name__}, 长度 {len(multi)}")

    # 不带括号的逗号表达式：赋值时右侧的逗号让右边变成元组
    a = 1, 2                                   # ✅ 等价于 (1, 2)
    print(f"  a = 1, 2  →  {a}   类型 {type(a).__name__}   （右侧逗号让 a 成为元组）")
    print(f"  ⚠️ 但函数调用里的逗号是【参数分隔】，不是元组：")
    print(f"     f(1, 2) 表示传两个参数，不是传一个元组")


# ============================================================
# 第 2 部分：不可变性
# ============================================================
def demo_immutable() -> None:
    """元组不能增删改，尝试会抛 AttributeError。"""
    print("\n【不可变性】\n")

    t = (1, 2, 3)
    print(f"  原元组: {t}")

    # 三种修改尝试都会失败
    for desc, action in [
        ("t[0] = 99", lambda: t.__setitem__(0, 99)),
        ("t.append(4)", lambda: t.append(4)),
        ("del t[0]", lambda: t.__delitem__(0)),
    ]:
        try:
            action()
            print(f"  ⚠️ {desc} 竟然成功了？")
        except AttributeError as exc:
            print(f"  {desc:<14} → AttributeError: {exc}")

    # 可用的只读方法
    print(f"\n  元组只有只读方法：")
    print(f"    t.count(2)  = {t.count(2)}")
    print(f"    t.index(2)  = {t.index(2)}")
    print(f"    len(t)      = {len(t)}")
    print(f"    t[::-1]     = {t[::-1]}   ← 切片返回【新元组】，不改原对象")
    print(f"    元组有 .append 吗? {hasattr(t, 'append')}   没有")

    # ⭐ 不可变性带来的三个好处（后面逐个演示）
    print("\n  ⭐ 不可变性带来的三个好处：")
    print("    1. 可哈希 → 能当字典键和集合元素")
    print("    2. 可安全共享 → 多个地方引用同一份，不可能被谁改坏")
    print("    3. 可作默认参数 → 不会像列表那样被后续调用污染")


# ============================================================
# 第 3 部分：元组与列表的取舍
# ============================================================
def demo_tuple_vs_list() -> None:
    """元组更小、更快、可哈希；列表更灵活。"""
    print("【元组与列表的取舍】\n")

    tup = tuple(range(BENCH_SIZE))
    lst = list(tup)

    # ⭐ 内存对比：必须说清楚「差异来自哪里」，否则容易得出错误结论
    # 实测结论：只有「逐个 append」构建的列表才会超额分配；
    # 用 list(range(...)) 这种「已知长度」的构造，列表是精确尺寸，此时和元组几乎一样大。
    built_by_append: list[int] = []
    for i in range(BENCH_SIZE):
        built_by_append.append(i)

    t_size = sys.getsizeof(tup)
    exact_size = sys.getsizeof(lst)
    append_size = sys.getsizeof(built_by_append)
    print(f"  {BENCH_SIZE} 个元素时：")
    print(f"    元组                        : {t_size:,} 字节")
    print(f"    列表 list(tuple)（精确尺寸）: {exact_size:,} 字节  差 {exact_size - t_size} 字节")
    print(f"    列表逐个 append（超额分配） : {append_size:,} 字节  "
          f"差 {append_size - t_size:,} 字节")
    print("\n  ⭐ 别急着下结论「列表一定大很多」，真实情况是：")
    print("    · 元组长度固定，底层内存永远「刚刚好」；")
    print("    · 列表如果是用 append 一点点长起来的，会预留约 12% 的空闲空间；")
    print("    · 但如果用 list(range(...)) 这种已知长度的构造，列表也是精确尺寸，两者几乎一样。")
    print("  所以元组「更省内存」的真正收益在【小而多的对象】上（每个省几十字节），")
    print("  而不是「大列表」上——大列表两者都受 8 字节/元素 + 56 字节对象头支配。")

    # 小对象场景才是元组的真正优势
    small_t = tuple(range(10))
    small_l = list(range(10))
    print(f"\n  小对象（10 元素）更能说明问题：")
    print(f"    元组: {sys.getsizeof(small_t)} 字节, 列表: {sys.getsizeof(small_l)} 字节, "
          f"差 {sys.getsizeof(small_l) - sys.getsizeof(small_t)} 字节/个")

    # 创建速度对比
    t0 = time.perf_counter()
    _ = [tuple(range(BENCH_SIZE)) for _ in range(20)]
    t1 = time.perf_counter()
    _ = [list(range(BENCH_SIZE)) for _ in range(20)]
    t2 = time.perf_counter()
    print(f"\n  创建 20 个 {BENCH_SIZE} 元素的容器：")
    print(f"    tuple: {(t1 - t0) * 1000:.1f} ms")
    print(f"    list : {(t2 - t1) * 1000:.1f} ms")
    print(f"  元组更快：因为不用考虑「以后还要不要加元素」的扩容问题")

    # ⭐ 可哈希性对比：这是最关键的区别
    print("\n  ⭐ 可哈希性（能不能当字典键 / 集合元素）：")
    print(f"    hash((1, 2))      = {hash((1, 2))}   元组可哈希 ✅")
    try:
        hash([1, 2])
    except TypeError as exc:
        print(f"    hash([1, 2])      → TypeError: {exc}   列表不可哈希 ⚠️")

    # 列表要当键必须转成元组
    try:
        _ = {[1, 2]: "a"}                     # ❌ 直接报错
    except TypeError as exc:
        print(f"\n  列表当字典键 {{[1, 2]: 'a'}} → TypeError: {exc}")
    print(f"  转成元组即可: { {tuple([1, 2]): 'a'} }")


# ============================================================
# 第 4 部分：元组与列表互转
# ============================================================
def demo_convert() -> None:
    """tuple(x) 和 list(x) 互转，以及 zip 的返回值。"""
    print("\n【元组与列表互转】\n")

    lst = [1, 2, 3]
    tpl = tuple(lst)
    back = list(tpl)
    print(f"  list → tuple: {lst} → {tpl}   类型 {type(tpl).__name__}")
    print(f"  tuple → list: {tpl} → {back}   类型 {type(back).__name__}")

    # ⭐ zip 返回的正是「元组」——这是 L07 讲过的
    pairs = list(zip(["a", "b"], [1, 2]))
    print(f"\n  list(zip(...)) = {pairs}")
    print(f"  ⚠️ 元素类型: {type(pairs[0]).__name__}   zip 每次产出一个元组")

    # zip 的两种解包写法
    names = ["张三", "李四"]
    scores = [88, 92]
    (n1, n2), (s1, s2) = zip(names, scores)   # 直接解包两层
    print(f"  (n1, n2), (s1, s2) = zip(...) → {n1}, {n2}, {s1}, {s2}")

    # 转成 tuple 再当键用的实战
    locations = {("北京", 39.9): "BJ", ("上海", 31.2): "SH"}
    print(f"\n  用 (城市, 纬度) 元组当字典键: {locations[('上海', 31.2)]}")
    print(f"  为什么用元组？因为 (城市, 纬度) 是一个不可变的「复合标识」")


# ============================================================
# 第 5 部分：元组作为字典键和集合元素
# ============================================================
def demo_as_key() -> None:
    """元组可哈希，所以能当字典键和集合元素。"""
    print("\n【元组当字典键 / 集合元素】\n")

    # 字典键
    cache = {}
    cache[(1, 2)] = "坐标 A"
    cache[(3, 4)] = "坐标 B"
    print(f"  字典: {cache}")
    print(f"  cache[(1, 2)] = {cache[(1, 2)]}   O(1) 查到")

    # 集合元素
    unvisited = {(0, 0), (1, 1), (2, 2), (0, 0)}
    print(f"  集合: {unvisited}   注意 (0, 0) 只出现一次（自动去重）")

    # ⭐ 哈希性的判定规则：元素全都可哈希，元组才可哈希
    print("\n  ⭐ 判定规则（元组可哈希 ⟺ 所有元素都可哈希）：")
    cases = [
        ("(1, 2, 3)", (1, 2, 3), "数字都是不可变 → 可哈希"),
        ("('a', 'b')", ("a", "b"), "字符串不可变 → 可哈希"),
        ("((1, 2), (3, 4))", ((1, 2), (3, 4)), "嵌套的元组也可哈希"),
        ("([1], 2)", ([1], 2), "含列表 → ⚠️ 不可哈希"),
    ]
    for name, obj, note in cases:
        try:
            h = hash(obj)
            print(f"    {name:<16} hash={h:<22} {note}")
        except TypeError as exc:
            print(f"    {name:<16} {exc}   {note}")

    # 反例演示：含列表的元组不能当键
    try:
        bad = {([1], 2): "x"}
    except TypeError as exc:
        print(f"\n  ⚠️ 但 {{([1], 2): 'x'}} 会报错: {exc}")


# ============================================================
# 第 6、7 部分：函数返回多值与解包
# ============================================================
def demo_multi_return() -> None:
    """函数返回多值，返回的其实是「一个元组」。"""
    print("\n【函数返回多值与解包】\n")

    # 返回多个值：其实返回的是元组
    def get_min_max(data: list[int]) -> tuple[int, int]:
        """返回最小值和最大值——本质是返回一个元组。"""
        return min(data), max(data)

    nums = [5, 2, 9, 1, 7]
    result = get_min_max(nums)
    print(f"  get_min_max({nums}) 返回: {result}   类型 {type(result).__name__}")

    # 解包的四种用法
    lo, hi = result                                   # 1. 位置解包
    print(f"  1. lo, hi = result                → lo={lo}, hi={hi}")

    lo, _ = result                                    # 2. 下划线占位不关心的
    print(f"  2. lo, _ = result                 → lo={lo}（不关心 hi）")

    first, *rest = [1, 2, 3, 4]                      # 3. 星号收集剩下的
    print(f"  3. first, *rest = [1,2,3,4]        → first={first}, rest={rest}")

    a, (b, c) = 1, (2, 3)                            # 4. 嵌套解包
    print(f"  4. a, (b, c) = 1, (2, 3)           → a={a}, b={b}, c={c}")

    # ⚠️ 解包数量不匹配会报错
    try:
        x, y, z = result
    except ValueError as exc:
        print(f"\n  ⚠️ x, y, z = result → ValueError: {exc}   ← 右边只有 2 个值")

    # 用星号丢弃不关心的（3.10+）
    head, *_ = result
    print(f"  head, *_ = result → {head}   （星号丢弃剩下的）")


# ============================================================
# 第 8 部分：命名元组
# ============================================================
def demo_namedtuple() -> None:
    """namedtuple 给元组的每个位置起名字，兼得可读性与不可变性。"""
    print("\n【命名元组 collections.namedtuple】\n")

    # 定义一个命名元组类型
    Point = namedtuple("Point", ["x", "y"])          # 传统写法
    p = Point(3, 4)
    print(f"  Point(3, 4) = {p}")
    print(f"  p.x = {p.x}, p.y = {p.y}       ← 可以用属性访问")
    print(f"  p[0] = {p[0]}, p[1] = {p[1]}       ← 仍然是元组，可以下标")

    # 等价的现代写法（更简洁，Python 3.6.1+）
    Color = namedtuple("Color", field_names=["red", "green", "blue"])
    c = Color(255, 128, 0)
    print(f"\n  Color(255, 128, 0) = {c}")
    print(f"  c.red = {c.red}")

    # ⭐ 为什么它比普通元组好：可读性
    plain = (3, 4)
    print("\n  ⭐ 可读性对比：")
    print(f"    普通元组 p = {plain}   → 要靠注释才知道 3 是 x 还是 y")
    print(f"    命名元组 p = {p}   → 一眼看出 x=3, y=4")

    # _asdict / _replace / _fields
    print("\n  常用辅助方法：")
    print(f"    p._asdict()  = {p._asdict()}   转成字典")
    print(f"    p._replace(x=10) = {p._replace(x=10)}   基于它造新对象")
    print(f"    p._fields   = {p._fields}   字段名元组")
    print(f"    p[0]        = {p[0]}   依然支持索引和切片")

    # ⚠️ 命名元组也是不可变的
    try:
        p.x = 99
    except AttributeError as exc:
        print(f"\n  ⚠️ p.x = 99 → AttributeError: {exc}   命名元组不可变")
    print(f"  但 _replace 返回新对象，原对象不变: p 仍是 {p}")

    # 能当字典键
    registry = {Point(0, 0): "原点", Point(1, 1): "对角点"}
    print(f"\n  能当字典键: {registry[Point(0, 0)]}")
    print(f"  __eq__ 是按值比较: {Point(1, 2) == (1, 2)}   和普通元组行为一致")


# ============================================================
# 第 9 部分：常见坑
# ============================================================
def demo_pitfalls() -> None:
    """本节把元组最容易踩的坑集中跑一遍。"""
    print("\n【常见坑集中演示】\n")

    # 坑 1：单元素元组忘逗号
    print("  坑 1：单元素元组忘逗号")
    bad = (42)                                     # ❌ 这是整数
    good = (42,)                                   # ✅ 这才是元组
    print(f"     (42)  → {bad!r}, 类型 {type(bad).__name__}，不是元组")
    print(f"     (42,) → {good!r}, 类型 {type(good).__name__}, 长度 {len(good)}")
    print(f"     函数返回时更隐蔽：")

    def f1() -> int:                             # ❌ 忘了逗号，返回的是整数
        return 5

    def f2() -> tuple[int]:                      # ✅ 带逗号，返回单元素元组
        return (5,)

    print(f"        def f1(): return 5    → 返回 {f1()!r}，类型 {type(f1()).__name__} ❌")
    print(f"        def f2(): return (5,) → 返回 {f2()!r}，类型 {type(f2()).__name__} ✅")
    print(f"     ⚠️ 这个 bug 极隐蔽：调用方 a, b = f1() 会直接报 ValueError")

    # 坑 2：元组「不可变」但元素可能可变
    print("\n  坑 2：元组不可变 ≠ 内容完全不变")
    t = ([1, 2], [3, 4])                           # 元素是两个列表
    print(f"     t = ({t[0]}, {t[1]})   元组本身不可变")
    try:
        t[0] = [9]
    except TypeError as exc:
        print(f"     t[0] = [9] → TypeError: {exc}   ← 换不了元素")
    t[0].append(99)                                # 但能改元素的内容！
    print(f"     t[0].append(99) 后 t = {t}   ⚠️ 内容还是变了！")

    # 深拷贝也不能让元组里的列表变不可变
    deep = copy.deepcopy(t)
    print(f"     deepcopy 后修改内部列表: ", end="")
    deep[1].append(77)
    print(f"原 t 不受影响 = {t[1]}，deep 变成 {deep[1]}")

    # 坑 3：不可变元组当默认参数是安全的，列表则不是
    print("\n  坑 3：默认参数用元组安全，用列表会出事")

    def with_list_default(items: list[int] = []) -> list[int]:
        """⚠️ 默认列表在【函数定义时】只创建一次，会被所有调用共享！"""
        items.append(99)
        return items

    print(f"     第1次调用 with_list_default() = {with_list_default()}")
    print(f"     第2次调用 with_list_default() = {with_list_default()}   ⚠️ 越积越多！")

    def with_tuple_default(items: tuple[int, ...] = ()) -> tuple[int, ...]:
        """✅ 默认元组不可变，每次调用都不会互相影响。"""
        return items + (99,)

    print(f"     元组版第1次 = {with_tuple_default()}")
    print(f"     元组版第2次 = {with_tuple_default()}   ✅ 互不影响")

    # 坑 4：命名元组不能改，也不能随意加字段
    print("\n  坑 4：命名元组「不能改」也不能「加」")
    P2 = namedtuple("P2", ["x", "y"])
    q = P2(1, 2)
    print(f"     P2(1, 2)._fields = {q._fields}   字段固定，不能动态加")
    print(f"     需要加字段 → 用 _replace 造一个新的，或用 dataclasses（阶段四）")


# ============================================================
# 第 10 部分：自检断言
# ============================================================
def verify_tuple() -> None:
    """用断言验证本课所有关键结论，防止示例与文档说法不一致。"""
    print("【自检断言】")

    # 单元素元组的逗号
    assert isinstance((1,), tuple)
    assert not isinstance((1), tuple)              # ⚠️ (1) 就是整数
    assert isinstance((), tuple) and len(()) == 0
    assert (1, 2, 3) == tuple([1, 2, 3])
    # ⚠️ 注意：不能写 assert (1, 2) == (1, 2)
    #    裸元组的逗号在「调用」里是参数分隔，会被解析成 assert (cond, "message")
    x = 1, 2                                      # 赋值时逗号让 x 成为元组
    assert x == (1, 2)

    # 不可变性
    t = (1, 2, 3)
    assert t.count(2) == 1 and t.index(2) == 1
    assert t[::-1] == (3, 2, 1)
    assert t == (1, 2, 3)                          # 切片不改原元组
    try:
        t[0] = 9
        raise AssertionError("元组竟然可赋值")
    except TypeError:
        pass

    # 可哈希性
    assert hash((1, 2)) == hash((1, 2))            # 可哈希 → 能当键
    assert {("a", 1): "v"}[("a", 1)] == "v"
    try:
        hash([1, 2])
        raise AssertionError("列表竟然可哈希")
    except TypeError:
        pass
    try:
        hash(([1], 2))                             # 含列表的元组也不可哈希
        raise AssertionError("含列表的元组竟然可哈希")
    except TypeError:
        pass

    # 多返回值与解包
    lo, hi = min([3, 1, 2]), max([3, 1, 2])
    assert (lo, hi) == (1, 3)
    first, *rest = [1, 2, 3, 4]
    assert first == 1 and rest == [2, 3, 4]
    a, (b, c) = 1, (2, 3)
    assert (a, b, c) == (1, 2, 3)
    try:
        _, _, _ = (1, 2)
        raise AssertionError("解包数量不匹配居然没报错")
    except ValueError:
        pass

    # 命名元组
    Point = namedtuple("Point", ["x", "y"])
    p = Point(3, 4)
    assert p.x == 3 and p[0] == 3 and p[1] == 4
    assert p._asdict() == {"x": 3, "y": 4}
    assert p._replace(x=10).x == 10 and p.x == 3   # _replace 不改原对象
    assert p == (3, 4)                              # 和普通元组按值相等
    assert Point(0, 0) != Point(1, 1)
    try:
        p.x = 99
        raise AssertionError("命名元组竟然可修改")
    except AttributeError:
        pass

    # ⭐ 元素可变时，元组的「不可变」是有限的
    nested = ([1], [2])
    nested[0].append(9)
    assert nested == ([1, 9], [2])                 # 元组本身没变，但内容变了

    # zip 返回元组
    assert list(zip([1, 2], [3, 4])) == [(1, 3), (2, 4)]
    assert isinstance(list(zip([1], [2]))[0], tuple)

    print("✅ verify_tuple 全部断言通过")


# ============================================================
# 程序入口
# ============================================================
def main() -> None:
    """按教学顺序调用全部演示函数。"""
    print("=" * 64)
    print("L09 · 元组：不可变性与命名元组")
    print("=" * 64)
    demo_create()
    demo_immutable()
    demo_tuple_vs_list()
    demo_convert()
    demo_as_key()
    demo_multi_return()
    demo_namedtuple()
    demo_pitfalls()
    print("\n" + "-" * 64)
    verify_tuple()
    print("\n🎉 L09 演示结束")


# 标准入口约定：直接运行本文件执行 main()，被 import 时不执行
if __name__ == "__main__":
    main()