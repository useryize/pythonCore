"""L02 运算符与表达式 —— 配套教案配套示例。

运行：python examples/L02_operators.py

本脚本演示六件事：
    1. 七类运算符：算术 / 比较 / 逻辑 / 赋值 / 成员 / 身份 / 位运算入门
    2. 运算符优先级：为什么加不加括号结果完全不同
    3. 链式比较：Python 独有的写法及其数学含义
    4. is 与 == 的本质区别（对象身份 vs 值相等），含驻留与小整数缓存
    5. 条件表达式 / 三元表达式与其他表达式写法
    6. 三大高频坑：浮点数相等、链式赋值、优先级误判

阅读建议：重点看 demo_is_vs_equal() 和 demo_precedence()，
这两节决定了你能不能读懂别人写的 Python 代码。
"""

# ============================================================
# 模块级常量
# ============================================================
PRICE = 199.99               # 商品单价，用于演示 float 精度与格式化
DISCOUNT_RATE = 0.8          # 折扣率
STOCK_LIMIT = 100             # 库存上限，用于成员判断
DEFAULT_NAME = "匿名用户"      # 默认值，含中文，顺便演示字符串格式化


# ============================================================
# 第 1 部分：算术运算符
# ============================================================
def demo_arithmetic() -> None:
    """七种算术运算，以及 int / float / 复数之间的类型变化。"""
    a, b = 17, 5
    print(f"a = {a}, b = {b}")
    print(f"a + b   = {a + b}      # 加法")
    print(f"a - b   = {a - b}      # 减法")
    print(f"a * b   = {a * b}      # 乘法，* 前后可以写空格，可读性更好")
    print(f"a / b   = {a / b}      # 真除法，永远返回 float")
    print(f"a // b  = {a // b}     # 地板除法，向下取整，int // int 得 int")
    print(f"a % b   = {a % b}      # 取余 = a - b * (a // b)")
    print(f"a ** b  = {a ** b}     # 幂运算，右结合：等价于 (a ** b)")
    print(f"a ** 0.5 = {a ** 0.5}  # 开平方的常用写法")
    print(f"-a ** 2 = {(-a) ** 2}  ⚠️ -a ** 2 等价于 -(a ** 2) = {-(a ** 2)}")

    # ⚠️ 除零必须显式说明：Python 对 int 和 float 一视同仁，都抛 ZeroDivisionError
    # 这点和 C / JavaScript 不同：JS 里 1.0/0 得到 Infinity，Python 里不会
    print(f"\nint 除零：1 / 0")
    try:
        _ = 1 / 0
    except ZeroDivisionError as exc:
        print(f"  实测报错: {type(exc).__name__}: {exc}")
    print(f"float 除零：1.0 / 0  ← 同样报错，不是 Infinity！")
    try:
        _ = 1.0 / 0
    except ZeroDivisionError as exc:
        print(f"  实测报错: {type(exc).__name__}: {exc}")
    print(f"float 取余除零 1.0 % 0 也一样报错:")
    try:
        _ = 1.0 % 0
    except ZeroDivisionError as exc:
        print(f"  实测报错: {type(exc).__name__}: {exc}")
    # 如果你真的需要「无穷大」，要自己构造，且必须先判分母
    print(f"\n需要无穷大时用 math.inf 显式构造: {__import__('math').inf}")
    print(f"需要 NaN 时用 float('nan'): {float('nan')}，注意 nan == nan 恒为 {float('nan') == float('nan')}")

    # 复数：Python 原生支持，用 j 表示虚数单位
    c = complex(3, 4)
    print(f"\n复数 complex(3, 4) = {c}，模长 = {abs(c):.2f}")

    # 位运算：把整数当作二进制来看
    print(f"\n位运算（按二进制位操作）：")
    print(f"  12 & 10   = {12 & 10}    # 1100 & 1010 = 1000   按位与，常用于掩码取位")
    print(f"  12 | 10   = {12 | 10}    # 1100 | 1010 = 1110   按位或，常用于合并标志位")
    print(f"  12 ^ 10   = {12 ^ 10}    # 1100 ^ 1010 = 0110   异或，不同时为 1")
    print(f"  12 << 2    = {12 << 2}    # 左移 2 位 = 乘 4")
    print(f"  12 >> 2    = {12 >> 2}    # 右移 2 位 = 除 4（向下取整）")
    print(f"  ~12        = {~12}      # 按位取反 = -(12+1) = -13，这是恒等式")
    print(f"  判断偶数最快的方式: n & 1 == 0，12 & 1 = {12 & 1}")


