"""L06 循环基础 —— 配套教案配套示例。

运行：python examples/L06_loops.py

本脚本演示七件事：
    1. for + range 的五个参数，以及为什么默认从 0 开始
    2. for 直接遍历可迭代对象（比 range + 下标更 Pythonic）
    3. while 的适用场景与「计数变量」写法
    4. break / continue / else 的完整语义（else 是「没被打断」才执行）
    5. 嵌套循环：外层内层的职责划分
    6. 常见循环模式：累加、计数、查找、去重、斐波那契
    7. 三大高频坑：死循环、range 边界、循环内修改容器

⚠️ 纯标准库，可直接运行。
"""

import time                                     # 标准库：演示累加器与计时

# ============================================================
# 模块级常量
# ============================================================
FIRST_N = 10                                    # 打印前 N 个数
GUESS_LIMIT = 5                                 # 猜数字游戏的次数上限
MAX_STEPS = 1000                                # 循环步数上限，安全阀
FIB_COUNT = 12                                  # 计算前 12 个斐波那契数
NESTED_LIMIT = 5                                # 嵌套循环的外层次数
STEP = 1                                        # 步长默认值


# ============================================================
# 第 1 部分：for + range
# ============================================================
def demo_range_basics() -> None:
    """range 的五个参数与常见变体。"""
    print("【range(start, stop, step)】stop 不包含在结果里（左闭右开）\n")
    # 最常见：range(stop)，从 0 到 stop-1
    print(f"range({FIRST_N})        -> {list(range(FIRST_N))}")
    print(f"  长度 = {len(list(range(FIRST_N)))}，含 0 不含 {FIRST_N}\n")

    # range(start, stop)：从 start 到 stop-1
    print(f"range(2, 6)     -> {list(range(2, 6))}   # 2 3 4 5")
    print(f"range(-3, 3)    -> {list(range(-3, 3))}  # 支持负数\n")

    # range(start, stop, step)：带步长
    print(f"range(0, 10, 2) -> {list(range(0, 10, 2))}  # 偶数")
    print(f"range(10, 0, -1) -> {list(range(10, 0, -1))} # 倒序 10..1")
    print(f"range(0, 10, 3) -> {list(range(0, 10, 3))}  # 步长 3，最后一个不足也照样输出")
    print(f"range(5)        -> {list(range(5, 0, -2))} # 注意顺序：stop 必须是 0 才递减\n")

    # range 的三个「陷阱」
    print("【三个必知细节】")
    # 1) range 是惰性的，不占内存
    r = range(1_000_000_000)          # 10 亿元素，但内存占用几乎为零
    print(f"  1) range(10亿) 的内存占用 = {r.__sizeof__()} 字节（不真正创建元素）")
    # 2) range 只支持整数
    try:
        _ = range(1.0, 5.0)
    except TypeError as exc:
        print(f"  2) range 不支持小数: TypeError: {exc}")
    # 3) 步长为 0 会报错
    try:
        _ = range(0, 10, 0)
    except ValueError as exc:
        print(f"  3) 步长不能为 0: ValueError: {exc}")
    # 补充：len 和 in 对 range 有效，但不遍历
    print(f"  补充: len(range(10)) = {len(range(10))}，999 in range(1000) = {999 in range(1000)}（O(1) 计算）")


def demo_for_over_iterable() -> None:
    """直接遍历对象，是 Python 最地道 的循环写法。"""
    print("【for 直接遍历可迭代对象 —— 比 range + 下标更推荐】")

    # 遍历列表
    fruits = ["苹果", "香蕉", "橙子"]
    print(f"\n1) 遍历列表 {fruits}")
    for fruit in fruits:
        print(f"   - {fruit}")

    # 遍历字符串得到的是单个字符
    print("\n2) 遍历字符串")
    for ch in "AB":
        print(f"   - {ch!r}")

    # 遍历字典得到的是「键」
    print("\n3) 遍历字典只得到键（这是高频误解）")
    scores = {"张三": 90, "李四": 85}
    for key in scores:
        print(f"   - 键: {key}")
    print(f"   想要键值对要用 items(): {list(scores.items())}")
    print(f"   想要值要用 values()  : {list(scores.values())}")

    # 遍历集合（⚠️ 顺序不保证，不能依赖）
    print("\n4) 遍历集合 —— 顺序不保证，不能依赖它")
    nums = {3, 1, 2}
    print(f"   {nums} 的遍历顺序: {list(nums)}   ⚠️ 每次运行可能不同")

    # ⚠️ 遍历嵌套结构时，别名指向同一个对象
    print("\n5) ⚠️ 别名问题：两个变量指向同一个列表对象")
    a_list = [1, 2, 3]
    b_list = a_list                    # b_list 是 a_list 的另一个名字
    b_list.append(4)                    # 改动会互相影响
    print(f"   a_list = {a_list}, b_list = {b_list}   ⚠️ 都变成 4 个元素了")

    # 正确做法：需要独立副本时显式拷贝
    c_list = a_list.copy()
    c_list.append(5)
    print(f"   用 copy() 后 a_list = {a_list}, c_list = {c_list}   ✅ 互不影响")


