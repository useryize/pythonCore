# -*- coding: utf-8 -*-
"""
================================================================================
文件：02_operators.py
模块：02_basics（基础语法配套）

【本文件演示的语法点列表】
  1. 算术运算符：+ - * / // % **，含整除与浮点的差异、负数取模的方向
  2. 赋值运算符：= += -= *= /= //= %= **= &= |= ^= >>= <<= 及其"原地修改"语义
  3. 比较运算符：== != > < >= <=，含链式比较（Python 独有特性）
  4. 逻辑运算符：and / or / not，返回值【不是】布尔而是操作数本身
  5. 位运算符：& | ^ ~ << >>，异或交换两数技巧
  6. 成员运算符：in / not in，含"容器 vs 字符串"语义差异
  7. 身份运算符：is / is not
  8. 三元条件表达式与运算符优先级陷阱
  9. 运算符优先级与结合性的完整实测（用表达式求值验证）

【设计意图】
  Python 的运算符设计有两个显著特征：
  (1) 运算符【重载】由类型自己定义 —— int 的 + 和 str 的 + 是两套完全不同的代码；
  (2) 逻辑运算符沿用 C 的短路语义，返回操作数而非 bool，使"默认参数"等惯用法成为可能。
  理解这两点，就理解了 Python 运算符与 C 的根本差异。

【预期输出摘要】
  [1] 算术运算：/ 永远返回 float，// 向下取整（不是向零截断！）
  [2] 赋值运算符：+= 对 list 是原地追加，对 int 是新建
  [3] 比较与链式比较：1 < x < 10 在 Python 中是合法语法
  [4] 逻辑运算：and/or 返回操作数本身（短路演示）
  [5] 位运算：异或交换、正负数移位的陷阱
  [6] 成员与身份运算：'a' in 'abc' 为 True 但 1 in 'abc' 抛 TypeError
  [7] 优先级陷阱：`not a == b` 实际是 `not (a == b)`
  [8] 优先级完整实测表
================================================================================
"""