# ============================================================
# 第 2 部分：比较运算符
# ============================================================
def demo_comparison() -> None:
    """六个比较运算符，以及「可比较对象」的概念。"""
    a, b = 10, 3
    print(f"a = {a}, b = {b}")
    print(f"a == b  -> {a == b}      # 等于（比较值）")
    print(f"a != b  -> {a != b}      # 不等于")
    print(f"a > b   -> {a > b}       # 大于")
    print(f"a >= b  -> {a >= b}      # 大于等于")
    print(f"a < b   -> {a < b}       # 小于")
    print(f"a <= b  -> {a <= b}      # 小于等于")

    # ⚠️ = 和 == 完全是两回事，这是初学者最高频的语法错误之一
    print("\n⚠️ 赋值 = 与相等 == 的区别：")
    # if x = 5:      # ❌ 语法错误，Python 会直接报错而不是悄悄执行
    # if x == 5:     # ✅ 正确
    if a == 10:
        print("  a == 10 成立，说明 == 是「比较」")
    print(f"  (a == 10) 的结果是 bool: {type(a == 10).__name__}")

    # 同一个对象可以和多个类型比较：数字、字符串、元组、列表都能比较
    print("\n可比较性演示：")
    print(f"  'apple' < 'banana' -> {'apple' < 'banana'}    # 字符串按逐字符 Unicode 码位比较")
    print(f"  (1, 2) < (1, 3)   -> {(1, 2) < (1, 3)}    # 元组逐元素比较")
    print(f"  [1, 2] < [1, 3]   -> {[1, 2] < [1, 3]}    # 列表同理")
    # 数字和字符串不能比较，这是 Python 的硬规则（不同于 JS 的隐式转换）
    try:
        _ = 1 < "2"
    except TypeError as exc:
        print(f"  1 < '2' 报错: TypeError: {exc}")
    # ⚠️ 列表的 == 只比较元素，不比较身份
    print(f"\n  [1,2] == [1,2] -> {[1, 2] == [1, 2]}   值相等")
    print(f"  [1,2] is [1,2] -> {[1, 2] is [1, 2]}   身份不同，每次新建列表")


# ============================================================
# 第 3 部分：链式比较（Python 特色）
# ============================================================
def demo_chained_comparison() -> None:
    """a < b < c 之所以能工作，是因为它真的等价于 a < b and b < c。"""
    score = 75
    # 最自然的写法，直接表达「介于 60 到 90 之间」
    print(f"60 <= {score} <= 90 -> {60 <= score <= 90}")
    # 展开后等价于下面两行的 and 组合，Python 只会对中间表达式求值一次
    print(f"等价写法 -> {60 <= score and score <= 90}")
    print(f"求值次数对比：链式写法中 score 只被比较 2 次，且 75 > 60 成立后短路")

    # ⚠️ 陷阱：如果中间表达式有副作用或有函数调用，等价展开会重复求值
    calls = []
    def get_value() -> int:
        """记录自己被调用了几次，用来验证求值次数。"""
        calls.append(1)
        return 5
    # 链式写法：get_value() 只被调用两次（一次比较左边界，一次取中间值）
    result = 1 < get_value() < 10
    print(f"\n链式比较 1 < get_value() < 10 = {result}，get_value 被调用 {len(calls)} 次")
    # 手工展开：get_value() 被调用四次！
    calls.clear()
    v = get_value()
    result2 = 1 < v < 10
    print(f"手工展开（先用变量接住）结果 {result2}，调用 {len(calls)} 次 ✅")

    # ⚠️ 链式比较在赋值时不要连写，会变成链式赋值
    print("\n⚠️ 链式比较 ≠ 链式赋值：")
    # if 0 < x < 10:  ✅ 这是链式比较
    x = 5
    if 0 < x < 10:
        print("  0 < x < 10 判断正确 ✅")
    # a = b = c = 1  ✅ 这是链式赋值，三个名字都指向 1
    a = b = c = 1
    print(f"  a = b = c = 1 后 a={a}, b={b}, c={c} ✅")
    # ❌ 错误示范：if a = b = c 会报 SyntaxError
    try:
        exec("if 0 = x:\n    pass")
    except SyntaxError as exc:
        print(f"  链式赋值误写成判断会报 SyntaxError: {exc.msg}")


