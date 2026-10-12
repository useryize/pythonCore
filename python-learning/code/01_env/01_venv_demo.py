# -*- coding: utf-8 -*-
"""
================================================================================
文件：01_venv_demo.py
模块：01_env（环境与工具链配套）

【本文件演示的语法点列表】
  1. sys.executable —— 当前真正执行本文件的解释器路径
  2. sys.prefix / sys.base_prefix —— 虚拟环境判断的核心依据
  3. sys.path —— 模块搜索路径清单及其顺序（导入机制的根基）
  4. os.environ —— 进程环境变量的读取与判断
  5. os.sep / os.pathsep / os.name —— 跨平台路径与路径分隔符常量
  6. venv 模块的探测（本文件只做检测与打印，不真正创建环境）
  7. 导入顺序与导入时机（import 放在顶部 vs 函数内 import）

【设计意图】
  本文件"只检测、不创建"，因此在没有任何虚拟环境的机器上也能安全运行。
  它是第 01 章的"体检报告"，让学习者对自己的运行环境有可观测的认知。

【预期输出摘要】（共 5 段，实际路径因机器而异）
  [1] 解释器信息：Python 3.13.14，executable = C:/Users/.../python.exe
  [2] 虚拟环境检测：在虚拟环境中 = False（prefix == base_prefix）
  [3] sys.path：共 N 条路径，第 0 条是脚本所在目录
  [4] 环境变量：只列出我们关心的若干个，缺失的显示 <未设置>
  [5] 跨平台常量：os.name = nt，sep = '\\'，pathsep = ';'
================================================================================
"""

import os
import sys


# ============================================================================
# 语法解析 1：sys 模块 —— 解释器自身的信息出口
# ============================================================================
# 【语法规则】
#   import sys
#   sys.属性名
# 【关键字作用】
#   sys 是 Python 标准库内置模块，无需安装，任何解释器都有。
#   它的每个"属性"都是解释器在运行时把 C 层状态暴露给 Python 层的只读数据。
# 【执行顺序】
#   1) import 先在 sys.modules 缓存里查找 sys
#   2) 找不到则由内置的冻结模块加载器直接返回内置模块对象（不读磁盘！）
#   3) 把结果绑定到当前全局命名空间的变量名 sys
# 【设计意图】
#   Python 把"解释器自身"这种元信息也做成了普通对象属性，
#   使得脚本可以用同一套属性访问语法读取运行时状态，
#   而不需要 FFI 或 ctypes。


def show_interpreter_info():
    """打印解释器基本信息。

    拆成独立函数而不是全部写在 main 里，是为了让"信息的获取"与"信息的展示"
    分离：获取逻辑无副作用，便于被测试。
    """
    print("[1] 解释器信息")

    # sys.executable：真正运行本文件的 python 可执行文件绝对路径。
    # 虚拟环境中它会指向 venv/Scripts/python.exe，这是判断"是否在虚拟环境里"最直观的方式。
    print(f"    executable   = {sys.executable}")

    # sys.version 是一个元组：(主版本号, 次版本号, 微版本号, 发布级别, 序列化号)
    # 前三个元素是字符串型数字，第四个是 'final' / 'candidate' / 'release' 之类
    info = sys.version_info
    print(
        f"    version      = {info.major}.{info.minor}.{info.micro}"
        f" ({info.releaselevel})"
    )

    # sys.platform 是平台标识：win32 / linux / darwin
    # 写跨平台代码时用它做分支，而不是用 os.name（后者粒度更粗，见第 5 段）
    print(f"    platform     = {sys.platform}")

    # sys.maxsize：解释器能表示的最大整数。
    # CPython 内部用 Py_ssize_t 存放容器长度，它是有符号 64 位，所以是 2**63 - 1
    print(f"    maxsize      = {sys.maxsize}")

    # sys.byteorder：机器字节序。'little' 几乎所有 PC 都是，意味着多字节整数低位在前
    print(f"    byteorder    = {sys.byteorder}")


