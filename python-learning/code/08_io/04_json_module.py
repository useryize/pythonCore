#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
json 模块：序列化与反序列化
================================================

【配套数据文件】
- data/sample.json：含嵌套结构、中文、布尔值、null 的测试数据

【演示的语法点】
1. json.dumps / json.loads：最基本的一对
2. ensure_ascii 的作用（中文是否转义成 \uXXXX）
3. indent 参数：格式化输出与体积对比
4. separators：紧凑输出
5. sort_keys：键排序（输出稳定，便于 diff）
6. 其他参数：skipkeys / allow_nan / default / cls
7. json.dump / json.load：直接读写文件
8. 文件读写时的三个坑：encoding / ensure_ascii / 中文字符
9. dataclass ↔ JSON 的双向转换（asdict / 自定义编解码）
10. json.JSONDecodeError 的定位信息
11. JSON 的优点与缺点（对比其他格式）

【预期输出摘要】
- dumps/loads 基础往返
- ensure_ascii=True vs False 的实际输出对比
- indent=None vs 2 的字节数对比
- compact separators 输出
- 文件读写的完整流程与陷阱演示
- dataclass -> JSON -> dataclass 往返验证
- JSON 优缺点总结表
"""

import json
import os
from dataclasses import dataclass, field, asdict
from datetime import datetime
from decimal import Decimal
from pathlib import Path


DATA_DIR = Path(__file__).parent / "data"
SAMPLE_JSON = DATA_DIR / "sample.json"
WORK_DIR = Path(__file__).parent / "_tmp_json"
WORK_DIR.mkdir(exist_ok=True)


# ===== 语法解析 =====
# 【1】json 模块的两组 API
#   dumps(obj) -> str    对象 -> JSON 字符串
#   loads(str) -> obj    JSON 字符串 -> Python 对象
#   dump(obj, fp)        对象 -> 文件
#   load(fp) -> obj      文件 -> 对象
#
# 【2】Python <-> JSON 的类型映射表（必须记住）
#   Python                JSON
#   dict                -> object
#   list / tuple        -> array       （注意 tuple 也变 list）
#   str                 -> string
#   int / float         -> number
#   True / False        -> true / false
#   None                -> null
#   （反方向：JSON 的 object 总是 dict，array 总是 list）
#
# 【3】json 只支持「基础类型」
#   datetime / Decimal / 自定义类 / set / 复杂对象都不能直接序列化，
#   需要自定义 default 函数（dump）或自定义 encoder 类。
def demo_1_basic_dumps_loads():
    """dumps / loads 基础用法与类型映射。"""
    print("=" * 74)
    print("【1】dumps / loads 基础用法与类型映射")
    print("=" * 74)

    # ===== 语法解析 =====
    # dumps 把 Python 对象转成 JSON 字符串
    data = {
        "name": "张伟",
        "age": 30,
        "salary": 18500.5,
        "is_active": True,
        "manager": None,
        "skills": ["Python", "Go", "C++"],
        "address": {"city": "北京", "district": "海淀区"},
        # tuple 在 JSON 中会变成 array
        "scores": (90, 85, 92),
    }
    print("① 原 Python 对象（dict）：")
    for k, v in data.items():
        print(f"   {k:<12} {type(v).__name__:<10} {v!r}")
    print()

    print("② dumps 结果（紧凑格式，无 indent）：")
    text = json.dumps(data)
    print(f"   {text}")
    print(f"   类型 = {type(text).__name__}, 长度 = {len(text)} 字符")
    print()

    print("③ 往返验证：loads(dumps(x)) 是否等于 x：")
    back = json.loads(text)
    print(f"   往返后相等: {back == data}")
    print(f"   注意 tuple 变成了 {type(back['scores']).__name__}: {back['skills']!r}")
    print("   -> tuple -> list 是单向的，所以 dict 比较时不相等")
    print(f"   原始 skills 类型 = {type(data['scores']).__name__}, "
          f"往返后 = {type(back['scores']).__name__}")
    print("   -> 把 tuple 换成 list 就能相等: "
          f"{ {**data, 'scores': list(data['scores'])} == back }")
    print()

    print("④ 类型映射对照：")
    mapping = [
        ("Python", "JSON", "往返后 Python"),
        ("dict", "object", "dict（顺序保留）"),
        ("list", "array", "list"),
        ("tuple", "array", "list  ← 类型丢失！"),
        ("str", "string", "str"),
        ("int", "number", "int"),
        ("float", "number", "float"),
        ("True", "true", "True"),
        ("False", "false", "False"),
        ("None", "null", "None"),
    ]
    for i, row in enumerate(mapping):
        sep = "-" * 60 if i == 0 else ""
        print(f"   {row[0]:<10} -> {row[1]:<8} -> {row[2]}")
        if sep:
            print(sep)
    print()
    print("   不支持直接转换的类型：datetime / Decimal / set / 自定义类")
    print(f"   尝试 dumps 一个 set: ", end="")
    try:
        json.dumps({1, 2, 3})
    except TypeError as e:
        print(f"TypeError: {e}")
    print()
    print("【要点】tuple 和 set 无法无损往返（set 直接报错）。")
    print("       需要 set 时，往返前手动转 list。")


def demo_2_ensure_ascii_and_indent():
    """ensure_ascii / indent / separators / sort_keys。"""
    print("=" * 74)
    print("【2】格式化参数：ensure_ascii / indent / separators / sort_keys")
    print("=" * 74)

    chinese_data = {"name": "张伟", "city": "北京", "desc": "中文描述"}

    # ===== 语法解析 =====
    # ensure_ascii（默认 True）：
    #   True  -> 所有非 ASCII 字符转义成 \uXXXX（JSON 规范兼容 ASCII）
    #   False -> 直接输出原文字符（UTF-8 文件可读性好，体积更小）
    print("① ensure_ascii 的效果：")
    ascii_text = json.dumps(chinese_data, ensure_ascii=True)
    utf8_text = json.dumps(chinese_data, ensure_ascii=False)
    print(f"   True （默认）: {ascii_text}")
    print(f"   False       : {utf8_text}")
    print(f"   长度: True={len(ascii_text)} 字符, False={len(utf8_text)} 字符")
    print("   -> \\uXXXX 每个汉字占 6 个字符，实际 UTF-8 只需 3 字节")
    print()

    print("② indent 参数：缩进格式化：")
    nested = {"公司": {"名称": "示例科技", "部门": [{"id": 1, "名称": "技术部"}]}}
    for indent_val in [None, 0, 2, 4]:
        text = json.dumps(nested, ensure_ascii=False, indent=indent_val)
        label = "None（紧凑）" if indent_val is None else f"{indent_val}"
        lines = len(text.splitlines())
        print(f"   indent={label:<14} 字符数={len(text):<5} 行数={lines}")
    print()

    print("   indent=2 的实际输出：")
    pretty = json.dumps(nested, ensure_ascii=False, indent=2)
    for line in pretty.splitlines():
        print(f"   {line}")
    print()

    # ===== 语法解析 =====
    # indent 的副作用是「分隔符也变了」：
    #   indent=None 时用 (', ', ': ')  （逗号后有空格）
    #   indent=2   时用 (',', ': ')    （逗号后无空格）
    # 原因是带缩进时已有换行+空格，不需要额外的空格。
    print("③ separators：自定义紧凑程度")
    separators_options = [
        ("默认(无indent)", None),
        ("极紧凑", (",", ":")),
        ("标准紧凑", (",", ":")),
    ]
    for label, sep in separators_options[1:]:
        text = json.dumps(nested, ensure_ascii=False, separators=sep)
        print(f"   {label:<14} {text}")
    print()

    print("④ sort_keys：保证输出顺序稳定")
    unordered = {"zebra": 1, "apple": 2, "banana": 3, "Orange": 4}
    print(f"   不排序: {json.dumps(unordered, ensure_ascii=False)}")
    print(f"   排序后: {json.dumps(unordered, ensure_ascii=False, sort_keys=True)}")
    print("   -> sort_keys 对【字符串】按字典序排序（大写在小写前）")
    print("   -> 稳定输出让 git diff 友好，配置文件改动一目了然")
    print()

    print("⑤ 其他实用参数：")
    # skipkeys=True 时，遇到无法作为 key 的类型会跳过而不是报错
    # （dict 的 key 必须是 str/int/float/bool/None）
    weird_keys = {"正常键": 1, 123: "int键", None: "None键"}
    print(f"   含各种类型的 key: {list(weird_keys.keys())}")
    try:
        json.dumps(weird_keys)
    except TypeError as e:
        print(f"   默认会报错: TypeError: {e}")
    text = json.dumps(weird_keys, skipkeys=True)
    print(f"   skipkeys=True: {text}  -> 非法的 key 被跳过了")
    print()

    # allow_nan：Python 默认允许 NaN/Infinity，但这不是合法 JSON
    float_special = {"normal": 1.5, "nan": float("nan"), "inf": float("inf")}
    text = json.dumps(float_special)
    print(f"   默认允许 NaN: {text}")
    print("   -> 注意这是【伪 JSON】，标准 JSON 解析器无法读取")
    try:
        json.dumps(float_special, allow_nan=False)
    except ValueError as e:
        print(f"   allow_nan=False: ValueError: {e}")
    print()


def demo_3_unsupported_types():
    """不支持的类型与 default / cls 参数。"""
    print("=" * 74)
    print("【3】自定义类型序列化：default 参数与 JSONEncoder")
    print("=" * 74)

    # ===== 语法解析 =====
    # default 参数：传入一个「兜底转换函数」。
    # json 遇到不认识的对象时，会调用 default(obj) 获取可序列化的替代值。
    # 这个函数只在遇到未知类型时才被调用（性能友好）。
    class Student:
        def __init__(self, name, score, tags):
            self.name = name
            self.score = score
            self.tags = tags

    def custom_encoder(obj):
        """把不支持的类型转成可序列化的形式。"""
        if isinstance(obj, datetime):
            # datetime 转 ISO 8601 字符串（标准做法）
            return obj.isoformat()
        if isinstance(obj, Decimal):
            # Decimal 转 float（注意精度损失）
            return float(obj)
        if isinstance(obj, Student):
            # 自定义类转成 dict
            return {
                "name": obj.name,
                "score": obj.score,
                "tags": list(obj.tags),   # set 必须转 list
            }
        if isinstance(obj, (set, frozenset)):
            return sorted(obj)
        if isinstance(obj, bytes):
            # bytes 常见处理：base64 或十六进制
            return obj.decode("utf-8", errors="replace")
        # 兜底：调用对象的 __dict__（对普通对象有效）
        if hasattr(obj, "__dict__"):
            return obj.__dict__
        # 必须返回可序列化的对象，否则抛 TypeError
        raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")

    complex_data = {
        "created_at": datetime(2026, 1, 15, 10, 30, 0),
        "amount": Decimal("12345.67"),
        "student": Student("王强", 95.5, {"数学", "物理"}),
        "unique_tags": {"a", "b", "c"},
        "blob": "字节数据".encode("utf-8"),
    }

    print("① 用 default 参数序列化复杂对象：")
    text = json.dumps(complex_data, default=custom_encoder,
                      ensure_ascii=False, indent=2)
    for line in text.splitlines():
        print(f"   {line}")
    print()

    print("② 验证往返：注意哪些信息丢失了")
    back = json.loads(text)
    print(f"   created_at -> {back['created_at']!r} ({type(back['created_at']).__name__})")
    print(f"   amount     -> {back['amount']!r} ({type(back['amount']).__name__})")
    print(f"   unique_tags-> {back['unique_tags']!r} ({type(back['unique_tags']).__name__})")
    print("   -> datetime 变字符串、Decimal 变 float、set 变 list，都是单向的")
    print()

    print("③ cls 参数：使用自定义编码器类：")
    class MyEncoder(json.JSONEncoder):
        """继承 JSONEncoder，覆盖 default 方法。"""

        def default(self, o):
            # 优先处理 Decimal，保证精度（转字符串而非 float）
            if isinstance(o, Decimal):
                return str(o)
            if isinstance(o, datetime):
                return o.strftime("%Y-%m-%d %H:%M:%S")
            # 复用父类的兜底逻辑
            return super().default(o)

    text2 = json.dumps({"amount": Decimal("12345.67"),
                        "created_at": datetime(2026, 1, 15, 10, 30)},
                       cls=MyEncoder, ensure_ascii=False)
    print(f"   {text2}")
    print("   -> Decimal 转字符串保留了精确精度")
    print("   -> custom_encoder 做不到这一点，因为它只能返回可序列化类型")
    print()

    print("④ object_hook：反序列化的自定义（对应 cls 的反向操作）：")
    # object_hook 在 loads 时对每个 JSON object 调用，
    # 返回值会替换该 object，可用于自动把 dict 转成 dataclass。
    def parse_json(pairs):
        """把 {'name': 'x', 'score': 1} 这样的 dict 转成 Student。"""
        d = dict(pairs)
        if set(d.keys()) == {"name", "score"}:
            return Student(d["name"], d["score"], set())
        return d

    demo_json = '{"obj": {"name": "李娜", "score": 88.0}, "other": 123}'
    result = json.loads(demo_json, object_hook=parse_json)
    print(f"   结果类型: {type(result['obj']).__name__}, "
          f"其他键类型: {type(result['other']).__name__}")
    print(f"   obj 的 score = {result['obj'].score}")
    print()
    print("【要点】default/cls 解决「对象 -> JSON」，object_hook 解决反向。")
    print("       两者都需要自己处理「信息丢失」的问题（类型不可逆）。")


def demo_4_file_io():
    """json 文件读写与三个典型陷阱。"""
    print("=" * 74)
    print("【4】json 文件读写与典型陷阱")
    print("=" * 74)

    # ===== 语法解析 =====
    # json.dump(obj, fp) 直接写入文件对象，省去手工 open/close；
    # json.load(fp) 直接从文件对象读取。
    # 但依然需要自己处理 with 语句与 encoding。
    print("① json.load 读取配套数据文件：")
    with open(SAMPLE_JSON, "r", encoding="utf-8") as f:
        data = json.load(f)
    print(f"   顶层键: {list(data.keys())}")
    print(f"   公司信息: {data['company']}")
    print(f"   部门数量: {len(data['departments'])}")
    print(f"   第一个部门: {data['departments'][0]['name']}")
    print(f"   该部门的项目数: {len(data['departments'][0]['projects'])}")
    print(f"   嵌套深度示例 -> 项目 tags: "
          f"{data['departments'][0]['projects'][0]['tags']}")
    print(f"   null 字段: {data['null_field']!r} "
          f"(Python 中是 {type(data['null_field']).__name__})")
    print()

    print("② json.dump 写入文件：")
    out_file = WORK_DIR / "output.json"
    payload = {
        "导出时间": datetime(2026, 1, 15, 10, 30).isoformat(),
        "员工": [{"姓名": "张伟", "薪资": 18500.5},
                {"姓名": "李娜", "薪资": 12000.0}],
        "统计": {"总人数": 2, "平均薪资": 15250.25},
    }
    with open(out_file, "w", encoding="utf-8") as f:
        # dump 的第四个参数是 indent，与 dumps 一致
        json.dump(payload, f, ensure_ascii=False, indent=2)
    print(f"   文件内容前 3 行:")
    for line in out_file.read_text(encoding="utf-8").splitlines()[:4]:
        print(f"   {line}")
    print(f"   文件大小 = {out_file.stat().st_size} 字节")
    print()

    print("③ 陷阱一：ensure_ascii 未设置导致文件可读性差")
    bad_file = WORK_DIR / "ascii.json"
    with open(bad_file, "w", encoding="utf-8") as f:
        json.dump(payload, f)     # 默认 ensure_ascii=True
    print(f"   默认写入的前 200 字符：")
    print(f"   {bad_file.read_text(encoding='utf-8')[:200]}")
    print("   -> 中文全部变成 \\uXXXX，人根本没法看")
    print(f"   文件大小 = {bad_file.stat().st_size} 字节")
    print()

    print("④ 陷阱二：忘记 encoding 导致 Windows 中文乱码")
    # 正确：用 utf-8
    with open(WORK_DIR / "ok.json", "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False)
    # 错误：不指定 encoding（使用平台默认值）
    default_enc = None
    try:
        with open(WORK_DIR / "bad_enc.json", "w") as f:
            json.dump(payload, f, ensure_ascii=False)
        default_enc = "未指定(平台默认)"
    except Exception as e:
        default_enc = f"错误: {e}"
    print(f"   不指定 encoding: {default_enc}")
    print("   -> Windows 简体中文环境下平台默认是 GBK，用 UTF-8 读取会乱码")
    print()

    print("⑤ 陷阱三：写入的 JSON 不是合法 JSON")
    # NaN/Infinity 是 Python 的扩展，标准 JSON 不允许
    bad_json = WORK_DIR / "nan.json"
    with open(bad_json, "w", encoding="utf-8") as f:
        json.dump({"value": float("nan")}, f)
    content = bad_json.read_text(encoding="utf-8")
    print(f"   写入的内容: {content.strip()}")
    print("   -> NaN 不是合法 JSON，JavaScript 的 JSON.parse 会报错")
    # 验证
    try:
        json.loads(content, parse_constant=lambda s: (_ for _ in ()).throw(
            ValueError(f"非法常量: {s}")))
    except ValueError as e:
        print(f"   验证: {e}")
    print()

    print("⑥ 读取失败时的错误信息：")
    for bad_text in ['{"key": }', '{key: "value"}', '[1, 2,]', 'not json',
                     '{"a": 1']:
        try:
            json.loads(bad_text)
            result = "解析成功"
        except json.JSONDecodeError as e:
            result = (f"{type(e).__name__}: {e.msg} "
                      f"(pos={e.pos}, line={e.lineno}, col={e.colno})")
        print(f"   {bad_text!r:<18} -> {result}")
    print()
    print("【要点】JSON 文件读写铁律：with + encoding='utf-8' + "
          "ensure_ascii=False + indent=2。")
    print("       indent=2 让人能读懂，代价是文件大约大三倍。")


def demo_5_dataclass_conversion():
    """dataclass 与 JSON 的双向转换。"""
    print("=" * 74)
    print("【5】dataclass <-> JSON 双向转换")
    print("=" * 74)

    # ===== 语法解析 =====
    # dataclass 是 Python 3.7+ 提供的「轻量类」：
    #   @dataclass 自动生成 __init__ / __repr__ / __eq__
    #   asdict(obj) 递归把 dataclass 转成 dict（dataclasses 内置）
    #
    # 转换方向：
    #   dataclass -> JSON : asdict() -> json.dumps()
    #   JSON -> dataclass : json.loads() -> cls(**data)
    # 注意 cls(**data) 要求 JSON 的键与 dataclass 字段名完全对应。

    @dataclass
    class Project:
        """项目。"""
        name: str
        status: str
        progress: float
        members: list = field(default_factory=list)
        tags: set = field(default_factory=set)
        # 嵌套 dataclass：asdict 会自动递归转换
        owner: "Employee" = None

    @dataclass
    class Employee:
        """员工。"""
        id: int
        name: str
        salary: float
        # Optional 类型用 | None 或 Optional[X]
        manager: str = None

    # 构造嵌套对象
    boss = Employee(id=1, name="王总", salary=50000.0)
    emp = Employee(id=100, name="张伟", salary=18500.5, manager="王总")
    proj = Project(
        name="订单中心重构",
        status="in_progress",
        progress=0.65,
        members=["张伟", "王强", "李娜"],
        tags={"重构", "核心"},
        owner=boss,          # 嵌套对象
    )

    print("① dataclass 对象（自动生成的 repr）：")
    print(f"   {proj}")
    print()

    print("② dataclass -> dict（asdict 递归）：")
    d = asdict(proj)
    print(f"   {d}")
    print(f"   注意 tags 变成了 {type(d['tags']).__name__}（set 被转成 list/frozenset）")
    print(f"   owner 被递归转换: {d['owner']}")
    print()

    print("③ dict -> JSON 字符串：")
    # asdict 之后 set 仍是 set，需要处理；用 default 兜底
    text = json.dumps(d, default=lambda o: sorted(o) if isinstance(o, set) else str(o),
                      ensure_ascii=False, indent=2)
    for line in text.splitlines():
        print(f"   {line}")
    print()

    print("④ JSON -> dict -> dataclass（反向）：")
    # 模拟从外部 API 拿到的 JSON
    api_json = '''
    {
        "id": 200,
        "name": "李娜",
        "salary": 12000.0,
        "manager": "王总"
    }
    '''
    data = json.loads(api_json)
    print(f"   原始 dict: {data}")
    # cls(**data) 用关键字参数展开，这是最简洁的反序列化方式
    emp2 = Employee(**data)
    print(f"   转成 dataclass: {emp2}")
    print(f"   类型 = {type(emp2).__name__}")
    print(f"   可以用属性访问: emp2.name = {emp2.name}")
    print()

    print("⑤ 字段不匹配时会怎样：")
    try:
        Employee(**{"id": 1, "name": "王强"})
    except TypeError as e:
        print(f"   缺少 salary -> TypeError: {e}")
    try:
        Employee(**{"id": 1, "name": "王强", "salary": 1, "extra": 2})
    except TypeError as e:
        print(f"   多余字段   -> TypeError: {e}")
    print("   -> 需要过滤未知字段，或给 dataclass 加默认值")
    print()

    print("⑥ 稳健的反序列化：过滤未知字段 + 填充默认值")
    def from_dict(cls, data):
        """按 dataclass 的字段列表过滤输入，创建实例。"""
        # fields(cls) 返回所有 Field 对象，用 f.name 拿到字段名字符串
        field_names = {f.name for f in dataclasses_fields(cls)}
        # 只保留已知字段，多余的自动丢弃
        filtered = {k: v for k, v in data.items() if k in field_names}
        return cls(**filtered)

    from dataclasses import fields as dataclasses_fields

    messy = {"id": 300, "name": "赵磊", "salary": 26000.0,
             "未知字段": "会被丢弃", "另一未知": [1, 2, 3]}
    emp3 = from_dict(Employee, messy)
    print(f"   输入: {messy}")
    print(f"   输出: {emp3}")
    print()

    print("⑦ 嵌套结构的稳健反序列化（自底向上）：")
    nested_json = '''
    {
        "id": 400,
        "name": "孙梅",
        "salary": 11000.0,
        "manager": "王总",
        "projects": [{"name": "活动策划", "status": "done", "progress": 1.0}],
        "owner": {"id": 1, "name": "王总", "salary": 50000.0}
    }
    '''
    raw = json.loads(nested_json)
    # 先转嵌套的 owner，再转外层
    owner_obj = from_dict(Employee, raw.pop("owner"))
    projects = [Project(**p) for p in raw.pop("projects")]
    raw.pop("unknown", None)
    main_emp = from_dict(Employee, raw)
    print(f"   主对象: {main_emp}")
    print(f"   owner: {owner_obj}")
    print(f"   projects: {projects}")
    print()
    print("【要点】dataclass <-> JSON 需要手工处理 set 和嵌套结构，")
    print("       因为 json 模块不认 dataclass，只能认出 dict 和 list。")


def demo_6_json_pros_cons():
    """JSON 的优缺点与选型对比。"""
    print("=" * 74)
    print("【6】JSON 的优缺点与格式对比")
    print("=" * 74)

    # ===== 语法解析 =====
    # JSON 的定位：「人类可读 + 机器可解析」的轻量数据交换格式。
    # 它的优点解决了 XML 的臃肿，缺点是类型系统太弱。

    pros = [
        "语法简单：只有对象/数组/字符串/数字/布尔/null 五种类型",
        "人类可读：结构清晰，缩进后直接能看懂",
        "跨语言：几乎所有语言都有内置解析器（JavaScript 原生支持）",
        "体积适中：比 XML 小得多（没有标签闭合与命名空间）",
        "生态成熟：JSON Schema 可定义校验规则，工具链完善",
    ]
    cons = [
        "无注释：标准 JSON 不支持 // 或 /* */ 注释",
        "无类型：数字都是 double，日期要靠约定（ISO 8601 字符串）",
        "不支持二进制：需要 base64 编码，体积膨胀约 33%",
        "不支持二进制以外的高级类型：日期、正则、Decimal 都要特殊处理",
        "冗余字段：结构相同的对象会重复写 key，压缩率低于列式存储",
        "精度问题：大整数超过 2^53 会被 JavaScript 丢失精度",
    ]

    print("① JSON 的优点：")
    for i, item in enumerate(pros, 1):
        print(f"   {i}. {item}")
    print()

    print("② JSON 的缺点：")
    for i, item in enumerate(cons, 1):
        print(f"   {i}. {item}")
    print()

    print("③ 大整数精度问题（JSON 的经典坑）：")
    # JSON 规范里数字没有整数/小数之分，JavaScript 全部按 double 解析
    big_id = 12345678901234567890     # 20 位，远超 2^53
    text = json.dumps({"id": big_id})
    print(f"   Python: {big_id}")
    print(f"   JSON 文本: {text}")
    back = json.loads(text)
    print(f"   Python 往返后: {back['id']}")
    print(f"   值相等: {back['id'] == big_id}")
    print("   -> 但 JavaScript JSON.parse 会丢精度（超过 2^53）")
    print(f"   -> 解决方案：把大整数当字符串传输 -> "
          f"{json.dumps({'id': str(big_id)})}")
    print()

    print("④ JSON 无注释的应对：许多工具支持「JSONC」（带注释的 JSON）")
    jsonc = '''{
        // 这是注释（标准 JSON 不允许，但很多工具支持）
        "name": "张伟",  /* 块注释 */
        "age": 30
    }'''
    try:
        json.loads(jsonc)
        print("   标准 json 模块竟然能解析带注释的？")
    except json.JSONDecodeError as e:
        print(f"   标准 json.loads 会报错: {e.msg}")
    print("   -> VS Code 的 settings.json 就是 JSONC，需要工具专门支持")
    print()

    print("⑤ 格式对比表：")
    table = [
        ("格式", "可读性", "体积", "类型支持", "标准库支持"),
        ("JSON", "高", "中", "弱（5 种类型）", "json ★★★"),
        ("XML", "高", "大", "强（可自定义标签）", "xml.etree ★★"),
        ("YAML", "很高", "小", "中（支持日期/多文档）", "无（需 PyYAML）"),
        ("TOML", "高", "小", "强（原生日期时间）", "tomllib ★★ (3.11+)"),
        ("CSV", "中", "最小", "无（只有字符串）", "csv ★★★"),
        ("pickle", "无", "小", "最强（任意 Python 对象）", "pickle ★★★"),
        ("MessagePack", "无", "很小", "中（二进制编码）", "无"),
    ]
    widths = [14, 8, 8, 22, 18]
    for i, row in enumerate(table):
        print("".join(c.ljust(w) for c, w in zip(row, widths)))
        if i == 0:
            print("-" * 70)
    print()
    print("【选型建议】")
    print("   API 接口      -> JSON（几乎唯一选择，浏览器原生支持）")
    print("   配置文件      -> TOML（Python 3.11+ 内置）/ YAML（可读性优先）")
    print("   纯表格数据-> CSV（体积最小，可被 Excel 直接打开）")
    print("   Python 内部缓存 -> pickle（最快，但不可跨版本、不可信来源）")
    print("   跨语言高性能   -> MessagePack / Protocol Buffers")


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
    print("json 模块：序列化与反序列化")
    print("=" * 74)
    print(f"数据文件: {SAMPLE_JSON}")
    print()
    try:
        demo_1_basic_dumps_loads()
        print()
        demo_2_ensure_ascii_and_indent()
        print()
        demo_3_unsupported_types()
        print()
        demo_4_file_io()
        print()
        demo_5_dataclass_conversion()
        print()
        demo_6_json_pros_cons()
    finally:
        cleanup()
    print()
    print("=" * 74)
    print("演示结束：JSON 的四个铁律 —— utf-8 / ensure_ascii=False / indent=2 / 不用 NaN")
    print("=" * 74)


if __name__ == "__main__":
    main()