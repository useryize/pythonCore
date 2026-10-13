"""L04 字符串深入 —— 配套教案配套示例。

运行：python examples/L04_strings.py

本脚本演示六件事：
    1. 索引与负数下标：为什么下标从 0 开始，越界怎么办
    2. 切片：左闭右开区间、步长、切片不越界的秘密
    3. 字符串不可变性的后果，以及「为什么不能原地修改」
    4. 字符串常用方法全景表：增（不适用）删改查排转各归其位
    5. f-string 进阶：嵌套引号、调试 =、多行、对齐
    6. 两个实战：解析 CSV 行 + 手机号/身份证简单脱敏

⚠️ 纯标准库，无任何第三方依赖，可直接运行。
"""

import csv                                    # 标准库：解析带引号的 CSV，比 split 可靠
import io                                     # 标准库：配合 csv.reader 读取字符串
import sys                                    # 标准库：取版本号，说明 3.12 的差异

# ============================================================
# 模块级常量
# ============================================================
SAMPLE_TEXT = "  Python 3.13 入门教程  "        # 带首尾空白，方便演示 strip
CSV_LINE = "张三,28,北京市,工程师,13800138000"   # 一条 CSV 记录
PHONE = "13812345678"                          # 待脱敏的手机号
ID_CARD = "110101199003074321"                 # 待脱敏的身份证号
LOREM = "the quick brown fox jumps over the lazy dog"   # 英文测试文本


# ============================================================
# 第 1 部分：索引
# ============================================================
def demo_indexing() -> None:
    """下标从 0 开始，负数从末尾数，越界抛 IndexError。"""
    s = "Python"
    print(f"字符串   : {s!r}")
    print(f"长度     : {len(s)}")
    # 正向下标：从 0 开始，最后一个是 len(s) - 1
    print("\n【正向索引 s[i]】")
    for i in range(len(s)):
        print(f"  s[{i}] = {s[i]!r}")
    # 负向索引：-1 表示最后一个，-2 倒数第二个，以此类推
    print("\n【负向索引 s[i]，-1 是最后一个】")
    for i in range(-len(s), 0):
        print(f"  s[{i}] = {s[i]!r}   （等价于 s[{len(s) + i}]）")

    # 为什么下标从 0 开始？
    # 因为第一个字符的「偏移量」是 0，语言设计者认为「前面有 i 个字符」
    # 这个心智模型比「第 i 个字符」更贴近内存寻址，也便于做偏移计算。
    print("\n【为什么从 0 开始】下标本质是「偏移量」：第 i 个字符前面有 i 个字符，偏移就是 i")
    print("  若从 1 开始，则 index 和偏移量差 1，所有指针运算都要多减一次，得不偿失")

    # ⚠️ 越界：正数和负数都会报错，但错误信息不同
    print("\n【越界 IndexError】")
    try:
        _ = s[10]
    except IndexError as exc:
        print(f"  s[10] 报错   : IndexError: {exc}")
    try:
        _ = s[-10]
    except IndexError as exc:
        print(f"  s[-10] 报错  : IndexError: {exc}   （负数越界的提示更长，因为要算负索引）")

    # 字符串的 index() 是找子串位置，和下标不是一回事
    print(f"\n⚠️ 别混淆：s[0] 取第 0 个字符，s.index('Py') 找子串首次出现的位置")
    print(f"  s[0]        = {s[0]!r}")
    print(f"  s.index('Py') = {s.index('Py')}   返回的是下标，不是子串")


