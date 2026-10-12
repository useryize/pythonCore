"""
================================================================================
  04_dict.py  ——  字典：键值映射与有序性保证
================================================================================

【演示的语法点】
 1. 字典创建、增删改查的完整 API（含 get/setdefault/pop/popitem/update）
 2. ★ get / setdefault / defaultdict 三种「默认值」方案对比
 3. ★ 遍历方式对比：items / keys / values、for + in、enumerate、列表推导
 4. ★ Python 3.7+ 的有序性保证（insertion order）与 del 的顺序影响
 5. defaultdict：自动创建缺失键的容器
 6. Counter：计数字典的专用工具
 7. OrderedDict：显式排序与 move_to_end 的历史价值（3.7+ 已可被普通 dict 替代）
 8. ★ 嵌套 dict 实战：JSON 风格的数据处理与聚合统计
 9. 字典视图（view）的动态特性与运算符
10. 字典合并 `|` 与展开 `{**a, **b}`
11. 键必须是可哈希对象、可变对象不能作键
12. defaultdict 的 factory 选择（list/set/int/str）

【预期输出摘要】
 - "遍历" 小节打印 4 种遍历方式与它们的行为差异
 - "有序性" 小节证明插入顺序决定遍历顺序
 - "聚合统计" 小节用 defaultdict 完成多级嵌套数据的分组计数
 - "Counter" 小节打印词频统计与 most_common 排行
================================================================================

"""

from __future__ import annotations

import copy
import timeit
from collections import Counter, OrderedDict, defaultdict
from typing import Any, DefaultDict, Dict, List


# ===== 语法解析 =====
# 【1】字典的增删改查完整 API
#   语法规则：d[key] = value 要求 key 可哈希；d[key] 缺失时抛 KeyError。
#   设计意图：用【键 → 值】的映射表达"稀疏数据"，避免线性查找。
def demo_basics() -> None:
    print("=" * 60)
    print("【1】字典的增删改查完整 API")
    print("=" * 60)

    # 创建
    d1 = {"name": "张三", "age": 20}       # 字面量
    d2 = dict(name="李四", age=18)         # dict() 关键字参数
    d3 = dict([("a", 1), ("b", 2)])        # 由键值对序列创建
    d4 = {k: v for k, v in [("x", 1), ("y", 2)]}  # 字典推导式
    empty: Dict[str, Any] = {}             # 空字典
    print(f"  字面量      {d1}")
    print(f"  dict(k=)    {d2}")
    print(f"  dict(键值对) {d3}")
    print(f"  字典推导式   {d4}")
    print(f"  空字典      {empty}   len={len(empty)}")

    # 增
    print()
    print("  【增】")
    d = {"a": 1}
    d["b"] = 2                             # 新增（键不存在则创建）
    d.update({"c": 3, "a": 99})            # 批量新增/覆盖；已存在的键被覆盖
    d.setdefault("d", 4)                   # 键不存在才设值，返回值 = 现有或新设的值
    print(f"    d = {d}")
    print(f"    setdefault 返回 = {d.setdefault('e', 5)}  （新增并返回 5）")
    print(f"    setdefault 已有键返回 = {d.setdefault('a', 777)}  （不覆盖，返回 99）")

    # 改
    print()
    print("  【改】")
    d = {"a": 1, "b": 2}
    d["a"] = 100                           # 直接赋值覆盖
    d["b"] += 1                            # 读-改-写
    print(f"    d['a']=100, d['b']+=1 → {d}")
    print(f"    两个字典合并 {{**d1, **d2}}：")
    print(f"      { {**{'a': 1}, **{'b': 2}} }   （展开，后面的键优先）")
    print(f"      或 dict1 | dict2（3.9+）：{ {'a': 1} | {'b': 2} }")

    # 查
    print()
    print("  【查】")
    d = {"a": 1, "b": 2}
    print(f"    d['a']       = {d['a']}    ← 缺失抛 KeyError")
    print(f"    d.get('z')   = {d.get('z')}   ← 缺失返回 None（默认值）")
    print(f"    d.get('z', 0)= {d.get('z', 0)}   ← 缺失返回指定默认值")
    print(f"    'a' in d     = {'a' in d}   （成员判断查的是【键】）")
    print(f"    len(d)       = {len(d)}")
    try:
        d["z"]                            # 访问不存在的键
    except KeyError as exc:
        print(f"    ★ d['z'] → KeyError: {exc}")

    # 删
    print()
    print("  【删】")
    d = {"a": 1, "b": 2, "c": 3}
    v = d.pop("b")                         # 删除并返回值的键；缺失会 KeyError（可给默认）
    print(f"    pop('b') = {v} → {d}")
    v2 = d.pop("zz", "默认值")              # 缺失时返回第二个参数
    print(f"    pop('zz', '默认值') = {v2}（不抛异常）")
    last_key, last_val = d.popitem()       # 删除并返回最后一个（键, 值）对
    print(f"    popitem() = {last_key},{last_val} → {d}")
    del d["a"]                             # del 语句删除键，不返回
    print(f"    del d['a'] → {d}")
    d.clear()                              # 清空字典
    print(f"    clear() → {d}  len={len(d)}")


