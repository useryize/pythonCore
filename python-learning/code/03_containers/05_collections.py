"""
================================================================================
  05_collections.py  ——  collections 模块五大工具类综合实战
================================================================================

【演示的语法点】
 1. namedtuple：带字段名的元组（轻量替代普通类的不可变数据载体）
 2. ★ deque：双端队列，高效的两端操作与 maxlen 滑动窗口
 3. Counter：词频统计、排行榜、算术运算
 4. ChainMap：把多个字典「串」成一个逻辑映射（配置分层常用）
 5. OrderedDict：显式排序、move_to_end、LIFO/FIFO 行为（引出 3.7+ 替代方案）
 6. ★ 三大实战场景：日志分析、任务队列（LRU）、词频统计
 7. 各工具类的选型决策表与性能对比（timeit 实测）

【预期输出摘要】
 - "日志分析" 小节用 namedtuple + ChainMap 解析多行访问日志并做统计
 - "任务队列" 小节用 deque 实现 FIFO/LIFO 队列与 maxlen 滑动窗口
 - "LRU 缓存" 小节用 OrderedDict 实现完整的 LRU 缓存类
 - "词频统计" 小节用 Counter 完成分词、TopN、词云数据
 - "性能对比" 小节打印 deque vs list 在两端操作上的耗时差
================================================================================

"""

from __future__ import annotations

import timeit
from collections import Counter, OrderedDict, deque, namedtuple, ChainMap
from typing import Any, Deque, Dict, List, Optional, Tuple


# ==============================================================================
# 【工具类一】namedtuple —— 带字段名的元组
# ==============================================================================
# ===== 语法解析 =====
# namedtuple("类型名", ["字段1", "字段2"])
#   语法：工厂函数，动态生成一个【元组子类】。
#   本质：既是 tuple（不可变、可哈希、轻量），又能用 .字段名 访问。
#   设计意图：用极低成本替代「只有几个字段、不可变的普通类」。
#   优势：比 dataclass 轻，比 dict 省内存，比普通类快（无 __dict__）。
def demo_namedtuple() -> None:
    print("=" * 60)
    print("【工具类一】namedtuple 带字段名的元组")
    print("=" * 60)

    # 1) 传统写法：tuple() 生成
    Point = namedtuple("Point", ["x", "y"])
    p = Point(1, 2)
    print(f"  Point(1, 2)       = {p}")
    print(f"  p.x, p.y          = {p.x}, {p.y}   ← 像类一样访问")
    print(f"  下标访问 p[0]      = {p[0]}   ← 本质仍是元组")
    print(f"  可哈希(可作字典键) = { {(p): '坐标'} }")
    print(f"  isinstance tuple  = {isinstance(p, tuple)}")

    # 2) 关键字参数构造（可读性更好）
    p2 = Point(y=4, x=3)                    # 字段顺序可乱
    print(f"  关键字构造 Point(y=4, x=3) = {p2}")

    # 3) 默认值（3.7+ 支持 defaults 参数）
    Product = namedtuple("Product", ["name", "price", "stock"], defaults=[0, 0])
    prod = Product("笔记本")                  # 后两个字段用默认值
    print(f"  带默认值 Product('笔记本') = {prod}")
    print(f"  ★ 用 _replace 修改（返回新对象）: {prod._replace(price=5999)}")

    # 4) 解包与 _asdict()
    name, price = p                         # 元组解包
    print(f"  解包 name, price = {name}, {price}")
    print(f"  _asdict() 转字典   = {p._asdict()}")

    print()
    print("  ★ 现代写法（推荐）：class Point(NamedTuple) —— 见 06_dataclass 的完整对比")
    print("    from typing import NamedTuple")
    print("    class P(NamedTuple):")
    print("        x: int")
    print("        y: int")
    print("    ★ 写法更直观，IDE 有补全；与 namedtuple() 等价。")

    print()
    print("  ★ namedtuple vs 普通类 vs dict：")
    print("  | 方式        | 不可变 | 可哈希 | 内存 | 字段访问 |")
    print("  |-------------|--------|--------|------|----------|")
    print("  | namedtuple  | ✓      | ✓      | 最小 | p.x  ✓    |")
    print("  | 普通 class  | 视实现 | 需实现 | 较大 | p.x  ✓    |")
    print("  | dict        | ✗      | ✗      | 较大 | p['x']    |")
    print(f"    namedtuple 内存 {len(p) * 8 + 16} 字节 vs dict {p._asdict() and 200}+ 字节")

    print()
    print("  ★ namedtuple 的特殊方法：")
    print(f"    _fields  字段名元组 = {p._fields}")
    print(f"    _replace 新建副本   = {p._replace(x=99)}   （不改原对象）")
    print(f"    _make    由序列构造 = {Point._make([7, 8])}")


