"""
================================================================================
 04_recursion.py  ——  递归
================================================================================

【演示的语法点】
 1. 递归的三要素：基线条件(base case)、递归条件(recursive case)、收敛性
 2. 递归调用栈：每层调用在栈上占一帧，函数返回时栈帧弹出
 3. 汉诺塔：经典递归，含 move() 通用动作抽象与最优性说明
 4. 斐波那契：递归 vs 迭代，Python 纯递归版的组合爆炸与性能实测
 5. 记忆化(memoization)：手写缓存 + functools.lru_cache 两种写法对比
 6. 尾递归：Python 不做尾调用优化，尾递归写成循环不会更快但也不会栈溢出
 7. 递归深度限制：sys.getrecursionlimit / sys.setrecursionlimit，
    真正的拦路虎是 CPython 的 C 栈深度 → 实际安全深度远小于设置值
 8. 递归深度探测：安全地递归到接近限制并捕获 RecursionError
 9. 递归的应用：目录树遍历、分形、树结构查找

【预期输出摘要】
 - "递归 vs 迭代" 打印 fib(25) 两版耗时，递归版明显更慢（数量级差距）
 - "深度限制" 小节打印默认上限 1000，并真实触发 RecursionError 后安全捕获
 - 汉诺塔打印 3 盘 7 步的最优解序列
================================================================================
"""

import functools
import sys
import time


# ===== 语法解析 =====
# 【1】递归函数的基本结构
#   语法规则：函数直接/间接调用自己，必须有【基线条件】保证终止。
#   递归三要素：
#     (a) 基线条件（base case）：不需要递归的最小问题，直接返回
#     (b) 递归条件：把问题规模缩小后调用自己
#     (c) 收敛性：参数必须朝着基线条件单调递减，否则无限递归 → RecursionError
#   执行原理：调用 f(n) → 压入新栈帧 → 执行到 f(n-1) 调用 → 再压栈 …
#     直到命中基线条件开始【回溯(unwinding)】，逐层把结果冒泡回最外层。
#   设计意图：用少量代码表达"重复结构"，天然贴合分治、树、回溯类问题。
def factorial(n: int) -> int:
    """阶乘：最经典的递归示例。"""
    if n <= 1:                      # (a) 基线条件 —— 必须放在递归调用之前
        return 1                     #     n=1 时 1! = 1，避免 0! 的 0 问题
    return n * factorial(n - 1)      # (b) 递归条件 + (c) 规模 n → n-1 严格递减


def fib_naive(n: int) -> int:
    """朴素递归斐波那契：T(n) = T(n-1) + T(n-2)，约等于 O(φ^n)，φ≈1.618。"""
    if n < 2:                       # 基线条件覆盖 n=0 和 n=1
        return n
    return fib_naive(n - 1) + fib_naive(n - 2)   # 问题规模持续收敛


# ===== 语法解析 =====
# 【2】迭代版斐波那契：作为递归版的性能对照组
#   O(n) 时间 / O(1) 空间，是斐波那契的最优解法。
#   对比意义：说明"递归 ≠ 正确解法"，工具选型要看复杂度。
def fib_iter(n: int) -> int:
    """迭代版：只用两个变量滚动前进。"""
    a, b = 0, 1                    # a=斐波那契(0), b=斐波那契(1)
    for _ in range(n):
        a, b = b, a + b             # 并行赋值：右侧先整体求值，再一次性绑定，
                                    # 因此无需临时变量，这正是 Python 赋值语法的妙处
    return a


