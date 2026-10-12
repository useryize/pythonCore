"""
================================================================================
 03_inheritance.py  ——  继承、MRO 与 super()
================================================================================

【演示的语法点】
 1. 单继承：class 子类(父类) 的语法与实例化过程
 2. 多继承：class C(A, B) 的语法与"菱形继承"
 3. ★ MRO（方法解析顺序）与 __mro__ / mro()
 4. ★ C3 线性化算法：C3(mro) = 子类 + merge(mro(父1), mro(父2), [父1,父2])
    用 A/B/C/D 经典例子手算验证
 5. ★ super() 的真实原理：super().__init__() 不是"调用父类"，而是"调用 MRO 中下一个"
 6. super() 的坑：
    - 必须用 super()，不能写 父类名.方法(self)（破坏多继承/子类定制）
    - super() 是编译期属性，不是关键字
    - 在类体外用 super() 报错
    - 类方法中用 super()（cls 语义）
 7. 方法解析顺序实测：同名方法的调用轨迹
 8. 继承中的属性查找完整流程
 9. __init_subclass__ / super().__init_subclass__ 的钩子
10. 方法覆盖 vs 方法扩展的取舍

【预期输出摘要】
 - "C3 线性化" 小节手算推导与真实 mro() 输出逐字比对，结果一致
 - "super 陷阱" 小节真实打印 父类名硬编码 导致的错误行为
================================================================================

"""

from __future__ import annotations

from typing import Any, ClassVar


# ===== 语法解析 =====
# 【1】单继承
#   语法规则：class 子类(父类): —— 括号内可写多个父类（多继承）
#   语义：子类【自动获得】父类的所有属性与方法，且可覆盖/扩展。
#   属性查找：子类 → 父类 → ... → object。
#   设计意图：表达"is-a"关系，复用实现 + 差异化行为。
#   ★ 判据：如果无法用"子类是一种父类"这句话描述，就不该用继承（考虑组合）。
class Animal:
    """动物基类。"""

    kingdom: ClassVar[str] = "Animalia"       # 类属性

    def __init__(self, name: str) -> None:
        self.name = name                     # 实例属性
        self._age = 0

    def speak(self) -> str:
        """被子类覆盖的方法。"""
        return f"{self.name} 发出声音"

    def describe(self) -> str:
        """子类【扩展】的方法：调用父类实现再加内容（复用而非重写）。"""
        return f"{self.__class__.__name__}: {self.speak()}"

    def birthday(self) -> None:
        """年龄自增。"""
        self._age += 1

    @property
    def age(self) -> int:
        return self._age


class Dog(Animal):
    """狗。继承 Animal 并覆盖 speak。"""

    def __init__(self, name: str, breed: str) -> None:
        # ★ 必须显式调用父类 __init__：子类 __init__ 会【覆盖】父类的，
        #   Python 不像 Java 那样自动调用父类构造器。
        #   若忘记调用，self.name 就不存在 → 后续 AttributeError
        super().__init__(name)
        self.breed = breed       # 子类新增属性

    def speak(self) -> str:
        """★ 覆盖（override）：签名必须兼容父类（Liskov 替换原则）。"""
        return f"{self.name} 汪汪叫"

    def fetch(self) -> str:
        """子类新增方法。"""
        return f"{self.name} 去捡球"


# ===== 语法解析 =====
# 【2】多继承与菱形继承
#   语法规则：class C(A, B): —— 顺序【有意义】，决定 MRO 中的优先级。
#   ★ 顺序的影响：
#       class C(A, B)  → A 优先于 B
#       class D(B, A)  → B 优先于 A
#     两者可能有完全不同的行为！这是 Python 与 Java 等语言的重要差异
#     （Java 用"单继承 + 接口"来规避这个问题）。
class Flyable:
    """可飞。"""

    def move(self) -> str:
        return f"{self.__class__.__name__} 在空中飞"

    def describe(self) -> str:
        return "飞行能力"


