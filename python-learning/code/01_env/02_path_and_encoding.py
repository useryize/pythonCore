# -*- coding: utf-8 -*-
"""
================================================================================
文件：02_path_and_encoding.py
模块：01_env（环境与工具链配套）

【本文件演示的语法点列表】
  1. pathlib.Path —— 面向对象的路径处理（/ 运算符、mkdir、iterdir、with_name）
  2. Windows 中文路径（GBK 控制台编码 vs 文件系统 UTF-8 编码的差异）
  3. 编码三要素：源文件编码 / 声明编码 / I/O 编码，各自独立
  4. open(..., encoding=...) 显式指定编码，newline="" 的作用
  5. 临时目录 tempfile.TemporaryDirectory + 上下文管理器 with
  6. sys.stdout.reconfigure / io.StringIO —— 标准输出的重定向与恢复
  7. str.encode / bytes.decode 与编解码错误处理策略 errors=
  8. 换行符归一化：文本模式 vs 二进制模式的 '\n' / '\r\n'

【设计意图】
  中文 Windows 环境下最大的坑不是语法，而是"编码"。
  Python 3 默认用 UTF-8 读写源文件，但 Windows 控制台默认 GBK，
  于是"print 中文正常、print emoji 崩溃"成为经典现象。
  本文件把路径与编码放在一起演示，是因为它们在真实项目中总是纠缠出现。

【预期输出摘要】
  [1] pathlib 基础：Path 拼接、绝对化、exists、suffix、name、stem
  [2] Windows 路径陷阱：反斜杠、盘符、路径拼接的三种方式对比
  [3] 源码编码：文件自身声明与解释器默认编码
  [4] 控制台编码：stdout.encoding 与文件 I/O 默认编码
  [5] UTF-8 读写演示：创建含中文文件 -> 读回 -> 校验字节一致
  [6] 编解码容错：strict / ignore / replace 三种 errors 策略对比
  [7] 换行符：文本模式与二进制模式读同一文件结果不同
  [8] 输出重定向：临时把 stdout 换成内存缓冲，再恢复并验证
  全部临时文件在退出前自动清理，不留垃圾。
================================================================================
"""

import io
import os
import os.path
import sys
import tempfile
from pathlib import Path


# ============================================================================
# 语法解析 1：pathlib —— 路径即对象
# ============================================================================
# 【语法规则】
#   from pathlib import Path
#   p = Path("a") / "b" / "c.txt"     # / 是运算符重载，不是除法
#   p = Path.cwd()                     # 类方法获取当前目录
#   p = Path(r"D:\data")               # r 前缀：原始字符串，反斜杠不转义
#   p.exists() / p.is_file() / p.is_dir()
#   p.suffix  扩展名含点 ".txt"； p.stem  主名不含扩展名 "c"； p.name  "c.txt"
#   p.parent  父目录； p.name = "新名" 改主名； p.with_suffix(".md") 换扩展名
#   p.iterdir()  返回生成器，逐个列出子项； p.mkdir(parents=True, exist_ok=True)
# 【执行顺序】
#   __truediv__ 是 Path 定义的方法，Python 遇到 a / b 时会自动调用 a.__truediv__(b)。
#   Path 内部不改动系统状态，所有写操作（mkdir/rename）都要显式调用方法。
# 【设计意图】
#   pathlib 明确取代了 os.path 的字符串拼接。
#   关键收益有二：
#   (1) "/" 重载让代码读起来像路径本身，而不是像在做除法；
#   (2) 把"路径 + 文件系统操作"绑在一个对象上，跨平台逻辑由库的作者写一次。


