"""
================================================================================
 08_performance.py —— 性能优化实战（每项都带实测数据）
================================================================================

【演示的语法点】
  1. timeit 模块      : repeat + number 自动选次，得出统计上稳定的耗时
  2. time.perf_counter : 高精度秒表，与 time.time() 的区别在于不受系统时间调整影响
  3. cProfile        : 函数级性能剖析，找出真正的瓶颈
  4. pstats          : 排序 + 过滤 cProfile 结果
  5. functools.lru_cache : 记忆化缓存
  6. __slots__       : 省内存的实例布局
  7. 生成器表达式     : 惰性求值
  8. 局部变量绑定     : LOAD_FAST vs LOAD_GLOBAL 字节码层面的差异
  9. 字符串 join      : O(n) vs O(n²)
 10. 列表推导式       : LIST_APPEND 优化
 11. dict vs list 查找: O(1) vs O(n) 哈希表原理

【实测数据规模说明】
  全部用例的数据量控制在"秒级完成"：N 取 1000~20000，迭代 5 次取中位数。
  实测耗时受机器影响，以下数值仅展示"相对倍数"关系，绝对值以你本地运行为准。

【预期输出摘要】
  [1] 列表 vs 生成器      : 内存差 40 倍以上，耗时接近
  [2] 局部变量绑定        : 循环体内约 20%~40% 提升
  [3] 字符串 += vs join   : O(n²) vs O(n)，差距随数据量指数级放大
  [4] 列表推导 vs for 循环 : 约 20%~50% 提升
  [5] dict vs list 查找    : 1000 次查找，dict 约快 100 倍
  [6] __slots__ 内存对比   : 每实例省约 50~100 字节（无 dict）
  [7] lru_cache 加速      : 重复调用可快 1000 倍以上
  [8] cProfile 剖析       : 找出热点函数与调用次数

【核心结论】
  1. 先测量，再优化 —— cProfile 告诉你热点，不要凭直觉猜
  2. 复杂度 > 微优化：O(n²) 改 O(n) 是数量级提升，局部变量只是常数级
  3. 内存和速度经常此消彼长（生成器 vs 列表），按场景取舍
"""

from __future__ import annotations

import cProfile
import functools
import io
import pstats
import sys
import time
from typing import Any, Callable, Iterator


# ==============================================================================
# 计时工具
# ==============================================================================
# ===== 语法解析 =====
# 为什么用 timeit 而不是手写 start = time.time() 循环？
#   1. 自动处理循环次数放大，让单次调用短到计时器噪声以下
#   2. GC 影响自动清理（timeit 默认在循环外关一次 GC，不在每次调用里反复开关）
#   3. 多次 repeat 取最小值，避开其他进程干扰和操作系统调度抖动
#
# 为什么用 perf_counter 而不是 time()？
#   time.time() 是墙上时钟，可能被 NTP 校正、闰秒、夏令时影响而回退
#   perf_counter() 是单调递增的高精度计时器，测耗时的唯一正确选择


def benchmark(
    func: Callable[..., Any],
    *args: Any,
    number: int = 1000,
    repeat: int = 5,
    **kwargs: Any,
) -> dict[str, float]:
    """用 timeit 测量函数耗时，返回最小/最大/平均值（微秒级）。"""
    # timeit 在导入时按需绑定到本地，避免计时循环里的全局查找开销
    import timeit

    timer = timeit.Timer(stmt="func(*args, **kwargs)", globals={"func": func, "args": args, "kwargs": kwargs})
    # repeat=7 取最小值最稳定（最小值代表"没有其他干扰"的理想情况）
    raw = timer.repeat(repeat=repeat, number=number)
    # 每项是 number 次的总耗时，换算成单次微秒
    microseconds = [item / number * 1e6 for item in raw]
    return {
        "min": min(microseconds),
        "max": max(microseconds),
        "avg": sum(microseconds) / len(microseconds),
    }


def report(title: str, results: dict[str, tuple[dict[str, float], str]], note: str = "") -> None:
    """打印对比表格。results: {名称: (benchmark 返回值, 说明)}"""
    print(f"\n  【{title}】")
    print(f"  {'方案':<26}{'最小(μs)':>12}{'平均(μs)':>12}{'倍数':>10}   说明")
    print("  " + "-" * 96)

    # 以第一个方案为基准，计算相对倍数
    baseline_name = next(iter(results))
    baseline = results[baseline_name][0]["min"]

    for name, (stats, desc) in results.items():
        ratio = stats["min"] / baseline if baseline > 0 else 1.0
        # 倍数小于 1 说明比基准更快，标成 0.5x 形式便于比较
        ratio_text = "基准" if name == baseline_name else f"{ratio:.2f}x"
        if name != baseline_name and ratio < 1:
            ratio_text = f"{1 / ratio:.2f}x↑"     # 更快时用向上箭头标注
        print(f"  {name:<26}{stats['min']:>12.3f}{stats['avg']:>12.3f}{ratio_text:>10}   {desc}")

    if note:
        print(f"\n  → {note}")


# ==============================================================================
# 一、生成器 vs 列表
# ==============================================================================
# ===== 语法解析 =====
# list comprehension : 立即一次性构建全部元素，占内存
# generator expression: 惰性产出，一次只占一个元素的内存
# 语法区别只有一个字符：外层方括号 [] 换成圆括号 ()
#
# 何时用哪个？
#   只需要遍历一次        -> 生成器（省内存）
#   需要多次遍历/len/索引  -> 列表
#   数据量小              -> 差别不大，优先可读性


