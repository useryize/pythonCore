"""L11 集合：去重与集合运算 —— 配套教案示例。

运行：python examples/L11_set.py

本脚本演示十件事：
    1. 集合的语义：去重 + 成员判断，以及它为什么【必须无序】
    2. ⚠️ 输出顺序的真相：小整数「看起来有序」是巧合，字符串每次运行都不同
    3. 创建方式与空集合的坑（不能用 {}）
    4. 增删查：add / update / discard / remove / pop / clear
    5. 四个集合运算：并、交、差、对称差（运算符 + 方法两种写法）
    6. 六个关系运算：== / != / <= / < / >= / > / isdisjoint
    7. 可变 set 与不可变 frozenset，以及 frozenset 唯一能哈希的原因
    8. 集合运算的实测耗时，以及 list vs set 的性能差距
    9. 去重实战：三种去重方式的正确性与保序性
   10. 常见坑：元素必须可哈希、无序性、就地运算的返回值陷阱

⚠️ 纯标准库，可直接运行。
"""

import subprocess                        # 标准库：用子进程演示哈希随机化
import sys                                # 标准库：重复利用当前解释器
import time                               # 标准库：性能对比

# ============================================================
# 模块级常量
# ============================================================
PERF_SIZE = 200_000                       # 性能对比的数据规模
DEDUP_SIZE = 200_000                      # 去重对比的数据规模


# ============================================================
# 第 1 部分：集合的语义与「为什么必须无序」
# ============================================================
def demo_semantics() -> None:
    """集合专精两件事：去重和成员判断。"""
    print("【集合的语义】\n")

    # 集合的核心价值：自动去重
    dup_list = [1, 2, 2, 3, 3, 3, 4]
    uniq_set = set(dup_list)
    print(f"  原列表（7 个元素，含重复）: {dup_list}")
    print(f"  转成集合（{len(uniq_set)} 个元素）  : {sorted(uniq_set)}")
    print(f"  ⚠️ 用 set() 去重比手动快得多（后面有实测）")

    # 第二个核心价值：O(1) 成员判断
    print("\n  ⭐ 集合的第二个价值：成员判断是 O(1)")
    print("     列表要一个个比（O(n)），集合算一次哈希直接定位（O(1)）")

    # 集合为什么「无序」？
    print("\n  ⭐ 为什么集合【必须无序】？")
    print("    集合内部用哈希表存储。要存 {3, 1, 2}，Python 算 hash(3)=3、")
    print("    hash(1)=1、hash(2)=2，然后把它们分别放进下标 3、1、2 的槽位。")
    print("    遍历集合时是【按槽位顺序】从头扫，所以 1、2、3 先被扫到——")
    print("    「看起来有序」只是巧合，不是承诺！")


# ============================================================
# 第 2 部分：⚠️ 输出顺序的真相（本课最容易搞错的地方）
# ============================================================
def demo_order_truth() -> None:
    """小整数看起来有序是巧合；字符串顺序每次运行都不同。"""
    print("\n【⚠️ 输出顺序的真相】\n")

    # 情况 1：小整数——看起来总是有序的
    small = {3, 1, 2}
    print(f"  小整数集合 {{3, 1, 2}} 打印为: {small}")
    print(f"  sorted 后             : {sorted(small)}")
    print("  看起来「总是有序」，但这是【巧合】：因为 hash(整数) == 整数本身，")
    print("  所以小整数的槽位下标恰好等于值本身，遍历顺序就成了升序。")
    print(f"  验证 hash(1)=1: {hash(1) == 1}   hash(3)=3: {hash(3) == 3}")

    # ⚠️ 但换个范围，小整数也不再有序
    bigger = {50, 10, 30, 20, 40}
    print(f"\n  ⚠️ 但 {{50, 10, 30, 20, 40}} 打印为: {bigger}")
    print("     → 已经不是升序了！证明「有序」只是小整数的巧合。")

    # 情况 2：字符串——每次运行都不同（PYTHONHASHSEED 随机化）
    print("\n  字符串集合：连续两次运行结果【不同】：")
    for i in range(2):
        result = subprocess.run(
            [sys.executable, "-c", "print(list({'abc', 'xyz', 'hello', 'world'}))"],
            capture_output=True, text=True, encoding="utf-8",
        )
        print(f"    第 {i + 1} 次: {result.stdout.strip()}")

    print("\n  ⭐ 结论：字符串的哈希值被 PYTHONHASHSEED 随机化（安全措施），")
    print("     所以每次运行的集合顺序都可能不同。这是【规范行为】，不是 bug。")
    print("     ⚠️ 所以永远不要依赖集合的顺序！需要有序输出就用 sorted()。")

    # 正确做法
    s = {"b", "a", "c"}
    print(f"\n  ❌ 直接遍历: {list(s)}   ⚠️ 顺序不确定（这次是 {list(s)}，下次可能是别的）")
    print(f"  ✅ sorted():  {sorted(s)}   保证升序，任何时候都一致")
    print("  ⭐ 结论：集合的【顺序永远不要依赖】，需要有序输出就用 sorted()。")


