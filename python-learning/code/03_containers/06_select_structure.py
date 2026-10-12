"""
================================================================================
  06_select_structure.py  ——  容器选型决策 + timeit 性能实测
================================================================================

【演示的语法点】
 1. ★ 四种容器的选型决策树与核心差异
 2. ★ 10 个真实业务场景 → 给出推荐容器与理由
 3. ★ 用 timeit 实测各方案性能（秒级完成），输出横向对比表
 4. list / tuple / set / dict 的时间复杂度速查
 5. 综合实战：为同一需求分别用 4 种容器实现，对比可读性与性能

【预期输出摘要】
 - "决策树" 小节打印按操作需求选择容器的判定表
 - "10个场景" 小节逐条打印场景 → 推荐容器 → 理由 → 复杂度
 - "性能实测" 小节打印 6 组 timeit 横向对比数据（含倍数换算）
 - "复杂度" 小节打印各容器常用操作的时间复杂度总表
================================================================================

"""

from __future__ import annotations

import sys
import timeit
from collections import Counter, OrderedDict, defaultdict, deque
from typing import Any, Dict, List, Tuple


# ==============================================================================
# 第一部分：选型决策树
# ==============================================================================
# ===== 语法解析 =====
# 四种内置容器的定位：
#   list  —— 有序、可变、按【索引】访问的场景
#   tuple —— 有序、不可变、语义上是「固定的一组值」
#   set   —— 【唯一】、无序、频繁做集合运算
#   dict  —— 【键值映射】，按 key 快速查找，3.7+ 保序
def print_decision_tree() -> None:
    print("=" * 68)
    print("第一部分：容器选型决策树")
    print("=" * 68)

    print()
    print("  【第一步】你需要做什么操作？")
    print()
    print("    需要按【索引】访问第 n 个元素？")
    print("      是 → list（唯一选择，set/dict 无序无索引）")
    print("      否 ↓")
    print()
    print("    需要按【键】查值（key → value）？")
    print("      是 → dict（唯一选择）")
    print("      否 ↓")
    print()
    print("    需要判断【是否存在 / 去重 / 集合运算】？")
    print("      是 → set")
    print("      否 ↓")
    print()
    print("    元素数量固定、不需要修改？")
    print("      是 → tuple")
    print("      否 → list")

    print()
    print("  【第二步】性能特征速记")
    print()
    print("  | 操作            | list        | tuple       | set          | dict         |")
    print("  |-----------------|-------------|-------------|--------------|--------------|")
    print("  | 尾部添加        | O(1) ✓      | ✗ 不可变     | O(1) ✓       | —            |")
    print("  | 头部添加        | O(n) ✗      | ✗           | O(1) ✓       | —            |")
    print("  | 按下标索引      | O(1) ✓      | O(1) ✓      | ✗ 无序       | ✗ 按键       |")
    print("  | 成员查找        | O(n)        | O(n)        | O(1) ✓       | O(1) ✓       |")
    print("  | 按键查找        | ✗           | ✗           | ✗            | O(1) ✓       |")
    print("  | 保证唯一        | ✗           | ✗           | ✓ ✓          | 键 ✓         |")
    print("  | 保证顺序        | ✓ ✓         | ✓ ✓         | ✗           | ✓ ✓ (3.7+)   |")
    print("  | 可哈希作键      | ✗           | ✓ ✓         | frozenset ✓  | —            |")
    print("  | 内存开销        | 中          | 小          | 中           | 最大         |")
    print()
    print("  ★ 一句话记忆：")
    print("    list=有序可变   tuple=有序不可变   set=唯一无序   dict=键值映射")


