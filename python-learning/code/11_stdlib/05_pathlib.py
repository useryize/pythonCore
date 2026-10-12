"""
================================================================================
 05_pathlib.py  ——  pathlib：面向对象的路径操作
================================================================================

【演示的语法点】
 1. Path 对象：/ 运算符拼接、.name/.stem/.suffix/.parent 属性
 2. 目录遍历：iterdir / glob / rglob / walk（★ 三者区别与性能）
 3. 路径操作：mkdir / rmtree / rename / replace / unlink（★ 批量重命名）
 4. ★ 安全重命名套路：先复制到临时目录，验证无误后再删除原文件
 5. 文件查找：按扩展名/大小/修改时间筛选
 6. 路径比较：PurePath vs Path、relative_to、is_relative_to
 7. Windows 注意事项：大小写不敏感、保留名、路径长度、盘符

【预期输出摘要】
 - "遍历" 小节：对比 rglob("*") 与 walk 的结果数量
 - "批量重命名" 小节：先复制到 tmp 目录，输出映射表后再删除
================================================================================

"""

from __future__ import annotations

import os
import shutil
import tempfile
from pathlib import Path, PurePosixPath, PureWindowsPath


# ===== 语法解析 =====
# 【1】Path 对象：把路径字符串变成"可操作对象"
#   语法规则：
#     Path("a") / "b" / "c.txt"     用 / 拼接（等价于 os.path.join，但更简洁）
#     p.suffix   扩展名含点，如 ".txt"
#     p.stem     不含扩展名的名字，如 "report"
#     p.parent   父目录（Path 对象，不是 str！）
#   设计意图：把"一串字符串拼接 + os.path.join"变成面向对象的链式调用。
#   ⚠ 核心区别：Path 对象【不等于】字符串，不能直接传给要求 str 的第三方库，
#             需要时用 str(p) 转换。
def demo_basics() -> None:
    p = Path("/data/logs/2026/report.tar.gz")

    print(f"  原始路径：{p}")
    print(f"    .name   = {p.name}        ← 含最后一个扩展名")
    print(f"    .stem   = {p.stem}          ← 去掉最后一个扩展名")
    print(f"    .suffix = {p.suffix}        ← .gz（只取最后一个！）")
    print(f"    .parent = {p.parent}        ← 类型是 {type(p.parent).__name__}")
    print(f"    .parents[0] = {p.parents[0]}   .parents[1] = {p.parents[1]}")
    print(f"    .parts  = {p.parts}")
    print(f"    .anchor = {p.anchor}  .root = {p.root}")

    # ⚠ 多层扩展名只取最后一个
    print(f"  ⚠ {p.name} 的 suffix_list = {p.suffixes}  ← 用 suffixes 取全部")

    # / 运算符拼接
    base = Path("E:/project")
    target = base / "data" / "input.csv"
    print(f"  / 拼接：{target}")
    # 如果右操作数是绝对路径，会【丢弃左边】全部内容！
    print(f"  ⚠ base / '/abs/path' = {base / '/abs/path'}   ← 左边被覆盖了")

    # 常用判断
    print("  ── 判断与信息 ──")
    print(f"    is_absolute() = {target.is_absolute()}")
    print(f"    is_file()      = {target.is_file()}      （文件不存在所以 False）")
    print(f"    is_dir()       = {target.is_dir()}")
    print(f"    exists()       = {target.exists()}")
    print(f"    resolve() 转绝对路径 = {target.resolve()}")

    # 与 os.path 的对应关系
    print("  ── 与 os.path 的等价写法 ──")
    print(f"    os.path.join('a','b')   == Path('a')/'b'  → {os.path.join('a', 'b')}")
    print(f"    os.path.splitext(x)     → (stem, suffix)   → {os.path.splitext('a.txt')}")
    print(f"    os.path.dirname(x)      == p.parent       → {os.path.dirname('a/b/c.txt')}")

    # PurePath：不涉及文件系统的"纯路径"，可跨平台计算
    pp = PureWindowsPath("C:/Windows/System32")
    posix = PurePosixPath("/usr/local/bin")
    print(f"  PureWindowsPath 分隔符/盘符：{pp} → parts={pp.parts}, drive={pp.drive}")
    print(f"  PurePosixPath：{posix} → root={posix.root}")
    print(f"  ⚠ PurePath 不做【存在性】检查，永远返回 False")


