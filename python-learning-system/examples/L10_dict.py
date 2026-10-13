"""L10 字典：键值对与哈希表 —— 配套教案示例。

运行：python examples/L10_dict.py

本脚本演示十件事：
    1. 字典的创建与本质：哈希表，为什么比列表查找快
    2. 键必须可哈希——与 L09 的元组呼应
    3. 增删改查四种操作，以及 KeyError 与 get 的取舍
    4. 三种遍历方式：keys / values / items
    5. 遍历时修改字典会抛 RuntimeError（改【值】却可以）
    6. 字典合并：| 运算符与 {**a, **b}
    7. 嵌套字典与「点号访问」的封装
    8. defaultdict / Counter / OrderedDict 三大专用字典
    9. 字典推导式
   10. 性能对比：字典 vs 列表的查找，以及 get 默认值的隐藏成本

⚠️ 纯标准库，可直接运行。
"""

import sys                                    # 标准库：getsizeof 内存对比
import time                                   # 标准库：性能对比
from collections import Counter, OrderedDict, defaultdict   # 标准库：三种专用字典

# ============================================================
# 模块级常量
# ============================================================
PERF_SIZE = 200_000                          # 性能对比的数据规模


# ============================================================
# 第 1 部分：创建与本质
# ============================================================
def demo_create() -> None:
    """字典的创建方式与基本特征。"""
    print("【创建与本质】\n")

    # 四种创建方式
    a = {"name": "张三", "age": 20}          # 方式1：字面量（最常用）
    b = dict(name="张三", age=20)            # 方式2：dict() + 关键字参数
    c = dict([("name", "张三"), ("age", 20)]) # 方式3：从键值对序列
    d = {k: v for k, v in [("name", "张三"), ("age", 20)]}   # 方式4：推导式
    print(f"  四种方式结果一致: {a == b == c == d}")

    # 空字典的两种写法
    print(f"\n  空字典: {{}} 是 {type({}).__name__}, dict() 是 {type(dict()).__name__}")
    print(f"  ⚠️ 区别：{{}} 是【空字典】，而 set() 才是空集合——{{}} 不是空集合！")

    # ⭐ 本质：字典是「哈希表」
    print("\n  ⭐ 字典的本质是哈希表：")
    print("    存进去时：key → hash(key) → 算出一个下标 → 存进对应位置")
    print("    取出来时：key → hash(key) → 算出同一个下标 → 直接定位")
    print("    所以查询是 O(1)：不需要和任何其他元素比较，算一次哈希就定位了。")
    print("    对比列表：列表只能从头一个个比，所以查询是 O(n)。")

    # 用 sys.getsizeof 直观感受
    d_small = {"a": 1, "b": 2, "c": 3}
    print(f"\n  3 个键的字典占: {sys.getsizeof(d_small)} 字节")
    print(f"  元组版本     占: {sys.getsizeof(('a', 'b', 'c'))} 字节")
    print(f"  列表版本     占: {sys.getsizeof(['a', 'b', 'c'])} 字节")
    print("  字典要为「哈希表结构」额外花空间（哈希表头 + 稀疏索引），这是查询快的代价。")