# ==============================================================================
# 第二部分：10 个业务场景选型
# ==============================================================================
def print_scenarios() -> None:
    print()
    print("=" * 68)
    print("第二部分：10 个业务场景选型（场景 → 容器 → 理由 → 复杂度）")
    print("=" * 68)

    scenarios = [
        (
            "1. 学生成绩单（有序、按排名索引）",
            "list",
            "需要按排名 index 取第 N 名成绩，且会对成绩排序",
            "按索引 O(1)，sort O(nlogn)",
        ),
        (
            "2. 地图经纬度坐标（固定不可变坐标）",
            "tuple",
            "坐标创建后不应改变，且常作 dict 的复合键",
            "不可变可哈希，作键 O(1)",
        ),
        (
            "3. 用户 ID 去重（只需存在性判断）",
            "set",
            "只关心在不在，不需要顺序，set 自带去重",
            "add/查找 O(1)，比 list 去重快一个数量级",
        ),
        (
            "4. 电话簿：姓名 → 电话",
            "dict",
            "按姓名快速查电话，天然键值映射",
            "按键查找 O(1)",
        ),
        (
            "5. 任务队列（FIFO 先进先出）",
            "deque",
            "频繁在头部取出、尾部加入，list.pop(0) 是 O(n) 太慢",
            "两端操作均 O(1)",
        ),
        (
            "6. 单词词频统计与 TopN",
            "Counter",
            "count() 直接计数，most_common() 直接排行",
            "计数 O(n)，排行 O(klogk)",
        ),
        (
            "7. 商品分类：类别 → 商品列表",
            "defaultdict(list)",
            "分组聚合的黄金搭档，缺失键自动建列表",
            "分组 O(n)",
        ),
        (
            "8. 多层配置（默认+用户+环境变量 合并）",
            "ChainMap",
            "多个字典按优先级串联读取，写入只进第一层",
            "读取 O(层数)",
        ),
        (
            "9. 最近 N 条访问日志",
            "deque(maxlen=N)",
            "自动丢弃最旧元素，天然滑动窗口",
            "两端操作 O(1)",
        ),
        (
            "10. LRU 缓存（淘汰最久未用）",
            "OrderedDict",
            "需要 move_to_end + popitem(last=False) 淘汰最旧",
            "查找 O(1)，淘汰 O(1)",
        ),
    ]

    for title, container, reason, complexity in scenarios:
        print()
        print(f"  【{title}】")
        print(f"    推荐容器：{container}")
        print(f"    理由    ：{reason}")
        print(f"    复杂度  ：{complexity}")

    print()
    print("  ─────────────────────────────────────────────────────────")
    print("  ★ 选型口诀：")
    print("    索引有序可变 → list ｜ 固定不可变 → tuple")
    print("    去重存在判断 → set   ｜ 按键查值 → dict")
    print("    双端增删     → deque ｜ 分组计数 → defaultdict/Counter")
    print("    配置分层     → ChainMap ｜ 淘汰策略 → OrderedDict")


