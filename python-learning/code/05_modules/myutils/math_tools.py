"""
================================================================================
 myutils/math_tools.py  ——  数学工具模块
================================================================================

【模块职责】
 提供一组数学函数，演示：
 - 数值校验装饰器在本模块内的复用（自定义装饰器）
 - 统计函数（平均、中位数、众数）
 - 几何函数
 - 整除与质数判断
 - 列表推导式、sorted(key=) 的应用

【依赖】
 本模块【不导入 myutils 内的其他模块】，与 config.py 一样是叶子模块。
 这样 myutils 包内不会出现"互相 import"的结构，从根本上规避循环导入。
"""

from __future__ import annotations

import functools
import math
from collections.abc import Callable, Sequence
from typing import TypeVar

# 模块内自定义装饰器：检查参数是否在指定区间内
# 这是 04 目录学到的装饰器在真实模块中的应用。
def in_range(lo: float, hi: float) -> Callable:
    """装饰器工厂：校验所有位置参数落在 [lo, hi] 区间。"""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            for v in args:
                if not (lo <= v <= hi):
                    raise ValueError(f"{func.__name__} 参数 {v} 超出范围 [{lo}, {hi}]")
            return func(*args, **kwargs)
        return wrapper
    return decorator


# ===== 语法解析 =====
# 【1】基础统计
def mean(numbers: Sequence[float]) -> float:
    """算术平均数。空序列会抛 ZeroDivisionError，这里显式给出更清晰的错误。"""
    if not numbers:
        raise ValueError("均值需要至少一个数")
    return sum(numbers) / len(numbers)


def median(numbers: Sequence[float]) -> float:
    """中位数：先排序，奇数取中间，偶数取中间两个的平均。"""
    if not numbers:
        raise ValueError("中位数需要至少一个数")
    ordered = sorted(numbers)             # sorted 返回新列表，不改原序列
    n = len(ordered)
    mid = n // 2
    # 三元表达式 + 整除：奇数时 mid*2+1 == n，偶数时 == n-1
    return float(ordered[mid]) if n % 2 else (ordered[mid - 1] + ordered[mid]) / 2


def mode(numbers: Sequence[float]) -> float | None:
    """众数：出现次数最多的值。有多个并列时返回最先出现的那个；无重复返回 None。"""
    if not numbers:
        return None
    counts: dict[float, int] = {}
    for n in numbers:
        counts[n] = counts.get(n, 0) + 1
    # 用 max 配合 key 找出计数最大值对应的键
    highest = max(counts.values())
    if highest == 1:                     # 全不重复 → 无众数
        return None
    for n in numbers:                    # 遍历原序列，保证返回"最先出现"的众数
        if counts[n] == highest:
            return n
    return None


# ===== 语法解析 =====
# 【2】方差 / 标准差
def variance(numbers: Sequence[float], sample: bool = False) -> float:
    """方差。sample=True 表示样本方差（除以 n-1）。"""
    if len(numbers) < (2 if sample else 1):
        raise ValueError("样本方差至少需要 2 个数，总体方差至少 1 个")
    m = mean(numbers)
    # 求和推导式：sum((x - m) ** 2 for x in numbers) —— 生成器表达式免建中间列表
    ss = sum((x - m) ** 2 for x in numbers)
    return ss / (len(numbers) - 1 if sample else len(numbers))


def stdev(numbers: Sequence[float], sample: bool = False) -> float:
    """标准差 = 方差的算术平方根。"""
    return math.sqrt(variance(numbers, sample))


# ===== 语法解析 =====
# 【3】质数与整除
def is_prime(n: int) -> bool:
    """判断质数。只试除到 √n，复杂度 O(√n)。"""
    if n < 2:
        return False
    if n < 4:
        return True                     # 2 和 3 是质数
    if n % 2 == 0:
        return False                    # 排除偶数
    # range(3, int(n**0.5)+1, 2) 只试奇数因子，步长 2 减半
    limit = int(math.isqrt(n))          # math.isqrt 精确整数平方根，避免浮点误差
    for d in range(3, limit + 1, 2):
        if n % d == 0:
            return False
    return True


def gcd(a: int, b: int) -> int:
    """最大公约数：欧几里得算法（辗转相除）。"""
    a, b = abs(a), abs(b)
    while b:                            # 当 b 不为 0 时持续迭代
        a, b = b, a % b                 # 并行赋值：右值先算，再同时绑定
    return a                            # 循环结束时 a 即最大公约数


def lcm(a: int, b: int) -> int:
    """最小公倍数：a*b // gcd(a,b)。先除后乘可避免中间结果过大。"""
    if a == 0 or b == 0:
        return 0
    return abs(a * b) // gcd(a, b)


# ===== 语法解析 =====
# 【4】几何函数（演示装饰器的实际应用）
@in_range(0, 1000)
def circle_area(radius: float) -> float:
    """圆面积。装饰器保证 radius 落在 [0, 1000]。"""
    return math.pi * radius ** 2


@in_range(0, 1000)
def rectangle_area(width: float, height: float) -> float:
    """矩形面积。装饰器会校验所有位置参数。"""
    return width * height


def distance(x1: float, y1: float, x2: float, y2: float) -> float:
    """两点欧氏距离。"""
    return math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)


# ===== 语法解析 =====
# 【5】批量统计工具
def top_n(numbers: Sequence[float], n: int = 3) -> list[float]:
    """返回最大的 n 个数（降序）。n 超过总数时全部返回。"""
    return sorted(numbers, reverse=True)[:n]


def clamp(value: float, lo: float, hi: float) -> float:
    """把 value 限制在 [lo, hi] 区间内。"""
    # 先比上界再比下界，保证 hi < lo 时行为可预测（返回 hi）
    return min(max(value, lo), hi)


def normalize_to_unit(values: Sequence[float]) -> list[float]:
    """归一化：把向量缩放到 [0, 1] 区间（min-max 归一化）。"""
    if not values:
        return []
    lo, hi = min(values), max(values)
    span = hi - lo
    if span == 0:                       # 全相等时避免除零
        return [0.0 for _ in values]
    return [(v - lo) / span for v in values]


if __name__ == "__main__":
    print("直接运行 math_tools.py：")
    data = [1, 2, 2, 3, 4, 5, 5, 5, 8]
    print(f"  mean([1..8]) = {mean(data):.4f}")
    print(f"  median = {median(data)}")
    print(f"  mode = {mode(data)}   # 5 出现 3 次，最多")
    print(f"  总体方差 = {variance(data):.4f}")
    print(f"  样本方差 = {variance(data, sample=True):.4f}")
    print(f"  标准差 = {stdev(data):.4f}")
    print(f"  is_prime(97) = {is_prime(97)}, is_prime(100) = {is_prime(100)}")
    print(f"  gcd(1071, 462) = {gcd(1071, 462)}, lcm(4, 6) = {lcm(4, 6)}")
    print(f"  circle_area(2) = {circle_area(2):.4f}")
    try:
        circle_area(9999)                # 超出装饰器允许的范围
    except ValueError as exc:
        print(f"  装饰器拦截：ValueError: {exc}")
    print(f"  top_n([3,1,4,1,5,9,2,6], 3) = {top_n([3, 1, 4, 1, 5, 9, 2, 6], 3)}")
    print(f"  clamp(150, 0, 100) = {clamp(150, 0, 100)}")
    print(f"  normalize([1,2,3,4]) = {normalize_to_unit([1, 2, 3, 4])}")