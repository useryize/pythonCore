"""
================================================================================
 05_pathlib.py  ——  pathlib：文件与目录操作的完整实战
================================================================================

【重要安全声明】
  本文件【不会修改任何真实文件】。
  涉及写、重命名、删除的演示，全部在 tempfile.mkdtemp() 创建的
  一次性临时目录中进行，运行结束（无论成功或异常）都由 finally 清理。
  真实目录仅被【只读】访问（统计、遍历），且仅限本文件同级的 data/ 目录。

【演示的语法点】
 1. Path 对象创建与 / 运算符拼接：Path("a") / "b" / "c.txt"
 2. PurePath vs Path：不做文件系统操作的纯路径对象
 3. 路径属性全解：.name .stem .suffix .suffixes .parent .parents .parts
 4. 构造与变形：with_name / with_suffix / with_stem / relative_to / is_relative_to
 5. 目录创建：mkdir(parents, exist_ok) 与 parents=True 的必要性
 6. 目录遍历：iterdir / glob / rglob / walk 的返回类型与性能对比
 7. ★ os 模块与 pathlib 的 API 对照表（系统路径 → pathlib 等价写法）
 8. 文件状态查询：exists is_file is_dir stat lstat samefile
 9. ★ 批量重命名完整演练（临时目录内）：
       - 三种命名方案：加序号 / 扩展名归一 / 模板化 / 递增编号
       - 重命名前的冲突检测与预演（dry-run）
       - 重命名失败时的回滚思路
10. 删除与清理：unlink / rmdir / shutil.rmtree 的区别与各自的使用时机
11. 路径安全检查：is_relative_to 防目录穿越
12. Windows 平台注意事项：大小写不敏感、保留文件名、盘符、路径长度

【预期输出摘要】
 - "属性" 小节：同一路径的 name/stem/suffix/parent 逐项打印
 - "遍历" 小节：iterdir/glob/rglob 对同一目录树返回的元素数量对比
 - "对比表" 小节：os.path.* 与 pathlib 的等价 API 映射
 - "重命名" 小节：先在临时目录造 6 个测试文件，打印"改造前 → 改造后"映射表，
   真实执行后再打印结果，最后清理临时目录（绝不触碰真实文件）
================================================================================

"""

import os
import shutil
import sys
import tempfile
import time
from pathlib import Path, PurePath, PurePosixPath, PureWindowsPath
from typing import Callable

# 只读访问的本目录数据目录（不做任何修改）
DATA_DIR = Path(__file__).parent / "data"


# ===== 语法解析 =====
# 【1】Path 对象的本质
#   Path 是一个【面向对象的路径包装器】，它不是字符串，不能直接传给
#   要求 str 的第三方 API（需要时用 str(p) 转换）。
#   设计意图：把"os.path.join + 字符串拼接"变成可链式调用的对象操作，
#             并且统一了 Windows / POSIX 两套路径差异。
#   语法规则：
#     Path("a") / "b"      —— 重载 __truediv__ 运算符做拼接，等价 os.path.join
#     注意末尾不带分隔符；Path("a/b/") 会自动规范化为 Path("a/b")
def demo_construction() -> None:
    print("=" * 74)
    print("【1】Path 的创建与 / 拼接")
    print("=" * 74)

    # 基本创建
    p = Path("data") / "sample.json"
    print(f"Path('data') / 'sample.json' = {p}")
    print(f"  类型 = {type(p).__name__}")
    print(f"  是否绝对路径 = {p.is_absolute()}")

    # 末尾分隔符会被规范化
    p2 = Path("data/subdir/")
    print(f"\nPath('data/subdir/') = {p2}   ← 末尾分隔符被自动去掉")

    # 多级拼接（比 os.path.join 更直观）
    deep = Path("root") / "a" / "b" / "c" / "file.txt"
    print(f"多级拼接 = {deep}")
    print(f"  对照 os.path.join = {os.path.join('root', 'a', 'b', 'c', 'file.txt')}")

    # 从字符串创建
    from_str = Path("some/path/file.txt")
    # 从已有 Path 创建（拷贝）
    copied = Path(from_str)
    print(f"\nPath(已有Path) = {copied}，与原对象相等 = {copied == from_str}")

    # 首页目录（跨平台安全）
    home = Path.home()
    print(f"\nPath.home() = {home}   ← 比 os.path.expanduser('~') 更好读")

    # ★ PurePath：不接触文件系统，纯字符串运算
    print("\nPurePath：不进行任何文件系统操作")
    pure = PurePath("a") / "b" / "c.txt"
    print(f"  PurePath('a')/'b'/'c.txt' = {pure}")
    print(f"  .parent = {pure.parent}")
    print(f"  .parts  = {pure.parts}")
    print("  PurePath 永远不会碰磁盘，因此没有 exists() / mkdir() 等方法")
    print("  用途：只需处理路径【字符串】而不想访问文件系统的场景（如路径校验）")

    # PurePosixPath / PureWindowsPath：强制按指定风格解析
    posix = PurePosixPath("/usr/local/bin/python")
    win = PureWindowsPath("C:/Users/name/file.txt")
    print(f"\n  PurePosixPath('/usr/local/bin/python').parts = {posix.parts}")
    print(f"  PureWindowsPath('C:/Users/...').parts         = {win.parts}")
    print(f"  PureWindowsPath('C:/a/b').drive               = {PureWindowsPath('C:/a/b').drive!r}")
    print("  用途：处理来自外部的、风格未知的路径字符串（如 HTTP 传入的路径）")

    # 跨平台反斜杠：Windows 上 / 和 \ 都能用，POSIX 上 \ 是合法文件名字符
    print(f"\n  Path('a/b') 在本平台的 parts = {Path('a/b').parts}")
    print("  ★ 跨平台代码请统一用 / 分隔，Path 会在 Windows 上自动转换")


