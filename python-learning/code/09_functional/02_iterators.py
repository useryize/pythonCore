# -*- coding: utf-8 -*-
"""
02_iterators.py —— 迭代器协议与自定义迭代

【演示的语法点】
1. 可迭代对象（Iterable）vs 迭代器（Iterator）的区别
2. 协议的本质：只认方法，不认类型 —— 只要有 __iter__ 就是可迭代的
3. __iter__/__next__ 手写自定义迭代器；__iter__ 返回 self 的「自迭代器」
4. __next__ 必须抛 StopIteration 来结束；不抛就是死循环/无限迭代
5. for 循环的完整展开：iter() -> __iter__，next() -> __next__，while not StopIteration
6. 可迭代对象 vs 迭代器的能力对比（len/索引/多次遍历）
7. __length_hint__ 与 __sizeof__：给 len() 的机会（list/tuple 之外的容器）
8. 反向迭代 __reversed__、切片 __getitem__ 协议
9. itertools.islice —— 【惰性切片】，为什么它不是真的切片
10. 无限序列：count/cycle/repeat —— 只能配 islice 取有限个
11. 生成器函数 vs 类式迭代器：等价性与选用场景
12. 迭代器协议的健壮性：__iter__ 返回非迭代器会怎样（TypeError）

【预期输出摘要】
- for x in obj 的输出，与手写 while + next() 完全一致
- 自定义 Range 迭代器支持 islice 惰性取子区间
- 无限序列必须用 islice 截断，否则 islice 本身也停不下来
- 同一对象 is_iter() is obj -> True 说明它是「自迭代器」
"""
import itertools
from collections.abc import Iterable, Iterator, Sequence


# ======================================================================
# 语法解析 1：Iterable 与 Iterator 的本质区别
# ======================================================================
#
# 语法规则（协议式鸭子类型）：
#   可迭代对象：实现 __iter__() -> 返回一个「迭代器」
#   迭代器：  实现 __iter__()（返回自己）+ __next__() -> 返回下一个元素，
#             没有更多元素时【必须】抛 StopIteration
#
# 类比：
#   Iterable = 有一张「路线图」的向导   -> 只能反复问"下一站在哪"
#   Iterator  = 「正在带队」的向导     -> 自己记着走到哪了，且只能走一遍
#
# 判定：
#   isinstance(x, Iterable)  看它有没有 __iter__
#   isinstance(x, Iterator)   看它有没有 __next__
#   iter(x) 是【永不】对普通 Iterable 报错的内置函数


def demo_iterable_vs_iterator() -> None:
    print("=" * 68)
    print("【1】可迭代对象 vs 迭代器")
    print("=" * 68)

    lst = [1, 2, 3]
    it = iter(lst)                     # list.__iter__ 返回一个 list_iterator

    print(f"list 是 Iterable? {isinstance(lst, Iterable)}")
    print(f"list 是 Iterator? {isinstance(lst, Iterator)}   <- 容器不是迭代器")
    print(f"iter(list) 是 Iterator? {isinstance(it, Iterator)}")
    print(f"生成器是 Iterator? {isinstance((x for x in [1]), Iterator)}")
    print(f"字符串是 Iterable? {isinstance('abc', Iterable)}  "
          f"但不可重复 next（每次都新建迭代器）")

    # 关键对比表
    print("\n能力对比：")
    print(f"{'对象':<18}{'可迭代':<8}{'迭代器':<8}{'len':<6}{'可重复遍历'}")
    print("-" * 50)
    for name, obj in [
        ("list [1,2,3]", lst),
        ("iter([1,2,3])", it),
        ("range(3)", range(3)),
        ("生成器表达式", (x for x in [1, 2, 3])),
    ]:
        print(f"{name:<18}{str(isinstance(obj, Iterable)):<8}"
              f"{str(isinstance(obj, Iterator)):<8}"
              f"{str(hasattr(obj, '__len__')):<6}"
              f"{'是' if isinstance(obj, Sequence) else '否'}")

    print("\n结论：容器「能被遍历」但自己「不是迭代器」；")
    print("      容器可以反复 iter()，迭代器只能消费一次。")


# ======================================================================
# 语法解析 2：手写 __iter__ / __next__ 迭代器
# ======================================================================
#
# 语法规则：class C:
#               def __iter__(self): return self     # 自迭代器写法
#               def __next__(self):                  # 必须返回元素或抛 StopIteration
#                   ...
#                   raise StopIteration
#
# 为什么 __iter__ 返回 self？
#   迭代协议的设计是「__iter__ 把自己变成迭代器」。
#   这类对象叫【自迭代器】(self-iterating)，好处是可重复遍历 —— 因为每次 iter() 都拿回自己，
#   但【状态是共享的】，所以多个 for 嵌套遍历会互相干扰（下面 demo3 演示这个坑）