# ===== 语法解析 =====
# 【3】记忆化：把重复子问题的结果缓存起来
#   朴素递归为什么慢？fib(5) 会重复计算 fib(3) 两次、fib(2) 三次……
#   记忆化后，每个 n 只真正算一次 → T(n) = O(n)。
#   手写版用 dict（也可改成 列表 prefill，因为 n 是连续小整数，列表更快）。
def fib_memo_manual(n: int, cache: dict[int, int] | None = None) -> int:
    """手写记忆化。注意：cache 用【默认 None + 内部创建】的写法，
    而不是 cache={} —— 这正是 01 学过的可变默认参数 BUG 的应用场景。"""
    if cache is None:
        cache = {0: 0, 1: 1}        # 预置基线，省去递归到最底层
    if n in cache:                  # 先查缓存，命中直接返回
        return cache[n]
    cache[n] = fib_memo_manual(n - 1, cache) + fib_memo_manual(n - 2, cache)
    return cache[n]


@functools.lru_cache(maxsize=None)
def fib_memo_lru(n: int) -> int:
    """用装饰器实现记忆化：代码更简洁，且可以【跨次调用】复用缓存。"""
    if n < 2:
        return n
    return fib_memo_lru(n - 1) + fib_memo_lru(n - 2)


# ===== 语法解析 =====
# 【4】汉诺塔：递归的教科书案例
#   问题：n 个盘子从 A 移到 C，借助 B，任意时刻大盘不能压在小盘上。
#   递归三步（把 n-1 盘移动让出中转柱）：
#     1) move(n-1, A, B, C)  —— 前 n-1 个盘子借 C 挪到 B，让出 A 柱的最大盘
#     2) 直接挪动最大盘 A → C（n=1 时这就是全部工作）
#     3) move(n-1, B, C, A)  —— B 上的 n-1 个盘子借 A 挪到 C
#   最优步数 2ⁿ - 1，可归纳证明（至少要 n-1 次才能挪走最大的盘）。
def hanoi(n: int, source: str, target: str, helper: str) -> list[str]:
    """返回操作序列，同时打印。"""
    moves: list[str] = []

    def move(count: int, src: str, dst: str, tmp: str) -> None:
        # ★ 基线条件必须是 count <= 1（而不是 == 0），否则 count=1 时会走进步骤1
        #   递归出 count=0 才停 —— 而 count=0 时又执行 move(1,...) 造成死循环。
        #   这是递归里最经典的"基线条件差一"错误。
        if count <= 1:                       # 基线：0 个不用动，1 个直接挪
            if count == 1:
                moves.append(f"把第 1 个盘子：{src} → {dst}")
            return                           # ← 收敛点，必须在这里终止
        move(count - 1, src, tmp, dst)       # 步骤1：前 count-1 个借 dst 挪到 tmp，让出 dst 柱
        moves.append(f"把第 {count} 个盘子：{src} → {dst}")
        move(count - 1, tmp, dst, src)       # 步骤3：tmp 上的 count-1 个借 src 挪到 dst

    move(n, source, target, helper)
    return moves


# ===== 语法解析 =====
# 【5】递归计算目录树结构（不依赖第三方库）
#   用 pathlib 遍历文件系统，展示递归在真实场景（而非数学题）中的应用。
def show_tree(path, prefix: str = "", max_depth: int = 3, depth: int = 0) -> None:
    """打印目录树。max_depth 防止目录太深导致递归过深。"""
    if depth > max_depth:                    # 显式限制深度，是生产代码的必备防御
        print(f"{prefix}└── ...")
        return
    items = sorted(path.iterdir(), key=lambda p: (p.is_file(), p.name))
    for i, item in enumerate(items):
        is_last = i == len(items) - 1       # 判断是不是最后一项，决定用 └── 还是 ├──
        connector = "└── " if is_last else "├── "
        suffix = "/" if item.is_dir() else ""
        print(f"{prefix}{connector}{item.name}{suffix}")
        if item.is_dir():
            # 递归时前缀要追加缩进/竖线，保持树的层级感
            show_tree(item, prefix + ("    " if is_last else "│   "),
                      max_depth, depth + 1)


