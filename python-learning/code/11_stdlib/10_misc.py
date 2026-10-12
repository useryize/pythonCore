"""
================================================================================
 10_misc.py  ——  杂项工具库：uuid / hashlib / base64 / random / statistics
================================================================================

【演示的语法点】
 1. uuid：uuid1/uuid4/uuid3/uuid5 的语义差异，UUID 对象与字符串互转
 2. hashlib：md5 / sha1 / sha256 的选择，digest 与 hexdigest，hash_file
 3. ★ hashlib 实战：基于 sha256 的文件内容去重（含分块读取，避免大文件占内存）
 4. base64：encodebytes / b64encode / urlsafe_b64encode 的用途差异
 5. random：random / randint / choice / sample / shuffle / randbytes 的语义
 6. random 的正确用法：seed 只影响 Mersenne Twister，密码场景请用 secrets
 7. statistics：mean / median / mode / stdev / variance / quantiles
 8. copy：浅拷贝 / 深拷贝 / 嵌套结构的区别与内存地址验证
 9. pprint：pprint vs print vs pformat，sort_dicts 参数
10. sys / os 常用接口：sys.argv / sys.exit / sys.path / os.environ / os.walk
11. ★ 时间测量：time.perf_counter / perf_counter_ns / time / monotonic 对比
12. 计时装饰器的实现（工程常用套路）

【预期输出摘要】
 - "hashlib" 小节：同一份数据三种算法摘要不同，文件去重发现重复文件
 - "copy" 小节：浅拷贝中修改内层 dict 会影响原对象，深拷贝不会
 - "perf_counter" 小节：三种计时函数的精度与适用场景对比
 - "性能" 小节：装饰器计时结果输出
================================================================================

"""

import base64
import copy
import hashlib
import os
import platform
import pprint
import random
import secrets
import statistics
import sys
import time
import uuid
from pathlib import Path
from typing import Any, Callable, Dict, List, Tuple

# 演示用工作目录（临时），避免污染真实目录
WORK_DIR = Path(__file__).parent / "_tmp_misc"


# ===== 语法解析 =====
# 【1】uuid：通用唯一标识符
#   版本语义（这是 uuid 最常考的知识）：
#     uuid1()  基于 MAC 地址 + 时间戳；★有隐私风险，泄露网卡信息
#     uuid3()  MD5 哈希，参数为 namespace + name，确定性（同输入同输出）
#     uuid4()  密码学随机，★最常用（几乎所有场景都用它）
#     uuid5()  SHA1 哈希，确定性（同 uuid3 但换更强哈希）
#   设计意图：uuid4 用 os.urandom 取随机源，冲突概率可忽略，
#             适合做主键、文件名、临时标识。
def demo_uuid() -> None:
    print("=" * 74)
    print("【1】uuid：唯一标识符")
    print("=" * 74)

    # uuid4：随机 UUID，最常用
    u4 = uuid.uuid4()
    print(f"uuid4()        = {u4}")
    print(f"  类型          = {type(u4).__name__}  （不是 str！）")
    print(f"  str(u)        = {str(u4)}")
    print(f"  .hex          = {u4.hex}  （32 位十六进制，无连字符）")
    print(f"  .int          = {u4.int}  （128 位整数）")
    print(f"  .version      = {u4.version}")
    print(f"  .urn          = {u4.urn}")

    # uuid1：基于 MAC + 时间戳
    u1 = uuid.uuid1()
    print(f"\nuuid1()        = {u1}  （含时间戳与 MAC，可反推机器信息）")

    # uuid3/uuid5：确定性 UUID，同输入必得同结果
    ns = uuid.NAMESPACE_DNS      # 标准命名空间
    u3_a = uuid.uuid3(ns, "example.com")
    u3_b = uuid.uuid3(ns, "example.com")
    u5_a = uuid.uuid5(ns, "example.com")
    print(f"\nuuid3(NS, 'example.com') 两次调用：")
    print(f"  第一次 = {u3_a}")
    print(f"  第二次 = {u3_b}")
    print(f"  是否相同 = {u3_a == u3_b}  ← 确定性：同参数必得同 UUID")
    print(f"uuid5(NS, 'example.com')  = {u5_a}  （sha1 版，与 uuid3 不同）")

    # 唯一性验证：生成一万个 uuid4 看看有没有重复
    ids = {uuid.uuid4() for _ in range(10000)}
    print(f"\n生成 10000 个 uuid4，去重后剩 {len(ids)} 个 → "
          f"{'全部唯一' if len(ids) == 10000 else '出现重复!'}")

    # 短 UUID：很多业务场景需要短标识（如分享链接）
    short = uuid.uuid4().hex[:8]
    print(f"\n短标识（取 hex 前 8 位）= {short!r}  ← 用作文件名/短码")
    print("  为什么要转 hex：UUID 对象不能直接做文件名，.hex 是纯十六进制字符串")

    # UUID 作为字典键
    registry = {uuid.uuid4(): "任务A", uuid.uuid4(): "任务B"}
    some_key = list(registry)[0]
    print(f"\nUUID 可作 dict 键（不可变且哈希唯一）：registry[{some_key}] = "
          f"{registry[some_key]}")