# ============================================================================
# 语法解析 2：虚拟环境检测 —— 为什么两个 prefix 相等就是"没有虚拟环境"
# ============================================================================
# 【语法规则】
#   sys.prefix      创建当前解释器时所使用的安装前缀
#   sys.base_prefix  底层"基础 Python"（安装器本体）的前缀，通常不会因虚拟环境改变
#   两者相等 => 用的就是系统/基础解释器本身
#   两者不等 => 当前解释器被某个虚拟环境"接管"过
# 【设计意图】
#   Python 3.3+ 的 venv 不复制 Python 二进制，而是在环境里放一个 python.exe，
#   启动时通过 pyvenv.cfg 定位到 base_prefix。虚拟环境的价值就是让
#   sys.prefix 指向独立目录，从而改变 sys.path[0] 附近的 site-packages 位置，
#   实现依赖隔离。


def check_virtual_env():
    print("[2] 虚拟环境检测")
    print(f"    sys.prefix      = {sys.prefix}")
    print(f"    sys.base_prefix = {sys.base_prefix}")

    # 注意：这两个值可能很长，在 Windows 上换行显示。这里用相等比较而非字符串前缀比较，
    # 因为 venv 可能嵌在 base_prefix 目录内部（如 .venv），前缀匹配会误判。
    in_venv = sys.prefix != sys.base_prefix
    print(f"    在虚拟环境中    = {in_venv}")

    # venv 标准库存在，就说明解释器支持创建虚拟环境（3.3+ 才有）
    try:
        import venv  # noqa: F401 —— 仅探测可用性，不使用

        has_venv = True
    except ImportError:
        has_venv = False
    print(f"    支持 venv 模块  = {has_venv}")

    # VIRTUAL_ENV 通常由 activate 脚本设置，是判断"当前 shell 是否已激活"的另一手证据。
    # 但它只反映 shell 状态，不反映解释器状态，两者可能不一致（例如手动调 venv 的 python.exe）
    print(f"    VIRTUAL_ENV    = {os.environ.get('VIRTUAL_ENV', '<未设置>')}")


# ============================================================================
# 语法解析 3：sys.path —— Python 模块导入的搜索顺序表
# ============================================================================
# 【语法规则】
#   sys.path 是一个列表，元素是目录字符串（现代 Python 也允许 zip 路径）
#   import 某个模块时：按 sys.path 从左到右逐个查找，先命中者胜出
# 【执行顺序（导入一个模块时）】
#   1) 查 sys.modules —— 命中则直接复用，不重复加载（这是 import 幂等的基础）
#   2) 未命中则遍历 sys.path，找到第一个包含该模块名（或模块名/__init__.py）的目录
#   3) 找到后创建模块对象、执行模块顶层代码（此时模块自己的顶层代码会看到半初始化的自己）
#   4) 回填 sys.modules，返回并绑定到当前命名空间
# 【设计意图】
#   Python 选择"路径搜索 + 顺序优先"而不是 Node 的 node_modules 嵌套查找，
#   是为了让导入逻辑对用户完全透明可干预：sys.path 是一个普通 list，
#   用户随时可以 insert/append，从而实现插件系统与热修复。


def show_sys_path():
    print("[3] sys.path 模块搜索路径")
    print(f"    共 {len(sys.path)} 条")

    # 用 enumerate 而不是 for 打印，因为"下标顺序"本身就是知识点：
    # sys.path[0] 是脚本所在目录，这解释了为什么同目录下的 myutils.py 会被优先导入，
    # 也是"标准库被同目录同名文件劫持"这类坑的根源。
    for idx, entry in enumerate(sys.path):
        # 截断过长的路径（尤其是 Windows 用户目录），保持输出可读
        short = entry if len(entry) <= 58 else entry[:26] + " ... " + entry[-26:]
        print(f"      [{idx}] {short}")

    # 第 0 项说明：直接运行脚本时，sys.path[0] 是脚本所在目录；
    # 而 python -m 包名 运行时，第 0 项是当前工作目录，行为不同，这是高频面试题。
    print(f"    sys.path[0]    = {sys.path[0]}")
    print(f"    cwd            = {os.getcwd()}")


# ============================================================================
# 语法解析 4：os.environ —— 进程环境变量
# ============================================================================
# 【语法规则】
#   os.environ 是一个 os._Environ 映射对象，行为接近 dict
#   os.environ["KEY"]         读取，KeyError 表示未设置
#   os.environ.get("KEY", 默认值)  读取并给兜底，不会抛异常
#   "KEY" in os.environ       判断是否存在
#   键名大小写敏感（Windows 上由系统做不区分大小写映射，Linux 上严格区分）
# 【设计意图】
#   环境变量是"进程启动时由操作系统注入的字符串键值对"，
#   Python 不创建它，只是把 C 的 environ 数组包装成 dict-like 接口，
#   所以修改 os.environ 只影响本进程及其子进程，不会写回系统。
#   跨平台兼容库都靠它读 PATH / HOME / TEMP，避免直接 hardcode 路径。


