"""L03 输入输出与格式化 —— 配套教案配套示例。

运行：python examples/L03_io_format.py

⚠️ 本脚本包含 input() 调用。为了让脚本能无人值守地跑完，
   所有 input() 都通过 safe_input() 包装：
   - 有真实终端输入时正常读取
   - 没有输入（重定向 / 自动化运行）时自动返回预设默认值

本脚本演示六件事：
    1. input() 永远返回字符串，以及由此引发的所有后果
    2. print() 的 sep / end / flush 参数与「输出到 stderr」
    3. 三种格式化方式：f-string / % / str.format() 的取舍
    4. 转义字符与原始字符串
    5. 常用字符串操作：strip / split / join / replace / find 家族
    6. 格式化语法全解：对齐、宽度、精度、千分位、进制
"""

import sys                                   # 标准库：用于判断是否有真实终端输入

# ============================================================
# 模块级常量
# ============================================================
PROMPT_NAME = "请输入你的姓名"
DEFAULT_NAME = "同学"                        # input 为空或无输入时的兜底值
MAX_WIDTH = 32                               # 表格列宽，演示对齐
DISCOUNT = 0.85                              # 折扣率，演示百分比格式


# ============================================================
# 第 0 部分：让脚本能独立运行的安全输入
# ============================================================
def safe_input(prompt: str, default: str = "") -> str:
    """包装 input()：读不到真实输入时自动返回默认值，绝不崩溃。

    为什么需要它？
        自动化测试、CI、或者把输出重定向到文件时，stdin 里没有内容，
        input() 会直接抛 EOFError 让整个脚本挂掉。脚本要「能独立运行」，
        就必须考虑这条路径。
    """
    # sys.stdin.isatty() 返回 True 表示「连接着交互式终端」
    # 重定向或无输入时它是 False，此时直接用默认值，跳过 input()
    try:
        if not sys.stdin.isatty():
            return default
        text = input(prompt)                  # 只有确认是真实终端才调用 input
    except EOFError:                          # input 被流关闭时的兜底
        return default
    # 用户可能直接回车（空字符串），这时也用默认值，但要保留 strip 过的结果
    return text.strip() if text.strip() else default


# ============================================================
# 第 1 部分：input() 的真相
# ============================================================
def demo_input_returns_str() -> None:
    """input() 永远返回 str，这是 90% 输入相关 bug 的根源。"""
    print("【实验】input() 返回值到底是什么类型")
    # 无论用户输入什么，input 的返回值都是字符串
    raw = safe_input("  请随便输入一个值（无输入时用 42）：", default="42")
    print(f"  输入内容 = {raw!r}")
    print(f"  type(raw) = {type(raw).__name__}   ← 永远是 str，和你输入的内容无关")
    # 即使输入看起来是数字，它依然是字符串
    print(f"  raw == '42' -> {raw == '42'}")
    print(f"  raw == 42   -> {raw == '42'}   ⚠️ 前一个 False 说明你写错了比较对象")
    # 字符串相加是拼接，不是求和
    print(f"  raw + 1 -> ", end="")
    try:
        _ = raw + 1
    except TypeError as exc:
        print(f"TypeError: {exc}")
    print(f"  int(raw) + 1 = {int(raw) + 1}   ✅ 必须先转类型")
    print(f"  raw * 2 = {raw * 2!r}   ⚠️ 字符串 * 2 是重复两次，不是乘以 2\n")

    print("【实验】input() 会保留前导空格，除非你 strip")
    padded = safe_input("  请输入带空格的文本（无输入时用 '  hi  '）：", default="  hi  ")
    print(f"  原样 = {padded!r}   len={len(padded)}")
    print(f"  strip 后 = {padded.strip()!r}   len={len(padded.strip())}")

    print("\n【实验】EOFError：没有输入可读时会怎样")
    print("  input() 在流结束时抛 EOFError，这正是 safe_input 要捕获的异常")

    print("\n【实验】带提示与不带提示")
    # input("提示") 的提示会打印出来但不带换行，所以常配合 print 后的空行
    v1 = safe_input("  带提示的 input：", default="A")
    print(f"  取值 = {v1!r}（用户看不到自己输入了什么）")


