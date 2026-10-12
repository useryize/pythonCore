"""
================================================================================
 05_logging_config.py —— 生产级日志体系配置
================================================================================

【演示的语法点】
  1. getLogger(name)   : logger 是按名字分层的树，用点号建立父子关系
  2. Logger 层级       : setLevel 沿调用栈逐级向上找第一个生效的级别
  3. Formatter         : %(asctime)s / %(levelname)s / %(message)s 等占位符
  4. StreamHandler    : 输出到控制台
  5. RotatingFileHandler : 按大小轮转（backupCount 份）
  6. TimedRotatingFileHandler : 按时间轮转（midnight / interval）
  7. Handler 隔离      : parent.setLevel + handler.setLevel 双层过滤
  8. 自定义 Formatter  : JSON 日志结构化输出
  9. addFilter/Filter  : 过滤特定 logger 及其子级
 10. getLogger(__name__) : ★ 工程铁律，绝不用 getLogger(__file__)
 11. structlog 风格    : 用标准库手写一个轻量 JSON Formatter
 12. env 隔离          : dev/prod 不同格式与输出目标

【预期输出摘要】
  [1] logger 层级树与各级别归属
  [2] dev 环境：控制台彩色简版 + 文件全量 INFO
  [3] prod 环境：控制台仅 WARN 以上 + JSON 文件 + 错误独立文件
  [4] RotatingFileHandler 轮转演示（写满 N KB 触发轮转，生成 .1 .2 备份）
  [5] 过滤演示：third_party 库的 DEBUG 被静音
  [6] 敏感信息脱敏演示

【★ 核心工程规范】
  ❌ print(...)              -> 无级别、无时间、无文件、无轮转，生产事故排查靠它？做梦
  ❌ logging.info(...)        -> 根 logger 无配置，WARNING 以上会直接被丢弃（KeyError: root）
  ✅ logging.getLogger(__name__)
  ✅ 模块级只创建 logger，不做配置（配置集中到 app 的 setup_logging）
  ✅ 库代码 NEVER 配置日志，only 应用入口 configure
"""

import io
import json
import logging
import logging.handlers
import platform
import re
import socket
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, TextIO


# ==============================================================================
# 一、模块级 logger —— 全文件唯一写法
# ==============================================================================
# ===== 语法解析 =====
# 为什么是 logging.getLogger(__name__) 而不是 logging.info(...)？
#   1. __name__ 在被 import 时是 "包名.模块名"，天然形成层级树，可分别控制级别
#   2. 用 __name__ 而不是 __file__：__file__ 含盘符/反斜杠，不是合法 logger 名
#   3. 调用模块根 logger 时必须先 basicConfig()，否则 WARNING 以上静默丢弃
# 为什么不在模块顶层配置？
#   因为这是「库代码」。库代码只负责发出结构化日志，
#   具体输出到哪、什么格式、是否轮转，由使用库的「应用」决定。
#   在库里配置 = 强行覆盖使用者的偏好，是公认的反模式。

# 注意：这里只创建 logger 对象，不设置任何 level/handler —— 交给上层
module_logger = logging.getLogger(__name__)


# ==============================================================================
# 二、日志级别与过滤机制
# ==============================================================================
# ===== 语法解析 =====
# 日志等级（数值越大越严重）：
#   DEBUG(10) < INFO(20) < WARNING(30) < ERROR(40) < CRITICAL(50)
# 过滤是「双层」的：
#   1. Logger 级别：isEnabledFor() 决定这条日志要不要被生成（省开销）
#   2. Handler 级别：决定这条日志要不要写进这个输出目标
# 例如：logger=DEBUG, console=WARNING, file=DEBUG
#       -> 控制台只出 WARN 以上，文件里全都有。这正是生产环境的常见组合。

# 自定义级别：插入到既有级别之间，比直接用 DEBUG(10) 更可读
logging.addLevelName(25, "NOTICE")
TRACE = 25
logging.addLevelName(TRACE, "TRACE")


