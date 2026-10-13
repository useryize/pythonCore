"""L01 变量与基本数据类型 —— 配套教案配套示例。

运行：python examples/L01_variables_types.py

本脚本演示五件事：
    1. 变量就是「贴标签」，不是「盒子」
    2. Python 的动态类型（运行期才确定类型）与类型可变性
    3. 六个基础类型：int / float / str / bool / None / bytes
    4. type() 与 isinstance() 的区别与正确用法
    5. 三类高频翻车现场：字符串数字相加、小数精度、bool 参与运算

阅读建议：先把 demo_int_float() ~ demo_bool_none() 跑一遍看输出，
再回头看每个函数的注释，最后自己敲一遍 verify_type_guesses() 里的断言。
"""

# ============================================================
# 模块级常量：全大写表示「约定上不会被重新赋值」
# ============================================================
EXCHANGE_RATE = 7.2        # 假设的美元兑人民币汇率，演示 float 精度问题
MAX_SCORE = 100            # 满分，演示 bool 参与运算
BONUS_RATE = 0.15          # 折扣比例，演示 float 与 str 混合输出


# ============================================================
# 第 1 部分：变量到底是什么
# ============================================================
def demo_variable_is_label() -> None:
    """证明「变量是贴在对象上的标签」，而不是一个装着对象的盒子。"""
    # 第 1 行：创建对象 42（int 在 Python 中不可变）
    first = 42
    # 第 2 行：只是又贴了一个标签在同一个对象上，内存里仍然只有一个 42
    second = first
    # 修改标签指向，而不是「修改盒子里的内容」
    first = 100
    # second 依然指向最初那个 42，所以输出 42 而不是 100
    print(f"first={first}, second={second}   # second 仍是 {second}")
    # id() 返回对象在内存中的地址，是验证「是不是同一个对象」的铁证
    third = 42
    # 小整数 42 被 Python 缓存复用，所以 first 那次的 42 和 third 的 42 地址相同
    print(f"id(second)={id(second)}, id(third)={id(third)}, 相同={id(second) == id(third)}")
    print(f"is 判断同一对象: second is third -> {second is third}")
    print(f"== 判断值相等  : second == third -> {second == third}")
    # 本质：赋值语句右边先算出一个「对象」，左边只是拿到它的引用
    print(f"id(EXCHANGE_RATE)={id(EXCHANGE_RATE)}（常量 7.2 的地址）")


def demo_dynamic_typing() -> None:
    """演示动态类型：类型是对象的属性，不是变量的属性。"""
    value = 100              # 此刻 value 贴在一个 int 对象上
    print(f"value = {value!r:>12}  type={type(value).__name__}")
    # 关键：同一个变量名可以先后贴在不同类型的对象上，Python 完全允许
    value = "一百"          # 现在 value 贴在一个 str 对象上
    print(f"value = {value!r:>12}  type={type(value).__name__}")
    # int 的 + 和 str 的 + 规则不同：数字是加法，字符串是拼接
    value = 3.14             # 又变成 float
    print(f"value = {value!r:>12}  type={type(value).__name__}")
    # 再变回 int，甚至变成 None
    value = None             # NoneType 表示「这里没有值」
    print(f"value = {value!r:>12}  type={type(value).__name__}")
    print("⚠️ 动态类型让代码灵活，但也让「类型错误」推迟到运行时才暴露")


# ============================================================
# 第 2 部分：六大基础类型逐个认识
# ============================================================
def demo_int() -> None:
    """int：任意精度整数，没有 64 位上限，没有溢出。"""
    big = 2 ** 100                     # 2 的 100 次方，远超 64 位整数范围
    print(f"2**100 = {big}")
    print(f"占用的二进制位数 = {big.bit_length()}")
    # 下划线只是视觉分隔符，Python 会忽略它，不影响数值
    million = 1_000_000
    print(f"1_000_000 = {million:,}   # 千分位只是显示格式，数值仍然是 1000000")
    # int // int 永远得到 int（向下取整的除法）
    print(f"7 // 2 = {7 // 2}   7 / 2 = {7 / 2}   7 % 2 = {7 % 2}")
    # 负数取模的规则：结果符号跟随除数，保证 a == b * (a // b) + a % b 恒成立
    print(f"-7 // 2 = {-7 // 2}  -7 % 2 = {-7 % 2}  # 商向下取整，余数非负")
    # bool 是 int 的子类，但打印时有自己的显示形式
    print(f"True + True = {True + True}   isinstance(True, int) = {isinstance(True, int)}")