# ===== 语法解析 =====
# 【2】★ get / setdefault / defaultdict：三种默认值方案
#   get(k, d)          —— 缺失时返回默认值，不修改字典（最常用）
#   setdefault(k, d)   —— 缺失时【写入】默认值并返回（用于惰性初始化）
#   defaultdict(f)      —— 缺失时自动用工厂 f() 创建默认值（最简洁）
#   设计意图：把「键不存在」这一高频分支简化，避免重复的 if 判断。
def demo_default_values() -> None:
    print()
    print("=" * 60)
    print("【2】★ get / setdefault / defaultdict 三种默认值方案")
    print("=" * 60)

    # 1. get：只读，不改字典
    d = {"a": 1}
    print(f"  get 缺失返回默认：d.get('b', 0) = {d.get('b', 0)}")
    print(f"  ★ get 不修改字典：d = {d}")

    # 2. setdefault：缺失时写入
    d2 = {"a": 1}
    r = d2.setdefault("b", [])
    r.append(10)                           # 返回的是字典里那个列表的引用，可直接改
    print(f"  setdefault 返回列表并可写：d2 = {d2}")

    # 3. defaultdict：缺失自动建
    dd: DefaultDict[str, List[int]] = defaultdict(list)
    dd["x"].append(1)                      # 键不存在 → 自动 dd["x"] = []
    dd["x"].append(2)
    print(f"  defaultdict(list)：dd = {dict(dd)}")

    print()
    print("  ★ 三者对比表：")
    print("  | 方案         | 缺失时行为       | 是否修改字典 | 适用场景         |")
    print("  |--------------|------------------|--------------|------------------|")
    print("  | get(k,d)     | 返回 d           | 否           | 纯查询           |")
    print("  | setdefault   | 写入 d 并返回    | 是           | 惰性初始化       |")
    print("  | defaultdict  | 自动建工厂对象   | 是           | 聚合/分组统计    |")

    print()
    print("  ★ defaultdict 的工厂函数选择：")
    print(f"    defaultdict(list)  → {dict(defaultdict(list, {'a': [1]}))}   收集成列表")
    print(f"    defaultdict(set)   → {dict(defaultdict(set, {'a': {1}}))}   收集成集合（去重）")
    print(f"    defaultdict(int)   → {dict(defaultdict(int, {'a': 5}))}   计数累加（默认0）")
    print(f"    defaultdict(str)   → {dict(defaultdict(str, {'a': 'x'}))}   默认空串")
    print(f"    defaultdict(float) → {dict(defaultdict(float, {'a': 1.5}))}   默认 0.0")

    print()
    print("  ★ Counter 本质就是一个『默认值为 0 的计数器』的 defaultdict(int) 特化：")
    c = Counter("aabbc")
    print(f"    Counter('aabbc') = {dict(c)}   （比手写 defaultdict(int) 更简洁且支持排行）")


