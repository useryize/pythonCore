"""
================================================================================
  06_dataclass.py  ——  数据类、枚举、协议与命名元组
================================================================================

【演示的语法点】
 1. ★ dataclass 全部参数：frozen / order / eq / repr / unsafe_hash /
      kw_only / slots / match_args / weakref_slot / kw_only
 2. ★ field() 的全部用法：默认值、default_factory、init/repr/compare、
      metadata、kw_only
 3. ★ dataclass 与普通类的对比（代码量、内存、速度）
 4. dataclass 继承、默认值与可变默认值的坑
 5. ★ Enum：成员定义、别名、@unique、IntEnum、Flag、Enum 的方法
 6. ★ Protocol：结构化子类型、runtime_checkable、泛型 Protocol
 7. ★ NamedTuple：带类型的命名元组
 8. TypedDict：字典的结构化类型标注
 9. dataclass 最佳实践与选型（什么时候用 dataclass / NamedTuple / Enum）

【预期输出摘要】
 - "全部参数" 小节逐个演示每个参数的实际效果（frozen 抛 FrozenInstanceError 等）
 - "field" 小节打印 default_factory 解决可变默认值的对比
 - "对比" 小节打印 dataclass vs 普通类的代码量/内存/速度对比
 - "Enum" 小节打印成员遍历、别名、IntEnum 求和结果
 - "Protocol" 小节打印 isinstance 的结构化检查结果
================================================================================

"""

from __future__ import annotations

import sys
import timeit
from dataclasses import (
    dataclass,
    field,
    FrozenInstanceError,
    asdict,
    astuple,
    fields,
    replace,
)
from enum import Enum, Flag, IntEnum, auto, unique
from typing import Any, Dict, List, Optional, Protocol, runtime_checkable
from typing import NamedTuple, TypedDict


# ==============================================================================
# 【第一部分】dataclass 基础：自动生成样板代码
# ==============================================================================
# ===== 语法解析 =====
# @dataclass 装饰器：自动为类生成 __init__ / __repr__ / __eq__
#   语法：@dataclass 装饰在 class 上方。
#   原理：扫描类中标注了类型注解的字段（__annotations__），
#         据此生成 __init__(self, 字段=默认值...) 等方法。
#   设计意图：消除"只为了存数据的类"的样板代码，让数据类定义聚焦于【字段语义】。
#   关键：只有【有类型注解】的字段才会被识别为数据字段（没注解的不算）。
@dataclass
class PointBasic:
    """最基础的 dataclass：自动生成 __init__、__repr__、__eq__。"""

    x: int                                   # 必填字段（无默认值）
    y: int = 0                               # 带默认值的字段（必须放在必填字段之后！）

    def distance(self) -> float:              # 自定义方法照常写，dataclass 不管它
        return (self.x ** 2 + self.y ** 2) ** 0.5


def demo_basics() -> None:
    print("=" * 60)
    print("【1】dataclass 基础：自动生成哪些方法？")
    print("=" * 60)

    p = PointBasic(3, 4)
    print()
    print(f"  PointBasic(3, 4)      = {p}        ← __repr__ 自动生成")
    print(f"  p.x, p.y              = {p.x}, {p.y}")
    print(f"  p.distance()          = {p.distance():.1f}    ← 自定义方法正常可用")
    print(f"  PointBasic(x=3, y=4)  = {PointBasic(x=3, y=4)}    ← 支持关键字参数")

    print()
    print("  ── 自动生成的方法 ──")
    print(f"    有 __init__？{ '__init__' in PointBasic.__dict__ }")
    print(f"    有 __repr__？{ '__repr__' in PointBasic.__dict__ }")
    print(f"    有 __eq__   ？{ '__eq__' in PointBasic.__dict__ }")
    print(f"    有自定义 distance？{ 'distance' in PointBasic.__dict__ }")

    print()
    print("  ── __eq__ 自动生成：按所有字段比较 ──")
    print(f"    PointBasic(3,4) == PointBasic(3,4) → {PointBasic(3, 4) == PointBasic(3, 4)}")
    print(f"    PointBasic(3,4) == PointBasic(4,3) → {PointBasic(3, 4) == PointBasic(4, 3)}")

    print()
    print("  ── ★ 字段顺序规则：默认值字段不能排在必填字段前面 ──")
    print("  （下面的写法会报错：")
    print("      @dataclass")
    print("      class Bad:")
    print("          x: int = 0     # 有默认值")
    print("          y: int           # 无默认值 ← TypeError: non-default argument follows default")
    print("      所以：必填字段在前，带默认值的字段在后。")

    print()
    print("  ── ★ 没加类型注解的字段【不会】被当作数据字段 ──")

    @dataclass
    class Mixed:
        a: int                               # 有注解 → 是字段
        b = "默认值"                          # 无注解 → 只是类属性，不是字段

    m = Mixed(1)
    print(f"    a 是字段（出现在 init 参数里）✓")
    print(f"    b 不是字段（只是普通类属性）：Mixed.a={m.a}, Mixed.b={Mixed.b}")
    try:
        Mixed(1, "新值")                      # b 不在 __init__ 里
    except TypeError as exc:
        print(f"    ★ 所以 b 不能通过构造函数传：TypeError: {exc}")


