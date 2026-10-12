r"""
================================================================================
 08_re.py  ——  re：正则表达式
================================================================================

【说明】本文件的模块文档字符串使用「原始字符串」前缀（r 加三引号）：
       因为文中大量出现 \d \w \s 等正则记号，若用普通字符串，
       Python 3.12+ 会对 \d \s 等发出 SyntaxWarning（无效转义序列）。
       原始字符串让所有反斜杠按字面展示，同时消除警告。

【演示的语法点】
 1. 元字符全表：. ^ $ * + ? {m,n} [] () | 反斜杠 与转义
 2. 字符类与预定义类：\d \w \s \D \W \S 与 [^...] 取反
 3. 量词：贪婪 * + ? {m,n} vs 非贪婪 *? +? ?? {m,n}?（★核心易错点）
 4. 分组捕获：( ) 编号组、非捕获组 (?: )、命名组 (?P<name> )
 5. 反向引用 \1 \2 与条件、lookahead (?= ) (?! )、lookbehind (?<= ) (?<! )
 6. re.compile：把模式编译成 Pattern 对象复用（★循环中必须提前编译）
 7. flags：IGNORECASE / DOTALL / MULTILINE / VERBOSE / UNICODE
 8. 六个查找函数区别：match / search / fullmatch / findall / finditer / sub
 9. sub 与 subn：替换、函数式替换、用分组做模板
10. 实战提取：邮箱 / URL / 日期 / 手机号 / HTML 标签清理
11. ★ re 方法与 str 方法的性能对比（timeit 计时）
12. 编译期报错 re.error，以及 flags 在 pattern 上的状态

【预期输出摘要】
 - "元字符" 小节：逐个字符对同一字符串做匹配演示
 - "量词" 小节：<div><p> 文本在贪婪/非贪婪下切出的不同结果
 - "查找函数" 小节：同一个模式在 match/search/findall 下的对比
 - "实战" 小节：从一段混合文本中抽出 邮箱/URL/日期/手机号
 - "性能" 小节：re.sub 明显慢于 str.replace 的倍数
 - "编译" 小节：re.error 的报错信息与 flags 生效状态
================================================================================

"""

import re
import sys
import timeit

# ===== 语法解析 =====
# 【re 模块的两种用法】
#   方式一（一次性）：re.sub(pattern, repl, text)   —— 内部每次都重新编译
#   方式二（复用型）：pat = re.compile(pattern); pat.sub(...)  —— 只编译一次
#   判定标准：同一个 pattern 被用【多次】就应当 compile，
#             因为编译（把文本转成状态机）比匹配本身更耗时。


