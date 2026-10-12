# -*- coding: utf-8 -*-
r"""
================================================================================
文件：05_loops.py
模块：02_basics（基础语法配套）

【本文件演示的语法点列表】
  1. for 循环：遍历可迭代对象（字符串/列表/元组/集合/字典/文件/range/生成器）
  2. range 三个参数的完整语义：start / stop / step，以及边界与陷阱
  3. while 循环：条件驱动，与 for 的适用场景区别
  4. for-else / while-else：else 的执行时机原理（最容易误解的语法）
  5. break / continue：跳出与跳过，对 else 的影响
  6. 嵌套循环与 break_flag 模式：为什么 break 只跳出【一层】
  7. zip 遍历：并行遍历多个序列，长度不等时的截断行为
  8. enumerate 遍历：同时拿下标与值，start 参数控制起始编号
  9. 循环中的 else/for 陷阱：break 会跳过 else
 10. 可迭代对象与迭代器的区别：iter() / next() / StopIteration
 11. 生成器表达式在循环中的惰性求值
 12. 性能对比：range vs while、列表推导 vs 循环（timeit 实测）

【设计意图】
  Python 只有两种循环，没有 C 的 do-while 和传统 for(;;)：
  (1) for 面向"可迭代对象"，把"遍历"抽象成协议，而非下标计数，
      因此 for 可以遍历文件、字典、生成器等一切可迭代对象；
  (2) while 是唯一的条件循环，配合 break 就能表达 do-while。
  for-else 的 else 不是"否则"，而是"【没有被打断】"——
  它只在循环【正常耗尽】时执行，一旦 break 就跳过。
  这是 Python 用来表达"搜索失败"这类逻辑的惯用法，比标志位优雅得多。

【预期输出摘要】
  [1] for 遍历各种可迭代对象（含字典的键/值/项）
  [2] range 三参数：起点/终点/步长，含负步长与边界不包含 stop
  [3] while 循环：计数器、累加、死循环的 break 退出
  [4] for-else：正常结束才执行 else，break 会跳过
  [5] break/continue 对 else 的影响
  [6] 嵌套循环：break 只跳一层，break_flag 模式解决
  [7] zip：并行遍历、stricter 参数、不等长截断
  [8] enumerate：下标+值，start 参数
  [9] 可迭代对象 vs 迭代器：next() 与 StopIteration
  [10] 性能实测：循环 vs 推导式
================================================================================
"""

import timeit