# ============================================================
# 第 3 部分：创建方式与空集合的坑
# ============================================================
def demo_create() -> None:
    """创建方式，以及 {} 是字典不是空集合这个大坑。"""
    print("\n【创建方式与空集合的坑】\n")

    # 三种创建方式（内容相同，便于对比）
    a = {1, 2, 3}                           # 1. 字面量
    b = set([1, 2, 3])                       # 2. set(可迭代对象)
    c = {x for x in (1, 2, 3)}               # 3. 集合推导式
    print(f"  三种方式: {sorted(a)}, {sorted(b)}, {sorted(c)}   内容相等: {a == b == c}")

    # ⚠️ 推导式会「重新计算」——写 x*2 得到的是 {2,4,6}，不是原集合
    doubled = {x * 2 for x in (1, 2, 3)}
    print(f"  ⚠️ 但 {{x*2 for x in (1,2,3)}} = {sorted(doubled)}   "
          f"（推导式会重新计算，不是原样复制）")

    # ⚠️⚠️ 空集合不能用 {}
    print("\n  ⚠️⚠️ 头号陷阱：空集合不能用 {} ")
    empty_wrong = {}                         # ❌ 这是空【字典】
    empty_right = set()                      # ✅ 这才是空集合
    print(f"    {{}} 的类型   = {type(empty_wrong).__name__}   ⚠️ 是字典！")
    print(f"    set() 的类型 = {type(empty_right).__name__}   ✅")
    print(f"    bool({{}}) = {bool({})}   bool(set()) = {bool(set())}")
    print("    原因：{{}} 在 Python 语法里必须表示「空映射」，所以集合只能用 set()。")

    # 空集合的常见后果：用 | 会报错
    try:
        _ = {} | {1}
    except TypeError as exc:
        print(f"\n    ⚠️ {{}} | {{1}} → TypeError: {exc}   （dict 不支持 |）")

    # 初始化集合的两种正确方式
    values: list[int] = [1, 2, 2, 3]
    s1 = set()                               # 逐个 add
    for v in values:
        s1.add(v)
    s2 = set(values)                         # 一次性转换（更快）
    print(f"\n  初始化：逐个 add → {sorted(s1)}   set(列表) → {sorted(s2)}   一致: {s1 == s2}")
    print("  ⚠️ 注意 set(字典) 是取【键】，不是键值对！")


# ============================================================
# 第 4 部分：增删查
# ============================================================
def demo_crud() -> None:
    """集合的增删查，以及 remove/discard 的区别。"""
    print("\n【增删查】\n")

    s = {1, 2, 3}

    # 增
    s.add(4)                                 # 加【一个】元素
    s.add(4)                                 # 加已有的 → 无变化，不报错
    s.update([5, 6])                         # 批量加多个
    s.update({7})                            # 也可以接受另一个集合
    print(f"  增后: {sorted(s)}   ⚠️ 重复 add(4) 不报错，集合自动去重")

    # 删
    s.discard(7)                             # 删【不存在】也不报错
    print(f"  discard(7) 后: {sorted(s)}   （7 不存在，但 discard 不报错）")

    try:
        s.remove(999)                        # 删不存在 → 报错
    except KeyError as exc:
        print(f"  ⚠️ remove(999) → KeyError: {exc}   （remove 会报错）")

    popped = s.pop()                         # ⚠️ 弹出【任意一个】，不确定是哪个
    print(f"  pop() 弹出 {popped}   ⚠️ 弹出的是「任意一个」元素，不是确定的！")

    s.clear()
    print(f"  clear() 后: {s}")

    # 关系判断
    s2 = {1, 2, 3}
    print(f"\n  判断成员: 1 in s2 = {1 in s2}   99 in s2 = {99 in s2}")
    print(f"  len(s2) = {len(s2)}   bool({{}}) = {bool(set())}（空集合是假值）")


