"""
================================================================================
 01_collections.py  ——  collections：把低效的手写数据结构换掉
================================================================================

【演示的语法点】
 1. defaultdict(factory)：缺 key 时自动调用工厂函数造默认值
 2. Counter：计数 / most_common / 集合运算 / 元素分解
 3. deque：双端队列，append/popleft 都是 O(1)，maxlen 自动淘汰
 4. namedtuple：具名元组，字段可读、可 _asdict、可 _replace
 5. OrderedDict：有序字典，move_to_end / popitem(last=False)
 6. ChainMap：多字典视图合并，写入只落第一个 map
 7. UserDict / UserList / UserString：dict/list 的可继承版本
 8. 实战：日志聚合、LRU 缓存、分组、滑动窗口

【预期输出摘要】
 - "defaultdict" 小节：分组结果一次性打印，无需 if key not in dict
 - "Counter" 小节：most_common(2) 输出 [('c', 4), ('b', 3)]
 - "deque" 小节：maxlen=3 的窗口自动保留最后 3 个元素
 - "实战 LRU 缓存" 小节：命中率统计随插入/访问变化
================================================================================

"""

from __future__ import annotations

import collections
from collections import ChainMap, Counter, OrderedDict, defaultdict, deque, namedtuple
from collections import UserDict, UserList
from typing import NamedTuple


# ===== 语法解析 =====
# 【1】defaultdict：把"先判断再赋值"压缩成一行
#   语法规则：defaultdict(default_factory)
#   - default_factory 是【可调用对象】，不是实例本身（与 list() 的区别见下）
#   - 访问一个不存在的 key 时，__missing__ 被调用 → 执行 factory() → 存进去并返回
#   执行顺序：
#     d['a']  → dict.__getitem__ 找不到 → 触发 __missing__ → factory() → 写入 → 返回
#   设计意图：把重复出现的"if k not in d: d[k] = []"样板代码提升为语言特性。
def demo_defaultdict() -> None:
    # 普通 dict 的样板代码：每次新增一个 key 都要写两行
    plain: dict[str, list[int]] = {}
    data = [("apple", 3), ("banana", 1), ("apple", 5)]
    for k, v in data:
        if k not in plain:      # 必须先判断，否则 KeyError
            plain[k] = []
        plain[k].append(v)
    print(f"  普通 dict 分组：{dict(sorted(plain.items()))}")

    # defaultdict(list)：工厂是 list 这个【类对象】本身，调用 list() → []
    dd = defaultdict(list)
    for k, v in data:
        dd[k].append(v)        # 首次访问 dd['apple'] 自动创建 []
    print(f"  defaultdict 分组：{dict(sorted(dd.items()))}")
    # ★ 注意：dd[k] 这一【读取】动作本身就产生了副作用（修改了字典）
    print(f"  ★ 读取即写入：访问 dd['pear'] 后字典多了一项 → {dict(sorted(dd.items()))}")

    # 工厂是 int 时实现"计数器"，比 setdefault 更简洁
    counter = defaultdict(int)
    for ch in "aabbbcccc":
        counter[ch] += 1        # 不存在的 key 自动变 0 再 +1
    print(f"  defaultdict(int) 计数：{dict(sorted(counter.items()))}")

    # 工厂是 lambda 时可以造更复杂的默认值（这里造一个嵌套字典）
    nested = defaultdict(lambda: {"count": 0, "sum": 0})
    for price in [10, 20, 30]:
        nested["total"]["count"] += 1
        nested["total"]["sum"] += price
    print(f"  嵌套默认值：{dict(nested)}")

    # ⚠ 坑：defaultdict(int) 访问缺失 key 返回 0，但 default dict 返回 None
    #   None 之后做运算会报 TypeError，所以选工厂要选"可参与后续运算"的类型
    print(f"  defaultdict(int) 访问不存在的 key → {counter['nope']}（不抛异常）")
    print(f"  get() 不会触发默认值：{counter.get('nope', '默认值')}")


