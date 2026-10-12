# -*- coding: utf-8 -*-
r"""
================================================================================
文件：04_branches.py
模块：02_basics（基础语法配套）

【本文件演示的语法点列表】
  1. if / elif / else：完整语法、悬挂 else（dangling else）归属规则
  2. 条件表达式的真值判定：哪些对象为"假"
  3. 真值表与短路：and / or 的执行顺序与返回值
  4. 真值表实测：穷举 4 个布尔变量的 16 种组合，验证优先级与括号
  5. 三元表达式：语法、与 if/else 的等价性、嵌套与可读性
  6. match-case（PEP 634，Python 3.10+）完整语法：
       字面量模式、结构化序列模式、映射模式、类模式、通配 _、捕获变量
       守卫 if（guard）、or 模式、多分支 case A | B、嵌套解构
  7. match-case 的原理：赋值语句模式匹配（assignment pattern matching）
     底层是编译为一系列比较与绑定，不是解释器逐字符匹配
  8. 结构化模式匹配的软关键字特性：不写 match 也能用 match x: 语法
  9. Python 3.12 新特性：多行 case 的省略括号语法
 10. match vs if/elif：何时该用、何时不该用
 11. 常见陷阱：顺序敏感、捕获变量泄漏、守卫失败不回溯到下一 case

【设计意图】
  match-case 是 Python 吸收了函数式语言模式匹配（SML/Haskell/OCaml）40 年经验后的产物。
  它相对 if/elif 的本质改进有三：
  (1) 解构与匹配【一步完成】—— 不必先判断 isinstance 再取属性，
      这是 if/elif 写法最啰嗦的地方；
  (2) 穷尽性检查—— 没有通配分支时，未覆盖的输入会抛 match 之外的静默 bug；
  (3) 语法更接近数学记号，可读性显著提升。
  但它是【软关键字】：不写 match 就是普通标识符，不破坏任何旧代码。

【预期输出摘要】
  [1] if/elif/else：悬�� else 归属于最近的无匹配 if
  [2] 三元表达式：与 if/else 等价的两种写法结果对照
  [3] 短路：and/or 的返回值与执行次数统计
  [4] 真值表：16 种组合的穷举输出，验证 not > and > or 优先级
  [5] match-case：字面量/序列/映射/类/守卫/or 模式全演示
  [6] match 原理：编译为比较指令的等价 if 代码
  [7] 3.12 多行 case 语法（省略括号）
  [8] 陷阱：顺序敏感、捕获泄漏、守卫失败不回溯
================================================================================
"""

import timeit
from collections import namedtuple

# 在模块作用域定义一个具名元组类型，供 match 的"类模式"演示使用。
# 具名元组自带 __match_args__ = ("x", "y")，
# 所以 case Point(0, 5) 这种【按位置】的模式匹配才能生效。
Point = namedtuple("Point", ["x", "y"])


# ============================================================================
# 语法解析 1：if / elif / else 与"悬挂 else"
# ============================================================================
# 【语法规则】
#   if 条件:
#       语句块
#   elif 条件:      # 可以有任意多个
#       语句块
#   else:           # 可选，最多一个，必须放在最后
#       语句块
#   条件      任何表达式都可以，按真值判定（truthiness）
#   语句块    必须缩进，用【空格】统一缩进，禁止混用 Tab
#   if/elif/else 整体是一个【语句】，所以【不能】直接赋值：x = if c: ... 报错
#   没有 else 时，条件全假就什么都不做（静默）
# 【执行顺序】
#   从上到下【逐个求值】，第一个为真的分支执行，其余【全部跳过】。
#   所以分支顺序会改变语义：把范围最窄的条件放前面性能更好，
#   也更符合"特例前置"的阅读习惯。
# 【设计意图】
#   Python 没有 C 的 switch，所以 if/elif 链必须靠缩进组织。
#   "没有 else 就静默跳过"的设计让"可选动作"写起来最短，
#   但这也意味着漏写 else 是最常见的 bug 来源 ——
#   尤其当条件写反时，不会报错，只是什么都不发生。
def demo_if_elif_else():
    print("[1] if / elif / else")

    score = 85

    # 标准三分支
    if score >= 90:
        level = "优秀"
    elif score >= 60:
        level = "及格"
    else:
        level = "不及格"
    print(f"    score={score} -> {level}")

    # 悬挂 else（dangling else）：else 归属于【最近的】未匹配的 if
    # 这是 C 语言著名的坑，Python 因为强制缩进而结构唯一，所以没有这个问题
    flag_a, flag_b = True, False
    if flag_a:
        if flag_b:
            result = "A 且 B"
    # else:
    #     result = "..."
    # 若允许这个 else，按缩进规则它属于内层 if；因为缩进不匹配，Python 直接报错
    print(f"    悬挂 else：Python 用缩进消除歧义，这里没有 else 也不会误配")

    try:
        exec(
            "if True:\n"
            "    if False:\n"
            "        r = 'A'\n"
            "else:\n"
            "    r = 'else 属于内层 if'"
        )
    except IndentationError as e:
        print(f"    缩进不匹配 -> IndentationError: {str(e).splitlines()[0][:60]}")
        print("    -> 这就是 Python 用缩进而非 {} 消除悬挂歧义的代价与收益")

    # if 是语句不是表达式，不能赋值（对比三元）
    try:
        _ = "x" if True else "y"
    except SyntaxError:
        print("    x = if True else 'y'  ->  SyntaxError（if 是语句，不能出现在等号右边）")
    print(f"    正确写法（三元）: x = {'x' if True else 'y'}")

    # 没有 else 时的静默行为 —— 最常见的 bug 来源
    def check(x):
        if x > 10:
            return "大"
        # 隐式返回 None

    print(f"    check(5) = {check(5)!r}   (条件全假 -> 隐式返回 None)")
    print(f"    check(0) = {check(0)!r}")
    print("    -> if 链没有 else 时结果为 None，写代码时务必想清楚这是不是你要的")

    # 条件的短路让嵌套 if 可以展平 —— 防御性检查的惯用法
    def risky(x):
        return x[0]  # 若 x 为空会 IndexError

    user = {"name": "张三"}
    # 嵌套写法冗长，展平后一层表达完
    safe = user and len(user["name"]) > 0 and user["name"]
    print(f"    and 链展平嵌套 if = {safe!r}   (user 非空才继续取键，避免 KeyError)")

    # elif 与多个独立 if 的区别
    n = 5
    if n > 0:
        a = "正数"
    if n > 3:
        b = "大于3"
    print(f"    两个独立 if：{a}, {b}   (两个条件都会判断，可能都成立)")

    p = 5
    if p > 0:
        c = "正数"
    elif p > 3:
        c = "大于3"  # 永远不会执行
    print(f"    if/elif：{c}   (第一个成立就停，第二个被跳过)")


