# -*- coding: utf-8 -*-
"""
================================================================================
文件：01_variables_and_types.py
模块：02_basics（基础语法配套）

【本文件演示的语法点列表】
  1. 变量赋值本质 —— 名字绑定（name binding）而非 C 的存储位置
  2. 动态类型 —— 同一个名字可先后绑定不同类型的对象
  3. type() / isinstance() / issubclass() 的区别与选择
  4. id() 与内存地址，以及小整数缓存 / 字符串驻留的"假共享"现象
  5. 可变对象 vs 不可变对象 —— 判定方法与实际后果
  6. 多重赋值的绑定顺序（a = b = value、a, b = b, a 的元组解包）
  7. 常量的"约定式模拟"与 typing.Final / 命名约定
  8. 类型标注的运行时效果 —— 标注不改变行为

【设计意图】
  Python 的变量模型是理解这门语言一切行为的总钥匙。
  "变量是盒子"这个流传甚广的比喻其实是错的 ——
  变量是贴在对象上的便利贴，盒子是对象本身。
  一旦理解"多个名字可以指向同一个对象"，
  可变默认参数、浅拷贝、is 与 == 的区别就全都自然浮现。

【预期输出摘要】
  [1] 动态类型：x 从 int 变 str 再变 list，type() 随之改变
  [2] id() 与驻留：小整数 -5..256 共享对象，字符串字面量驻留
  [3] 可变性与不可变性：三种判定方式对照
  [4] 赋值即绑定：多个名字指向同一对象，修改互相可见
  [5] 多重赋值的求值顺序演示
  [6] 类型标注：运行后 __annotations__ 存在但不产生任何约束
================================================================================
"""

import sys


# ============================================================================
# 语法解析 1：变量、动态类型与内省三函数
# ============================================================================
# 【语法规则】
#   x = 10                普通赋值语句
#   x: int = 10           带类型标注的赋值（Python 3.6+）
#   type(obj)             返回对象的精确类型对象
#   isinstance(obj, cls)  返回对象是否为 cls 或其子类实例
#   issubclass(A, B)      返回 A 是否是 B 的子类（两个都是类型）
# 【关键字作用】
#   isinstance 是内置函数，不是关键字，因此参数顺序固定为 (对象, 类型元组)
# 【执行顺序】
#   赋值语句执行时：先计算右侧表达式 -> 得到一个对象 -> 把名字绑定到该对象。
#   「绑定」这一步发生在当前命名空间（模块级为全局，函数内为局部）。
# 【设计意图】
#   Python 选择动态类型 + 运行时内省，而非编译期类型检查。
#   代价是错误延后到运行时才暴露；收益是同一套容器和运算符
#   （+ - * [] for in）能服务于任意类型，这就是"鸭子类型"能成立的基础。
def demo_dynamic_typing():
    print("[1] 动态类型与类型内省")

    x = 10
    print(f"    x = 10              -> type = {type(x).__name__}, id = {id(x)}")

    # 同一个名字重新绑定到另一个类型的对象，完全合法，无任何警告
    x = "现在我是字符串"
    print(f"    x = '字符串'        -> type = {type(x).__name__}, id = {id(x)}")

    x = [1, 2, 3]
    print(f"    x = [1,2,3]        -> type = {type(x).__name__}, id = {id(x)}")

    # type() 精确匹配；isinstance 支持子类，这是二者最重要的区别
    class Animal:
        pass

    class Dog(Animal):
        pass

    d = Dog()
    print(f"    type(d) is Dog        = {type(d) is Dog}       (精确)")
    print(f"    type(d) is Animal     = {type(d) is Animal}    (精确 -> False)")
    print(f"    isinstance(d, Animal) = {isinstance(d, Animal)}    (含子类 -> True)")

    # isinstance 支持元组，一次判断多个类型，等价于 or 的简写
    print(f"    isinstance(d, (str,int))   = {isinstance(d, (str, int))}")
    print(f"    isinstance(d, (str,Animal)) = {isinstance(d, (str, Animal))}")

    # 类的继承链：判断继承关系用 issubclass，与 isinstance 作用对象不同
    print(f"    issubclass(Dog, Animal) = {issubclass(Dog, Animal)}")
    print(f"    Dog.__mro__ = {[c.__name__ for c in Dog.__mro__]}")
    print("    -> MRO（方法解析顺序）决定 isinstance 沿哪条链找基类")