# ===== 语法解析 =====
# 【1】元字符全表 —— 正则的"单词表"
#   语法规则（. 不在字符类内时的含义）：
#     .        任意字符（默认【不含】换行符 \n，re.DOTALL 可改变）
#     ^        锚点：行首（字符串开头，或 MULTILINE 下的每行开头）
#     $        锚点：行尾（字符串结尾，或 MULTILINE 下的每行结尾）
#     *        量词：前一项重复 0 次或多次（贪婪）
#     +        量词：前一项重复 1 次或多次（贪婪）
#     ?        量词：前一项重复 0 次或 1 次（贪婪）
#     {m,n}    量词：前一项重复 m 到 n 次（m 省略=0，n 省略=无穷）
#     []        字符类：匹配方括号内任意一个字符
#     ()        分组：既是"括号内的整体"，又是"捕获组"
#     |        或：左右两侧任选其一（优先级【最低】，等价于 (左|右)）
#     \        转义：把元字符还原成普通字符，或引入 \d \w 等简写
#   设计意图：正则本质是一个【迷你语言】，
#             元字符相当于这个语言的运算符，字符类相当于它的字面量。
def demo_metacharacters() -> None:
    print("=" * 74)
    print("【1】元字符全表")
    print("=" * 74)

    text = "abc123"

    # . 任意字符（不含换行）
    print("①  .  匹配任意一个字符")
    print(f"   re.sub(r'.', '*', 'abc')     → {re.sub(r'.', '*', 'abc')!r}")
    print("   为什么这么写：'.' 不是普通点，是元字符，要匹配字面量点需写 r'\\.'")

    # ^ $ 行首行尾锚点
    print("\n②  ^  $  锚点（位置断言，零宽度，不消耗字符）")
    for pat in (r"^abc", r"abc$", r"^abc$"):
        print(f"   {pat:<8} search → {re.search(pat, text)}")

    # * + ? 量词：作用于【紧挨着的前一项】
    print("\n③  * + ?  量词（作用于前一项，可重复的部分）")
    for pat, s in ((r"a*", "aaab"), (r"a+", "aaab"), (r"ab?", "aab")):
        print(f"   {pat:<6} on {s!r:<8} findall → {re.findall(pat, s)!r}")
    print("   为什么这么写：量词只管前一个字符，'a+' 是匹配 aaa，不是 a+a+")

    # {m,n} 精确次数
    print("\n④  {m,n}  精确次数区间（最常用的量词）")
    for pat in (r"a{2}", r"a{2,}", r"a{2,3}"):
        print(f"   {pat:<8} findall on 'aaaa' → {re.findall(pat, 'aaaa')!r}")

    # [] 字符类
    print("\n⑤  [ ]  字符类（一次只匹配一个字符）")
    print(f"   [aeiou]     findall on 'education' → {re.findall(r'[aeiou]', 'education')!r}")
    print(f"   [0-9a-f]    findall on '0x9f 0xzz' → {re.findall(r'[0-9a-f]+', '0x9f 0xzz')!r}")
    print("   为什么这么写：'-' 放中间是范围符，放首位是字面量 '-'")

    # | 或
    print("\n⑥  |  逻辑或（优先级最低，需要分组时才用括号加优先级）")
    print(f"   'cat|dog'   findall → {re.findall(r'cat|dog', 'cat and dog')!r}")
    print(f"   'cat|dog'   match  → {re.match(r'cat|dog', 'dogcat')}")
    print("   为什么：match 只从【开头】找，开头是 dog 才成功，cat 被丢弃")

    # \ 转义
    print("\n⑦  \\  转义（把元字符变回字面量）")
    price = "价格是 19.99 元"
    print(f"   r'\\d+\\.\\d+'  匹配小数 → {re.findall(r'\\d+\\.\\d+', price)!r}")
    print(f"   若误写成 r'\\d+.\\d+' 会贪婪多吞 → {re.findall(r'\\d+.\\d+', price)!r}")
    print("   为什么这么写：正则中 '.' 天然贪婪，匹配字面量点必须转义成 '\\.'")

    # 预定义字符类
    print("\n⑧  预定义字符类：\\d \\w \\s 与大写取反形式")
    print(f"   \\d 数字      findall on 'a1b2'      → {re.findall(r'\\d', 'a1b2')!r}")
    print(f"   \\w 单词字符  findall on 'a_1 中文'  → {re.findall(r'\\w', 'a_1')!r}（中文属 \\w）")
    print(f"   \\s 空白字符  findall on 'a b\\tc'    → {re.findall(r'\\s', 'a b\\tc')!r}")
    print(f"   \\D 非数字    findall on 'a1b2'      → {re.findall(r'\\D', 'a1b2')!r}")
    print(f"   \\S 非空白    findall on 'a b\\tc'    → {re.findall(r'\\S', 'a b\\tc')!r}")


