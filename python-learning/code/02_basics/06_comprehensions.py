# -*- coding: utf-8 -*-
r"""
================================================================================
文件：06_comprehensions.py
模块：02_basics（基础语法配套）

【本文件演示的语法点列表】
  1. 列表推导式 List Comprehension：[expr for x in it if cond]
     完整语法：[表达式 for 目标 in 可迭代对象 if 条件1 if 条件2 for 子目标 in ...]
  2. 字典推导式 Dict Comprehension：{k_expr: v_expr for x in it}
  3. 集合推导式 Set Comprehension：{expr for x in it}
  4. 生成器表达式 Generator Expression：(expr for x in it)
  5. 多层 for 与多条件 if 的组合规则与执行顺序
  6. 条件表达式在推导式中的位置：(a if cond else b) 放在【表达式位】
     而 if cond 筛选放在【末尾】，两者语义完全不同（高频易混淆点）
  7. 嵌套推导式与矩阵展平
  8. 推导式的 Python 2 遗留语法：列表推导式的方括号作用域泄漏问题（附说明）
  9. 推导式的可读性边界：何时该停止使用推导式
 10. 推导式 vs 普通循环：timeit 性能实测（等价任务对比）
 11. 推导式 vs 生成器表达式：内存占用实测对比

【设计意图】
  推导式是 Python 的"语法糖 + 作用域规则"双重设计：
  (1) 语法糖层面，它把"建列表 + 循环 + 条件"三件事压成一行，
      可读性在适度嵌套时优于循环（这正是它被 PEP 8 推荐的原因）；
  (2) 作用域层面，Python 3 把列表推导式提升为一个【独立作用域】，
      修复了 Python 2 中循环变量泄漏到外层的 bug。
  需要强调的是：推导式不是"炫技"，它在【一层过滤/一层映射】时最清晰，
  超过两层就应该换回普通循环或辅助函数，否则可读性会断崖下跌。

【预期输出摘要】
  [1] 列表推导式：基础、过滤、双 if、多层 for
  [2] 字典推导式：反转、平方表、条件构造
  [3] 集合推导式：去重效果
  [4] 生成器表达式：惰性、内存对比
  [5] if 筛选 vs 三元表达式：位置不同语义不同
  [6] 作用域：推导式内变量不会泄漏
  [7] 性能实测：推导式 vs 循环、生成器 vs 列表的内存
================================================================================
"""

import sys
import timeit


