"""
================================================================================
  03_set.py  ——  集合：无序唯一容器与哈希查找
================================================================================

【演示的语法点】
 1. 集合的创建、添加、删除，以及「元素必须可哈希」约束
 2. ★ 集合运算：交集 `&`、并集 `|`、差集 `-`、对称差 `^`
 3. ★ 对应的运算符方法：intersection / union / difference / symmetric_difference
 4. ★ 可就地修改的运算符方法：`&=` `|=` `-=` `^=`（性能更优）
 5. frozenset：不可变集合，可作 dict key / set 元素
 6. ★ 去重原理：基于哈希表，add 平均 O(1)
 7. ★ 哈希查找原理：hash() 定位桶 → __eq__ 确认 → 哈希冲突处理
 8. 集合 vs 列表去重性能实测
 9. 集合的可比较性（子集/超集）与运算符 vs 方法的取舍
10. 常见坑：无序性、可变默认集合、遍历时修改集合

【预期输出摘要】
 - "运算" 小节打印四种集合运算的完整对比表与 Venn 示意结果
 - "frozenset" 小节证明 frozenset 可作字典键而 set 不行
 - "去重性能" 小节打印 set 去重比 list 去重快约一个数量级的实测数据
 - "哈希原理" 小节打印 hash 桶定位与冲突处理的分步演示
================================================================================

"""

from __future__ import annotations

import sys
import timeit
from typing import Any, FrozenSet, Set


# ===== 语法解析 =====
# 【1】集合的创建与基本操作
#   语法规则：{元素} 才是集合；set() 是空集合；{} 是空【字典】不是空集合。
#   约束：集合元素必须【可哈希】（不可变类型），list/dict 不能作元素。
#   设计意图：表达"数学上的集合"——唯一、无序、支持集合代数运算。
def demo_create() -> None:
    print("=" * 60)
    print("【1】集合的创建与基本操作")
    print("=" * 60)

    a = {1, 2, 3}                         # 字面量
    b = set([1, 2, 3, 2, 1])              # set(可迭代) —— 自动去重
    c = {1, 2, 3}
    empty = set()                         # ★ 空集合必须用 set()，{} 是空字典
    print(f"  {1, 2, 3}        {a}  type={type(a).__name__}")
    print(f"  set([1,2,3,2,1]) {b}  type={type(b).__name__}   ← 去重后只剩 {len(b)} 个")
    print(f"  相等性：a == c → {a == c}   （集合相等看元素，与顺序无关）")
    print(f"  set()  → {empty}  len={len(empty)}")
    print(f"  {{}} 是 {type({})}，不是 {type(set())}   ← ★ 易错点")

    # 添加与删除
    s = {1, 2}
    s.add(3)                              # 添加单个元素
    s.add(2)                              # 已存在则无操作（不报错）
    s.update([4, 5])                      # 批量添加（摊平可迭代对象）
    s.discard(4)                          # 删除，不存在【静默跳过】
    print()
    print(f"  add/update 后   {s}")
    s.discard(4)
    print(f"  discard(4) 后   {s}   ← 不存在也不报错")
    try:
        s.remove(999)
    except KeyError as exc:
        print(f"  ★ remove(999) → KeyError: {exc}   ← 集合用 KeyError 而非 ValueError")

    # 不可哈希元素不能加入
    print()
    print("  ★ 集合元素必须可哈希：", end=" ")
    try:
        hash([1, 2])                       # list 不可哈希
    except TypeError as exc:
        print(f"TypeError: {exc}")

    print()
    print("  ★ 元素不可变才可哈希，因此集合元素不能就地修改：")
    print(f"    列表进不了集合，但元组可以：{{(1, 2), (3, 4)}} = { {(1, 2), (3, 4)} }")
    print(f"    字符串也不行吗？可以：{{'a', 'b'}} = {{'a', 'b'}}   ← 字符串不可变故可哈希")

    # 无序性
    print()
    print("  ★ 集合是【无序】的：相同元素的集合可能打印出不同顺序")
    for _ in range(3):
        nums = {3, 1, 2, 8, 5, 9}         # 整数集合在小范围下顺序基本稳定
        print(f"    {nums}")