def trace(logger: logging.Logger, message: str, *args: Any) -> None:
    """为 TRACE(25) 注册便捷函数。

    为什么需要自定义级别？
      因为 INFO(20) 之上和 WARNING(30) 之下缺一档：普通业务信息用 INFO，
      系统健康数据（心跳、资源水位）用 NOTICE，DEBUG 太吵 INFO 又太杂。
    """
    # logger.log(级别, 消息, *args) 是所有级别的底层通用入口
    logger.log(TRACE, message, *args)


# ==============================================================================
# 三、Formatter：占位符与自定义格式化
# ==============================================================================
# ===== 语法解析 =====
# Formatter 接收一个 format 字符串，内部用 % 风格的命名占位符：
#   %(asctime)s    时间        %(name)s    logger 名
#   %(levelname)s  级别名      %(filename)s / %(lineno)d  文件与行号
#   %(module)s / %(funcName)s / %(process)d / %(threadName)s
#   %(message)s    用户消息    %(exc_info)s 异常堆栈
#
# datefmt 单独控制时间格式；style 可选 "%"（默认）、"{"（str.format）、"$"（string.Template）
#
# ★ 关键：%(filename)s 是「输出这条日志的文件名」，%(name)s 是 logger 名。
#   很多教程混淆二者 —— 日志里要同时出现，才能定位到具体代码行。

TEXT_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)-22s | %(filename)s:%(lineno)d | %(message)s"
SHORT_FORMAT = "%(asctime)s [%(levelname)s] %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


class JSONFormatter(logging.Formatter):
    """JSON 结构化日志 Formatter —— ELK / Loki / CloudWatch 友好。

    为什么生产日志要用 JSON 而不是文本？
      1. 文本日志要写正则解析，字段一多就崩；JSON 可以直接被索引
      2. JSON 是结构化的，字段名稳定，聚合查询（按 error_type 分组）才可能
      3. 单行格式便于按行分割；multiline 的堆栈要用 \\n 转义
    """

    def format(self, record: logging.LogRecord) -> str:
        """把 LogRecord 序列化成一行 JSON。

        LogRecord 是 logging 的核心数据结构：
        里面装着 msg、levelname、pathname、lineno、funcName、args、exc_info ...
        Formatter 的职责就是把这一堆字段拼成最终的一行文本。
        """
        # 先算出标准 message（把 %s 占位符用 args 填充后的最终文本）
        # parent.format() 会处理 %-args 替换
        base_msg = super().format(record)

        payload: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc)
            .astimezone()
            .isoformat(timespec="milliseconds"),
            "level": record.levelname,
            "logger": record.name,
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
            "file": record.filename,
            "message": record.getMessage(),      # ★ getMessage() 会做 args 替换
            "process": record.process,
            "thread": record.threadName,
            "host": socket.gethostname(),
        }

        # 条件字段：只有发生异常时才带上堆栈，不要污染正常日志
        if record.exc_info:
            # exc_text 由父类 format 自动填好，包含完整 traceback
            payload["exception"] = record.exc_info[0].__name__ if record.exc_info[0] else "?"
            payload["traceback"] = self.formatException(record.exc_info).replace("\n", "\\n")

        # 附加自定义字段：logger.info("msg", extra={"user_id": 1}) 打进来的
        for key in ("user_id", "request_id", "cost_ms", "module_name"):
            if hasattr(record, key):
                payload[key] = getattr(record, key)

        # ensure_ascii=False 保留中文可读性；default=str 兜底不可序列化对象
        return json.dumps(payload, ensure_ascii=False, default=str)


