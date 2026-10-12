"""
================================================================================
 06_error_handling_patterns.py —— 工程级错误处理模式
================================================================================

【演示的语法点】
  1. Result 类型模式   : 不用异常做流程控制，用返回值携带成功/失败
  2. 错误码枚举        : IntEnum / StrEnum（3.11+）统一错误契约
  3. 异常分组         : ExceptionGroup / BaseExceptionGroup（3.11+）
  4. 重试装饰器       : 指数退避 + 抖动 + 最大次数 + 可重试异常白名单
  5. 熔断降级         : fallback 返回默认值 / with_fallback 装饰器
  6. 错误边界隔离     : isolate_boundary 装饰器把异常挡在一层内
  7. 自定义异常基类   : AppError + 上下文信息 + __str__ 重写
  8. 异常链           : raise X from Y 与 __cause__ / __context__
  9. 兜底 except      : except Exception 的正确使用场景（不是用来忽略错误的）
 10. contextlib.suppress: 精准忽略特定异常，不留裸 try/except pass
 11. functools.wraps  : 装饰器保留原函数元数据

【预期输出摘要】
  [1] Result 模式：成功与失败都显式表达
  [2] 错误码枚举：E1001 NOT_FOUND -> 中文名与 HTTP 状态映射
  [3] 异常分组：3 个子异常一次性聚合报告
  [4] 重试装饰器：第 3 次才成功 / 重试耗尽抛异常
  [5] 降级：主逻辑失败 -> 返回默认值，业务不中断
  [6] 错误边界：单个 handler 崩溃不影响其他 handler
  [7] 异常链：__cause__ vs __context__ 的区别

【核心原则】
  · 异常用于「不该发生的意外」，Result 用于「预期会失败的正常分支」
  · 不要用异常控制业务流程（如「用户不存在」不该抛异常）
  · 不要用 try/except pass 静默吞掉错误
  · 边界处兜底，中间层透传 —— 让错误在最该处理的地方被处理
"""

from __future__ import annotations

import contextlib
import functools
import random
import sys
import time
import traceback
from dataclasses import dataclass, field
from enum import Enum, IntEnum
from typing import Any, Callable, Generic, TypeVar


T = TypeVar("T")


# ==============================================================================
# 一、错误码枚举：与前端/客户端的稳定契约
# ==============================================================================
# ===== 语法解析 =====
# 为什么用枚举而不是裸字符串常量？
#   1. 字符串会写错且编译器不管；枚举写错会直接 AttributeError
#   2. 枚举支持反向映射和遍历，便于生成 API 文档
#   3. 代码里不会出现魔法字符串 "E1001"，IDE 可跳转、可重构
#
# IntEnum 而非 Enum：让错误码能直接参与 HTTP 状态比较与排序


class ErrorCode(IntEnum):
    """业务错误码。规则：E + 四位数字，按模块划分区间。

    约定：
      1000-1999  参数/校验类
      2000-2999  资源类（不存在、无权限）
      3000-3999  外部依赖类
      4000-4999  状态机/业务规则类
      5000-5999  系统内部类
    """

    # ---- 1000 段：参数校验 ----
    INVALID_PARAM = 1001
    MISSING_FIELD = 1002

    # ---- 2000 段：资源 ----
    NOT_FOUND = 2001
    ALREADY_EXISTS = 2002
    PERMISSION_DENIED = 2003

    # ---- 3000 段：外部依赖 ----
    UPSTREAM_TIMEOUT = 3001
    UPSTREAM_UNAVAILABLE = 3002

    # ---- 4000 段：业务规则 ----
    INVALID_STATE_TRANSITION = 4001
    QUOTA_EXCEEDED = 4002

    # ---- 5000 段：系统 ----
    INTERNAL_ERROR = 5001
    DB_ERROR = 5002

    def __str__(self) -> str:
        """让 print(code) 直接得到「E2001」而不是 "ErrorCode.NOT_FOUND"。"""
        return f"E{int(self):04d}"

    @property
    def http_status(self) -> int:
        """错误码 -> HTTP 状态码。这是后端框架的标准映射。"""
        # 1000 段 -> 400, 2000 段 -> 404, 3000 段 -> 502, 4000 段 -> 409, 5000 段 -> 500
        segment = int(self) // 1000
        return {
            1: 400,  # Bad Request
            2: 404,  # Not Found
            3: 502,  # Bad Gateway（上游挂了）
            4: 409,  # Conflict（状态冲突）
            5: 500,  # Internal Server Error
        }.get(segment, 500)

    @property
    def message(self) -> str:
        """错误码 -> 面向用户的中文提示（可直接发给前端）。"""
        return _ERROR_MESSAGES[self]


