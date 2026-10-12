#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
常见内置异常类型速览
==============================

【演示的语法点】
1. 异常体系树：BaseException -> Exception -> 各具体异常
2. 每一类异常都用真实代码触发一次并捕获，展示：
   异常名 / 类型名 / args 内容 / 特有属性 / str() 输出
3. OSError 子类的真实触发（文件不存在、目录不存在、权限、解码错误）
4. 用 isinstance 遍历异常体系树，动态枚举某个基类的全部子类
5. 异常 args 属性的内部结构

【预期输出摘要】
- 按类别分组打印：LookupError 系、TypeError 系、ArithmeticError 系、
  AttributeError、OSError 系、ValueError 系、ImportError 系
- 每条形如：触发代码 -> 捕获类型 -> str(exc) -> 特有属性
- 末尾打印「通过异常体系树自动枚举出的 IndexError 的全部子类」
"""

import os
import sys
import tempfile


# ===== 语法解析 =====
# 【1】raise 语句的三种用法
#   raise ValueError              # 抛出一个异常类的实例（最常用）
#   raise ValueError("msg")       # 带消息，等价于 ValueError.__init__("msg")
#   raise exc_obj                 # 抛出一个已存在的异常实例
#
# 【2】raise 的位置要求
#   raise 必须写在「当前正在被处理的异常」之外。
#   如果写在 except 块内且不带 from，会形成「异常中异常」的隐式上下文链。
#
# 【3】本文件的演示策略
#   定义一个统一入口 trigger_and_catch(label, code_func, expected_type)，
#   用 lambda 把「可能出错的表达式」包起来，传给通用捕获器。
#   这样每种异常的展示结构完全一致，便于横向对比。
def trigger_and_catch(label, fn, expected_type=None):
    """触发 fn() 内的异常并按类型捕获，打印结构化信息。

    expected_type: 预期捕获的类型。若为 None 则捕获 Exception（通用兜底）。
    """
    # ===== 语法解析 =====
    # except (TypeA, TypeB) as e:  —— 元组形式，表示「或」关系
    # 这里我们用一个「动态构造的 except 元组」实现统一处理：
    # 把 except 需要的类型放进一个 tuple，再交给解释器。
    catch_types = (expected_type,) if expected_type else (Exception,)

    try:
        result = fn()
        print(f"[{label}] 未抛异常，返回: {result!r}")
    except catch_types as e:   # except 元组：命中其中任一类型即捕获
        # ===== 语法解析 =====
        # 所有异常对象都有三个必备属性：
        #   type(e)   -> 异常类
        #   str(e)    -> 异常消息字符串（相当于 e.args 单元素时的内容）
        #   e.args    -> 元组，装载传给异常构造函数的所有位置参数
        print(f"[{label}] 捕获 {type(e).__name__}")
        print(f"    str(e)  = {str(e)!r}")
        print(f"    e.args  = {e.args!r}")
        # isinstance 走 MRO 判断，支持子类匹配
        print(f"    isinstance(e, Exception) = {isinstance(e, Exception)}")
        if expected_type is not None:
            print(f"    isinstance(e, {expected_type.__name__}) = {isinstance(e, expected_type)}")
    else:
        # 此处不写 else 也行，但写上能强调「else 在无异常时才走」
        pass


def demo_lookup_errors():
    """LookupError 系：容器查找失败。"""
    print("=" * 70)
    print("【1】LookupError 系 —— 容器里找不到")
    print("=" * 70)

    # ===== 语法解析 =====
    # IndexError  -> 有序序列下标越界（list/str/tuple）
    # KeyError    -> 映射的键不存在（dict）。注意它的 str() 会加引号显示键，
    #               这是 CPython 为了区分 KeyError("a") 与 LookupError("a") 而特意设计的。
    # KeyError 直接继承 LookupError（不是从 IndexError 继承），二者是兄弟关系。
    trigger_and_catch("IndexError: 空列表取[0]",
                      lambda: [] [0], IndexError)
    trigger_and_catch("IndexError: 'ab'[10]",
                      lambda: "ab"[10], IndexError)
    trigger_and_catch("KeyError: 字典取不存在的键",
                      lambda: {"a": 1}["b"], KeyError)
    trigger_and_catch("KeyError: 字典.get 默认值不报错",
                      lambda: {"a": 1}.get("b", "默认值"))
    print()

    print("【对比】IndexError 与 KeyError 的 str() 表现：")
    try:
        {"k": 1}["missing"]
    except KeyError as e:
        # KeyError 的 str() 结果带引号：'missing'
        print(f"    KeyError 的 str()    = {str(e)!r}   <- 带引号，方便定位是键的问题")
        print(f"    e.args[0]            = {e.args[0]!r}   <- 拿到原始的键对象")
    print("【要点】KeyError 的 str() 有引号是刻意设计，便于区分「键」与「消息」。")
    print()


def demo_type_errors():
    """TypeError 系：类型不匹配。"""
    print("=" * 70)
    print("【2】TypeError 系 —— 类型用错了")
    print("=" * 70)

    trigger_and_catch("TypeError: int + str",
                      lambda: 1 + "abc", TypeError)
    trigger_and_catch("TypeError: len(5)",
                      lambda: len(5), TypeError)
    trigger_and_catch("TypeError: 不可迭代对象",
                      lambda: iter(42), TypeError)
    trigger_and_catch("TypeError: 非函数调用",
                      lambda: "abc"(), TypeError)
    # ===== 语法解析 =====
    # TypeError 的 str() 通常包含两段信息：
    #   unsupported operand type(s) for +: 'int' and 'str'
    #   ^^^^ 操作符                      ^^^^^^^^^^^ 两个操作数的类型
    # 阅读技巧：先看 operator 部分确定是哪个运算，再看两侧类型。
    print()

    print("【要点】TypeError 消息的固定格式：")
    print("    unsupported operand type(s) for <运算符>: '<左>' and '<右>'")
    print("    -> 先看运算符，再看两侧类型名。")
    print()


def demo_arithmetic_errors():
    """ArithmeticError 系：数值运算失败。"""
    print("=" * 70)
    print("【3】ArithmeticError 系 —— 算不动了")
    print("=" * 70)

    trigger_and_catch("ZeroDivisionError: 整数除零",
                      lambda: 1 / 0, ZeroDivisionError)
    trigger_and_catch("ZeroDivisionError: 取模除零",
                      lambda: 5 % 0, ZeroDivisionError)
    # ===== 语法解析 =====
    # 重要：浮点除零不抛 ZeroDivisionError！
    # 因为浮点数遵循 IEEE 754，有 +inf / -inf / nan 的表示。
    # 只有「模运算 %」对浮点仍然抛异常。
    trigger_and_catch("浮点除零不报错: 1.0 / 0.0",
                      lambda: 1.0 / 0.0)
    trigger_and_catch("浮点取模才报错: 1.0 % 0.0",
                      lambda: 1.0 % 0.0, ZeroDivisionError)

    # OverflowError：数值超过可表示范围（int 转 float 时常见）
    trigger_and_catch("OverflowError: int 转 float 溢出",
                      lambda: float(10 ** 400), OverflowError)
    print()

    print("【要点】1/0 抛 ZeroDivisionError，但 1.0/0.0 返回 inf（IEEE 754 语义）。")
    print("【要点】Python 整数是任意精度，只有转成 float 时才可能 OverflowError。")
    print()


def demo_attribute_name_errors():
    """AttributeError / NameError：属性与名字找不到。"""
    print("=" * 70)
    print("【4】AttributeError 与 NameError —— 名字找不到")
    print("=" * 70)

    trigger_and_catch("AttributeError: 整数没有 .upper",
                      lambda: (42).upper(), AttributeError)
    trigger_and_catch("NameError: 使用未定义变量",
                      lambda: undefined_variable_xyz, NameError)

    # ===== 语法解析 =====
    # AttributeError 在 Python 3.10+ 新增了 name / obj 属性，
    # 可以精确知道「是哪个对象的哪个属性」找不到，极大提升可调试性。
    print()
    print("【AttributeError 的 name/obj 属性（Python 3.10+）】")
    try:
        "abc".no_such_method()
    except AttributeError as e:
        print(f"    e.name = {e.name!r}   <- 缺失的属性名")
        print(f"    e.obj  = {e.obj!r}   <- 承载该属性的对象")
    print()

    # NameError 与 UnboundLocalError 的关系
    # UnboundLocalError 继承自 NameError，出现在「局部变量在赋值前被读取」时：
    #     def f(): return x; x = 1   -> 先读 x 再赋值 -> UnboundLocalError
    def use_before_assign():
        # 下面这行会先读取 local_var，但它是局部变量且尚未赋值
        return local_var
        local_var = 1   # 这行赋值让 local_var 成为局部变量，但已经晚了
    trigger_and_catch("UnboundLocalError: 局部变量先读后赋值",
                      use_before_assign, NameError)
    print("【要点】UnboundLocalError 是 NameError 的子类，证明「Python 在编译期就确定作用域」。")
    print()


def demo_os_errors():
    """OSError 系：真实的文件系统错误。"""
    print("=" * 70)
    print("【5】OSError 系 —— 真实的操作系统错误")
    print("=" * 70)

    # 用系统临时目录做实验，保证「路径确实不存在」
    missing = os.path.join(tempfile.gettempdir(), "definitely_not_exists_xyz.txt")
    trigger_and_catch("FileNotFoundError: 打开不存在的文件",
                      lambda: open(missing, encoding="utf-8"), FileNotFoundError)
    trigger_and_catch("FileNotFoundError: 删除不存在的文件",
                      lambda: os.remove(missing), FileNotFoundError)

    # ===== 语法解析 =====
    # 「把目录当文件打开」在 Linux 抛 IsADirectoryError，在 Windows 抛 PermissionError。
    # 这是跨平台差异的真实体现：OSError 的具体子类由「各平台的 C 层实现」决定，
    # 跨平台代码必须用 `except OSError` 兜底，不能硬编码具体子类。
    # 这里用「期望元组」+ 打印真实类型来适配两种平台。
    catch_types = (IsADirectoryError, PermissionError, OSError)
    print(f"[把目录当文件打开] 预期类型(跨平台): {[c.__name__ for c in catch_types]}")
    try:
        open(tempfile.gettempdir(), encoding="utf-8")
    except catch_types as e:
        print(f"    本平台实际捕获 {type(e).__name__}")
        print(f"    str(e)  = {str(e)!r}")
        print(f"    e.errno = {getattr(e, 'errno', None)}")
    print("    -> 跨平台代码请 `except OSError`，不要硬编码 IsADirectoryError")
    print()

    # ===== 语法解析 =====
    # 重要知识：NotADirectoryError / IsADirectoryError 只在部分平台可用。
    # 它们属于「阻塞错误」的子类关系：
    #   OSError
    #   ├── BlockingIOError
    #   ├── ChildProcessError
    #   ├── ConnectionError
    #   ├── FileExistsError
    #   ├── FileNotFoundError
    #   ├── InterruptedError
    #   ├── IsADirectoryError
    #   ├── NotADirectoryError
    #   ├── PermissionError
    #   ├── ProcessLookupError
    #   └── TimeoutError
    #
    # errno 属性：OSError 独有的、来自 C 层的错误码。
    # strerror 属性：错误码对应的系统消息。
    print()
    print("【OSError 的 errno / strerror / filename 属性】")
    try:
        open(missing, encoding="utf-8")
    except FileNotFoundError as e:
        print(f"    e.errno     = {e.errno}      # 数字错误码，2 = ENOENT")
        print(f"    e.strerror  = {e.strerror!r}")
        print(f"    e.filename  = {e.filename!r}")
    print()

    # UnicodeError 是 ValueError 的子类，属于解码/编码失败
    # 用 latin-1 解码一段 utf-8 字节会产生非法字节序列错误
    trigger_and_catch("UnicodeDecodeError: 用错误编码解码",
                      lambda: "你好".encode("utf-8").decode("latin-1"),
                      UnicodeDecodeError)
    print("【要点】UnicodeDecodeError 是 ValueError 的子类，不是 OSError，注意 except 顺序。")
    print()


def demo_value_errors():
    """ValueError 系：类型对但值不对。"""
    print("=" * 70)
    print("【6】ValueError 系 —— 类型没错，取值不合法")
    print("=" * 70)

    trigger_and_catch("ValueError: int('abc')",
                      lambda: int("abc"), ValueError)
    trigger_and_catch("ValueError: 非列表传入 count 参数",
                      lambda: "abc".count("a", 0, "b"), TypeError)
    # ===== 语法解析 =====
    # UnicodeDecodeError 已经在上一节展示，这里演示它的父类 ValueError。
    # 注意区分：
    #   TypeError  = 类型不匹配（把 str 当 int 用）
    #   ValueError = 类型匹配但值不在允许集合内（int('abc')）
    #
    # JSONDecodeError 也是 ValueError 的子类（json 模块定义），
    # 它继承自 ValueError 而非 json.JSONDecodeError -> ValueError 的旧结构。
    import json
    trigger_and_catch("JSONDecodeError: 非法 JSON",
                      lambda: json.loads("{not json}"), json.JSONDecodeError)
    print("【要点】ValueError 与 TypeError 的分界：类型是否匹配，而非取值是否合法。")
    print()


def demo_import_and_assert_errors():
    """ImportError / AssertionError / StopIteration / RecursionError。"""
    print("=" * 70)
    print("【7】ImportError、AssertionError、StopIteration、RecursionError")
    print("=" * 70)

    trigger_and_catch("ImportError: 导入不存在的模块",
                      lambda: __import__("no_such_module_xyz"), ImportError)
    trigger_and_catch("ModuleNotFoundError(ImportError子类)",
                      lambda: __import__("no_such_module_xyz"), ImportError)

    # 直接调用模块级工具函数，行为明确，无副作用
    trigger_and_catch("AssertionError: assert 失败",
                      _raise_assert, AssertionError)

    # ===== 语法解析 =====
    # StopIteration 由 next()/迭代器耗尽时抛出。
    # 「PEP 479」规定：生成器内若让 StopIteration 逃逸出生成器函数，
    # 会被自动转换成 RuntimeError，这是 Python 3.7+ 的重要行为变更。
    def gen_bad():
        yield 1
        raise StopIteration("生成器内部显式抛 StopIteration")
    trigger_and_catch("StopIteration 在生成器中逃逸 -> RuntimeError(PEP479)",
                      lambda: list(gen_bad()), RuntimeError)

    # RecursionError：递归过深（Python 3.5+ 新增，取代 RuntimeError）
    def deep(n):
        return deep(n + 1)
    trigger_and_catch("RecursionError: 无限递归",
                      lambda: deep(0), RecursionError)
    print("【要点】RecursionError 是 RuntimeError 的子类；默认递归上限约 1000。")
    print("【要点】PEP 479：生成器里的 StopIteration 会被转成 RuntimeError。")
    print()


def _raise_assert():
    """内部工具：用 raise 显式抛 AssertionError（比 assert 更可控）。"""
    raise AssertionError("这是手动 raise 的 AssertionError，消息可自定义")


def enumerate_subclasses(cls):
    """用异常体系树递归枚举某个异常类的全部后代子类。"""
    # ===== 语法解析 =====
    # cls.__subclasses__() 返回「直接子类」列表。
    # 递归调用即可得到整个子树。这是纯反射的标准用法。
    result = []
    for sub in cls.__subclasses__():
        result.append(sub.__name__)
        result.extend(enumerate_subclasses(sub))
    return sorted(result)


def demo_reflection():
    """利用反射遍历异常体系树。"""
    print("=" * 70)
    print("【8】反射：用 __subclasses__ 遍历异常体系树")
    print("=" * 70)

    # 验证体系树
    print("IndexError 的 MRO（方法解析顺序 = 继承链）:")
    # __mro__ 是「方法解析顺序」元组，展示类的线性化继承顺序
    for cls in IndexError.__mro__:
        print(f"    {cls.__name__}")

    print()
    print("LookupError 的全部后代子类:")
    subs = enumerate_subclasses(LookupError)
    for name in subs:
        print(f"    - {name}")

    print()
    print("OSError 的直接子类（按 errno 分组的关键错误）:")
    for name in enumerate_subclasses(OSError):
        print(f"    - {name}")
    print()
    print("【要点】__mro__ 决定属性查找顺序；__subclasses__ 用于动态发现类型。")
    print()


def main():
    """主入口。"""
    print("=" * 70)
    print("常见内置异常类型速览")
    print("=" * 70)
    demo_lookup_errors()
    demo_type_errors()
    demo_arithmetic_errors()
    demo_attribute_name_errors()
    demo_os_errors()
    demo_value_errors()
    demo_import_and_assert_errors()
    demo_reflection()
    print("=" * 70)
    print("演示结束：记住「先判断异常大类，再看具体子类」的两层捕获模式")
    print("=" * 70)


if __name__ == "__main__":
    main()