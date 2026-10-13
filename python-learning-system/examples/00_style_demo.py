"""好代码 vs 坏代码对比 —— 配套 G03《代码风格与命名规范》。

这个文件用一个「学生成绩统计」的需求，展示同一件事的 9 种写法，
从最糟糕的 bad_00() 一路改到推荐的 good_09()。

运行：python examples/00_style_demo.py

阅读建议：不要一次看完，先跑一遍 bad_good() 看输出，
然后回到源码逐个对比每个版本的「改了哪里、为什么这么改」。
"""

from collections import Counter
from typing import Optional

# ============================================================
# 模块级常量：全大写，放在文件顶部
# ============================================================
# 为什么放这里？常量在整个文件里都要用，集中放在顶部便于查阅和统一修改，
# 而不是散落在函数内部重复出现不同的魔法数字。
PASSING_SCORE = 60          # 分数大于等于它算及格
EXCELLENT_SCORE = 90        # 分数大于等于它算优秀
SCORE_MIN = 0               # 分数合法下界
SCORE_MAX = 100             # 分数合法上界
SUBJECT_NAMES = ("语文", "数学", "英语")   # 元组：不可变，适合当固定集合


# ============================================================
# 坏代码 1：变量名毫无意义 + 无换行 + 超长行
# ============================================================
def bad_00(a, b, c):
    x = 0
    for i in range(len(a)):
        if a[i] > 60:
            x = x + a[i]
    y = []
    for i in range(len(b)):
        if b[i] > 60:
            y.append(b[i])
    z = []
    for i in range(len(c)):
        if c[i] > 60:
            z.append(c[i])
    print("语文及格总分", x, "数学及格总分", sum(y), "英语及格总分", sum(z), "三科及格人数", len(y) + len(z))
    return x, y, z


# ============================================================
# 坏代码 2：注释写的是「做什么」，而且在复述代码
# ============================================================
def bad_01(scores):
    # 定义一个变量
    result = []
    # 循环遍历 scores
    for s in scores:
        # 判断 s 是否大于 60
        if s > 60:
            # 把 s 加进 result
            result.append(s)
    # 返回 result
    return result


# ============================================================
# 坏代码 3：魔法数字满天飞 + 缺 docstring + 硬编码阈值
# ============================================================
def bad_02(scores):
    """处理分数。

    参数：
        scores: 分数

    返回：
        结果
    """
    total = 0
    count = 0
    best = 0
    for s in scores:
        total = total + s
        count = count + 1
        if s > best:
            best = s
    avg = total / count
    if avg > 90:
        level = "A"
    elif avg > 80:
        level = "B"
    elif avg > 60:
        level = "C"
    else:
        level = "D"
    return avg, best, level


# ============================================================
# 坏代码 4：函数做太多事（违反单一职责）
# ============================================================
def bad_03(scores):
    """一个函数里塞了校验、统计、判级、打印四件事。"""
    if not scores:
        print("没有数据")
        return None
    total = sum(scores)
    avg = total / len(scores)
    if avg > 90:
        level = "A"
    else:
        level = "B"
    print(f"总分 {total}")
    print(f"平均分 {avg}")
    print(f"等级 {level}")
    print(f"最高分 {max(scores)}")
    print(f"最低分 {min(scores)}")
    return avg


# ============================================================
# 坏代码 5：可变默认参数陷阱（Python 最经典的坑之一）
# ============================================================
def bad_04(item, bucket=[]):
    """用可变对象（列表）作默认参数，会导致数据在多次调用间累积。"""
    bucket.append(item)
    return bucket


# ============================================================
# 好代码：命名清晰 + 提取常量 + docstring + 单一职责 + 类型标注
# ============================================================
def filter_passing(scores: list[int]) -> list[int]:
    """筛选出所有及格分数。

    只做一件事：把及格的分数挑出来。

    Args:
        scores: 所有学生的分数列表。

    Returns:
        及格分数组成的列表，顺序与输入一致。

    Raises:
        ValueError: 传入的分数超出 0~100 合法区间时抛出。
    """
    # 先校验再计算：让函数在错误输入下立刻失败，而不是先算出一堆错误结果
    for score in scores:
        if not SCORE_MIN <= score <= SCORE_MAX:
            raise ValueError(f"分数 {score} 超出 0~100 的合法区间")

    # 用推导式替代 6 行 for 循环，可读性反而更高——这是 Python 的风格优势
    return [score for score in scores if score >= PASSING_SCORE]