def demo_int_input_pitfall() -> None:
    """经典翻车：用户输入 "3.14"，int() 却报错。"""
    print("\n【经典翻车现场】")
    # int() 不接受带小数点的字符串
    try:
        int("3.14")
    except ValueError as exc:
        print(f"  int('3.14')   -> ValueError: {exc}")
    # float() 可以接受整数形式的字符串
    print(f"  float('3.14') -> {float('3.14')}   ✅")
    # float() 还能处理带空白的
    print(f"  float(' 3.14 ')-> {float(' 3.14 ')!r}   ✅ int/float 都会忽略首尾空白")

    print("\n【正确做法】永远用 try/except 包住输入转换")
    def ask_number(prompt: str, default: float) -> float:
        """反复询问直到拿到合法数字，或用户输入为空用默认值。"""
        text = safe_input(prompt, default=str(default))
        try:
            return float(text)
        except ValueError:
            print(f"  ⚠️ {text!r} 不是数字，改用默认值 {default}")
            return default

    price = ask_number("  请输入价格（无输入时用 19.9）：", default=19.9)
    qty = ask_number("  请输入数量（无输入时用 3）：", default=3)
    print(f"  小计 = {price} × {qty} = {price * qty:.2f}")


# ============================================================
# 第 2 部分：print() 的完整用法
# ============================================================
def demo_print() -> None:
    """print 的 sep / end / flush 三个参数，以及实战用法。"""
    print("【print 的三个关键字参数】")

    # sep：多个参数之间的分隔符，默认是一个空格
    print("  默认 sep:", "甲", "乙", "丙")
    print("  sep=':':", "甲", "乙", "丙", sep=",")
    print("  sep='':", "甲", "乙", "丙", sep="")            # 完全不隔开
    print("  sep=' | ':", "甲", "乙", "丙", sep=" | ")

    # end：输出结束后追加的字符，默认是换行 \n
    print("  默认 end:" , "第一行", end="")
    print(" ← 没有换行，所以和这行接在一起了")
    print("  end='' :", "A", "B", end="")                   # 连续打印进度条就靠它
    print(" ← 演示 end=''")
    print("  end=';':", "甲", "乙", end=";\n")               # 分号分隔再手动换行

    # 数字的格式化：print 支持直接写 sep 和格式化
    print("\n【print 的实用技巧】")
    # 进度条：不换行 + 手动擦除上次输出
    total = 5
    for i in range(1, total + 1):
        # end="" 让光标停在行尾，\r 把光标拉回行首，形成原地刷新的效果
        print(f"\r进度 {i}/{total} {'█' * i}", end="")
    print()                                                 # 最后补一个换行收尾

    # flush=True：强制立即输出，不等缓冲区。
    # 用途：长时间运行的任务、需要实时看到日志的调试场景
    print("  这行会立刻显示，即使 stdout 被重定向（flush=True）", flush=True)
    # 注意：print 的内容到 stderr 就不受重定向影响，常用于把「结果」和「日志」分开
    # 在本脚本中为了保证输出顺序清晰，这里只做注释说明，不实际切换流


def demo_stderr_note() -> None:
    """补充说明：print 默认输出到 stdout，日志应输出到 stderr。"""
    print("\n【stdout vs stderr】")
    print("  print(...) 默认写 stdout，是程序「正常产出」")
    print("  print(..., file=sys.stderr) 写 stderr，是「诊断信息」")
    print("  好处：`python x.py > 结果.txt` 时日志仍在终端可见")
    print("  这是所有正经命令行工具的标准做法（L23 会系统讲）")
    # 实际演示一次 stderr 输出
    print("  ↓ 下面这一行是 stderr（在终端里也是黑色/红色，重定向后才会分离）", file=sys.stderr)