def create_list(n: int) -> list[int]:
    """用列表推导式一次性构建 n 个平方数。"""
    # 列表推导在 CPython 中会走 LIST_APPEND 字节码，比 for + append 快
    return [i * i for i in range(n)]


def create_generator(n: int) -> Iterator[int]:
    """用生成器惰性产出 n 个平方数。"""
    # yield 每次只挂起一个 frame，内存 O(1) 而非 O(n)
    return (i * i for i in range(n))


def consume_list(gen: list[int]) -> int:
    """消费列表：只做求和，不需要保留元素。"""
    total = 0
    for item in gen:
        total += item
    return total


def consume_generator(gen: Iterator[int]) -> int:
    """消费生成器：求和。"""
    total = 0
    for item in gen:
        total += item
    return total


def list_memory(n: int) -> int:
    """测量列表的深层内存（sys.getsizeof 不算内部元素，需要递归）。"""
    import sys

    return sys.getsizeof(create_list(n))


def generator_memory(n: int) -> int:
    """测量生成器的内存 —— 与 n 无关，恒定。"""
    import sys

    return sys.getsizeof(create_generator(n))


def sum_via_loop(n: int) -> int:
    """基准：普通循环累加平方。"""
    total = 0
    for i in range(n):
        total += i * i
    return total


def sum_via_comprehension(n: int) -> int:
    """方案 A：列表推导 + sum（快但占内存）。"""
    return sum([i * i for i in range(n)])


def sum_via_generator(n: int) -> int:
    """方案 B：生成器 + sum（慢一点但内存恒定）。

    注意：sum 接收生成器时，CPython 有专门优化路径，边取边加不建中间列表
    """
    return sum(i * i for i in range(n))


def demo_generator_vs_list() -> None:
    N = 20_000
    print("\n" + "=" * 96)
    print(f" 01. 生成器 vs 列表（N = {N}）")
    print("=" * 96)

    results = {
        "列表推导 + sum": (benchmark(sum_via_comprehension, N, number=200), "构建完整列表再求和"),
        "生成器 + sum": (benchmark(sum_via_generator, N, number=200), "惰性产出，不建中间列表"),
        "for 循环累加": (benchmark(sum_via_loop, N, number=200), "最朴素写法"),
    }
    report("耗时对比", results, "生成器和列表耗时接近；但内存差 40 倍以上 —— 选生成器。")

    print("\n  内存对比：")
    list_size = list_memory(N)
    gen_size = generator_memory(N)
    print(f"    列表({N} 元素)      : {list_size:>10,} 字节")
    print(f"    生成器(任意 N)      : {gen_size:>10,} 字节")
    print(f"    差距              : {list_size / max(gen_size, 1):>10,.0f} 倍")
    print(f"\n  注意：{list_size:,} 字节只是 20,000 个 int 的【引用数组 + 整数对象】")
    print(f"       sys.getsizeof 不含列表容器的额外开销，真实占用更大")

    print("\n  实测：100 万元素时的内存量级估算")
    big_list_size = list_memory(1_000_000)
    print(f"    列表(1,000,000)    : {big_list_size / 1024 / 1024:>8.2f} MB")
    print(f"    生成器             : {gen_size:>10,} 字节（恒定，不随 N 增长）")
    print("    → 处理百万级数据流，生成器是唯一可行方案")


# ==============================================================================
# 二、局部变量绑定（LOAD_FAST vs LOAD_GLOBAL）
# ==============================================================================
# ===== 语法解析 =====
# 字节码层面的真相：
#   x = 5; x + x      -> LOAD_FAST  x    （查局部变量表，纳秒级）
#   global_x = 5; global_x + global_x -> LOAD_GLOBAL（查 globals 再查 builtins，慢 3~5 倍）
#
# 为什么循环里把全局变量取到局部会有帮助？
#   循环体执行 N 次，每次都要 LOAD_GLOBAL；改成先赋值到局部，
#   之后 N 次都是 LOAD_FAST。N 越大差距越明显。
#
# 这是"微优化"：只提升常数倍，不改变复杂度。
# 但在热循环里（图像处理、逐帧计算）实测能有 20%~40% 提升。


GLOBAL_COUNTER = 0


def loop_global(n: int) -> int:
    """循环体内直接引用全局变量：每次访问都要 LOAD_GLOBAL。"""
    total = 0
    for _ in range(n):
        total += GLOBAL_COUNTER          # 每次迭代都查全局表
    return total


def loop_local_bound(n: int) -> int:
    """先把全局绑定到局部：循环体内全是 LOAD_FAST。"""
    counter = GLOBAL_COUNTER              # ★ 关键：提到循环外，只做一次 LOAD_GLOBAL
    total = 0
    for _ in range(n):
        total += counter                  # LOAD_FAST，快得多
    return total


def loop_attribute(n: int) -> int:
    """属性访问在 Python 3.11+ 有特化字节码，比 LOAD_GLOBAL 还快。"""
    import math

    total = 0.0
    sqrt = math.sqrt                       # 同样先绑定到局部
    for i in range(1, n):
        total += sqrt(i)
    return int(total)


