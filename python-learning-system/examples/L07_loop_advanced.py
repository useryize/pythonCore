"""L07 循环进阶与推导式基础 —— 配套教案配套示例。

运行：python examples/L07_loop_advanced.py

本脚本演示八件事：
    1. enumerate：同时拿到下标和值，正确处理 1-based 计数
    2. zip：并行遍历多组数据，以及「长度不等时按最短截断」的陷阱
    3. sorted(key=)：自定义排序的六种常见 key
    4. sum / max / min 的 key 参数与内置函数为何比手写快
    5. 嵌套循环的 break 技巧：一次退出多层循环
    6. 双重循环优化：把 O(n²) 降到 O(n) 的四种手法
    7. 累加器模式：累加、计数、字典聚合三种写法
    8. 生成器表达式与列表推导式：把「循环 + 收集」压成一行

⚠️ 纯标准库，可直接运行。
"""

import time                                      # 标准库：用于计时对比性能
from itertools import combinations               # 标准库：L08 会详讲，这里先感受一下

# ============================================================
# 模块级常量
# ============================================================
PERF_DATA_SIZE = 50_000                          # 性能对比的数据规模（保证脚本跑得快）
SHOW_TOP = 5                                     # 排行榜要显示的条数
TABLE_WIDTH = 4                                  # 表格列宽


# ============================================================
# 第 1 部分：enumerate —— 下标与值一起拿
# ============================================================
def demo_enumerate() -> None:
    """enumerate 是解决 off-by-one 的标准工具。"""
    print("【enumerate：把下标和值一起给你】\n")
    fruits = ["苹果", "香蕉", "橙子", "葡萄"]

    # 传统写法：需要手写 range(len(...)) 并做 i-1 换算
    print("  传统写法（下标 + 值，要手动换算）:")
    for i in range(len(fruits)):
        print(f"    第 {i + 1} 个是 {fruits[i]}   ⚠️ 每次都要 i+1 或 i-1，容易错")

    # enumerate 写法：直接给出 (下标, 值) 二元组
    print("\n  enumerate 写法（下标 + 值，自动对应）:")
    for i, fruit in enumerate(fruits):
        print(f"    下标 {i} → {fruit}")

    # start 参数：让下标从 1 开始，这是「人类计数」的正解
    print("\n  用 start=1 实现 1-based 计数（推荐）：")
    for rank, fruit in enumerate(fruits, start=1):
        print(f"    第 {rank} 名: {fruit}   ✅ 不用再 i+1 了")

    print("\n  start=2 用于「名次从第二名算起」的场景:")
    for rank, fruit in enumerate(fruits, start=2):
        print(f"    名次 {rank}: {fruit}")

    # 返回的是元组，可以按需要拆开用
    print("\n  enumerate 返回的是元组，可以只要其中一项：")
    indices = [i for i, _ in enumerate(fruits)]
    values = [v for _, v in enumerate(fruits)]
    print(f"    只要下标: {indices}")
    print(f"    只要值  : {values}   （但如果不需要下标，直接 for f in fruits 更好）")

    # 实战：找出重复出现的城市名，并报出第一次出现的位置
    print("\n【实战：找出重复出现的城市名，并报出第一次出现的位置】")
    cities = ["北京", "上海", "北京", "广州", "上海", "北京"]
    seen_positions: dict[str, int] = {}
    # enumerate 让「第一次出现在第几个」这件事变得容易表达
    for idx, city_name in enumerate(cities):
        if city_name in seen_positions:           # 字典查询 O(1)
            first_at = seen_positions[city_name]
            print(f"    第 {idx} 位的 {city_name} 与第 {first_at} 位重复（间隔 {idx - first_at}）")
        else:
            seen_positions[city_name] = idx        # 记下第一次出现的位置
    print(f"    出现过的城市: {list(seen_positions)}")

    # 实战：找出所有重复的编号及其出现位置（enumerate 让定位变得容易）
    print("\n【实战：定位重复编号的所有下标】")
    ids = [101, 102, 101, 103, 101, 104, 102]
    positions: dict[int, list[int]] = {}
    for idx, item_id in enumerate(ids):
        positions.setdefault(item_id, []).append(idx)   # 字典聚合模式
    for item_id, idx_list in positions.items():
        if len(idx_list) > 1:
            print(f"    编号 {item_id} 出现在下标 {idx_list}，共 {len(idx_list)} 次")


