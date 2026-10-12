"""
================================================================================
 02_scope_and_closure.py  ——  作用域、LEGB、闭包
================================================================================

【演示的语法点】
 1. 作用域四层嵌套：Local → Enclosing → Global → Builtin，即【LEGB 规则】
 2. 名字查找方向：沿作用域链向外找，找到第一个即停；全局都找不到才报 NameError
 3. global 声明：把名字绑定到【模块级 __dict__】，修改的是全局变量
 4. nonlocal 声明：把名字绑定到【外层函数作用域】（不能是模块级）
 5. ★ 闭包（closure）的本质：内层函数捕获了外层函数的变量，构成
    "函数 + 自由变量的环境" 的组合体；可用 __closure__ 和 co_freevars 观察
 6. 逐层绘制作用域链：把 LEGB 抽象概念可视化成缩进层级
 7. 闭包实现"配置对象"：函数充当工厂，产出带私有状态的行为对象
 8. 闭包陷阱：循环中引用外层变量导致"晚绑定"问题及修复
 9. 作用域相关的易错点：只读 global 无需声明，赋值才需要

【预期输出摘要】
 - "LEGB 逐层演示" 打印出四层作用域各自能看到的名字
 - "闭包原理" 小节打印出 __closure__ 中的 cell 对象和 co_freevars 元组
 - "闭包实现配置对象" 产出的两个配置器互不影响，state 不共享
 - "循环闭包陷阱" 先输出错误结果，再用默认参数修复后输出正确结果
================================================================================
"""

import sys


# ===== 语法解析 =====
# 【1】global 声明的作用域
#   语法规则：global x 必须出现在【函数体顶层】或【该函数使用的嵌套层中】，
#              且 x 不能同时被声明为参数名。
#   语义：告诉解释器"x 是模块级名字"，所有读写都走 sys.modules[__name__].__dict__
#   特别注意：只有在【赋值/增删】时才必须写 global；仅仅读取全局变量不需要声明
#            （写了 global 后，名字在该函数内就从"全局"解析，即使还没赋值）。
global_counter = 0        # 模块级变量，本质是模块 __dict__ 里的一项


def read_global_only() -> int:
    """只读取全局变量 —— 无需 global 声明。"""
    return global_counter      # 沿着 LEGB 一路找到模块层（Global）


def write_global() -> int:
    """修改全局变量 —— 必须 global，否则 a += 1 等价于局部变量 a = a + 1。"""
    global global_counter      # 声明：下面所有 global_counter 都指向模块级那一个
    global_counter += 1
    return global_counter


# ===== 语法解析 =====
# 【2】闭包的核心：内层函数引用外层函数的局部变量
#   语法规则：只要内层函数体中出现某个名字，且该名字在外层【函数】作用域中有绑定，
#              外层函数在【创建该 cell 变量】时就会把它捕获。
#   底层机制（三步）：
#     1) CPython 编译外层函数时，发现 make_closure 要用到 make_cell，
#        于是把 x 提升为 cell 变量（cellvar），指令 LOAD_DEREF 取代 LOAD_FAST；
#     2) 外层函数返回一个函数对象，函数对象的 __closure__ 是一个【元组】，
#        按 co_freevars 的顺序装入若干 cell；
#     3) 内层函数通过 LOAD_DEREF / STORE_DEREF 指令访问 cell 内容，
#        于是"函数记住了它出生时的环境"。
#   设计原理：让数据私有化成为可能 —— 不需要类，也能造出"带状态的实例"。
#   易错点：只有被【引用】的外层变量才会成为自由变量；未被引用的局部变量不入 cell。
def make_counter(start: int = 0):
    """返回一个计数器闭包。每次调用 make_counter 都会生成【独立】的一组 cell。"""

    count = start              # 这个变量会被内层函数引用 → 提升为 cell 变量

    def increment(step: int = 1) -> int:
        nonlocal count         # 修改外层函数的变量必须写 nonlocal（只读不需要）
        count += step          # LOAD_DEREF → 加法 → STORE_DEREF
        return count

    # 返回的是 (函数对象, 捕获的环境) 的组合，靠 __closure__ 关联
    return increment