# ============================================================
# 第 4 部分：逻辑运算符与短路
# ============================================================
def demo_logic() -> None:
    """and / or / not 的返回值不是布尔，而是「参与运算的那个对象」。"""
    # and：左边为假就返回左边，否则返回右边
    print(f"True  and  'x' -> {True and 'x'!r}     # 左边真，返回右边")
    print(f"False and  'x' -> {False and 'x'!r}    # 左边假，直接返回左边")
    print(f"0     and  'x' -> {0 and 'x'!r}        # 0 是 falsy，返回 0 本身")
    # or：左边为真就返回左边，否则返回右边
    print(f"'a' or 'b'   -> {'a' or 'b'!r}          # 左边真，返回左边")
    print(f"''    or '默认' -> {'' or '默认'!r}      # 左边假，返回右边，这就是默认值惯用法")
    print(f"0     or 10   -> {0 or 10}              # 0 是 falsy")
    # not：永远返回 bool
    print(f"not 'x' -> {not 'x'}   not 返回的才是严格的 True/False")

    print("\n短路求值（short-circuit）：")
    calls = []
    def risky() -> bool:
        """模拟一个可能出错的操作（比如查数据库、访问网络）。"""
        calls.append(1)
        return False
    # and 短路：左边 False，risky 根本不会被调用
    _ = risky() and risky()
    print(f"risky() and risky() -> risky 被调用 {len(calls)} 次")
    calls.clear()
    # or 短路：左边 True，risky 同样不会被调用
    _ = True or risky()
    print(f"True or risky()     -> risky 被调用 {len(calls)} 次")
    calls.clear()
    # 短路是「保护机制」：把可能抛异常的调用放在后面做保护
    safe = None
    _ = safe is not None and safe.get("key")      # safe 为 None 时后半段不执行
    print(f"safe is not None and safe.get('key') -> 安全短路，不报错")

    # ⚠️ 陷阱：短路让 is None 写在前面成为必要，而不只是风格问题
    # 因为 `x is None and len(x) > 0` 才是安全的；`len(x) > 0 and x is None` 会崩
    print(f"\n正确顺序: x is not None and len(x) > 0")
    print(f"错误顺序: len(x) > 0 and x is not None   # x 为 None 时直接崩")


