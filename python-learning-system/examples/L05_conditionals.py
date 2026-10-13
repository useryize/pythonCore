"""L05 条件分支 —— 配套教案配套示例。

运行：python examples/L05_conditionals.py

本脚本演示八件事：
    1. if / elif / else 的完整语义与「第一个成立的分支才执行」
    2. 比较运算组合、逻辑运算的短路求值
    3. 真值判断（Truthy / Falsy）：哪些值在 if 里等价于 False
    4. 三元表达式何时用、何时别用
    5. 嵌套的代价与「扁平化」重构手法
    6. match 语句（Python 3.10+）及其适用边界
    7. 三大高频坑：赋值写成判断、浮点比较、边界 off-by-one
    8. 一个完整业务案例：BMI 分级 + 折扣计算

⚠️ 纯标准库，可直接运行。
"""

import sys                                    # 标准库：判断当前 Python 是否支持 match

# ============================================================
# 模块级常量
# ============================================================
BMI_UNDERWEIGHT = 18.5                        # 偏瘦下界（含）
BMI_NORMAL = 24.0                             # 正常上界（含）
BMI_OVERWEIGHT = 28.0                         # 偏胖上界（含）
# 以上之外即为肥胖

SCORE_EXCELLENT = 90                          # 优秀下界
SCORE_GOOD = 80                               # 良好下界
SCORE_PASS = 60                               # 及格下界

VALID_GRADES = {"A", "B", "C", "D"}           # 合法等级集合，用集合做成员判断更快


# ============================================================
# 第 1 部分：if / elif / else 基础
# ============================================================
def demo_basic_if() -> None:
    """条件分支的核心语义：自上而下，找到第一个成立的分支就停。"""
    print("【基本结构】")
    score = 85
    if score >= 90:
        grade = "优秀"
    elif score >= 80:
        grade = "良好"
    elif score >= 60:
        grade = "及格"
    else:
        grade = "不及格"
    print(f"  score = {score} -> {grade}")

    print("\n【关键语义】从上到下判断，第一个成立的分支执行完就跳过所有 else")
    # 用一个带副作用的函数来证明「只执行一个分支」
    executed = []

    def probe(tag: str) -> bool:
        """记录自己被调用，并返回一个预设条件。"""
        executed.append(tag)
        return tag == "第二个"

    if probe("第一个"):
        print("    → 执行了第一个分支")
    elif probe("第二个"):
        print("    → 执行了第二个分支")
    elif probe("第三个"):
        print("    → 执行了第三个分支（不会被执行）")
    else:
        print("    → 执行了 else（不会被执行）")
    # 只有前两个被调用，第三个短路掉了
    print(f"  实际被调用: {executed}   ← 证明不会一次评估所有条件")

    print("\n【if 后面的冒号与缩进】")
    n = 10
    if n > 0:              # 冒号不能漏
        print("    n 是正数")   # 4 空格缩进表示「这行属于 if」
    # 缩进不一致会报 IndentationError，这是新手最常见的语法错误

    print("\n【条件里可以写任意表达式】")
    data = [3, 1, 4]
    if data and max(data) > 3:      # data 非空 且 最大值大于 3
        print(f"    列表非空且最大值 {max(data)} > 3")