# ===== 语法解析 =====
# 【3】观察闭包内部结构（教学利器）
#   - func.__closure__  : 元组或 None，每个元素是一个 cell 对象
#   - func.__code__.co_freevars : 自由变量名字的元组（编译期确定）
#   - cell.cell_contents: cell 里真正装的 Python 对象
#   注意：co_freevars 的顺序与 __closure__ 一一对应，这是理解闭包的关键。
def inspect_closure() -> None:
    outer_value = "我是被捕获的变量"
    other = 999                      # 未被内层引用 → 不会进入 cell

    def inner() -> str:
        return outer_value

    print(f"  inner.__code__.co_freevars      = {inner.__code__.co_freevars}")
    print(f"  inner.__code__.co_cellvars      = {inner.__code__.co_cellvars}   # 内层自己的 cell")
    print(f"  inner.__closure__               = {inner.__closure__}")
    print(f"  len(__closure__)                = {len(inner.__closure__)}")
    for i, (name, cell) in enumerate(zip(inner.__code__.co_freevars, inner.__closure__)):
        print(f"    [{i}] 自由变量名={name!r} → cell 内容={cell.cell_contents!r}")
    print(f"  'other' 是否被捕获：{'other' in inner.__code__.co_freevars}   # 未引用就不捕获")


# ===== 语法解析 =====
# 【4】闭包实现"配置对象"（实际工程常用模式）
#   思路：把一组相关的数据 + 操作数据的函数封装成一个整体，
#         外部只能通过暴露的函数访问数据，无法直接改内部状态 → 天然封装。
#   对比：
#     class + self     → 需要 4~5 行样板代码，有显式的对象标识
#     闭包             → 3 行搞定，无类开销，但对象不可 pickle（需 __qualname__ 等）
def make_configurer(default: str, *, strict: bool = False):
    """工厂函数：产出一个配置器闭包。strict=True 时未配置项直接报错。"""
    settings = {default: ""}         # cell 变量；用 dict 而非局部变量便于批量更新

    def configure(key: str, value: str = "") -> str:
        """设置或读取配置项。value 默认空串，读取时可省略 value。"""
        if key not in settings:
            if strict:
                raise KeyError(f"未预声明的配置项：{key}")
            settings[key] = ""       # 动态允许新 key（宽松模式）
        if value:
            settings[key] = value
        return settings[key]

    def snapshot() -> dict[str, str]:
        """返回配置副本 —— dict(...) 是浅拷贝，避免外部改到内部状态。"""
        return dict(settings)

    return configure, snapshot        # 返回多个函数，各自共享同一份 settings


# ===== 语法解析 =====
# 【5】闭包陷阱：循环中的晚绑定（late binding）
#   现象：三个函数都返回了 3，因为它们引用的都是【同一个 cell】 i，
#         循环结束时 i 的值是 3，调用时才去读。
#   根因：闭包捕获的是【变量】而不是【某时刻的值】。
#   修复：给 make_adder 加上默认参数 i=idx，让 i 变成各函数【自己的形参】，
#         不再是自由变量。
#   记忆点：闭包捕获变量，不捕获值；需要捕获值，就用默认参数把它变成形参。
def good_adder_factory():
    fns = []
    for i in range(1, 4):
        def adder(x, i=i):         # ✓ 默认参数在此刻求值，把"值"固化进形参
            return x + i
        fns.append(adder)
    return fns


def bad_adder_factory():
    """错误版本：闭包捕获同一个 i，返回 [f1, f2, f3] 会全是 3。"""
    fns = []
    for i in range(1, 4):
        def adder(x):               # ✗ i 是自由变量，所有 adder 共享一个 cell
            return x + i
        fns.append(adder)
    return fns


# ===== 语法解析 =====
# 【6】逐层绘制作用域：把 LEGB 抽象成可视结构
#   用字典嵌套模拟"作用域链"，展示查找顺序。
#   这是教学用的模型化实现，真实机制是 LOAD_NAME → LOAD_GLOBAL → LOAD_BUILDERS，
#   非局部变量则走 LOAD_DEREF。
def draw_scope_chain() -> None:
    # 模拟三层作用域，键是变量名，值是来源层
    builtin_layer = {"len": "<Built-in>"}
    global_layer = {"APP_NAME": "demo", "VERSION": "1.0"}
    local_layer = {"name": "局部变量", "APP_NAME": "局部同名变量（遮蔽全局）"}

    chain = [("Local  L", local_layer),
             ("Enclosing E", {"greet": "外层函数变量"}),
             ("Global  G", global_layer),
             ("Builtin B", builtin_layer)]

    print("  LEGB 查找链（自内向外）：")
    for level, table in chain:
        items = ", ".join(f"{k}={v!r}" for k, v in table.items())
        print(f"    {level:<12} → {{{items}}}")
    print()
    print("  关键规则：")
    print("    1. 自内向外逐层查找，命中即停（这就是『就近遮蔽』）")
    print("    2. Local 层遮蔽同名 Enclosing；Local 遮蔽 Global")
    print("    3. Builtin 是最后一道，包含 len / print / int 等内置函数")
    print("    4. 四层都没有 → NameError")


