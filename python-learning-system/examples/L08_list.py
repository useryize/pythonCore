"""L08 列表：创建、本质与常用方法 —— 配套教案示例。

运行：python examples/L08_list.py

本脚本演示九件事：
    1. 列表的创建方式与「本质是动态数组」
    2. 索引、负索引与越界错误
    3. 增删改查：append / extend / insert / remove / pop / del 的区别
    4. 常用只读方法：index / count / in / reversed / copy
    5. 原地排序 sort 与返回新列表的 sorted/reversed
    6. 切片的全部形态（含负步长与切片赋值）
    7. 浅拷贝 vs 深拷贝：共享引用导致的数据被意外修改
    8. 列表当栈（append/pop）与当队列（append/pop(0) 的性能代价）
    9. 高频坑：append 返回 None、循环中删除元素、remove 与 del 的语义差

⚠️ 纯标准库，可直接运行。
"""

import copy                                   # 标准库：copy / deepcopy 浅拷贝与深拷贝
import sys                                    # 标准库：sys.getsizeof 查看对象内存占用
import time                                   # 标准库：用于对比 pop(0) 与 deque 的性能

# ============================================================
# 模块级常量
# ============================================================
QUEUE_SIZE = 100_000                          # 队列性能对比的数据规模
SCALE = 100_000                               # 「动态扩容」演示用：预留 10 万个空位


# ============================================================
# 第 1 部分：列表的创建与本质（动态数组）
# ============================================================
def demo_create_and_nature() -> None:
    """列表在 CPython 中是「动态数组」：一块连续的内存 + 长度 + 容量。"""
    print("【列表的创建与本质】\n")

    # 四种创建方式
    empty: list[int] = []                      # 方式 1：字面量（最常用）
    a = [1, 2, 3]
    b = list(a)                                # 方式 2：list(可迭代对象)
    c = a.copy()                               # 方式 3：copy()（等价于 a[:]）
    d = list(range(1, 4))                      # 方式 4：从 range 转换
    print(f"  四种创建方式结果一致: {a == b == c == d}   （但它们是不同对象：{len({id(x) for x in (a, b, c, d)})} 个）")

    # ⚠️ 危险写法：不要用 [0] * n 或 [None] * n 造「需要分别修改」的数据
    alias_problem = [[0]] * 3                  # 3 个格子指向【同一个】列表对象
    alias_problem[0].append(9)
    print(f"\n  ⚠️ [[0]] * 3 的陷阱: {alias_problem}")
    print(f"     三个格子其实是同一个对象: {alias_problem[0] is alias_problem[1] is alias_problem[2]}")

    # ✅ 正确写法：列表推导式，每个格子都是独立的新列表
    fixed = [[0] for _ in range(3)]
    fixed[0].append(9)
    print(f"  ✅ [[0] for _ in range(3)]: {fixed}   互不影响")

    # ⭐ 本质验证：列表是「连续的动态数组」
    # 追加元素时，Python 要在内存里找一块更大的连续空间，把老数据整体搬过去。
    # 为了减少搬运次数，CPython 不会「每次只加 1 个槽位」，而是超额分配约 12.5%。
    # 下面实测：从空列表开始连续 append，观察容量在哪些长度上「跳级」。
    growing: list[int] = []
    previous_size = 0
    growth_points: list[str] = []
    for i in range(30):                        # 连续追加 30 次
        growing.append(i)
        current_size = sys.getsizeof(growing)   # 列表占用的字节数
        if current_size != previous_size:       # 只有「内存变大」时才记录
            growth_points.append(f"长度 {len(growing):>2} → {current_size} 字节")
            previous_size = current_size
    print("\n  从空列表连续 append 30 次，内存「跳级」的时刻：")
    for point in growth_points:
        print(f"     {point}")
    print("  → 容量不是每次 +1，而是攒够一截再跳级，这就是「超额分配」：")
    print("     牺牲一点内存，换取平均 O(1) 的 append（不必每次都搬数据）")