# ============================================================
# 第 2 部分：zip —— 并行遍历
# ============================================================
def demo_zip() -> None:
    """zip 把多组数据「拉链」起来一起遍历。"""
    print("【zip：把多组数据配成对一起遍历】\n")

    names = ["张三", "李四", "王五"]
    scores = [88, 92, 79]
    ages = [20, 25, 30]

    # 传统写法：用下标同时取多个列表的元素
    print("  传统写法（下标对齐）：")
    for i in range(len(names)):
        print(f"    {names[i]} {ages[i]} 岁 {scores[i]} 分")
    print("  ⚠️ 要求所有列表长度一致，否则 IndexError")

    # zip 写法：语法清晰，长度不一致时自动按最短截断
    print("\n  zip 写法：")
    for name, score, age in zip(names, scores, ages):
        print(f"    {name} {age} 岁 {score} 分")

    # start 也能给（3.10+）
    print("\n  zip(..., strict=True)（3.10+）：长度不等时直接报错")
    short_list = [1, 2]
    long_list = [1, 2, 3]
    # 默认行为：按最短的截断，静默丢失数据
    pairs_default = list(zip(short_list, long_list))
    print(f"    默认 zip   : {pairs_default}   ⚠️ 静默丢掉 {long_list[len(short_list):]}")
    # strict=True：长度不等立刻抛 ValueError，更安全
    try:
        _ = list(zip(short_list, long_list, strict=True))
    except ValueError as exc:
        print(f"    strict=True: ValueError: {exc}   ✅ 主动暴露问题")

    print("\n  zip 还能遍历字典的键和值：")
    user = {"name": "张三", "age": 20, "city": "北京"}
    for key, value in zip(user.keys(), user.values()):
        print(f"    {key} = {value}")
    # 更推荐 items()：意图更明确，也少一层调用
    print("  💡 遍历字典键值对用 items() 比 zip(keys(), values()) 更好")

    print("\n  zip 还能并行遍历「不同类型」：")
    # 把字符串和列表 zip 在一起，得到 (字符, 元素) 的配对
    letters = "abc"
    nums = [1, 2, 3]
    for ch, n in zip(letters, nums):
        print(f"    字母 {ch} 对应数字 {n}   → {'A' * n}")

    print("\n  zip 常见用途：两个有序序列做「对比/配对/求差」")
    # 求两个订单金额的差（假设两者按时间一一对应）
    print("  两个月的销售额求差：")
    jan = [1200, 1500, 1800]
    feb = [1350, 1400, 2100]
    for month, (a, b) in zip(("1月", "2月"), zip(jan, feb)):
        delta = b - a
        trend = "增长" if delta > 0 else "下滑" if delta < 0 else "持平"
        print(f"    {month}: {a} → {b}，{trend} {abs(delta)}")

    print("\n  ⚠️ zip 的惰性：它是一个「迭代器」，用一次就没了")
    z = zip(names, scores)
    first_pass = list(z)
    second_pass = list(z)
    print(f"    第一次转 list: {first_pass}")
    print(f"    第二次转 list: {second_pass}   ⚠️ 空！需要重新创建 zip 对象")