# ============================================================================
# 语法解析 1：for 循环与 range
# ============================================================================
# 【语法规则】
#   for 目标变量 in 可迭代对象:
#       循环体
#   range(stop)              从 0 到 stop-1，步长 1
#   range(start, stop)       从 start 到 stop-1
#   range(start, stop, step) 带步长；step 为负时反向递减
#   区间是【左闭右开 [start, stop)】，即包含 start，不包含 stop
#   range 是惰性的：range(1000000) 不会真的创建一百万个数字
# 【执行顺序】
#   for 循环的执行过程：
#     1. 调用 iter(可迭代对象) 取得迭代器
#     2. 反复调用 next(迭代器)，把返回值绑定到目标变量
#     3. 直到 next() 抛 StopIteration，循环结束
#   目标变量在每次迭代后【保留最后一次的值】(循环外仍可访问)
#   修改目标变量不影响遍历（遍历的是原对象的元素，不是变量）
# 【设计意图】
#   for 遍历的是"可迭代对象"而不是"下标+长度"，
#   这样把"如何取下一个元素"的责任交给了对象自己（迭代器协议），
#   于是 list、tuple、str、文件、字典、生成器都能用同一条 for 遍历。
#   range 之所以惰性，是为了避免为一个纯整数序列白白分配内存 ——
#   range(10**9) 也只占几十字节。
def demo_for_and_range():
    print("[1] for 循环与 range")

    # for 遍历各种可迭代对象
    print("    [遍历各种可迭代对象]")
    for item in "Python":
        print(f"      字符串: {item}")
        break  # 只演示第一个，避免刷屏
    for item in [1, 2, 3]:
        print(f"      列表: {item}")
        break
    for item in (1, 2, 3):
        print(f"      元组: {item}")
        break
    for item in {1, 2, 3}:
        print(f"      集合: {item}")
        break
    # 字典默认遍历【键】，三种遍历方式
    d = {"a": 1, "b": 2}
    for k in d:
        print(f"      字典键: {k}")
        break
    for k, v in d.items():
        print(f"      字典项: {k} -> {v}")
    for k in d.keys():
        print(f"      keys(): {k}")
        break
    for v in d.values():
        print(f"      values(): {v}")
        break

    # range 的三种参数
    print("\n    [range 三参数]")
    print(f"      list(range(5))         = {list(range(5))}          range(stop)")
    print(f"      list(range(2, 6))      = {list(range(2, 6))}       range(start, stop)")
    print(f"      list(range(2, 10, 3))  = {list(range(2, 10, 3))}   range(start, stop, step)")
    print(f"      list(range(10, 2, -1)) = {list(range(10, 2, -1))}  负步长：反向")
    print(f"      list(range(0, 10, -1)) = {list(range(0, 10, -1))}  负步长起点<终点 -> 空列表")

    # range 左闭右开
    print("\n    [左闭右开区间 [start, stop)]")
    print(f"      range(5) 含 0 不含 5: {list(range(5))}")
    print(f"      想含 5 就要写 range(6): {list(range(6))}")
    print("      -> 这是数学区间 [a, b) 的直接对应，也保证了 len(range(n)) == n")

    # range 是惰性的，不占内存
    print("\n    [range 的惰性]")
    r = range(10 ** 12)
    print(f"      range(10^12) 的长度 = {len(r):,}，但它只是三个数字，不占内存")
    print(f"      list(range(10^12)) 会耗尽内存，而 range 本身只需几十字节")
    print(f"      range 对象可直接索引：r[0]={r[0]}, r[999]={r[999]}")
    print(f"      r[10^12] 越界会抛 IndexError（因为要真的算这个值）")
    try:
        _ = r[10 ** 12]
    except IndexError as e:
        print(f"        r[10^12] -> IndexError: {e}   (索引需要求值，无法惰性返回)")

    # range 支持 in 判定（O(1)），但不支持和 都能真的迭代出全部元素
    print(f"      10**12 in range(10**12) = {10**12 in r}   (O(1) 常数时间，不遍历)")

    # 目标变量保留最后值
    print("\n    [目标变量的作用域]")
    for x in [10, 20, 30]:
        pass
    print(f"      循环后 x 仍存在 = {x}   (Python 没有块作用域)")

    # 修改目标变量不影响遍历
    print("\n    [修改目标变量不影响遍历]")
    nums = [1, 2, 3, 4]
    for num in nums:
        num = num * 100  # 修改循环变量，不会改原列表
        print(f"      num={num}", end=" ")
    print(f"\n      原 nums 未变 = {nums}   -> 修改目标变量只是改名字的绑定")

    # 反向遍历的正确方式
    print(f"      反向遍历 list(range(5,0,-1)) 或 reversed(range(5))，不要用 [::-1] 切片浪费内存")