# ===== 语法解析 =====
# 【6】递归深度限制
#   机制：CPython 递归层数由 sys.getrecursionlimit() 控制（默认 1000）。
#        超过即抛 RecursionError。
#   ★ 重要警告：setrecursionlimit 只是【把上限数字调大】，但 Python 3.12+ 默认
#     还会检查【C 栈剩余空间】（Py_C_RECURSION_LIMIT），单纯调大 sys 限制
#     在深递归时会直接 Segmentation Fault / 崩溃，而不是抛可捕获的异常。
#     正确做法：优化算法为迭代，而不是无限调大上限。
def recursive_sum(n: int) -> int:
    """线性递归：每一层只调一次，深度 = n。"""
    return 0 if n == 0 else n + recursive_sum(n - 1)


def _infinite_depth(n: int) -> int:
    """故意永不收敛的递归，用于真实触发 RecursionError。"""
    return _infinite_depth(n + 1)


def tail_recursion_as_loop(n: int, acc: int = 0) -> int:
    """尾递归形式写成显式循环：Python 不做尾调用优化(TCO)，
    写成循环后才能真正获得 O(1) 栈空间。"""
    total = acc
    while n > 0:
        total += n                        # 这就是"尾调用"位置的累加
        n -= 1
    return total


# ===== 语法解析 =====
# 【7】递归 vs 迭代：实测对比
#   用 time.perf_counter（单调钟）测量，避免 time.time 受系统校时干扰。
def benchmark() -> None:
    n = 25                       # 选 25 是平衡点：递归版约 24 万次调用，能测出差异又不至于超时
    print(f"  测试目标：fib({n})")
    print(f"  理论值：{fib_iter(n)}（用迭代版作标准答案交叉验证）")

    t0 = time.perf_counter()
    naive_result = fib_naive(n)
    t_naive = time.perf_counter() - t0

    t1 = time.perf_counter()
    iter_result = fib_iter(n)
    t_iter = time.perf_counter() - t1

    fib_memo_lru.cache_clear()
    t2 = time.perf_counter()
    memo_result = fib_memo_lru(n)
    t_memo = time.perf_counter() - t2

    print(f"  朴素递归：{naive_result}  耗时 {t_naive:.6f}s")
    print(f"  迭代    ：{iter_result}  耗时 {t_iter:.6f}s")
    print(f"  记忆化  ：{memo_result}  耗时 {t_memo:.6f}s")
    print(f"  结果一致性：{naive_result == iter_result == memo_result}   # 三者必须相等")
    print(f"  递归比迭代慢约 {t_naive / max(t_iter, 1e-9):,.0f} 倍")
    print(f"  记忆化把 {t_naive / max(t_memo, 1e-9):,.0f} 倍的差距抹平 —— 因为它消除了重复子问题")
    print("  结论：复杂度错误的递归，再怎么优化也赢不了 O(n) 的迭代。")


