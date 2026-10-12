"""
================================================================================
 02_typing_quality.py —— 类型注解与静态类型的正确用法
================================================================================

【演示的语法点】
  1. 基础注解      : int / str / float / bool / list[str] / dict[str, int]
  2. 注解的两种写法: `def f(a: int) -> str`  与  `f: Callable[[int], str] = ...`
  3. 默认值 + 注解 : 有默认值的参数仍要完整标注（含 None -> Optional）
  4. Optional      : `int | None`（Python 3.10+）取代 typing.Optional
  5. 泛型          : Generic[T] + TypeVar，类型在运行时被保留
  6. Protocol      : 结构化子类型（duck typing 的类型安全版）
  7. TypedDict     : 用「带类型的 dict」描述 JSON 结构
  8. Final / ClassVar : 标记不可变实例属性 / 类级常量
  9. 类型别名      : `type UserId = int`（3.12+）或显式 TypeAlias
  10. __annotations__ : 运行时反射读取注解 —— 类型注解本质是「存起来的数据」
  11. get_type_hints() : 求值字符串形式的注解（支持前向引用）
  12. dataclass + 注解: 自动生成 __init__/__repr__/__eq__

【⚠ 故意埋入的类型错误】（第 4 节，标注了 mypy 的真实报错文案）
  错误 1: 把 str 传给 int 参数           → arg-type
  错误 2: 返回值类型声明为 str 却 return int → return-value
  错误 3: Optional 取值后直接当 str 用   → union-attr / 返回 Optional 却声明 str
  错误 4: 违反 Protocol 的结构契约       → arg-type

【预期输出摘要】
  [1] 函数 __annotations__ 打印结果
  [2] 类属性注解、get_type_hints() 求值结果
  [3] Protocol 的 runtime_checkable isinstance 结果
  [4] 4 个类型错误的「运行时无害 / 静态检查报错」对照表
  [5] TypedDict 解析 JSON 的完整过程

【核心认知】
  类型注解在运行时是「存进 __annotations__ 的普通对象」，不会强制约束任何行为。
  真正的价值在于：编辑���提示 + mypy 静态检查 + 文档表达力。
"""

from __future__ import annotations   # ★ 让所有注解变成字符串，延迟求值

import json
import sys
from dataclasses import dataclass, field
from typing import (
    Any,
    Callable,
    Generic,
    Protocol,
    TypedDict,
    TypeVar,
    get_type_hints,
    runtime_checkable,
)


# ==============================================================================
# 一、基础注解：函数与类
# ==============================================================================
# ===== 语法解析 =====
# 语法：def 函数名(参数: 类型 = 默认值) -> 返回类型:
#   - 冒号后的部分叫「注解(annotation)」，只是元数据，不产生任何运行时约束
#   - 注意顺序：注解在冒号前，默认值在注解后（等价于 def f(a: int = 0)）
#   - -> 后是返回类型注解
#   - 没有默认值且在默认值参数之后的参数，是「仅位置/仅关键字」分隔符，不能标注解
# 为什么这么写：注解让阅读者一眼知道契约，也是 mypy/pyright 的唯一输入来源。

# 单一职责的纯函数：最容易推断类型的写法
def normalize_email(email: str) -> str:
    """规范化邮箱：小写 + 去空格。"""
    return email.strip().lower()


# 可变默认值陷阱的正确写法：用 None 哨兵，而不是 list/dict 字面量
# 为什么这么写：def f(items: list = []) 会在函数定义时创建一次空列表，
#              所有调用共享同一对象，是经典 BUG。
def collect(tag: str, items: list[str] | None = None) -> list[str]:
    """收集标签；若 items 为 None 则新建列表。"""
    if items is None:
        items = []          # 每次调用都拿到全新的独立列表
    items.append(tag)
    return items


# 多返回值用 tuple 注解；可变长度用元组包一层：tuple[int, ...]
def divmod_safe(a: float, b: float) -> tuple[float, float] | None:
    """安全除法：除数为 0 时返回 None（而非抛异常）。"""
    if b == 0:
        return None
    return a / b, a % b


