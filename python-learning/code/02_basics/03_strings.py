# -*- coding: utf-8 -*-
r"""
================================================================================
文件：03_strings.py
模块：02_basics（基础语法配套）
【说明】本文件字符串教学主题多，文档字符串特意用原始字符串（r 前缀）书写：
        否则摘要里的转义记号会被 Python 自己先解释一遍，
        \u 甚至会因缺少 4 位十六进制而直接报 SyntaxError。

【本文件演示的语法点列表】
  1. 字符串的"不可变性"证明 —— 为什么 str 没有 append / 修改方法
  2. 字符串创建方式：字面量、构造、join、split、多行
  3. 索引与切片：负索引、步长、越界不报错、切片返回新对象
  4. 转义字符与原始字符串：\n \t \\ \u \x 与 r"..." 的区别
  5. 编码：ASCII / UTF-8 / Unicode，以及 encode / decode 的往返
  6. str 与 bytes 的关系 —— 文本模式 vs 二进制模式
  7. 常用方法全览：
       大小写类：upper lower title capitalize casefold swapcase
       查询类  ：find rfind index rindex count startswith endswith
                 isdigit isalpha isalnum isspace isupper islower istitle
       操作类  ：strip lstrip rstrip replace split rsplit splitlines
                 join center ljust rjust zfill removeprefix removesuffix
       判断类  ：isascii isprintable isidentifier
  8. 三种格式化方式对比：% / .format() / f-string（性能与可读性实测）
  9. f-string 的进阶：= 说明符、格式说明符 !r !s !a、嵌套引号、多行 f-string
 10. 常用场景：日志拼接、CSV 解析、URL 构造、文本对齐、密码脱敏
 11. 字符串驻留与驻留机制：sys.intern、is 判断的陷阱

【设计意图】
  str 被设计为不可变，有三个层面的好处：
  (1) 可以被安全地作为 dict 的 key / set 的元素 —— 因为 key 一旦存入就绝不能变，
      否则哈希值会失效，整张表会损坏；
  (2) 多线程下无需加锁即可安全共享 —— 没有任何线程能修改一个 str；
  (3) 字符串驻留与常量折叠（"a"+"b" 在编译期合并）才有可能，
      因为字面量本身不会被运行时改写。
  代价是"看似修改"的操作其实都是新建对象 + 返回，
  所以拼接大量字符串要用 ''.join 而不是 +=。

【预期输出摘要】
  [1] 不可变性：s[0]='X' 抛 TypeError，任何"修改"都产生新对象
  [2] 索引切片：负索引从尾部计；越界返回 ''；切片返回全新 str
  [3] 转义：r"\d+" 是正则，"\d+" 是退格符 + d + 加号
  [4] 编码：'中'.encode('utf-8') 得到 3 字节，decode 可完全还原
  [5] str vs bytes：bytes 不能切片出 str 以外的东西，str 与 bytes 相加报 TypeError
  [6] 方法表：分类打印全部方法及示例
  [7] 三种格式化：输出对齐对比 + timeit 实测 f-string 最快
  [8] f-string 进阶：f"{x=}" 自带表达式文本
  [9] 实战场景：CSV 解析、URL 构造、日志、密码脱敏、文本对齐
  [10] 驻留：sys.intern 可强制驻留，编译期字面量天然驻留
================================================================================
"""

import sys
import timeit


# ============================================================================
# 语法解析 1：不可变性 —— str 的第一性原理
# ============================================================================
# 【语法规则】
#   str 是不可变对象（immutable）：
#     - 没有 __setitem__、没有 append / pop / extend / remove
#     - 所有看似"修改"的方法（replace/strip/upper）都返回【新对象】
#     - 只有 index（只读）、count、find 等查询方法返回 int
#   字符串字面量 "abc" 是 str 对象；s[0] 读字符，s[0] = 'X' 是语法/运行时报错
# 【执行顺序】
#   s2 = s.replace('a','b') 的执行过程是：
#     1. 计算新字符串所需长度
#     2. 在堆上分配一块新内存
#     3. 把未命中的片段拷贝过去
#     4. 返回新对象的引用；原 s 引用计数不变、内容不变
# 【设计意图】
#   不可变性是 Python 能提供"字符串驻留 + 常量折叠 + 可哈希"的前提。
#   CPython 还利用它做字符串驻留（interning）：
#   编译期相同内容的字面量会被合并成同一个对象，
#   于是 `'abc' is 'abc'` 为 True，用字符串做 switch/case 判断才有意义。
def demo_immutability():
    print("[1] 字符串的不可变性")

    s = "Python"
    print(f"    原始 s = {s}, id = {hex(id(s))}")

    # 试图"修改"下标 -> TypeError
    try:
        s[0] = "J"  # type: ignore[index]
    except TypeError as e:
        print(f"    s[0] = 'J'  ->  TypeError: {e}")
    print("    -> str 没有 __setitem__，元素不可写")

    # 不存在这些方法
    for method in ("append", "pop", "insert", "remove", "sort"):
        print(f"    'Python'.{method:<8} 存在 = {hasattr(s, method)}")

    # "看似修改"其实返回新对象
    original = "  Hello World  "
    stripped = original.strip()
    print(f"    original.strip() 前 len={len(original)}, 原对象={original!r}")
    print(f"    original.strip() 后 len={len(stripped)}, 新对象={stripped!r}")
    print(f"    新对象 is 原对象 = {stripped is original}  (重新分配了内存)")

    # 证明内容确实没变
    _ = original.replace("Hello", "你好")
    print(f"    调用 replace 后原对象仍是 = {original!r}  (原对象不受影响)")

    # 用 id 追踪"修改"实际发生了什么
    a = "ab"
    b = a + "cd"
    print(f"    a = {a!r} (id={hex(id(a))}), b = a+'cd' = {b!r} (id={hex(id(b))})")
    print("    -> '+' 创建了新对象，a 与 b 是两个不同的字符串")

    # 字符串驻留：编译期相同的字面量被合并为同一对象
    # 注意：CPython 对字面量之间的 `is` 比较会发 SyntaxWarning（因为几乎总是笔误），
    # 所以这里先绑定到变量再比较 —— 这也是真实代码中的正确写法。
    lit_a = "abc"
    lit_b = "abc"
    print(f"    'abc' is 'abc'  = {lit_a is lit_b}   (编译期驻留：两个字面量合并为一个对象)")
    joined = "ab" + "c"
    print(f"    'ab'+'c' is 'abc' = {joined is lit_a}   (字面量拼接被【编译期常量折叠】，仍是同一对象)")
    # 但涉及变量的拼接就一定产生新对象：
    prefix = "ab"
    dynamic = prefix + "c"
    print(f"    (变量+'c') is 'abc' = {dynamic is lit_a}   (运行时才知道值，无法折叠 -> 新对象)")
    print("    -> 驻留/常量折叠只覆盖【编译期就能确定】的表达式，动态拼接必得新对象")

    # sys.intern 显式驻留：把运行时产生的字符串也放进驻留表
    hello_literal = "hello"
    runtime_str = "".join(["he", "llo"])
    print(f"    ''.join 产生的 {runtime_str!r} 是驻留对象吗 = {runtime_str is hello_literal}")
    interned = sys.intern(runtime_str)
    print(f"    sys.intern 后 is 'hello' = {interned is hello_literal}  -> 可以用来做快速比较")
    print("    -> 用驻留字符串做 == / is 比较，比内容比较快得多")


