"""
================================================================================
 02_package_demo.py  ——  包（package）的组织与导入
================================================================================

【演示的语法点】
 1. 什么是包：__init__.py 的作用与包命名空间
 2. 包内导入：from . import X（相对一级）、from .. import X（相对二级）
 3. ★ 相对导入 vs 绝对导入：语法、语义、适用场景对比
 4. __all__ 的精确作用（影响 from 包 import *，不影响其他导入方式）
 5. 包中模块的加载顺序：__init__.py 顶层 import 会连带触发子模块
 6. 包的命名空间与属性访问 myutils.config
 7. __init__.py 的四种典型用途
 8. import * 的危害与 __all__ 的治理作用
 9. 子包（多级包）的导入

【运行方式】
 必须在 05_modules 目录下运行：
      cd 05_modules && python 02_package_demo.py

【预期输出摘要】
 - 相对/绝对导入对比小节打印两种写法的等价性
 - __all__ 小节对比 import * 前后当前命名空间新增的名字数量
================================================================================

"""

from __future__ import annotations

import sys


# ===== 语法解析 =====
# 【1】什么是包
#   定义：一个包含 __init__.py 的目录被视为"常规包(regular package)"。
#   作用：
#     (a) 让目录内各模块共享一个命名空间（访问时带包名前缀，避免全局污染）
#     (b) 通过 __init__.py 执行包级初始化逻辑
#     (c) 通过 __all__ 精确声明公开 API
#   补充：Python 3.3+ 支持"命名空间包"（无 __init__.py 的目录），
#         但无法执行 __init__.py 逻辑，工程上应始终添加 __init__.py。
def demo_what_is_package() -> None:
    import myutils

    print(f"  myutils 的类型：{type(myutils)}")
    print(f"  myutils.__name__ = {myutils.__name__!r}")
    print(f"  myutils.__file__ = {myutils.__file__!r}")
    print(f"  myutils.__path__ = {myutils.__path__}")
    print()
    print("  关键：__path__ 是【包特有的属性】，普通模块没有。")
    print("        它是一个列表，装着包所在目录的路径 —— 这就是解释器")
    print("        在包内继续查找子模块的依据。所以只有包才能有子模块。")
    print()
    print(f"  包对象上已绑定的子模块：")
    for attr in ("text_tools", "math_tools", "config"):
        sub = getattr(myutils, attr)
        print(f"    myutils.{attr:<12} → {sub.__name__!r}  (来自 {sub.__file__.split(chr(92))[-1]})")
    print()
    print("  这三个子模块之所以在 import myutils 后就存在，")
    print("  是因为 __init__.py 顶层写了 `from . import text_tools, math_tools, config`。")


# ===== 语法解析 =====
# 【2】包内导入：相对导入
#   语法规则：
#     from . import x        → 从【当前包】导入 x（1 个点 = 同级）
#     from .mod import x     → 从当前包的 mod.py 导入 x
#     from .. import x       → 从【父包】导入 x（2 个点 = 上级）
#     from ..pkg.mod import x→ 从祖父包的 pkg.mod 导入
#     from ... import x      → 3 个点 = 再上一级
#   语义：开头的点数决定"相对于哪个包层级"，由【当前模块的 __package__】决定起点。
#   ★ 相对导入【只能在包内使用】：直接运行 myutils/text_tools.py 时
#     （__package__ 为空/None）用 from . import x 会 ImportError
#     "attempted relative import with no known parent package"。
def demo_relative_import() -> None:
    import myutils

    print("  myutils/__init__.py 中使用的是：")
    print("    from . import text_tools, math_tools, config")
    print("  等价于（绝对导入写法）：")
    print("    from myutils import text_tools, math_tools, config")
    print()
    print(f"  验证结果一致：{myutils.math_tools.is_prime(11) == True}")
    print()
    print("  当前脚本 02_package_demo.py 本身就在包【外面】（无 __init__.py 的目录），")
    print("  所以它【不能】使用相对导入 —— 相对导入需要 __package__ 有值。")
    print(f"  本模块 __package__ = {__package__!r}  → 空字符串，说明不在包内")