# ===== 语法解析 =====
# 【2】目录遍历：iterdir / glob / rglob / walk
#   语法规则：
#     p.iterdir()            只列出【直接子项】，返回生成器
#     p.glob("*.txt")        匹配当前层；"**/*.txt" 含子目录
#     p.rglob("*.txt")       等价于 glob("**/*.txt")
#     os.walk(top)           递归产出 (dirpath, dirnames, filenames)
#   设计意图：glob 用 fnmatch 风格通配，路径分隔符在不同平台由 pathlib 适配。
#   ⚠ 性能：glob/rglob 在大目录上比 os.walk 慢很多（每个文件都要做路径对象创建）。
#     海量文件用 os.scandir / os.walk。
def demo_traverse() -> None:
    # 建一个测试目录树（放在系统临时目录，不污染项目）
    root = Path(tempfile.mkdtemp(prefix="pathlib_demo_"))
    try:
        # 结构：
        # root/
        #   a.txt  b.txt  c.log  sub/
        #     d.txt  e.log  deep/
        #       f.txt
        (root / "a.txt").write_text("根目录A", encoding="utf-8")
        (root / "b.txt").write_text("根目录B", encoding="utf-8")
        (root / "c.log").write_text("根目录C", encoding="utf-8")
        sub = root / "sub"
        sub.mkdir()
        (sub / "d.txt").write_text("子目录D", encoding="utf-8")
        (sub / "e.log").write_text("子目录E", encoding="utf-8")
        deep = sub / "deep"
        deep.mkdir()
        (deep / "f.txt").write_text("深层F", encoding="utf-8")

        # iterdir：只列直接子项（不区分文件/目录）
        print("  iterdir() 直接子项：")
        for item in sorted(root.iterdir()):
            kind = "目录" if item.is_dir() else "文件"
            print(f"      {item.name:<8} [{kind}]")

        # glob：只匹配当前层
        print(f"  glob('*.txt') 当前层：{[f.name for f in sorted(root.glob('*.txt'))]}")
        print(f"  glob('*') 当前层全部：{[f.name for f in sorted(root.glob('*'))]}")

        # rglob：递归向下匹配
        print(f"  rglob('*.txt') 递归：{[f.name for f in sorted(root.rglob('*.txt'))]}")
        print(f"  glob('**/*.txt') 与 rglob 等价：{[f.name for f in sorted(root.glob('**/*.txt'))]}")

        # 多层通配
        print(f"  rglob('*/*.txt')：{[str(f.relative_to(root)) for f in sorted(root.rglob('*/*.txt'))]}")

        # walk：一次性产出所有层的目录与文件（效率更高）
        print("  os.walk() 遍历结果：")
        for dirpath, dirnames, filenames in os.walk(root):
            rel = Path(dirpath).relative_to(root)
            rel_str = str(rel) if str(rel) != "." else "(根目录)"
            print(f"      {rel_str:<12} 目录={dirnames} 文件={filenames}")

        # 统计对比
        n_glob = len(list(root.rglob("*.txt")))
        # ⚠ 对比时必须【逐个文件】判断，不能用 len(filenames)（那会把 .log 也算进去）
        n_walk = sum(
            1 for _, _, fs in os.walk(root)
            for f in fs if f.endswith(".txt")
        )
        print(f"  统计 .txt 数量：rglob={n_glob}, walk={n_walk}（应相等）")

        # find：满足条件的第一个（★ 惰性，找到就停）
        first = root.rglob("*.log")
        print(f"  find 第一个 .log：{next(first).name}")
    finally:
        shutil.rmtree(root, ignore_errors=True)      # 清理测试目录


