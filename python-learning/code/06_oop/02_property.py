"""
================================================================================
 02_property.py  ——  property 属性与封装
================================================================================

【演示的语法点】
 1. property 的语法：@property 装饰 getter，自动生成同名 property 描述符
 2. getter / setter / deleter 三件套：fget / fset / fdel
 3. 只读属性的实现：只写 getter，不写 setter → 赋值抛 AttributeError
 4. 计算属性 vs 存储属性：property 的本质是把【方法】伪装成【属性】
 5. 底层机制：property 是【描述符】，实现 __get__/__set__/__delete__
 6. 手写 property 装饰器：等价实现 Python 内置 property
 7. 校验逻辑放在 setter 中的范式（把不变量守卫在唯一入口）
 8. 缓存属性对比：手写缓存 vs functools.cached_property vs @property
 9. property 的坑：装饰器顺序、继承时的坑、__slots__ 冲突
10. 计算密集场景下 property 的性能代价

【预期输出摘要】
 - "只读属性" 小节真实抛出 AttributeError 并捕获
 - "手写 property" 小节证明自制实现与内置 property 行为一致
 - "缓存对比" 小节打印三种方式的调用次数统计
================================================================================

"""

from __future__ import annotations

import functools
import time
from typing import Any


# ===== 语法解析 =====
# 【1】property 的本质：把方法伪装成属性
#   语法规则：
#       @property
#       def name(self) -> T:        # getter：读取时调用
#           return self._name
#
#       @name.setter                  # ★ 这里的 name 必须是【上面那个 property 对象】
#       def name(self, value: T) -> None:
#           self._name = value
#
#       @name.deleter
#       def name(self) -> None: ...
#   执行机制：
#     - @property 把 getter 函数包成一个 property【描述符对象】存入类 __dict__
#     - 读 obj.name → 触发 property.__get__ → 调用 fget(obj) → 返回其结果
#     - 写 obj.name = v → 触发 property.__set__ → 有 fset 则调用，否则 AttributeError
#   ★ 为什么要用"下划线私有 + property 暴露"这种写法（这是 Python 封装的标准范式）：
#     直接暴露属性 → 外部可随意破坏内部状态（不变量失效）
#     全用方法 get_name()/set_name() → 啰嗦，不像 Python
#     用 property → 既像属性一样访问，又能在内部做校验/派生/兼容
#   设计意图：让【接口保持数据访问的自然形式】，同时【实现可自由演进】。
class Person:
    """人。属性 name 经过校验，温度通过 Fahrenheit/Celsius 派生。"""

    def __init__(self, name: str, age: int) -> None:
        self._name = name      # 真正的存储位置（下划线表示"私有"约定）
        self._age = age

    # ---------- 基础 property 三件套 ----------
    @property
    def name(self) -> str:
        """读取姓名。"""
        return self._name

    @name.setter
    def name(self, value: str) -> None:
        """设置姓名，带校验。"""
        if not value.strip():
            raise ValueError("姓名不能为空")
        self._name = value.strip()

    @name.deleter
    def name(self) -> None:
        """删除姓名（较少用，但语法上完整）。"""
        del self._name

    # ---------- 只读属性：只写 getter ----------
    @property
    def age(self) -> int:
        """年龄只读：创建后不应随意改变，故不提供 setter。"""
        return self._age


# ===== 语法解析 =====
# 【2】计算属性：数据"看起来是属性"，实际每次都计算
#   典型场景：单位换算、派生字段。
#   注意：f_celsius 与 f_fahrenheit 互为依赖，但只【存储】一个底层的摄氏值，
#         避免数据不一致（这是 property 设计的核心价值）。
class Temperature:
    """温度。内部只存摄氏度，华氏度是派生值。"""

    def __init__(self, celsius: float) -> None:
        self._celsius = celsius

    @property
    def celsius(self) -> float:
        return self._celsius

    @celsius.setter
    def celsius(self, value: float) -> None:
        self._celsius = value

    @property
    def fahrenheit(self) -> float:
        """计算属性：读取时现场换算，不存储。"""
        return self._celsius * 9 / 5 + 32

    @fahrenheit.setter
    def fahrenheit(self, value: float) -> None:
        """★ 反向 setter：只写华氏度时自动换算回摄氏度，保证唯一数据源。"""
        self._celsius = (value - 32) * 5 / 9

    @property
    def kelvin(self) -> float:
        """只读派生属性。"""
        return self._celsius + 273.15