# ==============================================================================
# 第三部分：timeit 性能实测
# ==============================================================================
# ===== 语法解析 =====
# timeit.timeit(stmt, setup, number)
#   - stmt  ：要测的语句字符串
#   - setup ：每次执行前运行的准备代码（不计入耗时）
#   - number：执行次数（默认 1e6），取多次求平均降低噪声
#   设计意图：在同一进程内用高精度计时器对比方案，避免计时器本身开销。
def print_performance_benchmarks() -> None:
    print()
    print("=" * 68)
    print("第三部分：★ timeit 性能实测（秒级完成）")
    print("=" * 68)

    N = 100_000
    R = 20                        # 每组重复次数：控制总耗时在秒级

    print()
    print("  ─────────────────────────────────────────────────────────")
    print("  【测试1】去重：list 循环 vs set()")
    print("  ─────────────────────────────────────────────────────────")
    # ★ 规模说明：list 版 `x not in out` 是线性扫描，整体 O(n²)，
    #   数据量与重复次数必须压小（2万元素/2000不同值/重复5次）才能秒级完成。
    setup_dup = "data = [i % 2000 for i in range(20000)]"
    t_list_dup = timeit.timeit(
        """
out = []
for x in data:
    if x not in out:
        out.append(x)
""",
        setup=setup_dup,
        number=5,
    )
    t_set_dup = timeit.timeit("set(data)", setup=setup_dup, number=5)
    t_dict_dup = timeit.timeit("list(dict.fromkeys(data))", setup=setup_dup, number=5)
    print(f"    list 循环去重（保序）  {t_list_dup:>8.4f}s")
    print(f"    set() 去重（乱序）     {t_set_dup:>8.4f}s")
    print(f"    dict.fromkeys（保序）  {t_dict_dup:>8.4f}s")
    print(f"    ★ set 比 list 循环快 {t_list_dup / t_set_dup:>5.1f} 倍；fromkeys 兼顾保序与速度")

    print()
    print("  ─────────────────────────────────────────────────────────")
    print("  【测试2】成员查找：list vs set vs dict")
    print("  ─────────────────────────────────────────────────────────")
    probe = N // 2
    t_in_list = timeit.timeit(
        f"{probe} in d", setup="d = list(range(100000))", number=R * 5
    )
    t_in_set = timeit.timeit(
        f"{probe} in d", setup="d = set(range(100000))", number=R * 5
    )
    t_in_dict = timeit.timeit(
        f"{probe} in d", setup="d = dict.fromkeys(range(100000))", number=R * 5
    )
    print(f"    {probe} in list        {t_in_list:>8.4f}s   ← O(n) 线性扫描")
    print(f"    {probe} in set         {t_in_set:>8.4f}s   ← O(1) 哈希查找")
    print(f"    {probe} in dict        {t_in_dict:>8.4f}s   ← O(1) 哈希查找")
    print(f"    ★ set 比 list 快 {t_in_list / t_in_set:>5.1f} 倍，数据量越大差距越明显")

    print()
    print("  ─────────────────────────────────────────────────────────")
    print("  【测试3】按键查找：dict vs list of tuples（线性扫描）")
    print("  ─────────────────────────────────────────────────────────")
    setup_lookup = "d = {i: f'v{i}' for i in range(10000)}; pairs = list(d.items())"
    t_dict_get = timeit.timeit("d[5000]", setup=setup_lookup, number=R * 5)
    t_scan_list = timeit.timeit(
        "next(v for k, v in pairs if k == 5000)", setup=setup_lookup, number=R
    )
    print(f"    dict[5000]              {t_dict_get:>8.4f}s   ← O(1)")
    print(f"    list 中线性扫描找 5000    {t_scan_list:>8.4f}s   ← O(n)")
    print(f"    ★ dict 快 {t_scan_list / t_dict_get:>5.1f} 倍 —— 键值数据必须用 dict")

    print()
    print("  ─────────────────────────────────────────────────────────")
    print("  【测试4】两端操作：list vs deque")
    print("  ─────────────────────────────────────────────────────────")
    # ★ timeit 的 setup 在独立命名空间运行，用到 deque 必须自行导入
    setup_deque = "from collections import deque"
    t_list_head = timeit.timeit(
        """
l = []
for _ in range(100000):
    l.insert(0, 1)
""",
        setup="",
        number=1,
    )
    t_deque_head = timeit.timeit(
        """
d = deque()
for _ in range(100000):
    d.appendleft(1)
""",
        setup=setup_deque,
        number=1,
    )
    t_list_tail = timeit.timeit(
        """
l = []
for _ in range(100000):
    l.append(1)
""",
        setup="",
        number=1,
    )
    t_deque_tail = timeit.timeit(
        """
d = deque()
for _ in range(100000):
    d.append(1)
""",
        setup=setup_deque,
        number=1,
    )
    print(f"    list.insert(0) 头部加   {t_list_head:>8.4f}s   ← O(n)")
    print(f"    deque.appendleft 头加   {t_deque_head:>8.4f}s   ← O(1)")
    print(f"    list.append 尾部加      {t_list_tail:>8.4f}s   ← O(1)")
    print(f"    deque.append 尾部加     {t_deque_tail:>8.4f}s   ← O(1)")
    print(f"    ★ 头部操作 deque 快 {t_list_head / t_deque_head:>4.1f} 倍；尾部两者持平")

    print()
    print("  ─────────────────────────────────────────────────────────")
    print("  【测试5】集合运算：手写循环 vs set 运算符")
    print("  ─────────────────────────────────────────────────────────")
    setup_set = "a = set(range(3000)); b = set(range(1500, 4500)); c = list(range(3000)); d = list(range(1500, 4500))"
    # ★ list 版是 O(n·m)，1万×1万 仍偏慢，故缩到 3000 并重复 20 次以保证秒级完成
    t_handmade = timeit.timeit(
        "out = set(x for x in c if x in d)", setup=setup_set, number=20
    )
    t_operator = timeit.timeit("a & b", setup=setup_set, number=20)
    print(f"    list 手写求交集      {t_handmade:>8.4f}s")
    print(f"    set 运算符 a & b     {t_operator:>8.4f}s   ← C 层实现")
    print(f"    ★ 集合运算请直接用 & | - ^，比手写循环快 {t_handmade / t_operator:>4.1f} 倍")

    print()
    print("  ─────────────────────────────────────────────────────────")
    print("  【测试6】分组聚合：dict.setdefault vs defaultdict vs Counter")
    print("  ─────────────────────────────────────────────────────────")
    setup_group = f"data = [i % 100 for i in range({N})]"
    t_sd = timeit.timeit(
        """
out = {}
for x in data:
    if x not in out:
        out[x] = []
    out[x].append(1)
""",
        setup=setup_group,
        number=R,
    )
    t_dd = timeit.timeit(
        """
out = defaultdict(list)
for x in data:
    out[x].append(1)
""",
        setup=setup_group + "\nfrom collections import defaultdict",
        number=R,
    )
    t_ct = timeit.timeit("Counter(data)", setup=setup_group + "\nfrom collections import Counter", number=R)
    print(f"    setdefault 手动判断   {t_sd:>8.4f}s")
    print(f"    defaultdict(list)     {t_dd:>8.4f}s")
    print(f"    Counter（只计数）     {t_ct:>8.4f}s")
    print(f"    ★ defaultdict 比手写快 {t_sd / t_dd:>4.1f} 倍；只计数时 Counter 最快")

    print()
    print("  ─────────────────────────────────────────────────────────")
    print("  【测试7】排序：list.sort vs sorted vs 插入排序对比")
    print("  ─────────────────────────────────────────────────────────")
    setup_sort = "d = [i for i in range(10000)]; d.reverse()"
    t_sort = timeit.timeit("d.sort()", setup=setup_sort, number=R)
    t_sorted = timeit.timeit("r = sorted(d)", setup=setup_sort, number=R)
    t_key = timeit.timeit("r = sorted(d, key=lambda x: -x)", setup=setup_sort, number=R)
    print(f"    d.sort()            {t_sort:>8.4f}s   ← 原地，返回 None")
    print(f"    sorted(d)           {t_sorted:>8.4f}s   ← 新建列表")
    print(f"    sorted(d, key=...)  {t_key:>8.4f}s   ← 带比较函数")
    print(f"    ★ sort 略快（省一次列表分配）；key 版最慢但最灵活")

    print()
    print("  ─────────────────────────────────────────────────────────")
    print("  【测试8】内存占用对比")
    print("  ─────────────────────────────────────────────────────────")
    data = list(range(10000))
    print(f"    list(range(10000))          {sys.getsizeof(data):>8,} 字节")
    print(f"    tuple(range(10000))         {sys.getsizeof(tuple(data)):>8,} 字节")
    print(f"    set(range(10000))           {sys.getsizeof(set(data)):>8,} 字节")
    print(f"    dict.fromkeys(range(10000)) {sys.getsizeof(dict.fromkeys(data)):>8,} 字节")
    print(f"    deque(range(10000))         {sys.getsizeof(deque(data)):>8,} 字节")
    print(f"    ★ tuple 最省内存；dict 最大（键和值各存一份 + 哈希桶开销）")
    print(f"    ★ 空容器：list {sys.getsizeof([])}B  tuple {sys.getsizeof(())}B  dict {sys.getsizeof({})}B  set {sys.getsizeof(set())}B")