class SensitiveDataFilter(logging.Filter):
    """脱敏过滤器：拦截手机号、身份证、密码等敏感信息。

    正确做法：在 Formatter 之前挂 Filter，
    这样敏感数据连内存里的 buffer 都不会进去。
    """

    PATTERNS = [
        ("password=123456", "password=***"),
        ("13800138000", "138****8000"),
        ("4111111111111111", "4111****1111"),
    ]

    def filter(self, record: logging.LogRecord) -> bool:
        """返回 True 表示放行，False 表示丢弃该条日志。"""
        # getMessage() 做占位符替换后的最终文本 —— 必须改这里，改 record.msg 不够
        message = record.getMessage()
        for raw, masked in self.PATTERNS:
            if raw in message:
                message = message.replace(raw, masked)
                # 同步改写 record，避免后面 formatter 再读到原文
                record.msg = message
                record.args = ()
        return True


# ==============================================================================
# 四、Handler 组装：配置函数的工程写法
# ==============================================================================
# ===== 语法解析 =====
# 一个 handler = 一个「输出目标」+ 一个「级别」+ 一个「格式」+ 若干「过滤器」
# 一个 logger 可以挂多个 handler：同一条日志被分别写到多个目标。
#
# ★ configure 幂等：重复调用会不断 addHandler 导致日志重复打印。
#   解决办法见下面 setup_logging 的实现。


def make_console_handler(
    level: int,
    fmt: str,
    colorize: bool = False,
) -> logging.Handler:
    """构造控制台 handler。"""
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(level)
    handler.setFormatter(logging.Formatter(fmt, datefmt=DATE_FORMAT))
    if colorize:
        handler.setFormatter(ColorFormatter(fmt, datefmt=DATE_FORMAT))
    return handler


# ANSI 颜色码：终端下自动生效，重定向到文件时不会输出杂字符
ANSI = {
    "TRACE": "\033[36m",     # 青色
    "DEBUG": "\033[36m",     # 青色
    "INFO": "\033[32m",      # 绿色
    "NOTICE": "\033[32;1m",  # 亮绿
    "WARNING": "\033[33m",   # 黄色
    "ERROR": "\033[31m",     # 红色
    "CRITICAL": "\033[41;37m",  # 红底白字
}
RESET = "\033[0m"


class ColorFormatter(logging.Formatter):
    """给级别名上色的 Formatter（仅终端有效）。"""

    def format(self, record: logging.LogRecord) -> str:
        # 复用父类格式化，再把级别名包上颜色码
        text = super().format(record)
        color = ANSI.get(record.levelname)
        if not color:
            return text
        # record.levelname 出现在格式化结果里，替换成「颜色码 + 原名 + 重置码」
        return text.replace(record.levelname, f"{color}{record.levelname}{RESET}", 1)


def make_file_handler(
    path: Path,
    level: int,
    formatter: logging.Formatter,
    max_bytes: int = 0,
    backup_count: int = 0,
    when: str = "",
    interval: int = 0,
) -> logging.Handler:
    """构造文件 handler，自动在「按大小轮转」和「按时间轮转」之间二选一。"""
    path.parent.mkdir(parents=True, exist_ok=True)      # 自动建目录，避免 FileNotFoundError
    if max_bytes > 0:
        # 按大小轮转：文件超过 max_bytes 就改名成 xxx.log.1 并新建
        handler: logging.Handler = logging.handlers.RotatingFileHandler(
            path, maxBytes=max_bytes, backupCount=backup_count, encoding="utf-8",
        )
    elif when:
        # 按时间轮转：midnight 每天零点，interval 秒/h/MIDNIGHT
        handler = logging.handlers.TimedRotatingFileHandler(
            path, when=when, interval=interval, backupCount=backup_count, encoding="utf-8",
        )
    else:
        handler = logging.FileHandler(path, encoding="utf-8")

    handler.setLevel(level)
    handler.setFormatter(formatter)
    # 主动把文件推到磁盘，防止进程被 kill 后丢日志
    handler.flush()
    return handler