# ============================================================================
# 语法解析 2：索引与切片
# ============================================================================
# 【语法规则】
#   s[i]        取第 i 个字符；i 可以是负数，-1 表示最后一个
#   s[a:b]       取 [a, b) 左闭右开区间；负数表示从尾部计
#   s[a:b:step]  带步长；step 为负时【反向】遍历
#   越界切片【不报错】，直接返回可取到的部分；单元素越界才报 IndexError
# 【执行顺序】
#   切片 s[a:b:step] 由解释器调用 PySequence_GetSlice，
#   新建一个 str 并填充字符；无论是否取全量都不与原对象共享。
#   CPython 对全量切片做了优化（return self），因为 str 不可变，返回自己无风险。
# 【设计意图】
#   (1) 负索引是"倒数第 n 个"的自然表达，避免了 len(s)-1 的冗余计算；
#   (2) 左闭右开 [a, b) 与数学区间一致，且 b 有默认值 len(s) 时省略了上界；
#   (3) 切片对所有序列统一（str/list/tuple/range 都一样），降低学习成本；
#   (4) 切片永不越界报错，让"截取后缀"这类操作可以安全地写 s[:n]。
def demo_index_and_slice():
    print("[2] 索引与切片")

    s = "Python"

    # 单字符索引
    print(f"    s[0] = {s[0]!r}   s[-1] = {s[-1]!r}  (负索引从尾部计)")
    print(f"    len(s) = {len(s)}, s[-len(s)] == s[0] -> {s[-len(s)] == s[0]}")

    # 单元素越界 -> IndexError
    try:
        _ = s[10]
    except IndexError as e:
        print(f"    s[10]  ->  IndexError: {e}")

    # 切片越界 -> 不报错，静默截断
    print(f"    s[1:100] = {s[1:100]!r}   (切片不越界报错)")
    print(f"    s[:3]    = {s[:3]!r}      (省略起始 = 0)")
    print(f"    s[3:]    = {s[3:]!r}      (省略结束 = len(s))")
    print(f"    s[:]     = {s[:]!r}      (全量切片)")
    print(f"    s[::-1]  = {s[::-1]!r}    (步长 -1 = 反转)")
    print(f"    s[::2]   = {s[::2]!r}     (步长 2 = 隔一个取一个)")

    # 负索引与负步长的组合
    long_s = "abcdefghij"
    print(f"    {long_s!r}")
    print(f"    long_s[2:8]    = {long_s[2:8]!r}")
    print(f"    long_s[::2]    = {long_s[::2]!r}")
    print(f"    long_s[1::2]   = {long_s[1::2]!r}")
    print(f"    long_s[::-2]   = {long_s[::-2]!r}   (反向 + 步长)")
    print(f"    long_s[-3:]    = {long_s[-3:]!r}     (最后三个)")
    print(f"    long_s[:-3]    = {long_s[:-3]!r}     (去掉最后三个)")
    # 负结束索引 -3 指的是索引 7，所以不含 7
    print(f"    long_s[8:-3]   = {long_s[8:-3]!r}    (8 之后、-3(index 7) 之前 -> 空)")
    print(f"    long_s[2:-2]   = {long_s[2:-2]!r}    (掐头去尾)")

    # 切片返回新对象（但 CPython 全量切片会复用自身）
    part = s[2:]
    print(f"    s[2:] is s = {part is s}   -> 长度不同，必然是新对象")
    full = s[:]
    print(f"    s[:]  is s = {full is s}   -> CPython 对全量切片复用原对象(因不可变，安全)")

    # 切片的三种等价写法：s[a:b] 就是 s[a:b:1]，步长为 1 时可省略
    assert s[2:5] == s[2:5:1] == s[2:5:5 - 4]
    print("    s[2:5] == s[2:5:1] == s[2:5:5-4]  -> 三种写法完全等价（步长 1 可省略）")

    # 切片常用于"清理"数据
    raw = "   2024-01-15   "
    print(f"    strip 去空白 = {raw.strip()!r}")
    print(f"    strip()[0:10] 取日期 = {raw.strip()[0:10]!r}")
    # 路径/URL 截取
    path = "/user/profile/avatar.png"
    print(f"    路径去扩展名 = {path[: path.rfind('.')]!r}   (rfind 找最后一个点的位置)")