def demo_float() -> None:
    """float：双精度浮点数，能表示小数，但存在无法精确表示的十进制数。"""
    pi = 3.14159265358979
    print(f"pi 存储的值    = {pi}")
    print(f"保留 5 位小数  = {pi:.5f}")
    # .0 是「显式声明这是浮点」的写法，阅读代码时能立刻看出类型意图
    explicit = 10.0
    print(f"10 / 3 = {10 / 3}   # int/int 一定得到 float")
    print(f"10.0 / 3 = {explicit / 3}")
    # 科学计数法：e 或 E 表示「乘以 10 的多少次方」
    print(f"1.5e3 = {1.5e3}   3e-2 = {3e-2}")
    # float 能表示的范围极大，但「精确」只是有限度的
    print(f"float 最大值约 {1.7976931348623157e308}")
    print(f"float 最小正数约 {5e-324}")


def demo_float_precision() -> None:
    """float 精度问题的成因与三种应对方案。"""
    print("【问题 1】十进制小数 0.1 在二进制里是无限循环小数，无法精确表示")
    print(f"0.1 + 0.2 = {0.1 + 0.2}        # 结果不是 0.3")
    print(f"0.1 + 0.2 == 0.3 -> {0.1 + 0.2 == 0.3}   # 直接比较会失败")
    print(f"abs(0.1 + 0.2 - 0.3) = {abs(0.1 + 0.2 - 0.3):.20f}   # 但差极小")

    print("\n【方案 A】比较时用容差（最常用）")
    a, b = 0.1 + 0.2, 0.3
    # math.isclose 默认 rel_tol=1e-9，对绝大多数业务判断足够
    import math                     # 局部导入只为让本示例自包含
    print(f"math.isclose(a, b) = {math.isclose(a, b)}")
    print(f"a == b 或 abs(a - b) < 1e-9 = {a == b or abs(a - b) < 1e-9}")

    print("\n【方案 B】金额用整数存「分」，输出时再除以 100（财务场景首选）")
    price_cents = 1999              # 存 1999 分，而不是 19.99 元
    print(f"19.99 元存成分后：{price_cents} 分 -> 显示为 {price_cents / 100:.2f} 元")

    print("\n【方案 C】确实需要十进制精确运算时用 decimal 模块")
    from decimal import Decimal     # 标准库，无需 pip 安装
    d_a = Decimal("0.1")           # 注意必须用字符串初始化，用 float 初始化会继承误差
    d_b = Decimal("0.2")
    print(f"Decimal('0.1') + Decimal('0.2') = {d_a + d_b}")
    print(f"float(Decimal('0.1')) + float(Decimal('0.2')) = {float(d_a) + float(d_b)}")


def demo_str() -> None:
    """str：不可变的 Unicode 字符串，下标从 0 开始。"""
    s = "Python"
    # 单引号和双引号完全等价，选哪个只取决于「字符串里有没有那个引号」
    print(f"s            = {s!r}")
    print(f"s[0]         = {s[0]!r}   # 第 0 个字符，下标从 0 开始")
    print(f"s[-1]        = {s[-1]!r}   # 负数下标表示从末尾往回数")
    print(f"s[1:4]       = {s[1:4]!r}   # 切片取 [1, 4) 左闭右开")
    print(f"s[::-1]      = {s[::-1]!r}   # 步长 -1 表示倒序")
    print(f"len(s)       = {len(s)}")
    # 三引号字符串可以跨行，常用于写多行提示语
    multi = """第一行
第二行"""
    print(f"多行字符串行数 = {len(multi.splitlines())}")
    # 字符串不可变：任何「修改」操作其实都返回了一个新对象
    print(f"'a' + 'b' = {'a' + 'b'!r}   # 产生了新对象，原始的 'a' 没变")
    print(f"原字符串 s 仍然是 = {s!r}")
    # 转义字符：\n 换行、\t 制表符、\\ 反斜杠本身
    print(f"转义演示：a\\tb\\nc\\\\d")