def demo_range_pitfalls() -> None:
    """range 的边界问题：为什么最后总是「差一点」。"""
    print("【range 边界：为什么我少了一个？】")
    data = ["A", "B", "C", "D"]

    print("\n  错误：range(1, len(data)) —— 漏掉了最后一个 D")
    result = []
    for i in range(1, len(data)):
        result.append(data[i])
    print(f"    得到 {result}   ⚠️ 漏了 D")

    print("\n  正确：range(len(data)) —— 从 0 开始全覆盖")
    result = []
    for i in range(len(data)):
        result.append(data[i])
    print(f"    得到 {result}   ✅")

    print("\n  1-based 想清楚：range(1, len(data) + 1)，但索引要用 i - 1")
    for i in range(1, len(data) + 1):
        print(f"    第 {i} 个是 {data[i - 1]}   ⚠️ 一定要减 1，这就是 off-by-one")

    print("\n【⚠️ 结论：Python 里 99% 的情况不应该手写 range(len(x))】")
    print("  需求：按顺序取元素 → 直接 for item in data")
    print("  需求：既要元素又要下标 → 用 enumerate（L07 详讲）")
    print("  手写 range(len(...)) 只是为了理解原理，真实代码里应避免")


# ============================================================
# 第 2 部分：while 循环
# ============================================================
def demo_while_loop() -> None:
    """while 的语法、计数变量模板、以及与 for 的选择。"""
    print("【while 语法：条件为真就重复】")
    # while 的三要素：初始化、判断、更新。缺一个就是死循环
    count = 0                            # ① 初始化计数变量
    while count < FIRST_N:               # ② 条件判断
        print(f"   count = {count}", end="")   # ③ 循环体
        count += 1                       # ④ 更新计数器 —— 漏了这行就是死循环
    print("\n   循环结束，count =", count)

    print("\n【为什么用 while 而不是 for 的本意场景】")
    # 场景 1：次数事先未知，由数据决定
    print("1) 处理未知长度的输入流（读到结束为止）")
    lines = ["第一行", "第二行", "第三行"]
    idx = 0
    while idx < len(lines):
        print(f"   读到: {lines[idx]}")
        idx += 1

    # 场景 2：模拟一个需要「每次做不同事」的递减过程
    print("\n2) 倒计时类任务")
    fuel = 3
    while fuel > 0:
        print(f"   剩余燃料 {fuel}，继续")
        fuel -= 1
    print(f"   燃料耗尽，剩余 {fuel}")

    # 场景 3：条件复杂到无法用 range 表达
    print("\n3) 条件复杂的循环（斐波那契）")
    a, b = 0, 1
    produced = 0
    while produced < FIB_COUNT:
        a, b = b, a + b                   # Python 的元组解包同时更新两个变量
        produced += 1
    print(f"   前 {FIB_COUNT} 个斐波那契数已生成，当前 a={a}, b={b}")

    print("\n【⚠️ while 的两大风险】")
    print("  1) 死循环：忘记更新计数器 → 程序永远跑下去，只能 Ctrl+C")
    print("  2) 无限输入：while True 必须有 break 出口，否则永不退出")
    print("\n【for vs while 的选择原则】")
    print("  ✅ 用 for：已知要循环几次 / 要遍历某个集合")
    print("  ✅ 用 while：不知道次数，条件由业务决定（如等待某事件发生）")