# ============================================================================
# 语法解析 1：列表推导式 —— 完整语法与执行顺序
# ============================================================================
# 【语法规则】
#   [表达式 for 目标 in 可迭代对象 if 条件]
#     [ ]  是列表推导式的标志（决定结果是 list）
#     表达式  每个元素的结果，可以是任意表达式
#     for 目标 in 可迭代  遍历，可以有多层
#     if 条件  过滤（可选），可以写多个 if（是 AND 关系）
#   执行顺序（从左到右理解，从右往左执行）：
#     最右侧的 for 最先执行，然后逐层向左
#     每个 for 内部，if 条件在表达式之前判断（不满足就跳过）
#   等价普通写法：
#     result = []
#     for x in 可迭代对象:
#         if 条件:
#             result.append(表达式)
# 【设计意图】
#   推导式的三段式结构（表达式 / for / if）严格对应普通循环的三步
#   （做什么 / 遍历什么 / 过滤什么），只是把它们压缩进了中括号。
#   注意 if 写在【末尾】是"过滤"，不是"条件表达式"——
#   条件表达式 (a if cond else b) 写在【开头】的表达式位置，二者极易混淆。
def demo_list_comprehension():
    print("[1] 列表推导式")

    # 基础：映射
    numbers = [1, 2, 3, 4, 5]
    squares = [x ** 2 for x in numbers]
    print(f"    [x**2 for x in numbers]      = {squares}   （映射：每个元素平方）")

    # 基础：过滤
    evens = [x for x in numbers if x % 2 == 0]
    print(f"    [x for x in numbers if x%2==0] = {evens}   （过滤：只留偶数）")

    # 映射 + 过滤（最常用组合）
    even_squares = [x ** 2 for x in numbers if x % 2 == 0]
    print(f"    [x**2 for x in numbers if x%2==0] = {even_squares}   （先过滤，再对留下的元素平方）")

    # 等价于普通循环
    manual = []
    for x in numbers:
        if x % 2 == 0:
            manual.append(x ** 2)
    print(f"    等价普通循环结果 = {manual}   （与推导式一致：{manual == even_squares}）")

    # 多个 if 条件是 AND 关系（相当于串联的 if）
    # 先过滤出 5..10 的偶数
    result = [x for x in range(20) if x > 5 if x % 2 == 0]
    print(f"    [x for x in range(20) if x>5 if x%2==0] = {result}   （两个 if 是 AND）")
    # 等价于 if x > 5 and x % 2 == 0
    result2 = [x for x in range(20) if x > 5 and x % 2 == 0]
    print(f"    [x for x in range(20) if x>5 and x%2==0] = {result2}   （等价写法）")

    # 多层 for：笛卡尔积
    # 等价于 for a in A: for b in B: result.append(...)
    pairs = [(a, b) for a in [1, 2] for b in ["x", "y"]]
    print(f"    [(a,b) for a in [1,2] for b in 'xy'] = {pairs}")
    print("    -> 最右侧的 for 最先执行：先遍历 b（'x','y'），每次再遍历 a（1,2）")

    # 嵌套推导式：展平二维列表
    matrix = [[1, 2, 3], [4, 5, 6], [7, 8, 9]]
    flat = [num for row in matrix for num in row]
    print(f"    展平二维 = [num for row in matrix for num in row] = {flat}")
    print("    -> 多层 for 用空格分隔，展平二维列表的标准写法")

    # 推导式遍历字符串
    chars = [c.upper() for c in "hello"]
    print(f"    [c.upper() for c in 'hello'] = {chars}")

    # 推导式遍历字典（遍历的是键）
    d = {"a": 1, "b": 2, "c": 3}
    keys = [k for k in d]
    vals = [v for v in d.values()]
    print(f"    [k for k in d]         = {keys}   （遍历字典得到键）")
    print(f"    [v for v in d.values()] = {vals}")

    # 推导式遍历 range 生成数字
    print(f"    [x*x for x in range(1,5)] = {[x*x for x in range(1,5)]}   （平方 1,4,9,16）")

    # 嵌套：外层推导里放内层推导
    nested = [[x + y for x in row] for y in [0, 10] for row in [[1, 2], [3, 4]]]
    print(f"    嵌套推导式 = {nested}")

    # 用推导式调用有副作用的函数（可用于扁平化，但要谨慎）
    words = ["hello", "world", "python"]
    chars_flat = [c for w in words for c in w]
    print(f"    展平字符串列表 = {chars_flat}")


# ============================================================================
# 语法解析 2：字典推导式
# ============================================================================
# 【语法规则】
#   {键表达式: 值表达式 for 目标 in 可迭代对象 if 条件}
#     { }  标志结果是 dict
#     键表达式:值表达式   冒号分隔，键在前值在后
#     同样支持 if 过滤和多层 for
#   字典推导式的键必须【可哈希】（不能是 list/dict/set）
# 【执行顺序】
#   与列表推导式一致：最右 for 先执行，逐层向左，每层内先 if 后表达式。
#   键和值的表达式【都】会求值，键先算（用于定位槽位），值后算。
# 【设计意图】
#   字典推导式是"批量构造映射"的最自然表达：
#       {word: len(word) for word in words}
#   它比 dict.fromkeys + 循环更新更清晰，且只需遍历一次数据。
def demo_dict_comprehension():
    print("[2] 字典推导式")

    # 基础：构造字典
    words = ["apple", "banana", "cherry"]
    word_len = {word: len(word) for word in words}
    print(f"    {{word: len(word)}} = {word_len}   （单词 -> 长度）")

    # 键值互换（反转字典）
    original = {"a": 1, "b": 2, "c": 3}
    inverted = {v: k for k, v in original.items()}
    print(f"    反转字典 {{v:k for k,v in d.items()}} = {inverted}")

    # 平方表
    squares = {x: x ** 2 for x in range(1, 6)}
    print(f"    平方表 {{x: x**2 for x in range(1,6)}} = {squares}")

    # 带条件
    even_squares = {x: x ** 2 for x in range(10) if x % 2 == 0}
    print(f"    {{x:x**2 for x in range(10) if x%2==0}} = {even_squares}   （偶数的平方）")

    # 从两个列表并行构造字典（用 zip）
    names = ["Alice", "Bob", "Charlie"]
    scores = [92, 88, 75]
    score_map = {name: score for name, score in zip(names, scores)}
    print(f"    {{name:score for name,score in zip(names,scores)}} = {score_map}")

    # 分组（分组计数是字典推导式的经典应用）
    # 把学生按分数段分组
    students = [
        ("Alice", 95), ("Bob", 82), ("Charlie", 58),
        ("David", 91), ("Eve", 76), ("Frank", 65),
    ]
    # 按分数段分组：优(>=90) 良(>=80) 及格(>=60) 不及格
    def grade_group(score):
        if score >= 90: return "优秀"
        if score >= 80: return "良好"
        if score >= 60: return "及格"
        return "不及格"
    groups = {}
    for name, score in students:
        g = grade_group(score)
        groups.setdefault(g, []).append(name)
    print(f"    分组（普通循环 + setdefault）= {groups}")

    # 同样逻辑用嵌套推导式（更紧凑）
    groups_comp = {
        g: [name for name, score in students if grade_group(score) == g]
        for g in ["优秀", "良好", "及格", "不及格"]
    }
    print(f"    分组（嵌套字典推导式）= {groups_comp}")
    print("    -> 两种写法结果一致，推导式更紧凑（但循环分组性能与可读性各有权衡）")

    # 计数（用 dict.get 惯用法 / Counter）
    print("\n    [字典计数惯用法]")
    fruits = ["apple", "banana", "apple", "cherry", "banana", "apple"]
    # 普通循环计数
    counts = {}
    for f in fruits:
        counts[f] = counts.get(f, 0) + 1
    print(f"    普通循环 counts.get(f,0)+1 = {counts}")
    # 字典推导式做不到增量计数（它是一次性构造），所以计数场景要用循环或 Counter
    print("    -> 注意：字典推导式【不适合】增量计数，因为推导式不保存中间状态")
    print("       计数场景应该用 collections.Counter 或普通循环")

    # 键必须可哈希
    print("\n    [键必须可哈希]")
    try:
        _ = {[1, 2]: "value" for x in range(1)}  # list 不可哈希
    except TypeError as e:
        print(f"    用 list 做键 -> TypeError: {str(e).splitlines()[0][:60]}")
    print("    -> 字典的键必须是 int/str/float/tuple(元素都可哈希)等，不可变且可哈希")


