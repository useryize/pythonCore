#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
assert 与 warnings
==============================

【演示的语法点】
1. assert 语句的语法与执行机制
2. assert 的正确用法 vs 错误用法（不要用 assert 做参数校验）
3. -O / -OO 会禁用 assert（用 sys.flags.optimize 证明）
4. assert 的短路求值：多个条件写在一条 assert 里
5. 优化模式下 assert 内代码被整体删除的字节码证据
6. warnings 模块：warnings.warn 的分类（UserWarning/DeprecationWarning 等）
7. warnings 的过滤器：simplefilter / filterwarnings / resetwarnings
8. warnings.warn_explicit / catch_warnings 上下文管理器
9. warnings 转异常：simplefilter("error")
10. DeprecationWarning 的默认可见性陷阱

【预期输出摘要】
- 每个assert 正误用例的执行与捕获结果
- 用 dis.dis 对比优化模式（__debug__ 为 False 时的字节码差异）
- 各类warning 的类别名与默认行为
- 三种警告过滤器配置后的行为对比
- warnings 转异常的完整演示
"""

import dis
import sys
import warnings


# ===== 语法解析 =====
# 【1】assert 的语法
#   assert <表达式> [, <失败消息>]
#   - 表达式为真 -> 什么都不做，继续往下执行
#   - 表达式为假 -> 抛 AssertionError，失败消息作为异常参数
#   - 第二个参数是「可选的失败消息」，语法上叫第二个表达式
#
# 【2】assert 的本质：一个 if 语句的语法糖
#   编译器会把 assert 编译成：
#       if not 表达式:
#           raise AssertionError(失败消息)
#   并且整体被包在 `if __debug__:` 条件里！
#   __debug__ 是一个内置常量：默认 True，加 -O 后变成 False。
#   于是 -O 模式下整段代码被编译器直接删除（不是「不执行」，是「不存在」）。
#
# 【3】设计意图
#   assert 的定位是「开发者内部不变量检查」（internal invariant），
#   而不是「用户输入校验」（user input validation）。
#   前者由开发者负责保证正确，后者由外部数据决定，必须显式处理。
def demo_1_assert_basics():
    """assert 的基本行为与短路求值。"""
    print("=" * 70)
    print("【1】assert 基本行为与短路求值")
    print("=" * 70)

    # ===== 语法解析 =====
    # assert 的三个典型形态
    n = 10
    assert n > 0# 条件成立，无任何输出
    print(f"① 条件成立: assert n > 0 无异常")

    try:
        assert n < 0, "n 必须为负数"       # 失败消息是第二个参数
    except AssertionError as e:
        print(f"② 条件失败: AssertionError: {e}")
        # 注意：断言消息被放进 args 元组的第一个元素
        print(f"   e.args = {e.args}")
    print()

    # ===== 语法解析 =====
    # 短路求值：多个条件写在一条 assert 里，用 and 连接
    # and 的左值若为假，右值根本不会被求值。
    # 这既是性能优化，也是安全写法（避免在校验前就执行危险操作）。
    def divide(a, b):
        # 注意顺序：必须先校验 b != 0，再做除法。
        # 如果写成 assert b and a / b > 1，b 为 0 时会短路，反而安全；
        # 但如果写成 assert a / b > 1 and b != 0，就会先做除法而崩溃。
        assert b != 0, "除数不能为 0"
        return a / b

    print("③ 短路求值（and 连接多个条件）：")
    print(f"   divide(10, 2) = {divide(10, 2)}")
    try:
        divide(10, 0)
    except AssertionError as e:
        print(f"   divide(10, 0) -> AssertionError: {e}")
    except ZeroDivisionError as e:
        # 用 python -O 运行时 assert 被整段删除，这里会走到这个分支：
        # 断言失效，错误以更底层的方式暴露出来。
        print(f"   divide(10, 0) -> ZeroDivisionError: {e}（-O 模式：assert 已失效）")
    print()

    # 危险写法演示：顺序错误导致崩溃
    def divide_dangerous(a, b):
        # BUG：先做了除法才校验除数
        assert a / b > 1 and b != 0, "要求结果大于 1"
        return a / b

    print("④ 错误写法（条件顺序颠倒）：")
    try:
        divide_dangerous(10, 0)
    except ZeroDivisionError as e:
        print(f"   -> ZeroDivisionError: {e}  <- 绕过了 assert！")
        print("      原因：and 的左值 a / b 先求值，除零直接崩溃")
    print()
    print("【要点】assert 里多个条件必须把「最可能抛异常的求值」放在最后，")
    print("       或者拆成多条 assert，让 Python 自己短路保护。")


def demo_2_assert_pitfalls():
    """assert 的典型陷阱。"""
    print("=" * 70)
    print("【2】assert 的典型陷阱")
    print("=" * 70)

    # 陷阱1：不要用 assert 做用户输入校验
    # 原因：python -O 会把 assert 整段删除，校验彻底失效。
    print("① 陷阱：用 assert 校验用户输入")
    print("   反例：")
    print("""   def set_age(age):
       assert isinstance(age, int) and age >= 0, "年龄非法"
       # python -O 运行时，以上两行被完全删除，
       # 负数/字符串会直接进入后续逻辑，导致更难排查的崩溃
   """)
    print("   正例：")
    print("""   def set_age(age):
       if not isinstance(age, int) or age < 0:
           raise ValueError(f"年龄非法: {age!r}")
       # 显式抛异常，-O 下依然生效
   """)
    # 用真实代码验证「-O 会删除 assert」
    def check_with_assert(value):
        assert isinstance(value, int), f"必须是整数: {value!r}"
        return f"接受: {value}"

    print(f"   正常模式: {check_with_assert(42)}")
    try:
        check_with_assert("不是整数")
        print("   -O 模式：assert 被删除，非法值被直接接受（校验完全失效）")
    except AssertionError as e:
        print(f"   正常模式传入非法值 -> AssertionError: {e}")
    print()

    # 陷阱2：assert 后不要有裸 except
    print("② 陷阱：不要用 try/except 包裹 assert 来「兜底」")
    print("""   # 反例：断言失败本该让测试失败，被吞掉后问题被隐藏
   try:
       assert condition, "关键前置条件"
   except AssertionError:
       log.warning("跳过")     # <-- 危险：assert 的意义荡然无存
   """)

    # 陷阱3：函数调用写在 assert 里会有副作用
    print("③ 陷阱：assert 中的表达式会被执行（副作用）")
    counter = {"value": 0}

    def side_effect():
        counter["value"] += 1
        return counter["value"]

    # 条件恒为真，所以每次调用都会执行 side_effect
    assert side_effect() > 0, "永远成立"
    assert side_effect() > 0, "永远成立"
    print(f"   执行两条恒真 assert 后，counter = {counter}")
    print("   -> 优化模式删除 assert 后，这些副作用也一并消失，行为不一致")
    print()

    # 陷阱4：optimize 标志的查看
    print("④ 查看当前优化标志：")
    print(f"   sys.flags.optimize = {sys.flags.optimize}")
    print(f"   __debug__ = {__debug__}")
    print(f"   当前解释器命令行是否含 -O：{'是' if sys.flags.optimize else '否'}")
    print()
    print("【要点】assert 只用于「开发者保证」的不变量；用户输入校验必须显式抛异常。")


def demo_3_optimize_mode():
    """用 dis 证明 -O 会把 assert 整段删除。"""
    print("=" * 70)
    print("【3】-O 优化模式如何删除 assert（字节码证据）")
    print("=" * 70)

    # ===== 语法解析 =====
    # 关键洞察：assert 不是「运行时不执行」，而是「编译时不存在」。
    # 源码被编译成字节码时，__debug__ 为 False 会让编译器直接跳过整个块，
    # 因此连函数体里的字节码都不存在 —— 这比运行时判断更快、也无分支开销。
    def with_assert(x):
        assert x > 0, "必须为正"
        return x * 2

    print("① assert 生效时的字节码：")
    dis.dis(with_assert)
    print("   可以看到有 POP_JUMP_IF_TRUE 之类的跳转与 LOAD_GLOBAL(__debug__) 相关逻辑，")
    print("   失败分支会构造并抛出 AssertionError。")
    print()

    # 用 compile + dis 模拟 -O：传入 optimize=1
    print("② 用 compile(..., optimize=1) 模拟 -O 优化后的字节码：")
    src = "def f(x):\n    assert x > 0, 'x must be positive'\n    return x * 2\n"
    # optimize=1 等价于 python -O；optimize=2 还会去掉 docstring（-OO）
    code_optimized = compile(src, "<string>", "exec", optimize=1)
    code_normal = compile(src, "<string>", "exec", optimize=0)

    print("   --- optimize=0（默认）---")
    dis.dis(code_normal)
    print("   --- optimize=1（-O）---")
    dis.dis(code_optimized)
    print()

    # 实际对比两种模式下函数的行为
    namespace_normal = {}
    exec(code_normal, namespace_normal)
    namespace_opt = {}
    exec(code_optimized, namespace_opt)

    print("③ 行为对比：")
    try:
        namespace_normal["f"](-1)
        print("   默认模式返回:", namespace_normal["f"](-1))
    except AssertionError as e:
        print(f"   默认模式(-1) -> AssertionError: {e}")

    # 优化模式下 assert 被删除，-1 也能通过
    result_opt = namespace_opt["f"](-1)
    print(f"   -O 模式(-1) -> 返回 {result_opt}（断言消失，校验失效！）")
    print()

    # 用 __debug__ 做分支的写法（仍然会被优化删除）
    print("④ __debug__ 与 -O：")
    print(f"   当前 __debug__ = {__debug__}（-O 下会变成 False）")
    # 在 -O 下，if __debug__: 的整个分支也会被编译器删除
    print("   if __debug__: print('仅调试模式')  <- -O 下这行也不会输出")
    print()
    print("【要点】-O 删除的是整个代码块（含副作用表达式），不是简单跳过判断。")
    print("【要点】绝不能用 python -O 运行生产程序：会丢失所有 assert 检查。")
    print("【要点】用 assert 写测试断言时要小心：pytest 的 -O 选项同样会禁用它们。")


def get_effective_action(category):
    """按 warnings.filters 的匹配规则，算出某类别当前生效的动作。

    匹配规则：从前往后找第一条「类别匹配」的过滤器，返回它的动作；
    都不匹配则返回列表最后一条（即默认的 "default"）。
    这里手写匹配逻辑，而不是调用 warnings._getaction 私有 API，
    便于理解过滤器的语义（公开 API 没有直接查询生效动作的函数）。
    """
    for action, _msg, cat, _mod, _lineno in warnings.filters:
        if cat is None or issubclass(category, cat):
            return action
    return warnings.filters[-1][0]


def demo_4_warnings_basics():
    """warnings 模块基础。"""
    print("=" * 70)
    print("【4】warnings 模块基础")
    print("=" * 70)

    # ===== 语法解析 =====
    # warnings 模块的定位：不是异常，不中断程序，只是「提醒」。
    # 适用场景：
    #   - API 即将废弃（DeprecationWarning）
    #   - 行为将来会变（PendingDeprecationWarning / FutureWarning）
    #   - 资源即将耗尽（ResourceWarning）
    #   - 用户可能有误但又不至于失败（UserWarning）
    #
    # 关键差异：warnings.warn() 不会中断执行，程序继续往下跑。

    print("① 发出一个普通警告：")
    warnings.warn("这是一个默认的 UserWarning")
    print("   -> 程序继续执行了，警告没有中断流程")
    print()

    # ===== 语法解析 =====
    # warnings 的显示位置：默认只显示「调用 warn 的那一行」（stacklevel=1），
    # 这对库代码很不友好（显示的是库内部行号）。
    # stacklevel=2 表示「报告调用者所在的行」，是库的推荐做法。
    print("② stacklevel 控制警告显示的行号：")
    warnings.warn("这是 stacklevel=1，显示调用 warn 的这一行", stacklevel=1)
    warnings.warn("这是 stacklevel=2，显示我的调用行（推荐）", stacklevel=2)
    print()

    # ===== 语法解析 =====
    # category 参数指定警告类别，决定了它的默认可见性与处理策略。
    # 内置类别（部分）：
    #   UserWarning            默认显示（大多数程序唯一显示的一类）
    #   DeprecationWarning     默认忽略（面向库开发者，需手动开启）
    #   PendingDeprecationWarning 默认忽略（比 Deprecation 更早期）
    #   FutureWarning          默认显示（面向应用开发者）
    #   ResourceWarning        默认忽略（资源未释放等）
    #   RuntimeWarning          默认显示（运行时不确定性问题）
    #   SyntaxWarning           编译期问题
    print("③ 各类警告的默认可见性：")
    test_categories = [
        (UserWarning, "普通用户提醒"),
        (DeprecationWarning, "API 已废弃"),
        (PendingDeprecationWarning, "未来将废弃"),
        (FutureWarning, "行为将要变更"),
        (ResourceWarning, "资源使用不当"),
        (RuntimeWarning, "运行时可疑行为"),
        (SyntaxWarning, "语法层面警告"),
        (BytesWarning, "bytes/str 比较隐患"),
        (EncodingWarning, "编码问题"),
    ]
    # warnings._getaction(category) 返回该类别当前生效的过滤器动作
    for cat, desc in test_categories:
        action = get_effective_action(cat)
        print(f"   {cat.__name__:<28} 默认action={action:<10} {desc}")
    print()
    print("【要点】只有 UserWarning / FutureWarning / RuntimeWarning 默认可见，")
    print("       DeprecationWarning 默认被忽略（这是 PEP 565 的有意设计）。")


def demo_5_warning_filters():
    """警告过滤器的配置与效果。"""
    print("=" * 70)
    print("【5】警告过滤器：simplefilter / filterwarnings")
    print("=" * 70)

    # ===== 语法解析 =====
    # 警告过滤规则由一组「过滤器」决定，每个过滤器是一个五元组：
    #   (action, message_regex, category, module_regex, lineno)
    #
    # action 的取值：
    #   "error"      -> 把警告升级为异常（最常用，便于测试）
    #   "ignore"     -> 完全忽略
    #   "always"     -> 每次都显示（不受 __warningregistry__ 去重影响）
    #   "default"    -> 每个位置（模块+行号+类别）只显示一次
    #   "module"     -> 每个模块只显示一次
    #
    # 匹配规则：从过滤器列表「前面往后面」找第一条匹配的规则，
    #   找到即用；找不到则用最后一个过滤器（通常是 "default"）。
    #   所以越具体的过滤器要放越前面。

    def emit_warnings():
        warnings.warn("测试消息 A", UserWarning)
        warnings.warn("测试消息 B", DeprecationWarning)
        warnings.warn("测试消息 C", UserWarning)

    print("① 默认过滤器（warnings.filters）：")
    print(f"   过滤器数量: {len(warnings.filters)}")
    # 打印过滤器，但太长的正则表达式省略显示
    for i, filt in enumerate(warnings.filters):
        action, msg, cat, mod, lineno = filt
        msg_text = msg.pattern if hasattr(msg, "pattern") else msg
        mod_text = mod.pattern if hasattr(mod, "pattern") else mod
        print(f"   [{i}] action={action:<8} message={str(msg_text)[:20]:<22}"
              f" category={cat.__name__:<22} module={str(mod_text)[:14]}")
    print()

    # ===== 语法解析 =====
    # filterwarnings(action, message="", category=Warning, module="", lineno=0)
    # 四个参数是正则表达式（字符串会内部编译），按「子串匹配」处理。
    print("② filterwarnings 精确控制：")
    with warnings.catch_warnings(record=True) as captured:
        # record=True 让警告不打印，而是收集到 captured 列表里
        # 这样就能「测试」警告是否产生、类别是什么
        warnings.filterwarnings("ignore", category=DeprecationWarning)
        warnings.filterwarnings("always", message="消息 A")
        emit_warnings()

        print(f"   捕获到 {len(captured)} 条警告：")
        for w in captured:
            print(f"     {w.category.__name__:<20} {w.message}")
    print("   -> DeprecationWarning 被 ignore 过滤掉，只剩两条 UserWarning")
    print()

    print("③ simplefilter 批量设置：")
    with warnings.catch_warnings(record=True) as captured:
        warnings.simplefilter("always")     # 所有警告都显示并全部记录
        emit_warnings()
        print(f"   simplefilter('always') 后捕获 {len(captured)} 条")
    with warnings.catch_warnings(record=True) as captured:
        warnings.simplefilter("ignore")     # 全部忽略
        emit_warnings()
        print(f"   simplefilter('ignore') 后捕获 {len(captured)} 条")
    with warnings.catch_warnings(record=True) as captured:
        warnings.simplefilter("error")      # 升级为异常
        try:
            emit_warnings()
            print("   没有异常（不该发生）")
        except UserWarning as e:
            print(f"   simplefilter('error') -> 抛出 {type(e).__name__}: {e}")
    print()

    # ===== 语法解析 =====
    # catch_warnings 上下文管理器的作用：
    #   1. 保存进入前的 filters 与 showwarning 状态
    #   2. 退出时完整恢复 —— 这是它最大的价值，避免污染全局配置
    #   3. record=True 时把警告收集到 list（元素是 WarningMessage 对象）
    # WarningMessage 对象有 .message / .category / .filename / .lineno 等属性。
    print("④ catch_warnings 的状态恢复保证：")
    before = len(warnings.filters)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        inside = len(warnings.filters)
    after = len(warnings.filters)
    print(f"   进入前过滤器数={before}, 块内={inside}, 退出后={after}")
    print("   -> 完全恢复，测试之间不会互相干扰")
    print()

    print("⑤ 同一位置的警告去重（default action）：")
    def same_place_warning():
        warnings.warn("同一条警告重复发出")
        warnings.warn("同一条警告重复发出")
    with warnings.catch_warnings(record=True) as captured:
        warnings.simplefilter("default")
        same_place_warning()
        print(f"   simplefilter('default') 捕获 {len(captured)} 条（同一位置去重）")
    with warnings.catch_warnings(record=True) as captured:
        warnings.simplefilter("always")
        same_place_warning()
        print(f"   simplefilter('always') 捕获 {len(captured)} 条（不去重）")
    print()
    print("【要点】过滤器从前往后第一条匹配者胜，越具体的规则越要靠前。")
    print("【要点】catch_warnings 必须在 finally 语义下恢复状态，推荐用 with 语法。")


def demo_6_warnings_to_exception():
    """把警告转成异常：测试与严格模式的利器。"""
    print("=" * 70)
    print("【6】warnings 转异常 —— 把「隐患」升级为「故障」")
    print("=" * 70)

    # ===== 语法解析 =====
    # 核心场景：pytest 中用 filterwarnings = ["error"] 让任何警告都变成测试失败，
    # 这样「将会出问题的隐患」在 CI 阶段就暴露，而不是上线后才发现。
    def deprecated_api_v1():
        warnings.warn("这个函数即将废弃，请改用 v2", DeprecationWarning)
        return "v1 的结果"

    def deprecated_api_v2():
        return "v2 的结果"

    print("① 默认情况下：DeprecationWarning 被忽略")
    print(f"   返回: {deprecated_api_v1()}（没有任何警告提示）")
    print()

    print("② 转成异常后立刻可见：")
    with warnings.catch_warnings():
        warnings.simplefilter("error", category=DeprecationWarning)
        try:
            deprecated_api_v1()
        except DeprecationWarning as e:
            print(f"   捕获到 {type(e).__name__}: {e}")
            print("   -> 可以在这里引导用户改用新 API")
    print()

    print("③ 批量检测一组旧 API（典型用法）：")
    def call_old_apis():
        results = {}
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("error")
            for name in ["v1", "v2"]:
                try:
                    results[name] = (deprecated_api_v1() if name == "v1"
                                     else deprecated_api_v2())
                except DeprecationWarning:
                    results[name] = "已替换为新实现"
        print(f"   逐个调用结果: {results}")
        print(f"   期间捕获警告: {[str(w.message) for w in caught]}")

    call_old_apis()
    print()

    print("④ -W 命令行参数（无需改代码）：")
    print("   python -W error your_script.py       # 所有警告变异常")
    print("   python -W ignore your_script.py      # 忽略所有警告")
    print("   python -W default your_script.py     # 默认行为（每个位置一次）")
    print("   python -W once your_script.py        # 整个程序只显示一次")
    print("   python -W always::DeprecationWarning your_script.py  # 精确指定")
    print()

    print("⑤ warnings.warn_explicit：手动指定文件名与行号")
    # warn_explicit 不使用调用栈，直接用传入的位置信息。
    # 适用于代码生成（模板、动态代码）等「没有真实源码位置」的场景。
    with warnings.catch_warnings(record=True) as captured:
        warnings.simplefilter("always")
        warnings.warn_explicit(
            "模板渲染时字段缺失",
            category=UserWarning,
            filename="template.j2",   # 伪造的文件名
            lineno=42,                      # 伪造的行号
        )
        for w in captured:
            print(f"   捕获: {w.category.__name__} @ {w.filename}:{w.lineno}")
            print(f"         {w.message}")
    print()


def demo_7_assert_vs_warning_vs_exception():
    """三种机制的选择对比。"""
    print("=" * 70)
    print("【7】assert vs warnings vs raise 的选型")
    print("=" * 70)

    comparison = [
        ("机制", "触发条件", "程序是否继续", "默认可见性", "典型用途"),
        ("assert", "内部不变量被破坏", "中断（AssertionError）", "总是", "开发者自检"),
        ("warnings.warn", "可能有问题但可继续", "继续执行", "看类别", "API 废弃提醒"),
        ("raise", "操作无法完成", "中断或被捕获", "-", "真实的错误"),
    ]
    # 打印对比表（中文列宽处理：直接用 ljust，终端会自动对齐）
    widths = [12, 22, 24, 14, 16]
    for i, row in enumerate(comparison):
        print("".join(c.ljust(w) for c, w in zip(row, widths)))
        if i == 0:
            print("-" * 88)
    print()

    print("同一问题的三种处理：")
    print("-" * 60)

    def process_config(strict: bool, path: str):
        """演示同一场景下三种机制的选择差异。"""
        if strict:
            # 配置错误无法继续 -> raise
            raise FileNotFoundError(f"配置文件不存在: {path}")
        else:
            # 只是提醒用户，且有默认行为 -> warn
            warnings.warn(f"配置文件不存在，使用默认配置: {path}")
            return {"debug": False}
        # 注意：这里不应该用 assert —— 配置文件不存在是外部因素，
        # 不是「开发者保证的不变量」，且 -O 下会失效

    print("strict=False（宽松模式，只警告）：")
    result = process_config(False, "/etc/app.conf")
    print(f"   返回默认配置: {result}")
    print()

    print("strict=True（严格模式，抛异常）：")
    try:
        process_config(True, "/etc/app.conf")
    except FileNotFoundError as e:
        print(f"   捕获到 {type(e).__name__}: {e}")
    print()

    print("选型口诀：")
    print("   assert  ->「我认为绝不会发生」")
    print("   warn    ->「可能有问题，但先不中断，你最好处理一下」")
    print("   raise   ->「真的没法继续了」")
    print()


def main():
    """主入口。"""
    print("=" * 70)
    print("assert 与 warnings")
    print("=" * 70)
    demo_1_assert_basics()
    print()
    demo_2_assert_pitfalls()
    print()
    demo_3_optimize_mode()
    print()
    demo_4_warnings_basics()
    print()
    demo_5_warning_filters()
    print()
    demo_6_warnings_to_exception()
    print()
    demo_7_assert_vs_warning_vs_exception()
    print()
    print("=" * 70)
    print("演示结束")
    print("=" * 70)
    print()
    print("提示：用 python -O 07_assert_and_warnings.py 再跑一次，")
    print("     可以亲眼看到 assert 相关的演示全部失效。")


if __name__ == "__main__":
    main()