# ============================================================================
# 语法解析 3：转义字符、原始字符串与编码
# ============================================================================
# 【语法规则】
#   \n \t \r \\ \' \" \0 \b \f \v \a     常用转义
#   \x41 \u4f60 \U0001F600                十六进制 / Unicode 码位
#   \N{GREEK SMALL LETTER ALPHA}        Unicode 字符名（可读性更好）
#   \ddd                                八进制
#   r"..."                              原始字符串：除 \' 外所有转义失效
#   r"..." 只能以奇数个反斜杠结尾        因为结尾反斜杠会转义引号
#   'a' 'b'   相邻字面量在【编译期】拼接成一个字面量
#   '''...''' / """..."""  三引号多行字符串
# 【执行顺序】
#   转义在【词法分析】阶段处理：源码 -> token。
#   因此字符串字面量里不可能出现"未处理完的转义"。
#   相邻字面量拼接也在编译期完成，运行期零开销。
# 【设计意图】
#   原始字符串是为了正则表达式而生的：\d \w \s 在正则里有含义，
#   若不提供 r"" 就得写 "\\d"，正则表达式会变得无法阅读。
#   编码则解决了"文本到底是一串什么字符"的问题：
#   Python 3 的 str 内部是 Unicode（码位），bytes 才是字节序列，
#   两者转换必须显式声明编码，这消除了 Python 2 中 str/unicode 混用的噩梦。
def demo_escaping_and_encoding():
    print("[3] 转义字符与编码")

    # 常用转义
    print(f"    'a\\nb'       -> {chr(10).join(['a', 'b'])!r}   (\\n 换行)")
    print(f"    'a\\tb'       -> {'a\tb'!r}   (\\t 制表符)")
    print(f"    '\\x41'       -> {'\x41'!r}  (\\x41 = 十进制 65 = 'A')")
    print(f"    '\\u4f60\\u597d'  -> {'你好'!r}  (\\u 转义直接写出中文)")
    print(f"    '\\U0001F600' -> {'\U0001F600'!r}  (\\U 转义 emoji)")
    print(f"    字符码位 ord('中') = {ord('中')}, chr(0x4e2d) = {chr(0x4e2D)!r}")
    print(f"    码位转十六进制 = {ord('中'):#x}")

    # 原始字符串：正则表达式的刚需
    # 关键对比：普通字符串里 \d 会被当作"无效转义序列"处理（3.12+ 会发 SyntaxWarning），
    # 反斜杠实际上被丢弃，只剩下 'd'；原始字符串则逐字符原样保留。
    pattern_raw = r"\d+\.\d+"          # 正确：正则里 \d 是数字类，\. 是转义的点
    pattern_wrong = "\\d+\\.\\d+"      # 错误但能运行：每个反斜杠都要写两遍，可读性灾难
    print(f"    原始字符串 r'\\d+\\.\\d+'   = {pattern_raw!r}   <- 反斜杠原样保留")
    print(f"    普通字符串 '\\\\d+\\\\.\\\\d+' = {pattern_wrong!r}   <- 每个反斜杠写两遍")
    print(f"    两者值相等 = {pattern_raw == pattern_wrong}，但原始字符串可读性高得多")
    # 证明无效转义的实际后果。
    # 这里【故意】不写 "\d" 字面量：3.12+ 会对无效转义序列发 SyntaxWarning，
    # 而警告的成因正是我们要展示的现象 —— 反斜杠被静默丢弃。
    invalid_escape = chr(92) + chr(92) + "d"  # 用 "\\d" 的真实字符构造，避免自身触发警告
    print(f"    '\\\\d' 实际得到 = {invalid_escape!r}  长度={len(invalid_escape)} <- 反斜杠被丢弃了！")
    print(f"    r'\\d' 实际得到 = {r'\d'!r}  长度={len(r'\d')} <- 反斜杠完好无损")
    print("    -> 结论：写正则/Windows 路径/转义序列，一律用 r'' 前缀")
    print(f"    Windows 路径：r'C:\\Users\\test' = {r'C:\Users\test'!r}")

    # 原始字符串 r"..." 的陷阱：不能以【奇数个】反斜杠结尾。
    # 因为收尾的那个反斜杠会把结束引号转义掉，导致引号不闭合。
    #   r"abc\"   -> 编译期直接 SyntaxError，无法用 try/except 捕获！
    # 这是词法分析阶段就失败的问题，代码根本不会进入运行期。
    # 正确做法：写成 "abc\\"（普通字符串，两个反斜杠）或 r"abc" + "\\"
    print(f"    普通字符串 'abc\\\\'   = {'abc' + chr(92)!r}   (两个反斜杠，合法)")
    print("    r'abc\\'  ->  编译期 SyntaxError（反斜杠转义掉了引号，连运行期都到不了）")
    print("    注意：这类错误 try/except 捕获不到，因为解析阶段整个模块就加载失败了")

    # 相邻字面量在编译期拼接
    s_concat = "Hello" " " "World"
    print(f"    'Hello' ' ' 'World' = {s_concat!r}   (编译期拼接，运行期无 + 开销)")
    print(f"    'Hel' + 'lo' == 'Hello' = {'Hel' + 'lo' == 'Hello'}   (运行期拼接，值相同)")

    # 三引号多行字符串
    text = """第一行
第二行
    第三行(保留缩进)
"""
    print(f"    三引号字符串行数 = {len(text.splitlines())}")
    print("    -> 多行字符串保留换行与缩进，常用于文档字符串/模板")

    # 编码：Unicode 码位 <-> 字节序列
    ch = "中"
    print(f"    '中' 的 Unicode 码位 = U+{ord(ch):04X}，字符数 = 1")
    for enc in ("utf-8", "gbk", "latin-1"):
        try:
            data = ch.encode(enc)
            # len(data) 是字节数，不是字符数 —— 这是编码最核心的差异
            print(
                f"    '{ch}'.encode({enc:<8}) = {data!r:<20} "
                f"字节数={len(data)}  还原={data.decode(enc)!r}"
            )
        except UnicodeEncodeError as e:
            print(f"    '{ch}'.encode({enc:<8}) -> UnicodeEncodeError（该编码不支持此字符）")

    # gb2312 不支持某些字符
    try:
        _ = "😀".encode("gbk")
    except UnicodeEncodeError as e:
        print(f"    '😀'.encode('gbk') -> UnicodeEncodeError: {str(e).splitlines()[0]}")

    # 编码往返：encode 再 decode 必须无损
    original = "Hello 世界 🌍"
    utf8_bytes = original.encode("utf-8")
    restored = utf8_bytes.decode("utf-8")
    print(f"    往返一致性 = {original == restored}   (encode/decode 可逆)")
    print(f"    原串 {len(original)} 个字符 <-> {len(utf8_bytes)} 字节  <- 长度不同才是正常的")

    # 常见编码标识
    print("    常用编码：utf-8(通用) / gbk(简体中文Windows) / latin-1(西欧) / ascii(仅英文)")
    print(f"    sys.getdefaultencoding() = {sys.getdefaultencoding()}  (str 内部编码)")
    print(f"    sys.stdout.encoding = {sys.stdout.encoding}  <- 控制台/IO 用它")
    print(f"    sys.getfilesystemencoding() = {sys.getfilesystemencoding()}  (文件名用)")