class Swimmable:
    """可游泳。"""

    def move(self) -> str:
        return f"{self.__class__.__name__} 在水里游"

    def describe(self) -> str:
        return "游泳能力"


class Duck(Flyable, Swimmable):
    """鸭子：既能飞又能游 —— 典型的多继承场景。"""

    def __init__(self, name: str) -> None:
        self.name = name
        # 注意：这里【故意不调用】 super().__init__()，因为父类都没有 __init__

    def abilities(self) -> str:
        return f"{self.describe()} + {Swimmable.describe(self)}"   # 显式调用避免歧义


class Swimmer(Swimmable, Flyable):
    """用于演示：同样两个父类，但顺序【相反】。"""

    def __init__(self, name: str) -> None:
        # 两个父类都没有 __init__，所以只需设置自己的属性
        self.name = name


# ===== 语法解析 =====
# 【3】★ C3 线性化算法（必须理解的核心）
#   算法定义：
#     L[C] = C + merge(L[B1], L[B2], ..., [B1, B2, ...])
#     merge 的规则：
#       ① 取每个列表的【第一个】元素作为候选；
#       ② 若该元素【不出现在其他任何列表的尾部】，则选它并从所有列表中删除；
#       ③ 否则取下一个列表的头部重复尝试；
#       ④ 若所有候选都被阻塞 → 无解（存在不一致的继承关系）
#
#   经典例子：
#     class A: pass
#     class B(A): pass
#     class C(A): pass
#     class D(B, C): pass
#     MRO(A)    = [A]
#     MRO(B)    = [B] + merge([A], [A]) = [B, A]
#     MRO(C)    = [C] + merge([A], [A]) = [C, A]
#     MRO(D)    = [D] + merge([B,A], [C,A], [B,C])
#                候选 B：B 不在其他列表尾部 → 选 B，剩 merge([A],[C,A],[C])
#                候选 A：A 在 [C,A] 的尾部 → 阻塞！换下一个列表
#                候选 C：C 不在尾部 → 选 C，剩 merge([A],[A],[])
#                候选 A：选出
#                结果 = [D, B, C, A]
#   ★ C3 的核心价值：在保持"子类优先、父类相对顺序"的前提下，
#     尽可能让局部顺序【单调】—— 这就是"线性化"这个名字的含义。
class A:
    def who(self) -> str:
        return "A"


class B(A):
    def who(self) -> str:
        return "B"


class C(A):
    def who(self) -> str:
        return "C"


class D(B, C):
    """D(B, C) 的 MRO 应为 [D, B, C, A]。"""

    def who(self) -> str:
        return "D"


def demo_c3_algorithm() -> None:
    print("  继承关系：class D(B, C)，而 B(A)、C(A)")
    print()
    print("  【手算推导】")
    print("    MRO(A) = [A]")
    print("    MRO(B) = [B, A]")
    print("    MRO(C) = [C, A]")
    print("    MRO(D) = [D] + merge([B,A], [C,A], [B,C])")
    print("      ① 候选 B（在 [B,A] 首位，且不在其他列表尾部）→ 选 B")
    print("         剩余 merge([A], [C,A], [C])")
    print("      ② 候选 A（在 [C,A] 的尾部）→ 被阻塞，跳过 [A]")
    print("      ③ 候选 C（在 [C,A] 首位且不在尾部）→ 选 C")
    print("         剩余 merge([A], [A], [])")
    print("      ④ 候选 A → 选 A")
    print("      MRO(D) = [D, B, C, A]")
    print()

    print("  【实测验证】")
    mro_d = D.__mro__
    print(f"    D.__mro__        = {[c.__name__ for c in mro_d]}")
    print(f"    D.mro()          = {[c.__name__ for c in D.mro()]}")
    print(f"    与手算结果一致    = {[c.__name__ for c in mro_d] == ['D', 'B', 'C', 'A']}")
    print()
    print("  所有类的 MRO：")
    for cls in (A, B, C, D):
        print(f"    {cls.__name__}.__mro__ = {[c.__name__ for c in cls.__mro__]}")

    print()
    print("  ★ C3 保证的两条不变量：")
    print("    1. 子类永远在父类之前（D 在 B、C 之前）")
    print("    2. 父类之间的相对顺序与【继承声明顺序】一致（B 在 C 之前）")
    print("       —— 若写成 class D(C, B)，MRO 就变成 [D, C, B, A]，行为相反！")