# ============================================================
# 第 2 部分：索引、负索引与越界
# ============================================================
def demo_index() -> None:
    """下标从 0 开始，-1 表示最后一个。"""
    print("\n【索引与负索引】\n")
    fruits = ["苹果", "香蕉", "橙子", "葡萄", "西瓜"]

    # 正索引：从左往右 0, 1, 2, 3, 4
    print(f"  fruits[0] = {fruits[0]}   fruits[2] = {fruits[2]}")

    # 负索引：从右往左 -1, -2, -3, -4, -5（等价于 len + 负数）
    print(f"  fruits[-1] = {fruits[-1]}  （最后一个）")
    print(f"  fruits[-2] = {fruits[-2]}  （倒数第二个）")
    print(f"  fruits[-5] = {fruits[-5]}  （第一个，-len 刚好回到 0）")

    # 越界会抛 IndexError，这是「明确的错误」优于「静默返回 None」
    for bad_index in (5, -6):
        try:
            _ = fruits[bad_index]
        except IndexError as exc:
            print(f"  fruits[{bad_index}] → IndexError: {exc}   ⚠️ 越界了，长度只有 {len(fruits)}")

    # 赋值时越界同样报错
    try:
        fruits[9] = "荔枝"
    except IndexError as exc:
        print(f"  赋值 fruits[9] → IndexError: {exc}   ⚠️ 列表不会自动扩容")


# ============================================================
# 第 3 部分：增删改查——方法语义全景
# ============================================================
def demo_add_remove() -> None:
    """append / extend / insert / remove / pop / del 各管一件事，别混用。"""
    print("\n【增：append vs extend vs insert】\n")

    nums = [1, 2, 3]
    nums.append(4)                             # 追加一个元素
    print(f"  append(4) 后          : {nums}")

    nums.extend([5, 6])                        # 逐个追加多个元素
    print(f"  extend([5, 6]) 后     : {nums}")

    # ⚠️ 最经典的坑：append 一个列表不会展开，而是把列表当一个元素塞进去
    trap = [1, 2]
    trap.append([3, 4])
    print(f"\n  ⚠️ append([3, 4])   : {trap}   ← 元素个数是 {len(trap)}，不是 4")
    print(f"     类型检查: 第 2 个元素是 {type(trap[2]).__name__}")

    trap = [1, 2]
    trap.extend([3, 4])
    print(f"  ✅ extend([3, 4])  : {trap}   ← 元素个数是 {len(trap)}")

    # 第三个参数是插入位置，超出范围会追加到末尾（不报错）
    pos_demo = [1, 4]
    pos_demo.insert(1, 3)                      # 在下标 1 处插入 3
    pos_demo.insert(100, 99)                   # 位置超出长度 → 直接放最后
    print(f"\n  insert(1,3) 再 insert(100,99): {pos_demo}   ⚠️ 位置过大不会报错，只会追加")

    print("\n【删：remove vs pop vs del vs clear】\n")
    data = ["a", "b", "c", "b", "d"]
    dup = data.copy()

    popped = data.pop()                        # pop() 删最后一个，并【返回它】
    print(f"  pop() 返回 {popped!r}，剩下 {data}")

    data = dup.copy()
    data.remove("b")                           # remove 按【值】删第一个匹配
    print(f"  remove('b') → 返回 None，剩下 {data}   （只删了第一个 'b'）")

    data = dup.copy()
    del data[1]                                # del 按【下标】删，不返回值
    print(f"  del data[1]  → 剩下 {data}")

    data = dup.copy()
    value = data.pop(1)                        # pop(下标) 也可以，返回被删的元素
    print(f"  pop(1) 返回 {value!r}，剩下 {data}")

    data = dup.copy()
    data.clear()                               # 清空（等价于 del data[:]）
    print(f"  clear() 后    : {data}")

    # 删不存在的值会抛 ValueError（而不是静默无操作）
    try:
        dup.remove("不存在")
    except ValueError as exc:
        print(f"\n  ⚠️ remove('不存在') → ValueError: {exc}")
    print(f"     删不存在的【下标】也一样报错: ", end="")
    try:
        _ = dup.pop(99)
    except IndexError as exc:
        print(f"IndexError: {exc}")

    # ⚠️ remove 只删第一个：想删全部必须循环，或用列表推导式
    all_b = ["b"] * 5
    while "b" in all_b:                        # 循环 remove 会不断找到「下一个」
        all_b.remove("b")
    print(f"\n  ⚠️ 循环 remove 删光所有 'b': {all_b}")
    cleaner = [x for x in dup if x != "b"]    # ✅ 推导式更清晰
    print(f"  ✅ 推导式删光所有 'b'      : {cleaner}")

    print("\n【改：赋值、+=、乘法】\n")
    mutable = [1, 2, 3]
    mutable[0] = 100                           # 单个位置赋值
    mutable += [4, 5]                          # += 对列表是「原地扩展」
    print(f"  mutable[0]=100 且 += [4,5] → {mutable}")
    print(f"  乘法重复: ['ab'] * 3 = {['ab'] * 3}   ⚠️ 元素是同一个对象的引用")
    print(f"  ['ab'] * 3 里第 0 和第 1 项是同一对象: {(['ab'] * 3)[0] is (['ab'] * 3)[1]}")