# ==============================================================================
# 【第二部分】★ dataclass 全部参数
# ==============================================================================
# ===== 语法解析 =====
# @dataclass(init, repr, eq, order, unsafe_hash, frozen, match_args,
#             kw_only, slots, weakref_slot)
#   下面逐个参数演示其作用与默认行为。
@dataclass(frozen=True, slots=True)            # ★ 最常用的"不可变数据类"
class PointFrozen:
    """frozen=True：不可变（创建后不能改字段）。slots=True：省内存。

    ★ frozen=True 会：
      ① 覆盖 __setattr__ 和 __delattr__，赋值时抛 FrozenInstanceError
      ② 自动生成 __hash__（因为不可变，可安全哈希）
    ★ slots=True 生成 __slots__，不创建实例 __dict__，省内存。
    """
    x: int
    y: int = 0


@dataclass(order=True)                          # 生成 __lt__ __le__ __gt__ __ge__
class Version:
    """order=True：可比较（生成 < <= > >=）。

    ★ 前提：所有字段本身也要可比较，否则比较时会抛 TypeError。
    ★ 比较规则：按字段【声明顺序】逐个比较（元组式比较）。
    """
    major: int
    minor: int
    patch: int = 0


@dataclass(eq=False, repr=False)                # 关闭自动生成的 eq 和 repr
class RawData:
    """eq=False：不生成 __eq__（改用身份比较 is）。repr=False：不生成 __repr__。

    ★ 适用：大对象（比较很贵）或不关心表示的场景。
    """
    name: str
    data: List[int]

    def __repr__(self) -> str:                 # 手动定义 repr（覆盖关闭的效果）
        return f"<RawData {self.name}>"


@dataclass(kw_only=True)                        # 强制关键字参数
class ConfigKwOnly:
    """kw_only=True：字段只能用【关键字】传参，不能按位置传。

    ★ 好处：① 避免位置传参搞错顺序 ② 允许默认值字段排在必填字段【前面】
      ③ 与默认值无关（unrelated to default 的限制被解除）
    """
    debug: bool = False
    workers: int = 1
    name: str = "未命名"


