"""
================================================================================
 04_datetime.py  ——  datetime：日期时间与时区
================================================================================

【演示的语法点】
 1. date / time / datetime / timedelta / timezone / tzinfo 五大类型
 2. strftime / strptime 格式符全表与跨平台陷阱
 3. 时间戳：timestamp() / fromtimestamp() / 毫秒精度处理
 4. ★ naive vs aware：时区处理的四大经典坑
 5. 日期加减、日期区间遍历、replace / dateutil 思路
 6. 工作日与自然日计算（无第三方库实现法）
 7. 实战：账务对账、日历、跨时区转换、时长格式化

【预期输出摘要】
 - "格式符" 小节：打印 %Y/%m/%d 等一组指令的输出
 - "时区" 小节：打印 naive 与 aware 相减的 TypeError 演示
 - "工作日" 小节：输出某月的工作日天数与具体日期列表
================================================================================

"""

from __future__ import annotations

import calendar
import time as time_module          # ★ 模块改名，避免与 datetime.time 类冲突
from datetime import date, datetime, time as dtime, timedelta, timezone


# ===== 语法解析 =====
# 【1】五个核心类型，各管一件事
#   语法规则与设计意图：
#     date          —— 只有年月日（无时分秒、无时区）
#     time          —— 只有时分秒微秒（无日期）
#     datetime      —— date + time 的组合（最常用）
#     timedelta     —— 时间差 / 时间段（可正可负）
#     timezone/tzinfo —— 时区对象
#   ★ 为什么分成三个类而不是一个？
#     业务语义不同：生日只需 date，营业时间只需 time，日志需要 datetime。
#     类型分离能在【编译期/静态检查期】拦住"给 date 传 timezone"的错误。
def demo_types() -> None:
    d = date(2026, 10, 12)                    # 位置参数：年, 月, 日
    t = dtime(14, 30, 45, 123456)               # 时, 分, 秒, 微秒
    dt = datetime(2026, 10, 12, 14, 30, 45, 123456)

    print(f"  date     = {d}，字段：{d.year}/{d.month}/{d.day}")
    print(f"  time     = {t}，字段：{t.hour}/{t.minute}/{t.second}/{t.microsecond}")
    print(f"  datetime = {dt}")
    print(f"  date.today()     = {date.today()}")
    print(f"  datetime.now()   = {datetime.now()}")
    print(f"  datetime.utcnow() = {datetime.utcnow()}   ← 已废弃！见时区小节")

    # 关键字参数更清晰：避免"20xx 年"这种歧义
    dt_kw = datetime(year=2026, month=10, day=12, hour=9)
    print(f"  关键字构造 = {dt_kw}")

    # min/max：类的取值范围（可表示的最大/最小 datetime）
    print(f"  datetime.min = {datetime.min}")
    print(f"  datetime.max = {datetime.max}")

    # 从时间戳还原
    ts = datetime.fromtimestamp(0)            # 1970-01-01 本地时间
    print(f"  datetime.fromtimestamp(0) = {ts}   ← 按【本地时区】解释")

    # isoformat：标准格式，可被其他系统解析
    print(f"  dt.isoformat() = {dt.isoformat()}")
    print(f"  dt.date() 取日期部分 = {dt.date()}")
    print(f"  dt.time() 取时间部分 = {dt.time()}")