# ===== 语法解析 =====
# 【2】贪婪 vs 非贪婪 —— Python 正则最容易踩的坑
#   语法规则：在量词后面再加一个 ?，即变成"懒惰/非贪婪"模式
#     *   贪婪：尽可能多匹配      *?  非贪婪：尽可能少匹配
#     +   贪婪                    +?
#     ?   贪婪                    ??
#     {m,n} 贪婪                  {m,n}?
#   执行顺序：正则引擎【默认贪婪】，先吃到不能再吃；
#             整体匹配失败时才回溯（backtracking）缩短。
#   设计意图：让同一个模式在"要多的"和"要少的"场景下只差一个字符。
def demo_greedy_vs_lazy() -> None:
    print("\n" + "=" * 74)
    print("【2】贪婪 vs 非贪婪")
    print("=" * 74)

    html = "<div><p>正文一</p><p>正文二</p></div>"
    tag = "div"

    # 贪婪：<.*> 会一口气吃到最后一个 >
    greedy = re.search(r"<.*>", html)
    print(f"原文: {html}")
    print(f"贪婪  r'<.*>'      → {greedy.group()!r}")
    print("  为什么这么长：.* 吃到最后一个 '>'，然后回溯找回整个匹配")

    # 非贪婪：碰到第一个 > 就停
    lazy = re.search(r"<.*?>", html)
    print(f"非贪婪 r'<.*?>'    → {lazy.group()!r}")
    print("  为什么这么短：.*? 满足最低需求（0 个字符）后立刻停手")

    # 更规范的写法：匹配具体标签名，避免通配
    precise = re.findall(r"<div>.*?</div>", html)
    print(f"更稳妥 r'<div>.*?</div>' → {precise!r}")
    print("  经验法则：能用具体标签就别用 .*，能不用 .* 就别用 .*")

    # 经典例题：提取成对标签内的内容
    for pat in (r"<p>(.*)</p>", r"<p>(.*?)</p>"):
        got = re.findall(pat, html)
        print(f"  {pat:<14} findall → {got!r}")

    # 转义后的 {m,n}? 懒惰形式
    digits = "1234567890"
    print(f"\n贪婪  r'\\d{{3,}}'    → {re.findall(r'\\d{3,}', digits)!r}")
    print(f"非贪婪 r'\\d{{3,}}?'  → {re.findall(r'\\d{3,}?', digits)!r}")
    print("  为什么：上面输出中多个 '3' 代表每个匹配起点各匹配一次，非贪婪只取 3 位")


# ===== 语法解析 =====
# 【3】分组、捕获与命名组
#   语法规则：
#     (pattern)        捕获组，编号从 1 开始，match.group(1) 取内容
#     (?:pattern)      非捕获组：只做"括号分组"（控制优先级），不占用编号
#     (?P<name>pattern) 命名组，比数字编号可读性高，group('name') 取内容
#     (?P=name)        命名组反向引用
#     \1 \2            数字反向引用，指向第 1、2 个捕获组
#   设计意图：把长模式切成可复用的片段，并允许"匹配到的内容"参与后续计算。
def demo_groups() -> None:
    print("\n" + "=" * 74)
    print("【3】分组、捕获与命名组")
    print("=" * 74)

    log = "2024-03-15 10:30:00 ERROR 数据库连接超时"

    # ---- 数字编号组 ----
    pattern = r"(\d{4})-(\d{2})-(\d{2}) (\d{2}):(\d{2}):(\d{2}) (\w+)"
    m = re.search(pattern, log)
    print(f"模式: {pattern}")
    print(f"完整匹配 group(0)  : {m.group(0)!r}")
    print(f"日期   group(1..3) : {m.group(1)}-{m.group(2)}-{m.group(3)}")
    print(f"时间   group(4..6) : {m.group(4)}:{m.group(5)}:{m.group(6)}")
    print(f"级别   group(7)    : {m.group(7)!r}")
    print(f"groups() 元组形式  : {m.groups()!r}")
    # groups() 是 group(1..n) 的元组形式，批量解包很方便
    year, month, day = m.group(1), m.group(2), m.group(3)
    print(f"解包演示: 年={year} 月={month} 日={day}")

    # ---- 命名组 ----
    named = r"(?P<year>\d{4})-(?P<month>\d{2})-(?P<day>\d{2})"
    m2 = re.search(named, log)
    print(f"\n命名组 groupdict(): {m2.groupdict()!r}")
    print(f"按名取值 group('year') = {m2.group('year')!r}")
    print("  为什么用命名组：组一多，纯数字编号完全无法维护")
    print(f"  模式的 groupspec: {re.compile(named).groupindex!r}  ← 名字到编号的映射")

    # ---- 非捕获组 ----
    # (?:...) 不产生捕获，只用于限定优先级/分组，节省内存
    raw_url = "https://example.com:8080/path?q=1"
    p_num = re.search(r"(https?)://([^:/]+)(?::(\d+))?(/.*)", raw_url)
    # 同样的结构，但全部用 (?:...) 包裹：能匹配，只是不记录任何捕获
    p_non = re.search(r"(?:https?)://(?:[^:/]+)(?::\d+)?(?:/.*)", raw_url)
    print(f"\n含捕获组 groups(): {p_num.groups()!r}  ← 3 个捕获")
    print(f"非捕获组匹配结果    : {p_non.group()!r}  ← 匹配成功")
    print(f"非捕获组 groups(): {p_non.groups()!r}  ← 0 个捕获")
    print("  为什么这么写：只需要判断是否匹配、不需要取值时，用 (?:) 省掉捕获开销")

    # ---- 反向引用 ----
    # \1 引用第 1 个捕获组的内容，用来匹配"紧跟其后的重复部分"
    dup = "xababab"
    print(f"\n反向引用：要求紧邻的相同内容重复出现")
    # ★ 注意 f-string 中【表达式部分】的原始字符串要写单反斜杠 \1，
    #   而【文本部分】要写 \\1 才会显示为 \1
    print(f"  r'(ab)\\1' on {dup!r} → {re.findall(r'(ab)\1', dup)!r}")
    print("  为什么：\\1 让第 1 组匹配到的 'ab' 必须【再出现一次】，即 'abab'")
    print(f"  注意 findall 只返回【被反向引用的部分】；")
    print(f"  'xababab' 中匹配占用了 4 个字符，剩余的 'ab' 后面已无内容可引用")

    # 更直观的例子：连续重复的字符
    repeat = "hello world aa bb cc"
    print(f"\n  r'(\\w)\\1' on {repeat!r} → {re.findall(r'(\w)\1', repeat)!r}")
    print("  这里捕获的是【单个字符】，所以能找出 'aa' 'bb' 'cc' 这类相邻重复")

    # findall 带多个捕获组时，返回的是"元组的列表"（重要！）
    print(f"\nfindall 多组返回元组: {re.findall(named, log)!r}")
    print("  规则：0 个组 → [str, ...]；1 个组 → [str, ...]；≥2 个组 → [(g1,g2), ...]")
    print(f"  单组时列表长度: {len(re.findall(named, log))}  （不是字符数！）")