# ===== 语法解析 =====
# 【3】★ 遍历方式对比
#   语法规则：
#     - d.items()   同时遍历键和值（最常用）
#     - d.keys() / d.values() 分别只遍历键 / 值
#     - for k in d 等价于 for k in d.keys()
#   设计意图：视图对象（view）是【动态】的 —— 遍历中修改字典会 RuntimeError。
def demo_iteration() -> None:
    print()
    print("=" * 60)
    print("【3】★ 字典遍历方式对比")
    print("=" * 60)

    d = {"name": "张三", "age": 20, "city": "北京"}

    print(f"  原字典 {d}")
    print()
    print("  方式1：items() 同时取键值（推荐）：")
    for k, v in d.items():
        print(f"    {k} = {v}")

    print()
    print("  方式2：keys() / values()：")
    for k in d.keys():
        print(f"    key: {k}")
    for v in d.values():
        print(f"    value: {v}")

    print()
    print("  方式3：for k in d（等价 keys()，最简洁）：")
    for k in d:
        print(f"    {k}")

    print()
    print("  方式4：enumerate() 给键编号（转成列表后）：")
    for idx, (k, v) in enumerate(d.items(), 1):
        print(f"    {idx}. {k}={v}")

    print()
    print("  方式5：字典推导式（构建新字典）：")
    upper = {k.upper(): v for k, v in d.items()}   # 键大写
    print(f"    {{k.upper(): v}} = {upper}")

    print()
    print("  ★ 注意：视图是【动态引用】的，遍历时改字典会报错：")
    d2 = {"a": 1, "b": 2}
    try:
        for k in d2:
            d2["c"] = 3                      # 遍历中新增 → RuntimeError
    except RuntimeError as exc:
        print(f"    RuntimeError: {exc}   ← 需要先 keys() 取快照再遍历")

    print()
    print("  ★ 正确做法（先转 list 快照）：")
    d3 = {"a": 1}
    for k in list(d3.keys()):                # list() 快照，允许中途修改
        d3[k.upper()] = d3[k]
    print(f"    遍历中安全修改 → {d3}")

    print()
    print("  ★ 按值排序遍历（dict 无 sort，按键或按值都要先转）：")
    scores = {"张三": 88, "李四": 95, "王五": 72}
    ranked = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)  # 按值降序
    print(f"    按分数降序：{ranked}")
    print(f"    最高分：{max(scores, key=scores.get)}   ← max/min + key")


# ===== 语法解析 =====
# 【4】★ Python 3.7+ 的有序性保证
#   语法规则：PEP 468（3.6 实现）→ PEP 468/语言规范（3.7 正式保证）：
#             字典【保持插入顺序】。
#   设计意图：从依赖 OrderedDict 到直接用 dict，简化代码。
#   注意：顺序指「插入顺序」，不是排序；删除再插入会改变位置。
def demo_ordering() -> None:
    print()
    print("=" * 60)
    print("【4】★ Python 3.7+ 字典有序性保证")
    print("=" * 60)

    d = {}
    for word in ["z", "a", "m", "b"]:
        d[word] = ord(word)                  # 按插入顺序赋值
    print(f"  按序插入 z,a,m,b → 遍历顺序 {list(d.keys())}")
    print("  ★ 字典保持【插入顺序】，不是字母序也不是哈希序（3.7+ 语言规范保证）")

    print()
    print("  ★ 删除后重新插入会移到【末尾】：")
    d2 = {"a": 1, "b": 2, "c": 3}
    del d2["b"]                              # 删除 b
    d2["b"] = 99                            # 再插入 b
    print(f"    del b 后再 b=99 → 顺序 {list(d2.keys())}")
    print("    ★ 'b' 跑到了末尾 —— 顺序是『当前插入顺序』，删除腾出的位置不复用。")

    print()
    print("  ★ 更新已有键【不改变】位置：")
    d3 = {"a": 1, "b": 2}
    d3["a"] = 100                           # 覆盖 a 的值
    print(f"    d['a']=100 → 顺序 {list(d3.keys())}   （a 仍在首位）")

    print()
    print("  ★ OrderedDict：3.7+ 前用于显式排序，现在主要价值是 move_to_end 和相等性：")
    od = OrderedDict([("z", 1), ("a", 2), ("m", 3)])
    od.move_to_end("z")                     # 把 z 移到末尾（普通 dict 没有此功能）
    print(f"    move_to_end('z') → {list(od.keys())}")
    print(f"    普通 dict 无 move_to_end：{hasattr({}, 'move_to_end')}   ← False")
    print(f"    但 OrderedDict 支持按顺序 popitem(last=False) 从头弹出：")
    od2 = OrderedDict([("first", 1), ("second", 2)])
    print(f"      popitem(last=False) = {od2.popitem(last=False)}")