# ============================================================
# 第 3 部分：sorted(key=) 自定义排序
# ============================================================
def demo_sorted_key() -> None:
    """key 参数把「按什么排」的逻辑抽出来，代码立刻清晰。"""
    print("【sorted 的 key 参数：告诉 Python「按什么排」】\n")

    users = [
        {"name": "张三", "age": 25, "score": 88, "city": "北京"},
        {"name": "李四", "age": 30, "score": 95, "city": "上海"},
        {"name": "王五", "age": 22, "score": 72, "city": "广州"},
        {"name": "赵六", "age": 28, "score": 95, "city": "深圳"},
    ]

    # 1) 不传 key：按元素本身排序（字典无法直接比较，会报错）
    print("1) 不传 key")
    print(f"   sorted 数字列表: {sorted([3, 1, 4, 1, 5])}   ✅ 直接排序")
    try:
        _ = sorted(users)
    except TypeError as exc:
        print(f"   sorted 字典列表: TypeError: {exc}\n")

    # 2) key=lambda x: x['字段']：最常见的排序
    print("2) 按某个字段排序")
    by_age = sorted(users, key=lambda u: u["age"])
    print(f"   按年龄升序: {[(u['name'], u['age']) for u in by_age]}")
    by_age_desc = sorted(users, key=lambda u: u["age"], reverse=True)
    print(f"   按年龄降序: {[(u['name'], u['age']) for u in by_age_desc]}")
    print(f"   💡 reverse=True 让代码从「年龄最大」倒着写变成正着写，避免逻辑反转错误")

    # 3) 多级排序：key 返回元组
    print("\n3) 多级排序：key 返回元组，按位置依次比较")
    multi = sorted(users, key=lambda u: (u["score"], u["age"]))
    print(f"   先按分数再按年龄: {[(u['name'], u['score'], u['age']) for u in multi]}")
    print("   💡 元组比较是逐元素的：先比第一个，相等才比第二个")

    # 4) key 用内置函数（更快，因为不是 Python 层函数）
    print("\n4) key 传内置函数：len / str.lower / abs")
    words = ["banana", "Apple", "cherry", "date"]
    print(f"   默认（区分大小写）: {sorted(words)}")
    print(f"   key=str.lower     : {sorted(words, key=str.lower)}   ✅ 忽略大小写")
    print(f"   key=len           : {sorted(words, key=len)}   按长度排")
    nums = [-5, 3, -1, 10, -20]
    print(f"   数字默认排序       : {sorted(nums)}")
    print(f"   key=abs（按绝对值）: {sorted(nums, key=abs)}   → {sorted(nums, key=abs)}")

    # 5) operator.itemgetter：多字段排序的快捷方式
    print("\n5) itemgetter：等价于 lambda，但由 C 实现，更快")
    import operator
    fast = sorted(users, key=operator.itemgetter("score"))
    slow = sorted(users, key=lambda u: u["score"])
    print(f"   itemgetter 结果 == lambda 结果: {fast == slow}   ✅ 完全一致")
    multi_fast = sorted(users, key=operator.itemgetter("score", "age"))   # 多字段
    multi_slow = sorted(users, key=lambda u: (u["score"], u["age"]))
    print(f"   多字段版本也一致: {multi_fast == multi_slow}")

    # 6) sorted 返回新列表，不改原列表（与 list.sort() 的关键区别）
    print("\n6) sorted 不改原列表，list.sort() 原地改")
    original = [3, 1, 2]
    result = sorted(original)
    print(f"   original = {original}   ← 没被改")
    print(f"   result   = {result}   ← 新列表")
    in_place = [3, 1, 2]
    in_place.sort()
    print(f"   sort() 后 = {in_place}   ← 原地修改，且返回 None！")

    print("\n7) 实战：多维排行榜")
    # 先按分数降序，分数相同再按年龄升序（年轻人优先）
    ranking = sorted(users, key=lambda u: (-u["score"], u["age"]))
    print(f"   {'排名':<6}{'姓名':<8}{'分数':<8}{'年龄':<6}{'城市'}")
    for rank, u in enumerate(ranking, start=1):
        print(f"   {rank:<6}{u['name']:<8}{u['score']:<8}{u['age']:<6}{u['city']}")
    print("   💡 降序技巧：key 里取负号，而不是反转列表（后者会破坏并列顺序）")


# ============================================================
# 第 4 部分：sum / max / min
# ============================================================
def demo_aggregate_functions() -> None:
    """内置聚合函数：写得更短、更快、更不易错。"""
    print("【sum / max / min：不用写循环的聚合函数】\n")

    nums = [10, 25, 3, 47, 18, 30]

    # 手写循环 vs 内置函数
    total_manual = 0
    for n in nums:
        total_manual += n
    print(f"1) 求和")
    print(f"   手写循环: {total_manual}")
    print(f"   sum():   {sum(nums)}   ✅ 结果一致，代码短一半且快很多")

    # sum 的三个实用参数
    print(f"\n2) sum 的实用参数")
    print(f"   sum(nums, 100)   = {sum(nums, 100)}   # start 参数：加一个初始值")
    print(f"   sum([0.1]*10)    = {sum([0.1] * 10):.2f}  # 注意浮点累加有误差")
    print(f"   sum([], 0)       = {sum([], 0)}   ⚠️ 空列表会报错，必须给 start")

    # max / min
    print(f"\n3) max / min")
    print(f"   max(nums) = {max(nums)}, min(nums) = {min(nums)}")
    # max 可以带 key：按什么标准找最大值
    users = [
        {"name": "张三", "age": 25},
        {"name": "李四", "age": 30},
        {"name": "王五", "age": 22},
    ]
    oldest = max(users, key=lambda u: u["age"])
    print(f"   max(users, key=age) = {oldest['name']}（{oldest['age']} 岁）")
    # 带 key 的 max 支持多个 key，返回第一个最大值
    best = max(users, key=lambda u: (u["age"], u["name"]))
    print(f"   多字段 max = {best['name']}")

    # 求最大/最小/最长的字符串
    words = ["apple", "banana", "cherry"]
    print(f"   max(words, key=len) = {max(words, key=len)}   # 最长的单词")

    # 找极值的位置
    print(f"\n4) 找极值所在的索引")
    idx_max = nums.index(max(nums))              # ⚠️ 有坑：只能找「第一个」最大值
    print(f"   nums.index(max(nums)) = {idx_max}（值 {max(nums)}）")
    # 如果要精确找出所有最大值的位置，用 enumerate + key
    all_max_positions = [i for i, v in enumerate(nums) if v == max(nums)]
    print(f"   所有最大值位置: {all_max_positions}")
    print("   ⚠️ nums.index() 只能返回第一次出现的位置，重复值要小心")

    # 其他常用的聚合函数
    print(f"\n5) 其他聚合函数（L08 会系统讲列表）")
    print(f"   any([0, 0, 1])  = {any([0, 0, 1])}    # 至少一个为真")
    print(f"   all([1, 1, 0])  = {all([1, 1, 0])}    # 全部为真才算真")
    print(f"   len(nums)       = {len(nums)}")
    avg = sum(nums) / len(nums)
    print(f"   平均值          = {avg:.2f}")
    # ⚠️ 浮点数求平均有误差，工业做法是先求和再除，或用 Decimal / Fraction
    print(f"   ⚠️ sum([0.1]*3)/3 = {sum([0.1] * 3) / 3:.17f}   浮点误差暴露")

    print(f"\n6) ⚠️ 用内置函数而不是 sum(生成器) 来求整数和")
    # 教学示例：小规模下没有差别，但规模大时内置函数快一个数量级
    small = list(range(100_000))
    t0 = time.perf_counter()
    manual = 0
    for n in small:
        manual += n
    t1 = time.perf_counter()
    built_in = sum(small)
    t2 = time.perf_counter()
    print(f"   手写循环 {t1 - t0:.4f} 秒，sum() {t2 - t1:.4f} 秒，"
          f"加速 {(t1 - t0) / max(t2 - t1, 1e-9):.0f} 倍")
    print(f"   结果一致: {manual == built_in}   ✅ 数值都是 {built_in}")
    print("   💡 原因：sum 的循环在 C 层执行，省去每轮的字节码解释开销")


