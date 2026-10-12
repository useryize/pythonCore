"""
================================================================================
 07_typing.py  ——  typing：类型注解体系
================================================================================

【演示的语法点】
 1. 基本注解：变量注解 / 函数参数与返回值
 2. Union[X, Y] 与 X | Y；Optional[X] ≡ Union[X, None]
 3. Literal：字面量约束（枚举语义）
 4. Annotated：附加元数据
 5. TypeVar / Generic：泛型，协变与不变
 6. Protocol：结构化子类型（鸭子类型的静态版）
 7. overload：用多个签名表达"同一函数的不同参数组合"
 8. TypeAlias：给复杂类型起别名
 9. NewType：编译期类型安全的"标签"
 10. ★ 运行时行为：__annotations__、get_type_hints、get_origin/get_args

【预期输出摘要】
 - "运行时" 小节：打印函数字典 __annotations__ 的实际内容
 - "get_type_hints" 小节：解析字符串注解并自动处理名字作用域
 - "overload" 小节：展示多个重载签名的注册情况
================================================================================

"""

from __future__ import annotations   # ★ 让所有注解延迟为字符串，避免前向引用问题

import sys
import typing
from typing import (Any, Callable, ClassVar, Generic, Literal, NamedTuple, NewType, Optional, Protocol,
                    TypeVar, TypedDict, Union, cast, final, get_args, get_origin, get_type_hints,
                    overload, runtime_checkable)

# from __future__ import annotations 的影响（务必理解）：
#   开启后，所有注解都变成【字符串】，如 "int" 而不是 int。
#   好处：可以引用尚未定义的名字（前向引用）、注解不产生运行时开销
#   代价：运行期读注解拿到的是字符串，需 get_type_hints() 才能解析成类型对象


# ===== 语法解析 =====
# 【1】基本注解：注解在运行时几乎不起作用，主要服务于静态检查
#   语法规则：变量: 类型 = 值 / def f(a: T) -> R
#   关键认知：Python 不会因为注解错误而拒绝执行！
def demo_basics() -> None:
    # 变量注解（PEP 526）
    count: int = 10
    name: str = "Python"
    items: list[int] = [1, 2, 3]
    mapping: dict[str, int] = {"a": 1}

    # ⚠ 注解【不做运行时校验】：写错类型照样能跑
    wrong: int = "我其实是字符串"     # 运行时完全合法！
    print(f"  标注为 int 的值实际是：{type(wrong).__name__} = {wrong!r}")
    print(f"     ← 证明注解只是给 mypy/pyright 看的【提示】，运行时不管")

    # 函数注解
    def add(a: int, b: int) -> int:
        """两个数相加。"""
        return a + b

    print(f"  add(1, 2) = {add(1, 2)}")
    print(f"  add.__annotations__ = {add.__annotations__}")
    # ⚠ 注意：因为开了 from __future__ import annotations，这里拿到的是【字符串】
    print(f"  值实际类型：{type(add.__annotations__['return'])} = "
          f"{add.__annotations__['return']!r}   ← 字符串！")

    # 嵌套注解会被展平到顶层字典（不做树形结构）
    def outer(x: int, y: "list[str]") -> "dict[str, int]":
        return {y[0]: x}
    print(f"  嵌套注解的 __annotations__ 键：{list(outer.__annotations__)}")
    print(f"     类型注解在函数对象上是【扁平字典】，与参数顺序一致")

    # 容器类型注解的两种写法
    legacy: typing.List[int] = [1, 2, 3]     # 老写法（3.9 前必需）
    modern: list[int] = [1, 2, 3]            # 新写法（3.9+ 内置泛型）
    print(f"  typing.List[int] 与 list[int] 都可用：{legacy == modern}")
    print(f"     运行时 {type(legacy)} == {type(modern)}（都只是 list）")

    # ClassVar：声明"这是类变量而非实例变量"
    class Config:
        VERSION: ClassVar[str] = "1.0"       # 类变量：所有实例共享
        name: str                              # 实例变量

    print(f"  ClassVar 标注类属性：Config.VERSION = {Config.VERSION}")
    print(f"     __annotations__ 中标记了它是类变量：{Config.__annotations__}")

    # Final：声明"此变量不再改变"
    MAX_SIZE: typing.Final[int] = 100
    print(f"  Final 标注常量：MAX_SIZE = {MAX_SIZE}")


