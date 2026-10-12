"""
================================================================================
 06_binary_and_large.py  ——  二进制读写与大文件流式处理
================================================================================

【重要安全声明】
  1. 本文件【不会执行任何不可信代码】。
     关于 pickle 反序列化攻击的部分，只做【原理说明与防御讲解】，
     不构造、不运行可执行的恶意 payload。
  2. 所有文件写入都在 tempfile 临时目录中，结束即清理。
  3. data/ 目录仅被只读访问。

【演示的语法点】
 1. 二进制基础：bytes / bytearray / memoryview 三者的区别与选用场景
 2. 二进制读写：open 的 'rb' 'wb' 'ab' 'r+b' 模式，'b' 的含义
 3. bytes 常用操作：切片、切片赋值限制、decode/encode、fromhex/hex
 4. ★ bytearray：可变字节序列的原地修改（bytes 不可变，这是最大区别）
 5. struct：二进制结构化打包与解包（网络协议、文件头、C 交互）
 6. struct 的对齐问题：'>' '<' '=' '!' 前缀与 size/alignment 影响
 7. array 模块：紧凑存储数值，比 list 省内存
 8. ★ pickle 的基本使用：dump / load / 协议版本 / 支持的类型
 9. ★★ pickle 安全风险：反序列化攻击原理（为什么 = 即可执行代码）
    与防御方案（HMAC 签名、JSON 替代、sandbox），只讲原理不执行攻击
10. 大文件流式处理：为什么 read() 会 OOM
11. ★ 分块读取标准写法：iter(lambda: f.read(n), b"") 与 readinto()
12. 分块读取统计词频：跨块边界的单词如何正确处理（核心技术点）
13. 行式流式处理：for line in f 的惰性机制与 tell/seek 的限制
14. 生成器 + 缓冲：把块处理封装成可复用管道
15. 内存对比实验：一次性读取 vs 分块读取的实际峰值差异

【预期输出摘要】
 - "bytes" 小节：bytes 不可变报错的实测异常，bytearray 可原地修改
 - "struct" 小节：同一组数据在小端/大端下的解包结果对比
 - "pickle" 小节：协议号与体积对比；风险小节展示 __reduce__ 的
   危险结构但【只打印说明文本，不执行】
 - "流式" 小节：10MB 文件一次性读入 vs 64KB 分块的内存峰值对比
 - "词频" 小节：跨块边界的单词（如被切成 "Py" + "thon"）能正确计数
================================================================================

"""

import array
import os
import pickle
import shutil
import struct
import sys
import tempfile
import tracemalloc
from collections import Counter
from pathlib import Path
from typing import Any, Dict, Iterator, List, Tuple

DATA_DIR = Path(__file__).parent / "data"


# ===== 语法解析 =====
# 【定义在模块顶层的类才能被 pickle】
#   pickle 记录的是"类所在的模块路径 + 类名"（如 __main__.Point），
#   反序列化时按这个路径去 import 并找到该类。
#   ⚠ 若类定义在函数内部（局部类），pickle.dump 时就会报错：
#      Can't get local object 'func.<locals>.Point'
#   因为函数返回后那个类就不存在了，任何地方都无法再 import 到它。
#   正确做法：所有需要被 pickle 的类都定义在模块顶层。
class Point:
    """简单的二维点，用于演示自定义类的序列化。"""

    def __init__(self, x: int, y: int) -> None:
        self.x = x
        self.y = y

    def __repr__(self) -> str:
        return f"Point({self.x}, {self.y})"


class Adder:
    """演示 __reduce__ 的类。

    __reduce__ 告诉 pickle「这个对象该如何被重建」。
    pickle 会把它返回的 (可调用对象, 构造参数) 编码成
    GLOBAL + REDUCE 操作码——这正是反序列化攻击利用的机制。
    """

    def __init__(self, a: int, b: int) -> None:
        self.a = a
        self.b = b

    def __reduce__(self) -> "tuple":
        # 返回 (可调用对象, 构造参数元组)
        # load 时会执行 Adder(*参数) 来重建对象
        return (self.__class__, (self.a, self.b))

    def __repr__(self) -> str:
        return f"Adder({self.a}+{self.b})"


# ===== 语法解析 =====
# 【1】bytes / bytearray / memoryview
#   bytes        不可变字节序列，底层是连续的 C 数组，支持哈希
#   bytearray    可变字节序列，是 bytes 的"可变版"，可原地修改
#   memoryview   零拷贝视图，直接引用底层内存，修改会同步影响原对象
#
#   选用规则（设计意图）：
#     只需读取、处理 → bytes（不可变更安全，能作为 dict 键/哈希）
#     需要频繁修改 → bytearray（避免反复拷贝）
#     需要把二进制数据交给 C 扩展/网络库零拷贝 → memoryview
#
#   ★ 为什么 str 和 bytes 必须区分：
#     str 是【Unicode 字符序列】，"一个字符"是一个码点（可能是多个字节）
#     bytes 是【字节序列】，长度永远是字节数
#     '中' 编码成 utf-8 是 3 个字节，len('中')=1 而 len(b'\xe4\xb8\xad')=3
def demo_bytes_basics() -> None:
    print("=" * 74)
    print("【1】bytes / bytearray / memoryview")
    print("=" * 74)

    # str 与 bytes 的本质区别
    text = "中文abc"
    raw = text.encode("utf-8")
    print(f"① str 与 bytes 的长度差异：")
    print(f"  str  : {text!r}  len={len(text)}  ← 按【字符】计数")
    print(f"  bytes: {raw!r}  len={len(raw)}  ← 按【字节】计数")
    print(f"  为什么：'中' 在 UTF-8 中占 3 字节 {raw[:3].hex()}")
    print(f"  bytes.decode('utf-8') → {raw.decode('utf-8')!r}  ← 还原成 str")
    print("  ★ 磁盘与网络传输用 bytes；程序内部文本处理用 str，边界处做编解码")

    # bytes 的创建方式
    print(f"\n② bytes 的多种创建方式：")
    print(f"  b'ABC'                  = {b'ABC'!r}")
    print(f"  bytes([65, 66, 67])     = {bytes([65, 66, 67])!r}   ← 列表转 bytes")
    print(f"  bytes('ABC', 'utf-8')   = {bytes('ABC', 'utf-8')!r}   ← str 转 bytes")
    print(f"  bytes(5)                = {bytes(5)!r}   ← 5 个零字节")
    print(f"  bytes.fromhex('48656c6c6f') = {bytes.fromhex('48656c6c6f')!r}   ← 十六进制")
    print(f"  b'Hello'.hex()          = {b'Hello'.hex()!r}   ← 转十六进制")

    # bytes 的常用操作
    print(f"\n③ bytes 的常用操作（{b'Hello, World'!r}）：")
    data = b"Hello, World"
    print(f"  data[0]        = {data[0]}   ← 整数（不是字符！）")
    print(f"  data[0:5]      = {data[0:5]!r}   ← 切片仍是 bytes")
    print(f"  len(data)      = {len(data)}")
    print(f"  b'World' in data → {b'World' in data}   ← 子串判断")
    print(f"  data.count(b'o')= {data.count(b'o')}")
    print(f"  data.split(b',')= {data.split(b',')!r}")
    print(f"  b'-'.join([b'a', b'b']) = {b'-'.join([b'a', b'b'])!r}")
    print(f"  data.upper()   = {data.upper()!r}")
    print(f"  ⚠ 注意 bytes 没有 decode 之外的字符方法（upper/lower 可用，"
          f"但没有 isdigit 等）")

    # ★ bytes 不可变：赋值会报错
    print(f"\n④ ★ bytes 是不可变的：")
    frozen = bytes(bytearray(b"immutable"))
    try:
        frozen[0] = ord("X")     # 对 bytes 赋值
    except TypeError as e:
        print(f"  frozen[0] = ord('X') → {type(e).__name__}: {e}")
    print("  这是 bytes 作为 dict 键能用的前提：不可变 → 可哈希")
    print(f"  验证可哈希: hash(b'abc') 有效 = {isinstance(hash(b'abc'), int)}")

    # ★ bytearray 可变
    print(f"\n⑤ ★ bytearray 是可变的：")
    ba = bytearray(b"modifiable")
    ba[0] = ord("M")             # 直接赋值，不需要重新生成对象
    ba.append(ord("!"))           # 可以 append
    ba.extend(b"XY")             # 可以 extend
    print(f"  修改后: {bytes(ba)!r}")
    print(f"  类型: {type(ba).__name__}，字节内容: {ba.hex()}")
    print(f"  ★ 用法：需要反复修改缓冲区时用 bytearray，避免反复创建新 bytes")

    # bytearray 切片赋值可改变长度
    print(f"\n⑥ bytearray 的切片赋值（可改变长度，bytes 不行）：")
    ba2 = bytearray(b"abcdef")
    ba2[1:3] = b"XYZ"             # 替换 2 个字节为 3 个 → 长度变了
    print(f"  ba2[1:3] = b'XYZ' → {bytes(ba2)!r}  （长度 {len(ba2)}）")
    print("  ★ 这个「长度可变」的特性和 bytes 的「长度固定」形成鲜明对比")

    # memoryview：零拷贝
    print(f"\n⑦ memoryview：零拷贝视图：")
    original = bytearray(b"0123456789")
    view = memoryview(original)
    print(f"  original = {bytes(original)!r}")
    view[0] = ord("X")            # 通过视图改，原对象同步变化
    print(f"  view[0] = ord('X') → original 变为 {bytes(original)!r}")
    print(f"  view 是原对象的视图: {view.obj is original}")
    print(f"  len(view) = {len(view)}，itemsize = {view.itemsize}")
    print("  ★ 用途：把大块二进制零拷贝交给 socket.send / hashlib.update，"
          "不产生中间副本")

    # bytes 与编码
    print(f"\n⑧ 编码错误处理：")
    invalid = b"\xff\xfe\x00invalid"
    try:
        invalid.decode("utf-8")
    except UnicodeDecodeError as e:
        print(f"  invalid.decode('utf-8') → {type(e).__name__}: {e}")
    # errors 参数控制容错策略
    print(f"  errors='ignore'    → {invalid.decode('utf-8', errors='ignore')!r}（丢弃）")
    print(f"  errors='replace'   → {invalid.decode('utf-8', errors='replace')!r}"
          f"（替换为 U+FFFD）")
    print("  ★ 处理外部数据时必须显式指定 errors，避免程序崩溃")