def demo_all_parameters() -> None:
    print()
    print("=" * 60)
    print("【2】★ dataclass 全部参数逐个演示")
    print("=" * 60)

    # --- frozen ---
    print()
    print("  ── frozen=True：不可变 ──")
    pf = PointFrozen(1, 2)
    print(f"    PointFrozen(1,2) = {pf}")
    print("    ", end="")
    try:
        pf.x = 99                             # 不可变，赋值报错
    except FrozenInstanceError as exc:
        print(f"    pf.x = 99 → FrozenInstanceError: {exc}")
    print("    ★ frozen=True 让对象不可变，且【自动可哈希】（可用于 dict 键）")
    print(f"    hash 可用：{{pf: '点'}} = { {pf: '点'} }")

    # --- slots ---
    print()
    print("  ── slots=True：省内存 + 防动态属性 ──")
    print("    ", end="")
    try:
        pf.new_attr = 1                        # slots 不允许新属性
    except AttributeError as exc:
        print(f"    加新属性 → AttributeError（slots 白名单机制）")
    print("    ★ slots 通过生成 __slots__ 省掉实例 __dict__，大对象省内存明显")

    # --- order ---
    print()
    print("  ── order=True：生成比较运算符 ──")
    v1 = Version(1, 2, 3)
    v2 = Version(1, 3, 0)
    v3 = Version(2, 0, 0)
    print(f"    v1={v1}  v2={v2}  v3={v3}")
    print(f"    v1 < v2   = {v1 < v2}    ← __lt__（按 major,minor,patch 逐个比）")
    print(f"    v2 < v3   = {v2 < v3}")
    print(f"    v1 < v3   = {v1 < v3}")
    print(f"    v3 > v1   = {v3 > v1}")
    print("    ★ order=True 要求所有字段【可比较】（否则运行时 TypeError）。")

    # --- eq=False / repr=False ---
    print()
    print("  ── eq=False / repr=False：关闭自动生成 ──")
    r1, r2 = RawData("a", [1]), RawData("a", [1])
    print(f"    两个内容相同但身份不同的 RawData：")
    print(f"      r1 == r2  = {r1 == r2}   （eq=False → 退化为 is 身份比较）")
    print(f"      r1 is r2  = {r1 is r2}")
    print(f"      repr      = {r1}   （repr=False 但手动定义了 __repr__，用手动的）")

    # --- kw_only ---
    print()
    print("  ── kw_only=True：强制关键字传参 ──")
    print("  （注意：这里 debug/workers/name 都有默认值，但 kw_only 仍强制用 = 传）")
    cfg = ConfigKwOnly(debug=True, workers=4)   # 关键字传参
    print(f"    ConfigKwOnly(debug=True, workers=4) = {cfg}")
    print("    ", end="")
    try:
        ConfigKwOnly(True, 4)                  # 位置传参应报错
    except TypeError as exc:
        print(f"位置传参 ConfigKwOnly(True, 4) → TypeError（kw_only 要求关键字）")

    # --- unsafe_hash ---
    print()
    print("  ── unsafe_hash=True：为可变对象生成 __hash__（谨慎使用） ──")

    @dataclass(unsafe_hash=True)                # 显式生成 __hash__
    class MutableHashed:
        """警告：字段可变时哈希值会变，若已入 dict/set 会【丢失查找能力】。"""
        a: int

    mh = MutableHashed(1)
    print(f"    hash(MutableHashed(1)) = {hash(mh)}   ← unsafe_hash 生成了 __hash__")
    print("    ★ 为什么叫『unsafe』：修改 a 后 hash 会变，若它已在 set 里就再也找不到。")

    # --- match_args ---
    print()
    print("  ── match_args=True：支持位置参数的 match/case 匹配 ──")
    print(f"    PointFrozen.__match_args__ = {getattr(PointFrozen, '__match_args__', '不存在')}")
    print("    ★ 有了它，match p: case PointFrozen(x, y): 可用位置匹配。")

    # --- field() ---
    print()
    print("  ── field()：精细控制字段 ──")

    @dataclass
    class WithFields:
        """演示 field() 的各参数。"""
        # init=False：不进 __init__，在 __post_init__ 中赋值
        created_at: str = field(default="2024-01-01", init=False)
        # default_factory：可变默认值的正确解法（每次调用生成新对象）
        items: List[int] = field(default_factory=list)
        # metadata：附加元信息（不参与比较，供框架使用）
        label: str = field(default="未标记", metadata={"description": "标签"})
        # repr=False：不显示在 repr 中
        secret: str = field(default="hidden", repr=False)
        # compare=False：不参与 __eq__ 比较
        cached_count: int = field(default=0, compare=False)
        name: str = "默认名"

    wf = WithFields()
    print(f"    WithFields() 默认值 = {wf}")
    print("    ★ items 用 default_factory=list，【每次新建】都得到独立列表：")
    w1 = WithFields()
    w2 = WithFields()
    w1.items.append(1)
    print(f"      w1.items = {w1.items}")
    print(f"      w2.items = {w2.items}   ← 没有互相污染！")
    print("    ★ 如果写成 items: List[int] = []，所有实例会共享同一个列表（经典坑）。")

    print()
    print(f"    created_at 不在 init 里（init=False）：")
    print(f"      尝试传参 → ", end="")
    try:
        WithFields(created_at="2025-01-01")
    except TypeError as exc:
        print(f"TypeError（init=False 排除了它）")

    print()
    print(f"    secret 不显示在 repr（repr=False）：{wf.secret}")
    print(f"    label 的 metadata：")
    for f in fields(WithFields):
        meta = f"  metadata={f.metadata['description']}" if f.metadata else ""
        print(f"      {f.name:14} default={f.default!r:14} factory={'有' if f.default_factory is not None else '无'} {meta}")

    # --- dataclass 工具函数 ---
    print()
    print("  ── dataclass 内置工具函数 ──")
    print(f"    asdict(wf)   = {asdict(wf)}   （转普通字典，递归）")
    print(f"    astuple(wf)  = {astuple(wf)}   （转元组）")
    print(f"    replace(wf, name='新名') = {replace(wf, name='新名')}   （复制并改字段）")
    print(f"    fields(wf)   = {len(fields(wf))} 个字段   （反射元信息）")
    print("    ★ asdict 可用于 JSON 序列化；replace 用于不可变对象的『改字段』。")