class Countdown:
    """经典示例：从 start 倒数到 stop，步长 -1。"""

    def __init__(self, start: int, stop: int = 0, step: int = -1) -> None:
        self.current = start
        self.stop = stop
        self.step = step
        # 方向与 step 不一致时永远到不了 stop -> 启动时就拒绝（fail fast）
        if (self.step > 0 and start > stop) or (self.step < 0 and start < stop):
            raise ValueError(f"步长 {step} 与区间 [{start} -> {stop}] 矛盾")

    def __iter__(self) -> "Countdown":        # 返回类型注解可写字符串（前向引用）
        # 每次 iter() 都返回【新的】游标，才能安全地嵌套遍历
        return Countdown(self.current, self.stop, self.step)

    def __next__(self) -> int:
        if self.step > 0 and self.current > self.stop:
            raise StopIteration                # 结束的唯一正确方式
        if self.step < 0 and self.current < self.stop:
            raise StopIteration
        value = self.current
        self.current += self.step              # 在【返回之后】才推进游标
        return value


class SelfIterating:
    """反例：__iter__ 返回 self —— 不可重复遍历，嵌套 for 会互相抢状态。"""

    def __init__(self, data: list[int]) -> None:
        self.data = data
        self.index = 0

    def __iter__(self) -> "SelfIterating":
        return self                           # 注意：返回自己

    def __next__(self) -> int:
        if self.index >= len(self.data):
            raise StopIteration
        value = self.data[self.index]
        self.index += 1
        return value


def demo_custom_iterator() -> None:
    print()
    print("=" * 68)
    print("【2】手写自定义迭代器")
    print("=" * 68)

    # for 循环内部到底发生了什么
    print("for 循环的完整展开：")
    for x in Countdown(5):
        print(f"  倒计时 {x}")
    print("↑ 这 6 行实际等价于：")
    _it = iter(Countdown(5))
    while True:
        try:
            _v = next(_it)
            print(f"  倒计时 {_v}")
        except StopIteration:
            break

    # 双向/步进区间
    print(f"\nCountdown(2, 10, 3) -> {list(Countdown(2, 10, 3))}")
    print("（参数校验拦住了非法区间，见下面）")
    try:
        Countdown(1, 10, -1)
    except ValueError as e:
        print(f"构造时报错: {e}")

    # 对比：自迭代器的重复遍历陷阱
    print("\n自迭代器（__iter__ 返回 self）的陷阱：")
    si = SelfIterating([1, 2, 3])
    print(f"  is_iter(si) is si -> {iter(si) is si}   （同一个对象）")
    print(f"  第一次遍历: {list(si)}")
    print(f"  第二次遍历: {list(si)}   <- 空了！状态被上次消费掉")
    print("  这就是为什么标准库的迭代器大多让 __iter__ 返回【新游标】。")


# ======================================================================
# 语法解析 3：for 循环的三步展开与嵌套遍历
# ======================================================================


def demo_for_expansion() -> None:
    print()
    print("=" * 68)
    print("【3】for 循环语义展开")
    print("=" * 68)

    # 展开 1：等价改写
    def for_loop(it: Iterable[int]) -> list[int]:
        out = []
        # for 的等价伪码：iter = iter(it); while True: try: next() except StopIteration: break
        for x in it:
            out.append(x)
        return out

    print(f"for 遍历 Countdown(4): {for_loop(Countdown(4))}")

    # 展开 2：提前 break 对生成器的影响 —— 关键在「变量是否还被引用」
    def gen_with_break() -> Iterator[int]:
        try:
            yield 1
            yield 2
            yield 3
        finally:
            print("    [生成器] finally 执行（生成器被关闭/GC）")

    print("A) 直接 for + break，生成器是临时变量：")
    for v in gen_with_break():
        print(f"  在 {v} 处 break")
        break
    print("  -> for 结束后临时生成器无人引用，被 GC，close() 触发 finally\n")

    print("B) 生成器赋给变量 g，for 提前 break：")
    g = gen_with_break()
    for v in g:
        break
    print(f"  g 仍被引用 -> 生成器还活着: gi_frame is not None = {g.gi_frame is not None}")
    print("  -> finally 【还没执行】，因为没人 close 它\n")

    g.close()      # 显式关闭，才真正触发 finally
    print("  显式 g.close() 后 -> finally 执行完毕")

    # 展开 3：__iter__ 返回非迭代器 -> TypeError
    print("\n协议健壮性：")
    class BadIterable:
        def __iter__(self):
            return 42                      # 错误：返回的不是迭代器
    try:
        for _ in BadIterable():
            pass
    except TypeError as e:
        print(f"  __iter__ 返回非迭代器 -> TypeError: {e}")

    class MissingNext:
        def __iter__(self):
            return self
    try:
        for _ in MissingNext():
            pass
    except TypeError as e:
        print(f"  缺 __next__ -> TypeError: {e}")

    print("结论：协议只要求方法【存在】，不要求类型 —— 但类型错误会在 for 里爆出来。")


