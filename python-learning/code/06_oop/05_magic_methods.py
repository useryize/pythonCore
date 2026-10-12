"""
================================================================================
  05_magic_methods.py  ——  魔术方法（特殊方法 / 双下划线方法）
================================================================================

【演示的语法点】
 1. ★ 核心机制：特殊方法由【Python 隐式调用】，普通方法由【用户显式调用】
 2. ★ 完整实现 Vector 类，覆盖全部常用魔术方法：
       __add__ __radd__ __sub__ __mul__ __rmul__ __truediv__ __floordiv__
       __mod__ __pow__ __neg__ __abs__
       __eq__ __ne__ __lt__ __le__ __gt__ __ge__
       __len__ __bool__ __contains__
       __getitem__ __setitem__ __delitem__ __iter__
       __repr__ __str__
       __call__ __hash__
       __enter__ __exit__
 3. ★ 隐式 vs 显式调用的时机差异（运算符语法糖 → dunder）
 4. 运算符反射机制：左操作数不支持时回退到右操作数的 __r*__
 5. ★ __eq__ 与 __hash__ 的绑定契约（定义 __eq__ 必须同时定义 __hash__）
 6. ★ 上下文管理器 __enter__/__exit__ 与 with 语句
 7. 模拟内置类型：让自定义类像 list 一样支持 len/迭代/索引/成员判断
 8. 运算符优先级表与对应的 dunder 方法映射
 9. __slots__ 与魔术方法的配合（性能与内存）
10. 常见错误：__str__ vs __repr__、__eq__ 与身份、不可变对象的 __hash__

【预期输出摘要】
 - "隐式vs显式" 小节证明 v + v 实际调用了 v.__add__(v)，且两种写法结果相同
 - "反射" 小节打印 __radd__ 被触发的证据（int + Vector）
 - "上下文管理器" 小节打印 with 语句的 __enter__/__exit__ 调用顺序与异常传递
 - "hash契约" 小节打印定义 __eq__ 后 __hash__ 变为 None 的实际后果
================================================================================

"""

from __future__ import annotations

import timeit
from typing import Any, Iterator, List, Optional, Tuple


# ==============================================================================
# 【第一部分】核心机制：隐式调用 vs 显式调用
# ==============================================================================
# ===== 语法解析 =====
# 魔术方法（特殊方法 / dunder 方法）：名字前后各有两个下划线，如 __add__。
#
# ★ 关键区别（本章最重要的知识点）：
#   普通方法   —— 由【用户显式调用】：obj.method()
#                 例：obj.show()      → 类必须显式提供 show 方法
#   魔术方法   —— 由【Python 隐式调用】：用户用语法糖，解释器翻译成方法调用
#                 例：a + b          → 解释器翻译为 a.__add__(b)
#
# 执行顺序（以 a + b 为例）：
#   1. 检查 a 的类型是否有 __add__
#   2. 有 → 调用 a.__add__(b)
#   3. 返回 NotImplemented 或 a 类型不支持 → 尝试 b.__radd__(a)（右操作数反射）
#   4. 都不支持 → 抛 TypeError: unsupported operand type(s)
#
# 设计意图：让用户用「自然的语法」表达意图（+ 表示加），而不是调用
#          冗长的方法名（add_up）。语法糖背后是方法，这就是 Python 的"一致性"。
def explain_implicit_vs_explicit() -> None:
    print("=" * 60)
    print("【1】★ 隐式调用 vs 显式调用（核心机制）")
    print("=" * 60)

    class Simple:
        def hello(self) -> str:
            return "普通方法：需要 obj.hello() 显式调用"

        def __str__(self) -> str:
            return "魔术方法：print(obj) 时由 Python 自动调用"

    s = Simple()

    print()
    print("  ── 普通方法：必须【显式】写方法名 ──")
    print(f"    s.hello()          → {s.hello()}")
    print("    ★ 如果不写 s.hello()，直接用 s 则不会有任何输出 —— Python 不会自动调用它。")

    print()
    print("  ── 魔术方法：由【语法糖】隐式触发 ──")
    print(f"    print(s)           → {s}")
    print(f"    str(s)             → {str(s)}")
    print(f"    f'{s}'             → {f'{s}'}")
    print("    ★ 上面三种写法全部触发同一个 __str__，你从没写过 s.__str__()。")

    print()
    print("  ── 运算符是如何翻译成方法调用的 ──")
    print("  下面是「隐式调用」的等价翻译：")

    class Calc:
        def __add__(self, other: Any) -> str:
            return f"__add__ 被调用，other={other}"

    c1, c2 = Calc(), Calc()
    print(f"    写法A：c1 + c2        → {c1 + c2}")
    print(f"    写法B：c1.__add__(c2)  → {c1.__add__(c2)}")
    print("    ★ 两个结果【完全相同】—— 证明 `+` 就是 __add__ 的语法糖。")

    print()
    print("  ── 各类运算符的语法糖翻译表 ──")
    print("    a + b   →  a.__add__(b)        a - b    →  a.__sub__(b)")
    print("    a * b   →  a.__mul__(b)        a / b    →  a.__truediv__(b)")
    print("    a // b  →  a.__floordiv__(b)   a % b    →  a.__mod__(b)")
    print("    a ** b  →  a.__pow__(b)        -a       →  a.__neg__()")
    print("    abs(a)  →  a.__abs__()         a == b   →  a.__eq__(b)")
    print("    len(a)  →  a.__len__()         str(a)   →  a.__str__()")
    print("    repr(a) →  a.__repr__()        a in b   →  b.__contains__(a)")
    print("    a[i]    →  a.__getitem__(i)    a()      →  a.__call__()")
    print("    iter(a) →  a.__iter__()        next(a)  →  a.__next__()")
    print("    a > b   →  a.__gt__(b)         hash(a)  →  a.__hash__()")
    print("    with a  →  a.__enter__() / a.__exit__()")


