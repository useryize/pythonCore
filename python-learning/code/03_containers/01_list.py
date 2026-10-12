"""
================================================================================
  01_list.py  ——  列表：可变序列的完整操作
================================================================================

【演示的语法点】
 1. 列表的 5 种创建方式（字面量 / list() / range() / 推导式 / split()）
 2. ★ 增：append / extend / insert / + 与 * 的区别（最易错点）
 3. ★ 删：remove / pop / del / clear 的语义差异
 4. 改：单元素赋值与切片赋值（切片长度可以不一致！）
 5. 查：index / count / in 成员判断 / 负索引
 6. ★ 切片 slice：正负步长、切片赋值、切片是【新对象】
 7. ★ 排序：sort() vs sorted()、key 参数、多级排序、稳定性
 8. ★ 浅拷贝 vs 深拷贝：copy.copy / copy.deepcopy / [:] 的差别
 9. ★ list 别名坑：赋值是引用同一对象，不是复制
10. ★ remove 与 pop 的本质区别（按值 vs 按位置）
11. ★ sort 与 sorted 的本质区别（原地 vs 返回新对象）
12. 可变对象作为函数参数默认值的"共享默认值"坑
13. 常用方法速查表与反向遍历技巧

【预期输出摘要】
 - "增删改查" 小节展示各方法返回值（append 返回 None 是高频坑）
 - "拷贝" 小节打印三层嵌套列表在浅拷贝/深拷贝下的不同结果
 - "别名坑" 小节证明 a is b 为 True 且互相影响
 - "remove vs pop" 小节打印 remove 返回 None / pop 返回被删元素
 - "sort vs sorted" 小节证明原列表在 sorted 后未被修改
================================================================================

"""

from __future__ import annotations

import copy
import timeit
from typing import Any


# ===== 语法解析 =====
# 【1】列表创建的 5 种方式
#   语法规则：`[元素]` 中的每个元素可以是任意类型（包括容器自身）。
#   设计意图：把"同类元素的容器"这一概念交给程序员，list 不做类型约束。
#   执行顺序：列表推导式先执行 for 再产出，比 for + append 循环快。
def demo_create() -> None:
    print("=" * 60)
    print("【1】列表创建的 5 种方式")
    print("=" * 60)

    a = [1, 2, 3]                       # 方式1：字面量，最常用
    b = list((1, 2, 3))                  # 方式2：list() 可迭代对象 -> 列表
    c = list(range(1, 4))               # 方式3：range 是"惰性"的，必须转成 list
    d = [i * i for i in range(4)]        # 方式4：列表推导式（等价于 for + append，但更快）
    e = "a,b,c".split(",")              # 方式5：split 由字符串得到列表

    print(f"  字面量            {a}")
    print(f"  list(iterable)    {b}")
    print(f"  list(range(1,4))  {c}   ← range 本身不是列表")
    print(f"  列表推导式        {d}   ← [i*i for i in range(4)]")
    print(f"  str.split()       {e}")
    print()
    # ★ 推导式 vs 循环 append 的性能差异：推导式在 C 层拼接，省去多次方法查找
    t_loop = timeit.timeit("[x for x in range(10000)]", number=1000)
    t_apnd = timeit.timeit(
        """
l = []
for x in range(10000):
    l.append(x)
""",
        number=1000,
    )
    print(f"  ★ 性能：推导式 {t_loop:.3f}s  vs  for+append {t_apnd:.3f}s")
    print("    原因：推导式由解释器直接调用 LIST_APPEND 指令，不做属性查找。")