# ============================================================
# 第 4 部分：常用只读与返回新对象的方法
# ============================================================
def demo_read_methods() -> None:
    """index / count / in / reversed / sorted：不修改原列表的方法。"""
    print("\n【常用只读方法】\n")

    nums = [3, 7, 1, 7, 4, 7]
    print(f"  原列表: {nums}")

    # index 找下标，count 找个数——两者都是 O(n)
    print(f"  index(7) = {nums.index(7)}    （第一次出现的位置）")
    print(f"  count(7) = {nums.count(7)}    （一共出现几次）")
    try:
        nums.index(999)
    except ValueError as exc:
        print(f"  index(999) → ValueError: {exc}   ⚠️ 找不到就报错")

    # in 判断「是否存在」，是布尔值；这与 index 是两回事
    print(f"  7 in nums = {7 in nums}        （布尔，只关心有没有）")
    print(f"  999 in nums = {999 in nums}")

    # ⚠️ reversed 返回的是「反向迭代器」，不是新列表
    rev = reversed(nums)
    print(f"\n  reversed(nums) 返回 {type(rev).__name__}，不是列表：{rev}")
    print(f"  list(reversed(nums)) = {list(rev)}")
    print(f"  原列表没变: {nums}   ✅")

    # reversed 迭代器只能消费一次
    again = reversed(nums)
    print(f"  ⚠️ 第一次消费: {list(again)}")
    print(f"     第二次消费: {list(again)}   ← 迭代器已被耗尽")

    # sorted 返回新列表，list.sort() 原地改并返回 None
    original = [5, 2, 8, 1]
    new_list = sorted(original, reverse=True)
    print(f"\n  sorted(original, reverse=True) = {new_list}，原列表 {original}   ✅ 原列表没变")

    inplace = [5, 2, 8, 1]
    result = inplace.sort(reverse=True)
    print(f"  inplace.sort() 返回 {result!r}，列表变成 {inplace}   ⚠️ 返回 None，且原地改了")


# ============================================================
# 第 5 部分：切片——Python 最优雅的语言特性之一
# ============================================================
def demo_slice() -> None:
    """切片语法是「三段式」：lst[start:stop:step]，stop 不含。"""
    print("\n【切片】\n")

    data = list(range(10))                     # [0, 1, 2, ..., 9]

    print(f"  原列表 : {data}")
    print(f"  data[2:5]   = {data[2:5]}     下标 2,3,4（stop 不含）")
    print(f"  data[:5]    = {data[:5]}      start 省略 = 从头")
    print(f"  data[5:]    = {data[5:]}      stop 省略 = 到尾")
    print(f"  data[:]     = {data[:]}       完整复制（新对象）")
    print(f"  data[-3:]   = {data[-3:]}     最后三个")
    print(f"  data[::2]   = {data[::2]}     每隔一个取一个")
    print(f"  data[::-1]  = {data[::-1]}    ⭐ 反转列表，不改原列表")
    print(f"  原列表没被反转: {data}")

    # ⭐ 切片是「浅拷贝」——这一点很重要，第 6 部分专门讲
    shallow = data[:3]
    shallow[0] = 999
    print(f"\n  切片副本改元素，原列表不受影响: data[0] 仍是 {data[0]}")
    print(f"  但切片是浅拷贝（内部嵌套列表仍是共享的），见下一节")

    # ⭐ 切片赋值：可以增、删、改，且长度可以不同
    board = [0] * 5                            # 五个格子
    board[1:4] = [7, 8]                        # 用 2 个元素替换 3 个 → 长度变了
    print(f"\n  切片赋值 board[1:4] = [7, 8] → {board}   （长度从 {5} 变成 {len(board)}）")

    board = [0] * 5
    board[1:4] = []                            # 删除一段
    print(f"  切片赋值 board[1:4] = []    → {board}   相当于 del board[1:4]")

    board = [0] * 5
    board[2:2] = [1, 1, 1]                     # 插入：起点 == 终点
    print(f"  切片赋值 board[2:2] = [1,1,1] → {board}   相当于 insert")

    # 切片超界不会报错，自动截断
    tolerant = [1, 2, 3]
    print(f"\n  data[0:100] = {data[0:100]}   ⚠️ 超出范围自动截断，不报错（与单点索引不同）")