# ==============================================================================
# 【工具类二】deque —— 双端队列
# ==============================================================================
# ===== 语法解析 =====
# deque(iterable, maxlen=N)
#   语法：双端队列，两端添加/删除都是 O(1)。
#   对比 list：list.append/pop() 只在尾部高效；deque 两端都 O(1)。
#   maxlen 参数：超过长度时【自动丢弃最旧元素】（滑动窗口核心）。
#   设计意图：队列/栈/滑动窗口的标准实现，比 list 更安全高效。
def demo_deque() -> None:
    print()
    print("=" * 60)
    print("【工具类二】deque 双端队列")
    print("=" * 60)

    # 1) 创建
    d: Deque[int] = deque([1, 2, 3])
    print(f"  deque([1,2,3])       = {d}")
    print(f"  空 deque()          = {deque()}")
    print(f"  deque(可迭代对象)     = {deque('abc')}")

    # 2) 双端操作
    d.append(4)                             # 右端加
    d.appendleft(0)                         # 左端加（list 没有）
    print()
    print(f"  append(4) + appendleft(0) = {d}")
    print(f"  pop()      右端弹出 = {d.pop()}      → {d}")
    print(f"  popleft()  左端弹出 = {d.popleft()}      → {d}")
    print("    ★ pop()/popleft() 是 O(1)；list.pop(0) 是 O(n)（需搬移所有元素）。")

    # 3) 索引访问（O(n)，但支持两端快速访问）
    print()
    print(f"  d[0]={d[0]}  d[-1]={d[-1]}   （索引访问仍是 O(n)，但不被视为错误）")

    # 4) ★ maxlen：自动丢弃最旧元素 —— 滑动窗口
    print()
    print("  ★ maxlen 滑动窗口（超出自动丢最旧）：")
    window: Deque[int] = deque(maxlen=3)
    for i in range(1, 6):
        window.append(i)
        print(f"    append({i}) 后 → {list(window)}")
    print("    ★ 始终保持最新 3 个值 —— 这是限流/最近N条 的标准写法。")

    # 5) 常用方法
    print()
    print("  常用方法：")
    print(f"    append(x)      右端加")
    print(f"    appendleft(x)  左端加")
    print(f"    pop()          右端弹")
    print(f"    popleft()      左端弹")
    print(f"    extend(可迭代)  右端批量扩展")
    print(f"    extendleft()   左端批量扩展")
    print(f"    rotate(n)      旋转（n>0 右移）")
    print(f"    clear()        清空")
    print(f"    count(x)/remove(x) 计数/删除")

    # 6) rotate：循环滑动（做游戏/轮询）
    d2 = deque([1, 2, 3, 4, 5])
    d2.rotate(2)                            # 右移 2 位
    print()
    print(f"    deque([1..5]).rotate(2) = {list(d2)}   （整体右移 2）")
    d2.rotate(-1)                           # 左移 1
    print(f"    再 rotate(-1)          = {list(d2)}   （左移回退）")