# ===== 语法解析 =====
# 【2】二进制文件读写
#   open 模式中 'b' 的含义：以【字节】为单位读写，不做任何编码转换
#   模式速查：
#     'rb'  读二进制     'wb'  写二进制（覆盖）
#     'ab'  追加二进制   'xb'  排他创建（已存在则报错）
#     'r+b' 读写二进制（不截断，必须文件已存在）
#     'w+b' 读写二进制（先截断）
#   设计意图：'b' 模式下不经过文本层的编码/换行转换，
#             写入的字节与内存中的 bytes 完全一致。
def demo_binary_io() -> None:
    print("\n" + "=" * 74)
    print("【2】二进制文件读写")
    print("=" * 74)

    tmp = Path(tempfile.mkdtemp(prefix="binary_io_"))
    bin_file = tmp / "demo.bin"
    text_file = tmp / "demo.txt"

    try:
        # 写二进制
        payload = bytes(range(256))       # 0~255 的所有字节值
        with open(bin_file, "wb") as f:
            f.write(payload)
        print(f"① 写二进制 {len(payload)} 字节 → {bin_file.name}")
        print(f"  文件实际大小 = {bin_file.stat().st_size} 字节（与写入完全一致）")

        # 读二进制
        with open(bin_file, "rb") as f:
            content = f.read()
        print(f"② 读回内容校验: 完全一致 = {content == payload}")
        print(f"  前 8 字节 hex = {content[:8].hex()}")

        # ★ 追加模式
        with open(bin_file, "ab") as f:
            f.write(b"TAIL")
        print(f"③ 'ab' 追加模式: 文件大小 {payload.__len__()} → "
              f"{bin_file.stat().st_size} 字节（+4）")

        # ★ r+b 读写模式（不截断）
        with open(bin_file, "r+b") as f:
            f.seek(0)                     # 定位到文件开头
            f.write(b"\xAA\xBB")           # 覆盖前两个字节
        with open(bin_file, "rb") as f:
            print(f"④ 'r+b' 原地修改: 前 4 字节 = {f.read(4).hex()}"
                  f"  ← 大小未变，仅内容被覆盖")

        # ★ 排他模式 xb
        excl = tmp / "exclusive.bin"
        with open(excl, "xb") as f:
            f.write(b"first")
        try:
            with open(excl, "xb") as f:    # 文件已存在
                f.write(b"second")
        except FileExistsError as e:
            print(f"⑤ 'xb' 排他模式: 重复创建 → {type(e).__name__}")
        print("  ★ 用途：确保不会意外覆盖已有文件（临时文件的安全写法）")

        # ★ 二进制 vs 文本模式的实际差别
        with open(text_file, "w", encoding="utf-8") as f:
            f.write("行1\n行2\n")
        with open(text_file, "rb") as f:
            raw_bytes = f.read()
        print(f"\n⑥ 文本模式写入 vs 原始字节：")
        print(f"  以 'wb' 读到的内容 = {raw_bytes!r}")
        print(f"  说明：'\\n' 在二进制中就是 0x0A，一个字节；")
        print(f"       Windows 文本模式写 '\\n' 会变成 '\\r\\n' 两个字节")
        print(f"  ★ 所以图片/字体/模型等必须用二进制模式，否则文件会被破坏")

        # tell/seek：随机访问
        print(f"\n⑦ tell() / seek() 随机访问：")
        with open(bin_file, "rb") as f:
            print(f"  初始 tell() = {f.tell()}")
            f.seek(0, os.SEEK_END)          # 定位到文件末尾
            size = f.tell()
            print(f"  seek(0, SEEK_END) → tell() = {size}（即文件大小）")
            f.seek(-4, os.SEEK_END)         # 相对末尾往前 4 字节
            print(f"  seek(-4, SEEK_END) 读最后 4 字节 = {f.read()!r}")
            f.seek(2)                       # 绝对定位
            print(f"  seek(2) 后读 4 字节 = {f.read(4)!r}")

        # ★ 为什么不能用 seek 的场景：管道/网络流
        print(f"\n⑧ 不可 seek 的流：")
        print("  管道(stdin)、网络 socket、zip 内部的流【不支持 seek】")
        print("  对它们调用 seek() 会抛 io.UnsupportedOperation")
        print("  ★ 流式处理的代码因此【只能顺序读】，这正是分块读取的基础")

    finally:
        shutil.rmtree(tmp, ignore_errors=True)
        print(f"\n已清理临时目录: {tmp}")