# ===== 语法解析 =====
# 【2】Counter：dict 的子类，但重载了算术运算符
#   语法规则：Counter(iterable) —— 用可迭代对象的所有元素做计数
#   关键特性：
#     - 缺失 key 返回 0（dict 会 KeyError）→ 可以直接 c[k] += 1
#     - 支持 + - & | 四种运算，语义是【多重集】（multiset）的并/交/差
#   设计意图：把"词频统计"这个高频任务标准化，并让集合运算复用到计数场景。
def demo_counter() -> None:
    text = "aabbbcccc"
    c = Counter(text)
    print(f"  Counter({text!r}) = {dict(c)}")
    print(f"  c['a'] = {c['a']}，c['zzz'] = {c['zzz']}   # 缺失返回 0 而不报错")

    # most_common(n)：返回 [(元素, 次数), ...]，按次数降序；不给 n 则全给
    # ⚠ 次数相同时保持【插入顺序】，不是字典序
    print(f"  most_common(2) = {c.most_common(2)}")
    print(f"  most_common() 全量 = {c.most_common()}")

    # elements()：把计数"展开"回原始序列，常用于还原或做统计
    print(f"  elements() 展开后 = {''.join(sorted(c.elements()))}")

    # 实战：找众数 + 找只出现一次的元素
    words = ["go", "python", "go", "rust", "go", "python"]
    wc = Counter(words)
    print(f"  词频 = {dict(wc)}")
    print(f"  众数 top1 = {wc.most_common(1)}")
    print(f"  只出现一次的词 = {[w for w, n in wc.items() if n == 1]}")

    # 多重集运算：+ 是"逐 key 相加"，- 是"截断相减"，& | 是取 min/max
    a, b = Counter("aab"), Counter("abc")
    print(f"  {dict(a)} + {dict(b)} = {dict(a + b)}      # 并：相加")
    print(f"  {dict(a)} & {dict(b)} = {dict(a & b)}      # 交：取 min")
    print(f"  {dict(a)} | {dict(b)} = {dict(a | b)}      # 并：取 max")
    print(f"  {dict(a)} - {dict(b)} = {dict(a - b)}      # 差：只保留正数")
    # ⚠ - 会丢弃结果为负/零的 key，所以它不是普通集合差集

    # 实战：用 Counter 找"非众数"元素，天然处理重复
    nums = [1, 2, 2, 3, 3, 3]
    mode = Counter(nums).most_common(1)[0][0]
    print(f"  众数 = {mode}，去掉众数后的集合 = {sorted(set(nums) - {mode})}")


# ===== 语法解析 =====
# 【3】deque：两端都能 O(1) 进出队的双端队列
#   语法规则：deque(iterable, maxlen=n)
#   - 左侧操作：appendleft / popleft；右侧操作：append / pop（与 list 同名）
#   - maxlen 非空时，【从任一端插入都会自动从另一端弹出最旧的】，长度恒定
#   设计意图：list.pop(0) 是 O(n)（要搬移所有元素），
#             deque.popleft() 是 O(1)，所以队列/栈/滑动窗口必须用 deque。
def demo_deque() -> None:
    d = deque([1, 2, 3])
    d.append(4)          # 右端加入 → O(1)
    d.appendleft(0)      # 左端加入 → O(1)
    print(f"  双端操作后：{list(d)}")
    print(f"  popleft() 弹出左端 = {d.popleft()}，剩余 {list(d)}")
    print(f"  pop() 弹出右端 = {d.pop()}，剩余 {list(d)}")

    # 实战：用 deque 实现 FIFO 任务队列
    queue: deque[str] = deque()
    for task in ["A", "B", "C"]:
        queue.append(task)
    order = []
    while queue:
        order.append(queue.popleft())      # 先来先服务
    print(f"  FIFO 出队顺序：{order}")

    # ★ 滑动窗口：maxlen 自动淘汰旧元素，天然实现"最近 N 条"
    window = deque(maxlen=3)
    for i in range(1, 7):
        window.append(i)
        if len(window) == 3:
            print(f"    第 {i} 次滑动，窗口 = {list(window)}，均值 = {sum(window)/3:.2f}")
    print(f"  最终窗口只剩最近 3 个：{list(window)}")

    # rotate：整体循环右移，常用于轮询
    r = deque([1, 2, 3, 4, 5])
    r.rotate(2)          # 右移 2 位，左端的元素绕到右端
    print(f"  rotate(2) 后：{list(r)}")
    r.rotate(-1)         # 负数表示左移
    print(f"  rotate(-1) 后：{list(r)}")

    # 对比：list 头部删除的代价（用 timeit 风格的粗略计时说明量级）
    lst = list(range(100_000))
    import time

    t0 = time.perf_counter()
    dq = deque(lst)
    for _ in range(1000):
        dq.popleft()    # O(1)
    t_deque = time.perf_counter() - t0

    t0 = time.perf_counter()
    lst2 = list(range(100_000))
    for _ in range(1000):
        del lst2[0]     # ⚠ O(n)：每次都要把后面所有元素前移一格
    t_list = time.perf_counter() - t0
    print(f"  头部删除 1000 次：deque {t_deque * 1000:.3f} ms  vs  list {t_list * 1000:.3f} ms")

    # extend / 批量操作
    d.extend([9, 9])
    print(f"  extend 后：{list(d)}，count(9) = {d.count(9)}")