# ===== 语法解析 =====
# 【2】Union / Optional / | ：联合类型
#   语法规则：
#     Union[int, str]  或  int | str       （3.10+ 写法）
#     Optional[int]    等价于 Union[int, None]  ≡  int | None
#   设计意图：NoneType 不是任何类型的子类，所以必须显式联合才能表示"可能为 None"
def demo_union() -> None:
    # 三种等价写法
    a: Union[int, str] = 1
    b: int | str = "x"
    c: typing.Union[int, str] = 2.5       # 运行时不做检查，随便赋
    print(f"  a={a}, b={b}, c={c}   ← 注解不校验运行值")

    # Optional 的含义
    def find_user(uid: int) -> Optional[str]:
        """可能找到也可能返回 None。"""
        return None if uid < 0 else f"user_{uid}"

    print(f"  find_user(1) = {find_user(1)}，find_user(-1) = {find_user(-1)}")

    # Optional[X] 与 Union[X, None] 完全等价
    print(f"  Optional[int] == Union[int, None] → "
          f"{Optional[int] == Union[int, None]}")
    print(f"  Optional[int] 就是 int | None   → {Optional[int] == (int | None)}")

    # ⚠ 经典坑：默认参数是 None 时，注解要写 Optional，否则静态检查器会报错
    def connect(host: Optional[str] = None) -> str:
        """host 可以是 None。"""
        return f"连接 {host or 'localhost'}"
    print(f"  connect() = {connect()}")

    # 用 Literal 收紧字符串取值（比 Union[str, ...] 更精确）
    Status = Literal["pending", "success", "failed"]
    def handle(status: Status) -> str:
        return f"处理状态: {status}"
    print(f"  handle('success') = {handle('success')}")

    # Annotated：给类型附加元数据（供框架/校验器使用）
    UserId = typing.Annotated[int, "用户ID，必须为正数"]
    uid: UserId = 1001
    print(f"  Annotated 类型 = {UserId}")
    print(f"     运行时 Annotated 的 __metadata__ = {UserId.__metadata__}")
    print(f"     底层的真实类型（get_args）= {get_args(UserId)}")


# ===== 语法解析 =====
# 【3】TypeVar / Generic：泛型
#   语法规则：
#     T = TypeVar("T")                    声明一个类型变量
#     class Box(Generic[T]): ...          泛型类：__init__(self, item: T)
#     def first(items: list[T]) -> T: ... 泛型函数
#   设计意图：表达"输入输出类型之间有关联"（如 list[T] → T），
#             这是普通注解做不到的。
#   核心特性：约束（bound）、上限（covariant=True）等
T = TypeVar("T")                      # 无约束的类型变量
NumberT = TypeVar("NumberT", int, float)    # 受限：只能是 int 或 float
BoundedT = TypeVar("BoundedT", bound=int)   # 约束：必须是 int 的子类
# 协变：T_co 只能出现在【返回值】位置
T_co = TypeVar("T_co", covariant=True)
# 不变（默认）：既能输入又能输出
T_inv = TypeVar("T_inv")


def demo_generic() -> None:
    print(f"  TypeVar 名称与约束：T={T}, NumberT 约束={NumberT.__constraints__}, "
          f"BoundedT 上界={BoundedT.__bound__}")
    print(f"  T_co 的标志 covariant = {T_co.__covariant__}")

    # 泛型类：栈
    class Stack(Generic[T]):
        """一个类型安全的栈：Stack[int] 只能装 int。"""

        def __init__(self) -> None:
            self._items: list[T] = []          # ★ 用 T 标注内部存储

        def push(self, item: T) -> None:
            self._items.append(item)

        def pop(self) -> T:
            if not self._items:
                raise IndexError("栈为空")
            return self._items.pop()

        def peek(self) -> T | None:
            return self._items[-1] if self._items else None

        def __len__(self) -> int:
            return len(self._items)

    # 使用
    int_stack: Stack[int] = Stack()
    int_stack.push(1)
    int_stack.push(2)
    print(f"  Stack[int] 栈顶 = {int_stack.peek()}，长度 = {len(int_stack)}")
    print(f"  pop() = {int_stack.pop()}，再 pop() = {int_stack.pop()}")

    str_stack: Stack[str] = Stack()
    str_stack.push("hello")
    print(f"  Stack[str] 栈顶 = {str_stack.peek()}")
    # ⚠ 运行时不做检查，push("混进去") 也能跑（但 mypy 会报错）

    try:
        int_stack.pop()
    except IndexError as e:
        print(f"  ⚠ 空栈 pop → IndexError: {e}")

    # 泛型函数
    def first_item(items: list[T]) -> T:
        """返回列表第一个元素；声明保证了返回值类型与列表类型一致。"""
        if not items:
            raise ValueError("空列表")
        return items[0]

    print(f"  first_item([1,2,3]) = {first_item([1, 2, 3])}")
    print(f"  first_item(['a','b']) = {first_item(['a', 'b'])}")

    # 多类型参数
    K = TypeVar("K")
    V = TypeVar("V")

    def invert(mapping: dict[K, V]) -> dict[V, K]:
        """反转字典：K、V 是两个独立类型变量。"""
        return {v: k for k, v in mapping.items()}

    print(f"  invert({{'a':1}}) = {invert({'a': 1})}")

    # 实战：类型安全的缓存容器
    class Cache(Generic[K, V]):
        def __init__(self) -> None:
            self._store: dict[K, V] = {}

        def put(self, key: K, value: V) -> None:
            self._store[key] = value

        def get(self, key: K) -> V | None:
            return self._store.get(key)

    cache: Cache[str, int] = Cache()
    cache.put("hits", 42)
    print(f"  Cache[str,int].get('hits') = {cache.get('hits')}")


