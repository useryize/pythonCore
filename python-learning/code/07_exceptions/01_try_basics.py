#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
try / except / else / finally 完整演示
================================================

【演示的语法点】
1. try 块与 except 子句的基本结构，异常对象的 as 绑定
2. except 的「顺序匹配」语义：先匹配先赢，子句从上到下逐个尝试
3. else 子句：只有 try 块「没有抛异常」时才执行
4. finally 子句：无论是否发生异常都执行，且最后执行
5. 多条 except 捕获不同异常类型
6. except 后裸 except / except Exception / except BaseException 的区别
7. finally 中 return 对异常/返回值的「吞掉」作用（面试高频坑）
8. try/except/else/finally 各种嵌套与组合的完整执行顺序推演

【预期输出摘要】
- 四种组合（正常 / 抛异常被捕获 / 抛异常未捕获 / finally 内 return）各有独立小节输出
- 每节均打印带序号的执行轨迹，形如：1.进入try -> 2.try正常 -> 3.else -> 4.finally
- 最后打印一张「组合 -> 执行序列」对照表
"""

import sys


# ===== 语法解析 =====
# 【1】基本语法规则
#   try:
#       <语句块 A>          # 可能抛异常的代码
#   except [异常类型] as e:  # 可选捕获类型；as 把异常对象绑定到变量
#       <语句块 B>
#   else:
#       <语句块 C>
#   finally:
#       <语句块 D>
#
# 【2】执行顺序（最重要的规则）
#   1) 进入 try，执行语句块 A
#   2) A 正常结束 -> 跳过所有 except -> 执行 else(C) -> 执行 finally(D)
#   3) A 抛异常 -> 从上到下找第一条「类型匹配」的 except -> 执行对应 B -> 执行 finally(D)
#      若没有任何 except 匹配 -> finally(D) 仍会执行 -> 然后异常继续向上传播
#
# 【3】设计意图
#   else 的存在是为了解决「try 块过宽」的老问题：
#   如果把不相关的代码也写进 try，那么 try 出错时会被错误地当成「保护对象出错」。
#   else 把「真正需要保护的那几行」和「后续处理逻辑」隔离开，
#   使 except 捕获到的异常一定来自受保护的代码，语义更精确。
#
#   finally 的存在是为了「无论成功失败都必须执行的清理」（关文件、关连接、回滚）。
#   它写在 try 的最外层保护范围，因此拥有最高的执行优先级和不可被绕过的地位。
def demo_1_basic_flow():
    """最基础的成功路径：try 正常 -> else -> finally。"""
    print("=" * 60)
    print("【演示1】正常路径：try -> else -> finally")
    print("=" * 60)

    trace = []  # 用列表记录执行轨迹，比逐行 print 更直观

    # ===== 语法解析 =====
    # def 定义函数；文档字符串是函数体的第一个字符串字面量，
    # 运行时被赋给函数对象的 __doc__ 属性，可用 help() 或 f.__doc__ 读取。
    # 文档字符串不是注释，是「表达式语句」，有实际运行时含义。
    def divide(a, b):
        """受保护地做除法。"""
        trace.append("1.进入 try")
        try:
            result = a / b        # 关键行：b==0 时触发 ZeroDivisionError
            trace.append(f"2.try 正常完成: {a}/{b}={result}")
        except ZeroDivisionError as e:
            # except 子句内的 as e 把异常实例绑定到局部名 e。
            # Python 3 会在 except 块结束后自动 del e，防止内存泄漏（异常 traceback 持有帧对象）。
            trace.append(f"2.try 抛异常被捕获: {type(e).__name__}: {e}")
            result = None
        else:
            # else 只在 try 块「完全无异常」时运行。
            trace.append("3.执行 else（try 无异常）")
        finally:
            # finally 无论如何都执行，且是最后一步（除非它自己 return/break）。
            trace.append("4.执行 finally（总是执行）")
        return result

    print("场景A：除数正常")
    divide(10, 2)
    for i, step in enumerate(trace, 1):
        print(f"   步骤{i}: {step}")
    print()

    trace.clear()  # 清空轨迹，不改变对象引用（list.clear 是原地清空）

    print("场景B：除数为 0（ZeroDivisionError 被捕获）")
    divide(10, 0)
    for i, step in enumerate(trace, 1):
        print(f"   步骤{i}: {step}")
    print()

    print("【要点】else 的执行时机：只在 try 未抛异常时；finally 永远执行且最后执行。")


# ===== 语法解析 =====
# 【1】多 except 的匹配语义
#   解释器维护一个「待处理异常」对象，从上到下逐条检查 except 子句的类型：
#     isinstance(异常对象, except子句类型) 为 True -> 选中该子句，匹配结束。
#   一旦某条 except 匹配成功，**后面的 except 全部不再检查**（不构成 else-if 链）。
#
# 【2】顺序敏感性
#   因为是「自上而下第一条匹配者胜」，把子类写在父类之前是正确写法：
#     except FileNotFoundError: ...   # 子类，必须在前
#     except OSError: ...             # 父类，必须在后
#   若顺序颠倒，FileNotFoundError 会被 OSError 先吃掉，子类分支永远进不去。
#
# 【3】类型匹配用 isinstance，不是 type() 全等
#   因此 except BaseException 可以捕获 IndexError、KeyboardInterrupt 等一切。
def demo_2_multiple_excepts():
    """演示多条 except 与顺序敏感性。"""
    print("=" * 60)
    print("【演示2】多条 except 的「先匹配先赢」与顺序敏感性")
    print("=" * 60)

    # ===== 语法解析 =====
    # 多个 except 子句是「并列可选」关系，不是 if-elif 互斥链。
    # 写成 except 子句时，类型必须是「类」，不是字符串（Python 2 允许字符串，这里不行）。
    def parse_and_process(raw):
        try:
            # 先尝试当作 JSON 解析（json 模块可能抛 JSONDecodeError）
            import json
            data = json.loads(raw)
            print(f"   -> 走 JSON 分支: {data}")
        except json.JSONDecodeError as e:
            # JSONDecodeError 是 ValueError 的子类，必须写在 ValueError 之前
            print(f"   -> JSON 解析失败(具体): {type(e).__name__}, pos={e.pos}")
            try:
                # 嵌套 try：JSON 不行，再试当作整数
                data = int(raw)
                print(f"   -> 嵌套成功，转为整数分支: {data}")
            except ValueError as e2:
                # 兜底：连整数都不是
                print(f"   -> 整数也失败，进入兜底: {type(e2).__name__}")
                data = None
            except TypeError as e2:
                print(f"   -> 类型错误: {type(e2).__name__}")
                data = None
            else:
                print("   -> 嵌套 try 无异常（本例未触发）")
            finally:
                print("   -> 嵌套 finally 总是执行")
        except ValueError as e:
            # 父类兜底：如果 JSONDecodeError 那条没写，这里会先吃掉它
            print(f"   -> 走父类 ValueError 分支（子类分支被跳过）: {e}")
        else:
            print("   -> JSON 解析成功，走 else 分支")
        finally:
            print("   -> 外层 finally 总是执行")
        return data

    print("场景A：合法 JSON 字符串")
    parse_and_process('{"name": "Tom", "age": 18}')
    print()

    print("场景B：非法 JSON，但是合法整数（触发嵌套成功）")
    parse_and_process("42")
    print()

    print("场景C：非法 JSON，也不是整数（触发全部兜底）")
    parse_and_process("abc_def")
    print()

    print("【要点】except 子句自上而下第一条匹配者胜；子类必须写在父类之前。")
    print("【要点】嵌套 try 时，内层 finally 先执行，然后才轮到外层 finally。")


# ===== 语法解析 =====
# 【1】三种「宽泛捕获」的语义层级（面试常问）
#   except:                  -> 等价 except BaseException: 捕获几乎一切，连
#                               KeyboardInterrupt / SystemExit / GeneratorExit 都捕获。
#                               这会吞掉 Ctrl+C，几乎永远是坏味道。
#   except Exception:        -> 捕获「程序逻辑错误」类异常，不含上述三个控制流异常。
#                               业务代码推荐用它作为最后一层兜底。
#   except BaseException:    -> Python 异常体系的根，捕获一切。
#
# 【2】异常体系树（简化）
#   BaseException
#   ├── KeyboardInterrupt   (Ctrl+C 产生，不该吞)
#   ├── SystemExit          (sys.exit() 产生，不该吞)
#   ├── GeneratorExit       (生成器.close() 产生，不该吞)
#   └── Exception           <- 业务代码处理的都是这一支
#       ├── ValueError / TypeError / NameError / IndexError / KeyError ...
#       ├── OSError
#       │   ├── FileNotFoundError
#       │   ├── PermissionError
#       │   └── IsADirectoryError
#       └── ...
def demo_3_bare_except_vs_exception():
    """对比裸 except / except Exception / except BaseException。"""
    print("=" * 60)
    print("【演示3】裸 except vs Exception vs BaseException")
    print("=" * 60)

    # 构造一个能被 BaseException 捕获、但不能被 Exception 捕获的异常：
    # 直接实例化 KeyboardInterrupt。它继承自 BaseException 而非 Exception。
    special_exc = KeyboardInterrupt("模拟用户按了 Ctrl+C")

    def catch_bare():
        try:
            raise special_exc
        except:              # 裸 except：捕获 BaseException 全部
            return "裸 except 捕获成功（连 Ctrl+C 都不放过）"

    def catch_exception():
        try:
            raise special_exc
        except Exception:    # 只捕获 Exception 子树 -> 捕获不到
            return "except Exception 捕获成功"
        except BaseException:
            return "except Exception 未捕获，被 BaseException 兜底捕获"

    def catch_normal():
        try:
            raise ValueError("普通业务异常")
        except Exception:
            return "except Exception 成功捕获 ValueError"

    print("1)", catch_bare())
    print("2)", catch_exception())
    print("3)", catch_normal())
    print()
    print("【要点】业务代码兜底请用 except Exception，禁止裸 except，否则 Ctrl+C 无效。")
    print("【要点】用 sys.exc_info() / raise 可以把捕获的异常重新抛出，不要用 except: pass 吞掉。")


# ===== 语法解析 =====
# 【1】finally 里 return 的「终止语义」
#   Python 用「异常表 + 调用栈」实现 try/finally，逻辑等价于把 finally
#   编译成函数末尾的一个无条件块，并带一个「待返回值的保存槽」。
#   当 finally 块执行 return 时：
#     - 待返回的值被丢弃
#     - 正在传播的异常被丢弃（不打印 traceback）
#     - 函数立即正常返回 finally 里 return 的值
#   这是 Python 里最反直觉的「异常屏蔽」行为，面试高频考点。
#
# 【2】正确写法
#   - 若必须在 finally 里做「返回类操作」（如 early return），先用 sys.exc_info()
#     或 except 标记把异常状态保存下来，再在 finally 末尾决定是否重新 raise。
#   - 若只是清理资源，finally 里永远不要写 return / break / continue。
def demo_4_finally_return_swallow():
    """演示 finally 中 return 会吞掉异常——典型陷阱。"""
    print("=" * 60)
    print("【演示4】陷阱：finally 里的 return 会吞掉异常")
    print("=" * 60)

    def bad_pattern():
        """反例：finally 里 return，异常被无声丢弃。"""
        try:
            raise ValueError("重要错误：数据校验失败")
        except ValueError:
            print("   已捕获 ValueError，准备记录日志")
            return "已处理"
        finally:
            # 这一行 return 会让上面的异常和返回值全部作废：
            # 函数直接返回 "清理完毕"，异常永远不会传播出去。
            # 调用方以为一切正常，实际上错误被彻底掩盖。
            return "清理完毕（但异常被吞了！）"

    def good_pattern():
        """正例：用返回值占位 + 显式返回，保持异常可传播。"""
        try:
            raise ValueError("重要错误：数据校验失败")
        except ValueError as e:
            print(f"   已捕获 ValueError: {e}")
            # 不在 finally 里 return，改为在 except 里决定返回值
            result = "已处理"
        finally:
            # finally 只做清理，绝不 return
            print("   资源清理完成（不干预返回值）")
        return result  # 在 try 之外 return，语义清晰

    def good_pattern2():
        """正例二：finally 里需要感知「是否有异常」时用 sys.exc_info()。"""
        trace = []
        try:
            raise RuntimeError("数据库连接失败")
        finally:
            # sys.exc_info() 返回 (type, value, traceback) 三元组；
            # 若当前无异常处理中，返回 (None, None, None)。
            exc_type, exc_val, _ = sys.exc_info()
            if exc_type is None:
                trace.append("finally：本次无异常经过")
            else:
                # 关键：这里只「观察」异常，不 return，异常会继续正常传播
                trace.append(f"finally：检测到 {exc_type.__name__} 将要传播，清理资源")
            print(f"   {trace[-1]}")
        return "此处不可达（因为异常会传播出去）"

    print("场景A：反例 bad_pattern()")
    try:
        r = bad_pattern()
        print(f"   返回值 = {r!r}")
        print("   !! 注意：异常被静默吞掉，调用方完全不知情，这是最危险的模式")
    except Exception as e:
        print(f"   捕获到异常: {e}")
    print()

    print("场景B：正例 good_pattern()")
    r = good_pattern()
    print(f"   返回值 = {r!r}（语义清晰）")
    print()

    print("场景C：正例二，finally 中用 sys.exc_info() 观察但不吞异常")
    try:
        good_pattern2()
    except RuntimeError as e:
        print(f"   异常成功传播到调用方: {type(e).__name__}: {e}")
    print()

    print("【要点】finally 中的 return/break/continue 会终止流程并屏蔽异常，务必避免。")


# ===== 语法解析 =====
# 【1】try/except/else/finally 的完整组合矩阵
#   我们穷举 4 种情形，观察执行轨迹：
#     情形1：try 无异常 + 无 else + 有 finally
#     情形2：try 有异常被捕获 + 有 else + 有 finally
#     情形3：try 有异常未被捕获 + 有 else + 有 finally（异常穿透）
#     情形4：try 嵌套 try
#
# 【2】观察重点
#   - else 在情形2中「不执行」：因为异常已被捕获，try 视为「不完整成功」。
#     这是最反直觉的一点：异常被 except 成功处理了，else 依然不执行。
#   - finally 在情形3中依然执行，然后异常继续向外抛。
def demo_5_all_combinations():
    """穷举 try/except/else/finally 的执行组合，输出对照轨迹。"""
    print("=" * 60)
    print("【演示5】try/except/else/finally 全部组合的执行轨迹")
    print("=" * 60)

    combos = []

    def case1_no_else():
        """情形1：try 成功，无 else。"""
        seq = []
        try:
            seq.append("try")
        except ValueError:
            seq.append("except")
        finally:
            seq.append("finally")
        return seq

    def case2_ok_with_else():
        """情形1': try 成功，有 else。"""
        seq = []
        try:
            seq.append("try")
        except ValueError:
            seq.append("except")
        else:
            seq.append("else")
        finally:
            seq.append("finally")
        return seq

    def case3_caught_with_else():
        """情形2：try 抛异常且被捕获，else 不执行。"""
        seq = []
        try:
            seq.append("try")
            raise ValueError("boom")
        except ValueError:
            seq.append("except")
        else:
            seq.append("else")   # 不会执行
        finally:
            seq.append("finally")
        return seq

    def case4_uncaught_with_else(seq):
        """情形3：try 抛异常且无 except 匹配，else 与 finally 的表现。

        注意 seq 由外部传入：异常穿透后局部变量仍在栈上，
        但若在函数内定义，调用方就拿不到轨迹了。
        """
        try:
            seq.append("try")
            raise ValueError("boom")
        except TypeError:       # 类型不匹配，捕获不到
            seq.append("except")
        else:
            seq.append("else")
        finally:
            seq.append("finally")
        # 注意：这个函数内部的 ValueError 会穿透出去，
        # 所以调用处必须自己 try/except 才能拿到返回值。
        return seq, "ValueError 会继续向上传播"

    combos.append(("情形1  try成功/无else", case1_no_else()))
    combos.append(("情形1' try成功/有else", case2_ok_with_else()))
    combos.append(("情形2  异常被捕获/有else", case3_caught_with_else()))
    # 情形3 必须由调用方 try 包裹，因为内部异常是「故意不捕获」的，
    # 这正是要演示的「异常穿透 finally 后继续传播」行为。
    seq4 = []
    try:
        case4_uncaught_with_else(seq4)
    except ValueError:
        seq4.append("!! ValueError 穿透到调用方")
        note = "finally 已执行，随后异常传播到调用方（traceback 完整保留）"
    combos.append(("情形3  异常未被捕获", seq4))

    # 打印对照表
    header = f"{'场景':<24} | {'执行轨迹':<38}"
    print(header)
    print("-" * 66)
    for name, seq in combos:
        print(f"{name:<24} | {' -> '.join(seq):<38}")
    print("-" * 66)
    print(f"情形3 补充说明：{note}")
    print()

    # ===== 语法解析 =====
    # 表格化输出：用字符串的 ljust/rjust 做定宽排版。
    # 这是纯字符串操作，不依赖任何第三方库，是处理 ASCII 表格的标准做法。
    # 注意：ljust 对中文字符不准（中文占两个终端列但 len()==1），
    #       所以下面用「场景名统一 6 个汉字」的方式规避，实际工程里应换 tabulate 等库。

    print("【对照总结】")
    print("  · try 无异常      -> else 执行, finally 执行")
    print("  · try 异常被捕获  -> except 执行, else 不执行(!), finally 执行")
    print("  · try 异常未捕获  -> except 跳过, else 跳过, finally 执行, 异常继续传播")
    print("  · finally 永远执行，且是整个 try 语句的最后一步")


