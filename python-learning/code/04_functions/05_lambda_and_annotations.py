"""
================================================================================
 05_lambda_and_annotations.py  ——  lambda 与类型注解
================================================================================

【演示的语法点】
 1. lambda 表达式：单表达式匿名函数，只能写一个表达式（无语句）
 2. lambda 是"函数对象"，可立即调用 (lambda x: x*2)(5)，本质是 (lambda x: x*2) 后接调用
 3. 排序 key 的使用：sorted(key=)/list.sort(key=)/min/max(key=)
 4. 多重排序、stable sort、operator.itemgetter/attrgetter
 5. 类型注解语法：参数注解、返回值注解、可变参数的注解写法
 6. TypedDict：描述"结构化的 dict"，运行时是普通 dict，只对类型检查器有意义
 7. Protocol：结构化子类型（structural subtyping），Python 的"鸭子类型 + 静态检查"
 8. ParamSpec：让装饰器保留被装饰函数的参数签名（PEP 612）
 9. TypeVar / Generic：泛型标注
10. ★ 类型注解的运行时影响：Python 注解【默认不生效】，纯提示；只有显式调用
    get_type_hints 才求值；__annotations__ 可直接读取原始注解对象

【预期输出摘要】
 - lambda 匿名性、闭包行为（loop 捕获 lambda 的循环变量陷阱）
 - 排序小节按姓名/年龄多重排序的完整输出
 - Protocol 小节验证 isinstance 依赖 runtime_checkable
 - 最后一节打印 get_type_hints 求值结果 与 纯字符串注解(from __future__ import annotations)的差别
================================================================================
"""

from __future__ import annotations
# ★ 本文件顶部启用 PEP 563：所有注解在运行时被存成【字符串】，不立即求值。
#   这是现代 Python 的最佳实践：前向引用无需引号、typing.get_type_hints 之外零开销。

import functools
import inspect
import operator
import time
import typing
from collections.abc import Callable, Iterable, Mapping, Sequence
from typing import Any, Generic, ParamSpec, TypeVar, Union, get_type_hints

# PEP 612：P 捕获被装饰函数的完整参数列表
P = ParamSpec("P")
# TypeVar：类型变量，代表"任意某种类型"
R = TypeVar("R")
Num = TypeVar("Num", int, float)   # 受限 TypeVar：只能是 int 或 float


# ===== 语法解析 =====
# 【1】lambda 表达式语法
#   语法规则：lambda [参数列表]: 表达式
#   - 只能有【一个表达式】，不能写赋值、不能写 if 语句、不能写 for
#   - 需要复杂逻辑时，用三元表达式  a if cond else b  代替 if 语句
#   - 等价转换：lambda x: expr  ≡  def f(x): return expr
#   - 立刻执行需要加括号：(lambda x: x*2)(5)
#   设计意图：为"临时、无名字、只用一次"的函数提供简洁语法。
#   易错点：lambda 的作用域遵循 LEGB，循环里创建 lambda 会晚绑定（与闭包同源问题）。
square = lambda x: x * x                     # 命名 lambda：能工作但风格不佳，PEP8 不推荐
double = lambda x: x * 2                    # 典型的"只用一次"场景更推荐直接写 lambda


def add_five(x: int) -> int:
    return x + 5                             # 需要多行/文档时用 def 更清晰


# ===== 语法解析 =====
# 【2】lambda 的立即调用 (IIFE 风格)
#   语法：(lambda 参数: 表达式)(实参)
#   执行过程：
#     ① 解释器构造 function 对象；
#     ② 立刻把它当函数调用，传入实参；
#     ③ 表达式求值后整体丢弃（无引用 → 被垃圾回收）。
#   常见于"需要立刻求值又不想定义有名字的函数"的场景，如排序的 key。
def apply_twice(func: Callable[[int], int], value: int) -> int:
    """把函数当参数传入：函数是一等公民的直接证据。"""
    return func(func(value))