# ===== 语法解析 =====
# 【2】路径属性全解 —— 每个属性对应"路径字符串的某一部分"
#   .name      最后一段的文件名（含扩展名）
#   .stem      不含最后一个扩展名的名字
#   .suffix    最后一个扩展名（含点，如 ".txt"）
#   .suffixes  全部扩展名列表（如 ".tar", ".gz"）
#   .parent    父目录（Path 对象）
#   .parents   所有祖先目录的序列（元组）
#   .parts     拆分成各部分的元组
#   .stem / .suffix 的区别在多扩展名文件上最明显：
#     archive.tar.gz → stem='archive', suffix='.gz', suffixes=['.tar', '.gz']
def demo_attributes() -> None:
    print("\n" + "=" * 74)
    print("【2】路径属性全解")
    print("=" * 74)

    samples = [
        "report.pdf",
        "archive.tar.gz",
        "main.py",
        "noext",
        "src/module/__init__.py",
    ]
    print(f"{'路径':<28}{'name':<16}{'stem':<14}{'suffix':<10}{'suffixes'}")
    print("-" * 88)
    for s in samples:
        p = Path(s)
        print(f"{s:<28}{p.name:<16}{p.stem:<14}{p.suffix:<10}{p.suffixes}")

    print("\n① .parent 与 .parents：")
    p = Path("src/module/__init__.py")
    print(f"  路径         = {p}")
    print(f"  .parent      = {p.parent}          # 上一级")
    print(f"  .parents     = {tuple(str(x) for x in p.parents)}   # 所有祖先")
    print(f"  .parts       = {p.parts}          # 拆成元组")

    # parent 的边界行为
    print(f"\n② parent 的边界行为：")
    root = Path("/")
    print(f"  Path('/').parent = {root.parent}   # 根目录的父目录还是自己")
    print(f"  这是死循环的来源：手动 while p.parent != p 会安全，纯 p = p.parent 会死循环")

    # ★ stem vs suffix 的区别与陷阱
    print(f"\n③ stem/suffix 的经典陷阱：")
    hidden = Path(".gitignore")
    print(f"  Path('.gitignore').name   = {hidden.name!r}")
    print(f"  Path('.gitignore').suffix = {hidden.suffix!r}   # 整个名字被当 stem")
    print(f"  Path('.gitignore').stem   = {hidden.stem!r}")
    print("  ⚠ 纯以点开头的文件（隐藏文件）suffix 为空，拆分后缀需用 splitext 或判断")

    print(f"\n④ parent 是 Path 而非 str：")
    print(f"  type(Path('a/b').parent) = {type(Path('a/b').parent).__name__}")
    print(f"  os.path.dirname 返回 str = {type(os.path.dirname('a/b')).__name__}")
    print("  所以 pathlib 风格里不要写 str 的字符串方法，如 .parent.endswith('/')")


# ===== 语法解析 =====
# 【3】路径变形：with_name / with_suffix / with_name 系列
#   语法规则（全部返回【新对象】，不修改原对象）：
#     with_name(name)   替换最后一段的文件名（保留所在目录）
#     with_suffix(suf)   替换最后一个扩展名
#     with_stem(stem)    替换不含扩展名的部分
#     relative_to(base) 返回相对于 base 的路径；若不在 base 下会抛 ValueError
#     is_relative_to(b) 判断是否在 b 之下（Python 3.9+），不抛异常
#   设计意图：这些方法体现了"不可变值对象"的编程风格，
#             链式调用可读性远高于"先取属性再拼接"。
def demo_transform() -> None:
    print("\n" + "=" * 74)
    print("【3】路径变形方法")
    print("=" * 74)

    p = Path("/data/report.txt")

    print("① with_name：替换文件名（目录不变）")
    print(f"  {p}")
    print(f"  .with_name('summary.txt')  = {p.with_name('summary.txt')}")
    print(f"  .with_name('a/b.txt')      → 会抛 ValueError（不能含分隔符）")
    try:
        p.with_name("a/b.txt")
    except ValueError as e:
        print(f"     实测: {type(e).__name__}: {e}")

    print("\n② with_suffix：替换扩展名")
    print(f"  {p}")
    print(f"  .with_suffix('.md')       = {p.with_suffix('.md')}")
    print(f"  .with_suffix('.tar.gz')   = {p.with_suffix('.tar.gz')}   # 可含多点")
    # 去掉扩展名：传空字符串
    print(f"  .with_suffix('')          = {p.with_suffix('')}   # 去后缀的官方写法")
    print(f"  ⚠ 注意：with_suffix('.gz') 对 'a.tar' 得到 'a.gz'，"
          f"而不是 'a.tar.gz'")

    print("\n③ with_stem：替换主体（保留扩展名）")
    print(f"  {p} → .with_stem('annual') = {p.with_stem('annual')}")

    print("\n④ relative_to：求相对路径（不在其下会抛 ValueError）")
    base = Path("/data")
    child = Path("/data/2024/report.txt")
    print(f"  {child}.relative_to({base}) = {child.relative_to(base)}")
    other = Path("/other/file.txt")
    print(f"  {other}.relative_to({base}) → 抛 ValueError")
    try:
        other.relative_to(base)
    except ValueError as e:
        print(f"     实测: {e}")
    # is_relative_to：只判断不抛异常，更适合做安全校验
    print(f"  {child}.is_relative_to({base}) = {child.is_relative_to(base)}   # 不抛异常")
    print(f"  {other}.is_relative_to({base}) = {other.is_relative_to(base)}")
    print("  ★ 安全校验优先用 is_relative_to（无异常开销，逻辑更清晰）")

    print("\n⑤ 链式变形（体现不可变对象风格）：")
    # ⚠ 注意括号：字符串字面量会与 . 运算符先结合，
    #   必须先用括号包住路径，否则 with_suffix 会作用在 str 上而报错
    base_path = Path("/data") / "2024" / "raw" / "photo.jpg"
    result = base_path.with_suffix(".png").with_name("avatar.png")
    print(f"  {base_path}")
    print(f"  → with_suffix('.png') → {base_path.with_suffix('.png')}")
    print(f"  → with_name('avatar.png') → {result}")
    print(f"  原对象不变: {base_path}   ← 每次变形都返回新对象")
    print("  正确的链式写法：((Path(...) / 'a.txt').with_suffix('.md')).with_name('b.md')")