# ============================================================
# 第 2 部分：切片
# ============================================================
def demo_slicing() -> None:
    """切片 s[start:stop:step]，左闭右开，永不越界。"""
    s = "abcdefghij"
    print(f"原串 : {s!r}（长度 {len(s)}）")
    print(f"语法 : s[start:stop:step]，区间是 [start, stop)，即「含 start 不含 stop」\n")

    print("【省略 start / stop】")
    print(f"  s[:4]  = {s[:4]!r}    # 等价于 s[0:4]")
    print(f"  s[4:]  = {s[4:]!r}    # 等价于 s[4:10]")
    print(f"  s[:]   = {s[:]!r}    # 全部复制一份新字符串")
    print(f"  s[2:8] = {s[2:8]!r}\n")

    print("【步长 step】")
    print(f"  s[::2]  = {s[::2]!r}    # 隔一个取一个：a c e g i")
    print(f"  s[1::2] = {s[1::2]!r}    # 从下标 1 开始隔一个")
    print(f"  s[::-1] = {s[::-1]!r}   # 倒序（反转字符串的经典写法）")
    print(f"  s[-3:]  = {s[-3:]!r}    # 负索引切片，取最后 3 个")
    print(f"  s[:-3]  = {s[:-3]!r}    # 去掉最后 3 个\n")

    # ⚠️ 切片永不越界，这是它比索引友好得多的地方
    print("【⚠️ 切片永不越界 —— 与索引的最大区别】")
    print(f"  s[5:100] = {s[5:100]!r}    # stop 超出长度，自动截到末尾，不报错")
    print(f"  s[100:]  = {s[100:]!r}      # start 超出长度 → 空字符串，不报错")
    print(f"  s[-100:] = {s[-100:]!r}     # 负 start 也会被规范到 0")
    print("  对比：s[100] 会抛 IndexError")
    print("  原理：切片内部做的是 min(max(start, 0), len) 的钳制处理")

    print("\n【切片越界时 stop < start 的行为】")
    print(f"  s[8:3] = {s[8:3]!r}    # start > stop → 空字符串")
    print("  ⚠️ 这不会报错，但也不是你想要的结果，务必自己保证顺序正确")

    print("\n【经典应用：定长切片做密码遮罩】")
    card = ID_CARD
    masked = card[:6] + "*" * len(card[6:])          # 前 6 位保留，后面全遮
    print(f"  身份证 {card} -> {masked}")
    print(f"  另一种：只露首尾  {card[:3]}***********{card[-4:]}")
    print(f"  切片也能套切片：{card[::2]!r}   每隔一位取一位")

    print("\n【三引号切片处理多行文本】")
    text = "第一行\n第二行\n第三行"
    lines = text.splitlines()
    print(f"  splitlines() = {lines}")
    print(f"  取最后一行   = {lines[-1]!r}   （用 [0] 会拿到第一行，这是新手高频错）")


# ============================================================
# 第 3 部分：不可变性
# ============================================================
def demo_immutable() -> None:
    """字符串不可变的后果：所有「修改」都是新建对象。"""
    print("【现象】所有看似「修改」的方法都返回新字符串，原串纹丝不动")
    s = "hello"
    results = {
        "upper()": s.upper(),
        "replace('l','L')": s.replace("l", "L"),
        "strip()": f"  {s}  ".strip(),
        "title()": s.title(),
    }
    for name, value in results.items():
        print(f"  {name:20} -> {value!r}")
    print(f"  原串 s 仍然是 {s!r}，id={id(s)}")

    print("\n【后果 1】不存在 s[0] = 'H' 这种写法")
    try:
        s[0] = "H"                      # type: ignore[index]
    except TypeError as exc:
        print(f"  TypeError: {exc}")
    print("  正确做法：s = 'H' + s[1:]  或者用切片拼接")

    print("\n【后果 2】循环里用 += 拼接是 O(n²)，10 万次会很慢")
    # 错误写法：每次 += 都新建一个完整的字符串
    slow = ""
    for ch in LOREM[:200]:
        slow += ch
    # 正确写法：先收集到列表，最后一次性 join（只新建一次）
    fast = "".join(list(LOREM[:200]))
    print(f"  两种写法结果相同：{slow == fast}")
    print(f"  += 方式创建了 {200} 个临时字符串，join 方式只创建了 1 个")
    # 真正要处理超长文本时，用 io.StringIO 能进一步降低开销
    buf = io.StringIO()                          # StringIO 是内存中的文本缓冲区，L23 详讲
    for ch in LOREM[:200]:
        buf.write(ch)
    print(f"  StringIO 方式结果也相同：{buf.getvalue() == slow}")

    print("\n【后果 3】必须传参的方法可以传 None 表示「保持原样」")
    # str.replace 的第三个参数是 count，传 0 表示「一个都不替换」
    print(f"  'aaa'.replace('a', 'b', 0) = {'aaa'.replace('a', 'b', 0)!r}   # 等于没改")
    print(f"  split 的 maxsplit 也类似：'a,b,c'.split(',', 0) = {'a,b,c'.split(',', 0)!r}")


