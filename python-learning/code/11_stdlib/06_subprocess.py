"""
================================================================================
 06_subprocess.py  ——  subprocess：调用外部程序
================================================================================

【演示的语法点】
 1. subprocess.run：最常用的顶层 API，返回 CompletedProcess
 2. capture_output=True：捕获 stdout/stderr（★ 不能和 stdin 一起用）
 3. text=True / encoding：子进程输出解码，避免处理 bytes
 4. check=True：返回码非 0 直接抛 CalledProcessError
 5. shell=True 的【命令注入风险】与安全替代方案
 6. 管道：Popen + communicate / 两个子进程串联
 7. 超时控制：timeout 参数 + TimeoutExpired 异常
 8. Windows 注意事项：list vs shell、编码 GBK、CREATE_NO_WINDOW
 9. 实战：git 调用的几种写法、批量 ping、程序版本检测

【预期输出摘要】
 - "run 基本用法" 小节：打印 echo 命令的 returncode/stdout/stderr
 - "shell 风险" 小节：演示命令注入把不同参数变成多条命令
 - "管道" 小节：两个子进程的输出被串联处理
================================================================================

"""

from __future__ import annotations

import subprocess
import sys


# ===== 语法解析 =====
# 【1】subprocess.run：最常用的顶层接口
#   语法规则：subprocess.run(args, capture_output=?, text=?, check=?, shell=?, timeout=?)
#     - 返回 CompletedProcess 对象，含 .returncode / .stdout / .stderr / .args
#     - .returncode = 0 表示成功，非 0 表示失败（约定，不代表所有程序）
#   执行顺序：启动子进程 → 等待结束 → 收集输出 → 返回结果对象
#   设计意图：把"最常见的同步调用"收敛成一个函数，
#             复杂场景（Popen）则是它的底层原语。
def demo_run_basic() -> None:
    # 调用 Python 自身作为外部命令，保证跨平台可运行
    cmd = [sys.executable, "-c", "print('来自子进程的输出')"]
    result = subprocess.run(cmd, capture_output=True, text=True)

    print(f"  命令：{cmd[:2]} -c ...")
    print(f"  returncode = {result.returncode}   ← 0 表示成功")
    print(f"  stdout     = {result.stdout!r}")
    print(f"  stderr     = {result.stderr!r}   （stderr 单独缓冲）")
    print(f"  CompletedProcess.args = {result.args[:2]} ...")

    # 不捕获输出时，子进程直接继承父进程的终端（能看到实时输出）
    print("  不捕获输出（直接打印到当前终端）：")
    subprocess.run([sys.executable, "-c", "print('  → 直接显示')"])

    # check=True：非 0 返回码自动抛异常
    print("  check=True 演示：")
    try:
        r = subprocess.run([sys.executable, "-c", "import sys; sys.exit(3)"],
                           capture_output=True, text=True, check=True)
        print(f"  未抛出（不应到达）: {r.returncode}")
    except subprocess.CalledProcessError as e:
        print(f"  ⚠ 抛 CalledProcessError，returncode={e.returncode}，stderr={e.stderr!r}")

    # 返回码约定
    ok = subprocess.run([sys.executable, "-c", "pass"], capture_output=True)
    fail = subprocess.run([sys.executable, "-c", "raise SystemExit(1)"], capture_output=True)
    print(f"  正常退出 returncode = {ok.returncode}；异常退出 returncode = {fail.returncode}")

    # ⚠ 坑：文件不存在会抛 FileNotFoundError，不是 CalledProcessError
    try:
        subprocess.run(["this_command_does_not_exist_xyz"], capture_output=True)
    except FileNotFoundError as e:
        print(f"  ⚠ 命令不存在 → FileNotFoundError: {e.__class__.__name__}")