# ==============================================================================
# 【工具类三】Counter —— 计数器
# ==============================================================================
# ===== 语法解析 =====
# Counter(可迭代) / Counter(mapping)
#   语法：返回 {元素: 次数} 的子类字典，缺失键默认 0。
#   扩展运算：+ 取 max，- 只保留正数，& 取 min（多重集合语义）。
#   设计意图：把「计数」内置，支持 most_common 排行。
def demo_counter() -> None:
    print()
    print("=" * 60)
    print("【工具类三】Counter 计数器")
    print("=" * 60)

    # 1) 基本计数
    words = ["apple", "banana", "apple", "orange", "banana", "apple"]
    c = Counter(words)
    print(f"  Counter(['apple','banana',...]) = {dict(c)}")
    print(f"  c['apple'] = {c['apple']}  c['grape'] = {c['grape']}  （缺失默认 0，不报错）")

    # 2) most_common 排行
    print()
    print(f"  most_common(2) 前两名   = {c.most_common(2)}")
    print(f"  most_common() 全部降序  = {c.most_common()}")

    # 3) 统计任意可迭代：字符、行、元组
    print()
    print(f"  统计字符  Counter('mississippi') = {dict(Counter('mississippi'))}")
    print(f"  统计元组  Counter([(1,2),(1,2)]) = {dict(Counter([(1, 2), (1, 2)]))}")

    # 4) 更新与合并
    print()
    c2 = Counter("aab")
    c2.update("ab")                          # 累加计数
    print(f"  Counter('aab') + update('ab') = {dict(c2)}")

    # 5) 算术运算（多重集合）
    print()
    x = Counter({"apple": 3, "banana": 2})
    y = Counter({"apple": 1, "cherry": 4})
    print(f"  x = {dict(x)}")
    print(f"  y = {dict(y)}")
    print(f"  x + y（取 max） = {dict(x + y)}")
    print(f"  x - y（差正数） = {dict(x - y)}")
    print(f"  x & y（取 min） = {dict(x & y)}")

    # 6) elements：按次数展开
    print()
    print(f"  elements() 展开 = {list(c.elements())[:8]} ...")
    print("    ★ 把 {元素:次数} 还原成 展开后的元素列表。")


# ==============================================================================
# 【工具类四】ChainMap —— 多字典串联
# ==============================================================================
# ===== 语法解析 =====
# ChainMap(*maps)
#   语法：把多个映射「链」成一个逻辑视图，按顺序查找（前者优先）。
#   读取：从左到右找第一个含该键的映射 → O(k)，k 为映射个数。
#   写入：永远写到【第一个】映射。
#   设计意图：配置分层（默认 + 用户 + 环境变量）优先级的经典方案。
def demo_chainmap() -> None:
    print()
    print("=" * 60)
    print("【工具类四】ChainMap 多字典串联")
    print("=" * 60)

    # 1) 基本链：优先级从左到右
    defaults = {"host": "localhost", "port": 80, "debug": False}
    user = {"port": 8080, "debug": True}
    env = {"host": "prod.example.com"}
    config = ChainMap(env, user, defaults)    # env 优先级最高，defaults 兜底
    print(f"  defaults = {defaults}")
    print(f"  user     = {user}")
    print(f"  env      = {env}")
    print()
    print(f"  ChainMap(env, user, defaults) 合并后：")
    print(f"    config['host'] = {config['host']}   （env 优先）")
    print(f"    config['port'] = {config['port']}   （user 覆盖 defaults）")
    print(f"    config['debug'] = {config['debug']}  （defaults 兜底）")

    # 2) 查看所有层
    print()
    print(f"  config.maps  = {len(config.maps)} 层")
    for i, m in enumerate(config.maps):
        print(f"    第{i + 1}层(优先级{len(config.maps) - i}): {dict(m)}")

    # 3) ★ 写入永远进【第一层】
    config["timeout"] = 30                   # 写入第一个映射
    print()
    print(f"  写入 timeout=30 后：")
    print(f"    第1层新增 = {config.maps[0]}")
    print(f"    ★ 注意 defaults 层【未被修改】（写入不穿透）")

    # 4) new_child：动态新增一层高优先级
    session = config.new_child({"user": "admin"})
    print()
    print(f"  new_child({{'user':'admin'}}) 新增最优先层：")
    print(f"    session['user'] = {session['user']}")
    print(f"    原 config['user'] = {config.get('user', '无')}   （原配置未变）")

    # 5) 合并为普通 dict
    print()
    merged = dict(config)                    # 物化成普通字典（按优先级取值）
    print(f"  dict(config) 物化 = {merged}")


