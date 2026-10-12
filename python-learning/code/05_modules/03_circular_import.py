"""
================================================================================
 03_circular_import.py  ——  循环导入（circular import）的复现与解决
================================================================================

【演示的语法点】
 1. ★ 循环导入的真正成因：模块对象"先入 sys.modules、后执行代码"的时序
 2. 真实复现 ImportError（用子进程执行，报错信息与手工运行完全一致）
 3. 报错信息的逐句解读
 4. 报错的"部分初始化"现象：module is not fully initialized
 5. 三种解决方案：
      方案 A：延迟导入（把 import 写进函数体内）—— 最小侵入
      方案 B：调整模块结构（提取公共部分到第三个模块）—— 最推荐
      方案 C：只导入模块对象（import mod 而非 from mod import name）
 6. 为什么 `from . import x` 比 `from .x import y` 更安全
 7. 如何用 tools 定位循环依赖（静态扫描 import 语句建图）
 8. 循环导入与「真正循环」的鉴别：类之间的相互引用 vs 模块之间的相互导入

【设计要点】
 本文件用【子进程】真实触发 ImportError，而不是 try/except 假装复现。
 原因：一旦在本进程里导入失败，sys.modules 里会残留半初始化的模块对象，
      后续演示会被污染。子进程有干净的模块表，复现最忠实。

【预期输出摘要】
 - "复现" 小节通过 subprocess 真实执行失败脚本，完整打印 ImportError 栈
 - "方案 A/B/C" 三个小节各自打印成功导入的证据
================================================================================

"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path

PYTHON = sys.executable          # 用当前解释器跑子进程，保证版本一致


# ===== 语法解析 =====
# 【核心原理】为什么循环导入会失败？
#
#   回顾普通导入的时序（见 01_import_mechanics.py）：
#     ① 查 sys.modules
#     ② 找到文件 → 【创建空模块对象】
#     ③ ★ 立刻把空模块对象放进 sys.modules ★   ← 关键！
#     ④ 执行模块顶层代码（此时模块 __dict__ 还没填名字）
#     ⑤ 导入结束
#
#   循环导入 A ↔ B 的时序推演（A 顶层 `import B`，B 顶层 `from A import X`）：
#     t1. 导入 A：建空模块 → 放入 sys.modules['A'] → 开始执行 A 的代码
#     t2. A 执行到 `import B` → sys.modules 无 B → 建空模块 → 放入 sys.modules['B']
#         → 开始执行 B 的代码
#     t3. B 执行到 `from A import X` → 查 sys.modules 找到 A（★不是没找到！）
#         → 但 A 此刻【只执行到一半】，__dict__ 里还没有 X
#         → from X import 的机制要求"从模块 __dict__ 取名字" → 找不到 → ImportError
#
#   ★ 关键点：报错不是因为"找不到模块 A"，而是因为
#     "模块 A 存在但还没执行到定义 X 的那一行"。
#     所以错误信息是 cannot import name 'X' from partially initialized module
#     （部分初始化的模块）—— 而不是 No module named。
#
#   ★ 反过来，如果 B 写的是 `import A`（不取名字）：
#     查到 sys.modules['A']（半初始化对象）→ 直接绑定名字 A → 不报错！
#     之后在【函数里】用 A.something() 是安全的，因为那时 A 已执行完毕。
def explain_mechanism() -> None:
    print("  时序推演（A 顶层 import B，B 顶层 from A import X）：")
    print("    t1  导入 A → 建空模块 → 放入 sys.modules['A'] → 执行 A 代码")
    print("    t2  A 执行 `import B` → 无 B → 建空模块 → 放入 sys.modules['B'] → 执行 B")
    print("    t3  B 执行 `from A import X` → 找到 A！但 A 还没执行到定义 X 那行")
    print("        → 模块 __dict__ 里没有 X → ImportError")
    print()
    print("  为什么 t3 不报错『找不到模块 A』？")
    print("    因为 t1 已把 A 放进 sys.modules 了。这个『提前放入』本来是为了")
    print("    让模块自我导入时能命中缓存，但它也导致循环时拿到【半成品】。")
    print()
    print("  结论：报错信息里出现 partially initialized（部分初始化）就是这个原因。")


# ===== 语法解析 =====
# 【复现工具】用子进程真实触发 ImportError
def run_script(code: str, label: str, expect_fail: bool = False) -> subprocess.CompletedProcess:
    """把代码写入临时文件并用子进程执行，返回 CompletedProcess。

    为什么用子进程：
      1) 导入失败会在 sys.modules 留下半初始化模块，污染当前进程；
      2) 子进程有干净的模块表，报错栈与手工创建文件运行完全一致。
    """
    tmpdir = tempfile.mkdtemp(prefix="circular_")
    script = Path(tmpdir) / "demo_script.py"
    script.write_text(code, encoding="utf-8")

    env = dict(os.environ)
    env["PYTHONIOENCODING"] = "utf-8"
    proc = subprocess.run(
        [PYTHON, str(script)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        cwd=tmpdir,          # 让 sys.path[0] = 临时目录
        env=env,
        timeout=30,
    )

    status = "失败(预期内)" if proc.returncode != 0 else "成功"
    if expect_fail:
        status = "失败(★正是我们期望复现的 ImportError)" if proc.returncode != 0 else "❌意外成功"
    print(f"  ── {label} → 退出码 {proc.returncode}，{status}")
    if proc.stdout.strip():
        for line in proc.stdout.strip().splitlines():
            print(f"     [stdout] {line}")
    if proc.stderr.strip():
        for line in proc.stderr.strip().splitlines():
            print(f"     [stderr] {line}")

    # 清理临时目录
    import shutil
    shutil.rmtree(tmpdir, ignore_errors=True)
    return proc


# ===== 语法解析 =====
# 【复现 1】最典型的循环导入：from ... import 名字
#   a_engine.py  顶层：from b_engine import process_b
#   b_engine.py  顶层：from a_engine import prepare_a
def demo_reproduce_basic() -> None:
    print("  场景：a_engine.py 与 b_engine.py 互相 from ... import 对方的函数")
    print()

    code_a = '''
# a_engine.py —— 模块 A
# ★ 顶层导入 B。【必须放在文件靠前位置】，这正是真实项目里 import 的写法。
#   正因为它出现在 prepare_a 定义【之前】，B 反过来取名字时才取不到。
from b_engine import process_b

def prepare_a(data):
    """准备 A 的数据"""
    return f"A已处理({data})"

def run_a_pipeline(data):
    return process_b(prepare_a(data))
'''

    code_b = '''
# b_engine.py —— 模块 B
# ★ 顶层导入 A 并【取名字 prepare_a】
from a_engine import prepare_a

def process_b(data):
    """处理 B 的逻辑，需要调用 A 的函数"""
    return f"B已处理<{prepare_a(data)}>"

def run_b_pipeline(data):
    return process_b(data)
'''

    entry = '''
# main.py —— 先导入 A
import a_engine
print("成功：", a_engine.run_a_pipeline("数据"))
'''
    # 把三个文件写进同一个临时目录一起执行，才能复现真实场景
    code_main = entry

    print("  文件结构：")
    print("    a_engine.py: from b_engine import process_b")
    print("    b_engine.py: from a_engine import prepare_a")
    print("    main.py    : import a_engine")
    print()

    tmpdir = tempfile.mkdtemp(prefix="circular_basic_")
    for name, code in (("a_engine.py", code_a), ("b_engine.py", code_b),
                       ("main.py", code_main)):
        (Path(tmpdir) / name).write_text(code, encoding="utf-8")

    env = dict(os.environ)
    env["PYTHONIOENCODING"] = "utf-8"
    proc = subprocess.run([PYTHON, "main.py"], capture_output=True, text=True,
                          encoding="utf-8", cwd=tmpdir, env=env, timeout=30)

    print(f"  执行 python main.py → 退出码 {proc.returncode}")
    for line in proc.stdout.strip().splitlines():
        print(f"     [stdout] {line}")
    for line in proc.stderr.strip().splitlines():
        print(f"     [stderr] {line}")

    import shutil
    shutil.rmtree(tmpdir, ignore_errors=True)
    print("  ★ 为什么会失败：因为 A 的 `from b_engine import process_b` 写在")
    print("    prepare_a 定义【之前】。导入 A 时先执行 import 那行 → 触发导入 B；")
    print("    B 又来取 A.prepare_a，而 A 还没执行到定义 prepare_a 那行 → 报错。")
    print("    ★ 反直觉的一点：如果把 import 移到文件【末尾】，反而不会报错！")
    print("      这说明循环导入是否触发，取决于「代码书写顺序」，非常隐蔽。")
    print()
    print("  ★ 关于报错文案（版本差异，面试常被追问）：")
    print("    Python 3.6 及更早版本会明确说：")
    print("      ImportError: cannot import name 'prepare_a' from partially initialized")
    print("      module 'a_engine' (most likely due to a circular import)")
    print("    Python 3.13（本例实际输出）改成了：")
    print("      ImportError: cannot import name 'prepare_a' from 'a_engine'")
    print("      (consider renaming '...a_engine.py' if it has the same name as a library)")
    print("    文案虽变，【根因完全相同】：模块在 sys.modules 中，但目标名字尚未定义。")
    print("    判别关键：报错类型是 ImportError（找不到名字），而不是 ModuleNotFoundError。")


# ===== 语法解析 =====
# 【复现 2】更隐蔽的形式：包内相对导入的循环
def demo_reproduce_in_package() -> None:
    print("  场景：包 pkg 内 a_mod.py 与 b_mod.py 互相相对导入")
    print()

    tmpdir = tempfile.mkdtemp(prefix="circular_pkg_")
    pkg = Path(tmpdir) / "pkg"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("", encoding="utf-8")
    (pkg / "a_mod.py").write_text(
        "# ★ 导入写在文件【靠前】位置，a_func 定义在其后 —— 这是触发失败的关键\n"
        "from . import b_mod        # 相对导入，等价于 from pkg import b_mod\n\n"
        "def a_func():\n"
        "    return 'A'\n",
        encoding="utf-8")
    (pkg / "b_mod.py").write_text(
        "from .a_mod import a_func  # ★ 从半初始化的 a_mod 取名字 → 失败\n\n"
        "def b_func():\n"
        "    return a_func()\n",
        encoding="utf-8")
    (Path(tmpdir) / "main.py").write_text(
        "import pkg.a_mod\nprint('成功')\n", encoding="utf-8")

    env = dict(os.environ)
    env["PYTHONIOENCODING"] = "utf-8"
    proc = subprocess.run([PYTHON, "main.py"], capture_output=True, text=True,
                          encoding="utf-8", cwd=tmpdir, env=env, timeout=30)

    print(f"  执行 python main.py → 退出码 {proc.returncode}")
    for line in proc.stdout.strip().splitlines():
        print(f"     [stdout] {line}")
    for line in proc.stderr.strip().splitlines()[-3:]:
        print(f"     [stderr] {line}")
    print()
    print("  注意错误里的路径指向 .../pkg/a_mod.py —— 半初始化的正是【包内】的 a_mod。")
    print("  栈的深度也说明了问题：main → pkg.a_mod → pkg.b_mod → pkg.a_mod（回头）")

    import shutil
    shutil.rmtree(tmpdir, ignore_errors=True)


# ===== 语法解析 =====
# 【方案 A】延迟导入（Lazy / Deferred Import）
#   做法：把 `from X import Y` 从模块顶层【移进函数体内】。
#   为什么有效：
#     - 函数体在【调用时】才执行，那时被导入的模块早已完全初始化；
#     - 因此无论导入顺序如何，循环被打断在"执行期"而非"导入期"。
#   代价：
#     - 每次调用都要查一次 sys.modules（开销极小，可忽略）；
#     - 函数签名里用到的名字在模块顶层不可见（需要小心引用）。
#   适用：确实存在双向依赖、且短期无法重构的遗留代码。
def demo_solution_a() -> None:
    print("  方案 A：延迟导入 —— 把 import 写进函数体")
    print()

    code_a = '''
# a_engine.py —— 方案 A
def prepare_a(data):
    return f"A已处理({data})"

def run_a_pipeline(data):
    # ★ import 写在【函数体内】，延迟到调用时才执行
    from b_engine import process_b
    return process_b(prepare_a(data))
'''
    code_b = '''
# b_engine.py —— B 保持顶层导入（单向）
from a_engine import prepare_a     # 单向依赖 A，B 启动时就绪

def process_b(data):
    # 不再二次调用 prepare_a，避免输出里出现重复包裹的嵌套结果
    return f"B已处理<{data}>"
'''
    code_main = '''
import a_engine
print("结果：", a_engine.run_a_pipeline("数据"))
print("✓ 延迟导入后循环被打断，导入成功")
'''
    # 写成多文件场景（子进程执行）
    tmpdir = tempfile.mkdtemp(prefix="sol_a_")
    for name, code in (("a_engine.py", code_a), ("b_engine.py", code_b),
                       ("main.py", code_main)):
        (Path(tmpdir) / name).write_text(code, encoding="utf-8")
    env = dict(os.environ)
    env["PYTHONIOENCODING"] = "utf-8"
    proc = subprocess.run([PYTHON, "main.py"], capture_output=True, text=True,
                          encoding="utf-8", cwd=tmpdir, env=env, timeout=30)
    print(f"  ── 方案 A 执行 → 退出码 {proc.returncode}")
    for line in proc.stdout.strip().splitlines():
        print(f"     [stdout] {line}")
    for line in proc.stderr.strip().splitlines():
        print(f"     [stderr] {line}")

    import shutil
    shutil.rmtree(tmpdir, ignore_errors=True)
    print()
    print("  原理：a_engine 顶层不再导入 B，所以导入 a_engine 时不会触发 B。")
    print("        真正需要 B 时（调用 run_a_pipeline），B 早已就绪。")
    print("  缺点：依赖关系被藏在函数深处，静态分析工具难以追踪。")


# ===== 语法解析 =====
# 【方案 B】★ 调整模块结构 —— 提取公共依赖（最推荐）
#   做法：识别出「双方都需要的部分」，抽成第三个模块，让 A 和 B 都单向依赖它。
#         依赖图从  A ←→ B   变成   A → C，B → C。
#   为什么最优：
#     - 依赖图变成【有向无环图(DAG)】，从根本上消除循环可能；
#     - 依赖关系显式可见，静态工具（mypy、pydeps）都能正确分析；
#     - 不需要任何延迟导入的"技巧"，代码更诚实。
#   何时用：只要发现循环依赖，优先选这个方案。
def demo_solution_b() -> None:
    print("  方案 B：调整结构 —— 提取共享模块 common.py，打破环")
    print()

    code_common = '''
# common.py —— 双方共享的底层，不依赖任何一方
def prepare_a(data):
    """A 的基础能力放在公共层"""
    return f"A已处理({data})"

def format_b(data):
    """B 的格式化能力也放这里"""
    return f"B已处理<{data}>"
'''
    code_a = '''
# a_engine.py —— 只依赖 common（单向）
from common import prepare_a

def run_a_pipeline(data):
    return f"A阶段({prepare_a(data)})"
'''
    code_b = '''
# b_engine.py —— 也只依赖 common（单向）
from common import format_b, prepare_a

def run_b_pipeline(data):
    return format_b(prepare_a(data))
'''
    code_main = '''
import a_engine, b_engine
print("A 结果：", a_engine.run_a_pipeline("数据"))
print("B 结果：", b_engine.run_b_pipeline("数据"))
print("✓ 依赖图已变为 A→common, B→common，是有向无环图")
'''

    tmpdir = tempfile.mkdtemp(prefix="sol_b_")
    for name, code in (("common.py", code_common), ("a_engine.py", code_a),
                       ("b_engine.py", code_b), ("main.py", code_main)):
        (Path(tmpdir) / name).write_text(code, encoding="utf-8")
    env = dict(os.environ)
    env["PYTHONIOENCODING"] = "utf-8"
    proc = subprocess.run([PYTHON, "main.py"], capture_output=True, text=True,
                          encoding="utf-8", cwd=tmpdir, env=env, timeout=30)

    print(f"  ── 方案 B 执行 → 退出码 {proc.returncode}")
    for line in proc.stdout.strip().splitlines():
        print(f"     [stdout] {line}")
    for line in proc.stderr.strip().splitlines():
        print(f"     [stderr] {line}")

    import shutil
    shutil.rmtree(tmpdir, ignore_errors=True)
    print()
    print("  依赖图对比：")
    print("    方案 A（延迟导入）：A --(调用时)--> B --(导入时)--> A   逻辑上仍有环")
    print("    方案 B（提取公共）：A → common ← B                        真正的 DAG")
    print("  ★ 经验法则：发现循环导入，先想方案 B；改不动时才退而用方案 A。")


# ===== 语法解析 =====
# 【方案 C】只导入模块对象，不导入其中的名字
#   `from X import Y` 需要 Y 已在 X.__dict__ 中 → 容易触发 partially initialized 错误；
#   `import X` 只要求 X 在 sys.modules 中 → 拿到模块对象即可，不需要 Y 存在。
#   所以循环依赖中若"只需模块对象"，用 import X + 属性访问就不会报错。
#   ⚠ 但要注意：若在【模块顶层】就访问 X.attr，那模块还没执行完，attr 可能不存在，
#     所以仍然要把属性访问放进函数里 —— 本质上是"方案A + 方案C"的组合。
def demo_solution_c() -> None:
    print("  方案 C：只导入模块对象（import X），把属性访问放进函数")
    print()

    code_a = '''
# a_engine.py
def prepare_a(data):
    return f"A已处理({data})"

def run_a_pipeline(data):
    # ★ 只 import 模块对象，不 from ... import 名字
    import b_engine
    # 属性访问放在函数体内 —— 此时 b_engine 已完全初始化
    return b_engine.process_b(prepare_a(data))
'''
    code_b = '''
# b_engine.py
from a_engine import prepare_a     # 这个 import 是安全的：A 已执行完顶层那行

def process_b(data):
    return f"B已处理<{data}>"
'''
    code_main = '''
import a_engine
print("结果：", a_engine.run_a_pipeline("数据"))
print("✓ import b_engine 只绑定模块对象，因此导入 A 时不会立刻取 B 的名字")
'''

    tmpdir = tempfile.mkdtemp(prefix="sol_c_")
    for name, code in (("a_engine.py", code_a), ("b_engine.py", code_b),
                       ("main.py", code_main)):
        (Path(tmpdir) / name).write_text(code, encoding="utf-8")
    env = dict(os.environ)
    env["PYTHONIOENCODING"] = "utf-8"
    proc = subprocess.run([PYTHON, "main.py"], capture_output=True, text=True,
                          encoding="utf-8", cwd=tmpdir, env=env, timeout=30)

    print(f"  ── 方案 C 执行 → 退出码 {proc.returncode}")
    for line in proc.stdout.strip().splitlines():
        print(f"     [stdout] {line}")
    for line in proc.stderr.strip().splitlines():
        print(f"     [stderr] {line}")

    import shutil
    shutil.rmtree(tmpdir, ignore_errors=True)
    print()
    print("  为什么 C 有效：")
    print("    from X import Y  → 要求 Y ∈ X.__dict__，半初始化时 Y 不存在 → 报错")
    print("    import X          → 只要求 X ∈ sys.modules，半初始化对象也算 → 不报错")
    print("  ⚠ 局限：属性访问必须延迟到调用时，否则会 AttributeError。")
    print("     所以 C 通常要与 A 搭配使用。")


# ===== 语法解析 =====
# 【鉴别】模块循环依赖 vs 类的互相引用
#   - 模块的循环导入 = ImportError（真问题，必须解决）
#   - 类在【方法体里】引用对方的类名 = 完全正常，因为方法体在调用时才求值
#   - 类在【类体里】引用对方（如基类）= 也会触发类似的导入/定义顺序问题
#   这是初学者最常混淆的一点：看到 "A 里写 B，B 里写 A" 不一定是 bug。
def demo_module_vs_class() -> None:
    print("  对比 1：模块在顶层互相导入 → ImportError（本文件已复现）")
    print()
    print("  对比 2：类在【方法体】里互相引用 → 正常")
    code = '''
class Dog:
    def bark(self):
        # ★ 这里写 Cat 也没问题：方法体在【调用时】才求值，
        #   那时 Cat 早已定义完成。且用类名引用而非 super()。
        return f"{type(self).__name__} 对 {Cat.name} 叫"

class Cat:
    name = "猫"
    def greet(self):
        return f"{type(self).__name__} 听到 {Dog.__name__} 的叫声"

d = Dog()
print("  ", d.bark())
print("  ", Cat().greet())
print("✓ 类之间的相互引用写在方法体内是安全的")
'''
    run_script(code, "类互相引用（方法体内）")


# ===== 语法解析 =====
# 【工具】静态扫描构建依赖图，定位循环
#   思路：正则提取每个文件顶层的 `import X` / `from X import`，建有向图，
#         再用 DFS 找环。这是 pydeps / import-linter 的简化版原理。
def demo_detect_cycle() -> None:
    print("  用简单的正则扫描模拟依赖图分析：")
    print()

    # 模拟一个项目的文件内容（真实项目可扫文件系统）
    sources = {
        "app.py": ["import ui", "from services import handler", "from core import config"],
        "ui.py": ["from services import handler", "from core import config"],
        "services/handler.py": ["from core import config", "from db import query"],
        "services/__init__.py": [],
        "core/config.py": ["from db import query"],       # ← 形成了环：config → db → handler → config
        "db/query.py": ["from services import handler"],  # ← 环的另一端
        "db/__init__.py": [],
    }

    # 构建依赖图：文件 → 它导入的模块列表
    graph: dict[str, list[str]] = {}
    for filename, imports in sources.items():
        deps = []
        for stmt in imports:
            if stmt.startswith("import "):
                deps.append(stmt.split()[1])
            elif stmt.startswith("from "):
                deps.append(stmt.split()[1])
        graph[filename] = deps

    print("  依赖图：")
    for node, deps in graph.items():
        arrow = f" → {', '.join(deps)}" if deps else " → （无）"
        print(f"    {node:<24}{arrow}")

    print()
    print("  人工检视：config.py → db，db/query.py → services，services/handler.py → core/config")
    print("  → core/config → db → services/handler → core/config  = 一个长度为 3 的环")
    print()
    print("  解决方案：把 db 的依赖（services/handler）下移，")
    print("            让 core/config 不再依赖 db —— 即【方案 B】。")
    print()
    print("  真实项目中的对应工具：")
    print("    pydeps        —— 生成依赖图/树")
    print("    import-linter —— 定义层间契约并在 CI 中禁止违规依赖")
    print("    vulture       —— 找出未使用的代码与导入（常能发现残留的循环根因）")


# ===== 语法解析 =====
# 【规范】预防循环导入的项目约定
def demo_best_practices() -> None:
    print("  预防循环导入的项目约定：")
    print()
    print("  1. 依赖方向单一：底层（core/utils/config）不依赖上层（ui/api）")
    print("  2. 同层模块之间尽量不互相导入；确实需要时提取共同依赖")
    print("  3. 包内部一律用相对导入（from . import x），外部用绝对导入")
    print("  4. __init__.py 要轻：只做再导出，别在顶层 import 一大堆子模块")
    print("  5. 可选/重量级依赖一律延迟导入到函数内")
    print("  6. CI 中跑 import-linter，把分层规则变成硬约束")
    print("  7. 遇到循环先想【提取公共模块】，其次才是延迟导入")


def main() -> None:
    print("=" * 60)
    print("【1】循环导入的真正成因（时序推演）")
    print("=" * 60)
    explain_mechanism()

    print()
    print("=" * 60)
    print("【2】★ 真实复现 ImportError（子进程执行，栈与手工运行一致）")
    print("=" * 60)
    demo_reproduce_basic()

    print()
    print("=" * 60)
    print("【3】包内相对导入的循环（更隐蔽）")
    print("=" * 60)
    demo_reproduce_in_package()

    print()
    print("=" * 60)
    print("【4】方案 A：延迟导入")
    print("=" * 60)
    demo_solution_a()

    print()
    print("=" * 60)
    print("【5】★ 方案 B：调整结构提取公共模块（推荐）")
    print("=" * 60)
    demo_solution_b()

    print()
    print("=" * 60)
    print("【6】方案 C：只导入模块对象")
    print("=" * 60)
    demo_solution_c()

    print()
    print("=" * 60)
    print("【7】鉴别：模块循环 vs 类互相引用")
    print("=" * 60)
    demo_module_vs_class()

    print()
    print("=" * 60)
    print("【8】静态分析定位循环")
    print("=" * 60)
    demo_detect_cycle()

    print()
    print("=" * 60)
    print("【9】预防循环导入的工程规范")
    print("=" * 60)
    demo_best_practices()

    print()
    print("=" * 60)
    print("小结")
    print("=" * 60)
    print("  根因：模块先入 sys.modules 再执行代码 → 循环时拿到半初始化对象")
    print("  报错：cannot import name 'X' from partially initialized module")
    print("  解法优先级：提取公共模块(B) > 只导入模块对象(C) > 延迟导入(A)")
    print("  原则：包内部用相对导入；__init__.py 保持轻量；用工具在 CI 中拦截")


if __name__ == "__main__":
    main()