# ==============================================================================
# 第四部分：复杂度速查表
# ==============================================================================
def print_complexity_table() -> None:
    print()
    print("=" * 68)
    print("第四部分：时间复杂度速查表")
    print("=" * 68)

    print()
    print("  | 操作         | list      | tuple     | set         | dict        |")
    print("  |--------------|-----------|-----------|-------------|-------------|")
    rows = [
        ("尾部添加", "O(1)", "✗", "O(1)", "—"),
        ("头部添加", "O(n)", "✗", "O(1)", "—"),
        ("按下标读", "O(1)", "O(1)", "✗", "✗"),
        ("按下标写", "O(1)", "✗", "✗", "✗"),
        ("尾部删除", "O(1)", "✗", "O(1)", "O(1)"),
        ("按值删除", "O(n)", "✗", "O(1)", "O(1)"),
        ("成员查找", "O(n)", "O(n)", "O(1)", "O(1)"),
        ("按键查找", "✗", "✗", "✗", "O(1)"),
        ("排序", "O(nlogn)", "✗", "O(nlogn)", "O(nlogn)"),
        ("集合运算", "O(n)", "✗", "O(min(n,m))", "O(n)"),
        ("可哈希", "✗", "✓", "frozenset", "键✓ 值✗"),
    ]
    for op, li, tu, se, di in rows:
        print(f"  | {op:<12} | {li:<9} | {tu:<9} | {se:<11} | {di:<11} |")

    print()
    print("  ★ 关键理解：")
    print("    · O(1) = 常数时间，与数据量无关（哈希表 / 直接索引）")
    print("    · O(n) = 线性时间，扫一遍所有元素（list 的成员查找）")
    print("    · list 头部操作 O(n) 是因为需要搬移所有后续元素")
    print("    · set/dict 的 O(1) 前提是元素可哈希（不可变类型）")
    print("    · 大数据 + 查找密集 → 必须用 set/dict，这是最大的性能差距来源")