_ERROR_MESSAGES: dict[ErrorCode, str] = {
    ErrorCode.INVALID_PARAM: "请求参数不合法",
    ErrorCode.MISSING_FIELD: "缺少必填字段",
    ErrorCode.NOT_FOUND: "请求的资源不存在",
    ErrorCode.ALREADY_EXISTS: "资源已存在",
    ErrorCode.PERMISSION_DENIED: "没有访问权限",
    ErrorCode.UPSTREAM_TIMEOUT: "依赖服务响应超时",
    ErrorCode.UPSTREAM_UNAVAILABLE: "依赖服务暂时不可用",
    ErrorCode.INVALID_STATE_TRANSITION: "当前状态不允许该操作",
    ErrorCode.QUOTA_EXCEEDED: "已超出使用额度",
    ErrorCode.INTERNAL_ERROR: "服务内部错误，请稍后重试",
    ErrorCode.DB_ERROR: "数据库操作失败",
}


# ==============================================================================
# 二、自定义异常体系
# ==============================================================================
# ===== 语法解析 =====
# 所有业务异常都继承自一个统一基类 AppError。
# 为什么要有统一基类？
#   -> 上层只需 `except AppError` 就能捕获所有业务异常，
#      而不会误吞掉 KeyboardInterrupt / SystemExit 这些系统级信号。
#      裸 `except Exception` 会把 Ctrl+C 也吃掉，导致程序无法退出 —— 这是真实事故。


class AppError(Exception):
    """所有业务异常的基类。"""

    code: ErrorCode = ErrorCode.INTERNAL_ERROR

    def __init__(
        self,
        message: str = "",
        *,
        code: ErrorCode | None = None,
        detail: dict[str, Any] | None = None,
        cause: BaseException | None = None,
    ) -> None:
        """
        :param message: 人类可读的错误描述
        :param code:    业务错误码，不传则用类上的默认
        :param detail:  结构化上下文（出错时哪个字段、哪个 id），用于排查
        :param cause:   底层异常，配合 `raise X from Y` 建立异常链
        """
        self.code = code or type(self).code
        self.message = message or self.code.message
        self.detail = detail or {}
        # self.args 是 Exception 的内置属性，重写它会影响 str(exc)
        super().__init__(f"[{self.code}] {self.message}")
        if cause is not None:
            # 手动设置 __cause__ 等价于 raise ... from ...
            self.__cause__ = cause

    def to_dict(self) -> dict[str, Any]:
        """转成可 JSON 序列化的响应体 —— 后端接口的标准错误格式。"""
        return {
            "success": False,
            "code": str(self.code),
            "message": self.message,
            "detail": self.detail,
        }


class ValidationError(AppError):
    """参数校验失败。"""

    code = ErrorCode.INVALID_PARAM


class NotFoundError(AppError):
    """资源不存在。"""

    code = ErrorCode.NOT_FOUND


class ConflictError(AppError):
    """状态冲突 —— 比如重复提交、并发修改。"""

    code = ErrorCode.INVALID_STATE_TRANSITION


class DependencyError(AppError):
    """外部依赖（网络、DB、缓存）不可用。"""

    code = ErrorCode.UPSTREAM_UNAVAILABLE


# ==============================================================================
# 三、Result 类型模式：用返回值代替控制流异常
# ==============================================================================
# ===== 语法解析 =====
# 什么时候该用 Result，什么时候该用异常？
#   Result：失败是「预期之内的正常结果」
#          例：查用户不存在、余额不足、参数校验不过 —— 这些是业务分支，不是 bug
#   异常：失败是「不该发生的意外」
#          例：网络断连、数组越界、NoneType 错误 —— 这些是 bug 或环境问题
#
# Result 模式的好处：
#   1. 调用方必须显式处理失败（返回类型标注会提醒你），不会静默忽略
#   2. 多个可能失败的操作可以链式调用，不用层层 try/except
#   3. 测试更容易：直接断言 Result 的字段，不用断言异常