# ============================================================
# 第 5 部分：嵌套循环的 break 技巧
# ============================================================
def demo_nested_break() -> None:
    """如何从双层循环里「一次性」跳出来——四种方案。"""
    print("【双层循环的 break：break 只跳一层，怎么办】\n")
    matrix = [
        [1, 2, 3],
        [4, 5, 6],
        [7, 8, 9],
    ]
    target = 5

    print("  方案 1（❌ 天真版）：break 只跳出内层")
    hits: list[tuple[int, int]] = []
    for r in range(len(matrix)):
        for c in range(len(matrix[r])):
            if matrix[r][c] == target:
                hits.append((r, c))
                break                              # 只跳出内层！外层继续跑完
    print(f"    执行了 {len(hits)} 次内层 break，剩下 2 层白跑了")

    print("\n  方案 2（✅ 标志变量）：内层 break，外层检查标志")
    hit = None
    for r in range(len(matrix)):
        for c in range(len(matrix[r])):
            if matrix[r][c] == target:
                hit = (r, c)
                break
        if hit is not None:                       # 每轮外层结束检查一次
            break
    print(f"    找到位置: {hit}   ✅ 第一层就停了")

    print("\n  方案 3（✅✅ 函数 + return）：最推荐、最干净")
    def locate(m: list[list[int]], t: int) -> tuple[int, int] | None:
        """用 return 一次性退出所有层循环。"""
        for r, row in enumerate(m):
            for c, value in enumerate(row):
                if value == t:
                    return r, c                   # 直接退出函数，等于跳出所有循环
        return None
    print(f"    找到位置: {locate(matrix, target)}   ✅ 找到即返回，无需标志变量")
    print(f"    找不到: {locate(matrix, 99)}   ✅ 走到函数末尾返回 None")
    print("    💡 函数天然形成一层作用域，return 是「跳出一切」的最强武器")

    print("\n  方案 4（✅ 哨兵值 / itertools.takewhile）：更进阶")
    import itertools
    # 把嵌套循环拍平成一维，用 any() 短路：找到就停
    flat = [(r, c, v) for r, row in enumerate(matrix) for c, v in enumerate(row)]
    found = next((t for t in flat if t[2] == target), None)
    print(f"    拍平后用 next(生成器, 默认值) 找: {found}")

    # any + 生成器是「找到即停」的组合拳
    def locate_any(m: list[list[int]], t: int) -> tuple[int, int] | None:
        """用 any + 嵌套生成器，天然短路。"""
        return next(
            ((r, c) for r, row in enumerate(m) for c, v in enumerate(row) if v == t),
            None,
        )
    print(f"    any 风格: {locate_any(matrix, target)}   ✅ any 会在找到 True 时立即停")
    print("    💡 面试高频：能说清「为什么这里要用 return 而不是 break」就是加分项")

    print("\n  方案 5（itertools 模块）：标准库直接提供「配对」能力")
    # combinations 一次生成所有两两组合，不用写双重循环
    pairs = list(combinations([1, 2, 3, 4], 2))
    print(f"    combinations([1,2,3,4], 2) = {pairs}   # 不用嵌套循环")