# ===== 语法解析 =====
# 【4】目录创建：mkdir 的参数陷阱
#   语法规则：
#     mkdir()                创建单层目录，父目录不存在则抛 FileNotFoundError
#     mkdir(parents=True)    递归创建所有缺失的父目录
#     mkdir(exist_ok=True)   目录已存在时不报错
#   设计意图：两个参数解决"幂等创建"问题，
#             生产代码里几乎总是 parents=True, exist_ok=True 连用。
def demo_mkdir() -> None:
    print("\n" + "=" * 74)
    print("【4】目录创建与删除")
    print("=" * 74)

    # ★ 所有写入都在一次性临时目录中进行
    tmp = Path(tempfile.mkdtemp(prefix="pathlib_demo_"))
    print(f"临时工作目录: {tmp}")

    try:
        # 对比：不加 parents 的失败
        print("\n① mkdir 的三种情况：")
        single = tmp / "a"
        single.mkdir()
        print(f"  单层创建成功: {single.name}")

        print(f"  再创建一次会抛 FileExistsError:")
        try:
            single.mkdir()
        except FileExistsError as e:
            print(f"     实测: {type(e).__name__}")

        print(f"  加 exist_ok=True 后不报错: ", end="")
        single.mkdir(exist_ok=True)
        print("成功")

        print("\n② 多层目录必须加 parents=True：")
        deep = tmp / "x" / "y" / "z"
        try:
            deep.mkdir()
        except FileNotFoundError as e:
            print(f"  不加 parents → {type(e).__name__}: 父目录不存在")
        deep.mkdir(parents=True)
        print(f"  加 parents=True → 创建成功: {deep.relative_to(tmp)}")

        print("\n③ ★ 生产代码的标准写法：")
        std = tmp / "app" / "config" / "cache"
        # parents=True + exist_ok=True 连用 = 幂等创建，可反复调用不报错
        std.mkdir(parents=True, exist_ok=True)
        std.mkdir(parents=True, exist_ok=True)     # 再调一次也不报错
        print(f"  mkdir(parents=True, exist_ok=True) 连用两次均成功: {std.relative_to(tmp)}")

        # rmdir 只能删空目录
        print("\n④ 删除的三个层次：")
        empty_dir = tmp / "empty"
        empty_dir.mkdir()
        empty_dir.rmdir()
        print(f"  rmdir() 删空目录成功（已删除: {not empty_dir.exists()}）")

        file = tmp / "f.txt"
        file.write_text("x", encoding="utf-8")
        try:
            (tmp / "x").rmdir()      # 该目录非空
        except OSError as e:
            print(f"  rmdir() 删非空目录 → {type(e).__name__}（需先清空或用 rmtree）")
        print(f"  unlink() 删文件: ", end="")
        file.unlink()
        print(f"成功（已删除: {not file.exists()}）")

        # rmtree 删除整个目录树
        tree = tmp / "a"
        shutil.rmtree(tree)
        print(f"  shutil.rmtree() 删目录树: 成功（已删除: {not tree.exists()}）")
        print("  ★ rmtree 是【递归删除】，不可逆，务必确认路径再调用")

        # unlink(missing_ok=True)：文件不存在也不报错
        print("\n⑤ unlink(missing_ok=True)：")
        ghost = tmp / "never_existed.txt"
        try:
            ghost.unlink()      # 对不存在的文件会抛 FileNotFoundError
        except FileNotFoundError as e:
            print(f"  默认行为 → {type(e).__name__}: 文件不存在")
        ghost.unlink(missing_ok=True)   # missing_ok=True 时静默跳过
        print("  missing_ok=True → 不报错，静默跳过不存在的文件")
        print("  适用场景：清理脚本中不确定文件是否存在的场景")

    finally:
        shutil.rmtree(tmp, ignore_errors=True)
        print(f"\n已清理临时目录: {tmp}")