# ============================================================================
# 语法解析 3：集合推导式
# ============================================================================
# 【语法规则】
#   {表达式 for 目标 in 可迭代对象 if 条件}
#     { }  标志结果是 set（不是 dict，因为没有冒号）
#     同样支持 if 过滤
#   set 的特性：元素唯一（自动去重），无序（3.7+ 保留插入序但不按序查找）
# 【执行顺序】
#   与列表推导式一致，但每个元素加入 set 时会：
#     1. 计算哈希值
#     2. 若已存在则丢弃（去重）
#     3. 否则插入
#   这就是 set 去重的原理：靠哈希 + 桶定位，而不是逐个比较。
# 【设计意图】
#   集合推导式是"去重 + 筛选"的最自然表达：
#       {x % 3 for x in data}   得到所有余数种类
#   由于 set 自动去重，往往可以省掉额外的去重逻辑。
def demo_set_comprehension():
    print("[3] 集合推导式")

    # 基础：去重
    numbers = [1, 2, 3, 4, 5, 2, 3, 1]
    unique_squares = {x ** 2 for x in numbers}
    print(f"    {{x**2 for x in [1,2,3,4,5,2,3,1]}} = {unique_squares}   （自动去重：重复元素只保留一份）")

    # 对比：列表推导式不会去重
    list_squares = [x ** 2 for x in numbers]
    print(f"    [x**2 for x in ...]（列表）= {list_squares}   （不去重，保留重复）")
    print(f"    长度对比：列表 {len(list_squares)} 个，集合 {len(unique_squares)} 个")

    # 筛选 + 去重
    words = ["apple", "banana", "apple", "orange"]
    first_letters = {w[0] for w in words}
    print(f"    {{w[0] for w in words}} = {first_letters}   （取首字母集合，自动去重）")

    # 求所有不同的字符
    text = "hello world"
    unique_chars = {c for c in text if c != " "}
    print(f"    文本去重（去掉空格）= {unique_chars}")

    # 求余数种类（经典应用）
    data = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
    remainders = {x % 3 for x in data}
    print(f"    所有模3余数 = {remainders}   （{{x%3 for x in range(1,11)}}）")

    # 集合推导式做交集、差集
    s1 = {x for x in range(10) if x % 2 == 0}   # 偶数
    s2 = {x for x in range(10) if x % 3 == 0}   # 3的倍数
    print(f"    偶数集合 = {s1}")
    print(f"    3的倍数 = {s2}")
    print(f"    交集 = {s1 & s2}")
    print(f"    并集 = {s1 | s2}")
    print(f"    差集 = {s1 - s2}")

    # 空集合的坑
    print("\n    [空集合的坑]")
    empty_comp = {x for x in []}
    print(f"    {{x for x in []}}      = {empty_comp!r}   （空集合推导式，type = {type(empty_comp).__name__}）")
    # 但 {} 在字面量中表示空【字典】不是空集合！
    empty_dict = {}
    print(f"    {{}} 字面量            = {empty_dict!r}   （这是空【字典】，type = {type(empty_dict).__name__}）")
    print(f"    空集合必须写 set()     = {set()!r}")
    print("    -> 这是 Python 经典陷阱：{} 是空字典，空集合是 set()")

    # set 与列表的对比用途
    print("\n    [set 的实际用途：快速去重/成员判定]")
    big_list = list(range(100))
    big_set = {x for x in big_list}
    print(f"    列表转集合：len(列表)={len(big_list)}, len(集合)={len(big_set)}")
    print(f"    这里元素本来就唯一，所以长度相同；但若原列表有重复，集合会自动去重")