# ============================================================
# 第 6 部分：浅拷贝 vs 深拷贝（最容易出事故的一节）
# ============================================================
def demo_copy_depth() -> None:
    """列表的拷贝只复制「最外层的容器」，不复制里面的对象。"""
    print("\n【浅拷贝 vs 深拷贝】\n")

    original = [1, [2, 3], [4, 5]]             # 嵌套列表：外层 3 个元素，第 2、3 项还是列表

    # 四种「拷贝」方式，其中前三种全是浅拷贝
    slice_copy = original[:]                   # 切片
    method_copy = original.copy()              # .copy()
    list_copy = list(original)                 # list()
    shallow_copy = copy.copy(original)         # copy.copy()

    print(f"  original = {original}")
    print(f"  四种拷贝结果内容都相同: "
          f"{slice_copy == method_copy == list_copy == shallow_copy == original}")

    # 关键区别：外层容器是不是同一个对象？
    print(f"\n  外层是同一个对象吗: {slice_copy is original}   "
          f"→ False，说明外层容器是新对象")
    print(f"  内层 [2,3] 是同一个对象吗: {slice_copy[1] is original[1]}   "
          f"→ True，说明内层对象被共享了！")

    # 事故现场：修改「内层」元素会影响原列表
    slice_copy[1].append(99)                  # 通过副本修改内层列表
    print(f"\n  ⚠️ slice_copy[1].append(99) 之后:")
    print(f"     original     = {original}   ← 原列表被改了！")
    print(f"     slice_copy   = {slice_copy}")

    # 重新开始，演示深拷贝
    fresh = [1, [2, 3], [4, 5]]
    deep = copy.deepcopy(fresh)                # 递归复制每一层
    deep[1].append(99)
    print(f"\n  ✅ deepcopy 之后修改内层:")
    print(f"     fresh = {fresh}   ← 原列表不受影响")
    print(f"     deep  = {deep}")

    # deepcopy 的代价：更慢、占更多内存
    big = [list(range(1000)) for _ in range(200)]
    t0 = time.perf_counter()
    _shallow = copy.copy(big)
    t1 = time.perf_counter()
    _deep = copy.deepcopy(big)
    t2 = time.perf_counter()
    print(f"\n  性能对比（{len(big)} × 1000 个元素）:")
    print(f"     copy.copy      : {(t1 - t0) * 1000:.2f} ms  （只复制外层指针）")
    print(f"     copy.deepcopy  : {(t2 - t1) * 1000:.2f} ms  （递归复制 {len(big) * 1000} 个对象）")
    print(f"  规则：元素都是不可变的（数字/字符串）→ 用浅拷贝；含可变对象 → 用 deepcopy")

    # ⚠️ 赋值「不是拷贝」——连外层都是同一个对象
    alias = fresh                              # 直接赋值，只是多了一个名字
    alias[0] = 111
    print(f"\n  ⚠️ 赋值不是拷贝: fresh[0] 变成了 {fresh[0]}，因为 alias 就是 fresh 本身")