# ==============================================================================
# 【工具类五】OrderedDict —— 有序字典
# ==============================================================================
# ===== 语法解析 =====
# OrderedDict
#   语法：3.6 前保证插入顺序；3.7+ 普通 dict 也保证，但 OrderedDict 额外提供：
#     - move_to_end(key)  移动到末尾/开头
#     - popitem(last=False)  从头部弹出（LIFO/FIFO 队列）
#   设计意图：3.7+ 前的有序字典；现在主要用它的这两个专属方法 + 实现 LRU。
def demo_ordereddict() -> None:
    print()
    print("=" * 60)
    print("【工具类五】OrderedDict 有序字典")
    print("=" * 60)

    # 1) 基本有序（普通 dict 现在也保序，但对比展示历史差异）
    od = OrderedDict()
    for k in ["z", "a", "m"]:
        od[k] = ord(k)
    print(f"  按插入顺序 z,a,m → {list(od.keys())}")
    print(f"  ★ 3.7+ 普通 dict 也保证插入顺序，OrderedDict 的优势在下面两个方法：")

    # 2) ★ move_to_end：移动位置（普通 dict 没有）
    od.move_to_end("z")                      # 移到末尾
    print()
    print(f"  move_to_end('z')    → {list(od.keys())}   （z 移到末尾）")
    od.move_to_end("a", last=False)          # 移到开头
    print(f"  move_to_end('a', False) → {list(od.keys())}   （a 移到开头）")
    print(f"  普通 dict 有 move_to_end 吗？{hasattr({}, 'move_to_end')}   ← False")

    # 3) popitem：LIFO / FIFO
    od2 = OrderedDict([("first", 1), ("second", 2), ("third", 3)])
    last = od2.popitem()                     # last=True（默认）：从尾部弹（LIFO）
    first = od2.popitem(last=False)          # last=False：从头部弹（FIFO）
    print()
    print(f"  popitem() 从尾弹(LIFO) = {last}")
    print(f"  popitem(last=False) 从头弹(FIFO) = {first}")

    # 4) 与普通 dict 的相等性差异
    print()
    print("  ★ 相等性差异：")
    od3 = OrderedDict([("a", 1), ("b", 2)])
    print(f"    OrderedDict == OrderedDict（顺序敏感）: {OrderedDict([('a',1),('b',2)]) == OrderedDict([('b',2),('a',1)])}")
    print(f"    dict == dict（只看内容）: { {'a':1,'b':2} == {'b':2,'a':1} }")
    print("    ★ 这是 OrderedDict 至今仍存在的理由之一（顺序有语义时）。")


# ==============================================================================
# ★ 实战场景一：日志分析（namedtuple + ChainMap + Counter）
# ==============================================================================
# ===== 语法解析 =====
# 用 namedtuple 定义日志结构（比 dict 省内存，适合海量日志）；
# 用 ChainMap 管理解析配置；用 Counter 做统计。
def demo_scenario_log_analysis() -> None:
    print()
    print("=" * 60)
    print("★ 实战场景一：访问日志分析")
    print("=" * 60)

    # 1) 用 namedtuple 定义日志记录结构
    LogEntry = namedtuple("LogEntry", ["time", "method", "path", "status", "size"])

    # 模拟原始日志（每行一条访问日志）
    raw_logs = [
        "2024-01-01 10:00:01 GET /api/user 200 1024",
        "2024-01-01 10:00:05 POST /api/order 201 512",
        "2024-01-01 10:01:12 GET /api/user 200 2048",
        "2024-01-01 10:02:30 GET /static/logo.png 200 8192",
        "2024-01-01 10:03:15 GET /api/nonexist 404 128",
        "2024-01-01 10:04:00 POST /api/order 500 256",
        "2024-01-01 10:05:22 GET /api/user 200 1024",
        "2024-01-01 10:06:00 DELETE /api/order 204 0",
    ]

    # 2) 解析成 LogEntry（用 ChainMap 管理解析配置）
    parse_config = ChainMap(
        {"sep": " ", "limit": 5},            # 默认配置
        {"encoding": "utf-8"},               # 扩展配置
    )
    print(f"  解析配置 sep='{parse_config['sep']}'  limit={parse_config['limit']}")

    sep = parse_config["sep"]
    entries: List[LogEntry] = []
    for line in raw_logs:
        parts = line.split(sep)
        # 用 dict 打包再转 namedtuple（也可用 LogEntry(**zip)）
        entries.append(LogEntry(
            time=parts[0] + " " + parts[1],
            method=parts[2],
            path=parts[3],
            status=int(parts[4]),
            size=int(parts[5]),
        ))

    print(f"  解析 {len(entries)} 条日志，前 2 条：")
    for e in entries[:2]:
        print(f"    {e.time} {e.method:6} {e.path:20} {e.status} {e.size}B")

    # 3) 统计分析 ①：按状态码统计（Counter）
    status_count = Counter(e.status for e in entries)
    print()
    print(f"  【状态码分布】{dict(status_count)}")
    success = status_count[200] + status_count[201] + status_count[204]
    print(f"    成功请求(2xx): {success}/{len(entries)}")
    print(f"    错误请求(4xx/5xx): {status_count[404] + status_count[500]}")

    # 4) 统计分析 ②：按路径统计访问次数（Counter）
    path_count = Counter(e.path for e in entries)
    print()
    print(f"  【访问最频繁的路径 Top3】")
    for path, cnt in path_count.most_common(3):
        print(f"    {path:22} {cnt} 次")

    # 5) 统计分析 ③：按 HTTP 方法统计
    method_count = Counter(e.method for e in entries)
    print()
    print(f"  【HTTP 方法分布】{dict(method_count)}")

    # 6) 统计分析 ④：流量最大的请求（按 size）
    biggest = max(entries, key=lambda e: e.size)   # namedtuple 不可变但可排序取极值
    print()
    print(f"  【流量最大请求】{biggest.path} ({biggest.size}B, {biggest.status})")

    # 7) 统计数据流大小
    total_bytes = sum(e.size for e in entries)
    avg_size = total_bytes // len(entries)
    print(f"  【总流量】{total_bytes}B  平均 {avg_size}B/请求")