# ===== 语法解析 =====
# 【3】★ 相对导入 vs 绝对导入（重点对比）
#   ┌──────────────┬────────────────────────┬────────────────────────┐
#   │     维度     │      相对导入           │      绝对导入           │
#   ├──────────────┼────────────────────────┼────────────────────────┤
#   │ 语法         │ from .x import y        │ from pkg.mod import y  │
#   │ 起点         │ 当前模块的 __package__  │ sys.path（从根开始搜索）│
#   │ 可移植性     │ 包改名/挪位置不用改代码  │ 改了包名所有引用都要改   │
#   │ 依赖 sys.path│ 不依赖（只需能在包内）  │ 依赖                    │
#   │ 直接运行文件 │ 不可用（会报错）        │ 可用                    │
#   │ 可读性       │ 一眼看出"同包内引用"    │ 一眼看出"来自哪个包"    │
#   └──────────────┴────────────────────────┴────────────────────────┘
#   ★ 工程惯例：**包内部一律用相对导入**（抗重构），**外部引用包时用绝对导入**。
def demo_relative_vs_absolute() -> None:
    # 绝对导入：写出完整包路径
    from myutils.math_tools import mean as abs_mean
    print(f"  绝对导入 from myutils.math_tools import mean → {abs_mean([1, 2, 3])}")
    print("     优点：清楚表明来自哪个包，IDE 可跳转，重命名工具友好")
    print("     缺点：包一改名，全仓库所有引用都要改")

    # 通过包对象访问（等价于绝对导入的一种形式）
    import myutils
    pkg_mean = myutils.math_tools.mean([1, 2, 3])
    print(f"  包对象属性访问 myutils.math_tools.mean → {pkg_mean}")
    print("     这也是绝对导入：myutils 名字来自 import myutils")
    print()
    print("  对比：包内部的 __init__.py 用的是相对导入 from . import xxx")
    print("        包的使用者用的是绝对导入 from myutils import xxx")
    print("  原因：包内部对包名不该有硬依赖，否则包一改名就全线崩溃。")

    print()
    print("  ★ 反例演示：直接运行包内模块时，相对导入会失败")
    print("     （把下面这行取消注释，会看到 ImportError）")
    print("       cd myutils && python -c \"from . import math_tools\"")
    print("     报错信息：ImportError: attempted relative import with no known parent package")


# ===== 语法解析 =====
# 【4】__all__ 的精确作用
#   作用范围【仅限】`from 包 import *` 这一种写法。
#   ┌──────────────────────────────┬──────────────────────────────┐
#   │ 语句                         │ 是否受 __all__ 影响           │
#   ├──────────────────────────────┼──────────────────────────────┤
#   │ from myutils import mean     │ 否，按名字精确导入             │
#   │ import myutils               │ 否，导入整个模块对象           │
#   │ import myutils.math_tools    │ 否                            │
#   │ from myutils import *        │ ✓ 是！只导入 __all__ 里的名字   │
#   │ from myutils.math_tools import *│ 是（子模块自己的 __all__）   │
#   └──────────────────────────────┴──────────────────────────────┘
#   ★ 若未定义 __all__，`import *` 会导入所有【不以 _ 开头】的名字。
def demo_dunder_all() -> None:
    import myutils

    print(f"  myutils.__all__ = {myutils.__all__}")
    print(f"  长度 = {len(myutils.__all__)}")

    print()
    print("  ① 精确导入（不受 __all__ 限制）：")
    from myutils import mean
    print(f"     from myutils import mean → {mean([10, 20])}")

    print()
    print("  ② 导入非 __all__ 中的名字也能成功：")
    # get_info 在 __all__ 里，但 show_version 不在 —— 只要不写 import * 就没事
    from myutils import get_info
    print(f"     from myutils import get_info → 版本 {get_info()['version']}")
    print("     → 因为精确导入走的是模块 __dict__，与 __all__ 无关")

    print()
    print("  ③ import * 的对比实验（在独立命名空间里做，避免污染本模块）：")
    public_ns: dict[str, object] = {}
    private_ns: dict[str, object] = {}
    # 用 exec 在受控字典中执行 import *，这是观察 import * 副作用的标准手段
    exec("from myutils import *", public_ns)          # noqa: S102  教学演示用途
    # 对比：不给 __all__ 的模块（math_tools 没有定义 __all__）
    exec("from myutils.math_tools import *", private_ns)  # noqa: S102
    # exec 会自动注入 __builtins__，要剔除才是"真正被导入的名字"
    pub_names = sorted(k for k in public_ns if not k.startswith("__"))
    math_names = sorted(k for k in private_ns if not k.startswith("__"))
    print(f"     from myutils import * 导入了 {len(pub_names)} 个名字：")
    print(f"       {pub_names}")
    print(f"     from myutils.math_tools import * 导入了 {len(math_names)} 个名字（无 __all__ → 全部非下划线名）")
    print(f"       {math_names}")
    print()
    print("     结论：")
    print("       - myutils 有 __all__ → 严格按列表导入，控制精准")
    print("       - math_tools 无 __all__ → 导入所有非下划线名字（连 in_range 也被导入了）")
    print("     这就是为什么成熟包一定要写 __all__：控制命名空间污染。")
    print(f"     注意 math_tools 里被'意外导出'的 in_range："
          f"{'in_range' in math_names} —— 它本该是私有辅助工具")