def demo_pathlib():
    print("[1] pathlib 基础")

    # 构造绝对路径。Path 不会要求路径真实存在，纯粹是字符串对象化。
    p = Path("demo") / "data" / "report.txt"
    print(f"    拼接结果      = {p}")
    # as_posix() 强制输出 '/' 分隔的 POSIX 风格，用于日志、URL、配置，保证跨平台一致
    print(f"    as_posix()   = {p.as_posix()}")
    # resolve() 返回绝对化的规范路径，会消解 '.' 和 '..'，Windows 上还会补盘符
    print(f"    resolve()    = {p.resolve()}")
    print(f"    exists()     = {p.exists()}  (布尔值，未创建所以为 False)")
    print(f"    suffix/stem  = {p.suffix!r} / {p.stem!r}")

    # with_name 改名不改扩展名，with_suffix 改扩展名不改主名。
    # 它们返回新 Path 而非原地修改，因为 Path 被设计为不可变值对象。
    renamed = p.with_name("final_report.txt")
    changed = p.with_suffix(".md")
    print(f"    with_name    = {renamed}")
    print(f"    with_suffix  = {changed}")
    print(f"    parent       = {p.parent}")

    # Path.cwd() 与 Path.home() 是两个最常用的类方法构造点
    print(f"    cwd          = {Path.cwd()}")
    print(f"    home         = {Path.home()}")

    # r 前缀的关键作用：r"D:\new\test" 里 \n 不是换行符而是反斜杠+n 两个字符。
    # 非 raw 字符串中 "\n" 会被解析为换行，"New" 里的 \n 甚至会破坏路径结构。
    raw = Path(r"D:\new\test.txt")
    non_raw = Path("D:\\new\\test.txt")
    print(f"    raw 字符串   = {raw}")
    print(f"    转义字符串   = {non_raw}  (两者等价，都要用双反斜杠)")


# ============================================================================
# 语法解析 2：Windows 路径的三个经典陷阱
# ============================================================================
# 【语法规则】
#   陷阱一：'\' 在字符串里是转义符，路径必须用 \\ 或 r"" 或 pathlib
#   陷阱二：'C:' 之后的反斜杠无法续行，会被当作行连接符
#   陷阱三：不能用 str 拼接 os.sep 做 URL 或数据库串，要用 os.path / pathlib
# 【设计意图】
#   Python 沿用了 C 系的字符串转义规则，'\' 天然有特殊含义。
#   pathlib 的设计正是为了让人彻底不用手写转义 —— 只要不手写字符串拼接就没有坑。


def demo_windows_pitfalls():
    print("[2] Windows 路径陷阱")

    # 陷阱一：单个反斜杠
    # "\x" 中 x 不是合法转义字符时，Python 3.12+ 给出 SyntaxWarning 而非静默通过，
    # 3.14 起将成为正式错误 —— 这是 PEP 相关收紧的体现。合法转义如 "\t" "\n" 仍会生效。
    safe = "D:\\logs\\app.log"
    print(f"    正确双反斜杠  = {safe}")

    # 陷阱二：路径以偶数个反斜杠结尾会续行，路径以单个反斜杠结尾则语法错误
    print(f"    行尾续行陷阱  = {chr(92) + chr(92)} 表示字符串继续，{'\\\\'!r} 才是路径结尾")

    # 陷阱三：路径拼接三种方式对比
    base = "D:\\project"
    # 方式1 手工拼接（依赖 os.sep，可行但啰嗦）
    manual = base + os.sep + "src" + os.sep + "main.py"
    # 方式2 os.path.join（正确做法：一次调用，内部处理分隔符）
    joined = os.path.join(base, "src", "main.py")
    # 方式3 pathlib（现代最佳实践）
    pl = Path(base) / "src" / "main.py"

    print(f"    手工拼接      = {manual}")
    print(f"    os.path.join  = {joined}")
    print(f"    pathlib       = {pl}")
    print(f"    三者一致      = {manual == joined == str(pl)}")

    # os.path.join 的隐藏规则：遇到绝对路径参数时，会丢弃之前的所有部分。
    # 这是从 Unix 的 cp/mv 语义继承来的，也是很多"为什么路径变成 C:\\Windows\\system32"的原因。
    reset = os.path.join(base, "D:\\other", "file.txt")
    print(f"    join 遇绝对路径 = {reset}  (前面的 base 被丢弃！)")
    # 注意：pathlib 也遵循同样的"锚定"规则（带盘符即绝对路径），
# 所以这里输出同样是 D:\other\file.txt。区别只在于 pathlib 是显式的属性访问，
# 读者能立刻看出为什么被重置，而字符串拼接版本的意图完全被掩盖了。
    reset_pl = Path(base) / "D:/other" / "file.txt"
    print(f"    pathlib / 遇盘符 = {reset_pl}  (pathlib 同样重置，但语义更显式)")