# ===== 语法解析 =====
# 【3】闭包创建器：用工厂函数返回 lambda
#   每次调用工厂得到新的 cell，因此互不干扰（与 02 的闭包同源）。
def make_adder(n: int) -> Callable[[int], int]:
    """返回一个加 n 的函数。这是 lambda 闭包的最小示例。"""
    return lambda x: x + n           # n 被捕获进 cell


# ===== 语法解析 =====
# 【4】类型注解：参数注解 + 返回值注解
#   语法规则：def f(a: int, b: str = "x") -> bool: ...
#   运行时行为：注解存入函数对象的 __annotations__ 字典，默认不做任何检查。
#   注意：x: int = 5 中的 `x: int` 只是"声明"，把 x 赋字符串运行也不报错。
def calculate_price(base: float, rate: float = 0.13, *, precision: int = 2) -> str:
    """计算含税价格，返回格式化字符串。"""
    total = base * (1 + rate)
    return f"{total:.{precision}f}"        # 嵌套格式化：精度来自变量


# ===== 语法解析 =====
# 【5】*args / **kwargs 的注解写法
#   *args: int              等价于 每个位置元素是 int（元组元素注解）
#   **kwargs: float         等价于 每个关键字值是 float
#   *args: *Ts               变长元组的元组展开（Python 3.11+ 支持）
#   **kwargs: Unpack[TD]     TypedDict 配合 **kwargs 的精确类型（3.11+）
def total_score(*scores: int, **weights: float) -> tuple[int, dict[str, float]]:
    """任意多个整数分数 + 任意多个浮点权重。"""
    return sum(scores), dict(weights)


# ===== 语法解析 =====
# 【6】TypedDict —— 用类语法声明"字典的形状"
#   运行时 TypedDict 的实例就是普通 dict（isinstance 会通过类检查失败/通过，
#   但 dict 行为不变）；它的价值在于【类型检查器】能校验键和值的类型。
#   注意：TypedDict 不能有默认值，不能有方法（本质是一个"类型说明"而非"行为类"）。
class Movie(typing.TypedDict):
    """一部电影的结构化字典。继承 typing.TypedDict 得到的是一个新"类"，
    但它产出的对象就是普通 dict —— TypedDict 只增加结构描述，不增加行为。"""
    title: str            # 必填键：值必须是 str
    year: int             # 必填键
    rating: float         # 必填键


class PartialMovie(typing.TypedDict, total=False):
    """全可选的字典（total=False 让所有键变成可选）。"""
    title: str
    year: int


# ===== 语法解析 =====
# 【7】Protocol —— 结构化子类型（PEP 544）
#   核心思想："鸭子类型"的静态版本。
#   只要一个类【结构上】满足 Protocol 要求的方法/属性，无需继承即可被视为该类型。
#   - @runtime_checkable 让 isinstance 可用（但只检查方法名是否存在，不检查签名/类型）。
#   - 注意：Protocol【不能实例化】，只能被"实现"。
def close_all() -> None:
    """关闭所有资源。"""
    print("  资源已全部关闭")


def write_log(msg: str) -> None:
    """写入日志。"""


@typing.runtime_checkable
class Closable(typing.Protocol):
    """结构化协议：只要有 close() 方法就满足。
    ★ @runtime_checkable 是必需的：没有它 isinstance() 会直接抛 TypeError
      （Protocol 的运行时检查属于「尽力而为」，只验证属性名存在，不验证签名/类型）。"""
    def close(self) -> None: ...


class FileWriter:
    """隐式实现 Closable：无需显式继承，但结构上满足协议。"""
    def __init__(self, path: str) -> None:
        self.path = path

    def close(self) -> None:
        print(f"  关闭文件 {self.path}")


class NotClosable:
    """没有 close 方法，不满足协议。"""
    def open(self) -> None: ...


# ===== 语法解析 =====
# 【8】ParamSpec：让装饰器"类型透明"
#   问题：普通装饰器写成 `def deco(f: Callable[..., Any])` 会丢失原函数参数类型。
#   ParamSpec P 能捕获原函数的 (参数类型列表)，使装饰后签名在类型检查器眼里不变。
#   这让日志装饰器、重试装饰器对 IDE 和 mypy 都"透明"。
def logged(func: Callable[P, R]) -> Callable[P, R]:
    """用 ParamSpec 保留原函数的参数与返回值类型。"""
    @functools.wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        print(f"  [ParamSpec] 调用 {func.__name__}")
        return func(*args, **kwargs)         # args/kwargs 的类型被识别为 P
    return wrapper