# ===== 语法解析 =====
# 【3】struct：二进制结构化打包
#   设计意图：C 语言和大多数二进制协议都按【固定字节布局】存储数据，
#             struct 让 Python 能按同样的布局读写，实现协议兼容。
#   格式字符：
#     b/B  有符号/无符号整数（1 字节）
#     h/H  短整数（2 字节）    i/I  整型（4 字节）
#     q/Q  长整型（8 字节）    f    浮点（4 字节）
#     d    双精度浮点（8 字节）
#     s    字符串（需配长度）   x  填充字节
#     ?    布尔
#   前缀（字节序）：
#     '>'  大端（网络字节序，★协议常用）
#     '<'  小端（x86 原生，本地计算快）
#     '='  本机字节序
#     '!'  网络字节序（等价于 '>' 的别名）
def demo_struct() -> None:
    print("\n" + "=" * 74)
    print("【3】struct：二进制结构化打包")
    print("=" * 74)

    # 基本打包解包：magic + 版本号 + 长度 + 内容
    fmt = ">4sHIH"     # 4字节魔数 + 2字节无符号 + 4字节无符号 + 2字节无符号
    magic = b"PYED"
    version = 3
    count = 12345
    flags = 0xFF
    packed = struct.pack(fmt, magic, version, count, flags)

    print(f"① 基本打包解包：")
    print(f"  格式 {fmt!r} = 4字节魔数 + 2字节 + 4字节 + 2字节")
    print(f"  pack 后 = {packed!r}  ({len(packed)} 字节)")
    print(f"  hex     = {packed.hex()}")
    unpacked = struct.unpack(fmt, packed)
    print(f"  unpack  → {unpacked}")
    print(f"  为什么这么写：'>' 表示大端字节序，'s' 前缀数字表示定长字节数")

    # ★ 字节序的影响
    print(f"\n② ★ 字节序（小端 vs 大端）的影响：")
    value = 0x01020304
    be = struct.pack(">I", value)
    le = struct.pack("<I", value)
    print(f"  数值 0x01020304 = {value}")
    print(f"  大端 '>I' → {be.hex()}  （高位在前，符合人的阅读习惯）")
    print(f"  小端 '<I' → {le.hex()}  （低位在前，x86 内存实际布局）")
    print(f"  ★ 解析网络协议/文件格式必须用【正确的字节序】，否则数值全错")
    print(f"  ★ 解包未知来源数据时，可用 '=' 让系统自动适配本机字节序")

    # iter_unpack：处理连续记录
    print(f"\n③ ★ iter_unpack：批量解包连续记录（高性能）")
    # 模拟一个包含多条记录的二进制文件：每条 = 时间戳(4字节) + 温度(float 4字节)
    records = [(1000, 25.5), (2000, 26.8), (3000, 24.1), (4000, 27.3)]
    blob = b"".join(struct.pack(">If", ts, temp) for ts, temp in records)
    print(f"  原始数据 {len(blob)} 字节 = 4 条记录 × 8 字节")
    # iter_unpack 返回迭代器，一次解包所有记录，比逐个 unpack 快
    decoded = list(struct.iter_unpack(">If", blob))
    print(f"  iter_unpack → {decoded}")
    print(f"  每项是元组 (时间戳, 温度)")
    print(f"  ★ 优点：内存友好（惰性迭代），且 C 层循环比 Python 快数倍")

    # 字符串字段
    print(f"\n④ 含字符串的格式：")
    fmt2 = ">10sH"      # 10 字节字符串 + 2 字节整数
    packed2 = struct.pack(fmt2, b"hello", 42)
    name, num = struct.unpack(fmt2, packed2)
    print(f"  pack(b'hello', 42) → {packed2.hex()}")
    print(f"  unpack → name={name!r}, num={num}")
    print(f"  ⚠ '10s' 读出的是 10 字节，可能带尾部空字节，需 .rstrip(b'\\x00')")
    print(f"  实测 strip 后 = {name.rstrip(chr(0).encode())!r}")

    # 对齐与 size/alignment
    print(f"\n⑤ ★ 对齐问题（最容易踩的坑）：")
    # 选 'c'(1字节) + 'i'(4字节) 组合：按本机对齐时 i 前会插入 3 字节填充
    print(f"  'c' 占 1 字节，'i' 占 4 字节，组合起来大小差异明显：")
    print(f"  'ci'  (本机对齐，插填充) → {struct.calcsize('ci')} 字节 "
          f"{struct.pack('ci', b'x', 1).hex()}")
    print(f"  '=ci' (标准大小，无填充) → {struct.calcsize('=ci')} 字节 "
          f"{struct.pack('=ci', b'x', 1).hex()}")
    print(f"  '>ci' (大端，无填充)     → {struct.calcsize('>ci')} 字节 "
          f"{struct.pack('>ci', b'x', 1).hex()}")
    print(f"  '@ci' (强制本机对齐)    → {struct.calcsize('@ci')} 字节 "
          f"{struct.pack('@ci', b'x', 1).hex()}")
    print(f"  ★ 差异：'ci' 在 x 后面插了 3 个填充字节(00)，数据被撑到 {struct.calcsize('ci')} 字节")
    print(f"  ★ 填充字节是无意义的数据，会让文件变大，且不同平台对齐规则不同")
    print(f"  ★ 存盘/网络传输应显式用 '<' 或 '>'，让布局确定且可移植")

    # size 与 unpack_from：无需预知大小
    print(f"\n⑥ struct.calcsize / unpack_from：")
    size = struct.calcsize(">I H")
    print(f"  calcsize('>I H') = {size} 字节（可预先算准记录大小）")
    # unpack_from 从指定偏移解包，适合含文件头的复合格式
    full = struct.pack(">I I H 5s", 0xDEADBEEF, 7, 3, b"XYZWV")
    magic2, val, count2, tail = struct.unpack_from(">I I H 5s", full, 0)
    print(f"  从偏移 0 解包复合结构 → magic=0x{magic2:08X}, val={val}, "
          f"count={count2}, tail={tail!r}")
    print(f"  ★ unpack_from 是解析「带文件头的二进制格式」的标准手段")
    print(f"     （如 PNG 的 8 字节签名、DOCX 的 PK 头）")

    # 校验和示例
    print(f"\n⑦ 实战：数据校验（crc32）")
    import zlib
    data = b"hello world"
    crc = zlib.crc32(data)
    print(f"  crc32(b'hello world') = 0x{crc:08X}")
    print(f"  打包成 4 字节存文件: {struct.pack('>I', crc).hex()}")
    print(f"  ★ 这是许多文件格式（zip/gzip/PNG）校验数据完整性的方式")