# ===== 语法解析 =====
# 【5】目录遍历：四种方式的区别
#   iterdir()   只遍历【当前层】，返回 Path 对象的迭代器
#   glob(pat)    遍历当前层，模式匹配（* 不跨分隔符，** 可跨层）
#   rglob(pat)   递归遍历【所有子目录】，等价于 glob("**/" + pat)
#   os.walk()    自上而下遍历整棵树，逐个 yield (根, 子目录列表, 文件列表)
#
#   关键区别（面试常考）：
#     glob 的 * 只匹配一层，* 不会跨越路径分隔符
#     rglob("*") 会返回【目录本身】，需要用 is_file() 过滤
#     需要剪枝（不进入某些目录）时只有 os.walk 方便
#     只关心文件且结构简单时，rglob 最简洁
def demo_traverse() -> None:
    print("\n" + "=" * 74)
    print("【5】目录遍历：iterdir / glob / rglob / walk")
    print("=" * 74)

    def bench(fn: "Callable[[], object]", n: int = 200) -> float:
        """执行 n 次 fn，返回单次平均耗时（毫秒）。"""
        start = time.perf_counter()
        for _ in range(n):
            fn()
        return (time.perf_counter() - start) / n * 1000

    # 构造一棵有结构的临时目录树
    tmp = Path(tempfile.mkdtemp(prefix="pathlib_traverse_"))
    try:
        structure = {
            "a.txt": "根文件",
            "b.log": "根日志",
            "sub1/c.py": "一级",
            "sub1/d.json": "一级",
            "sub1/nested/e.py": "二级",
            "sub1/nested/f.md": "二级",
            "sub2/g.txt": "一级",
            "sub2/nested2/h.csv": "二级",
        }
        for rel, content in structure.items():
            fp = tmp / rel
            fp.parent.mkdir(parents=True, exist_ok=True)
            fp.write_text(content, encoding="utf-8")

        print(f"目录树结构（临时目录 {tmp.name}/ 下）：")
        for dirpath, dirnames, filenames in os.walk(tmp):
            rel = Path(dirpath).relative_to(tmp)
            prefix = "." if str(rel) == "." else str(rel)
            print(f"  {prefix}/")
            print(f"    目录: {dirnames}")
            print(f"    文件: {filenames}")

        # ① iterdir
        print("\n① iterdir()：只遍历当前层")
        entries = list(tmp.iterdir())
        for e in sorted(entries):
            kind = "目录" if e.is_dir() else "文件"
            print(f"  {e.name:<20} {kind}")
        print(f"  共 {len(entries)} 项（含目录），返回类型 = {type(entries[0]).__name__}")

        # ② glob
        print("\n② glob('*.txt')：当前层的 txt（不跨目录）")
        found = sorted(tmp.glob("*.txt"))
        print(f"  {[f.name for f in found]}")
        print("  ★ glob 的 * 只匹配【一层】，不会到子目录里找")

        print("\n③ glob('*/*.py')：明确的层级模式")
        found3 = sorted(tmp.glob("*/*.py"))
        print(f"  {[str(f.relative_to(tmp)) for f in found3]}")
        print("  模式里的 / 表示层级，* 匹配一段，** 匹配任意多层")

        print("\n④ rglob('*.py')：递归查找所有 py 文件")
        found4 = sorted(tmp.rglob("*.py"))
        print(f"  {[str(f.relative_to(tmp)) for f in found4]}   共 {len(found4)} 个")

        print("\n⑤ ⚠ rglob('*') 会返回【目录】而非只有文件：")
        all_items = list(tmp.rglob("*"))
        dirs_count = sum(1 for p in all_items if p.is_dir())
        files_count = sum(1 for p in all_items if p.is_file())
        print(f"  共 {len(all_items)} 项：目录 {dirs_count} 个 + 文件 {files_count} 个")
        print("  ★ 所以写 'for f in rglob(\"*\"): f.stat()' 是错的，")
        print("    必须先过滤：for f in rglob('*') if f.is_file()")
        print("  或者直接 rglob('*.txt') 带上扩展名，天然只匹配文件")

        # 计数对比
        print("\n⑥ 四种方式在本目录树上的元素数量对比：")
        counts = {
            "iterdir()": len(list(tmp.iterdir())),
            "glob('*')": len(list(tmp.glob("*"))),
            "rglob('*')": len(list(tmp.rglob("*"))),
            "rglob('*.txt')": len(list(tmp.rglob("*.txt"))),
        }
        for name, cnt in counts.items():
            print(f"  {name:<20} {cnt} 项")

        # os.walk 对比
        print("\n⑦ os.walk：一次遍历拿到整棵树 + 可剪枝")
        total_files = 0
        for dirpath, dirnames, filenames in os.walk(tmp):
            total_files += len(filenames)
        print(f"  os.walk 累计文件数 = {total_files}")
        print(f"  （walk 每层 yield 三元组，dirnames 可【就地修改】实现剪枝）")

        # 性能对比
        print("\n⑧ 性能对比（各遍历 200 次取平均）：")
        t_iterdir = bench(lambda: list(tmp.iterdir()))
        t_glob = bench(lambda: list(tmp.glob("*")))
        t_shallow = bench(lambda: list(tmp.glob("*/*.txt")))
        t_rglob = bench(lambda: list(tmp.rglob("*.txt")))
        print(f"  iterdir()          : {t_iterdir:.4f} ms/次（只看当前层，通常最快）")
        print(f"  glob('*')          : {t_glob:.4f} ms/次")
        print(f"  glob('*/*.txt')    : {t_shallow:.4f} ms/次（指定层级，无需全递归）")
        print(f"  rglob('*.txt')     : {t_rglob:.4f} ms/次（需递归全部目录，通常最慢）")
        print("  说明：范围越精确越快，能用 glob('*/*.txt') 就别用 rglob")

        # 多模式 glob
        print("\n⑨ 一个 glob 传多个模式（3.13+ 支持 iterable）：")
        try:
            both = sorted(tmp.rglob(["*.py", "*.json"]))
            print(f"  rglob(['*.py','*.json']) → {[str(f.relative_to(tmp)) for f in both]}")
        except TypeError:
            # 兼容旧版本：用两个 glob 结果合并
            both = sorted(list(tmp.rglob("*.py")) + list(tmp.rglob("*.json")))
            print(f"  当前版本不支持，改用两次 glob 合并 → "
                  f"{[str(f.relative_to(tmp)) for f in both]}")

    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# ===== 语法解析 =====