# ==============================================================================
# 【第三部分】dataclass vs 普通类
# ==============================================================================
def demo_vs_normal_class() -> None:
    print()
    print("=" * 60)
    print("【3】★ dataclass vs 普通类 对比")
    print("=" * 60)

    # 1) 代码量对比
    print()
    print("  ── 代码量对比（同一个数据类） ──")

    class NormalClass:
        """普通类：需要手写 __init__、__repr__、__eq__（约 15 行）。"""
        def __init__(self, name: str, age: int) -> None:
            self.name = name
            self.age = age

        def __repr__(self) -> str:
            return f"NormalClass(name={self.name!r}, age={self.age})"

        def __eq__(self, other: Any) -> bool:
            if not isinstance(other, NormalClass):
                return NotImplemented
            return self.name == other.name and self.age == other.age

    @dataclass
    class DataClass:
        """dataclass：只需声明字段（约 3 行）。"""
        name: str
        age: int

    nc = NormalClass("张三", 20)
    dc = DataClass("张三", 20)
    print(f"    普通类   nc = {nc}")
    print(f"    数据类   dc = {dc}")
    print(f"    两者相等？{nc.name == dc.name and nc.age == dc.age}   （功能等价）")
    print("    ★ dataclass 省掉了 __init__/__repr__/__eq__ 的样板代码。")

    # 2) 内存对比
    print()
    print("  ── 内存占用对比 ──")
    print(f"    普通类实例   {sys.getsizeof(nc)} 字节（含实例 __dict__）")
    print(f"    dataclass实例 {sys.getsizeof(dc)} 字节（也含 __dict__）")
    print("    ★ 不带 slots 时两者内存接近；dataclass 的优势在【代码量】而非内存。")

    # 3) 创建速度对比
    print()
    print("  ── 创建速度对比（timeit，各 10 万次） ──")
    # ★ timeit 的 setup 在独立命名空间执行，函数内定义的类无法从 __main__ 导入，
    #   因此把类的定义直接写进 setup 字符串里。
    t_normal = timeit.timeit(
        "N('x', 1)",
        setup="""
class N:
    def __init__(self, name, age):
        self.name = name
        self.age = age
N = N
""",
        number=100000,
    )
    t_dc = timeit.timeit(
        "D('x', 1)",
        setup="""
from dataclasses import dataclass
@dataclass
class D:
    name: str
    age: int
""",
        number=100000,
    )
    print(f"    普通类 N('x', 1)      {t_normal:.4f}s")
    print(f"    数据类 D('x', 1)      {t_dc:.4f}s")
    print(f"    ★ dataclass 的 __init__ 同样在【定义类时】生成一次，运行期调用速度与手写接近。")
    print(f"      真正的收益是【少写样板代码】，不是运行更快。")

    # 4) 继承对比
    print()
    print("  ── 继承行为对比 ──")

    @dataclass
    class Base:
        """基类：dataclass 也会被继承（字段合并）。"""
        id: int

    @dataclass
    class Child(Base):
        """子类：字段 = 基类字段 + 子类新增字段。"""
        name: str

    child = Child(1, "子类")
    print(f"    Child(1, '子类') = {child}   ← 字段按【基类在前】顺序")
    print(f"    参数顺序 = 基类字段(id) + 子类字段(name)")

    print()
    print("  ★ dataclass 继承注意：")
    print("    - 父类是 dataclass，子类不写 @dataclass → 子类【不自动生成】方法")
    print("    - 字段顺序：基类字段在前，子类字段在后；子类默认值会追加在最后")
    print("    - 基类是普通类 → 子类 dataclass 只处理自己声明的字段")