# ============================================================================
# 语法解析 3-4：编码三要素与控制台编码
# ============================================================================
# 【语法规则】
#   源文件编码：由 PEP 3120 规定，无 BOM 的 .py 默认就是 UTF-8，无需声明
#   声明编码：文件首行 # -*- coding: utf-8 -*- 是历史惯例，现已多余但无害
#   I/O 编码：open() 不给 encoding 时默认用 locale.getpreferredencoding()，随平台变化
#   sys.stdout.encoding：控制台输出编码；被重定向到管道/文件时可能变成 UTF-8
#   Python 3.15 起将统一使用 UTF-8 作为默认 I/O 编码（PEP 686），此坑将自动消失
# 【设计意图】
#   Python 2 时代编码是一大噩梦（str/unicode 之分 + 默认 ASCII）。
#   Python 3 统一为 str 内部用 Unicode 表示，并规定源码默认 UTF-8。
#   但 I/O 层的"默认跟随系统 locale"是为了兼容 C 传统，
#   代价就是跨机器行为可能不一致 —— 所以工程规范要求永远显式写 encoding。


def demo_encoding_basics():
    print("[3] 源码与解释器编码")
    # PEP 3120：无论文件首行写了什么，Python 3 的 str 就是 Unicode 字符串
    print(f"    str 的长度语义  = 按 Unicode 码点计，不是字节数")
    print(f"    '中' 的长度      = {len('中')}")
    print(f"    '中' 的 UTF-8 字节 = {len('中'.encode('utf-8'))}")

    print("[4] 控制台与 I/O 默认编码")
    print(f"    locale 首选编码  = {sys.getdefaultencoding()} / {sys.getfilesystemencoding()}")
    print(f"    sys.stdout.encoding = {sys.stdout.encoding}")
    print(f"    sys.stderr.encoding = {sys.stderr.encoding}")

    # Windows 控制台在 PEP 528 之后（Python 3.6+）使用 UTF-8，
    # 但当 stdout 被重定向到文件或管道时，仍可能回退到系统 ANSI 代码页。
    # 这解释了"终端里好好的，日志文件里中文变问号"的现象。
    if sys.stdout.encoding and sys.stdout.encoding.lower().replace("-", "") in ("utf8", "cp65001"):
        print("    结论：当前控制台支持 UTF-8，中文与常用符号均可安全输出")
    else:
        print(f"    警告：当前输出编码为 {sys.stdout.encoding}，中文可能显示为问号")


# ============================================================================
# 语法解析 5：UTF-8 文件读写 + 临时目录 + 上下文管理器
# ============================================================================
# 【语法规则】
#   with tempfile.TemporaryDirectory() as tmpdir:
#       ...
#   with open(path, "w", encoding="utf-8", newline="") as f:
#       f.write(text)
# 【执行顺序】
#   1) __enter__ 被调用，返回对象绑定到 as 后的名字
#   2) with 块内的代码执行
#   3) 无论块内是否抛异常，__exit__ 都会被调用，异常会原样向上传播
#   5) 异常被抑制的行为由 __exit__ 返回值决定（True 则吞掉异常）
# 【设计意图】
#   with 语句替代了 try/finally 的样板代码，并保证资源一定释放。
#   CPython 的引用计数让"不用 with 也可能不泄漏"，但这不可靠：
#   解释器崩溃、PyPy 实现、循环引用都会让 __del__ 延迟甚至不执行。
#   所以规范是：任何打开的资源都用 with。


def demo_utf8_file_roundtrip():
    print("[5] UTF-8 文件读写往返")

    # 选系统临时目录而不是当前目录：避免污染用户的项目文件夹
    with tempfile.TemporaryDirectory(prefix="pycore_enc_") as tmpdir:
        base = Path(tmpdir)
        target = base / "中文文件名.txt"

        content = "第一行：中文内容\n第二行：English mixed\n第三行：数字 12345\n"

        # encoding="utf-8" 是必须的：否则在中文 Windows 上默认 GBK，
        # 写入 emoji 等 GBK 无法表示的字符会抛 UnicodeEncodeError
        # newline="" 表示"不做任何换行符转换"，原样写入 \n；
        # 默认（文本模式）会把 \n 转成 os.linesep，在 Windows 上变成 \r\n
        with open(target, "w", encoding="utf-8", newline="") as f:
            f.write(content)
        print(f"    已写入         = {target.name}")
        print(f"    文件存在       = {target.exists()}, 大小 = {target.stat().st_size} 字节")

        # 用 Path.read_text 读回 —— 它是 open(...).read() 的封装，默认就是 UTF-8
        read_back = target.read_text(encoding="utf-8")
        print(f"    内容一致       = {read_back == content}")

        # 用二进制模式读，看真实的字节分布：证明 UTF-8 里中文占 3 字节
        raw_bytes = target.read_bytes()
        # 找第一个中文字符的字节起点，验证 3 字节编码
        first_line_bytes = raw_bytes.split(b"\n")[0]
        print(f"    首行原始字节   = {first_line_bytes}")
        # 字节数 = 6 个中文/全角字符 x 3 字节 + 1 个 ASCII 冒号 = 19，实测 24 提示还有全角字符
        print(f"    首行字节数     = {len(first_line_bytes)}  (中文/全角各 3 字节，ASCII 各 1 字节)")

        # bytes 没有 decode 就只是数字序列，decode 才是变回 str
        decoded = raw_bytes.decode("utf-8")
        print(f"    decode 后一致  = {decoded == content}")

        # 列出目录内容，证明临时目录机制生效
        print(f"    目录内文件     = {[p.name for p in base.iterdir()]}")
        print("    -> with 块结束，TemporaryDirectory 自动递归删除，无需手写 shutil.rmtree")