# ============================================================
# 第 3 部分：三种格式化方式
# ============================================================
def demo_three_format_ways() -> None:
    """f-string、% 占位符、str.format() 的完整对比。"""
    name = "张三"
    age = 20
    score = 87.456
    print("【同一条信息的三种写法】\n")

    # 方式 1：f-string（Python 3.6+）。首选，几乎在所有场景都该用它
    print(f"方式1 f-string : 我叫{name}，今年{age}岁，成绩{score}")
    # f-string 里可以写完整的表达式，包括函数调用
    print(f"  表达式能力强 : 上课年份约 {2026 + 1}，分数四舍五入 {round(score)}")

    # 方式 2：% 格式化（C 风格）。优点是和旧代码、老库兼容
    print(f"\n方式2 %% 占位符  : 我叫%s，今年%d岁，成绩%.2f" % (name, age, score))
    print("  %s 用于任何类型，%d 用于整数，%.2f 表示两位小数")
    # %s 对对象也能工作
    print(f"  %%s 也接受对象 : 列表{[1, 2]} 元组{(3, 4)}")

    # 方式 3：str.format()，用 {} 占位，可以指定位置和名称
    print(f"\n方式3 .format()  : 我叫{name}，今年{age}岁，成绩{score}")
    print("  自动按位置填 : 我叫{0}，今年{1}岁".format(name, age))
    print("  重复使用     : {0}和{0}和{0}".format("甲"))
    print("  格式说明符   : {:.2f}".format(score))
    print("  命名参数     : {user} 在 {city}".format(user="李四", city="北京"))

    print("\n【怎么选】")
    print("  f-string   : 新代码默认选它，可读性最好，3.12+ 解析器已非常宽松")
    print("  %          : 维护老代码时会遇到，自己写新代码不推荐")
    print("  .format()  : 需要运行时动态拼接模板时仍有用（f-string 的变量必须是合法标识符）")

    print("\n【f-string 的额外威力】")
    # = 调试开关：f"{expr=}" 自动打印「expr=值」，是 3.8+ 的调试利器
    n = 42
    print(f"  调试输出   : {n=}")                              # 输出 n=42
    print(f"  带格式     : {n = }")                            # 注意 = 两侧有空格时保留空格
    # !r / !s / !a 转换说明符
    print(f"  !r 原样表示: {name!r}    # 加引号显示")
    print(f"  !s 字符串  : {name!s}")
    print(f"  !a ASCII   : {name!a}    # 中文会被转义成 \\u 形式")
    # 多行 f-string，适合长文本
    text = f"""
    多行 f-string 示例：
    姓名：{name}
    年龄：{age}
    """
    print(text)


# ============================================================
# 第 4 部分：格式化语法全解
# ============================================================
def demo_format_spec() -> None:
    """格式说明符的完整语法：[[fill]align][sign][#][0][width][,][.precision][type]"""
    print("【格式说明符的完整结构】")
    print("  语法：[[填充字符][对齐方式]][正负号][#][0][宽度][分组符][.精度][类型]")
    print("  常用类型：f(定点) e(科学计数) d(十进制整数) %  b(oct hex) s(字符串) g(自动)\n")

    n = 3.14159
    print("【精度 .】")
    print(f"  {n:.0f}   保留 0 位小数（注意是四舍五入，不是截断）")
    print(f"  {n:.2f}   保留 2 位小数 -> {n:.2f}")
    print(f"  {n:8.2f}  总宽 8（含小数点），不足左侧补空格")
    print(f"  {n:.5e}  科学计数法 -> {n:.5e}")

    print("\n【宽度与对齐】")
    print(f"  {42:<8}|   < 左对齐，宽度 8")
    print(f"  {42:>8}|   > 右对齐（数字的默认值）")
    print(f"  {42:^8}|   ^ 居中")
    print(f"  {'ab':^8}|  字符串默认左对齐")

    print("\n【填充字符】")
    print(f"  {42:*>8}|  用 * 填充右边")
    print(f"  {42:-<8}|  用 - 填充左边（模拟账单对齐）")
    print(f"  {42:_^8}|  用 _ 填充两边")

    print("\n【千分位与分组符】")
    big = 1234567.891
    print(f"  {big:,}        逗号分组 -> {big:,}")
    print(f"  {big:_}        下划线分组 -> {big:_}（3.6+ 支持，可读性更好）")
    print(f"  {big:,.2f}     分组 + 2 位小数 -> {big:,.2f}")
    print(f"  {12345678901234567890:,} 大整数分组也能用")

    print("\n【进制与其他类型】")
    num = 255
    print(f"  {num:b}   二进制 -> {num:b}")
    print(f"  {num:o}   八进制 -> {num:o}")
    print(f"  {num:x}   十六进制（小写）-> {num:x}")
    print(f"  {num:X}   十六进制（大写）-> {num:X}")
    print(f"  {num:#x}  带 0x 前缀 -> {num:#x}")
    print(f"  {num:#010b} 二进制补齐 10 位 -> {num:#010b}")
    print(f"  {42:5d}   整数右对齐宽度 5 -> {42:5d}")
    print(f"  {42:+d}   强制显示正号 -> {42:+d}")
    print(f"  {42: d}   非负数前留空格（表格对齐常用）-> {42: d}")

    print("\n【常用组合速记】")
    money = 12345.6
    rows = [
        f"{'科目':<10}{'金额（元）':>14}",
        f"{'语文':<10}{money:>14,.2f}",
        f"{'数学':<10}{money * 1.5:>14,.2f}",
        f"{'体育':<10}{0:>14,.2f}",
    ]
    print("  " + "\n  ".join(rows))
    print(f"  折扣后金额: {money * DISCOUNT:,.2f}（{DISCOUNT:.0%}）")