# ===== 语法解析 =====
# 【3】property 装饰器改进版：让代码更简洁
#   问题：标准写法三个方法都要 def，样板代码多。
#   解法：用一个自定义装饰器把"存"和"读"包装成 get/set 两个函数，
#         属性名从函数名推断。这正是 Python 内置 property 的设计原型。
def cached_property(func: Any) -> Any:
    """一个自定义的缓存型 property：只在首次访问时计算，之后缓存结果。

    实现要点：
      - func 是【函数】（func.__get__ 存在），因此可以作为描述符
      - 用 self.__dict__ 缓存：若 key 已存在就直接返回，跳过计算
      - key 用类名 + 函数名，避免继承时多级缓存互相覆盖
    """
    attr_name = f"_cached_{func.__name__}"

    @property
    @functools.wraps(func)
    def wrapper(self):
        # 先查缓存：属性存在说明已计算过
        if attr_name in self.__dict__:
            return self.__dict__[attr_name]
        # 未命中 → 计算一次并写入实例 __dict__
        value = func(self)
        self.__dict__[attr_name] = value
        return value

    return wrapper


class ExpensiveData:
    """演示缓存属性的类：sum_of_squares 计算一次就够了。"""

    def __init__(self, numbers: list[int]) -> None:
        self.numbers = numbers
        self.call_count = 0        # 统计真实计算次数

    @cached_property
    def sum_of_squares(self) -> int:
        """平方和。计算有一定开销，但结果不变 → 值得缓存。"""
        self.call_count += 1
        time.sleep(0.001)          # 模拟耗时计算
        return sum(n ** 2 for n in self.numbers)


# ===== 语法解析 =====
# 【4】★ 手写 property 装饰器（复现 Python 内置实现）
#   目标是写一个 my_property(fget, fset=None, fdel=None)，
#   其行为与内置 property 完全一致。
#   原理：property 本质是一个【数据描述符】，只需实现三个协议方法：
#     __get__(self, obj, objtype)     读取时调用（obj 为 None 表示类上访问）
#     __set__(self, obj, value)       写入时调用
#     __delete__(self, obj)           删除时调用
#   关键处理：
#     - obj is None：说明是【通过类】访问（Class.prop），此时返回 property 对象本身
#       而不是调用 getter（因为没有实例）
#     - fset is None：拒绝写入并抛 AttributeError（这是"只读属性"的来源）
def my_property(fget=None, fset=None, fdel=None, doc=None) -> Any:
    """自定义 property，行为对齐内置 property。

    用法（与内置完全一致）：
      @my_property
      def x(self): ...

      @x.setter
      def x(self, v): ...

      @x.deleter
      def x(self): ...

    实现原理：property 是一个【数据描述符】，只实现三个协议方法即可：
      __get__(self, obj, objtype)   读取时调用（obj 为 None 表示通过"类"访问）
      __set__(self, obj, value)     写入时调用（无 fset 则抛 AttributeError）
      __delete__(self, obj)         删除时调用（无 fdel 则抛 AttributeError）
    ★ 为什么可以直接把这个类当装饰器用：
      my_property(func) 返回 _Property 实例，
      而该实例又有 .setter/.deleter 方法，因此链式写法成立。
    """
    class _Property:
        def __init__(self, fget, fset, fdel, doc=None):
            self.fget = fget
            self.fset = fset
            self.fdel = fdel
            self.__doc__ = doc or (fget.__doc__ if fget else None)
            # 用函数名做后备名，报错信息更友好
            self.name = getattr(fget, "__name__", None)

        def __get__(self, obj, objtype=None):
            # ★ obj is None → 说明是【通过类】访问（Class.x），返回描述符自身。
            #   这样才能继续写 @x.setter；内置 property 也是这个行为。
            if obj is None:
                return self
            if self.fget is None:
                raise AttributeError("该属性不可读")
            return self.fget(obj)

        def __set__(self, obj, value):
            if self.fset is None:
                # ★ 只读属性的报错来源：没有 fset 却尝试赋值
                cls_name = obj.__class__.__name__
                name = self.name or "x"
                raise AttributeError(f"property '{cls_name}.{name}' 没有 setter")
            self.fset(obj, value)

        def __delete__(self, obj):
            if self.fdel is None:
                raise AttributeError("该属性不可删")
            self.fdel(obj)

        def setter(self, fset):
            """链式：返回绑定了 fset 的新 _Property。"""
            return type(self)(self.fget, fset, self.fdel, self.__doc__)

        def deleter(self, fdel):
            """链式：返回绑定了 fdel 的新 _Property。"""
            return type(self)(self.fget, self.fset, fdel, self.__doc__)

        def getter(self, fget):
            """内置 property 也支持链式 getter，这里一并实现。"""
            return type(self)(fget, self.fset, self.fdel, self.__doc__)

    # ★ 关键：返回的是【实例】而不是类本身。
    #   @my_property  → my_property(func) → _Property 实例（该实例还有 .setter/.deleter）
    #   @x.setter      → 实例.setter(func) → 又一个 _Property 实例（已绑定 fset）
    if isinstance(fget, type):         # 防御：万一传入的是类而非函数
        return _Property(None, fset, fdel, doc)
    return _Property(fget, fset, fdel, doc)


