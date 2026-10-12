# -*- coding: utf-8 -*-
"""
03_itertools.py —— itertools 全家桶实战

【演示的语法点】
1. 连接类：chain / chain.from_iterable / zip_longest / zip(*iters, strict=True)
2. 筛选类：filterfalse / compress / takewhile / dropwhile / islice
3. 分组类：groupby（必须先排序！key 参数、last 分组）
4. 聚合类：accumulate（operator 组合、自定义二元函数）、reduce 的位置
5. 数学类：product / permutations / combinations / combinations_with_replacement
6. 无穷类：count / cycle / repeat
7. 多路复用：tee（代价：缓存）
8. 高效转换：starmap（等价于 map(f, *zip(...))）
9. pairwise（相邻二元组滑动窗口）
10. 惰性 vs 物化：何时 list(...) 收口
11. accumulate 做「前缀和 / 移动平均 / 累计占比」
12. groupby 做「游程编码 RLE」与「分组 TOP1」

【预期输出摘要】
- 每个函数给出真实业务场景示例（订单对账、日志聚合、批量组合、密码学重置序列等）
- groupby 未排序会得到错误的「多组」结果，实测对比可见
- accumulate 可实现前缀和、复利、移动平均
- product 的笛卡尔积规模 = 各维度长度之积，组合类会先物化（注意内存）
"""
import itertools
import operator
import time
from collections import defaultdict


# ======================================================================
# 语法解析 1：连接类 —— chain / zip_longest
# ======================================================================
#
# 语法规则：
#   chain(a, b, c)        -> 依次产出 a、b、c 的元素（浅层拼接）
#   chain.from_iterable(l)-> 参数是「可迭代对象的可迭代对象」，自动展平一层
#   zip_longest(a, b, fillvalue=X)  -> 以最长为准，短的一方用 X 补齐
#   zip(*iters, strict=True)       -> 长度不等时直接报错（防「静默截断」事故）
#
# 设计原理：chain 的每个参数会被先 iter() 再依次消费，是【惰性】的；
#           但如果传入的是 list，Python 不会合并内存，只是多个游标接力。


def demo_chain_zip() -> None:
    print("=" * 68)
    print("【1】连接类：chain / zip_longest / zip(strict)")
    print("=" * 68)

    # 场景1：合并多个数据源的日志行（大文件处理前常用）
    log_a = ["ERROR db timeout", "WARN slow sql"]
    log_b = ["ERROR cache miss", "INFO ok", "ERROR db timeout"]

    print("场景：多机日志合并后统一处理")
    merged = itertools.chain(log_a, log_b)
    errors = [ln for ln in merged if ln.startswith("ERROR")]
    print(f"  合并后 ERROR 行数 = {len(errors)}: {errors}")
    print("  ^ chain 惰性，不创建新列表；这是流式日志处理的第一环")

    # 场景2：从配置里读出多个可变长度列表，一次展平
    batches = [["a", "b"], [], ["c"], ["d", "e", "f"]]
    flat = list(itertools.chain.from_iterable(batches))
    print(f"\n场景：展平不定长批次 {batches}")
    print(f"  chain.from_iterable -> {flat}")
    print("  ^ chain(a,b) 只能展【一层】且参数要拆开写，")
    print("    from_iterable 才能接「列表的列表」")

    # 场景3：zip_longest —— 订单对账，左右两边行数不一致
    left = ["订单A", "订单B", "订单C"]
    right = ["订单B", "订单C", "订单D", "订单E"]
    print("\n场景：订单对账（对账系统最经典的用法）")
    print(f"  左表 {left}")
    print(f"  右表 {right}")
    only_left, only_right = set(left) - set(right), set(right) - set(left)
    print(f"  用集合运算：仅左表={sorted(only_left)} 仅右表={sorted(only_right)}")

    # zip_longest 的真正价值是【逐行对齐】（按位置，不按 key）
    # 注意：它按【下标】对齐，不是按订单号匹配 —— 所以要配 fillvalue 才能发现缺行
    print("\nzip_longest 按【下标】对齐，缺的一方补 fillvalue：")
    for name, counterpart in itertools.zip_longest(left, right, fillvalue="<缺失>"):
        print(f"    左={name:<6} 右={counterpart}")

    # zip strict：Python 3.10+ 新增，把「静默截断」变成显式报错
    print("\nzip(strict=True) 的价值：")
    try:
        list(zip([1, 2, 3], "ab", strict=True))
    except ValueError as e:
        print(f"  长度不等 -> ValueError: {e}")
    print(f"  不加 strict 会静默截断成: {list(zip([1, 2, 3], 'ab'))}")
    print("  ^ 这就是【生产事故级 bug】：数据少了几条，你却毫不知情")

    # 注意：itertools【没有】zip。zip 只在内置命名空间（Python 3.10+ 支持 strict 参数）。
    print(f"\n内置 zip(strict=True) 的类型: {type(zip([1], [2])).__name__}（惰性）")
    print("  ^ itertools 只提供 zip_longest（惰性，按最长补齐），zip 本体不在其中。")


