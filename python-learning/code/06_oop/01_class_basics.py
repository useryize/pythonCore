"""
================================================================================
 01_class_basics.py  ——  类基础
================================================================================

【演示的语法点】
 1. class 语句的语法结构：class 名(基类): + 缩进体
 2. 类定义时到底发生了什么：执行 class 语句 → 动态【创建】一个新类对象
 3. 实例化过程详解：C.__call__ → cls.__new__ → cls.__init__
 4. 实例属性 vs 类属性：查找顺序（实例 → 类 → 继承链）
 5. 实例方法的绑定机制：描述符协议，obj.method 会自动传入 self
 6. 静态方法 @staticmethod：函数，不接收任何隐式参数
 7. 类方法 @classmethod：接收 cls，替代显式写类名（子类友好）
 8. __dict__ 与 vars()：查看对象与类的属性表
 9. dir() 与 help()：反射
 10. 最小化类：__slots__ 与普通类的内存/性能对比
 11. 方法的种类速查表（静态/类/实例/属性/魔术）

【预期输出摘要】
 - "实例化过程" 小节打印 __new__ 与 __init__ 的调用顺序
 - "属性查找" 小节演示类属性被实例属性遮蔽
 - "slots" 小节对比 __dict__ 是否存在
================================================================================

"""

from __future__ import annotations

import functools
from typing import Any, ClassVar


# ===== 语法解析 =====
# 【1】类的基本定义
#   语法规则：class 类名(基类列表):  + 缩进的类体
#   - 类名用【大驼峰】（PascalCase），这是 PEP 8 的强约定
#   - 基类列表可省略（括号可省，但保留可读性更好）
#   - 类体在【定义时】立即执行，产生：类属性、方法对象、__dict__、文档字符串等
#   设计意图：把"数据 + 操作数据的方法"封装为一个整体，并支持复用与多态。
def demo_basic_class() -> None:
    # 最小类
    class Empty:
        pass

    print(f"  class Empty 的类型：{type(Empty)}   # 就是一个 type 对象")
    print(f"  Empty.__name__ = {Empty.__name__!r}")
    print(f"  Empty.__dict__ 的键：{sorted(Empty.__dict__)}")
    print(f"  Empty.__doc__ = {Empty.__doc__!r}")
    print(f"  Empty.__bases__ = {Empty.__bases__}   # 无基类时为空元组")

    # 类是【对象】：可以赋值、可以传参、可以放进容器
    alias = Empty
    print(f"  Empty is alias → {Empty is alias}   # 类是一等对象")
    registry = {"empty": Empty}
    print(f"  类可放进字典：{registry['empty'].__name__}")

    print()
    print("  带属性和方法的类：")

    class Person:
        """人类。类体中的变量成为【类属性】。"""

        species = "Homo sapiens"        # 类属性：所有实例共享
        species_count = 0                # 类属性做计数器

        def __init__(self, name: str, age: int) -> None:
            """初始化实例属性。每个实例各自持有。"""
            self.name = name             # 实例属性：绑定到实例的 __dict__
            self.age = age
            Person.species_count += 1    # 修改类属性必须写类名，不能写 self.

        def introduce(self) -> str:
            """实例方法。第一个参数 self 是实例的隐式接收者。"""
            return f"我是{self.name}，{self.age}岁"

        def __repr__(self) -> str:
            # __repr__ 面向开发者（应尽量无歧义），区别于面向用户的 __str__
            return f"Person(name={self.name!r}, age={self.age})"

    print(f"  类属性 species = {Person.species}")
    # ★ 类体在定义时执行，其中的 def 只创建函数对象，此时还没有任何实例
    p = Person("张三", 25)
    print(f"  实例化 p1 = {p}")
    print(f"  p1.introduce() → {p.introduce()}")
    print(f"  类计数器 species_count = {Person.species_count}   # 共享类属性被累加")