# ==============================================================================
# 【第二部分】完整 Vector 类 —— 覆盖全部常用魔术方法
# ==============================================================================
# ===== 语法解析 =====
# 用二维向量演示所有常用魔术方法。
# 设计要点：
#   1. 运算类 (__add__ 等) 必须返回【新对象】，不修改自身
#   2. __eq__ 与 __hash__ 必须【同时定义】（哈希契约）
#   3. 容器协议要成套实现：__len__ + __getitem__，或 __len__ + __iter__
class Vector:
    """二维向量：演示全部常用魔术方法。

    不可变对象（不修改自身），所有运算返回新 Vector。
    """

    # ---------- 构造与内部状态 ----------
    def __init__(self, x: float = 0, y: float = 0) -> None:
        self.x = x
        self.y = y

    # __slots__：声明固定的属性集合，禁止动态添加属性
    # ★ 作用：① 省内存（不创建 __dict__）② 加快属性访问 ③ 提前暴露拼写错误
    # ★ 注意：加了 __slots__ 后不能再给实例加新属性，也不支持弱引用（除非加 __weakref__）
    # __slots__ = ("x", "y")

    # ========================================================================
    # 【运算类魔术方法】 —— 对应 + - * / // % ** 等运算符
    # ========================================================================

    def __add__(self, other: Any) -> "Vector":
        """对应 `self + other`：向量 + 向量，或 向量 + 标量。

        ★ 必须同时支持 Vector 和数字，否则 `v1 + 10` 会失败：
          运算 `a + b` 的查找顺序是 —— 先试 a.__add__(b)，若返回 NotImplemented
          再试 b.__radd__(a)。对于 `v1 + 10`，右操作数是 int，
          解释器找的是 int.__radd__，而不是本类的 __radd__。
          所以"向量在左边 + 数字"这种写法必须由【__add__】自己处理数字。
        ★ 什么时候 __radd__ 才生效？当【本类在右边】时，如 `10 + v1`。
        """
        if isinstance(other, Vector):
            return Vector(self.x + other.x, self.y + other.y)
        if isinstance(other, (int, float)):
            # 向量 + 标量：每个分量都加
            return Vector(self.x + other, self.y + other)
        # 其它类型（如字符串）→ 返回 NotImplemented，让解释器尝试右侧的 __radd__，
        # 若两侧都不支持，最终由 Python 抛出清晰的 TypeError
        return NotImplemented

    def __radd__(self, other: Any) -> "Vector":
        """对应 `other + self`：右操作数反射（当左边不支持 + 时调用）。

        ★ 典型场景：int + Vector，int 没有 __add__ 认识 Vector，
          于是解释器转而调用 Vector.__radd__(int)。
        ★ 因为数字与向量加法无意义，这里也做加法模拟（把 int 加到每个分量）。
        """
        if isinstance(other, (int, float)):
            return Vector(self.x + other, self.y + other)
        return NotImplemented

    def __sub__(self, other: Any) -> "Vector":
        """对应 `self - other`：向量减法。"""
        if not isinstance(other, Vector):
            return NotImplemented
        return Vector(self.x - other.x, self.y - other.y)

    def __rsub__(self, other: Any) -> "Vector":
        """对应 `other - self`：右操作数减法（如 10 - Vector(3,4)）。"""
        if isinstance(other, (int, float)):
            return Vector(other - self.x, other - self.y)
        return NotImplemented

    def __mul__(self, other: Any) -> "Vector":
        """对应 `self * other`：向量 × 标量（数乘）。"""
        if isinstance(other, (int, float)):
            return Vector(self.x * other, self.y * other)
        if isinstance(other, Vector):
            # 向量 × 向量 = 点积（标量），返回一个数字（标量）
            return self.x * other.x + self.y * other.y    # type: ignore[return-value]
        return NotImplemented

    def __rmul__(self, other: Any) -> "Vector":
        """对应 `other * self`：支持 2 * Vector（乘法交换律）。"""
        if isinstance(other, (int, float)):
            return Vector(self.x * other, self.y * other)
        return NotImplemented

    def __truediv__(self, scalar: float) -> "Vector":
        """对应 `self / scalar`：真除法（/）。注意名字是 truediv 不是 div。"""
        if scalar == 0:
            raise ZeroDivisionError("向量不能除以 0")
        return Vector(self.x / scalar, self.y / scalar)

    def __floordiv__(self, scalar: float) -> "Vector":
        """对应 `self // scalar`：向下取整除法。"""
        if scalar == 0:
            raise ZeroDivisionError("向量不能除以 0")
        return Vector(self.x // scalar, self.y // scalar)

    def __mod__(self, scalar: float) -> "Vector":
        """对应 `self % scalar`：取模（取余）。"""
        if scalar == 0:
            raise ZeroDivisionError("向量不能对 0 取模")
        return Vector(self.x % scalar, self.y % scalar)

    def __pow__(self, power: int) -> "Vector":
        """对应 `self ** power`：分量幂运算。"""
        return Vector(self.x ** power, self.y ** power)

    def __neg__(self) -> "Vector":
        """对应 `-self`：取负（每个分量取反）。一元运算符只需一个参数。"""
        return Vector(-self.x, -self.y)

    def __pos__(self) -> "Vector":
        """对应 `+self`：取正（返回新对象，保持"运算不修改自身"的约定）。"""
        return Vector(+self.x, +self.y)     # +x 是取正

    def __abs__(self) -> float:
        """对应 `abs(self)`：向量的模（长度）。"""
        return (self.x ** 2 + self.y ** 2) ** 0.5

    # ========================================================================
    # 【比较类魔术方法】 —— 对应 == != < <= > >=
    # ========================================================================

    def __eq__(self, other: Any) -> bool:
        """对应 `self == other`：相等比较。

        ★ 重要：定义了 __eq__ 后，Python 会自动把 __hash__ 设为 None！
          这意味着 Vector 实例【不可哈希】，无法放进 set 或作 dict 的键。
          必须同时定义 __hash__（见下方）来恢复可哈希性。
        ★ 组件几乎相等（容差比较）。
        """
        if not isinstance(other, Vector):
            return NotImplemented
        return abs(self.x - other.x) < 1e-9 and abs(self.y - other.y) < 1e-9

    def __ne__(self, other: Any) -> bool:
        """对应 `self != other`：不等（3.0+ 可由 __eq__ 自动推导，但显式写更清晰）。"""
        result = self.__eq__(other)
        if result is NotImplemented:
            return result
        return not result

    def __lt__(self, other: Any) -> bool:
        """对应 `self < other`：小于（按模长比较）。"""
        if not isinstance(other, Vector):
            return NotImplemented
        return abs(self) < abs(other)

    def __le__(self, other: Any) -> bool:
        """对应 `self <= other`：小于等于。"""
        if not isinstance(other, Vector):
            return NotImplemented
        return abs(self) <= abs(other)

    def __gt__(self, other: Any) -> bool:
        """对应 `self > other`：大于。"""
        if not isinstance(other, Vector):
            return NotImplemented
        return abs(self) > abs(other)

    def __ge__(self, other: Any) -> bool:
        """对应 `self >= other`：大于等于。"""
        if not isinstance(other, Vector):
            return NotImplemented
        return abs(self) >= abs(other)

    def __hash__(self) -> int:
        """对应 `hash(self)`：计算哈希值。

        ★ 哈希契约（必须遵守）：
          ① a == b  ⟹  hash(a) == hash(b)（相等的对象哈希值必须相同）
          ② 哈希值在对象【生命周期内不可变】（所以可变对象不适合作 dict 键）
        ★ 因为定义了 __eq__，Python 默认会把 __hash__ 置为 None；
          必须像这样显式重定义，才能让 Vector 可作 set 元素 / dict 键。
        ★ 用不可变分量（x, y）的哈希来计算，保证「相等即同哈希」。
        """
        return hash((self.x, self.y))

    # ========================================================================
    # 【容器协议魔术方法】 —— 对应 len / in / [] / for
    # ========================================================================

    def __len__(self) -> int:
        """对应 `len(self)`：返回对象"长度"。

        ★ 对 Vector 来说，长度就是分量个数（2）。
        ★ __len__ 还会影响真值判断：len(obj)==0 时 bool(obj) 为 False。
        """
        return 2

    def __bool__(self) -> bool:
        """对应 `bool(self)`：自定义真值判断（优先于 __len__）。

        ★ 设计意图：数学上 (0,0) 是【零向量】，但仍应视为"存在"，
          所以这里让零向量也为 True，避免 `if vector:` 意外跳过。
        """
        # 即使是零向量也返回 True（只要对象存在就是真的）
        return True

    def __contains__(self, item: Any) -> bool:
        """对应 `item in self`：成员判断。

        ★ 因为定义了 __contains__，`3 in vector` 会调用它，判断分量中是否含 3。
        ★ 注意：定义了 __contains__ 会禁用默认的迭代查找（更快）。
        """
        return item in (self.x, self.y)

    def __getitem__(self, key: Any) -> Any:
        """对应 `self[key]`：下标/切片访问。

        ★ 这是让类支持 `v[0]`、`v[0:1]`、甚至 `for x in v` 的关键。
        ★ 支持 int 索引（返回单个分量）和 slice（返回新 Vector）。
        ★ ★ 重要：只实现 __getitem__ 而不实现 __len__/__iter__，类就能被 for 循环遍历！
        """
        if isinstance(key, slice):
            # 切片：按索引取出分量，返回新 Vector
            values = (self.x, self.y)[key]
            if isinstance(values, tuple):
                return Vector(*values)
            return Vector(values, values)  # 只有一个分量
        if key == 0 or key == -2:
            return self.x
        if key == 1 or key == -1:
            return self.y
        raise IndexError(f"向量索引越界: {key}（只有 0 和 1）")

    def __setitem__(self, key: Any, value: float) -> None:
        """对应 `self[key] = value`：按下标赋值（原地修改）。

        ★ 与运算方法不同，__setitem__ 就是原地修改（因为它对应赋值语义）。
        ★ 这让 Vector 从"不可变"变成"可变"，此时 __hash__ 的契约就有风险了。
        """
        if key == 0 or key == -2:
            self.x = value
        elif key == 1 or key == -1:
            self.y = value
        else:
            raise IndexError(f"向量索引越界: {key}")

    def __delitem__(self, key: Any) -> None:
        """对应 `del self[key]`：按下标删除（置 0 或抛异常）。

        ★ 我们的 Vector 固定两个分量，不支持真删除，这里演示抛异常的模式。
        """
        raise TypeError("Vector 不支持删除分量")

    def __iter__(self) -> Iterator[float]:
        """对应 `iter(self)`：返回迭代器，让 `for x in vector` 工作。

        ★ 定义 __iter__ 后，list(vector)、tuple(vector)、for 都能用。
        ★ __getitem__ + __len__ 也能实现迭代，但 __iter__ 更高效、更明确。
        ★ 配合 yield 语法糖：函数体变成生成器，返回迭代器。
        """
        yield self.x
        yield self.y

    # ========================================================================
    # 【表示类魔术方法】 —— 对应 str() / repr() / print()
    # ========================================================================

    def __repr__(self) -> str:
        """对应 `repr(self)`：开发者可读的表示（"如何在代码里重建这个对象"）。

        ★ 约定：应该返回一个【能被 eval 重新构造出等价对象】的字符串。
        ★ 用途：调试时打印、异常回溯、容器嵌套显示（[Vector(...), ...]）。
        ★ eval(repr(v)) 应该能还原出 v —— 这是 repr 的黄金准则。
        """
        return f"Vector({self.x}, {self.y})"

    def __str__(self) -> str:
        """对应 `str(self)` / `print(v)`：用户可读的表示（"给人看的友好格式"）。

        ★ 约定：给人看的，可以随意设计（Unicode 符号、格式化等）。
        ★ 区别：
            print(v)        → 用 __str__（缺失时回退 __repr__）
            repr(v)         → 用 __repr__
            在列表中 [v]    → 用 __repr__（容器打印内部元素时用 repr）
        """
        return f"<{self.x:g}, {self.y:g}>"

    # ========================================================================
    # 【可调用类魔术方法 __call__】
    # ========================================================================

    def __call__(self, scalar: float) -> "Vector":
        """对应 `v(...)`：让【实例本身】可被调用。

        ★ 这是「函数式对象」的关键：定义了 __call__ 的类，其实例就是可调用的。
        ★ 应用场景：
            - 函数装饰器（见 07_design_patterns）
            - 策略模式的实现（把策略做成可调用对象）
            - 代替"只有函数、不需要保存状态"的简单闭包
        ★ 原理：type(obj).__call__(obj, ...) —— 调用实例时找 __call__。
        """
        return Vector(self.x * scalar, self.y * scalar)   # 相当于调用向量缩放

    # ========================================================================
    # 【上下文管理器魔术方法 __enter__ / __exit__】
    # ========================================================================

    def __enter__(self) -> "Vector":
        """对应 `with v:` 进入时调用：返回"资源对象"。

        ★ with 语句的执行流程：
            1. 调用 __enter__()，其返回值【绑定到 as 后的名字】
            2. 执行 with 代码块
            3. 无论块内是否抛异常，都调用 __exit__()
        ★ 返回 self（向量对象本身）作为资源。
        """
        print("    [上下文] __enter__ 被调用 —— 资源已获取")
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> bool:
        """对应 `with` 块结束时调用：清理资源。

        ★ 三个参数（由 Python 自动传入，表示块内的异常情况）：
            exc_type —— 异常类型（没有异常时为 None）
            exc_val  —— 异常对象
            exc_tb   —— 异常回溯
        ★ 返回值语义（★容易搞错）：
            返回 False（默认）→ 异常【继续向外传播】给调用者
            返回 True          → 异常被【吞掉】（抑制传播），视为已处理
        ★ 这里返回 False，保证异常正常传播（我们只是演示资源管理）。
        """
        if exc_type is not None:
            print(f"    [上下文] __exit__ 被调用（块内发生异常 {exc_type.__name__}）→ 继续传播")
        else:
            print("    [上下文] __exit__ 被调用（正常结束）→ 资源已释放")
        return False    # ★ 返回 False：不让异常被吞掉


# ==============================================================================
# 【第三部分】演示 Vector 的各组魔术方法
# ==============================================================================
def demo_vector_operators() -> None:
    print()
    print("=" * 60)
    print("【2】Vector 运算类魔术方法演示")
    print("=" * 60)

    v1 = Vector(3, 4)
    v2 = Vector(1, 2)

    print()
    print(f"  v1 = {v1}    v2 = {v2}")
    print(f"  （print 用 __str__ → <3, 4>；repr 用 __repr__ → Vector(3, 4)）")

    print()
    print("  ── 加减法 ──")
    print(f"    v1 + v2      = {v1 + v2}      ← __add__")
    print(f"    v1 - v2      = {v1 - v2}      ← __sub__")
    print(f"    -v1          = {-v1}      ← __neg__")
    print(f"    +v1          = {+v1}      ← __pos__")
    print(f"    ★ 注意：v1 本身没变，仍是 {v1}  （运算返回新对象）")

    print()
    print("  ── ★ 反射运算（__radd__ / __rsub__） ──")
    print(f"    v1 + 10       = {v1 + 10}      ← __add__（向量在左，__add__ 处理数字）")
    print(f"    10 + v1       = {10 + v1}      ← __radd__（向量在右，才走反射）")
    print(f"    10 - v1       = {10 - v1}      ← __rsub__")
    print("    ★ 反射机制：a + b 先试 a.__add__(b)，返回 NotImplemented 再试 b.__radd__(a)。")
    print("      注意 __radd__ 只在【本类位于右操作数】时才被查找，")
    print("      所以 v1 + 10 必须由 __add__ 自己处理数字，不能指望 __radd__。")

    print()
    print("  ── 乘法（数乘与点积） ──")
    print(f"    v1 * 2        = {v1 * 2}      ← __mul__（数乘）")
    print(f"    2 * v1        = {2 * v1}      ← __rmul__（反射数乘）")
    print(f"    v1 * v2       = {v1 * v2}      ← __mul__（点积=标量）")

    print()
    print("  ── 除法 / 取模 / 幂 ──")
    print(f"    v1 / 2        = {v1 / 2}      ← __truediv__")
    print(f"    v1 // 2       = {v1 // 2}      ← __floordiv__")
    print(f"    v1 % 2        = {v1 % 2}      ← __mod__")
    print(f"    v1 ** 2       = {v1 ** 2}      ← __pow__")

    print()
    print("  ── abs（模长） ──")
    print(f"    abs(v1)       = {abs(v1)}      ← __abs__（经典 3-4-5 三角形）")

    print()
    print("  ── 与不支持的类型运算：返回 NotImplemented → TypeError ──")
    print("    ", end="")
    try:
        v1 + "字符串"
    except TypeError as exc:
        print(f"v1 + '字符串' → TypeError: {exc}")
    print("    ★ 因为 __add__ 返回 NotImplemented，解释器才会去找 '字符串'.__radd__，")
    print("      两侧都不支持时给出【清晰的】TypeError。")
    print("      如果在 __add__ 里直接抛异常，错误信息会掩盖 Python 的运算符协议。")


def demo_vector_comparison() -> None:
    print()
    print("=" * 60)
    print("【3】Vector 比较类魔术方法 + 哈希契约")
    print("=" * 60)

    v1 = Vector(3, 4)
    v2 = Vector(3, 4)                        # 分量相同
    v3 = Vector(5, 6)                        # 模长不同

    print()
    print("  ── 相等/不等（按分量，有容差） ──")
    print(f"    v1 == v2     = {v1 == v2}     ← __eq__（3,4==3,4 且容差内）")
    print(f"    v1 == v3     = {v1 == v3}     ← __eq__（3,4 != 5,6）")
    print(f"    v1 != v3     = {v1 != v3}     ← __ne__")
    print(f"    v1 == 'str'  = {v1 == 'str'}    ← 类型不符返回 NotImplemented → False")

    print()
    print("  ── 大小比较（按模长） ──")
    print(f"    abs(v1)={abs(v1):.1f}  abs(v3)={abs(v3):.1f}")
    print(f"    v1 < v3      = {v1 < v3}     ← __lt__")
    print(f"    v1 <= v3     = {v1 <= v3}     ← __le__")
    print(f"    v1 > v3      = {v1 > v3}     ← __gt__")
    print(f"    v1 >= v3     = {v1 >= v3}     ← __ge__")

    print()
    print("  ── ★ 哈希契约：定义 __eq__ 必须同时定义 __hash__ ──")
    print("    原理：Python 在检测到类定义了 __eq__ 但没定义 __hash__ 时，")
    print("          会自动把 __hash__ 设为 None，导致实例【不可哈希】。")
    print()
    print(f"    hash(v1)     = {hash(v1)}   ← 我们显式定义了 __hash__，所以可哈希")
    print(f"    v1 作 set 元素：{ {v1, v2, v3} }   （v1 和 v2 相等 → set 自动去重成 2 个）")
    print(f"    v1 作 dict 键：{ {v1: '坐标A'} }")
    print()
    print("    ★ 契约验证：相等的对象哈希必相等")
    print(f"      hash(v1) == hash(v2) → {hash(v1) == hash(v2)}   （因为 v1 == v2）")

    print()
    print("  ── 反例：如果【不】定义 __hash__ 会怎样 ──")
    print("  （下面这个类的 __hash__ 会被 Python 自动置 None）")

    class BadHash:
        def __eq__(self, other: Any) -> bool:
            return isinstance(other, BadHash)

    print(f"    BadHash.__hash__ = {BadHash.__hash__}   ← 被置为 None！")
    try:
        hash(BadHash())
    except TypeError as exc:
        print(f"    hash(BadHash()) → TypeError: {exc}")
    print("    ★ 所以自定义 __eq__ 后，必须记得补上 __hash__，否则对象不能进 set/dict。")


def demo_vector_container() -> None:
    print()
    print("=" * 60)
    print("【4】Vector 容器协议：len / in / [] / 迭代")
    print("=" * 60)

    v = Vector(10, 20)

    print()
    print("  ── len 与 bool ──")
    print(f"    len(v)        = {len(v)}         ← __len__（分量个数）")
    print(f"    bool(v)       = {bool(v)}        ← __bool__（自定义，永远 True）")
    zero = Vector(0, 0)
    print(f"    bool(Vector(0,0)) = {bool(zero)}      ← 即使是零向量也为 True（数学上仍存在）")

    print()
    print("  ── 成员判断 in ──")
    print(f"    10 in v       = {10 in v}       ← __contains__（x 分量有 10）")
    print(f"    20 in v       = {20 in v}       ← __contains__（y 分量有 20）")
    print(f"    99 in v       = {99 in v}       ← __contains__")

    print()
    print("  ── 下标访问 [] ──")
    print(f"    v[0]          = {v[0]}          ← __getitem__（x 分量）")
    print(f"    v[1]          = {v[1]}          ← __getitem__（y 分量）")
    print(f"    v[-1]         = {v[-1]}         ← __getitem__（负索引=y）")
    print(f"    v[0:2]        = {v[0:2]}        ← __getitem__ 切片，返回新 Vector")

    print()
    print("  ── 下标赋值 [] = ──")
    v2 = Vector(1, 2)
    v2[0] = 100                             # __setitem__
    print(f"    v2[0] = 100 后  v2 = {v2}   ← __setitem__ 原地修改了 x")

    print()
    print("  ── 迭代 for ──")
    total = 0
    for component in v:                     # __iter__
        total += component
        print(f"      分量: {component}")
    print(f"    遍历求和 = {total}   ← for 循环用了 __iter__")
    print(f"    list(v)     = {list(v)}   ← list() 用了迭代协议")
    print(f"    tuple(v)    = {tuple(v)}")
    print(f"    sum(v)      = {sum(v)}   ← sum 通过迭代求和")
    print(f"    max(v)      = {max(v)}   ← max 通过迭代找最大")
    print("    ★ 定义了 __iter__ 后，Vector 能被所有「消费可迭代对象」的内置函数使用。")

    print()
    print("  ── 越界与删除 ──")
    print("    ", end="")
    try:
        v[5]
    except IndexError as exc:
        print(f"v[5] → IndexError: {exc}")
    print("    ", end="")
    try:
        del v[0]
    except TypeError as exc:
        print(f"del v[0] → TypeError: {exc}   ← Vector 不支持删除分量")


def demo_vector_call_and_context() -> None:
    print()
    print("=" * 60)
    print("【5】Vector __call__ 与上下文管理器")
    print("=" * 60)

    v = Vector(3, 4)

    print()
    print("  ── __call__：让实例可被调用 ──")
    print(f"    v(2)          = {v(2)}     ← 像函数一样调用 v 本身")
    print(f"    v(2) 实际是 __call__(2) = {v(2)}")
    print(f"    type(v).__call__(v, 2) = {type(v).__call__(v, 2)}")
    print("    ★ 原理：调用实例时，Python 找 __call__。这是「可调用对象」的基础。")
    print()
    print("    应用：把 Vector 当作「缩放函数」使用")
    scale = v                                # scale 现在是个可调用对象
    print(f"      scale(3) = {scale(3)}   （等价于把向量放大 3 倍）")
    print("      ★ 区别于普通函数：可调用对象可以【保存状态】（这里保存了 x,y）。")

    print()
    print("  ── __enter__ / __exit__：上下文管理器 ──")
    print("    用法：with obj as alias: ... ")
    print()
    print("  【正常进入退出】")
    with v as vec:
        print(f"      with 块内，as 绑定的是 {vec}  （= __enter__ 的返回值）")
        print(f"      块内可访问其方法：{vec + Vector(1, 1)}")
    print("    （离开 with 块，__exit__ 已自动调用）")

    print()
    print("  【块内抛异常：__exit__ 仍被调用，异常继续传播】")
    try:
        with v:
            print("      准备抛异常...")
            raise ValueError("块内主动抛出的异常")
    except ValueError as exc:
        print(f"    ★ 异常成功传播到 except：{exc}  （因为 __exit__ 返回 False）")

    print()
    print("  ── ★ __exit__ 返回 True 会【吞掉】异常 ──")

    class Suppressor:
        """演示 __exit__ 返回 True 抑制异常。"""
        def __enter__(self) -> "Suppressor":
            print("      Suppressor.__enter__")
            return self

        def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> bool:
            if exc_type is not None:
                print(f"      捕获到 {exc_type.__name__}，__exit__ 返回 True → 异常被抑制")
            return True    # ★ 返回 True = 告诉 Python「异常已处理，别再抛了」

    print("  with Suppressor(): 里抛异常，但不会传播出来：")
    with Suppressor():
        raise RuntimeError("这个异常会被吞掉，不会传播")
    print("    ★ 这就是 __exit__ 返回 True 的效果 —— 实现了 try/except 的等价行为。")


# ==============================================================================
# 【第四部分】运算符优先级 与 dunder 映射
# ==============================================================================
def print_operator_table() -> None:
    print()
    print("=" * 60)
    print("【6】运算符优先级表 与 对应魔术方法")
    print("=" * 60)

    print()
    print("  （从高到低，★ 表示常见）")
    print()
    print("  | 运算符 | 魔术方法 | 说明 | 类别 |")
    print("  |--------|----------|------|------|")
    rows = [
        ("**", "__pow__", "幂运算", "算术"),
        ("~", "__invert__", "按位取反", "一元"),
        ("-x / +x", "__neg__ / __pos__", "取负 / 取正", "一元"),
        ("* / // %", "__mul__ __truediv__ __floordiv__ __mod__", "乘除模", "算术"),
        ("+ -", "__add__ __sub__", "加减", "算术"),
        ("<< >>", "__lshift__ __rshift__", "位移", "位运算"),
        ("&", "__and__", "按位与 / 集合交", "位运算"),
        ("^", "__xor__", "按位异或", "位运算"),
        ("|", "__or__", "按位或", "位运算"),
        ("< <= > >=", "__lt__ __le__ __gt__ __ge__", "比较", "比较"),
        ("== !=", "__eq__ __ne__", "相等", "比较"),
        ("in / not in", "__contains__", "成员判断", "容器"),
        ("len()", "__len__", "长度", "容器"),
        ("[] / []=", "__getitem__ __setitem__", "索引 / 赋值", "容器"),
        ("for ... in", "__iter__ / __next__", "迭代", "容器"),
        ("str() / repr()", "__str__ / __repr__", "字符串表示", "表示"),
        ("bool()", "__bool__", "真值", "转换"),
        ("abs()", "__abs__", "绝对值", "转换"),
        ("hash()", "__hash__", "哈希", "转换"),
        ("obj()", "__call__", "调用实例", "可调用"),
        ("with", "__enter__ __exit__", "上下文管理", "上下文"),
        ("a **= b 等", "__iadd__ __isub__ ...", "原地运算符", "原地"),
    ]
    for op, magic, desc, cat in rows:
        print(f"  | {op:<12} | {magic:<34} | {desc:<12} | {cat:<6} |")

    print()
    print("  ★ 原地运算符（__iadd__ 等）：a += b 会先试 __iadd__，")
    print("    失败才回退到 __add__ 并重新绑定。不定义 __iadd__ 时 += 等价于 a = a + b。")

    print()
    print("  ★ 运算符反射的完整查找顺序（以 a + b 为例）：")
    print("    1. type(a).__add__(a, b)")
    print("    2. 返回 NotImplemented → type(b).__radd__(b, a)")
    print("    3. 仍返回 NotImplemented → 抛 TypeError")
    print("    ★ 所以【永远返回 NotImplemented，不要抛异常】，让 Python 有机会试另一侧。")


# ==============================================================================
# 【第五部分】__slots__ 与魔术方法的配合
# ==============================================================================
def demo_slots_and_best_practices() -> None:
    print()
    print("=" * 60)
    print("【7】__slots__ 与魔术方法最佳实践")
    print("=" * 60)

    # 演示 __slots__ 的效果
    class WithDict:
        def __init__(self, x: int) -> None:
            self.x = x

    class WithSlots:
        __slots__ = ("x",)                   # 声明固定属性

        def __init__(self, x: int) -> None:
            self.x = x

    a, b = WithDict(1), WithSlots(1)
    import sys
    print()
    print("  ── __slots__：省内存 + 防拼写错误 ──")
    print(f"    普通类实例大小：{sys.getsizeof(a)} 字节（含 __dict__）")
    print(f"    __slots__ 类实例：{sys.getsizeof(b)} 字节（无 __dict__）")
    print(f"    ★ __slots__ 省掉了实例的 __dict__，大对象场景内存优势明显。")
    print()
    print("    ", end="")
    try:
        b.new_attr = 99                       # __slots__ 不允许动态加属性
    except AttributeError as exc:
        print(f"给 __slots__ 类加新属性 → AttributeError: {exc}")
    print("    ★ 这也顺带防住了属性名拼写错误（__slots__ 是白名单）。")

    print()
    print("  ── 最佳实践清单 ──")
    print("    1. 返回 NotImplemented 而不是抛 TypeError（让反射有机会）")
    print("    2. 定义 __eq__ 时必须同时定义 __hash__")
    print("    3. __str__ 给人看，__repr__ 给开发者（repr 应可被 eval）")
    print("    4. 运算方法返回【新对象】，不要修改 self（除非 __i*__ 或 __setitem__）")
    print("    5. __len__ 返回 ≥ 0 的 int；返回 0 会让 bool(obj) 为 False")
    print("    6. 容器协议要成套：要么 __len__+__getitem__，要么 __iter__")
    print("    7. 不可变对象才定义 __hash__；可变对象不要作 dict 键")
    print("    8. 有了 __iter__ 就别只靠 __getitem__（前者更高效）")


def main() -> None:
    """主函数：按教学顺序演示魔术方法。"""
    explain_implicit_vs_explicit()
    demo_vector_operators()
    demo_vector_comparison()
    demo_vector_container()
    demo_vector_call_and_context()
    print_operator_table()
    demo_slots_and_best_practices()

    print()
    print("=" * 60)
    print("小结")
    print("=" * 60)
    print("  1. ★ 魔术方法由【语法糖隐式触发】，普通方法需【显式调用 obj.method()】")
    print("  2. ★ `a + b` 就是 `a.__add__(b)` 的语法糖，两种写法结果相同")
    print("  3. 运算方法返回 NotImplemented（不抛异常），给右操作数 __r*__ 留机会")
    print("  4. ★ 定义 __eq__ 必须同时定义 __hash__，否则对象不可哈希（不能进 set/dict）")
    print("  5. __len__+__getitem__ 或 __iter__ 让自定义类支持 for/len/[]")
    print("  6. __str__ 给人看（print），__repr__ 给开发者（调试、容器内显示）")
    print("  7. __call__ 让实例成为可调用对象（有状态的函数）")
    print("  8. ★ __exit__ 返回 True 吞掉异常，返回 False 让异常传播")
    print("  9. __setitem__ 原地修改，运算方法返回新对象（不要混用）")
    print(" 10. __slots__ 省内存防拼错，但不允许动态加属性")


if __name__ == "__main__":
    main()