# ============================================================
# 第 4 部分：字符串方法全景
# ============================================================
def demo_methods_by_category() -> None:
    """把常用字符串方法按用途分类记忆，比死记硬背有效。"""
    print("【查】找位置、判断包含")
    s = LOREM
    print(f"  find('brown')      = {s.find('brown')}   # 找不到返回 -1，安全")
    print(f"  rfind('o')         = {s.rfind('o')}   # 从右往左找")
    print(f"  index('brown')     = {s.index('brown')}   # 找不到抛 ValueError")
    print(f"  count('o')         = {s.count('o')}")
    print(f"  'fox' in s         = {'fox' in s}")
    print(f"  startswith('the')  = {s.startswith('the')}")
    print(f"  endswith('dog')    = {s.endswith('dog')}")
    print(f"  isidentifier()     = {'var_1'.isidentifier()}   # 能否作变量名")

    print("\n【转】大小写、首尾、类型转换")
    print(f"  upper() / lower()  = {s.upper()[:12]}... / {s.lower()[:12]}...")
    print(f"  title()            = {s.title()}")
    print(f"  capitalize()       = {s.capitalize()}")
    print(f"  swapcase()         = {'AbC'.swapcase()}")
    print(f"  strip/lstrip/rstrip= {s.strip()[:10]!r} / ...")
    print(f"  removeprefix('the ') = {s.removeprefix('the ')!r}   # 3.9+，只去一次前缀")
    print(f"  removesuffix('dog')  = {s.removesuffix('dog')!r}   # 只去一次后缀")

    print("\n【改】返回新字符串（不改原串）")
    print(f"  replace(old, new)  = {s.replace('quick', 'slow')[:20]}...")
    print(f"  replace(old,new,1) = {LOREM.replace('o', '0', 1)!r}   # 只替换第一处")
    print(f"  join(iterable)     = {', '.join(['a', 'b', 'c'])!r}   # 把序列拼成串")
    print(f"  zfill(width)       = {'7'.zfill(3)!r}")
    print(f"  center/ljust/rjust = {'ab'.center(8, '*')!r}")

    print("\n【拆】切分")
    print(f"  split(sep)         = {'a-b-c'.split('-')}")
    print(f"  rsplit(sep, max)   = {'a,b,c'.rsplit(',', 1)}")
    print(f"  splitlines()       = {'a\\nb'.splitlines()}   # 按行拆，自动吃换行符")
    print(f"  partition(sep)     = {'a=b=c'.partition('=')}   # 返回三元组，只切一刀")
    print(f"  rpartition(sep)    = {'a=b=c'.rpartition('=')}   # 从右边切一刀")

    print("\n【判】返回 bool，适合直接进 if")
    print(f"  isalpha()          = {'abc'.isalpha()}   只有字母")
    print(f"  isdigit()          = {'123'.isdigit()}   只有数字（0-9）")
    print(f"  isnumeric()        = {'一二三'.isnumeric()}   还包括中文数字等")
    print(f"  isalnum()          = {'abc123'.isalnum()}   字母数字混合")
    print(f"  isspace()          = {' '.isspace()}   全是空白")
    print(f"  isupper/islower    = {'ABC'.isupper()} / {'abc'.islower()}")
    print(f"  istitle()          = {'Hello World'.istitle()}")
    print(f"  isascii()          = {'abc'.isascii()}   # 纯 ASCII，检查英文文本很方便")

    print("\n【编】编码转换")
    print(f"  encode('utf-8')    = {'中文'.encode('utf-8')}   # str -> bytes")
    print(f"  bytes.decode()     = {'中文'.encode('utf-8').decode('utf-8')}   # bytes -> str")
    print("  ⚠️ 编码必须成对使用：encode 用什么，decode 就要用什么")


def demo_method_returns_new() -> None:
    """再强调一次：链式调用是安全的，因为每步都返回新对象。"""
    raw = "  Hello, World!  "
    cleaned = raw.strip().replace("World", "Python").upper()
    print(f"链式调用 raw.strip().replace(...).upper()")
    print(f"  原串     = {raw!r}   未被修改 ✅")
    print(f"  处理结果 = {cleaned!r}")
    print("\n为什么安全？因为链上每一步的返回值都是「新的字符串对象」，")
    print("你从未对同一个对象发起两次修改。真正危险的是把结果赋回原变量名，")
    print("那样会让人误以为「改了原串」，实际却是换了个新串。")


