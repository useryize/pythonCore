"""
================================================================================
 06_args_kwargs.py  ——  *args / **kwargs 深入
================================================================================

【演示的语法点】
 1. *args 与 **kwargs 的本质：形参侧的【打包】vs 实参侧的【解包】
 2. 三种解包形态：*list/tuple、**dict、可混合
 3. 参数转发：装饰器/DLL 封装的通用写法
 4. 装饰器透传：如何写一个"完全透明"的装饰器
 5. 字典/集合字面量的解包：{**a, **b}, [*a, *b], {*a, *b}
 6. ★ 函数签名检查：inspect.signature / inspect.getfullargspec 的使用
 7. 形参五种类型的划分：位置专用 / 位置或关键字 / *args / 仅关键字 / **kwargs
 8. 调用时 Python 如何匹配实参与形参（完整算法）
 9. 常见坑：kwargs 键必须为 str；** 只能展开 mapping；* 可展开任何可迭代对象
10. 实参调用中 * 与 ** 的混用与冲突（同一参数传两次 → TypeError）

【预期输出摘要】
 - 匹配算法小节逐条打印：位置实参如何填满 a,b,c，剩下的进 args，剩余关键字进 kwargs
 - 签名检查小节打印三种 inspect 方式的输出
 - 冲突小节真实抛出 TypeError 并捕获
================================================================================
"""

from __future__ import annotations

import functools
import inspect
import time
from collections.abc import Callable, Iterable, Mapping, Sequence
from typing import Any


# ===== 语法解析 =====
# 【1】五种形参形态的完整签名
#   语法规则（顺序被 Python 强制，不可调换）：
#       def f(pos_only, /, normal=默认值, *args, kw_only=默认值, **kwargs)
#          └─仅位置─┘  └─位置或关键字─┘  └─可变位置─┘  └─仅关键字─┘  └─可变关键字─┘
#   任何 f(...) 调用，实参按三条规则匹配（详见 match_rules 逐步演示）：
#     R1. 位置实参从左往右依次填充"仅位置"和"位置或关键字"形参；
#     R2. 关键字实参按名字填入对应形参（*args/**kwargs 兜底接收剩余的）；
#     R3. 实参只能被消费一次 —— 一个形参/形参组不能被两个实参填。
def full_signature(a, /, b=10, *args, c=100, **kwargs) -> dict[str, Any]:
    """演示五种形参并存时的匹配结果。"""
    return {
        "a(仅位置)": a,
        "b(位置或关键字)": b,
        "args(可变位置)": args,          # args 恒为 tuple
        "c(仅关键字)": c,
        "kwargs(可变关键字)": kwargs,    # kwargs 恒为 dict
    }