# ============================================================================
# 语法解析 2：id() 与对象驻留 —— 解释 is 与 == 的分歧根源
# ============================================================================
# 【语法规则】
#   id(obj)          返回对象身份标识（CPython 中即内存地址），进程内唯一
#   ==               比较"值是否相等"，由类型自己定义（__eq__）
#   is               比较"是否同一个对象"，即 id() 是否相同（PyObject_RichCompare 的另一分支）
# 【执行顺序】
#   CPython 缓存了 -5 到 256 的小整数对象，任何计算结果落在这个区间
#   都复用同一对象，因此 a is b 可能为 True 而与"是不是刚算出来的"无关。
#   同理，相同短字符串字面量在同一代码模块内会被 intern（驻留）成一个对象。
# 【设计意图】
#   区分"相等"和"同一"是必要的：
#   - 用 is 判断数值相等在小整数区间恰好成立，但在 1000 就不成立，
#     写出依赖它的代码属于危险行为。
#   - 需要"同一性"时（例如缓存查找、None 检查），is 才是正确且更快的工具。
#   数值比较应一律用 ==，None 判断用 `is None`。
def demo_id_and_interning():
    print("[2] id() 与对象驻留")

    # 小整数缓存区间：CPython 默认缓存 -5 <= n <= 256
    a = 100
    b = 100
    print(f"    a=100, b=100: a is b = {a is b}, id 相同 = {id(a) == id(b)}")
    print("    -> 小整数缓存，解释器为 [-5, 256] 预建对象并复用")

    # 超出缓存区间：编译器会把同一代码块中的整数【常量折叠】成同一个对象，
    # 所以 c is d 仍为 True。但这是编译期优化，与运行期的小整数缓存是两回事。
    c = 1000
    d = 1000
    print(f"    c=1000, d=1000: c is d = {c is d}, c == d = {c == d}")
    print("    -> 同代码块内的字面量被常量折叠为同一对象，故 is 恰为 True")

    # 但绕过常量折叠后就不成立了：这是"不要依赖 is 比较数值"的真实原因
    e = int("1000")  # 运行期构造，不参与常量折叠，得到全新对象
    f = 1000
    # 注意：必须经由变量做 is 比较，直接写 `int("1000") is 1000` 会被编译器
    # 判定为"用 is 比较字面量"并抛出 SyntaxWarning
    print(f"    int('1000') is f = {e is f}，但 e == f = {e == f}")
    print("    -> 运行期构造的值与字面量不是同一对象，is 不可靠，数值比较请一律用 ==")

    # 字符串驻留：同一代码位置重复出现的字面量共享对象
    s1 = "hello"
    s2 = "hello"
    print(f"    两个相同字面量 'hello': s1 is s2 = {s1 is s2} (interning)")
    # 但运行时动态构造的字符串不驻留
    s3 = "".join(["hel", "lo"])
    print(f"    动态拼接 'hello': s3 is s1 = {s3 is s1} (join 不驻留)")
    print(f"    但 s3 == s1 = {s3 == s1} (值比较仍然相等)")

    # None 的判断：唯一应该用 is 的场景
    print(f"    None is None = {None is None}  (None 是单例)")
    print("    -> 判空一律写 `x is None`，不要写 `x == None`")