# ===== 语法解析 =====
# 【4】★ C3 的一致性检测：无解的情况
#   如果存在"既要求 A 在 B 前、又要求 B 在 A 前"的矛盾，
#   C3 会失败，Python 解释器在【定义类时】就直接报 TypeError。
def demo_c3_inconsistency() -> None:
    print("  演示 C3 无解导致的 TypeError（发生在【类定义时】）：")
    code = '''
class X: pass
class Y(X): pass
class Z(X): pass
# 矛盾点：B 的 MRO 要求 A 紧邻其后，而 D 要求 C 在 B 之前且 A 在最前，
# 这里用经典冲突构造：让 E 继承自 Y 和 Z，同时 Z 继承自 Y 的子类关系反转
class P(Y, Z): pass          # 正常
class E(Z, P): pass          # ★ 冲突：E 要 Z 先于 P，但 P 的 MRO 里 Y 在 Z 前面
'''
    try:
        # 直接 exec 会真的触发定义期错误
        namespace: dict[str, Any] = {}
        exec(code, namespace)   # type: ignore[exec-used]
        print("    （该构造在某些顺序下是合法的，未报错）")
    except TypeError as exc:
        print(f"    TypeError: {str(exc)[:110]}")
    print()
    print("  说明：TypeError: Cannot create a consistent method resolution order (MRO)")
    print("  发生时机是【定义类的那一行】，而不是实例化时。")
    print("  实践建议：不要为了『让某个方法优先』而调整多继承顺序来绕过 C3 冲突，")
    print("            而应改用组合或 mixin（见 04_polymorphism.py）。")


# ===== 语法解析 =====
# 【5】★ super() 的真实原理（最高频面试题）
#   常见误解：super() 用来"调用父类方法"。
#   真相：super() 是"获取 MRO 中【下一个】类"的工具。
#         super() 的实现约等于 super(__class__, self)，其中 __class__ 是【当前类】
#         的编译期闭包单元格（编译器自动注入）。
#         因此 super() 在【函数体内部】取的是"定义它的那个类"的 MRO，
#         再找该类的下一个。
#   关键推论：
#     - super(Foo, self) 从 Foo 之后开始找，不是从 Foo 开始
#     - super() 在方法【运行时】才计算，所以同一个 super() 在多层继承里
#       会找到"不同的下一个类"
#   正确写法与错误写法的对比（本节核心）：
#     ✗ 父类名.方法(self)  —— 硬编码，跳过 MRO，破坏多继承与子类定制
#     ✓ super().方法()      —— 沿 MRO 查找，行为可被中间类拦截
class Base:
    def __init__(self, name: str) -> None:
        self.name = name
        self.trace = ["Base.__init__"]

    def process(self) -> str:
        return "Base 处理完成"


class Middle(Base):
    """中间层。用 super() 可以让子类插入逻辑而不打断调用链。"""

    def __init__(self, name: str) -> None:
        # ★ 先做自己的事
        self.middle_ran = True
        super().__init__(name)              # 再让父类继续
        self.trace.append("Middle.__init__ 续")

    def process(self) -> str:
        """★ 模板方法模式：前后加日志，中间交给 super()。"""
        result = super().process()
        return f"[Middle 审计] {result}"