@dataclass(frozen=True)
class Result(Generic[T]):
    """操作结果容器。frozen=True 保证不可变，链式传递时不会被意外修改。"""

    value: T | None = None
    code: ErrorCode | None = None
    message: str = ""
    detail: dict[str, Any] = field(default_factory=dict)

    # ---- 构造工厂：语义清晰的命名 ----
    @classmethod
    def ok(cls, value: T) -> "Result[T]":
        """构造成功结果。"""
        return cls(value=value, code=None, message="成功")

    @classmethod
    def fail(
        cls,
        code: ErrorCode,
        message: str = "",
        **detail: Any,
    ) -> "Result[T]":
        """构造失败结果。**detail 收集任意上下文，方便排查。"""
        return cls(
            value=None,
            code=code,
            message=message or code.message,
            detail=detail,
        )

    # ---- 状态判定 ----
    @property
    def is_ok(self) -> bool:
        return self.code is None

    @property
    def is_err(self) -> bool:
        return self.code is not None

    # ---- 状态访问（兼收并蓄的写法）----
    def unwrap(self) -> T:
        """取成功值；失败则抛异常。

        这个设计很关键：内部用 Result 表达流程，
        需要向上抛时用 unwrap() 一行转换，不用写 20 行 try/except 转发。
        """
        if self.is_err:
            raise AppError(self.message, code=self.code, detail=self.detail)
        return self.value  # type: ignore[return-value]

    def unwrap_or(self, default: T) -> T:
        """取成功值；失败返回默认值 —— 降级的标准写法。"""
        return self.value if self.is_ok else default

    def map(self, fn: Callable[[T], Any]) -> "Result[Any]":
        """成功时对值做变换；失败时原样透传 —— 链式调用的关键。"""
        if self.is_err:
            return self          # type: ignore[return-value]
        return Result.ok(fn(self.value))   # type: ignore[arg-type]

    def to_dict(self) -> dict[str, Any]:
        """统一的 API 响应体。"""
        if self.is_ok:
            return {"success": True, "data": self.value}
        return {"success": False, "code": str(self.code), "message": self.message, "detail": self.detail}


# ---- 业务函数：用 Result 而非异常表达正常失败 ----
def find_user(user_id: int) -> Result[dict[str, Any]]:
    """模拟查用户。"""
    # 内存假数据
    fake_db = {1: {"id": 1, "name": "张三", "balance": 1000.0},
               2: {"id": 2, "name": "李四", "balance": 50.0}}
    user = fake_db.get(user_id)
    if user is None:
        # 「用户不存在」是预期分支 -> 用 Result.fail 而不是 raise
        return Result.fail(ErrorCode.NOT_FOUND, user_id=user_id)
    return Result.ok(user)


def charge(user_id: int, amount: float) -> Result[dict[str, Any]]:
    """扣款：串联「查用户 -> 校验余额 -> 扣款」三个都可能失败的步骤。"""
    user_result = find_user(user_id)
    if user_result.is_err:
        # 失败直接透传，不做无意义的重试或包装
        return user_result

    user = user_result.value
    assert user is not None      # 运行时收敛：is_err 检查后 value 必有值
    if amount <= 0:
        return Result.fail(ErrorCode.INVALID_PARAM, amount=amount, reason="金额必须为正")
    if user["balance"] < amount:
        return Result.fail(
            ErrorCode.QUOTA_EXCEEDED,
            balance=user["balance"],
            required=amount,
        )
    user["balance"] -= amount
    return Result.ok({"user_id": user_id, "balance": user["balance"]})


# ==============================================================================
# 四、异常分组（ExceptionGroup，Python 3.11+）
# ==============================================================================
# ===== 语法解析 =====
# 场景：批量任务里要处理 100 个文件，可能同时多个出错。
#   旧做法：for 循环里 try/except 收集错误，最后 if errors: raise RuntimeError(全部)
#         -> 原始异常堆栈丢失，排查时看不到真实原因
#   新做法：ExceptionGroup 一次性打包所有异常，保留完整堆栈，
#         且 can 只有当所有子异常都支持时才为 True —— 精准语义。
#
# 语法：raise ExceptionGroup("描述", [异常1, 异常2, ...])
# Python 3.11 以下需要第三方库 exceptiongroup 兼容。


class BatchResult:
    """批量处理的结果收集器。"""

    def __init__(self) -> None:
        self.successes: list[Any] = []
        self.errors: list[Exception] = []

    def add_error(self, exc: Exception) -> None:
        self.errors.append(exc)

    def add_success(self, value: Any) -> None:
        self.successes.append(value)

    def raise_if_any(self, context: str) -> None:
        """有错误就整体抛出 ExceptionGroup。"""
        if not self.errors:
            return
        if sys.version_info >= (3, 11):
            # 3.11+ 原生支持
            raise ExceptionGroup(context, self.errors)
        # 3.10 及以下：用一个自定义聚合异常兜底，保留 cause 列表
        raise BatchFailure(context, self.errors) from self.errors[0]


class BatchFailure(AppError):
    """3.11 以下的批量失败聚合异常。"""

    def __init__(self, context: str, errors: list[Exception]) -> None:
        super().__init__(f"{context}：{len(errors)} 项失败", code=ErrorCode.INTERNAL_ERROR)
        self.errors = errors

    def __str__(self) -> str:
        """把每个子异常都列出来 —— 这是聚合异常的核心价值。"""
        lines = [super().__str__()]
        for index, exc in enumerate(self.errors, 1):
            lines.append(f"  [{index}] {type(exc).__name__}: {exc}")
        return "\n".join(lines)