# ===== 语法解析 =====
# 【5】__init__.py 的四种典型用途
#   (a) 标识包的存在
#   (b) 定义包的公开 API（__all__ + 再导出）
#   (c) 执行包级初始化（注册组件、检查依赖版本、设置常量）
#   (d) 提供包级函数（demo/get_info 这类聚合入口）
def demo_init_py_roles() -> None:
    import myutils

    print("  (a) 标识包：__file__ 指向 __init__.py")
    print(f"      {myutils.__file__}")
    print()
    print("  (b) 定义公开 API：")
    print(f"      __all__ 共 {len(myutils.__all__)} 项，覆盖 3 个子模块 + 6 个函数")
    print()
    print("  (c) 初始化常量：")
    print(f"      __version__ = {myutils.__version__}")
    print(f"      __author__  = {myutils.__author__}")
    print()
    print("  (d) 包级聚合函数：")
    info = myutils.get_info()
    for key, value in info.items():
        print(f"      {key} = {value}")
    print()
    print("  ★ 反面教材：如果在 __init__.py 顶层写 print()，")
    print("    那么任何人 `import myutils` 都会看到这行输出 —— 属于糟糕的副作用。")
    print("    正确做法：把演示逻辑放进 demo() 函数，由用户主动调用。")
    print()
    print("  调用 myutils.demo() 看看：")
    myutils.demo()


# ===== 语法解析 =====
# 【6】import 的加载顺序：__init__.py 的连锁效应
#   执行 `import myutils` 时：
#     ① 把空模块对象放入 sys.modules['myutils']
#     ② 执行 __init__.py 的顶层代码
#     ③ 顶层遇到 `from . import text_tools` → 触发 text_tools.py 的加载与执行
#     ④ text_tools 执行完毕后，把模块对象设为 myutils.text_tools 属性
#     ⑤ __init__.py 全部执行完，导入才结束
#   ★ 这意味着：__init__.py 的 import 语句决定了"导入这个包要付出多大代价"。
#     一个只有常量定义的包 vs 一个顶层导入 20 个子模块的包，启动速度天差地别。
def demo_load_order() -> None:
    import myutils

    print("  sys.modules 中 myutils 相关条目（按插入顺序）：")
    keys = [k for k in sys.modules if k.startswith("myutils")]
    for k in keys:
        print(f"    {k}")
    print()
    print("  加载链：myutils → myutils.text_tools / myutils.math_tools / myutils.config")
    print()
    print("  每个模块对象都有独立的 __dict__（各自的全局命名空间）：")
    import myutils.config as cfg
    import myutils.math_tools as mt
    print(f"    config.__dict__ 独有 {len(cfg.__dict__)} 个名字")
    print(f"    math_tools.__dict__ 独有 {len(mt.__dict__)} 个名字")
    print(f"    两者交集（共享的构建内名字）：{set(cfg.__dict__) & set(mt.__dict__)}")
    print("    → 模块之间【不共享】全局命名空间，这是模块封装的根本。")


