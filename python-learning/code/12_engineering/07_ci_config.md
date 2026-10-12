# 07 · 工程化配置速查（pre-commit / CI / ruff / mypy / pytest）

> 本文件是**纯文档**，不会被 Python 执行。目的是给出可以直接抄走的生产级配置模板。
> 配套示例：`04_pytest_style.py`（测试）、`02_typing_quality.py`（类型）、`08_performance.py`（性能）。

---

## 目录

1. [配置哲学：唯一真相源](#1-配置哲学唯一真相源)
2. [pyproject.toml —— 项目唯一配置中心](#2-pyprojecttoml--项目唯一配置中心)
3. [ruff 配置与常见规则](#3-ruff-配置与常见规则)
4. [mypy 配置](#4-mypy-配置)
5. [pytest 配置](#5-pytest-配置)
6. [pre-commit 配置](#6-pre-commit-配置)
7. [GitHub Actions CI](#7-github-actions-ci)
8. [本地一键检查脚本](#8-本地一键检查脚本)
9. [完整的目录结构与文件职责](#9-完整的目录结构与文件职责)
10. [落地顺序与常见坑](#10-落地顺序与常见坑)

---

## 1. 配置哲学：唯一真相源

**核心原则：同一件事只在一个地方配置一次。**

```text
❌ 反模式：ruff 配 .ruff.toml，mypy 配 mypy.ini，
           pytest 配 pytest.ini，项目元信息配 setup.py，
           CI 里再手写一遍 pytest --cov-fail-under=80

✅ 正确：全部写进 pyproject.toml 一个文件
        CI 只负责"在干净环境里执行 check.sh"，不重复声明任何规则
```

| 关注点 | 配置文件 | 说明 |
| --- | --- | --- |
| 项目元信息 | `pyproject.toml` | PEP 518 标准，pip/ruff/mypy/pytest 全部识别 |
| 代码风格 + lint | `[tool.ruff]` | 替代 flake8 + isort + black |
| 类型检查 | `[tool.mypy]` | 唯一类型配置源 |
| 测试规则 | `[tool.pytest.ini_options]` | 唯一测试配置源 |
| 提交前钩子 | `.pre-commit-config.yaml` | 只能改文件，无法在 commit -m 时跑（见坑 #3） |
| 依赖 | `pyproject.toml` 或 `requirements*.txt` | 单一来源，不要两处都写 |

> **为什么不再用 `.flake8` / `mypy.ini` / `pytest.ini`？**
> 它们都还在工作，但 `pyproject.toml` 是唯一被官方标准化的位置。
> 一堆零散配置文件意味着：CI 和本地跑的规则可能不一致 —— 这是最常见的"我本地好好的"事故。

---

## 2. pyproject.toml —— 项目唯一配置中心

```toml
# ============================================================
# [project] —— 项目元信息（PEP 621）
# ============================================================
[build-system]
requires = ["hatchling"]           # 或 setuptools / poetry-core / flit-core
build-backend = "hatchling.build"

[project]
name = "my-package"                # 与 PyPI 上的名字一致
version = "0.1.0"
description = "一个用于演示工程化配置的示例包"
readme = "README.md"
requires-python = ">=3.10"         # 用版本门槛直接屏蔽低版本语法差异
license = { text = "MIT" }
authors = [{ name = "Your Name", email = "you@example.com" }]
keywords = ["python", "engineering"]
classifiers = [
    "Development Status :: 4 - Beta",
    "Intended Audience :: Developers",
    "License :: OSI Approved :: MIT License",
    "Programming Language :: Python :: 3.10",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
    "Topic :: Software Development :: Libraries",
]

# 运行依赖 —— 只有真正 import 到的包才写进来
dependencies = [
    "httpx>=0.27,<1.0",
]

# 可选依赖组 —— 按用途分组，避免"全都要装"
[project.optional-dependencies]
dev = [
    "ruff>=0.6",            # lint + format
    "mypy>=1.11",           # 静态类型
    "pytest>=8.0",          # 测试
    "pytest-cov>=5.0",      # 覆盖率
    "pytest-mock>=3.14",    # mock 增强
    "pre-commit>=3.8",      # 提交钩子
]
docs = [
    "mkdocs>=1.6",
    "mkdocs-material>=9.5",
]
prod = [
    "gunicorn>=22.0",       # 生产 WSGI 服务器
    "uvicorn>=0.30",        # ASGI 服务器
]

[project.urls]
Homepage = "https://github.com/your-org/my-package"
Repository = "https://github.com/your-org/my-package"
Issues = "https://github.com/your-org/my-package/issues"

# 命令行入口 —— 安装后可直接 `mytool run`
[project.scripts]
mytool = "my_package.cli:main"

# ============================================================
# [tool.hatch.build] —— 告诉打包工具源码在哪
# ============================================================
[tool.hatch.build.targets.wheel]
packages = ["src/my_package"]

# ============================================================
# [dependency-groups] —— 现代标准的开发依赖（pip 25.1+ 支持）
# ============================================================
# 与 optional-dependencies 的区别：不会被打进发布包元数据
[dependency-groups]
dev = [
    "ruff>=0.6",
    "mypy>=1.11",
    "pytest>=8.0",
    "pytest-cov>=5.0",
    "pre-commit>=3.8",
]

# ============================================================
# [tool.uv] —— 如果用 uv 管理依赖
# ============================================================
[tool.uv]
package = true
dev-dependencies = ["pytest", "ruff", "mypy"]
```

**安装开发环境：**

```bash
pip install -e ".[dev]"          # 可编辑安装 + dev 依赖组
uv sync --all-extras            # 用 uv 更快
```

---

## 3. ruff 配置与常见规则

ruff 是**Rust 编写**的 linter + formatter，替代 flake8 / isort / black / isort 的组合，
速度快 10~100 倍，且一个工具覆盖四个工具的职责。

```toml
[tool.ruff]
# 与 black 官方文档一致：88 字符 + 双引号
line-length = 88
target-version = "py310"        # 与 requires-python 保持一致
src = ["src", "tests"]          # 帮助 ruff 正确解析 first-party import

[tool.ruff.lint]
# 规则分组：ruff 用前缀批量选择一整组规则
select = [
    "E",      # pycodestyle 错误（行宽、空白）
    "W",      # pycodestyle 警告
    "F",      # pyflakes（未使用的导入、未定义的名字）
    "I",      # isort（导入排序）
    "B",      # flake8-bugbear（易错模式）
    "C4",     # flake8-comprehensions（更优的推导式写法）
    "UP",     # pyupgrade（用新语法替代旧写法）
    "SIM",    # flake8-simplify（可简化的逻辑）
    "RET",    # flake8-return（return 的放置）
    "ARG",    # 未使用的函数参数
    "PTH",    # 用 pathlib 替代 os.path
    "TID",    # import 太乱（禁止裸 `import x.y`）
    "DTZ",    # 带时区的 datetime
    "RUF",    # ruff 自有规则（易错的字符串/集合操作等）
]

ignore = [
    # 与 formatter 冲突的规则 —— 必须关，否则会和 format 打架
    "E501",    # 行宽由 formatter 管，linter 不再重复报
    "COM812",  # 与 format 冲突
    "ISC001",  # 与 format 冲突
    # 项目特定取舍
    "B008",    # 函数默认值里调用函数（FastAPI 的 Depends 就靠它，需按需关）
]

# 只在特定文件放宽规则
[tool.ruff.lint.per-file-ignores]
# 测试代码可以长行、可以随便 print、可以有多余参数
"tests/**/*" = ["E501", "S101", "PLR2004", "ARG001"]
# 迁移脚本先豁免，等迁完再收紧
"scripts/migrations/**/*" = ["E402", "F401"]
# 初始化文件里大量导入是正常操作
"__init__.py" = ["F401"]

# 给特定规则配置参数
[tool.ruff.lint.flake8-bugbear]
extend-immutable-calls = ["fastapi.Depends", "fastapi.Query"]

[tool.ruff.lint.isort]
known-first-party = ["my_package"]
known-local-folder = ["tests"]

# 自动修复未使用的导入时要小心：__init__.py 的导入是"对外暴露"
[tool.ruff.lint.pydocstyle]
convention = "google"

[tool.ruff.format]
quote-style = "double"          # 与 black 兼容
indent-style = "space"
skip-magic-trailing-comma = false   # 保留魔法逗号 = 自动换行
line-ending = "auto"
docstring-code-format = true    # 自动格式化 docstring 里的代码块
```

**常用命令：**

```bash
ruff check .                    # 只检查不修改
ruff check . --fix              # 自动修复可修复的问题
ruff check . --diff             # 显示将要做的修改
ruff check . --statistics       # 按规则统计违规数量（治理时的第一份报告）
ruff format .                   # 格式化
ruff format . --diff           # 预览格式化差异
ruff check . --select ANN      # 只跑某一类规则（渐进式引入时很有用）
ruff rule ANN                   # 查看某条规则的详细解释与修复示例
ruff config lint.select         # 查看当前生效配置
```

**渐进式引入建议**（不要一上来就全开，否则 legacy 代码几千条报错无从下手）：

```text
阶段 1：select = ["E", "F"]                  # 只管明显错误，新代码零阻力
阶段 2：select = [..., "I", "B", "UP"]       # 加导入排序与 bugbear
阶段 3：select = [..., "SIM", "RET", "C4"]   # 代码质量
阶段 4：全量 + 补齐所有 # noqa                # 清零历史债
```

---

## 4. mypy 配置

```toml
[tool.mypy]
python_version = "3.10"
# 最关键的三行：让 mypy 认识依赖里的类型
mypy_path = "src"
files = ["src", "tests"]
plugins = ["pydantic.mypy", "sqlalchemy.ext.mypy.plugin"]

# 严格度：strict 是最终目标，新项目直接开
strict = true

# ---------- 逐项开关（strict=true 的等价展开，写出来便于微调）----------
disallow_untyped_defs = true          # 函数必须有完整注解
disallow_any_generics = true          # 禁止裸 list / dict（要写 list[str]）
check_untyped_defs = true             # 即使没注解也要检查函数体
no_implicit_reexport = true           # from a import b 不能被第三方间接 import
warn_redundant_casts = true           # 多余的 cast 报错
warn_unused_ignores = true            # ★ 没用的 type: ignore 报错（防止掩盖问题）
warn_unused_configs = true            # 配置里没用到的选项报错
no_implicit_optional = true           # x: int = None 报错
strict_equality = true                # 1 == "1" 报错
check_untyped_calls = true            # 调用无注解函数时检查

# ---------- 允许在哪些地方不严格 ----------
[[tool.mypy.overrides]]
module = [
    "tests.*",
    "scripts.*",
    "docs.*",
]
# 测试代码里用 Any 和 mock 很正常，全局放宽
disallow_untyped_defs = false
disallow_untyped_calls = false
disallow_any_generics = false
disallow_untyped_decorators = false
warn_return_any = false

[[tool.mypy.overrides]]
# 第三方库缺少类型注解（尤其是老库）
module = ["some_untyped_lib.*", "yaml", "passlib.*"]
ignore_missing_imports = true

# ---------- 报告格式 ----------
pretty = true
show_error_codes = true
show_column_numbers = true
hide_error_context = false
# 报错了直接给出修复建议
enable_error_code = [
    "ignore-without-code",     # 禁止裸 # type: ignore，必须写 # type: ignore[xxx]
    "truthy-bool",             # if 可能为 None 的对象
    "redundant-expr",
    "possibly-undefined",
    "unused-awaitable",
]

# ---------- 包发布检查 ----------
# 第三方用你的库时不该看到你内部的具体类型（尤其是 TypeVar 泄漏）
[tool.mypy]
strict_equality = true
```

**常用命令：**

```bash
mypy src/                                  # 检查
mypy --install-types                      # 缺类型桩时自动补装（types-requests 等）
mypy --strict src/                        # 命令行临时开严格模式，对比效果
mypy --disallow-any-expr src/foo.py        # 找出所有 Any 的来源（最难清的一类债）
mypy --warn-unused-ignores src/            # 找出失效的 type: ignore
mypy --html-report build/mypy/ src/        # 生成 HTML 报告
mypy --linecount-report build/lines.txt src/  # 按文件统计错误数，治理排序用
```

**类型注解与运行时检查的分工（务必理解）：**

```text
mypy 报错，但程序能正常跑 —— 这是最常见的困惑。
原因：Python 类型注解在运行时【只是存进 __annotations__ 的元数据】，不做任何强制。

  def f(x: int) -> None: ...
  f("abc")      # 运行时完全正常，mypy 报错

结论：
  · mypy 是「编译期保险丝」，负责在你 push 之前把类型错误拦住
  · dataclass / pydantic / attrs 等库会【额外】做运行时校验，那是另一条线
  · 别用 mypy 的标准去要求运行时 —— 那属于 over-engineering
```

---

## 5. pytest 配置

```toml
[tool.pytest.ini_options]
minversion = "8.0"

# ---------- 用例发现 ----------
testpaths = ["tests"]            # 不指定目录时默认只扫这里
python_files = ["test_*.py"]     # 默认就是 test_*.py
python_classes = ["Test*"]       # 类名以 Test 开头才收集
python_functions = ["test_*"]    # 函数名以 test 开头才收集
norecursedirs = [
    "*.egg", ".git", ".venv", "build", "dist",
    "node_modules", "src",       # src 里不会有测试，扫了纯浪费时间
]

# ---------- 默认行为 ----------
addopts = [
    "-ra",                      # 报告所有 skipped/xfail/xpass 的原因
    "--strict-markers",         # 用未注册的 marker 直接报错，防止 @pytest.mark.tyop 静默失效
    "--strict-config",          # 配置文件里有无效选项也报错
    "--strict-markers",
    "--import-mode=importlib",  # 3.11+ 推荐的导入模式，解决同名测试模块冲突
    "--tb=short",               # 短的失败堆栈
    "-v",
]

# ---------- 标记（相当于给用例分类，可选择性执行）----------
markers = [
    "slow: 耗时较长的用例（CI 里可跳过：-m 'not slow'）",
    "integration: 集成测试，需要外部服务",
    "e2e: 端到端测试",
    "db: 需要数据库",
    "network: 需要网络",
    "unit: 纯单元测试",
    "flaky: 不稳定的用例，CI 里重跑",
]

# ---------- fixture 行为 ----------
usefixtures = []                # 全局自动使用的 fixture
filterwarnings = [
    "error",                    # ★ 把所有警告当错误 —— 最好的防退化手段
    "ignore::DeprecationWarning:some_old_lib.*",
    "ignore::pytest.PytestUnraisableExceptionWarning",
]

# ---------- 日志 ----------
log_cli = false                 # 需要看实时日志时命令行加 --log-cli-level=INFO
log_cli_level = "INFO"
log_file = "logs/pytest.log"
log_file_level = "DEBUG"
log_format = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
log_date_format = "%Y-%m-%d %H:%M:%S"

# ---------- 超时与随机顺序 ----------
timeout = 30                    # 需 pip install pytest-timeout；卡死的用例自动判失败
faulthandler_timeout = 60       # 崩溃时打印所有线程栈

# ---------- 覆盖率（需 pip install pytest-cov）----------
addopts = [
    "--cov=src/my_package",     # 只统计业务代码，不统计测试代码
    "--cov-report=term-missing",# 终端报告里显示哪些行没覆盖
    "--cov-report=html:htmlcov",
    "--cov-report=xml:coverage.xml",
    "--cov-fail-under=85",      # ★ 覆盖率门槛：低于 85% 直接让 CI 失败
]

# ---------- xfail_strict ----------
xfail_strict = true             # ★ 意外通过的 xfail 算失败
                              # 防止"标记为已知失败，结果偷偷修好了却没人发现"

# ---------- 缓存 ----------
cache_dir = ".pytest_cache"
cache_show = true
```

> ⚠️ `addopts` 只能出现一次。要同时写两组（如"本地不跑覆盖率，CI 要跑"），
> 用环境变量条件化，或把覆盖率参数放到 CI 命令行里：
> ```bash
> # 本地
> pytest -p no:cacheprovider --no-cov
> # CI
> pytest --cov --cov-report=xml --junitxml=junit.xml
> ```

---

## 6. pre-commit 配置

**作用：在 `git commit` 之前自动跑检查，不通过就拒绝提交。**
这是投入产出比最高的工程化实践 —— 把问题拦在本地，远比 CI 拦下来省时间。

```yaml
# .pre-commit-config.yaml
# 官网：https://pre-commit.com
default_install_hook_types: [pre-commit, commit-msg]

# 全局排除：这些文件所有钩子都不检查
exclude: |
  (?x)^(
    migrations/.*\.py$|
    \.venv/.*|
    node_modules/.*|
    __pycache__/.*|
    .*\.pb\.py$
  )

default_stages: [pre-commit]

repos:
  # ---------- 1. 基础卫生检查（跑得极快，必须放最前）----------
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v5.0.0
    hooks:
      - id: trailing-whitespace      # 删除行尾空格
      - id: end-of-file-fixer        # 保证文件末尾有且仅有一个换行
      - id: mixed-line-ending        # 统一为 \n（跨平台协作必备）
        args: [--fix=lf]
      - id: check-yaml               # YAML 语法校验（k8s / CI 配置必备）
      - id: check-toml               # TOML 语法校验（pyproject.toml）
      - id: check-json               # JSON 语法校验
      - id: check-added-large-files
        args: [--maxkb=1024]         # 阻止提交 > 1MB 的文件
      - id: check-merge-conflict     # 防止把冲突标记提交进去
      - id: check-case-conflict      # macOS 大小写不敏感文件系统的老坑
      - id: check-ast                # ★ 语法错误：等价于 python -m py_compile
      - id: detect-private-key        # 阻止提交密钥 ★ 安全底线
      - id: forbid-new-submodules

  # ---------- 2. Python 格式与 lint ----------
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.6.9
    hooks:
      # 顺序很重要：先 lint --fix 修问题，再 format 统一格式
      - id: ruff
        args: [--fix, --exit-non-zero-on-fix]
      - id: ruff-format

  # ---------- 3. 类型检查 ----------
  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.11.2
    hooks:
      - id: mypy
        # additional_dependencies 必须列出插件和被检查包依赖的类型，否则 mypy 会误报缺失导入
        additional_dependencies: [
          types-requests,
          pydantic,
          pytest,
        ]
        args: [--strict]
        files: ^src/

  # ---------- 4. 提交信息规范 ----------
  - repo: https://github.com/commitizen-tools/commitizen
    rev: v4.6.1
    hooks:
      - id: commitizen
        stages: [commit-msg]

  # ---------- 5. 调试残留检查 ----------
  - repo: https://github.com/asottile/yesqa
    rev: v1.5.0
    hooks:
      - id: yesqa                   # 清理不再需要的 # noqa

  # ---------- 6. 安全扫描 ----------
  - repo: https://github.com/gitleaks/gitleaks
    rev: v8.18.4
    hooks:
      - id: gitleaks                # 检测硬编码的密钥、token

  # ---------- 7. 危险代码检查（可选）----------
  - repo: https://github.com/PyCQA/bandit
    rev: v1.7.10
    hooks:
      - id: bandit
        args: ["-c", "pyproject.toml"]   # bandit 配置写在 pyproject.toml 里
        exclude: ^tests/
```

**安装与使用：**

```bash
pip install pre-commit
pre-commit install                    # 装成 git hook（每个 clone 都要执行一次）
pre-commit install --install-hooks    # 同时把各 hook 环境装好（CI 里用）
pre-commit run --all-files            # 手动全量跑一遍
pre-commit run ruff --all-files       # 只跑某个 hook
pre-commit autoupdate                 # 自动升级所有 hook 版本 ★ 每两周跑一次
SKIP=mypy pre-commit run --all-files  # 本地临时跳过慢钩子
```

**推荐的提交信息规范（Conventional Commits）：**

```text
<type>(<scope>): <subject>

feat(auth): 增加双因素认证
fix(orders): 修复并发下单导致的库存超卖
refactor(core): 拆分订单状态机为独立模块
perf(search): 用字典索引替换线性查找，耗时降低 90%
docs(readme): 补充 Docker 部署步骤
test(payment): 补充支付回调的边界用例
chore(deps): 升级 ruff 到 0.6.9
```

`type` 可选值：`feat` `fix` `refactor` `perf` `docs` `test` `chore` `build` `ci` `style` `revert`。

---

## 7. GitHub Actions CI

```yaml
# .github/workflows/ci.yml
name: CI

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main, develop]
  # 打 tag 也跑一次，验证发布可用性
  workflow_dispatch:

# 取消同一分支上旧的运行，节省 CI 额度
concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true

permissions:
  contents: read        # 最小权限：只读。CI 不需要写权限

env:
  PYTHON_VERSION: "3.11"
  # 把缓存和覆盖率文件放到固定路径，避免各 job 重复上传
  PIP_CACHE_DIR: ~/.cache/pip

jobs:
  # ==========================================================
  # Job 1：快检（无依赖，10~20 秒）—— 失败立刻中断，省资源
  # ==========================================================
  lint:
    name: Lint (ruff + pre-commit)
    runs-on: ubuntu-latest
    timeout-minutes: 5
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0        # 完整历史，否则 pre-commit 某些钩子会异常

      - uses: actions/setup-python@v5
        with:
          python-version: ${{ env.PYTHON_VERSION }}
          cache: pip

      - name: 安装依赖
        run: |
          python -m pip install --upgrade pip
          pip install pre-commit ruff

      - name: 跑 pre-commit 全部钩子
        run: pre-commit run --all-files --show-diff-on-failure
        # 与本地用完全相同的配置 —— 这是"唯一真相源"的价值所在

      - name: 统计 ruff 违规分布（不阻断，仅产出报告）
        continue-on-error: true
        run: ruff check . --statistics || true

  # ==========================================================
  # Job 2：类型检查 + 单元测试（矩阵跑多个 Python 版本）
  # ==========================================================
  test:
    name: Test (py${{ matrix.python-version }})
    runs-on: ${{ matrix.os }}
    timeout-minutes: 15
    needs: lint                 # lint 挂了就不必跑测试，省 CI 时间
    strategy:
      # 一次全部跑完；不要用 fail-fast: true，否则一个版本挂了其他版本的结果都没了
      fail-fast: false
      matrix:
        os: [ubuntu-latest]
        python-version: ["3.10", "3.11", "3.12"]
        include:
          # 补充 Windows/macOS 兼容性验证（可按需删掉）
          - os: windows-latest
            python-version: "3.11"
          - os: macos-latest
            python-version: "3.12"
          # 预发布版本：提前发现不兼容
          - os: ubuntu-latest
            python-version: "3.13"
            experimental: true
        exclude:
          # 3.13 还不稳定，只跑不做门禁
          - os: ubuntu-latest
            python-version: "3.13"

    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}
          cache: pip
          allow-prereleases: ${{ matrix.experimental || false }}

      - name: 安装依赖
        run: |
          python -m pip install --upgrade pip
          pip install -e ".[dev]"

      - name: 类型检查 (mypy)
        run: mypy src/

      - name: 单元测试 + 覆盖率
        run: |
          pytest tests/unit \
            --cov=src/my_package \
            --cov-report=xml:coverage-${{ matrix.os }}-${{ matrix.python-version }}.xml \
            --cov-report=term-missing \
            --junitxml=junit-${{ matrix.os }}-${{ matrix.python-version }}.xml \
            -m "not slow and not integration and not e2e" \
            --tb=short

      - name: 校验覆盖率门槛
        run: |
          pip install coverage[toml]
          coverage report --fail-under=85
          # 低于门槛直接失败，防止覆盖率静默下降

      - name: 上传覆盖率到 Codecov
        uses: codecov/codecov-action@v4
        continue-on-error: true      # 第三方服务挂了不该让 CI 红
        with:
          files: ./coverage-${{ matrix.os }}-${{ matrix.python-version }}.xml
          token: ${{ secrets.CODECOV_TOKEN }}
          fail_ci_if_error: false

      - name: 上传测试报告到 Codecov
        uses: codecov/codecov-action@v4
        continue-on-error: true
        with:
          files: ./junit-${{ matrix.os }}-${{ matrix.python-version }}.xml

      - name: 缓存 pytest
        uses: actions/cache@v4
        with:
          path: ~/.cache/pytest
          key: pytest-${{ matrix.os }}-${{ matrix.python-version }}-${{ hashFiles('pyproject.toml') }}
          restore-keys: |
            pytest-${{ matrix.os }}-${{ matrix.python-version }}-

  # ==========================================================
  # Job 3：构建产物（只在 main 分支和 tag 上跑）
  # ==========================================================
  build:
    name: Build package
    runs-on: ubuntu-latest
    timeout-minutes: 10
    needs: test                  # 测试不过不构建，避免发布坏包
    if: github.ref == 'refs/heads/main' || startsWith(github.ref, 'refs/tags/v')
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: 构建 wheel 与 sdist
        run: |
          python -m pip install --upgrade pip build twine
          python -m build            # 产物在 dist/

      - name: 校验元数据（防止发一个坏包到 PyPI）
        run: twine check dist/*

      - name: 安装产物并做冒烟测试
        run: |
          pip install dist/*.whl
          python -c "import my_package; print('版本:', my_package.__version__)"

      - uses: actions/upload-artifact@v4
        with:
          name: dist
          path: dist/
          retention-days: 7          # 不要永久保留，占空间

  # ==========================================================
  # Job 4：安全扫描 + 依赖审计
  # ==========================================================
  security:
    name: Security scan
    runs-on: ubuntu-latest
    timeout-minutes: 10
    steps:
      - uses: actions/checkout@v4
        with:
          persist-credentials: false   # 安全最佳实践：不需要时立刻丢弃凭据

      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: 依赖漏洞扫描
        run: |
          pip install pip-audit
          pip-audit --strict --progress-spinner off
          # 漏洞时退出码非 0 -> CI 失败。可以配 .pip-audit.toml 忽略已知误报

      - name: 代码密钥扫描
        uses: gitleaks/gitleaks-action@v2
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}

      - name: CodeQL 静态分析（GitHub 原生）
        uses: github/codeql-action/analyze@v3
        with:
          languages: python
          category: "/language:python"

  # ==========================================================
  # Job 5：CI 全绿后才触发部署
  # ==========================================================
  deploy:
    name: Deploy
    runs-on: ubuntu-latest
    timeout-minutes: 10
    needs: [test, build, security]
    # 双重保险：分支/环境保护规则必须同时满足
    if: github.ref == 'refs/heads/main'
    environment:
      name: production
      url: https://example.com
    steps:
      - uses: actions/checkout@v4

      - name: 部署到服务器
        env:
          DEPLOY_HOST: ${{ secrets.DEPLOY_HOST }}
          DEPLOY_KEY: ${{ secrets.DEPLOY_KEY }}
        run: |
          echo "${{ secrets.DEPLOY_KEY }}" > ~/.ssh/deploy_key
          chmod 600 ~/.ssh/deploy_key
          ssh-keyscan -H "$DEPLOY_HOST" >> ~/.ssh/known_hosts
          rsync -avz --delete dist/ user@"$DEPLOY_HOST":/srv/app/
          ssh user@"$DEPLOY_KEY" 'systemctl restart myapp'

      - name: 健康检查
        run: |
          for i in $(seq 1 10); do
            if curl -fsS https://example.com/health; then
              echo "✓ 部署成功"; exit 0
            fi
            sleep 5
          done
          echo "✗ 健康检查失败，回滚"; exit 1
```

**配套：只在 PR 上跑评论机器人**

```yaml
# .github/workflows/pr-comment.yml
name: PR Comment
on: pull_request

permissions:
  pull-requests: write      # 最小权限

jobs:
  comment:
    runs-on: ubuntu-latest
    if: github.event.pull_request.draft == false
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.11" }

      - run: pip install pytest-cov

      - name: 生成覆盖率摘要
        id: cov
        run: |
          pytest tests/unit --cov=src/my_package --cov-report=xml -q
          pip install coverage[toml]
          coverage json -o cov.json
          python -c "
          import json
          d = json.load(open('cov.json'))
          t = d['totals']['percent_covered']
          print(f'coverage={t:.2f}')" >> $GITHUB_OUTPUT

      - uses: actions/github-script@v7
        with:
          script: |
            const body = `## 测试结果 ✅
            \`\`\`
            覆盖率：${{ steps.cov.outputs.coverage }}%
            \`\`\``;
            github.rest.issues.createComment({
              issue_number: context.issue.number,
              owner: context.repo.owner,
              repo: context.repo.repo,
              body: body,
            });
```

---

## 8. 本地一键检查脚本

把"提交前要跑的所有检查"封装成一个脚本，本地和 CI 调用**同一个**：

```bash
#!/usr/bin/env bash
# scripts/check.sh —— 本地一键检查，与 CI 跑完全相同的规则
set -euo pipefail    # -e 出错即停；-u 未定义变量报错；-o pipefail 管道中任一失败即失败

# ---- 颜色输出：CI 里没有 TTY 时自动降级为无色 ----
if [[ -t 1 ]]; then
  RED=$'\033[31m'; GREEN=$'\033[32m'; YELLOW=$'\033[33m'; NC=$'\033[0m'
else
  RED=""; GREEN=""; YELLOW=""; NC=""
fi

START=$(date +%s)
FAILED=()

run_check() {
  local name="$1"; shift
  printf '%n▶ %s%s\n' "$GREEN" "$name" "$NC"
  if "$@"; then
    printf '  ✓ 通过\n'
  else
    printf '  %s✗ 失败%s\n' "$RED" "$NC"
    FAILED+=("$name")
  fi
}

echo "=============================================="
echo " 工程质量检查  $(date '+%Y-%m-%d %H:%M:%S')"
echo "  分支: $(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo '非 git 仓库')"
echo "=============================================="

# ---- 1. 快速卫生检查（秒级）----
run_check "字节码编译（语法检查）" python -m compileall -q src tests

# ---- 2. 格式与 lint ----
run_check "ruff format 检查"  ruff format --check .
run_check "ruff lint"          ruff check .
# 需要自动修复时手动执行：ruff check . --fix && ruff format .

# ---- 3. 类型检查 ----
run_check "mypy 类型检查"      mypy src/

# ---- 4. 测试 ----
# --no-cov 关闭覆盖率：本地快速迭代不需要，CI 里再开
run_check "单元测试"            pytest tests/unit -q --no-cov -m "not slow"
# 快速迭代：pytest tests/unit -q --no-cov -x --lf --ff  （-x 首个失败停、--lf 上次失败优先）

# ---- 5. 依赖安全 ----
run_check "依赖漏洞扫描"        pip-audit --strict --progress-spinner off

# ---- 6. 提交钩子自检 ----
if [[ -f .pre-commit-config.yaml ]]; then
  run_check "pre-commit 全部钩子" pre-commit run --all-files
fi

# ---- 汇总 ----
DURATION=$(( $(date +%s) - START ))
echo
echo "=============================================="
if [[ ${#FAILED[@]} -eq 0 ]]; then
  printf '%s全部通过 ✓  用时 %ss%s\n' "$GREEN" "$DURATION" "$NC"
  echo "可以提交了：git commit -m \"...\""
else
  printf '%s以下检查失败：%s\n' "$RED" "$NC"
  for item in "${FAILED[@]}"; do
    echo "  ✗ $item"
  done
  printf '用时 %ss\n' "$DURATION"
  echo "修好后再提交。常见修法："
  echo "  格式问题  -> ruff format . && ruff check . --fix"
  echo "  类型问题  -> mypy src/  看具体报错"
  echo "  想临时跳过-> git commit --no-verify（会绕过钩子，慎用）"
fi
echo "=============================================="

exit $([[ ${#FAILED[@]} -eq 0 ]] && echo 0 || echo 1)
```

**Windows 用户**可用 `check.ps1`：

```powershell
# scripts/check.ps1
$ErrorActionPreference = "Continue"
$checks = @(
    @{ Name = "语法检查";   Cmd = { python -m compileall -q src tests } },
    @{ Name = "格式检查";   Cmd = { ruff format --check . } },
    @{ Name = "lint";       Cmd = { ruff check . } },
    @{ Name = "类型检查";   Cmd = { mypy src/ } },
    @{ Name = "单元测试";   Cmd = { pytest tests/unit -q --no-cov -m "not slow" } }
)

$failed = @()
foreach ($check in $checks) {
    Write-Host "`n> $($check.Name)" -ForegroundColor Green
    & $check.Cmd
    if ($LASTEXITCODE -ne 0) { $failed += $check.Name }
}

if ($failed.Count -eq 0) {
    Write-Host "`n全部通过" -ForegroundColor Green
} else {
    Write-Host "`n失败项: $($failed -join ', ')" -ForegroundColor Red
    exit 1
}
```

**Git 钩子（可选，配合 check.sh）**：`.husky/pre-commit`（Node 环境）或直接用 pre-commit。

---

## 9. 完整的目录结构与文件职责

```text
my-project/
├── .github/
│   ├── workflows/
│   │   ├── ci.yml                  # CI 主流程（lint → test → build → security → deploy）
│   │   └── nightly.yml             # 每晚定时跑慢测试（性能回归、模糊测试）
│   ├── ISSUE_TEMPLATE/
│   │   ├── bug_report.md           # 缺陷模板（含复现步骤、日志、环境）
│   │   └── feature_request.md      # 需求模板
│   ├── PULL_REQUEST_TEMPLATE.md    # PR 模板（自检清单）
│   └── dependabot.yml              # 依赖自动升级
│
├── .husky/                          # 若不用 pre-commit 可用 husky
│   └── pre-commit
│
├── docs/
│   ├── index.md                     # 文档首页（mkdocs.yml 定义导航）
│   ├── architecture.md              # 架构说明：模块职责与依赖方向
│   ├── changelog.md                 # 变更记录（可用 towncrier 自动生成）
│   └── adr/                         # Architecture Decision Record 架构决策记录
│       ├── 0001-use-src-layout.md
│       └── 0002-choose-ruff-over-black-flake8.md
│
├── src/
│   └── my_package/                  # ★ 与 src 同名，这是 src layout 的关键
│       ├── __init__.py              # 导出版本号与公开 API
│       ├── py.typed                 # ★ 存在此文件（可为空）才表示包提供类型信息
│       ├── main.py                  # 入口，含 main() 与 if __name__
│       ├── config.py                # 配置加载（pydantic-settings 或 dataclass）
│       ├── cli.py                   # 命令行界面（click/typer）
│       ├── api/                     # HTTP 层：路由、请求校验、响应序列化
│       │   ├── __init__.py
│       │   ├── routes.py
│       │   ├── schemas.py           # 请求/响应的 pydantic 模型
│       │   └── deps.py              # FastAPI Depends 依赖注入
│       ├── core/                    # 核心业务：不依赖任何框架
│       │   ├── __init__.py
│       │   ├── models.py            # 领域模型（dataclass / pydantic）
│       │   ├── services.py          # 业务编排
│       │   └── exceptions.py        # 统一异常体系（见 06 章）
│       ├── db/                      # 数据访问层
│       │   ├── __init__.py
│       │   ├── session.py
│       │   ├── repository.py        # 仓储模式：业务层不直接写 SQL
│       │   └── migrations/          # alembic 迁移
│       └── utils/                   # 无业务含义的纯工具
│           ├── __init__.py
│           ├── logging.py           # 日志配置（见 05 章）
│           ├── retry.py             # 重试/熔断装饰器（见 06 章）
│           └── text.py
│
├── tests/
│   ├── conftest.py                  # ★ 全局 fixture（session 级）
│   ├── unit/                        # 单元测试：快、无 I/O、占 70%
│   │   ├── conftest.py
│   │   └── test_services.py
│   ├── integration/                 # 集成测试：真数据库/真 Redis，占 20%
│   │   ├── conftest.py              # 用 testcontainers 起真实依赖
│   │   └── test_repository.py
│   └── e2e/                         # 端到端测试：起完整服务，占 10%
│       └── test_api.py
│
├── scripts/
│   ├── check.sh                     # 本地一键检查（与 CI 同源）
│   ├── check.ps1                    # Windows 版
│   ├── bootstrap.py                 # 数据初始化
│   └── migrate_prod.py              # 生产迁移
│
├── benchmarks/                      # 性能基准（pytest-benchmark / asv）
│   └── test_bench_core.py
│
├── .venv/                           # 虚拟环境，必须在 .gitignore 里
├── build/ dist/ *.egg-info/         # 构建产物，必须在 .gitignore 里
│
├── .env.example                     # 环境变量模板（★ 提交，.env 绝不提交）
├── .env                             # 本地真实环境变量（★ 加入 .gitignore）
├── .gitignore
├── .dockerignore
├── Dockerfile
├── docker-compose.yml
├── Makefile                         # 把常用命令收敛成 make lint / make test
│
├── .pre-commit-config.yaml
├── pyproject.toml                   # ★ 唯一配置中心
├── requirements.txt                 # 锁定版本（生产部署用）
├── requirements-dev.txt
├── CHANGELOG.md
├── CONTRIBUTING.md                  # 贡献指南
├── LICENSE
├── README.md
└── mkdocs.yml                       # 文档站点配置
```

**几个容易踩的坑：**

| 坑 | 后果 | 正确做法 |
| --- | --- | --- |
| `src/` 下没有 `py.typed` | 使用方 mypy 报 "missing imports" | 建空文件，打进包里 |
| `src/` 与包目录不同名 | 打包后 `import my_package` 失败 | 必须 `src/my_package/` |
| 忘记 `.gitignore` 里的 `.env` | 密钥泄露 | 提交 `.env.example`，`.env` 加 ignore |
| 迁移脚本被 lint | 每次迁移都要加 `# noqa` | ruff `per-file-ignores` 豁免 |
| 测试互相依赖执行顺序 | 单跑必挂 | 每个用例自己准备数据 |

---

## 10. 落地顺序与常见坑

**推荐引入顺序**（每步都能独立产生价值，不用一次做完）：

```text
第 1 周  pyproject.toml 建起来 + ruff（先只开 E/F 两条规则）
         → 立刻消除语法错误、未用导入、变量名问题

第 2 周  ruff 规则开到 I + B + UP + SIM
         → 导入自动排序、消除易错模式、语法现代化

第 3 周  pytest 配置 + conftest.py 抽取
         → 测试跑得快、可维护

第 4 周  pre-commit 装上
         → 问题在本地就拦住，不再等到 CI

第 5 周  mypy 从新模块开始，老模块逐目录开
         → 类型覆盖渐进提升，不被一次性报错淹没

第 6 周  GitHub Actions CI 上线（lint + test）
         → 团队协作的最低保障

第 7 周  加覆盖率门槛 + build + security
         → 可以放心发布了
```

**八个常见坑：**

1. **CI 与本地配置不一致** —— 最高频的事故来源。
   解决：所有配置进 `pyproject.toml`，本地和 CI 都调 `scripts/check.sh`。

2. **pre-commit 本地过、CI 挂** —— 通常是 `additional_dependencies` 缺了某个库。
   解决：mypy 钩子必须列出依赖的 stub 包，否则它看不到真实类型。

3. **pre-commit 缓存了旧代码** —— `pre-commit clean` 强制清缓存。

4. **`addopts` 写了两遍 TOML 会报错** —— 同一 key 不能重复。
   解决：覆盖率参数放 CI 命令行，本地用 `--no-cov` 关掉。

5. **覆盖率只看数字不看报告** —— 85% 但全是 `__init__.py` 的平凡分支。
   解决：终端加 `--cov-report=term-missing`，人肉看一眼漏了什么。

6. **filterwarnings 里没有 `"error"`** —— `DeprecationWarning` 堆积三年后一次性爆炸。
   解决：一开始就设 `error`，新警告立刻可见（旧的单独 ignore）。

7. **CI 矩阵没有 `fail-fast: false`** —— 一个版本失败，其他版本全部被取消，看不到全貌。

8. **`--strict-markers` 没开** —— `@pytest.mark.tyop` 打错字会被静默忽略，
   标记永远不会生效，测试白写。

**一条经验法则：**

> 任何一条检查规则，如果不能在 3 分钟内解释清楚为什么存在，就先别加。
> 工具配置本身也是需要维护的代码 —— 越复杂越容易变成没人敢动的摆设。