# ======================================================================
# 语法解析 4：可选协议 —— __len__ / __getitem__ / __reversed__
# ======================================================================
#
# 语法规则：
#   __len__        -> 让 len(obj) 可用，同时给 list(obj) 一个【预分配提示】
#   __getitem__(i)  -> 让 obj[i] 可用；这是【老式迭代协议】：
#                      只要有它，iter(obj) 就能靠 index=0,1,2... 无限试出来
#   __reversed__   -> 让 reversed(obj) 高效（否则会退化成用 __len__+__getitem__ 倒序取）


class SequenceLike:
    """用 __getitem__ 实现老式可迭代：不写 __iter__ 也能 for。"""

    def __init__(self, items: list[int]) -> None:
        self._items = items

    # 只有 __getitem__，没有 __iter__：Python 的 for 会依次尝试 index 0,1,2...
    # 直到 IndexError，于是「看起来」像个序列
    def __getitem__(self, index: int) -> int:
        return self._items[index]      # 越界时自动抛 IndexError，for 由此结束


class RichSequence:
    """完整协议容器：支持 len / 索引 / 切片 / 反向迭代。"""

    def __init__(self, items: list[int]) -> None:
        self._items = list(items)

    def __iter__(self) -> Iterator[int]:
        # 首选：显式 __iter__，语义清晰、性能可控
        return iter(self._items)

    def __len__(self) -> int:
        return len(self._items)

    def __getitem__(self, key):
        # key 可以是 int（索引）或 slice（切片），所以【故意不写返回类型注解】
        return self._items[key]

    def __reversed__(self) -> Iterator[int]:
        # 提供它，reversed() 才不用退化实现
        return iter(reversed(self._items))


class HintedContainer:
    """演示 __length_hint__：给 list() 一个容量预估，减少扩容。"""

    def __init__(self, n: int) -> None:
        self.n = n

    def __length_hint__(self) -> int:
        return self.n                  # Python 会把它当作「大概有多少个元素」的提示

    def __iter__(self) -> Iterator[int]:
        for i in range(self.n):
            yield i


def demo_optional_protocols() -> None:
    print()
    print("=" * 68)
    print("【4】可选协议：__len__ / __getitem__ / __reversed__")
    print("=" * 68)

    s = SequenceLike([10, 20, 30])
    print(f"只有 __getitem__ 也能遍历: {list(s)}")
    print(f"甚至支持索引: s[1] = {s[1]}")
    print(f"  iter(s) 可用（老式协议回退），但 isinstance(s, Iterable) = "
          f"{isinstance(s, Iterable)}")
    print("  ^ 反直觉点：Iterable ABC 靠 __subclasshook__ 检查【有没有 __iter__】，")
    print("    而老式对象只有 __getitem__。iter() 能用（内部逐个试 index），")
    print("    但 isinstance 会说 False —— 所以【新代码别只写 __getitem__】。")

    r = RichSequence([1, 2, 3, 4, 5])
    print(f"\n完整容器: len={len(r)}, r[1:4]={r[1:4]}, r[-1]={r[-1]}")
    print(f"reversed(r) = {list(reversed(r))}  （走了 __reversed__）")
    print(f"类型: {type(r).__name__}，reversed 结果类型: "
          f"{type(reversed(r)).__name__}")

    h = HintedContainer(5)
    print(f"\n__length_hint__ = {h.__length_hint__()}")
    print(f"list(h) = {list(h)}")
    print("用途：list(obj)/tuple(obj) 会预分配，避免多次 realloc。")