def demo_multiple_conditions() -> None:
    """如何组合多个条件：and / or / not 的语义与短路。"""
    print("【and：所有条件都成立】")
    age, has_ticket = 20, True
    # and 可以连接任意多个条件，语义是「全部为真」
    if age >= 18 and has_ticket:
        print("    ✅ 成年且有票 → 允许入场")

    print("\n【or：任一条件成立即可】")
    is_vip, balance = False, 5
    # or 的优先级低于 and，混用时一定要加括号
    if is_vip or balance >= 10:
        print("    ✅ VIP 或余额充足")
    else:
        print("    ⚠️ 都不是，拒绝进入（余额需 ≥10 或 VIP）")

    print("\n【⚠️ and/or 的优先级陷阱】")
    # 没有括号时，实际解析为 is_vip or (balance >= 10 and has_permission)
    has_permission = False
    result_no_paren = is_vip or balance >= 10 and has_permission
    # 加上括号后，解析为 (is_vip or balance >= 10) and has_permission
    result_paren = (is_vip or balance >= 10) and has_permission
    print(f"  is_vip=False, balance=5, has_permission=False")
    print(f"  is_vip or balance >= 10 and has_permission  = {result_no_paren}")
    print(f"  (is_vip or balance >= 10) and has_permission = {result_paren}")
    print("  💡 结论：混用 and 和 or 时，括号不是「可选的美化」，而是「必须的正确性保障」")

    print("\n【not 的位置】")
    text = ""
    # not 是一元运算符，作用于紧跟其后的整个表达式
    if not text:
        print("    not text 为 True → 空字符串是 Falsy")
    # ⚠️ not 的优先级高于比较运算符
    # not a == b 等价于 (not a) == b
    value = 5
    print(f"\n  ⚠️ not value == None 解析为 (not value) == None → {(not value) == None}")
    print(f"  ✅ value is not None  → {value is not None}")


def demo_short_circuit() -> None:
    """短路求值：为什么它是「保护机制」而不只是优化。"""
    print("【短路求值的实际价值】")
    calls: list[str] = []

    def risky_a() -> bool:
        """模拟一个可能失败的操作（比如读文件、查数据库）。"""
        calls.append("a")
        return False

    def risky_b() -> bool:
        """模拟另一个可能失败的操作。"""
        calls.append("b")
        return True

    # and：左边 False 直接返回，右边根本不执行
    _ = risky_a() and risky_b()
    print(f"  risky_a() and risky_b() -> 实际调用了 {calls}")
    calls.clear()
    # or：左边 True 直接返回，右边根本不执行
    _ = risky_b() or risky_a()
    print(f"  risky_b() or risky_a()  -> 实际调用了 {calls}")
    calls.clear()

    print("\n【保护写法：把可能抛异常的操作放在后面】")
    config = {"user": {"name": "张三"}}
    # 左边判断嵌套字典是否存在，右边才真正取值 —— 顺序不能反
    if "user" in config and "name" in config["user"]:
        print(f"    ✅ 安全取值: {config['user']['name']}")
    # 反过来写：config["missing"] 先被求值，直接 KeyError
    try:
        _ = config["missing"] and config["missing"]["name"]
    except KeyError as exc:
        print(f"    ❌ 顺序写反: KeyError: {exc}")
    print("  💡 经验法则：不确定的检查放左边，昂贵的取值放右边；"
          "需要前置校验时，把校验条件写在 and 的左侧")


def demo_truthiness() -> None:
    """真值判断：哪些对象在 if 里等价于 False。"""
    print("【Truthy / Falsy 完整清单】")
    print("Falsy（共 10 种值）：\n")
    falsy = [
        ("False", False),          # 布尔假
        ("None", None),            # 空值
        ("0", 0),                  # 整数零
        ("0.0", 0.0),              # 浮点零
        ("0j", 0j),                # 复数零
        ("''", ""),                # 空字符串
        ("'\\x00' 之外的所有空白串", "   "),   # 只含空格的字符串也是 Falsy
        ("[]", []),                # 空列表
        ("{}", {}),                # 空字典
        ("set()", set()),          # 空集合
    ]
    for desc, value in falsy:
        print(f"  bool({desc:<24}) = {bool(value)}")

    print("\nTruthy（其余一切都是真的）：\n")
    truthy = [1, -1, 0.1, "0", "False", " ", [0], {"k": None}, {"a": 1}, {0}, (0,), object()]
    for value in truthy:
        print(f"  bool({repr(value):<24}) = {bool(value)}")

    print("\n【⚠️ 三个最反直觉的案例】")
    # 1. 非空字符串一律为 True，哪怕内容是 "0" 或 "False"
    print(f"  bool('0')    = {bool('0')}    ⚠️ 字符串 '0' 是 True！判断数字请用 isdigit()")
    print(f"  bool('False')= {bool('False')}⚠️ 字符串 'False' 也是 True！")
    print(f"  '0'.isdigit()= {'0'.isdigit()}  ✅ 正确的判断方式")
    # 2. 空容器为 False，长度为 0 的字符串也算空
    print(f"  bool(' ')    = {bool(' ')}    ⚠️ 只有空格的字符串仍是 True，必须 strip 后判断")
    print(f"  bool(' '.strip()) = {bool(' '.strip())}   strip 后才变 False")
    # 3. 函数和类对象永远为 True
    print(f"  bool(len)    = {bool(len)}    函数对象本身恒为 True")

    print("\n【实用写法：直接判断，不要和 True/False 比较】")
    data = [1, 2, 3]
    # ✅ 简洁
    print(f"  if data:            -> {bool(data)}")
    # ❌ 多余的 == True 会导致 numpy 数组等场景行为异常，且掩盖意图
    # print(f"  if data == True:    -> ", end="")
    print("  ⚠️ 不要写 if x == True:，会阻止自定义对象的「真值」语义生效")
    # ⚠️ 更隐蔽的陷阱：和 1/0 比较容易看错
    print(f"\n  ⚠️ 陷阱：is 1 和 == 1 的写法极易混淆，一律用 is True/False")