# 可调用对象注解：Callable[[参数列表], 返回类型]
# 为什么这么写：Callable[[int, str], bool] 表示"接受一个 int 和一个 str，返回 bool"
Transformer = Callable[[str, bool], str]


def apply_transformer(fn: Transformer, raw: str) -> str:
    """把一个可调用对象作为参数传入——高阶函数的类型安全写法。"""
    return fn(raw, True)


def to_bool_strict(value: str, strict: bool) -> str:
    """演示用的可调用对象：把值转成布尔字符串。"""
    return f"{value}={bool(strict)}"


# ==============================================================================
# 二、类注解：属性 + 构造 + Final/ClassVar
# ==============================================================================
# ===== 语法解析 =====
# 语法：属性: 类型  —— 写在类体里，会进入 类.__annotations__
#   - 没有默认值的属性注解，只是声明，不会生成实际属性
#   - 在 __init__ 里 self.x: int = ... 或 self.x: int 赋值的才真正建立属性
# ClassVar  ：标记"这是类变量，不属于实例"，mypy 不会让你通过 self 改它
# Final     ：标记"此变量/属性不可重新赋值"，给读者一个强契约


class BankAccount:
    """银行账户：演示类级注解的三种写法。"""

    # ClassVar：类级常量，所有实例共享；mypy 禁止写 self.currency = ...
    currency: ClassVar[str] = "CNY"

    # 普通类属性注解 + 默认值：真正常量，存在类 __dict__ 里
    max_accounts: int = 1000

    # 仅注解无赋值：只是告诉类型检查器"实例上会有这个属性"
    owner: str
    balance: float

    def __init__(self, owner: str, initial: float = 0.0) -> None:
        # 参数校验放在边界处，是工程铁律
        if initial < 0:
            raise ValueError("初始余额不能为负数")
        self.owner = owner
        self.balance = initial
        self._history: list[str] = []   # 下划线前缀 = 约定上的私有

    def deposit(self, amount: float) -> None:
        """存款。"""
        if amount <= 0:
            raise ValueError("存款金额必须为正")
        self.balance += amount
        self._history.append(f"+{amount:.2f}")

    def withdraw(self, amount: float) -> None:
        """取款。金额不足时抛业务异常。"""
        if amount > self.balance:
            raise ValueError(f"余额不足：余额 {self.balance}，请求 {amount}")
        self.balance -= amount
        self._history.append(f"-{amount:.2f}")

    def summary(self) -> str:
        """返回账户摘要。"""
        # f-string 内使用 self 属性，格式化对齐让输出更整齐
        return f"[{self.owner}] {self.currency} {self.balance:>10.2f}"


# ==============================================================================
# 三、泛型、Protocol、TypedDict
# ==============================================================================
# ===== 语法解析 =====
# 语法：T = TypeVar("T")  +  class Box(Generic[T]):
#   - TypeVar 是"类型占位符"，Box[int] 和 Box[str] 是两个互不兼容的类型
#   - 泛型让容器/函数「对类型敏感」，而不是退化成 Any
# 为什么这么写：不用 Any 兜底，mypy 才能守住 int 容器不被塞进 str。

T = TypeVar("T")                 # 通用类型变量
K = TypeVar("K")                 # 键类型
V = TypeVar("V")                 # 值类型


class Box(Generic[T]):
    """泛型单值容器：装什么都行，但装进去的类型和取出来的类型必须一致。"""

    def __init__(self, item: T) -> None:
        self.item = item

    def get(self) -> T:
        """返回 item，类型被静态推断为 T。"""
        return self.item

    def map(self, fn: Callable[[T], V]) -> "Box[V]":
        """高阶映射：T -> V，返回新的 Box。这是泛型的精髓。"""
        # 类型转换注释告诉 mypy「这里确实是 Box[V]」
        return Box(fn(self.item))


class Cache(Generic[K, V]):
    """泛型 K->V 缓存，演示两个类型变量的组合。"""

    def __init__(self) -> None:
        # 只用于类型标注的空容器：dict() 本身是 dict 而非 dict[Any, Any]
        self._store: dict[K, V] = {}

    def put(self, key: K, value: V) -> None:
        self._store[key] = value

    def get_or(self, key: K, default: V | None = None) -> V | None:
        return self._store.get(key, default)

    def keys(self) -> list[K]:
        return list(self._store)