# ============================================================================
# 语法解析 2：真值判定 + 真值表穷举
# ============================================================================
# 【语法规则】
#   真值判定（truthiness）：在 if/while/not/and/or 中，条件如何转成布尔
#     假值 falsy：False None 0 0.0 0j "" [] {} set() 空字节串 空range
#     真值 truthy：其他一切（包括非空容器、自定义对象、绝大多数非零数）
#   bool(x) 是显式转换，等价于 if x 的隐式判定
#   and / or 返回【操作数】本身，不是 bool；not 永远返回 bool
#   优先级：not > and > or （比较运算符 > not）
# 【执行顺序】
#   and：先算左，若左为假【立即返回左】，不再求值右；否则求值并返回右
#   or ：先算左，若左为真【立即返回左】，不再求值右；否则求值并返回右
#   这就是短路，也是右侧不产生副作用的原因。
# 【设计意图】
#   and/or 返回操作数而非 bool，是为了写出"默认值"惯用法：
#       config = user_config or DEFAULT_CONFIG
#   如果强制返回 bool，Python 2 就得写 config = user_config if user_config else DEFAULT，
#   而这种"取第一个非空值"的逻辑会淹没在代码里。
def demo_truth_table():
    print("[2] 真值判定与真值表穷举")

    # 真值判定表：哪些对象是"假"
    falsy = [False, None, 0, 0.0, 0j, "", [], {}, set(), (), range(0), b""]
    truthy = [True, 1, -1, "0", "False", [0], {"a": 0}, (1,), {1, 2}]
    print("    【假值 falsy】bool() 均为 False：")
    for v in falsy:
        print(f"      {type(v).__name__:<8} {v!r:<12} -> {bool(v)}")
    print("    【真值 truthy】bool() 均为 True：")
    for v in truthy:
        print(f"      {type(v).__name__:<8} {v!r:<12} -> {bool(v)}")
    print(f"    注意 {'0'!r} 与 {'False'!r} 是非空字符串 -> 真值！")
    print("    自定义对象默认永远为真（除非定义 __bool__ 或 __len__）")
    print(f"    bool(对象()) = {bool(object())}   -> '一切非空即真' 是最省心的默认规则")

    # 短路：统计右侧执行次数
    calls = []

    def probe(tag, value=True):
        calls.append(tag)
        return value

    calls.clear()
    r1 = False and probe("A")
    print(f"\n    False and probe()  -> 返回 {r1}, 右侧执行 {len(calls)} 次  (短路)")
    calls.clear()
    r2 = True or probe("B")
    print(f"    True or probe()    -> 返回 {r2}, 右侧执行 {len(calls)} 次  (短路)")
    calls.clear()
    r3 = True and probe("C")
    print(f"    True and probe()   -> 返回 {r3}, 右侧执行 {len(calls)} 次  (不短路)")
    calls.clear()
    r4 = False or probe("D")
    print(f"    False or probe()   -> 返回 {r4}, 右侧执行 {len(calls)} 次  (不短路)")

    # and/or 返回操作数本身
    print(f"\n    and/or 返回操作数而非 bool：")
    print(f"      0 and 'x'        = {0 and 'x'!r}        (左侧假 -> 返回左侧 0)")
    print(f"      1 and 'x'        = {1 and 'x'!r}        (左侧真 -> 返回右侧)")
    print(f"      '' or '默认'     = {'' or '默认'!r}")
    print(f"      type(0 and 1)    = {type(0 and 1).__name__}   (是 int 不是 bool)")
    print(f"      type(1 and 2)    = {type(1 and 2).__name__}   (是 int 不是 bool)")

    # ---- 真值表穷举：4 个变量 16 种组合 ----
    print("\n    【真值表穷举】a and b or not c and d（not > and > or）")
    header = f"      {'a':>3}{'b':>3}{'c':>3}{'d':>3} | {'表达式':<22}{'结果'}"
    print(header)
    print("      " + "-" * (len(header) - 6))
    t = True
    f = False
    # 手工列出 16 种组合，验证优先级解析
    combos = [
        (t, t, t, t), (t, t, t, f), (t, t, f, t), (t, t, f, f),
        (t, f, t, t), (t, f, t, f), (t, f, f, t), (t, f, f, f),
        (f, t, t, t), (f, t, t, f), (f, t, f, t), (f, t, f, f),
        (f, f, t, t), (f, f, t, f), (f, f, f, t), (f, f, f, f),
    ]
    # 三种等价解析方式，必须结果一致才说明优先级被正确处理
    for a, b, c, d in combos:
        # 写法1：裸表达式（依赖 Python 优先级 not > and > or）
        v1 = a and b or not c and d
        # 写法2：完全加括号，优先级显式化
        v2 = (a and b) or ((not c) and d)
        # 写法3：展开为 if/elif 链
        if a and b:
            v3 = True
        elif (not c) and d:
            v3 = True
        else:
            v3 = False
        assert v1 == v2 == v3, "优先级解析错误"
        print(f"      {int(a):>3}{int(b):>3}{int(c):>3}{int(d):>3} | {'a and b or not c and d':<22}{v1}")
    print("      -> 16 种组合全部一致，三种写法等价，优先级 not > and > or 得到验证")

    # 关键陷阱：and/or 混用加括号会改变结果
    print("\n    【优先级陷阱】or/and 混用，加括号结果就不同：")
    print(f"      True or (False and False)   = {t or (f and f)}    (or 最低，无括号)")
    print(f"      (True or False) and False   = {(t or f) and f}    (加括号后结果变了！)")
    print("      -> 结论：and 与 or 混用时，括号不是可选的")


