"""
================================================================================
 myutils/__init__.py  ——  包的入口与门面（Facade）
================================================================================

【包的 __init__.py 到底做什么？】
 1. 【标识包的存在】—— 一个目录有 __init__.py 才是"包"（传统定义）。
    （注：Python 3.3+ 的命名空间包可不带 __init__.py，但生产项目仍应添加）
 2. 【定义包的公开 API】—— 用 __all__ 声明"对外暴露哪些名字"，
    影响 from myutils import * 的行为。
 3. 【统一再导出】—— 把子模块的函数"提到"包层面，
    使用者只需 from myutils import mean，不必关心它在哪个子模块。
    这就是【门面(Facade)模式】。
 4. 【执行包级初始化代码】—— 常用于注册组件、设置包级常量、
    检查依赖版本等。
 5. 【控制命名空间污染】—— 子模块之间可以互相导入私有名字，
    而不会泄漏到包的使用者面前。

【导入机制关键点】
 - 执行 myutils/__init__.py 时，import 语句会把包名 myutils 绑定到当前命名空间，
   并在 sys.modules 中注册 "myutils" → <module myutils>。
 - __init__.py 中【自带的 import 语句会被执行】，这是"导入包会触发子模块加载"的原因。
 - ★ 顺序陷阱：如果 __init__.py 顶部就 import 了某个会循环引用本包的子模块，
   会直接触发 ImportError。本包特意把导入放在 __init__.py 内部函数里（惰性导入），
   原因见 03_circular_import.py。

【预期输出摘要】
 - 直接运行本文件会打印门面聚合后的函数清单
================================================================================

"""

from __future__ import annotations

__version__ = "1.0.0"          # 包级常量：版本号
__author__  = "Python 学习体系"
# 包级文档字符串（本段注释已在文件顶部，这里用变量保存"长描述"）
__doc__ += """
本包提供三类工具：
  - text_tools：文本清洗、词频、命名风格转换
  - math_tools：统计、质数、几何
  - config   ：分层配置管理
"""

# ===== 语法解析 =====
# 【1】__all__ 的作用
#   语法：__all__ = ["名字1", "名字2", ...]
#   作用一：from myutils import * 只导入 __all__ 里列出的名字。
#   作用二：向使用者明确"这些才是本包的公开 API"。
#   注意：__all__ 本身不会被 import（名字以下划线开头属于私有）。
__all__ = [
    # 子模块（把模块对象本身也暴露出去，支持 myutils.config 访问）
    "text_tools",
    "math_tools",
    "config",
    # 从子模块再导出的常用函数（门面模式）
    "mean",
    "median",
    "is_prime",
    "clean_text",
    "camel_to_snake",
    "get_config",
]


# ===== 语法解析 =====
# 【2】导入子模块的三种写法对比
#   写法 A：import myutils.text_tools
#         → 名字 myutils 被绑定；访问要用 myutils.text_tools.func()（长）
#   写法 B：from myutils import text_tools
#         → text_tools 被直接绑定到当前命名空间；访问 text_tools.func()（短）
#   写法 C：from myutils.text_tools import clean_text
#         → 直接把函数绑定过来；调用最简洁，但丢失了"来源模块"信息
#   ★ 关键区别：C 中 sys.modules 里依然会注册 myutils 和 myutils.text_tools，
#     只是当前命名空间的绑定方式不同。三者都会真正执行一次模块代码。
from . import text_tools, math_tools, config
# 注意开头的点：这是相对导入，含义是"从当前包（myutils）导入"。
# 等价于 from myutils import text_tools, math_tools, config（绝对导入）。

from .text_tools import clean_text, camel_to_snake
from .math_tools import mean, median, is_prime
from .config import get as get_config     # ★ as 起别名，避免与用户自己的 get 冲突


# ===== 语法解析 =====
# 【3】包级函数：门面再封装
#   设计意图：对外只暴露"业务语义"清晰的接口，内部实现可以自由重构。
def get_info() -> dict[str, object]:
    """返回本包的基本信息，便于自检。"""
    # 注意访问子模块用【全名】myutils.text_tools 而不是 text_tools，
    # 这样即使本模块内的局部名字被覆盖也不受影响。
    return {
        "name": __name__,              # 恒为 "myutils"
        "version": __version__,
        "author": __author__,
        "公开API": __all__,
        "已加载子模块": _loaded_modules(),
    }


def _loaded_modules() -> list[str]:
    """列出已成功导入的子模块。私有函数（_ 前缀），不在 __all__ 里。"""
    # 用 name 属性判断是否为包（本包的模块都有 __path__）
    return [
        name for name in ("text_tools", "math_tools", "config")
        if _module_in_sysmodules(f"myutils.{name}")
    ]


def _module_in_sysmodules(full_name: str) -> bool:
    """检查某模块是否在 sys.modules 中。避免 import sys 带来的额外耦合。"""
    import sys                # ★ 局部导入：只在函数内部需要时才导入
    return full_name in sys.modules


# ===== 语法解析 =====
# 【4】包级演示函数
def demo() -> None:
    """一次性演示本包的主要能力。放在函数里而非模块顶层，
    避免"导入包就打印"的副作用。"""
    print("--- myutils 包能力演示 ---")
    print(f"[文本] clean_text('  Hello,  Python!  ') = "
          f"{clean_text('  Hello,  Python!  ')!r}")
    print(f"[文本] camel_to_snake('getUserName')   = {camel_to_snake('getUserName')}")
    print(f"[数学] mean([1, 2, 3, 4, 5])            = {mean([1, 2, 3, 4, 5])}")
    print(f"[数学] median([1, 2, 3, 4])             = {median([1, 2, 3, 4])}")
    print(f"[数学] is_prime(97)                     = {is_prime(97)}")
    print(f"[配置] get_config('app_name')           = {get_config('app_name')}")
    print(f"[配置] get_config('database.port')     = {get_config('database.port')}")
    print("--- 演示结束 ---")


if __name__ == "__main__":
    # 直接运行 myutils/__init__.py 时，包内相对导入通常不可用
    # （因为此时 myutils 不在 sys.path 的包搜索上下文中），
    # 因此这里只打印基础信息，不调用依赖子模块的功能。
    print(f"__name__      = {__name__}")
    print(f"__version__   = {__version__}")
    print(f"__author__    = {__author__}")
    print(f"__all__ 长度  = {len(__all__)}")
    print(f"公开 API      = {__all__}")
    print("提示：包文件请通过 `python -c \"import myutils; myutils.demo()\"` "
          "或导入使用，而非直接运行。")