# ============================================================================
# 语法解析 4：str 与 bytes
# ============================================================================
# 【语法规则】
#   str    文本序列，元素是 1 个字符（码位），内部是 Unicode
#   bytes  字节序列，元素是 0..255 的整数
#   str 与 bytes 是【不同类型】，不能混用 + 或比较：
#       'a' + b'a'   -> TypeError
#       'a' == b'a'  -> False（连比较都直接为 False 而不报错）
#   转换：str.encode(enc) -> bytes；bytes.decode(enc) -> str
#   bytes 支持切片，返回 bytes；b'a'[0] 得到整数 97 而不是 'a'
# 【执行顺序】
#   bytes 索引取到的是 int，因为字节就是 0-255 的数，没有"字符"概念。
#   要看字符需 bytes.decode() 或用 .hex()。
# 【设计意图】
#   Python 3 把"文本"和"数据"在类型层面彻底分开，是为了消除 Python 2 的经典 bug：
#   在 Py2 里 str 既能当字节又能当文本，编码转换靠隐式 decode，
#   结果就是程序在不同机器上乱码。
#   Py3 强制你声明意图：处理文本用 str，处理协议/文件用 bytes，
#   边界处显式 encode/decode，从根上杜绝了乱码。
def demo_str_vs_bytes():
    print("[4] str 与 bytes")

    text = "中文"
    data = text.encode("utf-8")

    print(f"    text = {text!r}, type = {type(text).__name__}, 长度 = {len(text)}")
    print(f"    data = {data!r}, type = {type(data).__name__}, 长度 = {len(data)}")
    print(f"    同一内容，长度不同：{len(text)} 字符 != {len(data)} 字节")

    # 类型不同，元素也不同
    print(f"    text[0] = {text[0]!r}       (字符 str)")
    print(f"    data[0] = {data[0]}          (字节 int，97 == ord('a'))")
    print(f"    type(data[0]) = {type(data[0]).__name__}")

    # 不能混用
    try:
        _ = text + data
    except TypeError as e:
        print(f"    text + data -> TypeError: {e}")
    print(f"    text == data = {text == data}   (不同类型比较直接 False，不报错)")

    # bytes 的常用方法
    print(f"    data.hex() = {data.hex()}    (十六进制，看不清内容时用)")
    print(f"    data.decode('utf-8') = {data.decode('utf-8')!r}   (唯一的逆操作)")

    # 解码错误处理：strict / ignore / replace 三种策略
    # 注意 bytes.decode 的 errors 是【仅限位置参数】，
    # 必须写 decode("utf-8", errors=...)；若写成 decode("utf-8", "replace")
    # 会被当成第二个编码参数，抛 TypeError。
    bad = b"\xff\xfe abc"
    for err in ("strict", "ignore", "replace"):
        if err == "strict":
            try:
                result = bad.decode("utf-8", errors=err)
            except UnicodeDecodeError:
                print(f"    b'\\xff\\xfe abc'.decode(errors={err!r:<10}) -> UnicodeDecodeError（严格模式直接抛错）")
                continue
        else:
            result = bad.decode("utf-8", errors=err)
        print(f"    b'\\xff\\xfe abc'.decode(errors={err!r:<10}) = {result!r}")

    # bytes 构造：网络/协议/二进制数据
    print(f"    bytes('中', 'utf-8')  = {bytes('中', 'utf-8')!r}   (指定编码)")
    print(f"    bytes([104, 105])    = {bytes([104, 105])!r}      (从码位数组)")
    print(f"    bytes(5)             = {bytes(5)!r}             (N 个零字节，用于预分配缓冲区)")
    print("    -> bytes(5) 预分配缓冲是高性能网络编程的常用手法")

    # 文本模式 vs 二进制模式的 IO 差异
    import io

    text_io = io.StringIO("中文")
    bin_io = io.BytesIO("中文".encode("utf-8"))
    print(f"    StringIO 读出  = {text_io.read()!r}  (文本流，读出 str)")
    print(f"    BytesIO  读出  = {bin_io.read()!r}  (二进制流，读出 bytes)")
    print("    -> 打开文件时 open(f,'r') 是文本，open(f,'rb') 是二进制，务必对应")