# ==============================================================================
# 【第四部分】Enum 枚举
# ==============================================================================
# ===== 语法解析 =====
# class Color(Enum): RED = 1
#   语法：类成员即枚举值，成员名全大写（常量约定）。
#   特性：
#     - 每个成员是【唯一】的类属性，创建后不可变
#     - 自动提供 name 与 value
#     - 遍历只遍历【成员】，不含别名
class Color(Enum):
    """普通枚举：值唯一，类型安全（比字符串常量安全得多）。

    ★ 注意：@unique 会禁止重复值，下面的 ALIAS_RED 演示了
      『不做 @unique 时的别名』行为（值相同 → 别名，不出现在遍历中）。
      所以本类【故意不加】@unique，ALIAS_RED 就是 RED 的别名。
    """

    RED = "红色"
    GREEN = "绿色"
    BLUE = "蓝色"
    ALIAS_RED = "红色"                        # 与 RED 同值 → 【别名】，遍历时不出现


@unique
class Season(Enum):
    """加了 @unique 的枚举：保证所有成员值互不相同（否则类定义时就报错）。"""

    SPRING = 1
    SUMMER = 2
    AUTUMN = 3
    WINTER = 4


class Level(IntEnum):
    """IntEnum：枚举值同时是 int，可直接参与数值运算。"""

    LOW = 1
    MEDIUM = 5
    HIGH = 10

    def __add__(self, other: int) -> int:
        """可以给枚举加方法。"""
        return int(self) + other


class Permission(Flag):
    """Flag：位标志枚举，用于组合权限（可按位或组合）。"""

    READ = auto()
    WRITE = auto()
    EXECUTE = auto()


def demo_enum() -> None:
    print()
    print("=" * 60)
    print("【4】Enum 枚举")
    print("=" * 60)

    # 1) 基本使用
    print()
    print("  ── 基本访问 ──")
    c = Color.RED
    print(f"    Color.RED          = {c}")
    print(f"    c.name / c.value   = {c.name} / {c.value}")
    print(f"    Color('红色')       = {Color('红色')}      ← 按值反查成员")
    print(f"    Color.RED == '红色' = {Color.RED == '红色'}   ← 【False】！枚举 ≠ 字符串")

    # 2) 遍历成员（不含别名）
    print()
    print("  ── 遍历成员 ──")
    print(f"    list(Color)        = {[m.name for m in Color]}   ← ALIAS_RED 是别名，不出现")
    print(f"    Color.__members__  = {list(Color.__members__)}   ← 含别名")
    print(f"    Season（@unique）   = {[m.name for m in Season]}   ← 无别名")
    print("    ★ @unique 装饰器保证【无重复值】，有重复会在类定义时就抛 ValueError。")

    # 3) in 判断
    print()
    print(f"    'RED' in Color.__members__ = {'RED' in Color.__members__}   ← 含别名的成员表")
    print(f"    Color.RED in Color          = {Color.RED in Color}   ← 按身份判断")

    # 4) IntEnum：可参与运算
    print()
    print("  ── IntEnum：枚举即整数 ──")
    lv = Level.HIGH
    print(f"    Level.HIGH         = {lv} (int={int(lv)})")
    print(f"    Level.HIGH > 5     = {lv > 5}       ← 当普通 int 比较")
    print(f"    int(Level.HIGH)    = {int(lv)}")
    print(f"    Level.HIGH + 1     = {lv + 1}   ← 调用自定义 __add__")
    print(f"    sum([Level.LOW, Level.MEDIUM]) = {Level.LOW + Level.MEDIUM}")
    print("    ★ IntEnum 适合表示【有数值大小的枚举】（优先级、日志级别）。")

    # 5) Flag：位标志组合
    print()
    print("  ── Flag：权限位组合 ──")
    rw = Permission.READ | Permission.WRITE       # 按位或组合
    print(f"    READ | WRITE       = {rw}")
    print(f"    含 READ 吗？        = {Permission.READ in rw}     ← in 判断是否含某标志")
    print(f"    含 EXECUTE 吗？     = {Permission.EXECUTE in rw}")
    print("    ★ Flag 用位运算表示『多个开关同时开启』，比多个 bool 优雅。")
    print(f"    Permission.__members__ = {list(Permission.__members__)}")

    # 6) 枚举 vs 类常量
    print()
    print("  ── 枚举 vs 类常量 vs 字符串常量 ──")
    print("    字符串常量：'active' == 'active' → True，但写错字'activ'【不会报错】！")
    print("    枚举      ：Color.RED 写错成 Color.REDD → 属性错误【立即报错】")
    print("    ★ 枚举的价值：【类型安全 + 可穷举】，适合表示有限的固定选项。")