# ===== 语法解析 =====
# 【4】★ Protocol：结构化子类型（鸭子类型的静态版）
#   语法规则：
#     @runtime_checkable
#     class Writer(Protocol):
#         def write(self, data: str) -> int: ...
#   设计意图：Python 的"鸭子类型"是运行时的；
#             Protocol 把它提升到【编译期】——
#             只要你有这些方法，就算实现了这个"接口"，无需显式继承。
#   对比 ABC（抽象基类）：必须显式继承才能满足类型检查
#   ⚠ runtime_checkable 的 Protocol 只能检查【方法名是否存在】，
#     不能检查方法【签名是否匹配】。
def demo_protocol() -> None:
    @runtime_checkable
    class Writer(Protocol):
        """任何有 write 方法的对象都算 Writer。"""
        def write(self, data: str) -> int: ...

    @runtime_checkable
    class Closer(Protocol):
        def close(self) -> None: ...

    class FileWriter:                          # ★ 注意：没有继承任何 Protocol
        def __init__(self) -> None:
            self.data: list[str] = []

        def write(self, data: str) -> int:
            self.data.append(data)
            return len(data)

    class NetworkWriter:
        def write(self, data: str) -> int:
            return len(data)

    class NotAWriter:                          # 没有 write 方法
        def read(self) -> str:
            return ""

    fw = FileWriter()
    nw = NetworkWriter()
    naw = NotAWriter()

    # isinstance 检查（需要 @runtime_checkable）
    print(f"  isinstance(FileWriter(), Writer)   = {isinstance(fw, Writer)}")
    print(f"  isinstance(NetworkWriter(), Writer) = {isinstance(nw, Writer)}   ← 没继承也通过")
    print(f"  isinstance(NotAWriter(), Writer)    = {isinstance(naw, Writer)}   ← 缺 write 方法")
    print(f"  isinstance(FileWriter(), Closer)    = {isinstance(fw, Closer)}")

    # 实战：一个函数接受任何"可写"的东西
    def dump(obj: Writer, data: str) -> None:
        """接受任何实现了 write 的对象。"""
        written = obj.write(data)
        print(f"      写入 {data!r}，返回 {written} 字符")

    print("  ★ 结构化子类型实际应用：")
    dump(fw, "文件内容")
    dump(nw, "网络内容")
    # dump(naw, "x")  # ⚠ 类型检查器会报错，但运行时仍能调用（duck typing）

    # 组合多个 Protocol（鸭子类型的"多重继承"）
    @runtime_checkable
    class ReadWrite(Writer, Closer, Protocol):
        """既有 write 又有 close。"""
        pass

    class Resource:
        def write(self, data: str) -> int:
            return len(data)

        def close(self) -> None:
            print("      资源已关闭")

    res = Resource()
    print(f"  组合协议 isinstance(Resource(), ReadWrite) = {isinstance(res, ReadWrite)}")
    try:
        dump(fw, "测试")           # FileWriter 没有 close
        print(f"  FileWriter 满足 ReadWrite？{isinstance(fw, ReadWrite)}")
    except Exception:
        pass

    # ⚠ 局限演示：方法名存在但签名不匹配，isinstance 仍返回 True
    class WrongSignature:
        def write(self, *args, **kwargs) -> None:    # 签名完全不同
            pass
    print(f"  ⚠ 签名不匹配也是 True：isinstance(WrongSignature(), Writer) = "
          f"{isinstance(WrongSignature(), Writer)}")
    print("     → runtime_checkable 只检查【方法名】，不检查签名；严格检查需靠 mypy")