# ============================================================================
# 语法解析 5：字符串常用方法全览
# ============================================================================
# 【语法规则】
#   大小写：upper() lower() title() capitalize() casefold() swapcase()
#            casefold 用于大小写不敏感比较（比 lower 更彻底：处理 ß → ss）
#   查询  ：find 返回索引或 -1；index 返回索引，找不到抛 ValueError
#            count 计数；startswith/endswith 支持元组：startswith(('a','b'))
#   判断  ：isdigit isalpha isalnum isspace isupper islower istitle
#            注意 "12.3".isdigit() 为 False（含小数点）
#   操作  ：strip 去掉两端字符（默认空白，也可传字符集）
#            replace(a,b,n) n 可指定替换次数；replace 不改变原串
#            split(sep) 分割成列表；split(None) 按任意空白分割并丢弃空串
#            splitlines() 按行分割且不保留换行符
#            join 拼接：sep.join(可迭代对象)，sep 通常用 ''
#            center/ljust/rjust/expandtabs/zfill 对齐
#            removeprefix/removesuffix 是 3.9+ 的新方法
# 【执行顺序】
#   str 的绝大多数方法都不修改自身，而是返回新对象（因不可变）。
#   split 返回 list，join 需要所有元素都是 str，否则报 TypeError。
# 【设计意图】
#   方法全部以动词命名并返回新值，强化了"字符串是值类型"的直觉。
#   find 与 index 的双轨设计（返回 -1 vs 抛异常）同样延续了
#   "EAFP（易安于浮舟难于溺死）" 与 "LBYL" 两种错误处理哲学的对立，
#   让调用方自己选择。
def demo_string_methods():
    print("[5] 字符串常用方法")

    s = "  Hello Python World  "
    print(f"    演示字符串 = {s!r}\n")

    # ---- 大小写类 ----
    print("    [大小写]")
    print(f"    upper()      = {s.upper()!r}")
    print(f"    lower()      = {s.lower()!r}")
    print(f"    title()      = {'hello python'.title()!r}   (每个单词首字母大写)")
    print(f"    capitalize() = {'HELLO python'.capitalize()!r}   (整串首字母大写)")
    print(f"    swapcase()   = {'Hello'.swapcase()!r}")
    # casefold：做大小写不敏感比较的正确方式
    print(f"    'Straße'.lower()   = {'Straße'.lower()!r}   (长度 {len('Straße'.lower())})")
    print(f"    'Straße'.casefold() = {'Straße'.casefold()!r}   (长度 {len('Straße'.casefold())})")
    print(f"    'Straße'.lower() == 'STRASSE' -> {'Straße'.lower() == 'STRASSE'}")
    print(f"    'Straße'.casefold() == 'STRASSE' -> {'Straße'.casefold() == 'STRASSE'}  <- 推荐")

    # ---- 查询类 ----
    print("\n    [查询]")
    text = "Python is fun, Python is powerful"
    print(f"    find('Python')      = {text.find('Python')}    (第一次出现的位置)")
    print(f"    rfind('Python')     = {text.rfind('Python')}   (最后一次出现的位置)")
    print(f"    count('Python')     = {text.count('Python')}   (出现次数)")
    print(f"    find('Java')        = {text.find('Java')}    (找不到返回 -1，不抛异常)")
    try:
        _ = text.index("Java")
    except ValueError as e:
        print(f"    index('Java')       ->  ValueError: {e}   (找不到抛异常)")
    print(f"    startswith(('Py','Ja')) = {text.startswith(('Py', 'Ja'))}  (元组：任一匹配即可)")

    print("\n    [判断]")
    for value in ("123", "abc", "abc123", "12.3", "  ", "Python", "PYTHON"):
        print(
            f"    {value!r:<10} isdigit={value.isdigit()!s:<6} isalpha={value.isalpha()!s:<6} "
            f"isalnum={value.isalnum()!s:<6} isspace={value.isspace()!s:<6} isupper={value.isupper()}"
        )
    print(f"    '12.3'.isdigit() = {'12.3'.isdigit()}  <- 含小数点所以为 False，做数字校验要小心")
    print(f"    '中'.isascii() = {'中'.isascii()}  isalpha() = {'中'.isalpha()}  <- 中文也算字母")
    print(f"    '_a1'.isidentifier() = {'_a1'.isidentifier()}  (合法的变量名)")
    print(f"    'ab'.isprintable() = {'ab'.isprintable()}  '\\n'.isprintable() = {'\\n'.isprintable()}")

    # ---- 操作类 ----
    print("\n    [操作]")
    raw = "  aabbccaa  "
    print(f"    strip()        = {raw.strip()!r}")
    print(f"    strip('a')     = {raw.strip('a')!r}   (传字符集，去掉两端的所有 a)")
    print(f"    lstrip/rstrip  = {raw.lstrip()!r} / {raw.rstrip()!r}")
    print(f"    replace('a','X')    = {raw.replace('a', 'X')!r}   (替换全部)")
    print(f"    replace('a','X',2)  = {raw.replace('a', 'X', 2)!r}   (只替换 2 次)")
    print(f"    'ab'.removeprefix('a') = {'ab'.removeprefix('a')!r}  (3.9+，去掉前缀，无则返回原串)")

    print("\n    [分割与拼接]")
    csv_line = "name,age,city"
    print(f"    split(',')     = {csv_line.split(',')}   (保留分隔符语义)")
    print(f"    'a  b   c'.split() = {'a  b   c'.split()}   (sep=None：按任意空白，且丢弃空串)")
    print(f"    'a,,b'.split(',') = {'a,,b'.split(',')}   (sep 明确：保留空串)")
    print(f"    'a,b,c'.split(',',1) = {'a,b,c'.split(',', 1)}   (maxsplit 限制次数)")
    print(f"    'a\\nb\\nc'.splitlines() = {'a\nb\nc'.splitlines()}   (不保留 \\n)")
    # join：把列表拼成字符串，高效的唯一正解
    parts = ["Python", "is", "great"]
    print(f"    ''.join({parts}) = {' '.join(parts)!r}   (注意顺序：分隔符.join(列表))")

    print("\n    [对齐与填充]")
    print(f"    'ab'.center(8,'*') = {'ab'.center(8, '*')!r}")
    print(f"    'ab'.ljust(8,'.')   = {'ab'.ljust(8, '.')!r}")
    print(f"    'ab'.rjust(8,'.')   = {'ab'.rjust(8, '.')!r}")
    print(f"    '42'.zfill(5)       = {'42'.zfill(5)!r}   (补零，生成/校验码常用)")
    print(f"    'a\\tb'.expandtabs(4) = {'a\tb'.expandtabs(4)!r}   (制表符对齐输出)")
    # 对齐输出的实用组合（比 f-string 的 :>10 更灵活时用）
    rows = [("姓名", 3), ("Alice", 5), ("Bob", 10)]
    print("    对齐表格：")
    for k, v in rows:
        print(f"      {k:<10}| {v:>6}")

    # ---- 常见坑 ----
    print("\n    [常见坑]")
    # join 要求所有元素是 str
    try:
        _ = ",".join(["a", 1])
    except TypeError as e:
        print(f"    ','.join(['a',1]) -> TypeError: {e}")
    print(f"    ','.join(map(str, ['a',1])) = {','.join(map(str, ['a', 1]))!r}  <- 先转 str")
    # empty separator + empty list
    print(f"    ''.join([]) = {''.join([])!r}  (空列表拼接为空串，不报错)")
    # 字符串是序列，支持 in / 索引，但不可哈希性问题不存在（str 可哈希）