# ===== 语法解析 =====
# 【4】array 模块：紧凑存储数值
#   设计意图：Python 的 list 每个元素是 8 字节指针 + 独立对象，
#             存储 int 浪费内存。array 用 C 数组存储原始值，
#             存 1 万个 int 只占 4 万字节（typecode 'i'）而非几十万个指针。
#   代价：只能存同一种数值类型，且没有 list 的丰富方法。
def demo_array() -> None:
    print("\n" + "=" * 74)
    print("【4】array：紧凑的数值数组")
    print("=" * 74)

    # list vs array 的内存对比
    import sys as _sys

    big_list = [i for i in range(10000)]
    arr_i = array.array("i", big_list)          # 'i' = 4 字节有符号 int
    arr_l = array.array("l", big_list)          # 'l' = C long，平台相关
    arr_d = array.array("d", [i * 1.5 for i in range(10000)])   # 'd' = 8字节浮点

    def obj_size(o: Any) -> int:
        """估算对象占用的内存字节数（含元素对象开销）。"""
        return _sys.getsizeof(o) + sum(
            _sys.getsizeof(x) for x in o
        ) if isinstance(o, list) else _sys.getsizeof(o)

    print(f"① 内存占用对比（1 万个整数）：")
    print(f"  list 容器本身 = {_sys.getsizeof(big_list)} 字节")
    print(f"  array('i')     = {_sys.getsizeof(arr_i)} 字节")
    print(f"  list + 元素对象合计 ≈ {obj_size(big_list)} 字节")
    print(f"  ★ array 紧凑得多：元素直接以 C 数值存储，没有 Python 对象开销")
    print(f"    （注意：元素对象开销估算偏大，因为小整数被缓存复用；")
    print(f"     但对非小整数的数据集，差距是数量级的）")

    print(f"\n② typecode 类型码：")
    print(f"  array('b').itemsize = {array.array('b').itemsize} 字节  (有符号字节)")
    print(f"  array('h').itemsize = {array.array('h').itemsize} 字节  (短整型)")
    print(f"  array('i').itemsize = {array.array('i').itemsize} 字节  (整型)")
    print(f"  array('f').itemsize = {array.array('f').itemsize} 字节  (单精度浮点)")
    print(f"  array('d').itemsize = {array.array('d').itemsize} 字节  (双精度浮点)")

    print(f"\n③ 基本操作：")
    arr = array.array("i", [1, 2, 3, 4, 5])
    arr.append(6)
    print(f"  array('i', [1..5]) → append(6) = {list(arr)}")
    print(f"  sum(arr)   = {sum(arr)}")
    print(f"  max/min    = {max(arr)} / {min(arr)}")
    print(f"  支持索引    = {arr[2]}")
    print(f"  支持切片    = {arr[1:3]}（返回同类型 array）")
    print(f"  ⚠ 不支持 append 之外的方法："
          f"{'有 sort 方法' if hasattr(arr, 'sort') else '无 sort 方法'}，"
          f"需用 sorted() 返回新对象")

    # tobytes/frombytes：与二进制互转
    print(f"\n④ ★ tobytes/frombytes：与二进制数据互转（对接 struct）")
    data = arr.tobytes()
    print(f"  arr.tobytes() = {data.hex()}  ({len(data)} 字节)")
    restored = array.array("i")
    restored.frombytes(data)
    print(f"  frombytes 后还原 = {list(restored)}  ← 内容一致 = {list(restored) == list(arr)}")
    print(f"  ★ 用途：把数值数组存成二进制文件，实现紧凑存储")


# ===== 语法解析 =====
# 【5】pickle：对象序列化
#   语法规则：
#     pickle.dump(obj, file, protocol)   对象 → 文件
#     pickle.load(file)                  文件 → 对象
#     pickle.dumps(obj, protocol)        对象 → bytes
#     pickle.loads(bytes)                bytes → 对象
#
#   协议版本（protocol 参数）：
#     0  文本表示，最兼容但体积大（Python 2 的默认格式）
#     2  二进制表示，更紧凑
#     3  支持 bytes 对象
#     4  优化体积，支持大对象（当前推荐）
#     5  支持 out-of-band 数据缓冲
#     HIGHEST_PROTOCOL 常量 = 当前最高版本
#
#   ★ 关键认知：pickle 保存的是【对象的完整状态 + 类型信息】，
#     而不只是数据。它记录了"如何重建这个对象"，这正是它强大且危险的原因。
def demo_pickle_basics() -> None:
    print("\n" + "=" * 74)
    print("【5】pickle：基本使用")
    print("=" * 74)

    # 演示数据
    # ★ 能被 pickle 的对象：自定义类必须定义在【模块顶层】（见文件开头的 Point）
    data = {
        "name": "张伟",
        "age": 30,
        "scores": [90, 85, 92],
        "tags": {"python", "web"},
        "point": Point(3, 4),
    }

    # dumps/loads：内存中的序列化
    blob = pickle.dumps(data, protocol=pickle.HIGHEST_PROTOCOL)
    print(f"① dumps/loads 基本用法：")
    print(f"  序列化后类型 = {type(blob).__name__}，长度 = {len(blob)} 字节")
    print(f"  前 32 字节 hex = {blob[:32].hex()}")
    restored = pickle.loads(blob)
    print(f"  反序列化结果 = {restored}")
    print(f"  类型信息完整保留 = {type(restored['point']).__name__}  ← 类也被保存了")
    print(f"  数据完全一致 = {restored['name'] == data['name']}")

    # 协议版本对比
    print(f"\n② 协议版本对比（同一对象，不同 protocol）：")
    print(f"  HIGHEST_PROTOCOL = {pickle.HIGHEST_PROTOCOL}")
    for proto in range(0, pickle.HIGHEST_PROTOCOL + 1):
        try:
            b = pickle.dumps(data, protocol=proto)
            print(f"  protocol={proto}: {len(b):>4} 字节")
        except (ValueError, TypeError) as e:
            print(f"  protocol={proto}: 不支持（{type(e).__name__}）")
    print("  ★ 版本越高通常体积越小、速度越快，但老版本 Python 读不了高版本数据")
    print("  ★ 跨版本通信要兼顾兼容性：存长期数据用 protocol=2~4")

    # 文件读写
    tmp = Path(tempfile.mkdtemp(prefix="pickle_demo_"))
    try:
        pkl_file = tmp / "data.pkl"
        with open(pkl_file, "wb") as f:
            pickle.dump(data, f, protocol=pickle.HIGHEST_PROTOCOL)
        print(f"\n③ dump/load 文件读写：")
        print(f"  已写入 {pkl_file.name}，大小 = {pkl_file.stat().st_size} 字节")
        with open(pkl_file, "rb") as f:
            from_file = pickle.load(f)
        print(f"  load 还原 = {from_file['name']!r}, "
              f"point = {from_file['point']}")

        # 对比 JSON：pickle 体积更小但不可读
        import json
        json_size = len(json.dumps({"name": "张伟", "age": 30,
                                    "scores": [90, 85, 92],
                                    "tags": ["python", "web"]},
                                   ensure_ascii=False).encode())
        print(f"\n④ pickle vs json 对比：")
        print(f"  pickle 大小 = {pkl_file.stat().st_size} 字节")
        print(f"  json   大小 = {json_size} 字节（不含自定义类）")
        print(f"  ★ pickle 更快更全（能存任意 Python 对象），但不可读、不安全")
        print(f"  ★ json 慢但可读、跨语言、安全；只存纯数据时优先 json")

        # ⚠ 自定义类的限制
        print(f"\n⑤ ⚠ pickle 自定义类的限制：")
        # Point 定义在【模块顶层】，所以能正常序列化
        ok_blob = pickle.dumps(Point(1, 2))
        print(f"  模块顶层的类 dump 成功，{len(ok_blob)} 字节")
        # 反例：局部类（定义在函数内部）无法被 pickle
        class LocalPoint:                    # 局部类，函数返回后就不存在了
            pass
        try:
            pickle.dumps(LocalPoint())
        except (AttributeError, pickle.PicklingError) as e:
            print(f"  函数内的局部类 dump → {type(e).__name__}: {e}")
        print("  ★ 关键限制：反序列化时必须能【导入到同一个类】")
        print("     所以自定义类必须定义在模块顶层（可被 import），")
        print("     不能定义在函数内部，否则 dump 时就会直接报错")

        # pickle 支持的多种类型
        print(f"\n⑥ pickle 支持的多种类型：")
        import datetime as _dt
        # 用 list of (标签, 对象) 而不是 dict，避免 tuple 键的歧义
        samples: List[Tuple[str, Any]] = [
            ("int/float/str/bool/None", {"i": 1, "f": 1.5, "s": "x",
                                         "b": True, "n": None}),
            ("list", [1, 2, 3]),
            ("tuple", (3, 4)),
            ("set", {5, 6}),
            ("dict 嵌套", {"a": {"b": {"c": 1}}}),
            ("datetime", _dt.datetime(2024, 1, 1)),
            ("bytes", b"raw"),
        ]
        for label, obj in samples:
            try:
                back = pickle.loads(pickle.dumps(obj))
                ok = (back == obj)
            except Exception:
                ok = False
            print(f"  {'✓' if ok else '✗'} {label}")
        print("  ★ 大部分内置类型都支持，但【函数、lambda、生成器、文件句柄】")
        print("     【无法】被 pickle")

        print(f"\n⑦ 无法 pickle 的类型：")
        import io
        unliftable: List[Tuple[str, Any]] = [
            ("lambda 表达式", lambda x: x),
            ("生成器", (i for i in range(3))),
            ("模块对象", sys),
            ("局部定义的类", type("Local", (), {"__module__": "__main__"})),
        ]
        for label, obj in unliftable:
            try:
                pickle.dumps(obj)
                print(f"  {label}: 可以 pickle")
            except (pickle.PicklingError, TypeError, AttributeError) as e:
                print(f"  {label}: {type(e).__name__}")
        # 注意：io.StringIO 等部分文件类【是】可以 pickle 的，
        # 但真实文件句柄（open() 的返回值）不行——别一概而论。

    finally:
        shutil.rmtree(tmp, ignore_errors=True)
        print(f"\n已清理临时目录: {tmp}")