# ============================================================
# 第 2 部分：键必须可哈希
# ============================================================
def demo_hashable_keys() -> None:
    """字典的键必须可哈希，这是 L09 元组知识的直接应用。"""
    print("\n【键必须可哈希】\n")

    # 可哈希的键
    ok_keys = [
        ("字符串 'name'", "name"),
        ("整数 42", 42),
        ("元组 (1, 2)", (1, 2)),
        ("布尔 True", True),
        ("None", None),
        ("frozenset", frozenset({1, 2})),
    ]
    for name, key in ok_keys:
        print(f"  ✅ {name:<16} hash={hash(key)}")

    # 不可哈希的键
    print()
    bad_keys = [("列表 [1]", [1]), ("字典 {}", {}), ("集合 {1}", {1})]
    for name, key in bad_keys:
        try:
            _ = {key: "v"}
        except TypeError as exc:
            print(f"  ❌ {name:<16} {exc}")

    # ⭐ 呼应 L09：元组「含列表元素」也不能当键
    print("\n  ⭐ 呼应 L09：元组本身可哈希，但含列表元素的元组不可哈希：")
    print(f"     hash((1, 2))   = {hash((1, 2))}   ✅")
    try:
        hash(([1], 2))
    except TypeError as exc:
        print(f"     hash(([1], 2)) → {exc}   ⚠️ 元组可哈希 ⟺ 每个元素都可哈希")

    # ⚠️ 相等与哈希必须一致（字典的正确性依赖这一点）
    print("\n  ⚠️ 为什么键必须不可变：如果你能在放进哈希表后改掉键，")
    print("     它的哈希值就变了，原来的位置再也找不到 → 这条记录就「丢了」。")
    print("     所以字典要求：hash(key) 相等 ⟺ key 相等（哈希一致性）")


# ============================================================
# 第 3 部分：增删改查
# ============================================================
def demo_crud() -> None:
    """字典的增删改查，以及 KeyError 与 get 的取舍。"""
    print("\n【增删改查】\n")

    d = {"a": 1, "b": 2}

    # 增：新增键、新增键并保留旧键
    d["c"] = 3                                # 新增
    d.update({"a": 10, "d": 4})               # 批量：有则更新，无则新增
    print(f"  增后: {d}")

    # 改：就是赋值（键存在时）
    d["a"] = 100
    print(f"  改后: {d}")

    # 删：三种写法
    tmp = d.copy()
    del tmp["a"]                              # 方式1：del（不存在会 KeyError）
    tmp.pop("b")                              # 方式2：pop（不存在会 KeyError）
    gone = tmp.pop("zzz", None)               # 方式3：pop 带默认值（安全）
    print(f"  删后: {tmp}   不存在的键 pop 返回: {gone!r}")

    # 查：三种写法
    print(f"\n  d['a']      = {d['a']}      直接下标——不存在会 KeyError")
    print(f"  d.get('a')  = {d.get('a')}    安全返回")
    print(f"  d.get('zz') = {d.get('zz')!r}   不存在返回 None")
    print(f"  d.get('zz', 0) = {d.get('zz', 0)}  不存在返回指定默认值")

    # ⚠️ 下标查找不到 = KeyError
    try:
        _ = d["不存在的键"]
    except KeyError as exc:
        print(f"\n  ⚠️ d['不存在的键'] → KeyError: {exc}   （用 repr 看才看得到引号）")

    # 三个「成员/查询」方法
    print("\n  查询相关方法：")
    print(f"    'a' in d      = {'a' in d}      键是否存在（O(1)）")
    print(f"    len(d)        = {len(d)}        键的个数")
    print(f"    list(d.keys()) = {list(d.keys())}")
    print(f"    list(d.values())[:3] = {list(d.values())[:3]}   ⚠️ 值可能重复，list 不去重")
    print(f"    d.get('a', '默认') = {d.get('a', '默认')}   键存在时默认值【不会】被返回")