# ============================================================
# 第 5 部分：赋值运算符
# ============================================================
def demo_assignment_operators() -> None:
    """八种复合赋值，以及链式赋值的执行顺序。"""
    n = 10
    print(f"初始 n = {n}")
    n += 5
    print(f"n += 5    -> {n}     等价于 n = n + 5")
    n -= 3
    print(f"n -= 3    -> {n}")
    n *= 2
    print(f"n *= 2    -> {n}")
    n /= 4
    print(f"n /= 4    -> {n}     ⚠️ / 会把 int 变成 float")
    n //= 3
    print(f"n //= 3   -> {n}")
    n **= 2
    print(f"n **= 2   -> {n}")
    n %= 50
    print(f"n %= 50   -> {n}")

    # ⚠️ 字符串的 += 不是原地修改，而是反复新建对象（因为 str 不可变）
    # 循环里用 s += x 会是 O(n²)；正确做法是用列表 join 或 io.StringIO
    s = ""
    for ch in "abc":
        s += ch
    print(f"\n字符串 += 在循环中可行但低效，{s!r} 共 {len(s)} 个字符")
    s_join = "".join(list("abc"))
    print(f"改用 join 得到 {s_join!r}，复杂度 O(n)")

    # 链式赋值：从左到右依次赋值
    a = b = c = 0
    print(f"\n链式赋值 a = b = c = 0 -> a={a}, b={b}, c={c}")
    # 解包赋值：左右个数必须一致，否则报 ValueError
    x, y = 1, 2
    print(f"解包 x, y = 1, 2 -> x={x}, y={y}")
    # 交换两个变量不需要临时变量，这是 Python 的招牌写法
    x, y = y, x
    print(f"交换后 x={x}, y={y}")
    # 交换三个
    p, q, r = 1, 2, 3
    p, q, r = r, p, q
    print(f"三元轮换 p,q,r = 1,2,3 -> p={p}, q={q}, r={r}")
    # 星号解包：让列表「剩下全给」最后一个变量
    head, *rest = [1, 2, 3, 4, 5]
    print(f"head, *rest = [1,2,3,4,5] -> head={head}, rest={rest}")
    first, *middle, last = [1, 2, 3, 4, 5]
    print(f"first, *middle, last      -> first={first}, middle={middle}, last={last}")


# ============================================================
# 第 6 部分：成员运算符与身份运算符
# ============================================================
def demo_membership() -> None:
    """in / not in 的语义，以及它们和索引查找的关系。"""
    fruits = ["苹果", "香蕉", "橙子"]
    print(f"fruits = {fruits}")
    print(f"'香蕉' in fruits   -> {'香蕉' in fruits}   # 判断「值是否存在」")
    print(f"'草莓' in fruits   -> {'草莓' in fruits}")
    print(f"'草莓' not in fruits -> {'草莓' not in fruits}")

    # ⚠️ in 判断的是「元素值」，不是「索引位置」，也不是「子串」
    print(f"\n2 in [1, 2, 3]    -> {2 in [1, 2, 3]}   # 元素值存在")
    print(f"10 in [1, 2, 3]   -> {10 in [1, 2, 3]}  # 不存在")
    text = "hello world"
    print(f"'lo wo' in text   -> {'lo wo' in text}  # 字符串的 in 是子串判断")
    print(f"'xyz' in text     -> {'xyz' in text}")

    # 字典的 in 判断的是「键」，不是「值」——这是超级高频的误解
    user = {"name": "张三", "age": 20}
    print(f"\nuser = {user}")
    print(f"'name' in user    -> {'name' in user}    # 键存在")
    print(f"'张三' in user    -> {'张三' in user}    # ⚠️ 值不算，False！")
    print(f"查值要用 user.values(): '张三' in user.values() -> {'张三' in user.values()}")

    # in 的时间复杂度：list 是 O(n)，set 是 O(1)，所以查重要用 set
    big_list = list(range(10000))
    big_set = set(big_list)
    print(f"\n10000 元素中判断 9999 是否存在：list 遍历 9999 次，set 约 1 次哈希查找")
    print(f"结果 list: {9999 in big_list}，set: {9999 in big_set}（结论一致但速度天差地别）")