# ============================================================
# 第 6 部分：双重循环优化
# ============================================================
def find_pair_sum_two_pass(nums: list[int], target: int) -> tuple[int, int] | None:
    """方法 A：双重循环，O(n²)。作为基线。"""
    # 最朴素的做法：枚举所有数对
    for i in range(len(nums)):
        for j in range(i + 1, len(nums)):        # j 从 i+1 开始，避免重复枚举和无意义比较
            if nums[i] + nums[j] == target:
                return nums[i], nums[j]
    return None


def find_pair_sum_hash(nums: list[int], target: int) -> tuple[int, int] | None:
    """方法 B：哈希表 + 一次遍历，O(n)。"""
    # 核心思路：遍历到 x 时，检查 target - x 是否已在「看过的数」中
    seen: dict[int, int] = {}                    # 值 -> 出现位置（便于报错定位）
    for idx, x in enumerate(nums):
        need = target - x                        # 需要的配对值
        if need in seen:                         # 哈希查询 O(1)
            return x, need
        seen[x] = idx                             # 记下看过的数
    return None


def find_pair_sum_two_pointer(nums: list[int], target: int) -> tuple[int, int] | None:
    """方法 C：排序 + 双指针，O(n log n)，但要求有额外空间。"""
    # 前置条件：nums 必须已排序（所以先 copy 一份，不改原列表）
    arr = sorted(nums)
    left, right = 0, len(arr) - 1                 # 双指针从两端向中间靠
    while left < right:                          # ⚠️ 必须 left < right，否则会用到同一个元素两次
        s = arr[left] + arr[right]
        if s == target:
            return arr[left], arr[right]
        if s < target:
            left += 1                            # 和太小，左指针右移（变大）
        else:
            right -= 1                           # 和太大，右指针左移（变小）
    return None


def demo_double_loop_optimization() -> None:
    """四种降复杂度手法 + 真实性能对比。"""
    print("【双重循环优化：把 O(n²) 变成 O(n)】\n")

    nums = [2, 7, 11, 15, 3, 6, 1, 20]
    target = 22
    print(f"  数据: {nums}")
    print(f"  目标: 和为 {target}\n")
    print(f"  A) 双重循环   : {find_pair_sum_two_pass(nums, target)}   O(n²)")
    print(f"  B) 哈希表     : {find_pair_sum_hash(nums, target)}   O(n)  ✅ 推荐")
    print(f"  C) 双指针     : {find_pair_sum_two_pointer(nums, target)}   O(n log n)\n")

    # 把判断移到循环外：内层循环的 if 提到外面，减少内层的判断次数
    print("【手法 1：把筛选条件提到循环外，避免无效迭代】")
    data = list(range(100_000))
    evens = [x * 2 for x in data if x % 2 == 0]     # 筛选后再计算
    print(f"  先筛选后计算: 得到 {len(evens)} 个偶数倍")
    print("  ❌ 低效写法（if 嵌在循环体里，每次都要重新判断）：")
    print("     for x in data:")
    print("         if x % 2 == 0:")
    print("             result.append(x * 2)")
    print("  ✅ 先用推导式把符合条件的筛出来，循环体内只做计算，逻辑更清晰")

    # 手法 2：把内层循环的重复计算提到外面
    print("\n【手法 2：把「不变的量」提到循环外】")
    # ❌ 低效：len(data) 每轮都算一次（虽然快，但仍是无谓调用）
    # for i in range(len(data)):
    #     if i < len(data) - 1:            # ← 每轮重算 len(data)
    #         ...
    n = len(data)                              # ✅ 算一次，存到变量
    for i in range(n):
        if i < n - 1:
            break
    print(f"  把 len(data) 存到 n = {n}，循环体内不再调用")

    # 手法 3：用集合加速成员判断
    print("\n【手法 3：成员判断从 O(n) 降到 O(1)（用 set）】")
    small = list(range(1000))
    target_set = set(small)                     # 列表转集合，构建一次 O(n)
    checks = [999, 1000, 5000]                  # 准备查询
    # 在集合里查，O(1)
    results_set = [x in target_set for x in checks]
    print(f"  set 查询结果: {results_set}   （每个查询约 1 次哈希计算）")
    print("  💡 经验：查询次数多 + 数据量大时，list 转 set 是必做优化")

    # 手法 4：用推导式替代「循环 + 条件 + 收集」三段式
    print("\n【手法 4：推导式替代「循环 + 判断 + 收集」三段式】")
    # ❌ 低效三段式
    result = []
    for x in small:
        if x % 100 == 0:
            result.append(x)
    # ✅ 推导式：一行表达同样逻辑，且没有 append 的方法调用开销
    result2 = [x for x in small if x % 100 == 0]
    print(f"  三段式:   共 {len(result)} 个：{result[:8]}...")
    print(f"  推导式:   共 {len(result2)} 个：{result2[:8]}...")
    print(f"  结果一致: {result == result2}")

    # 真实性能对比
    print("\n【真实性能对比：数据量 5 万时】")
    big = list(range(PERF_DATA_SIZE))
    goal = PERF_DATA_SIZE - 3 + 999            # 构造一个一定存在的目标（999 在列表里）
    t0 = time.perf_counter()
    find_pair_sum_two_pass(big, goal)
    t1 = time.perf_counter()
    find_pair_sum_hash(big, goal)
    t2 = time.perf_counter()
    print(f"  A) 双重循环: {t1 - t0:.4f} 秒")
    print(f"  B) 哈希表  : {t2 - t1:.4f} 秒")
    speedup = (t1 - t0) / max(t2 - t1, 1e-9)
    print(f"  加速比    : {speedup:.0f} 倍")
    print("  💡 数据量越大，差距越夸张。这就是面试官爱问「你怎么优化」的原因")


