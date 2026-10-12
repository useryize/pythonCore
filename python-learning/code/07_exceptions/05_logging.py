#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
logging 完整配置与最佳实践
==============================

【演示的语法点】
1. 五级日志：DEBUG / INFO / WARNING / ERROR / CRITICAL 与 level 过滤规则
2. basicConfig 配置：level / format / datefmt / stream / force
3. 多 handler：控制台 + 文件（RotatingFileHandler 防爆盘）
4. logger 层级体系：root -> myapp -> myapp.db，child 的 level 与 propagate
5. 自定义 Formatter 输出字段（asctime/levelname/name/message）
6. 异常日志最佳实践：
   - logger.exception() 自动附加 traceback
   - exc_info=True 显式附加
   - logger.error(..., exc_info=e) 的区别与陷阱
   - 绝不手动 f-string 拼接 traceback
7. 结构化 JSON 日志：自定义 Formatter 输出 JSON
8. 日志中敏感信息脱敏
9. 多个进程/模块各自配置 logger 的正确做法（getLogger(__name__)）
10. 与 warnings 的关系：warnings 走专门的处理器，不进 logging

【预期输出摘要】
- 控制台打印彩色化的分级日志
- 同时在 logs/ 目录下生成 demo.log、demo_error.log、app.jsonl 三个文件
- 演示层级继承：app.db 的 DEBUG 日志只在 setLevel(DEBUG) 的父级生效时输出
- 输出 JSON 日志样例一行
"""

import json
import logging
import logging.handlers
import sys
import tempfile
from pathlib import Path


# ===== 语法解析 =====
# 【1】五个日志级别的数值
#   NOTSET(0) < DEBUG(10) < INFO(20) < WARNING(30) < ERROR(40) < CRITICAL(50)
#
# 【2】过滤规则的精确表述
#   logger.isEnabledFor(level): 当 level >= logger 的有效级别时返回 True
#   即：级别越高越容易「通过」。把 logger 设为 WARNING，则 DEBUG/INFO 被丢弃，
#      WARNING/ERROR/CRITICAL 保留。
#
# 【3】basicConfig 的行为陷阱
#   basicConfig 只在 root logger「还没有 handler」时才生效；
#   如果已经配置过（例如某些库先调用了），再次调用完全无效。
#   解决：basicConfig(..., force=True) 强制清空并重建 root 的 handler。
#      force 参数是 Python 3.8+ 新增。
LOG_DIR = Path(tempfile.gettempdir()) / "python_exception_logs"
LOG_DIR.mkdir(exist_ok=True)   # mkdir(exist_ok=True)：目录已存在不报错

MAIN_LOG = LOG_DIR / "demo.log"
ERROR_LOG = LOG_DIR / "demo_error.log"
JSON_LOG = LOG_DIR / "app.jsonl"


def demo_1_levels_and_basicconfig():
    """日志级别与 basicConfig 配置。"""
    print("=" * 70)
    print("【1】日志级别与 basicConfig")
    print("=" * 70)

    # ===== 语法解析 =====
    # basicConfig 参数说明：
    #   level      : root logger 的最低级别
    #   format     : 格式字符串，用 %(asctime)s 等占位符
    #   datefmt    : 时间戳本身的格式（传给 time.strftime）
    #   stream     : 输出流，默认 sys.stderr
    #   force      : Python 3.8+，清空已有 handler 后重新配置
    #
    # %(levelname)s  - 级别名，如 INFO
    # %(name)s       - logger 名，如 myapp
    # %(message)s    - 日志正文
    # %(asctime)s    - 格式化后的时间
    # %(lineno)d     - 行号，需要 %(lineno)d 占位符显式请求
    # %(funcName)s   - 函数名
    # %(module)s     - 模块名
    # %(pathname)s   - 文件完整路径
    logging.basicConfig(
        level=logging.DEBUG,
        format="[%(levelname)-8s] %(asctime)s | %(name)-12s | %(funcName)s:%(lineno)d | %(message)s",
        datefmt="%H:%M:%S",
        force=True,   # 关键：允许重复配置（否则本文件第二次调用无效）
    )

    # logging 的模块级函数实际是 root logger 的快捷方式
    logging.debug("这是一条 DEBUG 消息")       # 级别 10 >= 10 -> 输出
    logging.info("这是一条 INFO 消息")         # 20 >= 10 -> 输出
    logging.warning("这是一条 WARNING 消息")   # 30 -> 输出
    logging.error("这是一条 ERROR 消息")       # 40 -> 输出
    logging.critical("这是一条 CRITICAL 消息") # 50 -> 输出

    # 更低级别会被过滤掉，演示不输出
    logging.log(logging.DEBUG - 5, "这条级别过低，不会输出")
    print()
    print(f"【要点】日志级别数值：NOTSET={logging.NOTSET}, DEBUG={logging.DEBUG}, "
          f"INFO={logging.INFO}, WARNING={logging.WARNING}, "
          f"ERROR={logging.ERROR}, CRITICAL={logging.CRITICAL}")

    # ===== 语法解析 =====
    # 调高级别后，低级别日志被丢弃。注意这是 root 的级别，
    # 对通过 getLogger 创建的子 logger 也生效。
    print("\n--- 把级别改成 WARNING 后再输出 ---")
    logging.getLogger().setLevel(logging.WARNING)
    logging.info("这条 INFO 因为级别不足被丢弃（不会出现在控制台）")
    logging.error("这条 ERROR 仍然输出")
    logging.getLogger().setLevel(logging.DEBUG)  # 恢复
    print()
    print("【要点】级别过滤发生在 Logger.isEnabledFor()，早于格式化，因此性能开销小。")


def demo_2_hierarchy():
    """logger 层级体系。"""
    print("=" * 70)
    print("【2】logger 层级体系与 propagate")
    print("=" * 70)

    # ===== 语法解析 =====
    # logger 名用「点号」分隔形成层级，层级由名字决定，与调用位置无关：
    #   getLogger("app")          -> name = "app"
    #   getLogger("app.db")       -> name = "app.db"，parent 是 "app"
    #   getLogger("app.db.pool")  -> parent 是 "app.db"
    #
    # 关键属性：
    #   level   : 本 logger 的过滤级别。NOTSET 表示「继承父级」。
    #   handler : 本 logger 自己的处理器。为空时向父级借用。
    #   propagate: 是否把日志继续上传给父级。默认 True。
    #
    # 一次 getLogger("x") 返回的都是同一个对象（缓存在 logging 的字典里），
    # 因此重复调用不会创建新 logger，这一点非常关键。
    root = logging.getLogger()
    app_logger = logging.getLogger("app")
    db_logger = logging.getLogger("app.db")

    print(f"logger 对象是否同一: {logging.getLogger('app') is app_logger}")
    print(f"app.parent     = {app_logger.parent.name}")
    print(f"app.db.parent  = {db_logger.parent.name}")
    print(f"app.level      = {app_logger.level} (0 = NOTSET，继承父级)")
    print(f"app.db.propagate = {db_logger.propagate}")
    print()

    # 子 logger 级别为 NOTSET 时，继承父级的有效级别
    app_logger.setLevel(logging.DEBUG)
    db_logger.debug("子 logger 用父级的 DEBUG 级别 -> 会输出")
    db_logger.info("子 logger INFO -> 会输出")

    # 单独提高子 logger 级别，只影响它自己
    db_logger.setLevel(logging.ERROR)
    db_logger.warning("被过滤：db logger 级别已提高到 ERROR")
    db_logger.error("输出：ERROR 级别仍通过")
    db_logger.setLevel(logging.NOTSET)   # 恢复继承
    print()

    print("【要点】getLogger 返回全局单例，模块内应使用 getLogger(__name__) 避免命名冲突。")
    print("【要点】子 logger 级别为 NOTSET(0) 时继承父级；显式设置则独立生效。")
    print("【要点】propagate=False 可让子 logger 只输出到自己的 handler，不重复上报。")
    print()


def demo_3_multi_handler():
    """多 handler：控制台 + 两个文件（一个全量，一个只收 ERROR）。"""
    print("=" * 70)
    print("【3】多 Handler：控制台 + 全量文件 + 错误文件")
    print("=" * 70)

    # ===== 语法解析 =====
    # Handler 的职责：决定「输出到哪里」
    # Formatter 的职责：决定「输出成什么样」
    # Filter 的职责：决定「哪些记录通过」
    # 三者正交组合，可以任意搭配。
    logger = logging.getLogger("app.multi")

    # 清空该 logger 的 handler，避免与其他演示互相干扰
    logger.handlers.clear()
    # 设为独立 logger：不再向 root 上报，避免重复输出到控制台
    logger.propagate = False
    logger.setLevel(logging.DEBUG)

    # Handler1：控制台，使用 StreamHandler，默认输出到 stderr
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)      # 控制台只显示 INFO 及以上
    console_handler.setFormatter(logging.Formatter(
        fmt="CONSOLE | %(levelname)-8s | %(message)s"
    ))

    # Handler2：全量文件，用 RotatingFileHandler 防止日志无限增长撑爆磁盘
    # maxBytes=100_000：单文件上限 100KB
    # backupCount=3：最多保留 3 个历史文件（demo.log.1/.2/.3）
    # encoding="utf-8"：必须指定，否则 Windows 下中文会乱码
    file_handler = logging.handlers.RotatingFileHandler(
        MAIN_LOG, maxBytes=100_000, backupCount=3, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)        # 文件记录全部级别
    file_handler.setFormatter(logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    ))

    # Handler3：只收 ERROR 及以上的错误日志（filter 而不是 level）
    # level 只能表达「>=某级别」，用 Filter 可以表达任意条件
    error_handler = logging.FileHandler(ERROR_LOG, mode="w", encoding="utf-8")
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(logging.Formatter(
        fmt="ERRORFILE | %(levelname)s | %(filename)s:%(lineno)d | %(message)s"))

    # 把三个 handler 挂到 logger 上
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
    logger.addHandler(error_handler)

    print(f"当前 logger 的 handler 数量: {len(logger.handlers)}")
    for h in logger.handlers:
        print(f"   {type(h).__name__}  level={h.level}")
    print()

    # 现在观察同一个 logger 的不同级别如何分流
    logger.debug("DEBUG 消息 -> 只进全量文件")
    logger.info("INFO 消息 -> 控制台 + 全量文件")
    logger.warning("WARNING 消息 -> 控制台 + 全量文件")
    logger.error("ERROR 消息 -> 控制台 + 全量文件 + 错误文件")
    logger.critical("CRITICAL 消息 -> 三个去处都有")
    print()
    print(f"控制台 handler 级别=INFO，所以 DEBUG 那条没有显示在控制台（但已写入文件）")
    print()


def demo_4_filter():
    """自定义 Filter：按内容过滤。"""
    print("=" * 70)
    print("【4】自定义 Filter —— 按内容过滤")
    print("=" * 70)

    # ===== 语法解析 =====
    # Filter 可以挂在 Logger 上（过滤该 logger 的所有记录），
    # 也可以挂在单个 Handler 上（只过滤送往该 handler 的记录）。
    # 一个 Logger 上可以挂多个 Filter，必须全部返回 True 才通过。
    class SensitiveDataFilter(logging.Filter):
        """拦截含敏感关键词的日志，替换为脱敏版本。"""

        SENSITIVE = ("password", "token", "secret", "身份证")

        def filter(self, record):
            # record 是 LogRecord 对象，拥有全部日志字段 + 自定义 extra 字段
            # 返回 True 放行，False 丢弃。
            # 也可以在返回 False 前修改 record，实现「脱敏而非丢弃」。
            for key in self.SENSITIVE:
                if key in record.msg.lower():
                    # 修改 msg 实现脱敏：把敏感片段替换成 ***
                    record.msg = record.msg.replace(record.msg, record.msg.replace(
                        record.msg.split("=")[-1] if "=" in record.msg else key, "***REDACTED***"))
                    return True   # 脱敏后放行
            return True

    logger = logging.getLogger("app.secure")
    logger.handlers.clear()
    logger.propagate = False
    logger.setLevel(logging.DEBUG)

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter("SECURE | %(message)s"))
    handler.addFilter(SensitiveDataFilter())
    logger.addHandler(handler)

    logger.info("普通日志：用户登录成功")
    logger.info("危险日志：password=hunter2")
    logger.info("危险日志：api_token=abc123xyz")
    print()
    print("【要点】Filter 返回 False 丢弃记录；修改 record.msg 则可实现脱敏后继续输出。")


def demo_5_exception_logging():
    """异常日志记录最佳实践。"""
    print("=" * 70)
    print("【5】异常日志最佳实践")
    print("=" * 70)

    logger = logging.getLogger("app.errors")
    logger.handlers.clear()
    logger.propagate = False
    logger.setLevel(logging.DEBUG)
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter(
        "LOG | %(levelname)-8s | %(message)s", style="%"))
    logger.addHandler(handler)

    def level3_failure():
        # 真实触发一个异常
        result = {"key": "value"}
        return result["missing_key"]      # KeyError

    def level2_failure():
        # 第一种做法：logger.exception()
        # 只能在 except 块内调用（它内部用 sys.exc_info() 取当前异常），
        # 会自动以 ERROR 级别记录并附带完整 traceback。
        try:
            level3_failure()
        except KeyError:
            logger.exception("字典键不存在，配置读取失败")

    print("① logger.exception()（推荐，仅限 except 块内）")
    level2_failure()
    print()

    # 第二种做法：exc_info=True，可以在任何地方用，也能显式传异常对象
    print("② logger.error(msg, exc_info=True) —— 效果同 exception()")
    try:
        level3_failure()
    except KeyError:
        logger.error("同上，这是 exc_info=True 的写法", exc_info=True)
    print()

    # 传入具体异常对象：只有在 except 块外、手里已有异常实例时才有意义
    print("③ logger.error(msg, exc_info=exc) —— 传入已有异常对象")
    caught = None
    try:
        level3_failure()
    except KeyError as e:
        caught = e
    # 注意：此时已经在 except 块外，sys.exc_info() 返回 (None,None,None)
    logger.error(f"捕获到的异常是 {type(caught).__name__}，但故意不附 traceback")
    logger.error("显式传入异常对象 -> 附带 traceback", exc_info=caught)
    print()

    # 常见错误做法：手动格式化 traceback
    print("④ 反例：手动拼接 traceback 字符串（不推荐）")
    import traceback as tb_module
    try:
        level3_failure()
    except KeyError:
        # 错误做法 1：塞进 %s 占位符 -> 转义换行，日志文件里是一坨长文本
        logger.error("出错了：%s", tb_module.format_exc().replace("\n", "\\n"))
        # 错误做法 2：f-string 拼接 -> 丢失 %-格式风格，且无法延迟求值
        logger.error(f"出错了：{tb_module.format_exc()}")
    print("   -> 对比上面 ①②③，正确做法输出的是结构化的多行 traceback")
    print()

    print("【要点】必须附 traceback 的四种写法优先级：")
    print("   1. logger.exception(msg)         —— except 块内最简洁")
    print("   2. logger.error(msg, exc_info=True) —— 需要控制更灵活时")
    print("   3. logger.error(msg, exc_info=e)    —— 已有异常实例时（except 块外）")
    print("   4. 禁止：f'{traceback.format_exc()}' —— 破坏结构，无法被日志系统解析")
    print()

    print("【要点】logger.exception() 等价于 logger.error(msg, exc_info=True)，级别固定 ERROR。")
    print("【要点】logger.warning(..., exc_info=True) 可以降级为「记录但不算错误」。")


def demo_6_json_logging():
    """结构化 JSON 日志。"""
    print("=" * 70)
    print("【6】结构化 JSON 日志")
    print("=" * 70)

    # ===== 语法解析 =====
    # 结构化日志的价值：机器可解析。
    # 纯文本日志需要正则解析，字段边界不可靠；
    # JSON 每条一行（JSONL），可以按行读取后 json.loads()。
    # 监控系统（ELK / Loki / Prometheus）普遍要求这种格式。
    class JsonFormatter(logging.Formatter):
        """把 LogRecord 序列化成一行 JSON。"""

        def format(self, record):
            # ===== 语法解析 =====
            # LogRecord 是 logging 的核心数据结构，包含：
            #   name/levelname/levelno/pathname/lineno/msg/args/asctime/...
            # 以及通过 logger.info("...", extra={...}) 传入的自定义字段。
            # 我们挑选需要的字段 + 拼接 traceback。
            payload = {
                "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%S"),
                "level": record.levelname,
                "logger": record.name,
                "message": record.getMessage(),   # 用 getMessage() 而非 record.msg
                "module": record.module,
                "func": record.funcName,
                "line": record.lineno,
            }

            # 把 extra 传入的自定义字段也带上（排除 LogRecord 自带的固定字段）
            standard = {
                "name", "msg", "args", "levelname", "levelno", "pathname",
                "filename", "module", "exc_info", "exc_text", "stack_info",
                "lineno", "funcName", "created", "msecs", "relativeCreated",
                "thread", "threadName", "processName", "process", "asctime",
                "taskName",
            }
            custom = {k: v for k, v in record.__dict__.items() if k not in standard}
            if custom:
                payload["extra"] = custom

            # 异常信息单独放一个字段，避免污染 message
            if record.exc_info:
                # self.formatException(record.exc_info) 返回格式化后的 traceback 字符串
                payload["exception"] = self.formatException(record.exc_info)

            # ensure_ascii=False 保留中文原样，便于人工排查
            # separators=(",", ":") 去掉多余空格，减小日志体积
            return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))

    logger = logging.getLogger("app.json")
    logger.handlers.clear()
    logger.propagate = False
    logger.setLevel(logging.DEBUG)

    json_handler = logging.FileHandler(JSON_LOG, mode="w", encoding="utf-8")
    json_handler.setFormatter(JsonFormatter())
    logger.addHandler(json_handler)
    # 额外加一个控制台 handler 方便观察
    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(logging.Formatter("JSONLOG | %(message)s"))
    logger.addHandler(console)

    print("① 普通结构化日志（含 extra 自定义字段）：")
    logger.info("用户下单", extra={
        "user_id": 1001,
        "order_id": "SO-2026-001",
        "amount": 299.5,
    })
    print()

    print("② 带异常的结构化日志：")
    try:
        int("not_a_number")
    except ValueError:
        logger.error("金额转换失败", extra={"order_id": "SO-2026-001"}, exc_info=True)
    print()

    print(f"③ 生成的 JSONL 文件：{JSON_LOG}")
    print("   实际内容（每行一条 JSON）：")
    content = JSON_LOG.read_text(encoding="utf-8").strip()
    for i, line in enumerate(content.split("\n"), 1):
        # 打印前 110 字符，避免 traceback 部分过长
        display = line if len(line) <= 110 else line[:110] + " ...(截断)"
        print(f"   {i}. {display}")
    print()

    print("【要点】结构化日志三要素：固定字段 + extra 自定义字段 + 异常独立字段。")
    print("【要点】JSONL 格式（一行一个 JSON 对象）是日志采集的事实标准。")
    print("【要点】用 getMessage() 而非 record.msg，因为 msg 可能含 %s 占位符未替换。")


def demo_7_module_pattern():
    """模块化 logger 的正确用法。"""
    print("=" * 70)
    print("【7】模块化 logger 的正确写法")
    print("=" * 70)

    # ===== 语法解析 =====
    # 反模式：logger = logging.getLogger(__name__) 写成了全局变量，
    #         或者直接用 logging.info()（走 root）。
    # 正模式：模块级单例 logger = logging.getLogger(__name__)，只调配置不重复配置。
    #
    # 工程约定：
    #   - 每个模块用 getLogger(__name__)，名字自动是模块路径
    #   - 只有应用入口（main）调用 basicConfig
    #   - 库代码绝不调用 basicConfig（会劫持宿主程序的日志配置）
    module_logger = logging.getLogger("myapp.service.order")

    print(f"模块 logger 名: {module_logger.name}")
    print(f"推断出的层级: {'.'.join(module_logger.name.split('.')[:-1])}")
    print()

    # ===== 语法解析 =====
    # 用 extra 传递上下文（推荐做法）：
    # 不要用 %-格式化把上下文拼进 message，否则无法结构化。
    def process_order(order_id, user_id=None):
        # %-占位符由 logging 在最终输出时才替换（延迟格式化），
        # 这样即使级别不够、最终不输出，省下的也是格式化开销。
        module_logger.debug("开始处理订单 %s", order_id)
        module_logger.info("订单处理完成 %s", order_id,
                           extra={"order_id": order_id, "user_id": user_id})

    # 复用之前配置的 app.json logger 来展示 extra 的效果
    jl = logging.getLogger("app.json")
    jl.info("订单服务处理完成", extra={
        "order_id": "SO-2026-777",
        "user_id": 2002,
        "duration_ms": 15.3,
    })
    print("（上面这行已按 JSON 格式写入 app.jsonl）")
    print()

    print("【要点】库/模块代码只创建 logger，不调用 basicConfig —— 否则污染宿主配置。")
    print("【要点】用 %s 延迟占位符，不要用 f-string —— 后者会无条件执行格式化。")
    print("【要点】上下文用 extra={} 传递，保持 message 简洁可聚合。")


def demo_8_rotate_and_cleanup():
    """日志文件轮转验证与收尾。"""
    print("=" * 70)
    print("【8】生成的日志文件与轮转配置")
    print("=" * 70)

    print(f"日志目录: {LOG_DIR}")
    for f in sorted(LOG_DIR.glob("*")):
        size = f.stat().st_size
        # stat().st_size 是字节数
        print(f"   {f.name:<16} {size:>8} 字节")
    print()
    print("【RotatingFileHandler 配置说明】")
    print(f"   maxBytes    = 100000  单文件超过 100KB 就轮转")
    print(f"   backupCount = 3       最多保留 demo.log.1 / .2 / .3")
    print("   轮转策略：按大小适合写日志量可预估的场景；")
    print("             按时间（TimedRotatingFileHandler）适合每天固定生成日志的场景。")
    print()
    print("【要点】生产环境必须配轮转，否则日志会撑爆磁盘导致服务不可用。")


def main():
    """主入口。"""
    print("=" * 70)
    print("logging 完整配置演示")
    print("=" * 70)
    demo_1_levels_and_basicconfig()
    demo_2_hierarchy()
    demo_3_multi_handler()
    demo_4_filter()
    demo_5_exception_logging()
    demo_6_json_logging()
    demo_7_module_pattern()
    demo_8_rotate_and_cleanup()
    print()
    print("=" * 70)
    print(f"演示结束。日志文件位于: {LOG_DIR}")
    print("=" * 70)


if __name__ == "__main__":
    main()