@runtime_checkable
class Serializable(Protocol):
    """Protocol（结构化子类型）：不要求继承，只要求「长得像」。

    运行时检查只校验「方法是否存在」，不校验签名 —— 这是 Protocol 的边界。
    要校验签名一致性需要第三方库 beartype 或 mypy 插件。
    """

    def to_dict(self) -> dict[str, Any]: ...


@runtime_checkable
class Comparable(Protocol):
    """可比较协议：一个比较方法。"""

    def __lt__(self, other: "Comparable") -> bool: ...


@dataclass(frozen=True, slots=True)   # frozen=不可变, slots=省内存(见 08 章)
class User:
    """用 dataclass 声明数据类：注解直接变成字段和构造函数参数。"""

    # 没有默认值 = 必填字段；有默认值的字段必须排在后面（Python 语法要求）
    user_id: int
    name: str
    email: str
    age: int = 18
    # field(default_factory=list) 是可变默认值的正确写法：
    # 每次实例化都调用一次 list()，各实例互不影响
    tags: list[str] = field(default_factory=list)

    def to_json(self) -> str:
        """序列化为 JSON。"""
        # default= 处理 dataclass 无法自动转换的自定义类型
        return json.dumps(
            {"user_id": self.user_id, "name": self.name, "tags": self.tags},
            ensure_ascii=False,
        )


class UserPayload(TypedDict):
    """TypedDict：用「带类型的 dict」精确描述 JSON 结构。

    与 dataclass 的区别：TypedDict 不做运行时校验，键缺失或类型错都不会报错，
    它的全部价值在静态检查阶段。
    """

    id: int
    name: str
    score: float
    active: bool


# ==============================================================================
# 四、故意写错的 4 个类型错误（教学用，切勿照抄进业务代码）
# ==============================================================================
# ===== 语法解析 =====
# 运行时行为：Python 完全不检查类型，以下函数照样能正常跑。
# 静态检查行为：mypy 会在 CI 阶段报错，把 bug 拦在部署之前。
# 这就是「动态语言 + 渐进式类型」的价值：类型不是运行时锁，而是编译期保险丝。


def error_1_wrong_arg_type(count: int) -> str:
    """❌ 错误 1：把 str 传给声明为 int 的参数。

    mypy 报错：
        error: Argument 1 to "error_1_wrong_arg_type" has incompatible type "str";
        expected "int"  [arg-type]
    """
    # 运行时：'5' 和 int 一样能参与计算，Python 不拦你
    return "收到 " + str(count)


def error_2_wrong_return(count: int) -> str:
    """❌ 错误 2：返回类型声明为 str，实际 return 了 int。

    mypy 报错：
        error: Incompatible return value type (got "int", expected "str")  [return-value]
    """
    return count + 1      # 运行时返回 6，类型却是 int


def error_3_optional_misuse(value: int | None) -> str:
    """❌ 错误 3：把 Optional[str] 直接当 str 返回，没做 None 判断。

    mypy 报错：
        error: Incompatible return value type (got "str | None", expected "str")
        error: Item "None" of "str | None" has no attribute "upper"  [union-attr]
    """
    # 正确写法应该是下面这样（已注释）：
    # if value is None:
    #     return "默认值"
    return value.upper()  # 若 value 为 None，运行时直接 AttributeError


def error_4_protocol_violation(item: int) -> str:
    """❌ 错误 4：传给要求 Serializable 协议的参数一个 int。

    mypy 报错：
        error: Argument 1 has incompatible type "int"; expected "Serializable"
               [arg-type]
    """
    return serialize(item)


def serialize(item: Serializable) -> str:
    """要求入参实现 Serializable 协议（拥有 to_dict 方法）。"""
    return json.dumps(item.to_dict(), ensure_ascii=False)


# ✅ 正确写法：满足协议的鸭子类型对象，静态检查通过
class GoodUser:
    """结构上符合 Serializable 协议（不需要继承任何东西）。"""

    def to_dict(self) -> dict[str, Any]:
        return {"name": "合规用户", "level": 9}