# ===== 语法解析 =====
# 【3】★ 批量重命名：先复制到临时目录，确认无误后再删除原文件
#   需求：把一批文件按规则重命名（如 report_2026-10-01.txt → 20261001_report.txt）
#   为什么不能直接 rename()？
#     - rename 立即生效，中途出错会留下【半改半没】的混乱状态
#     - 无法撤销
#   安全套路（三步走）：
#     ① 先复制到临时目录（副本可随时检查）
#     ② 校验副本数量/内容无误
#     ③ 再删除原文件，把副本移回
def demo_batch_rename() -> None:
    root = Path(tempfile.mkdtemp(prefix="rename_demo_"))
    try:
        # 造一批待重命名文件
        names = ["report_2026-10-01.txt", "report_2026-10-02.txt",
                 "report_2026-10-03.txt", "old_notes.md"]
        for n in names:
            (root / n).write_text(f"内容-{n}", encoding="utf-8")
        print(f"  重命名前：{sorted(p.name for p in root.iterdir())}")

        # ── 第一步：算出目标名（纯函数，不动磁盘）
        def make_new_name(p: Path) -> Path | None:
            """report_2026-10-01.txt → 20261001_report.txt；非目标文件返回 None。"""
            if not p.name.startswith("report_"):
                return None
            date_part, _, ext = p.name[len("report_"):].partition(".")
            # ⚠ 用 partition('.') 而不是 [-4:] 切片：后者在名字里还有点时会切错
            if not date_part or not ext:
                return None
            compact = date_part.replace("-", "")              # 2026-10-01 → 20261001
            return p.with_name(f"{compact}_report.{ext}")    # with_name 换名不换目录

        plan = [(p, make_new_name(p)) for p in sorted(root.iterdir())]
        plan = [(old, new) for old, new in plan if new is not None]
        print("  ── 重命名计划 ──")
        for old, new in plan:
            print(f"      {old.name}  →  {new.name}")

        # ── 第二步：复制到临时目录
        tmp = Path(tempfile.mkdtemp(prefix="rename_staging_"))
        print(f"  暂存目录：{tmp.name}")
        for old, new in plan:
            shutil.copy2(old, tmp / new.name)     # copy2 连元数据一起复制

        # ── 第三步：校验副本
        staged = sorted(p.name for p in tmp.iterdir())
        expected = sorted(new.name for _, new in plan)
        ok = staged == expected and len(staged) == len(plan)
        print(f"  校验：期望 {expected}")
        print(f"        实际 {staged}")
        print(f"        校验结果：{'✅ 通过' if ok else '❌ 失败，取消操作'}")

        # 内容校验：确认副本内容与原文件一致
        for old, new in plan:
            assert old.read_text(encoding="utf-8") == (tmp / new.name).read_text(encoding="utf-8")
        print("  内容校验通过（所有副本与原文件字节一致）")

        # ── 第四步：确认无误后才删除原文件，并把副本移回去
        if ok:
            for old, _ in plan:
                old.unlink()                       # 删除原文件
            for new in tmp.iterdir():
                shutil.move(str(new), root / new.name)   # 副本移回原目录
            print(f"  重命名后：{sorted(p.name for p in root.iterdir())}")
        shutil.rmtree(tmp, ignore_errors=True)
    finally:
        shutil.rmtree(root, ignore_errors=True)