# ============================================================
# 第 5、6 部分：四个运算与六个关系运算
# ============================================================
def demo_operations() -> None:
    """并、交、差、对称差，以及关系运算。"""
    print("\n【集合运算】\n")

    a = {1, 2, 3}
    b = {2, 3, 4}

    # 四个运算：运算符 vs 方法
    print(f"  a = {sorted(a)}, b = {sorted(b)}")
    print("\n  ┌────────────┬──────────────────────┬──────────────────────┐")
    print("  │ 运算       │ 运算符写法            │ 方法写法              │")
    print("  ├────────────┼──────────────────────┼──────────────────────┤")
    print(f"  │ 并集       │ a | b = {sorted(a | b)}       │ a.union(b) = {sorted(a.union(b))}       │")
    print(f"  │ 交集       │ a & b = {sorted(a & b)}       │ a.intersection(b) = {sorted(a.intersection(b))}       │")
    print(f"  │ 差集       │ a - b = {sorted(a - b)}       │ a.difference(b) = {sorted(a.difference(b))}       │")
    print(f"  │ 对称差     │ a ^ b = {sorted(a ^ b)}       │ a.symmetric_difference(b) = {sorted(a.symmetric_difference(b))}    │")
    print("  └────────────┴──────────────────────┴──────────────────────┘")

    # ⚠️ 运算符 vs 方法的【返回值】区别
    print("\n  ⚠️⚠️ 关键区别：运算符返回【新集合】，|= 等返回【None】（原地修改）")
    x = {1, 2}
    result = x.union({3})
    print(f"    x.union({{3}}) 返回 {sorted(result)}，x 变成 {sorted(x)}   ✅ x 未变")
    y = {1, 2}
    none_result = y.update({3})
    print(f"    y.update({{3}}) 返回 {none_result!r}，y 变成 {sorted(y)}   ⚠️ 返回 None！")

    # 关系运算
    print("\n  【关系运算】比较的是「集合之间的包含关系」：")
    small = {1, 2}
    big = {1, 2, 3}
    equal_reversed = {2, 1}
    print(f"    {sorted(small)} <= {sorted(big)}   → {small <= big}      真子集（含等号）")
    print(f"    {sorted(small)} <  {sorted(big)}   → {small < big}       严格子集（不含等号）")
    print(f"    {sorted(big)} >= {sorted(small)}   → {big >= small}      超集")
    print(f"    {sorted(small)} == {sorted(equal_reversed)} → {small == equal_reversed}   ⚠️ 集合不关心顺序！")
    print(f"    {sorted(small)} != {sorted(big)}   → {small != big}")
    print(f"    isdisjoint: {sorted(small)}.isdisjoint({{9, 10}}) → {small.isdisjoint({9, 10})}   没有交集")

    # ⭐ 交集的多集合版本很实用
    print("\n  ⭐ 交集支持多参数（找「所有列表都有的元素」）：")
    lists = [[1, 2, 3, 4], [2, 3, 4, 5], [3, 4, 5, 6]]
    common = set(lists[0]).intersection(*lists[1:])
    print(f"    {lists} 的共同元素 = {sorted(common)}")
    print(f"    set.intersection(*others) 可以一次传入多个集合")