# ============================================================
# 第 5 部分：转义字符与原始字符串
# ============================================================
def demo_escapes() -> None:
    """常见转义字符，以及路径场景为什么必须用原始字符串。"""
    print("【常用转义字符】")
    print(r"  \n  换行")
    print(r"  \t  水平制表符（对齐表格常用）")
    print(r"  \r  回车（进度条靠它回到行首）")
    print(r"  \\  反斜杠本身")
    print(r"  \'  \"  单引号 / 双引号")
    print(r"  \0  空字符（几乎不用）")
    print(r"  \a  响铃（几乎不用）")
    print(r"  \b  退格符")
    print(r"  \f  换页符")
    print(r"  \u4e2d  Unicode 码位转义，\u4e2d\u6587 = 中文")
    print(r"  \U0001F600  完整 Unicode，\U0001F600 = 表情")

    print("\n【实际效果演示】")
    print("  第一行\t第二列|换行用 \\n")
    print("  竖线 | 制表 | 对齐 | 演示")
    print(f"  emoji 直出: \U0001F600 \U0001F680")
    print(f"  Unicode 转义再解码: {chr(0x4E2D)}{chr(0x6587)}")

    print("\n【raw 字符串：路径场景必用】")
    # 普通字符串里 \t 是制表符，\n 是换行，路径会被吃掉
    bad_path = "C:\temp\new\file.txt"
    print(f"  ❌ 普通字符串: {bad_path!r}")
    print(f"     实际内容  : {bad_path}   ← \\t 变成了制表符，\\n 变成了换行！")
    # 原始字符串让反斜杠保持字面意义
    good_path = r"C:\temp\new\file.txt"
    print(f"  ✅ 原始字符串: {good_path!r}")
    print(f"     实际内容  : {good_path}")
    # 但 raw 字符串不能以单个反斜杠结尾（那是语法错误）
    print(f"  推荐做法     : 用 pathlib.Path 拼路径，从根本上绕开转义问题（L23 详讲）")

    print("\n【多行字符串的两种写法】")
    triple_double = """第一行
第二行
第三行"""
    triple_single = '''也支持
多行'''
    print(f"  三双引号行数 = {len(triple_double.splitlines())}")
    print(f"  三单引号行数 = {len(triple_single.splitlines())}")
    # 开头加个反斜杠可以吃掉第一行的换行（行连接）
    joined = """\
这是第一行
这是第二行"""
    print(f"  用行连接后首行 = {joined.splitlines()[0]!r}   ← 没有多余空行")