# ============================================================
# 第 7 部分：累加器模式
# ============================================================
def demo_accumulator() -> None:
    """累加器是循环最核心的模式：把每轮的结果「攒」起来。"""
    print("【累加器模式：循环的三种经典变体】\n")

    # 变体 1：累加器初值必须是「单位元」
    print("1) 求和：初值必须是 0（加法的单位元）")
    prices = [19.9, 35.5, 8.0, 128.0]
    total = 0                                    # ⚠️ 必须初始化，否则 NameError
    for p in prices:
        total += p
    print(f"   {total:.2f} 元   （验证 sum: {sum(prices):.2f}）")
    # ⚠️ 陷阱：如果初值写成第一个元素，循环里又加了一遍
    wrong = prices[0]
    for p in prices:
        wrong += p
    print(f"   ⚠️ 初值写成 prices[0] 会得到 {wrong:.2f}，第一个元素被算了两次")

    print("\n2) 求积：初值必须是 1（乘法的单位元）")
    product = 1                                  # 乘法的单位元
    for p in [1, 2, 3, 4, 5]:
        product *= p
    print(f"   1×2×3×4×5 = {product}")

    print("\n3) 求最大值：初值必须是 -inf 或列表第一个元素")
    # 陷阱：初值写 0 时，如果所有数据都是负数，结果会错
    negatives = [-5, -8, -3]
    max_manual = negatives[0]                    # ✅ 用第一个元素，不会错
    for n in negatives[1:]:
        if n > max_manual:
            max_manual = n
    print(f"   {negatives} 的最大值 = {max_manual}   ✅")
    # 错误示范：初值写 0
    wrong_max = 0
    for n in negatives:
        if n > wrong_max:
            wrong_max = n
    print(f"   ⚠️ 初值写 0 得到 {wrong_max}，全负数时会漏掉 -3")

    print("\n4) 字典聚合：把元素按条件分组（最实用的累加器）")
    orders = [
        {"city": "北京", "amount": 100},
        {"city": "上海", "amount": 200},
        {"city": "北京", "amount": 150},
        {"city": "广州", "amount": 80},
        {"city": "上海", "amount": 120},
    ]
    # 累加一个字典：key 是分组，value 是该组的合计
    by_city: dict[str, int] = {}
    for order in orders:
        city = order["city"]
        # setdefault 的第二个参数只在 key 不存在时使用，等价于「先判断再赋值」
        by_city[city] = by_city.get(city, 0) + order["amount"]
    print(f"   各城市销售额: {by_city}")
    # L08 会讲 collections.defaultdict 的写法，更简洁

    print("\n5) 计数聚合：统计每个词出现的次数")
    words = "python is great python is simple python is fun".split()
    word_count: dict[str, int] = {}
    for w in words:
        word_count[w] = word_count.get(w, 0) + 1
    print(f"   词频统计: {word_count}")
    print(f"   最高频的词: {max(word_count, key=word_count.get)}（出现 {max(word_count.values())} 次）")

    print("\n6) 列表累加器：收集满足条件的元素")
    evens: list[int] = []                        # 累加器是一个列表
    for n in range(1, 20):
        if n % 2 == 0:
            evens.append(n)
    print(f"   偶数: {evens}")
    # 迭代遍历两个累加器（同一列表的增删交替）—— 常见于去重
    print("\n7) 单列表去重：借「已见集合」实现 O(n)")
    seen: set[int] = set()                       # set 累加器
    unique: list[int] = []                       # list 累加器
    for n in [3, 1, 3, 2, 1, 4, 3, 5, 2]:
        if n not in seen:                        # set 查询 O(1)
            seen.add(n)                          # 加入已见集合
            unique.append(n)                     # 加入结果列表
    print(f"   原序列: [3, 1, 3, 2, 1, 4, 3, 5, 2]")
    print(f"   去重后: {unique}   （保持原顺序）")