# ===== 语法解析 =====
# 【2】★ capture_output 与 text 的坑
#   规则：
#     capture_output=True 不能与 stdout=PIPE / stderr=PIPE 同时指定 → ValueError
#     text=True 等价于 universal_newlines=True，自动按 locale 解码
#   设计意图：避免多个参数组合出矛盾的状态，Python 直接拒绝。
def demo_capture() -> None:
    # text=True：得到 str
    r1 = subprocess.run([sys.executable, "-c", "print('中文输出')"],
                        capture_output=True, text=True, encoding="utf-8")
    print(f"  text=True      → stdout 类型={type(r1.stdout).__name__}，值={r1.stdout!r}")

    # ★ 注意：只要显式传了 encoding（即使 text=False），Python 也会自动按文本模式解码
    #   所以"默认(bytes)"演示必须【完全不传 encoding】
    r2 = subprocess.run([sys.executable, "-c", "print('中文输出')"],
                        capture_output=True)
    print(f"  默认(bytes)    → stdout 类型={type(r2.stdout).__name__}，值={r2.stdout!r}")
    print(f"  手动 decode    → {r2.stdout.decode('utf-8').strip()!r}")
    r2b = subprocess.run([sys.executable, "-c", "print('中文输出')"],
                         capture_output=True, text=True, encoding="utf-8")
    print(f"  显式 encoding  → 同样得到 str：{type(r2b.stdout).__name__}（自动解码，无需手写 decode）")

    # encoding 参数显式指定编码（★ Windows 下 subprocess 常输出 GBK）
    print("  ★ Windows 上 Python 输出可能是 GBK/CP936，所以务必显式 encoding='utf-8'")

    # 冲突组合会报错
    try:
        subprocess.run([sys.executable, "-c", "pass"],
                       stdout=subprocess.PIPE, capture_output=True)
    except ValueError as e:
        print(f"  ⚠ capture_output 与 stdout=PIPE 冲突 → ValueError: {e}")

    # 分离 stdout 和 stderr 是子进程调试的关键手段
    r3 = subprocess.run(
        [sys.executable, "-c", "import sys; print('正常信息'); sys.stderr.write('错误信息\\n')"],
        capture_output=True, text=True, encoding="utf-8"
    )
    print(f"  stdout = {r3.stdout.strip()!r}")
    print(f"  stderr = {r3.stderr.strip()!r}")
    print("  ★ 排查问题时 stderr 最有价值，绝不要丢弃")


# ===== 语法解析 =====
# 【3】★ shell=True 的风险与正确用法
#   规则：
#     shell=False（默认）：第一个元素是【可执行程序名】，后面的都是【参数】（不解析）
#     shell=True：整个字符串交给系统 shell 解释，会【解析元字符】
#   核心风险：把用户输入拼进 shell 字符串 → 【命令注入】
#   设计意图：subprocess 默认不经过 shell，从设计上消除注入面。
def demo_shell_risk() -> None:
    # 安全：参数以列表传入，shell 不参与解释
    safe_cmd = [sys.executable, "-c", "import sys; print('参数:', sys.argv[1])", "hello world; rm -rf /"]
    r1 = subprocess.run(safe_cmd, capture_output=True, text=True, encoding="utf-8")
    print(f"  安全写法（list）：{r1.stdout.strip()!r}")
    print(f"     → '; rm -rf /' 被当成【普通字符串参数】打印出来，没有执行")

    # 危险：字符串拼接进 shell，';' 会被解释成"多条命令的分隔符"
    user_input = "hello; echo 我被注入了"
    dangerous_cmd = f"{sys.executable} -c \"print('参数:', 'x')\" {user_input}"
    #   演示原理：用 echo 这个安全命令来展示注入效果（不执行任何破坏性操作）
    demo = subprocess.run(["echo", f"输出:{user_input}"], capture_output=True, text=True,
                          encoding="utf-8")
    print(f"  危险原理演示（echo）：{demo.stdout.strip()!r}")

    # 真正演示注入：让命令分隔符生效
    #   ★ Windows cmd.exe 用 '&' / '&&' 分隔命令；Unix sh 用 ';' / '&&'
    #   统一写法用 '&&'，两个平台都支持（且不涉及中文，避免控制台编码干扰）
    sep = "&&" if sys.platform == "win32" else ";"
    injected = subprocess.run(
        f"echo first_part {sep} echo INJECTED",
        shell=True, capture_output=True, text=True, encoding="utf-8",
        errors="replace",                 # ★ shell 回显可能是本地代码页，容错解码
    )
    output = injected.stdout or ""
    print(f"  ⚠ shell=True 时 '{sep}' 分隔生效：{output.strip()!r}")
    print(f"     输出里出现 INJECTED = {'INJECTED' in output}")
    print("     这就是命令注入：攻击者的输入被当成了命令执行")
    print(f"     ★ 注意 cmd.exe 不认 ';'，只认 '&'/'&&'；这就是跨平台 shell 的麻烦")

    # ✅ shell=False 的安全替代：整个参数用列表传递
    safe_alt = subprocess.run(
        [sys.executable, "-c", "import sys; print('收到:', sys.argv[1])", user_input],
        capture_output=True, text=True, encoding="utf-8"
    )
    print(f"  ✅ 安全替代写法：{safe_alt.stdout.strip()!r}")
    print(f"     '{sep}' 被安全地当作数据传入，没有执行第二条命令")

    # 什么时候才真的需要 shell=True？
    print("  ── 何时需要 shell=True ──")
    print("     需要使用【shell 特性】时：管道 |、重定向 >、通配符 *、&& 串联命令")
    # 演示：shell=True 才能识别管道
    piped = subprocess.run("echo hello | tr a-z A-Z", shell=True,
                           capture_output=True, text=True, encoding="utf-8")
    print(f"     管道示例：{piped.stdout.strip()!r}   ← 只有 shell 能把 | 当管道")

    # ★ 安全折中：确实要用 shell，但用户输入仍走列表占位
    print("  ★ 折中方案：cmd 中用固定字符串 + 列表占位")
    print("     subprocess.run(f'{sys.executable} script.py ' + shlex.quote(user_input), shell=True)")
    import shlex
    safe_with_shell = subprocess.run(
        f"{shlex.quote(sys.executable)} -c {shlex.quote('import sys; print(sys.argv[1:])')} "
        f"{shlex.quote(user_input)}",
        shell=True, capture_output=True, text=True, encoding="utf-8"
    )
    print(f"     shlex.quote 转义后：{safe_with_shell.stdout.strip()!r}   ← 注入被阻断")