# ===== 语法解析 =====
# 【2】hashlib：哈希与摘要
#   术语严格区分：
#     哈希函数 hash()  —— 内置，进程内【每次运行结果可能不同】(PYTHONHASHSEED)
#     摘要 digest     —— hashlib.sha256 等，跨进程、跨机器【结果稳定】
#   ★ 因此需要"可持久化的唯一标识"（文件去重、签名、密码存储）必须用 hashlib，
#     绝不能用内置 hash()。
#   摘要算法选择：
#     md5    128 位，已被破解，只能用于【非安全场景的快速校验】
#     sha1   160 位，也已被破解，Git 曾用它标识对象
#     sha256 256 位，当前标准，安全性足够
def demo_hashlib() -> None:
    print("\n" + "=" * 74)
    print("【2】hashlib：哈希摘要")
    print("=" * 74)

    data = b"Hello, Python!"
    print(f"原始数据: {data!r}（{len(data)} 字节）\n")

    # 三种算法对比
    for algo in ("md5", "sha1", "sha256"):
        h = hashlib.new(algo)
        h.update(data)                # 分次 update 可以拼接多次
        print(f"  {algo:<7} hexdigest = {h.hexdigest()}")
        print(f"  {'':<7} digest长度 = {len(h.digest())} 字节 / "
              f"{len(h.digest()) * 8} 位")

    # ★ 内置 hash() 与 hashlib 的关键区别
    print(f"\n⚠ 内置 hash() vs hashlib 的区别：")
    builtin = hash("Hello, Python!")
    print(f"  hash('Hello, Python!')      = {builtin}")
    print(f"  hashlib.sha256(...).hexdigest()[:16] = "
          f"{hashlib.sha256(data).hexdigest()[:16]}")
    print("  hash() 每次运行可能不同（哈希随机化），hashlib 结果【永远稳定】")
    print("  结论：文件去重、校验、签名一律用 hashlib")

    # hashlib 常用 API
    print(f"\n便捷 API：")
    # 一次性计算（内部就是 update + digest）
    print(f"  sha256(b'...').hexdigest()      = "
          f"{hashlib.sha256(b'...').hexdigest()[:32]}...")
    # 分多次 update 等价于一次拼接后计算（流式计算的基础）
    h = hashlib.sha256()
    h.update(b"Hello, ")
    h.update(b"Python!")
    print(f"  分两次 update 的结果相同 = {h.hexdigest() == hashlib.sha256(data).hexdigest()}")
    # 十六进制转回字节
    print(f"  bytes.fromhex() 可逆     = "
          f"{bytes.fromhex(h.hexdigest())[:8]!r}...")

    # ★★ 实战：文件内容 sha256 去重
    print("\n" + "=" * 74)
    print("【3】★ 实战：基于 sha256 的文件内容去重")
    print("=" * 74)

    WORK_DIR.mkdir(exist_ok=True)

    # 制造测试文件：3 个内容完全相同、1 个不同、1 个空文件
    files = {
        "a_original.txt": "完全相同的内容\n",
        "b_copy1.txt": "完全相同的内容\n",      # 与 a 重复
        "c_copy2.txt": "完全相同的内容\n",      # 与 a 重复
        "d_different.txt": "不一样的內容\n",
        "e_empty.txt": "",
    }
    for name, content in files.items():
        (WORK_DIR / name).write_text(content, encoding="utf-8")

    # ★ 关键点：不能 file.read() 一次读进内存——大文件会撑爆内存。
    #   正确做法是【分块读取，边读边喂给 hash】，内存占用恒定。
    def sha256_file(path: Path, chunk_size: int = 64 * 1024) -> str:
        """流式计算文件 sha256。chunk_size 默认 64KB，可按需调大提速。"""
        h = hashlib.sha256()
        with open(path, "rb") as f:
            # iter(lambda: f.read(chunk_size), b"") 是流式读取的标准写法：
            # 不断产出 chunk_size 字节，产出 b''（空 bytes）时停止。
            # 为什么用 lambda 延迟调用：写成 f.read 会只读一次就停。
            for chunk in iter(lambda: f.read(chunk_size), b""):
                h.update(chunk)
        return h.hexdigest()

    # 按摘要分桶：同一个摘要 = 内容完全相同
    buckets: Dict[str, List[str]] = {}
    for f in sorted(WORK_DIR.glob("*.txt")):
        digest = sha256_file(f)
        buckets.setdefault(digest, []).append(f.name)
        print(f"  {f.name:<20} size={f.stat().st_size:<3} sha256={digest[:16]}...")

    print(f"\n去重结果（共 {len(list(WORK_DIR.glob('*.txt')))} 个文件）：")
    dup_count = 0
    for digest, names in buckets.items():
        if len(names) > 1:
            dup_count += len(names) - 1
            print(f"  ★ 重复组（{digest[:12]}...）：{names}")
        else:
            print(f"    唯一文件：{names[0]}")
    print(f"\n可删除的冗余副本数：{dup_count}")

    # 分块读取的内存优势演示
    big = WORK_DIR / "big_test.bin"
    # 写入 5MB 数据（内容重复，便于压缩观察；用二进制块快速写）
    block = b"A" * 65536
    with open(big, "wb") as f:
        for _ in range(80):      # 80 * 64KB = 5 MB
            f.write(block)
    print(f"\n生成了 {big.stat().st_size / 1024 / 1024:.1f} MB 测试文件")

    import tracemalloc
    # 方式1：错误做法——一次性读进内存
    tracemalloc.start()
    with open(big, "rb") as f:
        _ = hashlib.sha256(f.read()).hexdigest()   # 一次性读入 5MB
    _, peak_all = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    # 方式2：正确做法——分块流式
    tracemalloc.start()
    _ = sha256_file(big)
    _, peak_chunk = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    print(f"  一次性 read() 的内存峰值 ≈ {peak_all / 1024:.1f} KB")
    print(f"  分块流式的内存峰值     ≈ {peak_chunk / 1024:.1f} KB")
    print("  结论：文件越大差距越明显，分块读取是处理大文件的唯一正确姿势")

    # 清理
    for f in WORK_DIR.glob("*"):
        f.unlink()
    WORK_DIR.rmdir()