# ======================================================================
# 语法解析 2：筛选类 —— filterfalse / compress / takewhile / dropwhile
# ======================================================================
#
# 语法规则：
#   filterfalse(pred, it)   保留【使 pred 为假】的元素（与 filter 相反）
#   compress(it, selectors) 只保留 selectors 中对应位置为真的元素
#   takewhile(pred, it)    【连续】满足条件的，一旦不满足立即停（不检查后面的）
#   dropwhile(pred, it)    丢弃开头【连续】满足条件的，剩下全要
#
# takewhile vs filter 的关键差异：
#   filter 会「扫描全表」；takewhile 遇到第一个不满足就【停止消费】，
#   因此可以作用于【无限序列】。


def demo_filter_family() -> None:
    print()
    print("=" * 68)
    print("【2】筛选类：filterfalse / compress / takewhile / dropwhile")
    print("=" * 68)

    prices = [100, 0, 250, 0, 30, 0, 999]

    print("场景：过滤掉无效的 0 值")
    print(f"  原数据            : {prices}")
    print(f"  filter(lambda p: p)        -> {list(filter(lambda p: p, prices))}")
    print(f"  filterfalse(lambda p: p)   -> {list(itertools.filterfalse(lambda p: p, prices))}")
    print(f"  dropwhile(lambda p: p)     -> {list(itertools.dropwhile(lambda p: p, prices))}")
    print("  ^ dropwhile 只丢【开头连续】的 0，遇到 250 就停 —— 数据脏在开头才用它")

    # takewhile：可以作用于无限序列（filter 做不到）
    fibs = (n for n in itertools.count(1)
            if all(n % d for d in range(2, int(n ** 0.5) + 1)))
    first5 = list(itertools.takewhile(lambda n: n < 30, fibs))
    print(f"\n场景：取小于 30 的质数（takewhile 遇 31 立即停）")
    print(f"  {first5}")
    print("  ^ 用 filter(lambda n: n<30, fibs) 也能得到同样结果，但会【无限跑下去】；")
    print("    takewhile 因为「不满足就停止消费」，所以能安全地作用于无限源")

    # compress：按「位掩码」筛选，密码重置状态机常用
    flags = [True, False, True, True, False]
    items = ["登录", "登出", "改密", "绑定MFA", "解绑"]
    print(f"\n场景：compress 按选择位筛选（前端勾选框后端实现）")
    print(f"  勾选位 {flags}")
    print(f"  全部项 {items}")
    print(f"  compress -> {list(itertools.compress(items, flags))}")
    print("  ^ selectors 可以是任意可迭代，不限于 bool/0/1；")
    print("    长度短时以【最短】为准，多余项被静默丢弃")


# ======================================================================
# 语法解析 3：groupby —— 必须先排序
# ======================================================================
#
# 语法规则：
#   groupby(it, key=None)  -> (key, 分组迭代器) 的序列
#   关键约束：相邻相同才分组 —— 所以【必须先排序】，否则相同项分散在各处会被拆成多组
#   分组迭代器是【惰性且一次性】的：必须在前一个组被消费完之前处理当前组
#
# 常见死法：
#   for k, g in groupby(data):
#       print(k, list(g))      # 正确
#       print(k, list(g), list(g))   # 第二次 list(g) 得到空！


