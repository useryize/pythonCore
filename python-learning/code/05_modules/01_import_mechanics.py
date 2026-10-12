"""
================================================================================
 01_import_mechanics.py  ——  import 导入机制详解
================================================================================

【演示的语法点】
 1. import 的三种写法：import / from...import / from...import as
 2. sys.modules：模块缓存表，是"导入只执行一次"的根本原因
 3. 模块的 __name__ / __file__ / __doc__ / __spec__ 等特殊属性
 4. 导入路径机制：sys.path 的顺序、. 与 '' 的含义、模块搜索路径
 5. sys.modules 的读写与手动注册/删除模块
 6. 导入的三种风格：顶层导入 / 函数内延迟导入 / try-except 可选导入
 7. import 的执行时机：绑定名字，不是执行"调用"
 8. 为什么重复导入不会重复执行（对象 id 相同可验证）

【运行方式】
 必须在 05_modules 目录下运行，因为要导入同级的 myutils 包：
      cd 05_modules && python 01_import_mechanics.py

【预期输出摘要】
 - "模块缓存" 小节证明两次导入的模块对象 id() 完全相同
 - "导入路径" 小节打印 sys.path 各项含义
 - "三种写法" 小节打印各写法产生的绑定名
================================================================================

"""

from __future__ import annotations

import os
import sys
import time


# ===== 语法解析 =====
# 【语法 1】import 模块
#   语法规则：import 模块名[.子模块名]
#   语义：把【最左边的顶层包名】绑定到当前命名空间。
#   副作用：会【真正执行】被导入模块的顶层代码（用模块级对象缓存该结果）。
#   访问方式：包名.子模块.函数()
def demo_import_style() -> None:
    print("  ① import myutils.config")
    # import 只绑定 myutils 这个名字
    import myutils.config

    print(f"     绑定到当前命名空间的名字：{myutils}")
    print(f"     访问深层成员：{myutils.config.get('app_name')}")
    print(f"     为什么不能写 myutils.config.get(...) 之外的东西？")
    print(f"     因为 config 只是 myutils 模块对象的属性，需要逐级属性访问。")

    # ★ 常见坑：import a.b 之后直接用 b 会 NameError
    try:
        print(config)                  # type: ignore[name-defined]  # noqa: F821
    except NameError as exc:
        print(f"     ✗ 直接写 config 会 NameError: {exc}")
    print("     ✓ 正确写法二选一（都要先真正绑定名字）：")
    from myutils import config          # 写法一：显式绑定子模块名
    print(f"        from myutils import config → config.get('version') = "
          f"{config.get('version')}")
    import myutils.config as config_alias   # 写法二：import ... as 别名
    print(f"        import myutils.config as config_alias → "
          f"{config_alias.get('version')}")
    print(f"        或用全名 myutils.config.get(...) = {myutils.config.get('version')}")


# ===== 语法解析 =====
# 【语法 2】from ... import ...
#   语法规则：from 模块名 import 名字1[, 名字2, ...]
#   语义：把被导入模块中的【指定名字】绑定到当前命名空间。
#   注意：若要导入的是【子模块本身】，写 from 包 import 子模块。
def demo_from_import_style() -> None:
    print("  ② from myutils.math_tools import mean, median")
    from myutils.math_tools import mean, median

    print(f"     mean([1,2,3]) = {mean([1, 2, 3])}")
    print(f"     median([1,2,3,4]) = {median([1, 2, 3, 4])}")
    print(f"     当前命名空间新增了名字：mean, median")

    print()
    print("  ③ from myutils import math_tools（导入子模块对象本身）")
    from myutils import math_tools

    print(f"     math_tools 是模块对象：{math_tools}")
    print(f"     math_tools.is_prime(7) = {math_tools.is_prime(7)}")
    print("     两种 ②③ 的区别：② 绑函数，③ 绑模块。")


# ===== 语法解析 =====
# 【语法 4】as 别名
#   语法规则：from 模块名 import 名字 as 别名 / import 模块名 as 别名
#   用途：起别名（避免同名冲突）、缩短长路径。
def demo_alias_style() -> None:
    print("  ④ import ... as ... 起别名")
    import myutils.text_tools as tt

    print(f"     tt 是 {tt.__name__} 的别名：tt.clean_text(' a  b ') = "
          f"{tt.clean_text(' a  b ')!r}")

    # 起别名的意义：模块名和它的内部名字冲突时依然可用
    from myutils.config import get as config_get

    print(f"     from ... import get as config_get → config_get('debug') = "
          f"{config_get('debug')}")