# ============================================================
# 第 7 部分：列表当栈与当队列
# ============================================================
def demo_stack_queue() -> None:
    """栈用 append/pop(末尾) 是 O(1)；队列用 pop(0) 是 O(n)，要用 collections.deque。"""
    print("\n【列表当栈与当队列】\n")

    # 栈（后进先出 LIFO）：append + pop() 都在末尾，O(1)
    stack = []
    for item in ["a", "b", "c"]:
        stack.append(item)                     # push
        print(f"  入栈 {item!r} → 栈: {stack}")
    while stack:
        print(f"  出栈 {stack.pop()!r} → 栈: {stack}")

    # 队列（先进先出 FIFO）：list.pop(0) 需要把后面所有元素往前挪，O(n)
    print()
    naive_queue = [1, 2, 3]
    naive_queue.append(4)
    print(f"  队列入队 4 → {naive_queue}")
    print(f"  ⚠️ 出队 pop(0) = {naive_queue.pop(0)}，代价是后面 {len(naive_queue)} 个元素全部前移（O(n)）")

    # ⚠️ 更糟的是「头部插入」：insert(0, x) 同样是 O(n)
    head_demo = [1, 2, 3]
    head_demo.insert(0, 0)
    print(f"  ⚠️ insert(0, 0) = {head_demo}，同样是 O(n)（每个元素都要后移）")

    # 实测：pop(0) 在大数据上明显慢于 deque.popleft()
    from collections import deque               # 标准库：双端队列，O(1) 头部操作

    lst = list(range(QUEUE_SIZE))
    dq = deque(range(QUEUE_SIZE))
    for _ in range(1000):
        pass                                   # 预热，避免首次调用的干扰

    t0 = time.perf_counter()
    for _ in range(10_000):
        if lst:
            lst.pop(0)                         # O(n)：最坏要移动 10 万个元素
    t1 = time.perf_counter()
    for _ in range(10_000):
        if dq:
            dq.popleft()                       # O(1)：只动链表头部
    t2 = time.perf_counter()
    print(f"\n  出队 1 万次（数据规模 {QUEUE_SIZE:,}）:")
    print(f"     list.pop(0)     : {(t1 - t0) * 1000:.1f} ms")
    print(f"     deque.popleft() : {(t2 - t1) * 1000:.1f} ms   ✅ 生产环境请用 deque 做队列")


# ============================================================
# 第 8 部分：高频坑演示
# ============================================================
def demo_pitfalls() -> None:
    """本节把初学者最容易踩的四个坑集中跑一遍。"""
    print("\n【高频坑集中演示】\n")

    # 坑 1：append / insert / extend 都返回 None，不能赋值
    print("  坑 1：append 返回 None")
    bad = [1, 2]
    result = bad.append(3)                      # ❌ 常见错误写法
    print(f"     result = bad.append(3) 得到 {result!r}，而 bad 是 {bad}")
    print(f"     → 所以 'bad.append(3) or bad' 这种写法会返回 bad 本身，不是 None")

    # 坑 2：循环中删除元素会「漏掉」一部分元素
    # 原因：for 循环靠内部下标前进，而删除让后面的元素【整体左移一位】，
    #       于是紧跟在被删元素后面的那个元素被跳过了。
    print("\n  坑 2：循环中删除元素")
    buggy = [5, 1, 2, 3, 4, 6]
    for num in buggy:
        if num < 5:
            buggy.remove(num)                  # ❌ 删掉 1 后，2 左移到下标 1，下轮直接看 3
    print(f"     源列表 [5, 1, 2, 3, 4, 6]，条件 num < 5")
    print(f"     ❌ 边遍历边 remove: {buggy}   ← 2 和 4 被漏掉了（正确应是 [5, 6]）")

    # ⚠️ 更隐蔽的情况：数据「碰巧」看起来是对的，因为遍历顺序恰好能掩盖问题
    lucky = [1, 2, 3, 4, 5, 6, 7, 8]
    for num in lucky:
        if num % 2 == 0:
            lucky.remove(num)
    print(f"     ⚠️ 但 [1..8] 删偶数得到 {lucky}，恰好是对的！")
    print(f"        → 这说明该 bug【时灵时不灵】，比稳定出错更危险：测试通过、上线出错")

    # ✅ 正确做法 1：遍历副本（推荐，最贴近原意）
    fixed1 = [5, 1, 2, 3, 4, 6]
    for num in fixed1[:]:                      # 注意这里的 [:]，遍历的是副本
        if num < 5:
            fixed1.remove(num)
    print(f"     ✅ 遍历副本 fixed1[:]: {fixed1}")

    # ✅ 正确做法 2：用推导式重建（更简洁，且只遍历一次）
    fixed2 = [num for num in [5, 1, 2, 3, 4, 6] if num >= 5]
    print(f"     ✅ 推导式重建        : {fixed2}")

    # ❌ 最糟的情况：想「清空列表」，结果只删了一半
    half = [1, 2, 3, 4, 5]
    for num in half:
        half.remove(num)                       # 每删一个，后面的都左移
    print(f"     ❌ 循环里删【全部】: [1,2,3,4,5] → {half}   ← 只删了一半")

    # 坑 3：remove 与 del 的语义完全不同
    print("\n  坑 3：remove 按值、del 按下标")
    items = [1, 2, 3, 2, 4]
    copy_a = items.copy()
    copy_a.remove(2)                            # 删【值】2 的第一次出现
    print(f"     remove(2) → {copy_a}   ← 只删了第一个 2")

    # 坑 4：sort 与 sorted 的返回值
    print("\n  坑 4：原地方法返回 None")
    target = [3, 1, 2]
    sorted_copy = sorted(target)
    print(f"     sorted(target) = {sorted_copy}，target 仍是 {target}  ✅")
    target.sort()
    print(f"     target.sort() 之后 target = {target}  ⚠️ sort 没有返回值可用")