# ==============================================================================
# 第五部分：同一需求的多容器实现对比
# ==============================================================================
# ===== 语法解析 =====
# 需求：统计一段文本中每个单词的出现次数，并找出最高频的 3 个词。
# 分别用 list、dict、Counter、defaultdict 实现，对比代码量与性能。
def demo_same_task() -> None:
    print()
    print("=" * 68)
    print("第五部分：同一需求的 4 种实现对比（词频统计 Top3）")
    print("=" * 68)

    text = "python java python go java python rust go python java python"

    # 方案1：纯 list 循环（最原始）
    words = text.split()

    # (a) 嵌套循环计数 —— O(n²)
    def count_nested(ws: List[str]) -> Dict[str, int]:
        result: Dict[str, int] = {}
        for w in ws:
            if w in result:                 # list 的 in 是 O(n)
                result[w] += 1
            else:
                result[w] = 1
        return result

    # (b) 借助 set 辅助 —— O(n)
    def count_with_set(ws: List[str]) -> Dict[str, int]:
        seen = set(ws)                       # 先用 set 去重
        return {w: sum(1 for x in ws if x == w) for w in seen}  # 每个不同词扫一遍

    # (c) dict.get 累加 —— O(n)，最常用
    def count_with_dict(ws: List[str]) -> Dict[str, int]:
        result: Dict[str, int] = {}
        for w in ws:
            result[w] = result.get(w, 0) + 1  # get 返回默认值
        return result

    # (d) Counter —— O(n)，最简洁
    def count_with_counter(ws: List[str]) -> Dict[str, int]:
        return dict(Counter(ws))              # 一行搞定

    print()
    print(f"  需求文本：{text!r}")
    print(f"  目标：统计词频，取 Top3")

    print()
    print("  【方案1】dict.get 累加（最常用写法）")
    r1 = count_with_dict(words)
    top1 = sorted(r1.items(), key=lambda kv: kv[1], reverse=True)[:3]
    print(f"    词频: {r1}")
    print(f"    Top3: {top1}")
    print(f"    ★ 优势：O(n)，无需 import，通用性好")

    print()
    print("  【方案2】Counter（最简洁）")
    r2 = count_with_counter(words)
    top2 = Counter(words).most_common(3)      # 内置排行
    print(f"    词频: {r2}")
    print(f"    Top3: {top2}")
    print(f"    ★ 优势：一行完成计数+排行，但需 import Counter")

    print()
    print("  【方案3】set 去重 + 推导式")
    r3 = count_with_set(words)
    top3 = sorted(r3.items(), key=lambda kv: kv[1], reverse=True)[:3]
    print(f"    词频: {r3}")
    print(f"    Top3: {top3}")
    print(f"    ★ 优势：利用了 set 的 O(1) 查找，避免 in 的 O(n)")

    print()
    print("  【性能对比】这 4 种方案实测（timeit，重复 200 次）：")
    # ★ 注意：timeit 的 setup 字符串在独立命名空间中执行，
    #   因此必须把被测函数显式注入 setup，否则会 NameError。
    src_dict = """
def count_with_dict(ws):
    result = {}
    for w in ws:
        result[w] = result.get(w, 0) + 1
    return result
"""
    src_set = """
def count_with_set(ws):
    seen = set(ws)
    return {w: sum(1 for x in ws if x == w) for w in seen}
"""
    src_nested = """
def count_nested(ws):
    result = {}
    for w in ws:
        if w in result:
            result[w] += 1
        else:
            result[w] = 1
    return result
"""
    base = f"words = {words!r}\n"      # ★ 结尾必须有换行，否则拼接的 setup 会粘成一行
    t_get = timeit.timeit("count_with_dict(words)", setup=base + src_dict, number=200)
    t_set = timeit.timeit("count_with_set(words)", setup=base + src_set, number=200)
    t_ct = timeit.timeit("Counter(words)", setup=base + "from collections import Counter\n", number=200)
    t_nested = timeit.timeit("count_nested(words)", setup=base + src_nested, number=200)

    print(f"    dict.get 累加      {t_get:>8.4f}s   ← O(n)")
    print(f"    set 去重+推导式     {t_set:>8.4f}s   ← O(n×不同词数)")
    print(f"    Counter 内置       {t_ct:>8.4f}s   ← O(n)，C 层最快")
    print(f"    嵌套循环 O(n²)      {t_nested:>8.4f}s   ← 数据少时差异不明显，大数据会爆炸")
    print()
    print(f"    ★ 推荐顺序：Counter > dict.get > set 推导式 > 嵌套循环")
    print(f"    ★ 但 Counter 仅适用『纯计数』，需要自定义逻辑时 dict.get 更灵活")


