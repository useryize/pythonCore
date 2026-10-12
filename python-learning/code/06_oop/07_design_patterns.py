"""
================================================================================
  07_design_patterns.py  ——  Python 设计模式实现
================================================================================

【演示的语法点】
 1. ★ 单例模式（Singleton）的 4 种实现对比：
       ① __new__ 方法   ② 模块级（Python 推荐）  ③ 装饰器  ④ 元类（metaclass）
 2. ★ 工厂模式（Factory）：简单工厂 / 工厂方法 / 抽象工厂
 3. ★ 策略模式（Strategy）：把可变算法封装成可互换对象
 4. ★ 观察者模式（Observer）：发布订阅、解耦回调
 5. ★ 装饰器模式（Decorator）：函数装饰器 / 类装饰器 / 带参数装饰器
 6. 建造者模式（Builder）：分步构造复杂对象
 7. 各模式的 Python 惯用写法与标准库对应（functools.singledispatch / lru_cache 等）
 8. 模式选型决策表与反模式提醒

【预期输出摘要】
 - "单例" 小节打印 4 种实现各自的结果与优缺点对比表
 - "工厂" 小节打印按参数创建不同产品的输出
 - "策略" 小节打印同一算法切换不同收费方式的计价对比
 - "观察者" 小节打印发布消息后多个监听者按注册顺序响应的日志
 - "装饰器" 小节打印带参数的装饰器与 functools.wraps 的效果
================================================================================

"""

from __future__ import annotations

import functools
import threading
import timeit
import weakref
from typing import Any, Callable, Dict, List, Optional, Type


# ==============================================================================
# 【第一部分】单例模式 Singleton —— 4 种实现
# ==============================================================================
# 单例：保证一个类在整个进程中只有一个实例。
# 用途：配置管理器、连接池、日志器、硬件句柄（打印机/显卡）等"唯一资源"。

# ===== 实现① __new__ 方法 =====
class SingletonNew:
    """通过重写 __new__ 实现单例。

    语法机制：
      - __new__ 是【创建实例的底层方法】，先于 __init__ 执行
      - 若返回已存在实例，Python 会【跳过 __init__】（避免重复初始化）
    ★ 优点：实现直观、保留类的正常写法。
    ★ 缺点：不线程安全（并发下可能创建多个）；子类继承时会意外共享实例。
    """
    _instance: Optional["SingletonNew"] = None

    def __new__(cls, *args: Any, **kwargs: Any) -> "SingletonNew":
        # 双重检查加锁：线程安全（但有性能开销）
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, name: str = "默认") -> None:
        # 用标记防止 __init__ 被重复执行
        if not hasattr(self, "_initialized"):
            self.name = name
            self.created_at = timeit.default_timer()
            self._initialized = True

    def show(self) -> str:
        return f"{self.__class__.__name__}(name={self.name}, id={id(self)})"


# ===== 实现② 模块级（Python 官方推荐）=====
# 在模块顶层直接创建实例，导入该实例即可实现单例。
# ★ 这是 Pythonic 的做法：利用【模块只会被导入一次】的天然特性。
# ★ 优点：最简单、线程安全（导入机制保证）、无需特殊语法。
# ★ 缺点：不能用于"参数在实例化时才能确定"的场景；略依赖模块全局状态。
class ConfigManager:
    """模块级单例：模块首次导入时创建实例，之后所有导入共享同一对象。"""
    def __init__(self) -> None:
        self.settings: Dict[str, Any] = {"env": "dev", "debug": True}

    def get(self, key: str) -> Any:
        return self.settings.get(key)


# 模块级实例（这就是"单例"的本体）
config_singleton = ConfigManager()
# 其它模块只要 from module import config_singleton 拿到的就是同一个对象