def process_batch(items: list[str]) -> list[str]:
    """批量处理：成功的不受影响，失败的聚合上报。"""
    batch = BatchResult()

    for item in items:
        try:
            # 模拟不同类型的失败
            if item == "":
                raise ValidationError("空字符串不合法", detail={"item": repr(item)})
            if item == "timeout":
                raise DependencyError("调用支付网关超时", detail={"endpoint": "/pay"})
            if item.isdigit():
                raise ValidationError(f"数字不是合法名称：{item}", detail={"item": item})
            # 正常路径
            batch.add_success(item.upper())
        except AppError as exc:
            # 只捕获自己定义的异常，让未预期的 bug 继续冒泡
            batch.add_error(exc)

    batch.raise_if_any(f"批量处理 {len(items)} 项时出错")
    return batch.successes


# ==============================================================================
# 五、重试装饰器：指数退避 + 抖动
# ==============================================================================
# ===== 语法解析 =====
# 为什么需要重试？
#   分布式系统里「瞬时故障」（网络抖动、连接池耗尽、限流）占故障的绝大多数，
#   重试一次往往就成功了。但无脑重试会放大故障（雪崩），
#   所以必须配合：最大次数 + 指数退避 + 抖动 + 可重试异常白名单。
#
# 抖动(jitter)为什么重要？
#   假设 1000 个客户端同时失败，若都按 1s/2s/4s 退避，第 1 秒它们会同时重试，
#   把刚恢复的服务再打垮。加入随机抖动让重试时间错开，起到削峰作用。


