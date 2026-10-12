# -*- coding: utf-8 -*-
"""
================================================================================
文件：03_script_vs_module.py
模块：01_env（环境与工具链配套）

【本文件演示的语法点列表】
  1. __name__ 变量的取值规则 —— '__main__' 与 模块名 的区别
  2. if __name__ == "__main__": 守卫模式的作用与历史由来
  3. 直接运行 (python 文件.py) 与 以模块导入 (import 文件 / python -m) 的差异
  4. sys.modules 与导入缓存 —— 为什么重复 import 只执行一次顶层代码
  5. 相对导入 vs 绝对导入（__package__ 的作用）
  6. 副作用控制的工程意义：模块顶层应只做定义，不做执行
  7. 动态导入 importlib —— 演示本文件被导入时与直接运行时的两种行为

【设计意图】
  Python 无法像 C/Java 那样区分"程序入口"和"库文件"，
  同一个 .py 文件既可能是程序也可能是库。
  `if __name__ == "__main__"` 是语言层面承认这一事实后给出的约定式解法。
  它不是关键字，没有强制力，全靠开发者自觉 —— 理解这一点比记住写法更重要。

【预期输出摘要】
  [1] __name__ 的取值：直接运行时为 '__main__'
  [2] 被导入时为模块名 '_03_script_vs_module_demo'（子进程实测）
  [3] 三种执行方式的对照表
  [4] 导入缓存：顶层代码只执行一次（计数器验证）
  [5] __package__ 与相对导入的可用性
  [6] 主逻辑是否执行的差异总结
================================================================================
"""

import os
import subprocess
import sys


# 模块级全局变量：用于统计本模块顶层代码被执行了几次。
# 这是观察"导入机制"最直接的手段，也是理解 Python 模块生命周期的最佳切入点。
TOP_LEVEL_EXECUTION_COUNT = 0


def top_level_code_that_runs_once():
    """模拟模块顶层的"一次性初始化"工作。

    函数名暗示了它的预期行为：无论被 import 多少次，这个函数体只会在
    模块首次加载时执行一次。
    """
    global TOP_LEVEL_EXECUTION_COUNT
    TOP_LEVEL_EXECUTION_COUNT += 1
    print(f"    [顶层代码] 第 {TOP_LEVEL_EXECUTION_COUNT} 次执行")
    print("    [顶层代码] 这里通常放：加载配置、建立连接、注册表项")


def demonstrate_name_value():
    """【语法解析】__name__ 的取值机制。

    【语法规则】
      __name__ 是模块对象上的一个特殊属性，解释器在创建模块时自动注入。
      它不是关键字，也不是内置函数，只是一个普通的模块全局变量。

    【取值规则】
      情况 A：直接运行 python 03_script_vs_module.py
              -> 解释器把模块命名为 '__main__'，故 __name__ == '__main__'
      情况 B：被其他文件 import
              -> __name__ == 模块名（如 'my_module'，不含 .py 后缀）
      情况 C：python -m 包.模块
              -> __name__ == 模块的完整点分名（如 'pkg.mod'）

    【执行顺序】
      解释器创建模块对象 -> 注入 __name__ -> 编译并执行模块顶层代码。
      也就是说 __name__ 在顶层第一行代码执行前就已经存在，
      所以它可以安全地写在文件最开头做守卫。

    【设计意图】
      CPython 把"入口模块"特殊命名为 __main__，源于 1991 年的 UNIX 传统：
      UNIX 启动一个程序时，argv[0] 就是程序名，而解释器需要区分
      "我是被启动的那个"还是"我是被别人需要的"。
      2008 年 PEP 302 引入绝对导入时，官方意识到许多模块既想当库又想当脚本，
      于是把这个约定正式写进语言文档，成为事实标准。

    【易错点】
      - 在子进程里 sys.argv[0] 才是脚本路径，__name__ 不是。
      - 用 exec(open(...).read()) 执行代码时 __name__ 保持调用者的值，不变。
      - Jupyter/交互式解释器中 __name__ 也是 '__main__'，所以守卫会失效（这正是
        Jupyter 里直接调用函数会触发整段逻辑的原因）。
    """
    print("[1] __name__ 的取值")
    print(f"    __name__ = {__name__!r}")
    print(f"    是否为主入口 = {__name__ == '__main__'}")

    # sys.argv[0] 是脚本路径（直接运行时）或模块路径（-m 时），与 __name__ 语义不同
    print(f"    sys.argv[0] = {sys.argv[0]!r}")
    print(f"    __file__    = {globals().get('__file__', '<交互式模式无此属性>')!r}")

    # 直接运行时 __spec__ 为 None（没有"以模块被导入"的加载规格），
    # 只有通过 -m 或 import 加载时它才是一个 ModuleSpec 对象。必须判空再用。
    spec = globals().get("__spec__")
    if spec is not None:
        print(f"    __spec__.name = {spec.name!r}  (-m 运行时为完整点分名)")
    else:
        print("    __spec__ = None  (直接运行脚本时没有模块加载规格)")