# ===== 语法解析 =====
# 【4】namedtuple：给元组的每个位置起名字
#   语法规则：
#     Point = namedtuple("Point", "x y")            # 空格/逗号分隔字段名
#     Point = namedtuple("Point", ["x", "y"])        # 列表形式
#   - 它是 tuple 的子类，因此【不可变】、可哈希、可当字典键
#   - 生成的方法：_asdict() _replace() _make() _fields
#   设计意图：纯 tuple 靠下标访问（p[0]）可读性差，纯类又太啰嗦，
#             namedtuple 提供"零成本"的具名记录（本质仍是 tuple，内存不增）。
def demo_namedtuple() -> None:
    Point = namedtuple("Point", "x y")
    p = Point(1, 2)
    print(f"  Point(1, 2) = {p}，类型 = {type(p).__name__}")
    print(f"  按名访问 p.x = {p.x}   # 比 p[0] 可读")
    print(f"  仍是元组：p[0] = {p[0]}，可哈希 → {hash(p) != 0}")

    # _fields：字段名元组；_asdict：转成普通 dict（**p 可解包）
    print(f"  _fields = {Point._fields}")
    print(f"  _asdict() = {p._asdict()}")
    print(f"  **解包 = {dict(**p._asdict())}")

    # _replace：**基于自身生成修改后的新对象**（不可变，不能原地改）
    print(f"  _replace(x=99) = {p._replace(x=99)}  ← 原对象不变：{p}")

    # _make：从可迭代对象批量构造（等价 Point(*iterable)）
    print(f"  Point._make([7, 8]) = {Point._make([7, 8])}")

    # 带默认值与类型注解（3.6+ / 3.7+ 语法）
    Record = namedtuple("Record", ["id", "name", "score"], defaults=["未命名", 0])
    print(f"  默认值：Record(1) = {Record(1)}")

    # ⚠ 坑：字段名列表里【不能写 ("id", int) 这样的元组】，它只接受字符串字段名
    #   错误写法：namedtuple("R", [("id", int)]) → ValueError: must be valid identifiers
    #   想带注解请用 3.7+ 的 class 语法（见 06_oop/06_dataclass.py 的 NamedTuple）
    AnnRecord = collections.namedtuple("AnnRecord", "id name")
    print(f"  字段名元组：{AnnRecord._fields}")
    print(f"  构造：{AnnRecord(1, '张三')}")
    #   ⚠ NamedTuple 在 typing 模块里，不在 collections 里
    # 类语法版 NamedTuple：既有具名访问，又能声明类型
    class TypedRecord(NamedTuple):
        id: int
        name: str

    tr = TypedRecord(1, "张三")
    print(f"  NamedTuple 类语法：{tr}，类型注解 = {TypedRecord.__annotations__}")

    # 实战：一条日志记录
    LogEntry = namedtuple("LogEntry", "ts level module message")
    entries = [
        LogEntry("10:00", "INFO", "auth", "用户登录成功"),
        LogEntry("10:05", "ERROR", "db", "连接超时"),
    ]
    for e in entries:
        print(f"    [{e.level}] {e.ts} {e.module} → {e.message}")

    # 对比：dataclass 版本（06_oop/06_dataclass.py 会详讲）
    print("  相比 class：namedtuple 不可变、内存更小，但加字段/方法需重建类")