def demo_is_vs_equal() -> None:
    """is vs ==：这是本课最重要的概念，必须彻底搞清楚。"""
    # == 比较「值是否相等」，由 __eq__ 决定
    # is 比较「是不是同一个对象」（内存地址相同），由 id() 决定
    print("【核心区别】== 看值，is 看身份（内存地址）\n")

    # 小整数缓存：Python 会缓存 -5 到 256 的整数对象
    a = 256
    b = 256
    print(f"a = 256; b = 256")
    print(f"  a == b -> {a == b}   值相等")
    print(f"  a is b -> {a is b}   ⚠️ 恰好也是同一对象，因为 256 在缓存范围内")
    print(f"  id(a)={id(a)}, id(b)={id(b)}\n")

    # 超出缓存范围后，is 就变成 False 了
    c = 1000
    d = 1000
    print(f"c = 1000; d = 1000（超出 -5~256 缓存范围）")
    print(f"  c == d -> {c == d}   值仍然相等")
    print(f"  c is d -> {c is d}   ⚠️ 值相等但对象不同！因为字面量池里没有 1000")
    print(f"  id(c)={id(c)}, id(d)={id(d)}\n")

    # 在同一个代码块里写 c = d = 1000 会共享对象（赋值是同一个对象）
    same = 1000
    also = same
    print(f"同一次赋值 same = also = 1000")
    print(f"  same is also -> {same is also}   ✅ 必然 True，因为标签贴的是同一个对象\n")

    # 字符串驻留：字面量字符串会被自动复用
    s1 = "hello"
    s2 = "hello"
    print(f"字符串字面量 s1 = {s1!r}, s2 = {s2!r}")
    print(f"  s1 == s2 -> {s1 == s2}")
    print(f"  s1 is s2 -> {s1 is s2}   ⚠️ 字面量驻留，恰好同对象")
    # 运行时拼接出来的字符串不驻留
    s3 = "".join(["hel", "lo"])
    print(f"  s3 = ''.join(['hel','lo'])")
    print(f"  s3 == s1 -> {s3 == s1}   值相等")
    print(f"  s3 is s1 -> {s3 is s1}   ⚠️ 运行时构造，不驻留\n")

    # is 的正确用途（只有两种情况）
    print("【is 的正确用法】\n")
    print("用法 1：和 None 比较。None 是唯一合法单例，必须用 is")
    value = None
    if value is None:
        print("  if value is None: ✅")
    print(f"  if value == None 也能工作，但是 is 更快且意图更明确（见 L05）\n")
    print("用法 2：和 True / False 比较（可选，也可直接写 if value:）")
    print(f"  if (1 == 1) is True -> {(1 == 1) is True}")
    print(f"  if 1 is True        -> {1 is True}   ⚠️ 必须写 (1 == 1) is True\n")

    print("【is 的错误用法】用 is 比较数字或字符串的值")
    print("  ❌ if score is 60:   # 用户输入可能来自别处，是否同对象不可控")
    print("  ✅ if score == 60:   # 比较值才是你想要的语义")
    print(f"  实测 (1000 is 1000) = {1000 is 1000}，行为在不同写法场景下会变，故禁止这么写")

    # ⚠️ 语法警告：is not 不是「不是」运算符，而是和 is 优先级一样的独立运算符
    print("\n⚠️ 优先级坑：not a is b 会被解析成 (not a) is b，结果永远是 False")
    a2 = None
    print(f"  not a2 is a2  -> {not a2 is a2}   ⚠️ 错误，等价于 (not None) is None")
    print(f"  a2 is not a2  -> {a2 is not a2}  ✅ 正确")


# ============================================================
# 第 7 部分：优先级与表达式
# ============================================================
def demo_precedence() -> None:
    """优先级顺序（从高到低），以及用括号改变含义。"""
    print("【优先级从高到低】")
    print("""
    1. ()  []  {}          括号、下标、字典/集合字面量
    2. **                   幂运算（右结合）
    3. +x  -x  ~x           一元正负、按位取反
    4. *  /  //  %          乘除取模
    5. +  -                 加减
    6. <<  >>               位移
    7. &                    按位与
    8. ^                    按位异或
    9. |                    按位或
    10. in not in is is not == != < <= > >=   比较与成员身份
    11. not                 逻辑非
    12. and                 逻辑与
    13. or                  逻辑或
    14. = += -= ...         赋值（最低）
    15. 三元表达式 x if c else y  实际优先级高于 or，需用括号包住整个三元式
    """)

    # 优先级误判的经典案例
    print("【案例 1】加法 vs 比较")
    print(f"1 + 2 > 3         -> {1 + 2 > 3}      # 先算 1+2=3，再比较 3>3 → False")
    print(f"(1 + 2) > 3       -> {(1 + 2) > 3}    # 同上，但括号让意图明确")
    print(f"1 + (2 > 3)       -> {1 + (2 > 3)}    # 括号改变了结果：2>3 是 False，1+False=1\n")

    print("【案例 2】not / and / or 的组合")
    print(f"not True and False or True -> {not True and False or True}")
    print("  not True = False → False and False = False → False or True = True")
    print(f"(not (True and False)) or True -> {(not (True and False)) or True}\n")

    print("【案例 3】三元表达式与 or 的优先级（这是最容易错的）")
    label = ""
    # ⚠️ 错误写法：实际被解析成 label or ('已命名' if x else '未命名')
    x = 1
    print(f"错误：label or ('已命名' if x else '未命名') -> {label or ('已命名' if x else '未命名')!r}")
    # ✅ 正确写法：三元式必须整体加括号
    correct = label if label else ("已命名" if x else "未命名")
    print(f"正确：(label if label else (...))          -> {correct!r}\n")

    print("【实践建议】\n")
    print("  1) 混用不同优先级时一律加括号，可读性 > 极简")
    print("  2) not 和 == 混用时，记住 not 的优先级比 == 高：not a == b 等价于 (not a) == b")
    print("  3) 一元 -x ** 2 等价于 -(x ** 2)，需要 -(x ** 2) 或 (-x) ** 2 时务必写括号")