# ============================================================================
# 语法解析 6：编解码容错策略 errors=
# ============================================================================
# 【语法规则】
#   str.encode(encoding, errors='strict'|'ignore'|'replace')
#   bytes.decode(encoding, errors=...)
#   strict   —— 遇到无法表示的字符立即抛异常（默认，安全）
#   ignore   —— 静默丢弃无法表示的字符（数据丢失但程序不崩）
#   replace  —— 用替换符 U+FFFD 替代（可发现数据损坏）
#   errors='backslashreplace' —— 转义形式 '\xXX'（写 HTML/日志时有用）
# 【设计意图】
#   编解码失败是"数据边界"问题而非"逻辑错误"。
#   Python 强制调用者显式面对它，默认 strict 宁可崩溃也不静默产出乱码，
#   这是一种"fail fast"哲学：错误的数据比没有数据更危险。


def demo_codec_errors():
    print("[6] 编解码容错策略")

    text = "价格 100 元"  # 挑 GBK 无法表示的部分做演示
    # emoji 是测试编解码容错的最佳素材：几乎所有非 UTF-8 传统编码都无法表示它
    tricky = "价格 100 元 😀"

    for enc in ("utf-8", "gbk"):
        try:
            data = tricky.encode(enc)
            print(f"    {enc:<8} 编码成功，{len(data)} 字节: {data}")
        except UnicodeEncodeError as e:
            # UnicodeEncodeError 的属性：encoding / object / start / end / reason
            # reason 是可读的失败原因，这是内置异常比裸 ValueError 强的地方
            print(f"    {enc:<8} 编码失败: {e.reason} (位置 {e.start}-{e.end})")

    # 三种容错策略对比
    for policy in ("strict", "ignore", "replace"):
        try:
            result = tricky.encode("gbk", errors=policy)
            print(f"    gbk+{policy:<8} -> {result}")
        except UnicodeEncodeError:
            print(f"    gbk+{policy:<8} -> 抛异常")

    # backslashreplace 不丢信息，把不可表示字符写成可见的转义串
    escaped = tricky.encode("gbk", errors="backslashreplace")
    print(f"    gbk+backslashreplace -> {escaped}  (信息无损，反向可还原)")

    # 常见陷阱：GBK 编出来的字节用 UTF-8 解，必然乱码
    try:
        wrong = "中文".encode("gbk").decode("utf-8")
        print(f"    错配解码 -> {wrong}")
    except UnicodeDecodeError as e:
        print(f"    错配解码 -> 失败: {e.reason}（这正是日志文件乱码的根因）")


# ============================================================================
# 语法解析 7：换行符 —— 文本模式 vs 二进制模式
# ============================================================================
# 【语法规则】
#   open(path, "r")            文本模式，开启 universal newlines：\r\n 和 \r 都读成 \n
#   open(path, "r", newline="")  文本模式但关闭转换：原样返回 \r\n
#   open(path, "rb")           二进制模式：无任何转换，返回 bytes
# 【执行顺序】
#   文本模式底层先按二进制读字节，再经过 io.TextIOWrapper 按 encoding 解码、
#   按 newline 规则转换换行符，最后交给 str。
# 【设计意图】
#   Universal newlines 是跨平台文本处理的必需品：
#   Windows 写出的 \r\n 在 Unix 工具（如 wc -l、grep）里会被当成一个字符，行为不一致。
#   Python 选择在文本层默认归一化，让业务代码只需处理一种换行形式。