# ============================================================
# 第 8 部分：生成器表达式与列表推导式
# ============================================================
def demo_comprehensions() -> None:
    """推导式：把「循环 + 收集」压成一行，并按需求选对类型。"""
    print("【列表推导式：等价于循环 + append，但写得更紧凑】\n")

    data = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]

    # 循环写法
    squares_loop = []
    for n in data:
        squares_loop.append(n ** 2)
    # 推导式写法
    squares_comp = [n ** 2 for n in data]
    print(f"1) 基本用法：求平方")
    print(f"   循环     : {squares_loop}")
    print(f"   推导式   : {squares_comp}")
    print(f"   结果一致 : {squares_loop == squares_comp}   ✅\n")

    # 带条件过滤
    evens_comp = [n for n in data if n % 2 == 0]
    print(f"2) 带过滤：[n for n in data if n % 2 == 0] = {evens_comp}")
    # if-else：把 if 写在最前面做「值变换」，不是过滤
    parity = ["偶" if n % 2 == 0 else "奇" for n in data[:6]]
    print(f"   if-else（值变换）: {parity}")
    print("   💡 区别：if 在后面 = 过滤；if 在前面 = 三元表达式，做值变换\n")

    # 双重 for = 嵌套循环
    matrix = [[1, 2], [3, 4]]
    flat = [v for row in matrix for v in row]
    print(f"3) 双重 for（嵌套循环压平）：{flat}")
    # 结果等价于嵌套循环
    print(f"   等价于: {[v for row in matrix for v in row]} = {flat}")

    # 带条件的三重嵌套：九九乘法表
    table = [f"{i}×{j}={i*j}" for i in range(1, 4) for j in range(1, i + 1)]
    print(f"\n4) 三角形数据（三重结构）:")
    for line in table:
        print(f"   {line}")

    # 带 if 过滤的双重推导式：找出所有「和为偶数」的配对
    pairs = [(a, b) for a in data[:5] for b in data[:5] if (a + b) % 2 == 0 and a < b]
    print(f"\n5) 双重 + 过滤（找出和为偶数的不同数对）：{pairs[:8]} ...")

    print("\n" + "=" * 64)
    print("【生成器表达式：加括号变惰性，不占内存】\n")

    # 列表推导式 vs 生成器表达式的本质区别
    list_comp = [n * 2 for n in range(10)]        # 立刻生成完整列表
    gen_comp = (n * 2 for n in range(10))         # 只生成「描述」，不执行
    print(f"  列表推导式（立即求值）: {list_comp}")
    print(f"  生成器表达式（惰性）  : {gen_comp}   ← 此时什么都没算")
    print(f"  用掉它才计算: {list(gen_comp)}")
    # 关键区别：能否重复遍历
    g = (n for n in range(3))
    print(f"\n  ⚠️ 生成器只能遍历一次：")
    print(f"     第 1 次: {list(g)}")
    print(f"     第 2 次: {list(g)}   ← 已经被消耗完了")
    # 列表可以重复遍历
    lst = [n for n in range(3)]
    print(f"  列表可以重复遍历：第 1 次 {lst}，第 2 次 {lst}")

    print("\n【生成器的优势：处理大数据时不爆内存】")
    # 列表推导式会立刻创建 100 万元素的列表，占用大量内存
    huge_list = [n for n in range(1_000_000)]
    print(f"  列表推导式：已创建 {len(huge_list):,} 个元素的列表，内存占用大")
    # 生成器表达式逐个产出，用完即弃，内存几乎不增长
    huge_gen = (n for n in range(1_000_000))
    # sum 会把生成器消耗掉
    total = sum(huge_gen)
    print(f"  生成器表达式：sum() 得到 {total:,}，内存占用极小")
    print(f"  💡 处理大文件/大数据流时，生成器是必备工具（L26 会深入讲）")

    print("\n【何时用哪个：决策表】")
    print("  需要重复遍历 → 列表推导式")
    print("  只遍历一次   → 生成器表达式")
    print("  数据量极大   → 生成器表达式")
    print("  需要 len() / 索引 / 切片 → 列表推导式（生成器不支持）")

    # 验证生成器不支持索引
    print("\n  验证：生成器不支持 len 和索引")
    try:
        _ = len(huge_gen)  # 已被消耗，这里会报 TypeError
    except TypeError as exc:
        print(f"     len(生成器) -> TypeError: {exc}   ← 所以只能用 list() 转换后取")

    print("\n【双推导式：dict / set 推导式】")
    # 字典推导式：{key_expr: value_expr for ...}
    word_lengths = {w: len(w) for w in ["apple", "banana", "cherry"]}
    print(f"  字典推导式: {word_lengths}")
    # set 推导式：{expr for ...}，自动去重
    unique_lengths = {len(w) for w in ["ab", "cd", "ef", "gh"]}
    print(f"  set 推导式（自动去重）: {unique_lengths}")
    print("  💡 推导式是 Python 最「Pythonic」的表达数据转换的方式（L08 会全面展开）")