# ============================================================================
# 语法解析 4：生成器表达式
# ============================================================================
# 【语法规则】
#   (表达式 for 目标 in 可迭代对象 if 条件)
#     ( )  标志结果是【生成器/迭代器】，不是列表
#   生成器表达式的语法与列表推导式几乎一样，唯一区别是最外层 [] vs ()
#   关键区别：
#     列表推导式  立即计算全部，结果占 O(n) 内存
#     生成器表达式 惰性计算，每次只产出一个，O(1) 内存
#   生成器表达式【不能为空】：(x for x in []) 是合法的空生成器，但
#     [x for x in [] if x] 也是合法的空列表 —— 空不是错误
# 【执行顺序】
#   生成器表达式的执行是【惰性的】：
#     创建时不执行任何元素计算
#     每次 next() 时，才计算下一个元素并 yield
#   所以它天然支持无限序列、数据流处理、超大数据集的流式处理。
# 【设计意图】
#   生成器表达式解决的是"数据量大到装不进内存"的场景。
#   它是"惰性求值"在 Python 中的直接体现：
#   不需要先算完所有中间结果，而是像流水线一样逐个产出。
#   当你不确定数据规模、或数据来自网络/文件流时，生成器是更安全的选择。
def demo_generator_expression():
    print("[4] 生成器表达式")

    # 基础：语法与列表推导式一样
    numbers = [1, 2, 3, 4, 5]
    gen = (x ** 2 for x in numbers)
    print(f"    (x**2 for x in numbers) = {gen}   （是生成器对象，不是列表）")
    print(f"    type = {type(gen).__name__}")

    # 惰性：创建时不计算
    print("\n    [惰性验证]")
    side_effects = []
    def track(x):
        side_effects.append(x)
        return x
    lazy_gen = (track(x) for x in range(5))  # 创建时不执行 track
    print(f"    创建生成器后 side_effects = {side_effects}   （一个都没执行）")
    next(lazy_gen)
    print(f"    next() 一次后 side_effects = {side_effects}   （只执行了第 0 个）")
    # 完全消费
    print(f"    list(生成器) = {list(lazy_gen)}   （把剩下的都算出来，side_effects 现在 {side_effects}）")

    # 一次性：生成器只能遍历一次
    gen2 = (x for x in range(3))
    print(f"\n    [一次性] 第一次遍历 = {list(gen2)}")
    print(f"    第二次遍历 = {list(gen2)}   （已耗尽，空列表）")
    print("    -> 生成器是不可重复的，需要重复用请转成 list 或重新创建")

    # sum/any/all 直接消费生成器，不需转 list
    print("\n    [直接消费生成器]")
    nums_gen = (x for x in range(10))
    print(f"    sum(生成器) = {sum(nums_gen)}   （sum 内部迭代生成器，不需先转 list）")
    # 过滤后求和
    filtered_sum = sum(x for x in range(100) if x % 3 == 0)
    print(f"    sum(x for x in range(100) if x%3==0) = {filtered_sum}   （更常见：直接传生成器给 sum）")

    # 生成器 vs 列表：内存对比
    print("\n    [内存对比实测]")
    import sys
    list_obj = [x ** 2 for x in range(100000)]
    gen_obj = (x ** 2 for x in range(100000))
    list_size = sys.getsizeof(list_obj)
    gen_size = sys.getsizeof(gen_obj)
    print(f"    列表推导式（10万元素）: getsizeof = {list_size:,} 字节 ≈ {list_size/1024:.0f} KB")
    print(f"    生成器表达式（10万元素）: getsizeof = {gen_size:,} 字节（几乎不占内存）")
    print(f"    -> 列表已提前算完并驻留内存；生成器只保存规则，元素用到才计算")
    print(f"    -> getsizeof 只算容器本身，不含元素对象；但足以说明量级差异")

    # 生成器 vs 列表：性能（惰性在少量消费时更快）
    print("\n    [性能对比] 只取前 3 个元素时")
    # 列表：要算完 10 万个才能取前 3 个（浪费）
    t_list = timeit.timeit(
        "[x for x in range(100000)][:3]",
        number=1000,
    )
    # 生成器：只算前 3 个就停（高效）
    t_gen = timeit.timeit(
        "import itertools; list(itertools.islice((x for x in range(100000)), 3))",
        number=1000,
    )
    print(f"    列表[:3]  {t_list:.4f}s   （要先算完整个列表才能取前3个，浪费）")
    print(f"    生成器取3  {t_gen:.4f}s   （islice 只算前3个，但 islice 有额外开销）")
    print("    -> 只消费少量时生成器优势明显；消费全部时两者接近（生成器还要付惰性管理的开销）")

    # itertools.islice 是消费生成器前 N 个的标准工具
    from itertools import islice
    print(f"\n    [islice：只取前N个而不算全部]")
    big_gen = (x * 2 for x in range(1000000))
    first5 = list(islice(big_gen, 5))
    print(f"    islice(大生成器, 5) = {first5}   （一百万个数据，只算了 5 个）")
    print("    -> 需要'只看前几个'时，生成器 + islice 是正确且高效的组合")

    # 空生成器
    empty_gen = (x for x in [])
    print(f"\n    (x for x in []) = {empty_gen}   （空生成器是合法的，不报错）")
    print(f"    list(空生成器) = {list(empty_gen)}")