# ============================================================================
# 语法解析 2：while 循环
# ============================================================================
# 【语法规则】
#   while 条件:
#       循环体
#   条件为真时执行，条件在【每次迭代前】检查
#   while 没有 do-while 形式，但可以用 break 模拟：
#       while True:
#           if cond: break
#   循环体必须改变条件，否则死循环（Py3 里死循环也能用 Ctrl+C 中断）
# 【执行顺序】
#   while 的执行顺序（与 for 的本质区别）：
#     1. 求值条件 -> 假则跳出
#     2. 执行循环体
#     3. 回到第 1 步
#   注意：条件在【进入循环前】就检查一次，所以 while 后的条件至少执行一次求值。
#   while-else 中，只有【条件为假而正常退出】才执行 else，被 break 跳出则不执行。
# 【设计意图】
#   Python 没有独立的 do-while，是因为 while True + break 已足够表达，
#   且 while-else 的 else 语义（正常结束才执行）弥补了"是否至少执行一次"的表达需求：
#   要写 do-while 只需先执行一次循环体，再写 while 条件。
def demo_while():
    print("[2] while 循环")

    # 基本 while：计数器
    i = 1
    while i <= 5:
        print(f"    第 {i} 次循环")
        i += 1  # 必须改变条件，否则死循环

    # while vs for：计数式循环优先用 for
    print("\n    [while 累加 vs for 累加]")
    total_while = 0
    i = 1
    while i <= 100:
        total_while += i
        i += 1
    total_for = sum(range(1, 101))  # 实际用 sum 更快
    print(f"    while 累加 1..100 = {total_while}")
    print(f"    sum(range)      = {total_for}   (内置 sum 用 C 实现，更快)")
    assert total_while == total_for

    # do-while 的模拟（Python 没有 do-while）
    print("\n    [模拟 do-while]")
    # 需求：至少执行一次循环体
    count = 0
    data = []
    while True:
        data.append(f"第{count}次")
        count += 1
        if count >= 3:
            break  # 满足条件才跳出
    print(f"    do-while 模拟（至少执行一次）: {data}")

    # while True + break 处理菜单/命令行循环的经典模式
    print("\n    [while True 处理不定次数输入]")
    commands = ["add 1", "quit"]
    processed = []
    while True:
        cmd = commands[len(processed)] if len(processed) < len(commands) else "quit"
        if cmd == "quit":
            processed.append("退出")
            break
        processed.append(f"处理: {cmd}")
    print(f"    处理序列 = {processed}")

    # while-else：正常结束才执行 else
    print("\n    [while-else]")
    n = 5
    while n > 0:
        n -= 1
    else:
        # 条件自然变假（没有被 break 打断）时执行
        print(f"    while-else 执行了，n 现在 = {n}   (自然耗尽)")

    n = 5
    while n > 0:
        n -= 1
        if n == 2:
            break  # 被 break 跳出
    else:
        print("    这行【不会执行】（被 break 打断了）")
    print("    -> while-else：else 只在循环【正常结束】（条件变假）时执行，break 会跳过它")

    # 死循环的演示（用计数器避免真死循环）
    print("\n    [避免死循环的防御]")
    def risky_loop(limit):
        count = 0
        while count < limit:
            # 如果这里忘记 count += 1，就是死循环
            count += 1
        return count
    print(f"    risky_loop(10) = {risky_loop(10)}   (有计数保护，安全)")