def demo_while_else_and_patterns() -> None:
    """while 的常见模式，以及安全阀写法。"""
    print("【模式 1：while + 条件变量 + 计数器三重保险】")
    # 安全阀：即使业务逻辑写错，也不会真的死循环
    steps = 0
    x = 1
    while x < 1000 and steps < MAX_STEPS:      # 加一个步数上限
        x *= 2
        steps += 1
    print(f"   x = {x}, 共 {steps} 步   ← 安全阀让程序永远能结束")

    print("\n【模式 2：累加器模式 —— 循环最核心的用途】")
    # 初始化累加器在循环外，每轮把新值加进去
    total = 0
    for i in range(1, 101):
        total += i
    print(f"   1 到 100 的和 = {total}")
    # 验证用内置函数（性能更好，L07 详讲）
    print(f"   用 sum() 验证  = {sum(range(1, 101))}   ✅ 一致")

    print("\n【模式 3：计数模式 —— 统计满足条件的个数】")
    numbers = [3, 7, 12, 8, 20, 5, 15, 1, 9, 30]
    count = 0
    for n in numbers:
        if n > 10:
            count += 1                       # 满足条件才计数
    print(f"   大于 10 的个数 = {count}")
    print(f"   原列表共 {len(numbers)} 个，验证一下: {[n for n in numbers if n > 10]}")

    print("\n【模式 4：查找模式 —— 找到就退出】")
    target = 20
    for i, n in enumerate(numbers):
        if n == target:
            print(f"   找到 {target}，位置是第 {i} 个（下标 {i}）")
            break
    else:
        print(f"   未找到 {target}")          # for-else 的 else 分支

    print("\n【模式 5：while 模拟「逐字符输入」】")
    text = "a b c"
    pos = 0
    while pos < len(text):
        ch = text[pos]
        if ch != " ":
            print(f"   第 {pos} 位: {ch!r}")
        pos += 1


# ============================================================
# 第 3 部分：break / continue / else
# ============================================================
def demo_break_continue_else() -> None:
    """三个关键字的完整语义，especially for-else 这个反直觉设计。"""
    print("【break：立刻跳出整个循环】")
    for i in range(10):
        if i == 3:
            print(f"   i={i} 时 break")
            break
    print("   循环结束\n")

    print("【continue：跳过本轮剩余部分，进入下一轮】")
    skipped = []
    for i in range(6):
        if i % 2 == 0:
            skipped.append(i)                 # 记录被跳过的
            continue                          # 偶数跳过
        print(f"   处理奇数 {i}")
    print(f"   跳过的偶数: {skipped}\n")

    print("【continue 的近亲：if/else 结构更清晰】")
    # 对比：continue 的替代写法是把主逻辑放进 if
    print("  写法 A（用 continue）:")
    for i in range(6):
        if i % 2 == 0:
            continue
        print(f"    A: 奇数 {i}", end="")
    print()
    print("  写法 B（主逻辑在 if 里，更扁平）:")
    for i in range(6):
        if i % 2 != 0:
            print(f"    B: 奇数 {i}", end="")
    print("\n  💡 经验：只有一个 continue 时改用 if 包裹正文，代码更平\n")

    print("【⭐ for-else：整个循环「没有被打断」时才执行 else】")
    # 这是 Python 特有的设计，意义是「区分正常遍历完 vs 提前 break 退出」
    print("\n  场景 1：找到就 break，else 不执行")
    numbers = [3, 7, 12, 8, 20]
    found, used_for_else = search_with_for_else(numbers, 8)
    print(f"   找 8 的结果: {found}，else 是否执行: {used_for_else}   ← 找到就 break，else 被跳过")

    print("\n  场景 2：没找到，循环正常走完，else 执行")
    found, used_for_else = search_with_for_else(numbers, 999)
    print(f"   找 999 的结果: {found}，else 是否执行: {used_for_else}   ← 没有 break，else 执行了")

    print("\n【for-else 的等价手写版（不用 else 时怎么写）】")
    # 用一个标志变量模拟，但更啰嗦
    def find_first_manual(data: list[int], target: int) -> int | None:
        """不用 for-else 的等价写法。"""
        result = None
        for i, v in enumerate(data):
            if v == target:
                result = i
                break
        # 因为 result 初始是 None，找不到自然就是 None
        return result
    print(f"   手写版找 8   = {find_first_manual(numbers, 8)}")
    print(f"   手写版找 999 = {find_first_manual(numbers, 999)}   ← 代码更长但更直观")


def search_with_for_else(data: list[int], target: int) -> tuple[int | None, bool]:
    """用 for-else 实现查找，返回 (结果, else 是否被执行)。

    返回两个值是为了让「else 到底有没有跑」这件事变得可观察，
    这正是 for-else 最反直觉、也最需要验证的地方。
    """
    result: int | None = None
    else_ran = False
    for i, value in enumerate(data):
        if value == target:
            result = i
            break                                # 一旦 break，下面的 else 被跳过
    else:
        # 只有「循环自然结束、一次 break 都没有」才会走到这里
        else_ran = True
    return result, else_ran