# 【6】os.path 与 pathlib 的 API 对照
#   设计意图：pathlib 是"面向对象"的现代写法，os.path 是"字符串函数"的传统写法。
#             两者功能等价，新代码优先用 pathlib，老代码仍大量使用 os.path。
#   迁移时最容易出错的点：
#     os.path 返回 str，pathlib 返回 Path；两者不能直接互相传给对方的 API。
def demo_os_vs_pathlib() -> None:
    print("\n" + "=" * 74)
    print("【6】os 与 pathlib 对比")
    print("=" * 74)

    print("\n① 核心 API 对照表：")
    print(f"  {'功能':<26}{'os 写法':<40}{'pathlib 写法'}")
    print("-" * 96)
    table = [
        ("路径拼接", "os.path.join('a', 'b')", "Path('a') / 'b'"),
        ("绝对路径", "os.path.abspath('x')", "Path('x').resolve()"),
        ("取父目录", "os.path.dirname('a/b.txt')", "Path('a/b.txt').parent"),
        ("取文件名", "os.path.basename('a/b.txt')", "Path('a/b.txt').name"),
        ("拆主名/后缀", "os.path.splitext('a.txt')", "Path('a.txt').stem/.suffix"),
        ("是否存在", "os.path.exists('a')", "Path('a').exists()"),
        ("是否目录", "os.path.isdir('a')", "Path('a').is_dir()"),
        ("是否文件", "os.path.isfile('a')", "Path('a').is_file()"),
        ("列出目录", "os.listdir('a')", "Path('a').iterdir()"),
        ("建目录", "os.mkdir('a')", "Path('a').mkdir()"),
        ("删目录", "os.rmdir('a')", "Path('a').rmdir()"),
        ("删文件", "os.remove('a')", "Path('a').unlink()"),
        ("重命名", "os.rename('a', 'b')", "Path('a').rename('b')"),
        ("读文本", "open('a').read()", "Path('a').read_text()"),
        ("写文本", "open('a','w').write(s)", "Path('a').write_text(s)"),
        ("扩展名判断", "os.path.splitext(x)[1] == '.py'", "Path(x).suffix == '.py'"),
        ("通配查找", "glob.glob('a/*.txt')", "Path('a').glob('*.txt')"),
        ("递归查找", "glob.glob('a/**/*.txt', recursive=True)", "Path('a').rglob('*.txt')"),
    ]
    for func, os_way, pl_way in table:
        print(f"  {func:<26}{os_way:<40}{pl_way}")

    print("\n② 返回类型对比（最易踩的坑）：")
    print(f"  os.path.dirname('a/b.txt')  返回 {type(os.path.dirname('a/b.txt')).__name__}")
    print(f"  Path('a/b.txt').parent      返回 {type(Path('a/b.txt').parent).__name__}")
    print(f"  os.listdir('.')            返回 {type(os.listdir('.')).__name__}，"
          f"元素类型 {type(os.listdir('.')[0]).__name__}")
    print(f"  Path('.').iterdir()         返回 {type(Path('.').iterdir()).__name__}"
          f"，元素类型 {type(next(Path('.').iterdir())).__name__}")
    print("  ⚠ 迁移时不能想当然：list(Path.iterdir()) 得到的是 [PosixPath(...)]，")
    print("     需要字符串列表时要写 [str(p) for p in path.iterdir()]")

    print("\n③ 实际调用对比：")
    target = Path("example.txt")
    print(f"  os.path.exists('example.txt')      = {os.path.exists('example.txt')}")
    print(f"  Path('example.txt').exists()       = {target.exists()}")
    print(f"  os.path.splitext('demo.tar.gz')    = {os.path.splitext('demo.tar.gz')}")
    p_tar = Path("demo.tar.gz")
    print(f"  Path('demo.tar.gz').suffix         = {p_tar.suffix!r}")
    print(f"  Path('demo.tar.gz').suffixes       = {p_tar.suffixes}  ← pathlib 能拿全部后缀")

    print("\n④ 何时仍该用 os：")
    print("  - os.environ：环境变量没有 pathlib 版本")
    print("  - os.getcwd() / os.chdir()：进程工作目录")
    print("  - os.walk()：需要遍历并剪枝时")
    print("  - shutil：copy / move / rmtree 等高级操作")
    print("  - os.stat()：底层元数据调用")
    print("  结论：新写文件操作用 pathlib，进程/环境类操作用 os，两者互补")


