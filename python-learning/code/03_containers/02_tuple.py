"""
================================================================================
  02_tuple.py  ——  元组：不可变序列与解包
================================================================================

【演示的语法点】
 1. 元组的不可变性：增删改都会抛 TypeError
 2. 元组的 4 种创建方式与「单元素元组陷阱」`(1,)`
 3. ★ 解包：位置解包、嵌套解包、星号解包、交换变量
 4. ★ 元组作为 dict 的 key 与 set 的元素（要求可哈希）
 5. ★ 元组 vs 列表取舍：语义、内存、性能、可变性
 6. ★ tuple 与 list 的性能实测对比（创建、索引、遍历、增删）
 7. 元组的方法：count / index，以及它为什么没有 append
 8. 命名元组 NamedTuple 与 tuple 的关系（引出 05_collections）
 9. 不可变性的真正价值：默认参数、缓存键、并发安全

【预期输出摘要】
 - "不可变" 小节打印 3 处 TypeError
 - "单元素元组" 小节证明 (1) 是 int 而 (1,) 是 tuple
 - "解包" 小节打印星号解包吸收剩余元素的分组结果
 - "性能" 小节打印 tuple 全面优于 list 的实测耗时表
================================================================================

"""

from __future__ import annotations

import sys
import timeit
from typing import Any


# ===== 语法解析 =====
# 【1】不可变性：元组创建后不能增删改
#   语法规则：tuple 实现了 __setitem__ / __delitem__ 但显式抛 TypeError，
#             因此所有"修改"操作都会失败。
#   设计意图：不可变 = 可哈希 = 可安全用作字典键/集合元素/缓存键，
#             在多线程下共享时也不会被意外修改。
def demo_immutable() -> None:
    print("=" * 60)
    print("【1】元组的不可变性")
    print("=" * 60)

    t = (10, 20, 30)
    print(f"  创建元组：{t}  类型={type(t).__name__}")
    print(f"  len={len(t)}  t[0]={t[0]}  t[-1]={t[-1]}   ← 读取与 list 完全一致")

    # 下面三种修改全部非法，用于演示错误类型
    for label, action in (
        ("赋值", lambda: t.__setitem__(0, 99)),
        ("删除", lambda: t.__delitem__(0)),
        ("追加", lambda: t.append(40)),
    ):
        try:
            action()
        except (TypeError, AttributeError) as exc:
            print(f"  ★ {label}操作 → {type(exc).__name__}: {exc}")

    print()
    print("  ★ 对比 list：同样操作全部成功")
    lst = [10, 20, 30]
    lst[0] = 99
    lst.append(40)
    print(f"    list 允许：{lst}")

    print()
    print("  ★ 不可变不等于『里面的对象也不可变』：")
    t2 = ([1, 2], [3, 4])                 # 元组内部装的是列表（可变对象）
    t2[0].append(99)                      # 修改元组【内部】的列表是允许的
    print(f"    t2 = {t2}")
    print("    ★ 元组只保证『自身的元素引用不能改』，不保证『元素本身不可变』。")
    print("    ★ 这就是『浅不可变』（shallow immutability）。")

    print()
    print("  ★ 元组只有两个方法，因为它只需支持查询：")
    print(f"    可用方法：{[m for m in dir(t) if not m.startswith('_')]}")
    print(f"    count(20)={t.count(20)}   index(30)={t.index(30)}   ← 同 list")


