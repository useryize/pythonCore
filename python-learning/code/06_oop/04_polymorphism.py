"""
================================================================================
 04_polymorphism.py  ——  多态、鸭子类型、ABC 与 Mixin
================================================================================

【演示的语法点】
 1. 多态的三种实现层次：继承多态、鸭子类型、抽象基类
 2. ★ 鸭子类型（Duck Typing）："如果它走起来像鸭子、叫起来像鸭子，它就是鸭子"
 3. ★ 抽象基类 ABC：ABCMeta 元类、@abstractmethod、抽象类不能实例化
 4. 抽象方法的三种实现：继承实现、register() 虚拟子类、__subclasshook__
 5. ★ 组合 vs 继承：is-a vs has-a，对比代码与内存/耦合度分析
 6. ★ Mixin 模式：定义、命名约定（MixIn 后缀）、不继承、不写 __init__、用 super() 协作
 7. 运行时多态 vs 编译时多态（Python 只有前者）
 8. 运算符重载作为多态的另一种形式（引出 05_magic_methods）
 9. 方法解析顺序对 Mixin 的影响（Mixin 必须放在基类之前）
10. 鸭子类型的局限与 Protocol 的补足

【预期输出摘要】
 - "ABC" 小节真实抛出 TypeError（不能实例化抽象类）与 NotImplementedError
 - "组合vs继承" 小节打印两者的内存与耦合对比
 - "Mixin" 小节打印完整的协作链式输出
================================================================================

"""

from __future__ import annotations

import abc
import time
from typing import Any, Protocol, runtime_checkable


# ===== 语法解析 =====
# 【1】继承多态：基类定义接口，子类各自实现
#   前提：有继承关系（同宗）。
#   价值：编译器/IDE 能发现"漏实现方法"的错误。
#   局限：非本类的对象无法参与（除非刚好继承同一基类）。
class PaymentMethod(abc.ABC):
    """支付方式抽象基类。"""

    @abc.abstractmethod
    def pay(self, amount: float) -> str:
        """抽象方法：子类必须实现。返回支付凭证字符串。"""

    def describe(self) -> str:
        """具体方法：所有子类共享的公共逻辑。"""
        return f"{self.__class__.__name__} 支付"


class Alipay(PaymentMethod):
    def pay(self, amount: float) -> str:
        return f"支付宝支付 {amount:.2f} 元成功"


class WeChatPay(PaymentMethod):
    def pay(self, amount: float) -> str:
        return f"微信支付 {amount:.2f} 元成功"


class BankCard(PaymentMethod):
    def pay(self, amount: float) -> str:
        return f"银行卡支付 {amount:.2f} 元成功"


# ===== 语法解析 =====
# 【2】★ 鸭子类型：Python 真正的多态基础
#   核心思想：不检查类型，只检查"有没有需要的方法"。
#   语法：不需要任何声明 —— 只要对象上有该方法就能调用。
#   ★ 这就是为什么 Python 里不需要接口就能实现多态：
#     函数在【运行时】才决定调用哪个实现（动态绑定）。
#   设计意图：降低耦合，让"能协作"的对象协作，而不强制"血缘关系"。
#   代价：没有编译期检查，缺方法要到运行时才报错。
def process_payment(method: Any, amount: float) -> str:
    """接受任意支付方式 —— 只要求它有 pay 方法。

    ★ 注意类型注解用了 Any 而不是 PaymentMethod：
      这就是鸭子类型的精髓 —— 函数不关心参数到底是什么类型，
      只关心它能不能完成 pay() 这件事。
    """
    return method.pay(amount)


class CashPayment:
    """鸭子：一个完全没有继承 PaymentMethod 的类。"""
    def pay(self, amount: float) -> str:
        return f"现金支付 {amount:.2f} 元成功"

    def describe(self) -> str:
        return "CashPayment 支付"


class DuckTypedProcessor:
    """鸭子类型的经典案例：任何有 read 方法的对象都能用。"""
    def process(self, source: Any) -> str:
        return f"读取到：{source.read()}"