def demo_bool_and_none() -> None:
    """bool 只有 True / False 两个值；None 是「没有值」，不是 False。"""
    # 比较运算的结果一定是 bool
    print(f"3 > 2 -> {3 > 2}    type={type(3 > 2).__name__}")
    # 真值判断：Falsy 的对象一共有 10 个（数值 0、空容器、None、False）
    falsy_values = [0, 0.0, -0.0, 0j, "", [], {}, set(), None, False]
    print("下面这些值在 if 里都等价于 False：")
    for v in falsy_values:
        print(f"  bool({v!r:>6}) = {bool(v)}")
    # True / False 可以参与算术，因为它们是 int 的子类
    print(f"\nTrue + True = {True + True}（True 数值上就是 1）")
    print(f"False * 100 = {False * 100}")
    print(f"MAX_SCORE > 80 = {MAX_SCORE > 80}")
    # None 与 False 的区别：None 是「没赋值 / 没找到」，False 是「值就是假」
    print(f"\nNone == False -> {None == False}   # 二者互不相等")
    print(f"bool(None) -> {bool(None)}        # 但真值判断上等价")
    print(f"None 是 False -> {None is False}  # is 判断身份，必然不同")
    print(f"str(None) -> {str(None)}         # 打印时写成 None，不是 false")


# ============================================================
# 第 3 部分：type() 与 isinstance()
# ============================================================
def demo_type_and_isinstance() -> None:
    """type() 用来「精确验证」，isinstance() 用来「判断归属家族」。"""
    data = [1, 2.0, "3", True, None, [1], (1,), {"k": 1}, {1, 2}]
    print(f"{'值':<10}{'repr':<12}{'type(...).__name__':<14}{'是 int 吗':<10}{'是数值吗'}")
    print("-" * 62)
    for d in data:
        # type(x) 返回类型对象本身，取 __name__ 拿到 'int' 这样的字符串
        type_name = type(d).__name__
        # isinstance 接受「类型或类型的元组」，可以一次判断多个类型
        is_int = isinstance(d, int)
        # (int, float) 是元组写法，表示「int 或 float」
        is_number = isinstance(d, (int, float))
        print(f"{str(d):<10}{repr(d):<12}{type_name:<14}{str(is_int):<10}{is_number}")
    # ⚠️ isinstance(True, int) 是 True，因为 bool 是 int 的子类
    # 如果你只想要「纯粹的整数」，必须显式排除 bool
    pure_int = isinstance(10, int) and not isinstance(10, bool)
    print(f"\n严格意义的纯整数判断（排除 bool）: {pure_int}")
    # 浮点数不是 int 的子类，反之亦然，类型系统是严格的、不做隐式兼容
    print(f"isinstance(2.0, int) = {isinstance(2.0, int)}   # 2.0 不是 int")


# ============================================================
# 第 4 部分：可变 vs 不可变
# ============================================================
def demo_mutable_vs_immutable() -> None:
    """字符串看起来「被改了」，其实是新对象；列表才是真正被改。"""
    # str / int / tuple 不可变：任何操作都不会改动原对象
    s = "hello"
    s_upper = s.upper()             # 返回全新对象，s 本身没变
    print(f"s.upper() 后原 s = {s!r}，新对象 = {s_upper!r}")
    print(f"内存地址不同: id(s)={id(s)}, id(s_upper)={id(s_upper)}")

    # list 可变：append / 赋值都会改动原对象
    items = ["a", "b"]
    items.append("c")              # 直接改动原列表
    print(f"\nitems = {items}   id={id(items)}")
    alias = items                   # alias 和 items 指向同一个列表
    alias.append("d")               # 通过别名改动
    print(f"通过 alias 追加后，items = {items}   # 同一个对象，两边都变")

    # 反例：想复制必须显式拷贝，否则会互相干扰
    shallow = items.copy()          # 浅拷贝：新建列表，但内部元素仍共享
    shallow.append("e")
    print(f"copy() 后 items   = {items}   # 原列表没受影响")
    print(f"copy() 后 shallow = {shallow}")

    # 嵌套列表时浅拷贝不够用，需要 deepcopy（L08 详讲）
    nested = [[1, 2], [3, 4]]
    deep = [line[:] for line in nested]         # 逐层重新构造，这是最直观的深拷贝
    deep[0][0] = 99
    print(f"\n嵌套深拷贝后 nested[0] = {nested[0]}   # 原结构未受影响")
    print(f"               deep[0]  = {deep[0]}")


