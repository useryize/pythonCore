"""
================================================================================
 01_function_basics.py  ——  函数基础语法全演示
================================================================================

【演示的语法点】
 1. def 定义函数、函数对象是一等公民、可赋值给变量
 2. 位置参数 (positional parameters)
 3. 默认参数 (default parameters) 与「定义时求值一次」原理
 4. ★ 可变默认参数 BUG 的复现与两种修复方案（面试高频）
 5. 返回值：单返回 / 多返回值（实际是元组解包）/ return None 的隐式返回
 6. *args 可变位置参数（打包为 tuple）
 7. **kwargs 可变关键字参数（打包为 dict）
 8. 仅位置参数 `/` 与仅关键字参数 `*`（Python 3.8+ 语法）
 9. 参数的书写顺序强制规则：位置参数 -> 默认参数 -> *args -> 仅关键字 -> **kwargs
10. 参数对象的"可调用性"：函数可以作为参数传递（高阶函数的起点）

【预期输出摘要】
 - "BUG 复现" 小节会打印出 list 累积成 [1,1,1]，直观暴露可变默认参数的坑
 - "BUG 修复" 小节打印 []，说明 None 哨兵方案生效
 - 签名检查小节打印 3 个函数的 inspect.signature 字符串，展示 / 与 * 的效果
================================================================================
"""

from __future__ import annotations  # 让本文件里的注解在运行时不被立即求值（此处仅为演示预留）


# ===== 语法解析 =====
# 【1】def 语句：定义函数
#   语法规则：def 函数名(参数列表) -> 返回类型:  函数体
#   - 参数列表中的每个"名字"是【形参】(formal parameter)
#   - 函数体必须有缩进，缩进结束（dedent）时函数定义才真正完成
#   - def 是【语句】(statement)，不是表达式；执行到 def 时，Python 会创建一个
#     function 对象并把它绑定到函数名上。函数体此时【不会执行】。
#   设计意图：函数名 = 函数对象（名字绑定），因此可以 f = my_func 这种赋值。
#   易错点：def 后面必须紧跟括号，即使无参也要写 ()。
def greet(name: str) -> str:
    """返回一段问候语。docstring 不影响运行，但会被 __doc__ 读取。"""
    return f"你好，{name}！"


# ===== 语法解析 =====
# 【2】位置参数：调用时按【位置顺序】一一对应
#   语法规则：定义时形参名任意；调用时实参的顺序必须与形参顺序一致。
#   执行过程：解释器维护一个"形参名 -> 实参值"的映射，做值拷贝。
#   易错点：位置参数数量必须精确匹配，多一个少一个都 TypeError。
def add_positional(a: int, b: int) -> int:
    return a + b


# ===== 语法解析 =====
# 【3】默认参数 (default parameter)
#   语法规则：def f(a, b=默认值) —— 有默认值的形参必须排在无默认值形参的【后面】。
#              否则语法错误："non-default argument follows default argument"。
#   ★ 关键原理：默认值只在【函数定义被执行的那一瞬间】求值一次，然后被所有调用共享。
#     这就是可变默认参数 BUG 的根源 —— 列表对象是同一个，不是每次新建。
#   设计意图：让调用方可以省略次要参数（参数降级 / 可选配置）。
def power(x: int, exp: int = 2) -> int:
    """默认参数让 exp 可以省略，省略时取 2。"""
    result = 1
    for _ in range(exp):          # range(exp) 而非 range(2)：exp 可变才是默认参数的意义
        result *= x
    return result


# ===== 语法解析 =====
# 【4】BUG 复现：可变对象做默认值
#   现象：连续调用两次 append('x')，第二次调用时默认值依然是【同一个列表】，
#         于是把第一次的结果也带上了 —— 出现 ['x', 'x']。
#   根因推演（逐步）：
#     t1. 执行 def 时，Python 计算默认值表达式 `[]`，得到列表对象 L，id(L)=140...
#     t2. 把 L 作为函数对象的 __defaults__ 元组中的一员保存（函数持有引用！）
#     t3. 第一次调用 append_default('a')：未传 items -> 用 L -> L 变成 ['a']
#     t4. 第二次调用 append_default('b')：未传 items -> 还是 L（L 已被改脏）-> ['a','b']
#   结论：默认值在【定义期】只求值一次，属于"跨调用共享的状态"。
def append_default(item: str, items: list[str] = []) -> list[str]:  # noqa: B006 故意保留 bug
    items.append(item)
    return items