# ===== 实现③ 装饰器 =====
def singleton(cls: Type[Any]) -> Callable[..., Any]:
    """装饰器实现单例：把类包成一个"总是返回同一实例"的函数。

    语法机制：
      - 装饰器接收类，返回一个替代的【函数/工厂】
      - 内部用闭包保存唯一实例
    ★ 优点：可复用（可作用于任意多个类）、显式表达意图。
    ★ 缺点：返回的是函数而非类，会破坏 isinstance 和类方法；不适合继承。
    """
    instances: Dict[type, Any] = {}

    @functools.wraps(cls, updated=())
    def get_instance(*args: Any, **kwargs: Any) -> Any:
        if cls not in instances:
            instances[cls] = cls(*args, **kwargs)
        return instances[cls]

    # 附加类引用，方便 isinstance 判断
    get_instance._cls = cls  # type: ignore[attr-defined]
    return get_instance


@singleton
class Logger:
    """被装饰为单例的日志器。"""
    def __init__(self, name: str = "app") -> None:
        self.name = name
        self.logs: List[str] = []

    def log(self, msg: str) -> str:
        self.logs.append(msg)
        return f"[{self.name}] {msg}"


# ===== 实现④ 元类 metaclass =====
class SingletonMeta(type):
    """元类实现单例：控制"类实例化"这一动作本身。

    语法机制：
      - 元类（metaclass）是"类的类"，其 __call__ 在【实例化时】被调用
      - 在元类的 __call__ 里缓存实例，就实现了全局唯一
    ★ 优点：可继承（子类各自单例）；保留类的全部能力（isinstance/类方法）；
      与其它元类（如 EnumMeta）可组合。
    ★ 缺点：概念最复杂，对初学者不友好；同样需要自己处理线程安全。
    """
    _instances: Dict[type, Any] = {}

    def __call__(cls, *args: Any, **kwargs: Any) -> Any:
        # 双检锁：线程安全
        if cls not in cls._instances:
            cls._instances[cls] = super().__call__(*args, **kwargs)
        return cls._instances[cls]


class DatabasePool(metaclass=SingletonMeta):
    """用元类实现单例的数据库连接池。"""
    def __init__(self, url: str = "sqlite://") -> None:
        self.url = url
        self.connections: List[str] = []

    def connect(self) -> str:
        conn = f"conn#{len(self.connections) + 1}"
        self.connections.append(conn)
        return conn


def demo_singleton() -> None:
    print("=" * 60)
    print("【1】★ 单例模式：4 种实现对比")
    print("=" * 60)

    print()
    print("  ── 实现① __new__ ──")
    s1 = SingletonNew("配置A")
    s2 = SingletonNew("配置B")               # 参数被忽略：__init__ 不会再执行
    print(f"    s1 = {s1.show()}")
    print(f"    s2 = {s2.show()}")
    print(f"    s1 is s2 = {s1 is s2}   ← 同一个实例！")
    print(f"    s2.name = {s2.name}   ← 仍是 s1 的值（__init__ 没重跑）")

    print()
    print("  ── 实现② 模块级（Python 推荐） ──")
    print(f"    config_singleton.settings = {config_singleton.settings}")
    from importlib import reload                          # 演示模块只导入一次的特性
    print(f"    从模块取到的永远是同一个对象（模块缓存机制）")
    print(f"    config_singleton.get('env') = {config_singleton.get('env')}")
    print("    ★ 这是【最 Pythonic】的单例：利用模块只被导入一次。")

    print()
    print("  ── 实现③ 装饰器 ──")
    log1 = Logger("服务A")
    log2 = Logger("服务B")
    log1.log("第一条")
    log2.log("第二条")
    print(f"    log1 = {log1}")
    print(f"    log2 = {log2}")
    print(f"    log1 is log2 = {log1 is log2}   ← 装饰器保证唯一")
    print(f"    共享的日志：{log1.logs}   ← log2 写进了同一个实例的列表")

    print()
    print("  ── 实现④ 元类 ──")
    db1 = DatabasePool("postgresql://a")
    db2 = DatabasePool("postgresql://b")
    print(f"    db1 is db2 = {db1 is db2}   ← 元类保证唯一")
    print(f"    db1.url    = {db1.url}   （db2 的参数被忽略）")
    print(f"    db1.connect() = {db1.connect()}，连接池共用：{db1.connections}")

    print()
    print("  ── ★ 4 种实现对比表 ──")
    print("  | 实现      | 线程安全 | 支持继承 | isinstance | 复杂度 | 推荐度 |")
    print("  |-----------|----------|----------|-----------|--------|--------|")
    print("  | __new__   | 需自己加锁 | ✗ 会共享 | ✓          | 中     | ★★★☆  |")
    print("  | 模块级    | ✓         | 不适用   | ✓          | 极低   | ★★★★★|")
    print("  | 装饰器    | 需自己加锁 | ✗        | ✗(返回函数)| 中     | ★★★☆  |")
    print("  | 元类      | 需自己加锁 | ✓        | ✓          | 高     | ★★★★  |")
    print()
    print("  ★ 结论：默认用【模块级】；需要继承体系或与其它元类组合时才用元类；")
    print("    __new__/装饰器 适合教学与特定场景，注意线程安全与 isinstance 限制。")
    print()
    print("  ★ 重要提醒：单例是【反模式】，滥用会带来：")
    print("    - 全局状态导致测试困难、隐式依赖")
    print("    - 多线程/多进程下需额外同步")
    print("    - 难以替换（mock）测试")
    print("    Python 中更推荐【模块级变量】或【依赖注入】替代单例。")