# ===== 语法解析 =====
# 【4】零宽断言：环视（不消耗字符，只检查位置）
#   语法规则：
#     (?=pat)     正向先行：右边【必须】是 pat，但不取它（零宽度）
#     (?!pat)     负向先行：右边【不能】是 pat
#     (?<=pat)    正向后顾：左边【必须】是 pat（Python 固定宽度）
#     (?<!pat)    负向后顾：左边【不能】是 pat
#   设计意图：实现"匹配一个词，但不看这个词本身"的约束，
#             如匹配后面跟着数字的单词、密码中的强弱规则。
def demo_lookaround() -> None:
    print("\n" + "=" * 74)
    print("【4】零宽断言 lookaround")
    print("=" * 74)

    # 正向先行：单词后面紧跟数字
    words = "room 4 kitchen 7 bath"
    pat = r"\b\w+(?= \d)"
    print(f"r'\\b\\w+(?= \\d)'   on {words!r} → {re.findall(pat, words)!r}")
    print("  \\b 是单词边界（零宽），(?= \\d) 断言右边是空格+数字但不消耗它")

    # 密码强度：必须同时含大小写和数字，且长度>=8
    pwd = "Abcdef123"
    ok = bool(re.fullmatch(
        r"(?=.*[a-z])(?=.*[A-Z])(?=.*\d).{8,}", pwd))
    print(f"\n密码 {pwd!r} 是否满足强密码规则: {ok}")
    print("  为什么这么写：多个 (?=.*) 从不同角度【同时】提要求，组合起来就是与逻辑")

    # 负向先行 / 负向后顾：排除特定后缀
    log_lines = ["setup.cfg", "main.py", "readme.txt", "tool.cfg.bak"]
    # (?!.*\.cfg$) 表示"后面不能再跟 .cfg"，实现排除
    exclude_cfg = re.compile(r"^(?!.*\.cfg$)")
    kept = [n for n in log_lines if exclude_cfg.search(n)]
    print("\n含负向先行 (?!...) 的排除匹配:")
    for n in log_lines:
        print(f"   {n:<16} r'^(?!.*\\.cfg$)' → {'保留' if exclude_cfg.search(n) else '排除'}")
    print(f"   过滤结果: {kept}")
    print("  说明：(?!...) 断言【后面不能匹配某模式】，不消耗字符，是排除类需求的利器")
    print("  Python 要求后顾 (?<=) 宽度固定，前行 (?!...) 则无此限制")