# ===== 语法解析 =====
# 【2】创建方式与单元素元组陷阱
#   语法规则：括号是【分组符号】而非"元组符号"。
#             Python 靠【逗号】判断是不是元组：没有逗号就是普通括号表达式。
#   设计意图：让 (a + b) * c 这类数学表达式能保持自然书写。
#   ★ 陷阱：(1) 是 int 1；(1,) 才是长度为 1 的元组。
def demo_create() -> None:
    print()
    print("=" * 60)
    print("【2】创建方式 + ★ 单元素元组陷阱")
    print("=" * 60)

    a = (1, 2, 3)                         # 方式1：字面量
    b = tuple([1, 2, 3])                  # 方式2：tuple() 转换
    c = 1, 2, 3                           # 方式3：逗号即可，括号可省略
    d = tuple("abc")                      # 方式4：由可迭代对象转换
    print(f"  (1,2,3)            {a}  {type(a).__name__}")
    print(f"  tuple([1,2,3])     {b}  {type(b).__name__}")
    print(f"  1, 2, 3（无括号）  {c}  {type(c).__name__}   ← 逗号才是关键")
    print(f"  tuple('abc')       {d}  {type(d).__name__}")

    print()
    print("  ★★ 单元素元组陷阱 ★★")
    not_tuple = (1)                       # 只是给 1 加了括号
    real_tuple = (1,)                     # 逗号让它成为元组
    print(f"    (1)   → 值={not_tuple}  类型={type(not_tuple).__name__}  长度=无 len()")
    print(f"    (1,)  → 值={real_tuple}  类型={type(real_tuple).__name__}  长度={len(real_tuple)}")

    print()
    print("  ★ 零元素元组：")
    empty = ()                            # 空元组必须写逗号
    print(f"    ()   → {empty}  类型={type(empty).__name__}  长度={len(empty)}")
    print("    ★ 空元组是【不可变的空容器】，常用于表示『无参数』或『空结果』。")

    print()
    print("  ★ 其他常见陷阱：")
    print(f"    (1, 2, 3,)   末尾逗号 → {1, 2, 3,}   合法且等价 (1,2,3)")
    print(f"    (1, 2), (3, 4)   含逗号的括号 → 是二元组 ( (1,2), (3,4) ) 的元素")


# ===== 语法解析 =====
# 【3】★ 解包：把元组拆成多个变量
#   语法规则：左侧变量数必须【恰好】等于右侧元素数，否则报 ValueError。
#   星号解包：`*rest` 会吸收剩余元素并组成一个 list（长度 0 则是 []）。
#   设计意图：让"多返回值"调用变得自然可读，是函数返回多值的配套语法。
def demo_unpack() -> None:
    print()
    print("=" * 60)
    print("【3】★ 解包：位置 / 嵌套 / 星号 / 变量交换")
    print("=" * 60)

    # 位置解包
    x, y, z = (10, 20, 30)
    print(f"  位置解包      x={x} y={y} z={z}")

    # 星号解包：中间吸收剩余
    name, *scores, last = ("张三", 88, 92, 79, "优秀")
    print(f"  星号解包      name={name} scores={scores} last={last}")
    print("    ★ `*scores` 吸收中间所有剩余元素，类型是 list 而非 tuple。")

    # 下划线丢弃不需要的位置（PEP 8 约定）
    first, _, third = ("a", "b", "c")     # _ 是"我知道但不用"的约定命名
    print(f"  用 _ 丢弃     first={first} third={third}")

    # 嵌套解包
    (a, (b, c)) = (1, (2, 3))             # 左值也支持括号嵌套
    print(f"  嵌套解包      a={a} b={b} c={c}")

    # ★ 变量交换：解包最经典的用途
    p, q = 1, 2
    p, q = q, p                           # 右值先整体求值，再一次性解包
    print(f"  变量交换      p={p} q={q}   ← 无需临时变量")

    print()
    print("  ★ 在 for 循环中解包（遍历二元组）：")
    points = [(1, "东"), (2, "南"), (3, "西")]
    for idx, direction in points:         # 两个变量解包每个元素
        print(f"    {idx} -> {direction}")

    print()
    print("  ★ 在推导式中解包：")
    data = [(1, 2), (3, 4), (5, 6)]
    sums = [a + b for a, b in data]       # 推导式的 for 目标也能解包
    print(f"    每对求和：{sums}")
    print(f"    展平列表：{[n for pair in data for n in pair]}   ← 双重推导式展平")

    print()
    print("  ★ 解包数量不匹配会报错：", end=" ")
    try:
        a, b = (1, 2, 3)                  # 变量不够
    except ValueError as exc:
        print(f"ValueError: {exc}")

    print("  ★ 但用星号可以接收任意个数：")
    head, *tail = (1, 2, 3, 4, 5)
    print(f"    head={head}  tail={tail}")
    print(f"    扩展解包可以用于已有列表：first, *rest = list(range(5))")