# ===== 语法解析 =====
# 【2】★ 增：四个方法的语义边界
#   append(x)  —— 加【一个元素】；x 整体作为单元素（哪怕 x 是列表）
#   extend(x)  —— 把 x 的元素【逐个摊平】加入；只接受可迭代对象
#   insert(i,x)—— 在下标 i 处【插入一个元素】，会移动后续元素（O(n)）
#   + 与 *     —— 返回【新列表】，原列表不变（不是原地操作）
#   ★ 返回值坑：append/extend/insert 都返回 None，因为它们是"原地修改"；
#     而 `lst += x` 等价于 `lst.extend(x)`（这是列表唯一重载 += 的地方）。
def demo_add() -> None:
    print()
    print("=" * 60)
    print("【2】★ 增：append / extend / insert / + / *")
    print("=" * 60)

    base = [1, 2]
    print(f"  初始：{base}")

    r1 = base.append([3, 4])            # 把 [3,4] 当作【一个元素】加入
    print(f"  append([3,4])   -> {base}    返回值={r1}  ← 返回 None！")
    print("    ★ append 不会摊平，它把整个列表作为一个元素塞进去。")

    base.extend([5, 6])                 # 逐个摊平加入
    print(f"  extend([5,6])   -> {base}")
    print("    ★ extend 只接受可迭代对象；传整数会 TypeError。")

    base.insert(1, "插入")               # 在下标 1 处插入，后续元素右移
    print(f"  insert(1,'插入') -> {base}")
    print("    ★ insert 是 O(n)，因为需要移动插入点之后的所有元素。")

    new_list = base + [99]              # + 产生新对象
    print(f"  base + [99]     -> 新列表 {new_list}")
    print(f"  base 本身        -> {base}   ← 原地操作与 + 的关键区别")

    print(f"  base * 2        -> {base * 2}  ← 重复拼接，不改原列表")

    print()
    print("  ★ 对比：a + b 保持 a 不变；a += b 直接改 a（是 extend 的语法糖）")
    x = [1, 2]
    y = x
    x += [3]
    print(f"    x += [3] 后  x={x}  y={y}   ← y 跟着变，因为 x += 是原地操作")


# ===== 语法解析 =====
# 【3】★ 删：四个方法的语义边界
#   remove(x)  —— 按【值】删除【第一个】匹配项；找不到抛 ValueError
#   pop()      —— 按【下标】删除并【返回】被删元素；默认弹出最后一个
#   del lst[i] —— 按下标删除，【不返回】任何值（语句，非函数）
#   clear()    —— 清空整个列表（原地）
#   ★ 性能：pop() 从尾部弹出是 O(1)；remove() 总是从头线性查找 O(n)。
def demo_delete() -> None:
    print()
    print("=" * 60)
    print("【3】★ 删：remove / pop / del / clear")
    print("=" * 60)

    data = [10, 20, 30, 20, 40]

    r = data.remove(20)                 # 只删【第一个】20，不返回值
    print(f"  remove(20) 返回 {r}  ->  {data}   ← 只删了第一个 20")

    v = data.pop(0)                     # 删除并【返回】下标 0 的元素
    print(f"  pop(0) 返回 {v}       ->  {data}")

    v2 = data.pop()                     # 不传参数默认弹【最后】一个
    print(f"  pop() 返回 {v2}        ->  {data}   ← 栈式操作首选 pop()")

    del data[1]                         # del 是语句，不产生返回值
    print(f"  del data[1]       ->  {data}")

    data.clear()                        # 原地清空
    print(f"  clear()           ->  {data}   ← 列表对象还在，只是空了")

    print()
    print("  ★ remove 找不到会抛 ValueError：", end=" ")
    try:
        [1, 2].remove(99)
    except ValueError as exc:
        print(f"ValueError（{exc}）  ← 必须先用 in 判断存在性")

    # 安全的删除写法：先判断再删，避免异常开销
    safe = [1, 2, 3]
    target = 2
    if target in safe:                  # in 判断走 C 层循环，比 try/except 快
        safe.remove(target)
    print(f"  安全写法：{safe}")


