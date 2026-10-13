"""环境自检脚本 —— 安装 Python 后第一个必须跑起来的程序。

用法（三种，任选其一都能看到同样的输出）：

    1) 直接运行脚本：  python examples/00_hello_env_check.py
    2) 以模块方式运行：python -m examples.00_hello_env_check
                       （需在父目录执行，且目录含 __init__.py）
    3) 交互式解释器：  python  →  然后输入下面这行：
        exec(open('examples/00_hello_env_check.py', encoding='utf-8').read())

本脚本不依赖任何第三方库，只用标准库，随时可以放心运行。

作者：Python 自学体系 · 阶段零
"""

import os
import platform
import sys


def report_python_version() -> None:
    """打印当前 Python 的版本号，并解释版本号每一段的含义。"""
    # sys.version_info 是一个「类元组」对象，major/minor/micro 分别对应 3.12.4 的 3 / 12 / 4
    info = sys.version_info
    print("=" * 60)
    print("【一】Python 版本信息")
    print("=" * 60)
    print(f"  完整版本串   : {sys.version}")
    print(f"  主版本号     : {info.major}")
    print(f"  次版本号     : {info.minor}   # 3.9 / 3.10 / 3.14 这一位变化最大")
    print(f"  修订号       : {info.micro}   # 补丁号，修 bug 用，日常无感")
    print(f"  简短版本号   : {platform.python_version()}")

    # releaselevel 可能是 'alpha'/'beta'/'candidate'/'final'，正式发布版是 'final'
    print(f"  发布阶段     : {info.releaselevel}")
    if info.releaselevel != "final":
        print("  ⚠️ 你用的不是正式版，遇到怪问题请先换正式版")

    # 本教材体系要求 3.10 及以上，低于该版本本课程的部分示例会跑不起来
    if info < (3, 10):
        print("  ❌ 版本过低：本学习体系要求 Python 3.10+，请到官网重新安装")
    else:
        print("  ✅ 版本满足本学习体系要求（3.10+）")


def report_interpreter_path() -> None:
    """打印解释器路径 —— 这是排查「装到哪儿了 / PATH 有没有配好」的关键信息。"""
    print()
    print("=" * 60)
    print("【二】解释器位置（PATH 排查的关键）")
    print("=" * 60)
    # sys.executable 是当前真正在跑的 python.exe 的绝对路径
    print(f"  解释器路径   : {sys.executable}")

    # dirname 去掉文件名，得到安装目录
    print(f"  安装目录     : {os.path.dirname(sys.executable)}")

    # sys.prefix 是「环境根目录」，虚拟环境就用它来区分自己
    print(f"  环境根目录   : {sys.prefix}")

    # base_prefix：系统 Python 的根目录。在虚拟环境里它和 prefix 不相等，
    # 所以可以用它判断「我现在是不是在虚拟环境里」
    print(f"  系统根目录   : {sys.base_prefix}")
    if sys.prefix != sys.base_prefix:
        print("  ✅ 当前处于虚拟环境（virtualenv / venv）中")
    else:
        print("  ℹ️  当前在「系统/全局」Python 环境中")

    # env 分隔符：Windows 是分号，Linux/macOS 是冒号
    print(f"  PATH 中的环境变量: {';' if os.name == 'nt' else ':'}  （这个是分隔符）")


def report_system() -> None:
    """打印操作系统信息，顺便演示 f-string 的格式化能力。"""
    print()
    print("=" * 60)
    print("【三】操作系统信息")
    print("=" * 60)
    print(f"  系统平台     : {platform.system()}       # Windows / Linux / Darwin(macOS)")
    print(f"  系统版本     : {platform.release()}")
    print(f"  机器架构     : {platform.machine()}      # AMD64 / arm64 / x86_64")
    print(f"  处理器       : {platform.processor()}")

    # win32_ver() 是平台专有方法：非 Windows 平台上它返回一组空值，不会报错
    win_version = platform.win32_ver()
    print(f"  Windows 版本 : {win_version[0]} {win_version[1]}  （非 Windows 平台返回空）")


