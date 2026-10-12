# P2 · CSV 数据处理流水线

> **难度**：★★★　**预计工时**：6-10 小时
> **目标**：把面向对象、异常处理、文件 IO、模块拆分、类型注解综合练一遍。本项目是走向"工程化"的分水岭。

---

## 一、项目需求

给定一份销售订单 CSV，完成一个可配置的数据处理流水线：

```
原始 CSV → 读取 → 校验清洗 → 转换聚合 → 分析统计 → 多格式输出（CSV/JSON/报告）
```

### 示例输入 `sales_2026Q1.csv`

```csv
order_id,date,customer,region,product,category,quantity,unit_price,discount
S001,2026-01-05,张三,华东,机械键盘,外设,2,499,0.9
S002,2026-01-06,李四,华南,显示器,显示设备,1,1599,1
S003,2026-01-07,王五,华东,鼠标,外设,5,89,0.85
S004,2026-01-08,赵六,华北,机械键盘,外设,-1,499,1
S005,2026-01-09,张三,华东,,外设,3,199,1
```

---

## 二、功能需求

| 模块 | 说明 | 必须 |
|---|---|---|
| 数据模型 | `SaleRecord` dataclass，含校验逻辑 | ✅ |
| 读取层 | `Reader`：CSV → 原始 dict 列表 | ✅ |
| 清洗层 | `Cleaner`：去空、量正校验、金额计算、异常记录隔离 | ✅ |
| 转换层 | `Transformer`：按维度聚合 | ✅ |
| 分析层 | `Analyzer`：Top N、同比、占比、统计指标 | ✅ |
| 输出层 | `Exporter`：CSV / JSON / 文本报告 | ✅ |
| 流水线 | `Pipeline` 串联全流程，阶段可插拔 | ✅ |
| 异常 | 每阶段独立异常类，脏数据进 `errors.log` 不中断 | ✅ |

### 清洗规则（明确列出）

1. `order_id` 为空 → 丢弃
2. `quantity <= 0` → 丢弃
3. `unit_price <= 0` → 丢弃
4. `product` 为空 → 丢弃
5. `date` 格式非法 → 丢弃
6. `discount` 为空按 1.0 处理；不在 (0, 1] 范围 → 丢弃
7. 金额 = `quantity * unit_price * discount`
8. 每条丢弃的记录要**记原因并写入错误日志**，不能让整个流程挂掉

### 输出要求

- `output/summary_by_region.csv`：各区域销售额、销售量、订单数
- `output/summary_by_product.csv`：产品维度汇总 + Top 10
- `output/summary_by_category.csv`：品类维度
- `output/result.json`：全部统计结果嵌套结构
- `output/report.txt`：人类可读的文本报告（带表头、汇总、Top 榜）

---

## 三、加分项（★★★★ 目标）

- 命令行参数：`--input --output-dir --top-n --log-file --strict`
- `strict=True` 时遇到脏数据直接抛异常退出（非严格模式继续）
- 类型注解完整，`mypy --strict` 通过
- `pytest` 测试覆盖率 ≥ 75%，含 `parametrize`
- 使用 `pathlib` 全部路径操作
- `ruff check` + `ruff format` 通过
- 支持 `--format csv|json|all` 控制输出格式
- 加一个 `matplotlib` 简单柱状图（可选，输出 PNG）

---

## 四、参考架构

```
pipeline/
├── main.py               # CLI 入口
├── models.py             # SaleRecord / RegionStat 等 dataclass
├── exceptions.py         # DataError 体系
├── readers.py            # CSVReader
├── cleaners.py           # Cleaner（脏数据收集）
├── transformers.py       # Transformer（聚合）
├── analyzers.py          # Analyzer（统计指标）
├── exporters.py          # CsvExporter / JsonExporter / ReportExporter
├── pipeline.py           # 流程编排
├── tests/
│   ├── test_cleaners.py
│   ├── test_analyzers.py
│   └── test_pipeline.py
└── data/
    └── sales_2026Q1.csv
```

### 关键接口设计（参考）

```python
# models.py
@dataclass(frozen=True)
class SaleRecord:
    order_id: str
    date: date
    customer: str
    region: str
    product: str
    category: str
    quantity: int
    unit_price: Decimal
    discount: Decimal

    @property
    def amount(self) -> Decimal:
        return self.quantity * self.unit_price * self.discount

# exceptions.py
class DataError(Exception): ...
class FileNotFoundError_(DataError): ...
class ValidationError(DataError): ...

# cleaners.py
@dataclass
class CleanResult:
    records: list[SaleRecord]
    errors: list[tuple[int, str, str]]   # (行号, 原因, 原始数据)

class Cleaner:
    def __init__(self, strict: bool = False): ...
    def clean(self, raw_rows: list[dict]) -> CleanResult: ...
```

> **金额一律用 `Decimal` 或整数分**，不要用 float——这是 P3 的伏笔。

---

## 五、验收清单

- [ ] 给定的示例 CSV 能完整跑通，输出文件正确
- [ ] 故意在 CSV 里塞入 5 种脏数据，全部被正确拦截并记录原因
- [ ] 删除整个 `output/` 目录后程序能自动重建
- [ ] 输入文件不存在时，报错信息清晰，不抛栈回溯给用户
- [ ] `report.txt` 内容排版整齐（列对齐、可读）
- [ ] `mypy --strict` 无 error
- [ ] `pytest --cov` 覆盖率 ≥ 75%
- [ ] 有 README，含输入格式说明、运行示例、输出样例

---

## 六、思考题（面试常问）

1. 为什么金额用 `Decimal` 不用 `float`？举例说明 float 会出什么问题。
2. 你的流水线如果中间某阶段崩溃，已经处理完的数据会怎样？如何做到阶段级容错？
3. 如果 CSV 有 500 万行，你的 `Read all → Clean all` 的写法有什么问题？怎么改成流式处理？
4. `Cleaner` 为什么返回 `CleanResult` 对象而不是直接返回 list？这样设计好在哪？
5. 如果要支持 Excel 输入（.xlsx），你的架构需要改哪一层？

---

**下一步 → P3-API数据聚合与可视化**