# ============================================================
# 自我检验
# ============================================================
def verify_advanced_loops() -> None:
    """用断言确认 L07 的核心工具。"""
    # enumerate
    assert list(enumerate(["a", "b"])) == [(0, "a"), (1, "b")]
    assert list(enumerate(["a", "b"], start=1)) == [(1, "a"), (2, "b")]
    # zip
    assert list(zip([1, 2], ["a", "b"])) == [(1, "a"), (2, "b")]
    assert list(zip([1, 2], [1, 2, 3])) == [(1, 1), (2, 2)]   # 按最短截断
    # sorted 的 key
    words = ["banana", "Apple"]
    assert sorted(words) == ["Apple", "banana"]                # 大写优先（ASCII 顺序）
    assert sorted(words, key=str.lower) == ["Apple", "banana"]
    assert sorted([3, 1, 2], key=lambda x: -x) == [3, 2, 1]  # 降序技巧
    assert sorted(["a", "bb", "c"], key=len) == ["a", "c", "bb"]
    # max/min 的 key
    assert max([1, 5, 3], key=lambda x: -x) == 1              # 找「负数最小」即原数最大
    assert min(["apple", "fig"], key=len) == "fig"
    # sum / max / min 基本
    assert sum([1, 2, 3]) == 6
    assert sum([1, 2], 10) == 13                                # start 参数
    assert max([1, 3, 2]) == 3 and min([1, 3, 2]) == 1
    assert any([0, 0, 1]) is True and all([1, 0]) is False
    # sorted 不改原列表
    original = [3, 1, 2]
    _ = sorted(original)
    assert original == [3, 1, 2]
    # 推导式
    assert [n * 2 for n in range(4)] == [0, 2, 4, 6]
    assert [n for n in range(6) if n % 2 == 0] == [0, 2, 4]
    assert {n: n * 2 for n in range(3)} == {0: 0, 1: 2, 2: 4}
    assert {len(w) for w in ["a", "bb", "c"]} == {1, 2}
    # 生成器表达式
    g = (n for n in range(3))
    assert list(g) == [0, 1, 2]
    assert list(g) == []                                       # 只能消耗一次
    # 三种求和算法结果一致（⚠️ 注意顺序可能不同，所以要排序后比较）
    nums_12 = [1, 5, 11, 13]
    a = find_pair_sum_two_pass(nums_12, 12)
    b = find_pair_sum_hash(nums_12, 12)
    c = find_pair_sum_two_pointer(nums_12, 12)
    print(f"  两遍法 {a}，哈希法 {b}，双指针 {c}")
    assert tuple(sorted(a)) == tuple(sorted(b)) == tuple(sorted(c)) == (1, 11)
    # 双指针边界：相同数值的两个不同位置也可以配对
    assert find_pair_sum_two_pointer([3, 3], 6) == (3, 3)
    print("✅ verify_advanced_loops 全部断言通过")


# ============================================================
# 程序入口
# ============================================================
def main() -> None:
    """按教学顺序调用全部演示函数。"""
    print("=" * 64)
    print("L07 · 循环进阶与推导式基础")
    print("=" * 64)
    demo_enumerate()
    print("\n" + "-" * 64)
    demo_zip()
    print("\n" + "-" * 64)
    demo_sorted_key()
    print("\n" + "-" * 64)
    demo_aggregate_functions()
    print("\n" + "-" * 64)
    demo_nested_break()
    print("\n" + "-" * 64)
    demo_double_loop_optimization()
    print("\n" + "-" * 64)
    demo_accumulator()
    print("\n" + "-" * 64)
    demo_comprehensions()
    print("\n" + "-" * 64)
    verify_advanced_loops()
    print("\n🎉 L07 演示结束")


# 标准入口约定：直接运行本文件执行 main()，被 import 时不执行
if __name__ == "__main__":
    main()