# ===== 语法解析 =====
# 【5】Counter：计数字典
#   语法：Counter(可迭代) 直接统计元素出现次数，返回 {元素: 次数}。
#   设计意图：把"计数"这一高频模式内置，支持 most_common 排行。
#   常用方法：most_common(n)、elements()、total()、update()、减法。
def demo_counter() -> None:
    print()
    print("=" * 60)
    print("【5】Counter：计数字典")
    print("=" * 60)

    text = "hello world hello python world hello"
    c = Counter(text)                        # 统计每个字符出现次数
    print(f"  Counter('hello world...') = {dict(c)}")

    words = ["python", "java", "python", "go", "java", "python"]
    wc = Counter(words)                      # 统计单词词频
    print()
    print(f"  单词词频 {dict(wc)}")
    print(f"  most_common(2) 前两名：{wc.most_common(2)}   ★ 排行榜核心功能")
    print(f"  most_common(1) 最高频  ：{wc.most_common(1)[0][0]}")
    print(f"  'python' 出现次数：{wc['python']}  （缺失键返回 0，不抛异常）")
    print(f"  'rust' 出现次数：{wc['rust']}    ← Counter 缺失键默认 0")

    print()
    print("  ★ Counter 支持【算术】运算（按元素加减次数）：")
    c1 = Counter("aab")
    c2 = Counter("abc")
    print(f"    Counter('aab') = {dict(c1)}")
    print(f"    Counter('abc') = {dict(c2)}")
    print(f"    加法(+) 取最大次数：{dict(c1 + c2)}")
    print(f"    减法(-) 只保留正数：{dict(c1 - c2)}")

    print()
    print("  ★ Counter 的其它工具方法：")
    print(f"    elements() 展开元素：{list(c1.elements())}   ← 按次数重复展开")
    print(f"    total() 总次数：{c1.total()}")

    print()
    print("  ★ 最常见用途：单词词频 TopN（比手写字典循环简洁得多）：")
    sentence = "the quick brown fox jumps over the lazy dog the fox the end"
    top3 = Counter(sentence.split()).most_common(3)   # 分词后取前三
    print(f"    句子 Top3 高频词：{top3}")


