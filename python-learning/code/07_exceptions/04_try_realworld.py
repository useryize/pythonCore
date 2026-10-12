#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
真实场景异常处理策略对比
==============================

【演示的语法点】
1. 网络请求失败：urllib 真实发起请求（连接失败 / 超时 / HTTP 错误）
2. 文件不存在 / 权限不足 / 编码错误的不同处理策略
3. JSON 解析失败的降级策略（fail-fast vs fail-safe vs 兜底重试）
4. 参数校验失败的两种思路：raise-early（快速失败）vs 返回错误对象
5. 四种策略对比表：抛出 / 返回 None / 返回默认值 / 重试降级
6. 异常聚合：一次收集多个错误（ExceptionGroup，Python 3.11+）
7. 上下文管理器 + 异常处理的配合

【预期输出摘要】
- 网络演示：真实请求一个必然失败的地址（本地未监听端口）与一个真实可达地址
- 文件演示：三种文件错误的捕获顺序演示
- JSON 演示：三种降级策略的输出对比
- 校验演示：批量收集所有字段错误（ExceptionGroup）
- 末尾打印四策略对比表
"""

import json
import socket
import tempfile
import urllib.error
import urllib.request
from pathlib import Path


# ===== 语法解析 =====
# 【1】网络异常的三层结构
#   URLError            <- urllib 顶层异常，通常包裹 socket 错误
#   ├── HTTPError       <- 服务端返回了 4xx/5xx（是一个合法的「响应」而非传输失败）
#   └── URLError(reason=socket.timeout)  <- 连接阶段超时
#   socket.timeout 是 socket.timeout 的别名（Python 3.10 起 timeout 成为 OSError 子类）
#
# 【2】处理顺序的正确性
#   HTTPError 是 URLError 的子类，必须先 except HTTPError，
#   否则它会被 `except URLError` 先吃掉，导致 404/500 无法区分。
class NetworkErrorPolicy:
    """网络请求的异常处理策略集合。"""

    @staticmethod
    def fetch_with_retry(url, max_retries=2, timeout=2.0):
        """带重试的网络请求：演示「可恢复错误重试，不可恢复错误快速失败」。"""
        print(f"  请求: {url} (最多重试 {max_retries} 次, 超时 {timeout}s)")

        # ===== 语法解析 =====
        # for ... in range(max_retries + 1) 产生 0..max_retries，
        # +1 是因为「首次尝试」不算在「重试」里。
        for attempt in range(max_retries + 1):
            is_last = (attempt == max_retries)
            try:
                # urllib.request.urlopen 返回一个 HTTPResponse 对象，
                # 它本身是一个上下文管理器（支持 with），必须及时关闭。
                with urllib.request.urlopen(url, timeout=timeout) as resp:
                    data = resp.read().decode("utf-8")
                    return {"ok": True, "status": resp.status, "data": data[:60]}
            except urllib.error.HTTPError as e:
                # HTTPError 有 .code / .reason / .headers 属性
                # 4xx 是客户端错误（不重试），5xx 是服务端错误（可重试）
                if 400 <= e.code < 500:
                    print(f"  [尝试{attempt + 1}] HTTP {e.code} {e.reason} -> 客户端错误，不重试")
                    return {"ok": False, "kind": "http_client_error", "status": e.code}
                print(f"  [尝试{attempt + 1}] HTTP {e.code} {e.reason} -> 服务端错误，{'放弃' if is_last else '重试'}")
                if is_last:
                    return {"ok": False, "kind": "http_server_error", "status": e.code}
            except socket.timeout:
                # 超时属于「暂时性」错误，最值得重试
                print(f"  [尝试{attempt + 1}] 请求超时 -> {'放弃' if is_last else '重试'}")
                if is_last:
                    return {"ok": False, "kind": "timeout"}
            except urllib.error.URLError as e:
                # 走到这里说明是连接层失败（DNS 失败、连接被拒绝等）
                # e.reason 是底层的 socket 异常对象
                print(f"  [尝试{attempt + 1}] 连接失败: {e.reason}")
                return {"ok": False, "kind": "connection", "reason": str(e.reason)}
            except Exception as e:
                # 最外层兜底：任何未预料的异常都不能让整个程序崩溃
                print(f"  [尝试{attempt + 1}] 未知异常: {type(e).__name__}: {e}")
                return {"ok": False, "kind": "unknown", "error": str(e)}
        # for 循环正常走完（理论上不可达，因为最后一次总会 return）
        return {"ok": False, "kind": "exhausted"}

    @staticmethod
    def fetch_fail_safe(url, default=None, timeout=2.0):
        """fail-safe 策略：任何异常都返回默认值，永不抛出。"""
        try:
            with urllib.request.urlopen(url, timeout=timeout) as resp:
                return resp.read().decode("utf-8")
        except Exception:
            # 兜底捕获所有异常，直接返回默认值。
            # 适用场景：非核心链路（如统计上报），失败不能影响主流程。
            return default

    @staticmethod
    def fetch_fail_fast(url, timeout=2.0):
        """fail-fast 策略：包装成统一异常，让调用方决定怎么处理。"""
        try:
            with urllib.request.urlopen(url, timeout=timeout) as resp:
                return resp.read().decode("utf-8")
        except urllib.error.HTTPError as e:
            # 异常翻译：把 HTTP 状态码异常翻译成业务异常
            raise ServiceUnavailableError(
                f"服务返回 {e.code}", status=e.code) from e
        except (urllib.error.URLError, socket.timeout) as e:
            raise ServiceUnavailableError(f"无法连接服务: {e}") from e


class ServiceUnavailableError(Exception):
    """服务不可用（业务异常，承载 HTTP 状态码）。"""

    def __init__(self, message, status=None):
        super().__init__(message)
        # 记录状态码，便于上层决定是否降级
        self.status = status


def demo_network():
    """网络请求失败的四种策略对比。"""
    print("=" * 70)
    print("【1】网络请求失败 —— 策略对比")
    print("=" * 70)

    # 构造一个必然失败的地址：本地一个没人监听的端口。
    # 这样不依赖外网，结果稳定可复现。
    # socket 探测：先确认这个端口确实没人监听
    sock = socket.socket()
    sock.settimeout(0.3)
    # 绑定到随机端口再关闭，即可得到一个「几乎肯定无人监听」的端口
    sock.bind(("127.0.0.1", 0))
    dead_port = sock.getsockname()[1]
    sock.close()
    dead_url = f"http://127.0.0.1:{dead_port}/api/data"

    print(f"① fail-fast（包装成业务异常）：")
    try:
        NetworkErrorPolicy.fetch_fail_fast(dead_url, timeout=1.0)
    except ServiceUnavailableError as e:
        print(f"   -> 捕获到 {type(e).__name__}: {e}")
        print(f"   -> 异常链 __cause__ = {type(e.__cause__).__name__}")
    print()

    print(f"② fail-safe（返回默认值，永不抛）：")
    value = NetworkErrorPolicy.fetch_fail_safe(dead_url, default="[默认数据]", timeout=1.0)
    print(f"   -> 返回 {value!r}（调用方无需写 try/except）")
    print()

    print(f"③ 带重试（可恢复错误才重试）：")
    result = NetworkErrorPolicy.fetch_with_retry(dead_url, max_retries=2, timeout=1.0)
    print(f"   -> 最终结果 {result}")
    print()

    print("【策略选择原则】")
    print("   fail-fast  : 核心链路，失败必须让上层知道（配合降级方案）")
    print("   fail-safe  : 旁路/非核心链路，失败静默用默认值")
    print("   retry      : 仅对「暂时性错误」(超时/5xx) 重试，4xx 立即失败")
    print("   circuit    : 大规模场景需配合熔断（标准库无此能力，需第三方库）")
    print()


def demo_file_errors():
    """文件相关的三类错误：不存在 / 权限 / 编码。"""
    print("=" * 70)
    print("【2】文件错误 —— 不存在 / 权限 / 编码")
    print("=" * 70)

    base = Path(tempfile.gettempdir())
    # ===== 语法解析 =====
    # Path 是 pathlib 的对象，用 / 运算符拼接路径，比字符串拼接更安全：
    #   "a" + "/" + "b"  在 Windows 上可能产生 "a\\/b" 之类的混合分隔符问题
    missing_file = base / "not_exist_file.txt"
    temp_file = base / "_demo_encoding.txt"
    # 写入 UTF-8 中文内容
    temp_file.write_text("中文内容\n", encoding="utf-8")

    print("① 文件不存在 —— 三种策略")
    # 策略A：让异常传播（fail-fast）
    try:
        missing_file.read_text(encoding="utf-8")
    except FileNotFoundError as e:
        print(f"   [fail-fast] FileNotFoundError: {e.filename}")
    print()

    # 策略B：判断存在性后降级（fail-safe，但要先检查，浪费一次 IO）
    content = (missing_file.read_text(encoding="utf-8")
               if missing_file.exists() else "[使用默认配置]")
    print(f"   [exists 检查] {content!r}")
    # 注意：exists() 与 read 之间存在「竞态窗口」（TOCTOU），
    # 高并发下文件可能刚好被删除，所以生产代码仍应以捕获异常为准。
    print()

    # 策略C：捕获异常并给默认值（推荐，无竞态问题）
    try:
        content = missing_file.read_text(encoding="utf-8")
    except FileNotFoundError:
        content = "[使用默认配置]"
    print(f"   [异常兜底] {content!r}  <- 推荐这种")
    print()

    print("② 编码错误 —— 用错编码读取")
    # 用 latin-1 读 UTF-8 的中文文件：latin-1 能映射所有字节，不会报解码错误，
    # 但会得到乱码（这演示了「静默乱码」的危害）。
    garbled = temp_file.read_text(encoding="latin-1")
    print(f"   用 latin-1 读取 UTF-8 文件（不报错但乱码）: {garbled!r}")
    print(f"   -> 危险！没有异常提示，数据已经损坏")
    print()

    # 用 utf-8 读 GBK 编码的文件：会抛 UnicodeDecodeError（显式失败，更安全）
    try:
        # 先造一个 GBK 文件
        gbk_file = base / "_demo_gbk.txt"
        gbk_file.write_bytes("中文".encode("gbk"))
        gbk_file.read_text(encoding="utf-8")
    except UnicodeDecodeError as e:
        print(f"   [显式失败] UnicodeDecodeError: {e.object[:10]!r} @ 位置 {e.start}")
        print(f"              e.reason = {e.reason}, e.encoding = {e.encoding}")
    finally:
        # 清理临时文件
        for f in [temp_file, base / "_demo_gbk.txt"]:
            if f.exists():
                f.unlink()
    print()
    print("【要点】latin-1 永不报错 -> 静默乱码；utf-8 解码失败会抛异常 -> 显式暴露。")
    print("【要点】读写文本文件必须显式指定 encoding=True，永远不要依赖平台默认值。")
    print()


def demo_json_strategies():
    """JSON 解析失败的三种降级策略。"""
    print("=" * 70)
    print("【3】JSON 解析失败 —— 三种降级策略")
    print("=" * 70)

    bad_payloads = [
        '{"name": "Tom", "age": 18}',   # 合法
        "{name: 'Tom'}",                # 非法：单引号 + 无引号键
        "",# 空字符串
        '{"name": "Tom",}',            # 非法：尾随逗号
        "not json at all",
    ]

    # 策略A：fail-fast，尽早崩溃
    def parse_strict(text):
        try:
            return {"ok": True, "data": json.loads(text)}
        except json.JSONDecodeError as e:
            raise ValueError(f"配置格式非法（位置 {e.pos}，行{e.lineno} 列{e.colno}）") from e

    # 策略B：fail-safe，返回 None
    def parse_safe(text):
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return None

    # 策略C：带默认值 + 修复尝试
    def parse_with_recovery(text):
        """尝试修复常见的「机器生成 JSON」错误。"""
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            # 修复策略1：尝试去掉尾随逗号
            import re
            # 正则：匹配 , 后紧跟 } 或 ] 的位置
            fixed = re.sub(r",\s*([\]}])", r"\1", text)
            try:
                return json.loads(fixed)
            except json.JSONDecodeError:
                # 修复策略2：仍失败则用默认值
                return {"name": "default", "recovered": False}
            else:
                return {"name": "default", "recovered": True}

    for payload in bad_payloads:
        print(f"\n输入: {payload!r}")
        # A
        try:
            r = parse_strict(payload)
            print(f"  A[strict]   成功 -> {r}")
        except ValueError as e:
            print(f"  A[strict]   失败 -> {e}")
        # B
        print(f"  B[safe]     -> {parse_safe(payload)!r}")
        # C
        print(f"  C[recovery] -> {parse_with_recovery(payload)}")
    print()
    print("【策略选择】")
    print("   strict  : 配置文件/接口数据，格式错必须立刻暴露，否则问题被掩盖")
    print("   safe    : 非关键的可选数据，失败返回 None 即可")
    print("   recovery: 来自第三方系统的脏数据，可尝试修复 + 兜底默认值")
    print()


def demo_validation_strategies():
    """参数校验：raise-early vs 收集全部错误。"""
    print("=" * 70)
    print("【4】参数校验 —— 快速失败 vs 收集全部错误")
    print("=" * 70)

    # ===== 语法解析 =====
    # 两种校验风格：
    #   raise-early : 第一个错就抛，调用方逐个修错（体验差但逻辑简单）
    #   collect-all : 把所有错收集起来一次性抛出（体验好，实现复杂）
    # collect-all 的标准工具是 ExceptionGroup（Python 3.11+ 标准库）。

    def validate_raise_early(user):
        """策略A：快速失败，发现第一个错误立即抛。"""
        if not user.get("name"):
            raise ValueError("name 不能为空")
        if not isinstance(user.get("age"), int):
            raise TypeError("age 必须是整数")
        if not (0 <= user.get("age", -1) <= 150):
            raise ValueError("age 必须在 0-150 之间")
        return True

    def validate_collect_all(user):
        """策略B：收集所有错误，用 ExceptionGroup 一次性抛出。"""
        errors = []
        if not user.get("name"):
            errors.append(ValueError("name 不能为空"))
        if not isinstance(user.get("age"), int):
            errors.append(TypeError("age 必须是整数"))
        elif not (0 <= user["age"] <= 150):
            errors.append(ValueError("age 必须在 0-150 之间"))
        if not user.get("email"):
            errors.append(ValueError("email 不能为空"))
        elif "@" not in user["email"]:
            errors.append(ValueError("email 格式不正确"))

        # ===== 语法解析 =====
        # ExceptionGroup(msg, excs) 要求 excs 是「非空」异常序列。
        # 若为空会抛 ValueError，所以必须先判断再构造。
        if errors:
            raise ExceptionGroup("参数校验未通过", errors)
        return True

    bad_user = {"name": "", "age": "abc", "email": "not-an-email"}

    print(f"待校验数据: {bad_user}\n")

    print("策略A：raise-early（只能看到第一个错误）")
    try:
        validate_raise_early(bad_user)
    except Exception as e:
        print(f"   -> {type(e).__name__}: {e}")
    print("   -> 用户需要修 3 次才能提交成功（体验差）")
    print()

    print("策略B：collect-all + ExceptionGroup（一次看到全部）")
    try:
        validate_collect_all(bad_user)
    except* ValueError as eg:
        # ===== 语法解析 =====
        # `except*` 是 Python 3.11 新增的「异常组专用 except」语法：
        # 它只捕获 ExceptionGroup 中匹配类型的子异常，
        # 匹配失败的子异常会被重新打包成新的 ExceptionGroup 继续传播。
        # 与普通 `except Exception` 的区别：except* 会「拆包并筛选」。
        print(f"   ValueError 组内 {len(eg.exceptions)} 条：")
        for e in eg.exceptions:
            print(f"      - {e}")
    except* TypeError as eg:
        print(f"   TypeError 组内 {len(eg.exceptions)} 条：")
        for e in eg.exceptions:
            print(f"      - {e}")
    print()
    print("   -> 用户一次就能看到全部问题（体验好）")
    print()

    print("ExceptionGroup 的结构：")
    try:
        validate_collect_all(bad_user)
    except ExceptionGroup as eg:
        print(f"   type       = {type(eg).__name__}")
        print(f"   message    = {eg.message}")
        print(f"   exceptions = {len(eg.exceptions)} 个")
        for i, sub in enumerate(eg.exceptions, 1):
            print(f"     {i}. {type(sub).__name__}: {sub}")
    print()


def demo_error_result_pattern():
    """Result 模式：不抛异常，用返回值表达失败。"""
    print("=" * 70)
    print("【5】Result 模式 —— 用返回值代替异常")
    print("=" * 70)

    # ===== 语法解析 =====
    # Result 模式的优势：
    #   1) 失败路径在类型上可见（返回类型是 Result 而非 任意类型）
    #   2) 调用方「必须」处理失败，不会像异常那样被静默忽略
    #   3) 不会产生 traceback 对象的开销，异常在 Python 中有显著性能成本
    from dataclasses import dataclass, field

    @dataclass
    class Result:
        """统一的结果容器。"""
        value: object = None
        error: object = None
        # field(default_factory=list)：可变默认值必须用工厂，否则所有实例共享同一个 list
        warnings: list = field(default_factory=list)

        @property
        def is_ok(self):
            # @property 把方法伪装成属性，调用时写 result.is_ok 而非 result.is_ok()
            return self.error is None

        def unwrap(self):
            """取出值，失败则抛异常（Python 生态惯用做法）。"""
            if self.error is not None:
                # 把它包成 RuntimeError，保持「unwrap 失败必崩」的契约
                raise RuntimeError(f"unwrap 失败: {self.error}")
            return self.value

    def parse_port(text):
        """解析端口号，返回 Result 而不抛异常。"""
        warnings = []
        try:
            port = int(text)
            if not (1 <= port <= 65535):
                return Result(error=f"端口 {port} 超出合法范围")
            if port < 1024:
                # 非致命问题：记录警告但仍返回成功
                warnings.append(f"端口 {port} < 1024，需要管理员权限")
            return Result(value=port, warnings=warnings)
        except ValueError:
            return Result(error=f"'{text}' 不是合法的整数")
        except TypeError:
            return Result(error=f"期望字符串，得到 {type(text).__name__}")

    print("① 成功用例:")
    r = parse_port("8080")
    print(f"   is_ok = {r.is_ok}, value = {r.value}, warnings = {r.warnings}")
    print()

    print("② 成功但有警告:")
    r = parse_port("80")
    print(f"   is_ok = {r.is_ok}, value = {r.value}, warnings = {r.warnings}")
    print()

    print("③ 失败用例（注意：不需要 try/except）：")
    r = parse_port("99999")
    print(f"   is_ok = {r.is_ok}, error = {r.error}")
    print()

    print("④ 非字符串输入:")
    r = parse_port(None)
    print(f"   is_ok = {r.is_ok}, error = {r.error}")
    print()

    print("⑤ unwrap 把失败转成异常（桥接两种风格）：")
    try:
        parse_port("abc").unwrap()
    except RuntimeError as e:
        print(f"   -> {e}")
    print()

    print("【对比】")
    print("   异常模式  : 适合「异常情况罕见 + 需要完整 traceback」")
    print("   Result 模式: 适合「失败是常规业务流 + 需要类型可见 + 高频调用」")
    print("   Python 生态常混用：内部 Result，对外 unwrap 成异常")


def strategy_comparison_table():
    """四种策略对比表。"""
    print()
    print("=" * 70)
    print("【6】异常处理策略对比表")
    print("=" * 70)
    table = [
        ("策略", "调用方写法", "优点", "缺点", "适用场景"),
        ("抛出", "try/except", "类型明确、可追溯", "忘记捕获会崩", "核心流程"),
        ("返回None", "if x is None", "简单", "None 与合法值混淆", "可选数据"),
        ("返回默认值", "直接用", "调用方无负担", "掩盖问题", "旁路/统计"),
        ("Result对象", "if r.is_ok", "类型可见、强制处理", "样板代码多", "高频校验"),
        ("重试降级", "自动完成", "提升可用性", "需防雪崩", "网络/存储"),
        ("异常组", "except*", "一次报全错", "3.11+ 才支持", "表单/批量校验"),
    ]
    for i, row in enumerate(table):
        # 首行是表头，其余左对齐；用固定宽度占位便于阅读
        if i == 0:
            print(" | ".join(f"{c:<14}" for c in row[:4]))
            print("-" * 78)
        else:
            print(" | ".join(f"{c:<14}" for c in row[:4]))
    print()
    print("完整第5列（适用场景）：")
    for row in table[1:]:
        print(f"   {row[0]:<12} -> {row[4]}")


def main():
    """主入口。"""
    print("=" * 70)
    print("真实场景异常处理策略对比")
    print("=" * 70)
    demo_network()
    demo_file_errors()
    demo_json_strategies()
    demo_validation_strategies()
    demo_error_result_pattern()
    strategy_comparison_table()
    print("=" * 70)
    print("演示结束")
    print("=" * 70)


if __name__ == "__main__":
    main()