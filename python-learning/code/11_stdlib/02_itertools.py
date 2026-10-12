"""
================================================================================
 02_itertools.py  ——  itertools：惰性迭代器工厂
================================================================================

【与 09_functional 的侧重区别】
 - 09_functional 侧重【语言特性】：高阶函数、闭包、lambda、推导式
 - 本文件    侧重【标准库解决具体问题】：拿到 itertools 能替代哪些手写循环

【演示的语法点】
 1. 无限迭代器：count / cycle / repeat（惰性，必须配 islice 截断）
 2. 终止迭代器：chain / compress / dropwhile / takewhile / islice / pairwise
 3. 过滤类：filterfalse / takewhile / dropwhile
 4. 组合类：product / permutations / combinations / combinations_with_replacement
 5. 分组类：groupby（★ 必须先排序）
 6. 累加类：accumulate（比手写循环快）
 7. 索引类：enumerate / zip_longest / starmap / map
 8. 实战：笛卡尔积配置、去重、聚合、指数退避、密码强度

【预期输出摘要】
 - "accumulate" 小节：手写前缀和循环 vs accumulate 的耗时对比
 - "groupby" 小节：连续分组 vs 按 key 分组的差异（★ 易错点）
 - "实战" 小节：打印所有密码组合与退避序列
================================================================================

"""

from __future__ import annotations

import itertools
import operator
import time
from itertools import (accumulate, chain, combinations, compress, count, cycle, islice,
                        permutations, product, repeat)


# ===== 语法解析 =====
# 【1】★ 惰性迭代器：itertools 的核心设计理念
#   语法规则：所有 itertools 工具返回的是【迭代器】，不是列表
#   执行顺序：调用函数 → 只返回一个"状态机"对象（不计算任何元素）
#             真正取数发生在 for / next() 时，且【取一个算一个】
#   设计意图：
#     - 内存恒定为 O(1)，可以处理无限序列（count 永远数不完）
#     - 可以对接生成器管道：数据在管道中【流式流动】，不落地成大列表
#   ⚠ 三大坑：
#     1. 迭代器【只能消费一次】，耗尽后再 for 就是空；需要复用 → list() 包一层
#     2. 长度未知且没有 __len__，要用 len(x) 必须先 list() 或用 islice + enumerate
#     3. 不要在无限迭代器上直接 for（如 cycle），会死循环
def demo_lazy() -> None:
    # 无限计数器：只能靠 islice 截断
    print(f"  count(10, 2) 前 5 个：{list(islice(count(10, 2), 5))}")
    print(f"  cycle('AB') 前 7 个：{list(islice(cycle('AB'), 7))}")
    print(f"  repeat('x', 3) = {list(repeat('x', 3))}")
    print(f"  repeat('x', 3) 的 len：{len(list(repeat('x', 3)))}")  # 迭代器没有 len

    # ⚠ 验证"惰性"：counter 计数到 100 才打印，说明前 99 个都没被计算
    counter = count(1)
    list(islice(counter, 100))
    print(f"  取完 100 个后，counter 的下一个值 = {next(counter)}   ← 惰性证据")

    # 管道风格：数据在生成器之间流动，全程不落地
    pipeline = chain("abc", "def")
    print(f"  chain('abc','def') = {list(pipeline)}")
    # chain.from_iterable：展平"可迭代对象组成的可迭代对象"（只展平一层）
    pipeline2 = chain.from_iterable(["ab", ["cd", ["e"]]])
    print(f"  chain.from_iterable 展平一层 = {list(pipeline2)}")
    # ⚠ 注意末尾的 ['e'] 仍是列表：from_iterable 只处理一层，元素本身若是序列不会被拆开
    #   真正要深度展平得自己递归，或用 3.11+ 的 itertools.batched 之类组合

    # compress：用布尔选择器筛选数据（比 zip + 过滤更简洁）
    data = [1, 2, 3, 4, 5, 6]
    mask = [True, False, True, False, False, True]
    print(f"  compress({data}, {mask}) = {list(compress(data, mask))}")

    # takewhile / dropwhile：按【条件】而不是按位置截断（遇到第一个假值就停）
    prices = [3, 1, 2, 8, 12, 5]
    print(f"  takewhile(<6) = {list(itertools.takewhile(lambda x: x < 6, prices))}")
    print(f"  dropwhile(<6) = {list(itertools.dropwhile(lambda x: x < 6, prices))}")
    # ⚠ 与 filter 的区别：filter 会检查【每一个】元素，takewhile 遇到 False 就【中断整个迭代】

    # pairwise：滑动相邻二元组，比手写 zip(a, a[1:]) 高效
    nums = [1, 2, 3, 4, 5]
    print(f"  pairwise({nums}) = {list(itertools.pairwise(nums))}")

    # 实战：计算差分序列（相邻两项相减）
    diffs = [(b - a, a, b) for a, b in itertools.pairwise([1, 4, 9, 16])]
    print(f"  相邻差分 = {diffs}")