def classify(score: float) -> str:
    """把单个分数转换为等级。

    Args:
        score: 单个分数，允许小数。

    Returns:
        等级字符串："A" / "B" / "C" / "D"。

    Raises:
        ValueError: 分数越界时抛出。
    """
    if not SCORE_MIN <= score <= SCORE_MAX:
        raise ValueError(f"分数 {score} 超出 0~100 的合法区间")

    # 从高分往低分判断，一旦命中就返回，逻辑扁平无需嵌套。
    # 注意使用 >= 而非 >：60 分应该算及格。
    if score >= EXCELLENT_SCORE:
        return "A"
    if score >= 80:
        return "B"
    if score >= PASSING_SCORE:
        return "C"
    return "D"


def summarize(scores: list[int]) -> dict[str, object]:
    """汇总一组分数的统计信息。

    Args:
        scores: 非空的分数列表。

    Returns:
        含 total / average / best / worst / level / passed_count 的字典。

    Raises:
        ValueError: 列表为空时抛出——平均值无法从空数据算出，
            静默返回 0 会让调用方误以为「全班都考 0 分」。
    """
    if not scores:
        raise ValueError("分数列表不能为空")

    total = sum(scores)
    # round 保留一位小数，避免出现 82.83333333333333 这种噪音
    average = round(total / len(scores), 1)

    # 显式列出返回的键，而不是让调用方猜字典里有什么
    return {
        "total": total,
        "average": average,
        "best": max(scores),
        "worst": min(scores),
        "level": classify(average),
        "passed_count": len(filter_passing(scores)),
    }


def format_report(subject: str, scores: list[int]) -> str:
    """把一份成绩单格式化成可读文本。

    Args:
        subject: 科目名，如 "语文"。
        scores: 该科目的所有分数。

    Returns:
        多行字符串，每行一个统计项。

    Raises:
        ValueError: 分数数据非法时，异常会向上传播给调用方处理。
    """
    stats = summarize(scores)

    # 用三引号字符串 + 文本内换行，比一连串 print 或字符串拼接好读得多
    return (
        f"【{subject}】\n"
        f"  总分：{stats['total']}\n"
        f"  平均分：{stats['average']}\n"
        f"  最高分：{stats['best']}\n"
        f"  最低分：{stats['worst']}\n"
        f"  及格人数：{stats['passed_count']}\n"
        f"  综合等级：{stats['level']}"
    )


# ============================================================
# 坏代码 6：为了「面向对象」而面向对象（违反 KISS 原则）
# ============================================================
class _AbstractCalculatorBase:
    """完全不需要的抽象层：没有第二个实现，也没有可替换的行为。"""

    def calculate(self, data: list[int]) -> dict:
        raise NotImplementedError


class _ConcreteCalculatorImpl(_AbstractCalculatorBase):
    """为了「符合设计模式」而存在的空壳实现类。"""

    def __init__(self) -> None:
        self._cache: dict = {}
        self._config: dict = {}
        self._logger: dict = {}

    def calculate(self, data: list[int]) -> dict:
        # 三个字典从初始化到使用始终是空的，属于纯粹的无用代码
        self._cache["last"] = data
        return {"total": sum(data), "average": sum(data) / len(data)}


def bad_05_ood_for_no_reason(scores: list[int]) -> dict:
    """为了展示「不该用 OOP」，这里硬套了三层设计。"""
    return _ConcreteCalculatorImpl().calculate(scores)


def good_05_kiss(scores: list[int]) -> dict:
    """同样的功能，两行函数搞定——这才是 KISS 原则。"""
    return {"total": sum(scores), "average": sum(scores) / len(scores)}