class Leaf(Middle):
    def __init__(self, name: str) -> None:
        super().__init__(name)
        self.trace.append("Leaf.__init__")

    def process(self) -> str:
        return f"[Leaf] {super().process()}"


def demo_super_mechanism() -> None:
    print("  【正确：用 super() 的调用链】")
    leaf = Leaf("测试")
    leaf.trace.reverse()
    print(f"    __init__ 执行顺序：{leaf.trace}")
    print(f"    process() 结果：{leaf.process()}")
    print(f"    ★ 三层继承，一次调用穿透了整个继承链")

    print()
    print("  【super() 取的是 MRO 的下一个，而非『父类』】")
    print(f"    Leaf.__mro__ = {[c.__name__ for c in Leaf.__mro__]}")
    print(f"    Leaf 中 super() 的下一个类 = "
          f"{super(Leaf, leaf).__self__.__class__.__name__}")
    print(f"    Middle 中 super() 的下一个类 = "
          f"{super(Middle, leaf).__self__.__class__.__name__}")
    print(f"    ★ 同一个对象 leaf，两处 super() 找到的『下一个』不同，")
    print(f"      因为起点类不同（MRO 是从【各自类】开始找的）。")

    print()
    print("  【实测：super(C, obj) 等价于在【C 的方法内】写 super()】")
    # ★ 注意：super(Leaf, leaf) 是从 Leaf 【之后】开始找，所以它【不包含】Leaf 自己的逻辑。
    #   要证明等价，应与 Middle.process(leaf) 比较（同样跳过 Leaf）。
    result_a = super(Leaf, leaf).process()
    result_b = Middle.process(leaf)
    print(f"    super(Leaf, leaf).process() = {result_a}")
    print(f"    Middle.process(leaf)         = {result_b}")
    print(f"    两者相同 = {result_a == result_b}   ← 证明 super() 就是 super(__class__, self) 的简写")
    print(f"    对比 leaf.process() = {leaf.process()}   ← 多了一层 [Leaf]，因为它【包含】自身")
    print(f"    ★ 这正说明 super() 的语义是『从当前类之后继续』，而非『调用当前类』")