# ==============================================================================
# 第六部分：选型速查卡
# ==============================================================================
def print_cheatsheet() -> None:
    print()
    print("=" * 68)
    print("第六部分：选型速查卡")
    print("=" * 68)

    print()
    print("  【标准容器】")
    print("  ┌─────────────────────────────────────────────────────────────┐")
    print("  │ 需要索引 + 顺序 + 可变          → list                      │")
    print("  │ 元素固定不变 / 要作 dict 键     → tuple                     │")
    print("  │ 去重 / 存在性 / 交并差集        → set                       │")
    print("  │ 键→值映射 / 快速按键查找        → dict                      │")
    print("  └─────────────────────────────────────────────────────────────┘")

    print()
    print("  【collections 扩展】")
    print("  ┌─────────────────────────────────────────────────────────────┐")
    print("  │ 两端增删 / FIFO / 滑动窗口      → deque                      │")
    print("  │ 计数器 / 词频 / TopN           → Counter                    │")
    print("  │ 分组聚合                       → defaultdict(list/set/int)  │")
    print("  │ 多层配置优先级                 → ChainMap                   │")
    print("  │ LRU / 需重排 / 顺序有语义      → OrderedDict                │")
    print("  │ 不可变数据 + 字段名            → namedtuple / NamedTuple    │")
    print("  └─────────────────────────────────────────────────────────────┘")

    print()
    print("  【collections 进阶（标准库外但常用）】")
    print("  ┌─────────────────────────────────────────────────────────────┐")
    print("  │ 有界容器（限制最大值）          → 自行实现 / itertools        │")
    print("  │ 不可变映射（可哈希的 dict）     → types.MappingProxyType    │")
    print("  │ 多重映射（一键多值）            → defaultdict(set)          │")
    print("  └─────────────────────────────────────────────────────────────┘")

    print()
    print("  ★ 最容易搞错的三个选择：")
    print("    1. 需要排序 → 必须 list（set/dict 无序），别用 set 排序代替")
    print("    2. 高频队列 → deque，别用 list.pop(0)（O(n) 会拖垮）")
    print("    3. 嵌套结构需频繁查键 → defaultdict，别写多层 .get() 链")


def main() -> None:
    """主函数：完整演示容器选型与性能实测。"""
    print_decision_tree()
    print_scenarios()
    print_performance_benchmarks()
    print_complexity_table()
    demo_same_task()
    print_cheatsheet()

    print()
    print("=" * 68)
    print("小结")
    print("=" * 68)
    print("  1. 选型核心：list=索引有序可变 ｜ tuple=固定不可变 ｜ set=去重唯一 ｜ dict=键值映射")
    print("  2. ★ 性能关键分水岭：成员查找与去重用 set/dict（O(1)）而非 list（O(n)）")
    print("  3. ★ deque 在头部操作上大幅领先 list（O(1) vs O(n)），队列场景必用 deque")
    print("  4. ★ Counter 是纯计数的最优解，defaultdict 是自定义分组的最优解")
    print("  5. 排序只有 list 支持；数据量 >1万且有查找需求时，务必换哈希容器")
    print("  6. 集合运算直接用 & | - ^，比手写循环快数十倍")
    print("  7. 内存：tuple < set ≈ deque < dict，dict 最大因为要存键值两份 + 哈希桶")
    print("  8. timeit 实测：setup 不计时、number 控制次数，务必多次取平均降噪声")


if __name__ == "__main__":
    main()