# ============================================================================
# 语法解析 3：可变 vs 不可变
# ============================================================================
# 【语法规则】
#   可判定方式一：尝试原地修改，看对象是否被就地改变
#   可判定方式二：__hash__ 是否为 None（不可变类型通常可哈希）
# 【执行顺序】
#   对不可变对象执行"修改类"操作（如 lst.append），Python 会创建新对象并重新绑定名字，
#   而不是报错 —— 这个"静默新建"机制是初学者最困惑之处。
# 【设计意图】
#   可变性决定了对象能否被安全共享与跨线程传递。
#   不可变对象天然线程安全、可自由缓存（因为 id 不变、哈希不变），
#   所以 str / tuple / int 被设计为不可变，list / dict / set 被设计为可变。
def demo_mutability():
    print("[3] 可变性与不可变性")

    immutable_examples = [
        ("int", 42),
        ("str", "text"),
        ("tuple", (1, 2)),
        ("frozenset", frozenset({1, 2})),
    ]
    print("    不可变类型（含 __hash__）：")
    for name, obj in immutable_examples:
        # hasattr(__hash__) 为 True 且 __hash__ 不为 None，即为可哈希
        hashable = obj.__hash__ is not None
        print(f"      {name:<10} 可哈希 = {hashable}")

    mutable_examples = [
        ("list", [1, 2]),
        ("dict", {"a": 1}),
        ("set", {1, 2}),
        ("bytearray", bytearray(b"ab")),
    ]
    print("    可变类型（__hash__ 为 None）：")
    for name, obj in mutable_examples:
        # 可变容器的 __hash__ 被显式置为 None，导致 hash(obj) 直接抛 TypeError。
        # 这不是 bug，而是刻意的保护：内容会变的对象不允许作为 dict 键。
        print(f"      {name:<10} 可哈希 = {obj.__hash__ is not None}")

    # 演示不可变对象的"修改"实际发生了什么
    s = "hello"
    print(f"    原始 s = {s!r}, id = {id(s)}")
    # s[0] = 'H' 会直接抛 TypeError，这里用 s = s.upper() 展示"看似修改实为新建"
    s_upper = s.upper()
    print(f"    s.upper() = {s_upper!r}, id = {id(s_upper)}")
    print(f"    原 s 未变 = {s == 'hello'}  (返回的是新对象，不是原地修改)")
    # 字符串拼接同理：CPython 会对超长拼接做原地优化，但对使用者而言语义一致
    s2 = s + " world"
    print(f"    s + ' world' = {s2!r}，s 仍是 {s!r}")

    # 列表则是真正的原地修改
    lst = [1, 2, 3]
    before = id(lst)
    lst.append(4)
    print(f"    list.append 后 id 相同 = {id(lst) == before}, 内容 = {lst}")


# ============================================================================
# 语法解析 4：赋值即绑定 —— 多个名字共享一个对象
# ============================================================================
# 【语法规则】
#   a = b = [1, 2]     链式赋值：先把值算一次，再依次绑定给 a 和 b
#   a, b = 1, 2        元组解包：右侧先被打包成元组，再逐项解包（无实际元组开销）
#   a, b = b, a        交换：右侧先整体求值，再赋给左侧，交换成立
# 【执行顺序】
#   关键：赋值语句的所有右侧表达式【先于】任何绑定动作求值。
#   所以 x, x = 1, 2 的结果是 x == 2，而不是 1 —— 后者覆盖前者。
# 【设计意图】
#   理解"绑定"而非"赋值"是区分 Python 与 C 系语言的钥匙。
#   变量不是存储位置，名字与对象之间是多对多关系。
#   几乎所有"Python 玄学 bug"（可变默认参数、循环内 lambda 延迟绑定）
#   都源于这一点。
def demo_binding_semantics():
    print("[4] 赋值即绑定")

    # 链式赋值：a 和 b 指向【同一个】列表对象
    a = b = [1, 2]
    print(f"    a = b = [1,2]; a is b = {a is b}")
    a.append(3)
    print(f"    a.append(3) 后 b 也变了 = {b}  <- 共享同一对象")

    # 这是初学者最常见的 bug 来源：以为 a = b 是"复制一份"
    b = [9]  # 重新绑定 b，a 不受影响
    print(f"    b 重新赋值后 a 不变 = {a}, b = {b}")

    # 元组解包：左右数量必须严格匹配，否则 ValueError
    x, y = 1, 2
    print(f"    x, y = 1, 2 -> x={x}, y={y}")

    # 交换：右侧先求值，交换才成立
    x, y = y, x
    print(f"    x, y = y, x -> x={x}, y={y}  (右侧先整体求值)")

    # 顺序陷阱：右侧依次求值赋给同名左侧，后者覆盖前者
    z, z = 1, 2
    print(f"    z, z = 1, 2 -> z = {z}  (后写覆盖先写)")

    # 星号解包：收集剩余项，无论多少个
    first, *middle, last = [1, 2, 3, 4, 5]
    print(f"    first, *middle, last -> {first}, {middle}, {last}")

    # 嵌套解包，一次拆两层
    (a1, (b1, b2)), c1 = (1, (2, 3)), 4
    print(f"    (a1,(b1,b2)), c1 = (1,(2,3)),4 -> {a1}, {b1}, {b2}, {c1}")

    # 函数传参传的是"对象引用"，所以 list 会被改，int 不会（只是重新绑定）
    def modify(p):
        p.append(99)  # 修改的是对象内容

    def rebind(p):
        p = ["全新"]  # 只改了函数内的局部名字，外部毫无感知

    shared = [1]
    modify(shared)
    print(f"    函数内 p.append 后外部 = {shared}  (对象被改)")
    rebind(shared)
    print(f"    函数内 p = [...] 后外部 = {shared}  (仅局部重绑定)")