# ==============================================================================
# 五、运行时读取注解（类型注解的「真面目」）
# ==============================================================================
def show_annotations() -> None:
    """__annotations__ 本质是一个 dict，键是参数名，值是类型对象。"""
    # 从模块全局取 normalize_email 的注解
    raw = normalize_email.__annotations__
    print("  normalize_email.__annotations__ 原始值：")
    print(f"    {raw}")
    print(f"    类型 = {type(raw)}")

    # ★ 因为顶部写了 from __future__ import annotations，
    #   注解被「延迟求值」，存下来的是字符串而不是类型对象 —— 零运行时开销。
    print(f"    每个值的类型 = {type(list(raw.values())[0])}")

    # get_type_hints 会把字符串重新求值成真正的类型对象
    # 它还能解析前向引用（引号包起来的类名）
    resolved = get_type_hints(normalize_email)
    print(f"  get_type_hints() 求值后：")
    for name, hint in resolved.items():
        print(f"    {name:<8} -> {hint!r}  (类型对象: {type(hint).__name__})")

    # 类型别名本身也是对象，可以用 repr 打印
    print(f"  Transformer 别名本身 = {Transformer}")


def show_class_annotations() -> None:
    """类级别：__annotations__ 只含「有注解的类属性」，不含方法内的局部变量。"""
    print("  BankAccount.__annotations__（类属性注解）：")
    for key, value in BankAccount.__annotations__.items():
        print(f"    {key:<14} = {value}")

    # 方法的注解要从「类上取函数对象」再读
    print("  BankAccount.deposit.__annotations__（方法注解）：")
    for key, value in BankAccount.deposit.__annotations__.items():
        print(f"    {key:<10} = {value}")

    # get_type_hints 作用在类上，会递归解析所有方法的注解
    hints = get_type_hints(BankAccount)
    print(f"  get_type_hints(BankAccount) 解析出 {len(hints)} 条")

    # dataclass 把注解转成了真正的 fields，这是运行时反射的典型用法
    import dataclasses

    print("  dataclasses.fields(User)：")
    for f in dataclasses.fields(User):
        # repr=False / init=False 的字段在这里依然可见（除非用 field() 删掉）
        print(f"    {f.name:<10} type={f.type!r:<12} default={f.default!r}")


def show_protocol_runtime_check() -> None:
    """Protocol + runtime_checkable 可以在运行时做 isinstance 检查。"""
    print(f"  isinstance(GoodUser(), Serializable) = {isinstance(GoodUser(), Serializable)}")
    print(f"  isinstance(3, Serializable)           = {isinstance(3, Serializable)}")
    print(f"  isinstance([1,2], Comparable)        = {isinstance([1, 2], Comparable)}")
    print(f"  isinstance(object(), Comparable)     = {isinstance(object(), Comparable)}")
    print("  注意：只检查方法是否存在，不检查签名 —— 这是 Protocol 的已知限制")


def demo_typed_dict() -> None:
    """TypedDict 的价值：给 JSON 一个明确的结构契约。"""
    raw_json = '{"id": 7, "name": "小林", "score": 92.5, "active": true}'
    data: UserPayload = json.loads(raw_json)
    print(f"  原始 JSON : {raw_json}")
    print(f"  解析结果  : {data}")
    # TypedDict 就是普通 dict，下标访问；静态检查器能校验键名是否存在
    print(f"  data['score'] + 7.5 = {data['score'] + 7.5}")
    print("  运行时不做任何校验 —— 键写错要到 mypy 阶段才被发现")