# ===== 语法解析 =====
# 【3】base64：二进制 ↔ 文本编码
#   设计意图：很多协议（邮件头、URL、JSON 字段）只能传文本，
#             base64 把任意字节映射成安全 ASCII 字符。
#   ⚠ 重要：base64 是【编码】不是【加密】，任何人都能解码，不要用它保护机密！
#   API 差异：
#     b64encode(bytes)          返回单行 bytes，适合编程使用
#     encodebytes(data)         返回多行 bytes（含换行），适合邮件等场景
#     urlsafe_b64encode(data)   用 -_ 替换 +/ ，可直接放进 URL
def demo_base64() -> None:
    print("\n" + "=" * 74)
    print("【4】base64：二进制与文本互转")
    print("=" * 74)

    text = "Hello, 世界！"
    raw = text.encode("utf-8")            # str → bytes 必须先编码
    print(f"原始字符串: {text!r}")
    print(f"UTF-8 字节: {raw!r}  ({len(raw)} 字节)")
    print("  注意：中文占 3 字节，所以字节数远大于字符数")

    # 基本编解码
    b64 = base64.b64encode(raw)
    print(f"\nb64encode    = {b64!r}")
    print(f"解码还原      = {base64.b64decode(b64).decode('utf-8')!r}")
    print(f"  为什么 b64 比原文长：每 3 字节变 4 字符，膨胀约 1/3")

    # encodebytes：自动换行，适合邮件传输
    enc = base64.encodebytes(raw)
    print(f"\nencodebytes（自动换行，适合邮件）：")
    print(f"  返回类型 = {type(enc).__name__}，含换行符 = {b'\\n' in enc}")
    print(f"  内容:\n{enc.decode()}".rstrip())

    # URL 安全版本：+ / 会被 URL 解析器误解，需替换为 - _
    unsafe = base64.b64encode(b"\xfb\xff\xbe?==")
    safe = base64.urlsafe_b64encode(b"\xfb\xff\xbe?==")
    print(f"\nURL 安全 base64（关键差异演示）：")
    print(f"  b64encode       = {unsafe!r}  ← 含 + 和 / ，在 URL 中不安全")
    print(f"  urlsafe_b64encode = {safe!r}  ← 用 - 和 _ 替换")
    print("  用途：JWT token、URL 参数中的二进制数据")

    # base64 不是加密
    print(f"\n⚠ base64 不是加密：任何人都能一句话还原")
    secret = "password=123456"
    print(f"  编码: {base64.b64encode(secret.encode()).decode()}")
    print(f"  还原: {base64.b64decode(base64.b64encode(secret.encode())).decode()}")
    print("  真实加密请用 cryptography 库或标准库的 hashlib 做单向摘要")

    # base64 严格模式
    print(f"\n校验参数 validate：")
    try:
        base64.b64decode(b"aGVsbG8=!")     # 含非法字符 '!'
    except Exception as e:
        print(f"  默认会【静默丢弃】非法字符 → 得到 {base64.b64decode(b'aGVsbG8=!')!r}")
    try:
        base64.b64decode(b"aGVsbG8=!", validate=True)
    except Exception as e:
        print(f"  validate=True → 抛错: {type(e).__name__}: {e}")
    print("  解析外部数据时建议 validate=True，避免脏数据被悄悄吞掉")