# ==============================================================================
# 【第二部分】工厂模式 Factory
# ==============================================================================
# ===== 语法解析 =====
# 工厂：把"创建哪个对象"的逻辑集中到一处，调用方只说"要什么"不说"怎么做"。
# 三种形态：
#   简单工厂  —— 一个函数/方法，根据参数返回不同子类实例
#   工厂方法  —— 子类各自重写创建方法（依赖"子类决定"）
#   抽象工厂  —— 一个工厂生产一族相关对象（换工厂换整族）
def demo_factory() -> None:
    print()
    print("=" * 60)
    print("【2】工厂模式")
    print("=" * 60)

    # --- 产品类 ---
    class Notification:
        """产品抽象基类。"""
        def send(self, msg: str) -> str:
            raise NotImplementedError

    class EmailNotification(Notification):
        def send(self, msg: str) -> str:
            return f"📧 邮件发送: {msg}"

    class SMSNotification(Notification):
        def send(self, msg: str) -> str:
            return f"📱 短信发送: {msg}"

    class PushNotification(Notification):
        def send(self, msg: str) -> str:
            return f"🔔 推送通知: {msg}"

    # --- 简单工厂：一个方法根据类型字符串创建 ---
    class NotificationFactory:
        """简单工厂：集中管理"类型 → 类"的映射。"""
        _registry: Dict[str, Type[Notification]] = {
            "email": EmailNotification,
            "sms": SMSNotification,
            "push": PushNotification,
        }

        @classmethod
        def create(cls, channel: str) -> Notification:
            """根据渠道名创建对应通知对象。"""
            if channel not in cls._registry:
                raise ValueError(f"不支持的通知渠道: {channel}")
            return cls._registry[channel]()          # 返回实例

    print()
    print("  ── 简单工厂 ──")
    for channel in ("email", "sms", "push"):
        notifier = NotificationFactory.create(channel)
        print(f"    create({channel:6}) → {type(notifier).__name__:22} {notifier.send('订单已支付')}")

    print("    ", end="")
    try:
        NotificationFactory.create("fax")
    except ValueError as exc:
        print(f"    create('fax') → ValueError: {exc}   ← 工厂集中做参数校验")

    print()
    print("  ★ 简单工厂的优点：调用方不接触具体类，加新类型只改工厂一处")
    print("    缺点：工厂与产品耦合（新增产品要改工厂），且条件分支会变多")

    # --- 工厂方法：子类各自决定创建什么 ---
    print()
    print("  ── 工厂方法（子类决定） ──")

    class Logistics:
        """物流基类：定义 create 工厂方法。"""
        def create_transport(self) -> "Transport":
            raise NotImplementedError

        def deliver(self) -> str:
            t = self.create_transport()             # 业务逻辑固定，工厂方法可变
            return f"陆运: {t.transport()}"

    class SeaLogistics(Logistics):
        """海运：工厂方法返回海运工具。"""
        def create_transport(self) -> "Transport":
            return ShipTransport()

    class AirLogistics(Logistics):
        """空运：工厂方法返回空运工具。"""
        def create_transport(self) -> "Transport":
            return AirTransport()

    class Transport:
        def transport(self) -> str:
            raise NotImplementedError

    class ShipTransport(Transport):
        def transport(self) -> str:
            return "货轮运输"

    class AirTransport(Transport):
        def transport(self) -> str:
            return "飞机运输"

    for logistics in (SeaLogistics(), AirLogistics()):
        print(f"    {type(logistics).__name__:15} → {logistics.deliver()}")
    print("    ★ 工厂方法：deliver() 逻辑不变，create_transport() 由子类实现（开闭原则）")

    # --- 抽象工厂：生产一族相关对象 ---
    print()
    print("  ── 抽象工厂（生产一族对象） ──")

    class UIFactory:
        """UI 抽象工厂：生产一整套同风格的 UI 组件。"""
        def create_button(self) -> "Button":
            raise NotImplementedError

        def create_input(self) -> "Input":
            raise NotImplementedError

    class DarkFactory(UIFactory):
        """暗色工厂：生产暗色系组件。"""
        def create_button(self) -> "Button":
            return DarkButton()

        def create_input(self) -> "Input":
            return DarkInput()

    class LightFactory(UIFactory):
        """亮色工厂：生产亮色系组件。"""
        def create_button(self) -> "Button":
            return LightButton()

        def create_input(self) -> "Input":
            return LightInput()

    class Button:
        def render(self) -> str:
            raise NotImplementedError

    class Input:
        def render(self) -> str:
            raise NotImplementedError

    class DarkButton(Button):
        def render(self) -> str:
            return "⬛ 暗色按钮"

    class LightButton(Button):
        def render(self) -> str:
            return "⬜ 亮色按钮"

    class DarkInput(Input):
        def render(self) -> str:
            return "⬛ 暗色输入框"

    class LightInput(Input):
        def render(self) -> str:
            return "⬜ 亮色输入框"

    def build_ui(factory: UIFactory) -> str:
        """客户端代码：只依赖抽象工厂，不知道具体是暗色还是亮色。"""
        button = factory.create_button()
        input_box = factory.create_input()
        return f"{button.render()} + {input_box.render()}"

    print(f"    DarkFactory  → {build_ui(DarkFactory())}")
    print(f"    LightFactory → {build_ui(LightFactory())}")
    print("    ★ 抽象工厂：换工厂就换【整族】风格，客户端代码零改动")
    print("    实际应用：不同数据库方言、不同云厂商 SDK、不同支付渠道的整套 API")

    # --- 标准库中的工厂：singledispatch ---
    print()
    print("  ── 标准库里的工厂：functools.singledispatch ──")
    from functools import singledispatch

    @singledispatch
    def to_json(obj: Any) -> str:
        """通用兜底实现。"""
        return f'"<{type(obj).__name__}>"'

    @to_json.register
    def _(obj: int) -> str:
        return str(obj)

    @to_json.register
    def _(obj: list) -> str:
        return "[" + ", ".join(to_json(x) for x in obj) + "]"

    print(f"    to_json(42)         = {to_json(42)}")
    print(f"    to_json([1, 2, 3])  = {to_json([1, 2, 3])}   ← 递归调用")
    print(f"    to_json(3.14)       = {to_json(3.14)}   （没注册 → 兜底）")
    print("    ★ singledispatch 是标准库实现的多态工厂，按【第一个参数类型】分派。")