# ===== 语法解析 =====
# 【7】文件状态查询
#   stat() 返回的 st_ 开头的字段：
#     st_size    字节数
#     st_mtime   修改时间（Unix 时间戳，需 time.localtime 转换）
#     st_mode    权限位（stat.S_ISDIR 等判断类型）
#     st_ino     inode 号（Unix），stat() 会跟随符号链接，lstat() 不跟随
#   设计意图：is_file()/is_dir() 内部就是调用 stat() 并判断 S_ISREG/S_ISDIR，
#             语义完全一致，只是封装得更好。
def demo_stat() -> None:
    print("\n" + "=" * 74)
    print("【7】文件状态与元信息")
    print("=" * 74)

    # 只读访问 data 目录，不做任何修改
    if not DATA_DIR.exists():
        print(f"数据目录不存在: {DATA_DIR}")
        return

    print(f"只读查看数据目录: {DATA_DIR}")
    for f in sorted(DATA_DIR.iterdir()):
        print(f"\n  {f.name}:")
        print(f"    is_file()   = {f.is_file()}")
        print(f"    is_dir()    = {f.is_dir()}")
        print(f"    exists()    = {f.exists()}")
        st = f.stat()
        size_mb = st.st_size / 1024
        print(f"    stat().st_size  = {st.st_size} 字节 ({size_mb:.1f} KB)")
        mtime = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(st.st_mtime))
        print(f"    stat().st_mtime = {mtime}（本地时间）")
        print(f"    stat().st_mode  = {oct(st.st_mode)}（权限位）")

    # 按大小筛选文件（实用技巧）
    print("\n★ 按大小/时间筛选（实用组合）：")
    files = [f for f in DATA_DIR.iterdir() if f.is_file()]
    if files:
        largest = max(files, key=lambda f: f.stat().st_size)
        newest = max(files, key=lambda f: f.stat().st_mtime)
        print(f"  最大的文件: {largest.name} ({largest.stat().st_size} 字节)")
        print(f" 最新的文件: {newest.name}")
        print(f"  总大小: {sum(f.stat().st_size for f in files)} 字节")

    # 同文件判断
    print("\n★ samefile：判断两个路径是否指向同一个文件（比较 inode/大小）：")
    if files:
        f = files[0]
        print(f"  samefile(p, p)      = {f.samefile(f)}   # 同一对象")
        print(f"  samefile(p, 别名)    需要两个实际路径才能验证")
        print("  用途：判断链接/硬链接/相对路径是否指向同一实体")