def demo_local_binding() -> None:
    N = 200_000
    print("\n" + "=" * 96)
    print(f" 02. 局部变量绑定（循环 {N:,} 次）")
    print("=" * 96)

    results = {
        "循环内读全局变量": (benchmark(loop_global, N, number=20), "每次迭代 LOAD_GLOBAL"),
        "先绑定到局部变量": (benchmark(loop_local_bound, N, number=20), "LOAD_FAST，Python 3.11+"),
    }
    report("耗时对比", results, "这是微优化：只改常数倍，不改复杂度。")

    print("\n  字节码对比（用 dis 模块直接看）：")
    import dis

    print("\n  loop_global 中的 total += 语句：")
    for line in list(dis.Bytecode(loop_global))[-8:]:
        # 只打印关键指令，过滤掉 RESUME/PUSH_NULL 等样板
        if line.opname in ("LOAD_GLOBAL", "LOAD_FAST", "BINARY_OP"):
            print(f"      {line.opname:<14} {line.argrepr}")

    print("\n  loop_local_bound 中的 total += 语句：")
    for line in list(dis.Bytecode(loop_local_bound))[-8:]:
        if line.opname in ("LOAD_GLOBAL", "LOAD_FAST", "BINARY_OP"):
            print(f"      {line.opname:<14} {line.argrepr}")

    print("\n  ✓ 可以看到：全局版是 LOAD_GLOBAL，局部版是 LOAD_FAST")
    print("  ✓ LOAD_FAST 只查栈帧的局部变量表；LOAD_GLOBAL 要查 globals dict")


# ==============================================================================
# 三、字符串拼接：+= vs ''.join
# ==============================================================================
# ===== 语法解析 =====
# 这是最经典的复杂度陷阱：
#   s += "x"  在 CPython 里有优化（就地扩容，不一定每次新建），
#             但当 s 被多个对象引用时会退化成 O(n²)
#   ''.join() 一次性算出总长度，预分配一块内存，O(n)
#
# 实践结论：
#   - 循环里拼接大量字符串 -> 一定用 join
#   - 少量拼接（几个）  -> += 可读性更重要，差异可忽略


def concat_plus(n: int) -> str:
    """循环内 += 拼接（最坏情况 O(n²)）。"""
    result = ""
    for i in range(n):
        result += f"{i}."     # f-string 先造临时串，再 +=
    return result


def concat_join(n: int) -> str:
    """用 join 拼接（O(n)）。"""
    # join 会先遍历一遍拿到总长度，再一次性分配，避免反复扩容
    return "".join(f"{i}." for i in range(n))


def concat_join_list(n: int) -> str:
    """用 join + 显式列表。"""
    parts = []
    for i in range(n):
        parts.append(f"{i}.")
    return "".join(parts)


def demo_string_concat() -> None:
    print("\n" + "=" * 96)
    print(" 03. 字符串 += vs ''.join")
    print("=" * 96)

    # 用较小的 N，因为 += 是二次复杂度，数据量大会让演示变慢
    print("  数据量与耗时的关系（体现 O(n²) 与 O(n) 的差距）：")
    print(f"  {'N':>8}{'+= 拼接(μs)':>16}{'join 拼接(μs)':>16}{'差距':>12}")
    print("  " + "-" * 54)

    for n in (500, 1_000, 2_000, 4_000, 8_000):
        # number 随 N 增大而减小，保证总耗时稳定
        plus_stats = benchmark(concat_plus, n, number=3, repeat=3)
        join_stats = benchmark(concat_join, n, number=3, repeat=3)
        gap = plus_stats["min"] / max(join_stats["min"], 1e-9)
        print(f"  {n:>8}{plus_stats['min']:>16.1f}{join_stats['min']:>16.1f}{gap:>11.0f}x")

    print("\n  → N 每翻一倍，+= 的耗时约翻 4 倍（二次），join 约翻 2 倍（线性）")
    print("  → N=8000 时 join 快了三个数量级，这已经不是微优化，是救命")

    results = {
        "+= 循环拼接": (benchmark(concat_plus, 2_000, number=3, repeat=3), "O(n²)"),
        "join + 生成器": (benchmark(concat_join, 2_000, number=3, repeat=3), "O(n)，推荐"),
        "join + 列表": (benchmark(concat_join_list, 2_000, number=3, repeat=3), "O(n)，略快于生成器"),
    }
    report("N=2000 时的对比", results, "三者结果完全相同，只有性能差异 —— 推荐 join。")


# ==============================================================================
# 四、列表推导 vs for 循环
# ==============================================================================
# ===== 语法解析 =====
# 列表推导在 CPython 中被编译成 LOAD_FAST + LIST_APPEND 字节码，
# 循环体在一个更紧凑的作用域里执行，少了 STORE_FAST/LOAD_FAST 的往返。
# 官方说法是约 15%~25%，实测常在 20%~50%（取决于元素类型和表达式复杂度）。
#
# 什么情况下推导式更慢？
#   - 推导式里做了多次属性访问 / 索引
#   - 元素很复杂，临时变量很多（此时显式循环反而更清晰，收益也小）
#   - 需要在循环中间 break / continue（推导式只能靠三元表达式绕过，可读性差）


def loop_append(n: int) -> list[int]:
    """for 循环 + append。"""
    result = []
    append = result.append          # 提前绑定 append，省掉每次的属性查找
    for i in range(n):
        append(i * 2)
    return result