# ============================================================
# 第 7 部分：frozenset
# ============================================================
def demo_frozenset() -> None:
    """frozenset 是不可变集合，也是唯一可哈希的「集合类」。"""
    print("\n【frozenset 不可变集合】\n")

    fs = frozenset([1, 2, 3])
    print(f"  创建: frozenset([1, 2, 3]) = {sorted(fs)}")
    print(f"  类型: {type(fs).__name__}")

    # ⭐ 核心价值：可哈希，能当字典键/集合元素
    print("\n  ⭐ 核心价值：frozenset 可哈希（set 不行）")
    print(f"    hash(frozenset({{1,2}})) = {hash(frozenset({1, 2}))}   ✅")
    try:
        hash({1, 2})
    except TypeError as exc:
        print(f"    hash({{1, 2}})          → TypeError: {exc}   ❌")
    print(f"\n    当字典键: {{{frozenset([1, 2])}: 'v'}}   ✅ 可用")
    print(f"    嵌套进集合: { {frozenset([1, 2]), frozenset([3, 4])} }   ✅")

    # ⚠️ 但 frozenset 没有修改方法
    print("\n  ⚠️ frozenset 没有 add/discard/remove 等修改方法：")
    missing = [m for m in ("add", "update", "discard", "remove", "pop", "clear")
               if not hasattr(fs, m)]
    print(f"    缺失的修改方法: {missing}")

    # 但它保留了所有「运算方法」
    ops = [m for m in dir(fs) if not m.startswith("_")]
    print(f"    保留的方法: {ops}")
    print(f"    ✅ 所以 frozenset 能参与运算：fs | frozenset([4]) = {sorted(fs | frozenset([4]))}")
    print("    ⚠️ 但运算会返回【新的 frozenset】，不能原地修改")

    # 实战：需要「集合当字典键」时用 frozenset
    print("\n  【实战：用 frozenset 做不可变的集合键】")
    # 需求：记录「每个标签组合」出现过的次数，而标签组合本身不能变
    tag_counts: dict[frozenset[str], int] = {}
    for tags in [("python", "web"), ("web", "python"), ("data",), ("python", "web")]:
        key = frozenset(tags)                 # ⭐ 转成可哈希的
        tag_counts[key] = tag_counts.get(key, 0) + 1
    print(f"    标签组合计数: { {'/'.join(sorted(k)): v for k, v in tag_counts.items()} }")
    print("    ⚠️ 注意 (python,web) 和 (web,python) 被正确识别为同一个组合")
    print("    （因为 frozenset 会去重且不关心顺序）")


# ============================================================
# 第 8 部分：性能实测
# ============================================================
def demo_perf() -> None:
    """list vs set 的成员判断和去重性能。"""
    print("\n【性能实测】\n")

    # 成员判断：O(n) vs O(1)
    n = PERF_SIZE
    lst = list(range(n))
    st = set(range(n))
    target = 999_999                        # 不存在于两者中（最坏情况）

    t0 = time.perf_counter()
    for _ in range(1000):
        _ = target in lst
    t1 = time.perf_counter()
    for _ in range(1000):
        _ = target in st
    t2 = time.perf_counter()
    print(f"  在 {n:,} 个元素中查找不存在的值，各 1000 次：")
    print(f"    列表 in: {(t1 - t0) * 1000:.2f} ms    O(n)")
    print(f"    集合 in: {(t2 - t1) * 1000:.3f} ms    O(1)")
    print(f"    ⚠️ 相差约 {(t1 - t0) / max(t2 - t1, 1e-9):,.0f} 倍")

    # 增长曲线
    print("\n  ⭐ 增长曲线（数据量翻倍）：")
    prev_l = prev_s = 0.0
    for size in (50_000, 100_000, 200_000, 400_000):
        bl = list(range(size))
        bs = set(range(size))
        tgt = 999_999
        t0 = time.perf_counter()
        for _ in range(200):
            _ = tgt in bl
        t1 = time.perf_counter()
        for _ in range(200):
            _ = tgt in bs
        t2 = time.perf_counter()
        lr = f"{(t1 - t0) / prev_l:.2f}×" if prev_l > 0 else "—"
        sr = f"{(t2 - t1) / prev_s:.2f}×" if prev_s > 0 else "—"
        print(f"    n={size:>7,}: 列表 {(t1 - t0) * 1000:8.2f} ms（{lr}）"
              f"   集合 {(t2 - t1) * 1000:6.3f} ms（{sr}）")
        prev_l, prev_s = t1 - t0, t2 - t1
    print("    → 列表【线性增长】，集合【基本不变】")

    # 去重：O(n²) vs O(n)
    print("\n  【去重性能对比】数据 20 万条，取值范围 0-9999：")
    data = [i % 10_000 for i in range(DEDUP_SIZE)]

    t0 = time.perf_counter()
    manual: list[int] = []
    for x in data:
        if x not in manual:                  # 列表查找 O(n) → 整体 O(n²)
            manual.append(x)
    t1 = time.perf_counter()
    fast = set(data)
    t2 = time.perf_counter()
    print(f"    列表逐个判断: {(t1 - t0) * 1000:.1f} ms   O(n²)")
    print(f"    set(data)   : {(t2 - t1) * 1000:.2f} ms   O(n)")
    print(f"    ⚠️ 快 {(t1 - t0) / max(t2 - t1, 1e-9):,.0f} 倍，结果一致: {len(manual) == len(fast)}")