# ============================================================
# 对比演示入口
# ============================================================
def bad_good() -> None:
    """逐个演示每个坏代码版本「坏在哪」，以及改进后的正确写法。

    这是本文件的主函数，运行 python 00_style_demo.py 会自动调用它。
    """
    # 演示用的三科成绩
    chinese = [88, 95, 59, 100, 61]
    math = [100, 90, 90, 60, 45]
    english = [70, 70, 70, 70, 70]

    print("=" * 70)
    print("【1】命名：bad_00 用 a/b/c/i，改进后用有意义的英文名")
    print("=" * 70)
    print("bad_00 的参数名是 a, b, c —— 读者无从知道它们是什么")
    print("改进后的做法见 good 函数：scores / subject / passing_scores")
    print(f"  bad_00 输出：{bad_00(chinese, math, english)}")
    print(f"  这行 print 原本超过 100 字符，在 PEP 8 里应该换行")
    print()

    print("=" * 70)
    print("【2】注释：bad_01 复述代码，good 函数解释「为什么」")
    print("=" * 70)
    print("bad_01 的注释「循环遍历 scores」等于没说——代码本身就写着 for")
    print('good 的 docstring 说明的是「这个函数用来干什么」：'
          f"\n  {filter_passing.__doc__.splitlines()[0].strip()}")
    print(f"  bad_01 输出：{bad_01(chinese)}")
    print(f"  good  输出：{filter_passing(chinese)}")
    print()

    print("=" * 70)
    print("【3】魔法数字：bad_02 里散落着 60 / 90 / 80")
    print("=" * 70)
    print("改进后统一提到模块顶部成为常量：")
    print(f"  PASSING_SCORE={PASSING_SCORE}, EXCELLENT_SCORE={EXCELLENT_SCORE}")
    print(f"  bad_02 输出：{bad_02(chinese)}")
    print(f"  good  输出：{summarize(chinese)}")
    print()

    print("=" * 70)
    print("【4】单一职责：bad_03 一函数干四件事")
    print("=" * 70)
    print("bad_03 返回 None 时，调用方无法区分「没数据」和「算错了」")
    print("good 拆分后，summarize 遇空列表抛 ValueError，语义明确：")
    try:
        summarize([])
    except ValueError as exc:
        print(f"  good 的异常更清晰：ValueError: {exc}")
    print("  而 bad_03 只会静默返回 None，调用方还得自己猜")
    print()

    print("=" * 70)
    print("【5】可变默认参数：bad_04 的数据会跨调用累积")
    print("=" * 70)
    # 这个对比是本文件最重要的教学点：两次调用的输出里出现了上一轮的数据
    print(f"  bad_04('语文') 调用 1 次 → {bad_04('语文')}")
    print(f"  bad_04('数学') 调用 2 次 → {bad_04('数学')}  ← 语文混进来了！")
    print("  正确写法：默认值为 None，函数内部再创建新列表")
    print(f"  好写法 调用 1 次 → {good_04('语文')}")
    print(f"  好写法 调用 2 次 → {good_04('数学')}  ← 干净，无残留")
    print()

    print("=" * 70)
    print("【6】KISS 原则：bad_05 为 OOP 而 OOP")
    print("=" * 70)
    print("bad_05 套了三层类（抽象基类 + 实现类 + 空字典缓存），只为一个求和")
    print(f"  bad_05 输出：{bad_05_ood_for_no_reason(chinese)}")
    print(f"  good_05 输出：{good_05_kiss(chinese)}  ← 两行解决，结果完全一样")
    print()

    print("=" * 70)
    print("【7】格式化输出：三引号字符串优于 print 拼接")
    print("=" * 70)
    print(format_report("语文", chinese))
    print()
    print(format_report("数学", math))


def good_04(item: str, bucket: Optional[list] = None) -> list[str]:
    """正确处理「可变默认参数」的写法。

    默认值用 None（不可变），函数内部再按需创建新的列表，
    这样每次调用都有独立的 bucket，不会互相污染。

    Args:
        item: 要加入的科目名。
        bucket: 目标列表。为 None 时自动新建一个。

    Returns:
        传入（或新建）的列表，其中已包含 item。
    """
    # if bucket is None 而不是 if not bucket：
    # 后者会把「传入了一个空列表」也当成没传，导致调用方传入的列表被丢弃
    if bucket is None:
        bucket = []
    bucket.append(item)
    return bucket


def main() -> None:
    """程序入口：调用 bad_good 演示全部对比。"""
    bad_good()


# 直接运行本文件时执行；被 import 时不执行，便于别人复用里面的好函数
if __name__ == "__main__":
    main()