# ===== 语法解析 =====
# 【4】管道：用 Popen 把两个命令串起来
#   语法规则：
#     p1 = Popen(cmd1, stdout=PIPE)
#     p2 = Popen(cmd2, stdin=p1.stdout, stdout=PIPE)
#     p1.stdout.close()      ★ 必须关闭，否则 p2 永远等不到 EOF
#     out2 = p2.communicate()
#   设计意图：让 Unix 的管道模型在 Python 中重现，
#             支持流式处理【超大输出】而无需一次性读进内存。
def demo_pipe() -> None:
    # 场景：把子进程输出里的中文单词全部转大写
    #   相当于 shell 的： python -c "..." | tr a-z A-Z
    cmd1 = [sys.executable, "-c", "print('hello python world')"]
    cmd2 = ["tr", "a-z", "A-Z"]

    p1 = subprocess.Popen(cmd1, stdout=subprocess.PIPE, text=True, encoding="utf-8")
    p2 = subprocess.Popen(cmd2, stdin=p1.stdout, stdout=subprocess.PIPE,
                          text=True, encoding="utf-8")
    # ★ 关键：把 p1 的 stdout 交给 p2 后，必须在父进程里关闭这个管道句柄
    #   否则 p1 永远不会收到"所有写端已关闭"的信号，p2.communicate() 会永久阻塞
    if p1.stdout is not None:
        p1.stdout.close()

    out2, _ = p2.communicate()           # communicate 会等待 p2 结束
    p1.wait()
    print(f"  管道：'hello python world' → {out2.strip()!r}")
    print(f"  p1.returncode={p1.returncode}, p2.returncode={p2.returncode}  （0 = 成功）")

    # 在 Python 内部做管道（不依赖 tr，跨平台安全）
    #   第二个例子演示"两次 write"也能被正确拼接读取
    cmd_a = [sys.executable, "-c", "import sys; sys.stdout.write('abc'); sys.stdout.write('def')"]
    pa = subprocess.Popen(cmd_a, stdout=subprocess.PIPE, text=True, encoding="utf-8")
    # ★ 顺序很重要：必须【先】把管道交给 pb，【再】关闭父进程里的这个句柄
    #   提前 close 会导致 Popen 拿到已关闭的 fd（ValueError: I/O operation on closed file）
    pb = subprocess.Popen([sys.executable, "-c", "import sys; print(sys.stdin.read().upper())"],
                          stdin=pa.stdout, stdout=subprocess.PIPE, text=True, encoding="utf-8")
    if pa.stdout is not None:
        pa.stdout.close()      # 关闭父进程的这一端，子进程才会收到 EOF
    out_b, _ = pb.communicate()
    pa.wait()
    print(f"  Python 管到 Python：{out_b.strip()!r}   ← 说明分两次 write 也能被正确读取")