# ===== 语法解析 =====
# 【5】BUG 修复方案 A：None 哨兵（推荐、业界通用）
#   写法要点：
#     a) 默认值用 None（不可变对象，不会被改脏），类型注解写成 list[str] | None
#     b) 在【函数体内部】判断 None 时再创建新对象 —— 创建时机变成"每次调用"，
#        彻底切断跨调用共享。
#   为什么比方案 B 好：调用方仍可显式传入 None，行为一致；且语义清晰。
def append_fixed_a(item: str, items: list[str] | None = None) -> list[str]:
    if items is None:              # 用 `is None` 而不是 `if not items`：
        items = []                 # 空列表也是合法业务值，not 会误判成"未传"
    items.append(item)
    return items


# ===== 语法解析 =====
# 【5b】BUG 修复方案 B：用一个新函数对象承接（等价直观写法）
def append_fixed_b(item: str, items: tuple[str, ...] = ()) -> tuple[str, ...]:
    # 不可变默认值 + 元组相加，每次都产生新对象，无副作用
    return items + (item,)


# ===== 语法解析 =====
# 【6】返回值语法
#   - return 后面的表达式会被【立即求值】，然后函数立刻结束（不再往下执行）
#   - 没写 return 的函数，默认返回 None（隐式返回）
#   - 一个 return 返回多个值时，Python 实际把它们打包成一个【元组】再返回，
#     靠解包（unpacking）接收。这是"元组是Python最核心数据结构"的体现。
def divmod_demo(a: float, b: float) -> tuple[float, float]:
    """返回 (商, 余数)。本质上就是 return (a // b, a % b)"""
    return a // b, a % b          # 注意：这行等价于 return (a // b, a % b)


def two_results(a: int, b: int) -> tuple[int, int]:
    """演示多返回值 + 解包。"""
    return a + b, a * b


# ===== 语法解析 =====
# 【7】*args：可变位置参数
#   语法规则：形参列表里的 `*args` 会把【所有剩余的位置实参】打包成一个 tuple。
#   执行顺序约束：`*` 表达式出现在实参列表时做的是【解包】；
#                 出现在形参列表时做的是【打包】—— 同一符号，方向相反。
def sum_all(*args: int) -> int:
    """args 的类型是 tuple。求和的经典手写实现（注意 sum 内置函数的区别）。"""
    total = 0
    for n in args:
        total += n
    return total


def avg_with_others(*args: int, scale: float = 1.0) -> tuple[int, float]:
    """*args 之后仍可跟仅关键字参数，args 只吞掉位置实参。"""
    total = sum(args)
    return len(args), total * scale


# ===== 语法解析 =====
# 【8】**kwargs：可变关键字参数
#   把所有【未在形参列表中匹配到的关键字实参】打包成 dict。
#   注意：kwargs 的键天然是字符串，因此无法表达"位置语义"。
def build_profile(name: str, **extra: object) -> dict[str, object]:
    """name 命中形参，其余进入 extra。"""
    return {"name": name, **extra}   # 字典解包 {**a, **b}：合并字典


# ===== 语法解析 =====
# 【9】仅位置参数 `/` 与仅关键字参数 `*`（PEP 570 / PEP 362，3.8+）
#   语法规则（这一行的顺序就是 Python 强制的书写顺序）：
#       def f(pos_only, /, normal=默认值, *args, kw_only, **kwargs)
#                  ↑ / 左边        ↑ * 右边只能写关键字   ↑ *args 可有可无
#   - `/` 之前的参数【只能按位置传】：f(1) 可以，f(pos_only=1) 报 TypeError。
#     设计意图：保护参数名，允许日后自由重命名而不破坏调用方。
#   - `*` 之后的参数【必须用关键字传】：防止调用方误把位置实参塞进来。
#     设计意图：布尔型开关参数（如 verbose=True）用关键字传，可读性远好于 f(True)。
def positional_only_demo(a: int, b: int, /, c: int = 3, *, verbose: bool = False) -> str:
    parts = [f"a={a}", f"b={b}", f"c={c}", f"verbose={verbose}"]
    return ", ".join(parts)