# ===== 语法解析 =====
# 【4】改：单元素赋值与切片赋值
#   语法规则：`lst[i] = v` 中 i 必须落在 [-n, n-1]，越界抛 IndexError。
#   ★ 切片赋值允许【长度不一致】：这是批量插入/删除元素的惯用手法。
def demo_update() -> None:
    print()
    print("=" * 60)
    print("【4】改：单元素赋值 vs 切片赋值")
    print("=" * 60)

    nums = [1, 2, 3, 4, 5]
    nums[2] = 99                        # 单元素赋值，固定长度
    print(f"  nums[2] = 99        -> {nums}")

    nums[1:3] = [20, 21, 22]            # ★ 切片赋值：3 个元素替换 2 个，长度变了！
    print(f"  nums[1:3]=[20,21,22]-> {nums}   ← 长度不一致也合法")

    nums[:0] = [0, 0]                   # 在开头"插入"：右边界为 0 的空切片
    print(f"  nums[:0]=[0,0]     -> {nums}   ← 用空切片做批量插入")

    del nums[2:4]                       # 用 del + 切片批量删除
    print(f"  del nums[2:4]      -> {nums}")

    print()
    print("  ★ 越界赋值会报错：", end=" ")
    try:
        nums[999] = 1
    except IndexError as exc:
        print(f"IndexError（{exc}）  ← 普通赋值不自动扩容，append 才会")


# ===== 语法解析 =====
# 【5】查：index / count / in / 负索引
#   index(x) —— 返回【下标】；找不到抛 ValueError（与 str.index 语义一致）
#   count(x) —— 返回【出现次数】；找不到返回 0
#   in       —— 成员判断，返回布尔；线性查找 O(n)
def demo_query() -> None:
    print()
    print("=" * 60)
    print("【5】查：index / count / in / 负索引")
    print("=" * 60)

    scores = [88, 95, 72, 95, 60]

    print(f"  list           {scores}")
    print(f"  index(95)      {scores.index(95)}    ← 返回【第一个】匹配的下标")
    print(f"  count(95)      {scores.count(95)}    ← 返回出现总次数")
    print(f"  95 in scores   {95 in scores}    ← 布尔判断")
    print(f"  99 in scores   {99 in scores}")
    print(f"  [-1]  取最后   {scores[-1]}      ← 负索引从末尾往回数")
    print(f"  [-2]  取倒数二 {scores[-2]}")

    print()
    print("  ★ index 找不到抛 ValueError，而 count 找不到返回 0：", end=" ")
    try:
        scores.index(99)
    except ValueError as exc:
        print(f"index → ValueError（{exc}）")

    # 二分查找：列表有序时应改用 bisect 而不是 in / index
    from bisect import bisect_left, insort

    ordered = [1, 3, 5, 7, 9, 11]
    print(f"  有序表 {ordered}")
    print(f"  bisect_left(ordered, 7) = {bisect_left(ordered, 7)}  ← O(log n) 找插入点")
    insort(ordered, 6)                  # 保持有序地插入
    print(f"  insort(ordered, 6) 后 = {ordered}")
    t_in = timeit.timeit(lambda: 5000 in list(range(100000)), number=100)
    t_bs = timeit.timeit(lambda: bisect_left(list(range(100000)), 5000), number=100)
    print(f"  ★ 性能(10万有序表)：in  {t_in:.4f}s  vs  bisect  {t_bs:.4f}s")