# ===== 语法解析 =====
# 【5】超时控制：防止子进程永久挂起
#   规则：run(..., timeout=秒数) 超时抛 subprocess.TimeoutExpired
#   ⚠ 陷阱：超时抛异常后，子进程可能还在后台运行！
#            必须 run(..., timeout=..) 或 kill() 手动清理。
def demo_timeout() -> None:
    # 正常完成
    r = subprocess.run([sys.executable, "-c", "print('快速完成')"],
                       capture_output=True, text=True, encoding="utf-8", timeout=5)
    print(f"  未超时：returncode={r.returncode}, stdout={r.stdout.strip()!r}")

    # 超时
    print("  超时演示（子进程 sleep 5 秒，但只给 0.3 秒）：")
    try:
        subprocess.run([sys.executable, "-c", "import time; time.sleep(5)"],
                       capture_output=True, timeout=0.3)
    except subprocess.TimeoutExpired as e:
        print(f"    ⚠ 抛 TimeoutExpired：timeout={e.timeout} 秒")
        print(f"    ⚠ 部分输出：{e.stdout!r}   （已执行的内容可能丢失）")

    # ★ 安全用法：用 Popen + kill 确保进程被清理
    print("  ✅ 安全做法：Popen + poll + kill")
    proc = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(30)"],
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        proc.wait(timeout=0.3)
    except subprocess.TimeoutExpired:
        proc.kill()                      # 终止子进程
        proc.communicate()               # ★ 必须再 communicate() 回收管道，否则僵尸进程
        print(f"    已 kill，returncode={proc.returncode}")
        print(f"    ⚠ Windows 上 kill 等价于 TerminateProcess → 返回码 1；"
              f"Unix 上是信号终止（负数如 -9）")

    # 超时的实际用途：给外部命令设"最长等待"
    print("  实际用途：网络请求式的命令加超时，防止接口挂死拖垮主程序")


# ===== 语法解析 =====
# 【6】Windows 平台注意事项
def demo_windows_notes() -> None:
    print("  ① shell=True 在 Windows 上走 cmd.exe，语法与 Unix 的 sh/bash 不同")
    print("     '&'/'&&' 两边都支持，但 ';' 只有 Unix 认；变量展开/通配符差异更大")
    print("     ⚠ 别写跨平台 shell 命令；✅ 跨平台方案：shell=False + 列表参数")

    print("  ② 路径与可执行文件：")
    print(f"     Windows 上 'ls'/'cat' 不存在，要用 'dir'/'type'")
    print(f"     Python 解释器路径必须用 sys.executable 取，不能硬编码 'python'")

    print("  ③ 编码：Windows 控制台默认 GBK(cp936)，子进程输出中文可能乱码")
    print("     ✅ 始终显式写 encoding='utf-8'，并让子进程也用 UTF-8 输出")

    print("  ④ 弹出黑色控制台窗口：")
    print("     直接 run() 可能闪一个黑框。解决：")
    print("       Windows: creationflags=subprocess.CREATE_NO_WINDOW")
    print("       或 startinfo=STARTUPINFO() + wShowWindow=SW_HIDE")
    print("  ⑤ 结束进程：taskkill /T /F 可连子进程树一起杀")

    # 演示 encoding 必需性：让子进程输出中文，不指定编码时的风险
    code = "print('你好世界')"
    # 子进程自己设 PYTHONIOENCODING 避免 Windows 控制台编码问题
    import os
    env = dict(os.environ)
    env["PYTHONIOENCODING"] = "utf-8"
    r = subprocess.run([sys.executable, "-c", code], capture_output=True,
                       text=True, encoding="utf-8", env=env)
    print(f"  ── 编码验证 ──")
    print(f"     子进程输出：{r.stdout.strip()!r}   ← 显式 UTF-8 解码成功")

    # CREATE_NO_WINDOW 常量只在 Windows 上存在
    if sys.platform == "win32":
        flag = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        print(f"  CREATE_NO_WINDOW 常量存在：value={flag}")
        r2 = subprocess.run([sys.executable, "-c", "print('无黑框运行')"],
                            capture_output=True, text=True, encoding="utf-8",
                            creationflags=flag)
        print(f"  带 creationflags 运行：{r2.stdout.strip()!r}")