def demo_groupby() -> None:
    print()
    print("=" * 68)
    print("【3】groupby：相邻分组 + 排序前置")
    print("=" * 68)

    # 场景：日志按级别聚合
    raw_logs = [
        ("INFO", "启动"), ("ERROR", "超时"), ("INFO", "加载"),
        ("WARN", "慢"), ("ERROR", "空指针"), ("INFO", "就绪"),
    ]
    unsorted = [lvl for lvl, _ in raw_logs]
    print("场景：聚合同级别日志")
    print(f"  原始顺序: {unsorted}")

    # 未排序 -> ERROR 出现 2 次，被拆成 2 组
    bad = [(k, len(list(g))) for k, g in itertools.groupby(raw_logs, key=lambda t: t[0])]
    print(f"  ❌ 未排序直接 groupby -> {bad}   （ERROR 被拆成 2 组！）")

    # 先排序 -> 每种级别聚成 1 组
    ordered = sorted(raw_logs, key=lambda t: t[0])
    good = [(k, [msg for _, msg in g]) for k, g in itertools.groupby(ordered, key=lambda t: t[0])]
    print(f"  ✅ sorted 之后 groupby -> {good}")

    # 场景：游程编码 RLE（数据压缩的经典算法）
    pixels = ["A", "A", "B", "B", "B", "C", "A"]
    rle = [(k, len(list(g))) for k, g in itertools.groupby(pixels)]
    print(f"\n场景：游程编码 RLE（把 {pixels} 压缩成「值+连续次数」）")
    print(f"  {rle}")
    print("  ^ 这是 groupby 最经典的生产用途：内存/带宽压缩")

    # 场景：每组取 TOP1（注意不能先转 list 再排序，要用 max + key）
    sales = [("华东", 120), ("华北", 150), ("华东", 180), ("华南", 90), ("华北", 160)]
    ordered_sales = sorted(sales, key=lambda t: t[0])
    tops = []
    for region, group in itertools.groupby(ordered_sales, key=lambda t: t[0]):
        best = max(group, key=lambda t: t[1])       # 在「当前组」上直接求 max
        tops.append((region, best))
    print(f"\n场景：各区域销售额 TOP1（不物化分组，直接 max）")
    print(f"  {tops}")
    print("  ^ 记忆：groupby 的 value 是【一次性游标】，一次性消费掉最省内存")

    # 易错点：重复消费分组
    print("\n易错点：分组迭代器是一次性的")
    for k, g in itertools.groupby(ordered_sales, key=lambda t: t[0]):
        print(f"  {k}: 第一次 list(g) = {list(g)}")
        print(f"  {k}: 第二次 list(g) = {list(g)}  <- 空！游标已耗尽")


# ======================================================================
# 语法解析 4：accumulate —— 前缀运算流
# ======================================================================
#
# 语法规则：
#   accumulate(it)                        默认二元加法 -> 前缀和
#   accumulate(it, func)                  自定义二元函数（func(x, y) -> x op y）
#   accumulate(it, initial=v)             带上初始值（Python 3.8+）
#   关键：第 n 个产出 = func(第 n-1 个产出, 第 n-1 个元素) —— 是【累积】而非两两算
#
# 对比 pairwise：
#   accumulate -> 前缀形态 [a, a+b, a+b+c, ...]（窗口是「从头到当前」）
#   pairwise   -> 滑动窗口形态 [(a,b), (b,c), (c,d), ...]（窗口大小固定为 2）


def demo_accumulate() -> None:
    print()
    print("=" * 68)
    print("【4】accumulate：前缀和 / 复利 / 移动平均")
    print("=" * 68)

    amounts = [100, 200, 50, 300, 20]
    print(f"金额流: {amounts}")
    print(f"  累加余额      : {list(itertools.accumulate(amounts))}")

    # 复利：func = lambda 本金, 利息: 本金 + 本金*利率
    principal = 10_000
    rate = 0.03
    growth = list(itertools.accumulate(
        [principal] * 5,
        func=lambda p, _: round(p * (1 + rate), 2),
        initial=principal,
    ))
    print(f"\n复利（本金={principal}, 年利率={rate:.0%}）")
    print(f"  逐年余额: {growth}")
    print("  ^ 复利公式的本质就是「上一个结果 op 当前输入」的累积")

    # 乘法累积 -> 阶乘
    print(f"\n5 的阶乘（累积乘法）: "
          f"{list(itertools.accumulate(range(1, 6), operator.mul))}")

    # 累计占比：风控「前 N 笔交易贡献了多少金额」
    big = [100, 500, 20, 300, 80]
    total = sum(big)
    cum = list(itertools.accumulate(big))
    ratios = [round(c / total * 100, 1) for c in cum]
    print(f"\n累计占比（风控/帕累托分析）")
    print(f"  金额   {big}")
    print(f"  累计   {cum}")
    print(f"  累计%  {ratios}")
    top2 = next(i for i, r in enumerate(ratios) if r >= 80)
    print(f"  ^ 前 {top2 + 1} 笔就贡献了 80% 的金额 —— 这是典型的帕累托发现")

    # pairwise vs accumulate 对比（Python 3.10+ 有 itertools.pairwise）
    data = [3, 1, 4, 1, 5, 9, 2, 6]
    print(f"\n数据 {data}")
    print(f"  accumulate（前缀和）: {list(itertools.accumulate(data))}")
    print(f"  pairwise（相邻对）  : {list(itertools.pairwise(data))}")
    # itertools.pairwise 【没有】 n 参数（只能窗口=2），
    # 想要宽度 n 的滑动窗口，要用 accumulate 的差分技巧自己造
    window = 3
    diffs = list(itertools.accumulate(([0] + list(data)), initial=0))
    # 前缀和相减得到定长滑动窗口的和：sum(data[i-n+1..i])
    sliding = [diffs[i] - diffs[i - window] for i in range(window, len(diffs))]
    print(f"  自造宽度{window}的滑动窗口和: {sliding}")
    print(f"  移动平均(宽{window})       : "
          f"{[round(s / window, 2) for s in sliding]}")
    print("  ^ 技巧：利用「前缀和相邻两项之差 = 定长窗口之和」，避免反复求 sum")
    print("\n反向技巧：相邻差分 = [b - a for a, b in itertools.pairwise(data)]，")
    print("          即 accumulate 的逆运算，pairwise 正好提供相邻对。")