# ===== 语法解析 =====
# 【核心机制】sys.modules —— 模块缓存表
#   原理（import 语句的完整执行流程）：
#     步骤 1：在 sys.modules 里查模块名。
#            命中 → 直接返回缓存的模块对象，【不再执行模块代码】；
#            未命中 → 继续步骤 2。
#     步骤 2：在 sys.path 的每个目录下找 模块名.py / 模块名/__init__.py。
#     步骤 3：找到后【创建】一个空的模块对象（module），此时它的 __dict__ 几乎为空。
#            ★ 关键：此刻立刻把它【插入】 sys.modules！
#              这一步是为了让模块内部自己 import 自身时能命中缓存，
#              从而打破无限递归（循环导入报错的根源就在这里）。
#     步骤 4：把模块的 __name__ 设为全名，记录 __file__ / __spec__。
#     步骤 5：【执行模块的顶层代码】，逐条产生全局名字。
#     步骤 6：从 sys.modules 取回模块对象，绑定到 import 语句左侧的名字。
#
#   设计意图：单例化模块对象 + 循环导入的可检测性。
def demo_module_cache() -> None:
    print("  ① sys.modules 中已有的本包模块：")
    my_keys = [k for k in sys.modules if k.startswith("myutils")]
    print(f"     {my_keys}")
    print(f"     当前共缓存了 {len(sys.modules)} 个模块（含标准库）")

    print()
    print("  ② 重复导入的证据：对象是同一个（id 相同）")
    import myutils.config as c1
    import myutils.config as c2
    from myutils import config as c3

    print(f"     c1 是 c2 吗：{c1 is c2}")
    print(f"     c1 是 c3 吗：{c1 is c3}")
    print(f"     id(c1)={id(c1)}")
    print(f"     id(c2)={id(c2)}")
    print(f"     id(c3)={id(c3)}")
    print(f"     sys.modules['myutils.config'] 是 c1 吗："
          f"{sys.modules['myutils.config'] is c1}")
    print("     → 导入语句只执行一次模块代码，之后都是命中缓存。")

    print()
    print("  ③ 模块对象的特殊属性：")
    print(f"     __name__    = {c1.__name__!r}")
    print(f"     __file__    = {c1.__file__!r}")
    print(f"     __doc__     = {(c1.__doc__ or '')[:40]!r}...")
    print(f"     __package__ = {c1.__package__!r}")
    print(f"     __spec__    = {c1.__spec__.name!r}")
    print(f"     __dict__ 键 = {sorted(c1.__dict__)[:8]}")

    print()
    print("  ④ 用对象 id 证明模块顶层代码只执行一次：")
    # config 模块里的 _settings 是模块级变量，
    # 如果重复导入会重新执行，那这个列表的 id 就会变
    import myutils.config as c4
    print(f"     再次导入后 config._settings 的 id = {id(c4._settings)}")
    print(f"     与第一次相同：{id(c4._settings) == id(c1._settings)}")


# ===== 语法解析 =====
# 【核心机制】导入路径 sys.path
#   语法/规则：
#     - sys.path 是一个【列表】，Python 按顺序逐个目录查找模块。
#     - 运行脚本时，【脚本所在目录】会被自动放到 sys.path[0]。
#     - 交互式解释器(sys.path[0] == '') 用的是当前工作目录。
#     - 其余路径来自 PYTHONPATH 环境变量和标准库/第三方库的安装位置。
#   设计意图：让"模块放在哪都能被找到"，同时支持覆盖同名标准库模块
#   （把自定义文件放在 sys.path 前面即可覆盖同名模块 —— 既是特性也是陷阱）。
def demo_import_path() -> None:
    print(f"  脚本所在目录（sys.path[0]）：{sys.path[0]!r}")
    print(f"  当前工作目录 os.getcwd()：{os.getcwd()!r}")
    print(f"  sys.path 共 {len(sys.path)} 项，前 5 项：")
    for i, p in enumerate(sys.path[:5]):
        kind = ""
        if p == "" or p == ".":
            kind = "  ← 交互式：当前工作目录"
        elif p.startswith(sys.prefix):
            kind = "  ← Python 标准库/安装目录"
        print(f"    [{i}] {p!r}{kind}")
    print()
    print("  ★ 推论：")
    print("    1) 必须在本目录运行本文件，sys.path[0] 才会是 05_modules，")
    print("       myutils 才能被找到；换个目录运行就会 ModuleNotFoundError。")
    print("    2) 往 sys.path 里 `append` 而非 `insert(0, ...)`，")
    print("       可以避免自己的模块意外覆盖标准库同名模块。")
    print(f"    3) __file__ 是绝对路径：{__file__!r}")
    print(f"    4) __name__ = {__name__!r}  ← 因为是直接运行，所以是 __main__")


