#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
csv 模块：读写与格式陷阱
================================================

【配套数据文件】
- data/sample.csv：20 条员工数据（含中文）

【演示的语法点】
1. csv.reader：按行读，返回 list[str]
2. csv.writer：按行写
3. csv.DictReader / DictWriter：按表头字段名读写
4. dialect 与 Excel 相关参数：delimiter / quotechar / lineterminator
5. newline="" 的必要性（真实演示：不加会多出空行）
6. UTF-8 BOM 问题：utf-8-sig 的作用与真实乱码演示
7. 换行符陷阱：lineterminator / \r\n / 跨平台差异
8. 转义规则：quoting=QUOTE_MINIMAL / QUOTE_ALL / QUOTE_NONNUMERIC / QUOTE_NONE
9. 字段值含分隔符/换行/引号时的正确处理
10. 不规则行（字段数不一致）的处理：restkey / restval
11. Sniffer 自动探测分隔符
12. 大文件流式读取与写入

【预期输出摘要】
- reader / writer / DictReader / DictWriter 四种方式读取同一文件的对比
- 不加 newline="" 产生空行的真实证据
- BOM 导致表头变成 '\ufeffid' 的真实证据
- 引号转义的逐个案例
- Sniffer 的探测结果
"""

import csv
import io
import os
import tempfile
from pathlib import Path


DATA_DIR = Path(__file__).parent / "data"
SAMPLE_CSV = DATA_DIR / "sample.csv"
WORK_DIR = Path(__file__).parent / "_tmp_csv"
WORK_DIR.mkdir(exist_ok=True)


# ===== 语法解析 =====
# 【1】csv 模块存在的理由
#   CSV（Comma-Separated Values）本质是「带引号转义规则的文本表格」。
#   手写 split(",") 的问题：
#     - 字段内含逗号时会被错切："张伟,技术部" 变成两个字段
#     - 字段内含换行时更惨："第一行\n第二行" 会变成两行
#     - 引号包裹的规则完全没有处理
#   csv 模块实现了 RFC 4180 标准，能正确处理上述所有情况。
#
# 【2】writerow 与 writerows
#   writerow(row)写一行；writerows(list_of_rows) 批量写多行。
#   传入的每一行必须是「可迭代的字符串序列」（list / tuple 都行）。
def demo_1_reader_basic():
    """csv.reader 的基础用法。"""
    print("=" * 74)
    print("【1】csv.reader —— 基础读取")
    print("=" * 74)

    # ===== 语法解析 =====
    # csv.reader 返回的是一个「迭代器」，每次 __next__ 返回一行，
    # 每一行是一个 list（元素都是 str，不做任何类型转换）。
    # 这意味着「所有数字都是字符串」，需要自行转换。
    print("① 最简用法：")
    with open(SAMPLE_CSV, "r", encoding="utf-8", newline="") as f:
        # ===== 语法解析 =====
        # newline="" 的作用：告诉 csv 模块「文件里已经有换行符，
        # 你不要做任何转换，原样读取交给 csv 模块自己处理」。
        #
        # 原理：文本模式默认会做「通用换行符翻译」（universal newlines），
        #       把 \r\n、\r、\n 全部翻译成 \n。
        #       csv 模块需要知道真实的行结束符是什么（用于判断引号内的换行），
        #       如果被翻译了就无法区分「行结束」和「字段内的换行」。
        #       newline="" 关闭了这个翻译。
        reader = csv.reader(f)
        # next() 从迭代器取一行
        header = next(reader)
        print(f"   表头 = {header}")
        print(f"   类型 = {type(header).__name__}, 元素类型 = "
              f"{ {type(x).__name__ for x in header} }")
        print()

    print("② 读取前3 行数据：")
    with open(SAMPLE_CSV, "r", encoding="utf-8", newline="") as f:
        reader = csv.reader(f)
        for i, row in enumerate(reader):
            if i >= 3:
                break
            print(f"   第{i + 2}行: {row}")
    print()

    print("③ 所有行数与遍历方式：")
    with open(SAMPLE_CSV, "r", encoding="utf-8", newline="") as f:
        reader = csv.reader(f)
        # list(reader) 一次性读完，消耗迭代器
        rows = list(reader)
    print(f"   总行数 = {len(rows)}（含表头）")
    print(f"   数据行数 = {len(rows) - 1}")
    print(f"   每行字段数 = {len(rows[0])}")

    # ===== 语法解析 =====
    # 统计各行的字段数，可以发现「不规则行」
    field_counts = {len(row) for row in rows}
    print(f"   所有行的字段数集合 = {field_counts}"
          f"  -> {len(field_counts) == 1} 表示字段数完全一致")
    print()

    print("④ 迭代器特性验证：")
    with open(SAMPLE_CSV, "r", encoding="utf-8", newline="") as f:
        reader = csv.reader(f)
        first = next(reader)
        print(f"   第一次 next() 返回: {first[:3]}...")
        # 已消费的行不会重复出现 —— 这就是迭代器语义
        second = next(reader)
        print(f"   第二次 next() 返回: {second[:3]}...")
        print("   -> reader 是迭代器，取过的行不会重复")
        print(f"   reader 支持 len()? {hasattr(reader, '__length_hint__')}")
    print()
    print("【要点】csv.reader 返回的全是 str，数字需要 int()/float() 手动转换。")
    print("【要点】open 时必须加 newline=\"\"，否则会出现空行（见 demo_3）。")


def demo_2_dictreader_writer():
    """DictReader / DictWriter。"""
    print("=" * 74)
    print("【2】csv.DictReader / DictWriter —— 按字段名访问")
    print("=" * 74)

    # ===== 语法解析 =====
    # 纯列表方式的问题：依赖列的顺序，一旦文件列顺序变化，
    # 所有下标都错了，且可读性差。
    #
    # DictReader 的解法：把第一行当表头，之后每行返回一个 dict，
    # key 是表头字符串，value 是字段值。
    #   reader.fieldnames   -> 表头列表
    #   row['name']         -> 按字段名访问，不依赖顺序
    print("① DictReader 基本用法：")
    with open(SAMPLE_CSV, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        # ===== 语法解析 =====
        # fieldnames 是「延迟读取」的：第一次访问时才真正读取第一行。
        # 之后 for 循环从第二行开始。
        print(f"   fieldnames = {reader.fieldnames}")
        for i, row in enumerate(reader):
            if i >= 2:
                break
            print(f"   第{i + 2}行: name={row['name']}, "
                  f"dept={row['department']}, salary={row['salary']}")
    print()

    print("② DictReader 每次返回的都是 dict：")
    with open(SAMPLE_CSV, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        first_row = next(reader)
    print(f"   类型 = {type(first_row).__name__}")
    print(f"   内容 = {dict(first_row)}")
    print("   -> 用字段名访问，列顺序变化也不会出错")
    print()

    print("③ 用字典做统计（DictReader 的核心价值）：")
    dept_stats = {}
    salary_by_dept = {}
    with open(SAMPLE_CSV, "r", encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            dept = row["department"]
            # str 转 int 是必需的，因为 csv 只给字符串
            salary = int(row["salary"])
            dept_stats[dept] = dept_stats.get(dept, 0) + 1
            salary_by_dept.setdefault(dept, []).append(salary)

    print(f"   各部门人数:")
    for dept, count in sorted(dept_stats.items()):
        avg = sum(salary_by_dept[dept]) / len(salary_by_dept[dept])
        print(f"     {dept:<8} 人数={count:<3} 平均薪资={avg:.1f}")
    print()

    print("④ DictWriter 写入：")
    out_file = WORK_DIR / "output_dict.csv"
    # fieldnames 必须显式指定，它决定了「表头行」和「每个 dict 的 key 集合」
    fieldnames = ["id", "name", "department", "salary"]
    rows_to_write = [
        {"id": "101", "name": "新员工甲", "department": "技术部", "salary": "15000"},
        {"id": "102", "name": "新员工乙", "department": "市场部", "salary": "12000"},
        # 缺少 salary 字段 -> DictWriter 会写空字符串
        {"id": "103", "name": "新员工丙", "department": "技术部"},
        # 多余字段 -> 会被忽略（除非 extrasaction='raise'）
    ]
    with open(out_file, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        # writeheader() 写表头行 —— 忘了这一句，读回来就没有字段名可用
        writer.writeheader()
        # writerows 批量写入
        writer.writerows(rows_to_write)
    print(f"   写入结果（前3 行）:")
    for line in out_file.read_text(encoding="utf-8").splitlines()[:4]:
        print(f"     {line}")
    print()
    print("   注意第 4 行的 salary 为空 —— 缺失字段写空字符串")
    print()

    print("⑤ DictWriter 的 extrasaction 与 restval：")
    print("   extrasaction='raise'（默认）：dict 中有 fieldnames 之外的 key -> 报错")
    print("   extrasaction='ignore'：忽略多余字段")
    print("   restval='未知'：缺失字段填这个默认值（默认是空字符串）")
    out2 = WORK_DIR / "output_restval.csv"
    with open(out2, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames,
                                extrasaction="ignore", restval="未知")
        writer.writeheader()
        writer.writerow({"id": "201", "name": "丙",
                         "department": "人事部", "额外的key": "被忽略"})
    print(f"   结果: {out2.read_text(encoding='utf-8').splitlines()[1]}")
    print()
    print("⑥ readerow 的返回值：")
    # writer.writerow() 返回写入的字符数（或字节数，二进制模式下）
    with open(WORK_DIR / "ret.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        n = w.writerow(["ab", "cd"])
    print(f"   writerow(['ab','cd']) 返回 = {n}")
    print("   -> 可以用来统计写入量，但很少用到")


def demo_3_newline_trap():
    """newline 参数的陷阱：真实演示。"""
    print("=" * 74)
    print("【3】newline 参数的陷阱（真实演示空行问题）")
    print("=" * 74)

    # ===== 语法解析 =====
    # 问题根源：Python 的「通用换行符翻译」（universal newlines）。
    #   文本模式读取时，\r\n 和 \r 都会被翻译成 \n
    #   文本模式写入时，\n 会被翻译成 os.linesep（Windows 是 \r\n）
    #
    # 对csv 而言这是双重灾难：
    #   读取时：csv.writer 默认写出 \r\n，被翻译成 \n，
    #           csv.reader 认为这是「两个换行」，产生空行
    #   写入时：csv.writer 写出 \r\n，文本层又翻译一次变成 \r\r\n
    #
    # 解决：open() 时传 newline=""，完全关闭翻译。

    bad_file = WORK_DIR / "no_newline_arg.csv"
    # 用 csv.writer 写，看它实际写出什么
    with open(bad_file, "w", encoding="utf-8", newline="") as f:
        csv.writer(f).writerows([["a", "b"], ["c", "d"]])

    print("① 用 csv.writer 写出的原始字节：")
    print(f"   {bad_file.read_bytes()!r}")
    print(f"   -> 可见行结束符是 \\r\\n（CSV 的标准行结束符）")
    print()

    print("② 读取时【不加】newline='' 的后果：")
    # 这是错误示范
    with open(bad_file, "r", encoding="utf-8") as f:      # 故意不传 newline
        rows = list(csv.reader(f))
    print(f"   读到 {len(rows)} 行: {rows}")
    print(f"   -> 明明只有 2 行数据，却读出了 {len(rows)} 行！")
    print(f"   -> 每行末尾多出一个空列表 []，这就是「空行问题」")
    print()

    print("③ 读取时【加上】newline='' 的正确结果：")
    with open(bad_file, "r", encoding="utf-8", newline="") as f:
        rows = list(csv.reader(f))
    print(f"   读到 {len(rows)} 行: {rows}")
    print()

    print("④ 写入时不加 newline='' 的后果：")
    bad_write = WORK_DIR / "bad_write.csv"
    with open(bad_write, "w", encoding="utf-8") as f:      # 故意不传 newline
        csv.writer(f).writerows([["x", "y"]])
    print(f"   写入的原始字节: {bad_write.read_bytes()!r}")
    print(f"   -> 出现 \\r\\r\\n！换行符被翻译了两次，数据格式已损坏")
    print()

    print("⑤ 正确写入的字节：")
    good_write = WORK_DIR / "good_write.csv"
    with open(good_write, "w", encoding="utf-8", newline="") as f:
        csv.writer(f).writerows([["x", "y"]])
    print(f"   {good_write.read_bytes()!r}  -> 干净的 \\r\\n")
    print()

    print("⑥ newline 的其他取值：")
    print("   newline=None（默认）: 开启通用换行符翻译 <- CSV 场景禁用")
    print("   newline=''          : 关闭翻译，保留原始换行符 <- CSV 场景必用")
    print("   newline='\\n'        : 写入时把 \\n 翻译成指定的换行符")
    print("                         常用于生成 Unix 风格的文件")
    unix_file = WORK_DIR / "unix_style.csv"
    with open(unix_file, "w", encoding="utf-8", newline="\n") as f:
        csv.writer(f).writerows([["a", "b"], ["c", "d"]])
    print(f"   newline='\\n' 写出的字节: {unix_file.read_bytes()!r}")
    print()
    print("【铁律】读写 CSV 文件时，open() 必须加 newline=''。")


def demo_4_bom_problem():
    """UTF-8 BOM 问题。"""
    print("=" * 74)
    print("【4】UTF-8 BOM 问题")
    print("=" * 74)

    # ===== 语法解析 =====
    # BOM（Byte Order Mark，字节顺序标记）是文件开头的三个字节 EF BB BF。
    # 它的来源：Excel 的「CSV UTF-8（带 BOM）」格式就会写入 BOM。
    #
    # 问题：用 encoding='utf-8' 读时，BOM 会被当成正文字符 U+FEFF，
    #       导致第一个表头变成 '\ufeffid' 而不是 'id'，
    #       于是 row['id'] 抛 KeyError。
    # 解决：用 encoding='utf-8-sig' 读取，它会在解码时自动剥离 BOM。
    #
    # 注意方向性：
    #   - 读取含 BOM 的文件 -> 用 utf-8-sig
    #   - 写入文件给别人（可能是 Excel）-> 用 utf-8-sig（对方 Excel 才认）
    #   - 纯 Python 内部流转-> utf-8 就够，加 BOM 反而是冗余数据

    bom_file = WORK_DIR / "with_bom.csv"
    # 手动写入 BOM + 内容
    bom_file.write_bytes(b"\xef\xbb\xbf" + "id,name,dept\n1,张伟,技术部\n".encode("utf-8"))

    print("① 含 BOM 的文件：")
    print(f"   前 3 字节 = {bom_file.read_bytes()[:3]!r}  -> 这就是 BOM")
    print()

    print("② 用 utf-8 读（错误）：")
    with open(bom_file, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        print(f"   fieldnames = {reader.fieldnames!r}")
        print(f"   第一个字段名 = {reader.fieldnames[0]!r}")
        print(f"   -> 注意开头的 '\\ufeff'！它成了字段名的一部分")
        row = next(reader)
        print(f"   row['id'] -> ", end="")
        try:
            print(row["id"])
        except KeyError as e:
            print(f"KeyError: {e}")
    print()

    print("③ 用 utf-8-sig 读（正确）：")
    with open(bom_file, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        print(f"   fieldnames = {reader.fieldnames!r}")
        print(f"   第一个字段名 = {reader.fieldnames[0]!r}  -> BOM 被自动剥离")
        row = next(reader)
        print(f"   row['id'] = {row['id']!r}  -> 正常工作")
    print()

    print("④ 检查文件是否有 BOM：")
    data = bom_file.read_bytes()
    has_bom = data.startswith(b"\xef\xbb\xbf")
    print(f"   data.startswith(b'\\xef\\xbb\\xbf') = {has_bom}")
    print()

    print("⑤ 写入时的选择：")
    excel_file = WORK_DIR / "for_excel.csv"
    # 给 Excel 用：加 BOM，Excel 双击才不会乱码
    with open(excel_file, "w", encoding="utf-8-sig", newline="") as f:
        csv.writer(f).writerows([["姓名", "部门"], ["张伟", "技术部"]])
    print(f"   utf-8-sig 写入的字节前缀 = {excel_file.read_bytes()[:3]!r}（含 BOM）")
    # 程序间流转：不加 BOM
    internal_file = WORK_DIR / "internal.csv"
    with open(internal_file, "w", encoding="utf-8", newline="") as f:
        csv.writer(f).writerows([["姓名", "部门"], ["张伟", "技术部"]])
    print(f"   utf-8 写入的字节前缀   = "
          f"{internal_file.read_bytes()[:3]!r}（无 BOM）")
    print()
    print("【要点】读取可能含 BOM 的文件用 utf-8-sig，它对无 BOM 的文件也兼容。")
    print("       内部流转不要加 BOM，那是给 Excel 看的。")


def demo_5_quoting_rules():
    """引号与转义规则。"""
    print("=" * 74)
    print("【5】quoting 转义规则")
    print("=" * 74)

    # ===== 语法解析 =====
    # quoting 四种取值（csv.QUOTE_* 常量）：
    #   QUOTE_MINIMAL(0)   仅当字段含分隔符/引号/换行时才加引号（默认）
    #   QUOTE_ALL(1)       所有字段都加引号
    #   QUOTE_NONNUMERIC(2) 非数字字段加引号（读时也会尝试转数字）
    #   QUOTE_NONE(3)      永不加引号（此时必须设置 escapechar）
    #
    # CSV 的转义规则（RFC 4180）：
    #   - 字段含分隔符 -> 整个字段用引号包起来
    #   - 字段含引号   -> 引号本身写成两个引号（""），外部再加引号
    #   - 字段含换行   -> 整个字段用引号包起来
    test_rows = [
        ["普通字段", "含,逗号", '含"引号"', "含\n换行"],
        [123, 45.6, "text", ""],
    ]

    print("① QUOTE_MINIMAL（默认）：只给必要的字段加引号")
    buf = io.StringIO()
    csv.writer(buf, quoting=csv.QUOTE_MINIMAL).writerows(test_rows)
    minimal = buf.getvalue()
    for line in minimal.splitlines():
        print(f"   {line!r}")
    print()

    print("② QUOTE_ALL：全部加引号")
    buf = io.StringIO()
    csv.writer(buf, quoting=csv.QUOTE_ALL).writerows(test_rows)
    for line in buf.getvalue().splitlines():
        print(f"   {line!r}")
    print()

    print("③ QUOTE_NONNUMERIC：只有数字不加引号")
    buf = io.StringIO()
    csv.writer(buf, quoting=csv.QUOTE_NONNUMERIC).writerows(test_rows)
    for line in buf.getvalue().splitlines():
        print(f"   {line!r}")
    print("   -> 读取时也会把能转成数字的字段自动转换（见下方 demo_6）")
    print()

    print("④ 特殊字符的往返验证（写进去再读出来）：")
    tricky = [["有,逗号", '有"引号"', "有\n换行", "有\\反斜杠", "前后 空格 "]]
    out = WORK_DIR / "tricky.csv"
    with open(out, "w", encoding="utf-8", newline="") as f:
        csv.writer(f).writerows(tricky)
    with open(out, "r", encoding="utf-8", newline="") as f:
        back = next(csv.reader(f))
    print(f"   原始:  {tricky[0]}")
    print(f"   读回:  {back}")
    print(f"   完全一致: {tricky[0] == back}")
    print()

    print("⑤ 手写 split 的对比（说明为什么必须用 csv 模块）：")
    line = '"有,逗号",有"引号"'
    print(f"   原始行: {line}")
    print(f"   split(','): {line.split(',')}  -> 错切成 3 段")
    print(f"   csv.reader: {next(csv.reader(io.StringIO(line)))}  -> 正确的 2 段")
    print()
    print("【要点】QUOTE_MINIMAL 是通用默认；QUOTE_NONNUMERIC 在数据交换中很方便，")
    print("       但要注意它读时会把 '007' 这样的值也转成 int 7。")


def demo_6_dialect_and_sniffer():
    """dialect、自定义分隔符与 Sniffer。"""
    print("=" * 74)
    print("【6】dialect、自定义分隔符与 Sniffer")
    print("=" * 74)

    # ===== 语法解析 =====
    # dialect 是「一组 CSV 格式参数」的集合，最常用的是 'excel'。
    # 常用参数：
    #   delimiter       字段分隔符（默认 ','）
    #   quotechar       引号字符（默认 '"'）
    #   doublequote     双引号是否转义成两个双引号（默认 True）
    #   escapechar      转义字符（默认 None）
    #   lineterminator  行结束符（默认 '\r\n'）
    #   quoting         转义策略
    print("① 自定义分隔符（用 dialect 参数）：")
    tsv_data = "name\tdept\tsalary\n张伟\t技术部\t18000\n李娜\t市场部\t12000\n"
    reader = csv.reader(io.StringIO(tsv_data), dialect="excel-tab")
    print(f"   excel-tab dialect 解析 TSV:")
    for row in reader:
        print(f"     {row}")
    print()

    print("② 直接指定参数（不预定义 dialect）：")
    reader = csv.reader(io.StringIO(tsv_data), delimiter="\t")
    print(f"   delimiter='\\t' 解析:")
    for i, row in enumerate(reader):
        if i >= 2:
            break
        print(f"     {row}")
    print()

    print("③ 自定义 dialect 类（高级用法）：")
    class SemiColonDialect(csv.Dialect):
        """分号分隔、双引号转义、行结束符为 \\n。"""
        delimiter = ";"
        quotechar = '"'
        doublequote = True
        skipinitialspace = True   # 跳过分隔符后的空格
        lineterminator = "\n"
        quoting = csv.QUOTE_MINIMAL

    semi_data = "name; dept; note\n甲; 技术部; \"含;分号\"\n"
    reader = csv.reader(io.StringIO(semi_data), dialect=SemiColonDialect)
    for row in reader:
        print(f"     {row}")
    print("   -> skipinitialspace 让 '技术部' 不带前导空格")
    print()

    print("④ lineterminator 的作用：")
    for term_name, term in [("默认(\\r\\n)", "\r\n"), ("Unix(\\n)", "\n")]:
        buf = io.StringIO()
        w = csv.writer(buf, lineterminator=term)
        w.writerows([["a", "b"], ["c", "d"]])
        print(f"   {term_name}: {buf.getvalue()!r}")
    print("   -> 生成给 Windows Excel 打开的文件用 \\r\\n；")
    print("      生成给 Unix 工具处理的用 \\n")
    print()

    print("⑤ Sniffer：自动探测分隔符与引号：")
    sample = "id;name;salary\n1;张伟;18000\n2;李娜;12000\n"
    try:
        dialect = csv.Sniffer().sniff(sample)
        print(f"   探测到的 dialect:")
        print(f"     delimiter   = {dialect.delimiter!r}")
        print(f"     quotechar   = {dialect.quotechar!r}")
        print(f"     lineterminator = {dialect.lineterminator!r}")
        rows = list(csv.reader(io.StringIO(sample), dialect))
        print(f"   解析结果: {rows}")
    except csv.Error as e:
        print(f"   探测失败: {e}")
    print()

    print("⑥ Sniffer 的 has_header：探测首行是否为表头")
    # has_header 通过「列数一致性」与「类型差异」来猜测，**不可靠**
    with_header = "name,age\n张三,25\n李四,30\n"
    without_header = "1,25\n2,30\n"
    try:
        print(f"   有表头时 has_header = {csv.Sniffer().has_header(with_header)}")
    except csv.Error as e:
        print(f"   有表头时探测失败: {e}")
    try:
        print(f"   无表头时 has_header = "
              f"{csv.Sniffer().has_header(without_header)}")
    except csv.Error as e:
        print(f"   无表头时探测失败: {e}")
    print("   -> has_header 是启发式判断，生产环境不要依赖它")
    print()
    print("【要点】分隔符不确定时用 Sniffer；确定时直接指定 dialect 更可靠。")


def demo_7_malformed_rows():
    """不规则行的处理。"""
    print("=" * 74)
    print("【7】不规则行：字段数不一致的处理")
    print("=" * 74)

    # ===== 语法解析 =====
    # 现实中的 CSV 常有不规则行：
    #   - 字段多了（脏数据拼接）
    #   - 字段少了（末尾逗号缺失）
    #
    # DictReader 的两个专门参数：
    #   restkey   指定「多余字段存到哪个 key 下」（默认 None -> 直接丢）
    #   restval   指定「缺失字段用什么值填充」（默认 None -> 填 None）
    bad_csv = WORK_DIR / "irregular.csv"
    # 手工构造：不规则行 + 含换行的字段 + 含逗号的字段
    bad_csv.write_text(
        'id,name,dept\n'
        '1,张伟,技术部\n'
        '2,李娜,市场部,额外字段1,额外字段2\n'      # 字段多了
        '3,王强\n'                                  # 字段少了
        '4,"陈静,财务部",人事部\n'                # 字段内含逗号（不是多字段）
        '5,赵磊,\n',                               # dept 为空字符串
        encoding="utf-8")

    print(f"① 文件内容（真实的不规则 CSV）：")
    for line in bad_csv.read_text(encoding="utf-8").splitlines():
        print(f"   {line!r}")
    print()

    print("② 用 DictReader 读（默认行为：多余丢弃、缺失填 None）：")
    with open(bad_csv, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader, 1):
            print(f"   行{i}: {dict(row)}")
    print("   -> 行2 的多余字段被丢弃；行3 缺失的 dept 为 None")
    print()

    print("③ 用 restkey / restval 显式处理：")
    with open(bad_csv, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f, restkey="extra", restval="<缺失>")
        for i, row in enumerate(reader, 1):
            print(f"   行{i}: {dict(row)}")
    print("   -> restkey 把多余字段收进 'extra' 键（值是列表）")
    print("   -> restval 给缺失字段填默认值，避免下游处理 None")
    print()

    print("④ 主动校验字段数（推荐做法）：")
    with open(bad_csv, "r", encoding="utf-8", newline="") as f:
        reader = csv.reader(f)
        header = next(reader)
        expected = len(header)
        for lineno, row in enumerate(reader, start=2):
            if len(row) != expected:
                print(f"   第 {lineno} 行字段数异常: "
                      f"期望 {expected}, 实际 {len(row)} -> {row}")
    print("   -> 严格场景下应直接抛异常拒绝处理，而不是静默修正")
    print()

    print("⑤ 用 QUOTE_NONNUMERIC 读取时自动转数字：")
    num_csv = WORK_DIR / "numeric.csv"
    # 注意：读取端用 QUOTE_NONNUMERIC 时，**表头也必须加引号**，
    # 否则 csv 会尝试把 'id' 转成 float 而抛 ValueError。
    num_csv.write_text('"id","name","score","active"\n'
                       '"1","张伟","95.5","true"\n'
                       '"2","李娜","88","false"\n',
                       encoding="utf-8")
    with open(num_csv, "r", encoding="utf-8", newline="") as f:
        # 不加 quoting 时全部是 str
        for row in csv.DictReader(f):
            if row["id"] == "2":
                print(f"   默认模式: {dict(row)}")
                break
    with open(num_csv, "r", encoding="utf-8", newline="") as f:
        # quoting=QUOTE_NONNUMERIC 让 reader 尝试把字段转成 float/int
        reader = csv.DictReader(f, quoting=csv.QUOTE_NONNUMERIC)
        for row in reader:
            if row["id"] == 2:      # 此处 id 已是 int 2
                print(f"   NONNUMERIC: {dict(row)}")
                print(f"   类型: id={type(row['id']).__name__}, "
                      f"score={type(row['score']).__name__}")
                break
    print("   -> id 变成 int 2，score 变成 float 88.0，省去手动转换")
    print("   -> 前提：写入时表头也加引号，否则 reader 会尝试转换表头而崩溃")
    print("   -> 注意 '007' 会被转成 7，需要保留前导零时不要用这个选项")


def demo_8_streaming_large_file():
    """大文件的流式处理。"""
    print("=" * 74)
    print("【8】大文件的流式读写")
    print("=" * 74)

    # ===== 语法解析 =====
    # csv.reader 是惰性的：每次 next() 只解析一行，不把整个文件读进内存。
    # 因此处理千万行文件时，内存占用是常数级（只保留一行）。
    # 错误做法：f.readlines() 会把整个文件读成 list，内存爆炸。
    big_file = WORK_DIR / "big.csv"
    total_rows = 50000

    print(f"① 生成 {total_rows} 行的测试文件：")
    import time
    start = time.perf_counter()
    with open(big_file, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["id", "name", "amount"])
        # 用生成器 + writerows，避免手工 for 循环的样板代码
        writer.writerows(
            (i, f"用户{i}", i * 1.5) for i in range(total_rows)
        )
    elapsed = time.perf_counter() - start
    size_mb = big_file.stat().st_size / 1024 / 1024
    print(f"   耗时 {elapsed:.2f}s，大小 {size_mb:.2f} MB")
    print()

    print("② 流式统计（不把文件读进内存）：")
    start = time.perf_counter()
    count = 0
    total_amount = 0.0
    with open(big_file, "r", encoding="utf-8", newline="") as f:
        reader = csv.reader(f)
        next(reader)      # 跳过表头
        for row in reader:
            count += 1
            # 字符串转数字是流式处理的主要开销之一
            total_amount += float(row[2])
    elapsed = time.perf_counter() - start
    print(f"   处理 {count} 行，耗时 {elapsed:.2f}s")
    print(f"   金额合计 = {total_amount:.2f}")
    print(f"   平均 = {total_amount / count:.2f}")
    print(f"   内存占用：常数级（只有一行在内存中）")
    print()

    print("③ 对比：一次性读入内存（错误做法）：")
    start = time.perf_counter()
    with open(big_file, "r", encoding="utf-8", newline="") as f:
        all_lines = f.readlines()          # 整个文件进内存
    elapsed = time.perf_counter() - start
    print(f"   readlines() 读入 {len(all_lines)} 行，耗时 {elapsed:.2f}s")
    print(f"   内存中的字符数 = {sum(len(x) for x in all_lines):,}")
    print(f"   -> 文件再大 100 倍就会 OOM（内存不足）")
    print(f"   -> 流式方式只占几 KB，文件大小无关")
    del all_lines    # 及时释放
    print()

    print("④ 流式处理的推荐模式：")
    def summarize_csv(path, chunk=1000):
        """分块统计，返回汇总结果。全程不把数据累积到内存。"""
        with open(path, "r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            # 用生成器表达式做过滤/转换，保持惰性
            amounts = (float(r["amount"]) for r in reader)
            # itertools.islice 可以做惰性切片（06_itertools.py 详讲）
            import itertools
            sample = list(itertools.islice(amounts, 5))
            print(f"   前 5 个金额 = {sample}")
            # 注意：islice 消费了5 个元素，后续统计要重新读
            return sum(float(r["amount"]) for r in csv.DictReader(
                open(path, "r", encoding="utf-8", newline="")))

    total = summarize_csv(big_file)
    print(f"   重新统计总额 = {total:.2f}")
    print()

    print("【要点】csv.reader 是惰性迭代器，永远不要 readlines() 整个读入。")
    print("       流式处理的内存占用与文件大小无关，可以处理任意大的文件。")


def demo_9_pandas_style_helpers():
    """不依赖第三方库的实用辅助函数。"""
    print("=" * 74)
    print("【9】纯标准库实现的 CSV 辅助工具")
    print("=" * 74)

    # ===== 语法解析 =====
    # 没有 pandas 时，用标准库实现一些常用的表格操作。
    # 核心是用 csv.DictReader + 生成器 + 列表推导式组合。

    def load_csv(path, encoding="utf-8"):
        """读取整个 CSV 为 list[dict]（小文件才适用）。"""
        with open(path, "r", encoding=encoding, newline="") as f:
            # list(...) 消耗迭代器，得到所有行的 list
            return list(csv.DictReader(f))

    def filter_rows(rows, **conditions):
        """按字段值过滤。**conditions 是关键字参数。"""
        return [r for r in rows
                if all(r.get(k) == v for k, v in conditions.items())]

    def sort_rows(rows, key, reverse=False):
        """按字段排序，需要指定数值转换函数。"""
        # 字符串排序对数字不适用，所以用 key 函数转换
        return sorted(rows, key=lambda r: int(r[key]), reverse=reverse)

    def aggregate(rows, key, value_key, func=sum):
        """分组聚合。"""
        groups = {}
        for r in rows:
            groups.setdefault(r[key], []).append(float(r[value_key]))
        return {k: func(v) for k, v in groups.items()}

    rows = load_csv(SAMPLE_CSV)
    print(f"① 读取 {len(rows)} 行数据")
    print()

    print("② 过滤：dept=技术部")
    tech = filter_rows(rows, department="技术部")
    print(f"   技术部有 {len(tech)} 人: "
          f"{[r['name'] for r in tech]}")
    print()

    print("③ 排序：按薪资降序（前 5 名）")
    top5 = sort_rows(rows, "salary", reverse=True)[:5]
    for r in top5:
        print(f"     {r['name']:<6} {r['department']:<8} "
              f"薪资={int(r['salary']):,}")
    print()

    print("④ 聚合：各部门平均薪资")
    for dept, avg in aggregate(rows, "department", "salary",
                               func=lambda v: sum(v) / len(v)).items():
        print(f"     {dept:<8} 平均={avg:,.1f}")
    print()

    print("⑤ 组合使用：技术部高薪员工（薪资 > 20000）")
    tech_high = filter_rows(sort_rows(rows, "salary", reverse=True),
                           department="技术部")
    result = [r for r in tech_high if int(r["salary"]) > 20000]
    print(f"   {[(r['name'], int(r['salary'])) for r in result]}")
    print()
    print("【要点】这些函数足以应对中小规模 CSV；")
    print("       数据量大或需要复杂分析时应使用 pandas 等专业工具。")


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
    print("csv 模块：读写与格式陷阱")
    print("=" * 74)
    print(f"数据文件: {SAMPLE_CSV}")
    print(f"文件大小: {SAMPLE_CSV.stat().st_size} 字节")
    print()
    try:
        demo_1_reader_basic()
        print()
        demo_2_dictreader_writer()
        print()
        demo_3_newline_trap()
        print()
        demo_4_bom_problem()
        print()
        demo_5_quoting_rules()
        print()
        demo_6_dialect_and_sniffer()
        print()
        demo_7_malformed_rows()
        print()
        demo_8_streaming_large_file()
        print()
        demo_9_pandas_style_helpers()
    finally:
        cleanup()
    print()
    print("=" * 74)
    print("演示结束：三条铁律 —— newline=''、utf-8-sig、流式读取")
    print("=" * 74)


if __name__ == "__main__":
    main()