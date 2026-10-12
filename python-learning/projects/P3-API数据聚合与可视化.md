# P3 · API 数据聚合与可视化

> **难度**：★★★★　**预计工时**：10-15 小时
> **目标**：练标准库深度使用、类型标注、pytest、ruff/mypy、数据可视化。这是**能写进简历**的项目。

---

## 一、项目需求

聚合多个公开 API 的数据，生成一份可交互的分析报告。

### 数据源（任选两个，全部为公开无鉴权接口）

| API | 数据内容 |
|---|---|
| `api.open-meteo.com` | 天气/历史气候数据 |
| `jsonplaceholder.typicode.com` | 测试用用户/帖子数据 |
| `api.github.com` | 仓库 star / issue 数据（免鉴权可读） |
| `restcountries.com` | 国家信息 |
| Hacker News Firebase API | 新闻榜单 |

**建议组合**：天气 API（时序数据） + GitHub API（元数据）+ 国家 API（维度数据）

### 流水线

```
并发抓取 → 数据清洗 → 关联聚合 → 统计分析 → 可视化 → HTML 报告输出
```

---

## 二、功能需求

| 模块 | 说明 | 必须 |
|---|---|---|
| `fetcher` | 异步并发抓取，带超时、重试、限流 | ✅ |
| `cache` | 本地缓存（JSON/文件），TTL 过期重取 | ✅ |
| `models` | 所有 API 数据的 dataclass + 校验 | ✅ |
| `transformers` | 多源数据关联、字段对齐 | ✅ |
| `analyzers` | 统计指标计算 | ✅ |
| `visualizers` | matplotlib 图表 + 交互式 HTML（Plotly/ECharts） | ✅ |
| `report` | 生成 HTML 报告（内嵌图表） | ✅ |
| `config` | 配置分层：默认值 → 配置文件 → 环境变量 → 命令行 | ✅ |
| `cli` | 命令行入口 | ✅ |

### 必须实现的能力

1. **异步并发抓取**：用 `asyncio` + `httpx`，同时抓 5+ 个数据源，带 `Semaphore` 限流
2. **重试机制**：指数退避（1s → 2s → 4s），最多 3 次
3. **本地缓存**：24 小时 TTL，避免重复请求
4. **失败降级**：某个源挂了不影响整体，用已有缓存或跳过并记录
5. **数据校验**：所有外部数据进入系统前必须校验，脏数据隔离
6. **至少 3 张图**：趋势图（时序）、分布图（Top 排名/占比）、对比图
7. **HTML 报告**：自包含单文件，含关键指标卡片 + 图表

---

## 三、加分项（★★★★★ 目标）

- 完整类型注解，`mypy --strict` 通过
- `pytest` 覆盖率 ≥ 75%，用 `pytest.mark.asyncio` 测异步，用 `respx`/`aioresponses` mock HTTP
- 单元测试里**绝不打真实网络**
- 缓存层用 `sqlite3` 而非 JSON 文件（练标准库）
- 报告支持 `--theme dark`
- 架构有清晰分层，`main.py` 只做装配不做逻辑
- 完整的 Git 提交历史（每完成一个功能提交一次）

---

## 四、参考架构

```
aggregator/
├── pyproject.toml
├── README.md
├── .env.example
├── src/aggregator/
│   ├── __init__.py
│   ├── main.py                # 装配入口
│   ├── cli.py                 # argparse / typer
│   ├── config.py              # 配置分层
│   ├── models.py              # 所有 dataclass
│   ├── exceptions.py
│   ├── fetchers/
│   │   ├── base.py            # BaseFetcher：重试/超时/日志
│   │   ├── weather.py
│   │   ├── github.py
│   │   └── countries.py
│   ├── cache/
│   │   └── sqlite_cache.py
│   ├── transformers/
│   │   └── joiners.py
│   ├── analyzers/
│   │   └── metrics.py
│   ├── visualizers/
│   │   ├── charts.py          # matplotlib
│   │   └── report.py          # HTML 生成
│   └── utils/
│       ├── logger.py
│       └── retry.py
└── tests/
    ├── conftest.py
    ├── test_fetchers.py
    ├── test_analyzers.py
    └── test_cache.py
```

### 关键接口（参考）

```python
# fetchers/base.py
class BaseFetcher(ABC):
    def __init__(self, client: httpx.AsyncClient, retry: Retry = Retry()):
        ...

    @abstractmethod
    async def fetch(self) -> list[Record]: ...

    async def fetch_with_retry(self) -> list[Record]:
        for attempt in range(self.retry.max_times):
            try:
                return await self.fetch()
            except Exception as e:
                if attempt == self.retry.max_times - 1:
                    raise FetchError(f"{self.__class__.__name__} 失败") from e
                await asyncio.sleep(2 ** attempt)

# utils/retry.py
@dataclass(frozen=True)
class Retry:
    max_times: int = 3
    base_delay: float = 1.0
```

### 配置分层（`config.py`）

```python
@dataclass
class Config:
    cache_ttl_hours: int = 24
    max_concurrency: int = 5
    timeout_seconds: float = 10.0
    db_path: Path = Path("data/cache.db")
    theme: str = "light"

    @classmethod
    def load(cls, path: Path | None = None) -> "Config":
        # 默认值 → 配置文件 → 环境变量 → 命令行（后者覆盖前者）
```

---

## 五、验收清单

- [ ] 一条命令 `python -m aggregator` 跑完全流程并生成 HTML 报告
- [ ] 断网状态下运行，能从缓存生成报告并提示降级
- [ ] `httpx` 请求全部设了超时，没有裸奔请求
- [ ] 测试全部 mock，不依赖网络，且 `pytest` 可离线运行
- [ ] `mypy --strict` 无 error，`ruff check` 无 error
- [ ] HTML 报告自包含（双击可打开，图表正常渲染）
- [ ] README 有架构图、运行说明、示例截图
- [ ] 有 `.gitignore`、有 `.env.example`
- [ ] 至少 12 次有意义的 Git 提交

---

## 六、思考题

1. 为什么测试里不能打真实网络？如果必须验证真实接口行为怎么办？
2. `asyncio.Semaphore` 和 `asyncio.gather` 分别解决什么问题？去掉会怎样？
3. 指数退避为什么是 1→2→4 而不是 1→2→3？
4. 缓存的 TTL 应该是全局统一的吗？不同 API 该怎么设计？
5. 如果某个 API 返回了 10 万条数据，你的内存占用会怎样？如何流式处理？
6. 这个项目里哪些地方用了**组合优于继承**？哪些用了**依赖注入**？

---

**下一步 → P4-异步网页爬虫**
