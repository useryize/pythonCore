#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自定义异常体系
==============================

【演示的语法点】
1. 自定义异常基类的定义，继承 Exception
2. 多级派生：基类 -> 中间层 -> 具体业务异常（三层树）
3. 异常类携带上下文属性（在 __init__ 里存业务字段），自定义 str
4. raise ... from 显式异常链，异常链的三种状态：
   __cause__ / __context__ / __suppress_context__
5. 异常分组捕获：一次性捕获一整族自定义异常
6. 正确 vs 错误的异常类定义（为什么不建议继承 BaseException）
7. traceback 的三级链条 __traceback__ / __cause__ / __context__

【预期输出摘要】
- 打印自定义异常体系树（用 __subclasses__ 反射）
- 每个异常携带 code / message / 上下文数据，并输出自定义的 __str__
- 显式异常链演示：from 显式指定 vs 隐式上下文 vs from None 抑制
- 异常分组捕获 demo_all_app_errors(...) 一次接住整族异常
"""

import sys


# ===== 语法解析 =====
# 【1】继承语法
#   class MyError(Exception): ...
#   - 类名用 PascalCase，习惯上以 Error / Exception 结尾
#   - 必须继承 Exception 或其子类，不能继承 object
#     （继承 object 的类无法被 `except` 捕获，会直接穿透崩溃）
#   - 绝对不要继承 BaseException：那会连 KeyboardInterrupt 一起继承，
#     语义上不清晰，且违背「异常类属于业务域」的设计原则
#
# 【2】__init__ 签名规则
#   BaseException.__init__(self, *args) 会把所有位置参数存进 self.args。
#   如果子类想保存业务字段，标准写法是：
#       def __init__(self, message, *, code=None, **kwargs):
#           super().__init__(message)     # 必须调用父类初始化，让 args 有内容
#           self.code = code
#   注意 super().__init__() 一定要调用，否则 self.args 为空，
#   str(e) 会变成空字符串，traceback 失去可读性。
class AppError(Exception):
    """所有应用级异常的基类。

    携带三个通用字段：
      message : 人类可读的错误描述
      code    : 机器可读的错误码
      details : 附加上下文数据（字典）
    """

    # 类属性：所有子类共享的默认值，可在实例上覆盖
    default_code = "APP_UNKNOWN"

    def __init__(self, message="", *, code=None, **details):
        """统一入口：子类只需把额外字段塞进 details，无需重复父类逻辑。

        设计意图：让所有 AppError 子类共享同一套「消息 + 码 + 详情」结构，
        __str__ 也只需要在基类实现一次，子类按需扩展。
        """
        # **details 收集所有未显式声明的关键字参数，作为附加上下文存储
        super().__init__(message)
        self.message = message
        # code 为 None 时回退到类属性 default_code
        self.code = code if code is not None else self.default_code
        self.details = details

    def __str__(self):
        """基类默认 __str__：输出 code + message + 排序后的 details。"""
        extra = ""
        if self.details:
            # sorted 保证输出顺序稳定，便于测试断言与日志比对
            items = ", ".join(f"{k}={v!r}" for k, v in sorted(self.details.items()))
            extra = f" | 详情: {items}"
        return f"[{self.code}] {self.message}{extra}"

    # ===== 语法解析 =====
    # 类方法装饰器 @classmethod 的第一个参数是 cls（不是 self），
    # 表示绑定到「类对象」而非实例。这样可以用统一逻辑构造异常。
    @classmethod
    def with_code(cls, code, message, **details):
        """工厂方法：指定错误码快速构造。"""
        # type(self).__name__ 在实例方法里是 self 的类名；
        # 这里因为是类方法，可以直接用 cls.__name__，支持子类继承。
        err = cls(f"[{code}] {message}", **details)
        err.code = code
        return err


class ValidationError(AppError):
    """参数/数据校验失败（第一层派生）。"""
    default_code = "APP_VALIDATION"
    # 本类不重复实现 __str__，直接复用基类渲染（code/message/details）


class DataAccessError(AppError):
    """数据访问层错误（第一层派生，兄弟节点）。"""
    default_code = "APP_DATA_ACCESS"

    def __init__(self, message, *, operation=None, **details):
        """数据访问错误需要额外知道「是哪次操作」。"""
        # **details 是收集剩余关键字参数，保证调用方可以自由附加上下文
        super().__init__(message, **details)
        self.operation = operation

    def __str__(self):
        base = super().__str__()
        # 三引号 f-string 做多行拼接，让长错误信息可读
        return (f"{base}\n"
                f"    操作: {self.operation!r}")


# ===== 语法解析 =====
# 【2】第二层派生：把 ValidationError 继续细分
#   多级派生的价值：调用方可以写
#       except SchemaError:      # 精确处理某一种
#       except ValidationError:  # 兜底处理所有校验类
#   两层都能捕获到，实现「精确 + 兜底」并存。
class SchemaError(ValidationError):
    """数据结构/字段缺失。"""
    default_code = "APP_SCHEMA"

    def __init__(self, message, *, field=None, expected=None, **details):
        super().__init__(message, field=field, expected=expected, **details)
        # 注意：这里没调 ValidationError.__init__ 而调了 AppError.__init__？
        # 不——ValidationError 没有自定义 __init__，所以 super().__init__ 沿 MRO
        # 找到 AppError.__init__（继承来的），行为正确。
        self.field = field
        self.expected = expected

    def __str__(self):
        return (f"{super().__str__()}\n"
                f"    字段: {self.field!r}, 期望: {self.expected!r}")


class RangeValidationError(ValidationError):
    """数值超出允许范围。"""
    default_code = "APP_RANGE"

    def __init__(self, message, *, value=None, min_value=None, max_value=None, **details):
        # 把数值信息塞进 details，让 AppError.__str__ 能统一渲染
        super().__init__(message, value=value, min_value=min_value,
                         max_value=max_value, **details)


def build_exception_tree():
    """用反射打印自定义异常体系树。"""
    print("=" * 70)
    print("【1】自定义异常体系树")
    print("=" * 70)

    def walk(cls, depth=0):
        # depth 控制缩进，实现树形展示
        print("    " * depth + ("└─ " if depth else "") + cls.__name__)
        for sub in cls.__subclasses__():
            walk(sub, depth + 1)

    walk(AppError)
    print()
    print("【要点】继承 Exception 而非 BaseException；否则会误捕获 Ctrl+C。")
    print()


def demo_custom_str_and_context():
    """自定义异常携带上下文 + 自定义 __str__。"""
    print("=" * 70)
    print("【2】自定义异常携带上下文 + 自定义 __str__")
    print("=" * 70)

    # ===== 语法解析 =====
    # 关键字参数（*, code=None）强制调用方用具名传参，
    # 避免位置参数顺序记错，这是异常类设计的最佳实践。
    err1 = SchemaError("用户对象缺少必填字段",
                       field="email",
                       expected="str")
    print("① SchemaError 的多层 __str__：")
    print(f"    type   = {type(err1).__name__}")
    print(f"    str(e) =")
    # 多行字符串用 textwrap 或直接缩进打印
    for line in str(err1).split("\n"):
        print(f"      {line}")
    print(f"    code   = {err1.code}")
    print(f"    field  = {err1.field}  (业务字段)")
    print(f"    args   = {err1.args!r}")
    print()

    # ===== 语法解析 =====
    # 静态类型检查器（Pylance/mypy）靠 MRO 做异常推断，
    # `except SchemaError` 会自动把 err1 的类型收窄，
    # 访问 .field 属性时不会有「未知属性」告警。
    err2 = RangeValidationError("温度超出量程",
                               value=-273.2,
                               min_value=-50,
                               max_value=150)
    print("② RangeValidationError（字段都塞进 details 统一渲染）：")
    for line in str(err2).split("\n"):
        print(f"      {line}")
    print()

    err3 = DataAccessError("数据库连接超时",
                           operation="SELECT users",
                           retry_count=3,
                           host="db.internal")
    print("③ DataAccessError（自定义 __init__ 字段）：")
    for line in str(err3).split("\n"):
        print(f"      {line}")
    print(f"    e.operation = {err3.operation!r}  (实例属性)")
    print()

    # 工厂方法构造
    err4 = AppError.with_code("E9999", "工厂方法创建的异常", source="demo")
    print("④ 通过类方法工厂 with_code() 构造：")
    print(f"    {type(err4).__name__}: {err4}")
    print(f"    code = {err4.code}")
    print()


def demo_raise_from_chain():
    """raise ... from 异常链的三种状态。"""
    print("=" * 70)
    print("【3】raise ... from：异常链的三种语义")
    print("=" * 70)

    def low_level_read(path):
        """底层：抛 Python 原生异常。"""
        raise FileNotFoundError(f"系统找不到文件: {path}")

    def mid_level_load(path):
        """中层：捕获原生异常，翻译成业务异常，用 from 建立显式因果链。"""
        try:
            low_level_read(path)
        except FileNotFoundError as e:
            # ===== 语法解析 =====
            # raise NewError(...) from e
            #   设置 e.__cause__ = 原异常  -> 「因为它，才导致我」
            #   语义：显式声明因果关系，traceback 打印为
            #          "The above exception was the direct cause of..."
            # 不写 from 时，Python 也会自动设置 __context__（隐式上下文），
            #   打印为 "During handling of the above exception..."
            #   两者语义不同：隐式 = 「碰巧在 except 里发生」，
            #                 显式 = 「它就是原因」。
            raise DataAccessError("加载用户配置失败",
                                  operation="read_config",
                                  path=path) from e

    def mid_level_suppress(path):
        """中层：故意隐藏底层原因（from None）。"""
        try:
            low_level_read(path)
        except FileNotFoundError:
            # ===== 语法解析 =====
            # from None 会：
            #   1) 把 __cause__ 设为 None
            #   2) 把 __suppress_context__ 设为 True
            #   3) traceback 不再显示任何「上下文」
            # 适用场景：底层细节对调用方无意义，或含敏感信息不应泄露。
            raise AppError.with_code("E1001", "配置文件不可用") from None

    print("① 显式异常链 raise X from e：")
    try:
        mid_level_load("/etc/app/config.yaml")
    except DataAccessError as e:
        print(f"    捕获 {type(e).__name__}: {str(e).splitlines()[0]}")
        print(f"    __cause__   = {type(e.__cause__).__name__}: {e.__cause__}")
        print(f"    __context__ = {e.__context__}")
        print(f"    __suppress_context__ = {e.__suppress_context__}")
    print()

    print("② 隐式上下文（不写 from）：")
    def mid_level_implicit(path):
        try:
            low_level_read(path)
        except FileNotFoundError:
            # 不写 from：Python 自动把当前异常存进 __context__，
            # 语义是「在处理上一个异常时，又发生了新异常」。
            raise AppError("配置加载时发生未预期错误")
    try:
        mid_level_implicit("/x")
    except AppError as e:
        print(f"    __cause__   = {e.__cause__}      <- 显式原因为空")
        print(f"    __context__ = {type(e.__context__).__name__}: {e.__context__}")
    print()

    print("③ 抑制上下文 raise X from None：")
    try:
        mid_level_suppress("/y")
    except AppError as e:
        print(f"    __cause__   = {e.__cause__}")
        print(f"    __context__ = {type(e.__context__).__name__}  <- 仍然存在对象")
        print(f"    __suppress_context__ = {e.__suppress_context__}  <- 但 traceback 不会显示")
    print()

    print("④ 完整 traceback 文本（观察两种提示语的差别）：")
    print("-" * 60)
    import traceback
    try:
        mid_level_load("/etc/app/config.yaml")
    except DataAccessError:
        # traceback.format_exc() 返回完整字符串，不写入 stderr
        tb = traceback.format_exc()
        for line in tb.strip().split("\n"):
            print(f"    {line}")
    print("-" * 60)
    print("【要点】from e = 直接原因（direct cause）；不写 = 上下文（context）。")
    print("【要点】两种都会完整保留原始异常信息，便于排查根因。")


def demo_group_catch():
    """按异常族分组捕获。"""
    print("=" * 70)
    print("【4】分组捕获：一次接住整族自定义异常")
    print("=" * 70)

    # ===== 语法解析 =====
    # 自定义异常的最大价值就在这里：
    # 调用方可以用一个 except 接住「所有应用异常」，
    # 而不必知道底下有多少种具体类型、每个来自哪个层次。
    def process(operation):
        """模拟一个可能以多种方式失败的操作。"""
        if operation == "validate":
            raise SchemaError("请求体不是合法 JSON", field="body", expected="dict")
        elif operation == "range":
            raise RangeValidationError("端口超出范围", value=70000,
                                       min_value=1, max_value=65535)
        elif operation == "db":
            raise DataAccessError("死锁", operation="UPDATE", retry_count=3)
        else:
            raise ValueError("未知操作类型")

    ops = ["validate", "range", "db", "unknown"]
    for op in ops:
        print(f"\n操作: {op}")
        # ===== 语法解析 =====
        # except 子句的顺序在这里至关重要：
        #   SchemaError / RangeValidationError 是 ValidationError 的子类，
        #   必须写在 `except ValidationError` 之前才能被单独处理。
        # 这与内置异常「子类在前」的规则完全一致。
        try:
            process(op)
        except SchemaError as e:
            print(f"    [精确处理] SchemaError -> field={e.field}")
        except RangeValidationError as e:
            print(f"    [精确处理] RangeValidationError -> {e.details['value']}")
        except ValidationError as e:
            print(f"    [兜底] 其他 ValidationError -> {e}")
        except DataAccessError as e:
            print(f"    [精确处理] DataAccessError -> op={e.operation}")
        except AppError as e:
            print(f"    [兜底] 其他 AppError -> {e}")
        except ValueError as e:
            # 非 AppError 家族的原生异常，也要能被框架接住
            print(f"    [非业务异常] {type(e).__name__} -> {e}")
        except Exception as e:
            # 最外层兜底：记录未知异常并保持进程存活
            print(f"    [未知异常] {type(e).__name__} -> {e}")
        else:
            print("    [无异常] 正常完成")

    print()
    print("【要点】框架层用 `except AppError` 兜底业务异常，用 `except Exception` 兜底未知异常，")
    print("       两级兜底既不漏也不误吞控制流异常。")


def demo_traceback_chain():
    """traceback 的三级链条。"""
    print("=" * 70)
    print("【5】traceback 对象链条")
    print("=" * 70)

    def level3():
        raise ValueError("最深处的错误")

    def level2():
        level3()

    def level1():
        level2()

    # ===== 语法解析 =====
    # traceback 对象的类型是 types.TracebackType，
    # 它是一个「链表」：每个帧记录 tb_frame（栈帧）、tb_lineno（行号）、
    # tb_lasti（字节码偏移）、tb_next（上一层）。
    # 通过 tb_next 可以手动遍历调用栈，这是 logging.exception 打印的底层数据源。
    try:
        level1()
    except ValueError as e:
        print("手动遍历 traceback 链：")
        tb = e.__traceback__
        depth = 0
        while tb is not None:
            frame = tb.tb_frame
            print(f"    [{depth}] 函数 {frame.f_code.co_name:12s} "
                  f"第 {tb.tb_lineno} 行  文件 {frame.f_code.co_filename.split(chr(92))[-1]}")
            tb = tb.tb_next
            depth += 1
        print()
        print(f"e.__traceback__ 类型 = {type(e.__traceback__).__name__}")
        print("【要点】__traceback__ -> __cause__ -> __context__ 构成完整的三级异常链条。")


def demo_bad_inheritance():
    """对比：继承 object 的「假异常」类。"""
    print("=" * 70)
    print("【6】反例：没有继承 Exception 的异常类")
    print("=" * 70)

    # ===== 语法解析 =====
    # 这个类虽然叫 Error，但它继承的是 Exception，不是 object —— 先看正例。
    class GoodError(Exception):
        pass

    # 反例：继承 BaseException 会连 KeyboardInterrupt 一起「继承」语义
    class BaseError(BaseException):
        pass

    # 极端反例：完全没继承任何异常基类
    class NotAnError(Exception):
        """正确写法：继承 Exception，才能被 except 捕获。"""
        pass

    print(f"GoodError    的 MRO: {[c.__name__ for c in GoodError.__mro__]}")
    print(f"BaseError    的 MRO: {[c.__name__ for c in BaseError.__mro__]}")
    print(f"NotAnError   的 MRO: {[c.__name__ for c in NotAnError.__mro__]}")
    print()

    # 演示 BaseError 的危险性：except Exception 接不住它
    try:
        raise BaseError("危险：业务异常混入控制流分支")
    except Exception:
        print("!! 不可能走到这里")
    except BaseError as e:
        print(f"只有 `except BaseException/BaseError` 能接住: {e}")
        print("-> 业务异常绝不能继承 BaseException，否则框架的 `except Exception` 会漏掉它")
    print()

    # ===== 语法解析 =====
    # 反例：继承 object 的类，raise 时直接抛 TypeError（无法传参），
    # 即使勉强抛出去，`except 异常类:` 本身就会报
    # 「catching classes that do not inherit from BaseException is not allowed」。
    # 这里用「不真正抛出」的方式演示，避免中断程序。
    class PlainError:
        """错误写法：没有继承任何异常基类。"""

        def __init__(self, message):
            self.message = message   # 手动保存消息，但永远不会作为异常被捕获

    print("反例：PlainError 未继承 BaseException")
    print(f"    PlainError.__mro__ = {[c.__name__ for c in PlainError.__mro__]}")
    print(f"    isinstance(PlainError(), BaseException) = {isinstance(PlainError('x'), BaseException)}")
    # 用 try 包住这次非法捕获，捕获它自己抛出的 TypeError，证明规则确实存在
    try:
        try:
            raise PlainError("消息")   # 第一次失败：PlainError() 不能作为异常被 raise 带参
        except PlainError:
            pass
    except TypeError as e:
        print(f"    raise 时的真实报错: {e}")
    print("    -> 说明：异常类必须继承 BaseException 子树，否则 except 形同虚设")
    print("【要点】异常类正确继承链：object -> BaseException -> Exception -> 业务基类 -> 具体异常")


def main():
    """主入口。"""
    print("=" * 70)
    print("自定义异常体系演示")
    print("=" * 70)
    build_exception_tree()
    print()
    demo_custom_str_and_context()
    print()
    demo_raise_from_chain()
    print()
    demo_group_catch()
    print()
    demo_traceback_chain()
    print()
    demo_bad_inheritance()
    print("=" * 70)
    print("演示结束")
    print("=" * 70)


if __name__ == "__main__":
    main()