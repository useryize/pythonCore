# 09 · README 模板与完整示例

> 本文件提供两份内容：
> - **上半部分**：可复用的 README 模板（占位符 `{{...}}`，复制后替换即可）
> - **下半部分**：一份填好的完整示例（可直接对照参考）

---

## 目录

- [一、为什么 README 很重要](#一为什么-readme-很重要)
- [二、README 模板（复制即用）](#二readme-模板复制即用)
- [三、完整示例](#三完整示例)
- [四、各章节写法要点](#四各章节写法要点)
- [五、常见问题](#五常见问题)

---

## 一、为什么 README 很重要

```text
README 是你项目的「门面」，读者只有 30 秒注意力：

  30 秒内没搞懂"这个项目干什么、怎么装、怎么跑"，读者就走了。

GitHub 数据（经验值）：
  · 带截图和 badging 的项目，访问转化率高 2~3 倍
  · 有 Quick Start 的项目，首次使用成功率显著更高
  · 有 CONTRIBUTING.md 的项目，PR 数量更多

对新成员：README 决定他多久能独立跑起来
对用户  ：README 决定他会不会用你的库
对未来的你：README 是三个月后唯一还记得的设计意图
```

**写作顺序建议（按读者心理）**：

```text
1. 一句话说清楚【做什么】+ 一张截图     ← 30 秒
2. 关键特性列表                        ← 20 秒
3. 安装（能直接复制粘贴的命令）         ← 20 秒
4. 快速上手（最小可运行示例）           ← 40 秒
5. 详细用法 / API                      ← 需要时再查
6. 配置项表格                          ← 需要时再查
7. 开发、测试、贡献                     ← 面向贡献者
8. 许可证                              ← 合规要求
```

---

## 二、README 模板（复制即用）

````markdown
# {{项目名称}}

{{一句话描述：动词开头，说清楚"帮你解决什么问题"，不超过 100 字符}}

[![Python 版本](https://img.shields.io/badge/python-{{3.10|3.11|3.12}}-blue.svg)](https://www.python.org/)
[![许可证](https://img.shields.io/badge/license-{{MIT|Apache-2.0}}-green.svg)](LICENSE)
[![PyPI 版本](https://img.shields.io/badge/pypi-{{1.0.0}}-blue.svg)](https://pypi.org/project/{{name}}/)
[![构建状态](https://img.shields.io/badge/build-passing-brightgreen.svg)](https://github.com/{{org}}/{{name}}/actions)
[![代码覆盖率](https://img.shields.io/badge/coverage-{{85}}%25-brightgreen.svg)](https://github.com/{{org}}/{{name}})
[![许可证](https://img.shields.io/badge/代码许可证-MIT-yellow.svg)](LICENSE)
[![贡献者](https://img.shields.io/badge/contributors-{{12}}-orange.svg)](graphs/contributors)
[![最后提交](https://img.shields.io/badge/last_commit-{{2024-01-01}}-blue.svg)](commits/main)

{{用一句话说明它相对现有方案的区别 —— 这是别人决定要不要用的关键}}

## 📸 效果演示

{{截图 / GIF / 终端录屏。对 CLI 项目用终端录屏，对 GUI 项目用 GIF}}

```text
{{终端输出样例，真实粘贴，不要手打}}
```

## ✨ 特性

- ✅ {{特性 1，面向用户价值而非技术实现}}
- ✅ {{特性 2}}
- ✅ {{特性 3}}
- ⚡ {{性能相关特性：快 10 倍 / 零依赖 / 启动 < 1ms}}
- 🔒 {{安全、类型完备等信任类特性}}
- 🐍 {{Python 3.10+ 原生类型标注}}

## 📋 环境要求

| 依赖 | 最低版本 | 说明 |
| --- | --- | --- |
| Python | 3.10 | 依赖 PEP 604 联合类型语法 |
| {{其他系统依赖}} | {{版本}} | {{说明}} |

## 📦 安装

```bash
# 从 PyPI 安装（推荐）
pip install {{name}}

# 指定版本
pip install {{name}}==1.2.0

# 开发模式安装（含开发依赖）
pip install -e ".[dev]"

# 从源码安装
git clone https://github.com/{{org}}/{{name}}.git
cd {{name}}
pip install -e ".[dev]"
```

<details>
<summary>使用 uv / poetry / conda</summary>

```bash
uv add {{name}}                    # uv
poetry add {{name}}                # poetry
conda install -c conda-forge {{name}}  # conda
```

</details>

## 🚀 快速开始

### 方式一：命令行

```bash
{{name}} --help
{{name}} run --input data.csv --output result.json
```

### 方式二：作为库调用

```python
from {{package}} import {{MainClass}}

# 最小可运行示例 —— 读者复制就能看到结果
client = {{MainClass}}(api_key="{{your-key}}")
result = client.process("示例数据")
print(result)
```

预期输出：

```text
{{真实的输出内容}}
```

<details>
<summary>更多用法示例</summary>

### 异步用法

```python
import asyncio
from {{package}} import AsyncClient

async def main() -> None:
    client = AsyncClient()
    results = await asyncio.gather(*[client.fetch(i) for i in range(10)])
    print(results)

asyncio.run(main())
```

### 自定义配置

```python
config = {{MainClass}}.Config(
    timeout=30,
    max_retries=3,
    verbose=True,
)
client = {{MainClass}}(config=config)
```

</details>

## ⚙️ 配置项

支持三种配置方式，**优先级：环境变量 > 配置文件 > 默认值**

| 配置项 | 类型 | 默认值 | 环境变量 | 说明 |
| --- | --- | --- | --- | --- |
| `api_key` | `str` | 无（必填） | `{{NAME}}_API_KEY` | 服务端 API 密钥 |
| `timeout` | `int` | `30` | `{{NAME}}_TIMEOUT` | 超时时间（秒） |
| `max_retries` | `int` | `3` | `{{NAME}}_MAX_RETRIES` | 最大重试次数 |
| `log_level` | `str` | `"INFO"` | `{{NAME}}_LOG_LEVEL` | 日志级别 |
| `cache_dir` | `Path` | `~/.cache/{{name}}` | `{{NAME}}_CACHE_DIR` | 缓存目录 |

```bash
# 环境变量配置示例
export {{NAME}}_API_KEY="sk-xxxxx"
export {{NAME}}_LOG_LEVEL="DEBUG"

# 配置文件（toml）
cat > {{name}}.toml <<EOF
api_key = "sk-xxxxx"
timeout = 60
max_retries = 5
EOF
```

## 📖 API 参考

### `{{MainClass}}`

```python
class {{MainClass}}:
    def __init__(self, api_key: str, *, timeout: int = 30) -> None: ...
    def process(self, data: str, *, options: dict | None = None) -> Result: ...
    def close(self) -> None: ...
```

| 方法 | 参数 | 返回值 | 说明 |
| --- | --- | --- | --- |
| `process` | `data: str` | `Result` | 处理输入数据 |
| `close` | 无 | `None` | 释放资源，必须调用 |

完整的 API 文档见 [官方文档](https://{{name}}.readthedocs.io)。

## ❓ 常见问题（FAQ）

<details>
<summary><b>Q: 安装时报 <code>No matching distribution found</code>？</b></summary>

你的 Python 版本低于项目要求。检查：

```bash
python --version   # 需要 3.10+
```

</details>

<details>
<summary><b>Q: Windows 下如何运行？</b></summary>

项目同时支持 Windows / macOS / Linux，无需额外配置。

</details>

<details>
<summary><b>Q: 如何贡献代码？</b></summary>

见 [CONTRIBUTING.md](CONTRIBUTING.md)。基本流程：

```bash
git fork && git clone https://github.com/你的用户名/{{name}}.git
git checkout -b feat/your-feature
# ... 编写代码和测试 ...
bash scripts/check.sh        # 本地跑全部检查
git commit -m "feat: 新功能描述"
git push origin feat/your-feature
# 然后在 GitHub 上发起 PR
```

</details>

## 🛠️ 开发

```bash
# 克隆并安装开发环境
git clone https://github.com/{{org}}/{{name}}.git
cd {{name}}
pip install -e ".[dev]"
pre-commit install          # 安装提交钩子

# 日常命令
bash scripts/check.sh        # 一键跑完 lint + 类型 + 测试（推荐）
ruff check . --fix           # 修 lint 问题
ruff format .                # 格式化
mypy src/                    # 类型检查
pytest -v                    # 跑测试
pytest --lf                  # 只跑上次失败的用例
```

### 项目结构

```text
{{name}}/
├── src/{{name}}/        # 业务代码
├── tests/               # 自动化测试
│   ├── unit/
│   └── integration/
├── docs/                # 文档
├── scripts/check.sh     # 本地一键检查
└── pyproject.toml       # 唯一配置中心
```

## 🧪 测试

```bash
pytest                                  # 全部测试
pytest --cov=src/{{name}} --cov-report=html   # 带覆盖率
pytest -m "not slow"                    # 跳过慢测试
```

## 🤝 贡献指南

欢迎所有形式的贡献！请先阅读 [CONTRIBUTING.md](CONTRIBUTING.md)。

提交信息遵循 [Conventional Commits](https://www.conventionalcommits.org/)：

```text
feat(auth): 增加双因素认证
fix(orders): 修复并发下单导致的库存超卖
docs(readme): 补充 Docker 部署步骤
```

## 📄 许可证

本项目采用 [MIT 许可证](LICENSE) —— 详见 [LICENSE](LICENSE) 文件。

## 🙏 致谢

- 感谢所有 [贡献者](graphs/contributors)
- 灵感来自 [{{参考项目}}]({{链接}})

## 📊 项目统计

[![Star History](https://api.star-history.com/svg?repos={{org}}/{{name}}&type=Date)](https://star-history.com/#{{org}}/{{name}}&Date)
````

---

## 三、完整示例

> 以下是一个 CLI 工具项目的完整 README，可直接作为写作参照。

````markdown
# logcraft

**用装饰器一行代码给 Python 函数加上结构化日志与耗时统计的零依赖工具库。**

[![Python](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![PyPI](https://img.shields.io/badge/pypi-v2.1.0-blue.svg)](https://pypi.org/project/logcraft/)
[![Build](https://img.shields.io/badge/build-passing-brightgreen.svg)](https://github.com/demo/logcraft/actions)
[![Coverage](https://img.shields.io/badge/coverage-94%25-brightgreen.svg)](https://github.com/demo/logcraft)
[![License CN](https://img.shields.io/badge/%E8%AE%B8%E5%8F%AF%E8%AF%81-MIT-yellow.svg)](LICENSE)
[![Python 风格](https://img.shields.io/badge/code%20style-ruff-261230.svg)](https://github.com/astral-sh/ruff)

相比 `logging` + 手写装饰器，logcraft 让函数可观测性只需一行 `@traced()`，
并且开箱提供 JSON 结构化输出与性能耗时采集。

## 📸 效果演示

```text
$ logcraft-demo process --input data.csv

2026-01-15 14:32:07.123 INFO  [orders] 开始处理 order_id=8842 items=3
2026-01-15 14:32:07.124 INFO  [orders] 校验参数完成 cost=0.8ms
2026-01-15 14:32:07.451 INFO  [orders] 调用支付网关 txn_id=txn_9f3a cost=326.4ms
2026-01-15 14:32:07.452 INFO  [orders] 处理完成 total_cost=329.1ms status=success
2026-01-15 14:32:07.453 WARN  [inventory] 库存不足 sku=SKU-001 requested=5 available=2
2026-01-15 14:32:07.454 ERROR [payment] 扣款失败 amount=299.00 reason=余额不足
2026-01-15 14:32:07.455 ERROR [payment] 完整堆栈已记录至 logs/error.jsonl

统计：处理 1 单，耗时 329.1ms，失败 1 单
```

JSON 格式（便于 ELK / Loki 采集）：

```json
{
  "timestamp": "2026-01-15T14:32:07.452+08:00",
  "level": "INFO",
  "logger": "orders",
  "function": "process_order",
  "line": 142,
  "message": "处理完成",
  "cost_ms": 329.1,
  "request_id": "req-abc-123",
  "user_id": 10086
}
```

## ✨ 特性

- ✅ **一行接入** —— `@traced()` 装饰器，不改动任何业务代码
- ✅ **结构化日志** —— 自动输出 JSON，可直接被 ELK / Loki / CloudWatch 采集
- ✅ **耗时统计** —— 自动记录每个函数的 `cost_ms`，慢函数自动标红
- ✅ **异常捕获** —— 自动记录完整堆栈与上下文，不用再写 try/except
- ⚡ **零依赖** —— 仅用标准库，安装包 12 KB
- 🔒 **敏感信息脱敏** —— 自动遮蔽手机号、身份证、卡号
- 🐍 **类型完备** —— 全量类型注解，`py.typed` 已打包

## 📋 环境要求

| 依赖 | 最低版本 | 说明 |
| --- | --- | --- |
| Python | 3.10 | 依赖 PEP 604 联合类型语法 |
| 操作系统 | 任意 | Windows / macOS / Linux 全平台支持 |

## 📦 安装

```bash
# 从 PyPI 安装（推荐）
pip install logcraft

# 指定版本
pip install logcraft==2.1.0

# 开发模式安装（含开发依赖）
git clone https://github.com/demo/logcraft.git
cd logcraft
pip install -e ".[dev]"
```

<details>
<summary>使用 uv / poetry / conda</summary>

```bash
uv add logcraft
poetry add logcraft
conda install -c conda-forge logcraft
```

</details>

## 🚀 快速开始

### 方式一：装饰器（推荐）

```python
from logcraft import traced

@traced("orders", slow_threshold_ms=100)
def process_order(order_id: int, items: list) -> dict:
    """处理订单 —— 无需任何日志代码。"""
    validate(items)
    result = charge_gateway(order_id)
    return {"order_id": order_id, "status": "success"}

# 调用后自动输出日志、耗时、异常堆栈
process_order(8842, [{"sku": "SKU-001", "qty": 2}])
```

### 方式二：上下文管理器

```python
from logcraft import span

def process_order(order_id: int):
    with span("orders", "处理订单", order_id=order_id) as s:
        validate(items)
        s.cost_ms = charge_gateway(order_id)     # 手动标记关键阶段耗时
```

### 方式三：CLI（本地调试）

```bash
logcraft-demo process --input data.csv --level DEBUG
logcraft-demo config --show
```

<details>
<summary>更多用法</summary>

### 异步函数支持

```python
@traced("api")
async def fetch_user(user_id: int) -> dict:
    return await client.get(f"/users/{user_id}")
```

`traced` 同时支持同步与异步函数，无需区分。

### 全局配置

```python
from logcraft import configure

configure(
    level="DEBUG",
    output="logs/app.jsonl",     # JSON 文件
    max_bytes=10 * 1024 * 1024,  # 10MB 轮转
    backup_count=5,
    slow_threshold_ms=200,       # 超过 200ms 标记为慢
    redact=True,                 # 开启敏感信息脱敏
)
```

### 与 FastAPI 集成

```python
from logcraft.contrib.fastapi import LogcraftMiddleware

app = FastAPI()
app.add_middleware(LogcraftMiddleware)   # 自动记录每个请求的耗时与响应码
```

</details>

## ⚙️ 配置项

支持三种配置方式，**优先级：环境变量 > 配置文件 > 默认值**

| 配置项 | 类型 | 默认值 | 环境变量 | 说明 |
| --- | --- | --- | --- | --- |
| `level` | `str` | `"INFO"` | `LOGCRAFT_LEVEL` | 日志级别 |
| `output` | `str \| Path` | `None` | `LOGCRAFT_OUTPUT` | 日志文件路径，`None` 表示只输出到终端 |
| `format` | `str` | `"json"` | `LOGCRAFT_FORMAT` | `json` 或 `text` |
| `max_bytes` | `int` | `10485760` | `LOGCRAFT_MAX_BYTES` | 单文件大小上限，超出后轮转 |
| `backup_count` | `int` | `5` | `LOGCRAFT_BACKUP_COUNT` | 保留的历史日志份数 |
| `slow_threshold_ms` | `float` | `100` | `LOGCRAFT_SLOW_MS` | 慢函数阈值（毫秒） |
| `redact` | `bool` | `True` | `LOGCRAFT_REDACT` | 是否脱敏敏感信息 |
| `include_source` | `bool` | `True` | `LOGCRAFT_SOURCE` | 是否记录文件名与行号 |

```bash
# 环境变量配置
export LOGCRAFT_LEVEL="DEBUG"
export LOGCRAFT_SLOW_MS="300"
```

```toml
# 配置文件 logcraft.toml
level = "DEBUG"
output = "logs/app.jsonl"
slow_threshold_ms = 200
```

```python
# 代码配置（优先级最高）
from logcraft import configure
configure(level="INFO", slow_threshold_ms=500)
```

## 📖 API 参考

### `@traced`

```python
def traced(
    logger_name: str | None = None,
    *,
    slow_threshold_ms: float = 100,
    level: str = "INFO",
    capture_args: bool = True,
    reraise: bool = True,
) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """为函数添加结构化日志与耗时统计。

    :param logger_name:      logger 名称，None 时用函数所在模块名
    :param slow_threshold_ms: 超过该毫秒数时日志级别升为 WARNING
    :param level:            正常日志级别
    :param capture_args:     是否记录函数参数（敏感场景应关闭）
    :param reraise:          记录异常后是否继续抛出（False = 吞掉异常）
    """
```

| 参数 | 类型 | 默认 | 说明 |
| --- | --- | --- | --- |
| `logger_name` | `str \| None` | `None` | logger 名称 |
| `slow_threshold_ms` | `float` | `100` | 慢函数阈值 |
| `level` | `str` | `"INFO"` | 日志级别 |
| `capture_args` | `bool` | `True` | 是否记录参数 |
| `reraise` | `bool` | `True` | 异常是否继续抛出 |

### `span`

```python
with span(name: str, message: str, **context) -> SpanContext:
    ...
```

上下文管理器形式，可手动设置 `cost_ms` 标记关键阶段。

完整文档见 [readthedocs](https://logcraft.readthedocs.io)。

## ❓ 常见问题（FAQ）

<details>
<summary><b>Q: 会不会影响性能？</b></summary>

单次装饰开销约 3~8 微秒（实测：100 万次调用耗时 4.2 秒，原始耗时 0.9 秒）。
对于 I/O 密集或耗时 > 1ms 的函数，开销占比可忽略。

如果你在超高频的热路径上使用，可以关掉耗时统计：

```python
@traced("hot", slow_threshold_ms=-1)   # -1 表示不启用耗时采集
```

</details>

<details>
<summary><b>Q: 会记录函数参数吗？会不会泄露敏感信息？</b></summary>

默认会记录参数，但开启 `redact=True` 时自动遮蔽常见敏感格式
（手机号、身份证、银行卡、password 字段）。

如果要完全关闭：

```python
@traced("secure", capture_args=False)
```

</details>

<details>
<summary><b>Q: 异常会被吞掉吗？</b></summary>

不会。默认 `reraise=True`，即记录完堆栈后继续抛出，行为与不装饰时完全一致。
若你希望某些函数"记录但不抛"，显式设置 `reraise=False`。

</details>

<details>
<summary><b>Q: 与已有的 logging 配置冲突吗？</b></summary>

不冲突。logcraft 只调用 `logging.getLogger()` 获取 logger，
不修改任何 handler。已有的 handler 会继续按原配置输出。

</details>

<details>
<summary><b>Q: 如何贡献代码？</b></summary>

见 [CONTRIBUTING.md](CONTRIBUTING.md)。

</details>

## 🛠️ 开发

```bash
git clone https://github.com/demo/logcraft.git
cd logcraft
pip install -e ".[dev]"
pre-commit install
```

### 项目结构

```text
logcraft/
├── src/logcraft/         # 业务代码
│   ├── __init__.py       # 公开 API
│   ├── decorators.py     # @traced 实现
│   ├── context.py        # span 上下文管理器
│   ├── config.py         # 配置加载
│   ├── formatter.py      # JSON / 文本格式化
│   └── redaction.py      # 敏感信息脱敏
├── tests/                # 自动化测试
│   ├── unit/             # 单元测试（覆盖率 94%）
│   └── integration/      # 集成测试
├── benchmarks/           # 性能基准
├── scripts/check.sh      # 本地一键检查
└── pyproject.toml        # 唯一配置中心
```

### 常用命令

```bash
bash scripts/check.sh        # 一键跑完 lint + 类型 + 测试（推荐）
ruff check . --fix           # 修 lint 问题
ruff format .                # 格式化
mypy src/                    # 类型检查
pytest -v                    # 跑测试
pytest --lf                  # 只跑上次失败的
pytest --benchmarks          # 跑性能基准
```

## 🧪 测试

```bash
pytest                                          # 全部测试
pytest --cov=src/logcraft --cov-report=html     # 带覆盖率报告
pytest -m "not slow"                            # 跳过慢测试
```

## 🤝 贡献指南

欢迎所有形式的贡献！请先阅读 [CONTRIBUTING.md](CONTRIBUTING.md)。

提交信息遵循 [Conventional Commits](https://www.conventionalcommits.org/)：

```text
feat(redact): 支持自定义脱敏规则
fix(formatter): 修复并发写日志时的字段错乱
perf(decorators): 用 functools.wraps 保留签名，耗时降低 30%
docs(readme): 补充性能开销说明
```

**开发流程**：

1. 先开 issue 讨论（非 trivial 改动）
2. 从 `main` 切分支：`git checkout -b feat/xxx`
3. 写代码 **和测试**（覆盖率不能下降）
4. 跑 `bash scripts/check.sh` 确保全绿
5. 提交 + 推送 + 发 PR
6. CI 通过后由 maintainer 合并（squash merge）

## 📄 许可证

本项目采用 [MIT 许可证](LICENSE)。

```text
MIT License

Copyright (c) 2026 logcraft contributors

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, ...
```

## 🙏 致谢

- 感谢所有 [贡献者](graphs/contributors)
- 灵感来自 [structlog](https://www.structlog.org/) 与 [tenacity](https://tenacity.readthedocs.io/)
- 徽章样式来自 [shields.io](https://shields.io/)

## 📊 项目统计

[![Star History](https://api.star-history.com/svg?repos=demo/logcraft&type=Date)](https://star-history.com/#demo/logcraft&Date)
````

---

## 四、各章节写法要点

### 1. 标题 + 一句话描述

```markdown
# 项目名

动词开头，说明【帮用户解决什么问题】，不超过 100 字符。
```

| ❌ 不好 | ✅ 好 |
| --- | --- |
| 一个高效的 Python 工具库 | 一行代码给函数加上结构化日志与耗时统计 |
| 基于装饰器的日志中间件 | 让你不用写 try/except 也能拿到完整调用链 |
| This is a library | 用一行装饰器替代 30 行日志样板代码 |

> 读者只关心**他的问题被解决了没有**，不关心你用了什么技术。

### 2. 徽章（Badges）

```markdown
[![构建状态](https://img.shields.io/badge/build-passing-brightgreen.svg)](链接)
[![PyPI 版本](https://img.shields.io/badge/pypi-v1.0.0-blue.svg)](https://pypi.org/project/name/)
[![Python 版本](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://python.org)
[![代码覆盖率](https://img.shields.io/badge/coverage-85%25-brightgreen.svg)](链接)
[![许可证](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
```

**选择原则**：

| 徽章 | 作用 | 优先级 |
| --- | --- | --- |
| 构建状态 | 一眼看出能不能用 | ⭐⭐⭐ |
| PyPI 版本 | 当前稳定版本 | ⭐⭐⭐ |
| Python 版本 | 判断兼容性 | ⭐⭐⭐ |
| 覆盖率 | 反映项目质量 | ⭐⭐ |
| 许可证 | 合规前提 | ⭐⭐ |
| 代码风格 | 展示工程规范 | ⭐ |

> **别放**：下载量、Star 数、公众号二维码 —— 与"能不能用你的库"无关。

### 3. 安装

```markdown
```bash
pip install 包名          # 只有一行时，不要展开成一堆
```
```

**铁律：命令必须能直接复制粘贴执行**，不要出现占位符或伪代码。

如果项目还在开发阶段，诚实标注：

```markdown
> ⚠️ 本项目处于 0.x 阶段，API 可能变更，不建议用于生产环境。
```

### 4. 快速开始

```markdown
### 方式一：<最推荐的方式>
### 方式二：<备选>
<details><summary>更多用法</summary> ... </details>
```

原则：

- **第一个示例必须能跑出结果**，读者才有信心继续
- 提供"预期输出"，让读者知道自己是否成功
- 复杂用法折叠进 `<details>`，保持首屏清爽

```python
# ❌ 不好：片段化，读者拼不出完整程序
client = Client(key)
result = client.do()

# ✅ 好：完整可运行
from logcraft import traced

@traced("demo")
def hello(name: str) -> str:
    return f"Hello, {name}"

print(hello("World"))
# 输出：2026-01-15 14:32:07 INFO [demo] hello cost=0.3ms name='World'
```

### 5. 配置项表格

```markdown
| 配置项 | 类型 | 默认值 | 环境变量 | 说明 |
| --- | --- | --- | --- | --- |
```

- 类型标注清楚：`int` / `bool` / `str \| Path` / `list[str]`
- **默认值必须写**，用户要能判断"不配会怎样"
- 有环境变量的一律列出，方便容器化部署

### 6. 常见问题

```markdown
<details>
<summary><b>Q: 问题描述？</b></summary>

答案（含可复制的命令）

</details>
```

把 issue 区被问得最多的 5~10 个问题整理到这里，能显著减少重复提问。
**答案要具体到可复制执行的代码**，而不是"请检查你的配置"。

### 7. 开发与贡献

必须包含这几块：

```text
克隆命令
安装开发依赖命令
一键检查命令（这是贡献者最需要知道的）
常用命令列表
项目结构（让人快速定位代码）
提交信息规范
PR 流程
```

### 8. 许可证

```markdown
## 📄 许可证

本项目采用 [MIT 许可证](LICENSE)。
```

**必须存在 `LICENSE` 文件**，且内容与 README 声明一致。
版权年份和持有人要与项目实际情况相符。

### 9. 致谢

```markdown
## 🙏 致谢

- 感谢所有 [贡献者](graphs/contributors)
- 灵感来自 [参考项目](链接)
```

这一节成本极低，但对开源社区的友好度影响很大。

---

## 五、常见问题

<details>
<summary><b>Q: README 要写多长？</b></summary>

**首屏 30 秒可读完，全文不超过 5 分钟**。

超过 5 分钟没人会读完。详细文档放 docs/，README 只放入口和关键信息。

</details>

<details>
<summary><b>Q: 中英文哪个好？</b></summary>

看目标用户：

| 目标 | 建议 |
| --- | --- |
| 国内团队 / 中文用户 | 中文正文 + 英文代码注释 |
| 国际开源项目 | 英文为主，另建 README.zh-CN.md |
| 两者都要 | README.md（英文）+ README.zh-CN.md（中文），互相链接 |

```markdown
[English](README.md) | [简体中文](README.zh-CN.md)
```

</details>

<details>
<summary><b>Q: 截图还是 GIF？</b></summary>

| 项目类型 | 推荐 |
| --- | --- |
| CLI 工具 | 终端录屏 GIF，或直接贴代码块（更清晰、可搜索） |
| GUI 应用 | GIF 或多图并排 |
| 库 | 代码块 + 预期输出即可 |

**CLI 项目直接用代码块反而更好**：文本可搜索、可复制、不加载慢。
如果用了 shell 装饰（❯ 符号、颜色），就用 `<pre>` 包起来保留格式。

</details>

<details>
<summary><b>Q: 要不要写架构说明？</b></summary>

README 里放**简化版**（就一个目录树 + 每层一句话职责），
完整架构图和设计决策放 `docs/architecture.md`。

判断标准：新成员看了 README 后知道"代码该放在哪个文件"吗？

</details>

<details>
<summary><b>Q: 表格在窄屏手机上会不会破？</b></summary>

会。列数控制在 5 列以内，长内容用 `<details>` 折叠。

GitHub 的 Markdown 表格支持对齐语法，务必用上：

```markdown
| 配置项 | 类型 | 默认值 | 说明 |
| :--- | :--- | :--- | :--- |
| 名称 | `str` | `""` | 必填 |
```

</details>

<details>
<summary><b>Q: 需要放 Emoji 图标吗？</b></summary>

适度使用有帮助（视觉分区），但要克制：

| ✅ 推荐 | ❌ 过度 |
| --- | --- |
| 每节标题一个图标 | 每个列表项都带图标 |
| 图标含义直观 | 花哨且无实际含义 |

常用约定：📦 安装 🚀 快速开始 ⚙️ 配置 📖 API ❓ FAQ 🛠️ 开发 🤝 贡献 📄 许可

</details>

<details>
<summary><b>Q: README 里的版本号要不要手动同步？</b></summary>

**不要**。用自动化工具：

```bash
# CI 里自动把 pyproject.toml 的 version 替换进 README
sed -i "s/{{VERSION}}/$(python -c 'import tomllib; print(tomllib.load(open("pyproject.toml","rb"))["project"]["version"])')/" README.md
```

或者用 [bump-my-version](https://github.com/callowayproject/bump-my-version) 一并处理。

</details>

<details>
<summary><b>Q: 什么时候该写 README？</b></summary>

**项目创建的第一天**，不是发布前一天。

写 README 会强迫你回答"这项目到底解决什么问题"——
答不上来，说明项目本身还没想清楚。

</details>