# ===== 语法解析 =====
# 【核心机制】__name__ == "__main__" 的作用
#   规则：
#     - 直接运行某个文件 → 该文件的 __name__ 是 "__main__"
#     - 该文件被别的模块导入 → __name__ 是它的模块全名（如 "myutils.config"）
#   意义：这是区分"文件是程序入口"还是"文件是可复用模块"的唯一可靠依据。
#   若没有这个守卫，导入模块时其测试代码/打印会意外执行。
def demo_name_mechanism() -> None:
    import myutils.config as cfg

    print(f"  当前文件 __name__ = {__name__!r}  （直接运行 → __main__）")
    print(f"  被导入模块 __name__ = {cfg.__name__!r}  （导入 → 模块全名）")
    print()
    print("  所以 config.py 里的 `if __name__ == \"__main__\":` 判断为假，")
    print("  它的自测代码【不会】被执行 —— 这就是导入守卫的意义。")
    print(f"  验证：'__main__' == {cfg.__name__} ? {'__main__' == cfg.__name__}")


# ===== 语法解析 =====
# 【导入风格】三种常见写法的取舍
#   风格 A：模块顶层导入 —— 简单直观，但会拖慢启动（导入即执行）
#   风格 B：函数内延迟导入 —— 解决循环导入 / 减少启动开销 / 可选依赖
#   风格 C：try-except 可选导入 —— 处理"依赖没装"的优雅降级
def demo_import_styles() -> None:
    print("  风格 A：顶层导入（本文件顶部就是这么做的）")
    print("     优点：代码简洁，模块级名字一眼可见")
    print("     缺点：import myutils 时会连带执行全部子模块代码")

    print()
    print("  风格 B：函数内延迟导入")
    def lazy_need_math() -> str:
        # 只在真正调用时才导入 —— 循环导入的常用解法之一
        import myutils.math_tools as m
        return str(m.is_prime(13))
    print(f"     调用前 sys.modules 有 math_tools 吗："
          f"{'myutils.math_tools' in sys.modules}")
    print(f"     lazy_need_math() = {lazy_need_math()}")
    print(f"     调用后有吗：{'myutils.math_tools' in sys.modules}")
    print("     优点：不拖累启动 / 可打破循环导入；缺点：每次调用查一次字典（可忽略）")

    print()
    print("  风格 C：try-except 可选导入")
    try:
        import numpy as np  # type: ignore[import-not-found]
        HAS_NUMPY = True
    except ImportError:
        # 依赖缺失时优雅降级，而不是让整个程序崩掉
        HAS_NUMPY = False
        np = None            # type: ignore[assignment]
    print(f"     numpy 是否可用：{HAS_NUMPY}")
    print("     优点：可选依赖不装也能跑；缺点：需为缺失分支写降级逻辑")


# ===== 语法解析 =====
# 【进阶】手动操作 sys.modules
#   - 删除某个模块：del sys.modules['x'] → 下次 import 会【重新执行】模块代码
#     （常用于修改模块文件后热重载、单元测试中重置模块状态）
#   - 手动注册：sys.modules['alias'] = mod，实现"模块别名"
def demo_manual_sys_modules() -> None:
    import myutils.math_tools as m

    print(f"  ① 模块在缓存中的键名：{[k for k in sys.modules if 'math_tools' in k]}")
    print(f"     注意键是【全名】'myutils.math_tools'，而不是 'math_tools'")

    print()
    print("  ② 手动创建别名（不复制模块，只是多绑一个名字）：")
    sys.modules["myutils.math"] = m          # type: ignore[assignment]
    import myutils.math as alias_mod
    print(f"     import myutils.math as alias_mod → {alias_mod}")
    print(f"     alias_mod 是同一个对象吗：{alias_mod is m}")
    print("     ★ 技巧：这不是真的 'myutils.math' 子模块，只是 sys.modules 的别名项")
    print(f"     它的 __name__ 仍是 {alias_mod.__name__!r}（不会变）")
    del sys.modules["myutils.math"]         # 清理，避免污染后续演示

    print()
    print("  ③ 删除缓存以强制重新执行模块代码（热重载原理）：")
    key = "myutils.config"
    old_id = id(sys.modules[key])
    print(f"     删除前 id = {old_id}")
    del sys.modules[key]
    print(f"     删除后 '{key}' 还在 sys.modules 吗：{key in sys.modules}")
    import myutils.config as reloaded
    print(f"     重新导入后 id = {id(reloaded)}（与删除前不同 → 模块被重新执行了）")
    print(f"     注意：myutils.config 这个属性仍指向【旧的】模块对象，")
    print(f"           因为父包 myutils 的 __dict__ 还缓存着旧引用。")