# ============================================================================
# 语法解析 6：三种格式化方式对比
# ============================================================================
# 【语法规则】
#   1)  % 格式化（printf 风格，C 遗留）
#       "%s-%s" % (a, b)         占位符：%s %d %f %.2f %x %%r
#       "%(name)s" % {"name":x}  映射式：可读性更好
#       参数为 dict/元组时括号不能省
#   2)  .format() 方法
#       "{}".format(a)           自动编号 0,1,2
#       "{0}-{1}".format(a,b)    手动编号，可重复使用
#       "{name}".format(name=x)  关键字混用
#       "{:.2f}".format(x)       格式说明符写在花括号内
#   3)  f-string（3.6+，当前最佳）
#       f"{a}-{b}"              直接插值
#       f"{x:.2f}"              格式说明符
#       f"{x:,}"                千分位
#       f"{x!r}"                转 repr
#       f"{x=}"                 连同表达式文本一起输出
# 【执行顺序】
#   f-string 在编译期被解析：花括号内的表达式被编译成真实表达式，
#   格式说明符在运行期由 FORMAT_VALUE 指令处理。
#   因此 f-string 不能使用反斜杠（3.12 前）与空白的表达式部分，
#   但整体仍快于 .format 和 %。
# 【设计意图】
#   三代格式化的演进方向是"逐步减少样板代码、增加可读性、保证正确性"：
#     %  →  参数需转义 % → .format → 括号与参数可能错位 → f-string → 表达式即代码
#   f-string 的杀手锏是能在字符串里写【任意表达式】，甚至调用函数，
#   这是 .format 和 % 做不到的。
def demo_formatting():
    print("[6] 三种格式化方式对比")

    name, age, score, price = "张三", 28, 92.456, 1234567.891

    print("    [方式1] % 格式化（printf 风格）")
    # 单个值时元组括号可省略；多个值必须用元组
    print(f"      '姓名：%s，年龄：%d'  -> {'姓名：%s，年龄：%d' % (name, age)}")
    print(f"      '%.2f'                -> {'%.2f' % score}   (保留 2 位小数)")
    print(f"      '%5s' 左对齐补空格      -> {'[%5s]' % name}")
    print(f"      '%-5s' 右对齐           -> {'[%-5s]' % name}")
    print(f"      '%05d' 补零            -> {'[%05d]' % 42}   (学号/编号)")
    print(f"      '%x' / '%o'            -> {'%x' % 255} / {'%o' % 8}   (十六/八进制)")
    print(f"      '%e' 科学计数          -> {'%.3e' % 12345.6789}")
    # 注意：% 格式化【不支持千分位】，%,.2f 是非法的（ValueError）
    try:
        _ = "%,.2f" % price
    except ValueError as e:
        print(f"      '%,.2f' -> ValueError: {e}   <- % 不支持千分位，要用 f'{price:,.2f}'")
    print(f"      千分位正确写法 -> f'{{price:,.2f}}' = {f'{price:,.2f}'}   (.format/f-string 才支持)")
    # 映射式：可读性最好的一种 %
    print(f"      映射式 -> {'%(name)s 的年龄是 %(age)d' % {'name': name, 'age': age}}")
    print("      -> % 的坑：字面量里的 % 必须写成 %% ，否则报错")
    try:
        _ = "完成率 100%" % 0.8
    except ValueError as e:
        print(f"      '完成率 100%' % 0.8 -> ValueError: {e}   (100% 被当成占位符了)")
        print(f"      正确写法 = {'完成率 %.0f%%' % 80}   <- 百分号要写成 %%")

    print("\n    [方式2] .format()")
    print(f"      自动编号  -> {'{}-{}'.format(name, age)}")
    print(f"      手动编号（可重复）-> {'{0}-{0}-{1}'.format(name, age)}")
    print(f"      关键字    -> {'{n}的年龄是{a}'.format(n=name, a=age)}")
    print(f"      格式说明符-> {'{:.2f}'.format(score)} / {'{:,}'.format(price)}")
    print(f"      对齐      -> {'[{:>8}]'.format(name)} / {'[{:<8}]'.format(name)} / {'[{:^8}]'.format(name)}")
    # .format 最著名的问题：占位符与参数顺序易错
    try:
        _ = "{} {}".format(name)
    except IndexError as e:
        print(f"      占位符多于参数 -> IndexError: {e}   <- 运行时才发现，最易踩坑")
    print(f"      多余参数是允许的 -> {'{name}'.format(name=name, unused=1)!r}   (只是被忽略)")

    print("\n    [方式3] f-string（推荐）")
    print(f"      基础      -> f'{{name}}的年龄是{{age}}' = {f'{name}的年龄是{age}'}")
    print(f"      格式说明符 -> f'{{score:.2f}}' = {f'{score:.2f}'}")
    print(f"      千分位    -> f'{{price:,}}'  = {f'{price:,}'}")
    print(f"      对齐      -> f'[{{name:>8}}]' = {[f'{name:>8}']} / f'[{{name:<8}}]' = {[f'{name:<8}']}")
    # f-string 的独有能力：{x=} 把【表达式本身】也一起输出
    sample = "Python"
    print(f"      自解释    -> f'{{len(sample)=}}' = {f'{len(sample)=}'.strip()}")
    # 转换标志
    print(f"      !r        -> {f'{name!r}'}   (转 repr，能看到引号)")
    print(f"      !s        -> {f'{name!s}'}   (转 str)")
    print(f"      !a        -> {f'{name!a}'}   (转 ascii)")
    # f-string 里可以写任意表达式，包括函数调用和运算
    data = [3, 1, 2]
    print(f"      内嵌表达式 -> f'{{sorted(data)}}' = {f'{sorted(data)}'}")
    print(f"      内嵌运算   -> f'{{len(data)*2}}'  = {f'{len(data) * 2}'}")
    # 格式说明符的动态宽度：嵌套 f-string (3.12 前后语法有别，这里用经典写法)
    width = 10
    print(f"      动态宽度   -> f'{{name:>{width}}}' = {[f'{name:>{width}}']}")
    # 调试 f-string：3.8+ 的自省利器
    dbg = f"{score=}"
    print(f"      调试用法   -> {dbg}   (3.8+，等于 f'score={score}' 的简写)")
    # 多行 f-string
    multi = f"""
    姓名：{name}
    成绩：{score:.1f}
    """
    print(f"      多行 f-string 行数 = {len(multi.splitlines())}")

    print("\n    [同结果对比]")
    line1 = "姓名：%s，成绩：%.1f" % (name, score)
    line2 = "姓名：{}，成绩：{:.1f}".format(name, score)
    line3 = f"姓名：{name}，成绩：{score:.1f}"
    print(f"      %       -> {line1}")
    print(f"      format  -> {line2}")
    print(f"      f-string-> {line3}")
    print(f"      三者结果相同 = {line1 == line2 == line3}")

    print("\n    [性能实测 timeit：格式化方式对比]")
    setup_str = "name='张三'; score=92.456"
    n = 200_000
    cases = [
        # 四组必须产出完全相同的字符串，否则性能对比毫无意义（下面用 assert 钉死）
        ("%-格式化", "'姓名：%s，成绩：%.1f' % (name, score)"),
        ("%-映射式", "'姓名：%(n)s，成绩：%(s).1f' % {'n': name, 's': score}"),
        (".format()", "'姓名：{}，成绩：{:.1f}'.format(name, score)"),
        ("f-string", "f'姓名：{name}，成绩：{score:.1f}'"),
        # 对照组：不做任何格式化，只做字符串拼接。
        # 注意它【与上面几组不可比】—— 因为它根本没插入第二个值，
        # 少了一整个 FORMAT_VALUE 操作。它只用于说明"拼接本身有多便宜"。
        ("裸拼接(不可比)", "'姓名：' + name"),
    ]
    # 所有 case 都必须产出【同样的字符串】，否则性能对比不成立。
    # 这里用断言把这一点钉死，避免出现"比了个寂寞"的基准测试。
    for label, stmt in cases:
        if label.startswith("裸拼接"):
            continue
        assert eval(stmt, {"name": name, "score": score}) == line3, f"{label} 结果不一致"
    print(f"      数据量 n={n:,}，重复 {n:,} 次（所有方案输出相同字符串，已断言校验）：")
    # 先全部跑完，再统一打印 —— 否则归一化基准（如 .format()）在首轮还没测出来
    results = {label: timeit.timeit(stmt, setup=setup_str, number=n) for label, stmt in cases}
    baseline = results[".format()"]  # 以 .format() 为 1.00x 基准
    print(f"      {'方式':<16}{'总耗时(s)':>10}{'单次(μs)':>10}   相对速度")
    for label, t in results.items():
        print(f"      {label:<16}{t:>10.4f}{t / n * 1e6:>10.3f}   {baseline / t:>5.2f}x")
    fmt_labels = ("%-格式化", "%-映射式", ".format()", "f-string")
    print(f"      -> 四种格式化中最快：{min(fmt_labels, key=results.get)}，"
          f"最慢：{max(fmt_labels, key=results.get)}，"
          f"相差 {results[max(fmt_labels, key=results.get)] / results[min(fmt_labels, key=results.get)]:.2f} 倍")
    print("      -> 结论：四种方式差距其实不大（同一量级）。f-string 略快是因为编译器把它翻译为")
    print("         FORMAT_VALUE 字节码并省去 % 的参数元组打包；但选它的首要理由是可读性，不是速度。")
    print("      -> 裸拼接那一行【不可比】：它只插入 1 个值，少一次取整与类型转换，纯粹是陪跑对照。")