def demo_for_else_advanced() -> None:
    """for-else 在 while 和嵌套场景中的行为。"""
    print("【while-else 与 for-else 语义相同】")
    n = 5
    steps = 0
    while n > 1:
        n //= 2
        steps += 1
        if steps > 10:
            break
    else:
        print(f"   while 正常结束，共 {steps} 步（n 变成了 {n}）")
    print("   注意：while 的 else 在 break 时同样会跳过\n")

    print("【⭐ 嵌套循环里 for-else 的正确用法】")
    # 经典需求：内层循环找到就跳出「双层循环」
    matrix = [[1, 2, 3], [4, 5, 6], [7, 8, 9]]
    target = 5

    # ❌ 错误写法：break 只跳出内层，外层还在继续找（结果可能是错的）
    wrong_pos = None
    for r in range(len(matrix)):
        for c in range(len(matrix[r])):
            if matrix[r][c] == target:
                wrong_pos = (r, c)
                break                           # 只跳出内层！外层继续，下一轮可能覆盖 wrong_pos
    print(f"   错误写法结果: {wrong_pos}   ← 可能被后续循环污染")

    # ✅ 正确写法：用标志变量或函数返回
    def find_in_matrix(m: list[list[int]], t: int) -> tuple[int, int] | None:
        """用函数返回实现「找到就彻底结束双层循环」。"""
        for r in range(len(m)):
            for c in range(len(m[r])):
                if m[r][c] == t:
                    return r, c                # return 直接退出整个函数
        return None

    right_pos = find_in_matrix(matrix, target)
    print(f"   正确写法结果: {right_pos}   ← 用 return 一次性退出双层循环 ✅")

    # ✅ 也可以用标志变量（下一个例子会详讲）


# ============================================================
# 第 4 部分：嵌套循环
# ============================================================
def demo_nested_loops() -> None:
    """嵌套循环的结构、执行顺序与典型用途。"""
    print("【嵌套循环：外层控制行，内层控制列】")
    print("\n1) 打印 3×4 表格，观察执行顺序")
    for row in range(1, NESTED_LIMIT - 1):     # 外层：1, 2, 3
        line = ""
        for col in range(1, 5):                # 内层：1, 2, 3, 4
            line += f"{row * col:>4}"          # 累加器：逐轮拼接
        print(f"   行 {row}: {line}")
    print("   总共执行 3 × 4 = 12 次内层循环")

    print("\n2) 经典 99 乘法表（外层是乘数，内层是被乘数）")
    for i in range(1, 4):
        parts = []
        for j in range(1, i + 1):              # 内层只到 i → 形成三角形
            parts.append(f"{j}×{i}={i * j}")
        print("   " + "  ".join(parts))

    print("\n3) 三角形图案（用累加器而不是嵌套 print）")
    for i in range(1, 6):
        inner = ""
        for _ in range(i):
            inner += "*"                        # 每轮加一个星号
        print(f"   {inner}")

    print("\n4) 累乘与累加的二维版本：计算矩阵元素之和")
    matrix = [[1, 2, 3], [4, 5, 6], [7, 8, 9]]
    total = 0
    for row in matrix:
        for value in row:
            total += value                     # 三层含义：逐行 → 逐个 → 累加
    print(f"   3×3 矩阵元素总和 = {total}")
    # 验证：更好写的等价方式
    flat = [v for row in matrix for v in row]  # 嵌套推导式（L07 详讲）
    print(f"   用嵌套推导式验证 = {sum(flat)}   ✅ 一致")

    print("\n5) 双层循环的复杂度警告")
    # N × N 的双重循环是 O(N²)：N=10000 时是 1 亿次，会明显变慢
    print(f"   N=1000 的双重循环约 {1000 * 1000:,} 次操作")
    print(f"   N=10000 的双重循环约 {10000 * 10000:,} 次操作（慢 100 倍）")
    print("   💡 L07 会讲如何用推导式和内置函数把这类的常数因子降下来")