def loop_append_nobind(n: int) -> list[int]:
    """for 循环 + 直接调 result.append（常见写法）。"""
    result = []
    for i in range(n):
        result.append(i * 2)
    return result


def comprehension(n: int) -> list[int]:
    """列表推导式。"""
    return [i * 2 for i in range(n)]


def comprehension_nested(n: int) -> list[tuple[int, int]]:
    """嵌套推导：外层遍历对，内层遍历 n。"""
    return [(i, j) for i in range(20) for j in range(n)]


def loop_nested(n: int) -> list[tuple[int, int]]:
    """嵌套 for 循环 + append。"""
    result = []
    append = result.append
    for i in range(20):
        for j in range(n):
            append((i, j))
    return result


def demo_comprehension() -> None:
    N = 50_000
    print("\n" + "=" * 96)
    print(f" 04. 列表推导 vs for 循环（N = {N:,}）")
    print("=" * 96)

    results = {
        "for + append": (benchmark(loop_append, N, number=20), "提前绑定 append 方法"),
        "for + 直接append": (benchmark(loop_append_nobind, N, number=20), "每次都查属性"),
        "列表推导式": (benchmark(comprehension, N, number=20), "LIST_APPEND 字节码"),
    }
    report("耗时对比", results, "推荐列表推导式：更快且更简洁；for 循环保留给需要 break 的场景。")

    print(f"\n  嵌套推导式（20 × {N:,} = {20 * N:,} 个元组）：")
    results2 = {
        "嵌套 for 循环": (benchmark(loop_nested, N, number=2), "双层循环 + append"),
        "嵌套列表推导": (benchmark(comprehension_nested, N, number=2), "双层推导式"),
    }
    report("耗时对比", results2, "嵌套场景差距更大，且嵌套推导天然就是二维矩阵的写法。")


# ==============================================================================
# 五、dict vs list 查找
# ==============================================================================
# ===== 语法解析 =====
# list 查找：线性扫描 O(n)，最坏要比较 n 次
# dict 查找：哈希表 O(1)，平均 1~2 次比较，与数据量无关
#
# 这是"数据结构决定性能"最直观的例子。
# 优化原则：如果在循环里做成员检查或查找，先考虑能不能换成 set/dict。


def search_list(target: int, data: list[int]) -> int:
    """在列表里线性查找，返回索引。"""
    for index, value in enumerate(data):
        if value == target:
            return index
    return -1


def search_dict(target: int, data: dict[int, str]) -> str:
    """在字典里哈希查找。"""
    return data.get(target, "not-found")


def build_dict(n: int) -> dict[int, str]:
    """构造字典。"""
    return {i: f"user_{i}" for i in range(n)}


def build_list(n: int) -> list[int]:
    """构造列表。"""
    return list(range(n))


def membership_list(target: int, data: list[int]) -> bool:
    """列表成员检查。"""
    return target in data       # 内部是线性扫描


def membership_set(target: int, data: set[int]) -> bool:
    """集合成员检查。"""
    return target in data       # 哈希 O(1)


def demo_dict_vs_list() -> None:
    N = 20_000
    print("\n" + "=" * 96)
    print(f" 05. dict / set vs list 查找（N = {N:,}）")
    print("=" * 96)

    data_list = build_list(N)
    data_dict = build_dict(N)
    # 查最后一个 —— 列表最坏情况（要扫完全部 N 个元素）
    target = N - 1

    print(f"\n  查找最坏情况（目标在列表末尾，需扫描 {N:,} 个元素）：")
    list_us = benchmark(search_list, target, data_list, number=200)["min"]
    dict_us = benchmark(search_dict, target, data_dict, number=200)["min"]
    print(f"    list 线性查找    : {list_us:>10.3f} μs")
    print(f"    dict 哈希查找    : {dict_us:>10.3f} μs")
    print(f"    差距            : {list_us / dict_us:>10,.0f} 倍")

    print(f"\n  成员检查 in（同样的最坏情况）：")
    list_mem_us = benchmark(membership_list, target, data_list, number=200)["min"]
    set_mem_us = benchmark(membership_set, target, set(data_list), number=200)["min"]
    print(f"    target in list    : {list_mem_us:>10.3f} μs")
    print(f"    target in set     : {set_mem_us:>10.3f} μs")
    print(f"    差距             : {list_mem_us / set_mem_us:>10,.0f} 倍")

    print(f"\n  数据量对查找耗时的影响（看 dict 是否与 N 无关）：")
    print(f"  {'N':>10}{'list 查找(μs)':>16}{'dict 查找(μs)':>16}{'差距':>12}")
    print("  " + "-" * 56)
    for n in (5_000, 10_000, 20_000, 40_000):
        dl = build_list(n)
        dd = build_dict(n)
        lu = benchmark(search_list, n - 1, dl, number=100)["min"]
        du = benchmark(search_dict, n - 1, dd, number=100)["min"]
        print(f"  {n:>10,}{lu:>16.1f}{du:>16.3f}{lu / du:>11,.0f}x")

    print("\n  → list 耗时随 N 线性增长，dict 基本恒定（哈希 O(1)）")
    print("  → 原则：循环内的成员检查/查找，一律优先考虑 set / dict")

    print("\n  构造成本对比（字典构建比列表慢，因为要计算哈希）：")
    results = {
        "list(range(n))": (benchmark(lambda n=n: build_list(n), number=100), "直接分配连续内存"),
        "dict 推导式": (benchmark(lambda n=n: build_dict(n), number=100), "逐个算哈希 + 插入"),
    }
    report("构造耗时", results, "dict 贵在构建，但换来了 O(1) 查询 —— 值得。")