# ===== 语法解析 =====
# 【2】★ 实例化过程的完整拆解
#   执行 Person('张三', 25) 时，Python 内部发生：
#     步骤 1：查找 Person.__call__。类对象没有自定义 __call__，
#             所以走 type.__call__（元类的实现）。
#     步骤 2：type.__call__(Person, '张三', 25) 内部做两件事：
#             ① 调用 Person.__new__(Person, '张三', 25)  →  创建【空实例】
#                （默认 object.__new__ 只分配内存，不执行任何用户代码）
#             ② 若返回的对象确实是 Person 的实例，则调用 __init__(实例, '张三', 25)
#                → 执行初始化逻辑，把值放进实例 __dict__
#     步骤 3：返回实例。
#   ★ 关键推论：
#     - __new__ 负责"创建"，__init__ 负责"初始化"，二者职责不同
#     - __init__ 的返回值必须是 None（否则 TypeError）
#     - __new__ 返回的其他类型时，__init__ 不会被调用
#     - 若不定义 __init__，则继承 object.__init__，它什么都不做（故只能无参构造）
def demo_instantiation_process() -> None:
    print("  用打点法观测实例化全过程：")

    class Traced:
        created = 0

        def __new__(cls, *args, **kwargs):
            # __new__ 是【静态方法】风格：第一个参数是 cls，不是 self
            print(f"    ① __new__ 被调用：args={args} → 分配内存，返回空实例")
            Traced.created += 1
            return super().__new__(cls)   # 调用 object.__new__ 完成分配

        def __init__(self, value: int) -> None:
            print(f"    ② __init__ 被调用：value={value} → 填充实例属性")
            self.value = value

        def __del__(self) -> None:
            # __del__ 在对象被回收时调用；不要在里面做重要工作（时机不确定）
            print(f"    ③ __del__ 被调用：回收 value={getattr(self, 'value', '?')}")

    t = Traced(100)
    print(f"    创建完成，t.value = {t.value}")
    print(f"    累计创建实例数 = {Traced.created}")

    print()
    print("  验证 __init__ 返回值必须为 None：")

    class BadInit:
        def __init__(self) -> None:
            return 1          # 错误：__init__ 不能返回值

    try:
        BadInit()
    except TypeError as exc:
        print(f"    __init__ 返回值 → TypeError: {exc}")

    print()
    print("  验证 __new__ 返回其他类型时 __init__ 不被调用：")

    class Weird:
        def __new__(cls):
            return 42         # 返回一个非实例对象

        def __init__(self) -> None:
            print("    这个 print 不应该出现")

    result = Weird()
    print(f"    Weird() 返回 {result!r}，类型 {type(result).__name__} → __init__ 被跳过")

    print()
    print("  不定义 __init__ 时只能用无参构造：")

    class NoInit:
        pass

    NoInit()
    try:
        NoInit(1, 2)
    except TypeError as exc:
        print(f"    NoInit(1, 2) → TypeError: {exc}")