# ======================================================================
# 语法解析 5：组合类 —— product / permutations / combinations
# ======================================================================
#
# 语法规则：
#   product(A, B)              笛卡尔积，长度 = len(A)*len(B)，【参数顺序是轮转】
#   product(A, repeat=2)       A 自身与自己做笛卡尔积
#   permutations(A, r)         排列：不重复取 r 个，顺序敏感 -> n!/(n-r)!
#   combinations(A, r)         组合：不重复取 r 个，顺序无关 -> C(n, r)
#   combinations_with_replacement(A, r) 组合但可重复 -> C(n+r-1, r)
#
# 内存警告：combinations/permutations 会【先物化】整个列表（内部转成 tuple 池），
#          所以 n 很大时极耗内存。product 是【惰性】的。这是最重要的差别！


def demo_combinations() -> None:
    print()
    print("=" * 68)
    print("【5】组合类：product / permutations / combinations")
    print("=" * 68)

    colors = ["红", "绿", "蓝"]
    sizes = ["S", "M", "L"]

    print("场景：商品 SKU 笛卡尔积")
    print(f"  颜色 {colors} × 尺码 {sizes}")
    skus = list(itertools.product(colors, sizes))
    print(f"  product -> {skus}  （共 {len(skus)} 种）")
    print(f"  注意顺序：product(A,B) 是 A 在【外层】轮转 -> "
          f"{list(itertools.product([1, 2], 'xy'))}")

    # repeat：生成所有密码（数量为 字符集^长度）
    print(f"\n场景：穷举 PIN（4 位数字）")
    pins = itertools.product("0123456789", repeat=4)
    print(f"  理论总数 = 10^4 = {10 ** 4}，前 5 个 = "
          f"{[''.join(p) for p in itertools.islice(pins, 5)]}")
    print("  ^ product 是【惰性】的，所以理论上有 10000 个也不怕")

    # permutations：洗牌/排列顺序敏感
    print("\n场景：三项任务的两两执行顺序（顺序敏感）")
    tasks = ["A", "B", "C"]
    print(f"  permutations(tasks, 2) -> {list(itertools.permutations(tasks, 2))}")
    print(f"  数量 = 3*2 = 6（顺序不同算不同方案）")

    # combinations：选人不选序（顺序无关）
    print("\n场景：从 4 人中选 2 人组队（顺序无关）")
    people = ["张三", "李四", "王五", "赵六"]
    teams = list(itertools.combinations(people, 2))
    print(f"  combinations -> {teams}")
    print(f"  数量 = C(4,2) = 6，且 (张三,李四) 与 (李四,张三) 是【同一个】组合")

    # combinations_with_replacement：可重复取值（骰子、抽签可放回）
    print("\n场景：掷两颗骰子（可重复）")
    dice = list(itertools.combinations_with_replacement([1, 2, 3, 4, 5, 6], 2))
    print(f"  组合数 = C(7,2) = {len(dice)}（注意是 21 而不是 36）")
    print(f"  前 5 组: {dice[:5]}")
    print("  ^ 可重复组合多颗骰子时【天然去重】，比 product 再去重快得多")

    # 内存对比实测
    print("\n内存与惰性对比（实测）：")
    import timeit
    base = list(range(12))
    n_iter, n_comb = 1_000, 5_000

    t_product = timeit.timeit(lambda: sum(1 for _ in itertools.product(base, repeat=2)),
                              number=n_iter) / n_iter
    t_comb = timeit.timeit(lambda: sum(1 for _ in itertools.combinations(base, 2)),
                           number=n_comb) / n_comb
    print(f"  product(base, repeat=2)     : {t_product * 1e6:8.1f} us/次  "
          f"（惰性流式）")
    print(f"  combinations(base, 2)        : {t_comb * 1e6:8.1f} us/次  "
          f"（内部先物化）")
    print("  ^ 怎么读这组数：combinations 的单次【产出】其实更便宜（它只算不枚举），")
    print("    但它会把输入转成 tuple 池再消费，所以【首次】调用有 O(n) 固定开销；")
    print("    上面的数字因为 number 很小（5 次/1万次），被这个前置开销摊薄了。")
    print("    真正的结论是：若要反复取组合，请自己缓存 tuple 池再传进去，而不是")
    print("    对同一个 list 反复调用 combinations。")