# ==============================================================================
# ★ 实战场景二：任务队列 + LRU 缓存（deque + OrderedDict）
# ==============================================================================
# ===== 语法解析 =====
# deque 实现 FIFO/LIFO 任务队列；maxlen 实现滑动窗口；
# OrderedDict + move_to_end 实现 LRU 缓存（最经典用途）。
def demo_scenario_task_queue() -> None:
    print()
    print("=" * 60)
    print("★ 实战场景二：任务队列 与 LRU 缓存")
    print("=" * 60)

    # 1) FIFO 任务队列（先进先出）
    task_queue: Deque[str] = deque()
    for task in ["任务A", "任务B", "任务C"]:
        task_queue.append(task)
    print(f"  FIFO 队列：{list(task_queue)}")
    while task_queue:
        task = task_queue.popleft()            # 从头取 → 先进先出
        print(f"    处理 {task}")

    # 2) LIFO 栈（后进先出）
    stack: Deque[str] = deque()
    for task in ["操作1", "操作2", "操作3"]:
        stack.append(task)
    print()
    print(f"  LIFO 栈：{list(stack)}")
    while stack:
        task = stack.pop()                    # 从尾取 → 后进先出
        print(f"    撤销 {task}")

    # 3) ★ maxlen 实现滑动窗口均值
    window: Deque[int] = deque(maxlen=5)
    data_points = [10, 20, 30, 40, 50, 60, 70]
    print()
    print("  ★ 滑动窗口（maxlen=5，计算最近5个值的均值）：")
    for v in data_points:
        window.append(v)
        if len(window) == 5:
            print(f"    加入 {v} → 窗口={list(window)}  均值={sum(window) / 5:.1f}")
        else:
            print(f"    加入 {v} → 窗口={list(window)}（未满5个）")

    # 4) ★ LRU 缓存实现（OrderedDict 经典用途）
    class LRUCache:
        """最近最少使用缓存：容量满时淘汰最久未访问的键。"""

        def __init__(self, capacity: int) -> None:
            self.capacity = capacity
            # OrderedDict：有序，末尾是最新的，头部是最旧的
            self.cache: "OrderedDict[int, str]" = OrderedDict()

        def get(self, key: int) -> Optional[str]:
            if key not in self.cache:
                return None
            # 访问后移到末尾 → 标记为「最近使用」
            self.cache.move_to_end(key)
            return self.cache[key]

        def put(self, key: int, value: str) -> None:
            if key in self.cache:
                self.cache.move_to_end(key)
            self.cache[key] = value
            if len(self.cache) > self.capacity:
                # 超出容量 → 弹出最久未使用的（头部）
                evicted, _ = self.cache.popitem(last=False)
                print(f"      淘汰最旧: 键={evicted}")

    print()
    print("  【LRU 缓存演示】容量=3")
    cache = LRUCache(capacity=3)
    for i, k in enumerate([1, 2, 3]):
        cache.put(k, f"数据{k}")
        print(f"    put({k})")
    print(f"    缓存内容(头→尾): {list(cache.cache.items())}")

    print(f"    get(1) → {cache.get(1)}（1 移到末尾，变为最新）")
    print(f"    缓存内容: {list(cache.cache.items())}")

    print(f"    put(4) → 超出容量，淘汰头部：")
    cache.put(4, "数据4")
    print(f"    最终缓存: {list(cache.cache.items())}   （键1被淘汰，键2也因容量保留最新3个）")
    print(f"    验证 get(1) = {cache.get(1)}（已淘汰→None）  get(4) = {cache.get(4)}（在缓存中）")