# ===== 语法解析 =====
# 【3】★ 实例属性 vs 类属性（查找顺序）
#   属性查找顺序（MRO 链）：实例 __dict__ → 类 __dict__ → 父类 __dict__ → ... → object
#   - 读操作：从实例开始沿类链向上找
#   - 写操作 obj.x = v：【只写实例 __dict__】，绝不回写类属性
#   ★ 这就是"遮蔽(shadowing)"：给实例赋同名属性会遮住类属性，但不影响其他实例。
#   ★ 类属性适合放"所有实例共享且不常改"的常量；实例属性放"每个实例不同"的数据。
def demo_attribute_lookup() -> None:
    print("  演示类属性与实例属性的查找与遮蔽：")

    class Course:
        # 类属性：所有实例共享的"课程总量"
        total_students = 0
        school = "第一大学"       # 用作常量（虽未声明为 Final，实践中不改）

        def __init__(self, name: str) -> None:
            self.name = name
            self._secret = "私有（下划线约定）"
            Course.total_students += 1   # ★ 修改类属性：写 Course. 不用 self.

    c1 = Course("Python")
    c2 = Course("Java")

    print(f"    创建 2 个实例后，Course.total_students = {Course.total_students}")
    print(f"    c1.total_students = {c1.total_students}  # 沿类链找到类属性")
    print(f"    c2.total_students = {c2.total_students}  # 两者共享同一个值")
    print(f"    修改 c1.total_students 后：")
    c1.total_students = 99          # ★ 只在 c1 的实例 __dict__ 里新建一条
    print(f"      c1.total_students = {c1.total_students}   # 用了实例属性")
    print(f"      c2.total_students = {c2.total_students}   # 未受影响")
    print(f"      Course.total_students = {Course.total_students}  # 类属性也未受影响")

    print()
    print("  查看属性表的实际内容：")
    print(f"    c1.__dict__ = {c1.__dict__}")
    print(f"    Course.__dict__ 的实例相关键：{[k for k in Course.__dict__ if not k.startswith('__')]}")
    print(f"    'total_students' 在 c1.__dict__ 里吗：{'total_students' in c1.__dict__}")
    print(f"    'school' 在 c1.__dict__ 里吗：{'school' in c1.__dict__}   # 来自类")

    print()
    print("  ClassVar 注解的作用（仅供类型检查器，运行时无约束）：")
    class TypedCourse:
        count: ClassVar[int] = 0      # 明确标注"这是类变量"
        name: str                     # 这是实例变量
        def __init__(self, name: str) -> None:
            self.name = name
            TypedCourse.count += 1

    TypedCourse("A"); TypedCourse("B")
    print(f"    TypedCourse.count = {TypedCourse.count}")
    print(f"    注解：{sorted(TypedCourse.__annotations__)}   # ClassVar 是【特殊】类注解，"
          f"不进入实例")


# ===== 语法解析 =====
# 【4】实例方法的绑定机制（描述符协议）
#   原理：类体中的函数是【描述符(descriptor)】对象。
#         访问 obj.method 时，函数的 __get__ 被调用，返回"绑定了 obj 的新函数"。
#         因此 obj.method(arg) ≡ Person.method(obj, arg) —— self 是自动传入的。
#   验证方法：
#     - 类访问：Person.introduce  →  unbound function（self 未绑定）
#     - 实例访问：obj.introduce   →  bound method（有 __self__ 属性）
def demo_method_binding() -> None:
    class Counter:
        def __init__(self) -> None:
            self.n = 0

        def increment(self, step: int = 1) -> None:
            self.n += step

    c = Counter()
    print(f"  Counter.increment（类访问）：{Counter.increment}")
    print(f"    类型：{type(Counter.increment).__name__}   # 普通函数 unbound")
    print(f"  c.increment（实例访问）：{c.increment}")
    print(f"    类型：{type(c.increment).__name__}   # bound method")
    print(f"    __self__ = {c.increment.__self__!r}   # 绑定的实例")

    print()
    print(f"  等价性验证：c.increment(5) ≡ Counter.increment(c, 5)")
    c.increment(5)
    c2 = Counter()
    Counter.increment(c2, 7)                # 手动传 self
    print(f"    c.n={c.n}, c2.n={c2.n}   # 两种写法效果相同")
    print()
    print(f"  每次访问 c.increment 都生成新的绑定方法对象：")
    print(f"    c.increment is c.increment → {c.increment is c.increment}   # False")
    print(f"    但它们 __self__ 相同：{c.increment.__self__ is c.increment.__self__}")


# ===== 语法解析 =====
# 【5】@staticmethod —— 静态方法
#   语法：@staticmethod 装饰普通函数。
#   语义：不接收 self 也不接收 cls，本质是"塞进类命名空间的函数"。
#   调用：类名.方法() 或 实例.方法() 都可（后者仅是恰好能访问到）。
#   用途：与类业务相关但不需要实例/类状态的工具函数。
class MathUtil:
    """数学工具类。"""

    @staticmethod
    def add(a: float, b: float) -> float:
        """加法。不依赖任何实例状态。"""
        return a + b

    @staticmethod
    def is_even(n: int) -> bool:
        return n % 2 == 0

    def demo_call_ways(self) -> None:
        print(f"    实例调用静态方法：{self.add(1, 2)}   # 可行但不推荐，容易误解")
        print(f"    类调用静态方法：  {MathUtil.add(1, 2)}   # 推荐")