# ==============================================================================
# 【第五部分】Protocol 结构化子类型
# ==============================================================================
# ===== 语法解析 =====
# class Shape(Protocol): def area(self) -> float: ...
#   语法：Protocol 表示"结构化接口"——不需继承，只看方法是否存在。
#   与 ABC 的区别：
#     - ABC：必须【显式继承】，才能 isinstance 通过（侵入性）
#     - Protocol：只要【结构匹配】就算（鸭子类型的静态版，非侵入）
#   作用：主要给类型检查器（mypy）用；运行期可配合 runtime_checkable 做 isinstance。
@runtime_checkable
class Drawable(Protocol):
    """结构化接口：只要有 draw() 方法就算实现，无需继承。"""

    def draw(self) -> str:
        """绘制方法。"""
        ...


class CircleShape:
    """鸭子：没有继承 Drawable，但有 draw 方法。"""
    def draw(self) -> str:
        return "绘制圆形"


class SquareShape:
    """另一个鸭子：同样不需要继承。"""
    def draw(self) -> str:
        return "绘制方形"


class NoDraw:
    """非鸭子：没有 draw 方法。"""
    def render(self) -> str:
        return "我用 render 不是 draw"


def demo_protocol() -> None:
    print()
    print("=" * 60)
    print("【5】Protocol 结构化子类型")
    print("=" * 60)

    circle = CircleShape()
    square = SquareShape()
    nodraw = NoDraw()

    print()
    print("  ── runtime_checkable 的 isinstance 检查（只检查方法【存在】） ──")
    print(f"    isinstance(CircleShape(), Drawable) = {isinstance(circle, Drawable)}   ✓ 有 draw")
    print(f"    isinstance(SquareShape(), Drawable) = {isinstance(square, Drawable)}   ✓ 有 draw")
    print(f"    isinstance(NoDraw(), Drawable)      = {isinstance(nodraw, Drawable)}   ✗ 无 draw")
    print("    ★ runtime_checkable 只做【浅层】检查（方法名存在与否），不校验签名。")

    print()
    print("  ── 鸭子类型的实际调用（无需继承） ──")

    def render_all(items: List[Any]) -> None:
        """接受任何有 draw 方法的对象。"""
        for item in items:
            print(f"    {item.draw()}")

    render_all([circle, square])             # 传入未继承 Drawable 的对象也能用
    print("    ★ Protocol 的核心价值：接口契约 + 无需继承 + 静态检查器友好。")

    print()
    print("  ── Protocol vs ABC vs 鸭子类型 ──")
    print("  | 方式        | 需要继承 | 运行期检查 | 静态检查(mypy) |")
    print("  |-------------|----------|------------|---------------|")
    print("  | 鸭子类型    | ✗        | 无         | ✗             |")
    print("  | Protocol    | ✗        | 浅(isinst.)| ✓ 最强        |")
    print("  | ABC         | ✓        | 完整       | ✓             |")