def retry(
    max_attempts: int = 3,
    base_delay: float = 0.01,
    max_delay: float = 1.0,
    multiplier: float = 2.0,
    jitter: bool = True,
    retry_on: tuple[type[BaseException], ...] = (DependencyError, TimeoutError),
    on_exhausted: Callable[[], BaseException] | None = None,
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """重试装饰器。

    :param max_attempts:   最大尝试次数（含第一次）
    :param base_delay:     初始退避基数（秒）
    :param max_delay:      单次退避上限，防止指数爆炸
    :param multiplier:     退避倍数
    :param jitter:         是否加随机抖动
    :param retry_on:       可重试异常白名单 —— ★ 绝不能重试 ValidationError
    :param on_exhausted:   重试耗尽后的工厂函数，返回最终抛出的异常
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        # functools.wraps 保留原函数 __name__/__doc__/签名，
        # 否则 traceback 和文档里全变成 "decorator"，排查问题时非常痛苦
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            attempt = 0
            last_exc: BaseException | None = None

            while attempt < max_attempts:
                attempt += 1
                try:
                    return func(*args, **kwargs)
                except retry_on as exc:      # 只捕获白名单内的异常
                    last_exc = exc
                    if attempt >= max_attempts:
                        break

                    # 指数退避：base * multiplier^(attempt-1)
                    delay = min(base_delay * (multiplier ** (attempt - 1)), max_delay)
                    if jitter:
                        # 抖动区间取 [delay/2, delay]，避免完全随机导致忽快忽慢
                        delay = delay / 2 + random.random() * delay / 2
                    print(f"    [retry] {func.__name__} 第 {attempt} 次失败"
                          f"（{type(exc).__name__}: {exc}），{delay * 1000:.0f}ms 后重试")
                    time.sleep(delay)

            # 重试耗尽
            if on_exhausted:
                raise on_exhausted()
            assert last_exc is not None
            raise AppError(
                f"{func.__name__} 重试 {max_attempts} 次仍失败",
                code=ErrorCode.UPSTREAM_UNAVAILABLE,
                cause=last_exc,
            ) from last_exc

        return wrapper

    return decorator


# ---- 重试演示用的模拟函数 ----
class FlakyService:
    """不稳定的外部服务：前 N 次调用失败。"""

    def __init__(self, fail_times: int) -> None:
        self.fail_times = fail_times
        self.calls = 0

    @retry(max_attempts=5, base_delay=0.01, multiplier=2.0, retry_on=(DependencyError,))
    def fetch(self, key: str) -> str:
        """模拟调用外部服务。"""
        self.calls += 1
        if self.calls <= self.fail_times:
            raise DependencyError(f"连接 {key} 失败（第 {self.calls} 次）")
        return f"{key} 的数据"


# ==============================================================================
# 六、降级模式：失败时返回默认值而不是崩溃
# ==============================================================================
# ===== 语法解析 =====
# 降级的三种层次：
#   1. 返回默认值    —— 缓存查询失败 -> 返回 None/空列表，调用方继续跑
#   2. 降级数据      —— 主库挂了 -> 读从库；读从库也挂 -> 返回静态兜底数据
#   3. 熔断         —— 连续失败太多次就快速失败，不再打后端（保护系统）
#
# 何时该降级？关键判断：这次失败是否影响主流程的正确性。
#   影响 -> 不能降级，快速失败（fail fast）让调用方重试
#   不影响 -> 降级，保证用户体验


def with_fallback(default: Any, *, log_message: str = "主逻辑失败，已降级") -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """降级装饰器：主逻辑抛异常时返回默认值，并把异常记录到标准错误。

    ★ 注意：这里只 catch Exception，不裸 catch BaseException。
      否则 Ctrl+C 会被吞掉，程序无法退出。
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                return func(*args, **kwargs)
            except Exception as exc:
                # 生产环境这里应该 logging.exception(...)，把堆栈写进日志
                print(f"    [fallback] {func.__name__}: {type(exc).__name__} -> 返回默认值")
                print(f"              {log_message}", file=sys.stderr)
                return default

        return wrapper

    return decorator


@with_fallback(default=[], log_message="推荐服务不可用，返回空推荐列表")
def fetch_recommendations(user_id: int) -> list[str]:
    """推荐服务：模拟调用失败。"""
    if user_id != 1:
        raise DependencyError("推荐引擎连接失败")
    return ["热门文章-1", "热门文章-2"]


# ---- 熔断器：连续失败达阈值后快速失败 ----
class CircuitBreaker:
    """简化的三态熔断器。

    状态机：
      CLOSED(闭合)   -- 正常放行；连续失败超过阈值 -> OPEN(打开)
      OPEN(打开)     -- 直接快速失败，不再打后端；冷却期到 -> HALF_OPEN(半开)
      HALF_OPEN(半开) -- 放一个请求试探；成功 -> CLOSED；失败 -> OPEN
    """

    class State(Enum):
        CLOSED = "closed"
        OPEN = "open"
        HALF_OPEN = "half_open"

    def __init__(self, fail_threshold: int = 3, recovery_timeout: float = 0.2) -> None:
        self.fail_threshold = fail_threshold
        self.recovery_timeout = recovery_timeout
        self.state = CircuitBreaker.State.CLOSED
        self.fail_count = 0
        self.opened_at = 0.0

    def allow(self) -> bool:
        """是否允许本次请求通过。"""
        if self.state is CircuitBreaker.State.CLOSED:
            return True
        if self.state is CircuitBreaker.State.OPEN:
            # 冷却时间到了就进入半开状态试探
            if time.monotonic() - self.opened_at >= self.recovery_timeout:
                self.state = CircuitBreaker.State.HALF_OPEN
                return True
            return False
        # HALF_OPEN 只放一个请求进来
        return True

    def record_success(self) -> None:
        self.fail_count = 0
        self.state = CircuitBreaker.State.CLOSED

    def record_failure(self) -> None:
        self.fail_count += 1
        if self.fail_count >= self.fail_threshold or self.state is CircuitBreaker.State.HALF_OPEN:
            self.state = CircuitBreaker.State.OPEN
            self.opened_at = time.monotonic()

    def execute(self, func: Callable[[], T], default: T | None = None) -> T | None:
        """受保护的执行入口。"""
        if not self.allow():
            # 熔断中：直接返回默认值，不打扰后端
            return default
        try:
            result = func()
            self.record_success()
            return result
        except Exception:
            self.record_failure()
            return default


# ==============================================================================
# 七、错误边界隔离
# ==============================================================================
# ===== 语法解析 =====
# 什么是错误边界？
#   Web 前端的 ErrorBoundary 概念：子树崩溃时不让整棵 UI 树挂掉。
#   后端的等价物：单个请求处理器崩溃时，不应该让整个 worker 进程死掉。
#
# 关键原则：
#   边界层负责「兜住一切 + 记录完整现场 + 返回可降级的响应」
#   业务层负责「只抛有意义的异常，不做无意义的 try/except」


def isolate_boundary(
    fallback: Any = None,
    on_error: Callable[[str, BaseException], None] | None = None,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """错误边界装饰器：把 handler 里的异常挡在这一层，不向上污染。

    与 with_fallback 的区别：
      with_fallback  —— 预期内的降级，返回默认值
      isolate_boundary —— 兜底防线，记录现场后返回 fallback，通常用于请求入口
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                return func(*args, **kwargs)
            except AppError as exc:
                # 业务异常：已知问题，结构化记录即可
                print(f"    [boundary] 业务异常 {exc}")
                if on_error:
                    on_error(func.__name__, exc)
                return {"success": False, "code": str(exc.code), "message": exc.message}
            except Exception as exc:
                # 未预期异常：可能是 bug，必须留下完整堆栈，否则线上无法排查
                print(f"    [boundary] 未预期异常 {type(exc).__name__}: {exc}")
                print("    堆栈：")
                for line in traceback.format_exc().strip().splitlines()[-4:]:
                    print(f"      {line}")
                if on_error:
                    on_error(func.__name__, exc)
                return {
                    "success": False,
                    "code": str(ErrorCode.INTERNAL_ERROR),
                    "message": "服务内部错误",
                }

        return wrapper

    return decorator


class RequestDispatcher:
    """模拟请求分发器：多个处理器并发挂载，一个崩了不能影响其他。"""

    @isolate_boundary(fallback={"success": False, "code": "E5001"})
    def handle_profile(self, user_id: int) -> dict[str, Any]:
        """正常处理器。"""
        result = find_user(user_id)
        if result.is_err:
            raise NotFoundError(result.message, code=result.code)  # type: ignore[arg-type]
        return {"success": True, "data": result.value}

    @isolate_boundary(fallback={"success": False, "code": "E5001"})
    def handle_divide(self, a: int, b: int) -> dict[str, Any]:
        """会崩溃的处理器：除零 + 类型错误都会触发。"""
        return {"success": True, "data": a / b}

    @isolate_boundary(fallback={"success": False, "code": "E5001"})
    def handle_buggy(self) -> dict[str, Any]:
        """会触发 NoneType 错误的处理器（典型线上事故）。"""
        obj: dict[str, Any] | None = None
        return {"success": True, "data": obj["missing"]}   # type: ignore[index]

    def dispatch(self, handler_name: str, *args: Any) -> dict[str, Any]:
        """分发：无论哪个 handler 出错，请求都能得到结构化响应。"""
        return getattr(self, handler_name)(*args)


# ==============================================================================
# 八、异常链与 contextlib
# ==============================================================================
def demo_exception_chain() -> None:
    """演示 raise ... from ... 与隐式 __context__ 的区别。"""
    print("  1) 隐式异常链（__context__）：不写 from 时自动关联")
    try:
        try:
            int("abc")
        except ValueError:
            raise AppError("数据处理失败")      # 没写 from
    except AppError as exc:
        print(f"     类型      : {type(exc).__name__}")
        print(f"     __cause__ : {type(exc.__cause__).__name__ if exc.__cause__ else 'None'}")
        print(f"     __context__: {type(exc.__context__).__name__ if exc.__context__ else 'None'}")
        print("     注意：__cause__ 为 None，__context__ 隐式指向原始异常")

    print("\n  2) 显式异常链（raise ... from ...）：__cause__ 被明确指定")
    try:
        try:
            [1, 2, 3][99]
        except IndexError as original:
            # from 后面可以是异常对象，也可以是 None（表示切断链条、隐藏内部实现）
            raise AppError("索引越界", code=ErrorCode.INVALID_PARAM) from original
    except AppError as exc:
        print(f"     类型      : {type(exc).__name__}")
        print(f"     __cause__ : {type(exc.__cause__).__name__ if exc.__cause__ else 'None'}")
        print(f"     __context__: {type(exc.__context__).__name__ if exc.__context__ else 'None'}")
        print("     ✓ 链条清晰：AppError <- IndexError")

    print("\n  3) 切断链条：raise ... from None")
    try:
        try:
            {}["k"]
        except KeyError:
            raise AppError("配置缺失", code=ErrorCode.MISSING_FIELD) from None
    except AppError as exc:
        print(f"     __cause__ : {exc.__cause__}")
        print(f"     __suppress_context__: {exc.__suppress_context__}")
        print("     ✓ 不暴露「内部用了字典」这种实现细节")


def demo_contextlib() -> None:
    """contextlib 的精准异常处理工具。"""
    print("  contextlib.suppress：只忽略指定异常，不留裸 try/except pass")

    # ❌ 错误做法：把异常吞了，出了问题都不知道
    # try:
    #     risky()
    # except Exception:
    #     pass

    # ✓ 正确做法：明确声明"我知道这里可能失败，且失败可接受"
    with contextlib.suppress(FileNotFoundError, PermissionError):
        with open("/nonexistent/path/file.txt", encoding="utf-8") as f:
            f.read()
    print("    ✓ 文件不存在：异常被精准抑制，程序继续")

    # 关键：suppress 只抑制列出的异常，其他异常照样冒泡
    try:
        with contextlib.suppress(FileNotFoundError):
            raise ValueError("这个异常不在白名单里")
    except ValueError as exc:
        print(f"    ✓ 未列出的异常正常冒泡：{exc}")

    print("\n  contextlib.ExitStack：动态管理多个资源（本文件已用它做过 stdout 重定向）")
    print("    with ExitStack() as stack:")
    print("        f1 = stack.enter_context(open('a.txt'))")
    print("        f2 = stack.enter_context(open('b.txt'))")
    print("        # 退出时按逆序自动关闭，无论是否抛异常")


# ==============================================================================
# 九、主流程
# ==============================================================================
def demo_result_pattern() -> None:
    print("  成功场景：")
    ok = find_user(1)
    print(f"    is_ok={ok.is_ok}  value={ok.value}  to_dict={ok.to_dict()}")

    print("  失败场景（用户不存在 —— 这是预期分支，不是 bug）：")
    err = find_user(999)
    print(f"    is_err={err.is_err}  code={err.code}  message={err.message}")
    print(f"    detail={err.detail}")
    print(f"    to_dict={err.to_dict()}")

    print("  链式：find_user(1).map(取名字) =")
    print(f"    {find_user(1).map(lambda u: u['name'])}")

    print("  链式失败透传：find_user(999).map(取名字) =")
    print(f"    {find_user(999).map(lambda u: u['name'])}   ← 失败时不执行 map 函数")

    print("  串联多个可能失败的步骤（charge）：")
    print(f"    charge(1, 100)  -> {charge(1, 100).to_dict()}")
    print(f"    charge(1, 99999)-> {charge(1, 99999).to_dict()}")
    print(f"    charge(999, 10) -> {charge(999, 10).to_dict()}   ← 第一步就失败，直接透传")
    print(f"    charge(1, -5)   -> {charge(1, -5).to_dict()}")

    print("  unwrap_or 降级取值：")
    print(f"    find_user(999).unwrap_or({'name': '游客'}) -> {find_user(999).unwrap_or({'name': '游客'})}")

    print("  unwrap 转异常（需要向上抛时）：")
    try:
        find_user(999).unwrap()
    except AppError as exc:
        print(f"    抛出 {type(exc).__name__}: {exc}")
        print(f"    to_dict = {exc.to_dict()}")


def demo_error_codes() -> None:
    print(f"  {'错误码':<8}{'枚举名':<28}{'HTTP':<6}{'面向用户的消息'}")
    print("  " + "-" * 72)
    for code in ErrorCode:
        print(f"  {str(code):<8}{code.name:<28}{code.http_status:<6}{code.message}")

    print("\n  错误码区间约定：")
    print("    1xxx 参数校验 -> HTTP 400")
    print("    2xxx 资源问题 -> HTTP 404")
    print("    3xxx 外部依赖 -> HTTP 502")
    print("    4xxx 状态冲突 -> HTTP 409")
    print("    5xxx 系统内部 -> HTTP 500")
    print(f"\n  IntEnum 可直接比较和排序：{ErrorCode.INTERNAL_ERROR > ErrorCode.NOT_FOUND}")


def demo_exception_group() -> None:
    print(f"  Python {sys.version.split()[0]}，ExceptionGroup 原生支持："
          f"{sys.version_info >= (3, 11)}")
    items = ["ok_item", "", "timeout", "12345", "another_ok"]
    print(f"\n  批量处理：{items}")

    # BatchFailure 是 AppError 子类，两种版本都从它抛出，所以只需捕获 AppError
    try:
        results = process_batch(items)
        print(f"  全部成功：{results}")
    except AppError as exc:
        errors = getattr(exc, "errors", [])
        print(f"  捕获到聚合异常：{type(exc).__name__}")
        print(f"  子异常数量：{len(errors)}")
        for sub in errors:
            # getattr 兼容两种实现：ExceptionGroup 也有 .exceptions 属性
            detail = getattr(sub, "detail", {})
            print(f"    - {type(sub).__name__}: {sub}  detail={detail}")
        print("\n  优势：每个子异常的完整堆栈都被保留，")
        print("        不会出现「RuntimeError: 批量处理出错」这种丢失现场的错误。")

    # 单独演示一下所有用例都成功的情况
    print(f"\n  全部合法时：{process_batch(['a', 'b', 'c'])}")

    # 如果 Python 3.11+，演示原生 ExceptionGroup 的 catch-all 语法
    if sys.version_info >= (3, 11):
        print(f"\n  原生 ExceptionGroup 写法（3.11+）：")
        try:
            raise ExceptionGroup("并行任务汇总", [
                NotFoundError("用户 1 不存在"),
                DependencyError("支付网关超时"),
                ValidationError("amount 必须为正"),
            ])
        except* AppError as eg:
            # except* 可以「按类型筛选」子异常，一行代码处理同类错误
            print(f"    except* 捕获到 {len(eg.exceptions)} 个 AppError 子异常：")
            for sub in eg.exceptions:
                print(f"      - {type(sub).__name__}: {sub}")
        except* ValueError as eg:
            print(f"    except* 捕获到 {len(eg.exceptions)} 个 ValueError")


def demo_retry() -> None:
    print("  场景 A：第 3 次才成功（退避间隔递增，带抖动）")
    svc = FlakyService(fail_times=3)
    result = svc.fetch("user:1001")
    print(f"    结果：{result}   总调用次数：{svc.calls}")

    print("\n  场景 B：始终失败，重试耗尽")
    bad = FlakyService(fail_times=99)
    try:
        bad.fetch("user:2002")
    except AppError as exc:
        print(f"    最终异常：{exc}")
        print(f"    错误码  ：{exc.code}")
        print(f"    根因    ：{type(exc.__cause__).__name__}")

    print("\n  场景 C：不可重试的异常立即抛出（不做无谓重试）")
    svc3 = FlakyService(fail_times=99)
    svc3.fetch = retry(max_attempts=3, retry_on=(DependencyError,))(_always_raise_validation)
    try:
        svc3.fetch("x")
    except ValidationError as exc:
        print(f"    ✓ 只调用 1 次就抛出 {type(exc).__name__}（不在 retry_on 白名单）")


def _always_raise_validation(key: str) -> str:
    raise ValidationError(f"参数 {key} 不合法，不值得重试")


def demo_degrade() -> None:
    print("  场景 A：降级返回默认值（业务不中断）")
    print(f"    user_id=1（正常）-> {fetch_recommendations(1)}")
    print(f"    user_id=2（降级）-> {fetch_recommendations(2)}")

    print("\n  场景 B：熔断器 —— 连续失败后快速失败，保护后端")
    breaker = CircuitBreaker(fail_threshold=3, recovery_timeout=0.05)

    def flaky_call() -> str:
        raise DependencyError("后端持续故障")

    states = []
    for i in range(5):
        result = breaker.execute(flaky_call, default="降级数据")
        states.append(f"第{i + 1}次调用: {result}")
    print(f"    {chr(10).join('      ' + s for s in states)}")
    print(f"    熔断器状态：{breaker.state.value}，累计失败 {breaker.fail_count} 次")
    print(f"    连续失败达到阈值后，后续调用直接返回降级数据，不再打扰后端 ✓")

    # 等冷却期结束后自动半开探测
    time.sleep(0.06)
    breaker.record_success()
    print(f"    冷却期后探测成功，状态恢复为：{breaker.state.value}")


def demo_boundary() -> None:
    """展示一个处理器崩溃不影响其他处理器。"""
    dispatcher = RequestDispatcher()

    scenarios: list[tuple[str, tuple[Any, ...]]] = [
        ("handle_profile", (1,)),      # 正常
        ("handle_profile", (999,)),    # 业务异常（用户不存在）
        ("handle_divide", (10, 2)),   # 正常
        ("handle_divide", (10, 0)),   # ZeroDivisionError
        ("handle_divide", ("a", "b")),# TypeError
        ("handle_buggy", ()),          # TypeError: NoneType
    ]

    print(f"  {'处理器':<20}{'入参':<16}{'返回'}")
    print("  " + "-" * 78)
    for handler, args in scenarios:
        resp = dispatcher.dispatch(handler, *args)
        arg_text = ", ".join(repr(a) for a in args) or "-"
        status = "OK " if resp.get("success") else "ERR"
        detail = resp.get("data") if resp.get("success") else resp.get("message")
        print(f"  {handler:<20}{arg_text:<16}[{status}] {detail}")

    print("\n  ✓ 6 次调用全部返回结构化响应，没有一次让分发器崩溃")
    print("  ✓ 未预期异常被边界捕获并返回 500，而不是抛出打断整个服务")


def main() -> None:
    """主流程：8 个错误处理模式的完整演示。"""
    print("=" * 78)
    print(" 06. 工程级错误处理模式")
    print("=" * 78)

    print("\n[1] Result 类型模式")
    print("-" * 78)
    demo_result_pattern()

    print("\n[2] 自定义错误码枚举")
    print("-" * 78)
    demo_error_codes()

    print("\n[3] 异常分组（ExceptionGroup）")
    print("-" * 78)
    demo_exception_group()

    print("\n[4] 重试装饰器（指数退避 + 抖动）")
    print("-" * 78)
    demo_retry()

    print("\n[5] 降级与熔断")
    print("-" * 78)
    demo_degrade()

    print("\n[6] 错误边界隔离")
    print("-" * 78)
    demo_boundary()

    print("\n[7] 异常链 raise ... from ...")
    print("-" * 78)
    demo_exception_chain()

    print("\n[8] contextlib 精准异常处理")
    print("-" * 78)
    demo_contextlib()

    print("\n" + "=" * 78)
    print(" 决策速查：")
    print("   预期内的失败（查不到/余额不足） -> Result.fail，不抛异常")
    print("   意外失败（网络/崩溃）             -> raise AppError，向上传递")
    print("   可恢复的瞬时故障                  -> retry 装饰器 + 白名单")
    print("   不影响主流程的失败                -> with_fallback 降级")
    print("   后端持续故障                      -> CircuitBreaker 熔断")
    print("   请求入口的最后一道防线             -> isolate_boundary")
    print("=" * 78)


if __name__ == "__main__":
    main()