# ===== 语法解析 =====
# 【5】★ overload：用多个签名表达同一函数的不同调用形式
#   语法规则：
#     @overload
#     def f(x: int) -> int: ...        ← 这些函数体只有 ...，运行时被丢弃
#     @overload
#     def f(x: str) -> str: ...
#     def f(x): ...                    ← 真正执行的实现
#   设计意图：一个函数可以有多种调用形式（如处理 int 或 str），
#             但实现只有一个；@overload 让类型检查器知道所有合法组合。
#   ⚠ 运行时行为：所有 @overload 装饰过的函数都被替换掉，
#     最后那个实现才是真正可调用的。typing.get_overloads() 可取回签名。
def demo_overload() -> None:
    # 定义：处理 int 或 str 的函数
    @overload
    def process(data: int) -> str: ...          # 重载签名 1：int → str

    @overload
    def process(data: str) -> int: ...          # 重载签名 2：str → int

    def process(data: int | str) -> str | int:  # 真正的实现
        """根据输入类型返回另一种类型。"""
        if isinstance(data, int):
            return str(data * 2)                # int → str
        return len(data)                        # str → int

    print(f"  process(21) = {process(21)!r}   （int 入，str 出）")
    print(f"  process('abc') = {process('abc')}   （str 入，int 出）")

    # ★ 运行时：实现函数只有一个，注解是合并的
    print(f"  实现函数的 __name__ = {process.__name__}")
    print(f"  实现函数的注解 = {process.__annotations__}")

    # get_overloads 取回所有重载签名（3.11+）
    if hasattr(typing, "get_overloads"):
        overloads = typing.get_overloads(process)
        print(f"  get_overloads 注册了 {len(overloads)} 个重载签名：")
        for ov in overloads:
            print(f"      {ov.__annotations__}")

    # 实战：处理表格数据的格式化函数
    @overload
    def to_cell(value: int, width: int) -> str: ...
    @overload
    def to_cell(value: str, width: int, align: str) -> str: ...
    def to_cell(value: int | str, width: int, align: str = "<") -> str:
        """数字默认右对齐，字符串默认左对齐。"""
        if isinstance(value, int):
            return f"{value:>{width}}"          # > 右对齐
        return f"{value:<{width}}"              # < 左对齐

    print(f"  to_cell(42, 8)      = {to_cell(42, 8)!r}   ← 右对齐")
    print(f"  to_cell('hi', 8)    = {to_cell('hi', 8)!r}   ← 左对齐")
    print(f"  to_cell('hi', 8, '>') = {to_cell('hi', 8, '>')!r}   ← 显式右对齐")

    # ⚠ 没有 @overload 的写法：参数类型被迫联合，丢失精确性
    print("  ⚠ 不加 @overload 只能写 Union[int,str]，再在函数体内用 isinstance 分流")


# ===== 语法解析 =====
# 【6】TypeAlias / NewType：类型别名与新类型
#   语法规则：
#     Vector = list[float]                       # 普通别名
#     type Vector = list[float]                  # 3.12+ 新语法 type 语句
#     UserId = NewType("UserId", int)            # 新类型（底层还是 int）
#   设计意图：
#     TypeAlias 只是"给复杂类型起个短名字"，可读性工具
#     NewType 创建【运行时的新类型】，让 mypy 拒绝把 str 传给 UserId 参数
def demo_typealias() -> None:
    # TypeAlias：类型别名
    Vector = typing.Union[tuple[float, float], list[float]]
    Coord = dict[str, float]
    Handler = Callable[[str, int], bool]

    def process_point(p: Vector) -> float:
        return sum(p)
    print(f"  别名定义后：process_point((1,2)) = {process_point((1, 2))}")

    # 3.12+ 的 type 语句（更明确的类型别名语法）
    if sys.version_info >= (3, 12):
        type NewVec = list[float]       # ★ 显式声明"这是类型别名"
        nv: NewVec = [1.0, 2.0]
        print(f"  type 语句别名 NewVec = {nv}")
        print(f"     运行时 NewVec 就是 list[float]：{NewVec}")
    else:
        print(f"  当前 Python {sys.version_info.major}.{sys.version_info.minor} < 3.12，"
              f"不支持 type 语句")

    # NewType：编译期类型安全标签
    UserId = NewType("UserId", int)        # 运行时仍是一个 int 的"别名"
    OrderId = NewType("OrderId", int)

    def get_user(uid: UserId) -> str:
        return f"用户{uid}"
    print(f"  get_user(UserId(1)) = {get_user(UserId(1))}")
    # ⚠ 运行时 NewType 就是 int，可以传普通 int 进去（不做检查）
    print(f"  get_user(1) 也能跑   = {get_user(1)}   ← 运行时不检查，mypy 会报错")
    print(f"  UserId(5) = {UserId(5)}，实际类型 = {type(UserId(5))}   ← 调用即返回原值")
    print(f"  UserId.__supertype__ = {UserId.__supertype__}   ← 底层就是 int")
    print(f"  UserId 和 OrderId 是不同对象：{UserId is not OrderId}（底座都是 int）")
    print(f"  ⚠ NewType 现在是类对象：type(UserId) = {type(UserId)}")
    print(f"     所以不能 issubclass(UserId, int)（会 TypeError），要用 __supertype__")