# ===== 语法解析 =====
# 【6】★ 切片 slice 的完整规则
#   语法：lst[start:stop:step]
#   规则要点：
#     - 取值区间为 [start, stop)，左闭右开
#     - start/stop 可省略、可为负（负数先 +len 归一化）
#     - step 为负时表示【倒序】遍历
#   ★ 关键：切片总是返回【新列表】，是浅拷贝，不会改原列表。
def demo_slice() -> None:
    print()
    print("=" * 60)
    print("【6】★ 切片 slice：区间、步长、负索引")
    print("=" * 60)

    lst = list(range(10))

    print(f"  原始       {lst}")
    print(f"  lst[2:5]   {lst[2:5]}     ← 左闭右开，取下标 2,3,4")
    print(f"  lst[:4]    {lst[:4]}     ← start 省略 = 从头开始")
    print(f"  lst[6:]    {lst[6:]}     ← stop 省略 = 一直到末尾")
    print(f"  lst[::2]   {lst[::2]}     ← step=2，隔一个取一个")
    print(f"  lst[::-1]  {lst[::-1]}     ← step=-1，倒序（不修改原列表）")
    print(f"  lst[-3:]   {lst[-3:]}     ← 负索引取末尾 3 个")

    print()
    print("  ★ 切片返回新对象，是浅拷贝：")
    part = lst[2:5]
    part.append(999)
    print(f"    part={part}")
    print(f"    lst={lst}   ← 原列表未受影响")

    print()
    print("  ★ 切片用于【安全复制】一维列表（比 list() 快且不改类型语义）：")
    src = [1, 2, 3]
    dup = src[:]
    dup.append(4)
    print(f"    src={src}  dup={dup}   ← 两者独立")

    print()
    print("  ★ 反向遍历的两种正确写法：")
    data = ["a", "b", "c"]
    print(f"    lst[::-1]          -> {data[::-1]}")
    print(f"    reversed(data)     -> {list(reversed(data))}  ← 不复制元素，更省内存")


# ===== 语法解析 =====
# 【7】★ 排序：sort() vs sorted()、key、多级排序
#   语法规则：
#     lst.sort(key=None, reverse=False)  原地排序，返回 None
#     sorted(可迭代对象, key=..., reverse=...) 返回新列表，不改原对象
#   key 的设计意图：把"如何比较"从"比较谁"中分离（策略模式的思想）。
#   ★ 稳定性：Python 的 sort 是稳定排序 —— key 相等的元素保持原有相对顺序。
def demo_sort() -> None:
    print()
    print("=" * 60)
    print("【7】★ 排序：sort / sorted / key / 多级排序")
    print("=" * 60)

    nums = [5, 2, 9, 1, 7]
    print(f"  原始           {nums}")

    r = nums.sort()                     # 原地排序
    print(f"  nums.sort()    -> {nums}   返回值={r}  ← 返回 None！")

    nums = [5, 2, 9, 1, 7]
    result = sorted(nums)               # 返回新列表
    print(f"  sorted(nums)   -> {result}   ← 返回新列表")
    print(f"  原 nums        -> {nums}     ← 未被修改")

    print()
    print("  ★ key 参数：按【规则】排序，而不是按值本身")
    words = ["banana", "apple", "Kiwi", "cherry"]
    print(f"  按长度排序    {sorted(words, key=len)}")
    print(f"  忽略大小写    {sorted(words, key=str.lower)}")
    print(f"  长度降序      {sorted(words, key=len, reverse=True)}")

    print()
    print("  ★ 多级排序：key 返回元组，按元组元素依次比较")
    users = [
        ("张三", 20),
        ("李四", 18),
        ("王五", 20),
        ("赵六", 25),
    ]
    # 先按年龄升序，年龄相同再按姓名升序 —— 元组比较天然支持多键
    users.sort(key=lambda item: (item[1], item[0]))
    print(f"  多级排序结果：{users}")
    print("    ★ key=lambda 返回元组，元组的比较规则就是逐元素比较")

    print()
    print("  ★ 稳定性演示（key 相等的元素保持原顺序）：")
    pairs = [("first", 1), ("second", 0), ("third", 0), ("fourth", 1)]
    stable = sorted(pairs, key=lambda p: p[1])
    print(f"    排序前 {pairs}")
    print(f"    排序后 {stable}")
    print("    ★ 同 key 的 first 仍在 fourth 之前，说明排序稳定")

    print()
    print("  ★ 性能：sort 原地排序 vs sorted 新建列表")
    t_sort = timeit.timeit(lambda: sorted(list(range(1000))), number=1000)
    t_rev = timeit.timeit(lambda: sorted(list(range(1000)), reverse=True), number=1000)
    print(f"    sorted 升序 {t_sort:.4f}s   降序 {t_rev:.4f}s")
    print("    ★ 降序不是把升序结果反转再排（那会不稳定），而是重新排序。")