# ============================================================
# 第 4、5 部分：遍历与遍历时修改
# ============================================================
def demo_traverse() -> None:
    """三种遍历方式，以及遍历时修改字典的 RuntimeError。"""
    print("\n【遍历方式】\n")

    d = {"苹果": 3, "香蕉": 5, "橙子": 2}

    # 方式1：只遍历键（默认）
    print(f"  for k in d            → {list(d)}")
    # 方式2：只遍历值
    print(f"  for v in d.values()   → {list(d.values())}")
    # 方式3：遍历键值对（最常用）
    print(f"  for k, v in d.items() → {[(k, v) for k, v in d.items()]}")

    # ⭐ items() 遍历时还可以用元组解包
    print("\n  items() 返回的是【视图对象】，不是列表：")
    items_view = d.items()
    print(f"    type(d.items()) = {type(items_view).__name__}")
    print(f"    视图是「动态」的：反射性——它反映字典的【当前】内容")
    print(f"    d 现在有 {len(d)} 个键，视图也有 {len(d.keys())} 个")
    print(f"    视图支持 in：'苹果' in d.items() → {'苹果' in d.items()}  （按整对判断）")

    # items() 比 keys() + 查值更快
    print("\n  ⭐ 性能对比：items() vs keys() 反复查值")
    big = {f"k{i}": i for i in range(50_000)}
    t0 = time.perf_counter()
    for _ in range(20):
        total = 0
        for k in big:
            total += big[k]                  # 每个键都要再查一次
    t1 = time.perf_counter()
    for _ in range(20):
        total = 0
        for _k, v in big.items():           # 值直接给到，不用再查
            total += v
    t2 = time.perf_counter()
    print(f"    keys() + 查值: {(t1 - t0) * 1000:.1f} ms")
    print(f"    items()      : {(t2 - t1) * 1000:.1f} ms   ✅ 少了一半以上的哈希查询")

    # ⚠️⚠️ 遍历时改变字典【大小】会抛 RuntimeError
    print("\n  实测【遍历时新增键】：")
    target = {"a": 1, "b": 2}
    try:
        for k in target:
            target[k + "_x"] = 0
    except RuntimeError as exc:
        print(f"    ❌ RuntimeError: {exc}")

    print("\n  实测【遍历时删除键】：")
    target2 = {"a": 1, "b": 2}
    try:
        for k in target2:
            del target2[k]
    except RuntimeError as exc:
        print(f"    ❌ RuntimeError: {exc}")

    print("\n  ⚠️ 但【只改值、不加不减】是安全的：")
    target3 = {"a": 1, "b": 2}
    for k in target3:
        target3[k] = 99                      # 只改值，大小没变
    print(f"    ✅ 改值后: {target3}")

    print("\n  ✅ 正确写法一：遍历键的副本（list(t) 是键的快照）")
    t4 = {"a": 1, "b": 2, "c": 3}
    for k in list(t4):
        if t4[k] < 3:
            del t4[k]
    print(f"    删掉值 < 3 的 → {t4}   （a=1 和 b=2 都被删了，只剩 c=3）")

    print("\n  ✅ 正确写法二：字典推导式重建（推荐：不改原字典）")
    src = {"a": 1, "b": 2, "c": 3}
    t5 = {k: v for k, v in src.items() if v >= 2}
    print(f"    保留值 >= 2 的 → {t5}，原字典仍是 {src} ✅")


# ============================================================
# 第 6 部分：字典合并
# ============================================================
def demo_merge() -> None:
    """两种字典合并方式。"""
    print("\n【字典合并】\n")

    a = {"x": 1, "y": 2}
    b = {"y": 20, "z": 3}

    # 方式1：| 运算符（Python 3.9+）
    merged = a | b
    print(f"  a = {a}")
    print(f"  b = {b}")
    print(f"  a | b = {merged}      ⚠️ 右边同名的键覆盖左边")
    print(f"  a 本身没变: {a}   ✅ | 返回新字典")

    # 方式2：{**a, **b}
    print(f"  {{**a, **b}} = { {**a, **b} }")

    # 原地合并
    c = a.copy()
    c |= b                                     # 原地合并（3.9+）
    print(f"  c |= b 后 c = {c}   （| 是新对象，|= 是原地）")

    # ⚠️ 不能用 + 号
    try:
        _ = a + b
    except TypeError as exc:
        print(f"\n  ⚠️ a + b → TypeError: {exc}   （字典不支持 +）")

    # ⚠️ update 会原地修改，且返回值是 None
    d = {"x": 1}
    result = d.update({"z": 9})
    print(f"  d.update({{'z': 9}}) 返回 {result!r}，d 变成 {d}")
    print(f"  ⚠️ 所以 x = d.update(...) 一定错：更新生效了，但 x 是 None")