# ============================================================================
# 语法解析 3：break / continue / else 的完整语义
# ============================================================================
# 【语法规则】
#   break     立即跳出【最内层】循环
#   continue  跳过本次迭代剩余部分，进入下一次迭代
#   else      循环【正常耗尽】（没被 break 打断）时执行
#   组合：
#     break    -> 跳出循环，【不执行】else
#     continue -> 跳过本次，【会执行】else（如果最终耗尽）
#     正常结束 -> 执行 else
# 【执行顺序】
#   else 的执行时机是很多人误解的点：
#     for/while 的 else 子句在循环【正常终止】（迭代器耗尽或条件变假）后执行。
#     任何 break 都会直接跳出循环，跳过 else。
#     continue 不会跳过 else，因为它不是跳出循环，只是跳过本次。
#   这个设计是为了表达"搜索完成且没找到"这类语义：
#     for x in items:
#         if cond(x): break
#     else:
#         raise NotFound("没找到")  # 只有没 break 才执行 = 没找到
# 【设计意图】
#   for-else 的 else 不表示"否则"，而表示"【没有被打断】"。
#   它是 Python 里表达"搜索未命中"的惯用法，避免了定义标志位的样板代码。
def demo_break_continue_else():
    print("[3] break / continue / for-else 的完整语义")

    # break 的基本作用
    print("    [break：跳出最内层循环]")
    for i in range(10):
        if i == 3:
            print(f"    i=={i} 时 break")
            break
        print(f"    i={i}")

    # continue 的基本作用
    print("\n    [continue：跳过本次]")
    for i in range(6):
        if i % 2 == 0:
            continue  # 跳过偶数
        print(f"    奇数: {i}")

    # for-else：break 会跳过 else
    print("\n    [for-else：break 跳过 else]")
    # 案例1：找到就 break，不执行 else
    data = [1, 3, 5, 7]
    for x in data:
        if x > 4:
            print(f"    案例1：找到 {x} > 4，break（else 不执行）")
            break
    else:
        print("    案例1的 else【不会执行】（break 了）")
    # 案例2：没找到，正常耗尽，执行 else
    for x in [1, 2, 3]:
        if x > 100:
            print(f"    案例2：找到 {x}")
            break
    else:
        print("    案例2的 else【执行了】（没 break，循环正常耗尽）")

    # continue 不会跳过 else
    print("\n    [continue 不影响 else]")
    for i in range(5):
        if i == 2:
            continue  # 跳过 2，但不影响循环的正常耗尽
    else:
        print("    有 continue，但最终正常耗尽，else【仍然执行】")

    # for-else 搜索惯用法
    print("\n    [for-else 惯用法：查找未命中]")
    def find_first(items, pred):
        for idx, item in enumerate(items):
            if pred(item):
                return idx  # 找到就返回，不走 else
        else:
            return -1     # 只有【没找到】（正常耗尽）才走到这里

    print(f"    find_first([1,2,3,4], x>2) = {find_first([1,2,3,4], lambda x: x>2)}   (找到 3)")
    print(f"    find_first([1,2,3], x>10) = {find_first([1,2,3], lambda x: x>10)}   (没找到，返回 -1)")
    print("    -> for-else 把『找到返回 / 没找到返回 -1』表达得极其清晰，无需标志位")

    # for-else 做校验：确保循环至少找到了一个
    print("\n    [for-else 做校验]")
    nums = [1, 2, 3]
    has_positive = False
    for n in nums:
        if n > 0:
            has_positive = True
            break
    print(f"    传统方式 has_positive = {has_positive}")
    # for-else 版：找到就设标志，没找到走 else 报错
    try:
        for n in [1, 2, 3]:
            if n > 0:
                print(f"    for-else 版：找到正数 {n}")
                break
        else:
            raise ValueError("没有正数")
    except ValueError as e:
        print(f"    for-else 版 -> {e}   (不会触发，因为有正数)")

    try:
        for n in [-1, -2]:
            if n > 0:
                break
        else:
            raise ValueError("没有正数")
    except ValueError as e:
        print(f"    for-else 版（全负数）-> {e}   (else 报错)")

    # else 与 continue 配合的注意点
    print("\n    [易错：continue 不是 break]")
    # 有时候写成了 continue，误以为会跳到 else
    for i in range(3):
        if i == 1:
            continue
    else:
        print("    for i in range(3)，中间 continue，else 仍然执行 -> 循环还是正常结束")