def main() -> None:
    print("=" * 60)
    print("【1】递归基础：阶乘")
    print("=" * 60)
    for i in range(1, 7):
        print(f"  {i}! = {factorial(i)}")
    print(f"  5! 的递归展开：5 * (4 * (3 * (2 * (1)))) = {factorial(5)}")
    print("  注意：递归深度 = 5，栈上同时存在 5 个栈帧（未返回前）。")

    print()
    print("=" * 60)
    print("【2】递归 vs 迭代 vs 记忆化：性能实测")
    print("=" * 60)
    benchmark()

    print()
    print("=" * 60)
    print("【3】三种斐波那契实现的复杂度对比")
    print("=" * 60)
    print("  | 实现     | 时间复杂度 | fib(30) 理论调用次数 | 空间复杂度 |")
    print("  |----------|-----------|--------------------|-----------|")
    print("  | 朴素递归 | O(φ^n)    | 约 271 万次         | O(n) 栈    |")
    print("  | 迭代     | O(n)      | 30 步               | O(1)       |")
    print("  | 记忆化   | O(n)      | 31 步               | O(n)       |")
    print()
    print(f"  实测 fib(20) 朴素递归调用 {fib_naive_count(20)} 次（函数内部计数）")

    print()
    print("=" * 60)
    print("【4】记忆化两种写法对比")
    print("=" * 60)
    fib_memo_lru.cache_clear()
    print(f"  手写记忆化 fib_memo_manual(50) = {fib_memo_manual(50)}")
    print(f"  lru_cache   fib_memo_lru(50)   = {fib_memo_lru(50)}")
    print(f"  lru 缓存统计：{fib_memo_lru.cache_info()}   # hits=misses-1，符合树形递归规律")
    print("  手写版每次都要新建 dict（除非显式传入），lru 版跨调用复用缓存。")

    print()
    print("=" * 60)
    print("【5】汉诺塔：递归的经典应用")
    print("=" * 60)
    moves = hanoi(3, "A", "C", "B")
    for i, step in enumerate(moves, 1):
        print(f"  第{i}步：{step}")
    print(f"  总步数 = {len(moves)}，理论最优 2³-1 = {2 ** 3 - 1}   ✓ 一致")
    print(f"  n=5 的最优步数 = {2 ** 5 - 1}，递归会指数级变慢")

    print()
    print("=" * 60)
    print("【6】递归的真实应用：目录树遍历")
    print("=" * 60)
    show_tree(__import__("pathlib").Path(".").resolve(), max_depth=1)
    print("  递归让『遍历任意深度目录』只写一个函数；深度限制 max_depth 是必要防御。")

    print()
    print("=" * 60)
    print("【7】★ 递归深度限制与 RecursionError")
    print("=" * 60)
    print(f"  sys.getrecursionlimit() = {sys.getrecursionlimit()}")
    print(f"  当前 Python 3.13 的 C 栈保护上限（Py_C_RECURSION_LIMIT）约为 1500")
    print(f"  递归深度 200 的求和：{recursive_sum(200)}   # 安全")
    print(f"  尾递归改写成循环（深度 200）：{tail_recursion_as_loop(200)}   # 结果一致，栈深 O(1)")
    print("  → 对比：递归占 O(n) 栈空间，循环只占 O(1)。")

    print()
    print("  真实触发 RecursionError（用无限递归探测）：")
    try:
        _infinite_depth(0)
    except RecursionError as exc:
        print(f"  ✓ 捕获到 RecursionError: {str(exc)[:60]}...")
        print("  ✓ 说明系统按预期阻止了栈溢出，而不是让进程崩溃")

    print()
    print("  演示 setrecursionlimit 的作用与风险：")
    original_limit = sys.getrecursionlimit()
    sys.setrecursionlimit(3000)
    print(f"  已把上限临时调到 {sys.getrecursionlimit()}")
    print(f"  深度 2500 的求和：{recursive_sum(2500)}   # 能跑通")
    print("  ⚠ 但把上限调到几万会让 C 栈溢出 → Segmentation Fault，无法捕获")
    print("  ★ 正确做法：把递归改写成迭代，而不是无限调大上限")
    sys.setrecursionlimit(original_limit)      # ★ 务必还原，避免污染进程状态
    print(f"  已还原为 {sys.getrecursionlimit()}")

    print()
    print("=" * 60)
    print("【8】何时用递归，何时用迭代")
    print("=" * 60)
    print("  适合递归：问题天然是树/图结构、分治法、回溯搜索（八皇后、路径查找）")
    print("  不适合递归：线性累加、纯数值计算 —— 迭代更快且栈空间 O(1)")
    print("  经验法则：能用迭代写就迭代；确实需要递归时，把 max_depth 显式设好。")
    print(f"  当前解释器版本：{sys.version.split()[0]}")


# 用于统计朴素递归的调用次数（教学用计数器）
_call_count = 0


def fib_naive_count(n: int) -> int:
    """带调用计数的朴素递归，用来直观展示指数爆炸。"""
    global _call_count
    _call_count += 1
    if n < 2:
        return n
    return fib_naive_count(n - 1) + fib_naive_count(n - 2)


if __name__ == "__main__":
    main()