# ===== 语法解析 =====
# 【2】★ 集合运算：四种核心集合代数
#   交集 &    —— 同时属于 A 和 B 的元素（and）
#   并集 |    —— 属于 A 或 B 的元素（or）
#   差集 -    —— 属于 A 但不属于 B 的元素
#   对称差 ^  —— 属于 A 或 B 但不同时属于两者
#   语法规则：运算符要求两侧【都是 set】；与 dict 运算时 & 取键的交集。
def demo_operations() -> None:
    print()
    print("=" * 60)
    print("【2】★ 集合运算：交 / 并 / 差 / 对称差")
    print("=" * 60)

    A = {1, 2, 3, 4, 5}
    B = {4, 5, 6, 7, 8}
    print(f"  A = {A}")
    print(f"  B = {B}")
    print()
    print("  | 运算 | 数学 | Python | 结果 |")
    print("  |------|------|--------|------|")
    print(f"  | 交集 | ∩    | A & B  | {A & B}  |")
    print(f"  | 并集 | ∪    | A | B  | {A | B}  |")
    print(f"  | 差集 | A-B  | A - B  | {A - B}  |")
    print(f"  | 对称差| △   | A ^ B  | {A ^ B}  |")
    print()
    print(f"  ★ 差集方向敏感：A - B = {A - B}  而 B - A = {B - A}  （不同！）")
    print(f"  ★ 对称差对称  ：A ^ B = {A ^ B}  而 B ^ A = {B ^ A}  （相同）")

    print()
    print("  ★ 方法形式（语义相同，参数可以是任意可迭代对象）：")
    print(f"    A.intersection(B)             = {A.intersection(B)}")
    print(f"    A.intersection([3, 4, 99])    = {A.intersection([3, 4, 99])}   ← 可吃列表")
    print(f"    A.union(B)                    = {A.union(B)}")
    print(f"    A.difference(B)               = {A.difference(B)}")
    print(f"    A.symmetric_difference(B)     = {A.symmetric_difference(B)}")

    print()
    print("  ★ 多集合运算：方法支持任意多个参数，运算符只支持两元")
    C = {9, 10}
    print(f"    A.union(B, C, [99]) = {A.union(B, C, [99])}")
    print(f"    A & B & C（不合法，需逐个）→ A & B & C = {(A & B) & C}")
    print(f"    A.intersection(B, C) = {A.intersection(B, C)}")

    print()
    print("  ★ 判断子集/超集关系：")
    X = {1, 2}
    Y = {1, 2, 3}
    print(f"    {X} <= {Y}  → {X <= Y}   子集（issubset）")
    print(f"    {Y} >= {X}  → {Y >= X}   超集（issuperset）")
    print(f"    {X} <  {Y}  → {X < Y}    真子集（严格包含）")
    print(f"    X.issubset(Y)  = {X.issubset(Y)}")
    print(f"    X <= X（相等也算子集）→ {X <= X}")

    print()
    print("  ★ 运算符 vs 方法的取舍：")
    print("    - 运算符 & | - ^：两侧必须都是 set，写法简洁")
    print("    - 方法 intersection()：接受任意可迭代对象，更灵活")
    print("    - 与 dict 运算时：dict & set 取【公共键】，dict | dict 合并字典")

    d = {"a": 1, "b": 2}
    print()
    print("  ★ dict 与 set 的混合运算：")
    print(f"    {d}.keys() & {{'a','b','c'}} = {d.keys() & {'a', 'b', 'c'}}   ← 取公共键")
    print(f"    {d} & {{'a','b','c'}}（直接 &）→ ", end="")
    try:
        print(d & {"a", "b", "c"})
    except TypeError as exc:
        print(f"TypeError: {exc}")
    print("    ★ 注意：dict 与 set 之间【不能】直接用 &，只有 dict.keys() 才能。")
    print(f"    {d} | {{'c': 3}}   = {d | {'c': 3}}      ← 字典合并（3.9+），右侧覆盖左侧")

    print()
    print("  ★ 经典应用：求两段列表的【共同好友】/【互不重复】元素")
    group_a = {"张三", "李四", "王五"}
    group_b = {"李四", "王五", "赵六"}
    print(f"    共同成员（&）：{group_a & group_b}")
    print(f"    仅在 A 中（-）：{group_a - group_b}")
    print(f"    至少一组在（|）：{group_a | group_b}")