# ===== 语法解析 =====
# 【3】★ 抽象基类 ABC 的完整机制
#   语法要点：
#     - class Foo(abc.ABC)            让类使用 ABCMeta 元类
#     - @abc.abstractmethod           标记抽象方法
#   运行时行为：
#     ① ABCMeta 会在【实例化时】检查是否还有未实现的抽象方法；
#        只要有一个未实现，实例化就抛 TypeError。
#     ② 抽象方法可以带默认实现（子类可以 super() 调用），
#        也可以完全空实现（pass / ...）。
#   ★ 关键区别：abstractmethod【不阻止继承】，只阻止【实例化】。
#     这让抽象基类既能当接口契约，又能提供共享实现。
class Shape(abc.ABC):
    """几何图形抽象基类。"""

    def __init__(self, name: str) -> None:
        self.name = name

    @abc.abstractmethod
    def area(self) -> float:
        """必须由子类实现的面积计算。"""

    @abc.abstractmethod
    def perimeter(self) -> float:
        """必须由子类实现的周长计算。"""

    def summary(self) -> str:
        """具体方法：子类共享的展示逻辑。"""
        # 调用抽象方法 —— 运行时实际会分派到子类的实现（多态）
        return f"{self.name}: 面积={self.area():.2f}, 周长={self.perimeter():.2f}"


class Rectangle(Shape):
    def __init__(self, w: float, h: float) -> None:
        super().__init__("矩形")
        self.w = w
        self.h = h

    def area(self) -> float:
        return self.w * self.h

    def perimeter(self) -> float:
        return 2 * (self.w + self.h)


class Circle(Shape):
    PI = 3.1415926

    def __init__(self, r: float) -> None:
        super().__init__("圆形")
        self.r = r

    def area(self) -> float:
        return self.PI * self.r ** 2

    def perimeter(self) -> float:
        return 2 * self.PI * self.r

    @property
    def diameter(self) -> float:
        """派生属性。"""
        return 2 * self.r


# ===== 语法解析 =====
# 【4】★ 抽象方法的第三种实现：把"非抽象方法"也标成抽象
#   @abc.abstractmethod 并不强制方法体为空，你可以给它一个默认实现，
#   效果是：子类【可以】不重写（直接用父类实现），但语义上标记为"核心方法"。
#   应用：Template Method 模式中，把"可选覆盖"的关键步骤标记出来。
class DataProcessor(abc.ABC):
    """数据处理流水线模板。"""

    def process(self, data: str) -> str:
        """模板方法：定义固定的算法骨架，步骤由子类填充。"""
        cleaned = self.clean(data)
        validated = self.validate(cleaned)
        return self.transform(validated)

    def clean(self, data: str) -> str:
        """可选步骤：子类可覆盖。"""
        return data.strip()

    @abc.abstractmethod
    def validate(self, data: str) -> str:
        """必须实现的校验步骤。"""

    def transform(self, data: str) -> str:
        """可选步骤。"""
        return data.upper()


class StrictProcessor(DataProcessor):
    def validate(self, data: str) -> str:
        if not data:
            raise ValueError("数据不能为空")
        return data


class UpperProcessor(DataProcessor):
    def validate(self, data: str) -> str:
        return data

    def transform(self, data: str) -> str:
        # 覆盖可选步骤（父类有默认实现）
        return f"<<{data.lower()}>>"


# ===== 语法解析 =====
# 【5】★ 虚拟子类 register()：不需要真的继承
#   语法：Base.register(SomeClass)
#   语义：把一个【不继承 Base】的类"登记"为 Base 的虚拟子类，
#         这样 isinstance(x, Base) 就返回 True，且 Base 的方法可被调用。
#   用途：
#     a) 让第三方的类满足接口（无法修改其继承关系时的适配手段）
#     b) 把【结构相似】的类归为一类（如所有"有 read 方法"的都算 Reader）
#   ★ 局限：register() 只影响 isinstance/issubclass，
#     不提供抽象方法的强制实现检查。
class Reader(abc.ABC):
    """读取器抽象基类。"""

    @abc.abstractmethod
    def read(self) -> str:
        ...

    @abc.abstractmethod
    def close(self) -> None:
        ...


class FileHandle:
    """普通类：完全不继承 Reader，但有 read/close 方法。"""

    def __init__(self, path: str) -> None:
        self.path = path

    def read(self) -> str:
        return f"文件内容({self.path})"

    def close(self) -> None:
        print(f"    关闭文件 {self.path}")