# ===== 语法解析 =====
# 【5】re.compile 与 flags
#   语法规则：
#     pat = re.compile(pattern, flags)   编译出可复用的 Pattern 对象
#     re.VERBOSE | re.MULTILINE | re.IGNORECASE | re.DOTALL | re.UNICODE ...
#   常用 flags 语义：
#     IGNORECASE  忽略大小写
#     MULTILINE    ^ $ 匹配每行的首尾（默认只匹配整个字符串的首尾）
#     DOTALL       . 也能匹配换行符（默认不能）
#     VERBOSE      模式中的空白和 # 注释被忽略（长正则可读性救星）
#     ASCII        \d\w\s 只认 ASCII（性能略高，中文场景不要用）
#   设计意图：compile 把"字符串模式"编译成可执行的对象，
#             使同一模式在循环中避免重复解析，属于性能优化手段。
def demo_compile_and_flags() -> None:
    print("\n" + "=" * 74)
    print("【5】re.compile 与 flags")
    print("=" * 74)

    # flags 可以在两种位置给出：调用处 或 模式内联
    s = "Hello World"
    print(f"re.search('world', {s!r}, re.I) → {re.search('world', s, re.I)}")
    print(f"re.search('(?i)world', {s!r})   → {re.search('(?i)world', s)}")
    print("  两种写法等价；内联写法的好处是模式整体带标记，自解释")

    # MULTILINE
    # ★ 要让 abc 出现在【每行开头】，否则 ^abc 什么也匹配不到
    multi = "abc第一行\nabc第二行\nabc第三行"
    print(f"\n测试文本: {multi!r}")
    print(f"无 MULTILINE: re.findall('^abc', ...)  → {re.findall('^abc', multi)!r}")
    print(f"有 MULTILINE:                          → "
          f"{re.findall('^abc', multi, re.M)!r}")
    print("  为什么：默认 ^ 只认整个字符串开头，M 打开后认每一行的行首")

    # DOTALL
    dot_text = "a\nb"
    print(f"\n无 DOTALL: re.search(r'a.b', ...)  → {re.search('a.b', dot_text)}")
    print(f"有 DOTALL:                           → {re.search('a.b', dot_text, re.S)}")
    print("  为什么：. 默认排除换行符，S 让它能跨行（日志多行匹配必备）")

    # VERBOSE：长模式的最佳实践
    verbose_pat = re.compile(r"""
        (?P<year>\d{4})     # 年份：4 位数字
        [-/]                 # 分隔符：兼容 - 和 /
        (?P<month>\d{2})     # 月份：2 位
        [-/]
        (?P<day>\d{2})       # 日：2 位
    """, re.VERBOSE)
    print(f"\nVERBOSE 多行模式匹配: {verbose_pat.search('2024/03/15').groupdict()}")

    # 编译对象的复用与属性
    number_pat = re.compile(r"\d+")
    print(f"\nPattern 对象属性：pattern={number_pat.pattern!r}, "
          f"flags={number_pat.flags}")
    print(f"  flags 位值: {number_pat.flags:#x}  (re.UNICODE 的默认值也在里面)")
    print(f"  复用演示: {[number_pat.findall(t) for t in ('a1', 'b22', 'c333')]}")

    # 编译期错误：模式非法会在 compile 时立刻抛错
    print("\n错误处理（模式非法属于【编程错误】，应尽早暴露）：")
    try:
        re.compile(r"(unclosed")
    except re.error as exc:
        print(f"  re.error: {exc}")
        print(f"  exc.pattern={exc.pattern!r}, exc.pos={exc.pos}  ← 定位到出错位置")
        print("  设计意图：re.error 带 pattern/pos，便于排查模式写错的位置")