# ===== 语法解析 =====
# 【5】OrderedDict：记住插入顺序的字典
#   语法规则：OrderedDict(mapping)
#   专属方法：move_to_end(key, last=True/False)、popitem(last=False)
#   为什么还需要它（3.7+ 之后）：
#     - Python 3.7 起【普通 dict 本身已保证插入顺序】，这是语言规范而非实现细节
#     - 但 OrderedDict 多了 move_to_end 等【顺序操作方法】，且 == 比较时
#       会【考虑顺序】：OrderedDict([('a',1),('b',2)]) != OrderedDict([('b',2),('a',1)])
#     - dict 之间 == 只比较内容，与顺序无关
def demo_ordereddict() -> None:
    od = OrderedDict([("a", 1), ("b", 2), ("c", 3)])
    print(f"  初始：{list(od.items())}")
    od.move_to_end("a")             # 把 a 移到末尾
    print(f"  move_to_end('a') 后：{list(od.items())}")
    od.move_to_end("c", last=False)  # 把 c 移到最前
    print(f"  move_to_end('c', last=False) 后：{list(od.items())}")

    # popitem(last=False)：弹出【最左】的键值对 —— LRU 的基础操作
    first_k, first_v = od.popitem(last=False)
    print(f"  popitem(last=False) → ({first_k}, {first_v})，剩余 {list(od.items())}")

    # ★ 顺序敏感的比较：这是 OrderedDict 与 dict 最关键的区别
    od1 = OrderedDict([("a", 1), ("b", 2)])
    od2 = OrderedDict([("b", 2), ("a", 1)])
    print(f"  OrderedDict 顺序不同则不等：{od1 == od2}   ← 会考虑顺序")
    print(f"  普通 dict 顺序不同仍相等：{dict(od1) == dict(od2)}   ← 忽略顺序")

    # 实战：LRU 缓存（真正的实现见 functools.lru_cache，这里手写版看原理）
    class SimpleLRU:
        """手写 LRU：OrderedDict 的顺序操作正好对应 LRU 的访问序。"""

        def __init__(self, capacity: int) -> None:
            self.cap = capacity
            self.data: OrderedDict[str, int] = OrderedDict()

        def get(self, key: str) -> int | None:
            if key not in self.data:
                return None
            self.data.move_to_end(key)      # 命中 → 标记为"最近使用"
            return self.data[key]

        def put(self, key: str, value: int) -> None:
            if key in self.data:
                self.data.move_to_end(key)
            self.data[key] = value
            if len(self.data) > self.cap:
                self.data.popitem(last=False)   # 淘汰最久未使用

    lru = SimpleLRU(capacity=3)
    for k, v in [("a", 1), ("b", 2), ("c", 3)]:
        lru.put(k, v)
    print(f"  填满 3 个：{list(lru.data.keys())}")
    lru.get("a")                        # 访问 a → a 变最新
    print(f"  访问 a 之后：{list(lru.data.keys())}   ← a 被移到末尾")
    lru.put("d", 4)                     # 超容量 → 淘汰最左的 b
    print(f"  插入 d 之后：{list(lru.data.keys())}   ← b 被淘汰")
    print(f"  b 是否还在：{lru.get('b') is None}")