class NativeReader(Reader):
    """正常继承的实现。"""
    def read(self) -> str:
        return "原生读取内容"
    def close(self) -> None:
        print("    原生读取器已关闭")


# ===== 语法解析 =====
# 【6】★ __subclasshook__：用"结构相似"自动归类
#   语法：定义类方法 __subclasshook__(cls, subclass)，返回 True/False/NotImplemented
#   语义：自定义 issubclass() 的判定逻辑 —— 只要子类有全部必需方法，就算子类。
#   ★ 这就是鸭子类型的【静态版本】，也是 collections.abc 大量采用的做法
#     （如 Iterable、Container、Hashable 都靠这个自动识别）。
class Closeable(abc.ABC):
    """可关闭对象：结构化判定 —— 任何有 close 方法的类都算。"""

    @abc.abstractmethod
    def close(self) -> None:
        """逻辑上的契约（实际不强制实现）。"""

    @classmethod
    def __subclasshook__(cls, subclass: type) -> Any:
        """自定义子类判定：有 close 方法即可。"""
        if cls is Closeable:
            # 遍历子类的 MRO，任一层有 close 就算
            if any("close" in klass.__dict__ for klass in subclass.__mro__):
                return True
            return NotImplemented
        return NotImplemented


# ===== 语法解析 =====
# 【7】★ 组合 vs 继承（is-a vs has-a）
#   继承 = is-a：子类【是一种】父类。子类型可替换父类型（Liskov 替换原则）。
#   组合 = has-a：一个对象【持有】另一个对象。
#   判断准则："is-a" 说不通就用组合。
#   对比维度：
#     耦合度：继承 → 父子紧耦合（改父类影响子类）；组合 → 松耦合
#     灵活性：继承的层次固定在编译/定义期；组合的组成可在运行时任意改变
#     复用：继承复用【代码】；组合复用【对象/功能】
class Engine:
    """发动机：被拥有（has-a），而不是被继承。"""

    def __init__(self, power: float) -> None:
        self.power = power
        self.running = False

    def start(self) -> str:
        self.running = True
        return f"{self.power}马力发动机启动"

    def stop(self) -> str:
        self.running = False
        return "发动机关闭"


class Wheel:
    def __init__(self, size: int = 15) -> None:
        self.size = size


# ---- 继承版：Car 是一种 Vehicle ----
class Vehicle:
    """交通工具。"""

    def __init__(self, name: str) -> None:
        self.name = name

    def move(self) -> str:
        return f"{self.name} 在移动"

    def describe(self) -> str:
        return f"【继承】{self.move()}，类型={type(self).__name__}"


class Car(Vehicle):
    """汽车【是一种】交通工具 —— is-a，成立，用继承。"""

    def __init__(self, name: str, engine: Engine) -> None:
        super().__init__(name)
        # ★ 注意：这里【持有】 engine，而不是继承 Engine
        self.engine = engine
        self.wheels = [Wheel() for _ in range(4)]

    def move(self) -> str:
        return f"{self.name} 启动发动机后在移动"

    def start(self) -> str:
        return self.engine.start()


# ---- 组合版：Car 用组合而非继承 ----
class MovableCar:
    """汽车【拥有】发动机与车轮 —— has-a，用组合。"""

    def __init__(self, name: str, engine: Engine) -> None:
        self.name = name
        self.engine = engine          # 组合的关键：把对象存为属性
        self.wheels = [Wheel() for _ in range(4)]

    def move(self) -> str:
        return f"{self.name}（组合版）在移动"

    def start(self) -> str:
        # ★ 运行时可自由替换内部引擎 —— 这就是组合的灵活性
        return self.engine.start()

    def upgrade_engine(self, new_engine: Engine) -> None:
        """运行时改变内部实现，继承做不到这一点。"""
        self.engine = new_engine