# ===== 语法解析 =====
# 【6】★★ pickle 反序列化攻击的原理与防御
#   ⚠ 本节【只做原理解释，不构造、不运行任何攻击 payload】，
#     目的是让学习者理解"为什么 pickle 反序列化 = 任意代码执行"。
#
#   【攻击原理】
#   pickle 的本质是一个【小型虚拟机】：pickle 数据由一串"操作码(opcode)"组成，
#   每个操作码对应一个动作，如：
#     PROTO  声明协议版本
#     GLOBAL 导入一个模块中的某个名字        ← 危险点①
#     REDUCE 调用一个对象，并传入参数          ← 危险点②
#     BUILD  用状态字典更新对象 __dict__
#   load() 的过程就是【顺序执行这些操作码，重建对象】。
#   关键在于 GLOBAL + REDUCE 的组合可以实现：
#     "导入 os.system，然后把字符串传给它执行"
#   所以 pickle.load() 本质上等价于【执行一段被压缩过的字节码】，
#   它无法判断数据是否"可信"。攻击者只要控制 pickle 数据，
#   就能让你的程序执行任意命令（读文件、反弹 shell、提权……）。
#
#   【为什么危险】
#     1. 恶意 pickle 文件看起来是二进制乱码，人和防病毒软件都难识别
#     2. 它可能在"加载模型/缓存/会话"等看似无害的场景被触发
#     3. __reduce__ 允许任何类"自定义"如何被 pickle，从而嵌入任意函数调用
#
#   【防御方案】
#     方案一【首选】：不要用 pickle 加载不可信数据
#            —— 纯数据交换用 json / msgpack（它们只解析数据，不执行代码）
#     方案二：如果必须用 pickle，加【完整性校验 HMAC】
#            —— 先用 hmac 对数据签名，验证通过才 load
#     方案三：限制可用的类（自定义 Unpickler.find_class）
#            —— 白名单机制，只允许反序列化指定的少数类型
#     方案四：隔离执行
#            —— 在容器/沙箱/独立进程中运行反序列化逻辑
def demo_pickle_security() -> None:
    print("\n" + "=" * 74)
    print("【6】★★ pickle 反序列化攻击：原理与防御（不执行任何攻击代码）")
    print("=" * 74)

    print("\n① 为什么 pickle 反序列化 = 任意代码执行？")
    print("  pickle 数据是【操作码流】，load() 逐条执行以重建对象。")
    print("  其中两个操作码组合起来非常危险：")
    print("    GLOBAL  <模块名> <名字>   → 导入模块中的某个可调用对象")
    print("    REDUCE  <参数元组>        → 用参数调用这个对象")
    print("  两者组合的效果 = 「拿到某个 Python 函数，用我给定的参数调用它」。")
    print("  如果这个函数是系统命令执行函数，那么加载即等于执行命令。")

    print("\n② __reduce__ 的作用（这是原理的核心）：")
    print("  Python 允许任何类通过定义 __reduce__ 自定义'如何被 pickle'：")
    print("  当 pickle 遇到带 __reduce__ 的对象时，会把返回的元组")
    print("  (可调用对象, 构造参数) 编码成 GLOBAL+REDUCE 操作码。")
    print("  这意味着：即使你的类是纯业务类，攻击者也能利用")
    print("  某些系统的内置类（如 subprocess、os 的包装）构造恶意数据流。")

    # 用一个无害的例子说明 GLOBAL+REDUCE 的机制（不涉及任何危险函数）
    print("\n③ 机制演示（使用【无害】函数，不涉及系统命令）：")
    # ★ Adder 定义在模块顶层（见文件开头），局部类无法被 pickle
    obj = Adder(3, 4)
    blob = pickle.dumps(obj)
    # 查看 pickle 字节流里的操作码
    print(f"  对象 = {obj}")
    print(f"  pickle 后 {len(blob)} 字节，字节流（部分）: {blob[:40]!r}")
    print(f"  ★ 可以看到字节流里出现了模块名和类名的引用，")
    print(f"    这正是 GLOBAL 操作码——load 时会去 import 并引用它")
    restored = pickle.loads(blob)
    print(f"  还原 = {restored}")
    print("  （此处用的是无害的构造器；攻击者换成危险函数即为攻击）")

    print("\n④ 攻击链的概念流程（仅文字说明，不构造 payload）：")
    print("  step1 攻击者构造恶意 pickle 数据，其操作码等价于：")
    print("         调用 [某个能触发系统行为的函数]，参数为 [攻击者指定的命令]")
    print("  step2 将该数据伪装成 .pkl / 缓存 / 模型文件 / 会话文件 分发")
    print("  step3 受害程序执行 pickle.load() / joblib.load() / "
          "torch.load()")
    print("  step4 load 顺序执行操作码 → 危险函数被以攻击者参数调用 → 命令执行")
    print("  ★ 之所以难以防御，是因为【在 load 完成前无法判断数据是否恶意】")

    print("\n⑤ ★ 防御方案一：HMAC 签名校验（原理演示）")
    import hmac
    import hashlib as _hashlib

    # 原理：用一个只有你和服务器知道的密钥对数据签名，
    # 加载前先验证签名，对不上就拒绝——攻击者没有密钥就伪造不出签名。
    SECRET = b"demo-secret-key-do-not-use-in-production"
    payload = {"user": "admin", "role": "read"}

    def sign(data: bytes, key: bytes) -> bytes:
        """用 HMAC-SHA256 对数据签名。"""
        return hmac.new(key, data, _hashlib.sha256).digest()

    # 正常流程：签名 → 写入 → 验证 → 加载
    data_blob = pickle.dumps(payload)
    signature = sign(data_blob, SECRET)
    print(f"  原始数据 = {data_blob!r}")
    print(f"  签名(前 16 字节) = {signature[:16].hex()}...")
    verified = hmac.compare_digest(sign(data_blob, SECRET), signature)
    print(f"  验证签名通过 = {verified}  → 可以安全 load")
    print(f"  load 结果 = {pickle.loads(data_blob)}")

    # 篡改场景：数据被改但签名未更新
    tampered = pickle.dumps({"user": "admin", "role": "ROOT"})   # 内容被篡改
    verified_tampered = hmac.compare_digest(sign(tampered, SECRET), signature)
    print(f"\n  数据被篡改后，签名验证 = {verified_tampered}  → 拒绝加载！")
    print("  ★ 原理：HMAC 用密钥保证只有可信来源能产生有效签名")
    print("  ★ 局限：密钥泄露则防护失效；仍需保证 pickle.load 只在校验后执行")

    print("\n⑥ ★ 防御方案二：自定义 Unpickler 白名单")
    print("  通过覆写 find_class，只允许反序列化【白名单里的类型】：")
    print("    class SafeUnpickler(pickle.Unpickler):")
    print("        ALLOWED = {'builtins': {'dict', 'list', 'set'}}")
    print("        def find_class(self, module, name):")
    print("            if module not in self.ALLOWED or \\")
    print("               name not in self.ALLOWED[module]:")
    print("                raise pickle.UnpicklingError('禁止的类型')")
    print("            return super().find_class(module, name)")
    print("  ★ 原理：find_class 是 pickle 加载【类/函数】的唯一入口，")
    print("    在这里拦截就能阻断 GLOBAL 操作码指向危险函数")

    # 实际演示白名单机制（用无害类型）
    class SafeUnpickler(pickle.Unpickler):
        """只允许反序列化 dict/list 等纯数据类型。"""

        ALLOWED = {
            "builtins": {"dict", "list", "set", "tuple", "int", "str", "float"},
        }

        def find_class(self, module: str, name: str) -> Any:
            # 校验这个"类引用"是否在白名单内
            if module not in self.ALLOWED or name not in self.ALLOWED[module]:
                raise pickle.UnpicklingError(f"禁止反序列化类型: {module}.{name}")
            return super().find_class(module, name)

    tmp = Path(tempfile.mkdtemp(prefix="safe_unpickle_"))
    try:
        safe_file = tmp / "safe.pkl"
        # 写入纯数据（只有 dict/list，应该能加载）
        with open(safe_file, "wb") as f:
            pickle.dump({"a": [1, 2, 3]}, f)
        with open(safe_file, "rb") as f:
            safe_result = SafeUnpickler(f).load()
        print(f"\n  白名单允许的数据加载成功 = {safe_result}")

        # 构造一个引用【非白名单】类型的数据（用 operator.add，它是安全函数）
        # 目的只是让数据里带上「函数引用」这种 GLOBAL 操作码，
        # 观察白名单能否拦截，而不是真的执行任何危险操作
        import operator

        evil_file = tmp / "blocked.pkl"
        with open(evil_file, "wb") as f:
            pickle.dump(operator.add, f)   # 序列化一个函数引用
        with open(evil_file, "rb") as f:
            try:
                SafeUnpickler(f).load()
                print("  非白名单数据竟然加载了（不应发生）")
            except pickle.UnpicklingError as e:
                print(f"  非白名单数据被拦截 = {type(e).__name__}: {e}")
                print("  ★ 白名单成功阻断了 GLOBAL 操作码的函数引用")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print("\n⑦ 各方案对比与选型建议：")
    print("  ┌ 场景                  → 推荐方案")
    print("  │ 纯数据交换（网络/文件） → json / msgpack（★最安全）")
    print("  │ 缓存临时数据          → pickle 需配 HMAC 签名")
    print("  │ 机器学习模型          → 优先 safetensors 等安全格式；")
    print("  │                         禁用 torch.load 的反序列化风险")
    print("  │ 不可信输入            → 【绝对不要】用 pickle")
    print("  │ 内部进程间传输        → pickle 可用（信任边界内）")
    print("  ★ 核心原则：【永远不要对不可信数据调用 pickle.load】")

    print("\n⑧ 其他相关风险提醒：")
    print("  - json 也有风险但类型有限：json 不会调用任意函数，"
          "但别和 eval() 混用")
    print("  - eval()/exec() 同样危险，且 ast.literal_eval 是 json 的安全替代")
    print("  - 不可信输入应做 schema 校验（如校验类型、范围、长度）")
    print("  - 下载的第三方库/扩展模块也可能是投毒载体，供应链安全同样重要")