# ===== 语法解析 =====
# 【4】random：伪随机数
#   ⚠ 核心认知：random 是【伪随机】，用的是 Mersenne Twister 算法。
#     它速度快、可复现（给定 seed 结果固定），但【不适合安全用途】。
#     密码、令牌、密钥必须用 secrets 模块（基于 os.urandom）。
def demo_random() -> None:
    print("\n" + "=" * 74)
    print("【5】random 与 secrets")
    print("=" * 74)

    # basic API
    print("常用 API：")
    print(f"  random()              = {random.random()}          # [0, 1) 浮点")
    print(f"  randint(1, 10)        = {random.randint(1, 10)}       # 闭区间 [1, 10]")
    print(f"  randrange(0, 10, 2)  = {random.randrange(0, 10, 2)}   # 带步长")
    print(f"  uniform(1, 6)         = {random.uniform(1, 6):.3f}    # 浮点闭区间")
    print(f"  choice(['a','b','c'])  = {random.choice(['a', 'b', 'c'])}     # 单选")
    print(f"  choices('ABC', k=3)  = {random.choices('ABC', k=3)}    # 可重复的单选多次")
    print(f"  sample(range(10), 3)  = {random.sample(range(10), 3)}    # 不重复抽样")

    # randbytes：生成随机字节串
    rb = random.randbytes(16)
    print(f"  randbytes(16)         = {rb.hex()[:24]}...  # 16 字节随机")

    # 洗牌（list 专用）
    cards = ["A", "2", "3", "4", "5"]
    random.shuffle(cards)
    print(f"  shuffle()             = {cards}  # 原地打乱，无返回值")

    # ★ seed：可复现性
    print("\n★ seed 的作用（可复现的随机）：")
    random.seed(42)
    first = [random.random() for _ in range(3)]
    random.seed(42)
    second = [random.random() for _ in range(3)]
    print(f"  seed(42) 第一次: {[f'{x:.6f}' for x in first]}")
    print(f"  seed(42) 第二次: {[f'{x:.6f}' for x in second]}")
    print(f"  两组相同 = {first == second}  ← 相同 seed 必得相同序列")
    print("  用途：单元测试、可复现的实验、数据增强时的确定性随机")
    print(f"  randbytes 不受 seed 控制: {random.randbytes(4).hex()}（基于 os.urandom）")

    # ★ 安全随机：secrets 模块
    print("\n★ 安全场景必须用 secrets（基于操作系统熵池）：")
    token = secrets.token_urlsafe(24)
    print(f"  secrets.token_urlsafe(24) = {token}")
    print(f"  secrets.token_hex(16)      = {secrets.token_hex(16)}")
    print(f"  secrets.randbelow(100)     = {secrets.randbelow(100)}  # [0, 100) 安全随机")
    print(f"  secrets.choice(...)        = {secrets.choice(['a', 'b', 'c'])}")
    print("  结论：密码/令牌/密钥 → secrets；模拟、抽样、测试 → random")

    # random 在业务中的实战：加权随机
    print("\n实战：加权随机（按权重抽取）")
    items = [("普通用户", 70), ("VIP", 20), ("SVIP", 10)]
    # 用 choices 的 cum_weights 参数实现加权，避免手写循环
    names = [n for n, _ in items]
    weights = [w for _, w in items]
    picked = random.choices(names, weights=weights, k=1000)
    print(f"  权重设置: {dict(items)}")
    print(f"  抽样 1000 次的比例: "
          f"{ {n: picked.count(n) for n in names} }  ← 接近权重比例")


# ===== 语法解析 =====
# 【5】statistics：描述统计
#   选型指南：
#     mean      算术平均，会被极端值拉偏
#     median    中位数，对极端值稳健 ★ 收入等偏态数据优先用
#     mode      众数，出现次数最多的值
#     stdev     样本标准差（除以 n-1），衡量离散程度
#     variance  样本方差（stdev 的平方）
#     quantiles 分位数，如 p90 表示 90% 的数据不超过它
def demo_statistics() -> None:
    print("\n" + "=" * 74)
    print("【6】statistics：描述统计")
    print("=" * 74)

    # 典型数据：含极端值，演示 mean 与 median 的差异
    data = [12, 15, 18, 20, 22, 25, 28, 30, 35, 1000]
    print(f"数据集: {data}")
    print(f"  注意末尾的 1000 是一个极端值\n")

    print("集中趋势：")
    print(f"  mean()   算术平均 = {statistics.mean(data):.2f}   ← 被 1000 严重拉高")
    print(f"  median() 中位数   = {statistics.median(data):.2f}   ← 更能代表典型水平")
    # 对比：不带极端值时的均值
    trimmed = data[:-1]
    print(f"  去掉极端值后 mean = {statistics.mean(trimmed):.2f}  ← 更接近中位数")
    print(f"  几何平均 geomean = {statistics.geometric_mean(trimmed):.2f}（适合比率数据）")

    # 众数
    scores = [88, 92, 92, 95, 88, 100, 92]
    print(f"\n离散程度（数据 {scores}）：")
    print(f"  mode()      众数     = {statistics.mode(scores)}      # 高频项；"
          f"multi_mode 可返回全部众数")
    print(f"  multi_mode()         = {statistics.multimode(scores)}")
    print(f"  pstdev() 总体标准差 = {statistics.pstdev(scores):.4f}   # 除以 n")
    print(f"  stdev()  样本标准差 = {statistics.stdev(scores):.4f}   # 除以 n-1 ★抽样时用这个")
    print(f"  variance() 样本方差 = {statistics.variance(scores):.4f}   # 标准差的平方")
    print(f"  关系验证: variance == stdev**2 → "
          f"{abs(statistics.variance(scores) - statistics.stdev(scores) ** 2) < 1e-9}")

    # 分位数
    print(f"\n分位数（quantiles）：")
    q = statistics.quantiles(scores, n=4)   # n=4 即四分位数
    print(f"  quantiles(n=4) = {[f'{x:.2f}' for x in q]}  # 对应 Q1 Q2 Q3")
    print(f"  quantiles(n=10) 前三个 = "
          f"{[f'{x:.1f}' for x in statistics.quantiles(scores, n=10)[:3]]}  # 即 P10 P20 P30")
    # ★ 统计函数要求至少 2 个数据点
    print(f"  注意：单元素列表会抛 StatisticsError → "
          f"（演示：{_safe_stdev([1])}）")

    # 汇总统计（均值/极值/和/数量）
    print(f"\n汇总信息：")
    print(f"  sum()  = {sum(scores)}   ← 求和用内置 sum；statistics 只额外提供 fsum")
    # fsum 用"补偿求和"算法规避浮点累积误差，这是它相对内置 sum 的唯一优势
    tenths = [0.1] * 10
    print(f"  fsum([0.1]*10) = {statistics.fsum(tenths)!r}   ← 数学上精确等于 1.0")
    print(f"  sum([0.1]*10)  = {sum(tenths)!r}   ← 存在浮点累积误差")
    print("  金额累加场景一律用 fsum 或 decimal.Decimal")
    print(f"  min / max = {min(scores)} / {max(scores)}")
    print(f"  median_low / median_high = {statistics.median_low(scores)} / "
          f"{statistics.median_high(scores)}")
    print(f"  综合: 期望值 {statistics.mean(scores):.2f}，"
          f"标准差 {statistics.stdev(scores):.2f}")