@logged
def join_strings(a: str, b: str, sep: str = "-") -> str:
    return sep.join((a, b))


# ===== 语法解析 =====
# 【9】Generic + TypeVar：可复用的泛型容器标注
#   运行时 Generic 子类的 __class_getitem__ 会返回 typing 别名；
#   用 get_origin / get_args 可反解。
class Stack(Generic[R]):
    """一个简单的泛型栈标注。"""

    def __init__(self) -> None:
        self._items: list[R] = []

    def push(self, item: R) -> None:
        self._items.append(item)

    def pop(self) -> R:
        return self._items.pop()

    def __repr__(self) -> str:
        return f"Stack({self._items!r})"


# ===== 语法解析 =====
# 【10】★ 类型注解的运行时影响（重点澄清）
#   事实：Python 的类型注解是【惰性】的、默认不影响运行。
#   - 函数注解存于 func.__annotations__，不求值（配合 future import 更是纯字符串）
#   - 变量注解（x: int = 5）连 __annotations__ 都不一定写（模块级才写）
#   - 真正强制类型靠：a) 类型检查器（mypy/pyright，静态）  b) 显式运行时校验（pydantic/beartype）
#   - typing.get_type_hints() 会在【运行时】真正解析字符串注解，是获取真实类型的途径。
def runtime_annotations_demo() -> None:
    def sample(a: int, b: str = "x", *args: float, **kwargs: bool) -> list[int]:
        return [a]

    raw = sample.__annotations__
    print(f"  原始 __annotations__（因 future import 全是字符串）：{raw}")
    resolved = get_type_hints(sample)
    print(f"  get_type_hints() 求值后：{resolved}")
    print(f"  键集合一致：{set(raw) == set(resolved)}")
    print(f"  __annotations__ 是普通 dict：{isinstance(raw, dict)}")
    # 类型检查器视角：sample(1) 合法，sample('a') 非法 —— 但运行期两者都跑！
    print(f"  运行时 sample('a', 'b') 也照样返回：{sample('a', 'b')!r}  ← 注解不拦截")