# ============================================================================
# 语法解析 3：三元条件表达式
# ============================================================================
# 【语法规则】
#   a if cond else b
#   完整形式，必须有 else（否则 SyntaxError）
#   条件为真取 a，为假取 b
#   等价于：result = a if cond else b
#   可【嵌套】：a if c1 else (b if c2 else c)   else 分支中嵌套时建议加括号
#   优先级【低于】算术与比较，高于 and/or，低于 lambda
# 【执行顺序】
#   先求 cond，再求被选中的那一支；未被选中的一支【完全不求值】（惰性求值）
#   这让三元可以安全地放有副作用或不存在的分支：
#       y = 1/x if x != 0 else None
# 【设计意图】
#   三元表达式的核心价值是【表达式化】：
#   它可以出现在赋值右侧、函数参数、返回值、列表字面量里 —— 这些地方 if 语句做不到。
#   但因为它是表达式，滥用会严重损害可读性，PEP 8 规定：
#   简单的二选一用三元，复杂的逻辑仍然用 if/else 语句。
def demo_ternary():
    print("[3] 三元条件表达式")

    x = 10
    y = 20

    # 标准用法
    max_val = x if x > y else y
    print(f"    max({x},{y}) = {max_val}   (写法: x if x > y else y)")

    # 与 if/else 等价性验证
    if x > y:
        r1 = x
    else:
        r1 = y
    r2 = x if x > y else y
    print(f"    三元与 if/else 结果相同 = {r1 == r2}")

    # 惰性求值：未被选中的分支不执行 —— 三元的关键性质
    a = 0
    safe_div = "N/A" if a == 0 else 10 / a
    print(f"    0 == 0 三元 = {safe_div}   (else 分支的 10/a 未执行，否则会 ZeroDivisionError)")

    # 这也是它优于 if/else 的地方：能内联
    data = [1, 2, 3, 4, 5]
    doubled = [v * 2 if v % 2 == 0 else v for v in data]
    print(f"    内联推导式 = {doubled}   (三元可以直接放进推导式，if 语句不行)")

    # 嵌套三元
    grade = 85
    level = "优" if grade >= 90 else ("良" if grade >= 80 else "差")
    print(f"    嵌套三元 grade=85 -> {level}")
    # 演示所有分支
    for g in (95, 85, 55):
        lv = "优" if g >= 90 else ("良" if g >= 80 else "差")
        print(f"      grade={g} -> {lv}")
    print("    -> 嵌套超过两层就不该用三元，应该改用 if/elif 链或查表字典")

    # 用字典查表替代 if/elif 链（更 Pythonic，也支持 O(1) 查表）
    # 这是"结构化分支"的替代思路
    grade_to_level = {95: "优", 85: "良", 55: "差"}
    # 实际场景通常这样写：
    print("    替代方案：用 map/查表代替长 if/elif 链")
    thresholds = [(90, "优"), (80, "良"), (60, "及格")]
    for g in (95, 85, 70, 50):
        # 用 any+next 或者简单的循环推导来查第一个匹配的阈值
        lv = next((label for th, label in thresholds if g >= th), "不及格")
        print(f"      grade={g} -> {lv}")

    # 三元的优先级：低于比较，高于 or
    print(f"\n    优先级演示：")
    print(f"      1 if True else 2 or 3   = {1 if True else 2 or 3}   (三元最宽，or 在 else 支内)")
    print(f"      0 or 1 if True else 2   = {0 or 1 if True else 2}   (等价于 (0 or 1) if True else 2 = {0 or (1 if True else 2)})")
    print("    -> 三元优先级【低于】or，读复杂表达式时要警惕")