# ===== 语法解析 =====
# 【6】@classmethod —— 类方法
#   语法：@classmethod 装饰，第一参数固定为 cls（惯例名）。
#   语义：cls 绑定的是【实际被调用的那个类】，而不是定义它的类。
#   ★ 巨大价值：子类调用父类方法时，cls 自动是子类 —— 这就是"子类友好"，
#     避免了硬编码类名导致子类无法完全定制（工厂方法模式的基础）。
class Shape:
    """图形基类。"""
    # 类属性作为"类级别配置"，子类可覆盖
    type_name = "Shape"

    def __init__(self, name: str) -> None:
        self.name = name

    @classmethod
    def describe(cls) -> str:
        """用 cls 而非硬编码类名，子类调用会自动返回子类信息。"""
        return f"这是一个 {cls.__name__}（类型标记：{cls.type_name}）"

    @classmethod
    def create(cls, *args, **kwargs):
        """工厂方法基类：子类继承后 cls 是子类，返回子类实例。"""
        return cls(*args, **kwargs)


class Circle(Shape):
    type_name = "圆形"

    def __init__(self, name: str, r: float) -> None:
        super().__init__(name)
        self.r = r

    @classmethod
    def describe(cls) -> str:
        # 复用父类逻辑再加工 —— 因为 cls 是 Circle
        return super().describe() + f"，半径 = {cls.__name__}"


def demo_static_and_class_methods() -> None:
    print("  @staticmethod 静态方法：")
    print(f"    MathUtil.add(3, 4) = {MathUtil.add(3, 4)}")
    print(f"    MathUtil.is_even(4) = {MathUtil.is_even(4)}")
    print(f"    MathUtil.add.__dict__ 存在吗（普通函数）：{'__dict__' in MathUtil.add.__dict__}")
    util = MathUtil()
    util.demo_call_ways()
    print(f"    注意：静态方法通过实例也能调用，但【不会】自动传入 self")

    print()
    print("  @classmethod 类方法：")
    print(f"    Shape.describe()   → {Shape.describe()}")
    print(f"    Circle.describe()  → {Circle.describe()}")
    print(f"    ★ 同一个 describe 方法，因 cls 不同返回不同信息 —— 子类友好")

    print()
    print("  工厂方法模式（类方法的高级应用）：")
    c = Circle.create("圆A", 5.0)
    print(f"    Circle.create('圆A', 5.0) → {type(c).__name__} 实例, r={c.r}")
    s = Shape.create("形状A")
    print(f"    Shape.create('形状A')     → {type(s).__name__} 实例")
    print(f"    证明：cls 是【实际调用的类】，不是 Shape")


# ===== 语法解析 =====
# 【7】__slots__ —— 最小化内存的类
#   语法：类体中 __slots__ = ("a", "b")  声明【固定】的实例属性集合。
#   效果：
#     - 实例不再有 __dict__，内存占用大幅下降（创建百万对象时差别显著）
#     - 不能随意添加新属性（未声明的名字赋值会 AttributeError）
#     - 属性访问稍快（走 slot 描述符，省去哈希表查找）
#   限制：
#     - 父类若没定义 __slots__，子类加 __slots__ 不会消除继承来的 __dict__
#     - 不能与 __dict__ 同名；类变量名不能与 slot 重名
#     - 不适用于需要动态属性的场景
class Point2D:
    """使用 __slots__ 的轻量点。"""

    __slots__ = ("x", "y")          # 声明可用属性，固定集合

    def __init__(self, x: float, y: float) -> None:
        self.x = x
        self.y = y

    def __repr__(self) -> str:
        return f"Point2D({self.x}, {self.y})"