def main() -> None:
    print("=" * 60)
    print("【1】lambda 基础")
    print("=" * 60)
    print(f"  square(5) = {square(5)}   # 命名 lambda")
    print(f"  立即调用 (lambda x: x*2)(5) = {(lambda x: x * 2)(5)}")
    print(f"  立即调用并传多参 = {(lambda a, b: a ** b)(2, 10)}")
    print(f"  lambda 的类型：{type(square)}   # 依然是普通函数对象")
    print(f"  有 __name__：{square.__name__!r}  # 命名后才有意义")
    anon = lambda x: x
    print(f"  匿名 lambda 的 __name__ = {anon.__name__!r}  # 定界符 '<lambda>'")
    print(f"  lambda 只能一个表达式 → 复杂逻辑用三元："
          f"{(lambda x: '大' if x > 10 else '小')(50)}")
    print(f"  apply_twice(square, 3) = {apply_twice(square, 3)}   # 函数当参数传递")
    print(f"  add_five 作为值：{add_five(1)}")

    print()
    print("=" * 60)
    print("【2】lambda 闭包工厂")
    print("=" * 60)
    add10 = make_adder(10)
    add100 = make_adder(100)
    print(f"  add10(1)={add10(1)}, add100(1)={add100(1)}  # 各自捕获不同的 n")
    print(f"  add10 捕获的自由变量：{add10.__code__.co_freevars}")

    print()
    print("=" * 60)
    print("【3】★ 排序中的 lambda / key")
    print("=" * 60)
    people = [("赵", 30), ("钱", 25), ("孙", 35), ("李", 25)]
    print(f"  原始：{people}")
    by_age = sorted(people, key=lambda p: p[1])
    print(f"  按年龄升序：{by_age}")
    by_age_desc = sorted(people, key=lambda p: -p[1])
    print(f"  按年龄降序（用 - 取负）：{by_age_desc}")
    by_age_then_name = sorted(people, key=lambda p: (p[1], p[0]))
    print(f"  多级排序 (年龄, 姓名)：{by_age_then_name}   # 元组比较，先比年龄再比姓名")
    # 反例：用元组第一个元素排序会按中文 Unicode 码点（不是拼音）
    print(f"  ⚠ 直接按姓名排序是按 Unicode 码点，不是拼音：{sorted(people, key=lambda p: p[0])}")

    print()
    print("  排序稳定性演示（同 key 时保持原相对顺序）：")
    raw = [("a", 1), ("b", 1), ("c", 0), ("d", 1)]
    stable = sorted(raw, key=lambda x: x[1])
    print(f"    原始：{raw}")
    print(f"    按 key 排序：{stable}   # 三个 1 保持 a,b,d 原顺序 → Python sort 稳定")

    print()
    print("  operator 模块：key 的高性能替代（避免调用 Python 层 lambda）")
    users = [{"name": "李雷", "age": 30}, {"name": "韩梅梅", "age": 25}]
    # attrgetter 取【属性】，itemgetter 取【键】。下面的类实例供 attrgetter 使用。
    class User:
        def __init__(self, name: str, age: int) -> None:
            self.name = name
            self.age = age

        def __repr__(self) -> str:
            return f"User({self.name!r}, {self.age})"

    print(f"    itemgetter('age')：{sorted(users, key=operator.itemgetter('age'))}")
    user_objs = [User("李雷", 30), User("韩梅梅", 25)]
    print(f"    attrgetter('name')：{sorted(user_objs, key=operator.attrgetter('name'))}")
    print(f"    itemgetter('age','name') 多键："
          f"{sorted(users, key=operator.itemgetter('age', 'name'))}")

    print()
    print("  list.sort vs sorted 的区别：")
    lst = [3, 1, 2]
    ret = lst.sort(key=lambda x: -x)
    print(f"    lst.sort(...) 返回 {ret!r}  ← 返回 None！它是【原地排序】")
    print(f"    但 lst 已被修改为 {lst}")
    print(f"    sorted(...) 返回新列表，不改原列表")

    print()
    print("  min/max 也接受 key：")
    print(f"    max(people, key=lambda p: p[1]) = {max(people, key=lambda p: p[1])}")
    print(f"    min(people, key=lambda p: p[1]) = {min(people, key=lambda p: p[1])}")

    print()
    print("=" * 60)
    print("【4】类型注解：函数 / 变量 / 可变参数")
    print("=" * 60)
    print(f"  calculate_price(100)         = {calculate_price(100)}")
    print(f"  calculate_price(100, 0.2)    = {calculate_price(100, 0.2)}")
    print(f"  precision 仅关键字：         = {calculate_price(100, precision=4)}")
    print(f"  total_score(1,2,3, a=1.0)    = {total_score(1, 2, 3, a=1.0)}")
    # 变量注解：只对静态检查器有意义，运行期不校验
    count: int = 42
    label: str = "计数"
    print(f"  变量注解：count={count} ({type(count).__name__}), label={label}")

    print()
    print("=" * 60)
    print("【5】TypedDict：字典的结构化标注")
    print("=" * 60)
    m: Movie = {"title": "星际穿越", "year": 2014, "rating": 9.4}
    print(f"  创建 Movie：{m}")
    print(f"  运行时类型仍是 dict：{type(m)}")
    print(f"  用 TypedDict 类实例化：{Movie(title='盗梦空间', year=2010, rating=9.3)}")
    print(f"  必填校验（静态检查器职责，运行期不拦）：")
    try:
        # 运行期照常成功，因为 TypedDict 就是一个 dict 工厂
        bad = Movie(title="缺字段")     # type: ignore[typeddict-item]
        print(f"    运行期未拦截：{bad}   ← 静态检查器才会报错")
    except Exception as exc:
        print(f"    {type(exc).__name__}: {exc}")
    partial: PartialMovie = {}
    print(f"  total=False 全可选：{partial!r}   # 空字典也合法")

    print()
    print("=" * 60)
    print("【6】Protocol：鸭子类型的静态版")
    print("=" * 60)
    print(f"  FileWriter 结构上满足 Closable（它并没有写 class FileWriter(Closable)）：")
    fw = FileWriter("data.txt")
    close_all()                        # 无关演示：调用一个普通函数
    fw.close()                         # 结构化子类型：靠方法存在即可被当资源用
    print(f"  isinstance(FileWriter实例, Closable) = {isinstance(fw, Closable)}   # True，靠结构而非继承")
    print(f"  isinstance(NotClosable实例, Closable) = "
          f"{isinstance(NotClosable(), Closable)}   # False，缺 close 方法")
    print(f"  Closable 能否实例化？", end=" ")
    try:
        Closable()                      # Protocol 类不能被实例化
    except TypeError as exc:
        print(f"TypeError: {exc}")
    print("  说明：Protocol 是【结构化】而非【名义化】继承 —— 不需要写 class X(Closable)。")

    print()
    print("=" * 60)
    print("【7】ParamSpec：类型透明的装饰器")
    print("=" * 60)
    print(f"  join_strings('a','b') = {join_strings('a', 'b')}")
    print(f"  join_strings('a','b','sep=/') = {join_strings('a', 'b', sep='/')}")
    print(f"  wraps 保留了 __wrapped__：{hasattr(join_strings, '__wrapped__')}")
    sig = inspect.signature(join_strings)
    print(f"  inspect.signature 看到原签名：{sig}   # ParamSpec 在类型层 + __wrapped__ 在运行层共同保证透明")
    print(f"  ParamSpec P 本体：{P}")
    print(f"  P.args = {P.args}, P.kwargs = {P.kwargs}   # 这两个属性携带原始参数信息")

    print()
    print("=" * 60)
    print("【8】Generic：泛型容器")
    print("=" * 60)
    st: Stack[int] = Stack()
    st.push(1)
    st.push(2)
    print(f"  Stack[int] 实例：{st}")
    print(f"  pop() 返回 {st.pop()}（元素类型由 R=TypeVar 泛化）")
    print(f"  Stack[int] 是 typing 别名：{Stack[int]}, origin={typing.get_origin(Stack[int])}")
    print(f"  get_args(Stack[int]) = {typing.get_args(Stack[int])}")
    print(f"  注意：泛型只影响静态检查，运行时不做类型校验。")

    print()
    print("=" * 60)
    print("【9】★ 类型注解的运行时影响（澄清常见误解）")
    print("=" * 60)
    runtime_annotations_demo()
    print("  总结：注解在运行期是【惰性字符串】，不拦截任何调用。")
    print("  强制类型的三种手段：")
    print("    1) 静态：mypy / pyright 在【运行前】检查（主流方案）")
    print("    2) 运行时：typing.get_type_hints 手动求值，或用 pydantic 校验数据")
    print("    3) 手动：在函数体里 isinstance 断言（繁琐但明确）")
    print(f"  性能：注解几乎零开销。测试反射开销：")
    # 测量 with-statement 与纯函数调用的耗时差异，说明注解开销可忽略
    def noop() -> None:
        pass

    t0 = time.perf_counter()
    for _ in range(100000):
        noop()
    plain = time.perf_counter() - t0
    # 测量 10 万次调用（含解包返回）的耗时，说明注解/反射开销可忽略
    t1 = time.perf_counter()
    for _ in range(100000):
        sample_fn(1)
    annot = time.perf_counter() - t1
    print(f"    100k 次调用：无注解 {plain:.4f}s vs 带注解 {annot:.4f}s（差异属噪声，非注解成本）")


def sample_fn(a: int, b: str = "x") -> bool:
    """带完整注解的示例函数，用于开销对比。"""
    return bool(a)


if __name__ == "__main__":
    main()