# ============================================================
# 第 7 部分：嵌套字典
# ============================================================
def demo_nested() -> None:
    """嵌套字典的访问与「安全取值」的层层调用。"""
    print("\n【嵌套字典】\n")

    config = {
        "db": {"host": "localhost", "port": 5432},
        "app": {"name": "myapp", "debug": True},
    }

    print(f"  config['db']['host'] = {config['db']['host']}")
    print(f"  config['db']['port'] = {config['db']['port']}")

    # ⚠️ 逐层 get 会很啰嗦，而且中间层缺失就断了
    print(f"\n  config.get('cache', {{}}).get('host', '默认') = "
          f"{config.get('cache', {}).get('host', '默认')}   ⚠️ 每个 {{}} 都要新建")

    # ✅ 实战：用循环下钻，避免写一堆重复的 .get()
    def deep_get(data: dict, path: str, default: object = None) -> object:
        """按 'a.b.c' 形式的路径安全取值。"""
        current: object = data
        for key in path.split("."):
            if not isinstance(current, dict) or key not in current:
                return default              # 任何一层断了就返回默认值
            current = current[key]
        return current

    print(f"  deep_get(config, 'db.host')      = {deep_get(config, 'db.host')}")
    print(f"  deep_get(config, 'cache.host')   = {deep_get(config, 'cache.host')!r}   "
          f"（中间层不存在，安全）")
    print(f"  deep_get(config, 'db.port', 0)   = {deep_get(config, 'db.port', 0)}")


# ============================================================
# 第 8 部分：三大专用字典
# ============================================================
def demo_special_dicts() -> None:
    """defaultdict / Counter / OrderedDict。"""
    print("\n【三大专用字典】\n")

    # defaultdict：访问不存在的键时自动创建默认值
    print("  【defaultdict】—— 自动按类型创建默认值")
    dd = defaultdict(list)
    dd["苹果"].append(3)                     # 不用先判断键是否存在
    dd["香蕉"].append(5)
    dd["苹果"].append(2)
    print(f"    dd = {dict(dd)}")
    print(f"    default_factory = {dd.default_factory.__name__}")

    # 对比普通字典的写法
    print("\n    对比普通字典（同样的操作要写 4 行）：")
    plain = {}
    for item, price in [("苹果", 3), ("香蕉", 5), ("苹果", 2)]:
        if item not in plain:
            plain[item] = 0
        plain[item] += price
    print(f"    plain = {plain}")
    print("    defaultdict 用一行就完成了「不存在就建、然后累加」")

    # ⚠️ defaultdict 的陷阱：访问一个不存在的键会「凭空创建」它
    print("\n  ⚠️ defaultdict 的陷阱：")
    trap = defaultdict(list)
    print(f"    访问 trap['从未出现过的键'] → {trap['从未出现过的键']}")
    print(f"    结果字典变成了: {dict(trap)}   ⚠️ 只是【读】了一下，字典却被污染了！")
    print(f"    所以：只在「确定要写入」的场景用 defaultdict，谨慎用 .get() 读取。")

    # Counter：专��计数
    print("\n  【Counter】—— 专门做计数")
    words = ["apple", "banana", "apple", "orange", "banana", "apple"]
    counter = Counter(words)
    print(f"    Counter({words[:3]}...) = {dict(counter)}")
    print(f"    counter['apple'] = {counter['apple']}   不存在的键返回 0，不报错！")
    print(f"    counter.most_common(2) = {counter.most_common(2)}   最常见的 2 个")
    print(f"    sum(counter.values()) = {sum(counter.values())}   总数")

    # 手写计数 vs Counter
    print("\n    对比：手写计数要 6 行，Counter 一行")
    manual: dict[str, int] = {}
    for w in words:
        manual[w] = manual.get(w, 0) + 1
    print(f"    手写结果 {manual}")
    print(f"    Counter 结果 {dict(counter)}   一致: {manual == dict(counter)}")

    # OrderedDict：现在普通 dict 已经有序了
    print("\n  【OrderedDict】—— ⚠️ 3.7+ 后普通 dict 已经【保持插入顺序】了")
    print(f"    普通 dict:  {list({'b': 1, 'a': 2, 'c': 3})}   也是插入顺序！")
    od = OrderedDict([("b", 1), ("a", 2), ("c", 3)])
    print(f"    OrderedDict: {list(od)}")
    print(f"    两者顺序一致: {list(od) == list({'b': 1, 'a': 2, 'c': 3})}")
    print("\n    但 OrderedDict 仍有两个独有能力：")
    od2 = OrderedDict([("a", 1), ("b", 2), ("c", 3)])
    od2.move_to_end("a")                       # 把 a 移到末尾
    print(f"      move_to_end('a')：{list(od2)}   （a 被移到最后）")

    od3 = OrderedDict([("a", 1), ("b", 2)])
    popped = od3.popitem(last=False)           # 弹出【第一个】
    print(f"      popitem(last=False)：弹出 {popped}，剩下 {dict(od3)}")
    print(f"      ⚠️ 而普通 dict 的 popitem() 只能弹出最后一个（LIFO 语义）。")