def show_environ():
    print("[4] 环境变量（只读取关心的几项）")

    # 用列表定义关注项，避免遍历全部环境变量（可能有上百条，且可能含敏感值）
    watch = ["PATH", "HOME", "USERPROFILE", "TEMP", "CONDA_DEFAULT_ENV", "PYTHONPATH"]

    for key in watch:
        if key in os.environ:
            # 逻辑：PATH 可能超长，截断只保留头尾，保持"看起来像个路径"的信息量
            value = os.environ[key]
            if len(value) > 60:
                value = value[:28] + " ... " + value[-28:]
            print(f"    {key:<20} = {value}")
        else:
            print(f"    {key:<20} = <未设置>")

    # PYTHONPATH 会被 Python 启动时插入 sys.path，是"我能控制导入路径"的第一入口
    pythonpath = os.environ.get("PYTHONPATH")
    if pythonpath:
        # 用 os.pathsep 而非固定字符串切分，才能同时适配 Windows(';') 和 POSIX(':')
        print(f"    PYTHONPATH 会向 sys.path 注入 {len(pythonpath.split(os.pathsep))} 条路径")
    else:
        print("    PYTHONPATH 未设置，sys.path 未被它污染")

    # get 的默认值用法：不存在时返回 None，比 try/except KeyError 更简洁
    print(f"    get 不存在的键 = {os.environ.get('DEFINITELY_NOT_SET_12345')!r}")


# ============================================================================
# 语法解析 5：跨平台路径常量
# ============================================================================
# 【语法规则】
#   os.sep     —— 路径分隔符，Windows 为 '\'，POSIX 为 '/'
#   os.altsep  —— 备用分隔符，Windows 为 '/'，POSIX 为 None
#   os.pathsep —— 多个路径拼接时的分隔符，Windows 为 ';'，POSIX 为 ':'
#   os.name    —— 'nt' 表示 Windows，'posix' 表示类 Unix
# 【执行顺序】
#   这些常量在 os 模块导入时依据 os.name 一次性确定，不随运行中修改而变。
# 【设计意图】
#   早期 Python 用字符串拼接拼路径（'a' + '/' + 'b'），跨平台必然出问题。
#   提供平台常量是"承认路径本质是平台相关的"这一现实。
#   但现代最佳实践是直接用 pathlib.Path —— 它在内部做了同样的平台适配，
#   且是面向对象的，无需手工拼接。上面的常量用于理解 pathlib 内部的实现原理。


def show_cross_platform():
    print("[5] 跨平台路径常量")
    print(f"    os.name    = {os.name}")
    print(f"    os.sep     = {os.sep!r}")
    print(f"    os.altsep  = {os.altsep!r}")
    print(f"    os.pathsep = {os.pathsep!r}")
    print(f"    os.linesep = {os.linesep!r}")

    # 演示为什么硬编码 '/' 和 '\\' 都不可靠：Windows 上两者都能用，POSIX 上只有 '/' 能用
    # 而 os.sep 在两边都正确，这是它的存在意义。
    demo = f"data{os.sep}logs{os.sep}app.txt"
    print(f"    用 os.sep 拼接 = {demo}")

    # os.pathsep 的实际用途：还原"PATH 环境变量"里那一长串路径的分割方式
    print(f"    PATH 的分段符  = {os.pathsep!r}（用 split 切分 os.environ['PATH']）")


def main():
    # 顺序即讲解顺序，逐段打印，不做任何状态依赖
    show_interpreter_info()
    check_virtual_env()
    show_sys_path()
    show_environ()
    show_cross_platform()
    print("[完成] 01_env/01_venv_demo.py 运行结束")


# __name__ 由解释器在导入模块时设为模块名，直接运行本文件时设为 '__main__'。
# 用它守卫可让本文件既能被当脚本跑，也能被其他文件 import 而不触发副作用。
if __name__ == "__main__":
    main()