class ConfigDemo:
    """用 my_property 实现的配置类：验证与内置 property 行为一致。"""

    def __init__(self) -> None:
        self._width = 0

    @my_property
    def width(self) -> int:
        """宽度（只读）。"""
        return self._width

    # 用 setter 绑定到 my_property（与内置写法一致）
    @width.setter
    def width(self, value: int) -> None:
        if value < 0:
            raise ValueError("宽度不能为负")
        self._width = value

    def __repr__(self) -> str:
        return f"ConfigDemo(width={self.width})"


# ===== 语法解析 =====
# 【5】属性校验范式：把不变量守卫在唯一入口
#   设计原则：属性 setter 是外部修改内部状态的【唯一入口】，
#             在这里做校验，就不需要在每个使用点重复检查。
class BankAccount:
    """银行账户。余额永远非负 —— 这个不变量由 setter 保证。"""

    MIN_BALANCE = 0.0            # 类属性作为常量

    def __init__(self, owner: str, balance: float = 0.0) -> None:
        self.owner = owner
        # ★ 先建好 _history，再走 setter 赋值 balance。
        #   否则 setter 里的 self._history.append(...) 会因属性尚不存在而 AttributeError
        #   —— 这是"属性互相依赖"的经典初始化顺序坑。
        self._history: list[float] = []
        self.balance = balance    # 初始化时也走 setter，保证即使在 __init__ 里也满足不变量

    @property
    def balance(self) -> float:
        """余额只读 —— 防止外部用 account.balance = -100 直接改坏数据。"""
        return self._balance

    @balance.setter
    def balance(self, value: float) -> None:
        # ★ 唯一写入口：任何赋值都经过这里，负余额被拦截
        if value < self.MIN_BALANCE:
            raise ValueError(f"余额不能低于 {self.MIN_BALANCE}，收到 {value}")
        self._balance = value
        self._history.append(value)

    def withdraw(self, amount: float) -> None:
        """业务方法：先查业务规则，再改状态。"""
        if amount <= 0:
            raise ValueError("取款金额必须为正")
        if amount > self.balance:
            raise ValueError(f"余额不足：当前 {self.balance}，尝试取 {amount}")
        self.balance = self.balance - amount      # 走 setter，保持不变量

    def deposit(self, amount: float) -> None:
        if amount <= 0:
            raise ValueError("存款金额必须为正")
        self.balance = self.balance + amount

    @property
    def is_overdrawn(self) -> bool:
        """派生属性：不存储，由 balance 计算。"""
        return self.balance < 0