# ============================================================
# 第 9 部分：字典推导式
# ============================================================
def demo_comprehension() -> None:
    """字典推导式是处理「转换 + 过滤」的最短路径。"""
    print("\n【字典推导式】\n")

    words = ["apple", "banana", "cherry", "date"]

    # 基本形式：{k: v for ...}
    lengths = {w: len(w) for w in words}
    print(f"  {{w: len(w) for w in words}} = {lengths}")

    # 带条件过滤
    long_only = {w: len(w) for w in words if len(w) > 5}
    print(f"  带 if 过滤 → {long_only}")

    # 从已有字典转换（键值互换）
    scores = {"张三": 88, "李四": 92, "王五": 79}
    inverted = {v: k for k, v in scores.items()}
    print(f"  键值互换 → {inverted}   （分数 → 姓名）")

    # 从两个平行列表构建
    names = ["张三", "李四", "王五"]
    nums = [88, 92, 79]
    table = {n: s for n, s in zip(names, nums)}
    print(f"  zip 构建 → {table}")

    # 带条件转换
    passed = {k: ("及格" if v >= 85 else "不及格") for k, v in scores.items()}
    print(f"  值带条件 → {passed}")

    # 计数：dict 推导式也能做
    counts: dict[str, int] = {}
    for w in ["a", "b", "a", "c", "b", "a"]:
        counts[w] = counts.get(w, 0) + 1
    print(f"\n  手写计数（用 .get）：{counts}")
    print(f"  但用 Counter 更短: {dict(Counter(['a', 'b', 'a', 'c', 'b', 'a']))}")