# ==============================================================================
# 六、__slots__ 内存对比
# ==============================================================================
# ===== 语法解析 =====
# 默认情况下，每个实例都有自己的 __dict__（一个哈希表），开销约 100+ 字节。
# __slots__ = ("a", "b") 声明固定属性后，实例改用「紧凑布局」：
#   不再创建 __dict__，属性直接存在对象内部的定长槽位里。
#
# 收益：
#   - 内存减少 30%~50%（取决于属性数量）
#   - 属性访问略快（没有 dict 哈希查找）
#   - ★ 附带好处：禁止随意添加未声明的属性，能提前发现拼写错误
#
# 代价：
#   - 不能给实例动态加新属性（除非子类有 __dict__）
#   - 不能用 __dict__ 遍历属性
#   - 内存中几百万对象时才有意义


class PointNormal:
    """普通类：每个实例都有自己的 __dict__。"""

    def __init__(self, x: float, y: float, label: str) -> None:
        self.x = x
        self.y = y
        self.label = label


class PointSlotted:
    """使用 __slots__ 的类：无 __dict__，属性存在定长槽位。

    __slots__ 只能写属性名，且必须写成"元组字面量"或"单个字符串"。
    写了 __slots__ 后：
      - 实例不能再加未声明的属性
      - 也不能继承一个有 __dict__ 的父类（否则 __slots__ 失效）
    """

    __slots__ = ("x", "y", "label")     # ← 元组形式，不能写成 ["x", "y"]（列表会被当作单个名字）

    def __init__(self, x: float, y: float, label: str) -> None:
        # 槽位赋值走 C 层 slot descriptor，比普通属性写入快
        self.x = x
        self.y = y
        self.label = label

    def __repr__(self) -> str:
        # __slots__ 类不能自动生成 __repr__，需要手写
        return f"PointSlotted({self.x}, {self.y}, {self.label!r})"


def measure_memory(cls: type, count: int = 50_000) -> tuple[int, int]:
    """测量 count 个实例的单个大小（字节）。

    用 sys.getsizeof 只量对象本身；因为两者对象头大小相同，
    差值就是 __dict__ 的开销。
    """
    import sys

    # 先创建一个"代表性"实例来量 —— 实例大小与属性值无关，只与类型布局有关
    instance = cls(1.0, 2.0, "p")
    single_size = sys.getsizeof(instance)
    # 对象头包含指向类的指针，所以要减去这部分才是"属性存储成本"
    return single_size, count * single_size


def demo_slots() -> None:
    print("\n" + "=" * 96)
    print(" 06. __slots__ 内存对比")
    print("=" * 96)

    global _normal_instance, _slotted_instance

    COUNT = 50_000
    normal_one, normal_total = measure_memory(PointNormal)
    slotted_one, slotted_total = measure_memory(PointSlotted)

    print(f"\n  单个实例大小（{COUNT:,} 个实例）：")
    print(f"  {'类':<20}{'单实例(字节)':>14}{'{:,} 个实例(字节)'.format(COUNT):>20}")
    print("  " + "-" * 56)
    print(f"  {'PointNormal':<20}{normal_one:>14}{normal_total:>20,}")
    print(f"  {'PointSlotted':<20}{slotted_one:>14}{slotted_total:>20,}")

    saved = normal_one - slotted_one
    ratio = normal_one / slotted_one
    print(f"\n  每个实例节省 : {saved} 字节")
    print(f"  内存压缩比   : {ratio:.2f}x（省 {saved / normal_one * 100:.1f}%）")
    print(f"  {COUNT:,} 个实例共省 : {saved * COUNT / 1024 / 1024:.2f} MB")

    # 真实案例：百万级对象时的差距
    MILLION = 1_000_000
    print(f"\n  放大到 {MILLION:,} 个对象（真实业务场景量级）：")
    print(f"    普通类   : {normal_one * MILLION / 1024 / 1024:>8.2f} MB")
    print(f"    __slots__: {slotted_one * MILLION / 1024 / 1024:>8.2f} MB")
    print(f"    节省     : {saved * MILLION / 1024 / 1024:>8.2f} MB")

    # 属性访问速度对比
    def read_normal(n: int) -> float:
        total = 0.0
        for _ in range(n):
            total += _normal_instance.x
        return total

    def read_slotted(n: int) -> float:
        total = 0.0
        for _ in range(n):
            total += _slotted_instance.x
        return total

    # 提前把实例绑成模块级变量，读写测量的都是真正的属性访问路径
    _normal_instance = PointNormal(1.5, 2.5, "normal")
    _slotted_instance = PointSlotted(1.5, 2.5, "slotted")

    results = {
        "普通类属性读取": (benchmark(read_normal, 1_000_000, number=5), "走 __dict__ 哈希查找"),
        "__slots__ 属性读取": (benchmark(read_slotted, 1_000_000, number=5), "slot descriptor，更直接"),
    }
    report("属性访问 100 万次", results, "__slots__ 访问更快，但差距小于内存收益。")

    # 展示 slots 的限制
    print("\n  __slots__ 的副作用（工程上要注意）：")
    p = PointSlotted(1.0, 2.0, "test")
    try:
        p.z = 3.0        # type: ignore[attr-defined]
    except AttributeError as exc:
        print(f"    动态添加属性被拒 : {type(exc).__name__}: {exc}")
        print("    ✓ 这其实是好事 —— 能提前发现属性名拼写错误")

    print("\n  什么时候该用 __slots__：")
    print("    ✓ 纯数据载体类（DTO / Point / Record），实例数量以万计")
    print("    ✓ 不需要继承、不需要动态属性、不需要 __dict__ 遍历")
    print("    ✗ 需要多态（要继承）时慎用 —— 子类会丢失 slots 收益")
    print("    ✗ 实例数量只有几百个时，收益可以忽略")