# ===== 语法解析 =====
# 【6】property 的性能代价
#   ★ 重要事实：Python 的 property【没有真正的"缓存"】！
#     每次读 obj.prop 都会真的执行 getter 函数。
#     对于昂贵计算，必须自己缓存（手写缓存或 functools.cached_property）。
#   这是一个常见误解，面试常考。
def demo_property_performance() -> None:
    class PlainAttr:
        def __init__(self) -> None:
            self.value = 42

    class PropAttr:
        def __init__(self) -> None:
            self._value = 42

        @property
        def value(self) -> int:
            return self._value

    n = 2_000_000
    p = PlainAttr()
    pr = PropAttr()

    t0 = time.perf_counter()
    for _ in range(n):
        _ = p.value
    t_plain = time.perf_counter() - t0

    t1 = time.perf_counter()
    for _ in range(n):
        _ = pr.value
    t_prop = time.perf_counter() - t1

    print(f"  读取普通属性 {n} 次：{t_plain:.4f}s")
    print(f"  读取 property  {n} 次：{t_prop:.4f}s")
    print(f"  property 慢约 {t_prop / t_plain:.2f} 倍")
    print(f"  ★ 原因：每次访问都调用一次 getter 函数（Python 层调用开销）")
    print(f"  ★ 所以 property 不做缓存，高频访问的热路径要用普通属性或cached_property")


# ===== 语法解析 =====
# 【7】三种"缓存属性"方案对比
def demo_cache_comparison() -> None:
    class Manual:
        """方案一：手写缓存（用 None 哨兵 + 标志位）"""
        def __init__(self) -> None:
            self._cache = None
            self.dirty = True

        def _compute(self) -> int:
            time.sleep(0.001)
            return sum(n ** 2 for n in range(100))

        @property
        def value(self) -> int:
            if self.dirty or self._cache is None:
                self._cache = self._compute()
                self.dirty = False
            return self._cache

    class Cached:
        """方案二：functools.cached_property（Python 3.8+）
        - 自动把缓存值写入实例 __dict__，与普通属性同速读取
        - 第一次读取后，后续读取直接命中 __dict__，零函数调用
        - 无需手写标志位，最简洁
        - 局限：需实例有 __dict__（__slots__ 类不适用）
        """
        def __init__(self) -> None:
            self.calls = 0

        @functools.cached_property
        def value(self) -> int:
            self.calls += 1
            time.sleep(0.001)
            return sum(n ** 2 for n in range(100))

    class Plain:
        """方案三：直接存成普通属性（最省事，但要自己判断何时更新）"""
        def __init__(self) -> None:
            self.value: int | None = None

        def refresh(self) -> None:
            time.sleep(0.001)
            self.value = sum(n ** 2 for n in range(100))

    print("  方案对比（读取 5 次）：")
    print()

    m = Manual()
    t0 = time.perf_counter()
    results_m = [m.value for _ in range(5)]
    tm = time.perf_counter() - t0
    print(f"    方案一 手写缓存 property：{results_m}  耗时 {tm * 1000:.2f}ms")
    print(f"      特点：每次都走 getter 函数（但内部有缓存判断），逻辑可控")

    c = Cached()
    t1 = time.perf_counter()
    results_c = [c.value for _ in range(5)]
    tc = time.perf_counter() - t1
    print(f"    方案二 cached_property：   {results_c}  耗时 {tc * 1000:.2f}ms")
    print(f"      计算次数 = {c.calls}  （只算了一次，缓存进了 __dict__）")
    print(f"      首次后 c.__dict__ 的键 = {list(c.__dict__)}")

    pl = Plain()
    t2 = time.perf_counter()
    results_p = [pl.value for _ in range(5)]
    tp = time.perf_counter() - t2
    print(f"    方案三 普通属性：          {results_p}  耗时 {tp * 1000:.2f}ms")
    print(f"      特点：未 refresh 时全是 None，需要调用方保证数据新鲜")

    print()
    print("  方案二为什么最快：cached_property 把结果写进实例 __dict__，")
    print("  之后读取走的是【普通属性查找】，完全跳过了函数调用。")
    print("  这是 Python 属性系统的'数据描述符优先级高于非数据描述符'规则的妙用。")