# ============================================================
# 第 8 部分：条件表达式与其他表达式
# ============================================================
def demo_expressions() -> None:
    """三元表达式、条件表达式、以及表达式 vs 语句的区别。"""
    age = 20
    # 条件表达式（俗称三元）：值1 if 条件 else 值2
    status = "成年" if age >= 18 else "未成年"
    print(f"age = {age} -> status = {status!r}")

    # 它也常用于「提供默认值」：|| 风格
    nickname = None
    display = nickname if nickname else DEFAULT_NAME
    print(f"nickname 为 None 时 display = {display!r}")

    # ⚠️ 不要把三元表达式用到需要「多分支」的场景，可读性反而变差
    score = 85
    # 推荐：if/elif 更清晰
    level = ("优秀" if score >= 90 else "良好" if score >= 80 else "及格")
    print(f"score = {score} -> level = {level!r}   （嵌套三元虽然能跑，但可读性差）")
    if score >= 90:
        level2 = "优秀"
    elif score >= 80:
        level2 = "良好"
    else:
        level2 = "及格"
    print(f"同样的逻辑用 if/elif: level = {level2!r}   ✅ 更推荐")

    # walrus 海象运算符（3.8+）：在表达式里赋值，避免重复计算
    data = [1, 2, 3, 4, 5]
    if (n := len(data)) > 3:
        print(f"\n海象运算符：(n := len(data)) = {n} > 3 成立，省去一行")
    # 更典型的场景：while 循环里避免调用两次昂贵函数
    # while (line := fp.readline()): ...  （L03 会用到）

    # 表达式 vs 语句：表达式「能求出一个值」，语句「做一件事」
    print("\n表达式：能计算出值")
    print(f"  2 + 3 -> {2 + 3}")
    print(f"  len('ab') -> {len('ab')}")
    print(f"  x if x > 0 else -x -> {(lambda x: x if x > 0 else -x)(-5)}")
    print("语句：不产生值，如赋值、if、for、print 的调用")