# ===== 语法解析 =====
# 【2】组合类：笛卡尔积、排列、组合
#   语法规则：
#     product(A, B)                      笛卡尔积，A[0]*B[0]*... 个
#     permutations(A, r)                 排列，取 r 个【不重复】，顺序有关
#     combinations(A, r)                 组合，取 r 个【不重复】，顺序无关
#     combinations_with_replacement(A,r) 组合，允许重复
#   参数 repeat=  等价于把同一个序列传多次：product(A, repeat=2) == product(A, A)
#   设计意图：这些函数【内部用位置索引访问】，不复制输入，r 小的时候极省内存。
def demo_combinations() -> None:
    # product：两种支付方式 × 三个套餐 = 6 种配置
    print(f"  product 笛卡尔积：{list(product([1, 2], 'AB'))}")
    # repeat 关键字：洗牌 3 副牌 = 52*51*50 种排列（只取前 3 个演示）
    cards = ["A♠", "K♠"]
    print(f"  product(repeat=2) 前 3：{list(islice(product(cards, repeat=2), 3))}")

    # permutations：顺序不同算不同排列
    print(f"  permutations('ABC', 2) = {list(permutations('ABC', 2))}")
    # combinations：顺序无关（会自动去重，因为要求输入有序）
    print(f"  combinations('ABC', 2) = {list(combinations('ABC', 2))}")
    print(f"  combinations_with_replacement('AB', 2) = "
          f"{list(itertools.combinations_with_replacement('AB', 2))}")

    # ⚠ 重要：combinations 的输入必须【已排序】才能得到不重复的结果
    dup = ["B", "A", "B"]
    print(f"  ⚠ combinations(['B','A','B'], 2) = {list(combinations(dup, 2))}   ← 有重复")
    print(f"  ✅ 先排序再组合 = {list(combinations(sorted(dup), 2))}   ← 已去重")

    # 实战 1：三人两两握手的所有组合（36 场球赛）
    teams = ["A队", "B队", "C队", "D队"]
    games = list(combinations(teams, 2))
    print(f"  {len(teams)} 队两两对阵共 {len(games)} 场：{games}")

    # 实战 2：暴力破解 4 位数字密码（每位独立任选，用 product 而非组合）
    #   ⚠ 密码字符【有顺序】，必须用 product(迭代器, repeat=n)；
    #   combinations_with_replacement 产出的一定是"升序"元组（如 0247），
    #   永远穷举不出 0427 这种乱序密码 —— 这是选错函数的典型后果。
    digits = "0123456789"
    found = None
    attempts = 0
    for combo in product(digits, repeat=4):        # 10^4 = 10000 种，有序
        attempts += 1
        if "".join(combo) == "0427":
            found = "".join(combo)
            break
    print(f"  4 位密码穷举：尝试 {attempts} 次命中 {found}（第 {attempts} 种）")
    # 验证反例：组合方式穷举 10C4=715 种，压根遇不到 "0427"
    print(f"  对比：用 combinations_with_replacement 穷举永远得不到 0427"
          f"（只产出升序元组，共 {len(list(itertools.combinations_with_replacement(digits, 4)))} 种）")