def _safe_stdev(data: List[int]) -> str:
    """演示 statistics 对数据量的要求：样本标准差至少需要 2 个数据点。"""
    try:
        return str(statistics.stdev(data))
    except statistics.StatisticsError as e:
        return f"抛出 StatisticsError: {e}"


# ===== 语法解析 =====
# 【6】copy：拷贝的三种方式与区别
#   语法规则：
#     copy.copy(x)          浅拷贝：新建顶层对象，内部元素【仍共享】
#     copy.deepcopy(x)      深拷贝：递归复制所有层级（自定义 __deepcopy__ 可定制）
#     x[:]  / list(x) / dict(x) / x.copy()  —— 容器类的浅拷贝快捷方式
#   执行顺序理解：
#     浅拷贝只复制一层容器本身，容器【内部的对象引用】不变
#     深拷贝递归下去，为每一层都创建新对象
#   设计意图：浅拷贝快但共享引用（易踩坑），深拷贝安全但慢且可能无法拷贝某些对象。
def demo_copy() -> None:
    print("\n" + "=" * 74)
    print("【7】copy：浅拷贝与深拷贝")
    print("=" * 74)

    original = {
        "name": "配置",
        "items": [1, 2, 3],                    # 列表是【可变对象】
        "nested": {"a": 1},
    }

    # 三种拷贝
    shallow = copy.copy(original)              # 浅拷贝
    deep = copy.deepcopy(original)            # 深拷贝
    shortcut = original.copy()                # dict 自带的浅拷贝

    # 用 id() 验证：顶层是新对象还是同一个对象
    print("① 顶层对象是否相同（id 对比）：")
    print(f"  original is shallow ? {original is shallow}")
    print(f"  original['items'] is shallow['items'] ? "
          f"{original['items'] is shallow['items']}")
    print(f"  original['nested'] is deep['nested'] ? "
          f"{original['nested'] is deep['nested']}")

    # ★ 演示浅拷贝的"共享引用"陷阱
    print("\n② 修改 shallow['items'][0] = 99 后：")
    shallow["items"][0] = 99
    shallow["nested"]["a"] = 999
    print(f"  original['items'][0]  = {original['items'][0]}  ← 被改了！浅拷贝共享引用")
    print(f"  original['nested']['a']= {original['nested']['a']}  ← 同样被改")
    print(f"  deep['items'][0]      = {deep['items'][0]}      ← 未受影响，深拷贝完全隔离")
    print("  结论：浅拷贝后修改【内层可变对象】会污染原数据，这是最常见的坑")

    # 修改顶层键（新增/改标量）不共享
    print("\n③ 修改顶层键（不影响原对象）：")
    shallow2 = copy.copy(original)
    shallow2["new_key"] = "新增"
    shallow2["name"] = "改名"
    print(f"  'new_key' in original ? {'new_key' in original}  ← 浅拷贝新增键不污染")
    print(f"  original['name'] = {original['name']!r}  ← 改标量也不影响")

    # 自定义类的拷贝
    print("\n④ 自定义对象的拷贝：")

    class Config:
        def __init__(self, name: str, tags: List[str]) -> None:
            self.name = name
            self.tags = tags          # 可变属性，是拷贝问题的重灾区

        def __repr__(self) -> str:
            return f"Config(name={self.name!r}, tags={self.tags})"

    cfg = Config("app", ["prod"])
    cfg_shallow = copy.copy(cfg)
    cfg_deep = copy.deepcopy(cfg)
    cfg_shallow.tags.append("staging")     # 修改内层列表
    print(f"  原对象       = {cfg}")
    print(f"  浅拷贝后     = {cfg_shallow}   ← tags 共享，原对象被污染")
    print(f"  深拷贝后     = {cfg_deep}       ← tags 独立，不受影响")

    # 循环引用：deepcopy 能处理，浅拷贝不会递归所以不会栈溢出
    print("\n⑤ 循环引用（深拷贝的考验）：")
    a: Dict[str, Any] = {"name": "root"}
    a["self"] = a                       # 自己引用自己
    dc = copy.deepcopy(a)
    print(f"  deepcopy 成功，且 dc['self'] is dc ? {dc['self'] is dc}")
    print("  为什么不会无限递归：deepcopy 内部用 memo 记录已拷贝对象")

    # 不可拷贝对象
    print("\n⑥ 无法深拷贝的对象（会抛 TypeError）：")
    import threading
    lock = threading.Lock()
    try:
        lock_copy = copy.deepcopy(lock)
        print(f"  深拷贝后是同一对象 ? {lock_copy is lock}")
    except TypeError as e:
        print(f"  threading.Lock 深拷贝 → TypeError: {e}")
        print("  原因：deepcopy 内部用 pickle 协议复制，遇到 C 扩展类型不支持则抛错")
    # 函数、模块这类对象 deepcopy 会直接返回原对象（属于不可变/不可复制）
    def some_func() -> None:
        pass
    print(f"  函数对象 deepcopy 后是同一对象 ? {copy.deepcopy(some_func) is some_func}")
    print("  结论：deepcopy 遇到不支持的类型会抛 TypeError，需 try/except 或自定义 __deepcopy__")

    # copy 模块的性能
    print("\n⑦ 性能对比（浅拷贝远快于深拷贝）：")
    import timeit
    big = {"a": list(range(1000)), "b": {"c": list(range(1000))}}
    n = 2000
    t_shallow = timeit.timeit(lambda: copy.copy(big), number=n)
    t_deep = timeit.timeit(lambda: copy.deepcopy(big), number=n)
    print(f"  copy.copy      : {t_shallow:.4f}s / {n} 次")
    print(f"  copy.deepcopy  : {t_deep:.4f}s / {n} 次")
    print(f"  深拷贝慢约 {t_deep / t_shallow:.1f} 倍 "
          f"← 不需要隔离内部引用时用浅拷贝")