# ===== 语法解析 =====
# 【2】参数转发：把任意实参原样传给另一个函数
#   这是**kwargs 最主要的生产用途：
#     - 装饰器（不知道被装饰函数的签名，只能"全收全转"）
#     - 包装 C 库 / DLL / HTTP 客户端（签名千变万化）
#     - 框架路由（参数由用户请求决定）
#   写法要点：形参列表里 **kwargs 必须排在最后。
def forward(func: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
    """把 args/kwargs 原样转发给 func，自己不解释任何参数。"""
    return func(*args, **kwargs)


# ===== 语法解析 =====
# 【3】★ 完全透明的装饰器
#   透明 = 调用方看不出被装饰（签名保持、异常透传、返回值不变）。
#   用 inspect.signature 可以在运行时【复制】原函数签名到 wrapper 上，
#   这样 IDE 与 inspect 都能看到正确的参数列表。
def trace_calls(func: Callable[..., Any]) -> Callable[..., Any]:
    """装饰器：打印调用轨迹，并复制原签名。"""
    # 复制签名：拿到原函数的 Signature 对象赋给 wrapper.__signature__。
    # 这样 inspect.signature(被装饰函数) 就等于 inspect.signature(原函数)。
    signature = inspect.signature(func)

    @functools.wraps(func)            # 复制 __name__/__doc__/等
    def wrapper(*args, **kwargs):
        # 把实参按"形参名"还原成可读形式，便于打印日志
        try:
            bound = signature.bind(*args, **kwargs)
            bound.apply_defaults()      # 补齐默认值，否则日志里看不到默认参数
            readable = f"{func.__name__}({', '.join(f'{k}={v!r}' for k, v in bound.arguments.items())})"
        except TypeError:
            readable = f"{func.__name__}(<签名不匹配的调用>)"
        print(f"    → 调用 {readable}")
        result = func(*args, **kwargs)
        print(f"    ← 返回 {result!r}")
        return result

    wrapper.__signature__ = signature  # ★ 额外一步：让 inspect 看到真签名
    return wrapper


@trace_calls
def create_user(name: str, /, age: int = 18, *, active: bool = True, **tags: str) -> dict:
    """创建一个用户字典。"""
    return {"name": name, "age": age, "active": active, "tags": tags}


# ===== 语法解析 =====
# 【4】* 的两种角色
#   形参侧 `*args`：打包剩余位置实参 → tuple
#   实参侧 `f(*x)` ：把可迭代对象 x 展开成多个位置实参 → 每个元素占一个位置
#   关键区别：* 可以展开【任何可迭代对象】（list/tuple/str/generator/range），
#            不要求是序列。
def test_star_unpack() -> None:
    print("    实参侧 * 解包 4 种可迭代对象：")
    print(f"      f(*[1,2,3])      → args={[1, 2, 3]}")
    print(f"      f(*(1,2))        → args={(1, 2)}")
    print(f"      f(*'ab')         → args={('a', 'b')}   # 字符串也是可迭代对象！")
    print(f"      f(*range(3))     → args={tuple(range(3))}")
    print(f"      f(*(i for i in [7,8])) → args={(7, 8)}   # 生成器也能展开")


def collect(*args: int) -> tuple[int, ...]:
    return args


# ===== 语法解析 =====
# 【5】** 解包：把 mapping 展开成关键字实参
#   限制：必须是 mapping（dict / Mapping / collections.abc.Mapping），
#         且键必须是【字符串】（因为关键字实参的名字必须是标识符）。
#   报错场景：
#     f(**{1: 'a'})    → TypeError: keywords must be strings
#     f(**[1, 2])      → TypeError: argument after ** must be a mapping
def test_double_star_unpack() -> None:
    d = {"b": 2, "c": 3}
    print(f"      collect(**{{'b':2}})  → {full_signature(1, **d)}")
    try:
        full_signature(1, **{1: "int key"})       # type: ignore[dict-item]
    except TypeError as exc:
        print(f"      ** 的键不是 str → TypeError: {exc}")
    try:
        full_signature(1, **[1, 2])               # type: ignore[arg-type]
    except TypeError as exc:
        print(f"      ** 后不是 mapping → TypeError: {str(exc)[:60]}")


# ===== 语法解析 =====
# 【6】字面量中的解包（Python 3.5+）
#   {**a, **b}  合并字典，右侧同键会【覆盖】左侧
#   [*a, *b]    合并列表
#   {*a, *b}    用可迭代对象的元素作为集合元素（去重）
#   设计意图：无需先建中间变量，可读性优于 update()/extend()。
def test_literal_unpack() -> None:
    base = {"host": "localhost", "port": 80}
    override = {"port": 8080, "debug": True}
    merged = {**base, **override}         # port 被 override 覆盖成 8080
    print(f"      {{**base, **override}} = {merged}")
    print(f"      原 base 未被修改 = {base}   # 解包产生新对象")
    print(f"      [*[1,2], *[2,3]] = {[*[1, 2], *[2, 3]]}")
    print(f"      {{*[1,2,2,3]}}    = {sorted({*[1, 2, 2, 3]})}   # 集合自动去重")


# ===== 语法解析 =====
# 【7】★ 函数签名检查（反射）
#   inspect.signature(f)      返回 Signature 对象（最通用，能穿透 __wrapped__）
#   inspect.getfullargspec(f) 返回 FullArgSpec 的 7 元组（老式 API，不穿透装饰器）
#   f.__code__.co_varnames    返回 (形参名..., *args名, **kwargs名) 的元组
#   设计意图：让"动态调用"成为可能 —— 这是框架、序列化、依赖注入的基础。
def inspect_signature(f: Callable[..., Any]) -> None:
    """演示三种签名检查方式。"""
    sig = inspect.signature(f)
    print(f"    inspect.signature({f.__name__}) -> {sig}")
    print(f"      参数列表：{list(sig.parameters)}")
    print(f"      返回注解：{sig.return_annotation}")

    for name, param in sig.parameters.items():
        # Parameter.kind 明确区分五种形态，是判断"能不能按位置传"的权威依据
        kind_name = {
            inspect.Parameter.POSITIONAL_ONLY: "仅位置",
            inspect.Parameter.POSITIONAL_OR_KEYWORD: "位置或关键字",
            inspect.Parameter.VAR_POSITIONAL: "可变位置(*args)",
            inspect.Parameter.KEYWORD_ONLY: "仅关键字",
            inspect.Parameter.VAR_KEYWORD: "可变关键字(**kwargs)",
        }[param.kind]
        has_default = "，有默认值" if param.default is not inspect.Parameter.empty else ""
        print(f"        {name:<9} 类型={kind_name:<20}{has_default}")

    spec = inspect.getfullargspec(f)
    print(f"    getfullargspec → args={spec.args}, varargs={spec.varargs}, "
          f"kwonlyargs={spec.kwonlyargs}, varkw={spec.varkw}")


def sample(a: int, b: str = "hi", /, *args: float, key: str = "k", **extra: object) -> bool:
    """用于签名检查的示例函数，覆盖五种形参。"""
    return True


# ===== 语法解析 =====
# 【8】易错点：同一参数被"传两次"
#   Python 严格遵循 R3：每个形参只能被一个实参填充。
#   f(1, a=2) 其中 a 是"仅位置"形参 → 看似"位置传一次+关键字传一次" → TypeError
#   f(1, b=2) 其中 b 是"位置或关键字"形参，会被位置实参占用，冲突 → TypeError
def test_conflicts() -> None:
    def f(a, /, b=1):
        return (a, b)

    print(f"      f(1, 2)            → {f(1, 2)}")
    try:
        f(1, b=2)          # b 同时被位置实参 2 和关键字 b=2 指定
    except TypeError as exc:
        print(f"      f(1, b=2) → TypeError: {exc}")
    try:
        f(1, a=2)          # a 是仅位置参数，不能用关键字
    except TypeError as exc:
        print(f"      f(1, a=2) → TypeError: {str(exc)[:70]}")


# ===== 语法解析 =====
# 【9】**kwargs 的键顺序保留
#   Python 3.7+ 保证 dict 插入有序，所以 **kwargs 的顺序 == 调用时书写顺序。
#   这在"参数合并/转发"场景中可预测，便于调试。
def kwargs_order() -> None:
    def collect(**kw):
        return list(kw.keys())
    print(f"      collect(z=1, a=2, m=3) 的键顺序 = {collect(z=1, a=2, m=3)}   # 保持书写顺序")


# ===== 语法解析 =====
# 【10】泛型包装器：*args/**kwargs 的最高级用法
#   通过 ParamSpec 保留任意函数签名（运行时则用 inspect 复制签名）。
#   工厂/策略等设计模式里常需要"任何签名的函数都能套"。
def make_logger(prefix: str) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """返回一个装饰器：给任意签名的函数加前缀日志。"""
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        sig = inspect.signature(func)
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            print(f"    [{prefix}] 调用 {func.__name__}，实参个数={len(args) + len(kwargs)}")
            return func(*args, **kwargs)
        wrapper.__signature__ = sig
        return wrapper
    return decorator


@make_logger("DB")
def execute_query(sql: str, timeout: float = 5.0, *, retry: int = 3) -> str:
    """模拟执行 SQL。"""
    return f"执行成功: {sql} (timeout={timeout}, retry={retry})"


def main() -> None:
    print("=" * 60)
    print("【1】★ 实参与形参的匹配算法（逐步演示）")
    print("=" * 60)
    print("  调用：full_signature(1, 2, 3, 4, c=5, extra=6)")
    print("  匹配过程：")
    print("    R1. 位置实参 1→a(仅位置)、2→b、3、4→ 无对应形参 → 进入 args")
    print("    R2. 关键字 c=5 → 匹配形参 c")
    print("    R3. 关键字 extra=6 → 无同名形参 → 进入 kwargs")
    for key, value in full_signature(1, 2, 3, 4, c=5, extra=6).items():
        print(f"    {key:<20} = {value!r}")

    print()
    print("  省略参数时的默认值填充：")
    print(f"    full_signature(1) → {full_signature(1)}")
    print("  全用关键字传（仅位置参数除外）：")
    print(f"    full_signature(1, b=2, z=9) → {full_signature(1, b=2, z=9)}")

    print()
    print("=" * 60)
    print("【2】参数转发")
    print("=" * 60)
    print(f"    forward(full_signature, 1, 2, 3, c=7) → "
          f"{forward(full_signature, 1, 2, 3, c=7)}")
    print("    转发函数不需要知道被调函数的任何签名，这是**kwargs 的核心价值。")

    print()
    print("=" * 60)
    print("【3】★ 完全透明的装饰器（含签名复制）")
    print("=" * 60)
    print("    调用过程：")
    user = create_user("张三", 20, active=False, role="admin", level=3)
    print(f"    结果：{user}")
    print()
    print("  装饰器如何做到'透明'：")
    print(f"    1) @functools.wraps 复制了 __name__ = {create_user.__name__}")
    print(f"    2) wrapper.__signature__ 让 inspect 看到真签名：")
    print(f"       {inspect.signature(create_user)}")
    print(f"    3) __wrapped__ 指向原函数：{hasattr(create_user, '__wrapped__')}")
    print("    三者叠加，调用方与 IDE 几乎察觉不到装饰器存在。")

    print()
    print("=" * 60)
    print("【4】实参侧 * 的解包：任意可迭代对象")
    print("=" * 60)
    test_star_unpack()
    print(f"    实际验证：collect(*{[1,2,3]}) = {collect(*[1, 2, 3])}")
    print(f"    实际验证：collect(*{'xy'})     = {collect(*'xy')}")
    print("    ★ * 要求可迭代，不要求序列；生成器也支持（但只能展开一次）。")

    print()
    print("=" * 60)
    print("【5】实参侧 ** 的解包：必须是 str 键的 mapping")
    print("=" * 60)
    test_double_star_unpack()

    print()
    print("=" * 60)
    print("【6】字面量解包")
    print("=" * 60)
    test_literal_unpack()

    print()
    print("=" * 60)
    print("【7】★ 函数签名检查")
    print("=" * 60)
    inspect_signature(sample)
    print()
    print("    两种 API 的区别：")
    print("      signature()      会穿透 __wrapped__ 看到『逻辑上真实』的签名")
    print("      getfullargspec() 不穿透装饰器，只能看到 *args/**kwargs")
    print(f"      被装饰后的 getfullargspec：{inspect.getfullargspec(create_user)}")
    print(f"      被装饰后的 signature：    {inspect.signature(create_user)}")
    print()
    print("    反射的实际用途：动态调用未知签名的函数（框架、依赖注入的基础）。")
    print(f"    根据签名自动调用示例：")
    sig = inspect.signature(full_signature)
    bound_args = sig.bind(10, 20)      # 只提供必需参数，其余用默认值
    bound_args.apply_defaults()        # 显式填充默认值
    print(f"      bind 后参数 = {dict(bound_args.arguments)}")
    print(f"      自动调用 → {full_signature(*bound_args.args, **bound_args.kwargs)}")

    print()
    print("=" * 60)
    print("【8】易错：同一实参被传两次")
    print("=" * 60)
    test_conflicts()
    print("    规则：一个形参只能被一个实参消费，重复指定必报 TypeError。")

    print()
    print("=" * 60)
    print("【9】**kwargs 的键顺序")
    print("=" * 60)
    kwargs_order()
    print("    Python 3.7+ dict 保序 → kwargs 顺序可预测，便于日志与调试。")

    print()
    print("=" * 60)
    print("【10】通用装饰器工厂（*args/**kwargs 的高阶用法）")
    print("=" * 60)
    print(f"    {execute_query('SELECT 1')}")
    print(f"    {execute_query('SELECT 2', timeout=1.0, retry=0)}")
    print(f"    签名依然透明：{inspect.signature(execute_query)}")

    print()
    print("=" * 60)
    print("【11】五种形参速查")
    print("=" * 60)
    print("  | 形态              | 关键字写法      | 位置写法 | 说明|")
    print("  |-------------------|-----------------|----------|------|")
    print("  | 仅位置 a          | ✗ 报错          | ✓        | 参数名可安全重命名|")
    print("  | 位置或关键字 b    | ✓ b=1           | ✓        | 最常用|")
    print("  | 可变位置 *args    | ✗               | ✓ 打包   | 得到 tuple|")
    print("  | 仅关键字 c        | ✓ 必须 c=1      | ✗ 报错   | 提升可读性|")
    print("  | 可变关键字**kwargs| ✓ 兜底          | ✗        | 得到 dict|")
    print()
    print("  必记：*,** 出现在【形参】= 打包；出现在【实参】= 解包。")


if __name__ == "__main__":
    main()