def main() -> None:
    print("=" * 60)
    print("【1】global 声明")
    print("=" * 60)
    print(f"初始 global_counter     = {global_counter}")
    print(f"只读函数返回           = {read_global_only()}")
    print(f"write_global() 第一次   = {write_global()}")
    print(f"write_global() 第二次   = {write_global()}")
    print(f"模块级变量现在是        = {global_counter}   # 说明确实改到了全局")
    print(f"从 __dict__ 直接确认    = {globals()['global_counter']}")

    print()
    print("=" * 60)
    print("【2】★ 闭包：每个闭包实例有独立的 cell")
    print("=" * 60)
    c1 = make_counter(10)
    c2 = make_counter(100)
    print(f"闭包1：{c1()} -> {c1()} -> {c1()}")
    print(f"闭包2：{c2()} -> {c2()}")
    print("两个计数器互不干扰，说明各自持有独立的 cell。")
    print(f"c1 和 c2 是同一个函数对象吗：{c1 is c2}   # 同一份代码，但环境不同")
    print(f"它们的 __closure__ 相同吗：{c1.__closure__ is c2.__closure__}")

    print()
    print("=" * 60)
    print("【3】观察闭包内部结构")
    print("=" * 60)
    inspect_closure()

    print()
    print("=" * 60)
    print("【4】闭包实现配置对象（数据私有化）")
    print("=" * 60)
    configure, snapshot = make_configurer("host", strict=False)
    configure("host", "127.0.0.1")
    configure("port", "8080")
    print(f"快照：{snapshot()}")
    # 返回的是副本，改它不影响内部状态
    fake = snapshot()
    fake["host"] = "被篡改"
    print(f"修改副本后重新读取：{snapshot()['host']}   # 内部状态未被污染")

    print()
    strict_conf, strict_snap = make_configurer("token", strict=True)
    print("严格模式下读取未声明项：")
    try:
        strict_conf("token")            # 预声明，OK
        strict_conf("secret")           # 未声明 → 报错
    except KeyError as exc:
        print(f"  KeyError: {exc}")

    print()
    print("  —— 对比：闭包配置器 vs 类配置器 ——")
    print("  闭包：无需类、无 self 样板、不显示对象类型、内部状态无法从外部直接改写")
    print("  类：  可继承、可 pickle、可 isinstance 检查、有 repr 便于调试")

    print()
    print("=" * 60)
    print("【5】★ 闭包陷阱：循环中的晚绑定")
    print("=" * 60)
    good = good_adder_factory()
    bad = bad_adder_factory()
    print(f"修复版 f(10)：{[f(10) for f in good]}   # ✓ 各自固化了 1/2/3")
    print(f"错误版 f(10)：{[f(10) for f in bad]}   # ✗ 全是 13，共享同一个 i")
    print("原因：闭包捕获的是变量本身，不是调用那一刻的值。")

    print()
    print("=" * 60)
    print("【6】LEGB 作用域链逐层演示")
    print("=" * 60)
    draw_scope_chain()

    print()
    print("=" * 60)
    print("【7】嵌套三层作用域的完整验证")
    print("=" * 60)

    def level3() -> str:
        return f"level3 找到 -> {level1_var}, {level2_var}, {level3_var}"

    def level2() -> str:
        level3_var = "我在第三层"
        return level3()

    level2_var = "我在第二层"
    level1_var = "我在第一层"
    level3_var = "我在模块层"
    print(f"  {level2()}")
    print("  可见性：内层能读外层的全部变量；反向（外层读内层）则不可能。")

    print()
    print("=" * 60)
    print("【8】闭包 vs 全局变量：为什么工业代码偏好闭包")
    print("=" * 60)
    print("  全局变量：任何函数都能改 → 无封装、易冲突、难测试")
    print("  闭包：  状态被函数私有 → 有封装、可独立测试、可安全并发创建多实例")
    print(f"  当前解释器：{sys.version.split()[0]}")


if __name__ == "__main__":
    main()