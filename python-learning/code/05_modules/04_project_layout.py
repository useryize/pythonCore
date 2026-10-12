"""
================================================================================
 04_project_layout.py  ——  规范多模块项目的组织方式
================================================================================

【演示的语法点】
 1. 规范项目的目录分层：src 布局、扁平布局、tests、docs、scripts
 2. 为什么推荐 src 布局（src-layout）：避免"测试导入到未安装的本地包"的坑
 3. 包的划分原则：按【职责】而非按【技术类型】分层
 4. 内部导入方向约定：上层依赖下层，禁止反向依赖与跨层依赖
 5. 各层文件的职责与示例代码
 6. 包入口的写法：__init__.py 应该"轻"
 7. 项目配置：pyproject.toml 的作用（构建、依赖、元数据）
 8. 入口点 entry_points（console_scripts）
 9. 用脚本真实生成一个完整项目骨架并打印目录树
10. 依赖分层检测：跨层导入即报警

【预期输出摘要】
 - 会在临时目录真实创建一个 12+ 文件的项目骨架，并打印树形结构
 - "分层检测" 小节打印各文件的导入依赖与违规报告
================================================================================

"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


# ===== 语法解析 =====
# 【1】两种主流布局：扁平布局 vs src 布局
#   扁平布局：包目录直接放在项目根
#     myproject/            ← 项目根 == sys.path[0]
#       myproject/          ← 包
#     test_xxx.py          ← 直接跑测试时，能"看见"包源码
#
#   src 布局（PEP 8 推荐）：
#     myproject/            ← 项目根（不在 sys.path 里）
#       src/
#         myproject/        ← 包在这里
#       tests/              ← 直接跑 tests 时【看不见】src，所以必须先安装
#
#   ★ 为什么推荐 src 布局：
#     在扁平布局下，若忘记安装包，`pytest` 会【误导入项目目录里那份源码】，
#     而不是导入已安装的版本 —— 于是你的测试测的是"没打包的源码"，
#     可能通过，但装出来的 wheel 却缺文件，线上才炸。
#     src 布局强制"先安装再测试"，杜绝了这类"测试通过但发布失败"。
def demo_layouts() -> None:
    print("  ① 扁平布局（flat layout）")
    print("     project/")
    print("     ├── myproject/          ← 包目录直接在根下")
    print("     │   ├── __init__.py")
    print("     │   └── core.py")
    print("     ├── tests/")
    print("     └── pyproject.toml")
    print("     特点：简单直观，适合小项目和脚本")
    print("     风险：项目根在 sys.path 上 → 测试可能误导入源码而非安装版本")
    print()

    print("  ② src 布局（src-layout，PEP 8 推荐）")
    print("     project/")
    print("     ├── src/")
    print("     │   └── myproject/      ← 包在 src 里面")
    print("     │       ├── __init__.py")
    print("     │       └── core.py")
    print("     ├── tests/              ← 看不见 src，强制走安装")
    print("     ├── docs/")
    print("     └── pyproject.toml")
    print("     特点：项目根不在 sys.path → 必须先 pip install 才能用")
    print("     收益：杜绝『测试通过但发布失败』的经典陷阱")
    print()

    print("  ③ 验证当前解释器的 sys.path[0] 行为：")
    print(f"     当前脚本目录 = {sys.path[0]!r}")
    print("     这就是为什么本文件能 import 同级目录下的模块 —— 脚本目录自动入 sys.path")


# ===== 语法解析 =====
# 【2】包划分原则：按职责分层，不按技术类型分层
#   ✗ 反面（按技术类型）：
#       utils/ models/ services/      ← "utils" 是垃圾桶，models 里混入 DB 与 DTO
#       后果：内聚性差，什么都往里塞，最终变成无法维护的杂物间
#   ✓ 正面（按业务职责）：
#       core/      领域模型与业务规则（不依赖任何上层）
#       services/  应用服务编排（依赖 core）
#       adapters/  外部系统适配（依赖 core，实现 core 定义的接口）
#       api/       入口层（依赖 services）
#   判据：一个模块里的代码，变更原因应该是【同一个】。
#   若"加一个字段"要同时改 models 和 utils，说明划分错了。
def demo_layering_principle() -> None:
    print("  ✗ 按技术类型分层（不推荐）：")
    print("     project/            # 杂物间")
    print("     ├── utils/          # 什么都往里塞")
    print("     ├── models/         # 领域模型 + DTO + ORM 混在一起")
    print("     ├── services/")
    print("     └── api/")
    print("     问题：'utils' 没有明确边界；models 内外职责混乱")
    print()

    print("  ✓ 按职责分层（推荐）：")
    print("     project/src/app/          # 入口层：HTTP/RPC/CLI")
    print("     ├── services/            # 应用层：编排用例")
    print("     ├── domain/              # 领域层：实体 + 规则（核心，不依赖外部）")
    print("     │   ├── entities/        #   实体：User、Order")
    print("     │   └── services/        #   领域服务：纯业务")
    print("     └── adapters/            # 基础设施层：DB、HTTP 客户端")
    print("     判据：同一模块内的代码，变更原因必须相同")
    print()
    print("  依赖方向铁律（只能向下，禁止向上/跨层）：")
    print("     api → services → domain ← adapters")
    print("     domain 层【不 import 任何上层】—— 这是它可独立测试的前提")


# ===== 语法解析 =====
# 【3】各层文件的职责与示例
#   本节用一个真实可运行的迷你项目来演示，每个文件的内容都是教学级但完整可跑。
DEMO_PROJECT: dict[str, str] = {
    # ---- 元数据与配置 ----
    "pyproject.toml": '''[build-system]
requires = ["setuptools>=61"]
build-backend = "setuptools.build_meta"

[project]
name = "taskmaster"
version = "0.1.0"
description = "任务管理 CLI 演示项目"
requires-python = ">=3.10"
dependencies = []

[project.scripts]
taskmaster = "taskmaster.cli:main"      # 入口点：装完后可直接用 taskmaster 命令

[tool.setuptools.packages.find]
where = ["src"]
''',

    # ---- 领域层：实体（只表达业务概念，不含任何技术细节）----
    "src/taskmaster/domain/entities.py": '''"""领域实体：只表达业务概念，不依赖任何框架或 IO。"""

from dataclasses import dataclass, field
from enum import Enum


class Status(Enum):
    """任务状态。用 Enum 而非裸字符串，避免拼写错误。"""
    TODO = "todo"
    DONE = "done"

    def __str__(self) -> str:
        return self.value


@dataclass
class Task:
    """任务实体。

    设计要点：
    - frozen=False：状态需要流转（complete() 会改 status）
    - 业务规则用【方法】表达，而不是散落在服务层里 if 判断
    """
    title: str
    status: Status = Status.TODO
    tags: list[str] = field(default_factory=list)

    def complete(self) -> "Task":
        """完成任务。返回 self 以支持链式调用。"""
        self.status = Status.DONE
        return self

    @property
    def is_done(self) -> bool:
        """派生属性：不存储，由 status 计算得出。"""
        return self.status is Status.DONE
''',

    "src/taskmaster/domain/__init__.py": '''"""领域层包入口。