# ===== 语法解析 =====
# 【7】★ 运行时行为：注解在运行期到底是什么
#   关键函数：
#     __annotations__          直接访问，拿到的是原始注解（开启 future 后是字符串）
#     get_type_hints()         解析字符串 → 真实类型对象，能处理名字作用域
#     get_origin(T)            取泛型的"容器类型"：list[int] → list
#     get_args(T)              取泛型的参数：list[int] → (int,)
#     get_type_hints(类)        解析类的所有方法注解
#   ★ 面试高频：注解在运行时基本是"字符串"，要用 get_type_hints 才有意义
def demo_runtime() -> None:
    import sys as _sys

    # 定义一个带各种注解的函数
    def sample(a: int, b: str, c: list[int], d: "int | None" = None) -> dict[str, int]:
        return {}

    # 1. 直接访问 __annotations__（开启 future 后是字符串字典）
    raw = sample.__annotations__
    print("  ── __annotations__（原始值）──")
    for k, v in raw.items():
        print(f"      {k:<10}: {v!r:<20} 类型={type(v).__name__}")

    # 2. get_type_hints：解析成真正的类型对象
    print("  ── get_type_hints()（解析后）──")
    resolved = get_type_hints(sample)
    for k, v in resolved.items():
        print(f"      {k:<10}: {v!r:<22} 类型={type(v).__name__}")

    # 3. get_origin / get_args：拆解泛型
    print("  ── 泛型拆解 ──")
    examples = [list[int], dict[str, list[int]], Union[int, str], int | None, Literal["a", "b"]]
    for ex in examples:
        print(f"      {str(ex):<30} origin={get_origin(ex)}  args={get_args(ex)}")

    # 常见对应关系
    print("  ── 常用映射 ──")
    print(f"      get_origin(list[int])          = {get_origin(list[int])}")
    print(f"      get_origin(Dict[str, int])     = {get_origin(typing.Dict[str, int])}")
    print(f"      get_origin(Union[int, str])    = {get_origin(Union[int, str])}")
    print(f"      get_origin(int | None)         = {get_origin(int | None)}")

    # 4. 类的注解
    class Model:
        table: str = "users"
        columns: list[str] = ["id", "name"]

        def find(self, id: int) -> "Model | None":
            return None

    print(f"  ── 类的注解 ──")
    print(f"      Model.__annotations__ = {Model.__annotations__}")
    print(f"      get_type_hints(Model) = {get_type_hints(Model)}")
    # ⚠ find 的返回类型是 "Model | None"（自引用），但 Model 定义在【局部作用域】，
    #    get_type_hints 默认只看全局命名空间 → NameError。
    #    解决办法：把类型定义在模块级，或显式传 localns
    try:
        get_type_hints(Model.find)
    except NameError as e:
        print(f"      ⚠ get_type_hints(Model.find) → NameError: {e}")
        print(f"         （自引用 + 局部作用域导致，属于预期行为）")
    hints = get_type_hints(Model.find, localns={"Model": Model})
    print(f"      ✅ 传 localns 后解析成功：{hints}")

    # 5. ★ get_type_hints 能解析局部名字吗？—— 不能，需传 localns/globalns
    def local_defined() -> None:
        class Special:  ...
        def f(x: Special) -> Special: return x
        try:
            get_type_hints(f)          # 'Special' 不在全局作用域 → NameError
            print("      （意外）解析成功")
        except NameError as e:
            print(f"      ⚠ get_type_hints 对【局部定义】的类型会 NameError：{e}")
            print(f"      ✅ 解决办法：把类型提到模块级，或传 localns 字典")
            # 正确写法：提供作用域
            hints = get_type_hints(f, localns={"Special": Special})
            print(f"      传 localns 后：{hints}")

    local_defined()

    # 6. cast：不改变运行时，只影响静态检查
    value = "123"           # 实际是 str
    num = cast(int, value)  # 告诉检查器"这是 int"（运行时还是 str）
    print(f"  ── cast ──")
    print(f"      cast(int, '123') 返回 {num!r}，运行时类型仍是 {type(num).__name__}")
    print(f"      → cast 只影响静态检查器的推断，不做任何转换！")