def demo_ternary() -> None:
    """三元表达式的适用场景与误用场景。"""
    print("【三元表达式：值1 if 条件 else 值2】")
    age = 20
    status = "成年" if age >= 18 else "未成年"
    print(f"  age={age} -> {status}")

    print("\n【适用 1：给变量提供默认值】")
    # 这是三元最地道的用法，替代 C 里的 ?: 或 JS 里的 ||
    for raw in ("", "  ", "Alice"):
        name = raw if raw else "默认名"
        print(f"  输入 {raw!r:8} -> {name}")

    print("\n【适用 2：二选一赋值】")
    score = 45
    result = "及格" if score >= 60 else "不及格"
    print(f"  {result}")

    print("\n【⚠️ 误用 1：多分支用嵌套三元，可读性崩溃】")
    n = 85
    # 能跑，但需要读者在脑内构建决策树
    bad = "A" if n >= 90 else "B" if n >= 80 else "C" if n >= 60 else "D"
    print(f"  嵌套三元: {bad}   ← 需要数括号，很难快速读懂")
    # 推荐用 if/elif
    if n >= 90:
        good = "A"
    elif n >= 80:
        good = "B"
    elif n >= 60:
        good = "C"
    else:
        good = "D"
    print(f"  if/elif : {good}   ✅ 层级一目了然")

    print("\n【⚠️ 误用 2：有副作用的三元（不要这么写）】")
    counter = {"n": 0}

    def bump() -> int:
        """带副作用的函数：计数并返回。"""
        counter["n"] += 1
        return counter["n"]

    # 三元的两个分支可能都有副作用，此时它不再是「纯取值」，行为难以预测
    print(f"  建议：三元只用于「选值」，不要在分支里做有副作用的操作")
    print(f"  当前 counter = {counter}（本函数没有真的调用 bump，避免演示混乱）")

    print("\n【⚠️ 误用 3：三元表达式里忘记加括号】")
    x = 1
    # ❌ 错误写法：label or ('A' if x else 'B')  —— 整体是 or 表达式
    print("  ❌ name or ('A' if cond else 'B')  解析为 name or (...)，语义完全不同")
    # ✅ 正确写法：整个三元必须整体加括号
    label = ""
    correct = label if label else ("A" if x else "B")
    print(f"  ✅ (name if name else (...))  -> {correct}")
    print("  💡 规则：三元作为子表达式出现在 or/and 里时，必须用括号包住整个三元式")