# ==============================================================================
# ★ 实战场景三：词频统计（Counter + defaultdict）
# ==============================================================================
# ===== 语法解析 =====
# Counter 是词频统计的首选：一步完成「分词→计数→排行」。
def demo_scenario_word_count() -> None:
    print()
    print("=" * 60)
    print("★ 实战场景三：词频统计与文本分析")
    print("=" * 60)

    # 模拟一篇文章（按空格分词）
    article = """
    Python 是一种高级编程语言 它以简洁的语法和强大的功能著称
    Python 广泛应用于数据分析 机器学习 Web开发 自动化脚本等领域
    许多开发者选择 Python 是因为它易学易用 生态丰富 社区活跃
    无论是初学者还是资深工程师 Python 都是一个优秀的选择
    """

    # 1) 分词 + 词频统计（Counter 一行搞定）
    words = article.split()
    wc = Counter(words)
    print(f"  文章总词数：{len(words)}   不同词数：{len(wc)}")

    # 2) Top10 高频词
    print()
    print("  【Top10 高频词】")
    for rank, (word, cnt) in enumerate(wc.most_common(10), 1):
        bar = "█" * cnt                      # 用方块画简易词云
        print(f"    {rank:2}. {word:8} {cnt:2}次 {bar}")

    # 3) 统计指定词的频率（缺失返回0）
    print()
    print(f"    'Python' 出现 {wc['Python']} 次")
    print(f"    'Java' 出现 {wc['Java']} 次（文章中没提到）")

    # 4) 筛选：只统计长度 > 3 的词（过滤短词）
    long_words = Counter({w: c for w, c in wc.items() if len(w) > 3})
    print()
    print(f"  【只统计长度>3的词】Top3 = {long_words.most_common(3)}")

    # 5) 统计词长分布（Counter 统计数值分布）
    len_dist = Counter(len(w) for w in words)
    print(f"  【词长分布】（词长→个数）{dict(sorted(len_dist.items()))}")

    # 6) 找出唯一出现一次的词
    once = [w for w, c in wc.items() if c == 1]
    print(f"  【只出现一次的词】共 {len(once)} 个：{once[:5]} ...")

    # 7) defaultdict：按首字母分组
    from collections import defaultdict
    by_initial: Dict[str, List[str]] = defaultdict(list)
    for w in set(words):                      # set 去重后分组
        by_initial[w[0].upper()].append(w)
    print()
    print("  【按首字母分组】（defaultdict）：")
    for initial in sorted(by_initial)[:5]:
        print(f"    {initial}: {len(by_initial[initial])} 个词 {sorted(by_initial[initial])[:3]} ...")