# ===== 语法解析 =====
# 【10】参数转发（最常见的实际用法）
#   规则：调用方传来的实参形态可能是"位置形态"也可能是"关键字形态"，
#         接收方要用 * 和 ** 原样【透传】，否则会丢失信息、改变语义。
#   注意 * 和 ** 这里的角色是【解包】实参。
def passthrough(func, /, *args, **kwargs):
    """把任意实参原样转发给 func。func 用仅位置参数声明，强调它是内部实现细节。"""
    return func(*args, **kwargs)


def _strict_sum(a: int, b: int, /) -> int:
    return a + b


def _kw_sum(a: int, b: int) -> int:
    """无 / 限制，a、b 都能按关键字传，因此可以用 **dict 解包调用。"""
    return a + b


# ===== 语法解析 =====
# 【设计原理】为什么参数顺序被强制成这样？
#   Python 让"必填的、位置语义强的"排前面，"可选的、需要名字澄清的"排后面，
#   本质上是让【调用点的可读性】最大化：
#     f(1, 2)          —— 纯位置，调用方明确知道含义（靠类型/文档）
#     f(1, 2, verbose=True) —— 有名字的自证式调用
#   `*` 同时充当了"仅关键字分隔符"和"可变位置参数"，一个符号两用，
#   是 Python 语法设计中的"语法糖复用"经典案例。