# ===== 语法解析 =====
# 【6】★ 嵌套 dict 实战：聚合统计
#   场景：统计多个学生各科成绩，计算平均分、排名。
#   手法：嵌套 dict + defaultdict + 推导式，模拟 JSON 数据处理。
def demo_nested_dict() -> None:
    print()
    print("=" * 60)
    print("【6】★ 嵌套 dict 实战：成绩聚合统计")
    print("=" * 60)

    # 嵌套字典：外层 学生 → 内层 科目 → 成绩
    scores: Dict[str, Dict[str, int]] = {
        "张三": {"数学": 90, "英语": 85, "语文": 92},
        "李四": {"数学": 78, "英语": 95, "语文": 88},
        "王五": {"数学": 66, "英语": 72, "语文": 80},
    }
    print(f"  原始数据（模拟 JSON）：")
    for name, subs in scores.items():
        print(f"    {name}: {subs}")

    # 1. 每个学生的平均分
    print()
    print("  【每生平均分】")
    averages: Dict[str, float] = {}
    for name, subs in scores.items():
        avg = sum(subs.values()) / len(subs)   # 总分 / 科目数
        averages[name] = round(avg, 1)
        print(f"    {name}: 总分={sum(subs.values())} 平均={avg:.1f}")

    # 2. 各科平均分（转置聚合 → defaultdict）
    print()
    print("  【各科平均分】（defaultdict 聚合）：")
    subject_totals: DefaultDict[str, List[int]] = defaultdict(list)
    for subs in scores.values():
        for subject, score in subs.items():
            subject_totals[subject].append(score)  # 把每个科目成绩收集起来
    for subject, vals in subject_totals.items():
        print(f"    {subject}: 平均={sum(vals) / len(vals):.1f}  明细={vals}")

    # 3. 找出每个科目的最高分及学生
    print()
    print("  【各科最高分】")
    best: Dict[str, Any] = {}
    for name, subs in scores.items():
        for subject, score in subs.items():
            if subject not in best or score > best[subject]["score"]:
                best[subject] = {"name": name, "score": score}
    for subject, info in best.items():
        print(f"    {subject}: {info['name']}（{info['score']} 分）")

    # 4. 嵌套字典的安全访问
    print()
    print("  ★ 嵌套访问的容错（用多层 get 或 defaultdict）：")
    print(f"    scores['张三']['数学']        = {scores['张三']['数学']}")
    print(f"    scores['张三'].get('化学', '无') = {scores['张三'].get('化学', '无')}  （内层用 get）")
    print(f"    scores.get('赵六', '无此学生')  = {scores.get('赵六', '无此学生')}  （外层用 get）")
    print("    ★ 逐层用 .get(key, default) 或 .get(key, {}).get(key, default) 防 KeyError。")

    # 5. 用推导式扁平化嵌套字典
    print()
    print("  ★ 字典推导式扁平化（把 (学生,科目) 打平成键）：")
    flat = {(name, subject): score for name, subs in scores.items() for subject, score in subs.items()}
    print(f"    打平后共 {len(flat)} 条：{list(flat.items())[:4]} ...")
    print("    ★ 这正是元组作复合主键的典型场景（引出 02_tuple）")

    # 6. 反转嵌套结构：科目 → 学生 → 成绩
    print()
    print("  【反转结构：科目 → 学生 → 成绩】")
    by_subject: DefaultDict[str, Dict[str, int]] = defaultdict(dict)
    for name, subs in scores.items():
        for subject, score in subs.items():
            by_subject[subject][name] = score    # 嵌套 defaultdict(dict)
    for subject, students in by_subject.items():
        top = max(students.items(), key=lambda kv: kv[1])
        print(f"    {subject}: 最高 {top[0]}({top[1]})  平均={sum(students.values()) / len(students):.1f}")


# ===== 语法解析 =====
# 【7】字典视图的运算符与合并
#   视图对象：d.keys() / d.values() / d.items() 返回【动态视图】。
#   支持集合运算（仅 keys()/items()）：& | - ^
def demo_views_and_merge() -> None:
    print()
    print("=" * 60)
    print("【7】字典视图运算符 与 合并")
    print("=" * 60)

    d = {"a": 1, "b": 2, "c": 3}
    print(f"  字典 {d}")
    print(f"    list(d.keys())   = {list(d.keys())}   type={type(d.keys()).__name__}")
    print(f"    list(d.values()) = {list(d.values())}")
    print(f"    list(d.items())  = {list(d.items())}")

    print()
    print("  ★ keys() 是集合视图，支持集合运算：")
    k = d.keys()
    print(f"    d.keys() & {{'a','z'}} = {k & {'a', 'z'}}   （公共键）")
    print(f"    d.keys() | {{'d'}}    = {k | {'d'}}   （并集）")
    print(f"    d.keys() - {{'a'}}    = {k - {'a'}}   （差集）")

    print()
    print("  ★ 视图是【动态】的：")
    view = d.keys()
    print(f"    建视图 view={view}（此时 {len(view)} 个键）")
    d["new"] = 4                             # 修改原字典
    print(f"    添加 'new' 后再取 view = {list(view)}   ← 视图自动反映变化")
    print("    ★ 视图不拷贝数据，是『活的窗口』。")

    print()
    print("  ★ 字典合并（两种等价写法）：")
    base = {"host": "localhost", "port": 8080}
    override = {"port": 9090, "debug": True}
    merged1 = {**base, **override}           # 展开语法
    merged2 = base | override                # | 运算符（3.9+）
    print(f"    base    = {base}")
    print(f"    override= {override}")
    print(f"    {{**base, **override}} = {merged1}   （右侧覆盖左侧）")
    print(f"    base | override       = {merged2}   （等价）")

    print()
    print("  ★ 用 | 做条件合并（高效过滤）：")
    conf = {"host": "localhost", "port": 8080, "debug": False, "secret": "xxx"}
    # 只保留非敏感且为真的配置
    public = {k: v for k, v in conf.items() if k != "secret"}
    print(f"    去掉 secret：{public}")
    # 反向：只取出 debug=True 的配置（用 & 保留公共键）
    defaults = {"host": "localhost", "port": 80, "debug": True}
    override_keys = {"debug", "port"}
    merged3 = {**{k: v for k, v in conf.items() if k in override_keys}, **defaults}
    print(f"    按键合并默认值：{merged3}")