def demo_6_practical_pattern():
    """真实模式：资源清理 + 异常翻译。"""
    print("=" * 60)
    print("【演示6】工程实践：资源清理与「异常翻译」模式")
    print("=" * 60)

    # ===== 语法解析 =====
    # 「异常翻译」模式：底层代码抛低层异常（KeyError），
    # 上层用 except 捕获后 raise 自己的业务异常，并保留异常链（raise ... from e）。
    # 这样调用方只需理解高层异常，不必了解实现细节。
    class ConfigError(Exception):
        """配置错误（业务异常）。"""
        pass

    def load_setting(config, key):
        # 模拟底层：字典取值失败会抛 KeyError（低层、语义模糊）
        try:
            return config[key]
        except KeyError:
            # 重新抛出高层异常，from 显式指定「原因」
            raise ConfigError(f"缺少必需的配置项: {key!r}") from None

    def safe_settings(config, key, default):
        """需要容错的场景：缺失就用默认值，不抛异常。"""
        try:
            return config[key]
        except KeyError:
            # 这里不 raise，只返回兜底值；注意 e 已无用途，可写 except KeyError:
            return default

    config = {"host": "localhost", "port": 8080}

    print("1) 正常读取 port:", load_setting(config, "port"))
    print("2) 正常读取 host:", load_setting(config, "host"))
    print()

    print("3) 读取不存在的配置（触发异常翻译）：")
    try:
        load_setting(config, "debug")
    except ConfigError as e:
        print(f"   捕获到业务异常: {type(e).__name__}: {e}")
        # 查看异常链：e.__cause__ 是 from 指定的异常，e.__context__ 是隐式上下文
        print(f"   __cause__ (显式 from): {e.__cause__!r}")
        print(f"   __context__ (隐式上下文): {e.__context__!r}")
    print()

    print("4) 容错版本读取不存在的配置:", safe_settings(config, "debug", False))
    print()

    print("【要点】低层异常用 try/except 捕获，翻译成业务异常再抛；")
    print("       需要容错的地方直接给默认值，不要用 None 表示「没取到」以免混淆。")


def main():
    """主入口：依次执行所有演示。"""
    print("=" * 60)
    print("try / except / else / finally 完整演示")
    print("=" * 60)
    demo_1_basic_flow()
    print()
    demo_2_multiple_excepts()
    print()
    demo_3_bare_except_vs_exception()
    print()
    demo_4_finally_return_swallow()
    print()
    demo_5_all_combinations()
    print()
    demo_6_practical_pattern()
    print()
    print("=" * 60)
    print("演示结束")
    print("=" * 60)


# ===== 语法解析 =====
# 【1】if __name__ == "__main__": 的意义
#   Python 执行 .py 文件时，会把该脚本的模块名设为 "__main__"；
#   而被 import 时模块名是文件名（如 try_basics）。
#   判断 __name__ == "__main__" 可以让「主逻辑只在直接运行本文件时执行」，
#   被其他文件导入时只暴露函数与类定义。这是 Python 的标准惯例。
#
# 【2】为什么重要
#   若不写这个判断，其他文件 `import 01_try_basics`（严格说要用 importlib，
#   因为模块名不能以数字开头）时，主逻辑也会执行，产生副作用、打印大量内容。
if __name__ == "__main__":
    main()