def main() -> None:
    print("=" * 60)
    print("【1】函数是一等公民")
    print("=" * 60)
    f = greet                      # 函数对象赋值给另一个名字（原名 greet 依然存在）
    print(f("函数也是对象"))        # 调用别名
    print(f"函数对象类型：{type(greet)}")
    print(f"可调用判定：callable(greet) = {callable(greet)}")
    print(f"__name__ 属性：{greet.__name__}   # 函数对象自带元信息")
    print(f"__doc__ 属性：{greet.__doc__}")
    print(f"greet 是 f 吗：{greet is f}   # 两者指向同一个函数对象")

    print()
    print("=" * 60)
    print("【2】位置参数")
    print("=" * 60)
    print(f"add_positional(3, 4) = {add_positional(3, 4)}")

    print()
    print("=" * 60)
    print("【3】默认参数")
    print("=" * 60)
    print(f"power(3)    = {power(3)}         # exp 用默认值 2")
    print(f"power(3, 4) = {power(3, 4)}      # exp 被显式覆盖")
    print(f"默认值存放在函数对象的 __defaults__：{power.__defaults__}")

    print()
    print("=" * 60)
    print("【4】★ 可变默认参数 BUG 复现")
    print("=" * 60)
    print(f"第 1 次调用：{append_default('a')}")
    print(f"第 2 次调用：{append_default('b')}   # ← 'a' 混进来了，这就是 BUG")
    print(f"第 3 次调用：{append_default('c')}")
    print(f"函数 __defaults__：{append_default.__defaults__}")
    print("根本原因：默认值列表在【定义时】创建，被所有调用共享同一个对象。")
    print("另一颗地雷：default 参数的表达式在【定义时】就执行一次。")

    print()
    print("=" * 60)
    print("【5】★ BUG 修复方案 A：None 哨兵")
    print("=" * 60)
    print(f"第 1 次调用：{append_fixed_a('a')}")
    print(f"第 2 次调用：{append_fixed_a('b')}   # ← 干净，没有 'a'")
    print(f"第 3 次调用：{append_fixed_a('c')}")
    # 注意 append_fixed_a 的 __defaults__ 是 (None,) —— 不可变，绝不会被改脏
    print(f"函数 __defaults__：{append_fixed_a.__defaults__}")
    # 显式传入列表时仍然复用调用方的对象（这是期望行为，不是 bug）
    shared = ["已有"]
    print(f"显式传入列表：{append_fixed_a('新', shared)}，原列表变为 {shared}")

    print()
    print("=" * 60)
    print("【5b】BUG 修复方案 B：不可变默认值 + 产生新对象")
    print("=" * 60)
    print(f"第 1 次调用：{append_fixed_b('a')}")
    print(f"第 2 次调用：{append_fixed_b('b')}")

    print()
    print("=" * 60)
    print("【6】返回值")
    print("=" * 60)
    q, r = divmod_demo(17, 5)
    print(f"divmod_demo(17, 5) -> ({q}, {r})   # 多返回值本质是元组")
    total, product = two_results(6, 7)
    print(f"two_results(6, 7)  -> 和={total}, 积={product}")
    # 函数体没有 return 时，Python 在末尾自动插入 return None（隐式返回）
    def silent() -> None:
        pass
    print(f"没有 return 语句的函数返回：{silent()!r}")

    print()
    print("=" * 60)
    print("【7】*args 可变位置参数")
    print("=" * 60)
    print(f"sum_all()            = {sum_all()}              # 空 args，元组为空，打印 0")
    print(f"sum_all(1, 2, 3, 4)  = {sum_all(1, 2, 3, 4)}")
    n, scaled = avg_with_others(1, 2, 3, scale=2)
    print(f"avg_with_others(1,2,3, scale=2) -> 数量={n}, 加权={scaled}")
    print(f"args 的实际类型是 tuple：{type((1, 2, 3))}")

    print()
    print("=" * 60)
    print("【8】**kwargs 可变关键字参数")
    print("=" * 60)
    print(build_profile("张三", age=18, city="北京", score=99))
    print(build_profile("李四"))    # extra 为空字典

    print()
    print("=" * 60)
    print("【9】仅位置参数 / 与仅关键字参数 *")
    print("=" * 60)
    # a、b 在 / 左边 —— 只能按位置传
    print(f"位置传参：    {positional_only_demo(1, 2)}")
    print(f"混合传参：    {positional_only_demo(1, 2, 30, verbose=True)}")
    try:
        # 错误示范：a 在 / 左边，用关键字传会报 TypeError
        positional_only_demo(a=1, b=2)
    except TypeError as exc:
        print(f"用关键字传仅位置参数 -> TypeError: {exc}")
    try:
        # 错误示范：verbose 在 * 右边，必须写名字，否则被当成 c
        positional_only_demo(1, 2, 30, True)
    except TypeError as exc:
        print(f"用位置传仅关键字参数 -> TypeError: {exc}")

    print()
    print("=" * 60)
    print("【10】参数转发 * 与 ** 的解包角色")
    print("=" * 60)
    data = [7, 8]           # 列表作为实参数据源
    kw = {"a": 5, "b": 6}   # 字典作为关键字实参数据源
    # 注意：用关键字实参去填形参名，只能填那些【不是仅位置参数】的形参。
    # 形参 `func` 声明在 / 左边，因此只能靠位置传 —— 这正是 `/` 的语义价值。
    print(f"透传位置实参：  {passthrough(_strict_sum, 10, 20)}")
    print(f"实参 * 解包列表：{passthrough(_strict_sum, *data)}")   # * 在【实参侧】= 解包
    print(f"实参 ** 解包字典：{passthrough(_kw_sum, **kw)}")  # ** 在【实参侧】= 解包
    print("对比：**解包只能喂给接受关键字的形参，遇到仅位置形参会报 TypeError。")
    print(f"位置 + 关键字混传：{passthrough(power, 2, exp=10)}")


# 标准 Python 入口约定：只有被直接运行时才执行 main()，被 import 时不执行。
# 好处：其他模块可以放心 from 01_xxx import ... 而不会触发副作用。
if __name__ == "__main__":
    main()