# ============================================================================
# 语法解析 4：嵌套循环与 break_flag 模式
# ============================================================================
# 【语法规则】
#   嵌套循环：for 内嵌 for / while
#   break 只跳出【最内层】的那个循环
#   若想跳出【所有】层，有两种办法：
#     1. 把内层循环【提取成函数】，然后用 return 直接跳出
#     2. 用【标志位 break_flag】模式：设标志 + 外层检查 + break
# 【执行顺序】
#   break 的作用域是"最内层当前循环"。
#   嵌套循环中，内层 break 只结束内层，外层继续下一次迭代。
#   这是 C/Java 也一样的规则，但用标志位实现跳出多层会显得笨重。
# 【设计意图】
#   Python 没有 C 的 goto 或带标签的 break/continue。
#   原因：goto 会让控制流无法推理。
#   Python 的替代方案是【函数化】—— 把内层循环抽成函数，
#   用 return 天然实现"跳出多层"，这也符合 Python 的设计哲学。
#   标志位模式是"不想用函数"时的退路，但函数方案通常更清晰。
def demo_nested_loops():
    print("[4] 嵌套循环与 break_flag")

    # 基本嵌套
    print("    [基本嵌套：打印乘法表局部]")
    for i in range(1, 4):
        row = []
        for j in range(1, 4):
            row.append(f"{i}x{j}={i*j}")
        print(f"      {row}")

    # break 只跳出一层
    print("\n    [break 只跳最内层]")
    found = []
    for i in range(3):
        for j in range(3):
            if i == j:
                found.append((i, j))
                break  # 只跳出内层，外层继续
    print(f"    对角线元素（break 只跳内层，外层继续）= {found}")
    print("    -> 外层循环继续，所以收集到了 (0,0)(1,1)(2,2)")

    # 标志位模式：跳出所有层
    print("\n    [break_flag 模式：跳出所有层]")
    target_sum = 7
    result = None
    break_flag = False  # 标志位
    for i in range(1, 10):
        for j in range(1, 10):
            if i + j == target_sum:
                result = (i, j)
                break_flag = True  # 设置标志
                break               # 跳出内层
        if break_flag:             # 外层检查标志
            break                   # 跳出外层
    print(f"    break_flag 找到 i+j=={target_sum} = {result}")

    # 函数化方案（更 Pythonic，推荐）
    print("\n    [函数化方案：推荐]")

    def find_pair(target):
        # 把双层循环放进函数，return 天然跳出所有层
        for i in range(1, 10):
            for j in range(1, 10):
                if i + j == target:
                    return (i, j)  # 直接跳出函数，干净利落
        return None  # 没找到（等价于 for-else）

    result_func = find_pair(7)
    print(f"    find_pair(7) = {result_func}   (用 return 代替标志位，无标志位变量)")

    # 函数方案的本质就是 for-else
    def find_pair_else(target):
        for i in range(1, 10):
            for j in range(1, 10):
                if i + j == target:
                    return (i, j)
        else:
            return None  # 内层 for-else 不合适，用外层的也行

    print(f"    find_pair_else(7) = {find_pair_else(7)}")

    # 三重嵌套跳出（标志位仍笨拙，函数化更清晰）
    print("\n    [三重嵌套用函数化]")
    def deep_find(target):
        for i in range(5):
            for j in range(5):
                for k in range(5):
                    if i + j + k == target:
                        return (i, j, k)
        return None
    print(f"    deep_find(6) = {deep_find(6)}   (函数+return 三层循环跳出，非常干净)")

    # 嵌套 while + for
    print("\n    [嵌套 while + for]")
    count = 0
    results = []
    while count < 3:
        for x in ["a", "b"]:
            results.append(f"outer{count}-{x}")
        count += 1
    print(f"    混合嵌套 = {results}")

    # 嵌套循环的性能提示
    print("    -> 嵌套循环复杂度是乘积：外层 n 次 × 内层 m 次 = n*m 次操作，慎用大 n*m")
    print("    -> 优化手段：内层用推导式、外层用 map/filter、或者改变数据结构（如用 set/dict 替代查找）")