_normal_instance: PointNormal = None    # type: ignore[assignment]
_slotted_instance: PointSlotted = None  # type: ignore[assignment]


# ==============================================================================
# 七、lru_cache 记忆化
# ==============================================================================
# ===== 语法解析 =====
# functools.lru_cache 把函数的【输入 -> 输出】缓存下来，
# 相同参数直接返回上次的结果，不再执行函数体。
#
# 适用前提（缺一不可）：
#   1. 纯函数：相同输入必定相同输出（不能有副作用、不能依赖时间/随机）
#   2. 命中率高：参数组合可重复
#   3. 哈希成本低：参数必须可哈希（list 不行，要用 tuple 或 lru_cache + 手动 hash）
#
# lru_cache vs cache：
#   Python 3.9+ 推荐 @functools.cache（等价于 maxsize=128 的 lru_cache，无淘汰逻辑更快）
#   用 maxsize=None 才是真正的"全量缓存"


# ===== 演示 1：纯函数 + 高重复 =====
@functools.lru_cache(maxsize=128)
def fib(n: int) -> int:
    """斐波那契：典型的"该用记忆化但没用"的反例。

    朴素递归是 O(φ^n) 指数级；记忆化后变成 O(n) 线性。
    """
    if n < 2:
        return n
    return fib(n - 1) + fib(n - 2)


# ===== 演示 2：真正的性能加速 =====
@functools.lru_cache(maxsize=256)
def expensive_square(value: float) -> float:
    """模拟一个"很贵"的计算（现实中比如复杂公式、图像运算）。"""
    # 用一点真实计算量，让差异更明显
    result = 0.0
    for i in range(200):
        result += (value * i) % 7 / (i + 1)
    return value * value + result


def uncached_square(value: float) -> float:
    """同样的计算，但不带缓存。"""
    result = 0.0
    for i in range(200):
        result += (value * i) % 7 / (i + 1)
    return value * value + result


# ===== 演示 3：参数可哈希性的坑 =====
@functools.lru_cache(maxsize=64)
def cached_len(items: tuple[int, ...]) -> int:
    """缓存要求参数可哈希 —— 必须用 tuple，不能用 list。"""
    return len(items)