# ===== 语法解析 =====
# 【3】★ 就地修改运算符：&= |= -= ^=
#   语法规则：这些运算符【原地修改】左侧集合，返回 None（不是新集合）。
#   设计意图：交集/差集通常更小，就地替换可释放大集合的内存。
#   ★ 与 set.update() 的区别：update 是并集（| 的方法形式），&= 是原地求交。
def demo_inplace() -> None:
    print()
    print("=" * 60)
    print("【3】★ 就地运算 &= |= -= ^=")
    print("=" * 60)

    s = {1, 2, 3, 4, 5}
    t = {3, 4, 5, 6, 7}

    s &= t                                 # 原地取交集 → 左侧被改小
    print(f"  s &= t    → s = {s}   （原地交，不新建对象）")

    s2 = {1, 2}
    s2 |= {2, 3}
    print(f"  s |= t    → s = {s2}   （原地并，等价 update）")

    s3 = {1, 2, 3}
    s3 -= {2}
    print(f"  s -= t    → s = {s3}   （原地差，difference_update）")

    s4 = {1, 2, 3}
    s4 ^= {3, 4}
    print(f"  s ^= t    → s = {s4}   （原地对称差，symmetric_difference_update）")

    print()
    print("  ★ 对应的『update 类』方法（都是原地修改，返回 None）：")
    u = {1}
    u.update([2, 3])
    u.intersection_update({2, 3, 9})
    print(f"    update + intersection_update → {u}")

    print()
    print("  ★ 注意就地运算返回 None，不要写成 s = s &= t：")
    v = {1, 2}
    print(f"    v &= {{2}} 的结果 v = {v}   （若写 v = v &= {{2}}，v 会变成 None）")


# ===== 语法解析 =====
# 【4】frozenset：不可变集合
#   语法：frozenset(iterable)，运算规则与 set 相同，只是没有就地修改方法。
#   能力对比：set 有 add/discard，frozenset 全都没有。
#   设计意图：不可变 → 可哈希 → 可作 dict key / set 的元素 / 类属性。
def demo_frozenset() -> None:
    print()
    print("=" * 60)
    print("【4】frozenset 不可变集合")
    print("=" * 60)

    fs = frozenset([1, 2, 3, 2])           # 同样自动去重
    print(f"  frozenset([1,2,3,2]) = {fs}  type={type(fs).__name__}")
    print(f"  isinstance(fs, set)   = {isinstance(fs, set)}   ← frozenset 不是 set 子类")

    print()
    print("  ★ 没有修改类方法：")
    print(f"    有 add？   {hasattr(fs, 'add')}    有 discard？ {hasattr(fs, 'discard')}")
    print("    增删改都不可用 —— 这是它可哈希的前提。")

    print()
    print("  ★ 支持集合运算（返回【新】frozenset）：")
    other = {3, 4, 5}
    print(f"    fs & other        = {fs & other}   type={type(fs & other).__name__}")
    print(f"    fs | other        = {fs | other}")
    print(f"    fs - other        = {fs - other}")
    print(f"    fs ^ other        = {fs ^ other}")
    print(f"    fs <= fs          = {fs <= fs}   （与 set 比较可用，按元素判定）")

    print()
    print("  ★ 核心优势：frozenset 可哈希，能作字典键与集合元素：")
    # 用 frozenset 作字典键，缓存「权限集合 → 标签」的映射
    tag_map: dict[frozenset[str], str] = {
        frozenset(["读"]): "只读",
        frozenset(["读", "写"]): "读写",
    }
    perms = frozenset(["读", "写"])
    print(f"    frozenset(['读','写']) 作键 → {tag_map[perms]}   ★")

    # 对比：普通 set 不可哈希，无法作字典键
    try:
        hash({"读", "写"})                  # set 不可哈希
    except TypeError as exc:
        print(f"    set(['读','写']) 作键 → TypeError: {exc}   ← set 不可哈希")

    print()
    print("  ★ 用 frozenset 实现『集合的集合』（set 不能进 set）：")
    outer = {frozenset([1, 2])}            # 元素用 frozenset 就能装进外层集合
    print(f"    {{frozenset([1,2])}} = {outer}   ✓")

    print()
    print("  ★ 实际用途：把 set 转 frozenset 作字典键的通用技巧")
    s = {"a", "b"}
    d = {frozenset(s): len(s)}
    print(f"    {{frozenset(s): len(s)}} = {d}")