class Point2DWithDict:
    """普通类：实例自带 __dict__。"""

    def __init__(self, x: float, y: float) -> None:
        self.x = x
        self.y = y


def demo_slots() -> None:
    p = Point2D(1, 2)
    print(f"  Point2D 实例：{p}")
    print(f"    有 __dict__ 吗：{hasattr(p, '__dict__')}")
    print(f"    __slots__ = {Point2D.__slots__}")
    try:
        p.z = 3             # 未在 __slots__ 中声明
    except AttributeError as exc:
        print(f"    新增未声明属性 → AttributeError: {exc}")

    print()
    q = Point2DWithDict(1, 2)
    print(f"  普通类实例：{q.__dict__}   # 有 __dict__，可任意加属性")
    q.z = 3                # 动态添加，合法
    print(f"    动态加属性 z = {q.z} 成功")

    print()
    print("  内存占用对比（1000 个实例的 __dict__ 是否存在）：")
    n = 1000
    slots_objs = [Point2D(i, i) for i in range(n)]
    dict_objs = [Point2DWithDict(i, i) for i in range(n)]
    print(f"    __slots__ 类：每个实例无 __dict__，共 {n} 个对象")
    print(f"    普通类：每个实例含一个 __dict__（约 104+ 字节），共 {n} 个")
    print(f"    结论：大量小对象（如百万级）用 __slots__ 可显著省内存")
    # 访问 slot 属性的机制：Point2D.x 是一个 member_descriptor
    print(f"    Point2D.x 是：{type(Point2D.x).__name__}   # 描述符对象，实现 slot 访问")


# ===== 语法解析 =====
# 【8】反射工具：__dict__ / vars() / dir() / getattr / setattr / hasattr
def demo_reflection() -> None:
    class Student:
        school = "第一大学"

        def __init__(self, name: str) -> None:
            self.name = name
            self.age = 18

        def study(self) -> None:
            pass

    s = Student("张三")
    print("  __dict__ 与 vars()（vars 返回 __dict__ 的引用）：")
    print(f"    s.__dict__        = {s.__dict__}")
    print(f"    vars(s)           = {vars(s)}")
    print(f"    是同一个对象吗：{s.__dict__ is vars(s)}")
    print(f"    注意：返回的是【真实字典引用】，改它会改到实例！")
    vars(s)["grade"] = "A"
    print(f"    通过 vars(s) 添加 grade 后：s.grade = {s.grade}")

    print()
    print("  类级别的 __dict__（含方法与类属性）：")
    keys = sorted(Student.__dict__)
    print(f"    Student.__dict__ 键 = {keys}")
    for key in ("school", "study", "__init__"):
        print(f"      {key:<10} → {type(Student.__dict__[key]).__name__}")

    print()
    print("  dir()：列出所有可用名字（含继承来的）")
    print(f"    dir(s) = {dir(s)}")
    print(f"    比 __dict__ 多了：{[k for k in dir(s) if k not in s.__dict__]}")
    print(f"    这些是继承自 object 的方法，如 __eq__ / __str__ / __class__")
    print(f"    只看可调用/非下划线开头：{[k for k in dir(s) if not k.startswith('_')]}")

    print()
    print("  getattr / setattr / hasattr —— 按【字符串】动态访问属性")
    print(f"    getattr(s, 'name') = {getattr(s, 'name')}")
    print(f"    hasattr(s, 'study') = {hasattr(s, 'study')}")
    setattr(s, "grade", "B")
    print(f"    setattr(s, 'grade', 'B') → s.grade = {s.grade}")
    print(f"    getattr(s, '不存在的属性', '默认值') = "
          f"{getattr(s, '不存在的属性', '默认值')}   # 第三个参数是安全的默认值")
    try:
        getattr(s, "不存在")
    except AttributeError as exc:
        print(f"    getattr(s, '不存在') → AttributeError: {exc}")

    print()
    print("  反射的实战：通用序列化（把对象的 __dict__ 转成字典）")

    def to_dict(obj: Any) -> dict[str, Any]:
        """通用对象序列化：依赖 __dict__ 的存在。"""
        if hasattr(obj, "__dict__"):
            data = dict(obj.__dict__)
            # 递归处理嵌套对象，实现多层序列化
            return {k: to_dict(v) if hasattr(v, "__dict__") else v
                    for k, v in data.items()}
        return obj

    print(f"    to_dict(s) = {to_dict(s)}")
    print(f"    局限：只对【有 __dict__ 的对象】有效（__slots__ 类就不行）")
    try:
        to_dict(Point2D(1, 2))
    except AttributeError as exc:
        print(f"    对 __slots__ 类 → AttributeError: {exc}")