# ============================================================
# 第 9 部分：去重实战
# ============================================================
def demo_dedup() -> None:
    """三种去重方式的正确性与保序性。"""
    print("\n【去重实战】\n")

    data = ["b", "a", "b", "c", "a", "d"]

    # 方式1：set 去重——最快但【不保序】
    s = set(data)
    print(f"  方式1 set 去重: {sorted(s)}   ⚠️ 原始顺序已丢失")

    # 方式2：sorted(set())——去重 + 排序
    print(f"  方式2 sorted(set): {sorted(set(data))}   去重 + 升序")

    # 方式3：seen 集合 + 结果列表——⭐ 去重且【保序】（L07 讲过）
    seen: set[str] = set()
    unique: list[str] = []
    for item in data:
        if item not in seen:                # 集合判断 O(1)，比列表快得多
            seen.add(item)
            unique.append(item)
    print(f"  方式3 seen+列表: {unique}   ✅ 去重 + 保序")

    # 方式4：dict.fromkeys —— 3.7+ 后字典保序，最简洁的保序去重
    print(f"  方式4 dict.fromkeys: {list(dict.fromkeys(data))}   ✅ 最简洁的保序去重")

    # 三种去重的正确性验证
    print("\n  正确性验证（元素集合必须相同）：")
    print(f"    set 结果 == seen 结果 == fromkeys 结果: "
          f"{set(s) == set(unique) == set(dict.fromkeys(data))}")

    # ⚠️ 去重时保留「最后一次出现」vs「第一次出现」
    print("\n  ⚠️ 细节：保留第一次还是最后一次出现？")
    pairs = [("a", 1), ("b", 2), ("a", 3)]
    first_keep = dict(pairs)                 # 后面的覆盖前面的 → 保留最后一次的值
    print(f"    原始: {pairs}")
    print(f"    dict(pairs) = {first_keep}   ⚠️ 保留了 a 的【最后一次】值 3")
    print("    如果要保留第一次，需要反向遍历或 seen 集合")


# ============================================================
# 第 10 部分：常见坑
# ============================================================
def demo_pitfalls() -> None:
    """集合最容易踩的坑。"""
    print("\n【常见坑集中演示】\n")

    # 坑 1：元素必须可哈希
    print("  坑 1：集合元素必须可哈希")
    try:
        _ = {[1, 2], [3, 4]}                # 列表不可哈希
    except TypeError as exc:
        print(f"    {{[1,2],[3,4]}} → TypeError: {exc}")
    print(f"    ✅ 要放列表元素，得转成元组或 frozenset：{{(1,2),(3,4)}}")

    # 坑 2：不能用 {} 创建空集合
    print("\n  坑 2：空集合不能用 {}")
    print(f"    {{}} → {type({}).__name__}（字典），空集合要写 set()")

    # 坑 3：无序性
    print("\n  坑 3：无序性")
    print(f"    {{'b','a','c'}} 打印为 {'b', 'a', 'c'}   ⚠️ 顺序不保证（字符串哈希随机化）")
    print(f"    需要有序输出必须 sorted(): {sorted({'b', 'a', 'c'})}")

    # 坑 4：就地运算返回 None
    print("\n  坑 4：|= 等就地运算返回 None")
    s = {1, 2}
    result = s.update({3})
    print(f"    s.update({{3}}) 返回 {result!r}（None），s 变成 {sorted(s)}")
    print(f"    ⚠️ 所以 x = s.update(...) 一定错")
    # 运算符版本
    t = {1, 2}
    new_set = t | {3}
    print(f"    但 t | {{3}} 返回 {sorted(new_set)}，t 仍是 {sorted(t)}   ✅ 运算符返回新集合")

    # 坑 5：remove vs discard
    print("\n  坑 5：remove 报错、discard 静默")
    s2 = {1, 2}
    s2.discard(99)                           # 不存在也不报错
    print(f"    discard(99) 不报错，s2 = {sorted(s2)}")
    try:
        s2.remove(99)                        # 不存在会报错
    except KeyError as exc:
        print(f"    ⚠️ remove(99) → KeyError: {exc}")

    # 坑 6：pop 弹出的是「任意一个」
    print("\n  坑 6：pop() 是弹出「任意一个」")
    s3 = {"a", "b", "c"}
    print(f"    s3 = {sorted(s3)}（3 个元素，pop 弹哪个不确定）")
    # 连续弹多次，展示顺序不确定
    popped = [s3.pop() for _ in range(3)]
    print(f"    连续 pop 3 次得到: {popped}   ⚠️ 顺序不确定")
    print(f"    （小整数看起来像升序，那也是巧合；字符串就完全没规律）")

    # 坑 7：set(字典) 取的是键
    print("\n  坑 7：set(字典) 取的是【键】")
    d = {"a": 1, "b": 2}
    print(f"    set({{'a': 1, 'b': 2}}) = {set(d)}   ← 是键 {{'a','b'}}，不是键值对")