def report_encoding() -> None:
    """检查默认编码 —— 中文环境下最常见的乱码根源。"""
    print()
    print("=" * 60)
    print("【四】文本编码检查")
    print("=" * 60)
    # UTF-8 是现在的事实标准；如果是 gbk，说明用的是老式 Windows 默认编码
    encoding = sys.getdefaultencoding()
    print(f"  默认编码     : {encoding}")
    if encoding.lower().replace("-", "") == "utf8":
        print("  ✅ 编码正常，中文注释与输出不会乱码")
    else:
        print("  ⚠️ 非 UTF-8，若出现中文乱码，请在文件头加 # -*- coding: utf-8 -*- 并用 UTF-8 保存")

    # 实际做一次「写入 → 读回」往返测试，这是最直观的验证方式
    test_file = "./_env_check_temp.txt"
    try:
        with open(test_file, "w", encoding="utf-8") as fp:
            fp.write("Python 环境自检：中文读写测试 ✅\n")
        with open(test_file, "r", encoding="utf-8") as fp:
            content = fp.read().strip()
        print(f"  读写往返测试 : {content}")
    except OSError as exc:
        print(f"  读写测试失败 : {exc}")
    finally:
        # 无论成功失败都要清理临时文件，不给用户目录留垃圾
        if os.path.exists(test_file):
            os.remove(test_file)
            print(f"  已清理临时文件: {test_file}")


def report_run_mode() -> None:
    """演示「脚本运行 / 模块运行 / 交互式运行」三种方式下代码看到的东西有什么不同。"""
    print()
    print("=" * 60)
    print("【五】当前运行方式")
    print("=" * 60)
    # __name__ 等于 "__main__" 说明是「作为脚本直接执行」的
    print(f"  __name__     : {__name__}")

    # 直接运行脚本时 __file__ 一定存在；在某些交互式环境里可能是 undefined
    file_var = globals().get("__file__", "<未定义，可能在交互式解释器中>")
    print(f"  __file__     : {file_var}")

    if __name__ == "__main__":
        print("  运行方式     : 以「主脚本」身份运行，main() 被执行")
    else:
        print("  运行方式     : 被其他模块 import 进来，main() 不会自动执行")


def first_demo() -> None:
    """一个最小的「有输入 → 有处理 → 有输出」程序，用来确认真的能跑代码。"""
    print()
    print("=" * 60)
    print("【六】试跑一个小程序：摄氏温度转华氏温度")
    print("=" * 60)
    # 华氏 = 摄氏 × 9/5 + 32；这里只用常量 9、5、32 没问题，属于纯算术公式
    for celsius in (0, 25.5, 37, 100):
        fahrenheit = celsius * 9 / 5 + 32
        # :6.2f 表示总宽度 6 位、小数点后 2 位，不足用空格补齐
        print(f"  {celsius:>6.2f} °C  =  {fahrenheit:>6.2f} °F")

    # input() 从标准输入读一行并去掉换行符；这里给默认值，方便脚本非交互运行时不卡住
    raw = input("  请输入一个摄氏温度（直接回车用 20）：").strip()
    try:
        user_celsius = float(raw) if raw else 20.0
    except ValueError:
        # ValueError 表示「字符串转 float 失败」，初学者最常见的输入错误
        print("  ⚠️ 输入的不是数字，已自动改用 20 进行计算")
        user_celsius = 20.0

    user_fahrenheit = user_celsius * 9 / 5 + 32
    print(f"  你的答案是：{user_celsius} °C = {user_fahrenheit:.2f} °F")


def main() -> None:
    """程序总入口：按顺序调用各个检查环节。"""
    print("🎉 恭喜！你的 Python 环境已经可以正常使用了。\n")
    report_python_version()
    report_interpreter_path()
    report_system()
    report_encoding()
    report_run_mode()
    first_demo()
    print("\n✅ 自检结束。如果以上信息都对，说明环境配置完全正常，可以开始 L01 了。")


# 标准入口约定：直接运行本文件时执行 main()，被 import 时不执行。
# 好处是别人 import 本模块做环境检测时，不会莫名其妙弹出一大堆输出。
if __name__ == "__main__":
    main()