# ==============================================================================
# 性能对比：deque vs list 的两端操作
# ==============================================================================
# ===== 语法解析 =====
# 用 timeit 实测，证明 deque 两端操作 O(1) 优于 list 的头部操作 O(n)。
def demo_performance() -> None:
    print()
    print("=" * 60)
    print("性能对比：deque vs list")
    print("=" * 60)

    N = 100_000
    print(f"  测试规模：{N:,} 次操作")
    print()
    print("  | 操作             | list       | deque      | deque 优势 |")
    print("  |------------------|------------|------------|-----------|")

    # ★ 注意：timeit 的 setup 在独立命名空间中执行，
    #   因此每个用到 deque 的 setup 都必须自己 import，不能依赖模块顶部导入。
    setup_deque = "from collections import deque"
    setup_list = ""

    # 1) 尾部添加
    t_list_append = timeit.timeit(
        """
l = []
for _ in range(100000):
    l.append(1)
""",
        number=1,
    )
    t_deque_append = timeit.timeit(
        """
d = deque()
for _ in range(100000):
    d.append(1)
""",
        setup=setup_deque,
        number=1,
    )
    print(f"  | 尾部 append       | {t_list_append:.4f}s | {t_deque_append:.4f}s | {t_list_append / t_deque_append:>4.2f}x |")

    # 2) ★ 头部添加（list O(n) vs deque O(1)）—— 差距最大处
    t_list_linsert = timeit.timeit(
        """
l = []
for _ in range(100000):
    l.insert(0, 1)
""",
        setup=setup_list,
        number=1,
    )
    t_deque_lappend = timeit.timeit(
        """
d = deque()
for _ in range(100000):
    d.appendleft(1)
""",
        setup=setup_deque,
        number=1,
    )
    print(f"  | 头部 insert/left  | {t_list_linsert:.4f}s | {t_deque_lappend:.4f}s | {t_list_linsert / t_deque_lappend:>4.2f}x ★ |")

    # 3) 头部弹出
    t_list_popleft = timeit.timeit(
        """
l = list(range(100000))
for _ in range(100000):
    l.pop(0)
""",
        setup=setup_list,
        number=1,
    )
    t_deque_popleft = timeit.timeit(
        """
d = deque(range(100000))
for _ in range(100000):
    d.popleft()
""",
        setup=setup_deque,
        number=1,
    )
    print(f"  | 头部 pop(0)/left  | {t_list_popleft:.4f}s | {t_deque_popleft:.4f}s | {t_list_popleft / t_deque_popleft:>4.2f}x ★ |")

    # 4) 尾部弹出（两者相当）
    t_list_pop = timeit.timeit(
        """
l = list(range(100000))
for _ in range(100000):
    l.pop()
""",
        setup=setup_list,
        number=1,
    )
    t_deque_pop = timeit.timeit(
        """
d = deque(range(100000))
for _ in range(100000):
    d.pop()
""",
        setup=setup_deque,
        number=1,
    )
    print(f"  | 尾部 pop()        | {t_list_pop:.4f}s | {t_deque_pop:.4f}s | {t_list_pop / t_deque_pop:>4.2f}x |")

    print()
    print("  ★ 结论：")
    print("    · deque 头部操作（insert(0)/pop(0)）是 O(1)，list 是 O(n)，差距随规模拉大")
    print("    · 尾部操作两者基本持平（都是 O(1)）")
    print("    · 需要队列/栈/滑动窗口 → deque；仅在尾部增删 → list 也够用")

    print()
    print("  ★ 内存对比：")
    import sys
    dl = [0] * 100_000
    dd = deque([0] * 100_000)
    print(f"    list  占 {sys.getsizeof(dl) // 1024} KB")
    print(f"    deque 占 {sys.getsizeof(dd) // 1024} KB   （deque 每段 64 元素为一组，略多块开销）")


def main() -> None:
    """主函数：演示 collections 模块的五大工具类与实战。"""
    # 五大工具类基础
    demo_namedtuple()
    demo_deque()
    demo_counter()
    demo_chainmap()
    demo_ordereddict()
    # 三大实战场景
    demo_scenario_log_analysis()
    demo_scenario_task_queue()
    demo_scenario_word_count()
    # 性能对比
    demo_performance()

    print()
    print("=" * 60)
    print("小结")
    print("=" * 60)
    print("  1. namedtuple：不可变数据载体，比 dataclass 轻，比 dict 省，比类快")
    print("  2. ★ deque：两端 O(1) 操作；maxlen 自动滑动窗口；FIFO/LIFO 标准实现")
    print("  3. Counter：词频统计一行搞定，most_common 排行 + 算术运算")
    print("  4. ChainMap：多字典分层配置，左侧优先，写入只进第一层")
    print("  5. OrderedDict：3.7+ 普通 dict 也保序，但 move_to_end/popitem(last) 仍独有")
    print("  6. ★ 三大实战：日志分析(namedtuple+ChainMap+Counter)/队列(deque)/词频(Counter)")
    print("  7. deque 头部操作远快于 list（O(1) vs O(n)）；尾部操作持平")
    print("  8. 选型：不可变结构→namedtuple/具名元组；双端→deque；计数→Counter；")
    print("           分层配置→ChainMap；需重排/LRU→OrderedDict")


if __name__ == "__main__":
    main()