# ============================================================
# 第 5 部分：完整业务案例
# ============================================================
def fizzbuzz() -> None:
    """经典面试题 FizzBuzz：用循环 + 条件表达业务规则。"""
    print("【案例 1：FizzBuzz（面试高频）】")
    print("规则：3 的倍数打印 Fizz，5 的倍数打印 Buzz，15 的倍数打印 FizzBuzz，其余打印数字\n")
    for i in range(1, 16):
        # ⚠️ 关键：必须先判断「同时满足」的情况，再判断单个
        # 如果顺序反了，15 会被打印成 Fizz，永远走不到 FizzBuzz
        if i % 15 == 0:
            result = "FizzBuzz"
        elif i % 3 == 0:
            result = "Fizz"
        elif i % 5 == 0:
            result = "Buzz"
        else:
            result = str(i)
        print(f"   {i:2} -> {result}")


def find_duplicates() -> list[int]:
    """找出列表中重复出现的数字（双重循环版 + 优化版对比）。"""
    print("\n【案例 2：找重复元素】")
    numbers = [1, 3, 2, 3, 4, 1, 5, 3, 6, 2]

    # 写法 1：双重循环，时间复杂度 O(n²)
    seen: list[int] = []
    duplicates: list[int] = []
    for i in range(len(numbers)):
        for j in range(i + 1, len(numbers)):
            if numbers[i] == numbers[j] and numbers[i] not in duplicates:
                duplicates.append(numbers[i])
    print(f"   双重循环版: {duplicates}")

    # 写法 2：用 set，一次遍历，时间复杂度 O(n)
    seen_set: set[int] = set()
    dup_set: set[int] = set()
    for n in numbers:
        if n in seen_set:
            dup_set.add(n)
        seen_set.add(n)
    print(f"   set 版    : {sorted(dup_set)}   ← 更短更快，L07 会详讲原理")

    return sorted(dup_set)


def bubble_sort_steps(data: list[int]) -> None:
    """冒泡排序：展示嵌套循环最经典的用途。"""
    print("\n【案例 3：冒泡排序（观察每轮的变化）】")
    arr = [5, 2, 8, 1, 9, 3]
    print(f"   初始: {arr}")
    # 复制一份，避免改动原列表
    work = arr.copy()
    for round_no in range(len(work) - 1):      # 最后一位已经就位，少一轮
        swapped = False
        for i in range(len(work) - 1 - round_no):
            if work[i] > work[i + 1]:           # 左边大就交换
                work[i], work[i + 1] = work[i + 1], work[i]   # 元组交换，不用临时变量
                swapped = True
        print(f"   第 {round_no + 1} 轮后: {work}")
        if not swapped:                        # ⚠️ 优化：某一轮没交换 = 已排好，提前退出
            print("   本轮无交换，说明已排序完成，提前退出")
            break
    print(f"   最终: {work}   ✅ 已升序排列")


def number_guessing_game() -> None:
    """循环 + 条件的经典组合：猜数字小游戏。"""
    print("\n【案例 4：猜数字游戏（演示循环的交互逻辑）】")
    # 为了能独立运行，这里用固定序列模拟用户输入
    # 真实场景应该用 input()，L03 已讲
    guess_sequence = [50, 75, 62, 56, 60, 58, 59]
    secret = 60
    print(f"   我心里想了一个 1-100 的数字。你有 {GUESS_LIMIT} 次机会。")

    attempts = 0
    won = False
    for guess in guess_sequence:
        if attempts >= GUESS_LIMIT:            # 次数检查放在最前，防止超次数
            break
        attempts += 1
        if guess == secret:
            print(f"   第 {attempts} 次猜 {guess} → 猜中了！🎉")
            won = True
            break
        elif guess < secret:
            print(f"   第 {attempts} 次猜 {guess} → 太小了")
        else:
            print(f"   第 {attempts} 次猜 {guess} → 太大了")
    else:
        # for-else：所有猜测都用完还没 break，说明没猜中
        print(f"   {GUESS_LIMIT} 次机会用完，答案是 {secret}")

    print(f"   结果: {'赢了' if won else '输了'}，用了 {attempts} 次")