# ============================================================================
# 语法解析 7：常用实战场景
# ============================================================================
# 【语法规则】
#   场景化组合：
#     CSV 解析  split(',') + strip()
#     键值对    split(':', 1)  —— maxsplit=1 保住值里的冒号(如 URL)
#     URL 构造  f-string + urlencode 的思路（手写版，不引第三方）
#     日志      f-string / %，注意不要用 + 反复拼接
#     脱敏      切片 s[:3] + '*' * (len(s)-3)
#     对齐      f'{v:>8}' 或 ljust
#     路径      rsplit('/', 1)
# 【执行顺序】
#   组合多个方法时的顺序至关重要：
#   先 strip 去空白，再 split 分割，最后逐项 strip —— 否则分隔符周围
#   的空格会成为分割结果的一部分。
# 【设计意图】
#   这些是 90% 真实业务代码里 str 的用法。掌握它们比背方法列表更重要，
#   关键在于"选对方法"和"注意顺序"。
def demo_real_world():
    print("[7] 常用实战场景")

    # ---- CSV 解析 ----
    print("    [场景1] 解析 CSV 行")
    line = "Alice, 28, Beijing"
    # 顺序至关重要：先 split 再逐项 strip，而不是先 strip 整个串
    fields = [f.strip() for f in line.split(",")]
    print(f"      {line!r}")
    print(f"      解析结果 = {fields}  (顺序：先 split 再逐项 strip)")

    # 带引号的 CSV 场景（引号内含逗号）—— 手写解析器
    tricky = 'name="张,三",age=28'
    print(f"      复杂行 {tricky!r}")
    print(f"      split(': ',1) 演示 -> {'a:b:c'.split(':', 1)}   (maxsplit=1 保住后面的冒号)")
    print("      -> 真实 CSV 含引号/换行时必须用 csv 模块，手写 split 会出错")

    # ---- 键值对解析 ----
    print("\n    [场景2] 解析 key=value 串")
    kv_str = "host=localhost:8080;timeout=30"
    config = {}
    for pair in kv_str.split(";"):
        k, _, v = pair.partition("=")  # partition 比 split 更安全：sep 找不到不抛异常
        config[k] = v
    print(f"      {kv_str!r} -> {config}")
    print("      -> partition(sep) 返回三元组，不含 sep 时返回 (整串,'','')，不会抛异常")

    # ---- URL 构造与解析 ----
    print("\n    [场景3] URL 构造与查询参数")
    base, host, page = "https://example.com", "api.example.com", 2
    url = f"{base}//{host}/search?q=python&page={page}"
    print(f"      URL = {url}")
    # 解析 query string
    query = url.split("?", 1)[1]
    params = dict(p.split("=", 1) for p in query.split("&"))
    print(f"      解析 = {params}")
    print("      -> split('?',1) 与 split('=',1) 的 maxsplit=1 是解析的标配")

    # ---- 日志拼接 ----
    print("\n    [场景4] 日志消息")
    user, action, cost = "alice", "下单", 15.5
    # 错误写法：+ 反复拼接，每次都新建字符串
    # 正确写法：f-string 一次成型，或用 % 交给日志框架惰性格式化
    print(f"      f-string  = f'用户[{user}]执行[{action}]，耗时{cost:.2f}秒'")
    print(f"        -> {f'用户[{user}]执行[{action}]，耗时{cost:.2f}秒'}")
    print("      -> 生产环境应交给 logging 用 %s 惰性格式化，参数不格式化就不付代价：")
    print(f'         logger.info("用户[%s]执行[%s]，耗时%.2f秒", user, action, cost)')

    # ---- 脱敏 ----
    print("\n    [场景5] 敏感信息脱敏")
    phone, card = "13812345678", "6222021234567890123"
    masked_phone = phone[:3] + "*" * (len(phone) - 7) + phone[-4:]
    masked_card = card[:4] + "*" * (len(card) - 8) + card[-4:]
    print(f"      手机 {phone} -> {masked_phone}")
    print(f"      银行卡 {card} -> {masked_card}")
    print(f"      通用邮箱脱敏 -> {'zhangsan@example.com'.split('@')[0][:1] + '***' + '@example.com'}")
    print("      -> 切片 + 字符串乘法 '*' * n 是脱敏的标准写法")

    # ---- 路径处理 ----
    print("\n    [场景6] 路径处理（不依赖 pathlib，纯 str）")
    file_path = "/home/user/docs/report.2024.pdf"
    dir_part, _, filename = file_path.rpartition("/")
    name, _, ext = filename.rpartition(".")
    print(f"      路径 = {file_path}")
    print(f"      目录 = {dir_part!r}，文件名 = {filename!r}")
    print(f"      主名 = {name!r}，扩展名 = {ext!r}")
    print("      -> rpartition 从右往左分割一次，正是路径/扩展名拆分惯用法")

    # ---- 多行文本统计 ----
    print("\n    [场景7] 简易文本统计")
    article = """Python 是一门优雅的语言。
Python 的容器类型丰富。
学习 Python 从容器开始。"""
    lines = article.splitlines()
    print(f"      行数 = {len(lines)}")
    print(f"      含'Python'的行数 = {sum('Python' in ln for ln in lines)}")
    print(f"      去重单词数 = {len({w for ln in lines for w in ln.split()})}")
    print("      -> 嵌套推导式 + splitlines 是文本处理的基本功")

    # ---- 字符串驻留加速比较 ----
    print("\n    [场景8] 用驻留加速高频比较")
    tokens = ["if", "elif", "else"]
    interned = {sys.intern(t) for t in tokens}
    print(f"      驻留后 {'if' in interned}，基于身份比较，比基于内容比较快")
    print("      -> JSON 解析、词法分析等热点循环中，sys.intern 能带来可观提速")


def main():
    demo_immutability()
    demo_index_and_slice()
    demo_escaping_and_encoding()
    demo_str_vs_bytes()
    demo_string_methods()
    demo_formatting()
    demo_real_world()
    print("[完成] 02_basics/03_strings.py 运行结束")


if __name__ == "__main__":
    main()