def demonstrate_three_ways():
    """【语法解析】直接运行 vs 导入的输出差异。

    【语法规则】
      方式 1：python 03_script_vs_module.py      -> 直接运行
      方式 2：python 03_script_vs_module.py      -> 被 import（工作目录需在 sys.path）
      方式 3：python -m 03_script_vs_module      -> 以模块方式运行

    【执行顺序差异】
      方式 1：__name__ == '__main__'，main() 被调用，产生完整业务输出
      方式 2：__name__ == 模块名，main() 不被调用，只执行顶层定义，输出极少
      方式 3：__name__ == '03_script_vs_module'，守卫同样不触发

    【为什么 -m 会改变 sys.path[0]]
      直接运行脚本时，sys.path[0] = 脚本所在目录。
      使用 -m 时，sys.path[0] = 当前工作目录（CWD）。
      这决定了"同目录的兄弟模块能否被导入"，是打包与测试中偶发 ImportError 的根因。
    """
    print("[3] 三种执行方式对照")

    modes = [
        ("python 03_script_vs_module.py", "直接运行", "'__main__'", "main() 会执行"),
        ("import 03_script_vs_module", "被导入", "模块名", "main() 不执行"),
        ("python -m 03_script_vs_module", "模块方式", "完整点分名", "main() 不执行"),
    ]
    print(f"    {'命令':<38} {'方式':<8} {'__name__':<14} 结果")
    for cmd, kind, name, effect in modes:
        print(f"    {cmd:<38} {kind:<8} {name:<14} {effect}")

    print(f"    当前实际 sys.path[0] = {sys.path[0]}")
    print(f"    当前实际 CWD        = {os.getcwd()}")
    print(f"    两者相同={sys.path[0] == os.getcwd()}  (不同则说明是用 -m 或以包方式运行)")


def demonstrate_import_cache():
    """【语法解析】导入缓存 —— 为什么顶层代码只执行一次。

    【语法规则】
      sys.modules 是「模块名 -> 模块对象」的全局字典。
      import 的第一步永远是查这个字典。

    【执行顺序】
      import foo 时：
        1) 查 sys.modules['foo']
           - 命中 -> 直接返回缓存对象，顶层代码【不再执行】
           - 未命中 -> 走文件查找流程，编译执行顶层代码，然后写入 sys.modules
      2) 写入 sys.modules 的时机是【执行顶层代码之前】（CPython 3.3+），
           这样即使模块内部 import 了自己（循环导入场景），也不会无限递归，
           而是拿到一个尚未初始化完成的模块对象。

    【设计意图】
      导入应该是幂等的（idempotent）—— 这一条约束催生了大量工程规范：
      - 绝不在模块顶层写文件、发网络请求（会重复触发或污染导入者）
      - 副作用全部放进函数，由 __main__ 守卫显式调用
      - 重载模块需用 importlib.reload()，因为缓存不会自动失效

    【循环导入的实际后果】
      A import B，B 也 import A 时：
      A 尚未执行到 import B -> B 开始执行 -> B 里 import A 命中缓存，
      拿到"只有变量定义、还没执行到函数定义"的 A。
      若 B 在模块顶层就调用 A 的函数，会抛 AttributeError / NameError。
    """
    print("[4] 导入缓存机制")
    print(f"    sys.modules 条目数 = {len(sys.modules)}")

    # 打印部分内置模块名作为直观证据。内置模块（frozen）不占文件系统路径
    builtin_samples = [name for name in list(sys.modules) if name.startswith("builtins") or name.startswith("_io")]
    print(f"    内置模块样例 = {builtin_samples}")

    # 用 __file__ 判断模块来源类型
    this_file = globals().get("__file__")
    print(f"    本模块 __file__ = {this_file}")
    # 扩展模块（.pyd/.so）以 _ 开头的常见形式判断
    print(f"    sys.builtin_module_names 数量 = {len(sys.builtin_module_names)}")

    print("    -> 若本文件被 import 两次，下方顶层代码计数仍为 1，验证缓存生效：")
    print(f"    当前顶层执行次数 = {TOP_LEVEL_EXECUTION_COUNT}")


def demonstrate_relative_import():
    """【语法解析】__package__ 与相对导入。

    【语法规则】
      __package__ 保存模块所属的包名（PEP 366 引入）。
      - 直接运行单文件时：__package__ 为 ''（空字符串）或 None
      - 被包内导入时：__package__ 为所属包的点分名
      相对导入 `from . import x` 中的 `.` 就代表 __package__。

    【执行顺序】
      解释器在创建模块时同时确定 __package__，它决定了相对导入的基准目录。
      因此直接运行一个含相对导入的文件会抛 ImportError（attempted relative import
      with no known parent package）—— 这是初学者极常见的错误。

    【设计意图】
      PEP 328 引入相对导入，PEP 366 引入 __package__，共同解决了一个问题：
      库内部互相引用时，不该硬编码包的顶层名字。
      假设包 mypkg 改名，库内部所有 from mypkg import x 都要改；
      改成 from . import x 后，改名只需动包目录本身，包内部代码零改动。
    """
    print("[5] __package__ 与相对导入")
    pkg = globals().get("__package__")
    print(f"    __package__ = {pkg!r}")
    print(f"    可用相对导入 = {bool(pkg)}  (直接运行单文件时为 False)")

    if not pkg:
        print("    原因：直接运行单文件时，解释器无法确定归属包，")
        print("          故 `from . import x` 会抛 ImportError。这也是为什么")
        print("          带相对导入的模块必须通过 `python -m 包.模块` 运行。")

    # __spec__ 提供了模块的加载元信息，是 importlib 动态导入的依据
    spec = globals().get("__spec__")
    if spec is not None:
        print(f"    __spec__ 存在，origin = {spec.origin!r}")
        print(f"    __spec__.parent = {spec.parent!r}")