# ===== 语法解析 =====
# 【8】★ Mixin 模式
#   定义：Mixin 是一个【提供能力但不表达 is-a 关系】的类。
#   四条铁律（违反任何一条都会出问题）：
#     1. 命名以 Mixin 结尾（语义提示：这不是基类）
#     2. 不继承任何类（除 object）
#     3. 不定义 __init__（构造统一由真正的基类负责）
#     4. 方法里用 super() 协作，而不是硬编码类名
#   使用：class 目标类(Mixin1, Mixin2, 真正基类)
#         ★ Mixin 必须放在基类【之前】，否则 MRO 会先找到基类的实现。
class JsonMixin:
    """Mixin：提供 JSON 序列化能力。不表达 is-a 关系。"""

    def to_json(self) -> str:
        """把对象的关键属性转成 JSON 字符串。"""
        # ★ 用 super() 协作：如果前面还有其他 Mixin，会被链式调用
        prefix = super().to_json() if hasattr(super(), "to_json") else ""
        return f'{prefix}{{"type": self.__class__.__name__}}'

    def log(self) -> str:
        return f"[LOG] {self.__class__.__name__}"


class ValidationMixin:
    """Mixin：提供校验能力。"""

    def to_json(self) -> str:
        return super().to_json()

    def validate(self) -> bool:
        """校验钩子：基类提供具体校验逻辑。"""
        return hasattr(self, "name") and bool(getattr(self, "name"))


class Entity:
    """真正的基类：提供核心数据与实现。"""

    def __init__(self, name: str) -> None:
        self.name = name

    def to_json(self) -> str:
        """基类的序列化实现 —— Mixin 会通过 super() 走到这里。"""
        return f'{{"name": "{self.name}"}}'


class UserEntity(ValidationMixin, JsonMixin, Entity):
    """组合三个能力。注意 MRO 顺序：Mixin 在前，基类在后。"""

    def validate(self) -> bool:
        return len(self.name) > 0 and super().validate()


# ---- 顺序错误的反例 ----
class WrongOrder(JsonMixin, Entity):
    """顺序其实也对（Mixin 在前），但看下一个反例更清楚。"""


class WrongOrder2(Entity, JsonMixin):
    """★ 错误：基类写在前面 —— MRO 会先命中 Entity.to_json，Mixin 的增强失效。"""

    def to_json(self) -> str:
        return f"{super().to_json()}  # 注意：基类在前，Mixin 被跳过"


# ===== 语法解析 =====
# 【9】Protocol：鸭子类型的静态版本
#   Protocol（PEP 544）：结构化子类型 —— 不需要继承，只要结构满足即可。
#   ★ 与 ABC.register() 的区别：
#     register()  ：运行时判定（isinstance），不提供静态检查
#     Protocol    ：主要给静态类型检查器（mypy）用，可选支持运行时 isinstance
#   何时选哪个：
#     需要【强制子类实现契约】→ ABC
#     只是【能力识别】→ Protocol
@runtime_checkable
class Drawable(Protocol):
    """可绘制协议：只要有 draw 方法即可。"""

    def draw(self) -> str: ...


class CircleDrawer:
    def draw(self) -> str:
        return "画圆"

    def fill(self) -> str:
        return "填充颜色"


class NoDraw:
    def write(self) -> str:
        return "只是写字，不是绘制"


# ===== 语法解析 =====
# 【10】运行时多态的机制
#   Python 只有【运行时多态】：
#     obj.method() 在【运行时】才确定调哪个函数（动态绑定）。
#   原理：属性查找沿 MRO 找第一个同名函数对象 → 生成绑定方法 → 调用。
#   对比其他语言：
#     Java/C++ 有【编译时多态】（重载按参数静态绑定）+【运行时多态】（重写）
#     Python 把两者统一为运行时绑定，所以更灵活但也更难优化。
def demo_runtime_polymorphism() -> None:
    shapes: list[Shape] = [Rectangle(3, 4), Circle(2)]
    print("  同一段代码处理不同类型的对象：")
    for s in shapes:
        print(f"    {s.summary()}")
        # area() 在基类是抽象方法，这里实际调用子类的实现
        print(f"      → type(s).area.__qualname__ = {type(s).area.__qualname__}")

    print()
    print("  运行时绑定验证：")
    r = Rectangle(1, 2)
    print(f"    r.area           → 绑定方法 {r.area}")
    print(f"    r.area.__self__  → {r.area.__self__ is r}")
    print(f"    Shape.area       → 未绑定函数 {Shape.area}")
    print(f"    Shape.area.__self__ 存在吗：{hasattr(Shape.area, '__self__')}")

    print()
    print("  一次循环，调用了 3 个不同类的实现 —— 这就是多态：")
    total_area = sum(s.area() for s in shapes)
    print(f"    总面积 = {total_area:.2f}   # 代码里没出现任何 if isinstance 判断")