# ===== 语法解析 =====
# 【8】★★ 批量重命名完整演练
#   核心安全原则（生产环境同样适用）：
#     1. 先 dry-run：只打印"改造前 → 改造后"映射表，不实际执行
#     2. 冲突检测：新文件名之间不能重复，也不能与已有文件冲突
#     3. 两阶段改名：a → tmp_a → final_a，避免"交换文件名"时互相覆盖
#     4. 失败回滚：记录已完成的操作，出错时按逆序改回
#     5. 操作范围限定在临时目录，绝不碰真实文件
#
#   本演示在 tempfile 临时目录中运行，结束时彻底删除。
def demo_batch_rename() -> None:
    print("\n" + "=" * 74)
    print("【8】★★ 批量重命名演练（在临时目录中，绝不触碰真实文件）")
    print("=" * 74)

    tmp = Path(tempfile.mkdtemp(prefix="pathlib_rename_"))
    print(f"本次演练的沙箱目录: {tmp}")

    try:
        # ---- 准备测试文件 ----
        originals = {
            "IMG_001.JPG": "照片1",
            "IMG_002.JPG": "照片2",
            "IMG_003.jpeg": "照片3",
            "readme.TXT": "说明",
            "report.final.pdf": "报告",
            "无扩展名文件": "中文名",
        }
        for name, content in originals.items():
            (tmp / name).write_text(content, encoding="utf-8")

        print(f"\n① 改造前（{len(originals)} 个文件）：")
        for f in sorted(tmp.iterdir()):
            print(f"  {f.name:<22} {f.stat().st_size:>3} 字节")

        # ---- 方案 A：扩展名归一化（小写） ----
        print("\n② 方案 A：扩展名统一转小写（JPG → jpg）")
        plan_a = []
        for f in sorted(tmp.iterdir()):
            if f.suffix and f.suffix != f.suffix.lower():
                new_name = f.with_suffix(f.suffix.lower()).name
                plan_a.append((f.name, new_name))
            else:
                plan_a.append((f.name, f.name))
        print("  dry-run 映射表（尚未真正执行）：")
        for old, new in plan_a:
            mark = "  ← 需修改" if old != new else ""
            print(f"    {old:<22} → {new:<22}{mark}")
        # 真正执行
        for old, new in plan_a:
            if old != new:
                (tmp / old).rename(tmp / new)
        print("  执行后结果：")
        for f in sorted(tmp.iterdir()):
            print(f"    {f.name}")

        # ---- 方案 B：加序号并模板化 ----
        print("\n③ 方案 B：模板化重命名为「序号_原名.后缀」（对所有文件生效）")
        all_files = sorted(tmp.iterdir())
        plan_b = []
        for idx, f in enumerate(all_files, start=1):
            # 主名保留原样但转小写，后缀统一小写；无后缀则不补后缀
            stem = f.stem.lower()
            suffix = f.suffix.lower()
            new_name = f"{idx:03d}_{stem}{suffix}"
            plan_b.append((f, f.with_name(new_name)))
        print("  dry-run 映射表（先只打印，不执行）：")
        for old_p, new_p in plan_b:
            print(f"    {old_p.name:<24} → {new_p.name}")
        # 冲突检测：确保所有新名字互不相同，且不与现有文件冲突
        new_names = [p.name for _, p in plan_b]
        existing = {f.name for f in all_files}
        collision = [n for n in new_names if n in existing]
        assert len(new_names) == len(set(new_names)), "重命名目标之间存在冲突，已中止"
        assert not collision, f"目标名与现有文件冲突: {collision}，已中止"
        print(f"  冲突检测通过（{len(new_names)} 个目标名互不相同，且不与现有文件冲突）")
        # 真正执行
        for old_p, new_p in plan_b:
            old_p.rename(new_p)
        print("  执行后目录：")
        for f in sorted(tmp.iterdir()):
            print(f"    {f.name}")

        # ---- 方案 C：★两阶段改名演示（解决交换类操作互相覆盖）----
        print("\n④ 方案 C：两阶段改名（防止目标名与现有文件冲突）")
        a = tmp / "step_a.txt"
        b = tmp / "step_b.txt"
        a.write_text("原本是A", encoding="utf-8")
        b.write_text("原本是B", encoding="utf-8")
        print(f"  初始: a='{a.read_text(encoding='utf-8')}', "
              f"b='{b.read_text(encoding='utf-8')}'")
        print("  目标: 交换 a 和 b 的【文件名】（直接改会互相覆盖）")

        # 若直接 a.rename(b)：Windows 会因目标存在而报错或覆盖
        # 两阶段：先都改成临时名，再改到目标名
        stage1_a = tmp / "step_tmp1.txt"
        stage1_b = tmp / "step_tmp2.txt"
        a.rename(stage1_a)
        b.rename(stage1_b)
        print("  阶段一：全部改为临时名（此时与任何现有文件都不冲突）")
        print(f"    a → {stage1_a.name}, b → {stage1_b.name}")
        # 阶段二：改为最终名
        final_b = tmp / "step_a.txt"
        final_a = tmp / "step_b.txt"
        stage1_b.rename(final_b)     # 原 b 的内容现在叫 step_a.txt
        stage1_a.rename(final_a)     # 原 a 的内容现在叫 step_b.txt
        print("  阶段二：临时名 → 最终名")
        print(f"  结果: step_a.txt 内容='{final_b.read_text(encoding='utf-8')}'"
              f", step_b.txt 内容='{final_a.read_text(encoding='utf-8')}'")
        print("  结论：交换/循环改名必须走两阶段，单阶段会丢数据")

        # ---- 失败回滚的思路演示 ----
        print("\n⑤ 回滚演示：中途失败时如何还原")
        targets = sorted(tmp.glob("*.txt"))
        renamed_done = []          # 记录已完成的操作
        failed = False
        try:
            for i, f in enumerate(targets):
                new_p = f.with_name(f"renamed_{f.name}")
                f.rename(new_p)
                renamed_done.append((new_p, f))     # 记录 (新路径, 原路径)
            # 人为制造一个失败点
            raise RuntimeError("模拟第 100 个文件出错")
        except RuntimeError as e:
            print(f"  捕获异常: {e}")
            print(f"  已完成 {len(renamed_done)} 次改名，开始回滚：")
            # ★ 逆序回滚：把已改的改回去
            for new_p, old_p in reversed(renamed_done):
                new_p.rename(old_p)
            failed = True
        print(f"  回滚完成，目录中已无 renamed_ 前缀文件: "
              f"{not any(f.name.startswith('renamed_') for f in tmp.iterdir())}")
        print(f"  最终文件: {sorted(f.name for f in tmp.iterdir())}")

        # ---- 汇总当前状态 ----
        print("\n⑥ 本次演练结束时的目录状态：")
        for f in sorted(tmp.iterdir()):
            print(f"  {f.name:<26} {f.stat().st_size:>3} 字节  "
                  f"后缀={f.suffix!r} 主名={f.stem!r}")

    finally:
        # ★ 无论如何都清理临时目录（真实文件从未被访问或修改）
        shutil.rmtree(tmp, ignore_errors=True)
        print(f"\n已删除沙箱目录: {tmp}")
        print(f"  确认目录不存在: {not tmp.exists()}")


# ===== 语法解析 =====
# 【9】路径安全：防目录穿越
#   设计意图：任何"用户传入路径"拼接进文件操作前，都必须确认
#             最终路径仍在允许的根目录内，否则 ../ 可逃逸到任意位置。
#   标准写法：resolve() 消除 .. 和符号链接后，再用 is_relative_to 校验。
def demo_path_safety() -> None:
    print("\n" + "=" * 74)
    print("【9】路径安全：防目录穿越")
    print("=" * 74)

    allowed_root = Path("/data/uploads").resolve()
    print(f"允许的根目录: {allowed_root}")

    # 正常访问
    safe = (allowed_root / "photo.png").resolve()
    print(f"\n① 正常文件名:")
    print(f"  {safe}")
    print(f"  is_relative_to(根) = {safe.is_relative_to(allowed_root)}   ✓ 安全")

    # 攻击尝试：.. 逃逸
    evil = (allowed_root / ".." / ".." / "etc" / "passwd").resolve()
    print(f"\n② 目录穿越攻击尝试:")
    print(f"  原始输入: '../../etc/passwd'")
    print(f"  resolve() 后: {evil}")
    print(f"  is_relative_to(根) = {evil.is_relative_to(allowed_root)}   ✗ 已被拦截")

    # 安全检查函数
    def safe_join(root: Path, user_input: str) -> Path | None:
        """把用户输入安全地拼到 root 下，越界返回 None。"""
        candidate = (root / user_input).resolve()
        # resolve() 必须放在最后，否则 .. 还未来得及展开就检查
        if candidate.is_relative_to(root.resolve()):
            return candidate
        return None

    print("\n③ 安全检查函数演示：")
    for user_in in ["photo.png", "sub/dir/file.txt",
                    "../../../etc/passwd", "a/../../b.png"]:
        result = safe_join(allowed_root, user_in)
        status = f"允许 → {result}" if result else "拒绝（越界）"
        print(f"  输入 {user_in!r:<28} {status}")

    print("\n★ 安全要点：")
    print("  1. 必须先 resolve() 再检查，否则 '..' 还没展开")
    print("  2. 用 is_relative_to 而不是字符串 startswith（后者有前缀欺骗漏洞）")
    print(f"  3. 反例：'/data/uploads_evil'.startswith('/data/uploads') 为 True，但并不在目录内")