# ============================================================================
# 语法解析 5：高频易混淆 —— if 筛选 vs 条件表达式
# ============================================================================
# 【语法规则】
#   两者都用 if，但位置不同，语义完全不同：
#   [a if cond else b for x in it]   条件表达式（开头）：对每个元素【三选一】
#   [a for x in it if cond]          条件筛选（末尾）：对每个元素【二选一，保留或丢弃】
#   等价对照：
#     [x*2 if x>2 else 0 for x in data]   -> 每个元素，>2 则 *2 否则 0，长度不变
#     [x*2 for x in data if x>2]          -> 只保留 >2 的元素并 *2，长度变短
# 【执行顺序】
#   条件表达式在【表达式位置】，先算条件再选值，对每个元素都产出结果
#   条件筛选在【末尾】，条件为假的元素直接跳过，不进入表达式计算
# 【设计意图】
#   这是 Python 推导式最容易踩的坑，因为两者语法长得极像，
#   但一个改变长度、一个保持长度。
#   判断方法：看 if 后面【有没有 else】。
#     有 else -> 条件表达式（在表达式位），长度不变
#     无 else -> 筛选（在末尾），长度变短
def demo_if_confusion():
    print("[5] 高频易混淆：if 筛选 vs 条件表达式")

    data = [1, 2, 3, 4, 5, 6]

    # 条件表达式：if 在【开头】，有 else
    # 对每个元素：>3 则保留，否则变成 0（长度不变）
    cond_expr = [x if x > 3 else 0 for x in data]
    print(f"    [x if x>3 else 0 for x in data] = {cond_expr}   （三选一，长度 {len(cond_expr)} 不变）")
    print("       每个元素：>3 的保留原值，其余变 0")

    # 条件筛选：if 在【末尾】，无 else
    # 只保留 >3 的元素（长度变短）
    filter_only = [x for x in data if x > 3]
    print(f"    [x for x in data if x>3] = {filter_only}   （二选一，长度 {len(filter_only)} 变短）")
    print("       只保留满足条件的，其余丢弃")

    # 核心区别对照
    print(f"\n    [核心区别]")
    print(f"       条件表达式（有else）: {cond_expr}  长度 {len(cond_expr)}（与输入同长）")
    print(f"       条件筛选（无else）:   {filter_only}  长度 {len(filter_only)}（比输入短）")

    # 常见错误：用筛选语法想做条件表达式的事
    print("\n    [常见错误]")
    # 错误想法：想把 <=3 的变成 0
    # 错误写法：写成筛选 -> 长度变了
    wrong = [x if x > 3 else 0 for x in data]  # 这是对的
    # 假如误以为 if 在末尾，结果会丢掉 <=3 的元素
    # [x for x in data if x > 3 else 0] -> SyntaxError

    print(f"    正确：条件表达式 = {cond_expr}")
    # 对比：筛选 + 单独处理
    filtered_plus_zero = [x if x > 3 else 0 for x in data if True]
    print(f"    若强行组合 [x if x>3 else 0 for x in data if True] = {filtered_plus_zero}（多余）")

    # 在推导式里做三元 vs 用普通 if/else
    print("\n    [推导式三元 vs 普通 if/else]")
    # 推导式三元：所有元素都处理，满足条件的取 x，其他取默认值
    with_default = [x if x > 3 else "小" for x in data]
    print(f"    [x if x>3 else '小' for x in data] = {with_default}   （异质列表，混合类型）")

    # 在多层 for 中，if 的作用
    print("\n    [多层 for + 筛选组合]")
    # 两个列表，找出和为偶数的对
    a = [1, 2, 3]
    b = [1, 2, 3, 4]
    even_sums = [(x, y) for x in a for y in b if (x + y) % 2 == 0]
    print(f"    [(x,y) for x in [1,2,3] for y in [1,2,3,4] if (x+y)%2==0]")
    print(f"    = {even_sums}")
    print("    -> if 在最内层，筛选每一对组合")

    # 嵌套推导式中的 if 和三元
    print("\n    [嵌套推导式中两个位置]")
    nums = range(1, 6)
    # 外层用筛选（末尾 if），内层用条件表达式（开头 if...else）
    mixed = [[x if x > 2 else "*" for x in nums] if len(nums) > 0 else [] for _ in range(2)]
    print(f"    外层用筛选，内层用条件表达式 = {mixed}")

    # 判断口诀
    print("\n    [判断口诀]")
    print("       看 if 后面有没有 else：")
    print("         有 else -> 条件表达式（开头），长度不变，产出所有元素")
    print("         无 else -> 条件筛选（末尾），长度变短，丢弃不满足的元素")