# ===== 语法解析 =====
# 【8】★ 浅拷贝 vs 深拷贝
#   概念：Python 容器保存的是【对象的引用】。
#     浅拷贝 = 复制容器本身，元素仍是【同一批对象】的引用
#     深拷贝 = 连容器内部的每一层对象都复制一份全新的
#   三种写法：
#     lst[:] / list(lst) / copy.copy(lst)  → 浅拷贝
#     copy.deepcopy(lst)                   → 深拷贝
#   设计意图：默认浅拷贝是性能考虑；只有明确需要"完全独立"才用 deep。
def demo_copy() -> None:
    print()
    print("=" * 60)
    print("【8】★ 浅拷贝 vs 深拷贝（以三层嵌套列表为例）")
    print("=" * 60)

    original = [[1, 2], [3, 4]]
    shallow = copy.copy(original)       # 浅拷贝：外层新，内层同一引用
    deep = copy.deepcopy(original)       # 深拷贝：每一层都独立

    shallow[0].append(99)               # 修改【内层】列表
    print(f"  原始   original = {original}")
    print(f"  浅拷贝 shallow   = {shallow}   ← 内层被污染了！")
    print(f"  深拷贝 deep      = {deep}      ← 完全独立")

    print()
    print("  ★ 验证引用关系（is 判断是不是同一个对象）：")
    o = [[1], [2]]
    s = copy.copy(o)
    d = copy.deepcopy(o)
    print(f"    o is s          → {o is s}    浅拷贝外层是新对象")
    print(f"    o[0] is s[0]    → {o[0] is s[0]}    浅拷贝内层【是同一个对象】")
    print(f"    o[0] is d[0]    → {o[0] is d[0]}   深拷贝内层是不同对象")

    print()
    print("  ★ 不可变对象无需深拷贝（共享无害，省内存）：")
    tup = (1, 2, 3)
    dt = copy.deepcopy(tup)
    print(f"    deep((1,2,3)) is 原元组 → {dt is tup}   ← 元组/字符串/数字被直接复用")

    print()
    print("  ★ 性能对比（嵌套列表）：")
    src = [[i] for i in range(500)]
    t_copy = timeit.timeit(lambda: copy.copy(src), number=1000)
    t_deep = timeit.timeit(lambda: copy.deepcopy(src), number=1000)
    print(f"    copy.copy {t_copy:.4f}s   deepcopy {t_deep:.4f}s")
    print("    ★ deep 是递归的，层级越深差距越大 → 性能敏感场景优先浅拷贝。")

    print()
    print("  ★ 深层结构的推荐做法：共享不可变基础数据 + 深拷贝可变部分")
    template = {"tags": ["v1"], "meta": {"count": 0}}
    safe = copy.deepcopy(template)      # 关键配置用深拷贝隔离
    safe["tags"].append("v2")
    safe["meta"]["count"] = 5
    print(f"    模板未被污染：{template}")
    print(f"    副本已修改：  {safe}")