def run_subprocess_demo():
    """【语法解析】用子进程真实观测"被导入"时的行为。

    【语法规则】
      subprocess.run([...], capture_output=True, text=True)
      可执行文件用 sys.executable 而不是硬编码 'python'，
      保证子进程用的是同一个解释器（虚拟环境中尤其重要）。

    【设计意图】
      同一进程内无法既是"主模块"又是"被导入模块"，
      所以要观察导入态行为，唯一可靠的办法是开一个新进程。
      这也展示了工程上如何用标准库做无依赖的"冒烟测试"。
    """
    print("[2] 子进程实测：被导入时的 __name__")
    print(f"    解释器 = {sys.executable}")

    # -c 参数让子进程直接执行一段代码字符串
    code = "import importlib.util, sys; print('    子进程 __name__ =', repr(__name__))"

    try:
        # sys.executable 而不是 'python'：保证虚拟环境一致
        result = subprocess.run(
            [sys.executable, "-c", code],
            capture_output=True,  # 把 stdout/stderr 收成 bytes，避免污染当前终端输出
            text=True,             # 自动按默认编码解码为 str
            timeout=10,            # 防止子进程挂死导致父进程永久阻塞
            encoding="utf-8",
            errors="replace",      # 子进程输出编码不确定时的兜底策略
        )
        print(result.stdout.rstrip())
        if result.stderr:
            print(f"    子进程 stderr: {result.stderr.rstrip()}")

        # 再演示一次：把本文件当模块导入，看 __name__ 的另一面
        self_name = os.path.splitext(os.path.basename(__file__))[0]
        code2 = (
            f"import importlib, sys;"
            f"m = importlib.import_module('{self_name}');"
            f"print('    导入后 __name__ =', repr(m.__name__))"
        )
        result2 = subprocess.run(
            [sys.executable, "-c", code2],
            capture_output=True,
            text=True,
            timeout=10,
            encoding="utf-8",
            errors="replace",
            cwd=os.path.dirname(os.path.abspath(__file__)),
        )
        print(result2.stdout.rstrip())
        if result2.returncode != 0:
            print(f"    导入方式失败(returncode={result2.returncode}): {result2.stderr.rstrip()}")
    except (subprocess.TimeoutExpired, OSError) as e:
        # OSError 覆盖"解释器路径不存在"等系统级失败
        print(f"    子进程执行失败: {type(e).__name__}: {e}")

    print("    -> 对比可见：直接运行是 '__main__'，被导入是模块名，两者守卫结果不同")


def main():
    """主逻辑：只有通过 __main__ 守卫调用时才会执行。

    这正是本文件要演示的核心 —— 如果去掉文件末尾的守卫，
    任何 import 本文件的代码都会被迫打印这一大堆东西。
    """
    demonstrate_name_value()
    run_subprocess_demo()
    demonstrate_three_ways()
    top_level_code_that_runs_once()
    demonstrate_import_cache()
    demonstrate_relative_import()

    print("[6] 差异总结")
    print("    直接运行：__name__='__main__' -> main() 执行 -> 完整业务输出")
    print("    被导入  ：__name__=模块名     -> main() 不执行 -> 仅完成函数定义")
    print("    这就是守卫的意义：让一个文件同时胜任『程序』和『库』两种角色")
    print("[完成] 01_env/03_script_vs_module.py 运行结束")


# ============================================================================
# 语法解析：__main__ 守卫本身
# ============================================================================
# 【语法规则】
#   if __name__ == "__main__":
#       主逻辑
#
# 【关键字作用】
#   if 是关键字，__name__ 是变量，"__main__" 是字符串字面量，== 是比较运算符。
#   三个表达式构成一个布尔条件，解释器据其真假决定是否执行缩进块。
#
# 【执行顺序】
#   1) 解释器把 __name__ 与 "__main__" 做字符串相等比较（intern 后的指针比较，O(1)）
#   2) 为 True -> 执行 if 块；为 False -> 整个 if 块被跳过，直接往下
#   3) 跳过不等于"不解析"：整个文件仍被完整编译，顶层代码（import、函数定义、
#      类定义、赋值）仍然全部执行 —— 只有 if 块内的语句不执行。
#
# 【设计意图】
#   语言层面无法自动区分，所以选择给开发者一个显式开关。
#   代价是没有强制保护，一个没有守卫的库文件在导入时就会产生副作用；
#   收益是同一份代码不必为"当程序"和"当库"写两份。


if __name__ == "__main__":
    main()