# ===== 语法解析 =====
# 【7】大文件流式处理：为什么必须分块
#   设计意图：内存是有限资源，一个 10GB 的文件用 read() 一次性读入会
#             申请 10GB 内存，直接 OOM（MemoryError）。
#             流式处理只保持【一个块】在内存中，内存占用与文件大小【无关】。
#
#   分块读取的标准写法（背下来）：
#       for chunk in iter(lambda: f.read(CHUNK_SIZE), b""):
#           process(chunk)
#   逐句解释：
#     1. iter(callable, sentinel)：反复调用 callable，直到它返回 sentinel 为止
#     2. f.read(n)：读最多 n 字节，到文件尾时返回【不足 n 的剩余字节】
#     3. sentinel 用 b""（空 bytes）：只有真正读完才返回它
#     4. ★ 必须用 lambda 延迟调用；若写成 iter(f.read(n), b"")，
#          f.read(n) 会在 iter() 之前就执行一次，之后立即停止——这是常见 bug
def demo_streaming() -> None:
    print("\n" + "=" * 74)
    print("【7】★ 大文件流式处理")
    print("=" * 74)

    tmp = Path(tempfile.mkdtemp(prefix="stream_demo_"))
    big_file = tmp / "big.txt"

    try:
        # 生成一个 10 MB 的测试文件（内容为重复的自然语言片段）
        chunk_to_write = ("Python 是一门优雅的编程语言。它以可读性高著称，"
                          "拥有丰富的标准库和活跃的社区生态。"
                          "本文件用于演示大文件的分块读取技术。\n")
        total_size = 10 * 1024 * 1024      # 10 MB
        print(f"① 生成 {total_size // 1024 // 1024} MB 测试文件...")
        with open(big_file, "w", encoding="utf-8") as f:
            written = 0
            while written < total_size:
                f.write(chunk_to_write)
                written += len(chunk_to_write.encode("utf-8"))
        actual_size = big_file.stat().st_size
        print(f"  实际大小 = {actual_size / 1024 / 1024:.2f} MB")

        # ★ 方式一：一次性读取（错误做法，只为对比）
        print(f"\n② 一次性 read() —— 会把整个文件装进内存：")
        tracemalloc.start()
        with open(big_file, "rb") as f:
            whole = f.read()                 # 危险：申请与文件等大的内存
        _, peak_all = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        print(f"  内存峰值 ≈ {peak_all / 1024 / 1024:.2f} MB  ← 约等于文件大小！")
        print(f"  ★ 文件若 10GB，这里就会申请 10GB 内存 → MemoryError")
        del whole                           # 释放内存

        # ★ 方式二：分块读取（正确做法）
        print(f"\n③ ★ 分块读取 iter(lambda: f.read(n), b'') —— 标准写法：")
        CHUNK = 64 * 1024                    # 64 KB 一块
        tracemalloc.start()
        total_bytes = 0
        chunk_count = 0
        with open(big_file, "rb") as f:
            # ★★ 逐句拆解这个写法：
            # iter(callable, sentinel) —— 反复调用 callable 直到返回 sentinel
            # callable = lambda: f.read(CHUNK) —— 每次读一块
            # sentinel = b"" —— 空 bytes 表示文件读完（真正的结束标志）
            # 为什么用 lambda：延迟求值，保证每次迭代才读一次；
            #         若写 iter(f.read(CHUNK), b"") 只会读第一块就停（bug）
            for chunk in iter(lambda: f.read(CHUNK), b""):
                total_bytes += len(chunk)
                chunk_count += 1
        _, peak_chunk = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        print(f"  内存峰值 ≈ {peak_chunk / 1024:.1f} KB  ← 恒定，与文件大小无关！")
        print(f"  共 {chunk_count} 块，累计 {total_bytes / 1024 / 1024:.2f} MB")
        print(f"  ★ 对比：内存从 {peak_all / 1024 / 1024:.2f} MB 降到 "
              f"{peak_chunk / 1024:.1f} KB")

        # ★ readinto：零分配的缓冲区读取
        print(f"\n④ ★ readinto()：复用缓冲区，避免每次分配新块")
        tracemalloc.start()
        buffer = bytearray(CHUNK)          # ★ 预先分配一块固定缓冲区
        total_bytes2 = 0
        with open(big_file, "rb") as f:
            while True:
                n = f.readinto(buffer)      # 直接读进已有缓冲区，不新建对象
                if n == 0:
                    break                   # 读到文件尾（返回 0）
                total_bytes2 += n
                # 此时 buffer[:n] 就是刚读到的数据（注意切片[:n]）
        _, peak_into = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        print(f"  内存峰值 ≈ {peak_into / 1024:.1f} KB")
        print(f"  累计读取 {total_bytes2 / 1024 / 1024:.2f} MB")
        print("  ★ 优势：缓冲区只分配一次，全程复用，适合超高频读取")
        print("  ★ 注意：readinto 返回实际读取的字节数，最后一块可能不满")

        # ★ 行式流式处理
        print(f"\n⑤ ★ 行式流式处理（for line in f）：")
        print("  文本模式下，for line in f 也是惰性逐行读取，不会加载整个文件")
        line_count = 0
        char_count = 0
        with open(big_file, "r", encoding="utf-8") as f:
            for line in f:                  # 逐行，内存只驻留当前行
                line_count += 1
                char_count += len(line)
        print(f"  逐行读取 {line_count} 行，共 {char_count} 个字符")
        print("  ★ for line in f 是【惰性】的：每次迭代只从缓冲区取一行")
        print("  ★ 等价于显式调用 f.readline()，但由解释器优化，效率更高")
        print("  ★ 注意：文本模式下 tell() 只能返回不透明位置，seek() 受限")

        # ⚠ tell/seek 在文本模式下的陷阱
        print(f"\n⑥ ⚠ 文本模式的 tell()/seek() 陷阱：")
        with open(big_file, "r", encoding="utf-8") as f:
            pos1 = f.tell()
            f.readline()
            pos2 = f.tell()
        print(f"  读一行后 tell() = {pos2}  ← 不是简单的字节数")
        print("  ★ 原因：文本模式有【缓冲区】和【编码换算】，位置是不透明的字节偏移")
        print("  ★ 结论：需要精确随机访问时，用二进制模式 'rb' + tell/seek")

        # 生成器管道：把块处理封装成可复用组件
        print(f"\n⑦ ★ 生成器管道：封装成可复用的流式工具：")

        def read_chunks(path: Path, size: int = CHUNK) -> Iterator[bytes]:
            """以生成器形式分块产出文件内容。"""
            with open(path, "rb") as f:
                yield from iter(lambda: f.read(size), b"")

        def count_nonempty(path: Path) -> int:
            """统计文件非空行数（流式处理典型用例）。"""
            count = 0
            for chunk in read_chunks(path):
                # 按行拆分处理块内数据
                count += sum(1 for line in chunk.splitlines() if line.strip())
            return count

        nonempty = count_nonempty(big_file)
        print(f"  流式统计非空行数 = {nonempty}")
        print(f"  ★ 生成器：写一次、复用多次；yield 使函数变成惰性数据源")
        print("  ★ yield from 可把另一个生成器的结果直接透传（简化代码）")

    finally:
        shutil.rmtree(tmp, ignore_errors=True)
        print(f"\n已清理临时目录: {tmp}")