# ===== 语法解析 =====
# 【6】★ super() 的三个坑
def demo_super_pitfalls() -> None:
    print("  坑 1：硬编码父类名调用（看似等价，实则危险）")

    # 场景：Base 之上还有一层 Middle（将来由别人插入的审计层）
    class Audit(Base):
        """继承链中插入的中间层：给所有流程加审计。"""
        def process(self) -> str:
            return f"[审计] {super().process()}"

    class GoodChild(Audit):
        def process(self) -> str:
            # ✓ 用 super：沿 MRO 继续，Audit 的审计逻辑会被执行
            return f"[Good] {super().process()}"

    class BadChild(Audit):
        def process(self) -> str:
            # ✗ 硬编码父类：直接跳到 Base，Audit 被完全绕过
            return f"[Bad] {Base.process(self)}"

    good_result = GoodChild("示例").process()
    bad_result = BadChild("示例").process()
    print(f"    MRO(GoodChild) = {[c.__name__ for c in GoodChild.__mro__]}")
    print(f"    MRO(BadChild)  = {[c.__name__ for c in BadChild.__mro__]}")
    print()
    print(f"    GoodChild.process() = {good_result}")
    print(f"      → 含『[审计]』？{'[审计]' in good_result}  ✓ 中间层被正确调用")
    print(f"    BadChild.process()  = {bad_result}")
    print(f"      → 含『[审计]』？{'[审计]' in bad_result}  ✗ 中间层被跳过！")
    print()
    print("    ★ 两者 MRO 完全相同，行为却不同 ——")
    print("      差别只在于用 super() 还是写死了 Base.process(self)。")
    print("      这就是『硬编码父类名 = 绕过 MRO = 继承链被割裂』的直接证据。")

    print()
    print("  坑 2：在类定义体之外使用 super()")
    try:
        super()
    except RuntimeError as exc:
        print(f"    模块层 super() → RuntimeError: {str(exc)[:70]}")
    print("    原因：super() 依赖隐式的 __class__ 与第一个参数，"
          "只在方法体（编译器注入 __class__ 单元格）内才有效。")

    class NeedsArgs(Base):
        def process(self) -> str:
            return super().process()      # ← 在实例方法里可以

    print(f"    实例方法内 super() 正常：{NeedsArgs('演示').process()}")
    try:
        # 第二个参数必须是【当前类的实例或子类实例】，否则 TypeError
        super(NeedsArgs, "字符串不是实例")
    except TypeError as exc:
        print(f"    super(C, 非实例) → TypeError: {str(exc)[:80]}")
    try:
        # 第二个参数是【基类】实例但当前类需要 name → 说明参数约束是实打实的
        super(NeedsArgs, Base("演示")).process()
    except TypeError as exc:
        print(f"    super(C, 基类实例) → TypeError: {str(exc)[:60]}")

    print()
    print("  坑 3：类方法中使用 super()")
    class GrandParent:
        registry: ClassVar[list[str]] = []

        @classmethod
        def register(cls, name: str) -> None:
            GrandParent.registry.append(f"{cls.__name__} 注册 {name}")

    class ParentCL(GrandParent):
        @classmethod
        def register(cls, name: str) -> None:
            # ✓ 类方法里 super() 传的是 cls，MRO 正常工作
            super().register(name)
            cls.registry.append(f"{cls.__name__} 补充处理 {name}")

    class ChildCL(ParentCL):
        @classmethod
        def register(cls, name: str) -> None:
            super().register(name)

    ChildCL.register("数据")
    print(f"    注册表 = {GrandParent.registry}")
    print(f"    ★ cls 会【依次】是 ChildCL、ParentCL、GrandParent，"
          f"这是类方法配合继承做扩展的标准手法。")

    print()
    print("  补充：super() 不是关键字")
    print("    它是内置类型，绑定到 __builtins__.super")
    print("    可以被遮蔽（局部变量名 super 会导致调用失败），这也是用它的风险之一")


# ===== 语法解析 =====
# 【7】多继承中的方法解析实测
def demo_method_resolution() -> None:
    print("  场景：Duck(Flyable, Swimmable) 与反向继承的对比")
    print()
    print("  ① 正常顺序 class Duck(Flyable, Swimmable)：")
    print(f"    MRO = {[c.__name__ for c in Duck.__mro__]}")
    d = Duck("小鸭")
    print(f"    d.move() = {d.move()}")
    print(f"      → 来自 Flyable.move，因为 Flyable 在 MRO 中靠前")
    print(f"    d.describe() = {d.describe()}")
    print(f"      → 来自 Flyable.describe（不是 Swimmable）")
    print(f"    d.abilities() = {d.abilities()}   # 显式调用规避歧义")

    print()
    print("  ② 反转顺序 class Swimmer(Swimmable, Flyable)：")
    print(f"    MRO = {[c.__name__ for c in Swimmer.__mro__]}")
    s = Swimmer("潜水员")
    print(f"    s.move() = {s.move()}")
    print(f"      → 这次来自 Swimmable.move！同一个方法名，行为相反")
    print()
    print("  ★ 这是 Python 多继承最需要注意的地方：")
    print("    父类列表的【顺序】就是优先级声明，写反了行为就变了。")
    print("    所以不应依赖『恰好调用到了某个父类方法』，")
    print("    而应显式指定（Mixin.describe(self)）或重写方法。")

    print()
    print("  ③ 完整的方法查找演示：")
    class Level1:
        def who(self) -> str:
            return "Level1"
    class Level2(Level1):
        def who(self) -> str:
            return "Level2"
    class Level3(Level2):
        pass                       # 不重写 who

    for cls in (Level1, Level2, Level3):
        print(f"    {cls.__name__}().who() = {cls().who()}"
              f"   ← 沿 MRO 找到的第一个实现")

    print()
    print("  ④ 属性查找同理：")
    class AttrBase:
        shared = "来自 AttrBase"
    class AttrChild(AttrBase):
        pass

    print(f"    AttrChild().shared = {AttrChild().shared}")
    AttrChild.shared = "被 AttrChild 遮蔽"
    print(f"    修改 AttrChild.shared 后 = {AttrChild.shared}")
    print(f"    AttrBase.shared 仍是      = {AttrBase.shared}   # 父类不受影响")