def demo_flattening() -> None:
    """嵌套 if 的问题与三种扁平化手法。"""
    print("【嵌套 if 的问题】")
    # 嵌套越深，缩进越深，代码块向右滑，逻辑越难读
    age, has_pass, is_vip = 20, False, False
    if age >= 18:
        if has_pass:
            if is_vip:
                access = "VIP 通道"
            else:
                access = "普通通道"
        else:
            access = "无票，拒绝"
    else:
        access = "未成年，禁止"
    print(f"  嵌套三层得到: {access}   ← 缩进已达 4 层，再深就失控了")

    print("\n【扁平化手法 1：合并条件用 and / or】")
    # 前提条件相同 → 用 and 合并到一层；否则用一个临时布尔变量「提取」共同条件
    is_adult_with_pass = age >= 18 and has_pass      # 提取中间结果到一个有意义的变量
    if is_adult_with_pass:
        if is_vip:
            access2 = "VIP 通道"
        else:
            access2 = "普通通道"
    else:
        access2 = "无权进入"
    print(f"  提取中间变量后只剩 2 层: {access2}")

    print("\n【扁平化手法 2：卫语句（guard clause）提前返回】")
    # 这是工程上最推荐的手法：把「异常情况」提前处理掉，让主干保持在最外层
    def check_access(age: int, has_pass: bool, is_vip: bool) -> str:
        """用卫语句写出的等价实现。"""
        if age < 18:                       # 卫语句 1：先挡掉未成年
            return "未成年，禁止"
        if not has_pass:                   # 卫语句 2：再挡掉无票
            return "无票，拒绝"
        if is_vip:                         # 剩余情况只需一层判断
            return "VIP 通道"
        return "普通通道"                   # 兜底
    print(f"  卫语句版本: {check_access(age, has_pass, is_vip)}   ← 全部在同一缩进层")
    print(f"  卫语句版本: {check_access(15, True, True)}       （提前返回未成年）")

    print("\n【扁平化手法 3：查表 / 字典映射替代 if 链】")
    # 连续判断「同一个变量」的不同取值时，用字典最清晰
    grade_map = {90: "A", 80: "B", 60: "C", 0: "D"}

    def lookup_grade(score: int) -> str:
        """用查表代替四级 if/elif。"""
        for threshold in sorted(grade_map, reverse=True):   # 从高到低找第一个满足的
            if score >= threshold:
                return grade_map[threshold]
        return "D"
    for s in (95, 85, 65, 30):
        print(f"  查表 {s:3} 分 -> {lookup_grade(s)}")


# ============================================================
# 第 2 部分：match 语句（Python 3.10+）
# ============================================================
def demo_match() -> None:
    """结构化模式匹配：什么时候用、什么时候不该用。"""
    print(f"当前 Python {sys.version_info.major}.{sys.version_info.minor}")
    if sys.version_info < (3, 10):
        print("⚠️ match 需要 3.10+，本机版本过低，跳过演示")
        return

    print("\n【match 处理「值的分发」：替代长 if/elif 链】")

    def handle_status(code: str) -> str:
        """用 match 把 HTTP 状态码风格的分发逻辑写清楚。"""
        match code:
            case "200":
                return "成功"
            case "404" | "403":           # | 表示「或」，多个值共用一个分支
                return "客户端错误"
            case "500" | "502":
                return "服务器错误"
            case _:                        # _ 是通配符，相当于 else
                return "未知状态码"
        # 注意：match 不需要写 break，也不需要写 return 之后的兜底

    for code in ("200", "404", "403", "500", "999"):
        print(f"  {code} -> {handle_status(code)}")

    print("\n【match 处理「类型 + 值的组合」：这是 if 做不到的】")

    def describe(item: object) -> str:
        """演示如何同时匹配类型和值 —— 这是 match 的真正杀手锏。"""
        match item:
            case None:                                   # 精确匹配 None
                return "空值"
            case int() | float() if item == 0:           # 带 if 守卫的类型匹配
                return "数字零"
            case int() | float():                         # 匹配任何数值
                return f"数字 {item}"
            case str() as text if text == "":             # as 绑定变量 + 守卫
                return "空字符串"
            case str() as text:                           # as 把匹配到的值绑到 text
                return f"字符串「{text}」"
            case [x, y]:                                  # 序列模式，固定长度 2
                return f"二元列表 [{x}, {y}]"
            case [x, *rest]:                              # *rest 匹配剩余所有元素
                return f"列表，首元素 {x}，其余 {len(rest)} 个"
            case {"type": "user", "name": str(name)}:     # 字典模式 + 类型约束
                return f"用户对象，姓名 {name}"
            case {"type": "user"}:                        # 字典模式，只看部分键
                return "用户对象（缺少姓名）"
            case _:                                       # 兜底
                return f"其他类型：{type(item).__name__}"
        # 编译期如果漏了 _ 分支且无法证明穷尽，静态检查工具会给出提示

    samples = [
        None, 0, 3.14, "", "hello", [1, 2], [1, 2, 3],
        {"type": "user", "name": "张三"}, {"type": "user"}, (1, 2),
    ]
    for s in samples:
        print(f"  {str(s):32} -> {describe(s)}")

    print("\n【match 的值捕获：把匹配到的值绑到变量】")
    command = {"action": "add", "name": "苹果", "count": 3}

    def run(cmd: dict) -> str:
        """演示字典模式 + 值捕获。"""
        match cmd:
            case {"action": "quit"}:
                return "退出程序"
            case {"action": "add", "name": str(name), "count": int(n)}:
                return f"添加 {name} × {n}"
            case {"action": "add", "name": str(name)}:
                return f"添加 {name}（数量默认 1）"
            case {"action": other}:
                return f"未知命令：{other}"
            case _:
                return "非法命令格式"
        return "未匹配"

    print(f"  完整命令 {command} -> {run(command)}")
    print(f"  缺字段   {{'action':'add','name':'香蕉'}} -> {run({'action': 'add', 'name': '香蕉'})}")
    print(f"  未知动作 {{'action':'fly'}} -> {run({'action': 'fly'})}")

    print("\n【⚠️ match 的三条使用边界】")
    print("  1) match 只做「一次判断后选定一个分支」，分支之间不互斥回退")
    print("     （对比 if/elif：if 条件不成立就继续试下一个，match 是从上到下第一个匹配的分支）")
    print("  2) 不要用它替代简单的数值判断——if x > 10 比 match 更直白")
    print("  3) 卫语句（guard）用 if 关键字，写在 case 后面：case x if x > 0:")
    value = -5
    match value:
        case v if v > 0:
            print(f"  带守卫的 case: {v} > 0")
        case v:
            print(f"  落入兜底: {v} 不大于 0（守卫不满足，会继续往下匹配）")

    # 验证「守卫不满足会继续往下匹配」这一点
    match 1:
        case n if n > 100:
            print("  不会到这里")
        case 1:
            print("  ✅ 验证：守卫不成立时，case 1 依然能匹配上")