# ===== 语法解析 =====
# 【8】分块读取统计词频（核心技术点：跨块边界）
#   难点：如果一个单词恰好被块边界劈开（"Py" | "thon"），
#         简单地对每块独立 split() 会把它算成两个错误的词。
#   解决方案：
#     维护一个【残留尾巴】，把上一块末尾不完整的部分接到下一块前面。
#     判断"不完整"的标准：块末尾不是空白字符（说明单词被劈开了）。
def demo_word_count_streaming() -> None:
    print("\n" + "=" * 74)
    print("【8】★★ 分块读取统计词频（处理跨块边界的单词）")
    print("=" * 74)

    # ★★ 核心函数：带跨块处理的词频统计
    def count_words_file(path: Path, chunk_size: int = 16) -> Counter:
        """分块读取文件统计词频，正确处理被块边界劈开的单词。

        原理：
        - 每次处理时，先把上一块的【残留片段】拼到当前块前面
        - 处理完当前块后，记录末尾不完整的片段作为新的残留
        - 文件读完后，残留片段是最后一个完整词，要补统计一次
        """
        counter: Counter = Counter()
        leftover = ""              # 上一块残留的不完整单词

        with open(path, "r", encoding="utf-8") as f:
            for chunk in iter(lambda: f.read(chunk_size), ""):
                # ★ 把上一块的残留拼到当前块【前面】，保证跨块单词完整
                text = leftover + chunk
                words = text.split()     # split() 自动按空白切分并忽略多余空白

                # 处理一个边界问题：
                # 如果块末尾不是空白字符（如 "thon"），说明最后一个词可能没读完，
                # 需要把它从 words 中取出，作为新的残留，不立即计数
                if text and not text[-1].isspace():
                    # ★ 最后一个词可能是跨块的，先扣出来当残留
                    leftover = words.pop() if words else ""
                else:
                    # 块以空白结尾，说明所有词都完整，可以全部计数
                    leftover = ""

                # 此时 words 中的都是【完整】单词，安全计数
                counter.update(words)

        # ★ 文件读完，leftover 是最后一个完整单词，别忘了统计它
        if leftover:
            counter.update([leftover])
        return counter

    # ★★ 对比：不做跨块处理的朴素版本（会出错）
    def count_words_naive(path: Path, chunk_size: int = 16) -> Counter:
        """错误示范：每块独立 split，不处理跨块单词。"""
        counter: Counter = Counter()
        with open(path, "r", encoding="utf-8") as f:
            for chunk in iter(lambda: f.read(chunk_size), ""):
                counter.update(chunk.split())     # ★ 直接 split，会把跨块词劈开
        return counter

    tmp = Path(tempfile.mkdtemp(prefix="wordcount_"))
    try:
        test_file = tmp / "text.txt"
        content = ("Python 是一门编程语言 Python 很好用 Python 有强大的生态 "
                   "learn Python step by step Python rocks")
        test_file.write_text(content, encoding="utf-8")

        print(f"① 测试文本：")
        print(f"  {content!r}")
        print(f"  文件大小 = {test_file.stat().st_size} 字节")
        print(f"  ★ 用 16 字节的小块来读，确保单词必然跨块")

        # 正确版本
        correct = count_words_file(test_file, chunk_size=16)
        print(f"\n② ★ 正确版本（处理跨块）：")
        for word, cnt in correct.most_common(10):
            print(f"  {word:<10} {cnt}")
        print(f"  Python 计数 = {correct['Python']}  ← 正确（文本中确实有 5 次）")

        # 错误版本
        naive = count_words_naive(test_file, chunk_size=16)
        print(f"\n③ 错误版本（不处理跨块，对比）：")
        for word, cnt in naive.most_common(10):
            print(f"  {word:<10} {cnt}")
        print(f"  Python 计数 = {naive['Python']}  ← 偏少！（单词被块边界劈开了）")
        print(f"  ★ 对比可见：跨块单词 'Pyth/on' 被错误拆成了两个碎片")

        # 用大块做对照（块够大就不会跨块，两者结果一致）
        correct_big = count_words_file(test_file, chunk_size=4096)
        naive_big = count_words_naive(test_file, chunk_size=4096)
        print(f"\n④ 用大块（4096 字节）读取的对照：")
        print(f"  正确版 = {dict(correct_big)}")
        print(f"  朴素版 = {dict(naive_big)}")
        print(f"  两者一致 = {correct_big == naive_big}  "
              f"← 块够大就不会跨块，两者自然相同")

        # 统计真实词频：对 data 目录的示例文件做词频（只读）
        print(f"\n⑤ 实战：对英文文本做词频统计（自动生成测试文件）：")
        # 动态创建一个稍大的英文文本，避免依赖外部文件
        big_text = tmp / "english.txt"
        words_sample = ("the quick brown fox jumps over the lazy dog "
                        "the dog barks and the fox runs away "
                        "quick thinking saves the day in programming")
        # ★ 重复拼接时必须加空格分隔符！
        #   若直接写 words_sample * 50，拼接处会变成 "programmingthe"，
        #   两个词被黏成一个，总词数就会比预期少 49 个（恰好是重复次数-1）
        big_text.write_text(" ".join([words_sample] * 50), encoding="utf-8")

        big_counter = count_words_file(big_text, chunk_size=64)
        print(f"  文件大小 = {big_text.stat().st_size} 字节")
        print(f"  Top 5 词频：")
        for word, cnt in big_counter.most_common(5):
            print(f"    {word:<10} {cnt} 次")
        # 验证总词数正确
        expected_total = len(words_sample.split()) * 50
        actual_total = sum(big_counter.values())
        print(f"  总词数校验: 期望 {expected_total}，实际 {actual_total}，"
              f"一致 = {expected_total == actual_total}")
        print(f"  ★ 总词数一致说明没有任何单词被重复计数或漏计，跨块处理正确")
        print(f"  ★ 对比上一节：若漏掉拼接处的空格，总词数会少 49 个，"
              f"这就是数据构造本身的坑，与分块读取无关")

        # ★ 性能对比：流式 vs 一次性
        import time
        perf_file = tmp / "perf.txt"
        perf_file.write_text(" ".join([words_sample] * 2000), encoding="utf-8")

        # 一次性
        start = time.perf_counter()
        with open(perf_file, "r", encoding="utf-8") as f:
            all_words = f.read().split()
        counter_all = Counter(all_words)
        t_all = time.perf_counter() - start

        # 流式
        start = time.perf_counter()
        counter_stream = count_words_file(perf_file, chunk_size=8192)
        t_stream = time.perf_counter() - start

        print(f"\n⑥ 性能对比（{perf_file.stat().st_size / 1024:.0f} KB 文件）：")
        print(f"  一次性读取+统计 = {t_all * 1000:.2f} ms，内存占用高")
        print(f"  流式分块+统计   = {t_stream * 1000:.2f} ms，内存恒定")
        print(f"  结果一致 = {counter_all == counter_stream}")
        print(f"  ★ 流式在处理超大文件时优势巨大：内存不随文件增长")
        print(f"  ★ 对小文件一次性更快（有整体缓存优势），大文件才必须流式")

    finally:
        shutil.rmtree(tmp, ignore_errors=True)
        print(f"\n已清理临时目录: {tmp}")