# ===== 语法解析 =====
# 【8】键的限制与常见坑
def demo_key_rules() -> None:
    print()
    print("=" * 60)
    print("【8】键的限制与常见坑")
    print("=" * 60)

    # 可哈希（不可变）类型都能作键
    d = {1: "int", 1.5: "float", "s": "str", (1, 2): "tuple", True: "bool", None: "none"}
    print(f"  可哈希类型作键：{d}")
    print(f"    ★ 注意 1 和 True 冲突：{{1:'a', True:'b'}} 中 True 覆盖了 1 → { {1: 'a', True: 'b'} }")
    print("    （因为 hash(True)==hash(1) 且 True==1，被视为同一个键）")

    # 不可哈希类型不能作键
    print()
    print("  ★ 不可哈希类型不能作键：", end=" ")
    try:
        {[1, 2]: "list 不可变"}
    except TypeError as exc:
        print(f"TypeError（{exc}）—— list/dict/set 都不能作键")

    print()
    print("  ★ 需要用 list/dict 作键时，改用 tuple 或 frozenset：")
    print(f"    tuple 键    {{(1,2): 'v'}} 可用 → { {(1, 2): 'v'} }")
    print(f"    frozenset 键 {{frozenset([1,2]): 'v'}} 可用 → { {frozenset([1, 2]): 'v'} }")

    print()
    print("  ★ 字典不能自引用（不可哈希）：", end=" ")
    try:
        d2: Dict[Any, Any] = {}
        d2["self"] = d2
    except TypeError as exc:
        print(f"TypeError: {exc}")
    print("    （若要表达自引用结构，用 list 代替）")

    print()
    print("  ★ 常用坑：get 的默认值是【每次调用都求值】，即使键存在：")
    calls = {"n": 0}

    def expensive_default() -> list[int]:
        calls["n"] += 1
        return []

    d3 = {"key": "已有值"}
    _ = d3.get("key", expensive_default())   # 即使键存在，默认值表达式也会求值
    print(f"    调用次数 = {calls['n']}   ← 浪费了一次求值！")
    print("    ★ 默认值应避免副作用；需要惰性默认值用 setdefault 或 defaultdict。")


def main() -> None:
    """主函数：按教学顺序演示字典的知识点。"""
    demo_basics()
    demo_default_values()
    demo_iteration()
    demo_ordering()
    demo_counter()
    demo_nested_dict()
    demo_views_and_merge()
    demo_key_rules()

    print()
    print("=" * 60)
    print("小结")
    print("=" * 60)
    print("  1. 字典存【键→值】映射，键查找平均 O(1)（哈希表）")
    print("  2. ★ get 只读返回默认；setdefault 缺失时写入；defaultdict 自动建工厂对象")
    print("  3. ★ Python 3.7+ 保证插入顺序；删除再插入会移到末尾")
    print("  4. ★ 遍历用 items()；遍历中改字典会 RuntimeError，先 keys() 转快照")
    print("  5. Counter 是计数字典，内置 most_common 排行和算术运算")
    print("  6. defaultdict 做分组聚合最简洁：defaultdict(list) 收集、defaultdict(int) 计数")
    print("  7. 嵌套 dict 处理 JSON 风格数据，逐层用 .get() 容错")
    print("  8. keys() 是动态集合视图，支持 & | - ；视图会随字典变化")
    print("  9. 字典合并：** 解包（通用）vs | 运算符（3.9+）")
    print(" 10. 键必须可哈希：list/dict 不行，用 tuple/frozenset 替代")


if __name__ == "__main__":
    main()