# ============================================================================
# 语法解析 1：算术运算符
# ============================================================================
# 【语法规则】
#   a + b   加法（对 str 是拼接，对 list 是合并）
#   a - b   减法（对 set 是差集）
#   a * b   乘法（对 str/list 是重复，对两个 int 相乘是积）
#   a / b   真除法，【永远返回 float】，除零抛 ZeroDivisionError
#   a // b  向下取整除法，向【负无穷】取整（与 C 的向零截断不同！）
#   a % b   取模，结果符号【跟随除数】，这是 Python 与 C 的显著差异
#   a ** b  幂运算，右结合，且优先级高于一元负号
#   @       矩阵乘法（PEP 465），需自定义 __matmul__
# 【执行顺序】
#   运算符由操作数的类型决定实际执行哪段代码（重载机制）。
#   例如 2 + 3 调用 int.__add__，"a" + "b" 调用 str.__add__，二者代码不同。
# 【设计意图】
#   除法永远返回 float，是为了避免 C 中整数除法"5/2==2"造成的静默数据丢失，
#   Python 选择用类型系统阻止这类错误发生。
#   而 // 的存在正是为了在需要整数运算时明确表达意图。
def demo_arithmetic():
    print("[1] 算术运算符")

    a, b = 17, 5
    print(f"    {a} + {b}  = {a + b}")
    print(f"    {a} - {b}  = {a - b}")
    print(f"    {a} * {b}  = {a * b}")
    print(f"    {a} / {b}  = {a / b}   <- float，真除法")

    # 向下取整 vs 向零截断：C 中 -7/2 == -3（向零），Python 是 -4（向下）
    # 理由是数学上的"下取整"配合 % 的余数语义才能保证恒等式 a == (a//b)*b + a%b
    print(f"    {a} // {b} = {a // b}")
    print(f"    {a} % {b}  = {a % b}")

    neg_a, neg_b = -17, 5
    print(f"    {neg_a} // {neg_b} = {neg_a // neg_b}  <- 向下取整，不是向零截断(C 会得 -3)")
    print(f"    {neg_a} % {neg_b}  = {neg_a % neg_b}   <- 余数符号跟随除数(C 会得 -2)")
    print(f"    {neg_a} // {-neg_b} = {neg_a // -neg_b}, {neg_a} % {-neg_b} = {neg_a % -neg_b}")

    # 验证恒等式：a == (a // b) * b + a % b  在两个数异号时也成立
    assert neg_a == (neg_a // neg_b) * neg_b + neg_a % neg_b
    print("    恒等式 a == (a//b)*b + a%b 在异号时仍成立（Python 取模设计的核心原因）")

    # 幂运算：右结合 2**3**2 == 2**(3**2)
    print(f"    2 ** 3 ** 2 = {2 ** 3 ** 2}  <- 右结合，等于 2**(3**2) = {2 ** (3 ** 2)}")
    print(f"    2 ** 3      = {2 ** 3}")

    # 一元负号与幂的优先级陷阱：-(2**2) = -4，但 (-2)**2 = 4
    print(f"    -2 ** 2      = {-2 ** 2}      <- 幂优先于一元负号，等于 -(2**2)")
    print(f"    (-2) ** 2    = {(-2) ** 2}")

    # 除零错误
    try:
        _ = 1 / 0
    except ZeroDivisionError as e:
        print(f"    1 / 0  ->  ZeroDivisionError: {e}")
    try:
        _ = 1 // 0
    except ZeroDivisionError:
        print("    1 // 0 ->  ZeroDivisionError（整数除零不返回浮点inf）")

    # 运算符对不同类型的语义复用：同一个符号，服务多种类型
    print(f"    'ab' * 3        = {'ab' * 3}       (str 重复)")
    print(f"    [0] * 3         = {[0] * 3}        (list 重复，注意元素是【同一个对象】)")
    # 这个陷阱很实际：[0]*3 里的三个 0 是同一对象，修改一个会影响全部
    zeros = [0] * 3
    zeros[0] = 9
    print(f"    [0]*3 后改第0位 = {zeros}  -> 赋值替换不体现；要原地改才会共享")
    inner = [[0]]
    shared = inner * 3
    shared[0].append(1)
    print(f"    [[0]]*3 原地修改 = {shared}  <- 真正的别名陷阱")

    print(f"    'ab' + 'cd'     = {'ab' + 'cd'}      (str 拼接)")
    print(f"    [1] + [2]       = {[1] + [2]}        (list 合并，新建对象)")
    print(f"    {{1}} - {{2}}    = {{1}} - {{2}}          (set 差集)")


# ============================================================================
# 语法解析 2：赋值运算符 —— "原地修改"的真相
# ============================================================================
# 【语法规则】
#   x += 1     等价于 x = x + 1，但不是简单的语法糖
#   x *= 2     等价于 x = x * 2
#   += 可用于所有实现了 __iadd__ 的类型；没有实现时回退到 __add__
# 【执行顺序】
#   对可变对象，x += 1 调用 __iadd__，【原地修改】 x 并返回同一对象
#   对不可变对象（int/str/tuple），__iadd__ 不存在，回退到 __add__，
#   生成新对象后重新绑定名字。
#   这个差异导致：+= 对 list 是"修改"，对 tuple 是"重建"。
# 【设计意图】
#   提供 __iadd__ 让高频的"追加/累加"操作避免反复创建对象，
#   对大数据量的循环有显著性能收益。
def demo_assignment_operators():
    print("[2] 赋值运算符")

    n = 10
    n += 5
    n -= 3
    n *= 2
    n //= 4
    n **= 2
    print(f"    连续赋值运算后 n = {n}")

    # int 没有 __iadd__，每次 += 都是新建对象
    val = 1
    before = id(val)
    val += 1
    print(f"    int += 1 后 id 变化 = {id(val) != before}  (不可变 -> 只能新建)")

    # list 有 __iadd__，+= 是真正的原地追加
    lst = [1]
    before_list = id(lst)
    lst += [2, 3]
    print(f"    list += 后 id 不变 = {id(lst) == before_list}, 内容 = {lst}  (可变 -> 原地)")

    # 元组是不可变的，+= 产生新对象
    tup = (1,)
    before_tup = id(tup)
    tup += (2,)
    print(f"    tuple += 后 id 变化 = {id(tup) != before_tup}, 值 = {tup}")

    # 位运算的复合赋值
    flags = 0b1010
    flags &= 0b0110  # 按位与：保留公共位
    print(f"    0b1010 &= 0b0110 = {flags:#06b}")
    flags |= 0b0001  # 按位或：置位
    print(f"    |= 0b0001         = {flags:#06b}")
    flags ^= 0b1111  # 按位异或：翻转
    print(f"    ^= 0b1111         = {flags:#06b}")
    flags <<= 2  # 左移：乘以 4
    print(f"    <<= 2             = {flags:#06b} ({flags})")
    flags >>= 1  # 右移：整除 2
    print(f"    >>= 1             = {flags:#06b} ({flags})")


# ============================================================================
# 语法解析 3：比较运算符与链式比较
# ============================================================================
# 【语法规则】
#   a == b   相等；a != b   不等
#   a <  b   小于；a <= b   小于等于；a > b   大于；a >= b   大于等于
#   a < b < c    【链式比较】，等价于 (a < b) and (b < c)，只求值一次 b
# 【执行顺序】
#   链式比较由编译器转换为：先算 b 存临时变量，再依次比较。
#   因此 b 只会被求值一次 —— 这正是它比 and 更优的地方。
# 【设计意图】
#   链式比较直接对应数学记号 x ≤ y ≤ z，无需把 y 写两遍。
#   更重要的是避免了 `x <= y and y <= z` 中 y 是复杂表达式时的重复计算与
#   两次调用之间状态可能变化的问题。
def demo_comparison():
    print("[3] 比较运算符与链式比较")

    a, b, c = 1, 5, 10
    print(f"    {a} < {b} < {c}  = {a < b < c}   (链式比较，合法语法)")
    print(f"    {c} < {b} < {a}  = {c < b < a}")

    # 证明中间值只求值一次
    call_count = []

    def middle():
        call_count.append(1)
        return 5

    # 若写成 (middle() < 5 and 5 < middle())，middle 会被调用两次
    result = 1 < middle() < 10
    print(f"    链式比较中间值求值次数 = {len(call_count)}, 结果 = {result}")

    # 链式比较中若任一环节为 False，后续环节【不执行】（短路）
    side_effect = []

    def never_called():
        side_effect.append("不该被调用")
        return 99

    _ = 1 < 0 < never_called()
    print(f"    1 < 0 < never_called() -> 后续是否执行 = {len(side_effect) > 0}  (短路，短路求值)")

    # 相等性对不同类型的行为
    print(f"    1 == 1.0      = {1 == 1.0}      (数值相等，跨类型)")
    print(f"    1 == True     = {1 == True}     (bool 是 int 的子类，True == 1)")
    print(f"    '1' == 1      = {'1' == 1}        (不同类型不相等)")
    print(f"    [1] == [1]    = {[1] == [1]}     (逐元素比较)")
    print(f"    (1,) == (1,)  = {(1,) == (1,)}")
    # float 的相等是 IEEE 754 的规定，0.1+0.2 != 0.3
    print(f"    0.1 + 0.2 == 0.3 = {0.1 + 0.2 == 0.3}   (浮点精度问题，非 Python 特有)")
    # 正确做法：math.isclose 或容差比较
    import math

    print(f"    math.isclose(0.1+0.2, 0.3) = {math.isclose(0.1 + 0.2, 0.3)}")

    # 自定义类默认按身份比较
    class Point:
        def __init__(self, x):
            self.x = x

    p1, p2 = Point(1), Point(1)
    print(f"    自定义类 p1 == p2 = {p1 == p2}  (无 __eq__ 时退化为身份比较)")
    print(f"    p1 is p2 = {p1 is p2}")


# ============================================================================
# 语法解析 4：逻辑运算符 —— 返回操作数而非布尔
# ============================================================================
# 【语法规则】
#   a and b    若 a 为假返回 a，否则返回 b
#   a or b     若 a 为真返回 a，否则返回 b
#   not a      返回布尔：真变假，假变真（唯一返回 bool 的逻辑运算符）
#   真值判定规则（truthiness）：0、0.0、""、[]、{}、set()、None 为假，其余为真
# 【执行顺序】
#   and / or 短路求值：左侧能决定结果时，右侧【完全不执行】
#   这既是性能优化，也是副作用控制手段。
# 【设计意图】
#   返回操作数而非强制 bool，是为表达"提供默认值"这一模式：
#       value = user_input or "默认"     -> 空值时自动取默认
#   如果 and/or 返回 bool，这个惯用法就不可能写出来。
#   Python 3.4+ 还提供更明确的 x if x else default，但这不影响 and/or 的设计。
def demo_logical_operators():
    print("[4] 逻辑运算符")

    # and/or 返回操作数本身
    print(f"    1 and 2      = {1 and 2}       (左侧为真 -> 返回右侧)")
    print(f"    0 and 2      = {0 and 2}       (左侧为假 -> 返回【左侧】0，非 False)")
    print(f"    0 or '默认'  = {0 or '默认'}   (左侧为假 -> 返回右侧)")
    print(f"    '值' or '默认' = {'值' or '默认'}  (左侧为真 -> 返回左侧)")

    # 真值判定表
    print("    真值判定（False 与 None 视为假）：")
    for value in [0, 0.0, 0j, "", [], {}, set(), None, False, 1, -1, "0", [0], {"a": 0}]:
        # bool() 是显式的真值转换，等价于 if 条件中的隐式判断
        print(f"      {repr(value):<12} -> bool = {bool(value)}")

    # 短路：右侧不执行
    side = []

    def record(tag):
        side.append(tag)
        return True

    _ = False and record("不该执行")
    print(f"    False and record(...) -> 执行次数 = {len(side)}  (短路)")

    _ = True or record("不该执行")
    print(f"    True or record(...)   -> 执行次数 = {len(side)}  (短路，仍为 0)")

    # not 永远返回 bool，这是它与 and/or 的本质区别
    print(f"    not 0    = {not 0}      -> type = {type(not 0).__name__}")
    print(f"    not 'a'  = {not 'a'}    -> type = {type(not 'a').__name__}")
    print(f"    not []   = {not []}")

    # 实用惯用法：or 提供默认值
    def get_config():
        return {}  # 模拟配置为空

    config = get_config() or {"timeout": 30}
    print(f"    空配置 or 默认值 = {config}")

    # and 做前置守卫：非空才继续
    user = {"name": "张三"}
    display = user and user["name"]
    print(f"    user and user['name'] = {display}")
    user_empty = {}
    print(f"    空 dict and 取值 = {user_empty and user_empty['name']}  (无 KeyError 风险)")

    # 三种真值语义的层级：显式 > 隐式
    explicit = bool(user_empty) and user_empty["name"]  # 强制 bool，最清晰
    print(f"    bool(...) and ... = {explicit}  (推荐写法，意图最明确)")


# ============================================================================
# 语法解析 5：位运算符
# ============================================================================
# 【语法规则】
#   a & b    按位与
#   a | b    按位或
#   a ^ b    按位异或（不同为 1，相同为 0）
#   ~a       按位取反，等价于 -(a+1)
#   a << b   左移 b 位，等价于 a * 2**b（不溢出的情况下）
#   a >> b   右移 b 位，【算术右移】，正数等价于 a // 2**b
#   &= |= ^= <<= >>=    对应的复合赋值
# 【执行顺序】
#   运算在整数上进行，以无限精度（任意精度整数）实现，不受机器字长限制。
#   左移后的位被丢弃，超出部分直接消失（不像 C 会是未定义行为）。
# 【设计意图】
#   Python 保留位运算是因为它们在高性能场景不可替代：
#   哈希计算、标志位管理、掩码提取、二进制协议解析都依赖它。
#   任意精度整数让移位不再有溢出风险，这是相对 C 的显著优势。
def demo_bitwise():
    print("[5] 位运算")

    a = 0b1100  # 12
    b = 0b1010  # 10
    print(f"    a = {a:04b}, b = {b:04b}")
    print(f"    a & b = {a & b:04b}  (共同为 1 的位)")
    print(f"    a | b = {a | b:04b}  (任一为 1 的位)")
    print(f"    a ^ b = {a ^ b:04b}  (不同的位)")
    print(f"    ~a    = {~a:04b}   (取反，数值等于 -(a+1) = {-(a + 1)})")

    # 移位
    print(f"    a << 1 = {a << 1:04b} ({a << 1})  左移一位 = 乘 2")
    print(f"    a >> 1 = {a >> 1:04b} ({a >> 1})  右移一位 = 整除 2")

    # 算术右移：负数右移保持符号位（高位补 1），这是与逻辑右移的区别
    neg = -8
    print(f"    -8 >> 1 = {neg >> 1}  (算术右移，负数保持为负，等价于 -8//2)")
    print(f"    -8 // 2 = {neg // 2}")
    print(f"    -8 >> 10 = {neg >> 10}   (右移远多于位宽，结果趋近 -1)")

    # 标志位模式：判断整数权限位
    READ, WRITE, EXEC = 0b001, 0b010, 0b100
    perm = READ | WRITE  # 组合标志
    print(f"    权限 READ|WRITE = {perm:04b}")
    print(f"    含 WRITE 位 = {bool(perm & WRITE)}   用 & 判断位是否为 1")
    print(f"    含 EXEC 位  = {bool(perm & EXEC)}")
    # 置位用 |，清位用 & ~，翻转用 ^
    perm |= EXEC
    print(f"    置位 EXEC 后   = {perm:04b}")
    perm &= ~WRITE
    print(f"    清位 WRITE 后  = {perm:04b}   ~ 是取反掩码，配合 & 精确清除某位")

    # 异或交换两数（不用临时变量）
    x, y = 5, 9
    x ^= y
    y ^= x
    x ^= y
    print(f"    异或交换后 x={x}, y={y}   (面试常见，但 Python 可直接 x, y = y, x 更清晰)")

    # 任意精度整数：无溢出
    big = 1 << 200
    print(f"    1 << 200 的位数 = {len(bin(big)) - 2}   (C 中会溢出/未定义)")


# ============================================================================
# 语法解析 6：成员与身份运算符
# ============================================================================
# 【语法规则】
#   x in s        s 包含 x
#   x not in s    s 不包含 x
#   x is y        x 与 y 是同一个对象
#   x is not y    x 与 y 不是同一个对象
# 【执行顺序】
#   in 会调用容器类型的 __contains__；若未定义，Python 退回逐项 __eq__ 遍历。
#   对 list 是 O(n) 线性扫描，对 set/dict 是 O(1) 哈希查找 —— 这决定了选型。
# 【设计意图】
#   把"是否同一对象"和"值是否相等"都做成一等运算符，
#   消除了 Python 2 时期"空值要比较 identity"这种反直觉规则。
#   PEP 8 明确规定：与 None 比较用 is，不要用 ==。
def demo_membership_and_identity():
    print("[6] 成员与身份运算符")

    # 字符串的 in 是【子串】匹配，要求连续
    print(f"    'a' in 'abc'   = {'a' in 'abc'}    (str 的 in 只匹配连续子串)")
    print(f"    'ac' in 'abc'  = {'ac' in 'abc'}   (不连续 -> False，不是子序列匹配)")

    # 但用 in 找数字会抛 TypeError，因为 str 不支持整数成员
    try:
        _ = 1 in "abc"
    except TypeError as e:
        print(f"    1 in 'abc'     ->  TypeError: {e}")
    print("    -> 正确写法是 'a' in 'abc'；数字查找应先转 str 或用别的容器")

    # 列表的 in 逐项比较
    nums = [3, 7, 11]
    print(f"    7 in [3,7,11]  = {7 in nums}")
    print(f"    5 not in nums  = {5 not in nums}")

    # 字典的 in 检查【键】，不是值 —— 极高频误解
    d = {"name": "张三", "age": 18}
    print(f"    'name' in d    = {'name' in d}   (查的是键)")
    print(f"    '张三' in d    = {'张三' in d}   -> 值要用 d.values()")
    print(f"    '张三' in d.values() = {'张三' in d.values()}")

    # 集合的 in 是 O(1)
    s = {10, 20, 30}
    print(f"    20 in {s}   = {20 in s}   (set 哈希查找，O(1))")

    # in 的方向不对称（一个常见误解）
    print(f"    10 in s = {10 in s}  正确")
    try:
        _ = s in 10
    except TypeError as e:
        print(f"    s in 10 -> TypeError: {e}")
    print("    -> in 不是对称的，必须写【元素 in 容器】")

    # 身份运算（使用前面 demo_comparison 中定义的 Point 类，此处重新构造）
    x, y = [1, 2], [1, 2]
    print(f"    x == y = {x == y}  (值相等)")
    print(f"    x is y = {x is y}  (不同对象)")
    z = x
    print(f"    z = x 后 z is x = {z is x}  (同一对象)")

    # None 判断的规范写法
    val = None
    print(f"    val is None = {val is None}   (推荐)")
    print(f"    val == None = {val == None}   (能工作但不规范)")
    print("    -> PEP 8 要求用 is，因为 == 依赖自定义 __eq__，可能被重载")


# ============================================================================
# 语法解析 7-8：优先级陷阱与完整实测
# ============================================================================
# 【语法规则】
#   优先级从高到低（括号 > 一元 > 幂 > 乘除 > 加减 > 移位 > & > ^ > | >
#                             比较 > not > and > or >
#   结合性：除幂运算 ** 是右结合外，其余基本运算符都是左结合
# 【执行顺序】
#   编译器先按优先级建语法树，再按结合性决定同优先级的组合方向。
#   优先级相近的两个运算符（not / 比较 / is）正是陷阱高发区。
# 【设计意图】
#   Python 的运算符数量远少于 C 的位运算符（没有 ++、--、复合赋值不返回表达式），
#   优先级表短一些，但仍保留了几处历史遗留的意外顺序，
#   这也是为什么规范要求"能加括号就加括号"。
def demo_precedence_traps():
    print("[7] 优先级陷阱")

    # 陷阱一：not 的优先级【低于】比较运算符
    # 因此 not a == b 实际是 not (a == b)，而不是 (not a) == b
    a_val, b_val = 1, 2
    print(f"    not a == b     = {not a_val == b_val}   实际等价于 not (a == b) = {not (a_val == b_val)}")
    print(f"    (not a) == b   = {(not a_val) == b_val}")

    # 陷阱二：is 的优先级高于 ==
    # `x is y == z` 会被解析为 (x is y) == z
    print("    陷阱：a is b == c 实际解析为 (a is b) == c，不是 a is (b == c)")

    # 陷阱三：and 优先级高于 or —— 条件混用必须加括号
    # 真值表差异实测（这组取值两种解释结果【不同】，最能说明问题）：
    #  or 优先： True or (False and False) = True
    # 括号优先： (True or False) and False = False
    t, f = True, False
    print(f"    True or False and False   = {t or f and f}   (or 最低 -> t or (f and f))")
    print(f"    (True or False) and False = {(t or f) and f}   (括号优先 -> False)")
    print("    -> 两种写法结果【不同】，证明 and/or 混用时必须显式加括号")

    # 陷阱四：字符串字面量与乘号的隐式拼接
    s = "a" "b" "c"  # 相邻字面量自动拼接，发生在编译期
    print(f"    'a' 'b' 'c'     = {s}   (编译期隐式拼接，不是 +)")
    print(f"    'a' + 'b' + 'c' = {'a' + 'b' + 'c'}   (+ 是运行期操作)")

    # 陷阱五：一元负号与幂（前面已述，此处复现对比）
    print(f"    -2 ** 2 = {-2 ** 2}   (-(2**2))")
    print(f"    (-2) ** 2 = {(-2) ** 2}")

    # 陷阱六：三元表达式的结合方向（右结合），嵌套时容易看错
    # a if cond1 else (b if cond2 else c)  —— else 分支中嵌套时需要括号才清晰
    grade = 85
    level = "优" if grade >= 90 else ("良" if grade >= 80 else "差")
    print(f"    嵌套三元 grade=85 -> {level}")
    print("    -> 嵌套三元不加括号时，else 分支的嵌套部分是右结合的，可读性差")

    print("[8] 完整优先级实测（用真实求值验证）")

    # 每一行都是"断言 + 打印"，双重确认
    checks = [
        ("2 + 3 * 4", 14, "乘优先于加"),
        ("(2 + 3) * 4", 20, "括号强制"),
        ("2 ** 3 ** 2", 512, "幂右结合"),
        ("-2 ** 2", -4, "幂优先于一元负"),
        ("1 << 2 + 3", 32, "加优先于移位"),
        ("1 + 2 < 4 and 3 > 2", True, "比较优先于 and"),
        ("True or False and False", True, "and 优先于 or"),
        ("not 1 == 1", False, "not 低于比较"),
        ("5 & 3 | 2", 3, "& 优先于 |"),
        ("1 < 2 < 3 < 4", True, "链式比较"),
    ]
    for expr, expected, note in checks:
        # eval 在此仅用于教学演示，生产代码中禁止使用（安全风险）
        actual = eval(expr)
        status = "OK" if actual == expected else "不符合预期"
        print(f"    {expr:<24} = {str(actual):<8} [{note}] {status}")


def main():
    demo_arithmetic()
    demo_assignment_operators()
    demo_comparison()
    demo_logical_operators()
    demo_bitwise()
    demo_membership_and_identity()
    demo_precedence_traps()
    print("[完成] 02_basics/02_operators.py 运行结束")


if __name__ == "__main__":
    main()