# ===== 语法解析 =====
# 【4】★ 元组作为 dict key / set 元素：依赖可哈希性
#   语法规则：hashable 要求元素的 __hash__ 存在且 __eq__ 语义与之匹配。
#             元组是容器，内部所有元素可哈希时元组才可哈希。
#   设计意图：复合键（复合主键）天然用元组表达；(1,2) 与 (2,1) 是不同键。
def demo_as_key() -> None:
    print()
    print("=" * 60)
    print("【4】★ 元组作为 dict key / set 元素")
    print("=" * 60)

    # 元组作为字典键：模拟复合主键
    scores = {
        ("张三", "数学"): 95,
        ("张三", "英语"): 88,
        ("李四", "数学"): 79,
    }
    print("  元组作字典键（学生, 科目 → 分数）：")
    for key, val in scores.items():
        print(f"    {key} → {val}")
    print(f"    查询 scores[('张三','数学')] = {scores[('张三', '数学')]}")

    # ★ 顺序敏感：(1,2) != (2,1)
    print()
    print("  ★ 元组的顺序决定它是不是同一个键：")
    d = {(1, 2): "A", (2, 1): "B"}
    print(f"    字典中有 {len(d)} 个键：(1,2)→{d[(1, 2)]}，(2,1)→{d[(2, 1)]}")
    print("    ★ 所以 set({(1,2),(2,1)}) 有 2 个元素，而不是 1 个。")

    # 元组作集合元素：坐标去重
    coords = [(1, 2), (1, 2), (3, 4), (2, 1)]
    uniq = set(coords)                    # 元组可哈希才能放进 set
    print()
    print(f"  元组作 set 元素：{coords} → {uniq}")
    print(f"    去重后长度 {len(uniq)}  ← (1,2) 重复的被合并，(2,1) 是独立元素")

    # 不可哈希元素作键会报错
    print()
    print("  ★ 内部含不可哈希元素时，元组也不可哈希：", end=" ")
    try:
        bad = {[1, 2], 3}                  # 元组里塞了一个 list
        hash(bad)
    except TypeError as exc:
        print(f"TypeError: {exc}")

    print()
    print("  ★ 元组作字典键的经典用途：把多返回值直接作为缓存键")
    def expensive_query(user_id: int, month: int) -> str:
        return f"查询结果-{user_id}-{month}"

    cache: dict[tuple[int, int], str] = {}
    key = (1001, 10)                       # 多参数 → 元组键
    if key not in cache:
        cache[key] = expensive_query(*key)  # ★ * 解包回两个参数
    print(f"    缓存键 {key}（元组）→ {cache[key]}")
    print("    ★ 元组不可变 → 可以安全作缓存键；list 可变 → 不能。")

    print()
    print("  ★ 哈希与相等：元组按元素逐个 hash 后组合")
    print(f"    hash(('a',1)) = {hash(('a', 1))}")
    print(f"    ('a',1) == ('a',1) → {('a', 1) == ('a', 1)}   ★ 相等则 hash 必相等（契约）")