# ============================================================================
# 语法解析 6：作用域、可读性边界与实战
# ============================================================================
# 【语法规则】
#   Python 3 中，列表/集合/字典推导式和生成器表达式都有【独立作用域】：
#     推导式内部定义的变量，外部【看不到】（对比 Python 2 会泄漏）
#   for 循环本身【没有】独立作用域，循环变量在外部依然可见
#   推导式可以引用外部作用域的变量（闭包）
# 【执行顺序】
#   推导式是一个表达式，在其【独立作用域】中求值：
#     - 目标变量和内部定义的变量只在该作用域内存在
#     - 外部变量可读（闭包）
#   这修复了 Python 2 中 `[i for i in range(3)]` 后 i 泄漏到外部的问题。
# 【设计意图】
#   推导式的独立作用域是 Python 3 的重要修正：
#     Python 2: [x for x in range(3)] 后 x 泄漏到外部（bug 来源）
#     Python 3: x 被限制在推导式内部
#   独立作用域避免了循环变量污染外部命名空间，也避免了并发/闭包问题。
def demo_scope_and_practice():
    print("[6] 作用域、可读性边界与实战")

    # 推导式的独立作用域：内部变量不泄漏
    print("    [作用域：推导式变量不泄漏]")
    i = "外部的i"
    squares = [i for i in range(3)]  # 推导式内部的 i
    print(f"    推导式 [i for i in range(3)] 内部用了 i")
    print(f"    推导式后外部 i = {i!r}   （没被覆盖！推导式有独立作用域）")
    print("    -> 对比 Python 2：推导式后的 i 会变成 2（最后一次迭代值），Python 3 修复了这个 bug")

    # 但 for 循环没有独立作用域
    print("\n    [对比：for 循环变量会泄漏]")
    j = 0
    for j in range(3):
        pass
    print(f"    for 循环后 j = {j}   （for 没有独立作用域，变量泄漏到外部）")
    print("    -> 推导式有作用域、for 没有，这是 Python 的一个不对称设计")

    # 推导式可以引用外部变量（闭包）
    print("\n    [闭包：推导式可以引用外部变量]")
    multiplier = 10
    scaled = [x * multiplier for x in range(3)]
    print(f"    multiplier={multiplier}, scaled=[x*multiplier for x in range(3)] = {scaled}")
    print("    -> 推导式能读到外部作用域的变量")

    # 可读性边界：什么时候不该用推导式
    print("\n    [可读性边界：何时停止使用推导式]")
    print("    PEP 8 与社区共识：推导式在【一层过滤+一层映射】时最清晰。")
    print("    出现以下情况应改用普通循环或提取函数：")
    print("      1. 需要 try/except（推导式里不能写 try）")
    print("      2. 有复杂的多步逻辑")
    print("      3. 嵌套超过 2 层")

    # 不能在推导式里用 try/except
    print("\n    [推导式不能包含 try/except]")
    data = ["1", "2", "abc", "4"]
    # 错误：不能在推导式里写 try
    # [int(x) for x in data] -> 遇到 "abc" 抛 ValueError，整个推导式失败

    # 正确：改用普通循环处理异常
    result_ok = []
    for x in data:
        try:
            result_ok.append(int(x))
        except ValueError:
            result_ok.append(None)  # 标记失败
    print(f"    普通循环+try = {result_ok}   （'abc' 变成 None，其余正常转 int）")

    # 也可以把转换逻辑提取成函数
    def safe_int(x):
        try:
            return int(x)
        except ValueError:
            return None
    result_func = [safe_int(x) for x in data]
    print(f"    提取函数+推导式 = {result_func}   （把异常逻辑封装到函数，推导式保持简洁）")
    print("    -> 这是化解'推导式不能写 try'的常用手法：把复杂逻辑藏进辅助函数")

    # 实战1：数据清洗管道
    print("\n    [实战1] 数据清洗管道（多层处理）")
    raw = ["  Alice  ", "bob", " CHARLIE ", "dave"]
    # 多步：strip -> title -> 长度>=3 过滤（写成管道式）
    cleaned = [name.strip().title() for name in raw if len(name.strip()) >= 3]
    print(f"    原始 = {raw}")
    print(f"    清洗后 = {cleaned}   （strip->title->过滤，链式表达清晰）")

    # 实战2：矩阵转置（用嵌套推导式）
    print("\n    [实战2] 矩阵转置")
    matrix = [[1, 2, 3], [4, 5, 6], [7, 8, 9]]
    transposed = [[matrix[i][j] for i in range(len(matrix))] for j in range(len(matrix[0]))]
    print(f"    原矩阵 = {matrix}")
    print(f"    转置 = {transposed}")
    # 更 Pythonic 的转置用 zip
    transposed_zip = [list(row) for row in zip(*matrix)]
    print(f"    zip 转置 = {transposed_zip}   （更简洁，推荐）")

    # 实战3：分组 + 聚合（字典推导式）
    print("\n    [实战3] 按首字母分组单词")
    words = ["apple", "avocado", "banana", "blueberry", "cherry"]
    grouped = {}
    for w in words:
        grouped.setdefault(w[0], []).append(w)
    print(f"    分组结果 = {grouped}")
    # 字典推导式版（需要先有分组集合）
    initials = {w[0] for w in words}
    grouped_comp = {i: [w for w in words if w[0] == i] for i in initials}
    print(f"    推导式版 = {grouped_comp}   （结果一致，但 O(n*m)，性能不如循环版）")
    print("    -> 教训：推导式虽简洁，但要考虑性能；分组这类场景循环+setdefault 更优")

    # 实战4：嵌套字典推导式
    print("\n    [实战4] 嵌套字典（学生->课程->成绩）")
    report = {
        "Alice": {"math": 95, "english": 88},
        "Bob": {"math": 78, "english": 92},
    }
    # 提取所有不及格的科目
    failed = {
        student: [subject for subject, score in scores.items() if score < 85]
        for student, scores in report.items()
    }
    print(f"    不及格科目 = {failed}   （嵌套字典推导式，逐层解构）")
    print(f"    有不及格的 = {[s for s, subs in failed.items() if subs]}")