# ===== 语法解析 =====
# 【9】★ list 别名坑：赋值不是复制
#   语法规则：`b = a` 只是把【引用】赋给 b，a 和 b 指向同一个 list 对象。
#   原理：Python 变量是"名字到对象的绑定"，不是"存储容器"。
#   ★ 后果：对 b 的【原地修改】会影响 a；对 a 的【重新赋值】不影响 b。
def demo_alias() -> None:
    print()
    print("=" * 60)
    print("【9】★ list 别名坑：赋值 = 绑定同一个对象")
    print("=" * 60)

    a = [1, 2, 3]
    b = a                                # ★ 不是复制！是给同一个对象起了第二个名字
    print(f"  a is b → {a is b}   （同一个对象）")

    b.append(4)                          # 原地修改，双方都受影响
    print(f"  b.append(4) 后：a={a}  b={b}   ← 互相影响")

    a = [9, 9]                           # 重新绑定名字，b 仍指向旧对象
    print(f"  a = [9,9] 后：a={a}  b={b}   ← 重新赋值只改名字绑定")
    print("    ★ 这是【不可变类型】看起来没坑的原因：整数赋值本身就是新建对象。")

    print()
    print("  ★ 正确复制的三种写法：")
    src = [1, 2, 3]
    print(f"    src[:]        = {src[:]}        切片拷贝")
    print(f"    list(src)     = {list(src)}        显式转换")
    print(f"    copy.copy(src)= {copy.copy(src)}        通用拷贝（任意对象）")
    print("    ★ 三者都是【浅拷贝】，元素仍是共享引用。")

    print()
    print("  ★ 嵌套结构的正确复制：")
    nested = {"data": [1, 2]}
    shallow_c = {**nested, "data": nested["data"][:]}   # 只复制需要独立的那一层
    print(f"    手动浅拷贝字典：{shallow_c}")
    print("    ★ 解包 {...} 复制外层 dict 键值，值（列表）仍共享 → 需再切片。")

    print()
    print("  ★ 函数传参同样遵循此规则（可变默认值的经典坑）：")
    print("    def f(x=[]): x.append(1); return x  →  每次调用共享同一个列表！")
    print(f"    第1次 {[1]}   第2次会变成 [1, 1]  ← 因为默认值只在【定义时】求值一次")


# ===== 语法解析 =====
# 【10】★ remove 与 pop 的本质区别
#   remove(x)：按【值】查找并删除第一个匹配项，不返回被删元素，找不到抛 ValueError
#   pop([i])：按【下标】删除并【返回】被删元素，默认 i=-1
#   ★ 选型：知道值用 remove；需要拿到被删内容或知道位置用 pop。
#   ★ 复杂度：remove 内部是 index + 两次遍历 O(n)；pop 从尾 O(1)。
def demo_remove_vs_pop() -> None:
    print()
    print("=" * 60)
    print("【10】★ remove 与 pop 的区别")
    print("=" * 60)

    print("  | 方法      | 参数   | 删除依据 | 返回值   | 找不到时     | 复杂度 |")
    print("  |-----------|--------|----------|----------|-------------|--------|")
    print("  | remove(x) | 值     | 第一个匹配| None    | ValueError  | O(n)  |")
    print("  | pop(i)    | 下标   | 第 i 个  | 被删元素 | IndexError  | O(1)尾|")
    print("  | del lst[i]| 下标   | 第 i 个  | 无(语句) | IndexError  | O(n)  |")
    print()

    # 场景1：按值删除
    a = ["red", "blue", "red"]
    rv = a.remove("red")
    print(f"  remove 用法：a.remove('red') 返回 {rv}，a={a}  ← 只删第一个")

    # 场景2：按下标删除并接收返回值
    b = [10, 20, 30]
    pv = b.pop(1)
    print(f"  pop 用法   ：b.pop(1) 返回 {pv}，b={b}  ← 拿到了被删元素")

    # 场景3：只删最后一项（高频）—— 两者都可，但 pop 更快且能拿到值
    c = [1, 2, 3]
    last = c.pop()                       # 不传参数默认弹最后，等价 pop(-1)
    print(f"  pop() 弹尾：返回 {last}，c={c}")

    print()
    print("  ★ 批量删除所有匹配项（remove 不支持 count 参数）：")
    d = [1, 2, 3, 2, 4, 2]
    before = len(d)
    # 倒序遍历删除：正序遍历会因元素左移而跳过元素
    for i in range(len(d) - 1, -1, -1):
        if d[i] == 2:
            d.pop(i)                      # ★ 倒序 + pop 是删除元素的标准安全模式
    print(f"    {before} 个元素 -> {len(d)} 个，删除后 {d}")

    # 更简洁的列表推导式方案（产生新列表）
    e = [1, 2, 3, 2, 4, 2]
    filtered = [x for x in e if x != 2]  # 推导式天然避免"边遍历边删"的问题
    print(f"    推导式方案：{filtered}")

    print()
    print("  ★ 性能对比（10 万列表删除首元素）：")
    t_remove = timeit.timeit(
        lambda: [x for x in [1] + list(range(100000)) if x != 1], number=100
    )
    t_pop = timeit.timeit(lambda: list(range(100000))[0], number=100)
    print(f"    删除首元素：pop {t_pop:.4f}s  vs  生成过滤列表 {t_remove:.4f}s")
    print("    ★ pop(0) 在列表头部是 O(n)（需要搬移所有元素），尾部才是 O(1)。")