# ===== 语法解析 =====
# 【7】pprint：美化的打印
#   语法规则：
#     print(obj)            单行输出，超长会换行但不缩进美化
#     pprint.pprint(obj)    智能换行缩进，行宽默认 80
#     pprint.pformat(obj)   返回美化后的字符串（不打印），可拼进日志
#   常用参数：width 控制行宽、sort_dicts 控制字典是否排序、
#             compact 紧凑模式、depth 限制递归深度。
def demo_pprint() -> None:
    print("\n" + "=" * 74)
    print("【8】pprint：美化打印")
    print("=" * 74)

    data = {
        "app_name": "学习平台",
        "database": {
            "host": "localhost",
            "port": 5432,
            "options": {"pool_size": 5, "echo": False, "timeout": 30},
        },
        "features": ["登录", "上传", "导出", "权限管理"],
        "version": "1.2.3",
    }

    print("① pprint.pprint（自动换行缩进）：")
    pprint.pprint(data)

    print("\n② sort_dicts=False 保持插入顺序（调试配置结构时有用）：")
    pprint.pprint(data, sort_dicts=False, width=60)

    print("\n③ pformat：返回字符串而不打印（拼日志用）：")
    formatted = pprint.pformat(data, width=40)
    print(f"  返回类型 = {type(formatted).__name__}，长度 {len(formatted)} 字符")
    print(f"  可直接嵌入日志: logger.info('配置: %s', formatted)")

    print("\n④ width 参数控制行宽：")
    short = pprint.pformat(data["database"], width=30)
    print(short)

    print("\n⑤ print 对比（同样的嵌套结构，print 挤在一行）：")
    # print 直接输出 dict 时用 repr，不做换行美化
    print(f"  print(data) 的效果：{data}")
    print("  对比上面的 pprint 输出，缩进层次一目了然")

    # 嵌套容器中 pprint 的深度限制
    print("\n⑥ depth 参数限制递归层数（只打印结构骨架）：")
    nested = {"l1": {"l2": {"l3": {"l4": {"l5": "太深了"}}}}}
    print("  pprint(depth=2) 的输出：")
    pprint.pprint(nested, depth=2)
    print("  超过深度的部分用 ... 省略，避免巨型嵌套刷屏")