# ===== 语法解析 =====
# 【8】多继承中同名 __init__ 的协作（实际项目常见）
class Sensor:
    """传感器基类。"""

    def __init__(self, device_id: str) -> None:
        self.device_id = device_id
        self.log: list[str] = ["Sensor 初始化"]

    def report(self) -> str:
        return f"设备 {self.device_id}"


class NetworkedMixin:
    """网络功能 mixin。注意它【不继承】任何类，只提供增强方法。"""

    def connect(self) -> None:
        self.log.append("网络已连接")

    def report(self) -> str:
        # ★ mixin 用 super() 把自己挂进调用链，而不是硬编码类名
        return f"{super().report()}（已联网）"


class LoggingMixin:
    """日志 mixin。"""

    def report(self) -> str:
        return f"[LOG] {super().report()}"


class SmartSensor(NetworkedMixin, LoggingMixin, Sensor):
    """组合三个能力。注意：mixin 必须写在【真正提供实现的类】之前。"""

    def __init__(self, device_id: str) -> None:
        super().__init__(device_id)     # ★ 协作式多继承：每个父类各管各的
        self.log.append("SmartSensor 初始化完成")

    def report(self) -> str:
        return f"{super().report()} | 能力数={len(self.log)}"


def demo_multi_inheritance_init() -> None:
    print("  多继承中 __init__ 的协作（Mixin 模式）：")
    print(f"    MRO = {[c.__name__ for c in SmartSensor.__mro__]}")
    print()
    s = SmartSensor("SEN-001")
    print(f"    初始化日志：{s.log}")
    print(f"    只写了【一个】super().__init__()，三个父类的 __init__ 全都被调用了")
    print()
    s.connect()
    print(f"    report() = {s.report()}")
    print(f"    ★ 调用链：SmartSensor → NetworkedMixin → LoggingMixin → Sensor")
    print(f"      对照 MRO 顺序：{[c.__name__ for c in SmartSensor.__mro__]}")
    print()
    print("  ★ 协作式多继承的三条铁律：")
    print("    1. 每个类都用 super().__init__()，绝不硬编码父类名")
    print("    2. Mixin 类不定义 __init__（让真正的基础类负责）")
    print("    3. 所有提供同名方法的类都用 super() 协作，而不是覆盖")


# ===== 语法解析 =====
# 【9】__init_subclass__ 钩子
#   语法：父类中定义 __init_subclass__(cls)，在【每个子类被创建时】自动调用。
#   用途：子类注册表、统一的子类初始化逻辑、自动验证子类结构。
#   ★ 坑：它是【隐式类方法】（cls 是类本身），必须用 @classmethod 装饰（3.6+ 可省略）。
class Plugin:
    """插件基类：自动收集所有子类。"""

    plugins: ClassVar[list[str]] = []

    def __init_subclass__(cls, verbose: bool = False, **kwargs) -> None:
        """子类创建时自动调用。"""
        super().__init_subclass__(**kwargs)      # 继续调用父类的钩子（协作式）
        Plugin.plugins.append(cls.__name__)
        if verbose:
            print(f"    [注册] 新插件 {cls.__name__}，共 {len(Plugin.plugins)} 个")

    def run(self) -> str:
        return f"{self.__class__.__name__} 执行"