# ============================================================
# 第 10 部分：性能对比与 get 的隐藏成本
# ============================================================
def demo_perf() -> None:
    """字典 O(1) vs 列表 O(n)，以及 get 默认值总是被求值。"""
    print("\n【性能对比】\n")

    # 字典 vs 列表查找
    size = PERF_SIZE
    target = "key_199999"

    big_dict = {f"key_{i}": i for i in range(size)}
    big_list = [f"key_{i}" for i in range(size)]

    t0 = time.perf_counter()
    for _ in range(1000):
        _ = target in big_dict              # O(1)
    t1 = time.perf_counter()
    for _ in range(1000):
        _ = target in big_list              # O(n)，最坏要扫 20 万个
    t2 = time.perf_counter()

    print(f"  在 {size:,} 个元素里查找 {target}，各 1000 次：")
    print(f"    字典 in: {(t1 - t0) * 1000:.2f} ms   O(1)")
    print(f"    列表 in: {(t2 - t1) * 1000:.2f} ms   O(n)  ⚠️ 慢 {(t2 - t1) / max(t1 - t0, 1e-9):.0f} 倍")

    # 增长曲线：证明字典是常数，列表是线性
    print("\n  ⭐ 数据量翻倍时，两者耗时如何变化：")
    prev_d = prev_l = 0.0
    for n in (50_000, 100_000, 200_000, 400_000):
        bd = {f"k{i}": i for i in range(n)}
        bl = [f"k{i}" for i in range(n)]
        tgt = f"k{n - 1}"
        t0 = time.perf_counter()
        for _ in range(200):
            _ = tgt in bd
        t1 = time.perf_counter()
        for _ in range(200):
            _ = tgt in bl
        t2 = time.perf_counter()
        d_ratio = f"{(t1 - t0) / prev_d:.2f}×" if prev_d > 0 else "—"
        l_ratio = f"{(t2 - t1) / prev_l:.2f}×" if prev_l > 0 else "—"
        print(f"    n={n:>7,}:  字典 {(t1 - t0) * 1000:7.2f} ms（{d_ratio}）"
              f"   列表 {(t2 - t1) * 1000:7.2f} ms（{l_ratio}）")
        prev_d = t1 - t0
        prev_l = t2 - t1
    print("    → 数据量每翻倍，字典耗时【基本不变】，列表耗时【约翻倍】")

    # ⚠️ get 的默认值总会被求值
    print("\n  ⚠️⚠️ get 的隐藏成本：默认值表达式【总是】被求值")
    calls: list[int] = []

    def expensive_default() -> int:
        """模拟一个「很贵」的默认值计算。"""
        calls.append(1)
        return 0

    d = {"present": 1}
    calls.clear()
    _ = d.get("present", expensive_default())
    print(f"    键【存在】时，expensive() 被调用 {len(calls)} 次   "
          f"⚠️ 白算了，但结果被丢弃")

    calls.clear()
    _ = d.get("absent", expensive_default())
    print(f"    键【不存在】时，expensive() 被调用 {len(calls)} 次   （这时才需要）")
    print("    原因：Python 先【求值实参】再调用 get，所以默认值无论如何都会算一遍。")

    # ✅ 正确写法：只在真的缺失时才计算
    calls.clear()
    value = d.get("absent")
    if value is None:
        value = expensive_default()
    print(f"    ✅ 先 get 再判断：expensive() 被调用 {len(calls)} 次   "
          f"（键存在时一次都不调）")


