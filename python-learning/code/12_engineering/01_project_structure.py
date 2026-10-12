"""
================================================================================
 01_project_structure.py —— 规范 Python 项目结构演示
================================================================================

【演示的语法点】
  1. __file__      : 当前模块的绝对/相对文件路径（由解释器注入）
  2. __name__      : 模块名；作为主程序运行时为 "__main__"
  3. __doc__       : 模块文档字符串（本文件开头的这段说明）
  4. __package__   : 所属包名，顶层模块为 ""（空串）
  5. os.walk()     : 递归遍历目录树
  6. pathlib.Path  : 面向对象的路径操作，比字符串拼接更安全
  7. importlib     : 反射——运行时动态导入模块、读取模块属性
  8. sys.path      : 模块搜索路径，解释器导入模块的唯一依据
  9. 内置 __import__() + globals() : 最小化的动态导入演示
  10. if __name__ == "__main__":  —— 入口保护（import 本文件时不执行）

【预期输出摘要】
  [1] 本模块的 __file__      -> .../12_engineering/01_project_structure.py
  [2] 本模块的 __name__      -> __main__（作为脚本运行）
  [3] __doc__ 首行           -> 本文件的模块说明
  [4] __package__            -> ''（顶层模块）
  [5] 规范项目结构树         -> src/ tests/ pyproject.toml ... 逐行打印
  [6] sys.path 前 3 项       -> 脚本所在目录排在最前
  [7] 反射导入 json 模块     -> json.dumps / json.__name__ / json.__doc__
  [8] 目录统计               -> py 文件数、总字节数

【知识点补充】
  为什么必须有入口保护？
    别人 `import 01_project_structure` 时，模块顶层代码会执行。
    若没有 if __name__ == "__main__" 保护，顶层的演示代码会跟着执行，
    造成 import 副作用（打印刷屏、耗时、甚至误改数据）。工程上必须避免。
"""

import importlib
import json
import os
import sys
from pathlib import Path


# ==============================================================================
# 一、规范的 Python 项目结构（用嵌套字典描述，等价于一棵"结构树"）
# ==============================================================================
# 用 dict 描述目录树，好处是：纯数据、可被测试、可被遍历，
# 比在代码里硬编码一堆 print 更工程化。
PROJECT_STRUCTURE: dict[str, object] = {
    "my_project/": {
        # "src 布局"(src layout) 是当前社区主流做法：
        # 不装包时无法直接 import 你的模块，从物理上杜绝「误 import 本地文件」
        "├── src/": {
            "└── my_project/": {          # ★ src 下与包名同名的这一层是 src layout 的关键
                "├── __init__.py": "__version__ = '1.0.0'",
                "├── main.py": "程序入口",
                "├── config.py": "配置",
                "├── core/": {             # 核心业务，不依赖框架
                    "├── __init__.py": None,
                    "├── engine.py": "核心引擎",
                    "└── models.py": "数据模型",
                },
                "└── utils/": {            # 纯工具函数
                    "__init__.py": None,
                    "helpers.py": "工具函数",
                },
            }
        },
        "├── tests/": {                  # 与业务代码分离
            "├── __init__.py": None,
            "├── test_engine.py": "单元测试",
            "└── conftest.py": "pytest 全局 fixture",
        },
        "├── docs/": {"index.md": None, "architecture.md": "架构说明"},
        "├── scripts/": {"check_all.sh": "本地一键检查"},
        "├── .github/": {"workflows/": {"ci.yml": "GitHub Actions"}},
        "├── .pre-commit-config.yaml": "提交前钩子",
        "├── pyproject.toml": "★ 项目唯一配置中心(ruff/mypy/pytest 都在这)",
        "├── requirements.txt": "运行依赖",
        "├── README.md": "项目说明",
        "├── LICENSE": "许可证",
        "└── .gitignore": "忽略规则",
    }
}


# ==============================================================================
# 二、辅助函数：把上面的字典渲染成字符串
# ==============================================================================
def render_tree(structure: dict[str, object], indent: str = "") -> list[str]:
    """把嵌套 dict 渲染成若干行文本（递归）。

    :param structure: 节点字典，key 是"名字: 内容"，value 是子节点 dict 或 None
    :param indent:    当前缩进前缀，由递归逐层累加
    :return: 行列表
    """
    lines: list[str] = []
    for name, value in structure.items():
        # value 是 dict 表示还有子节点；否则是叶子（叶子后面带 ':' 后的说明文字）
        is_branch = isinstance(value, dict)
        if is_branch:
            lines.append(f"{indent}{name}")
            # 递归时多缩进两格，保持视觉层级
            lines.extend(render_tree(value, indent + "   "))
        else:
            lines.append(f"{indent}{name}   # {value}" if value else f"{indent}{name}")
    return lines


def scan_directory(target: Path, max_depth: int = 2) -> dict[str, object]:
    """统计目录信息：py 文件数、文件总数、总字节数。

    :param target:    要扫描的目录
    :param max_depth: 递归深度上限，防止误扫到巨大目录（如 C:\\）
    """
    py_files = total_files = total_bytes = 0
    # os.walk 会 yield (当前目录, 子目录列表, 文件列表) 三元组
    for current_root, dirs, files in os.walk(target):
        depth = len(Path(current_root).relative_to(target).parts)
        if depth >= max_depth:
            # 到达深度上限 -> 原地修改 dirs 列表来剪枝（os.walk 的约定做法）
            dirs[:] = []
            continue
        # 跳过隐藏目录和缓存目录，避免统计噪声
        dirs[:] = [d for d in dirs if not d.startswith((".", "__pycache__"))]
        for name in files:
            total_files += 1
            if name.endswith(".py"):
                py_files += 1
                total_bytes += (Path(current_root) / name).stat().st_size
    return {"py 文件数": py_files, "文件总数": total_files, "py 总字节": total_bytes}