def demo_pitfalls() -> None:
    """循环三大坑的集中演示。"""
    print("\n" + "=" * 64)
    print("【坑 1：死循环】")
    print("  错误代码（⚠️ 千万不要运行，会卡死）：")
    print("    i = 0")
    print("    while i < 10:")
    print("        print(i)        # ← 忘记 i += 1")
    print("\n  正确代码的安全阀版本：")
    i = 0
    safety = 0
    while i < 10 and safety < MAX_STEPS:      # 加安全阀
        i += 1
        safety += 1
    print(f"    结果 i={i}, safety={safety}   ← 即使以后改错逻辑也能退出")
    print("\n  💡 养成习惯：写 while 时先在心里默念「谁改了这个条件变量」")

    print("\n【坑 2：range 边界 off-by-one】")
    data = ["A", "B", "C"]
    print("  range(len(data))      → 遍历全部 3 个 ✅")
    print("  range(1, len(data))   → 漏掉最后一个 ⚠️")
    print("  range(1, len(data)+1) → 越界 IndexError ⚠️（索引 i 又会 -1）")
    # 实测：1-based 计数 + 0-based 索引的完整演示
    print("\n  实测 1-based 计数循环:")
    for i in range(1, len(data) + 1):
        print(f"    第 {i} 个 = {data[i - 1]}")
    print("  💡 结论：Python 里别手写 1-based 循环，用 enumerate(data, start=1) 一步到位")

    print("\n【坑 3：循环内修改正在遍历的容器】")
    # ⚠️ 删除元素时，列表会「左移」，后面的元素被跳过
    nums = [1, 2, 3, 4, 5, 6]
    # 错误示范（这里只打印，不真的删，展示会发生什么）
    removed = []
    for n in nums:
        if n % 2 == 0:
            removed.append(n)                  # 先记录要删的，而不是当场删
    safe = [n for n in nums if n not in removed]
    print(f"   原列表 {nums} → 正确做法（先收集后删除）→ {safe}")

    print("\n  如果一定要循环内 pop，会发生什么：")
    work = [1, 2, 3, 4, 5, 6]
    i = 0
    skipped = []
    while i < len(work):
        if work[i] % 2 == 0:
            removed_item = work.pop(i)         # 删除后后面元素左移，i 不前进
            skipped.append(removed_item)
        else:
            i += 1
        # 注意：删除时故意不让 i 前进，这样才不会跳过元素
    print(f"   循环内 pop 且 i 不前进 → 正确删除 {work}")
    print("   ⚠️ 如果删除后 i += 1，会跳过被左移过来的元素（off-by-one 的另一种形态）")


# ============================================================
# 自我检验
# ============================================================
def verify_loops() -> None:
    """用断言确认循环的核心行为。"""
    # range
    assert list(range(5)) == [0, 1, 2, 3, 4]
    assert list(range(2, 5)) == [2, 3, 4]
    assert list(range(0, 10, 3)) == [0, 3, 6, 9]
    assert list(range(5, 0, -1)) == [5, 4, 3, 2, 1]
    assert len(range(100)) == 100
    # 累加
    total = 0
    for i in range(1, 5):
        total += i
    assert total == 10
    # break / continue
    seen = []
    for i in range(10):
        if i == 5:
            break
        seen.append(i)
    assert seen == [0, 1, 2, 3, 4]
    # for-else：没 break 就执行 else
    hit = False
    for i in range(3):
        if i == 99:
            hit = True
            break
    else:
        hit = True                          # 正常走完，else 执行
    assert hit is True
    # 元组交换
    a, b = 1, 2
    a, b = b, a
    assert (a, b) == (2, 1)
    # 三元轮换
    p, q, r = 1, 2, 3
    p, q, r = r, p, q
    assert (p, q, r) == (3, 1, 2)
    print("✅ verify_loops 全部断言通过")


# ============================================================
# 程序入口
# ============================================================
def main() -> None:
    """按教学顺序调用全部演示函数。"""
    print("=" * 64)
    print("L06 · 循环基础")
    print("=" * 64)
    demo_range_basics()
    print("\n" + "-" * 64)
    demo_for_over_iterable()
    print("\n" + "-" * 64)
    demo_range_pitfalls()
    print("\n" + "-" * 64)
    demo_while_loop()
    print("\n" + "-" * 64)
    demo_while_else_and_patterns()
    print("\n" + "-" * 64)
    demo_break_continue_else()
    print("\n" + "-" * 64)
    demo_for_else_advanced()
    print("\n" + "-" * 64)
    demo_nested_loops()
    print("\n" + "-" * 64)
    fizzbuzz()
    print("\n" + "-" * 64)
    find_duplicates()
    print("\n" + "-" * 64)
    bubble_sort_steps([5, 2, 8, 1, 9, 3])
    print("\n" + "-" * 64)
    number_guessing_game()
    print("\n" + "-" * 64)
    demo_pitfalls()
    print("\n" + "-" * 64)
    verify_loops()
    print("\n🎉 L06 演示结束")


# 标准入口约定：直接运行本文件执行 main()，被 import 时不执行
if __name__ == "__main__":
    main()