# ===== 语法解析 =====
# 【9】小结
def demo_summary() -> None:
    print("\n" + "=" * 74)
    print("【9】小结：二进制与大文件处理要点")
    print("=" * 74)
    print("""
  ── 二进制基础 ──
  1. bytes 不可变（可哈希）→ 可做 dict 键；bytearray 可变 → 可原地修改
  2. str 按字符计数，bytes 按字节计数；边界处显式 encode/decode
  3. memoryview 零拷贝视图，适合把大块数据交给网络/加密库
  4. bytes 没有 str 那些字符判断方法（isdigit 等）

  ── 文件模式 ──
  5. 'b' 表示不做编码转换；图片/字体/模型必须用二进制模式
  6. 'rb'读 'wb'写 'ab'追加 'xb'排他(不覆盖) 'r+b'读写不截断
  7. 二进制模式可精确 tell/seek；文本模式位置不透明

  ── struct ──
  8. struct 按固定字节布局打包，'<'小端 '>'大端 '='本机
  9. iter_unpack 批量解包连续记录，比逐个 unpack 快且省内存
  10. 存盘/传输必须显式指定字节序，避免本机对齐插入填充字节

  ── pickle 安全 ──
  11. ★★ 永远不要对不可信数据调用 pickle.load —— 等价于执行任意代码
  12. 原理：GLOBAL+REDUCE 操作码可引用并调用任意函数
  13. 防御：纯数据用 json/msgpack；必须用 pickle 时加 HMAC 或白名单
  14. 自定义 Unpickler.find_class 白名单是阻断攻击的有效手段

  ── 大文件 ──
  15. ★ 分块读取标准写法：for c in iter(lambda: f.read(n), b"")
      必须用 lambda 延迟调用，否则只读第一块就停
  16. readinto() 复用缓冲区，进一步降低分配开销
  17. for line in f 同样是惰性的，适合按行处理
  18. ★ 分块处理文本的关键是处理【跨块边界】：用残留尾巴拼接，
      否则 "Python" 被劈成 "Pyth"+"on" 会统计错误
    """)


def main() -> None:
    """主入口。"""
    print("=" * 74)
    print("二进制读写与大文件流式处理")
    print("=" * 74)
    print(f"Python 版本: {sys.version.split()[0]}")
    print("⚠ 本文件不执行任何不可信代码，pickle 风险部分仅做原理讲解")
    print()

    demo_bytes_basics()
    demo_binary_io()
    demo_struct()
    demo_array()
    demo_pickle_basics()
    demo_pickle_security()
    demo_streaming()
    demo_word_count_streaming()
    demo_summary()


if __name__ == "__main__":
    main()