# ===== 语法解析 =====
# 【7】实战：外部命令调用的几种典型场景
def demo_practice() -> None:
    # 场景 1：检测 Python 版本（最常见的"外部命令"其实是调用解释器本身）
    r = subprocess.run([sys.executable, "--version"], capture_output=True,
                       text=True, encoding="utf-8")
    print(f"  ① Python 版本：{r.stdout.strip()}")

    # 场景 2：执行一段计算密集的代码，用子进程隔离（崩溃不影响主程序）
    heavy = (
        "import sys\n"
        "sum(i*i for i in range(10**7))\n"
        "print('计算完成')\n"
    )
    r = subprocess.run([sys.executable, "-c", heavy], capture_output=True,
                       text=True, encoding="utf-8")
    print(f"  ② 子进程计算：{r.stdout.strip()}")

    # 场景 3：传入大批量数据给子进程（stdin 管道）
    #   通过 communicate(input=...) 把数据送进去
    data = "\n".join(str(i) for i in range(10))
    code = "import sys; data=sys.stdin.read().split(); print('收到', len(data), '个数:', data[:5])"
    r = subprocess.run([sys.executable, "-c", code], input=data,
                       capture_output=True, text=True, encoding="utf-8")
    print(f"  ③ 通过 stdin 传数据：{r.stdout.strip()}")

    # 场景 4：批量执行命令并汇总结果
    print("  ④ 批量执行并汇总：")
    cmds = {
        "check-1": "print('ok1')",
        "check-2": "import sys; sys.exit(1)",
        "check-3": "print('ok3')",
    }
    results = {}
    for name, code in cmds.items():
        res = subprocess.run([sys.executable, "-c", code],
                             capture_output=True, text=True, encoding="utf-8")
        results[name] = (res.returncode, res.stdout.strip())
    for name, (rc, out) in results.items():
        status = "✅ 成功" if rc == 0 else f"❌ 失败(rc={rc})"
        print(f"      {name}: {status}  输出={out!r}")

    # 场景 5：用户输入的命令行参数（安全处理）
    #   注意：本示例不调用 input()（避免阻塞），用固定字符串模拟
    user_cmd = sys.executable
    user_args = "-c"
    user_script = "import sys; print('执行用户脚本:', sys.argv[1:])"
    user_input = ["arg1", "arg2"]
    #   ✅ 安全：所有参数放进列表，绝不拼接字符串
    r = subprocess.run([user_cmd, user_args, user_script] + user_input,
                       capture_output=True, text=True, encoding="utf-8")
    print(f"  ⑤ 安全执行用户参数：{r.stdout.strip()}")

    # 场景 6：交互式输入模拟（communicate 一次性给完多行）
    print("  ⑥ 模拟交互输入：")
    code = (
        "import sys\n"
        "a = input('名字: ')\n"
        "b = input('年龄: ')\n"
        "print(f'你好 {a}, 你 {b} 岁')\n"
    )
    r = subprocess.run([sys.executable, "-c", code], input="小明\n18\n",
                       capture_output=True, text=True, encoding="utf-8")
    print(f"      {r.stdout.strip()!r}")
    print("      ★ input() 只在【子进程】里用，父进程不受阻塞影响")


def main() -> None:
    print("=" * 60)
    print("【1】subprocess.run 基本用法")
    print("=" * 60)
    demo_run_basic()

    print()
    print("=" * 60)
    print("【2】捕获输出与编码")
    print("=" * 60)
    demo_capture()

    print()
    print("=" * 60)
    print("【3】shell=True 的命令注入风险")
    print("=" * 60)
    demo_shell_risk()

    print()
    print("=" * 60)
    print("【4】管道：Popen + communicate")
    print("=" * 60)
    demo_pipe()

    print()
    print("=" * 60)
    print("【5】超时控制")
    print("=" * 60)
    demo_timeout()

    print()
    print("=" * 60)
    print("【6】Windows 平台注意事项")
    print("=" * 60)
    demo_windows_notes()

    print()
    print("=" * 60)
    print("【7】实战：七种典型场景")
    print("=" * 60)
    demo_practice()

    print()
    print("=" * 60)
    print("小结")
    print("=" * 60)
    print("  1. 默认用 shell=False + 列表参数，这是最安全的写法")
    print("  2. returncode=0 表示成功；check=True 会抛 CalledProcessError")
    print("  3. capture_output 与 stdout=PIPE 互斥；text=True 自动解码")
    print("  4. ★ shell=True 遇用户输入 = 命令注入，绝不要拼接字符串")
    print("  5. 管道必须 p1.stdout.close()，否则 p2.communicate() 永久阻塞")
    print("  6. 超时后子进程可能残留，要用 Popen + kill + communicate 清理")
    print("  7. Windows：GBK 编码、CREATE_NO_WINDOW、别用 ls/cat")


if __name__ == "__main__":
    main()