# ============================================================================
# 语法解析 7：推导式 vs 循环 性能实测（timeit）
# ============================================================================
# 【语法规则】
#   timeit.timeit(stmt, setup, number, repeat)  测量执行耗时
#   对比原则：等价任务、相同数据、多次取最优
# 【执行顺序】
#   性能差异的来源：
#     列表推导式在字节码层面被优化（LIST_APPEND 替代方法调用），
#     比 for + append 的逐条 LOAD_METHOD/CALL 更高效。
#   但生成器表达式有惰性开销，全量消费时可能比列表推导慢。
# 【设计意图】
#   实测的意义在于建立"数量级直觉"：
#     推导式 vs 循环：约 1.1~1.3 倍，属微优化
#     真正的性能差距来自【算法复杂度】（O(n^2) vs O(n)），而非语法糖。
#   所以：先选对算法，再考虑语法糖。
def demo_performance():
    print("[7] 推导式 vs 循环 性能实测（timeit）")

    setup = "data = list(range(10000))"
    n = 200  # 200 * 10000 = 200万元素操作，秒级
    repeat = 3

    # 测试1：列表推导式 vs for+append
    print("    [测试1] 列表推导式 vs for+append（都产生相同结果）")
    t_append = min(timeit.repeat(
        "result = []\nfor x in data: result.append(x * 2)",
        setup=setup, number=n, repeat=repeat))
    t_comp = min(timeit.repeat(
        "result = [x * 2 for x in data]",
        setup=setup, number=n, repeat=repeat))
    print(f"      for+append  {t_append:.4f}s")
    print(f"      列表推导式   {t_comp:.4f}s   （快 {t_append/t_comp:.2f} 倍）")
    print("    -> 推导式的 LIST_APPEND 是字节码指令，比调用 list.append 方法更快")

    # 测试2：推导式 vs map
    print("\n    [测试2] 列表推导式 vs map")
    t_map = min(timeit.repeat(
        "result = list(map(lambda x: x*2, data))",
        setup=setup, number=n, repeat=repeat))
    print(f"      map+lambda  {t_map:.4f}s")
    print(f"      列表推导式   {t_comp:.4f}s")
    if t_comp < t_map:
        print(f"    -> 推导式快 {t_map/t_comp:.2f} 倍：map 要额外调用 lambda，函数调用有开销")
    else:
        print(f"    -> 本轮 map 略快，但差距在噪声内，不构成稳定结论")

    # 测试3：列表推导式 vs 生成器表达式（全量消费）
    print("\n    [测试3] 列表推导式 vs 生成器（全量转 list，公平对比）")
    t_list = min(timeit.repeat(
        "result = [x * 2 for x in data]",
        setup=setup, number=n, repeat=repeat))
    t_gen = min(timeit.repeat(
        "result = list(x * 2 for x in data)",
        setup=setup, number=n, repeat=repeat))
    print(f"      列表推导     {t_list:.4f}s")
    print(f"      生成器转list {t_gen:.4f}s   （{'快' if t_gen < t_list else '慢'} {abs(t_gen-t_list)/t_list*100:.0f}%）")
    print("    -> 全量消费时【生成器反而更慢】：它省内存，但要额外维护惰性迭代的挂起/恢复状态")
    print("    -> 结论：确定要全部结果且数据放得下内存 -> 用列表推导式；否则为省内存付出 1~1.5 倍时间是划算的")

    # 测试4：只消费少量时生成器的优势
    print("\n    [测试4] 只取前10个时：生成器的惰性优势")
    from itertools import islice
    # 注意：timeit 在独立命名空间里执行代码，setup 中导入的名称才可见，
    # 所以 islice 必须放进 setup，不能依赖本函数的局部导入。
    setup_islice = "from itertools import islice; data = list(range(10000))"
    t_list_partial = min(timeit.repeat(
        "[x for x in data][:10]",
        setup=setup_islice, number=n, repeat=repeat))
    t_gen_partial = min(timeit.repeat(
        "list(islice((x*2 for x in data), 10))",
        setup=setup_islice, number=n, repeat=repeat))
    print(f"      列表算完再取[:10] {t_list_partial:.4f}s   （要先算完1万个）")
    print(f"      生成器 islice(10) {t_gen_partial:.4f}s   （只算10个）")
    print(f"    -> 惰性优势明显：只要少量结果时，生成器省下了大量无用计算")

    # 测试5：真正的大差距来自算法复杂度（而非语法糖）
    print("\n    [测试5] 算法复杂度的差距远大于语法糖的差距")
    setup_n = "data = list(range(500))"
    # O(n^2)：双重循环找所有两数之和（无优化）
    t_o2 = min(timeit.repeat(
        "cnt = 0\nfor x in data:\n    for y in data:\n        cnt += 1",
        setup=setup_n, number=20, repeat=repeat))
    # O(n)：字典一次遍历做频次统计（核心技巧：用 dict 替代嵌套查找）
    t_on = min(timeit.repeat(
        "freq = {}\nfor x in data:\n    freq[x] = freq.get(x, 0) + 1",
        setup=setup_n, number=20, repeat=repeat))
    print(f"      O(n^2) 双重循环  {t_o2:.4f}s   （500^2=25万次）")
    print(f"      O(n) dict 计数   {t_on:.4f}s   （500次）")
    print(f"    -> 差距 {t_o2/t_on:.0f} 倍，这才是真正的性能优化（来自算法而非语法）")
    print("    -> 结论：先选对复杂度，再谈推导式 vs 循环这种微优化")


def main():
    demo_list_comprehension()
    demo_dict_comprehension()
    demo_set_comprehension()
    demo_generator_expression()
    demo_if_confusion()
    demo_scope_and_practice()
    demo_performance()
    print("[完成] 02_basics/06_comprehensions.py 运行结束")


if __name__ == "__main__":
    main()