# ============================================================
# 第 11 部分：自检断言
# ============================================================
def verify_dict() -> None:
    """用断言验证本课所有关键结论，防止示例与文档说法不一致。"""
    print("【自检断言】")

    # 创建与基本操作
    d = {"a": 1, "b": 2}
    d["c"] = 3
    assert d == {"a": 1, "b": 2, "c": 3}
    d.update({"a": 10, "d": 4})
    assert d["a"] == 10 and d["d"] == 4
    assert d.get("zzz") is None
    assert d.get("zzz", 0) == 0
    assert "a" in d and "zzz" not in d
    assert len(d) == 4
    assert isinstance({}, dict) and {} != set()

    # KeyError
    try:
        _ = d["不存在"]
        raise AssertionError("应该抛 KeyError")
    except KeyError:
        pass

    # pop / del
    tmp = d.copy()
    del tmp["a"]
    assert tmp.pop("b") == 2
    assert tmp.pop("zzz", "默认") == "默认"

    # 遍历
    d2 = {"x": 1, "y": 2}
    assert list(d2) == ["x", "y"]
    assert list(d2.keys()) == ["x", "y"]
    assert list(d2.values()) == [1, 2]
    assert list(d2.items()) == [("x", 1), ("y", 2)]
    assert ("x", 1) in d2.items()            # items() 按整对判断

    # ⚠️ 遍历时改变大小会报错
    for change in (lambda t: t.update({"new": 1}), lambda t: t.pop("x")):
        t = {"x": 1, "y": 2}
        try:
            for _k in t:
                change(t)
            raise AssertionError("遍历时改大小居然没报错")
        except RuntimeError:
            pass
    # 但改值是安全的
    t = {"x": 1, "y": 2}
    for k in t:
        t[k] = 99
    assert t == {"x": 99, "y": 99}

    # 遍历副本的正确写法：⚠️ 条件 < 3 会删掉 a(1) 和 b(2)，只剩 c(3)
    t = {"a": 1, "b": 2, "c": 3}
    for k in list(t):
        if t[k] < 3:
            del t[k]
    assert t == {"c": 3}

    # 推导式版本：同样的过滤，但结果一致且不动原字典
    src = {"a": 1, "b": 2, "c": 3}
    assert {k: v for k, v in src.items() if v >= 2} == {"b": 2, "c": 3}
    assert src == {"a": 1, "b": 2, "c": 3}          # 原字典未被修改

    # 合并
    a, b = {"x": 1, "y": 2}, {"y": 20, "z": 3}
    assert (a | b) == {"x": 1, "y": 20, "z": 3}   # 右边覆盖左边
    assert a == {"x": 1, "y": 2}                    # 原字典不变
    assert ({**a, **b}) == (a | b)
    c = a.copy()
    c |= b
    assert c == {"x": 1, "y": 20, "z": 3}
    assert a.update({"q": 1}) is None               # update 返回 None

    # 键必须可哈希
    assert {1: "a", "b": 2, (3, 4): 5, None: 6, True: 7}
    try:
        {[1]: "a"}
        raise AssertionError("列表竟然能当键")
    except TypeError:
        pass
    try:
        hash(([1], 2))
        raise AssertionError("含列表的元组竟然可哈希")
    except TypeError:
        pass

    # 专用字典
    dd = defaultdict(list)
    dd["k"].append(1)
    assert dd == {"k": [1]} and dd.default_factory is list
    trap = defaultdict(int)
    _ = trap["从未访问"]                         # 只读也会创建
    assert "从未访问" in trap                    # 确认这个陷阱

    cnt = Counter("aabbbcc")
    assert cnt["a"] == 2 and cnt["x"] == 0       # 不存在的键返回 0
    assert cnt.most_common(1) == [("b", 3)]
    assert sum(cnt.values()) == 7

    od = OrderedDict([("a", 1), ("b", 2)])
    od.move_to_end("a")                       # → [("b", 2), ("a", 1)]
    assert list(od) == ["b", "a"]
    # ⚠️ popitem(last=False) 弹出的是【当前第一个】，即 ("b", 2) 而不是 ("b", 1)
    assert od.popitem(last=False) == ("b", 2)

    # 普通 dict 也是插入有序的（3.7+）
    assert list({"b": 1, "a": 2}) == ["b", "a"]

    # 字典推导式
    words = ["ab", "cde", "fghi"]
    assert {w: len(w) for w in words} == {"ab": 2, "cde": 3, "fghi": 4}
    assert {v: k for k, v in {"a": 1}.items()} == {1: "a"}

    # ⚠️ get 的默认值总会被求值
    calls: list[int] = []
    probe = {"present": 1}

    def expensive() -> int:
        calls.append(1)
        return 0

    _ = probe.get("present", expensive())
    assert len(calls) == 1                      # ⚠️ 键存在也算了一次

    print("✅ verify_dict 全部断言通过")


# ============================================================
# 程序入口
# ============================================================
def main() -> None:
    """按教学顺序调用全部演示函数。"""
    print("=" * 64)
    print("L10 · 字典：键值对与哈希表")
    print("=" * 64)
    demo_create()
    demo_hashable_keys()
    demo_crud()
    demo_traverse()
    demo_merge()
    demo_nested()
    demo_special_dicts()
    demo_comprehension()
    demo_perf()
    print("\n" + "-" * 64)
    verify_dict()
    print("\n🎉 L10 演示结束")


# 标准入口约定：直接运行本文件执行 main()，被 import 时不执行
if __name__ == "__main__":
    main()