# ============================================================================
# 语法解析 5：zip 与 enumerate
# ============================================================================
# 【语法规则】
#   enumerate(可迭代对象, start=0)  产生 (下标, 值) 序列，start 控制起始编号
#   zip(可迭代1, 可迭代2, ...)      并行遍历多个序列，短的用完即止
#   zip(*可迭代的序列列表)          并行遍历【动态长度】的多个序列（转置）
#   zip(..., strict=True)  3.10+：长度不等时抛 ValueError（默认 False 静默截断）
#   zip 是【惰性】的，返回迭代器，不立即求值
#   reverse=True  3.8+：反向遍历（需序列支持 len 和下标）
# 【执行顺序】
#   zip 的执行：每次迭代，依次从每个可迭代对象取下一个元素，
#   任一取不到就停止（默认丢弃其余）。这叫"最短序列优先"。
#   enumerate：每次产生 (计数器, 下一个元素)，计数器自增。
#   两者都是惰性迭代器（生成器），不会一次性创建完整列表。
# 【设计意图】
#   enumerate 解决"手动维护计数器"的样板：
#       i = 0; for x in items: ...; i += 1   ->   for i, x in enumerate(items)
#   zip 解决"并行遍历多个序列"的样板，并天然处理了长度不等的情况。
#   注意 zip 与 itertools.zip_longest 的区别：
#   zip 遇到短的截断，zip_longest 遇到短的用 None/fillvalue 补齐。
def demo_zip_enumerate():
    print("[5] zip 与 enumerate")

    # enumerate：下标+值
    print("    [enumerate：下标+值]")
    fruits = ["苹果", "香蕉", "橙子"]
    for idx, fruit in enumerate(fruits):
        print(f"      {idx}: {fruit}")
    print("    -> 避免了手动 i=0; i+=1 的样板")

    # enumerate 的 start 参数：起始编号
    print("\n    [enumerate(start=)] 起始编号可自定义")
    for idx, fruit in enumerate(fruits, start=1):
        print(f"      第{idx}个: {fruit}")
    for idx, fruit in enumerate(fruits, start=10):
        print(f"      从10开始: {idx} -> {fruit}")
    print("    -> enumerate 支持 start/2，第二个位置参数就是 start")

    # enumerate + zip 组合
    print("\n    [enumerate + zip 组合]")
    scores = [92, 88, 75]
    for idx, (name, score) in enumerate(zip(fruits, scores), start=1):
        print(f"      第{idx}名 {name}: {score}")

    # zip：并行遍历两个序列
    print("\n    [zip：并行遍历]")
    names = ["张三", "李四", "王五"]
    ages = [28, 32, 25]
    for name, age in zip(names, ages):
        print(f"      {name} - {age}岁")

    # zip 不等长：短的截断
    print("\n    [zip 不等长：短的截断]")
    a = [1, 2, 3]
    b = ["x", "y"]  # 更短
    print(f"    zip([1,2,3], ['x','y'])   = {list(zip(a, b))}   (第3个元素 3 被丢弃，短的说了算)")
    short = ["x", "y"]
    print(f"    zip(['x','y'], [1,2,3])   = {list(zip(short, a))}   (换个位置，还是短的截断)")
    print("    -> zip 永远以【最短序列】为准，不管短的在哪一边")

    # strict 参数（3.10+）：长度不等时抛错，防止静默丢数据
    print("\n    [zip strict= 参数 3.10+]")
    print("    默认 strict=False：长度不等时【静默截断】，很容易悄悄丢数据")
    try:
        _ = list(zip(a, b, strict=True))
    except ValueError as e:
        print(f"    zip([1,2,3],['x','y'], strict=True) -> ValueError: {e}")
    print("    -> 生产代码建议一律加 strict=True，长度不等立刻暴露而不是静默丢数据")
    print(f"    长度相同时正常：{list(zip([1,2],['x','y'], strict=True))}")

    # zip(*...) 转置：动态长度
    print("\n    [zip(*) 转置：动态长度]")
    matrix = [[1, 2, 3], [4, 5, 6], [7, 8, 9]]
    transposed = list(zip(*matrix))
    print(f"    原矩阵 {matrix}")
    print(f"    转置后 {transposed}   (zip(*matrix) 把行变成列)")

    # zip 惰性
    print("\n    [zip 惰性]")
    z = zip(a, b)
    print(f"    type(zip(...)) = {type(z).__name__}   (是迭代器，不立即生成全部)")
    print(f"    next(z) = {next(z)}   (取一对)")

    # itertools.zip_longest：长的截断方向相反（长的用完，短补 None）
    print("\n    [itertools.zip_longest：补 None]")
    from itertools import zip_longest
    print(f"    zip_longest([1,2,3],['x','y']) = {list(zip_longest(a, b))}   (长的 x3，短补 None)")
    print(f"    zip_longest([1,2],['x','y'], fillvalue='?') = {list(zip_longest([1,2], ['x','y'], fillvalue='?'))}")

    # 排序时配合 key
    print("\n    [sorted + key + zip]")
    pairs = [("Alice", 25), ("Bob", 32), ("Charlie", 22)]
    sorted_pairs = sorted(pairs, key=lambda x: x[1])
    print(f"    按年龄排序 = {sorted_pairs}")
    names_only, ages_only = zip(*sorted_pairs)
    print(f"    转置后 names = {names_only}, ages = {ages_only}")