# ===== 语法解析 =====
# 【8】sys 与 os 常用接口
#   sys —— 解释器与运行时相关（参数、退出码、模块搜索路径、递归限制）
#   os  —— 操作系统相关（环境变量、路径、进程、目录遍历）
def demo_sys_and_os() -> None:
    print("\n" + "=" * 74)
    print("【9】sys 与 os 常用接口")
    print("=" * 74)

    # ---- sys ----
    print("① sys 模块：")
    print(f"  sys.argv           = {sys.argv}   # 命令行参数列表")
    print(f"  sys.executable     = {sys.executable}")
    print(f"  sys.platform       = {sys.platform}   # 'win32'/'linux'/'darwin'")
    print(f"  sys.maxsize        = {sys.maxsize}  # 2**63-1，定义整型上限")
    print(f"  sys.getrecursionlimit() = {sys.getrecursionlimit()}")
    print(f"  sys.float_info.epsilon   = {sys.float_info.epsilon}  # 浮点精度")
    # sys.path 是模块搜索路径，出问题时打印它最快定位
    print(f"  sys.path 前 3 项    = {sys.path[:3]}")
    # exit 与退出码：sys.exit(0) 正常，sys.exit(1) 出错
    print(f"  sys.exit 演示：返回整数即作为进程退出码（0 成功，非 0 失败）")

    # ---- os ----
    print("\n② os 模块：")
    print(f"  os.name             = {os.name}")
    print(f"  os.sep              = {os.sep!r}   # 路径分隔符")
    print(f"  os.linesep          = {os.linesep!r}  # 换行符")
    print(f"  os.getcwd()         = {os.getcwd()}")
    print(f"  os.cpu_count()      = {os.cpu_count()}")
    print(f"  os.getpid()         = {os.getpid()}   # 当前进程 PID")
    # os.walk：递归遍历目录的经典方式，返回 (dirpath, dirnames, filenames)
    # 相比 pathlib.rglob，os.walk 可以【就地修改 dirnames】来剪枝
    print(f"  os.environ 是类字典对象，类型 = {type(os.environ).__name__}")
    print(f"  os.path.join('a', 'b', 'c.txt') = {os.path.join('a', 'b', 'c.txt')!r}")
    print(f"  os.path.splitext('a/b.txt')     = {os.path.splitext('a/b.txt')}")
    print(f"  os.path.exists(__file__)         = {os.path.exists(__file__)}")

    # os.walk 演示（在临时目录里造结构）
    print("\n③ os.walk 递归遍历（在临时目录中演示）：")
    import tempfile
    import shutil as _shutil
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        (root / "sub1" / "deep").mkdir(parents=True)
        (root / "sub2").mkdir()
        (root / "a.txt").write_text("1", encoding="utf-8")
        (root / "sub1" / "b.txt").write_text("2", encoding="utf-8")
        (root / "sub1" / "deep" / "c.log").write_text("3", encoding="utf-8")
        (root / "sub2" / "d.txt").write_text("4", encoding="utf-8")

        for dirpath, dirnames, filenames in os.walk(root):
            rel = Path(dirpath).relative_to(root)
            print(f"  当前目录: {str(rel) or '.'}")
            print(f"    子目录: {dirnames}")
            print(f"    文件  : {filenames}")
            # ★ 在 walk 中 del dirnames 里的名字可【剪枝】，不再进入该目录
            if rel.name == "deep":
                dirnames[:] = []       # 用切片赋值才能真正生效
        print("  技巧：dirnames[:] = [] 可跳过子目录，等价于剪枝")

    # 平台信息（跨平台代码需要判断）
    print(f"\n④ 平台信息（编写跨平台代码时用来分支）：")
    print(f"  platform.system()   = {platform.system()}")
    print(f"  platform.machine()  = {platform.machine()}")
    print(f"  platform.python_version() = {platform.python_version()}")
    print(f"  Windows 判断: {platform.system() == 'Windows'}")


