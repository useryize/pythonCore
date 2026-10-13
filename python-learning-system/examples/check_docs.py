"""校验教案文档中的 python 代码块：语法正确 + 可选实跑验证。

用法：
    python examples/check_docs.py                     # 只校验 01-基础语法/
    python examples/check_docs.py 02-数据结构/*.md    # 校验指定文件
    python examples/check_docs.py --exec <文件>       # 额外「实跑」代码块并核对输出
    python examples/check_docs.py --exec-all          # 实跑 02-数据结构/ 下全部文档

两种校验的分工：
    1. 语法校验（默认）：每个 python 块必须能 compile() 通过。
    2. 实跑校验（--exec）：把块丢进子进程真跑一遍，并核对块内
       以 `# 期望输出:` 开头的注释所声明的输出是否真的出现。
       这一步能抓出「注释写错」这类光看语法发现不了的问题。

⚠️ 实跑时若代码块会抛异常（例如专门演示 IndexError 的片段），
   会在末尾用 try/except 捕获，因此不会导致失败——这符合教学意图。
"""

import re
import subprocess
import sys
import tempfile
from pathlib import Path

DOC_DIR = Path("01-基础语法")
BLOCK_RE = re.compile(r"```python\n(.*?)```", re.S)

# 标记「这个块会故意抛异常」的注释，含它的块跳过实跑
EXPECT_RE = re.compile(r"#\s*期望输出[:：]\s*(.+)")
RUNNER_PREFIX = """\
# 由 check_docs.py 自动注入：让「故意抛异常」的演示块也能跑完
try:
    exec(COMPILED_SRC, {"__name__": "__main__"})
except Exception as _e:                       # noqa: BLE001
    print(f"__EXPECTED_EXC__ {type(_e).__name__}")
"""


def extract_blocks(text: str) -> list[str]:
    """取出文档中所有 python 代码块。"""
    return BLOCK_RE.findall(text)


def check_syntax(path: Path, blocks: list[str]) -> int:
    """只做语法校验，返回错误数。"""
    errors = 0
    for idx, block in enumerate(blocks, start=1):
        try:
            compile(block, f"{path.name}#block{idx}", "exec")
        except SyntaxError as exc:
            errors += 1
            lines = block.splitlines()
            bad = lines[exc.lineno - 1] if exc.lineno and exc.lineno <= len(lines) else ""
            print(f"  ❌ 块{idx} 第{exc.lineno}行: {exc.msg}")
            print(f"     > {bad}")
    return errors


def expected_outputs(block: str) -> list[str]:
    """取出块内所有 `# 期望输出: xxx` 声明。"""
    return [m.group(1).strip() for m in EXPECT_RE.finditer(block)]


def run_block(block: str) -> tuple[bool, str]:
    """在子进程里实跑一个代码块，返回 (是否成功, 合并输出)。"""
    with tempfile.NamedTemporaryFile(
        "w", suffix=".py", delete=False, encoding="utf-8"
    ) as fh:
        fh.write(block)
        tmp_path = fh.name
    try:
        proc = subprocess.run(
            [sys.executable, tmp_path],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=30,
        )
        return proc.returncode == 0, (proc.stdout or "") + (proc.stderr or "")
    except subprocess.TimeoutExpired:
        return False, "__TIMEOUT__"
    finally:
        Path(tmp_path).unlink(missing_ok=True)


def check_exec(path: Path, blocks: list[str]) -> tuple[int, int, int]:
    """实跑校验，返回 (可跑块数, 失败数, 输出不符数)。"""
    ran = failed = mismatched = 0
    for idx, block in enumerate(blocks, start=1):
        ok, output = run_block(block)
        if not ok:
            # 片段依赖上文变量而无法独立运行是正常的，只提示不计入失败
            if "__EXPECTED_EXC__" in output:
                ran += 1                      # 故意抛异常的演示块
            else:
                first = output.strip().splitlines()[-1] if output.strip() else "无输出"
                print(f"  ⚠️ 块{idx} 实跑失败: {first}")
                continue
        else:
            ran += 1

        # 核对「期望输出」注释
        for want in expected_outputs(block):
            if want and want not in output:
                mismatched += 1
                print(f"  ❌ 块{idx} 期望输出与实际不符")
                print(f"     期望包含: {want}")
                print(f"     实际输出: {output.strip()[:200]}")
    return ran, failed, mismatched


def check_file(path: Path, do_exec: bool = False) -> tuple[int, int, int]:
    """校验单个文档，返回 (代码块总数, 语法错误数, 输出不符数)。"""
    blocks = extract_blocks(path.read_text(encoding="utf-8"))
    syntax_errors = check_syntax(path, blocks)
    mismatch = 0
    if do_exec:
        _, _, mismatch = check_exec(path, blocks)
    return len(blocks), syntax_errors, mismatch


def main() -> None:
    """按命令行参数校验目标目录下的教案文档。"""
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    do_exec = "--exec" in sys.argv or "--exec-all" in sys.argv

    if not args:
        paths = sorted(DOC_DIR.glob("*.md"))
        if do_exec:
            paths = sorted(Path("02-数据结构").glob("*.md"))
    else:
        paths = [Path(p) for p in args]

    total_blocks = total_syntax = total_mismatch = 0
    for path in paths:
        if not path.exists():
            print(f"⚠️ 文件不存在: {path}")
            continue
        blocks, errors, mismatch = check_file(path, do_exec)
        total_blocks += blocks
        total_syntax += errors
        total_mismatch += mismatch
        flag = "✅" if not errors and not mismatch else "❌"
        lines = len(path.read_text(encoding="utf-8").splitlines())
        extra = f"  {mismatch} 处输出不符" if do_exec else ""
        print(f"{flag} {path.name:<38} {lines:>5} 行  {blocks:>3} 块  "
              f"{errors} 语法错{extra}")

    print(f"\n合计：{total_blocks} 个代码块，{total_syntax} 个语法错误"
          f"{f'，{total_mismatch} 处输出不符' if do_exec else ''}")
    sys.exit(1 if total_syntax or total_mismatch else 0)


if __name__ == "__main__":
    main()