# ============================================================================
# 语法解析 6：可迭代对象 vs 迭代器
# ============================================================================
# 【语法规则】
#   可迭代对象 iterable：有 __iter__ 方法，能被 for 遍历
#       list str tuple set dict range 文件 生成器 ...
#   迭代器 iterator：有 __iter__ 和 __next__ 方法，能被 next() 调用
#   iter(x)    对可迭代对象返回迭代器（对迭代器返回自身）
#   next(it)   取下一个元素，耗尽时抛 StopIteration
#   可迭代对象 ≠ 迭代器：list 是可迭代但【不是】迭代器（可重复遍历）
#                    生成器既是可迭代也是迭代器（一次性的）
#   迭代器被耗尽后，再 next() 永远抛 StopIteration（不会重置）
#   生成器表达式 (x for x in y) 返回的是【迭代器】，不是列表
# 【执行顺序】
#   for 循环对可迭代对象的处理：
#     list: for 每次新建一个迭代器，从头遍历
#     生成器: for 直接复用那个一次性迭代器，遍历完就耗尽
#   这就是【列表可重复遍历、生成器只能遍历一次】的根本原因。
# 【设计意图】
#   区分"可迭代"与"迭代器"是为了在内存效率与易用性之间取得平衡：
#     list  占用 O(n) 内存，但可重复遍历、可随机访问
#     生成器 占用 O(1) 内存，但只能遍历一次
#   需要重复访问就用 list，只需要单次流式处理就用生成器。
def demo_iterable_vs_iterator():
    print("[6] 可迭代对象 vs 迭代器")

    # list 是可迭代对象，可以反复 for
    data = [1, 2, 3]
    print("    [list 可重复遍历]")
    for _ in range(2):
        print(f"      第1次遍历: {list(data)}")
        break
    # 每次 for 都创建新的迭代器
    it1, it2 = iter(data), iter(data)
    print(f"    两次 iter(data) 是同一个迭代器吗 = {it1 is it2}   (每次都新建)")

    # 生成器只能遍历一次
    print("\n    [生成器只能遍历一次]")
    gen = (x * 2 for x in range(5))
    print(f"    gen = {gen}")
    print(f"    第一次遍历: {list(gen)}")
    print(f"    第二次遍历: {list(gen)}   (已耗尽 -> 空列表)")

    # 生成器表达式返回的是迭代器
    print("\n    [生成器表达式 vs 列表推导式]")
    gen_expr = (x**2 for x in range(5))
    list_comp = [x**2 for x in range(5)]
    print(f"    type(生成器表达式) = {type(gen_expr).__name__}   (是迭代器/生成器)")
    print(f"    type(列表推导式)   = {type(list_comp).__name__}   (是 list)")
    print(f"    内存对比：生成器占 O(1)，列表占 O(n)")

    # next 与 StopIteration
    print("\n    [next 与 StopIteration]")
    it = iter([10, 20, 30])
    print(f"    next(it) = {next(it)}")
    print(f"    next(it) = {next(it)}")
    print(f"    next(it) = {next(it)}")
    try:
        next(it)
    except StopIteration:
        print(f"    next(it) -> StopIteration   (元素耗尽)")
    # 迭代器耗尽后永久耗尽
    try:
        next(it)
    except StopIteration:
        print(f"    再次 next(it) -> 仍是 StopIteration   (不会自动重置)")
    # list 重新 iter 后又可以了
    it2 = iter(data)
    print(f"    重新 iter([1,2,3]) 后 next = {next(it2)}   (新迭代器从头开始)")

    # 手动消费生成器（了解 next 机制）
    print("\n    [手动消费生成器]")
    def counter():
        n = 0
        while True:
            yield n       # 每次 yield 产生一个值并暂停
            n += 1
    c = counter()
    print(f"    取 3 个值: {[next(c) for _ in range(3)]}   (生成器每次 next 推进一次)")

    # 惰性验证：生成器不提前求值
    print("\n    [惰性验证]")
    side_effects = []
    def track(x):
        side_effects.append(x)
        return x
    lazy_gen = (track(x) for x in range(5))  # 创建时不执行任何 track
    print(f"    创建生成器后 side_effects = {side_effects}   (还没执行)")
    next(lazy_gen)
    print(f"    next() 一次后 side_effects = {side_effects}   (只执行了一个)")