# ======================================================================
# 语法解析 6：多路复用与高效映射 —— tee / starmap
# ======================================================================


def demo_tee_starmap() -> None:
    print()
    print("=" * 68)
    print("【6】tee（多路复用） 与 starmap（解包映射）")
    print("=" * 68)

    # tee：把一个流分给多个消费者
    # 场景：HTTP 请求既要做业务处理，又要做审计记录
    print("场景：响应数据同时用于「业务处理」和「审计留痕」")
    response = "data-payload"
    for_audit, for_business = itertools.tee(response, 2)      # 需要重试 -> tee
    print(f"  审计分支: {list(for_audit)}")
    print(f"  业务分支: {list(for_business)}")

    # tee 的正确用法示范：short-circuit 后丢弃
    print("\ntee 的「重试」惯用法：")
    attempts = itertools.tee("x", 3)      # 3 次重试机会
    for i, chunk in enumerate(attempts):
        if chunk:                       # 消费第一个分支
            print(f"  第{i + 1}次尝试成功，丢弃剩余 {len(list(attempts)) - 1} 个分支")
            break
    print("  ^ 第一个分支若为空，tee 会自动填满后面分支，保证数据不丢")

    # starmap = map(f, *zip(...))
    def add3(a, b, c):
        return a + b + c

    triples = [(1, 2, 3), (10, 20, 30), (100, 200, 300)]
    print("\n场景：按三元组批量计算")
    print(f"  普通 map:  {list(map(add3, [1, 10], [2, 20], [3, 30]))}  （三个列表分别传）")
    print(f"  starmap:  {list(itertools.starmap(add3, triples))}  （直接吃元组列表）")
    print("  ^ starmap(a,b,c) 等价 map(func, *zip(a,b,c))，但少建 3 个中间列表")

    # starmap + operator.itemgetter：字段提取的标准写法
    print("\n场景：从对象列表中提取指定字段（ETL 常用）")
    records = [{"id": 1, "name": "甲", "score": 90},
               {"id": 2, "name": "乙", "score": 75}]
    ids_and_scores = [(r["id"], r["score"]) for r in records]
    print(f"  取出 id 和 score: "
          f"{list(itertools.starmap(lambda i, s: (i, s), ids_and_scores))}")
    print(f"  配合 itemgetter: "
          f"{[tuple(t) for t in map(operator.itemgetter('id', 'name'), records)]}")
    print("  ^ operator.itemgetter(*keys) 返回一个函数，比 lambda 更快（无解释器开销）")


# ======================================================================
# 语法解析 7：完整 API 速查表
# ======================================================================