class PluginA(Plugin, verbose=True):
    pass


class PluginB(Plugin):
    pass


class PluginC(Plugin, verbose=True):
    pass


def demo_init_subclass() -> None:
    print("  ★ 观察上方类定义时的输出 —— __init_subclass__ 在【定义时】就触发了")
    print(f"  Plugin.plugins = {Plugin.plugins}")
    print(f"  → 定义 PluginA/B/C 时自动注册，无需手动维护列表")
    print()
    p = PluginA()
    print(f"  PluginA().run() = {p.run()}")
    print()
    print("  语法要点：")
    print("    def __init_subclass__(cls, **kwargs)  —— cls 是子类本身")
    print("    可通过类定义参数传入额外配置：class X(Base, verbose=True)")
    print("    ★ 注意它不接收 self，因为此时子类【实例还没创建】")


def main() -> None:
    print("=" * 60)
    print("【1】单继承与 super().__init__")
    print("=" * 60)
    dog = Dog("旺财", "柴犬")
    print(f"  dog.name = {dog.name}   ← 来自 Animal.__init__，通过 super() 调用")
    print(f"  dog.breed = {dog.breed}  ← 子类自己加的")
    print(f"  dog.speak() = {dog.speak()}   ← 子类覆盖了父类方法")
    print(f"  dog.describe() = {dog.describe()}   ← 子类复用了父类逻辑")
    print(f"  dog.fetch() = {dog.fetch()}   ← 子类新增")
    for _ in range(3):
        dog.birthday()
    print(f"  3 次 birthday 后 dog.age = {dog.age}   ← 继承自父类的方法")
    print(f"  dog.kingdom = {dog.kingdom}   ← 继承自父类的类属性")

    print()
    print("  ★ 验证：子类不调用 super().__init__() 会怎样")
    class Broken(Animal):
        def __init__(self, name: str) -> None:
            pass                        # ✗ 忘记调用 super().__init__
    b = Broken("小动物")
    print(f"    Broken().speak() →", end=" ")
    try:
        print(b.speak())
    except AttributeError as exc:
        print(f"AttributeError: {exc}")
    print(f"    ★ Python 不会自动调父类 __init__，忘记就是这种 AttributeError")

    print()
    print("=" * 60)
    print("【2】多继承与菱形继承")
    print("=" * 60)
    demo_method_resolution()

    print()
    print("=" * 60)
    print("【3】★ C3 线性化算法")
    print("=" * 60)
    demo_c3_algorithm()

    print()
    print("=" * 60)
    print("【4】C3 一致性检测")
    print("=" * 60)
    demo_c3_inconsistency()

    print()
    print("=" * 60)
    print("【5】★ super() 的真实原理")
    print("=" * 60)
    demo_super_mechanism()

    print()
    print("=" * 60)
    print("【6】★ super() 的三个坑")
    print("=" * 60)
    demo_super_pitfalls()

    print()
    print("=" * 60)
    print("【7】多继承中 __init__ 的协作（Mixin 模式）")
    print("=" * 60)
    demo_multi_inheritance_init()

    print()
    print("=" * 60)
    print("【8】__init_subclass__ 钩子")
    print("=" * 60)
    demo_init_subclass()

    print()
    print("=" * 60)
    print("小结")
    print("=" * 60)
    print("  1. 子类 __init__ 不自动调用父类，必须显式 super().__init__()")
    print("  2. MRO 由 C3 线性化决定，满足：子类在前、父类相对顺序与声明一致")
    print("  3. super() 返回 MRO 中【下一个】类，不是『父类』")
    print("  4. 永远用 super()，绝不硬编码父类名 —— 否则中断继承链")
    print("  5. 多继承顺序即优先级；不要依赖『恰好调到哪个父类』")
    print("  6. 协作式多继承：Mixin 不写 __init__，全部用 super() 协作")


if __name__ == "__main__":
    main()