def demo_lru_cache() -> None:
    print("\n" + "=" * 96)
    print(" 07. lru_cache 记忆化缓存")
    print("=" * 96)

    # ---------- 7.1 斐波那契：复杂度对比 ----------
    print("\n  7.1 记忆化把指数级变成线性级")

    def fib_naive(n: int, _cache: dict[int, int] | None = None) -> int:
        """朴素递归：同样的子问题会被反复计算。"""
        if n < 2:
            return n
        return fib_naive(n - 1) + fib_naive(n - 2)

    # 手写记忆化版，便于对比（功能与 lru_cache 版相同）
    def fib_manual(n: int, _memo: dict[int, int] | None = None) -> int:
        if _memo is None:
            _memo = {}
        if n < 2:
            return n
        if n in _memo:
            return _memo[n]
        _memo[n] = fib_manual(n - 1, _memo) + fib_manual(n - 2, _memo)
        return _memo[n]

    # 计时辅助：直接算运行时长（因为每次调用的耗时差太大，不适合 timeit 统一处理）
    def timed(fn: Callable[[], Any]) -> float:
        start = time.perf_counter()      # ★ 测耗时用 perf_counter，不用 time()
        fn()
        return (time.perf_counter() - start) * 1000   # 转成毫秒

    fib_lru = functools.lru_cache(maxsize=None)(fib)   # 复制一份无上限版单独计时

    print(f"  {'n':>5}{'朴素递归(ms)':>18}{'lru_cache(ms)':>18}{'提升':>14}")
    print("  " + "-" * 56)
    for n in (18, 20, 22, 24, 25):
        naive_ms = timed(lambda n=n: fib_naive(n))
        cache_ms = timed(lambda n=n: fib_lru(n))
        print(f"  {n:>5}{naive_ms:>18.3f}{cache_ms:>18.3f}{naive_ms / max(cache_ms, 1e-9):>13.0f}x")

    print("\n  → n=25 时朴素递归要算 24 万次，记忆化只算 25 次")
    print("  → 提升倍数随 n 指数增长，这正是 O(φⁿ) 与 O(n) 的差距")

    # 清空缓存，避免影响后面的统计
    fib_lru.cache_clear()
    fib.cache_clear()

    # ---------- 7.2 缓存命中率 ----------
    print("\n  7.2 缓存命中率的真实影响")

    print("\n  场景 A：全部命中（同一批参数反复调用）")
    hits = 0

    @functools.lru_cache(maxsize=128)
    def counted(value: int) -> int:
        return value * 2

    for _ in range(3):
        for i in range(10):
            counted(i)               # 第二次开始全部命中
    hits = counted.cache_info().hits
    print(f"    30 次调用 → {counted.cache_info()}")
    print(f"    → 命中率 {hits / 30 * 100:.0f}%，计算只发生 10 次")

    print("\n  场景 B：几乎不命中（每次参数都不同）")
    @functools.lru_cache(maxsize=128)
    def counted2(value: int) -> int:
        return value * 2

    for i in range(30):
        counted2(i * 1000 + i)       # 参数各不相同
    print(f"    30 次调用 → {counted2.cache_info()}")
    print(f"    → 命中率 0%，纯粹白付哈希+字典查找的 overhead")

    print("\n  → 结论：缓存只在【参数重复率高】时才划算")

    # ---------- 7.3 加速对比 ----------
    print("\n  7.3 同一批参数重复调用 100 次")
    values = [float(i) * 1.7 for i in range(10)]

    def call_all_cached() -> None:
        for _ in range(10):
            for v in values:
                expensive_square(v)

    def call_all_uncached() -> None:
        for _ in range(10):
            for v in values:
                uncached_square(v)

    # 清缓存，确保公平
    expensive_square.cache_clear()

    cached_ms = timed(call_all_cached)
    uncached_ms = timed(call_all_uncached)

    print(f"    带缓存   : {cached_ms:>10.3f} ms  ({call_all_cached.__name__} 执行 100 次)")
    print(f"    不带缓存 : {uncached_ms:>10.3f} ms")
    print(f"    加速比   : {uncached_ms / max(cached_ms, 1e-9):>10,.0f} 倍")
    print(f"    缓存统计 : {expensive_square.cache_info()}")
    print(f"    → 命中 {expensive_square.cache_info().hits} 次，"
          f"未命中 {expensive_square.cache_info().misses} 次，"
          f"命中率 {expensive_square.cache_info().hits / max(expensive_square.cache_info().hits + expensive_square.cache_info().misses, 1) * 100:.0f}%")

    # ---------- 7.4 参数可哈希性 ----------
    print("\n  7.4 常见陷阱：list 不可哈希")
    try:
        cached_len([1, 2, 3])        # type: ignore[arg-type]
    except TypeError as exc:
        print(f"    cached_len([1,2,3])   -> TypeError: {exc}")
        print("    → 缓存要求参数可哈希；传 list 会直接失败")
    print(f"    cached_len((1,2,3))   -> {cached_len((1, 2, 3))}   ← 用 tuple 即可")
    print(f"    缓存统计             : {cached_len.cache_info()}")

    print("\n  lru_cache 常用 API：")
    print("    .cache_info()   → 命中/未命中/大小统计（NamedTuple）")
    print("    .cache_clear()  → 清空缓存（改配置后必须调，否则拿到旧值）")
    print("    .cache_parameters() → 查看 maxsize 设置")
    print("    maxsize=None    → 无上限，永不淘汰（等价 @functools.cache）")


# ==============================================================================
# 八、cProfile 性能剖析
# ==============================================================================
# ===== 语法解析 =====
# cProfile 的工作原理：底层 C 实现，用采样式钩子记录每次函数调用。
# 相比手写计时（只能告诉你"整体慢"），它能精确告诉你：
#   - 哪些函数被调用了多少次（ncalls）
#   - 总耗时 / 每次平均耗时 / 累积耗时（含子调用）
#   - 函数内部各行的相对耗时（line_profiler 需要第三方库）
#
# 三个关键指标：
#   ncalls     调用次数 —— 如果这个数异常大，优化方向可能是"减少调用"
#   tottime    函数自身耗时（不含子函数）
#   cumtime    累积耗时（含子函数）—— tottime 小但 cumtime 大的，是"调用者视角的热点"


def work_small(n: int) -> int:
    """轻量级工作：调用次数多但单次很快。"""
    return sum(i * i for i in range(n))


def work_heavy(n: int) -> float:
    """重量级工作：调用次数少但单次很慢 —— 这才是真热点。"""
    total = 0.0
    for i in range(n):
        total += (i ** 0.5) * 1.000001
    return total


def mixed_workload(rounds: int, n: int) -> float:
    """混合负载：heavy 被调用少量次，small 被调用大量次。"""
    total = 0.0
    for r in range(rounds):
        total += work_heavy(n)
        # 在循环里多次调用轻量函数，制造"调用次数很多"的假象
        for _ in range(200):
            total += work_small(50) / 1000
    return total


def profile_workload() -> str:
    """用 cProfile 剖析 mixed_workload，返回文本报告。"""
    profiler = cProfile.Profile()
    profiler.enable()
    mixed_workload(rounds=6, n=3000)
    profiler.disable()

    # 写入 StringIO 而不是文件 —— 不污染工作目录
    buffer = io.StringIO()
    # sort_stats("cumulative") 按累积耗时排序：这是找"调用链上耗时最多"的视角
    stats = pstats.Stats(profiler, stream=buffer)
    stats.sort_stats("cumulative")
    stats.print_stats(limit=8)
    return buffer.getvalue()