# ===== 语法解析 =====
# 【11】★ sort 与 sorted 的本质区别
#   sort()   —— 绑定方法，原地排序，返回 None，会破坏原列表
#   sorted() —— 内置函数，返回新列表，对任意可迭代对象都可用
#   ★ 选型：要保留原顺序用 sorted；确定原列表不再需要（省内存）用 sort。
#   ★ 易错：x = x.sort() 会让 x 变成 None！
def demo_sort_vs_sorted() -> None:
    print()
    print("=" * 60)
    print("【11】★ sort 与 sorted 的区别")
    print("=" * 60)

    data = [3, 1, 2]
    data.sort()
    print(f"  sort()    → 原列表被改为 {data}，返回值 None（原地，省内存）")

    data2 = [3, 1, 2]
    new = sorted(data2)
    print(f"  sorted()  → 返回新列表 {new}，原列表 {data2} 不变")

    print()
    print("  ★ 经典错误：把 sort() 的返回值赋回去 = 全部丢失")
    bug = [3, 1, 2]
    bug = bug.sort()
    print(f"    bug = bug.sort() 之后  bug = {bug}   ← 数据没了！")

    print()
    print("  ★ sorted 的独有能力：对任意可迭代对象排序，list 没有的：")
    print(f"    sorted({3, 1, 2})      → {sorted({3, 1, 2})}       ← 集合")
    print(f"    sorted('dcba')       → {sorted('dcba')}       ← 字符串")
    print(f"    sorted((3, 1, 2))    → {sorted((3, 1, 2))}       ← 元组")
    print(f"    sorted(k for k in ...) → {sorted(x * x for x in range(4))}  ← 生成器")
    print(f"    sorted({{'b':1,'a':2}}) → {sorted({'b': 1, 'a': 2})}  ← dict 排的是键")

    print()
    print("  ★ 内存对比（10 万元素）：")
    t_sort = timeit.timeit(
        """
d = list(range(100000))
d.sort()
""",
        number=100,
    )
    t_sorted = timeit.timeit(
        """
d = list(range(100000))
r = sorted(d)
""",
        number=100,
    )
    print(f"    sort() {t_sort:.4f}s   sorted() {t_sorted:.4f}s")
    print("    ★ sort 省一次列表分配，所以略快；但 sorted 不会破坏原数据。")

    print()
    print("  ★ 补充：list.sort() 用的是 Timsort —— 自适应、稳定，O(n log n)")
    partly = [5, 3, 8, 1] * 5             # 已有序的小片段，Timsort 会识别成"run"
    t_part = timeit.timeit(lambda: sorted(partly), number=1000)
    t_rand = timeit.timeit(lambda: sorted(list(range(20))), number=1000)
    print(f"    近有序(20个*5) {t_part:.5f}s vs 完全有序(0-19) {t_rand:.5f}s")
    print("    ★ Timsort 对分段有序的数据接近 O(n)，这是它快的原因。")