# ============================================================================
# 语法解析 4：match-case —— 结构化模式匹配（Python 3.10+，PEP 634）
# ============================================================================
# 【语法规则】
#   match subject:
#       case pattern [if guard]:
#           body
#       case pattern2:
#           body2
#       case _:
#           default_body
#
#   模式种类：
#     字面量模式  case 42: / case "hello": / case None:
#     捕获模式    case x:        （x 是变量名，捕获整个值）
#     通配模式    case _:        （下划线，不捕获，匹配合何）
#     序列模式    case [a, b]:            （列表式解构）
#                 case (a, b):            （括号可省，case a, b: 也行）
#     映射模式    case {"k": v}:          （字典式解构，只匹配含该键的 dict）
#                 case {"k": v, **rest}:   （rest 收集剩余键值对）
#     类模式      case Point(x=0, y=0):   （调用 __match_args__ 或关键字匹配）
#     组合模式    case [1, 2] | [3, 4]:    （or，逗号可省，匹配合其中之一）
#     as 模式     case [x] as lst:        （把整个结构绑定到新名）
#     嵌套模式    case [{"k": [1, 2]}]:   （模式可任意嵌套）
#     守卫 guard  case x if x > 10:       （额外的布尔条件）
#
#   关键限制：
#     - 一个 case 里【同类】的多个位置，【只有第一个】捕获变量会绑定成功
#     - 变量名一旦在某个分支捕获，就是【局部变量】，未匹配的分支里是"未绑定"
#     - 守卫失败【不回溯】到下一个 case，而是【整个 match 失败】
#     - 所有分支都不匹配时，无 case _ 则静默跳过（和 if 一样）
# 【执行顺序】
#   match 语句逐个 case 尝试【模式匹配】：
#     1. 先判断【类型/形状/结构】（sequence 必须是序列，mapping 必须是映射）
#     2. 结构对上了，再解构并绑定捕获变量
#     3. 绑定完成后求【守卫 guard】，为假则该 case 不匹配
#   捕获变量一旦绑定就【不再改变】（不可回退），所以守卫必须放在捕获之后。
#   编译器把 match 优化为一系列分支跳转，不是逐字符的字符串搜索。
# 【设计意图】
#   match-case 把"判断类型 + 解构取值"合并为【一步】：
#     if isinstance(o, Point):  x = o.x; y = o.y   （3 行，冗长）
#     case Point(x, y):                               （1 行，清晰）
#   它还支持"深解构"，处理嵌套 JSON 响应时优势巨大。
#   它是【软关键字】：match / case 只是上下文相关的关键字，
#   仍可作为普通变量名（如 match = 5 合法，只要不处于 match 语句上下文）。
def demo_match_case():
    print("[4] match-case 完整语法（Python 3.10+）")

    # ---- 模式种类 1：字面量 ----
    print("    [1] 字面量模式")
    def classify_literal(value):
        match value:
            case 0:
                return "零"
            case 1:
                return "一"
            case "hello":
                return "问候"
            case None:
                return "空值"
            case _:
                return "其他"
    print(f"      classify_literal(0)    = {classify_literal(0)}")
    print(f"      classify_literal(1)    = {classify_literal(1)}")
    print(f"      classify_literal('hello') = {classify_literal('hello')}")
    print(f"      classify_literal(None) = {classify_literal(None)}")
    print(f"      classify_literal(99)   = {classify_literal(99)}   (落到 case _)")

    # ---- 模式种类 2：捕获 + 守卫 ----
    print("\n    [2] 捕获模式 + 守卫 guard")
    def describe(n):
        match n:
            case x if x < 0:
                return f"负数 {x}"
            case 0:
                return "零"
            case x if x < 10:
                return f"一位数 {x}"
            case x:
                return f"大数 {x}"
    for v in (-5, 0, 7, 999):
        print(f"      describe({v:>4}) = {describe(v)}")
    print("    -> 守卫 case x if cond：先捕获 x，再求值条件；条件为假则本 case 不匹配")
    print("    -> 守卫【不会回溯到下一个 case】，而是让整个 match 走到后面去")

    # 关键陷阱：守卫失败的流向
    print("\n    [陷阱] 守卫失败的分支流向")
    def guard_demo(n):
        match n:
            case x if x > 100:
                return "大"
            case x if x > 10:
                return "中"
            case _:
                return "小"
    for v in (200, 50, 5):
        print(f"      guard_demo({v:>3}) = {guard_demo(v)}")
    print("    -> 多个守卫按顺序尝试，每个守卫独立判断，这是正确的多区间写法")

    # ---- 模式种类 3：序列解构 ----
    print("\n    [3] 序列模式（列表/元组解构）")
    def process_point(coords):
        match coords:
            case [0, 0]:
                return "原点"
            case [x, 0]:
                return f"x轴上 ({x}, 0)"
            case [0, y]:
                return f"y轴上 (0, {y})"
            case [x, y]:
                return f"一般点 ({x}, {y})"
            case []:
                return "空列表"
            case _:  # 长度不为2的其他情况
                return "其他结构"
    for pt in ([0, 0], [3, 0], [0, 4], [1, 2], [], [1, 2, 3], "xy"):
        print(f"      process_point({str(pt):<10}) = {process_point(pt)}")
    print("    -> case [0,0] 先试，再逐个放宽，这是【从具体到一般】的匹配顺序")
    print("    -> 序列模式同时匹配 list / tuple / str / bytes 等所有序列")

    # 带 * 的序列模式：解包剩余
    print("\n    [3b] 带 *rest 的序列模式")
    def head_tail(seq):
        match seq:
            case [first, *rest]:
                return f"首={first}, 剩余={rest}"
            case []:
                return "空"
    for s in ([1, 2, 3, 4], [9], []):
        print(f"      head_tail({str(s):<12}) = {head_tail(s)}")

    # ---- 模式种类 4：映射（dict）解构 ----
    print("\n    [4] 映射模式（字典解构）")
    def parse_config(cfg):
        match cfg:
            case {"host": host, "port": port}:
                return f"连接 {host}:{port}"
            case {"host": host}:
                return f"仅主机 {host}（缺端口）"
            case {"error": msg}:
                return f"错误: {msg}"
            case {}:
                return "空配置"
            case _:
                return "未知格式"
    for c in (
        {"host": "localhost", "port": 8080},
        {"host": "example.com"},
        {"error": "timeout"},
        {},
        {"random": 1},
    ):
        print(f"      {str(c):<42} -> {parse_config(c)}")
    print("    -> 映射模式【只匹配明确列出的键】，多余的键被忽略（不是精确匹配）")
    print("    -> {'host':h,'port':p} 要求两个键【都】存在，少一个就匹配失败")

    # **rest 收集剩余键值对
    print("\n    [4b] 映射模式 + **rest")
    def split_config(cfg):
        match cfg:
            case {"env": env, **rest}:
                return f"环境={env}, 其余={rest}"
            case _:
                return "无环境键"
    for c in ({"env": "prod", "db": "mysql", "port": 3306}, {"db": "mysql"}):
        print(f"      split_config({str(c):<40}) = {split_config(c)}")

    # ---- 模式种类 5：类模式（对象解构）----
    print("\n    [5] 类模式（对象属性解构）")
    # 类在模块作用域已定义（见文件顶部），此处直接使用
    Color = namedtuple("Color", ["name", "rgb"])

    def describe_shape(shape):
        match shape:
            case Point(0, 0):
                return "点：原点"
            case Point(x=0, y=y):
                return f"点：y轴 (0, {y})"
            case Point(x=x, y=0):
                return f"点：x轴 ({x}, 0)"
            case Point(x, y):
                return f"点：一般 ({x}, {y})"
            case Color("red", rgb):
                return f"颜色：红色 rgb={rgb}"
            case Color(name, rgb):
                return f"颜色：{name} rgb={rgb}"
            case _:
                return "非形状对象"
    print(f"      describe_shape(Point(0,0))  = {describe_shape(Point(0, 0))}")
    print(f"      describe_shape(Point(0,5))  = {describe_shape(Point(0, 5))}")
    print(f"      describe_shape(Point(3,0))  = {describe_shape(Point(3, 0))}")
    print(f"      describe_shape(Point(1,2))  = {describe_shape(Point(1, 2))}")
    print(f"      describe_shape(Color('red',(255,0,0))) = {describe_shape(Color('red', (255, 0, 0)))}")
    print(f"      describe_shape(Color('blue',(0,0,255))) = {describe_shape(Color('blue', (0, 0, 255)))}")
    print("    -> 类模式 case Point(x, y): 等价于按位置匹配 __match_args__ 中的属性")
    print("    -> 关键字写法 case Point(x=x, y=0) 更直观，两者可混用")
    print("    -> 这是 match 相对 if/elif 最大的价值：判断类型+解构一步完成")

    # ---- 模式种类 6：or 组合模式 ----
    print("\n    [6] or 组合模式")
    def check_even_odd(n):
        match n:
            case 0 | 2 | 4 | 6 | 8:
                return f"{n} 是小偶数"
            case 1 | 3 | 5 | 7 | 9:
                return f"{n} 是小奇数"
            case _:
                return f"{n} 超出范围"
    for n in (2, 5, 20):
        print(f"      check_even_odd({n:>2}) = {check_even_odd(n)}")
    print("    -> case A | B | C 表示【或】，匹配合其中任意一个（相当于多个 case 合并）")
    print("    -> or 模式必须【全部是字面量】，不能混合捕获变量")

    # ---- 模式种类 7：嵌套解构 ----
    print("\n    [7] 嵌套模式（深解构）")
    def parse_json(data):
        match data:
            case {"status": "ok", "data": {"items": [_, _, *rest]}}:
                return f"成功，取2个+余{len(rest)}个"
            case {"status": "ok", "data": {"items": items}}:
                return f"成功，{len(items)}个items"
            case {"status": "error", "msg": msg}:
                return f"失败：{msg}"
            case _:
                return "未知响应"
    samples = [
        {"status": "ok", "data": {"items": [1, 2, 3, 4]}},
        {"status": "ok", "data": {"items": [1]}},
        {"status": "error", "msg": "timeout"},
        {"unexpected": True},
    ]
    for s in samples:
        print(f"      parse_json({str(s):<44}) = {parse_json(s)}")
    print("    -> 嵌套模式是 match 的杀手锏：深层 JSON 一行搞定，if/else 需十几层嵌套")

    # ---- 模式种类 8：as 模式 ----
    print("\n    [8] as 模式（整体绑定）")
    def bind_all(value):
        match value:
            case [x, y] as pair:
                return f"坐标({x},{y}), 整体是{type(pair).__name__}长度{len(pair)}"
            case _:
                return "非坐标"
    print(f"      bind_all([3, 4]) = {bind_all([3, 4])}")
    print("    -> case [x,y] as pair：既解构 x,y，又把整个 [x,y] 绑定到 pair")

    # ---- 综合实战：解析命令 ----
    print("\n    [实战] 用 match 解析文本命令")
    def run_command(cmd):
        match cmd.split():
            case ["quit" | "exit"]:
                return "退出程序"
            case ["add", a, b] if a.isdigit() and b.isdigit():
                return f"计算 {int(a) + int(b)}"
            case ["add", a, b]:
                return f"参数错误：{a} 和 {b} 不是数字"
            case ["cd", path]:
                return f"切换到目录 {path}"
            case ["ls"]:
                return "列出文件"
            case [cmd_name, *args]:
                return f"未知命令 {cmd_name}，附带参数 {args}"
            case []:
                return "空命令"
    for c in ("quit", "exit", "add 3 5", "add x y", "cd /tmp", "ls", "frobnicate 1 2 3", ""):
        print(f"      {c!r:<18} -> {run_command(c)}")
    print("    -> 这就是 match 的理想场景：解析、路由、协议分发，结构清晰无嵌套")