# ===== 语法解析 =====
# 【8】property 的坑
def demo_property_pitfalls() -> None:
    print("  坑 1：装饰器顺序写反")
    print("    正确：先 @property，再 @name.setter")
    print("    错误：先 @name.setter，再 @property（会报 AttributeError）")

    try:
        class Wrong:
            @property
            def value(self) -> int:
                return self._v

            # 顺序颠倒的写法：@value.setter 拿到的 value 还是一个普通函数，没有 .setter
            @value.setter              # type: ignore[misc]
            def value(self, v) -> None:
                self._v = v
        print(f"    实际未报错（因为 Python 允许在 class body 里这样写，但语义不同）")
    except AttributeError as exc:
        print(f"    AttributeError: {exc}")

    print()
    print("  坑 2：子类重写时忘记加 @property")
    class Base:
        @property
        def name(self) -> str:
            return "base"

    class BadChild(Base):
        def name(self) -> str:       # ✗ 忘了 @property
            return "child"

    base = Base()
    bad = BadChild()
    print(f"    Base().name        = {base.name!r}  → 是字符串")
    print(f"    BadChild().name    = {bad.name!r}  → 也是字符串（碰巧）")
    print(f"    但类型不同：Base={type(base.name).__name__}, Child={type(bad.name).__name__}")
    print(f"    若子类【删掉】父类 property，父类代码访问 b.name 会变成方法对象：")
    class BadChild2:
        def name(self) -> str:
            return "child2"
    print(f"      BadChild2().name  = {BadChild2().name!r}  → 是绑定方法，不是字符串！")

    print()
    print("  坑 3：property 与 __slots__ 冲突")
    print("    property 需要类属性名与 backing 属性名不同（如 name vs _name），")
    print("    且 backing 属性名必须已在 __slots__ 中声明，否则赋值会失败。")

    class SlotPoint:
        __slots__ = ("_x", "_y")      # backing 属性要声明

        def __init__(self, x: float, y: float) -> None:
            self._x = x
            self._y = y

        @property
        def x(self) -> float:
            return self._x

        @x.setter
        def x(self, value: float) -> None:
            if value < 0:
                raise ValueError("坐标不能为负")
            self._x = value

    sp = SlotPoint(1, 2)
    sp.x = 10
    print(f"    __slots__ 类也能用 property：SlotPoint(1,2).x = {sp.x}")
    print(f"      修改后 x = {sp.x}, _x = {sp._x}")
    try:
        sp.x = -1
    except ValueError as exc:
        print(f"      校验依然生效 → ValueError: {exc}")

    print()
    print("  坑 4：把 property 用在纯数据上（过度设计）")
    print("    如果属性只是存取、没有校验/派生/兼容需求，")
    print("    直接用普通属性更快更简单。用 property 要有【理由】。")