# ============================================================
# 第 5 部分：f-string 进阶
# ============================================================
def demo_fstring_advanced() -> None:
    """f-string 的四种进阶用法。"""
    name = "李雷"
    items = {"苹果": 3, "香蕉": 5, "橙子": 2}
    print("【用法 1：嵌套引号 —— 3.12 之前必须外单内双】")
    print(f"  当前 Python {sys.version_info.major}.{sys.version_info.minor}，"
          f"同引号嵌套（PEP 701）需要 3.12+")
    # f-string 内部如果需要用到引号，3.12 之前必须「外单内双」或「外双内单」
    apple = items["苹果"]
    print(f"  外双内单（3.12 之前通用）: apple = {apple}")
    # 字典取值最清晰的做法是先取到变量，避免引号嵌套带来的阅读负担
    banana = items.get("香蕉", 0)
    orange = items.get("橙子", 0)
    print(f"  先取变量再引用    : 苹果={apple} 香蕉={banana} 橙子={orange}")
    print("  💡 经验法则：f-string 里嵌套超过一层引号，就先把值取到变量里")

    print("\n【用法 2：调试 = 与多行 f-string】")
    total = sum(items.values())
    count = len(items)
    # = 自动输出「表达式=值」，调试时省去反复加 print
    print(f"  {total = }  ← 自动打印 total=10")
    print(f"  {total = :>6}  ← 还能配合格式说明符")
    # = 与转换符配合，注意顺序是「= 在前，转换符在后」
    print(f"  {name = !r}  ← 输出 name='李雷'")
    # 多行 f-string 适合拼提示语
    summary = f"""
    合计 {count} 种水果，共 {total} 个
    平均 {total / count:.2f} 个每种
    """
    print(summary)

    print("\n【用法 3：条件表达式直接嵌进 f-string】")
    for score, label in ((95, "A"), (75, "C"), (60, "F")):
        # 不想 if/else 就用三元，但记住上一课讲的优先级坑：整体要加括号
        text = f"{score} 分 → {'及格' if score >= 60 else '不及格'}"
        print(f"  {text}")

    print("\n【用法 4：格式说明符实用组合速查】")
    price = 12345.678
    rows = [
        f"{'原始':<14}{price}",
        f"{'千分位':<14}{price:,.2f}",
        f"{'百分比':<14}{0.8567:.2%}",
        f"{'科学计数':<14}{0.00012345:.3e}",
        f"{'十六进制':<14}{255:#06x}",
        f"{'定宽右对齐':<14}{'ab':>8}|",
        f"{'定宽居中':<14}{'ab':^8}|",
        f"{'补零':<14}{42:05d}",
    ]
    for row in rows:
        print(f"  {row}")

    print("\n【⚠️ f-string 的边界与限制】")
    print("  1) 3.12 之前，f-string 内部不能出现反斜杠（\\n 也不行）")
    print(f"  2) 3.12 之前，f-string 内部不能有 # 注释")
    print(f"  3) 变量名必须是合法标识符，不能写 f'{{a[0]}}' 之外的自定义变量名（L05 的模式匹配除外）")
    print(f"  4) f-string 总是返回 str，即使内容是数字：type(f'{{5}}') = {type(f'{5}').__name__}")
    print(f"  5) 要得到别的类型需要再包一层：int(f'{{5}}') = {int(f'{5}')}")


# ============================================================
# 第 6 部分：实战一 —— 解析 CSV 行
# ============================================================
def parse_csv_line() -> None:
    """把一行 CSV 文本解析成结构化字典，含各种脏数据的容错。"""
    print("【实战 1】解析一行 CSV")
    headers = ["姓名", "年龄", "城市", "职业", "手机"]
    print(f"表头: {headers}")
    print(f"数据: {CSV_LINE}\n")

    # 最朴素的切分：直接 split 逗号
    parts = CSV_LINE.split(",")
    print(f"split(',') -> {parts}   共 {len(parts)} 项")
    # 用 zip 把表头和数据对齐成键值对，这是处理单行 CSV 的标准做法
    record = dict(zip(headers, parts))
    print(f"dict(zip(...)) -> {record}")

    print("\n【逐字段清洗：真实的 CSV 数据永远不干净】")
    cleaned = {}
    for key, value in record.items():
        value = value.strip()                  # 去首尾空白
        if key == "年龄":
            try:
                value = int(value)             # 转成整数
            except ValueError:
                value = None                   # 转换失败要兜底，不能让程序崩
        cleaned[key] = value
    print(f"  清洗后: {cleaned}")
    print(f"  年龄类型: {type(cleaned['年龄']).__name__}   ← 字符串 '28' 已变成 int 28")

    print("\n【处理带引号和逗号的复杂情况】")
    # 标准 CSV 允许字段里包含逗号，只要用双引号包起来
    tricky = '韩梅梅,"北京,海淀",30'
    print(f"  原始行: {tricky}")
    # split 会把引号内的逗号也切开，这是错误的
    print(f"  ❌ 直接 split: {tricky.split(',')}   引号内的逗号被误切")
    # 标准解法是用标准库 csv 模块（推荐）
    fields = next(csv.reader(io.StringIO(tricky)))
    print(f"  ✅ csv.reader: {fields}   正确识别引号内的逗号")
    print("  💡 真实项目请永远用 csv 模块，不要自己 split")

    print("\n【实战 1 完整实现：处理多行 CSV】")
    data_lines = [
        "姓名,年龄,城市,职业,手机",               # 第 1 行是表头
        CSV_LINE,                                # 正常的一行
        '李雷,25,"上海,浦东区",设计师,13900139000',  # 城市里带逗号，必须加引号
        "韩梅梅,30,北京",                          # ⚠️ 故意少两列，用于演示列数校验
    ]
    table = parse_table(data_lines)
    print(f"  成功解析 {len(table)} 行：")
    for row in table:
        print(f"    {row}")