# ============================================================
# 第 3 部分：三大高频坑
# ============================================================
def demo_pitfalls() -> None:
    """把条件分支最容易踩的坑集中演示。"""
    print("【坑 1】把赋值写成了判断")
    # ❌ 错误：if x = 5:  →  SyntaxError
    # 原因：= 是赋值语句，if 后面必须是表达式
    try:
        exec("if 1 = 5:\n    pass")
    except SyntaxError as exc:
        print(f"  if 1 = 5    -> SyntaxError: {exc.msg}")
    # 正确写法
    correct_value = 5
    if correct_value == 5:
        print("  if x == 5   ✅ 用 == 比较")
    # ⚠️ 高频真实场景：为了「顺手」在判断里赋值，导致逻辑永远为真
    print("\n  ⚠️ 真实翻现场景：")
    # 错误版本：if (result = compute()) > 0: —— result 恒为真值（0 也算 True？）
    # 实际上 0 是 Falsy，所以只会「碰巧」对，但一旦 compute() 返回非 0 就会永远进 if
    def compute_wrong() -> int:
        """错误示范：把赋值写进条件，条件永远为真。"""
        if result := -5:                      # 这里 result 恒为非 0 → 恒真
            print(f"    ❌ 恒真执行，result={result}（-5 也算 True）")
        return result
    compute_wrong()
    # 正确做法：先赋值，再判断
    def compute_right() -> int:
        """正确示范：赋值和判断分开写。"""
        result = -5
        if result > 0:                        # 明确表达「大于 0」的业务含义
            print(f"    ✅ 正确判断，result={result}")
        return result
    compute_right()

    print("\n【坑 2】浮点数用 == 比较")
    total = 0.1 + 0.2
    print(f"  0.1 + 0.2 == 0.3 -> {total == 0.3}   ❌ 二进制表示误差")
    print(f"  abs(差) < 1e-9    -> {abs(total - 0.3) < 1e-9}   ✅ 用容差")
    print(f"  范围判断写法（推荐）: {0.2 < total < 0.4}   ← 链式比较天然规避了 == 的问题")
    # 金额场景的根本解法：用整数存分
    print(f"  金额存分：19.9+19.9=39.8 → 用整数 1990+1990=3980 分，精确无误")

    print("\n【坑 3】边界 off-by-one（差一错误）】")
    print("  典型场景：判断「年龄在 18 到 60 之间」，包含还是不含？")
    for age in (17, 18, 60, 61):
        # 正确写法：明确写出两个边界和比较方向
        in_range = 18 <= age <= 60
        print(f"    age={age:3} -> 18 <= age <= 60 = {in_range}")
    print("\n  范围判断的四种写法对比（age=18 时）：")
    age = 18
    print(f"    18 < age <= 60   = {18 < age <= 60}  ⚠️ 排除 18，若业务包含 18 就错了")
    print(f"    18 <= age <= 60  = {18 <= age <= 60} ✅ 包含 18（链式比较的推荐写法）")
    print(f"    age > 17         = {age > 17}       ⭐ 最不容易错：把「包含 18」翻译成「大于 17」")
    print(f"    not (age <= 17)  = {not (age <= 17)} ⚠️ 双否定，可读性差")

    print("\n  ⚠️ 另一个经典：range 与索引的错位")
    data = ["A", "B", "C"]
    # 用 1-based 计数去索引 0-based 列表，是新手高频 off-by-one
    for i in range(1, len(data) + 1):
        # i 取到 len(data) 时越界，这就是 1-based 索引 0-based 列表的必然结果
        try:
            wrong_index = data[i]                 # ⚠️ 最后一个会越界
            print(f"    data[{i}] = {wrong_index!r}")
        except IndexError as exc:
            print(f"    data[{i}] -> IndexError: {exc}   ← 1-based 索引 0-based 列表的必然结果")
    print(f"    正确写法 data[i-1] = {data[1 - 1]!r}   （L07 会讲 enumerate 的正确用法）")