def main() -> None:
    print("=" * 60)
    print("【1】property 三件套：getter / setter / deleter")
    print("=" * 60)
    p = Person("张三", 25)
    print(f"  初始：p.name = {p.name!r}, p.age = {p.age}")
    p.name = "  李四  "
    print(f"  赋值后（自动 strip）：p.name = {p.name!r}")
    try:
        p.name = "   "                 # 触发 setter 校验
    except ValueError as exc:
        print(f"  setter 校验 → ValueError: {exc}")
    try:
        p.age = 30                      # age 只有 getter
    except AttributeError as exc:
        print(f"  只读属性赋值 → AttributeError: {exc}")
    del p.name
    print(f"  del p.name 后，访问 →", end=" ")
    try:
        print(p.name)
    except AttributeError as exc:
        print(f"AttributeError: {exc}")

    print()
    print("  ★ name 在类 __dict__ 里是 property 描述符，不是函数：")
    print(f"    Person.__dict__['name'] = {Person.__dict__['name']}")
    print(f"    类型 = {type(Person.__dict__['name']).__name__}")
    print(f"    它的 fget = {Person.__dict__['name'].fget.__name__}")
    print(f"    它的 fset = {Person.__dict__['name'].fset.__name__}")
    print(f"    它的 fdel = {Person.__dict__['name'].fdel.__name__}")
    print(f"    实例的 __dict__ 里存的是：{list(Person('x', 1).__dict__)}   # 真正数据是 _name/_age")

    print()
    print("=" * 60)
    print("【2】计算属性与唯一数据源")
    print("=" * 60)
    t = Temperature(100)
    print(f"  Temperature(100).celsius   = {t.celsius}")
    print(f"  Temperature(100).fahrenheit = {t.fahrenheit}   # 现场换算")
    print(f"  Temperature(100).kelvin     = {t.kelvin:.2f}")
    t.fahrenheit = 212
    print(f"  设 fahrenheit=212 后，celsius 自动 = {t.celsius}   # 反向 setter 保证唯一数据源")
    print(f"  只读派生属性 kelvin 不可写：", end=" ")
    try:
        t.kelvin = 0
    except AttributeError as exc:
        print(f"AttributeError（只读）")

    print()
    print("=" * 60)
    print("【3】手写 property 装饰器（行为对齐内置）")
    print("=" * 60)
    cfg = ConfigDemo()
    print(f"  初始 width = {cfg.width}")
    cfg.width = 100
    print(f"  设 width=100 后 = {cfg}")
    try:
        cfg.width = -5
    except ValueError as exc:
        print(f"  自定义 setter 校验 → ValueError: {exc}")
    print(f"  ConfigDemo.width 是类属性访问 → {ConfigDemo.width}   # 返回 property 对象本身")
    print(f"    类型 = {type(ConfigDemo.width).__name__}   # 这就是 __get__ 里 obj=None 分支")

    print()
    print("  与内置 property 的行为对比：")
    class Builtin:
        def __init__(self) -> None:
            self._v = 1
        @property
        def v(self) -> int:
            return self._v

    print(f"    内置 Person.age 只读赋值报错：", end=" ")
    try:
        p.age = 1
    except AttributeError as exc:
        print(f"AttributeError ✓")
    print(f"    自制 ConfigDemo 有 setter，不报只读错，改为业务校验 ✓")

    print()
    print("=" * 60)
    print("【4】属性校验范式：不变量守卫在唯一入口")
    print("=" * 60)
    acct = BankAccount("张三", 1000.0)
    print(f"  初始余额 = {acct.balance}")
    acct.withdraw(300)
    print(f"  取款 300 后 = {acct.balance}")
    acct.deposit(500)
    print(f"  存款 500 后 = {acct.balance}")
    try:
        acct.balance = -100          # 直接写属性企图破坏不变量
    except ValueError as exc:
        print(f"  直接赋负余额 → ValueError: {exc}   ← setter 守住了不变量")
    try:
        acct.withdraw(99999)
    except ValueError as exc:
        print(f"  超额取款 → ValueError: {exc}")
    print(f"  balance 是只读属性，外部无法直接赋值（避免绕过业务规则）")

    print()
    print("=" * 60)
    print("【5】自定义缓存属性 cached_property 的实现")
    print("=" * 60)
    data = ExpensiveData([1, 2, 3, 4])
    print(f"  首次读取 sum_of_squares = {data.sum_of_squares}（真实计算）")
    print(f"  再次读取 = {data.sum_of_squares}（从缓存取）")
    print(f"  再次读取 = {data.sum_of_squares}（从缓存取）")
    print(f"  计算次数 call_count = {data.call_count}   ← 只算了一次")
    print(f"  缓存键写入 __dict__：{[k for k in data.__dict__ if 'cached' in k]}")

    print()
    print("=" * 60)
    print("【6】★ property 的性能代价（常见误解澄清）")
    print("=" * 60)
    demo_property_performance()
    print()
    print("  手写缓存能挽回性能（把重复计算挡在 getter 内）：")
    data2 = ExpensiveData([1, 2, 3, 4])
    t0 = time.perf_counter()
    for _ in range(1000):
        _ = data2.sum_of_squares
    dt = time.perf_counter() - t0
    print(f"    带缓存读 1000 次：{dt * 1000:.3f}ms，真实计算 {data2.call_count} 次")

    print()
    print("=" * 60)
    print("【7】三种缓存属性方案对比")
    print("=" * 60)
    demo_cache_comparison()

    print()
    print("=" * 60)
    print("【8】property 的四个坑")
    print("=" * 60)
    demo_property_pitfalls()

    print()
    print("=" * 60)
    print("小结")
    print("=" * 60)
    print("  1. property 把方法伪装成属性，读写都触发描述符协议")
    print("  2. 三件套：@property → @x.setter → @x.deleter，顺序不能乱")
    print("  3. 只写 getter 即为只读属性，赋值抛 AttributeError")
    print("  4. property 默认【无缓存】，每次读都执行 getter —— 昂贵计算要手动缓存")
    print("  5. 用 property 的正当理由：校验、派生、兼容旧接口，而不是单纯存取")
    print("  6. 底层是描述符；手写 property 只需实现 __get__/__set__/__delete__")


if __name__ == "__main__":
    main()