def main() -> None:
    print("=" * 60)
    print("【1】继承多态")
    print("=" * 60)
    methods: list[PaymentMethod] = [Alipay(), WeChatPay(), BankCard()]
    for m in methods:
        print(f"  {m.describe()} → {m.pay(99.9)}")
    print(f"  三个不同实现，调用代码完全相同 → 这就是多态")

    print()
    print("=" * 60)
    print("【2】★ 鸭子类型")
    print("=" * 60)
    print(f"  继承体系内的：{process_payment(Alipay(), 50)}")
    print(f"  鸭子类型（未继承 PaymentMethod）：{process_payment(CashPayment(), 50)}")
    print(f"    isinstance(CashPayment(), PaymentMethod) = "
          f"{isinstance(CashPayment(), PaymentMethod)}")
    print("    → 函数根本不检查类型，只要有 pay 方法即可，这就是鸭子类型")

    print()
    print("  经典鸭子类型案例（任何有 read() 的对象）：")
    class StringIO:
        """标准库风格的鸭子：只要有 read 就能被 DuckTypedProcessor 处理。"""
        def __init__(self, s: str) -> None:
            self.s = s
        def read(self) -> str:
            return self.s
    print(f"    {DuckTypedProcessor().process(StringIO('hello'))}")

    class FileDuck:
        """另一个鸭子：完全不同的类，只因有 read() 就能被处理。"""
        def read(self) -> str:
            return "文件里的内容"

    print(f"    {DuckTypedProcessor().process(FileDuck())}   # 结构不同，行为相同")
    print("    ★ DuckTypedProcessor 从不检查类型，只调用 read() —— 这就是鸭子类型")

    print()
    print("  鸭子的代价：缺方法要到运行时才发现")
    class NoPay:
        pass
    try:
        process_payment(NoPay(), 10)
    except AttributeError as exc:
        print(f"    NoPay 没有 pay → AttributeError: {exc}")
    print("    → 这是鸭子类型唯一的缺点：缺乏编译期检查")

    print()
    print("=" * 60)
    print("【3】★ 抽象基类 ABC")
    print("=" * 60)
    print("  抽象类【不能实例化】：")
    try:
        Shape("测试")           # type: ignore[abstract]
    except TypeError as exc:
        print(f"    Shape('测试') → TypeError: {str(exc)[:80]}")

    print()
    print("  子类漏实现抽象方法 → 同样不能实例化：")
    class IncompleteShape(Shape):
        def area(self) -> float:
            return 0.0
        # ✗ 漏了 perimeter()
    try:
        IncompleteShape("测试")     # type: ignore[abstract]
    except TypeError as exc:
        print(f"    漏实现 perimeter → TypeError: {str(exc)[:75]}")

    print()
    print("  完整子类正常工作：")
    rect = Rectangle(3, 4)
    circle = Circle(2)
    print(f"    {rect.summary()}")
    print(f"    {circle.summary()}")
    print(f"    circle.diameter = {circle.diameter}   # 圆形特有的派生属性")
    print(f"    isinstance(rect, Shape) = {isinstance(rect, Shape)}")
    print(f"    ABC 的抽象检查发生在【实例化时】，不是定义时")

    print()
    print("  抽象方法可以有默认实现（Template Method）：")
    p1 = StrictProcessor()
    p2 = UpperProcessor()
    print(f"    StrictProcessor.process('  hello  ') = {p1.process('  hello  ')}")
    print(f"    UpperProcessor.process('  Hi  ')    = {p2.process('  Hi  ')}")
    print(f"    ★ 上层 process() 骨架固定，clean/validate/transform 由子类填充")

    print()
    print("=" * 60)
    print("【4】虚拟子类 register()")
    print("=" * 60)
    fh = FileHandle("data.txt")
    print(f"  register 前：isinstance(FileHandle(), Reader) = "
          f"{isinstance(fh, Reader)}")
    Reader.register(FileHandle)          # 登记为虚拟子类
    print(f"  register 后：isinstance(FileHandle(), Reader) = "
          f"{isinstance(fh, Reader)}   ✓")
    print(f"    issubclass(FileHandle, Reader) = {issubclass(FileHandle, Reader)}")
    print(f"    MRO 仍然是 {[c.__name__ for c in FileHandle.__mro__]}   # 没有真的继承")
    print(f"  真实子类仍然正常：{isinstance(NativeReader(), Reader)}")
    print(f"    ★ register 只影响 isinstance/issubclass，不强制实现抽象方法")
    print()
    print("  补充：register 的影响是【全局且不可撤销】的（ABCMeta 内部以 C 结构存储），")
    print("        因此在真实项目中注册虚拟子类要谨慎 —— 一旦注册，")
    print("        所有 isinstance 检查都会认为该类是 Reader。")
    print("        排查此类'诡异 isinstance'问题时，第一件事就是查有没有 register。")
    print()
    print("  正确用法示例（按能力动态归类，而非污染类型体系）：")
    # 不 register，而是直接按能力判断 —— 这才是日常推荐做法
    def is_readlike(obj: Any) -> bool:
        """鸭子类型的能力检查：无需修改任何类的注册表。"""
        return callable(getattr(obj, "read", None))
    print(f"    is_readlike(fh) = {is_readlike(fh)}   # FileHandle 实例有 read")
    print(f"    is_readlike(Alipay()) = {is_readlike(Alipay())}   # 没有 read")
    print("    ★ 想要'按能力归类'时，写个判断函数即可，不必动用 register")

    print()
    print("=" * 60)
    print("【5】__subclasshook__：结构化归类")
    print("=" * 60)
    print(f"  FileHandle 有 close 方法 → 是 Closeable 的子类吗："
          f"{issubclass(FileHandle, Closeable)}")
    class NoClose:
        def open(self) -> None: ...
    print(f"  无 close 的类 → {issubclass(NoClose, Closeable)}")
    print(f"  str（无 close）→ {issubclass(str, Closeable)}")
    print(f"  list（无 close）→ {issubclass(list, Closeable)}")
    print("  ★ 这就是 collections.abc 判定 Iterable/Hashable 等的方式")
    fh.close()                          # 结构满足就能用 Closeable 的契约

    print()
    print("=" * 60)
    print("【6】★ 组合 vs 继承")
    print("=" * 60)
    print("  【继承版 Car(Vehicle)】—— is-a：汽车【是一种】交通工具")
    engine1 = Engine(200)
    car1 = Car("特斯拉", engine1)
    print(f"    isinstance(car1, Vehicle) = {isinstance(car1, Vehicle)}   # 是 Vehicle 的子类")
    print(f"    {car1.describe()}")
    print(f"    启动：{car1.start()}")

    print()
    print("  【组合版 MovableCar】—— has-a：汽车【拥有】发动机")
    car2 = MovableCar("比亚迪", Engine(150))
    print(f"    isinstance(car2, Vehicle) = {isinstance(car2, Vehicle)}   # 不是，靠鸭子类型")
    print(f"    {car2.move()}")
    print(f"    启动：{car2.start()}")

    print()
    print("  ★ 组合的关键优势：运行时替换内部实现（继承做不到）：")
    print(f"    替换前：{car2.engine.power} 马力")
    car2.upgrade_engine(Engine(400))     # 直接换掉发动机对象
    print(f"    替换后：{car2.engine.power} 马力，启动 → {car2.start()}")
    print(f"    继承版做不到这一点：Engine 不是 Car 的父类，无法『替换』")

    print()
    print("  内存与耦合对比：")
    print("    继承：Car 与 Vehicle 是强耦合 —— 改 Vehicle 会影响所有子类")
    print("    组合：MovableCar 只依赖 Engine 的【接口】 —— 可换成任何带 start 的对象")
    print("    继承 = 复用代码；组合 = 复用对象")
    print()
    print("  判据：说不清『X 是一种 Y』就用组合。")
    print("    引擎【是一种】交通工具吗？不是 → 不该让 Car 继承 Engine")
    print("    狗【是一种】动物吗？是 → 继承合适")

    print()
    print("=" * 60)
    print("【7】★ Mixin 模式")
    print("=" * 60)
    ue = UserEntity("张三")
    print(f"  MRO = {[c.__name__ for c in UserEntity.__mro__]}")
    print()
    print(f"  UserEntity('张三').to_json() = {ue.to_json()}")
    print(f"  调用链：ValidationMixin → JsonMixin → Entity（沿 MRO 由 super() 串联）")
    print(f"  validate() = {ue.validate()}   ← 子类覆盖后仍用 super() 协作")

    print()
    print("  对比：Mixin 顺序错误的反例")
    print(f"    class Entity, JsonMixin  → MRO = "
          f"{[c.__name__ for c in WrongOrder2.__mro__]}")
    print(f"    实体 to_json()           = {WrongOrder2('王五').to_json()}")
    print(f"    → Entity 在 MRO 中【先于】JsonMixin，所以基类实现胜出，Mixin 增强失效")
    print(f"    ★ 铁律：Mixin 必须写在真正基类的【前面】")

    print()
    print("  Mixin 四条铁律（本节代码逐条演示）：")
    print("    1. 命名带 Mixin 后缀        ✓ JsonMixin / ValidationMixin")
    print("    2. 不继承任何类             ✓ 两者的 __bases__ = "
          f"({JsonMixin.__bases__[0].__name__},)")
    print("    3. 不定义 __init__           ✓ "
          f"{'__init__' not in JsonMixin.__dict__}")
    print("    4. 方法内用 super() 协作     ✓ JsonMixin.to_json 调用了 super().to_json()")

    print()
    print("=" * 60)
    print("【8】Protocol：鸭子类型的静态版")
    print("=" * 60)
    cd = CircleDrawer()
    print(f"  CircleDrawer 有 draw() → isinstance(CircleDrawer(), Drawable) = "
          f"{isinstance(cd, Drawable)}")
    print(f"  NoDraw 没有 draw()      → isinstance(NoDraw(), Drawable) = "
          f"{isinstance(NoDraw(), Drawable)}")
    print(f"  Protocol 也能直接调用方法：{cd.draw()}")
    print(f"  但 NoDraw 无法使用 draw()：", end=" ")
    try:
        NoDraw().draw()
    except AttributeError as exc:
        print(f"AttributeError")
    print("  ★ Protocol 主要价值在【静态检查】（mypy 能报错），运行期只是辅助")

    print()
    print("=" * 60)
    print("【9】运行时多态机制")
    print("=" * 60)
    demo_runtime_polymorphism()

    print()
    print("=" * 60)
    print("【10】三种多态实现方式对比")
    print("=" * 60)
    print("  | 方式          | 需要继承 | 编译期检查 | 灵活性 | 适用场景|")
    print("  |---------------|----------|-----------|-------|---------|")
    print("  | 鸭子类型      | ✗        | ✗         | 最高  | 内部工具、同项目内|")
    print("  | ABC 抽象基类  | ✓        | ✓(我的py) | 中    | 插件体系、第三方扩展|")
    print("  | Protocol      | ✗        | ✓(mypy)   | 高    | 想同时要结构化+静态检查|")
    print("  | register()    | ✗        | ✗         | 中    | 适配【已有的】第三方类|")
    print()
    print("  选择建议：")
    print("    · 团队内部协作、追求简洁 → 鸭子类型")
    print("    · 需要防止子类漏实现 → ABC")
    print("    · 要用类型检查器保证质量 → Protocol")
    print("    · 第三方类无法修改继承关系 → register()")

    print()
    print("=" * 60)
    print("小结")
    print("=" * 60)
    print("  1. 多态的本质是『同一调用点、不同实现』，Python 全部是运行时绑定")
    print("  2. 鸭子类型最灵活但无编译期检查，是 Python 多态的基础")
    print("  3. ABC 用 @abstractmethod 在实例化时强制子类实现契约")
    print("  4. register() 与 __subclasshook__ 让不继承的类也能满足协议")
    print("  5. 组合(浅耦合、可运行时替换) 通常优于 继承(深耦合、层次固定)")
    print("  6. Mixin 复用横向能力：命名带 Mixin、不继承、不写 __init__、用 super() 协作")
    print("  7. Mixin 必须排在基类之前，否则 MRO 顺序会让基类实现胜出")


if __name__ == "__main__":
    main()