# ============================================================
# 第 6 部分：常用字符串操作
# ============================================================
def demo_string_ops() -> None:
    """字符串最常用的十组操作，每组说明「解决什么问题」。"""
    print("【1. 去空白 strip】去掉首尾的空白字符（空格/换行/制表符）")
    text = "   \t Hello Python \n  "
    print(f"  原样  : {text!r}")
    print(f"  strip : {text.strip()!r}            # 通用去首尾空白")
    print(f"  lstrip: {text.lstrip()!r}           # 只去左边")
    print(f"  rstrip: {text.rstrip()!r}           # 只去右边")
    print(f"  传参数 : {'xxhixx'.strip('x')!r}      # 只去掉指定字符集的任意组合")

    print("\n【2. 切分 split】把一整段文本拆成若干份")
    csv_line = "张三,18,北京,程序员"
    parts = csv_line.split(",")
    print(f"  {csv_line!r}.split(',') -> {parts}   共 {len(parts)} 份")
    print(f"  'a b  c'.split()       -> {'a b  c'.split()!r}   不传参数按任意空白切，自动忽略连续空白")
    print(f"  'a\nb\tc'.split()      -> {'a\nb\tc'.split()!r}   同时处理换行和制表符")
    print(f"  'a,b,c'.split(',', 1)  -> {'a,b,c'.split(',', 1)!r}   最多切 1 次")
    print(f"  'a,b,c'.rsplit(',', 1) -> {'a,b,c'.rsplit(',', 1)!r}   从右边切")
    print("  ⚠️ split 返回的是列表；空字符串 split 会得到 [''] 需留意")

    print("\n【3. 拼接 join】把一堆片段高效拼成一个字符串")
    words = ["Python", "入门", "教程"]
    print(f"  {words} -> {', '.join(words)!r}    # 用逗号加空格连接")
    print(f"  {words} -> {''.join(words)!r}          # 直接相连")
    print(f"  {words} -> {'-'.join(words)!r}         # 用短横线连接")
    # ⚠️ join 的接收者必须是 str
    print("  ⚠️ join 要求所有元素都是 str，混进 int 会报 TypeError:")
    try:
        _ = ",".join(["a", 1])
    except TypeError as exc:
        print(f"     TypeError: {exc}")
    print(f"     解决办法: {','.join(str(x) for x in ['a', 1])!r}")

    print("\n【4. 替换 replace】批量替换子串")
    s = "2026-01-15"
    print(f"  {s!r}.replace('-', '/') -> {s.replace('-', '/')!r}")
    print(f"  指定替换次数: {s.replace('-', '/', 1)!r}   只换第一个")
    print(f"  连续链式替换: {'a-b-c'.replace('-', '+').replace('+', '=')!r}")

    print("\n【5. 查找 find 家族】定位子串位置")
    hay = "Hello, Python World"
    print(f"  查找对象: {hay!r}")
    print(f"  find('Python')     = {hay.find('Python')}    # 找不到返回 -1")
    print(f"  index('Python')    = {hay.index('Python')}   # 找不到抛 ValueError")
    print(f"  find('Java')       = {hay.find('Java')}    # -1 表示不存在")
    print(f"  startswith('Hello') = {hay.startswith('Hello')}   前缀判断")
    print(f"  endswith('World')  = {hay.endswith('World')}   后缀判断")
    print(f"  count('o')         = {hay.count('o')}      # 出现次数")
    try:
        _ = hay.index("Java")
    except ValueError as exc:
        print(f"  index 找不到会崩: ValueError: {exc}")
    print(f"  rfind('o')         = {hay.rfind('o')}     # 从右往左找，返回最后一次的位置")

    print("\n【6. 大小写转换】处理英文文本")
    w = "python is Fun"
    print(f"  upper()   -> {w.upper()!r}")
    print(f"  lower()   -> {w.lower()!r}")
    print(f"  capitalize() -> {w.capitalize()!r}   # 只把首字母大写，其余不动")
    print(f"  title()   -> {w.title()!r}        # 每个单词首字母大写")
    print(f"  swapcase()-> {w.swapcase()!r}      # 大小写互换")
    print("  ⚠️ 这些方法对中文无效（中文没有大小写概念），也不影响原字符串")

    print("\n【7. 判断类方法】bool 返回，适合直接放进 if")
    for probe in ("  ", "abc", "123", "12.3", "  12  ", ""):
        print(f"  {probe!r:>8}: isdigit={probe.isdigit()}, isalpha={probe.isalpha()}, "
              f"isalnum={probe.isalnum()}, isspace={probe.isspace()}, isnumeric={probe.isnumeric()}")
    print("  ⚠️ isdigit('²') 为 True（Unicode 上标数字），isnumeric 范围更广，isdigit 更严")
    print(f"  '文件名.txt'.isidentifier() = {'文件名.txt'.isidentifier()}  # 能否作为变量名")

    print("\n【8. 对齐填充 zfill / center / ljust / rjust】不用 f-string 时也能用")
    print(f"  zfill:  {'42'.zfill(8)!r}     # 补零，常用于生成编号")
    print(f"  center: {'a'.center(9, '-')!r}     # 居中填充")
    print(f"  ljust:  {'a'.ljust(5, '.')!r}   rjust:  {'a'.rjust(5, '.')!r}")

    print("\n【9. 常用查询属性】")
    print(f"  len(hay)          = {len(hay)}")
    print(f"  max(hay) / min(hay)= {max(hay)!r} / {min(hay)!r}   # 按 Unicode 码位取极值")