def demo_newline_modes():
    print("[7] 换行符：文本模式 vs 二进制模式")

    with tempfile.TemporaryDirectory(prefix="pycore_nl_") as tmpdir:
        p = Path(tmpdir) / "crlf.txt"
        # 二进制写入 \r\n，模拟 Windows 记事本生成的文件
        p.write_bytes(b"line1\r\nline2\r\nline3\n")

        # 默认文本模式：\r\n 被归一化为 \n
        text_default = p.read_text(encoding="utf-8")
        print(f"    默认文本模式 repr = {text_default!r}")
        print(f"    splitlines 后行数  = {len(text_default.splitlines())}")

        # newline="" 保留原始换行符
        text_raw = p.read_text(encoding="utf-8", newline="")
        print(f"    newline='' repr    = {text_raw!r}")

        # 二进制模式：完全不做处理
        raw = p.read_bytes()
        print(f"    二进制模式       = {raw!r}")
        print(f"    二进制里 \\r\\n 的个数 = {raw.count(b'\r\n')}")

        # splitlines() 本身就很智能：能识别 \r\n / \n / \r / \v / \f / \x1c 等多种行界，
        # 且不返回末尾空元素 —— 比 str.split('\n') 实用得多
        print(f"    split('\\n') 结果  = {raw.decode('utf-8').split(chr(10))}  (末尾多出空串)")


# ============================================================================
# 语法解析 8：sys.stdout 重定向
# ============================================================================
# 【语法规则】
#   buf = io.StringIO()             内存文本缓冲区，可当作文件对象用
#   old = sys.stdout                 保存原对象引用（它本身是文件对象）
#   sys.stdout = buf                 替换模块属性，全局生效
#   ...                              所有 print 都写进 buf
#   sys.stdout = old                 还原
#   sys.stdout.reconfigure(...)     Python 3.7+：原地修改编码/换行，避免换对象
# 【执行顺序】
#   print() 内部执行 file=None 时的分支：sys.stdout.write(...)
#   因此只要改变 sys.stdout 这个名字的绑定，所有 print 的去向立刻改变 —— 无需改 print 代码。
# 【设计意图】
#   Python 选择让 print 依赖 sys.stdout 这个可变的模块级名字（而非保存引用），
#   这正是它能被 unittest、click、rich 等库"劫持输出"实现彩色/捕获的原因。
#   trade-off 是：全局可变状态，不适合多线程并发改写。


def demo_stdout_redirect():
    print("[8] 输出重定向与恢复")

    # StringIO 是纯内存对象，写入不落盘，速度快，测试中常用
    buf = io.StringIO()

    # 保存引用而非路径：sys.stdout 已经是对象了，直接存对象即可
    original = sys.stdout
    # 判断原对象是否支持 reconfigure（真实控制台/文件支持，StringIO 不支持）
    can_reconfigure = hasattr(original, "reconfigure")
    print(f"    原 stdout 可 reconfigure = {can_reconfigure}")

    try:
        # 替换模块属性 —— 这一行让后续所有 print 被劫持
        sys.stdout = buf
        print("这句不会显示在终端")
        print("它被写进了内存缓冲区")
        # 即使在被劫持期间，输出仍是带换行的字符串
        print(f"当前缓冲区内容长度 = {len(buf.getvalue())}")
    finally:
        # 用 finally 保证即使块内出错也能还原，
        # 否则后续所有输出都会消失，是极难排查的错误
        sys.stdout = original

    # 还原后取回被捕获的内容
    captured = buf.getvalue()
    print(f"    捕获到的输出 = {captured!r}")
    print(f"    终端已恢复 = {sys.stdout is original}")

    # reconfigure 的正确用途：把控制台编码改成 UTF-8，解决 emoji 崩溃
    # 它修改的是原对象内部状态，不改变 sys.stdout 的身份，比 sys.stdout = 新对象更安全
    if can_reconfigure:
        try:
            # show_default=False 表示不把默认编码写到 stdout 上，避免显示乱码
            original.reconfigure(encoding="utf-8")
            print("    reconfigure(utf-8) 成功，当前输出编码 =", sys.stdout.encoding)
        except (ValueError, OSError) as e:
            # 极端环境（输出被重定向到不支持的对象）会失败，捕获后不影响主流程
            print(f"    reconfigure 失败（不影响使用）: {type(e).__name__}")


def main():
    # 顺序即讲解顺序
    demo_pathlib()
    demo_windows_pitfalls()
    demo_encoding_basics()
    demo_utf8_file_roundtrip()
    demo_codec_errors()
    demo_newline_modes()
    demo_stdout_redirect()
    print("[完成] 01_env/02_path_and_encoding.py 运行结束")


if __name__ == "__main__":
    main()