# ============================================================================
# 语法解析 7：循环性能实测
# ============================================================================
# 【语法规则】
#   timeit.timeit(stmt, setup, number)  测量执行耗时
#   number  重复次数
#   repeat  多轮，返回列表，用 min() 取最佳值排除噪声
#   对比要点：等价任务、不同写法、相同数据量
# 【执行顺序】
#   性能对比的正确方法：
#     1. 保证【任务等价】（做同样的事），否则对比无意义
#     2. number 适中，控制在秒级
#     3. 用 min(repeat结果)，因为单次受系统调度噪声影响大
#     4. 结论要用"量级"而非"精确倍数"来描述
# 【设计意图】
#   教学重点不是背性能数字，而是理解【为什么快】：
#     推导式更快是因为它在解释器层面减少了逐条 bytecode 的循环开销，
#     并且常常把 O(n^2) 的嵌套改成 O(n) 的单次遍历。
def demo_performance():
    print("[7] 循环性能实测（timeit）")

    setup = "data = list(range(1000))"
    n = 1_000
    repeat = 3

    # 测试1：循环累加 vs sum 内置
    print("    [测试1] for 循环累加 vs sum()")
    t_loop = min(timeit.repeat(
        "total = 0\nfor x in data: total += x",
        setup=setup, number=n, repeat=repeat))
    t_sum = min(timeit.repeat(
        "total = sum(data)",
        setup=setup, number=n, repeat=repeat))
    print(f"      for 累加   {t_loop:.4f}s")
    print(f"      sum()      {t_sum:.4f}s   (快 {t_loop/t_sum:.1f} 倍)")
    print("    -> sum 是 C 实现的，直接遍历，省去 Python 层每条的循环开销")

    # 测试2：循环 append vs 列表推导式
    print("\n    [测试2] 循环 append vs 列表推导式")
    t_append = min(timeit.repeat(
        "result = []\nfor x in data: result.append(x*2)",
        setup=setup, number=n, repeat=repeat))
    t_comp = min(timeit.repeat(
        "result = [x*2 for x in data]",
        setup=setup, number=n, repeat=repeat))
    print(f"      for+append {t_append:.4f}s")
    print(f"      列表推导式  {t_comp:.4f}s   (快 {t_append/t_comp:.1f} 倍)")
    print("    -> 推导式在字节码层面优化了 append 调用，且没有显式循环变量")

    # 测试3：range vs while
    print("\n    [测试3] for range vs while 自增")
    t_for = min(timeit.repeat(
        "s = 0\nfor i in range(1000): s += i",
        setup="", number=n, repeat=repeat))
    t_while = min(timeit.repeat(
        "s = 0\ni = 0\nwhile i < 1000: s += i; i += 1",
        setup="", number=n, repeat=repeat))
    print(f"      for range   {t_for:.4f}s")
    print(f"      while 自增  {t_while:.4f}s   (慢 {t_while/t_for:.1f} 倍)")
    print("    -> for range 更优：省去条件判断与手动 i+=1，迭代器由 C 驱动")

    # 测试4：map vs 循环
    print("\n    [测试4] map vs 列表推导式 vs 循环")
    t_map = min(timeit.repeat(
        "result = list(map(lambda x: x*2, data))",
        setup=setup, number=n, repeat=repeat))
    print(f"      for+append   {t_append:.4f}s")
    print(f"      列表推导式    {t_comp:.4f}s")
    print(f"      map+lambda   {t_map:.4f}s   (比推导式慢 {t_map / t_comp:.1f} 倍)")
    print("    -> map+lambda 慢的原因：lambda 是【Python 函数调用】，每个元素都要进出一次函数")
    print("    -> 只有换成真正的 C 函数时 map 才有优势，例如：")
    t_map_abs = min(timeit.repeat(
        "result = list(map(abs, data))",
        setup=setup, number=n, repeat=repeat))
    print(f"      map(abs)     {t_map_abs:.4f}s   (无 lambda，直接调 C 函数)")
    print("    -> 经验法则：需要自定义逻辑就用【列表推导式】；只是套内置函数才考虑 map")
    print("    -> map 的真正优势是【惰性】：不加 list() 时不产出完整结果，节省内存")

    print("\n    -> 总结：")
    print("       1. 内置函数(sum/any/all/max) > 列表推导式 > 普通循环")
    print("       2. for 比 while 高效（省去条件判断与手动自增）")
    print("       3. 列表推导式 > for+append > map+lambda")
    print("       4. 但可读性和实际需求始终优先于微优化")


def main():
    demo_for_and_range()
    demo_while()
    demo_break_continue_else()
    demo_nested_loops()
    demo_zip_enumerate()
    demo_iterable_vs_iterator()
    demo_performance()
    print("[完成] 02_basics/05_loops.py 运行结束")


if __name__ == "__main__":
    main()