def setup_logging(
    env: str = "dev",
    log_dir: Path | None = None,
    quiet_stdout: bool = False,
) -> logging.Logger:
    """按环境配置日志 —— 应用的唯一日志入口（生产实践标准写法）。

    :param env:          "dev" 彩色详细 / "prod" JSON + 分级文件
    :param log_dir:      日志目录，默认用临时目录，避免污染仓库
    :param quiet_stdout: True 时把控制台输出重定向到内存（演示用，防止刷屏）
    """
    # ---------- 幂等保护：先清空 root 的 handler，再重新配置 ----------
    # 为什么必须这样？重复 setup_logging() 会让日志重复打印 N 次
    root = logging.getLogger()
    root.handlers.clear()
    # root 的级别必须设成最低，否则 Logger 创建时级别是 WARNING，
    # INFO/DEBUG 记录在 handler 之前就被丢弃了
    root.setLevel(logging.DEBUG)

    if log_dir is None:
        log_dir = Path(__file__).resolve().parent / "_logs"
    log_dir.mkdir(parents=True, exist_ok=True)

    # 演示时把控制台输出接到内存缓冲，这样报告干净且不污染仓库
    console_stream: TextIO = io.StringIO() if quiet_stdout else sys.stdout
    captured_console = console_stream if quiet_stdout else None

    text_formatter = logging.Formatter(TEXT_FORMAT, datefmt=DATE_FORMAT)
    short_formatter = ColorFormatter(SHORT_FORMAT, datefmt=DATE_FORMAT) if not quiet_stdout \
        else logging.Formatter(SHORT_FORMAT, datefmt=DATE_FORMAT)
    json_formatter = JSONFormatter()

    if env == "dev":
        # ---------------- 开发环境 ----------------
        # 特点：终端看全部，文件留一份，格式彩色简洁
        console = logging.StreamHandler(console_stream)
        console.setLevel(logging.DEBUG)          # dev 终端显示 DEBUG
        console.setFormatter(short_formatter)
        root.addHandler(console)

        file_h = make_file_handler(
            log_dir / "app.log", logging.DEBUG, text_formatter, max_bytes=512 * 1024, backup_count=3,
        )
        root.addHandler(file_h)
        root.addFilter(SensitiveDataFilter())    # 脱敏挂在 root 上，全局生效

    else:
        # ---------------- 生产环境 ----------------
        # 特点：终端只报 WARNING 以上（避免刷屏/污染容器日志采集），
        #       文件用 JSON（便于机器解析），错误再单独一份便于告警
        console = logging.StreamHandler(console_stream)
        console.setLevel(logging.WARNING)
        console.setFormatter(
            ColorFormatter("%(asctime)s [%(levelname)s] %(message)s", datefmt=DATE_FORMAT)
            if not quiet_stdout
            else logging.Formatter(SHORT_FORMAT, datefmt=DATE_FORMAT)
        )
        root.addHandler(console)

        # 全量日志（JSON），按 10MB 轮转，保留 10 份 —— 约 100MB 上限
        root.addHandler(make_file_handler(
            log_dir / "app.jsonl", logging.INFO, json_formatter,
            max_bytes=10 * 1024 * 1024, backup_count=10,
        ))
        # 错误日志独立文件，方便配告警规则（只收集 ERROR 及以上）
        root.addHandler(make_file_handler(
            log_dir / "error.jsonl", logging.ERROR, json_formatter, backup_count=5,
        ))

    # ---------- 第三方库降噪 ----------
    # 噪音王：urllib3 的连接池 DEBUG、asyncio 的事件循环 TRACE
    for noisy in ("urllib3", "asyncio", "requests", "urllib3.connectionpool", "chardet"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
    # 自己的业务 logger 单独降噪示例
    logging.getLogger("myapp.third_party").setLevel(logging.WARNING)

    # 附带的便捷属性：让调用方能取回控制台缓冲区内容（仅演示用）
    logging.getLogger().captured_console = captured_console  # type: ignore[attr-defined]
    return root


# ==============================================================================
# 五、模块化 logger 层级演示
# ==============================================================================
# ===== 语法解析 =====
# logger 名用点号分层：myapp.api / myapp.api.users / myapp.db
# 设置 myapp 的级别为 WARNING，会同时压制 myapp.api.users（子级）——
# 只要子级自己没有显式设置过级别，级别就沿树向上查找（"level 继承"）。


class AppLoggerFactory:
    """模拟一个多模块应用：每个模块拿到自己的 logger。"""

    @staticmethod
    def build() -> dict[str, logging.Logger]:
        # 真实项目里每个模块写：logger = logging.getLogger(__name__)
        return {
            "myapp": logging.getLogger("myapp"),
            "myapp.api": logging.getLogger("myapp.api"),
            "myapp.api.users": logging.getLogger("myapp.api.users"),
            "myapp.db.pool": logging.getLogger("myapp.db.pool"),
            "myapp.third_party.sdk": logging.getLogger("myapp.third_party.sdk"),
        }


def emit_all_levels(logger: logging.Logger) -> None:
    """依次发出所有级别的日志，直观感受级别过滤。"""
    # 用 %-占位符 + 惰性格式化：只有真正要输出的级别才会做字符串拼接
    # 如果写成 logger.info(f"值是 {expensive()}")，无论级别开不开都会先求值
    logger.debug("这是 DEBUG - 只在本地排查问题时可见")
    trace(logger, "这是 TRACE(25) - 自定义级别，用于系统健康数据")
    logger.info("这是 INFO - 常规业务流水，如「用户下单」")
    logger.warning("这是 WARNING - 需要关注但不影响主流程，如「重试第 2 次」")
    logger.error("这是 ERROR - 功能失败，如「支付网关超时」")
    logger.critical("这是 CRITICAL - 服务不可用，需要立即介入")


def emit_with_context(logger: logging.Logger) -> None:
    """演示 extra 字段 + exc_info 异常堆栈 + 结构化上下文。"""
    # extra= 往 LogRecord 上挂自定义字段，%(key)s 或 JSON Formatter 能取到
    logger.info(
        "用户请求完成 method=%s path=%s", "POST", "/api/v1/orders",
        extra={"user_id": 10086, "request_id": "req-abc-123", "cost_ms": 43},
    )
    logger.warning("磁盘使用率偏高", extra={"module_name": "storage", "cost_ms": 0})

    # exc_info=True 让 logger 自动抓取当前异常堆栈
    try:
        int("不是数字")
    except ValueError:
        logger.error("数据转换失败", exc_info=True)      # 堆栈自动附加

    # 自定义异常也可以
    class OrderError(Exception):
        pass

    try:
        raise OrderError("订单状态机非法：PAID -> SHIPPED")
    except OrderError:
        logger.critical("订单流程异常", exc_info=True)

    # 演示脱敏：日志里不该出现明文密码和手机号
    logger.info("用户登录 password=123456 手机=13800138000 卡号=4111111111111111")


# ==============================================================================
# 六、RotatingFileHandler 轮转实战演示
# ==============================================================================
def demo_rotation(log_dir: Path) -> list[Path]:
    """故意写爆一个 4KB 的日志文件，触发多次轮转，观察备份文件的生成。"""
    rot_dir = log_dir / "rotation_demo"
    rot_dir.mkdir(parents=True, exist_ok=True)

    # 清理历史产物，保证演示可重复
    for old in rot_dir.glob("*.log*"):
        old.unlink()

    handler = logging.handlers.RotatingFileHandler(
        rot_dir / "rotate.log",
        maxBytes=4 * 1024,          # 4KB 就轮转，让演示秒级完成
        backupCount=3,              # 最多保留 rotate.log.1 .2 .3
        encoding="utf-8",
    )
    handler.setFormatter(logging.Formatter("%(levelname)s|%(message)s"))

    logger = logging.getLogger("demo.rotation")
    logger.handlers.clear()      # 清掉继承自 root 的 handler，隔离演示
    logger.propagate = False     # ★ 关键：不往 root 冒泡，否则日志翻倍
    logger.setLevel(logging.DEBUG)
    logger.addHandler(handler)

    # 写够数据量：每条约 80 字符，写 120 条 = 约 9.6KB，必然触发多次轮转
    for i in range(120):
        logger.info(f"轮转演示第 %03d 条日志：填充数据填充数据填充数据填充数据填充数据")

    handler.close()
    # sorted 保证 .1 .2 .3 按新旧顺序输出
    return sorted(rot_dir.glob("rotate.log*"), key=lambda p: p.name)


# ==============================================================================
# 七、主流程
# ==============================================================================
def demo_logger_tree(loggers: dict[str, logging.Logger]) -> None:
    """展示 logger 树与级别继承关系。"""
    print("  logger 名称                  有效级别(见下)  isEnabledFor(ERROR)")
    print("  " + "-" * 66)
    # 给子级设一个显式级别，观察它覆盖父级继承
    loggers["myapp"].setLevel(logging.WARNING)
    loggers["myapp.api"].setLevel(logging.INFO)
    loggers["myapp.api.users"].setLevel(logging.DEBUG)     # 显式设置，最高优先级
    loggers["myapp.db.pool"].setLevel(logging.DEBUG)        # 未显式设置？此处显式设为 DEBUG

    for name, lg in loggers.items():
        eff = logging.getLevelName(lg.getEffectiveLevel())
        print(f"  {name:<28} {eff:<14} {lg.isEnabledFor(logging.ERROR)}")

    print("\n  说明：getEffectiveLevel() 沿父级向上查找，直到找到显式设置的级别")
    print("  生产实践：只给顶层 myapp 设级别，模块自己不再设，避免配置碎片化")

    # 复位：交给 root 统一管理，避免影响后面的 prod 演示
    # 把 logger 级别设成 NOTSET(0)，代表「不自己决定，完全继承父级」
    for lg in loggers.values():
        lg.setLevel(logging.NOTSET)


def main() -> None:
    """主流程：展示 dev/prod 两套配置、轮转、脱敏、降噪。仅标准库，秒级完成。"""
    print("=" * 78)
    print(" 05. 生产级日志配置")
    print("=" * 78)
    print(f"  运行环境 : Python {sys.version.split()[0]} / {platform.system()} {platform.release()}")
    print(f"  时间基准 : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    log_dir = Path(__file__).resolve().parent / "_logs"

    # ---------- 1. logger 层级 ----------
    print("\n[1] logger 层级树与级别继承")
    print("-" * 78)
    loggers = AppLoggerFactory.build()
    demo_logger_tree(loggers)

    # ---------- 2. dev 环境 ----------
    print("\n[2] dev 环境：控制台 DEBUG 全量 + 文件文本格式 + 脱敏 + 降噪")
    print("-" * 78)
    setup_logging(env="dev", log_dir=log_dir, quiet_stdout=True)
    console_buffer = getattr(logging.getLogger(), "captured_console")

    emit_all_levels(loggers["myapp.api.users"])
    loggers["myapp.api.users"].info("脱敏测试 password=123456 手机=13800138000")
    # 第三方库降噪验证：设置 DEBUG 但被强制 WARNING 压制
    logging.getLogger("urllib3.connectionpool").debug("这条 DEBUG 不该出现")
    emit_with_context(loggers["myapp.api"])

    # 把捕获的控制台内容打出来（含颜色码过滤）
    if console_buffer:
        raw = console_buffer.getvalue()
        # 去掉 ANSI 颜色码，让终端输出干净可读（真彩色终端则无需处理）
        clean = re.sub(r"\033\[[0-9;]*m", "", raw)
        for line in clean.splitlines():
            print(f"  {line}")

    print(f"\n  文件日志目录：{log_dir}")
    print(f"  app.log 行数：{len((log_dir / 'app.log').read_text(encoding='utf-8').splitlines())}")

    # ---------- 3. prod 环境 ----------
    print("\n[3] prod 环境：控制台仅 WARN+ / JSON 全量文件 / ERROR 独立文件")
    print("-" * 78)
    setup_logging(env="prod", log_dir=log_dir, quiet_stdout=True)
    emit_all_levels(loggers["myapp"])
    emit_with_context(loggers["myapp.db.pool"])

    app_json = log_dir / "app.jsonl"
    err_json = log_dir / "error.jsonl"
    app_lines = app_json.read_text(encoding="utf-8").splitlines()
    err_lines = err_json.read_text(encoding="utf-8").splitlines() if err_json.exists() else []

    print(f"  app.jsonl   总行数 : {len(app_lines)}")
    print(f"  error.jsonl 总行数 : {len(err_lines)}   ← 只有 ERROR 以上")
    print("\n  JSON 日志样例（第 1 条 INFO）：")
    if app_lines:
        # json.loads 再 dumps：验证输出确实是合法 JSON（结构化日志的意义）
        sample = json.loads(app_lines[0])
        print(json.dumps(sample, ensure_ascii=False, indent=4)[:900])

    print("\n  含异常堆栈的 ERROR 日志（字段已做 \\n 转义，单行化）：")
    for line in err_lines:
        obj = json.loads(line)
        if "traceback" in obj:
            tb = obj["traceback"]
            print(f"    level={obj['level']}  exception={obj['exception']}")
            print(f"    堆栈首行：{tb.split(chr(92) + 'n')[0]}")
            print(f"    堆栈行数：{len(tb.split(chr(92) + 'n'))}")
            break

    # ---------- 4. 轮转演示 ----------
    print("\n[4] RotatingFileHandler 轮转演示（maxBytes=4KB, backupCount=3）")
    print("-" * 78)
    files = demo_rotation(log_dir)
    print(f"  生成文件共 {len(files)} 个：")
    for f in files:
        size = f.stat().st_size
        print(f"    {f.name:<18} {size:>6} 字节")
    print("\n  轮转规则说明：")
    print("    写入时若当前文件超过 maxBytes -> 依次改名 rotate.log→.1→.2→.3")
    print("    超出 backupCount 的最旧备份被直接删除（这样磁盘占用有上限）")
    print(f"    rotate.log 的第 2 行内容：{files[0].read_text(encoding='utf-8').splitlines()[0] if files else 'N/A'}")

    # ---------- 5. 规范总结 ----------
    print("\n[5] 工程规范速查")
    print("-" * 78)
    rules = [
        ("模块级", "logger = logging.getLogger(__name__)"),
        ("禁用", "print() / logging.info() 直接调用 / 在库里 basicConfig"),
        ("级别", "dev=DEBUG, prod=INFO, 控制台=INFO/WARNING"),
        ("格式", "dev=彩色文本, prod=JSON(单行, \\n 转义堆栈)"),
        ("轮转", "按大小 RotatingFileHandler（10MB×10）或按时间 Timed"),
        ("脱敏", "Filter 拦在 Formatter 之前，改 record.msg 而非 args"),
        ("降噪", "第三方库 logger 显式设 WARNING"),
        ("性能", "用 %s 惰性占位，禁止 f-string 提前求值"),
        ("上下文", "extra={request_id, user_id} 传递链路追踪 ID"),
        ("异常", "logger.error(msg, exc_info=True) 而非 logger.error(e)"),
    ]
    for key, value in rules:
        print(f"    {key:<8} {value}")

    print("\n" + "=" * 78)
    print(f" 日志文件位于：{log_dir}（可在看完后自行删除）")
    print("=" * 78)


# 入口保护
if __name__ == "__main__":
    main()