def parse_table(lines: list[str]) -> list[dict[str, str]]:
    """把多行 CSV 文本解析成字典列表，自动补齐/丢弃缺列的行。"""
    # 先用 csv 模块逐行解析，它能正确处理引号内的逗号和换行
    reader = csv.reader(lines)
    rows = list(reader)
    if not rows:
        return []
    headers = rows[0]                          # 第一行是表头
    table: list[dict[str, str]] = []
    for line_no, row in enumerate(rows[1:], start=2):
        # ⚠️ 列数不齐是真实 CSV 最常见的问题，必须显式处理而不是让 zip 静默截断
        if len(row) != len(headers):
            print(f"  ⚠️ 第 {line_no} 行列数不符（{len(row)} vs {len(headers)}），已跳过")
            continue
        table.append(dict(zip(headers, row)))
    return table


# ============================================================
# 第 7 部分：实战二 —— 简单脱敏
# ============================================================
def mask_phone(phone: str) -> str:
    """手机号脱敏：13812345678 -> 138****5678

    为什么需要脱敏？
        日志、报表、截图都可能泄露个人信息。合规要求是最小化暴露。
    """
    # 先校验长度，不合法就原样返回（脱敏失败时宁可不动也不要泄露）
    if len(phone) != 11 or not phone.isdigit():
        return phone
    # 用切片取出前缀 3 位和后缀 4 位，中间遮掉
    return f"{phone[:3]}****{phone[-4:]}"


def mask_id_card(card: str) -> str:
    """身份证脱敏：110101199003074321 -> 110101********4321"""
    if len(card) != 18:
        return card
    return f"{card[:6]}{'*' * 8}{card[-4:]}"


def mask_bank_card(card: str) -> str:
    """银行卡脱敏：保留后 4 位（这是银行卡的标准规则）"""
    digits = card.replace(" ", "")               # 先去掉可能存在的空格
    if not digits.isdigit() or len(digits) < 8:
        return digits
    return f"{'*' * (len(digits) - 4)}{digits[-4:]}"


def demo_masking() -> None:
    """脱敏的各种写法与工程实践。"""
    print("【实战 2】数据脱敏")

    print("\n【手机号】")
    print(f"  原文: {PHONE}")
    print(f"  切片法: {mask_phone(PHONE)}")
    # 为什么保留前 3 后 4：前 3 位是运营商号段，后 4 位用于对账核验
    print("  规则说明：前 3 位是运营商号段，后 4 位核对账目，中间 4 位完全遮蔽")

    print("\n【身份证】")
    print(f"  原文: {ID_CARD}")
    print(f"  结果: {mask_id_card(ID_CARD)}")
    print("  规则说明：前 6 位是行政区划、后 4 位是校验码，中间 8 位（生日）遮蔽")

    print("\n【银行卡】")
    print(f"  原文: 6222 0202 1234 5678")
    print(f"  结果: {mask_bank_card('6222 0202 1234 5678')}   顺便演示了去掉空格")

    print("\n【通用写法：用 str.zfill 或 ljust 补齐长度】")
    # 如果要遮蔽的对象来自数据库，字段长度可能不一致
    print(f"  统一成 11 位: {'1381234567'.zfill(11)!r}   ← 前面补零")
    print(f"  长度不足时保持原样: {mask_phone('138')}   ← 校验失败就不脱敏，也不报错")

    print("\n【工程实践：脱敏要放在「最后一道出口」】")
    print("  原则 1：日志输出前脱敏，不依赖「调用方自觉」")
    print("  原则 2：只保留「业务必需」的部分，能少露就少露")
    print("  原则 3：脱敏函数要幂等 —— 已脱敏的再脱敏一次，结果不变")
    # 幂等性验证：第二次调用不应改变结果
    once = mask_phone(PHONE)
    twice = mask_phone(once)
    print(f"  第一次脱敏 = {once}")
    print(f"  第二次脱敏 = {twice}")
    print(f"  是否稳定   = {once == twice}")