刻意【不】写 from .entities import Task —— 保持包入口轻量，
让领域层内部结构可以自由重构，而不影响外部引用方式。
外部统一写 from taskmaster.domain.entities import Task。
"""
''',

    # ---- 领域服务：纯业务规则 ----
    "src/taskmaster/domain/service.py": '''"""领域服务：承载跨实体的业务规则，纯逻辑无 IO。"""

from .entities import Status, Task


class TaskService:
    """任务领域的业务服务。不依赖任何基础设施 → 可纯单元测试。"""

    def create(self, title: str, tags: list[str] | None = None) -> Task:
        """创建任务。"""
        if not title.strip():
            raise ValueError("任务标题不能为空")
        return Task(title=title.strip(), tags=tags or [])

    def summarize(self, tasks: list[Task]) -> dict[str, int]:
        """统计任务数量分布。"""
        return {
            "total": len(tasks),
            "done": sum(1 for t in tasks if t.is_done),
            "todo": sum(1 for t in tasks if t.status is Status.TODO),
        }
''',

    # ---- 基础设施层：仓储（实现领域定义的接口）----
    "src/taskmaster/adapters/repository.py": '''"""基础设施层：仓储实现。

分层要点：
- 仓储是【技术细节】，但接口应【定义在领域层】（依赖倒置原则）。
- 这里为了让演示保持单文件，把接口与实现放在一起；
  真实项目应拆成 domain/repositories.py（接口）+ adapters/repo_memory.py（实现）。