def demo_api_reference() -> None:
    print()
    print("=" * 68)
    print("【7】itertools 完整速查（全部实测输出）")
    print("=" * 68)

    rows = [
        # (函数名, 实际调用, 结果, 真实场景)
        ("chain", "chain('AB', 'CD')", list(itertools.chain("AB", "CD")),
         "合并多份日志"),
        ("chain.from_iterable", "from_iterable([[1,2],[3]])",
         list(itertools.chain.from_iterable([[1, 2], [3]])), "展平批次"),
        ("count", "count(10, 5) x4", list(itertools.islice(itertools.count(10, 5), 4)),
         "分页 offset"),
        ("cycle", "cycle('AB') x5", list(itertools.islice(itertools.cycle("AB"), 5)),
         "轮询多副本"),
        ("repeat", "repeat('x', 3)", list(itertools.repeat("x", 3)),
         "参数默认值填充"),
        ("dropwhile", "dropwhile(<5, [1,3,5,1])",
         list(itertools.dropwhile(lambda x: x < 5, [1, 3, 5, 1])), "跳过头部无效行"),
        ("filterfalse", "filterfalse(<5, [1,3,5,1])",
         list(itertools.filterfalse(lambda x: x < 5, [1, 3, 5, 1])), "取需要清理的"),
        ("groupby", "groupby 长度分组",
         [(k, len(list(g))) for k, g in
          itertools.groupby([1, 1, 2, 2, 2], key=lambda x: x)], "游程编码"),
        ("islice", "islice(range(9), 2, 8, 2)",
         list(itertools.islice(range(9), 2, 8, 2)), "分页/无限源截断"),
        ("pairwise", "pairwise([1,2,3])",
         list(itertools.pairwise([1, 2, 3])), "相邻差分"),
        ("permutations", "permutations('AB', 2)",
         [''.join(p) for p in itertools.permutations("AB", 2)], "任务执行顺序"),
        ("combinations", "combinations('ABCD', 2)",
         [''.join(c) for c in itertools.combinations("ABCD", 2)], "组队/选品"),
        ("comb_with_rep", "comb_with_rep('AB', 2)",
         [''.join(c) for c in itertools.combinations_with_replacement("AB", 2)],
         "掷骰子去重"),
        ("product", "product('AB','12')",
         [''.join(p) for p in itertools.product("AB", "12")], "SKU 组合"),
        ("starmap", "starmap(operator.add, [(1,2),(3,4)])",
         list(itertools.starmap(operator.add, [(1, 2), (3, 4)])), "批量二元计算"),
        ("takewhile", "takewhile(<5, [1,3,5,1])",
         list(itertools.takewhile(lambda x: x < 5, [1, 3, 5, 1])), "连续段截取"),
        ("zip_longest", "zip_longest('AB','xyz')",
         [''.join(t) for t in itertools.zip_longest("AB", "xyz", fillvalue="-")],
         "订单对账"),
        ("accumulate", "accumulate([1,2,3], mul)",
         list(itertools.accumulate([1, 2, 3], operator.mul)), "前缀积/余额"),
        ("compress", "compress('ABCD',[1,0,1,0])",
         list(itertools.compress("ABCD", [1, 0, 1, 0])), "按位掩码筛字段"),
        ("tee", "tee([1,2], 2)", [list(t) for t in itertools.tee([1, 2], 2)],
         "业务+审计双消费"),
    ]

    print(f"{'函数':<24}{'实测结果':<28}{'场景'}")
    print("-" * 78)
    for name, call, result, scene in rows:
        print(f"{name:<24}{str(result):<28}{scene}")

    print("\n还有 batched（Python 3.12+）：把流按固定大小分批，"
          "适合批量写库/批量调API")
    batches = list(itertools.batched(range(7), 3))
    print(f"  batched(range(7), 3) = {batches}")
    print("  ^ 支持 strict=True 让「最后一批不足」直接报错，避免半批写入数据不一致")

    print("\n【惰性 vs 物化】总表：")
    print(f"{'函数':<28}{'惰性':<8}说明")
    print("-" * 70)
    print(f"{'chain/zip_longest':<28}{'是':<8}每个参数一个游标")
    print(f"{'islice/takewhile/dropwhile':<28}{'是':<8}随时可停止")
    print(f"{'count/cycle/repeat':<28}{'是':<8}可无限")
    print(f"{'accumulate/starmap/tee':<28}{'是':<8}C 层实现，几乎无额外开销")
    print(f"{'product':<28}{'是':<8}不物化笛卡尔积")
    print(f"{'permutations/combinations*':<28}{'否':<8}内部物化输入池，注意内存")
    print(f"{'groupby':<28}{'半':<8}分组是惰性的，但整体仍需你保持有序输入")


def main() -> None:
    demo_chain_zip()
    demo_filter_family()
    demo_groupby()
    demo_accumulate()
    demo_combinations()
    demo_tee_starmap()
    demo_api_reference()
    print()
    print("=" * 68)
    print("03_itertools 演示完毕")
    print("核心一句话：itertools 是【C 实现的惰性流算子】，用好了能替代大量手写循环。")
    print("=" * 68)


if __name__ == "__main__":
    main()