# ===== 语法解析 =====
# 【导入的等价展开】
#   `import a.b.c` 在运行期等价于：
#     1) import a; import a.b; import a.b.c  （逐层导入，每层都触发 __init__.py）
#     2) sys.modules['a.b.c']  → 绑定名字 a
#   `from a.b import c` 等价于：
#     1) import a.b
#     2) 从 sys.modules['a.b'].__dict__ 里取 c，绑定到当前命名空间
#     3) 若 __dict__ 里没有 c → 抛 ImportError（名字不存在，不是模块不存在）
def demo_import_equivalence() -> None:
    print("  import myutils.text_tools 的等价展开：")
    print("    ① 确保 myutils 已导入 → 执行 myutils/__init__.py")
    print("    ② 确保 myutils.text_tools 已导入 → 执行 text_tools.py")
    print("    ③ 执行 myutils.text_tools = sys.modules['myutils.text_tools']")
    print()
    print("  逐步验证：")
    import myutils
    print(f"    导入 myutils 后，其下已加载："
          f"{[k for k in sys.modules if k.startswith('myutils.')]}")
    print(f"    myutils.text_tools 是否已被绑定：{hasattr(myutils, 'text_tools')}")
    print("    → 说明顶层 `from . import text_tools` 已经把子模块绑到包上了")

    print()
    print("  from X import Y 的两种失败（错误信息不同）：")
    try:
        from myutils import 不存在的名字
    except ImportError as exc:
        print(f"    模块存在但名字不存在 → ImportError: {exc}")
    try:
        from myutils import no_such_module
    except ImportError as exc:
        print(f"    子模块不存在     → ImportError: {str(exc)[:60]}")


def main() -> None:
    print("=" * 60)
    print("【0】环境信息")
    print("=" * 60)
    print(f"  Python 版本：{sys.version.split()[0]}")
    print(f"  当前文件   ：{__file__}")
    print(f"  当前 __name__：{__name__}")
    print(f"  当前工作目录：{os.getcwd()}")
    print(f"  解释器     ：{sys.executable}")

    print()
    print("=" * 60)
    print("【1】import 的三种写法")
    print("=" * 60)
    demo_import_style()
    demo_from_import_style()
    demo_alias_style()

    print()
    print("=" * 60)
    print("【2】★ sys.modules 模块缓存（导入只执行一次的原因）")
    print("=" * 60)
    demo_module_cache()

    print()
    print("=" * 60)
    print("【3】导入路径 sys.path")
    print("=" * 60)
    demo_import_path()

    print()
    print("=" * 60)
    print("【4】__name__ 与导入守卫")
    print("=" * 60)
    demo_name_mechanism()

    print()
    print("=" * 60)
    print("【5】三种导入风格")
    print("=" * 60)
    demo_import_styles()

    print()
    print("=" * 60)
    print("【6】手动操作 sys.modules")
    print("=" * 60)
    demo_manual_sys_modules()

    print()
    print("=" * 60)
    print("【7】import 语句的等价展开")
    print("=" * 60)
    demo_import_equivalence()

    print()
    print("=" * 60)
    print("【小结】导入机制四个要点")
    print("=" * 60)
    print("  1. import 绑定的名字 = 语句最左侧的名字")
    print("  2. sys.modules 是唯一真相来源，命中即复用，不重复执行")
    print("  3. 模块执行前就被放入 sys.modules（这正是循环导入会报错的原因）")
    print("  4. __name__ == '__main__' 用于区分入口与模块")


if __name__ == "__main__":
    main()