# ===== 语法解析 =====
# 【6】ChainMap：把多个字典【合并成一个视图】读取
#   语法规则：ChainMap(*maps)
#   执行顺序：按参数顺序在每个 map 里查找，【第一个命中的胜出】
#   设计意图：典型场景是"默认值 → 配置文件 → 环境变量"的分层配置。
#             读取时合并，写入时【只修改第一个 map】，从而天然实现"覆盖默认值"。
def demo_chainmap() -> None:
    defaults = {"host": "localhost", "port": 8080, "debug": False}
    config = {"host": "192.168.1.10", "port": 9090}
    merged = ChainMap(config, defaults)     # config 优先

    print(f"  合并后 host = {merged['host']}   ← 来自 config（优先级更高）")
    print(f"  合并后 debug = {merged['debug']}   ← defaults 里才有，回退取值")
    print(f"  所有键 = {list(merged.keys())}")

    # ★ 写入只落在【第一个 map】，defaults 永远不被修改 —— 这正是"覆盖默认"的关键
    merged["host"] = "10.0.0.1"
    print(f"  写入后 config = {config}")
    print(f"  写入后 defaults = {defaults}   ← 未被污染")
    print(f"  合并后 host = {merged['host']}")

    # new_child()：派生一个新 ChainMap，用于临时覆盖（不改原链）
    scoped = merged.new_child({"port": 3000})
    print(f"  new_child 后的 port = {scoped['port']}，原链 port = {merged['port']}")

    # maps 属性：可以看到底层是哪几个字典
    print(f"  maps = {merged.maps}")

    # 实战：命令行 > 环境变量 > 默认值 的分层（完整版见 09_json_config.py）
    import os

    defaults2 = {"level": "INFO", "encoding": "utf-8"}
    env_cfg = {"level": os.environ.get("APP_LEVEL", "")}  # 环境变量层
    cli_cfg = {}                                          # 命令行层
    final = ChainMap(cli_cfg, {k: v for k, v in env_cfg.items() if v}, defaults2)
    print(f"  三层配置最终值：{dict(final)}")


# ===== 语法解析 =====
# 【7】UserDict / UserList / UserString
#   语法规则：class MyDict(UserDict): pass
#   它们的本质是 MutableMapping / MutableSequence 的【适配器】：
#     - 内部用 self.data 真正存储数据
#     - 提供和内置 dict/list 一样的接口，但底层换成你自己的结构
#   设计意图：想在【已有字典逻辑】上叠加校验/加密/持久化，而又不想重写所有方法，
#             继承 UserDict 只需重写 __setitem__ 等少数钩子即可。
def demo_userdict() -> None:
    # 继承 UserDict 实现"只允许小写 key"的字典
    class LowerDict(UserDict):
        """所有 key 强制转小写 —— 只重写 __setitem__ 一个钩子。"""

        def __setitem__(self, key: str, value: object) -> None:
            super().__setitem__(key.lower(), value)   # 调用父类完成真实写入

    ld = LowerDict({"Name": "张三"})
    ld["Age"] = 18
    print(f"  LowerDict 内容：{dict(ld)}   ← key 全被规范成小写")
    ld["NAME"] = "李四"
    print(f"  再次写入后：{dict(ld)}   ← 覆盖了 Name 而非新增")

    # UserList：可以重写对"列表整体"的处理（如禁止删除）
    class ReadOnlyList(UserList):
        def __delitem__(self, index):        # 拦截删除操作
            raise PermissionError("列表为只读，禁止删除")

    rl = ReadOnlyList([1, 2, 3])
    print(f"  UserList 内容：{rl.data}   ← .data 才是真正存储")
    try:
        del rl[0]
    except PermissionError as e:
        print(f"  删除被拦截：{e}")

    # collections.abc 里的抽象基类（ABC），可用来做类型约束
    print(f"  isinstance(ld, collections.abc.MutableMapping) = "
          f"{isinstance(ld, collections.abc.MutableMapping)}")

    # 标准库还提供了一些"计算型"命名元组（了解即可）
    pt = collections.namedtuple("Pt", "x y")(3, 4)
    print(f"  通过 collections.namedtuple 创建：{pt}")
    # namedtuple 还有 ._asdict() 的现代替代：_replace 配合 **dict
    print(f"  现代写法：{pt._replace(**dict(zip(pt._fields, (5, 6))))}")