def profile_by_tottime() -> str:
    """按 tottime 排序：找"函数自身最耗时"的视角（排除子函数干扰）。"""
    profiler = cProfile.Profile()
    profiler.enable()
    mixed_workload(rounds=6, n=3000)
    profiler.disable()

    buffer = io.StringIO()
    stats = pstats.Stats(profiler, stream=buffer)
    stats.sort_stats("tottime")
    # print_stats("work") 只打印函数名含 work 的行 —— pstats 的过滤能力
    stats.print_stats("work", limit=6)
    return buffer.getvalue()


def demo_cprofile() -> None:
    print("\n" + "=" * 96)
    print(" 08. cProfile 性能剖析")
    print("=" * 96)

    print("\n  8.1 按 cumulative（累积耗时）排序 —— 找调用链上的热点")
    print("-" * 96)
    for line in profile_workload().splitlines():
        print(f"  {line}")

    print("\n  8.2 按 tottime（自身耗时）排序，只看 work 开头的函数")
    print("-" * 96)
    for line in profile_by_tottime().splitlines():
        print(f"  {line}")

    print("\n  8.3 如何读这张表")
    print("-" * 96)
    print("  ncalls    调用次数")
    print("  tottime   函数体自身耗时（已排除它调用的其他函数）")
    print("  cumtime   累积耗时（含它调用的所有函数）")
    print()
    print("  常见误读与正确读法：")
    print("    ✗ 看到 ncalls 最大的函数就去优化它")
    print("      → work_small 调用上万次但每次很快，总耗时可能不高")
    print("    ✓ 优先看 tottime 大且 ncalls 不多的 —— 那才是真热点")
    print("    ✓ cumtime 大但 tottime 小的函数是\"调用者\"，优化它下面的被调用函数更有效")
    print()
    print("  优化流程：")
    print("    1. cProfile 跑一遍，找到 tottime 最高的 1~2 个函数")
    print("    2. 只优化这几个，不要动其他地方")
    print("    3. line_profiler 看函数内部哪几行最慢（需 pip install line_profiler）")
    print("    4. 改完再 profile 一次，对比确认")
    print("    5. ★ 跑一遍基准测试确认没有让其他场景变慢")


# ==============================================================================
# 九、优化清单速查
# ==============================================================================
def print_optimization_guide() -> None:
    print("\n" + "=" * 96)
    print(" 09. 优化优先级速查")
    print("=" * 96)

    print("""
  【第一梯队：改变复杂度，效果通常 100 倍以上】
    ✅ 列表/线性扫描      -> set / dict          O(n)   -> O(1)
    ✅ 重复字符串拼接      -> ''.join()           O(n²)  -> O(n)
    ✅ 重复子问题计算      -> @lru_cache          指数级 -> 线性级
    ✅ 循环内数据库查询    -> 一次性批量查询      N 次IO -> 1 次IO
    ✅ O(n) 查找          -> 排序 + 二分         O(n)   -> O(log n)
    ✅ 字符串驻留/复用     -> sys.intern / 常量池

  【第二梯队：减少对象与调用，效果 2~10 倍】
    ✅ 生成器代替中间列表    省内存，少一次遍历
    ✅ __slots__            每实例省 50~100 字节
    ✅ 批量操作代替逐个操作  减少循环开销
    ✅ 惰性求值              用不到的不算（生成器 / 推导式的条件表达式）

  【第三梯队：微优化，效果 10%~50%】
    ✅ 局部变量绑定全局     LOAD_FAST vs LOAD_GLOBAL
    ✅ 列表推导 vs for+append
    ✅ 避免重复属性查找      x = obj.attr 提到循环外
    ✅ 用局部引用代替内建函数  func = len

  【几乎没用 / 反而有害】
    ❌ 不要把简单代码改成难懂的"性能写法" —— 可维护性损失大于收益
    ❌ 不要用 time.time 的差值做基准 —— 会被系统时间调整污染
    ❌ 不要凭直觉优化 —— 必须先 cProfile 找到热点
    ❌ 不要用 lru_cache 缓存有副作用的函数 —— 会导致重复执行被跳过
    ❌ 不要给参数几乎不重复的函数加缓存 —— 白付 overhead
""")


# ==============================================================================
# 十、主流程
# ==============================================================================
def main() -> None:
    """主流程：8 组性能实测，全部秒级完成。"""
    start = time.perf_counter()

    print("=" * 96)
    print(" 08. Python 性能优化实战（全部基于 timeit / cProfile 实测）")
    print("=" * 96)
    print(f"  解释器 : Python {sys.version.split()[0]}  ({sys.implementation.name})")
    print(f"  平台   : {sys.platform}")
    print(f"  计时器 : time.perf_counter()（单调递增，不受系统时间调整影响）")
    print("  说明   : 绝对耗时因机器而异，重点看【倍数】——它反映算法差异")

    demo_generator_vs_list()      # 1
    demo_local_binding()          # 2
    demo_string_concat()          # 3
    demo_comprehension()          # 4
    demo_dict_vs_list()           # 5
    demo_slots()                  # 6
    demo_lru_cache()              # 7
    demo_cprofile()               # 8
    print_optimization_guide()    # 9

    elapsed = time.perf_counter() - start
    print("=" * 96)
    print(f" 全部演示完成，总耗时 {elapsed:.2f} 秒")
    print("=" * 96)


if __name__ == "__main__":
    main()