# ============================================================
# 第 5 部分：类型转换
# ============================================================
def demo_type_casting() -> None:
    """四组转换函数，以及转换失败时的表现。"""
    # int()：字符串数字转整数；小数直接截断（不是四舍五入）
    print(f"int('42')       = {int('42')!r}")
    print(f"int('  7  ')    = {int('  7  ')!r}   # int 会自动忽略首尾空白")
    print(f"int(3.9)        = {int(3.9)!r}      # 直接截断小数部分")
    print(f"round(3.9, 0)   = {round(3.9, 0)!r}   # 四舍五入得到浮点 4.0")
    # int() 不接受带小数点的字符串，这是最常见的转换报错来源
    try:
        int("3.14")
    except ValueError as exc:
        print(f"int('3.14') 报错: {type(exc).__name__}: {exc}")

    # float()：更宽松，能吃 int、常见科学计数法
    print(f"\nfloat('3.14')   = {float('3.14')!r}")
    print(f"float('42')     = {float('42')!r}     # 整数串也能转")
    try:
        float("abc")
    except ValueError as exc:
        print(f"float('abc') 报错: {type(exc).__name__}: {exc}")

    # str()：几乎什么都能转，唯一失败的是极少数自定义 __str__ 出错的极端情况
    print(f"\nstr(42)         = {str(42)!r}")
    print(f"str(3.14)       = {str(3.14)!r}")
    print(f"str(None)       = {str(None)!r}       # 变成字符串 'None'，不再是 None 本身")
    print(f"str([1, 2])     = {str([1, 2])!r}")

    # bool()：遵循真值规则，而不是「非空字符串就 True」
    print(f"\nbool(0)={bool(0)}  bool('0')={bool('0')}   ⚠️ 非空字符串 '0' 是 True！")
    print(f"bool('')={bool('')}  bool(' ')={bool(' ')}     ⚠️ 空格字符串也是 True")

    # 安全转换：用 try 或 str.isdigit 预判，避免程序崩在用户输入上
    def safe_int(text: str) -> int | None:
        """把字符串安全转成 int，失败返回 None 而不是抛异常。"""
        try:
            return int(text.strip())
        except (ValueError, AttributeError):
            # ValueError: 内容不是数字；AttributeError: 传进来的不是字符串
            return None

    print(f"\nsafe_int(' 42 ') = {safe_int(' 42 ')}")
    print(f"safe_int('4.2')  = {safe_int('4.2')}")
    print(f"safe_int('abc')  = {safe_int('abc')}")


# ============================================================
# 第 6 部分：三大高频翻车现场
# ============================================================
def demo_pitfalls() -> None:
    """把初学者最高频的三个坑集中演示一遍。"""
    print("【坑 1】字符串数字「相加」得到的是拼接，不是求和")
    # 键盘敲进来的永远是字符串，两边都是字符串时 + 执行拼接
    user_input = "3"
    print(f"'3' + '4' = {'3' + '4'!r}   # 两边都是字符串时 + 执行拼接")
    # 正确做法：显式转换其中一边，推荐转成数字再运算
    right = int(user_input) + 4
    print(f"int('3') + 4 = {right}        # 先转类型再相加")
    # 混加直接报错，这是好事：它强制你正视类型
    try:
        _ = user_input + 4
    except TypeError as exc:
        print(f"'3' + 4 直接报错: TypeError: {exc}")

    print("\n【坑 2】小数用 == 比较永远可能失败")
    print(f"0.1 + 0.2 == 0.3 -> {0.1 + 0.2 == 0.3}")
    print(f"正确做法 abs(差) < 1e-9 -> {abs(0.1 + 0.2 - 0.3) < 1e-9}")

    print("\n【坑 3】bool 参与算术时 True 就是 1、False 就是 0")
    is_vip = True
    price = 100.0
    # 新手容易困惑：VIP 客户反而比普通客户便宜，因为 False 变成了 0 被减掉
    price_vip = price - is_vip * 10
    price_normal = price - (not is_vip) * 10
    print(f"is_vip = {is_vip}，直接参与算术：price - is_vip*10 = {price_vip}   ⚠️ 逻辑错误")
    print(f"正确写法：price - (not is_vip)*10 = {price_normal}   ✅")

    print("\n【额外提醒】变量名不要覆盖内置函数和关键字")
    print(f"str(123) -> {str(123)}  # str 是内置类型函数")
    try:
        list = [1, 2]          # noqa: 用 list 覆盖内置函数
        print(f"list = {list}")
        print(f"此时 list('abc') 会报: ", end="")
        list("abc")            # noqa
    except TypeError as exc:
        print(f"TypeError: {exc}")