# ===== 语法解析 =====
# 【9】方法的五种类型速查
def demo_method_types() -> None:
    class Demo:
        attr = "类属性"

        def instance_method(self) -> str:
            return "实例方法"

        @staticmethod
        def static_method() -> str:
            return "静态方法"

        @classmethod
        def class_method(cls) -> str:
            return "类方法"

        @property
        def property_method(self) -> str:
            return "属性（用调用，不用括号访问）"

        def __special__(self) -> str:
            return "魔术方法"

    d = Demo()
    rows = [
        ("d.instance_method()", "实例方法，自动传 self"),
        ("Demo.static_method()", "静态方法，不传任何参数"),
        ("Demo.class_method()", "类方法，自动传 cls（子类友好）"),
        ("d.property_method", "property，无括号，当属性访问"),
        ("d.__special__()", "魔术方法，双下划线，Python 内部调用"),
        ("Demo.attr", "类属性，是数据不是方法"),
    ]
    print("  访问方式                                → 说明")
    print("  " + "-" * 70)
    for how, result in rows:
        print(f"  {how:<38} → {result}")
    print()
    print("  ★ 三种『加装饰器』的区别（最易混淆点）：")
    print("    @staticmethod  → 函数不接收隐式 self/cls，用 类名.方法()")
    print("    @classmethod  → 函数接收 cls，用 类名.方法()，子类自动适配")
    print("    @property     → 把【方法】变成【属性】，用 实例.属性（不加括号）")
    print("    记忆：staticmethod/classmethod 改的是【第一个参数】，")
    print("          property 改的是【调用方式】。")


def main() -> None:
    print("=" * 60)
    print("【1】类的基础定义")
    print("=" * 60)
    demo_basic_class()

    print()
    print("=" * 60)
    print("【2】★ 实例化过程详解（__new__ 与 __init__）")
    print("=" * 60)
    demo_instantiation_process()

    print()
    print("=" * 60)
    print("【3】★ 实例属性 vs 类属性")
    print("=" * 60)
    demo_attribute_lookup()

    print()
    print("=" * 60)
    print("【4】实例方法的绑定机制（描述符协议）")
    print("=" * 60)
    demo_method_binding()

    print()
    print("=" * 60)
    print("【5】@staticmethod 与 @classmethod")
    print("=" * 60)
    demo_static_and_class_methods()

    print()
    print("=" * 60)
    print("【6】__slots__ 最小化内存")
    print("=" * 60)
    demo_slots()

    print()
    print("=" * 60)
    print("【7】反射：__dict__ / dir() / getattr")
    print("=" * 60)
    demo_reflection()

    print()
    print("=" * 60)
    print("【8】方法类型速查表")
    print("=" * 60)
    demo_method_types()

    print()
    print("=" * 60)
    print("小结")
    print("=" * 60)
    print("  1. class 语句执行时动态创建一个类（type 实例）")
    print("  2. 实例化 = type.__call__ → __new__（创建）→ __init__（初始化）")
    print("  3. 属性查找：实例 __dict__ → 类 → 父类链；写操作只落实例 __dict__")
    print("  4. 实例方法靠描述符自动绑定 self；classmethod 绑 cls（子类友好）")
    print("  5. __slots__ 省内存但禁止动态属性")
    print("  6. 装饰器三兄弟：staticmethod/classmethod 改首参，property 改调用方式")


if __name__ == "__main__":
    main()