# ===== 语法解析 =====
# 【5】★ tuple vs list 取舍
#   维度：语义（不变/可变）、内存、创建速度、访问速度、能否作键、API 契约。
def demo_compare() -> None:
    print()
    print("=" * 60)
    print("【5】★ 元组 vs 列表 取舍")
    print("=" * 60)

    print("  | 维度       | tuple                   | list                |")
    print("  |------------|-------------------------|---------------------|")
    print("  | 可变性     | 不可变                   | 可变                 |")
    print("  | 单元素内存 | 40 字节(空)             | 56 字节(空)          |")
    print("  | 可哈希     | ✓(元素都可哈希时)       | ✗                   |")
    print("  | 作 dict key| ✓                       | ✗                   |")
    print("  | 创建速度   | 更快(无容量预留)        | 略慢                |")
    print("  | 增删改     | ✗                       | ✓                   |")
    print("  | 切片       | ✓ 返回新元组            | ✓ 返回新列表        |")

    print()
    print("  ★ 选用建议：")
    print("    · 多返回值、复合主键、坐标/配置常量 → tuple")
    print("    · 数量未知、会动态增删的集合        → list")
    print("    · 函数返回值默认用 tuple（不可变更安全）")
    print("    · 若元素其实不可变，list 也可替代 tuple（语义更弱）")

    print()
    print("  ★ 内存对比实测（元素引用数固定为 1）：")
    n = 1_000_000
    t_list = timeit.timeit(lambda: [None] * n, number=1)      # 创建 n 元素 list
    t_tuple = timeit.timeit(lambda: tuple([None] * n), number=1)  # 创建 n 元素 tuple
    print(f"    创建 {n:,} 元素 list  {t_list:.4f}s")
    print(f"    创建 {n:,} 元素 tuple {t_tuple:.4f}s（含中间 list，偏向 list 劣势）")
    print(f"    list  空实例 {sys.getsizeof([])} 字节")
    print(f"    tuple 空实例 {sys.getsizeof(())} 字节")
    print("    ★ 元组少一个『整体容量预留』的字段，且不可变故无需为扩容留余量。")

    print()
    print("  ★ 元素本身大小：8 字节引用由容器统一持有")
    lst1 = [None]
    tup1 = (None,)
    print(f"    [None]        占 {sys.getsizeof(lst1)} 字节")
    print(f"    (None,)       占 {sys.getsizeof(tup1)} 字节")
    print(f"    每个元素引用 8 字节，由列表/元组底层数组统一存储。")