# ===== 语法解析 =====
# 【12】方法速查表与常见综合技巧
def demo_summary() -> None:
    print()
    print("=" * 60)
    print("【12】list 常用方法速查 + 综合技巧")
    print("=" * 60)

    print("  【查】")
    print("    index(x)      返回首个匹配下标，找不到抛 ValueError      O(n)")
    print("    count(x)      返回出现次数，找不到返回 0                O(n)")
    print("    in / not in   成员判断                                  O(n)")
    print("  【增】")
    print("    append(x)     末尾加【一个元素】，返回 None               O(1)")
    print("    extend(it)    末尾【摊平】加入可迭代对象                  O(k)")
    print("    insert(i,x)   下标 i 插入一个元素（会搬移后续元素）        O(n)")
    print("  【删】")
    print("    remove(x)     按值删第一个，返回 None，找不到抛异常      O(n)")
    print("    pop([i])      按下标删并【返回】，默认 -1                 O(1)尾")
    print("    clear()       原地清空                                   O(n)")
    print("  【改】")
    print("    sort(key,rev) 原地排序，返回 None                        O(nlogn)")
    print("    reverse()     原地反转                                   O(n)")
    print("  【拷贝】")
    print("    copy()        浅拷贝（等价 lst[:]）                      O(n)")

    print()
    print("  ★ 综合技巧 1：列表去重的三种做法（按场景选）")
    data = [3, 1, 3, 2, 1]
    print(f"    保持顺序去重：{list(dict.fromkeys(data))}   ← 利用 dict 保序（3.7+）")
    print(f"    set 去重（乱序）：{sorted(set(data))}   ← 最快但不保序")
    seen: set[int] = set()                        # 手动去重保序
    uniq = [x for x in data if not (x in seen or seen.add(x))]
    print(f"    手动去重保序：  {uniq}")

    print()
    print("  ★ 综合技巧 2：矩阵/表格数据的常用变换（zip + 推导式）")
    matrix = [[1, 2, 3], [4, 5, 6]]
    print(f"    矩阵       {matrix}")
    print(f"    转置       {[list(r) for r in zip(*matrix)]}   ← zip(*m) 解包成参数")
    print(f"    拉平       {[x for row in matrix for x in row]}   ← 双重推导式")
    print(f"    逐行求和   {[sum(row) for row in matrix]}")

    print()
    print("  ★ 综合技巧 3：原地去重（保持顺序，不用额外集合内存）")
    arr = [1, 1, 2, 3, 2, 4, 4, 5]
    i = 0
    for x in arr:                                # 用写指针 i 原地覆盖
        if x not in arr[:i]:                     # 只与已确定的部分比较
            arr[i] = x
            i += 1
    del arr[i:]                                  # 截掉尾部残留
    print(f"    原地去重结果：{arr}")
    print("    ★ 原理：i 始终指向下一个写入位置，读指针遍历整个列表。")


def main() -> None:
    """主函数：按教学顺序演示列表的全部知识点。"""
    demo_create()
    demo_add()
    demo_delete()
    demo_update()
    demo_query()
    demo_slice()
    demo_sort()
    demo_copy()
    demo_alias()
    demo_remove_vs_pop()
    demo_sort_vs_sorted()
    demo_summary()

    print()
    print("=" * 60)
    print("小结")
    print("=" * 60)
    print("  1. list 是【可变序列】：append/pop 尾部操作 O(1)，insert/remove O(n)")
    print("  2. ★ 赋值 b = a 是【绑定同一对象】，不是复制；复制用 [:]/copy/deepcopy")
    print("  3. ★ append 加一个元素（不摊平），extend 摊平加入 —— 最易错的一对")
    print("  4. ★ remove 按值删（返回 None），pop 按下标删（返回元素）")
    print("  5. ★ sort 原地返回 None，sorted 返回新列表；x = x.sort() 会丢数据")
    print("  6. ★ 浅拷贝复制容器，深拷贝递归复制内部；性能敏感优先浅拷贝")
    print("  7. 切片返回新对象、负索引从尾数、切片赋值允许长度不一致")
    print("  8. 排序用 key 分离『比较规则』；Python 排序稳定，Timsort 自适应")
    print("  9. 有序数据用 bisect（O(log n)）替代 in/index（O(n)）")
    print(" 10. 边遍历边删必须倒序，或改用列表推导式生成新列表")


if __name__ == "__main__":
    main()