# ============================================================
# 第 4 部分：完整业务案例
# ============================================================
def calc_bmi(weight_kg: float, height_m: float) -> tuple[float, str]:
    """计算 BMI 并返回分级结果 —— 条件分支的标准应用。"""
    # 先做参数校验，这是所有业务函数的第一道防线
    if weight_kg <= 0 or height_m <= 0:
        raise ValueError("身高体重必须为正数")
    bmi = weight_kg / (height_m ** 2)          # BMI = 体重(kg) / 身高(m)²
    # 从高到低判断，用「下界包含」的方式避免边界重叠
    if bmi < BMI_UNDERWEIGHT:
        return bmi, "偏瘦"
    if bmi < BMI_NORMAL:
        return bmi, "正常"
    if bmi < BMI_OVERWEIGHT:
        return bmi, "偏胖"
    return bmi, "肥胖"


def calc_discount(level: str, amount: float, is_member: bool) -> float:
    """根据等级、金额、会员身份计算最终应付 —— 演示多条件组合。"""
    # 第一步：等级折扣，用字典查表（扁平化手法 3）
    level_rate = {"A": 0.85, "B": 0.90, "C": 0.95}
    if level not in level_rate:
        raise ValueError(f"未知等级：{level}")
    price = amount * level_rate[level]
    # 第二步：满减，用 and 合并两个条件
    if amount >= 1000 and is_member:
        price -= 50
    # 第三步：会员额外 9 折，注意顺序（先减后折 vs 先折后减结果不同）
    if is_member:
        price *= 0.9
    # ⚠️ 顺序陷阱：先折扣后减钱 和 先减钱后折扣 结果不一样
    # (amount * 0.9 - 50) ≠ (amount - 50) * 0.9
    return round(price, 2)