# ============================================================
# 第 9 部分：三大高频坑
# ============================================================
def demo_pitfalls() -> None:
    """把三个最常见的运算符坑讲清楚。"""
    print("【坑 1】浮点数用 == 比较")
    print(f"0.1 + 0.2 == 0.3 -> {0.1 + 0.2 == 0.3}   ❌ 十进制小数在二进制里无法精确表示")
    print(f"abs(0.1+0.2-0.3) < 1e-9 -> {abs(0.1 + 0.2 - 0.3) < 1e-9}   ✅ 用容差")
    print(f"round(0.1+0.2, 10) == 0.3 -> {round(0.1 + 0.2, 10) == 0.3}   ✅ 也可以先四舍五入再比")
    print(f"0.1 * 3 == 0.3 -> {0.1 * 3 == 0.3}   ⚠️ 这个居然相等，运气成分，千万别依赖\n")

    print("【坑 2】链式赋值的误解")
    print("  a = b = 5    是「让 a 和 b 都等于 5」，不是「让 a 等于 b 再等于 5」")
    v1 = v2 = 5
    print(f"  v1 = v2 = 5 -> v1={v1}, v2={v2}，且 v1 is v2 = {v1 is v2}")
    print("  a = b = c 后面必须是「值」，不能是表达式列表（那是解包，规则完全不同）")
    left, right = 1, 2
    print(f"  left, right = 1, 2（解包）-> left={left}, right={right}")
    print("  ⚠️ 写成 left = right = 1, 2 是 SyntaxError\n")

    print("【坑 3】优先级误判")
    print("  错误：if not x is None:  → 解析为 (not x) is None")
    print("  正确：if x is not None:  → is not 是一个整体运算符")
    val = 5
    print(f"  实测 val = {val}")
    print(f"  not val is val  = {not val is val}   ❌ 解析为 (not 5) is 5 → False is 5 → False")
    print(f"  val is not val  = {val is not val}   ✅ 语义正确：5 不是 5 → False")
    print(f"  not val is None = {not val is None} ❌ 解析为 (not 5) is None → False is None → False")
    print(f"  val is not None = {val is not None} ✅ 语义正确：5 不是 None → True\n")
    print("\n  错误：'a' + 'b' * 2 以为是 'ab' * 2")
    print(f"  实测 'a' + 'b' * 2 = {'a' + 'b' * 2!r}   乘法优先，先算 'bb' 再拼 → 'abb'")
    print("  若想要 ('a' + 'b') * 2 必须写括号\n")

    print("【额外坑】整数除法后类型变了")
    print(f"  5 / 2 = {5 / 2}（float），5 // 2 = {5 // 2}（int）")
    print(f"  统计数量用 sum(range(n)) 或 // ，别用 / ，否则类型会污染后续计算")


# ============================================================
# 自我检验
# ============================================================
def verify_operator_understanding() -> None:
    """用断言确认关键概念你都算对了。"""
    # 算术与优先级
    assert 2 ** 3 ** 2 == 512        # ⚠️ 幂运算是右结合，等价于 2 ** (3 ** 2)
    assert (-2) ** 2 == 4            # 有括号才是 -(2**2) 的相反数
    assert 17 // 5 == 3 and 17 % 5 == 2 and 17 == 5 * 3 + 2
    # 链式比较
    assert (1 < 2 < 3) is True
    assert (1 < 2 > 3) is False
    # 逻辑运算返回值是对象不是 bool
    assert (0 or "default") == "default"
    assert (1 and 2) == 2
    # 身份 vs 相等
    assert (None is None) is True
    assert (1000 == 1000) is True
    # 但 is 的结果依赖缓存，不能作为断言基础
    # 成员与身份
    assert ("a" in "cat") is True
    assert ("name" in {"name": 1}) is True
    assert ("x" in {"name": 1}) is False
    # 三元表达式
    assert ("正" if 5 > 0 else "负") == "正"
    # 移位等价于乘除
    assert (1 << 10) == 1024 and (1024 >> 10) == 1
    print("✅ verify_operator_understanding 全部断言通过")


# ============================================================
# 程序入口
# ============================================================
def main() -> None:
    """按教学顺序调用全部演示函数。"""
    print("=" * 64)
    print("L02 · 运算符与表达式")
    print("=" * 64)
    demo_arithmetic()
    print("\n" + "-" * 64)
    demo_comparison()
    print("\n" + "-" * 64)
    demo_chained_comparison()
    print("\n" + "-" * 64)
    demo_logic()
    print("\n" + "-" * 64)
    demo_assignment_operators()
    print("\n" + "-" * 64)
    demo_membership()
    print("\n" + "-" * 64)
    demo_is_vs_equal()
    print("\n" + "-" * 64)
    demo_precedence()
    print("\n" + "-" * 64)
    demo_expressions()
    print("\n" + "-" * 64)
    demo_pitfalls()
    print("\n" + "-" * 64)
    verify_operator_understanding()
    print("\n🎉 L02 演示结束")


# 标准入口约定：直接运行本文件执行 main()，被 import 时不执行
if __name__ == "__main__":
    main()