# ===== 语法解析 =====
# 【4】文件查找：按扩展名 / 大小 / 时间筛选
def demo_find_files() -> None:
    root = Path(tempfile.mkdtemp(prefix="find_demo_"))
    try:
        # 造一批不同大小/时间的文件
        import datetime as dt_mod
        files = {
            "small.py": 100, "large.py": 5000, "test_a.py": 800,
            "readme.md": 2000, "data.csv": 15000, "config.yaml": 300,
        }
        base_time = dt_mod.datetime(2026, 10, 1, 12, 0)
        for i, (name, size) in enumerate(files.items()):
            p = root / name
            p.write_text("x" * size, encoding="utf-8")
            # 修改时间：逐个递增，便于按时间筛选
            import os as os_mod
            t = (base_time + dt_mod.timedelta(days=i)).timestamp()
            os_mod.utime(p, (t, t))

        print("  ── 按扩展名找 ──")
        py_files = sorted(root.glob("*.py"))
        print(f"  所有 .py：{[f.name for f in py_files]}")
        print(f"  所有 .py 共 {len(py_files)} 个")

        print("  ── 按大小找 ──")
        big = [f.name for f in root.iterdir() if f.stat().st_size > 1000]
        print(f"  大于 1KB 的文件：{sorted(big)}")
        # 批量排序：最大的三个
        top3 = sorted(root.iterdir(), key=lambda f: f.stat().st_size, reverse=True)[:3]
        print(f"  最大的三个：{[(f.name, f.stat().st_size) for f in top3]}")

        print("  ── 按修改时间找 ──")
        cutoff = (base_time + dt_mod.timedelta(days=2)).timestamp()
        recent = [f.name for f in root.iterdir() if f.stat().st_mtime > cutoff]
        print(f"  {dt_mod.datetime(2026,10,3,12,0):%Y-%m-%d} 之后修改的：{sorted(recent)}")

        print("  ── 组合条件 + 过滤 ──")
        result = [
            f.name for f in root.glob("*.py")
            if f.stat().st_size > 500 and not f.name.startswith("test_")
        ]
        print(f"  大于 500B 且非测试的 .py：{sorted(result)}")

        # 批量改权限 / 统计目录总大小
        total = sum(f.stat().st_size for f in root.rglob("*") if f.is_file())
        print(f"  目录总大小：{total} 字节")

        # 用 glob 做批量重命名（简单场景，无需暂存目录）
        print("  ── 就地重命名（无风险的小改动）──")
        for f in root.glob("test_*.py"):
            new = f.with_name(f.name.replace("test_", ""))
            f.rename(new)
            print(f"      {f.name} → {new.name}")
        print(f"  重命名后：{sorted(p.name for p in root.iterdir())}")
    finally:
        shutil.rmtree(root, ignore_errors=True)


# ===== 语法解析 =====
# 【5】路径比较与相对化
#   语法规则：
#     p.relative_to(base)      要求 p 在 base 之下，否则 ValueError
#     p.is_relative_to(base)   只判断，返回 bool（3.9+）
#     p1 == p2                 同平台按字符串比较；不同平台 PurePath 比较为 False
#   设计意图：把"路径包含关系"这种字符串操作变成语义操作。
def demo_compare() -> None:
    base = Path("/srv/app")
    child = Path("/srv/app/logs/error.log")

    print(f"  base   = {base}")
    print(f"  child  = {child}")
    print(f"  relative_to(base) = {child.relative_to(base)}")
    print(f"  is_relative_to(base) = {child.is_relative_to(base)}")

    other = Path("/etc/passwd")
    print(f"  {other}.is_relative_to({base}) = {other.is_relative_to(base)}")
    try:
        other.relative_to(base)
    except ValueError as e:
        print(f"  ⚠ relative_to 失败 → ValueError: {e}")

    # 实战：把绝对路径转成日志里友好的相对路径
    access_log = ["/srv/app/api/users", "/srv/app/api/orders",
                  "/var/log/nginx/error.log", "/srv/app/api/users"]
    from collections import Counter
    counts: Counter[str] = Counter()
    for path in access_log:
        p = Path(path)
        if p.is_relative_to(base):
            counts[str(p.relative_to(base))] += 1
        else:
            counts[f"[外部] {p.parts[1]}"] += 1
    print("  访问路径聚合（相对化后）：")
    for k, v in counts.most_common():
        print(f"      {k:<22} {v} 次")