# ==============================================================================
# 【第三部分】策略模式 Strategy
# ==============================================================================
# ===== 语法解析 =====
# 策略：把【一组可互换的算法】封装成独立对象，让算法能动态切换。
# 结构：Context(上下文) → 持有 Strategy 引用；Strategy(策略) → 各算法实现。
# ★ Python 惯用写法：直接把函数/lambda 当策略，无需定义类（"函数式策略"）。
def demo_strategy() -> None:
    print()
    print("=" * 60)
    print("【3】★ 策略模式")
    print("=" * 60)

    # --- 类式策略 ---
    print()
    print("  ── 类式策略：电商促销计费 ──")

    class PricingStrategy:
        """策略抽象接口：所有计费方式都实现 calculate。"""
        def calculate(self, price: float) -> float:
            raise NotImplementedError

    class NormalStrategy(PricingStrategy):
        """原价。"""
        def calculate(self, price: float) -> float:
            return price

    class DiscountStrategy(PricingStrategy):
        """折扣。"""
        def __init__(self, rate: float) -> None:
            self.rate = rate

        def calculate(self, price: float) -> float:
            return price * self.rate

    class FullReductionStrategy(PricingStrategy):
        """满减：满 300 减 50。"""
        def calculate(self, price: float) -> float:
            return price - 50 if price >= 300 else price

    class OrderContext:
        """上下文：持有一个策略对象，把计算委托给它。

        ★ 关键：客户端只替换 strategy，不修改 calculate 的调用代码 → 无 if/else。
        """
        def __init__(self, price: float) -> None:
            self.price = price
            self.strategy: PricingStrategy = NormalStrategy()   # 默认策略

        def set_strategy(self, strategy: PricingStrategy) -> None:
            """运行时【动态切换】算法。"""
            self.strategy = strategy

        def checkout(self) -> float:
            return round(self.strategy.calculate(self.price), 2)

    order = OrderContext(350)
    print(f"    原价结算：{order.checkout():>7.2f} 元   （NormalStrategy）")
    order.set_strategy(DiscountStrategy(0.8))                  # 8 折
    print(f"    8 折结算：{order.checkout():>7.2f} 元   （DiscountStrategy）")
    order.set_strategy(FullReductionStrategy())               # 满减
    print(f"    满减结算：{order.checkout():>7.2f} 元   （FullReductionStrategy）")
    print("    ★ 切换策略【不改变 checkout 的调用】，这就是策略模式的价值")

    # --- 函数式策略：Python 更惯用 ---
    print()
    print("  ── ★ 函数式策略（Pythonic，无需定义类） ──")

    def price_normal(p: float) -> float:
        return p

    def price_discount(p: float) -> float:
        return p * 0.8

    def price_full_reduction(p: float) -> float:
        return p - 50 if p >= 300 else p

    def checkout2(price: float, strategy_fn: Callable[[float], float]) -> float:
        """上下文接收一个【函数】作为策略。"""
        return round(strategy_fn(price), 2)

    strategies = {
        "原价": price_normal,
        "8折": price_discount,
        "满减": price_full_reduction,
    }
    print("    同一份订单(350元)，切换不同计费函数：")
    for name, fn in strategies.items():
        print(f"      {name:4} → {checkout2(350, fn):>7.2f} 元")

    print()
    print("    ★ 函数式策略的对比：")
    print("      类式  → 类型清晰、可有状态、适合策略间差异大（要存参数）")
    print("      函数式→ 简洁、无需类、适合逻辑短的算法（Python 首选）")
    print("      ★ Python 没有函数重载，所以常把『算法』做成可调用对象或函数。")