# ===== 语法解析 =====
# 【5】★ 去重原理：基于哈希表
#   内部结构：集合/字典底层是【哈希表】—— 一个固定长度的桶数组 + 开放寻址/链地址。
#   add 流程：算 hash(元素) → 取模定位桶 → 桶空则放入，桶有值则比较 == 判断是否重复。
#   ★ 因此 add 平均 O(1)，而 list 的 append 是 O(1) 但 in 判断是 O(n)。
def demo_dedup_principle() -> None:
    print()
    print("=" * 60)
    print("【5】★ 去重原理与哈希查找原理")
    print("=" * 60)

    print("  【集合去重的本质】")
    data = [1, 2, 2, 3, 1, 4, 2]
    print(f"  原始列表（{len(data)} 个，含重复）：{data}")
    print(f"  set(data)（去重后）：{set(data)}  长度={len(set(data))}")

    print()
    print("  ★ 三种去重方式对比（保序 / 速度）：")
    print(f"    1. set 去重（乱序）     {set(data)}")
    print(f"    2. dict.fromkeys（保序） {list(dict.fromkeys(data))}   ← 利用字典保序")
    print(f"    3. 循环去重（保序）     ", end="")

    seen: set[int] = set()                 # 借助 set 的 O(1) 查找，但保持 list 顺序
    uniq = []
    for x in data:
        if x not in seen:                  # set 的 in 是哈希查找 O(1)
            seen.add(x)
            uniq.append(x)                 # 保持首次出现顺序
    print(uniq)

    print()
    print("  【哈希查找五步流程】")
    print(f"  以 set 查找数字 7 为例（内部桶数约 {sys.getsizeof(set())} 字节量级）：")
    print(f"    1) 计算哈希      hash(7)       = {hash(7)}")
    print(f"    2) 定位桶下标    hash(7) % 8   = {hash(7) % 8}   （假设 8 个桶）")
    print(f"    3) 该桶为空？    → 是 → 直接放入，结束")
    print(f"    4) 若桶非空，比较 hash 是否相同，再比较 __eq__：")
    print(f"       hash(7) == hash(7) → {hash(7) == hash(7)}")
    print(f"       7 == 7            → {7 == 7}   ← 两者都成立才判定为『已存在』")
    print(f"    5) 若 hash 相同但 == 为假 → 【哈希冲突】，继续探测下一个桶（开放寻址）")

    print()
    print("  ★ 为什么『不可变』才能做集合元素：")
    print(f"    hash(整数 7) 稳定不变 → 可作为稳定的桶位置")
    print("    若对象可变，hash 会变 → 存进去就再也找不到，等于数据丢失")
    print(f"    验证：hash((1,2)) = {hash((1, 2))}  稳定")
    print(f"          hash('ab') = {hash('ab')}  稳定")
    print("    ★ 数值哈希=数值本身，所以小整数 set 遍历顺序看起来『有序』（其实是哈希序）")


# ===== 语法解析 =====
# 【6】★ 集合 vs 列表 去重性能实测
#   测试项：建集合、成员查找、交集计算、去重保序。
#   设计意图：量化 O(1) 与 O(n) 的差距，指导数据结构选型。
def demo_performance() -> None:
    print()
    print("=" * 60)
    print("【6】★ 集合 vs 列表 性能实测")
    print("=" * 60)

    # ★ 规模说明：list 的 `x not in out` 是 O(n) 线性扫描，