# ===== 语法解析 =====
# 【8】综合实战：把上面的工具串起来解决一个真实问题
#   任务：对一批访问日志做聚合分析 —— 统计 TOP IP、按状态码分组、
#         计算滑动窗口内的活跃 IP 数。
def demo_real_world() -> None:
    # 模拟访问日志：(IP, 状态码, 响应毫秒)
    logs = [
        ("192.168.1.1", 200, 120),
        ("192.168.1.2", 200, 340),
        ("10.0.0.5", 404, 80),
        ("192.168.1.1", 500, 2100),
        ("10.0.0.5", 200, 95),
        ("192.168.1.3", 200, 60),
        ("192.168.1.1", 200, 140),
        ("10.0.0.5", 429, 30),
    ]

    # ① Counter 统计各 IP 的访问次数（词频统计的标准场景）
    ip_counter = Counter(ip for ip, _, _ in logs)
    print("  ① 各 IP 访问次数：")
    for ip, n in ip_counter.most_common():
        print(f"      {ip:<15} {n} 次")

    # ② defaultdict 按状态码分组
    by_status: defaultdict[int, list[str]] = defaultdict(list)
    for ip, code, _ in logs:
        by_status[code].append(ip)
    print(f"  ② 按状态码分组：{ {k: len(v) for k, v in sorted(by_status.items())} }")

    # ③ 找出耗时超过 1 秒的慢请求（filter + 命名元组让结果可读）
    SlowReq = namedtuple("SlowReq", "ip code cost")
    slow = [SlowReq(ip, code, cost) for ip, code, cost in logs if cost > 1000]
    print(f"  ③ 慢请求(>1s)：{[dict(r._asdict()) for r in slow]}")

    # ④ deque 维护最近 3 条请求，算平均响应时间（滑动窗口）
    recent: deque[int] = deque(maxlen=3)
    for ip, code, cost in logs:
        recent.append(cost)
        if len(recent) == 3:
            avg = sum(recent) / len(recent)
            print(f"      最近 3 次平均 {avg:7.1f} ms（窗口 {list(recent)}）")

    # ⑤ 综合：每个 IP 的状态码集合，用 defaultdict(set) 自动去重
    ip_codes: defaultdict[str, set[int]] = defaultdict(set)
    for ip, code, _ in logs:
        ip_codes[ip].add(code)
    print("  ⑤ 每个 IP 出现过的状态码：")
    for ip in sorted(ip_codes):
        codes = ip_codes[ip]
        ok = "✓" if codes <= {200, 201, 204} else "✗ 存在错误"
        print(f"      {ip:<15} {sorted(codes)}  {ok}")


def main() -> None:
    print("=" * 60)
    print("【1】defaultdict：自动默认值")
    print("=" * 60)
    demo_defaultdict()

    print()
    print("=" * 60)
    print("【2】Counter：计数与多重集运算")
    print("=" * 60)
    demo_counter()

    print()
    print("=" * 60)
    print("【3】deque：双端队列与滑动窗口")
    print("=" * 60)
    demo_deque()

    print()
    print("=" * 60)
    print("【4】namedtuple：具名元组")
    print("=" * 60)
    demo_namedtuple()

    print()
    print("=" * 60)
    print("【5】OrderedDict：有序字典与 LRU 原理")
    print("=" * 60)
    demo_ordereddict()

    print()
    print("=" * 60)
    print("【6】ChainMap：分层配置合并")
    print("=" * 60)
    demo_chainmap()

    print()
    print("=" * 60)
    print("【7】UserDict / UserList：适配器基类")
    print("=" * 60)
    demo_userdict()

    print()
    print("=" * 60)
    print("【8】综合实战：访问日志聚合分析")
    print("=" * 60)
    demo_real_world()

    print()
    print("=" * 60)
    print("小结")
    print("=" * 60)
    print("  1. defaultdict 用工厂函数消除 if key not in dict 样板代码")
    print("  2. Counter 缺失 key 返回 0，支持多重集的 + - & | 运算")
    print("  3. deque 两端进出均 O(1)，maxlen 自动实现滑动窗口/淘汰")
    print("  4. namedtuple = 具名的不可变记录，内存与 tuple 相同")
    print("  5. OrderedDict 的顺序敏感比较与 move_to_end 是 LRU 的基础")
    print("  6. ChainMap 读取合并、写入只落首层，天然实现配置分层")
    print("  7. UserDict/UserList 是适配器基类，重写钩子即可定制行为")


if __name__ == "__main__":
    main()