def demo_business_case() -> None:
    """把前面所有知识串成一个完整业务。"""
    print("【完整案例：健身俱乐部收费计算】")
    print("=" * 56)

    people = [
        ("张三", 55.0, 1.70, "B", False, 800),
        ("李四", 82.0, 1.75, "A", True, 1500),
        ("王五", 45.0, 1.60, "C", False, 500),
        ("赵六", 95.0, 1.68, "A", True, 2000),
    ]
    print(f"{'姓名':<6}{'身高m':<8}{'体重kg':<9}{'BMI':<8}{'分级':<8}{'等级':<6}{'应付':<10}")
    print("-" * 56)
    for name, weight, height, level, member, amount in people:
        bmi, grade = calc_bmi(weight, height)
        price = calc_discount(level, amount, member)
        print(f"{name:<6}{height:<8.2f}{weight:<9.1f}{bmi:<8.1f}{grade:<8}{level:<6}{price:<10.2f}")
    print("=" * 56)

    print("\n【参数校验演示】")
    try:
        calc_bmi(0, 1.75)
    except ValueError as exc:
        print(f"  calc_bmi(0, 1.75) -> ValueError: {exc}   ✅ 参数校验生效")

    print("\n【等级折扣表】")
    print("  A 级 8.5 折 / B 级 9 折 / C 级 9.5 折")
    print("  满 1000 且会员额外减 50 元，会员再打 9 折")

    print("\n【⚠️ 折扣顺序陷阱】")
    amount = 1000
    print(f"  金额 {amount}，同时满足「满 1000 减 50」和「会员 9 折」")
    order_a = (amount - 50) * 0.9          # 先减后折
    order_b = amount * 0.9 - 50            # 先折后减
    print(f"    先减后折 (amount-50)*0.9 = {order_a}")
    print(f"    先折后减 amount*0.9-50   = {order_b}")
    print(f"    差额 {abs(order_a - order_b):.2f} 元 → 业务含义不同，必须明确约定顺序")


# ============================================================
# 自我检验
# ============================================================
def verify_conditionals() -> None:
    """用断言确认条件分支的关键行为。"""
    # 基本判断
    assert (5 > 3) is True
    assert (5 < 3) is False
    # 真值判断
    assert bool(0) is False and bool("") is False and bool(None) is False
    assert bool([]) is False and bool({}) is False
    assert bool("0") is True and bool([0]) is True
    assert bool(-1) is True and bool(0.1) is True
    # 短路：and 左边为 False 时，右边整个表达式不会被求值
    calls: list[int] = []
    _ = (len(calls) > 0) and calls.append(1)   # 左边 False → append 根本不执行
    assert len(calls) == 0
    # 对照：or 左边为 True 时，右边同样不执行
    calls.clear()
    _ = (len(calls) == 0) or calls.append(1)   # 左边 True → append 根本不执行
    assert len(calls) == 0
    # 链式比较
    assert (1 < 2 < 3) is True and (1 < 3 < 2) is False
    assert (18 <= 18 <= 60) is True
    # 三元
    assert ("正" if 5 > 0 else "负") == "正"
    # and/or 优先级
    assert (False or True and False) is False       # True and False → False → False or False
    assert (False or (True and False)) is False
    # 浮点容差
    assert (0.1 + 0.2) != 0.3
    assert abs((0.1 + 0.2) - 0.3) < 1e-9
    # match（3.10+）
    if sys.version_info >= (3, 10):
        matched = "matched"
        match 1:
            case 1:
                matched = "yes"
        assert matched == "yes"
    print("✅ verify_conditionals 全部断言通过")


# ============================================================
# 程序入口
# ============================================================
def main() -> None:
    """按教学顺序调用全部演示函数。"""
    print("=" * 64)
    print("L05 · 条件分支")
    print("=" * 64)
    demo_basic_if()
    print("\n" + "-" * 64)
    demo_multiple_conditions()
    print("\n" + "-" * 64)
    demo_short_circuit()
    print("\n" + "-" * 64)
    demo_truthiness()
    print("\n" + "-" * 64)
    demo_ternary()
    print("\n" + "-" * 64)
    demo_flattening()
    print("\n" + "-" * 64)
    if sys.version_info >= (3, 10):
        demo_match()
        print("\n" + "-" * 64)
    demo_pitfalls()
    print("\n" + "-" * 64)
    demo_business_case()
    print("\n" + "-" * 64)
    verify_conditionals()
    print("\n🎉 L05 演示结束")


# 标准入口约定：直接运行本文件执行 main()，被 import 时不执行
if __name__ == "__main__":
    main()