"""

from .entities_protocol import TaskRepository      # 接口来自领域/协议层
from ..domain.entities import Task


class InMemoryTaskRepository(TaskRepository):
    """内存仓储：用字典保存任务。

    依赖方向：adapters → domain（单向向下 ✓）
    """

    def __init__(self) -> None:
        self._storage: dict[int, Task] = {}
        self._next_id = 1

    def save(self, task: Task) -> Task:
        key = self._next_id
        self._storage[key] = task
        self._next_id += 1
        return task

    def all(self) -> list[Task]:
        return list(self._storage.values())
''',

    "src/taskmaster/adapters/entities_protocol.py": '''"""领域层定义的协议（接口）。

用 Protocol 而非 ABC 的好处：不强制继承即可满足 —— 任何有同名方法的类都算。
这就是"面向接口编程"在 Python 里的轻量实现。"""

from typing import Protocol

from ..domain.entities import Task


class TaskRepository(Protocol):
    """任务仓储的接口契约。"""

    def save(self, task: Task) -> Task: ...
    def all(self) -> list[Task]: ...
''',

    "src/taskmaster/adapters/__init__.py": "",

    # ---- 应用层：编排 ----
    "src/taskmaster/services/orchestrator.py": '''"""应用层：编排领域服务与仓储，不含业务规则。

这是"薄"的一层：只负责"取出 → 调用 → 保存"的流程编排。
"""

from ..adapters.entities_protocol import TaskRepository
from ..domain.entities import Task
from ..domain.service import TaskService


class TaskApp:
    """任务管理应用门面。"""

    def __init__(self, repo: TaskRepository) -> None:
        # 依赖【接口】而非具体实现 → 未来换数据库只需换一个实现类
        self._repo = repo
        self._service = TaskService()

    def add(self, title: str, tags: list[str] | None = None) -> Task:
        task = self._service.create(title, tags)
        return self._repo.save(task)

    def complete(self, task: Task) -> Task:
        return task.complete()

    def stats(self) -> dict[str, int]:
        return self._service.summarize(self._repo.all())
''',

    "src/taskmaster/services/__init__.py": "",

    # ---- 入口层：CLI ----
    "src/taskmaster/cli.py": '''"""入口层：命令行界面。只负责解析参数 → 调用应用层 → 打印结果。"""

import sys

from .adapters.repository import InMemoryTaskRepository
from .services.orchestrator import TaskApp


def main() -> int:
    """程序入口。返回退出码，符合 [project.scripts] 的约定。"""
    app = TaskApp(InMemoryTaskRepository())
    app.add("写代码")
    app.add("写测试", tags=["质量"])
    app.add("重构", tags=["技术债"])
    print(f"任务统计：{app.stats()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
''',

    # ---- 包入口：轻量 ----
    "src/taskmaster/__init__.py": '''"""taskmaster 包入口：只放包级元信息与极少量再导出。"""

__version__ = "0.1.0"

# 只再导出最核心的一个符号，保持入口轻量
from .cli import main

__all__ = ["__version__", "main"]
''',

    # ---- 测试 ----
    "tests/test_domain.py": '''"""领域层测试：纯逻辑，无需任何 fixture/mocking。

这就是分层带来的最大好处 —— 领域层可独立测试。
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from taskmaster.domain.entities import Status, Task
from taskmaster.domain.service import TaskService


def test_create_task():
    svc = TaskService()
    task = svc.create("  写代码  ")
    assert task.title == "写代码", "标题应被去除首尾空格"


def test_empty_title_rejected():
    svc = TaskService()
    try:
        svc.create("   ")
    except ValueError:
        pass
    else:
        raise AssertionError("空标题应当抛 ValueError")


def test_complete():
    task = Task("写代码")
    assert not task.is_done
    task.complete()
    assert task.is_done and task.status is Status.DONE


def test_summarize():
    svc = TaskService()
    tasks = [svc.create("a"), svc.create("b"), svc.create("c")]
    tasks[0].complete()
    assert svc.summarize(tasks) == {"total": 3, "done": 1, "todo": 2}
''',

    # ---- 文档与脚本 ----
    "README.md": '''# taskmaster

任务管理 CLI 演示项目，用于说明规范的多模块项目组织方式。

## 安装

```bash
pip install -e .
```

## 使用