# ======================================================================
# 语法解析 5：itertools.islice —— 惰性切片
# ======================================================================
#
# 语法规则：
#   islice(iterable, stop)             等价于 it[:stop]
#   islice(iterable, start, stop)      等价于 it[start:stop]
#   islice(iterable, start, stop, step)等价于 it[start:stop:step]
#
# 为什么需要它？
#   真实切片 it[1000:1010] 会【先消费前 1000 个元素】（对生成器是逐个产出并丢弃），
#   islice(iter(it), 1000, 1010) 同样要跳过，但 islice 不【复制】目标区间，
#   且对 list 这类支持索引的对象可以用「跳过式」迭代（islice 对 list 会走 PySequence 快速路径）。
#
# 关键：islice【不吃】整个可迭代对象，只吃到你 stop 为止 —— 但对无限序列必须配合 islice 停。


def demo_islice() -> None:
    print()
    print("=" * 68)
    print("【5】itertools.islice 惰性切片")
    print("=" * 68)

    data = list(range(20))

    print(f"原列表     : {data}")
    print(f"[2:5]      : {data[2:5]}      （真切片，生成新 list）")
    print(f"islice(,2,5): {list(itertools.islice(data, 2, 5))}   （不复制全量）")
    print(f"islice(2)   : {list(itertools.islice(data, 2))}      等价 data[:2]")
    print(f"islice(,0,10,2): {list(itertools.islice(data, 0, 10, 2))}  等价 data[::2][:5]")

    # islice 的计数单位是「【产出】了几个元素」，不是「处理了多少行」。
    # 下面这个生成器只产出 5 项，islice(.,50,55) 要等到第 55 个【产出】，
    # 可生成器在第 5 个就结束了 -> 结果是空列表。这是初学者最常踩的坑。
    def gen_tagged() -> Iterator[str]:
        for i in range(100):
            yield f"第{i}项"            # 每项都产出，所以产出数 == 处理的行数

    print(f"\n产出的 50..54 项: {list(itertools.islice(gen_tagged(), 50, 55))}")

    # 对比：筛选型生成器（产出数 << 处理数）上 islice 会【失效】
    def gen_filtered() -> Iterator[str]:
        for i in range(100):
            if 50 <= i < 55:            # 只有 5 项真正被产出
                yield f"命中-{i}"
            # 剩下 95 项被【消费并丢弃】，它们【不计入 islice 的计数】

    print(f"对『筛选型』生成器用 islice(gen_filtered(), 0, 3) = "
          f"{list(itertools.islice(gen_filtered(), 0, 3))}")
    print("  ^ 正确：要 3 个【产出】就写 0,3，而不是 50,53")
    print(f"  写错了 islice(gen_filtered(), 50, 55) -> "
          f"{list(itertools.islice(gen_filtered(), 50, 55))}（空，静默失败）")

    # 关键对比：真实切片会先把 100 个都算出来放进 list
    print("\n两种方式的开销对比：")
    import timeit
    n = 200_000

    def sliced() -> list[int]:
        return list(range(n))[n // 2: n // 2 + 10]     # 完整构造 200000 个再切

    def isl() -> list[int]:
        return list(itertools.islice(range(n), n // 2, n // 2 + 10))  # range 本身惰性

    t1 = timeit.timeit(sliced, number=5) / 5
    t2 = timeit.timeit(isl, number=5) / 5
    print(f"  list(range(n))[100000:100010]      : {t1 * 1000:.3f} ms")
    print(f"  list(islice(range(n), ...))       : {t2 * 1000:.3f} ms")
    print(f"  islice 快 {t1 / t2:.1f} 倍（跳过构建全量 list 的步骤）")

    print("\n易错点：islice 的 start/stop/step 必须是非负整数。")
    try:
        list(itertools.islice(data, 5, 2))
    except ValueError as e:
        print(f"  step 为负 -> {e}")
    else:
        print("  start(5) > stop(2) 时不报错，直接产出空列表: []"
              "  <- 这是最隐蔽的坑：切片参数写错不会提示，只会【静默返回空】")
    try:
        list(itertools.islice(data, 0, 10, -2))
    except ValueError as e:
        print(f"  step 为负 -> {e}")


# ======================================================================
# 语法解析 6：无限序列 —— 为什么必须有 islice
# ======================================================================


def natural_numbers() -> Iterator[int]:
    """无限计数：真实场景如自增 ID、时序序列号。"""
    i = 1
    while True:
        yield i
        i += 1


def demo_infinite() -> None:
    print()
    print("=" * 68)
    print("【6】无限序列")
    print("=" * 68)

    # count(2, 2) = 2,4,6,8...    cycle('AB') = A,B,A,B...
    print(f"count(2,2) 取前 8 个: {list(itertools.islice(itertools.count(2, 2), 8))}")
    print(f"count() 取前 6 个   : {list(itertools.islice(itertools.count(), 6))}")
    print(f"cycle('ABC') 取 8 个: {list(itertools.islice(itertools.cycle('ABC'), 8))}")
    print(f"repeat('x', 3)      : {list(itertools.repeat('x', 3))}")
    print(f"repeat('x') 取 4 个  : {list(itertools.islice(itertools.repeat('x'), 4))}"
          f"   （repeat 无参是【无限】的）")

    # 自定义无限序列 + islice 截断
    primes = (n for n in itertools.count(2)
              if all(n % d for d in range(2, int(n ** 0.5) + 1)))
    print(f"前 10 个质数: {list(itertools.islice(primes, 10))}")

    print("\n⚠️ 危险示范：如果不加 islice，下面的循环【永不结束】：")
    print("    for x in itertools.count(): ...        # 死循环")
    print("    print(next(itertools.count()))          # 安全，取一个就停")
    one = next(itertools.count(100))
    print(f"  实测 next(count(100)) = {one}  —— next 只消费一个，安全")

    print("\n工程场景：无限序列 + islice 是【惰性分页】的标准写法")
    # 模拟从 offset 开始、每页取 3 条的游标分页
    offsets = itertools.count(0, 3)
    for page in range(3):
        offset = next(offsets)                      # 每页的起始下标
        rows = list(itertools.islice(range(1000), offset, offset + 3))
        print(f"  第{page + 1}页 offset={offset} -> {rows}")
    print("  ^ 注意：islice(range(1000), offset, ...) 对 range 会走【跳过式】访问，")
    print("    不需要真的构造中间列表，所以再深的页也几乎不增加成本。")


# ======================================================================
# 语法解析 7：类式迭代器 vs 生成器 —— 何时选哪个
# ======================================================================
#
# 两者【协议上完全等价】：生成器本身就是迭代器（实现了 __iter__/__next__）。
# 选型表：
#   需要内部可变状态 / 需要复用对象 / 需要暂停恢复多路 -> 类式
#   只是产出序列                                      -> 生成器（代码少一半）
#   需要多路复用（yield from 嵌套）                   -> 生成器天然支持


class FibIterator:
    """类式斐波那契：显式维护状态。"""

    def __init__(self) -> None:
        self.a, self.b = 0, 1

    def __iter__(self) -> "FibIterator":
        return self

    def __next__(self) -> int:
        value = self.a
        self.a, self.b = self.b, self.a + self.b
        return value


def fib_gen() -> Iterator[int]:
    """生成器式斐波那契：同样逻辑，写法短得多。"""
    a, b = 0, 1
    while True:
        yield a
        a, b = b, a + b


def demo_class_vs_generator() -> None:
    print()
    print("=" * 68)
    print("【7】类式迭代器 vs 生成器")
    print("=" * 68)

    a = list(itertools.islice(FibIterator(), 10))
    b = list(itertools.islice(fib_gen(), 10))
    print(f"FibIterator: {a}")
    print(f"fib_gen    : {b}")
    print(f"两者结果一致: {a == b}")

    print("\n选型对照表：")
    print(f"{'维度':<22}{'类式迭代器':<26}{'生成器'}")
    print("-" * 66)
    print(f"{'代码量':<22}{'需手写 __iter__/__next__':<26}{'一个 yield 搞定'}")
    print(f"{'可否重复遍历':<22}{'看 __iter__ 返回谁':<26}{'天然一次（需 tee）'}")
    print(f"{'可否 send/throw':<22}{'不能':<26}{'可以（协程能力）'}")
    print(f"{'调试栈帧':<22}{'浅':<26}{'深（每个 yield 都是一个帧）'}")
    print("\n结论：99% 的场景用生成器；只有需要【复用同一个有状态对象】时才写类。")


def main() -> None:
    demo_iterable_vs_iterator()
    demo_custom_iterator()
    demo_for_expansion()
    demo_optional_protocols()
    demo_islice()
    demo_infinite()
    demo_class_vs_generator()
    print()
    print("=" * 68)
    print("02_iterators 演示完毕")
    print("核心一句话：迭代器 = 有状态游标 + __next__ 抛 StopIteration 收尾。")
    print("=" * 68)


if __name__ == "__main__":
    main()