# ==============================================================================
# 【第四部分】观察者模式 Observer
# ==============================================================================
# ===== 语法解析 =====
# 观察者：定义一对多依赖 —— 目标对象状态变化时，自动通知所有观察者。
# 结构：Subject(主题) → 维护观察者列表并广播；Observer(观察者) → 实现 update。
# ★ Python 惯用写法：观察者就是【回调函数】，主题调用 observer() 即可。
def demo_observer() -> None:
    print()
    print("=" * 60)
    print("【4】★ 观察者模式")
    print("=" * 60)

    # --- 类式观察者：事件总线 ---
    print()
    print("  ── 类式观察者：模拟事件总线 ──")

    class EventBus:
        """主题：管理观察者并广播事件。"""
        def __init__(self) -> None:
            self._observers: List["Observer"] = []

        def subscribe(self, observer: "Observer") -> None:
            """注册观察者。"""
            self._observers.append(observer)

        def unsubscribe(self, observer: "Observer") -> None:
            """取消订阅。"""
            if observer in self._observers:
                self._observers.remove(observer)

        def notify(self, event: str, data: Any = None) -> None:
            """广播事件给【所有】观察者。"""
            for obs in self._observers:              # 按注册顺序依次通知
                obs.update(event, data)

        @property
        def observer_count(self) -> int:
            return len(self._observers)

    class Observer:
        """观察者接口。"""
        def update(self, event: str, data: Any) -> None:
            raise NotImplementedError

    class LoggerObserver(Observer):
        """观察者1：记录日志。"""
        def __init__(self, name: str) -> None:
            self.name = name

        def update(self, event: str, data: Any) -> None:
            print(f"      [{self.name}] 收到事件『{event}』 数据={data}")

    class AlertObserver(Observer):
        """观察者2：触发告警。"""
        def __init__(self, threshold: int) -> None:
            self.threshold = threshold

        def update(self, event: str, data: Any) -> None:
            if event == "error" and isinstance(data, int) and data > self.threshold:
                print(f"      [告警] 错误数 {data} 超过阈值 {self.threshold}，触发告警!")

    bus = EventBus()
    logger = LoggerObserver("日志器")
    alert = AlertObserver(threshold=5)
    bus.subscribe(logger)                          # 订阅
    bus.subscribe(alert)
    print(f"    当前观察者数量：{bus.observer_count}")
    print()
    print("    广播事件 'login'：")
    bus.notify("login", "用户A")
    print()
    print("    广播事件 'error'（数据 10 > 阈值 5，日志器记录+告警器告警）：")
    bus.notify("error", 10)
    print()
    print("    广播事件 'error'（数据 3 < 阈值 5，只有日志器记录）：")
    bus.notify("error", 3)

    bus.unsubscribe(alert)                         # 退订
    print()
    print(f"    退订告警器后，观察者数量：{bus.observer_count}")
    print("    再广播 'error'（不再触发告警）：")
    bus.notify("error", 100)
    print("    ★ 观察者：主题【不知道】观察者内部细节，只依赖 update 接口 → 高度解耦")

    # --- 函数式观察者：回调式 ---
    print()
    print("  ── ★ 函数式观察者（回调式，Python 最常用） ──")

    def simple_event_bus() -> tuple:
        """返回一个 (注册函数, 广播函数)。观察者就是普通函数。"""
        callbacks: List[Callable[[str, Any], None]] = []

        def subscribe(fn: Callable[[str, Any], None]) -> Callable[[str, Any], None]:
            callbacks.append(fn)
            return fn        # 返回原函数，支持用作装饰器

        def notify(event: str, data: Any = None) -> None:
            for cb in callbacks:
                cb(event, data)

        return subscribe, notify

    subscribe, notify = simple_event_bus()

    def on_order_created(event: str, data: Any) -> None:
        print(f"      回调A(订单): {event} → {data}")

    def on_stock_changed(event: str, data: Any) -> None:
        print(f"      回调B(库存): {event} → {data}")

    subscribe(on_order_created)
    subscribe(on_stock_changed)
    print("    注册两个回调后广播 'order_created'：")
    notify("order_created", "订单123")
    print("    ★ 回调式观察者 = 发布订阅，Python 事件处理的标准范式。")
    print("      还可以把 subscribe 当【装饰器】用：@subscribe def handler(...): ...")

    # 演示观察者作为装饰器的用法
    print()
    print("  ── ★ subscribe 当装饰器用（更 Pythonic） ──")
    subscribe2, notify2 = simple_event_bus()

    @subscribe2
    def audit_log(event: str, data: Any) -> None:
        print(f"      装饰器注册的审计: {event} → {data}")

    notify2("login", "用户B")
    print("    ★ @subscribe2 直接把函数变成观察者，无需额外注册调用。")