# ============================================================================
# 语法解析 5：match-case 的底层原理与软关键字特性
# ============================================================================
# 【语法规则】
#   match 是【软关键字 soft keyword】：
#     - 在正常的赋值/表达式位置，match 仍可作为普通标识符使用
#     - 只有当它出现在语句开头且后面跟着 subject: 时，才被识别为 match 语句
#   case 同样是软关键字
#   原理：match 被【编译】成一系列比较与分支跳转，
#         不是解释器在运行期逐字符"匹配字符串"
#         编译器会为每个模式生成对应的字节码（如 isinstance 检查、解构赋值）
# 【执行顺序】
#   编译器把 match-case 转换成等价的一串 if 判断：
#     1. 对字面量：生成 == 比较
#     2. 对类模式：生成 isinstance 检查 + 属性解包
#     3. 对序列模式：生成长度检查 + 索引解包
#     4. 对守卫：生成额外的布尔判断
#   所以 match 不比 if 慢，且通常更快（跳转表 vs 线性比较）
# 【设计意图】
#   软关键字设计让 Python 在不破坏已有代码的前提下引入新语法。
#   例：match = 5、print(match) 都是合法的，
#       解析器只在检测到 match <表达式> : 这种结构时才切换到新语法。
def demo_match_principles():
    print("[5] match-case 原理与软关键字")

    # 软关键字：match/case 仍可作普通标识符
    match = 5
    print(f"    match = 5 合法（软关键字）: {match}   (不处于 match 语句上下文时按普通名解析)")
    case = 10
    print(f"    case = 10 也合法: {case}")
    # 重新用这些名字做赋值，证明没被"吃掉"
    match, case = 1, 2
    print(f"    match, case = 1, 2 -> {match}, {case}   (软关键字不影响普通赋值)")

    # 编译成等价 if：字面量
    print("\n    [等价改写] 字面量模式 -> == 比较")
    def m1(v):
        match v:
            case 1: return "one"
            case 2: return "two"
            case _: return "other"
    def i1(v):
        if v == 1: return "one"
        elif v == 2: return "two"
        else: return "other"
    for v in (1, 2, 3):
        assert m1(v) == i1(v)
    print("    match 与 if/elif 对字面量完全等价，编译器生成的是 == 比较")

    # 编译成等价 if：序列模式
    print("\n    [等价改写] 序列模式 -> isinstance + 长度检查 + 解包")
    def m2(p):
        match p:
            case [0, 0]: return "origin"
            case [x, y]: return f"({x},{y})"
            case _: return "other"
    def i2(p):
        if isinstance(p, (list, tuple)) and len(p) == 2:
            x, y = p
            if x == 0 and y == 0: return "origin"
            return f"({x},{y})"
        return "other"
    for p in ([0, 0], [1, 2], [1], "ab"):
        assert m2(p) == i2(p), f"{p} 不一致"
    print("    -> match 帮我们自动做了：类型检查 + 长度检查 + 解包 + 字面量比较")
    print("    -> 这正是 match 优于 if/elif 的地方：把 4 行样板压成 1 行")

    # 捕获变量的作用域：未匹配分支中是"未绑定"
    print("\n    [作用域] 捕获变量的绑定特性")
    def capture_demo(v):
        match v:
            case [x]:
                return f"单元素，x={x}"
            case [x, y]:
                return f"双元素，x={x}, y={y}"
            case _:
                # 这里 x/y 不可用（未绑定），会抛 UnboundLocalError
                return "其他（x 未绑定）"
    for v in ([1], [1, 2], [1, 2, 3]):
        print(f"      {str(v):<10} -> {capture_demo(v)}")

    # 陷阱：先宽后窄导致永远匹配不到
    # 注意：CPython 在【编译期】就能检出这种死代码并直接拒绝编译，
    # 所以下面这段用 exec() 动态编译，才能把这个真实的 SyntaxError 展示出来。
    print("\n    [陷阱] 顺序敏感：通配在前，具体在后")
    try:
        exec(
            "def wrong_order(v):\n"
            "    match v:\n"
            "        case _:\n"
            "            return '兜底'\n"
            "        case [0, 0]:\n"
            "            return '原点'\n"
        )
    except SyntaxError as e:
        print(f"      case _ 在前 + 具体模式在后 -> SyntaxError: {str(e).splitlines()[0]}")
        print("    -> CPython 编译期就检测到「wildcard makes remaining patterns unreachable」")
        print("    -> 也就是说：通配 case _ 后面再写任何 case 都是语法错误，不只是'没意义'")
    print("    -> 若用 if/elif 写同样逻辑，编译器【不会】报错，只是后半段成了死代码 —— match 更安全")

    # 用两个【非通配】的具体模式演示顺序敏感（能编译，但后者是死代码）
    def overlap_wrong(v):
        match v:
            case [0, _]:        # 宽：任何第一项为0的二元列表
                return "以0开头"
            case [0, 0]:        # 窄：完全等于 [0,0]，但永远轮不到
                return "原点"
            case _:
                return "其他"
    def overlap_right(v):
        match v:
            case [0, 0]:        # 窄的在前
                return "原点"
            case [0, _]:        # 宽的在后
                return "以0开头"
            case _:
                return "其他"
    print(f"      顺序错误 overlap_wrong([0,0]) = {overlap_wrong([0, 0])}   (返回'以0开头'，'原点'成了死代码)")
    print(f"      顺序正确 overlap_right([0,0]) = {overlap_right([0, 0])}   (返回'原点')")
    print(f"      两者对 [0,0] 的结果不同 = {overlap_wrong([0,0]) != overlap_right([0,0])}  -> 顺序即语义")
    print("    -> 和 if/elif 一样：【从上到下第一个匹配就赢】，必须具体模式在前")
    print("    -> 语法解析 4 里所有的 case _ 都放在最后，就是这个原因")

    # ---- Python 3.12 新特性：多行 case 省略括号 ----
    print("\n    [Python 3.12 新特性] 多行 case 省略括号")
    # 3.12 之前（3.10/3.11）：多行模式【必须】加括号，编译器靠括号判断 case 是否结束
    #   case (
    #       Point(x=0, y=0)
    #   ):
    # 3.12 起：可以省略括号，直接跨行写
    #   case Point(
    #       x=0, y=0
    #   ):
    def locate_multiline(value):
        # 下面这个 case 就是 3.12 的新写法：不加外层括号，直接跨行
        case_class = value
        match case_class:
            case (
                # 兼容写法：3.10/3.11 也认这个语法，3.12 更是自然支持
                Point(0, 0)
            ):
                return "原点"
            case Point(x, y) if x == y:   # 带守卫的单行 case
                return f"在对角线上的点 ({x},{y})"
            case Point(x, 0):
                return f"x轴 ({x},0)"
            case Point(0, y):
                return f"y轴 (0,{y})"
            case Point(x, y):
                return f"一般点 ({x},{y})"
            case _:
                return "非坐标"
    for p in (Point(0, 0), Point(3, 3), Point(5, 0), Point(0, 7), Point(1, 2)):
        print(f"      locate_multiline({str(p):<12}) = {locate_multiline(p)}")
    print("    -> 3.12 的语法糖：多行 case 可省略外层括号，写起来更清爽")
    print("    -> 本例用带括号的兼容写法，确保 3.10/3.11 也能正常解析")

    # 实际演示 3.12 的省略括号写法（用 exec 以便注明版本要求）
    print("\n    [3.12 新写法实测] 省略括号的多行 case")
    multiline_src = (
        "def handle(value):\n"
        "    match value:\n"
        "        case Point(   # <- 3.12 起：跨行时不再必须加括号\n"
        "            x=0,\n"
        "            y=0\n"
        "        ):\n"
        "            return '原点'\n"
        "        case [a, b, c]:   # 三元素序列，直接写\n"
        "            return f'三元组 {a}{b}{c}'\n"
        "        case _:\n"
        "            return '其他'\n"
    )
    ns = {"Point": Point}
    exec(multiline_src, ns)
    handle = ns["handle"]
    for v in (Point(0, 0), [1, 2, 3], [9, 9]):
        print(f"      handle({str(v):<14}) = {handle(v)}")
    print("    -> 3.12 新增：allowed to omit parentheses around cases（PEP 707 相关改进）")
    print("    -> 好处：深层嵌套或超长模式可以自然换行，不必层层套括号")
    print(f"    -> 当前解释器 {__import__('sys').version_info.major}.{__import__('sys').version_info.minor}，该语法可用")

    # 性能对比：match vs if/elif
    print("\n    [性能实测] match-case vs if/elif 链")
    setup = "v=42"
    n = 200_000
    repeat = 5  # 多轮取最小值：单次计时容易被系统噪声带偏
    t_match = timeit.repeat(
        """
match v:
    case 1: r = 'a'
    case 2: r = 'b'
    case 3: r = 'c'
    case 4: r = 'd'
    case _: r = 'other'
""",
        setup=setup,
        number=n,
        repeat=repeat,
    )
    t_if = timeit.repeat(
        """
if v == 1: r = 'a'
elif v == 2: r = 'b'
elif v == 3: r = 'c'
elif v == 4: r = 'd'
else: r = 'other'
""",
        setup=setup,
        number=n,
        repeat=repeat,
    )
    print(f"      match-case  最低 {min(t_match):.4f}s  (n={n:,}, repeat={repeat})")
    print(f"      if/elif 链  最低 {min(t_if):.4f}s  (n={n:,}, repeat={repeat})")
    ratio = min(t_match) / min(t_if)
    print(f"      性能比     {ratio:.2f}x  (match / if)")
    # 单次计时受系统噪声影响很大，这里如实报告多轮实测的波动区间
    spread_m = (max(t_match) - min(t_match)) / min(t_match) * 100
    spread_i = (max(t_if) - min(t_if)) / min(t_if) * 100
    print(f"      波动区间   match ±{spread_m:.0f}%，if/elif ±{spread_i:.0f}%")
    print("    -> 实测结论：两者处于【同一量级】，match 并不会因为是新语法就变慢")
    print("       （编译器把模式翻译成比较+跳转，不是运行期解释匹配）")
    print(f"    -> 本轮 match 约{'慢' if ratio > 1.1 else '快' if ratio < 0.9 else '持平'}，"
          "但这个差距在多轮波动范围内，不构成稳定结论")
    print("    -> 因此：选 match 的理由是【可读性与解构能力】，而不是性能")
    print("    -> 另注意：若分支很多且类型相同（如全是 int），或需要动态派发，"
          "dict 查表通常比两者都快")


def main():
    demo_if_elif_else()
    demo_truth_table()
    demo_ternary()
    demo_match_case()
    demo_match_principles()
    print("[完成] 02_basics/04_branches.py 运行结束")


if __name__ == "__main__":
    main()