def demo_string_pitfalls() -> None:
    """字符串相关的三个高频坑。"""
    print("\n【坑 1】字符串不可变，任何「修改」都产生新对象")
    s = "hello"
    s2 = s.upper()                 # s 没变，s2 是新对象
    print(f"  s = {s!r}, s.upper() = {s2!r}, s 未被修改")
    print("  ⚠️ 所以循环里 s += x 是 O(n²)，大量拼接用 ''.join(列表)")
    parts = []
    for i in range(1000):
        parts.append(str(i))
    print(f"  1000 段 join 一次搞定: {len(''.join(parts))} 字符")

    print("\n【坑 2】+= 对 list 和 str 行为完全不同")
    lst = [1, 2]
    lst += [3]                     # list 的 += 是原地追加（extend）
    print(f"  list += [3] -> {lst}   原对象被改了，id 不变")
    txt = "ab"
    txt += "cd"                    # str 的 += 是新建对象再赋值
    print(f"  str  += 'cd' -> {txt}   ⚠️ 每次都新建对象，id 变了")

    print("\n【坑 3】split 结果直接使用前要考虑空输入")
    print(f"  'a,,b'.split(',') -> {'a,,b'.split(',')!r}   中间有连续分隔符会得到空串")
    print(f"  ''.split(',')     -> {''.split(',')!r}        ⚠️ 有一个空串，不是空列表！")
    print(f"  ''.split()        -> {''.split()!r}          # 不传参时才是空列表")
    print("  处理 CSV 前请过滤: [p for p in text.split(',') if p.strip()]")


# ============================================================
# 自我检验
# ============================================================
def verify_io_understanding() -> None:
    """用断言确认关键格式化与字符串行为。"""
    # 对齐与精度
    assert f"{3.14159:.2f}" == "3.14"
    assert f"{42:5d}" == "   42"
    assert f"{42:<5}|" == "42   |"
    assert f"{42:^5}|" == " 42  |"
    assert f"{1234567:,}" == "1,234,567"
    assert f"{0.85:.0%}" == "85%"
    # 类型转换
    assert f"{255:#x}" == "0xff"
    # 调试开关 f"{x=}"
    debug_num = 1
    assert f"{debug_num = }" == "debug_num = 1"
    # 字符串操作
    assert "  x  ".strip() == "x"
    assert "a,b,c".split(",") == ["a", "b", "c"]
    assert ",".join(["a", "b"]) == "a,b"
    assert "hello".replace("l", "L") == "heLLo"
    assert "hello".find("z") == -1
    assert "Hello".startswith("He") and "Hello".endswith("lo")
    assert "123".isdigit() and "abc".isalpha()
    # 转义
    assert "\n" == chr(10) and "\t" == chr(9)
    assert r"a\tb" == "a\\tb"       # 原始字符串里 \t 是两个字面字符
    assert "\U0001F600" == "\U0001F600"
    print("✅ verify_io_understanding 全部断言通过")


# ============================================================
# 程序入口
# ============================================================
def main() -> None:
    """按教学顺序调用全部演示函数。"""
    print("=" * 64)
    print("L03 · 输入输出与格式化")
    print("=" * 64)
    demo_input_returns_str()
    print("\n" + "-" * 64)
    demo_int_input_pitfall()
    print("\n" + "-" * 64)
    demo_print()
    print("\n" + "-" * 64)
    demo_stderr_note()
    print("\n" + "-" * 64)
    demo_three_format_ways()
    print("\n" + "-" * 64)
    demo_format_spec()
    print("\n" + "-" * 64)
    demo_escapes()
    print("\n" + "-" * 64)
    demo_string_ops()
    print("\n" + "-" * 64)
    demo_string_pitfalls()
    print("\n" + "-" * 64)
    verify_io_understanding()
    print("\n🎉 L03 演示结束")


# 标准入口约定：直接运行本文件执行 main()，被 import 时不执行
if __name__ == "__main__":
    main()