# ============================================================================
# 语法解析 5：多重赋值的求值顺序
# ============================================================================
# 【语法规则】
#   a = b = c = value    右到左绑定
#   a, b = f(), g()      先全部求值，再解包
# 【执行顺序】
#   多元赋值的右侧永远先被构造为一个值序列，然后才逐个绑定。
#   这条规则让 a, b = b, a 这样的交换成为可能，
#   若边求值边赋值则会先覆盖。
# 【设计意图】
#   统一的"先求值后绑定"模型让语言行为可预测，
#   开发者不需要为交换、去包等场景单独记忆特例规则。
def demo_evaluation_order():
    print("[5] 多重赋值求值顺序")

    # 打印右侧求值的真实顺序
    order = []

    def tag(name, value):
        order.append(name)
        return value

    p, q = tag("先求 p", 1), tag("后求 q", 2)
    print(f"    右侧求值顺序 = {order}, p={p}, q={q}")

    # 对象构造器调用 vs 直接赋值：右侧为调用表达式时的顺序也一样
    counter = []

    class Tracker:
        def __init__(self, label):
            counter.append(label)

    t1, t2 = Tracker("A"), Tracker("B")
    print(f"    实例化顺序 = {counter}")

    # 链式赋值的绑定顺序：从左到右绑定同一个值
    bindings = []
    v = object()
    d1 = d2 = d3 = v
    # 三个名字全指向同一 id
    print(f"    链式赋值后 id 相同 = {id(d1) == id(d2) == id(d3)}")


# ============================================================================
# 语法解析 6：类型标注 —— 静态检查的契约，不是运行时的约束
# ============================================================================
# 【语法规则】
#   def f(x: int) -> str: ...     函数标注
#   g: int = 5                     变量标注（3.6+）
#   from typing import Final       常量标注
#   __annotations__               运行时可读取的标注字典
# 【执行顺序】
#   标注在函数定义时被求值并存入 __annotations__；
#   普通变量标注记录在模块的 __annotations__ 中。
#   但解释器【从不】根据标注做类型检查或自动转换 ——
#   传入 str 给标注为 int 的函数，完全不报错，函数体照常执行。
# 【设计意图】
#   Python 选择把标注设计为"可被工具读取的元数据"而非"运行时约束"。
#   这样类型检查交给 mypy / pyright 这类静态工具在开发期完成，
#   解释器保持零类型开销，运行时行为与纯 Python 代码完全一致。
def demo_annotations():
    print("[6] 类型标注的运行时效果")

    def greet(name: str, times: int = 1) -> str:
        # 标注说 name 是 str，但故意不做检查，传入 int 也能跑
        return f"{name}!" * times

    print(f"    正常调用   = {greet('hi', 3)}")
    # 违反标注但不报错 —— 证明标注不产生运行时约束
    print(f"    传 int 也不报错 = {greet(123, 1)}")

    print(f"    __annotations__ = {greet.__annotations__}")
    print("    -> 标注被保存为普通字典，可被类型检查工具读取，运行时不做校验")

    # typing.Final 是给静态检查器的建议，同样不影响运行时
    from typing import Final

    MAX_SIZE: Final[int] = 100
    # MAX_SIZE = 200  # 类型检查器会报错，但解释器允许
    print(f"    Final 常量 MAX_SIZE = {MAX_SIZE}  (赋新值解释器不阻止)")

    # 现代写法（3.10+）：类型别名用 type 语句，运行时创建一个类
    type UserId = int  # 3.12+ 的写法，此处仅演示概念，不影响功能
    print(f"    运行时对标注不做任何转换: greet(3.5, 2) = {greet(3.5, 2)}")


def main():
    demo_dynamic_typing()
    demo_id_and_interning()
    demo_mutability()
    demo_binding_semantics()
    demo_evaluation_order()
    demo_annotations()
    print("[完成] 02_basics/01_variables_and_types.py 运行结束")


if __name__ == "__main__":
    main()