# ===== 语法解析 =====
# 【8】TypedDict / NamedTuple / final：其他常用工具
def demo_extras() -> None:
    # TypedDict：描述字典的"形状"（运行时就是普通 dict）
    class Movie(TypedDict):
        title: str
        year: int
        rating: float

    m: Movie = {"title": "肖申克的救赎", "year": 1994, "rating": 9.3}
    print(f"  TypedDict = {m}，运行时类型 = {type(m).__name__}   ← 就是普通 dict")
    # ⚠ 不能用属性访问：m.title 会报错
    try:
        m.title
    except AttributeError as e:
        print(f"  ⚠ TypedDict 不能属性访问：AttributeError")

    # NamedTuple：带类型的具名元组
    class Point(NamedTuple):
        x: int
        y: int

    p = Point(1, 2)
    print(f"  NamedTuple = {p}，可哈希 = {hash(p) is not None}，字段 = {Point._fields}")
    print(f"     用 _replace 改字段 = {p._replace(x=10)}")

    # final：标记"不能被继承/覆盖"（仅类型检查层面）
    @final
    def critical_function() -> str:
        """标记为不可被子类覆盖。"""
        return "关键逻辑"

    print(f"  @final 函数 = {critical_function()}   ← 运行时与普通函数无差别")

    # 可调用对象的类型
    AddFunc = Callable[[int, int], int]
    def add(x: int, y: int) -> int:
        return x + y
    print(f"  Callable 注解 AddFunc 是否匹配 add：{get_type_hints(add)['return'] == int}")

    # 协变 / 逆变的直观理解
    print("  ── 协变对照 ──")
    print("     covariant=True  → 只能用在返回位置，如 Iterable[Dog] 可当 Iterable[Animal]")
    print("     默认不变         → 输入输出都用同一个 TypeVar")


def main() -> None:
    print("=" * 60)
    print("【1】基本注解：运行时不做校验")
    print("=" * 60)
    demo_basics()

    print()
    print("=" * 60)
    print("【2】Union / Optional / Literal / Annotated")
    print("=" * 60)
    demo_union()

    print()
    print("=" * 60)
    print("【3】TypeVar / Generic 泛型")
    print("=" * 60)
    demo_generic()

    print()
    print("=" * 60)
    print("【4】Protocol 结构化子类型")
    print("=" * 60)
    demo_protocol()

    print()
    print("=" * 60)
    print("【5】@overload 重载")
    print("=" * 60)
    demo_overload()

    print()
    print("=" * 60)
    print("【6】TypeAlias / NewType")
    print("=" * 60)
    demo_typealias()

    print()
    print("=" * 60)
    print("【7】运行时行为：__annotations__ 与 get_type_hints")
    print("=" * 60)
    demo_runtime()

    print()
    print("=" * 60)
    print("【8】TypedDict / NamedTuple / final / Callable")
    print("=" * 60)
    demo_extras()

    print()
    print("=" * 60)
    print("小结")
    print("=" * 60)
    print("  1. 注解运行时【不校验】，类型错也照跑；静态价值靠 mypy")
    print("  2. 开了 __future__ annotations 后注解变字符串，用 get_type_hints 解析")
    print("  3. Optional[X] ≡ Union[X, None] ≡ X | None")
    print("  4. TypeVar 表达类型间关联；Stack[int] 运行时不检查但 mypy 检查")
    print("  5. Protocol 无需继承即可满足；isinstance 只查方法名不查签名")
    print("  6. @overload 的签名运行时被丢弃，只有最后一个实现真正生效")
    print("  7. NewType 运行时就是原类型，作用在静态检查；cast 不做转换")
    print("  8. get_origin/get_args 拆解泛型是运行时反射的关键")


if __name__ == "__main__":
    main()