# ===== 语法解析 =====
# 【6】六个查找函数的区别（面试高频）
#   语义速查（对同一模式 p 和字符串 s）：
#     re.match(p, s)     只从【开头】匹配，成功返回 Match / 失败 None
#     re.search(p, s)    在【任意位置】找第一个，成功返回 Match / 失败 None
#     re.fullmatch(p, s) 要求【整个字符串】完全匹配
#     re.findall(p, s)   返回【所有】匹配；多组时返回元组列表
#     re.finditer(p, s)  返回【惰性迭代器】，每项是 Match 对象（省内存）
#     re.sub(p, r, s)    把匹配替换为 r，返回新字符串
#     re.subn(p, r, s)   同 sub，但额外返回替换次数
#   关键区别：match/search 返回 Match 对象（有 .group()/.groups()/.start()）；
#             findall 直接给字符串/元组，不用再 .group()。
#   设计意图：finditer 是"流式"接口，处理大文本时内存友好，是工程首选。
def demo_find_functions() -> None:
    print("\n" + "=" * 74)
    print("【6】match / search / fullmatch / findall / finditer / sub 对比")
    print("=" * 74)

    text = "hello python 3.12 world"

    print(f"被测字符串: {text!r}，模式: r'\\d+\\.\\d+'")
    pat = r"\d+\.\d+"

    m1 = re.match(r"hello", text)
    m2 = re.match(r"python", text)
    print(f"\n① match 从开头匹配")
    print(f"   re.match(r'hello', text)  → {m1}")
    print(f"   re.match(r'python', text) → {m2}   ← 开头不是 python，失败 None")
    print("  为什么：match 的搜索位置被固定为 index=0，不尝试往后找")

    s1 = re.search(pat, text)
    s2 = re.search(r"java", text)
    print(f"\n② search 任意位置找第一个")
    print(f"   re.search(r'\\d+\\.\\d+', text) → {s1}")
    print(f"     .group()={s1.group()!r}, .span()={s1.span()}, .start()={s1.start()}")
    print(f"   re.search(r'java', text)         → {s2}   ← 找不到是 None")

    f1 = re.fullmatch(r"hello.*", text)
    f2 = re.fullmatch(r"hello.*world", text)
    print(f"\n③ fullmatch 要求整体匹配")
    print(f"   fullmatch(r'hello.*', text)      → {f1!r}  ← .* 能吃掉剩余全部，成功")
    print(f"   fullmatch(r'python.*', text)     → {re.fullmatch(r'python.*', text)!r}"
          f"  ← 开头不是 python，失败")
    print(f"   关键点：fullmatch 只要求【整体匹配】，不要求按位置对齐。")
    print(f"     上面的 r'hello.*world' 其实也能匹配（.* 贪婪吃到最后再回溯到 world）")
    print(f"     实测 = {bool(f2)}")
    print("  为什么：search 只要【出现】即可；fullmatch 要求整个串被模式覆盖，"
          "校验场景用它")

    all1 = re.findall(pat, text)
    print(f"\n④ findall 一次性拿全部")
    print(f"   re.findall(pat, text) → {all1!r}  （返回字符串列表）")

    print("\n⑤ finditer 惰性迭代（省内存）")
    for m in re.finditer(pat, text):
        print(f"   匹配到 {m.group()!r}，位置 {m.span()}")
    print("  为什么用 finditer：大文本上它不会一次性构造整个结果列表")

    replaced = re.sub(r"\d+\.\d+", "X.Y", text)
    replaced_n = re.subn(r"\d+\.\d+", "X.Y", text)
    print(f"\n⑥ sub / subn 替换")
    print(f"   re.sub(...)  → {replaced!r}")
    print(f"   re.subn(...) → {replaced_n!r}   ← 元组 (新串, 替换次数)")

    # sub 的高级用法：函数式替换 + 反向引用
    print("\n⑦ sub 的高阶用法")
    md = "**粗体** 和 *斜体*"
    # ★ 反向引用必须用【单个】反斜杠：r'[\1]' 中的 \1 会被 re 替换成第 1 组的内容。
    #   若误写成 r'[\\1]'，那是"转义后的反斜杠 + 字符 1"，会原样输出 \1。
    print(f"   {md!r} → {re.sub(r'\*\*(.+?)\*\*', r'[\1]', md)!r}")
    print("   为什么写 r'[\\1]'：r'' 原始字符串里反斜杠不被转义，\\1 才被 re 当成反向引用")

    def double_num(m: re.Match) -> str:
        """把匹配到的数字翻倍。re.sub 会把每个 Match 传给这个函数。"""
        return str(int(m.group()) * 2)
    print(f"   {re.sub(r'\\d+', double_num, 'a1 b22 c3')!r}  ← 函数式替换")

    # count 参数限制替换次数
    print(f"   只替换前2个空格: {re.sub(r' ', '_', 'a b c d e', count=2)!r}")