# ===== 语法解析 =====
# 【2】★ strftime / strptime 格式符全表
#   strftime：datetime → 字符串（format）
#   strptime：字符串 → datetime（parse，必须【成对使用】）
#   规则：% 后面跟一个字符表示一个时间字段
#   设计意图：strftime 源自 C 语言的 printf，Python 沿用了这套语法。
def demo_strftime() -> None:
    dt = datetime(2026, 10, 12, 14, 30, 45)

    print("  ── 日期部分 ──")
    for code, desc in [
        ("%Y", "四位年份"), ("%y", "两位年份"), ("%m", "零填充月份 01-12"),
        ("%-m", "无填充月份（平台相关）"), ("%d", "零填充日 01-31"),
        ("%B", "英文月全名"), ("%b", "英文月缩写"), ("%A", "英文星期全名"),
        ("%a", "英文星期缩写"), ("%j", "年内第几天 001-366"),
    ]:
        try:
            out = dt.strftime(code)
            print(f"    {code:<6} → {out:<12} # {desc}")
        except Exception as e:                # -m 在 Windows 上支持情况不同
            print(f"    {code:<6} → 不支持 ({type(e).__name__})  # {desc}")

    print("  ── 时间部分 ──")
    for code, desc in [
        ("%H", "24 小时制小时 00-23"), ("%I", "12 小时制小时 01-12"),
        ("%M", "分钟 00-59"), ("%S", "秒 00-59"), ("%f", "微秒 6 位"),
        ("%p", "AM/PM"), ("%%", "字面量 % 号"),
    ]:
        print(f"    {code:<6} → {dt.strftime(code):<12} # {desc}")

    print("  ── 复合与本地化 ──")
    print(f"    %Y-%m-%d %H:%M:%S → {dt.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"    ISO8601(带T和微秒)  → {dt.isoformat()}")
    print(f"    中文本地化需 locale → 见下方 strptime 小节")

    # strptime：解析必须与格式【严格对应】
    s = "2026-10-12 14:30:45"
    parsed = datetime.strptime(s, "%Y-%m-%d %H:%M:%S")
    print(f"  strptime('{s}', ...) = {parsed}")
    print(f"  与原 datetime 相等：{parsed == dt}   ← 说明二者格式一致")

    # ⚠ 坑1：格式不匹配直接抛 ValueError
    try:
        datetime.strptime("2026/10/12", "%Y-%m-%d")
    except ValueError as e:
        print(f"  ⚠ 格式不匹配 → ValueError: {e}")

    # ⚠ 坑2：strftime 的 %-m / %-d（去填充）不是标准 C，Windows 上不保证支持
    try:
        print(f"  %-m-%-d 去填充 → {dt.strftime('%-m-%-d')}")
    except ValueError as e:
        print(f"  ⚠ 去填充格式在部分平台不支持：{e}")
        # 跨平台安全写法：手动处理
        print(f"  ✅ 手动去填充 → {dt.month}/{dt.day}")

    # ⚠ 坑3：%c / %x 等受【系统区域设置 locale】影响，输出会变
    print(f"  ⚠ %c 依赖系统区域设置，当前为：{dt.strftime('%c')}")
    print(f"  → 所以【不要】用 %c/%x/%X 存储数据，必须用 ISO 格式 %Y-%m-%d")


# ===== 语法解析 =====
# 【3】★ 时间戳与毫秒精度
#   时间戳 = 自 1970-01-01 00:00:00 UTC 起的【秒数】（浮点或整数）
#   核心坑：Python 的 timestamp()/fromtimestamp() 用【浮点数】表示，
#          浮点只有约 15-16 位有效数字，毫秒时间戳（13 位）尚可，
#          纳秒/微秒级时间戳（19 位）会丢精度。
#   正确做法：用整数运算或直接用 timedelta 差值，不要用浮点累加。
def demo_timestamp() -> None:
    dt = datetime(2026, 10, 12, 14, 30, 45)
    ts = dt.timestamp()
    print(f"  dt.timestamp() = {ts}   （浮点数，单位秒）")
    print(f"  毫秒时间戳 = {int(ts * 1000)}")
    print(f"  微秒时间戳 = {int(ts * 1_000_000)}")

    # 回转
    print(f"  datetime.fromtimestamp({ts:.6f}) = {datetime.fromtimestamp(ts)}")
    print(f"  往返一致：{datetime.fromtimestamp(ts).replace(microsecond=0) == dt}")

    # ★ 毫秒精度的时间戳转换（前后端对接最常见）
    def ms_to_datetime(ms: int) -> datetime:
        """毫秒时间戳 → datetime（推荐用 fromtimestamp + 微秒，避开浮点乘法）"""
        return datetime.fromtimestamp(ms / 1000.0)

    def datetime_to_ms(dt_: datetime) -> int:
        """datetime → 毫秒时间戳"""
        return int(dt_.timestamp() * 1000)

    now = datetime(2026, 10, 12, 14, 30, 45, 123000)
    print(f"  datetime_to_ms({now}) = {datetime_to_ms(now)}")
    print(f"  ms_to_datetime(往返)   = {ms_to_datetime(datetime_to_ms(now))}")

    # ⚠ 坑：浮点时间戳不能直接用来比较"是否同一毫秒"，要用差值
    ms1, ms2 = 1762000000000, 1762000000123
    print(f"  两个毫秒时间戳差 {ms2 - ms1} ms → {timedelta(milliseconds=ms2 - ms1)}")

    # 用 timedelta 精确做时间差（优于浮点相减）
    start = datetime(2026, 10, 12, 10, 0, 0)
    end = datetime(2026, 10, 12, 12, 30, 30)
    delta = end - start
    print(f"  时间差 = {delta}")
    print(f"    总秒数 = {delta.total_seconds()}")
    print(f"    总分钟 = {delta.total_seconds() / 60:.2f}")
    print(f"    小时:分 = {delta.seconds // 3600}:{(delta.seconds % 3600) // 60}")

    # ★ time 模块：测量耗时用 perf_counter（而非 time.time）
    t0 = time_module.perf_counter()
    sum(range(100000))
    cost = time_module.perf_counter() - t0
    print(f"  perf_counter 测得耗时 {cost * 1000:.3f} ms  ← 单调钟，不受系统时间调整影响")


# ===== 语法解析 =====
# 【4】★ 时区：naive vs aware（最容易被面试问倒的部分）
#   naive（朴素时间）：没有时区信息，如 datetime.now()
#   aware（带时区时间）：带 tzinfo，如 datetime.now(timezone.utc)
#   核心规则：
#     1. aware 之间可以相减（得到真实时间差）
#     2. naive 之间相减也能，但结果【未必是真实时间差】（跨夏令时会错 1 小时）
#     3. naive 与 aware 相减 → TypeError！这是【主动的保护】
#   设计意图：让"不知道时区的比较"这种逻辑错误在运行时立刻暴露，而不是悄悄算错。
def demo_timezone() -> None:
    # 固定偏移时区（不是真实时区名，无夏令时规则）
    tz8 = timezone(timedelta(hours=8), name="UTC+8")
    tz5 = timezone(-timedelta(hours=5), name="UTC-5")

    aware_utc = datetime(2026, 10, 12, 6, 0, tzinfo=timezone.utc)
    aware_cn = datetime(2026, 10, 12, 14, 0, tzinfo=tz8)
    print(f"  aware_utc = {aware_utc}")
    print(f"  aware_cn  = {aware_cn}")
    print(f"  两者表示同一时刻：{aware_utc == aware_cn}")
    print(f"  tzinfo = {aware_cn.tzinfo}，utcoffset = {aware_cn.utcoffset()}")

    # aware 之间相减：得到真实的时间差
    diff = aware_cn - aware_utc
    print(f"  aware 相减 = {diff}（正好 8 小时）")

    # ⚠ 核心坑：naive 与 aware 相减抛 TypeError
    naive = datetime(2026, 10, 12, 14, 0)
    print(f"  naive = {naive}")
    try:
        naive - aware_utc
    except TypeError as e:
        print(f"  ⚠ naive - aware → TypeError: {e}")
        print(f"     这正是设计意图：【强制你显式处理时区】，避免静默出错")

    # 检查类型的方法
    print(f"  如何判断 aware：dt.tzinfo is not None → {aware_cn.tzinfo is not None}")
    print(f"  naive 的 tzinfo：{naive.tzinfo} → is not None = {naive.tzinfo is not None}")

    # 时区转换必须先转成 UTC
    print(f"  aware_cn.astimezone(timezone.utc) = {aware_cn.astimezone(timezone.utc)}")
    print(f"  aware_cn.astimezone(tz5)          = {aware_cn.astimezone(tz5)}")

    # ⚠ replace 的陷阱：直接 replace(tzinfo=) 不做换算，只是"贴标签"
    fake = datetime(2026, 10, 12, 14, 0).replace(tzinfo=tz8)
    print(f"  ⚠ replace(tzinfo=) 只是贴标签：{fake}")
    print(f"     它的真实 UTC 时刻是 {fake.astimezone(timezone.utc)}，并非 14:00 UTC")

    # 正确做法：naive → aware 要用 astimezone（需先假定本地时区）或显式声明
    #   本地时间假定为某个时区：
    local_aware = naive.astimezone()          # 用系统本地时区解释 naive 时间
    print(f"  naive.astimezone() = {local_aware}   ← 假设 naive 是本地时间")

    # 存储与传输规范：
    print("  ── 存储/传输规范 ──")
    print("  1. 数据库存【带时区的 UTC 时间】或 Unix 时间戳")
    print("  2. 传输用 ISO 8601 带偏移：2026-10-12T14:00:00+08:00")
    print("  3. 展示时才转成用户本地时区")

    # ★ 夏令时坑：naive 相减在跨越 DST 时会算错（美/欧地区才有夏令时）
    print("  ⚠ 夏令时：naive 时间相减在跨 DST 的那天会少/多算 1 小时")
    print("     例：2026-03-08 02:00→03:00（美东 clocks jumped forward）")
    print("     所以【任何持久化的比较】都必须用 aware 或时间戳")


# ===== 语法解析 =====
# 【5】日期加减、区间遍历、replace
#   语法规则：
#     dt + timedelta(days=1)   加一天（dt 不变，生成新对象）
#     dt - timedelta(hours=2)  减两小时（得到过去时间）
#     dt2 - dt1                = timedelta  时间差
#     dt.replace(year=2027)     替换某个字段，得到新对象
#   构造 timedelta：days / seconds / microseconds / weeks / hours / minutes
def demo_arithmetic() -> None:
    dt = datetime(2026, 10, 12, 14, 30, 45)

    # 加减
    print(f"  原时间       {dt}")
    print(f"  +1 天        {dt + timedelta(days=1)}")
    print(f"  -2 小时      {dt - timedelta(hours=2)}")
    print(f"  +3 周        {dt + timedelta(weeks=3)}")
    print(f"  +90 秒       {dt + timedelta(seconds=90)}")
    # timedelta 的属性
    td = timedelta(days=1, hours=2, minutes=30)
    print(f"  timedelta(days=1,hours=2,minutes=30) = {td}")
    print(f"    .days={td.days} .seconds={td.seconds} .total_seconds()={td.total_seconds()}")

    # replace：批量修改字段（不改变未指定的字段）
    print(f"  replace(month=1)  = {dt.replace(month=1)}")
    print(f"  replace(day=1,year=2027) = {dt.replace(day=1, year=2027)}")

    # ⚠ 替换不存在的日期会抛 ValueError（2 月 30 日）
    try:
        dt.replace(day=30)
    except ValueError as e:
        print(f"  ⚠ replace(day=30) → ValueError: {e}   （10 月没有 30 日）")

    # 月末溢出是自动的
    print(f"  2026-10-31 + 1 天 = {date(2026, 10, 31) + timedelta(days=1)}   ← 自动进位到 11 月")

    # 实战：遍历日期区间
    start, end = date(2026, 10, 1), date(2026, 10, 5)
    cur = start
    days = []
    while cur <= end:
        days.append(cur.isoformat())
        cur += timedelta(days=1)
    print(f"  区间 {start} ~ {end} 逐日：{days}")
    print(f"  区间天数 = {(end - start).days + 1}   ← 注意要 +1 才是闭区间天数")

    # 实战：生日倒计时
    today = date(2026, 10, 12)
    birthday = date(2027, 3, 15)
    next_bd = birthday.replace(year=today.year)
    if next_bd < today:
        next_bd = next_bd.replace(year=today.year + 1)     # 今年已过，看明年
    print(f"  距离生日还有 {(next_bd - today).days} 天")


# ===== 语法解析 =====
# 【6】工作日计算（标准库方案）
#   问题：给定年/月，算这个月有多少工作日、哪些天是工作日。
#   思路：weekday() 返回 0(周一)~6(周日)；工作日 = weekday() < 5。
def demo_workday() -> None:
    year, month = 2026, 10

    # 该月所有工作日
    workdays = []
    weekend_days = []
    cal = calendar.Calendar()                      # calendar 模块提供日历工具
    # ⚠ Calendar 不是上下文管理器，不能用 with
    for week in cal.monthdatescalendar(year, month):# 每月分成若干"周"，每周是 7 个 date
        for d in week:
            if d.month != month:                   # 跳过补位显示的其他月份日期
                continue
            if d.weekday() < 5:
                workdays.append(d)
            else:
                weekend_days.append(d)

    print(f"  {year}年{month}月共 {len(workdays) + len(weekend_days)} 天")
    print(f"    工作日 {len(workdays)} 天：{[str(d) for d in workdays[:5]]} ...")
    print(f"    周末   {len(weekend_days)} 天：{[str(d) for d in weekend_days]}")

    # 星期几：weekday()=0 是周一；strftime('%w')=0 是周日（易混！）
    d = date(2026, 10, 12)                          # 2026-10-12 是周一
    print(f"  {d} 的 weekday() = {d.weekday()}   （0=周一）")
    print(f"  {d} 的 strftime('%w') = {d.strftime('%w')}  （0=周日）← 两套编号不同")

    # 实战：计算某日期往前 n 个工作日（跳过周末）
    def add_workdays(start: date, n: int) -> date:
        """从 start 起向前推 n 个工作日（不含 start 本身）。"""
        cur, added = start, 0
        while added < n:
            cur += timedelta(days=1)
            if cur.weekday() < 5:                   # 只要周一到周五
                added += 1
        return cur

    print(f"  {date(2026,10,12)} 起 5 个工作日后 = {add_workdays(date(2026,10,12), 5)}")

    # 计算两个日期之间的工作日数量
    def workday_count(start: date, end: date) -> int:
        """[start, end) 之间的工作日天数。"""
        cur, count = start, 0
        while cur < end:
            if cur.weekday() < 5:
                count += 1
            cur += timedelta(days=1)
        return count

    print(f"  2026-10-01 到 2026-10-31 的工作日数 = "
          f"{workday_count(date(2026,10,1), date(2026,11,1))}")

    # calendar.isleap：判断闰年
    print(f"  2024 是闰年：{calendar.isleap(2024)}，2026 是闰年：{calendar.isleap(2026)}")
    # ★ 2 月天数
    print(f"  2026年2月天数 = {calendar.monthrange(2026, 2)[1]}，2024年2月 = {calendar.monthrange(2024,2)[1]}")


# ===== 语法解析 =====
# 【7】实战：时长格式化、账务对账、日历打印
def demo_practice() -> None:
    # ① 把秒数格式化成"Xh Ym Zs"
    def humanize(seconds: float) -> str:
        """把秒数转成人类可读的时长。"""
        m, s = divmod(int(seconds), 60)              # divmod 同时返回商和余数
        h, m = divmod(m, 60)
        return f"{h}小时{m}分{s}秒" if h else (f"{m}分{s}秒" if m else f"{s}秒")

    print("  ① 时长格式化：")
    for sec in [45, 90, 3661, 86399]:
        print(f"      {sec}秒 → {humanize(sec)}")

    # ② 账务对账：找出 7 天内未平账的订单
    today = date(2026, 10, 12)
    orders = [
        {"id": "A001", "date": today - timedelta(days=10), "settled": True},
        {"id": "A002", "date": today - timedelta(days=3), "settled": False},
        {"id": "A003", "date": today - timedelta(days=1), "settled": False},
        {"id": "A004", "date": today, "settled": False},
    ]
    unsettled = [o for o in orders if not o["settled"] and 0 <= (today - o["date"]).days <= 7]
    print(f"  ② 近 7 天未平账订单：{[o['id'] for o in unsettled]}")

    # ③ 打印 2026年10月日历（★ 展示 calendar 的排版能力）
    year, month = 2026, 10
    print(f"  ③ {year} 年 {month} 月日历：")
    # ⚠ Calendar 是【日期计算器】没有排版能力；
    #   TextCalendar 才有 formatmonth()（输出多行字符串），且它是 Calendar 的子类
    text_cal = calendar.TextCalendar(firstweekday=0)   # 0 = 周一开头
    for line in text_cal.formatmonth(year, month).splitlines():
        print(f"      {line}")

    # ④ 跨时区：显示"全球各地当前时间"
    print("  ④ 全球主要时区当前时间：")
    zones = [
        ("UTC", timezone.utc),
        ("纽约(UTC-5)", timezone(timedelta(hours=-5))),
        ("伦敦(UTC+0)", timezone.utc),
        ("北京(UTC+8)", timezone(timedelta(hours=8), name="CST")),
        ("东京(UTC+9)", timezone(timedelta(hours=9))),
    ]
    base_utc = datetime(2026, 10, 12, 6, 0, tzinfo=timezone.utc)
    for name, tz in zones:
        local = base_utc.astimezone(tz)
        print(f"      {name:<12} {local.strftime('%Y-%m-%d %H:%M')}")

    # ⑤ 生成时间戳标识（如日志 ID）：毫秒精度 + 可读
    def make_ts_id(dt_: datetime) -> str:
        """生成形如 20261012-143045 的可读时间戳 ID。"""
        return dt_.strftime("%Y%m%d-%H%M%S")

    print(f"  ⑤ 可读时间戳 ID：{make_ts_id(datetime(2026,10,12,14,30,45))}")


def main() -> None:
    print("=" * 60)
    print("【1】datetime 五大类型")
    print("=" * 60)
    demo_types()

    print()
    print("=" * 60)
    print("【2】strftime / strptime 格式符")
    print("=" * 60)
    demo_strftime()

    print()
    print("=" * 60)
    print("【3】时间戳与毫秒精度")
    print("=" * 60)
    demo_timestamp()

    print()
    print("=" * 60)
    print("【4】时区处理（naive vs aware）")
    print("=" * 60)
    demo_timezone()

    print()
    print("=" * 60)
    print("【5】日期加减与区间遍历")
    print("=" * 60)
    demo_arithmetic()

    print()
    print("=" * 60)
    print("【6】工作日与日历计算")
    print("=" * 60)
    demo_workday()

    print()
    print("=" * 60)
    print("【7】实战：格式化 / 对账 / 日历 / 跨时区")
    print("=" * 60)
    demo_practice()

    print()
    print("=" * 60)
    print("小结")
    print("=" * 60)
    print("  1. date/time/datetime/timedelta 语义分离，静态检查能拦错")
    print("  2. strftime/strptime 成对使用；不要用 %c 等受 locale 影响的格式")
    print("  3. 测耗时用 time.perf_counter()，它是单调钟")
    print("  4. naive 与 aware 相减抛 TypeError，这是保护而非限制")
    print("  5. 存储用 UTC / 时间戳；replace(tzinfo=) 只贴标签不换算")
    print("  6. weekday()=0 是周一，strftime('%w')=0 是周日，两套编号")
    print("  7. 闭区间天数要 +1；replace 到不存在的日期会 ValueError")


if __name__ == "__main__":
    main()