# ==============================================================================
# 【第六部分】NamedTuple 与 TypedDict
# ==============================================================================
# ===== 语法解析 =====
# NamedTuple：带类型注解的元组子类（既不可变又能按名访问）。
# TypedDict：描述字典的结构（值仍是普通 dict，运行时无约束）。
class PointNT(NamedTuple):
    """NamedTuple：不可变 + 按字段名访问 + 有类型注解。"""
    x: int
    y: int
    label: str = "未命名"


class MovieTD(TypedDict):
    """TypedDict：描述字典应有哪些键（运行时还是普通 dict）。"""
    title: str
    year: int
    rating: float


def demo_namedtuple_typeddict() -> None:
    print()
    print("=" * 60)
    print("【6】NamedTuple 与 TypedDict")
    print("=" * 60)

    print()
    print("  ── NamedTuple ──")
    pt = PointNT(1, 2)
    print(f"    PointNT(1, 2)      = {pt}")
    print(f"    pt.x / pt.y        = {pt.x} / {pt.y}   ← 按名访问")
    print(f"    pt[0]              = {pt[0]}   ← 也是元组")
    print(f"    label 默认值       = {pt.label}")
    print(f"    可哈希（可作字典键）= { {(pt): '坐标'} }")
    print(f"    _asdict()          = {pt._asdict()}")
    print(f"    _replace(x=9)      = {pt._replace(x=9)}   ← 返回新对象")
    print()
    print("    ★ NamedTuple vs dataclass：")
    print("      NamedTuple  不可变 + 轻量 + 可哈希，但【不能】修改字段")
    print("      dataclass   可变（除非 frozen）+ 功能更多，但内存略大")

    print()
    print("  ── TypedDict（运行时仍是普通 dict） ──")
    movie: MovieTD = {"title": "电影A", "year": 2020, "rating": 8.5}
    print(f"    movie = {movie}")
    print(f"    movie['title'] = {movie['title']}")
    print(f"    type(movie) = {type(movie).__name__}   ← 运行时就是 dict，无类型约束")
    print("    ★ TypedDict 只在【静态检查】时约束结构，运行时字典仍可随意写错。")

    print()
    print("  ── 三者选型 ──")
    print("  | 需求                     | 用什么          |")
    print("  |--------------------------|-----------------|")
    print("  | 不可变 + 轻量 + 可哈希    | NamedTuple     |")
    print("  | 可变 + 复杂字段 + 方法   | dataclass      |")
    print("  | 有限个固定选项           | Enum           |")
    print("  | 结构化字典 + 静态检查     | TypedDict      |")


def main() -> None:
    """主函数：按教学顺序演示数据类与类型工具。"""
    demo_basics()
    demo_all_parameters()
    demo_vs_normal_class()
    demo_enum()
    demo_protocol()
    demo_namedtuple_typeddict()

    print()
    print("=" * 60)
    print("小结")
    print("=" * 60)
    print("  1. ★ @dataclass 自动生成 __init__/__repr__/__eq__，消除样板代码")
    print("  2. ★ frozen=True 不可变（抛 FrozenInstanceError）且自动可哈希；slots=True 省内存")
    print("  3. order=True 生成比较运算符（要求字段可比较）；eq=False/repr=False 关闭生成")
    print("  4. ★ field(default_factory=list) 是可变默认值的【唯一正解】")
    print("  5. 字段顺序：有默认值的后置；init=False 排除字段；metadata 附加元信息")
    print("  6. ★ 工具函数：asdict(序列化)/astuple/replace(改字段)/fields(反射)")
    print("  7. Enum 提供类型安全；IntEnum 可运算；Flag 支持位组合；别名不入遍历")
    print("  8. Protocol 是鸭子类型的静态版：无需继承，结构匹配即可")
    print("  9. 选型：不可变轻量→NamedTuple；可变复杂→dataclass；固定选项→Enum")
    print(" 10. dataclass 的价值在【开发效率】，运行时性能与普通类相当")


if __name__ == "__main__":
    main()