# ===== 语法解析 =====
# 【6】Windows 平台注意事项
#   1. 路径【大小写不敏感】：C:\Temp 与 c:\temp 在 Windows 上是同一目录
#      但 Path 比较是【大小写敏感】的，所以不能用 == 判断文件是否相同！
#   2. 保留设备名：CON PRN AUX NUL COM1~9 LPT1~9 不能做文件名
#   3. 非法字符：< > : " | ? *
#   4. 路径长度限制：传统 MAX_PATH = 260 字符
#   5. 分隔符：Path 会自动处理，字符串拼接时务必用 Path 或 os.path.join
def demo_windows_notes() -> None:
    print("  ① 大小写：Windows 路径比较【不区分大小写】，POSIX 区分")
    print(f"      PureWindowsPath('C:/Temp/a') == PureWindowsPath('c:/temp/A') → "
          f"{PureWindowsPath('C:/Temp/a') == PureWindowsPath('c:/temp/A')}")
    print(f"      PurePosixPath('/a/b') == PurePosixPath('/A/B')             → "
          f"{PurePosixPath('/a/b') == PurePosixPath('/A/B')}")
    print(f"      ⚠ 原因：WindowsPath 的 casefold/比较遵循文件系统语义（不区分大小写）")
    print(f"      ⚠ 但【裸字符串比较】区分大小写：'C:/Temp' == 'c:/temp' → "
          f"{'C:/Temp' == 'c:/temp'}   ← 与 Windows 路径语义相反，所以别拿字符串比路径")
    print(f"      跨平台路径互不相等：PureWindowsPath('C:/a') == PurePosixPath('/a') → "
          f"{PureWindowsPath('C:/a') == PurePosixPath('/a')}")
    print("      ✅ 需要判断'是否同一个文件'时用 os.path.samefile()（要求文件已存在）")
    print(f"      os.path.normcase('C:/Temp') = {os.path.normcase('C:/Temp')}  "
          f"← Windows 转小写+反斜杠，POSIX 原样返回")

    print("  ② 保留设备名：")
    reserved = ["CON", "PRN", "AUX", "NUL"] + [f"COM{i}" for i in range(1, 4)]
    print(f"      Windows 保留名：{reserved}")
    try:
        # 实际在 Windows 上创建 CON 文件会失败，这里只演示危险
        bad = Path(tempfile.gettempdir()) / "CON.txt"
        print(f"      ⚠ 尝试创建 {bad.name} 可能失败（即使带扩展名也不行）")
    except Exception as e:
        print(f"      实际报错：{e}")

    print("  ③ 非法字符：")
    print(f"      Windows 文件名禁止：< > : \" | ? *")

    print("  ④ 路径长度：")
    long_path = Path("C:/" + "/".join(["verylongdirectoryname"] * 25))
    print(f"      示例长度 = {len(str(long_path))} 字符（传统上限 260）")
    print(f"      ✅ 建议：项目目录不要过深，或启用 Windows 长路径支持")

    print("  ⑤ 路径拼接：")
    print("      ❌ 错误：'C:/data/' + '/' + name        ← 出现 // ，或盘符后错位")
    print("      ✅ 正确：Path('C:/data') / name  或  os.path.join('C:/data', name)")
    print(f"      Path 拼接结果：{Path('C:/data') / 'file.txt'}")


def main() -> None:
    print("=" * 60)
    print("【1】Path 基础操作")
    print("=" * 60)
    demo_basics()

    print()
    print("=" * 60)
    print("【2】目录遍历：iterdir / glob / rglob / walk")
    print("=" * 60)
    demo_traverse()

    print()
    print("=" * 60)
    print("【3】批量重命名（先复制到临时目录，确认后删除）")
    print("=" * 60)
    demo_batch_rename()

    print()
    print("=" * 60)
    print("【4】文件查找：按扩展名/大小/时间")
    print("=" * 60)
    demo_find_files()

    print()
    print("=" * 60)
    print("【5】路径比较与相对化")
    print("=" * 60)
    demo_compare()

    print()
    print("=" * 60)
    print("【6】Windows 平台注意事项")
    print("=" * 60)
    demo_windows_notes()

    print()
    print("=" * 60)
    print("小结")
    print("=" * 60)
    print("  1. Path 是对象不是字符串，/ 拼接；.parent 返回 Path 不是 str")
    print("  2. p / 绝对路径会丢弃左侧内容，这是常见坑")
    print("  3. iterdir 单层、glob 单层、rglob 递归、os.walk 最快")
    print("  4. 批量重命名务必「复制→校验→删除」，别直接 inplace rename")
    print("  5. suffix 只取最后一个扩展名，多层用 suffixes")
    print("  6. Windows 下 Path 比较不区分大小写（与 POSIX 不同），别拿字符串比路径")
    print("  7. Windows 保留名 CON/PRN/AUX 等不可做文件名")


if __name__ == "__main__":
    main()