# ============================================================
# 第 8 部分：字符串的排序与比较
# ============================================================
def demo_sorting() -> None:
    """字符串可以比较和排序，规则是 Unicode 码位顺序。"""
    words = ["banana", "Apple", "cherry", "date", "Elderberry"]
    print(f"原始列表: {words}")
    # ⚠️ 默认排序区分大小写，因为 'A'(65) < 'a'(97)，大写排在小写前面
    print(f"默认排序  : {sorted(words)}")
    # 忽略大小写排序：先统一转小写作为排序键
    print(f"忽略大小写: {sorted(words, key=str.lower)}")
    # 按长度排序：key 传函数，返回值作为排序依据
    print(f"按长度    : {sorted(words, key=len)}")
    # 中文按 Unicode 码位排，实际效果约等于按拼音（但不完全等同）
    cn = ["北京", "上海", "广州", "深圳"]
    print(f"\n中文默认排序: {sorted(cn)}")
    # ⚠️ 中文排序依赖 Unicode 码位，不等于拼音序，需要拼音库 pypinyin（L26 会讲）")

    print("\n【数值字符串不能直接排序】")
    nums_as_str = ["10", "9", "100", "1"]
    print(f"  原始        : {nums_as_str}")
    print(f"  直接排序    : {sorted(nums_as_str)}   ⚠️ 按字符排，'100' 排在 '9' 前面")
    print(f"  转 int 后排 : {sorted(nums_as_str, key=int)}   ✅ 1 9 10 100")


# ============================================================
# 自我检验
# ============================================================
def verify_string_understanding() -> None:
    """用断言确认关键概念。"""
    s = "abcdefghij"
    # 索引
    assert s[0] == "a" and s[-1] == "j"
    # 切片左闭右开
    assert s[:4] == "abcd" and s[4:6] == "ef"
    assert s[::2] == "acegi"
    assert s[::-1] == "jihgfedcba"
    # 切片不越界，索引会越界
    assert s[5:100] == "fghij"
    assert s[100:] == ""
    # 不可变
    t = "hello"
    assert t.upper() == "HELLO" and t == "hello"
    # 方法
    assert "  x ".strip() == "x"
    assert "a,b".split(",") == ["a", "b"]
    assert "-".join(["a", "b"]) == "a-b"
    assert "aaa".replace("a", "b", 1) == "baa"
    assert "abc".find("c") == 2 and "abc".find("z") == -1
    assert "123".isdigit() and not "12a".isdigit()
    assert "a".removeprefix("a") == ""
    assert "a=b=c".partition("=") == ("a", "=", "b=c")
    # f-string
    v = 5
    assert f"{v}" == "5" and f"{v:03d}" == "005"
    assert f"{v = }" == "v = 5"
    # 脱敏函数
    assert mask_phone("13812345678") == "138****5678"
    assert mask_id_card(ID_CARD) == "110101********4321"
    print("✅ verify_string_understanding 全部断言通过")


# ============================================================
# 程序入口
# ============================================================
def main() -> None:
    """按教学顺序调用全部演示函数。"""
    print("=" * 64)
    print("L04 · 字符串深入")
    print("=" * 64)
    demo_indexing()
    print("\n" + "-" * 64)
    demo_slicing()
    print("\n" + "-" * 64)
    demo_immutable()
    print("\n" + "-" * 64)
    demo_methods_by_category()
    print("\n" + "-" * 64)
    demo_method_returns_new()
    print("\n" + "-" * 64)
    demo_fstring_advanced()
    print("\n" + "-" * 64)
    parse_csv_line()
    print("\n" + "-" * 64)
    demo_masking()
    print("\n" + "-" * 64)
    demo_sorting()
    print("\n" + "-" * 64)
    verify_string_understanding()
    print("\n🎉 L04 演示结束")


# 标准入口约定：直接运行本文件执行 main()，被 import 时不执行
if __name__ == "__main__":
    main()