# ==============================================================================
# 三、模块自省（introspection）——认识 Python 注入的"魔法变量"
# ==============================================================================
def inspect_self() -> dict[str, str]:
    """读取本模块自身的元信息，演示 __file__ / __name__ / __doc__ / __package__。"""
    info: dict[str, str] = {
        "__file__": __file__,          # 解释器在导入时写入的绝对路径
        "__name__": __name__,          # "01_project_structure" 或 "__main__"
        "__doc__首行": (__doc__ or "").strip().splitlines()[0],
        "__package__": repr(__package__),   # 顶层模块为空串，用 repr 才能看出是 ""
    }
    # __spec__ 仅在「被正常导入」时存在；直接 python 文件运行时为 None
    info["__spec__"] = repr(getattr(__spec__, "name", None))
    return info


def demo_reflection() -> None:
    """用 importlib 反射：动态导入模块并读取其属性，无需在文件顶部 import。"""
    # importlib.import_module 按名字导入模块并返回模块对象
    json_mod = importlib.import_module("json")

    # 模块对象上的 dunder 属性
    print(f"  json.__name__       = {json_mod.__name__!r}")
    print(f"  json.__file__       = {json_mod.__file__}")
    print(f"  json.__doc__ 首行   = {(json_mod.__doc__ or '').strip().splitlines()[0]}")

    # 调用反射拿到的模块函数，证明它就是普通可调用对象
    payload = {"name": "工程化", "ok": True}
    print(f"  json.dumps(...)     = {json_mod.dumps(payload, ensure_ascii=False)}")

    # 枚举模块公开符号 —— 写插件系统/CLI 时常用
    public = [n for n in dir(json_mod) if not n.startswith("_")][:12]
    print(f"  json 公开符号(前12) = {public}")


def demo_sys_path() -> None:
    """sys.path 是解释器搜索模块的路径列表，脚本所在目录通常排在第 0 位。"""
    print(f"  sys.path 条目数     = {len(sys.path)}")
    for index, item in enumerate(sys.path[:3]):
        print(f"    [{index}] {item}")
    print(f"  'os' 是否已在内存中 = {'os' in sys.modules}")
    print(f"  sys.modules 条目数  = {len(sys.modules)}")


# ==============================================================================
# 四、主流程
# ==============================================================================
def main() -> None:
    """演示入口。逐节打印，全部只依赖标准库，无需联网、无 input() 阻塞。"""

    print("=" * 78)
    print(" 01. 规范 Python 项目结构演示")
    print("=" * 78)

    # ---------- 1. 读取自身模块信息 ----------
    print("\n[1] 本模块的自省信息（Python 注入的 dunder 变量）")
    print("-" * 78)
    for key, value in inspect_self().items():
        # 用 key.ljust 手动对齐，:>12 是「右对齐宽度 12」，比空格硬拼更整洁
        print(f"  {key:<16}: {value}")

    # ---------- 2. 打印规范项目结构树 ----------
    print("\n[2] 推荐的规范项目结构（src layout）")
    print("-" * 78)
    for line in render_tree(PROJECT_STRUCTURE):
        print("  " + line)

    print("\n  各目录职责速查：")
    roles = [
        ("src/", "业务代码。src 布局可防止测试外的代码误 import"),
        ("tests/", "自动化测试，与业务代码分离"),
        ("docs/", "文档：设计文档、使用说明、变更记录"),
        ("scripts/", "运维脚本：一键检查、数据迁移、发布"),
        (".github/", "GitHub Actions CI 配置"),
        ("pyproject.toml", "项目元数据 + 工具配置的唯一入口（PEP 518）"),
    ]
    for name, role in roles:
        print(f"    {name:<20} {role}")

    # ---------- 3. 实际扫描当前目录 ----------
    # __file__ 可能为相对路径，先 resolve() 拿到绝对路径再取父目录
    current_dir = Path(__file__).resolve().parent
    print(f"\n[3] 实测扫描当前目录：{current_dir}")
    print("-" * 78)
    for key, value in scan_directory(current_dir).items():
        print(f"  {key:<12}: {value}")

    # ---------- 4. sys.path 与模块缓存 ----------
    print("\n[4] 模块搜索机制：sys.path 与 sys.modules")
    print("-" * 78)
    demo_sys_path()

    # ---------- 5. importlib 反射 ----------
    print("\n[5] importlib 反射：运行时动态导入与属性访问")
    print("-" * 78)
    demo_reflection()

    print("\n" + "=" * 78)
    print(" 关键结论：")
    print("   1. 项目用 src 布局 + pyproject.toml 统一配置，是现代 Python 的默认答案")
    print("   2. __name__ == '__main__' 守卫必须在模块底部，防止 import 副作用")
    print("   3. importlib 提供运行时反射能力，是插件化/脚本化的基础")
    print("=" * 78)


# ==============================================================================
# 五、入口保护
# ==============================================================================
# 只有「直接运行本文件」时才执行 main()。
# 若他人 `import 本模块`，此处不执行，import 无任何副作用。
if __name__ == "__main__":
    main()