# ============================================================
# 第 7 部分：命名规范与自我检验
# ============================================================
def demo_naming() -> None:
    """变量命名规则与推荐风格。"""
    # 合法：字母数字下划线，不能以数字开头，不能是关键字
    student_name = "张三"        # 推荐：snake_case，可读性最好
    _private_count = 10          # 前导下划线是「约定上的内部变量」信号
    MAX_RETRY = 3                # 全大写表示常量
    # ❌ 以下写法全部非法或极差：
    # 2nd_place = "亚军"        # 以数字开头 → SyntaxError
    # class = "一班"             # class 是关键字 → SyntaxError
    # my-name = "x"              # 连字符不是标识符字符 → SyntaxError
    # 中文变量名 = 1            # 语法上合法（Python 3 支持），但团队协作中极不推荐
    print(f"student_name={student_name!r}, _private_count={_private_count}, MAX_RETRY={MAX_RETRY}")
    print("\n命名建议：")
    print("  1) 用有业务含义的名词：total_price 优于 a、b、temp1")
    print("  2) 布尔值用 is_/has_ 前缀：is_valid、has_permission")
    print("  3) 循环变量用 i、idx 或有意义的英文词")
    print("  4) 常量全大写；同一模块内保持命名风格一致")


def verify_type_guesses() -> None:
    """用断言自检：如果你改坏了前面的函数，这里会立刻报错。"""
    # assert 是最轻量的自检手段，为假时抛 AssertionError
    assert isinstance(42, int) and not isinstance(42, bool)
    assert isinstance(2.0, float) and not isinstance(2.0, int)
    assert isinstance(True, bool) and isinstance(True, int)
    assert isinstance(None, type(None))
    assert not isinstance(None, (int, float))
    assert bool(0) is False and bool("0") is True
    assert int(" 42 ") == 42 and int(3.9) == 3
    assert round(2.5) == 2      # 注意：Python 的 round 是「银行家舍入」，2.5 → 2
    assert "a" + "b" == "ab" and 1 + 2 == 3
    assert abs((0.1 + 0.2) - 0.3) < 1e-9 and (0.1 + 0.2) != 0.3
    # 「标签」模型的直接验证
    a, b = 42, 42
    a = 100
    assert b == 42 and a == 100
    # 可变对象的别名效应
    original = [1, 2]
    alias = original
    alias.append(3)
    assert original == [1, 2, 3]
    print("✅ verify_type_guesses 全部断言通过，基础概念掌握无误")


# ============================================================
# 程序入口
# ============================================================
def main() -> None:
    """按教学顺序调用全部演示函数。"""
    print("=" * 64)
    print("L01 · 变量与基本数据类型")
    print("=" * 64)
    demo_variable_is_label()
    print("\n" + "-" * 64)
    demo_dynamic_typing()
    print("\n" + "-" * 64)
    demo_int()
    print("\n" + "-" * 64)
    demo_float()
    print("\n" + "-" * 64)
    demo_float_precision()
    print("\n" + "-" * 64)
    demo_str()
    print("\n" + "-" * 64)
    demo_bool_and_none()
    print("\n" + "-" * 64)
    demo_type_and_isinstance()
    print("\n" + "-" * 64)
    demo_mutable_vs_immutable()
    print("\n" + "-" * 64)
    demo_type_casting()
    print("\n" + "-" * 64)
    demo_pitfalls()
    print("\n" + "-" * 64)
    demo_naming()
    print("\n" + "-" * 64)
    verify_type_guesses()
    print("\n🎉 L01 演示结束")


# 标准入口约定：直接运行本文件时执行 main()，被 import 时不执行，
# 这样别人 import 本模块做实验时不会莫名其妙弹出一大堆输出。
if __name__ == "__main__":
    main()