# ============================================================
# 第 11 部分：自检断言
# ============================================================
def verify_set() -> None:
    """用断言验证本课所有关键结论。"""
    print("【自检断言】")

    # 创建
    a, b, c = {1, 2, 3}, set([1, 2, 3]), {x * 2 for x in (1, 2, 3)}
    assert a == b
    assert isinstance({}, dict) and {} != set()     # ⚠️ {} 是字典
    assert isinstance(set(), set)
    assert bool(set()) is False                      # 空集合是假值

    # 去重
    assert set([1, 2, 2, 3, 3]) == {1, 2, 3}
    assert len(set([1, 2, 2, 3, 3])) == 3

    # 元素必须可哈希
    try:
        {[1, 2]}
        raise AssertionError("列表竟然能进集合")
    except TypeError:
        pass

    # 四个运算
    x, y = {1, 2, 3}, {2, 3, 4}
    assert (x | y) == {1, 2, 3, 4}
    assert (x & y) == {2, 3}
    assert (x - y) == {1}
    assert (x ^ y) == {1, 4}
    assert x.union(y) == (x | y)
    assert x.intersection(y) == (x & y)

    # ⚠️ 运算符返回新集合，方法 update 返回 None
    orig = {1, 2}
    _ = orig | {3}
    assert orig == {1, 2}                          # 运算符不改原集合
    assert orig.update({3}) is None                # update 返回 None
    assert orig == {1, 2, 3}

    # 关系运算
    small, big = {1, 2}, {1, 2, 3}
    assert small <= big and small < big            # 子集 vs 真子集
    assert big >= small and big > small
    assert small == {2, 1}                         # 集合不关心顺序
    assert small.isdisjoint({9, 10})

    # 多集合交集
    assert set([1, 2, 3, 4]).intersection([2, 3], [3, 4]) == {3}

    # frozenset
    fs = frozenset([1, 2])
    assert hash(fs) is not None                    # 可哈希
    assert {fs: "v"}[fs] == "v"                    # 能当字典键
    assert not hasattr(fs, "add")                  # 没有修改方法
    assert (fs | frozenset([3])) == frozenset([1, 2, 3])

    try:
        hash({1, 2})
        raise AssertionError("set 竟然可哈希")
    except TypeError:
        pass

    # remove vs discard
    s = {1, 2}
    s.discard(99)                                 # 静默
    try:
        s.remove(99)
        raise AssertionError("remove 应该报错")
    except KeyError:
        pass

    # 保序去重
    data = ["b", "a", "b", "c"]
    assert list(dict.fromkeys(data)) == ["b", "a", "c"]

    # set(字典) 取键
    assert set({"a": 1, "b": 2}) == {"a", "b"}

    print("✅ verify_set 全部断言通过")


# ============================================================
# 程序入口
# ============================================================
def main() -> None:
    """按教学顺序调用全部演示函数。"""
    print("=" * 64)
    print("L11 · 集合：去重与集合运算")
    print("=" * 64)
    demo_semantics()
    demo_order_truth()
    demo_create()
    demo_crud()
    demo_operations()
    demo_frozenset()
    demo_perf()
    demo_dedup()
    demo_pitfalls()
    print("\n" + "-" * 64)
    verify_set()
    print("\n🎉 L11 演示结束")


# 标准入口约定：直接运行本文件执行 main()，被 import 时不执行
if __name__ == "__main__":
    main()