# ===== 语法解析 =====
# 【10】Windows 平台注意事项
def demo_windows_notes() -> None:
    print("\n" + "=" * 74)
    print("【10】Windows 平台注意事项")
    print("=" * 74)

    print("① 路径大小写不敏感（Linux 敏感）：")
    p = Path("Data/Sample.JSON")
    print(f"  Path('Data/Sample.JSON').name      = {p.name}")
    print(f"  Path('data/sample.json') == p      = {Path('data/sample.json') == p}")
    print(f"  → Windows 上结果 {Path('data/sample.json') == p}，Linux 上为 False")
    print("  ★ 跨平台代码不要依赖大小写敏感的路径比较")

    print("\n② Windows 保留文件名（不能作为文件名）：")
    reserved = ["CON", "PRN", "AUX", "NUL",
                "COM1", "COM2", "LPT1", "LPT2"]
    print(f"  保留名: {reserved}")
    print("  ★ Windows 下创建这些名字会失败，程序应提前校验")

    print("\n③ 非法字符：")
    illegal = ['<', '>', ':', '"', '/', '\\', '|', '?', '*']
    print(f"  Windows 文件名非法字符: {illegal}")
    print("  Linux 只禁止 '/' 和 '\\0'，故跨平台文件名建议只保留 [a-zA-Z0-9_-]")

    print("\n④ 路径分隔符：")
    print(f"  os.sep 在本平台 = {os.sep!r}")
    print(f"  os.altsep      = {os.altsep!r}")
    print(f"  Path 对象的 str() 输出会自动用本平台分隔符")
    print(f"  Path('a/b/c') 的 parts = {Path('a/b/c').parts}  # 内部已按本平台拆分")

    print("\n⑤ 盘符与相对路径：")
    print(f"  Path('C:/Windows').drive          = {PureWindowsPath('C:/Windows').drive!r}")
    print(f"  Path('C:/Windows').root           = {PureWindowsPath('C:/Windows').root!r}")
    print(f"  Path('C:/a/b.txt').is_absolute() = {PureWindowsPath('C:/a/b.txt').is_absolute()}")
    print(f"  PurePosixPath('/a/b').is_absolute() = {PurePosixPath('/a/b').is_absolute()}")

    print("\n⑥ 长路径限制（Windows MAX_PATH 260）：")
    print("  Windows 默认单路径不超过 260 字符，深层嵌套目录易超限")
    print("  ★ 解决：路径尽量短，或在注册表/组策略开启 LongPathsEnabled，"
          "或用 \\\\?\\ 前缀")


# ===== 语法解析 =====
# 【11】小结
def demo_summary() -> None:
    print("\n" + "=" * 74)
    print("【11】小结：pathlib 使用要点")
    print("=" * 74)
    print("""
  1. / 运算符拼接路径；Path 对象不是字符串，需要时 str(p)
  2. .stem 主体 / .suffix 末后缀 / .suffixes 全部后缀，多后缀文件易混
  3. .parent 是 Path 不是 str；Path('/').parent 是它自己（死循环来源）
  4. 变形方法 with_name/with_suffix/with_stem/with_stem 都返回新对象
  5. mkdir(parents=True, exist_ok=True) 是生产标准写法
  6. iterdir 只看当前层；glob 的 * 不跨层；rglob 递归但会返回目录
  7. 只关心文件时用 rglob('*.txt') 或加 is_file() 过滤
  8. 批量重命名的铁律：先 dry-run、再查冲突、必要时两阶段改名、
     失败按逆序回滚
  9. rmtree 递归删除不可逆，执行前务必确认路径
  10. 处理用户传入的路径必须 resolve() + is_relative_to() 双重校验
  11. 跨平台代码统一用 / 分隔，不要依赖路径大小写敏感
    """)


def main() -> None:
    """主入口。"""
    print("=" * 74)
    print("pathlib：文件与目录操作完整实战")
    print("=" * 74)
    print(f"Python 版本: {sys.version.split()[0]}")
    print(f"平台: {sys.platform}（分隔符 {os.sep!r}）")
    print()

    demo_construction()
    demo_attributes()
    demo_transform()
    demo_mkdir()
    demo_traverse()
    demo_os_vs_pathlib()
    demo_stat()
    demo_batch_rename()
    demo_path_safety()
    demo_windows_notes()
    demo_summary()


if __name__ == "__main__":
    main()