#   去重循环整体是 O(n²)。数据量和重复次数必须压小，否则会跑到分钟级。
    N = 20_000                # 元素个数
    DISTINCT = 1_000          # 不同值的个数（决定 list 去重的内层扫描长度）
    R = 5# 每组重复次数（O(n²) 的项重复次数要少）
    data = [i % DISTINCT for i in range(N)]        # 有重复的数据

    print(f"  测试数据：{N:,} 个元素（只有 {DISTINCT:,} 种不同值）")
    print(f"  ★ 注：list 去重是 O(n²)，故数据量刻意压小以保证秒级完成")
    print()
    print(f"  | 操作           | list      | set        | 提升 |")
    print("  |----------------|-----------|------------|------|")

    # 1. 去重
    setup_dedup = f"data = [i % {DISTINCT} for i in range({N})]"
    t_list_dedup = timeit.timeit(
        """
out = []
for x in data:
    if x not in out:
        out.append(x)
""",
        setup=setup_dedup,
        number=R,
    )
    t_set_dedup = timeit.timeit(
        "set(data)",
        setup=setup_dedup,
        number=R,
    )
    print(f"  | 去重           | {t_list_dedup:.4f}s | {t_set_dedup:.4f}s | {t_list_dedup / t_set_dedup:>4.1f}x |")

    # 2. 成员查找（1 万个元素的容器，重复 2 万次）
    t_list_in = timeit.timeit(
        f"9999 in d",
        setup=f"d = list(range(10000))",
        number=20_000,
    )
    t_set_in = timeit.timeit(
        f"9999 in d",
        setup=f"d = set(range(10000))",
        number=20_000,
    )
    print(f"  | 成员查找       | {t_list_in:.4f}s | {t_set_in:.4f}s | {t_list_in / t_set_in:>4.1f}x |")

    # 3. 建容器成本
    t_make_list = timeit.timeit(f"list(range(10000))", number=2_000)
    t_make_set = timeit.timeit(f"set(range(10000))", number=2_000)
    print(f"  | 建容器         | {t_make_list:.4f}s | {t_make_set:.4f}s | {t_make_list / t_make_set:>4.1f}x |")

    # 4. 求交集
    # ★ 规模说明：list 版每次都要对 c(1万) 逐个 in d，是 O(n·m)；
    #   即便如此 1 万×1 万仍偏慢，故把容器缩到 3000、重复 20 次以保证秒级完成。
    setup_a = "a = set(range(3000)); b = set(range(1500, 4500)); c = list(range(3000)); d = list(range(1500, 4500))"
    t_list_inter = timeit.timeit(
        "e = set(x for x in c if x in d)", setup=setup_a, number=20
    )
    t_set_inter = timeit.timeit("a & b", setup=setup_a, number=20)
    print(f"  | 求交集         | {t_list_inter:.4f}s | {t_set_inter:.4f}s | {t_list_inter / t_set_inter:>4.1f}x |")

    print()
    print("  ★ 结论：")
    print("    · 成员查找、去重、求交集：集合是压倒性优势（哈希 O(1) vs 扫描 O(n)）")
    print("    · 建容器：集合慢一点（要算哈希、分配桶），但换来了后续所有操作提速")
    print("    · 需保序去重时，用『set 辅助 + list 输出』模式（见上一节）")

    print()
    print("  ★ 反向场景：只需【少量元素、频繁遍历】，集合因无序反而不如列表：")
    print(f"    小集合(3元素)遍历 set 与 list 相当：")
    t_small_set = timeit.timeit("sum(s)", setup="s = {1, 2, 3}", number=100_000)
    t_small_list = timeit.timeit("sum(l)", setup="l = [1, 2, 3]", number=100_000)
    print(f"      set {t_small_set:.4f}s   list {t_small_list:.4f}s   （数据量小时差异可忽略）")
    print("    ★ 集合是为『大规模 + 查找密集』优化的，小数据用什么都行。")


def main() -> None:
    """主函数：按教学顺序演示集合的知识点。"""
    demo_create()
    demo_operations()
    demo_inplace()
    demo_frozenset()
    demo_dedup_principle()
    demo_performance()

    print()
    print("=" * 60)
    print("小结")
    print("=" * 60)
    print("  1. set() 是空集合，{} 是空字典 —— 高频坑")
    print("  2. ★ 运算 & | - ^ 要求两侧都是 set；方法形式更灵活（吃任意可迭代）")
    print("  3. ★ 差集方向敏感 (A-B≠B-A)，对称差对称 (A^B==B^A)")
    print("  4. ★ &= |= -= ^= 原地修改、返回 None，用于交/差结果更小省内存")
    print("  5. ★ frozenset 不可变 → 可哈希 → 可作 dict key / set 元素")
    print("  6. ★ 集合基于哈希表：add/查找平均 O(1)；去重比 list 快约一个数量级")
    print("  7. ★ 元素必须不可变才可哈希（可变元素进去就再也找不到）")
    print("  8. 无序性：不要依赖遍历顺序；需保序去重用 dict.fromkeys 或 set 辅助")
    print("  9. dict & set 求公共键；dict | dict 合并字典")
    print(" 10. 大数据/查找密集 → set；需保序/需索引 → list/dict")


if __name__ == "__main__":
    main()