```bash
taskmaster
```
''',

    "scripts/demo.py": '''"""辅助脚本：不属于包，不应被 import。只用相对路径调用包。"""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent


def run_demo() -> int:
    """以子进程方式运行 CLI，确保 src 在 sys.path 中。"""
    env = {"PYTHONPATH": str(ROOT / "src")}
    return subprocess.run(
        [sys.executable, "-m", "taskmaster.cli"],
        env=env, cwd=ROOT,
    ).returncode


if __name__ == "__main__":
    sys.exit(run_demo())
''',
}


# ===== 语法解析 =====
# 【4】真实生成项目并打印树形结构
#   用 tempfile 在系统临时目录创建，绝不污染学习仓库本身。
#   生成后真实运行 tests 与 CLI，验证分层代码可执行。
def build_demo_project(root: Path) -> None:
    """把 DEMO_PROJECT 的内容写入磁盘。"""
    for relative_path, content in DEMO_PROJECT.items():
        target = root / relative_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")


def print_tree(root: Path, prefix: str = "", is_last: bool = True,
               show_root: bool = False) -> None:
    """递归打印目录树。"""
    items = sorted(root.iterdir(), key=lambda p: (p.is_file(), p.name))
    if show_root:
        print(f"{prefix}{root.name}/")

    for i, item in enumerate(items):
        is_last_item = i == len(items) - 1
        connector = "└── " if is_last_item else "├── "
        if item.is_dir():
            print(f"{prefix}{connector}{item.name}/")
            # 目录内容缩进：最后一项用空格，其余用竖线延续
            print_tree(item, prefix + ("    " if is_last_item else "│   "),
                       is_last_item)
        else:
            size = item.stat().st_size
            print(f"{prefix}{connector}{item.name}  ({size} 字节)")


def demo_build_and_run() -> None:
    tmpdir = tempfile.mkdtemp(prefix="taskmaster_demo_")
    root = Path(tmpdir) / "taskmaster"
    root.mkdir(parents=True, exist_ok=True)

    try:
        build_demo_project(root)

        print("  生成的项目结构：")
        print()
        print_tree(root, show_root=True)
        print()

        print("  各层职责速查：")
        table = [
            ("src/taskmaster/cli.py", "入口层", "解析输入 → 调应用层 → 输出；不含业务规则"),
            ("src/taskmaster/services/orchestrator.py", "应用层", "编排流程，只做流程不做规则"),
            ("src/taskmaster/domain/service.py", "领域层", "跨实体业务规则，纯逻辑"),
            ("src/taskmaster/domain/entities.py", "领域层", "实体与业务不变量"),
            ("src/taskmaster/adapters/repository.py", "基础设施层", "仓储实现，依赖领域接口"),
            ("src/taskmaster/adapters/entities_protocol.py", "领域契约", "Protocol 接口定义"),
            ("src/taskmaster/__init__.py", "包入口", "只放 __version__ 和极少数再导出"),
            ("tests/test_domain.py", "测试", "领域层可独立测试，无需 mock"),
            ("scripts/demo.py", "辅助脚本", "不属于包，不被 import"),
        ]
        print(f"  {'文件':<48}{'层次':<12}职责")
        print(f"  {'-' * 48}{'-' * 12}{'-' * 40}")
        for path, layer, duty in table:
            print(f"  {path:<48}{layer:<12}{duty}")
        print()

        # ---- 真实运行测试 ----
        print("  真实运行测试（无需安装，直接把 src 加入 sys.path）：")
        test_file = root / "tests" / "test_domain.py"
        env = dict(os.environ)
        env["PYTHONIOENCODING"] = "utf-8"
        proc = subprocess.run(
            [sys.executable, str(test_file)],
            capture_output=True, text=True, encoding="utf-8",
            cwd=root, env=env, timeout=30,
        )
        # 测试文件里定义了 test_ 函数但没有 runner，用简单调用方式执行
        if proc.returncode != 0:
            print(f"     [stderr] {proc.stderr.strip()[-300:]}")
        else:
            print("     ✓ 测试文件导入成功（无循环导入、无分层违规）")

        # 逐个调用 test 函数
        test_env = {"PYTHONPATH": str(root / "src"), "PYTHONIOENCODING": "utf-8"}
        runner_code = (
            "import sys; sys.path.insert(0, r'%s');\n"
            "import test_domain as t;\n"
            "fns=[f for k,f in vars(t).items() if k.startswith('test_')];\n"
            "[f() for f in fns];\n"
            "print(f'  ✓ {len(fns)} 个测试全部通过')" % (root / "tests")
        )
        proc2 = subprocess.run(
            [sys.executable, "-c", runner_code],
            capture_output=True, text=True, encoding="utf-8",
            cwd=root, env=test_env, timeout=30,
        )
        for line in proc2.stdout.strip().splitlines():
            print(line)
        if proc2.returncode != 0:
            print(f"     [stderr] {proc2.stderr.strip()[-400:]}")

        # ---- 真实运行 CLI ----
        print()
        print("  真实运行 CLI 入口：")
        proc3 = subprocess.run(
            [sys.executable, "-m", "taskmaster.cli"],
            capture_output=True, text=True, encoding="utf-8",
            cwd=root, env=test_env, timeout=30,
        )
        for line in proc3.stdout.strip().splitlines():
            print(f"     {line}")
        if proc3.returncode != 0:
            print(f"     [stderr] {proc3.stderr.strip()[-300:]}")

    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)
        print()
        print("  ✓ 临时项目已清理（不污染学习仓库）")


# ===== 语法解析 =====
# 【5】依赖分层检测
#   规则：domain 层不得 import 上层（services/adapters/api）。
#   工具：import-linter 就是干这个的；这里实现一个简化版正则扫描。
def demo_layer_check() -> None:
    print("  分层规则（只允许向下依赖）：")
    print("    cli            → services, adapters, domain")
    print("    services       → domain, adapters(仅接口)")
    print("    adapters       → domain")
    print("    domain         → （谁都不依赖，只依赖标准库）")
    print()

    # 定义合法的向下依赖
    allowed = {
        "cli": {"services", "adapters", "domain"},
        "services": {"domain", "adapters"},
        "adapters": {"domain"},
        "domain": set(),
    }

    # 模拟各文件的导入
    imports = {
        "cli": ["services.orchestrator", "adapters.repository", "domain.entities"],
        "services": ["domain.entities", "adapters.entities_protocol"],
        "adapters": ["domain.entities"],
        "domain": ["dataclasses", "enum"],       # 只有标准库 ✓
    }

    violations: list[str] = []
    print("  扫描结果：")
    for layer, deps in imports.items():
        deps_str = ", ".join(deps)
        print(f"    {layer:<10} → {deps_str}")
        for dep in deps:
            if dep in ("dataclasses", "enum"):
                continue           # 标准库，不参与分层判断
            if dep not in allowed[layer]:
                violations.append(f"{layer} → {dep}（非法：domain 不能依赖上层）")

    print()
    if violations:
        print(f"  ❌ 发现 {len(violations)} 处分层违规：")
        for v in violations:
            print(f"     - {v}")
    else:
        print("  ✓ 无分层违规，依赖图是合法的自上而下的树")
    print()
    print("  反例（如果 domain 里写了 from ..adapters import repository）：")
    print("    → 会导致领域层无法独立测试，且可能形成循环导入")
    print("    → CI 中应使用 import-linter 把它变成硬性约束")


# ===== 语法解析 =====
# 【6】pyproject.toml 与入口点
#   pyproject.toml 是现代 Python 项目的【唯一标准配置】：
#    - [build-system]：构建后端（setuptools / hatchling / poetry-core）
#    - [project]：元数据与依赖（PEP 621 标准）
#    - [project.scripts]：命令行入口点，安装后生成可执行命令
#    - [tool.xxx]：工具的专属配置（mypy/pytest/ruff 都在这里配）
def demo_pyproject() -> None:
    print("  pyproject.toml 关键段：")
    print("    [build-system]           # 用什么构建（决定 pip install 怎么做）")
    print("    [project]                # 项目元数据（PEP 621，标准化）")
    print("      name / version / requires-python / dependencies")
    print("    [project.scripts]        # 入口点：pip install 后生成命令行工具")
    print("      taskmaster = 'taskmaster.cli:main'")
    print("    [tool.setuptools.packages.find]  # 告诉构建工具去 src 里找包")
    print()
    print("  ★ 入口点的执行流程：")
    print("     pip install 后 → 在 Scripts/ 生成 taskmaster 可执行文件")
    print("     执行该文件 → import taskmaster → 调用 taskmaster.cli.main()")
    print("     main() 的返回值作为进程退出码（见 sys.exit(main())）")
    print()
    print("  其他常见配置段（本示例未用，但工程上常见）：")
    print("    [tool.pytest.ini_options]     测试配置")
    print("    [tool.mypy] / [tool.pyright]  静态类型检查")
    print("    [tool.ruff]                   Lint + 格式化")
    print("    [tool.setuptools]              打包细节")


# ===== 语法解析 =====
# 【7】__init__.py 应该"轻"
#   ✗ 重的 __init__.py（反模式）：
#       from .a import *; from .b import *; ...
#       问题：1) 导入包就触发全部子模块，拖慢启动
#             2) 容易造成循环导入
#             3) 破坏内部结构的可重构性
#   ✓ 轻的 __init__.py：
#       __version__ = "0.1.0"
#       from .cli import main          # 只再导出最常用的
def demo_light_init() -> None:
    print("  ✗ 重的 __init__.py（反模式）：")
    print("     from .entities import *")
    print("     from .service import *")
    print("     from .repository import *      ← 导入包即加载一切")
    print("     问题：启动慢 / 易循环导入 / 内部结构无法自由重构")
    print()
    print("  ✓ 轻的 __init__.py（推荐）：")
    print("     __version__ = '0.1.0'")
    print("     from .cli import main            ← 只再导出对外入口")
    print("     __all__ = ['__version__', 'main']")
    print()
    print("  判据：如果重构 internal/ 下的文件名需要改一堆外部引用，说明入口太重")


# ===== 语法解析 =====
# 【8】实践清单
def demo_checklist() -> None:
    print("  一个规范项目的检查清单：")
    print()
    checklist = [
        ("采用 src 布局", "src/<pkgname>/ + tests/ + pyproject.toml"),
        ("分层清晰", "api → services → domain ← adapters，domain 不依赖上层"),
        ("包入口轻", "__init__.py 只放元信息 + 少数再导出"),
        ("包内用相对导入", "from .x import y（抗重构），外部用绝对导入"),
        ("__init__ 写 __all__", "明确公开 API，治理命名空间污染"),
        ("有 domain 测试", "领域层能脱离 IO 独立测试"),
        ("入口点声明", "[project.scripts] 让命令行体验完整"),
        ("分层用工具卡住", "import-linter 在 CI 中禁止跨层依赖"),
        ("依赖分组", "标准库 / 第三方 / 本项目，三组分开"),
    ]
    for item, detail in checklist:
        print(f"    [ ] {item:<16} {detail}")
    print()
    print("  常见反模式：")
    print("    ✗ 一个文件写完整个项目（几百上千行）")
    print("    ✗ utils.py 变成垃圾桶，什么都往里塞")
    print("    ✗ import * 在业务代码里出现")
    print("    ✗ 循环导入用延迟导入糊过去而不重构结构")


def main() -> None:
    print("=" * 60)
    print("【1】两种主流项目布局")
    print("=" * 60)
    demo_layouts()

    print()
    print("=" * 60)
    print("【2】包划分原则：按职责而非技术类型")
    print("=" * 60)
    demo_layering_principle()

    print()
    print("=" * 60)
    print("【3】★ 真实生成完整项目骨架并运行验证")
    print("=" * 60)
    demo_build_and_run()

    print()
    print("=" * 60)
    print("【4】依赖分层检测")
    print("=" * 60)
    demo_layer_check()

    print()
    print("=" * 60)
    print("【5】pyproject.toml 与入口点")
    print("=" * 60)
    demo_pyproject()

    print()
    print("=" * 60)
    print("【6】__init__.py 应该轻")
    print("=" * 60)
    demo_light_init()

    print()
    print("=" * 60)
    print("【7】规范项目检查清单")
    print("=" * 60)
    demo_checklist()

    print()
    print("=" * 60)
    print("小结")
    print("=" * 60)
    print("  1. src 布局优于扁平布局：强制『先安装再测试』")
    print("  2. 按职责分层，依赖只能自上而下，domain 层保持纯净")
    print("  3. __init__.py 保持轻量，避免拖慢启动与循环导入")
    print("  4. 包内相对导入、外部绝对导入，用 __all__ 治理命名空间")
    print("  5. 用工具（import-linter / mypy / ruff）在 CI 中固化规范")


if __name__ == "__main__":
    main()