# ==============================================================================
# 【第五部分】装饰器模式 Decorator
# ==============================================================================
# ===== 语法解析 =====
# 装饰器：接收一个"被装饰对象"（函数/类），返回一个新对象增强它。
# 语法机制：
#   @my_decorator  等价于  func = my_decorator(func)
# ★ functools.wraps：保留原函数的 __name__/__doc__，否则它们会变成包装函数的。
def demo_decorator() -> None:
    print()
    print("=" * 60)
    print("【5】★ 装饰器模式（装饰器在 Python 中是一等公民）")
    print("=" * 60)

    # --- ① 基础函数装饰器 ---
    print()
    print("  ── ① 基础函数装饰器（无参数） ──")

    def log_call(func: Callable[..., Any]) -> Callable[..., Any]:
        """装饰器：包装函数，每次调用前后打印日志。"""
        @functools.wraps(func)                     # ★ 保留原函数元信息
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            print(f"      → 调用 {func.__name__}({args}, {kwargs})")
            result = func(*args, **kwargs)          # 调用原函数
            print(f"      ← 返回 {result}")
            return result
        return wrapper

    @log_call                                     # 等价于 greet = log_call(greet)
    def greet(name: str) -> str:
        """打招呼函数。"""
        return f"你好, {name}"

    print("    调用被装饰的 greet('世界')：")
    result = greet("世界")
    print()
    print(f"    返回值 = {result}")
    print(f"    ★ @wraps 生效：greet.__name__ = '{greet.__name__}'（不是 wrapper）")
    print(f"      greet.__doc__ = '{greet.__doc__}'（原文档保留）")

    # --- ② 带参数的装饰器（最常用） ---
    print()
    print("  ── ② ★ 带参数的装饰器（三层函数） ──")

    def retry(max_attempts: int = 3, delay: float = 0.1) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        """装饰器工厂：接收参数，返回真正的装饰器。

        ★ 三层结构的原因：@retry(3) 会先调用 retry(max_attempts=3) 得到装饰器，
          再用该装饰器包装目标函数。所以参数多了一层函数。
        """
        def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            @functools.wraps(func)
            def wrapper(*args: Any, **kwargs: Any) -> Any:
                last_exc: Optional[Exception] = None
                for attempt in range(1, max_attempts + 1):
                    try:
                        return func(*args, **kwargs)       # 成功就返回
                    except Exception as exc:               # 失败就重试
                        last_exc = exc
                        print(f"      第 {attempt}/{max_attempts} 次失败: {exc}")
                raise last_exc                             # 全部失败则抛出最后一次异常
            return wrapper
        return decorator

    attempt_counter = {"n": 0}

    @retry(max_attempts=3)
    def unstable_service() -> str:
        """一个不稳定的服务：前两次失败，第三次成功。"""
        attempt_counter["n"] += 1
        if attempt_counter["n"] < 3:
            raise ConnectionError("服务暂时不可用")
        return "终于成功了"

    print("    @retry(3) 装饰不稳定服务（模拟前2次失败）：")
    print(f"    结果 = {unstable_service()}   ← 重试机制生效")

    # --- ③ 用装饰器实现类 ---
    print()
    print("  ── ③ 类装饰器：给类加方法/属性 ──")

    def add_repr(cls: Type[Any]) -> Type[Any]:
        """类装饰器：接收类，返回增强后的类。"""
        cls.auto_repr = lambda self: f"<{cls.__name__} 自动表示>"  # 动态加方法
        return cls

    @add_repr
    class Plain:
        def __init__(self, v: int) -> None:
            self.v = v

    p = Plain(5)
    print(f"    Plain(5).auto_repr() = {p.auto_repr()}   ← 类装饰器动态添加了方法")

    # --- ④ 缓存装饰器（标准库 functools.cache/lru_cache） ---
    print()
    print("  ── ④ 缓存装饰器（标准库 functools） ──")
    calls = {"count": 0}

    @functools.lru_cache(maxsize=None)            # 无上限缓存
    def expensive_query(user_id: int) -> str:
        """模拟耗时查询：每次真实调用计数+1。"""
        calls["count"] += 1
        return f"用户{user_id}的数据"

    r1 = expensive_query(1001)
    r2 = expensive_query(1001)                     # 相同参数 → 命中缓存
    print(f"    expensive_query(1001) 调用两次 → {r1} / {r2}（结果相同）")
    print(f"    ★ 实际执行次数 = {calls['count']}   ← 第二次走缓存，未真正执行")
    print(f"    lru_cache 就是最常用的【装饰器】：自动缓存、线程安全。")

    # --- ⑤ 装饰器的执行时机：定义时 vs 调用时 ---
    print()
    print("  ── ★ 装饰器执行时机 ──")
    print("    @log_call 这一行在【函数定义时】就执行了一次（打印发生在定义时）。")
    print("    之后每次【调用 greet】时才执行 wrapper 的 before/after 部分。")
    print("    这是装饰器常被误解的点：装饰器本身只在定义时跑一次。")

    # --- ⑥ 装饰器栈（多层装饰，从下往上应用） ---
    print()
    print("  ── ⑥ 多层装饰器（自下而上依次包装） ──")

    def tag_a(func: Callable[..., Any]) -> Callable[..., Any]:
        @functools.wraps(func)
        def wrapper(*a: Any, **k: Any) -> Any:
            print("      [A前]")
            r = func(*a, **k)
            print("      [A后]")
            return r
        return wrapper

    def tag_b(func: Callable[..., Any]) -> Callable[..., Any]:
        @functools.wraps(func)
        def wrapper(*a: Any, **k: Any) -> Any:
            print("      [B前]")
            r = func(*a, **k)
            print("      [B后]")
            return r
        return wrapper

    @tag_a                                       # 外层
    @tag_b                                       # 内层（先包装原函数）
    def target() -> str:
        print("      [原函数执行]")
        return "done"

    print("    调用多层装饰的 target()：")
    target()
    print("    ★ 顺序：装饰器自下而上应用，调用时自上而下执行（A包B包原函数）。")


def main() -> None:
    """主函数：按教学顺序演示设计模式。"""
    demo_singleton()
    demo_factory()
    demo_strategy()
    demo_observer()
    demo_decorator()

    print()
    print("=" * 60)
    print("小结")
    print("=" * 60)
    print("  1. ★ 单例：模块级(推荐)/元类/__new__/装饰器；注意线程安全，慎用（反模式）")
    print("  2. ★ 工厂：集中创建逻辑，简单工厂管注册表，抽象工厂产『一族』对象")
    print("  3. ★ 策略：算法封装成可互换对象，运行时切换；Python 惯用函数式策略")
    print("  4. ★ 观察者：主题广播给订阅者，观察者即回调函数（发布订阅范式）")
    print("  5. ★ 装饰器：@dec 等价于 func=dec(func)；参数装饰器需三层函数")
    print("  6. ★ functools.wraps 必须用，否则 __name__/__doc__ 丢失")
    print("  7. 装饰器定义时执行一次，调用时才执行包装逻辑（常被误解）")
    print("  8. 标准库封装了众多模式：singledispatch(工厂)/lru_cache(缓存装饰器)/")
    print("     ABC(抽象工厂思想)/Enum(有限实例)")


if __name__ == "__main__":
    main()