# ===== 语法解析 =====
# 【9】时间测量：三种计时函数的区别
#   选型指南（重要）：
#     time.perf_counter()    高精度计时器，★测"耗时"首选
#                            基准是任意参考点，只关心两次的差值
#     time.perf_counter_ns() 同上但返回纳秒(int)，长时段测量更精确
#     time.monotonic()       单调递增时钟，不会因系统时间调整而回退
#     time.time()            Unix 时间戳，测"绝对时刻"，【不适合测耗时】
#                            （可能被 NTP 校时改写，导致差值为负）
#   设计意图：perf_counter 的名字就说明用途——performance counter。
def demo_timing() -> None:
    print("\n" + "=" * 74)
    print("【10】时间测量：perf_counter / perf_counter_ns / time")
    print("=" * 74)

    # 模拟一段耗时操作：求和 100 万次
    def workload() -> int:
        return sum(range(1_000_000))

    # perf_counter：浮点秒，精度约 1e-7 s
    start = time.perf_counter()
    result = workload()
    elapsed = time.perf_counter() - start
    print(f"① perf_counter: 耗时 {elapsed:.6f}s，结果={result}")
    print(f"  类型 = {type(elapsed).__name__}，精度到微秒级")

    # perf_counter_ns：纳秒整数，精度更高
    start_ns = time.perf_counter_ns()
    workload()
    elapsed_ns = time.perf_counter_ns() - start_ns
    print(f"\n② perf_counter_ns: 耗时 {elapsed_ns} 纳秒 = {elapsed_ns / 1e9:.6f}s")
    print(f"  类型 = {type(elapsed_ns).__name__}（int，无浮点误差）")
    print(f"  对应毫秒 = {elapsed_ns / 1e6:.3f}ms")
    print("  用途：测量极短操作（微秒级），int 运算没有浮点误差")

    # time.time：绝对时间戳
    t1 = time.time()
    workload()
    t2 = time.time()
    print(f"\n③ time(): 耗时 {t2 - t1:.6f}s")
    print(f"  time() 返回 Unix 时间戳 = {t1:.3f}")
    print(f"  转换成本地时间 = {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(t1))}")
    print("  ⚠ time() 测耗时不可靠：系统校时(NTP)可能导致差值为负数")

    # monotonic：单调递增
    m1 = time.monotonic()
    m2 = time.monotonic()
    print(f"\n④ monotonic(): {m2 - m1:.9f}s（严格单调递增，不会倒退）")
    print("  用途：计算超时、轮询间隔，语义上比 time() 更安全")

    # 三次运行取平均
    print("\n⑤ 多次测量取平均（降低单次波动影响）：")
    timings = []
    for _ in range(5):
        s = time.perf_counter()
        workload()
        timings.append(time.perf_counter() - s)
    avg = statistics.mean(timings)
    print(f"  5 次耗时: {[f'{t:.4f}' for t in timings]}")
    print(f"  平均 = {avg:.4f}s，最快 = {min(timings):.4f}s，"
          f"最慢 = {max(timings):.4f}s")
    print(f"  波动 = {(max(timings) - min(timings)) / avg * 100:.1f}%")

    # ★ 工程常用：计时装饰器
    print("\n⑥ 实战：计时装饰器（给任意函数自动加耗时统计）")

    def timer(func: Callable) -> Callable:
        """装饰器：包装函数，自动打印耗时。用 functools.wraps 保留元信息。"""
        import functools

        @functools.wraps(func)     # ★ 保留 __name__/__doc__，否则被包装成 timer
        def wrapper(*args, **kwargs):
            start = time.perf_counter()
            try:
                return func(*args, **kwargs)     # ★ 必须 return，吞掉返回值是常见 bug
            finally:
                # 用 finally 保证函数抛异常时也能统计耗时
                elapsed = time.perf_counter() - start
                print(f"    [{func.__name__}] 耗时 {elapsed:.6f}s")
        return wrapper

    @timer
    def query_database() -> str:
        """模拟数据库查询。"""
        time.sleep(0.01)     # 模拟 IO 等待
        return "查询结果"

    @timer
    def failing_task() -> None:
        """模拟会抛异常的任务，验证 finally 的清理作用。"""
        raise ValueError("任务失败")

    print("  调用 query_database():")
    print(f"    返回: {query_database()!r}")
    print("    注意 wrapper 保留了原函数名:", query_database.__name__)

    print("\n  调用 failing_task()（异常时仍打印耗时）：")
    try:
        failing_task()
    except ValueError as e:
        print(f"    捕获到异常: {e}")

    # 计时装饰器的进阶：返回耗时结果
    print("\n⑦ 进阶：让装饰器同时返回【耗时数值】便于断言")

    def timer_with_stats(func: Callable) -> Callable:
        import functools

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start = time.perf_counter_ns()      # 用 ns 拿整数，精度更高
            result = func(*args, **kwargs)
            elapsed_ns = time.perf_counter_ns() - start
            # 把耗时挂到结果上（若 result 是 dict）；此处演示返回元组
            return result, elapsed_ns / 1e6      # 转成毫秒
        return wrapper

    @timer_with_stats
    def compute() -> int:
        return sum(range(100000))

    val, ms = compute()
    print(f"  compute() 返回值={val}，耗时={ms:.3f}ms")
    print("  设计：需要把耗时写进日志或监控时，用这种返回元组的写法")


# ===== 语法解析 =====
# 【10】小结
def demo_summary() -> None:
    print("\n" + "=" * 74)
    print("【11】小结：杂项工具库速查")
    print("=" * 74)
    print("""
  1. uuid4() 做唯一标识最常用；uuid1 有隐私风险；uuid3/5 需确定性时用
  2. 需要稳定摘要一律用 hashlib，内置 hash() 每次运行可能不同
  3. 大文件哈希必须分块读取（iter(lambda: f.read(n), b"")），内存恒定
  4. base64 是编码不是加密，URL 场景要用 urlsafe_b64encode
  5. random 快但可预测；密码/令牌/密钥必须用 secrets
  6. 含极端值的数据用 median 比 mean 更能代表典型水平
  7. copy.copy 共享内层引用（易污染原对象），copy.deepcopy 完全隔离但慢
  8. pprint.pformat 返回字符串适合拼日志；debug 场景比 print 更友好
  9. 测耗时要 perf_counter（浮点）或 perf_counter_ns（整数），
     不要用 time.time()（可能被校时影响）
 10. 计时装饰器要点：functools.wraps 保留元信息 + finally 保证异常时也统计
    """)


def main() -> None:
    """主入口。"""
    print("=" * 74)
    print("杂项工具库：uuid / hashlib / base64 / random / statistics")
    print("         / copy / pprint / sys / os / 时间测量")
    print("=" * 74)
    print(f"Python 版本: {sys.version.split()[0]}")
    print(f"操作系统: {platform.system()} {platform.machine()}")
    print()

    demo_uuid()
    demo_hashlib()
    demo_base64()
    demo_random()
    demo_statistics()
    demo_copy()
    demo_pprint()
    demo_sys_and_os()
    demo_timing()
    demo_summary()


if __name__ == "__main__":
    main()