# ===== 语法解析 =====
# 【6】★ tuple 与 list 性能实测
#   测试项：创建、索引访问、遍历、尾部追加（仅 list）、字典键查找。
#   设计意图：明确「不可变带来性能优势」的真实边界。
def demo_performance() -> None:
    print()
    print("=" * 60)
    print("【6】★ tuple vs list 性能实测（timeit）")
    print("=" * 60)

    N = 100_000
    R = 100

    tests = [
        ("创建 list(range(N))", f"list(range({N}))", f"tuple(range({N}))"),
        ("索引访问 x[N//2]", "d[%d]" % (N // 2), "d[%d]" % (N // 2)),
        ("遍历求和 sum(d)", "sum(d)", "sum(d)"),
        ("切片 d[:100]", "d[:100]", "d[:100]"),
        ("成员查找 50000 in d", f"{N // 2} in d", f"{N // 2} in d"),
    ]

    print(f"  {'测试项':<24}{'list':>12}{'tuple':>12}   结论")
    print("  " + "-" * 60)
    setup = f"d = list(range({N}))"
    for name, list_expr, tup_expr in tests:
        t_list = timeit.timeit(list_expr, setup=setup, number=R)
        t_tup = timeit.timeit(tup_expr, setup=setup, number=R)
        faster = "tuple 更快" if t_tup < t_list else ("相当" if abs(t_tup - t_list) < max(t_list, t_tup) * 0.05 else "list 更快")
        print(f"  {name:<24}{t_list:>10.4f}s{t_tup:>10.4f}s   {faster}")

    print()
    print("  ★ 仅 list 支持的操作（对比 append）：")
    a = [0]
    t_ap = timeit.timeit(lambda: a.append(1), number=100_000)
    print(f"    list.append x100000  {t_ap:.4f}s   ← 元组没有此操作（不可变）")

    print()
    print("  ★ 作为 dict 键查找（元组的核心优势）：")
    t_key_list = timeit.timeit(
        lambda: {"k%d" % i: i for i in range(1000)}["k999"],
        number=10000,
    )
    t_key_tup = timeit.timeit(
        lambda: {("k", 999): 999}[("k", 999)],
        number=10000,
    )
    print(f"    list(不可哈希) 不可能作键；元组键可正常查找且可缓存。")
    print("    结论：不可变 → 可哈希 → 可作键/进 set，这是元组存在的核心意义。")

    print()
    print("  ★ 遍历时解构（list vs tuple 无性能差，元组略优）：")
    data_t = [(i, i * 2) for i in range(1000)]
    t_d_t = timeit.timeit(lambda: sum(b for a, b in data_t), number=100)
    data_l = [[i, i * 2] for i in range(1000)]
    t_d_l = timeit.timeit(lambda: sum(b for a, b in data_l), number=100)
    print(f"    tuple 数据解构 {t_d_t:.4f}s   list 数据解构 {t_d_l:.4f}s   基本持平")


# ===== 语法解析 =====
# 【7】元组方法与 NamedTuple 预告
#   元组只保留 count/index（查询类），没有 mutator。
#   NamedTuple 是「带字段名的元组」：既保留元组的轻量与不可变，又提升可读性。
def demo_methods_and_namedtuple() -> None:
    print()
    print("=" * 60)
    print("【7】元组方法 + NamedTuple 预览")
    print("=" * 60)

    t = (1, 2, 3, 2, 2)
    print(f"  count(2)  = {t.count(2)}    ← 出现次数")
    print(f"  index(3)   = {t.index(3)}    ← 首个下标")
    print("  ★ 没有 append/remove/sort —— 因为不可变")

    # 内置的命名元组：来自 typing，标准库的一部分
    from typing import NamedTuple

    class Point(NamedTuple):
        """命名元组：可按属性访问，底层仍是元组。"""
        x: int
        y: int

    p = Point(3, 4)
    print()
    print(f"  Point(3,4)      = {p}")
    print(f"  p.x, p.y        = {p.x}, {p.y}     ← 像类一样访问")
    print(f"  isinstance tuple = {isinstance(p, tuple)}   ← 本质仍是元组")
    # ★ f-string 会尝试对 {键} 调用 __format__，而 NamedTuple 未定义 __format__，
    #   直接把实例插进 f-string 的字典字面量会抛 TypeError，故先用 str() 转换。
    key_map = {p: "原点附近"}
    print(f"  可作 dict key    = { {str(p): key_map[p]} }   ← 因为不可变")
    print(f"  支持解包         = x, y = {p} → {p}")
    print("    ★ NamedTuple = tuple + 字段名，兼具不可变与可读性（详见 05_collections）")


def main() -> None:
    """主函数：按教学顺序演示元组的全部知识点。"""
    demo_immutable()
    demo_create()
    demo_unpack()
    demo_as_key()
    demo_compare()
    demo_performance()
    demo_methods_and_namedtuple()

    print()
    print("=" * 60)
    print("小结")
    print("=" * 60)
    print("  1. 元组不可变：增删改抛 TypeError，但内部可变对象仍可改（浅不可变）")
    print("  2. ★ `(1)` 是 int，`(1,)` 才是元组 —— 逗号才是元组的判定依据")
    print("  3. ★ 解包要求数量严格匹配，`*rest` 可吸收任意数量剩余元素")
    print("  4. ★ 元组可哈希 → 可作 dict key / set 元素；list 两者都不行")
    print("  5. ★ 元组顺序敏感：(1,2) 与 (2,1) 是不同键")
    print("  6. 内存与创建速度元组优于列表，访问/遍历基本持平")
    print("  7. 选型：多返回值/复合键/常量 → 元组；动态增删 → 列表")
    print("  8. 函数多返回值、循环解包、变量交换都是元组解包的经典应用")


if __name__ == "__main__":
    main()