def run_type_errors() -> None:
    """运行 4 个「类型错误」，展示它们的运行时真实后果。"""
    print("\n  类型错误              运行时实际结果                 静态检查(mypy)")
    print("  " + "-" * 78)

    # 错误 1
    try:
        out = error_1_wrong_arg_type("5")           # type: ignore[arg-type]
        print(f"  1 传 str 给 int      {out!r:<30} [arg-type]")
    except Exception as exc:                        # noqa: BLE001
        print(f"  1 传 str 给 int      运行时也炸了: {exc}")

    # 错误 2
    out2 = error_2_wrong_return(5)                  # type: ignore[return-value]
    print(f"  2 返回 int 给 str    {out2!r} (类型 {type(out2).__name__})".ljust(50)
          + " [return-value]")

    # 错误 3
    try:
        out3 = error_3_optional_misuse(None)        # type: ignore[union-attr]
        print(f"  3 Optional 未判空    {out3!r:<30} [union-attr]")
    except AttributeError as exc:
        print(f"  3 Optional 未判空    AttributeError: {exc}".ljust(50) + " [union-attr]")

    # 错误 4
    try:
        serialize(42)                               # type: ignore[arg-type]
    except (AttributeError, TypeError) as exc:
        print(f"  4 违反 Protocol      {type(exc).__name__}: {exc}".ljust(50) + " [arg-type]")

    # ✅ 正确对象调用 —— 静态与运行时双双通过
    print(f"  ✅ 正确调用 serialize(GoodUser()) -> {serialize(GoodUser())}")


def demo_generic_flow() -> None:
    """泛型 + dataclass 的组合使用。"""
    # Box[int] -> map(str) -> Box[str]：类型在流转中被精确保留
    int_box: Box[int] = Box(42)
    str_box: Box[str] = int_box.map(lambda x: f"答案={x}")
    print(f"  Box[int](42).get()          -> {int_box.get()!r}")
    print(f"  .map(str) 得到 Box[str]     -> {str_box.get()!r}")

    # 双类型变量缓存
    cache: Cache[str, User] = Cache()
    cache.put("u1", User(1, "张三", "zhangsan@example.com", 30))
    cache.put("u2", User(2, "李四", "lisi@example.com"))
    print(f"  Cache[str, User] 键        -> {cache.keys()}")
    print(f"  cache.get_or('u1')         -> {cache.get_or('u1')}")
    print(f"  cache.get_or('不存在')      -> {cache.get_or('none')}")

    # dataclass 自动生成的能力
    u1 = User(1, "张三", "a@b.c", 30, ["python"])
    u2 = User(1, "张三", "a@b.c", 30, ["python"])
    print(f"  dataclass 自动 __repr__ : {u1}")
    print(f"  dataclass 自动 __eq__   : u1 == u2 -> {u1 == u2}")
    print(f"  frozen=True 不可变       :")
    try:
        u1.name = "改名字"                          # type: ignore[misc]
    except Exception as exc:                        # FrozenInstanceError
        print(f"    赋值被拒 -> {type(exc).__name__}: {exc}")


def demo_python_version() -> None:
    """打印当前解释器版本与注解相关的能力开关。"""
    print(f"  Python 版本        : {sys.version.split()[0]}")
    print(f"  __future__.annotations 已启用（PEP 563）: True")
    print(f"  支持 PEP 604 联合类型 (int | None)     : {sys.version_info >= (3, 10)}")


# ==============================================================================
# 六、主流程
# ==============================================================================
def main() -> None:
    """类型注解完整演示。仅用标准库，无需安装 mypy 也能跑。"""
    print("=" * 78)
    print(" 02. 类型注解与静态类型质量")
    print("=" * 78)

    demo_python_version()

    print("\n[1] 运行时读取函数注解")
    print("-" * 78)
    show_annotations()

    print("\n[2] 运行时读取类与 dataclass 注解")
    print("-" * 78)
    show_class_annotations()

    print("\n[3] Protocol 运行时检查")
    print("-" * 78)
    show_protocol_runtime_check()

    print("\n[4] 泛型 + dataclass 实战")
    print("-" * 78)
    demo_generic_flow()

    print("\n[5] TypedDict 解析 JSON")
    print("-" * 78)
    demo_typed_dict()

    print("\n[6] 4 个故意写错的类型（运行时无害，mypy 会拦截）")
    print("-" * 78)
    run_type_errors()

    print("\n" + "=" * 78)
    print(" 工程要点：")
    print("   1. 类型注解是「编译期保险丝」，运行时零成本（配合 __future__）")
    print("   2. 从边界处开始标注（网络/文件/JSON 入口），收益最大")
    print("   3. 永远不要用 Any 糊弄 mypy —— 那是把类型检查关掉")
    print("   4. Protocol 做接口约束，泛型做容器约束，TypedDict 做数据契约")
    print("=" * 78)


if __name__ == "__main__":
    main()
