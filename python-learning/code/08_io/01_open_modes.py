#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
open() 的全部模式演示
================================================

【演示的语法点】
1. open(file, mode, buffering, encoding, errors, newline) 的完整签名
2. 模式字符全解：r / w / a / x / + / b / t 的组合与语义
3. 模式对照表：是否存在、是否截断、光标初始位置
4. buffering 参数：0 / 1 / 2（缓冲行数）、负数含义、只对二进制有效
5. encoding 必须指定的真实原因：跨平台默认编码不同 -> 真实演示乱码
6. errors 参数：strict / ignore / replace / xmlcharrefreplace / namereplace
7. newline 参数对换行符的影响（后续03_csv 会重点展开）
8. 文件指针操作：tell / seek / flush / truncate
9. 忘记 close 的后果：Windows 上无法删除文件（真实演示）
10. open() 返回的 TextIOWrapper / BufferedReader 类型

【预期输出摘要】
- 模式对照表（4 列）
- 各种模式的读写结果对比
- 三种编码（utf-8 / gbk / latin-1）读取同一文件的结果对比（真实乱码）
- 指针操作前后的位置输出
- 忘记 close 导致的 FileNotFoundError（Windows 特性，真实触发）
"""

import io
import locale
import os
import sys
import tempfile
from pathlib import Path


# 工作目录：所有临时文件都放在脚本同级，避免污染其他目录
WORK_DIR = Path(__file__).parent / "_tmp_open_modes"
WORK_DIR.mkdir(exist_ok=True)


def show_bytes(path):
    """读取文件的原始字节，用十六进制+ASCII 展示。"""
    data = path.read_bytes()
    # 每 3 字节分组，中文 utf-8 编码后是 3 字节
    return data[:30]


def demo_1_mode_table():
    """open 模式的完整对照表。"""
    print("=" * 74)
    print("【1】open 模式字符全解")
    print("=" * 74)

    # ===== 语法解析 =====
    # open(file, mode='r', buffering=-1, encoding=None, errors=None,
    #      newline=None, closefd=True, opener=None)
    #
    # mode 由两「类字符」与一个「修饰符」组合而成：
    #   类别（必须选一个，决定基本行为）：
    #     r  read  只读（默认）
    #     w  write 只写，文件存在则【清空】，不存在则创建
    #     a  append 只写，文件存在则【追加到末尾】，不存在则创建
    #     x  exclusive 新建，文件【已存在则报错 FileExistsError】
    #     +  是修饰符，可加在任何类别后：r+ / w+ / a+ / x+
    #        表示「读写都允许」。但 w+ 会先清空文件，x+ 要求文件不存在。
    #
    # 修饰符（可选）：
    #     b  binary二进制模式，返回 bytes，不做换行转换与解码
    #     t  text     文本模式（默认），返回 str，做解码与换行转换
    #
    # 设计意图：w 的「截断」和 a 的「追加」区分开，是为了让「重建文件」
    # 和「往文件里追加」这两种意图在语法上不可能混淆。

    table = [
        ("模式", "读", "写", "文件存在时", "文件不存在时"),
        ("r", "√", "×", "从头读", "FileNotFoundError"),
        ("r+", "√", "√", "从头读/写，不截断", "FileNotFoundError"),
        ("w", "×", "√", "清空后写", "创建"),
        ("w+", "√", "√", "清空后读写", "创建"),
        ("a", "×", "√", "末尾追加", "创建"),
        ("a+", "√", "√", "末尾追加/可读", "创建"),
        ("x", "×", "√", "FileExistsError", "创建"),
        ("x+", "√", "√", "FileExistsError", "创建"),
        ("b", "-", "-", "二进制无换行转换", "-"),
        ("rb", "√", "×", "读 bytes", "-"),
        ("wb", "×", "√", "写 bytes", "-"),
    ]
    widths = [8, 5, 5, 26, 22]
    for i, row in enumerate(table):
        print("".join(c.ljust(w) for c, w in zip(row, widths)))
        if i == 0:
            print("-" * 66)

    print()
    print("【口诀】")
    print("   r 读 / w 写(清空) / a 追加 / x 独占新建")
    print("   + 读写都行    b 二进制    t 文本(默认)")
    print("   组合示例：'r+b' = 读写二进制；'w+t' = 读写文本(与 'w+' 等价)")
    print()


def demo_2_modes_in_action():
    """实际用各种模式读写，观察差异。"""
    print("=" * 74)
    print("【2】各模式的实际行为")
    print("=" * 74)

    # ===== 语法解析 =====
    # w 模式：截断。如果文件原有内容，会被完全清空。
    f1 = WORK_DIR / "mode_w.txt"
    f1.write_text("原始内容", encoding="utf-8")
    print(f"① w 模式截断：")
    print(f"   写入前大小 = {f1.stat().st_size} 字节")
    with open(f1, "w", encoding="utf-8") as f:
        f.write("新内容")
    print(f"   写入后大小 = {f1.stat().st_size} 字节"
          f"  -> 原内容被清空")
    print()

    # a 模式：追加，不清空
    print("② a 模式追加：")
    with open(f1, "a", encoding="utf-8") as f:
        f.write("|追加的内容")
    print(f"   大小 = {f1.stat().st_size} 字节，内容 = {f1.read_text(encoding='utf-8')!r}")
    print()

    # x 模式：独占创建，文件已存在则报错
    print("③ x 模式独占创建：")
    try:
        with open(f1, "x", encoding="utf-8") as f:
            f.write("不可能执行到这里")
    except FileExistsError as e:
        print(f"   FileExistsError: {e.filename}已存在")
    # 用一个不存在的路径，x 就能成功
    f_new = WORK_DIR / "mode_x_new.txt"
    with open(f_new, "x", encoding="utf-8") as f:
        f.write("x 模式创建的全新文件")
    print(f"   新路径创建成功，内容 = {f_new.read_text(encoding='utf-8')!r}")
    print()

    # r+ 模式：可读写，但不截断，光标在开头
    print("④ r+ 模式（读写，不截断）：")
    # 注意：这里用纯 ASCII 内容演示。若用中文，会出现「按字节覆盖」
    # 导致半个字符被替换、剩余字节变成乱码的现象。
    f_ascii = WORK_DIR / "mode_rplus_ascii.txt"
    f_ascii.write_text("ABCDEF", encoding="utf-8")
    with open(f_ascii, "r+", encoding="utf-8") as f:
        content = f.read()
        print(f"   先读取全部: {content!r}")
        # seek(0) 回到开头，才能覆盖写入
        # 若不 seek，写入会从文件末尾开始（原因为「写入总是发生在当前指针处」）
        f.seek(0)
        f.write("XY")
    print(f"   退出 with 后文件内容: {f_ascii.read_text(encoding='utf-8')!r}")
    print("   -> 前两个字符被替换，其余部分保留")
    print()

    print("④b 按字节覆盖中文会产生乱码（r+ 模式的风险）：")
    f_cn = WORK_DIR / "mode_rplus_cn.txt"
    f_cn.write_text("新内容", encoding="utf-8")
    with open(f_cn, "r+", encoding="utf-8") as f:
        f.seek(0)
        f.write("XY")     # 只写了 2 字节，但「新」在 utf-8 下是 3 字节
    raw = f_cn.read_bytes()
    print(f"   写入后字节: {raw}")
    try:
        print(f"   按 utf-8 读取: {f_cn.read_text(encoding='utf-8')!r}")
    except UnicodeDecodeError as e:
        print(f"   按 utf-8 读取失败: UnicodeDecodeError: {e}")
        print("      -> 文本模式按字节覆盖，会切碎多字节字符，务必确保写入长度对齐")
    print()

    # w+ 模式：先清空，再读写
    print("⑤ w+ 模式（先截断再读写）：")
    f2 = WORK_DIR / "mode_wplus.txt"
    f2.write_text("这段内容会被清空", encoding="utf-8")
    with open(f2, "w+", encoding="utf-8") as f:
        f.write("全新内容")
        f.seek(0)          # 必须 seek 才能读到刚写的
        print(f"   写入后读回: {f.read()!r}")
    print()

    # a+ 模式：追加 + 可读，但读不到内容（因为指针在末尾）
    print("⑥ a+ 模式（追加+可读，指针在末尾）：")
    f3 = WORK_DIR / "mode_aplus.txt"
    f3.write_text("行1\n行2\n", encoding="utf-8")
    with open(f3, "a+", encoding="utf-8") as f:
        print(f"   打开后立即读: {f.read()!r}  -> 空！指针在末尾")
        f.write("行3\n")
        f.seek(0)          # seek 才能从头读
        print(f"   seek(0) 后读: {f.read()!r}")
    print("【要点】a/a+ 的初始指针永远在末尾，要读已有内容必须先 seek。")


def demo_3_binary_vs_text():
    """二进制模式与文本模式的核心差异。"""
    print("=" * 74)
    print("【3】二进制 vs 文本：换行转换与类型")
    print("=" * 74)

    # ===== 语法解析 =====
    # 文本模式（t，默认）：
    #   - 写入 str，底层按 encoding 编码成 bytes
    #   - 写入时把 '\n' 转成系统的换行符（Windows: '\r\n'，Linux: '\n'）
    #   - 读取时做反向转换，'\r\n' 统一还原成 '\n'
    #
    # 二进制模式（b）：
    #   - 读写 bytes，完全不做任何转换
    #   - 你看到什么字节就是什么字节
    #
    # 关键差异演示：同一个 '\n' 在两种模式下的磁盘表示不同。
    text_file = WORK_DIR / "newline_text.txt"
    bin_file = WORK_DIR / "newline_bin.txt"

    with open(text_file, "w", encoding="utf-8") as f:
        f.write("第一行\n第二行\n")
    with open(bin_file, "wb") as f:
        f.write("第一行\n第二行\n".encode("utf-8"))

    print("① 写入相同内容，磁盘上的字节：")
    text_bytes = text_file.read_bytes()
    bin_bytes = bin_file.read_bytes()
    print(f"   文本模式写入: {text_bytes}")
    print(f"   二进制模式写入: {bin_bytes}")
    if os.name == "nt":
        print(f"   -> Windows: 文本模式把 \\n 转成 \\r\\n，所以多了字节 {len(text_bytes) - len(bin_bytes)}")
    else:
        print("   -> Linux: 两者字节相同（换行符本身就是 \\n）")
    print()

    print("② 读取时类型不同：")
    with open(text_file, "r", encoding="utf-8") as f:
        t = f.read()
    with open(bin_file, "rb") as f:
        b = f.read()
    print(f"   文本模式读到: {type(t).__name__} -> {t!r}")
    print(f"   二进制模式读到: {type(b).__name__} -> {b}")
    print()

    print("③ 二进制模式不能指定 encoding（会报错）：")
    try:
        with open(bin_file, "rb", encoding="utf-8") as f:
            f.read()
    except ValueError as e:
        print(f"   ValueError: {e}")
    print()

    print("④ 文本模式的换行符统一化：")
    # 手动构造一个 CRLF 文件
    crlf_file = WORK_DIR / "crlf.txt"
    crlf_file.write_bytes(b"a\r\nb\r\nc")
    with open(crlf_file, "r", encoding="utf-8") as f:
        content = f.read()
    print(f"   文本模式读取 CRLF 文件 -> {content!r}")
    print(f"   -> 统一变成 \\n（universal newlines）")
    with open(crlf_file, "rb") as f:
        print(f"   二进制模式读取同一文件 -> {f.read()!r}（保留 \\r\\n）")
    print()
    print("【要点】文本模式做「换行符翻译」，二进制模式什么都不做。")
    print("       处理行式数据时，二进制模式更精确；日常读写用文本模式更方便。")


def demo_4_encoding_matters():
    """为什么必须指定 encoding：真实演示乱码。"""
    print("=" * 74)
    print("【4】encoding 必须指定的原因（真实演示乱码）")
    print("=" * 74)

    # ===== 语法解析 =====
    # open() 的 encoding 参数默认是 None，含义是「用 locale.getpreferredencoding(False)」
    # 这个值在不同平台/环境下不同：
    #   Windows 简体中文环境: cp936 (GBK)
    #   Windows 英文环境:    cp1252
    #   Linux 多数环境:      UTF-8
    #   macOS:               UTF-8
    # 这就是「同一份代码，在开发机正常、在服务器上乱码」的根源。
    print(f"① 当前环境信息：")
    print(f"   locale.getpreferredencoding() = {locale.getpreferredencoding()}")
    print(f"   sys.getdefaultencoding()    = {sys.getdefaultencoding()}")
    print(f"   sys.getfilesystemencoding() = {sys.getfilesystemencoding()}")
    print("   -> 不同平台这个值不同，所以必须显式指定 encoding='utf-8'")
    print()

    # 造一个 GBK 编码的文件
    gbk_file = WORK_DIR / "chinese_gbk.txt"
    chinese = "中文编码测试：张伟在技术部\n"
    # 用 gbk 编码写入字节
    gbk_file.write_bytes(chinese.encode("gbk"))
    # 用 utf-8 编码写入同一个内容
    utf8_file = WORK_DIR / "chinese_utf8.txt"
    utf8_file.write_bytes(chinese.encode("utf-8"))

    print("② 用 utf-8 读（正确）：")
    with open(utf8_file, "r", encoding="utf-8") as f:
        print(f"   {f.read()!r}")
    print()

    print("③ 用 gbk 读 utf-8 文件（乱码！）：")
    # 用 errors="replace" 保证能读出来（不指定时会抛 UnicodeDecodeError，
    # 因为 GBK 的双字节序列与 utf-8 的字节并不兼容）
    with open(utf8_file, "r", encoding="gbk", errors="replace") as f:
        result = f.read()
    print(f"   {result!r}")
    print(f"   -> 出现替换字符 U+FFFD，说明字节序列被误解了")
    print()

    print("④ 不指定 errors 时直接报错：")
    try:
        with open(utf8_file, "r", encoding="gbk") as f:
            f.read()
    except UnicodeDecodeError as e:
        print(f"   UnicodeDecodeError: {e}")
    print()

    print("⑤ 实际输出乱码的样子：")
    print(f"   {result}")
    print()

    print("⑥ 用 latin-1 读（永不报错，但全是乱码 —— 最危险的情况）：")
    # latin-1 能映射 0-255 全部字节，所以永远不会解码失败
    with open(utf8_file, "r", encoding="latin-1") as f:
        latin_result = f.read()
    print(f"   {latin_result!r}")
    print(f"   {latin_result}")
    print("   -> 没有报错，但数据已经彻底损坏，且下游程序无法察觉")
    print()

    print("⑦ 「正确」的检查方式：json.dumps 看真实码点：")
    import json
    print(f"   utf-8 正确读取: {json.dumps(chinese)}")
    print(f"   gbk 错误读取  : {json.dumps(result)}")
    print("   -> \\uXXXX 才是真实码点，肉眼看到的字形可能骗人")
    print()
    print("【要点】读写文本文件一律显式写 encoding='utf-8'，这是铁律。")
    print("       latin-1 永不报错这一点让它成为最隐蔽的乱码来源。")
    print()


def demo_5_errors_parameter():
    """errors 参数：解码出错时的行为策略。"""
    print("=" * 74)
    print("【5】errors 参数：解码失败的五种策略")
    print("=" * 74)

    # ===== 语法解析 =====
    # errors 参数只在**解码时字节序列非法**才起作用，取值：
    #   strict         严格（默认），立即抛 UnicodeDecodeError
    #   ignore         丢弃非法字节
    #   replace        用 U+FFFD（�）替换非法字节
    #   xmlcharrefreplace  用 &#xxx; XML 字符引用替换
    #   namereplace    只在解码时非法才用 \N{...} 替换
    #   surrogateescape / surrogatepass  用于处理代理项（处理损坏数据常用）
    #
    # 注意：errors 只影响「解码」，不影响「编码」。编码方向没有可配置的错误策略。

    bad_file = WORK_DIR / "broken_bytes.txt"
    # 构造一个含非法 utf-8 字节的文件：b'abc\xff\xfe def'
    bad_file.write_bytes(b"Hello \xff\xfe World \x80 End")

    print("① 构造的文件原始字节:")
    print(f"   {bad_file.read_bytes()!r}")
    print("   (\\xff\\xfe\\x80 不是合法的 UTF-8 序列)")
    print()

    strategies = ["strict", "ignore", "replace", "backslashreplace",
               "surrogateescape"]
    for strategy in strategies:
        try:
            with open(bad_file, "r", encoding="utf-8", errors=strategy) as f:
                result = f.read()
            print(f"② errors={strategy:<20} -> {result!r}")
        except UnicodeDecodeError as e:
            print(f"② errors={strategy:<20} -> UnicodeDecodeError: {e}")
    print()

    print("③ 各策略的取舍：")
    table = [
        ("策略", "输出", "适用场景"),
        ("strict", "抛异常", "必须保证数据干净，不容妥协"),
        ("ignore", "丢掉坏字节", "可容忍少量丢失，需统计丢弃量"),
        ("replace", "插入 �", "展示/预览场景，人眼可辨识"),
        ("backslashreplace", "\\xff 转义", "调试/日志排查，要还原字节"),
        ("surrogateescape", "\\udcff 等", "无损往返，配合写回修复数据"),
    ]
    widths = [22, 16, 40]
    for i, row in enumerate(table):
        print("".join(c.ljust(w) for c, w in zip(row, widths)))
        if i == 0:
            print("-" * 76)
    print()

    print("④ 重要事实：xmlcharrefreplace 只对「编码」有效，对「解码」无效：")
    try:
        with open(bad_file, "r", encoding="utf-8",
                  errors="xmlcharrefreplace") as f:
            f.read()
    except TypeError as e:
        print(f"   解码时使用它 -> TypeError: {e}")
    print("   同理 namereplace 也只适用于编码方向。")
    print()

    print("⑤ surrogateescape 实现「无损往返」（修复损坏数据的标准手法）：")
    # 读时用 surrogateescape，把非法字节存成代理项（U+DC80~U+DCFF）
    with open(bad_file, "r", encoding="utf-8", errors="surrogateescape") as f:
        roundtrip = f.read()
    print(f"   读到的字符串: {roundtrip!r}")
    print(f"   含代理项: {any('\\udc' in repr(ch) or ch == '�' for ch in roundtrip)}")
    # 写回时用同一个策略，原始字节会被还原
    restored = WORK_DIR / "restored.bin"
    with open(restored, "w", encoding="utf-8", errors="surrogateescape") as f:
        f.write(roundtrip)
    print(f"   写回后字节 == 原始字节: {restored.read_bytes() == bad_file.read_bytes()}")
    print()
    print("【要点】生产环境读外部数据，errors='replace' + 统计替换数量是常见做法。")
    print("       写文件时没有 errors 参数，编码失败必然抛异常。")


def demo_6_buffering():
    """buffering 参数详解。"""
    print("=" * 74)
    print("【6】buffering 参数：什么时候数据真正落盘")
    print("=" * 74)

    # ===== 语法解析 =====
    # buffering 控制「用户态缓冲区」的大小，决定「写」操作何时真正进入内核。
    # 取值：
    #   0   无缓冲（只允许二进制模式）。write 后立刻进内核。
    #        文本模式下传 0 会抛 ValueError。
    #   1   行缓冲（文本模式默认）。遇到 '\n' 就 flush。
    #        二进制模式下传 1 等同于默认缓冲区大小。
    #   n>1 指定缓冲区大小（字节）。n 为 0 之外的最小正整数都合法。
    #   -1  默认大小（文本模式 8192 字节 / 二进制模式 io.DEFAULT_BUFFER_SIZE）
    #        这也是默认值。
    #
    # 【关键理解】buffering 只对「写」有意义，「读」总是从缓冲区拿数据。
    # flush() 手动强制刷新缓冲区；close() 会自动 flush。

    print("① buffering=0（无缓冲，二进制专用）：")
    unbuffered = WORK_DIR / "unbuffered.bin"
    with open(unbuffered, "wb", buffering=0) as f:
        # buffering=0 时，f.write 是 RawIOBase.write，直接写进内核
        n = f.write(b"immediate write")
        print(f"   写入 {n} 字节（此时已落盘，文件大小 = "
              f"{unbuffered.stat().st_size}）")
    print("   -> 无缓冲的代价：每次 write 都有系统调用开销，慢")
    print()

    print("② buffering=1（行缓冲，文本模式默认）：")
    line_buf = WORK_DIR / "line_buffered.txt"
    with open(line_buf, "w", encoding="utf-8", buffering=1) as f:
        f.write("第一行\n")
        # 行缓冲：遇到 \n 立即 flush，文件里应该已经有内容了
        size_after_line = line_buf.stat().st_size
        print(f"   写入含 \\n 的一行后，文件大小 = {size_after_line}（已落盘）")
        f.write("没有换行的内容")
        size_no_nl = line_buf.stat().st_size
        print(f"   写入无\\n 的内容后，文件大小 = {size_no_nl}（仍在缓冲区）")
    print(f"   退出 with 后，文件大小 = {line_buf.stat().st_size}（close 自动 flush）")
    print()

    print("③ 文本模式传 buffering=0 会报错：")
    try:
        with open(WORK_DIR / "err.txt", "w", encoding="utf-8", buffering=0) as f:
            f.write("x")
    except ValueError as e:
        print(f"   ValueError: {e}")
    print()

    print("④ buffering=1024（指定 1KB 缓冲区）：")
    big_buf = WORK_DIR / "big_buffer.txt"
    with open(big_buf, "w", encoding="utf-8", buffering=1024) as f:
        f.write("x" * 500)     # 小于 1024，还在缓冲区
        print(f"   写 500 字节后，文件大小 = {big_buf.stat().st_size}（未满缓冲）")
        f.write("y" * 600)     # 累计超过 1024，触发 flush
        print(f"   再写 600 字节后，文件大小 = {big_buf.stat().st_size}（已 flush）")
    print()

    print("⑤ 手动 flush 与 tell/seek：")
    pointer_file = WORK_DIR / "pointer.txt"
    with open(pointer_file, "w+", encoding="utf-8") as f:
        f.write("Hello")
        f.flush()              # 强制刷入内核，文件立即可被其他进程看到
        print(f"   flush() 后 tell() = {f.tell()}（字节位置，文本模式下也按字节算）")
        f.seek(0)
        print(f"   seek(0) 后读取 = {f.read()!r}")
        f.seek(2)
        print(f"   seek(2) 后读取 = {f.read()!r}（从第 2 字节 'l' 开始）")
        # truncate：截断文件到指定大小，必须在写模式下
        f.seek(0)
        f.truncate(3)
        print(f"   truncate(3) 后文件内容 = {pointer_file.read_text(encoding='utf-8')!r}")
    print()
    print("【要点】buffering 影响的是「写」的时机；文本模式指针位置按「字节」计。")
    print("       实时日志场景要主动 flush()，否则崩溃时缓冲区内容会丢失。")


def demo_7_forget_close():
    """忘记 close 的真实后果。"""
    print("=" * 74)
    print("【7】忘记 close() 的后果（真实演示）")
    print("=" * 74)

    # ===== 语法解析 =====
    # 文件对象实现了 __del__，CPython 靠「引用计数归零时自动调用 __del__」来回收。
    # 所以在 CPython 上，忘记 close 通常不会报错 —— 但仍有三个严重问题：
    #   1. 缓冲区里的数据可能还没 flush（尤其 buffering>1 且无换行时）
    #   2. Windows 上文件句柄不释放 -> 无法删除/移动该文件
    #   3. PyPy 等非 CPython 实现没有引用计数，__del__ 触发时机不确定
    #
    # 结论：永远用 with 语句（02_with_statement.py 会详细讲）。

    leak_file = WORK_DIR / "leak_demo.txt"

    print("① 忘记 close，数据留在缓冲区：")
    # 用 -O 模式跑时这个 assert 会被删掉，这里用 if 代替更稳妥
    if True:
        f = open(leak_file, "w", encoding="utf-8", buffering=4096)
        f.write("这段数据还在缓冲区")
        # 故意不 close
        print(f"   写入后（未close）文件大小 = {leak_file.stat().st_size}"
              f"  -> 缓冲区未刷盘！")
        # 这里手动 close 只是为了演示对比效果
        f.close()
    print(f"   close() 后文件大小 = {leak_file.stat().st_size}  -> 数据落盘")
    print()

    print("② Windows 上文件句柄未释放 -> 无法删除：")
    target = WORK_DIR / "locked.txt"
    # 在 with 内部文件是打开的（Windows 会锁住）
    with open(target, "w", encoding="utf-8") as f:
        f.write("内容")
        # 尝试删除（会失败，因为当前进程还持有句柄）
        try:
            os.remove(target)
            print("   删除成功（说明当前平台允许删除已打开文件）")
        except (PermissionError, OSError) as e:
            print(f"   删除失败: {type(e).__name__}（Windows 特性：文件被锁定）")
            print("      -> 这就是「编辑器提示文件被占用」的同一个原因")
    # 出了 with，句柄已释放
    if target.exists():
        target.unlink()
        print("   退出 with 后可以正常删除了")
    print()

    print("③ 手动 close 的正确姿势（不用 with 时）：")
    f = open(leak_file, "w", encoding="utf-8")
    try:
        f.write("内容")
    finally:
        # 即使中间抛异常，finally 也能保证关闭
        f.close()
    print("   try/finally + close 是没有 with 时的等价写法")
    print()
    print("【要点】with 语句会自动 close，即使块内抛异常也能保证执行。")
    print("       CPython 的引用计数只保证「最终」关闭，不保证「及时」关闭。")
    print()


def demo_8_file_types():
    """open() 返回的对象类型与常用属性。"""
    print("=" * 74)
    print("【8】文件对象的类型层级与属性")
    print("=" * 74)

    # ===== 语法解析 =====
    # open() 返回的对象类型取决于模式：
    #   文本模式 -> io.TextIOWrapper
    #     包装了一个 BufferedWriter/BufferedReader + TextIOWrapper 编码层
    #   二进制读 -> io.BufferedReader
    #   二进制写 -> io.BufferedWriter
    #   二进制追加 -> io.BufferedWriter（配合 'a'）
    #   追加+读  -> io.BufferedRandom
    #
    # 所有这些类都继承自 io.IOBase -> object，
    # 所以它们都实现了上下文管理器协议（__enter__/__exit__）。
    sample = WORK_DIR / "type_sample.txt"

    with open(sample, "w", encoding="utf-8") as f:
        print(f"① 文本写模式 -> {type(f).__name__}")
        print(f"   MRO: {' -> '.join(c.__name__ for c in type(f).__mro__[:5])}")
        print(f"   常用属性: name={f.name!r}")
        print(f"             mode={f.mode!r}")
        print(f"             encoding={f.encoding!r}")
        print(f"             errors={f.errors!r}")
        print(f"             line_buffering={f.line_buffering}")
        print(f"             closed={f.closed}")
        print(f"   可用方法: {[m for m in ('read','readline','readlines','write','writelines','seek','tell','flush','truncate','fileno','isatty','readable','writable','seekable') if hasattr(f, m)]}")

    with open(sample, "rb") as f:
        print(f"\n② 二进制读模式 -> {type(f).__name__}")
        print(f"   可用方法: {[m for m in ('read','readinto','read1','readline','write','peek','fileno') if hasattr(f, m)]}")

    with open(sample, "rb+") as f:
        print(f"\n③ 二进制读写模式 -> {type(f).__name__}（随机访问）")

    # 检查 isatty：判断是否是终端
    # 在重定向的脚本里通常是 False
    with open(sample, "r", encoding="utf-8") as f:
        print(f"\n④ isatty() = {f.isatty()}（False 表示不是交互终端）")
        print(f"   readable={f.readable()} writable={f.writable()} "
              f"seekable={f.seekable()}")

    # fileno：底层文件描述符
    with open(sample, "r", encoding="utf-8") as f:
        print(f"\n⑤ fileno() = {f.fileno()}（操作系统层面的文件描述符编号）")

    print(f"\n【层级结构】")
    print(f"   IOBase")
    print(f"    ├── TextIOWrapper  (文本模式，处理编码与换行)")
    print(f"    │└── BufferedXxx (缓冲区)")
    print(f"    │    └── FileIO   (真正的系统调用封装)")
    print(f"    └── BufferedXxx  (二进制模式)")


def cleanup():
    """清理临时文件。"""
    for f in WORK_DIR.iterdir():
        try:
            f.unlink()
        except OSError:
            pass
    try:
        WORK_DIR.rmdir()
    except OSError:
        pass


def main():
    """主入口。"""
    print("=" * 74)
    print("open() 全部模式演示")
    print("=" * 74)
    try:
        demo_1_mode_table()
        print()
        demo_2_modes_in_action()
        print()
        demo_3_binary_vs_text()
        print()
        demo_4_encoding_matters()
        print()
        demo_5_errors_parameter()
        print()
        demo_6_buffering()
        print()
        demo_7_forget_close()
        print()
        demo_8_file_types()
    finally:
        # 即使某段演示出错，也清理临时文件
        cleanup()
    print()
    print("=" * 74)
    print("演示结束：记住「永远用 with + 永远写 encoding='utf-8'」")
    print("=" * 74)


if __name__ == "__main__":
    main()