# ============================================================
# 第 9 部分：自检断言
# ============================================================
def verify_list() -> None:
    """用断言验证本课所有关键结论，防止示例与文档说法不一致。"""
    print("【自检断言】")

    # 增删改查
    xs = [1, 2, 3]
    assert xs.append(4) is None                 # append 返回 None
    assert xs == [1, 2, 3, 4]
    assert xs.extend([5]) is None               # extend 也返回 None
    assert xs == [1, 2, 3, 4, 5]
    assert xs.pop() == 5 and xs == [1, 2, 3, 4]     # pop 返回被删的元素
    xs.remove(1)                                # remove 不返回任何值
    assert xs == [2, 3, 4]
    assert xs.index(3) == 1 and xs.count(3) == 1

    # 索引与切片
    ys = list(range(10))
    assert ys[-1] == 9
    assert ys[2:5] == [2, 3, 4]
    assert ys[::-1] == list(reversed(ys))      # 反转切片 == reversed
    assert ys[:100] == ys                      # 切片超界不报错
    assert ys[:] == ys and ys[:] is not ys     # 切片是浅拷贝（不同对象）

    # 排序
    zs = [3, 1, 2]
    assert sorted(zs) == [1, 2, 3] and zs == [3, 1, 2]      # sorted 不改原列表
    assert zs.sort() is None                                 # sort 返回 None
    assert zs == [1, 2, 3]

    # ⭐ 浅拷贝与深拷贝的核心区别
    orig = [1, [2, 3]]
    shallow = orig[:]                          # 浅拷贝：外层新，内层共享
    shallow[1].append(4)
    assert orig == [1, [2, 3, 4]]              # ⚠️ 原列表被连带修改
    orig2 = [1, [2, 3]]
    deep = copy.deepcopy(orig2)
    deep[1].append(4)
    assert orig2 == [1, [2, 3]]                # ✅ 深拷贝互不影响

    # 栈与队列
    st = []
    st.append("a")
    st.append("b")
    assert st.pop() == "b" and st == ["a"]      # 后进先出

    # 循环中删除的坑：⚠️ 结果依赖数据，必须用实测值而不是想当然
    buggy = [5, 1, 2, 3, 4, 6]
    for num in buggy:
        if num < 5:
            buggy.remove(num)
    assert buggy == [5, 2, 4, 6]               # ⚠️ 2 和 4 被漏掉了（正确应是 [5, 6]）
    assert [n for n in [5, 1, 2, 3, 4, 6] if n >= 5] == [5, 6]   # ✅ 推导式才对

    # 循环中删除的正确写法：遍历副本
    fixed = [5, 1, 2, 3, 4, 6]
    for num in fixed[:]:
        if num < 5:
            fixed.remove(num)
    assert fixed == [5, 6]

    print("✅ verify_list 全部断言通过")


# ============================================================
# 程序入口
# ============================================================
def main() -> None:
    """按教学顺序调用全部演示函数。"""
    print("=" * 64)
    print("L08 · 列表：创建、本质与常用方法")
    print("=" * 64)
    demo_create_and_nature()
    demo_index()
    demo_add_remove()
    demo_read_methods()
    demo_slice()
    demo_copy_depth()
    demo_stack_queue()
    demo_pitfalls()
    print("\n" + "-" * 64)
    verify_list()
    print("\n🎉 L08 演示结束")


# 标准入口约定：直接运行本文件执行 main()，被 import 时不执行
if __name__ == "__main__":
    main()