# ===== 语法解析 =====
# 【7】实战提取：从混合文本中抽取结构化信息
#   重点：正则负责"定位和切分"，解析后的字符串仍要做类型转换和校验，
#         正则不是万能的解析器（如嵌套 JSON、HTML 解析应交给专用库）。
def demo_real_world() -> None:
    print("\n" + "=" * 74)
    print("【7】实战：邮箱 / URL / 日期 / 手机号提取")
    print("=" * 74)

    text = """
    联系方式：admin@example.com  备用：support@demo.org.cn
    官网：https://www.python.org/doc/ 和 http://127.0.0.1:8000/api?x=1
    会议时间：2024-03-15 至 2024年12月31日
    手机：13812345678 / 备用 15987654321
    噪声：not-an-email@  12345@abc
    """

    # ---- 邮箱 ----
    # 原理拆解：[local] @ [domain] [.tld]
    email_pat = re.compile(
        r"[a-zA-Z0-9._%+-]+"          # 本地部分：允许字母数字和 . _ % + -
        r"@"                        # 必含 @
        r"[a-zA-Z0-9.-]+"            # 域名主体
        r"\.[a-zA-Z]{2,}"            # 点 + 顶级域（至少 2 个字母）
    )
    emails = email_pat.findall(text)
    print(f"① 邮箱 ({len(emails)} 个):")
    for e in emails:
        print(f"   {e}")
    print("  为什么这么写：\\.[a-zA-Z]{2,} 强制要求顶级域，"
          '从而排除 "12345@abc" 这类无点域名')

    # ---- URL ----
    url_pat = re.compile(
        r"(https?|ftp)://"                        # 协议
        r"([a-zA-Z0-9.-]+)"                       # 主机
        r"(:\d{1,5})?"                            # 可选端口
        r"(/[^\s，。]*)"                           # 路径
    )
    print("\n② URL（拆出协议/主机/端口/路径四个组）：")
    for proto, host, port, path in url_pat.findall(text):
        print(f"   协议={proto:<6} 主机={host:<16} 端口={port or '默认':<8} 路径={path}")

    # ---- 日期 ----
    # 兼容 2024-03-15 与 2024年12月31日 两种写法
    date_pat = re.compile(
        r"(?P<y>\d{4})"
        r"[-年](?P<m>\d{1,2})"
        r"[-月](?P<d>\d{1,2})"
        r"日?"
    )
    print("\n③ 日期（命名组 + 多分隔符兼容）：")
    for m in date_pat.finditer(text):
        g = m.groupdict()
        # 校验业务规则：月和日必须在合理区间（正则保证格式，业务保证有效）
        y, mo, d = int(g["y"]), int(g["m"]), int(g["d"])
        flag = "✓有效" if 1 <= mo <= 12 and 1 <= d <= 31 else "✗非法"
        print(f"   {m.group()!r:<20} → {y}-{mo:02d}-{d:02d} {flag}")

    # ---- 手机号 ----
    # 中国大陆手机号：1 开头，第二位 3-9，共 11 位
    phone_pat = re.compile(r"(?<!\d)1[3-9]\d{9}(?!\d)")
    phones = phone_pat.findall(text)
    print(f"\n④ 手机号 ({len(phones)} 个): {phones}")
    print("  为什么用前后 (?<!\\d)(?!\\d)：")
    print("  防止把 13812345678901 这类超长数字串中截取出一段误判为手机号")

    # ---- HTML 标签清理（正则的"合理用途"）----
    raw_html = "<p>这是 <b>正文</b>，包含 <a href='#'>链接</a> 与 <img src=x.png/> 标签</p>"
    # 先去 script/style（它们的"内容"不是标签，粗暴去标签会破坏文本）
    cleaned = re.sub(r"<script.*?</script>|<style.*?</style>", "", raw_html, flags=re.S)
    cleaned = re.sub(r"<[^>]+>", "", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    print(f"\n⑤ HTML 提取正文")
    print(f"   原文  : {raw_html}")
    print(f"   提取后: {cleaned!r}")
    print("  ⚠ 反面教材：正则【不能】用于解析嵌套 HTML（嵌套层级会让正则失效），")
    print("     真实项目请用 html.parser / BeautifulSoup，这里只演示简单的去标签。")


# ===== 语法解析 =====
# 【8】性能对比：re 方法 vs str 方法
#   结论要点：
#     1. 简单字面量替换，str.replace 快一个数量级（无正则引擎开销）
#     2. 同一模式多次使用，re.compile 明显优于重复 re.xxx(...)
#     3. 正则存在"灾难性回溯"风险，模式写不好复杂度可能指数级
def demo_performance() -> None:
    print("\n" + "=" * 74)
    print("【8】性能对比")
    print("=" * 74)

    text = "hello world " * 2000

    # ① str.replace vs re.sub（简单字面量）
    n_replace = 4000
    n_sub = 4000
    t_replace = timeit.timeit(lambda: text.replace("world", "python"), number=n_replace)
    t_sub = timeit.timeit(lambda: re.sub("world", "python", text), number=n_sub)
    print(f"① 简单字面量替换（{len(text)} 字符 × {n_replace} 次）")
    print(f"   str.replace : {t_replace:.4f}s")
    print(f"   re.sub      : {t_sub:.4f}s")
    print(f"   re.sub 慢约 {t_sub / t_replace:.1f} 倍 "
          f"← 没有元字符时不要用正则")

    # ② 编译复用 vs 每次重新编译
    pattern = r"\d{4}-\d{2}-\d{2}"
    date_text = "2024-03-15 " * 2000
    compiled = re.compile(pattern)

    n = 2000
    t_no_compile = timeit.timeit(lambda: re.findall(pattern, date_text), number=n)
    t_compile = timeit.timeit(lambda: compiled.findall(date_text), number=n)
    print(f"\n② 编译复用对比（findall × {n} 次）")
    print(f"   每次 re.findall(pattern,...) : {t_no_compile:.4f}s")
    print(f"   提前 compile 后复用          : {t_compile:.4f}s")
    print(f"   提速约 {t_no_compile / t_compile:.2f} 倍 "
          f"← 模式复用场景务必提前编译")

    # ③ 灾难性回溯演示（嵌套量词是元凶）
    evil = r"^(a+)+$"
    bad = "a" * 22 + "!"      # 末尾加一个不匹配字符，强制引擎逐一回溯
    print(f"\n③ 灾难性回溯（嵌套量词的陷阱）")
    print(f"   模式 {evil!r} 对 {len(bad)} 个字符（22 个 a 加 1 个 '!'）：")
    try:
        # 字符数必须【严格控制】：(a+)+ 的可能分组数约为 2^(n-1)，
        # n=22 时约两百万次，仍在可接受范围；n=30 就是十亿级，会卡死进程。
        t_evil = timeit.timeit(lambda: re.match(evil, bad), number=1)
        print(f"   耗时 {t_evil:.4f}s / 1 次")
        safe_pat = re.compile(r"^a+$")
        t_safe = timeit.timeit(lambda: safe_pat.match(bad), number=100)
        print(f"   安全写法 r'^a+$' 同样输入：{t_safe * 1000:.4f}ms / 100 次")
    except Exception as exc:  # pragma: no cover
        print(f"   异常: {exc}")
    print("   为什么慢：(a+)+ 的匹配方式有指数级多的组合，")
    print("   末尾的 '!' 让所有组合都失败，只能逐个回溯验证")
    print("   安全写法：避免嵌套量词，改用 r'^a+$'，或用原子组 (?>...)")


# ===== 语法解析 =====
# 【9】小结与易错清单
def demo_summary() -> None:
    print("\n" + "=" * 74)
    print("【9】小结与易错清单")
    print("=" * 74)
    print("""
  1. 先用 str 方法，确有需要再上正则：replace > re.sub(字面量)
  2. 模式复用一律 re.compile()，性能差距可达数倍
  3. 贪婪是默认行为，非贪婪加 '?'；能用具体字符就别用 .*
  4. match 只看开头、search 全局找、fullmatch 必须整串
  5. findall 多于一个捕获组时，返回的是【元组列表】
  6. re.sub 的替换串用 r'' 原始字符串写反向引用 \\1
  7. 嵌套量词 (a+)+ 会导致灾难性回溯，必须避免
  8. 正则不是解析器：嵌套结构（HTML/XML/JSON）请用专用库
  9. 正则保证"格式"正确，业务有效性（日期范围、手机号归属）仍需额外校验
  10. 编译失败抛 re.error，带 pattern 与 pos 属性可直接定位问题
    """)


def main() -> None:
    """主入口：按顺序演示全部知识点。"""
    print("=" * 74)
    print("re 模块：正则表达式")
    print("=" * 74)
    print(f"Python 版本: {sys.version.split()[0]}")
    print()

    demo_metacharacters()
    demo_greedy_vs_lazy()
    demo_groups()
    demo_lookaround()
    demo_compile_and_flags()
    demo_find_functions()
    demo_real_world()
    demo_performance()
    demo_summary()


if __name__ == "__main__":
    main()