# ===== 语法解析 =====
# 【3】★ groupby：分组迭代器（最易用错的一个）
#   语法规则：groupby(iterable, key=None)
#   - 它【只能对【连续的】相同 key 分组】，不是按 key 全局归拢！
#   - 因此使用前通常必须先 sorted(iterable, key=...)
#   - 迭代结果为 (key, group) 二元组；group 是个迭代器，【用过即废】
#   执行过程：
#     1. 内部记录上一个 key
#     2. 逐个取元素，若 key 变了才 yield 出一个新组
#   设计意图：为了不消耗额外内存去建 dict（groupby 是流式的）。
#   ⚠ 连续 vs 全局：
#     [A,A,B,B,A,A] → groupby 得 3 组（AA BB AA），Counter 得 2 类（A:4 B:2）
def demo_groupby() -> None:
    raw = [("a", 1), ("a", 2), ("b", 3), ("b", 4), ("a", 5)]

    # ⚠ 未排序：相同 key 不相邻 → 被切成 3 组
    print("  未排序直接 groupby：")
    for key, group in itertools.groupby(raw, key=lambda x: x[0]):
        print(f"    key={key} → 组内 {list(group)}")
    # 结论：'a' 出现了【两组】，这通常不是我们想要的

    # ✅ 先排序，让相同 key 相邻 → 正确合并成 2 组
    print("  先 sorted 再 groupby：")
    for key, group in itertools.groupby(sorted(raw, key=lambda x: x[0]), key=lambda x: x[0]):
        print(f"    key={key} → 组内 {list(group)}")

    # ⚠ 组迭代器【一次性】：不先转 list，第二次就空了
    _, grp = next(itertools.groupby(sorted(raw, key=lambda x: x[0]), key=lambda x: x[0]))
    #   注意：这里必须先 next() 取出 (key, group) 二元组，再对 group 取 list
    print(f"  group 第一次取：{list(grp)}")
    print(f"  group 第二次取：{list(grp)}   ← 已耗尽，必须在循环内立刻消费")

    # 实战：把日志按级别聚合，输出每个级别的条数
    logs = [
        ("INFO", "服务启动"), ("ERROR", "连接失败"), ("INFO", "处理请求"),
        ("DEBUG", "进入分支"), ("ERROR", "超时"), ("INFO", "关闭连接"),
    ]
    summary = {}
    for level, items in itertools.groupby(sorted(logs, key=lambda x: x[0]), key=lambda x: x[0]):
        summary[level] = list(items)          # ★ 必须立刻转 list，否则丢失
    for level in sorted(summary):
        print(f"    {level:<6} {len(summary[level])} 条  {[m for _, m in summary[level]]}")

    # groupby 也可用于对已排序的数值做连续区间分组
    temps = [21, 22, 23, 28, 29, 15, 16]
    sorted_t = sorted(temps)
    print(f"  按 10 度分箱：")
    for k, g in itertools.groupby(sorted_t, key=lambda t: t // 10 * 10):
        vals = list(g)
        print(f"    [{k}, {k+10}) → {len(vals)} 个: {vals}")


# ===== 语法解析 =====
# 【4】accumulate：前缀运算，比手写循环快
#   语法规则：accumulate(iterable, func=operator.add, *, initial=None)
#   - 默认 func 是 operator.add（累加）
#   - 给 func=operator.mul 得前缀乘积；func=max 得"历史最大值"序列
#   设计意图：省掉每次迭代里的一次函数调用开销（纯 C 层循环）。
def demo_accumulate() -> None:
    nums = [1, 2, 3, 4, 5]
    print(f"  前缀和 = {list(accumulate(nums))}")
    print(f"  前缀积 = {list(accumulate(nums, operator.mul))}")
    print(f"  历史最大 = {list(accumulate(nums, max))}")
    print(f"  带 initial=0 = {list(accumulate(nums, initial=0))}   ← initial 多算一项")

    # 实战 1：算移动平均（accumulate + 差分）
    series = [10, 12, 15, 11, 20]
    acc = [0] + list(accumulate(series))      # 前缀为 0，使 sums[i] 表示"前 i 项之和"
    sums = acc
    # 3 点移动平均 = 第 i 项减去第 i-3 项；i 从 3 到 len(series)，共 len-2 个窗口
    ma3 = [(sums[i] - sums[i - 3]) / 3 for i in range(3, len(series) + 1)]
    print(f"  原序列   {series}")
    print(f"  前缀和   {acc}")
    print(f"  3 点移动平均 {['%.2f' % v for v in ma3]}   ← 共 {len(ma3)} 个窗口")

    # 实战 2：投资复利增长
    balance = 10000
    rates = [0.03, -0.01, 0.05]
    balances = [balance]
    for r in rates:
        balance *= 1 + r
        balances.append(round(balance, 2))
    print(f"  复利变化：{balances}")

    # 性能对比：手写 for 累加 vs accumulate（遍历 20 万次）
    big = list(range(200_000))
    t0 = time.perf_counter()
    total = 0
    for x in big:
        total += x
    t_loop = time.perf_counter() - t0

    t0 = time.perf_counter()
    total2 = sum(big)        # sum 同样是 C 层，比 accumulate 更适合单纯求和
    t_sum = time.perf_counter() - t0

    t0 = time.perf_counter()
    total3 = list(accumulate(big))
    t_acc = time.perf_counter() - t0

    print(f"  20 万次求和：手写 for {t_loop * 1000:.2f} ms | sum() {t_sum * 1000:.2f} ms "
          f"| accumulate {t_acc * 1000:.2f} ms")
    print(f"  三者结果一致：{total == total2 == total3[-1]}")
    # 结论：单纯求和用 sum（最快）；需要前缀序列才用 accumulate（它多算了 n-1 次中间值）


# ===== 语法解析 =====
# 【5】索引与打包：enumerate / zip / starmap
#   语法规则：
#     enumerate(iterable, start=0)  → (下标, 值)
#     zip(a, b)                    → 同步遍历多个序列，【短的到头就停】
#     zip_longest(a, b, fillvalue) → 【长的走完】，短的用 fillvalue 补
#     starmap(func, iterable)      → func(*每个元组)，把元组展开成多参数
#   设计意图：zip 的"最短优先"是安全的（不会解包出长度不足的元组），
#             需要补齐时用 zip_longest 显式表达意图。
def demo_zip() -> None:
    names = ["张三", "李四", "王五", "赵六"]
    scores = [90, 85, 95]                # 比 names 少一个

    # zip 最短优先：只产出 3 组，第 4 个人直接被丢弃
    print(f"  zip 截断：{list(zip(names, scores))}")
    print(f"  长度：{len(list(zip(names, scores)))}")

    # zip_longest：长的走完，短的位置填 fillvalue
    print(f"  zip_longest：{list(itertools.zip_longest(names, scores, fillvalue='缺考'))}")

    # starmap：把 ((3,4),) 这样的元组展开成 pow(3,4)
    print(f"  starmap(pow) = {list(itertools.starmap(pow, [(2, 3), (3, 2)]))}")
    # 对比 map：map 是逐元素传一个参数
    print(f"  map(lambda x: x*2) = {list(map(lambda x: x * 2, [1, 2, 3]))}")

    # 实战：合并两份配置，缺失项用默认值补齐
    defaults = {"host": "localhost", "port": 80, "debug": False}
    custom = {"port": 8080, "debug": True}
    merged = {**defaults, **custom}       # ★ 列表字典合并的常规写法
    print(f"  配置合并 = {merged}")

    # 实战的表格对齐：两列长度不一致时也能对齐输出
    for i, (n, s) in enumerate(itertools.zip_longest(names, scores, fillvalue="-"), start=1):
        print(f"    {i}. {n:<4} 分数={s}")


# ===== 语法解析 =====
# 【6】实战工具箱：把上面几个工具组合起来
def demo_practice() -> None:
    # ① 指数退避序列：重试间隔 0.5, 1, 2, 4, 8 秒（最多 5 次）
    backoff = [0.5 * (2 ** i) for i in range(5)]
    print(f"  指数退避（秒）：{backoff}")

    # ② 配置矩阵：3 台服务器 × 2 种模式
    servers = ["web01", "web02", "web03"]
    modes = ["debug", "prod"]
    for server, mode in product(servers, modes):
        print(f"    部署 {server} @ {mode}")

    # ③ 分批：把任务列表按每批 3 个切分
    tasks = [f"T{i}" for i in range(1, 8)]
    size = 3
    chunks = [tasks[i:i + size] for i in range(0, len(tasks), size)]
    print(f"  每组 {size} 个切分：{chunks}")
    print(f"  共 {len(chunks)} 批，最后一批 {len(chunks[-1])} 个（不足 size 也保留）")

    # ⚠ 反例警示：zip_longest 配【无限迭代器】会永不结束！
    #   因为 zip_longest 以【最长】为准，而 count() 没有尽头 → 内存耗尽。
    #   反过来 zip(有限的, 无限的) 则以短的为准，安全。
    #   （此处只演示前 3 项就主动用 islice 掐断，避免真的跑飞）
    demo_pair = list(islice(
        zip(tasks, itertools.count(1)), 3))    # zip 取短者，安全
    print(f"  zip(有限, 无限) 安全取前 3：{demo_pair}")
    # ⚠ 危险写法（不要真跑）：list(zip_longest(tasks, itertools.count()))
    #   → 永不终止，最终 MemoryError。这就是"惰性迭代器 + 无限源"的经典事故。

    # ④ 密码强度：要求至少包含大小写+数字
    def strong(pw: str) -> bool:
        return (any(c.islower() for c in pw) and any(c.isupper() for c in pw)
                and any(c.isdigit() for c in pw))

    candidates = list(product("aA1", repeat=3))   # 3^3 = 27 种，product 本身就是有限迭代器
    ok = [w for w in map("".join, candidates) if strong(w)]
    print(f"  满足「大小写+数字」的 3 位串：共 {len(ok)} 种，示例 {ok[:5]}")

    # ⑤ 去重但保序：用 dict 去重（3.7+ 字典保序）
    raw = [3, 1, 3, 2, 1, 4]
    seen = list(dict.fromkeys(raw))       # ★ 标准保序去重技巧
    print(f"  原序列 {raw} → 保序去重 {seen}")
    # 对比：set 去重会【丢失顺序】
    print(f"  set 去重 {list(set(raw))}   ← 顺序不保证")


def main() -> None:
    print("=" * 60)
    print("【1】惰性迭代器与终止工具")
    print("=" * 60)
    demo_lazy()

    print()
    print("=" * 60)
    print("【2】组合类：product / permutations / combinations")
    print("=" * 60)
    demo_combinations()

    print()
    print("=" * 60)
    print("【3】groupby 分组（★ 最易用错）")
    print("=" * 60)
    demo_groupby()

    print()
    print("=" * 60)
    print("【4】accumulate 累加与性能对比")
    print("=" * 60)
    demo_accumulate()

    print()
    print("=" * 60)
    print("【5】索引与打包：zip / zip_longest / starmap")
    print("=" * 60)
    demo_zip()

    print()
    print("=" * 60)
    print("【6】实战工具箱")
    print("=" * 60)
    demo_practice()

    print()
    print("=" * 60)
    print("小结")
    print("=" * 60)
    print("  1. itertools 返回惰性迭代器：内存 O(1)，但只能消费一次")
    print("  2. 无限序列必须配 islice 取用，否则死循环")
    print("  3. groupby 只对【连续】的相同 key 分组，使用前必须排序")
    print("  4. group 的迭代器一次性消耗，必须在循环内立刻转 list")
    print("  5. combinations 要求输入有序才能得到不重复组合")
    print("  6. 单纯求和用 sum，需要前缀序列才用 accumulate")
    print("  7. zip 最短优先，zip_longest 用 fillvalue 补齐")


if __name__ == "__main__":
    main()