# ===== 语法解析 =====
# 【7】多级包（子包）的导入
#   如果目录嵌套更深，如 pkg/sub/inner.py，则包名是 pkg.sub。
#   每一级都必须有 __init__.py。
#   本节通过临时创建一个两级包来真实演示。
def demo_subpackage() -> None:
    import os
    import tempfile

    # 在临时目录里造一个两级包，避免污染本项目
    tmp = tempfile.mkdtemp(prefix="pkgdemo_")
    outer = os.path.join(tmp, "shop")
    inner = os.path.join(outer, "pricing")
    os.makedirs(inner)

    # 外层 __init__.py
    with open(os.path.join(outer, "__init__.py"), "w", encoding="utf-8") as f:
        f.write('SHOP_NAME = "示例商店"\n'
                'from . import pricing\n'
                'def hello():\n'
                '    return f"欢迎来到{SHOP_NAME}"\n')
    # 内层 __init__.py（子包）
    with open(os.path.join(inner, "__init__.py"), "w", encoding="utf-8") as f:
        f.write('TAX_RATE = 0.13\n'
                'def with_tax(price):\n'
                '    return round(price * (1 + TAX_RATE), 2)\n')
    # 内层子模块
    with open(os.path.join(inner, "discount.py"), "w", encoding="utf-8") as f:
        f.write('def coupon(price, rate=0.1):\n'
                '    return round(price * (1 - rate), 2)\n')

    # 把临时目录加进 sys.path，让解释器能找到它
    sys.path.insert(0, tmp)
    try:
        import shop
        print(f"  两级包导入成功：shop.__name__ = {shop.__name__!r}")
        print(f"  外层常量：shop.SHOP_NAME = {shop.SHOP_NAME}")
        print(f"  外层函数：shop.hello() = {shop.hello()!r}")

        print()
        print("  ① 导入外层包时，__init__.py 的 from . import pricing 会连锁加载子包：")
        print(f"     shop.pricing 已绑定：{hasattr(shop, 'pricing')}")
        print(f"     sys.modules 里有 'shop.pricing'：{'shop.pricing' in sys.modules}")

        print()
        print("  ② 导入子包中的名字（绝对导入，需要完整包路径）：")
        from shop.pricing import with_tax
        print(f"     from shop.pricing import with_tax → with_tax(100) = {with_tax(100)}")

        print()
        print("  ③ 导入更深一层的模块（包名变成 shop.pricing.discount）：")
        from shop.pricing.discount import coupon
        print(f"     from shop.pricing.discount import coupon → coupon(100) = {coupon(100)}")

        print()
        print("  ④ 在外层包内用【相对导入】引用子包模块（推荐写法）：")
        print("     外层 __init__.py 写的是 `from . import pricing`")
        print("     内层若要引用兄弟模块，写 `from .discount import coupon`")
        print(f"     实际验证：shop.pricing 的 __name__ = {shop.pricing.__name__!r}")

        print()
        print("  ⑤ 子包的 __path__ 指向自己的目录：")
        print(f"     shop.__path__         = {shop.__path__}")
        print(f"     shop.pricing.__path__ = {shop.pricing.__path__}")
        print("     → 每一级包有独立的搜索目录，解释器逐级下钻。")

    finally:
        # ★ 清理：必须从 sys.path 移除，并从 sys.modules 清除，否则会污染后续
        sys.path.remove(tmp)
        for mod in list(sys.modules):
            if mod == "shop" or mod.startswith("shop."):
                del sys.modules[mod]
        import shutil
        shutil.rmtree(tmp, ignore_errors=True)
        print()
        print("  ✓ 临时包已清理（sys.path 与 sys.modules 都已还原）")


# ===== 语法解析 =====
# 【8】命名空间：包最重要的价值
#   顶层模块命名空间是【全局共享】的 —— 两个同名模块会互相覆盖。
#   包提供了一层独立命名空间：shop.pricing 与 other.pricing 可以共存。
#   这就是"为什么 Python 要有包"的根本答案。
def demo_namespace_isolation() -> None:
    import myutils.text_tools as tt
    import myutils.math_tools as mt

    print(f"  tt 和 mt 都导入了 functools/sre 等同名模块，但互不干扰：")
    print(f"    tt 有 clean_text：{hasattr(tt, 'clean_text')}")
    print(f"    mt 有 clean_text：{hasattr(mt, 'clean_text')}   ← 没有，各自独立")
    print()
    print("  同理，若有名为 json.py 的文件放在包内，import json 时：")
    print("    包内的 json  → json.自己的东西")
    print("    标准库的 json → json.dumps / loads")
    print("  完全隔离，这就是命名空间机制的价值。")


def main() -> None:
    print("=" * 60)
    print("【1】什么是包")
    print("=" * 60)
    demo_what_is_package()

    print()
    print("=" * 60)
    print("【2】包内导入与相对导入")
    print("=" * 60)
    demo_relative_import()

    print()
    print("=" * 60)
    print("【3】★ 相对导入 vs 绝对导入")
    print("=" * 60)
    demo_relative_vs_absolute()

    print()
    print("=" * 60)
    print("【4】★ __all__ 的精确作用")
    print("=" * 60)
    demo_dunder_all()

    print()
    print("=" * 60)
    print("【5】__init__.py 的四种用途")
    print("=" * 60)
    demo_init_py_roles()

    print()
    print("=" * 60)
    print("【6】import 的加载顺序与连锁效应")
    print("=" * 60)
    demo_load_order()

    print()
    print("=" * 60)
    print("【7】多级包（子包）演示")
    print("=" * 60)
    demo_subpackage()

    print()
    print("=" * 60)
    print("【8】包提供的命名空间隔离")
    print("=" * 60)
    demo_namespace_isolation()

    print()
    print("=" * 60)
    print("小结")
    print("=" * 60)
    print("  1. 包 = 目录 + __init__.py，提供独立命名空间与包级初始化能力")
    print("  2. 包内用相对导入（from . import），外部用绝对导入（from pkg import）")
    print("  3. __all__ 只影响 `from 包 import *`，是治理命名空间污染的核心手段")
    print("  4. __init__.py 顶层不要写副作用代码（print / 耗时操作 / 网络请求）")
    print("  5. 多级包逐级下钻，每级 __path__ 指向自己的目录")


if __name__ == "__main__":
    main()