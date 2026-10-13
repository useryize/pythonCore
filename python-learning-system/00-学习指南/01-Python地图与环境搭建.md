# G01 · Python 地图与环境搭建

| 项目 | 内容 |
| --- | --- |
| 所属阶段 | 阶段零 学习指南 |
| 建议时长 | 90 分钟（含环境安装实操） |
| 前置知识 | 无，只需要会开电脑、会用鼠标 |
| 学习产出 | 能在自己电脑上装好 Python、跑通第一个脚本、看懂 `python` 命令的各种用法 |
| 配套示例 | `examples/00_hello_env_check.py` |

---

## 🎯 一、学习目标

- [ ] 能用一句话说清 Python 是什么，并说出它最擅长和不擅长什么
- [ ] 知道 Python 与 JavaScript / Java / Go 的差别，能判断一个需求该选哪种语言
- [ ] 知道当前主流 Python 版本号，并能解释 `3.12.4` 这串数字的含义
- [ ] 能在 Windows 上独立完成 Python 安装，并勾选 `Add python.exe to PATH`
- [ ] 能在命令行验证安装成功，会用 `python --version` 和 `where python`
- [ ] 遇到「'python' 不是内部或外部命令」时，知道按哪几步排查
- [ ] 能说清 `python xxx.py`、`python -m xxx`、交互式解释器三种运行方式的区别
- [ ] 能在 VS Code / PyCharm / IDLE 中任选一个写代码并运行
- [ ] 能独立跑通 `examples/00_hello_env_check.py` 并看懂它的输出

---

## 📖 二、知识讲解

### 2.1 Python 是什么：一门「让程序跑起来」的通用语言

**一句话定义**：Python 是一门高级、解释型、动态类型、跨平台的通用编程语言，以语法简洁、可读性强著称。

拆开理解这几个形容词：

| 术语 | 含义 | 对你的实际影响 |
| --- | --- | --- |
| 高级 | 贴近人类英语，不像 C 那样要手动管内存 | 同样的功能，Python 代码行数通常是 Java 的 1/3 |
| 解释型 | 不需要先编译成机器码，写完直接运行 | 改一行保存即可生效，反馈快，适合自学 |
| 动态类型 | 变量不用提前声明类型，`x = 1` 后还能 `x = "a"` | 少很多类型相关的报错，但要有自觉的命名习惯 |
| 通用 | 不是为某个特定领域设计的语言 | 写脚本、数据分析、网站、后端、自动化都能用 |

**为什么学 Python**：它是目前入门门槛最低、又能覆盖最多高薪岗位的语言。具体说三点：

1. **写起来快**。同样的「读一个 Excel、算平均数、画张图」，Python 5 行能写完，Java 可能要 30 行。初学者的心智负担小，能把精力放在「逻辑」而不是「语法」上。
2. **生态厚**。几乎所有现实需求都有成熟库：数据处理用 pandas、网页用 Flask/FastAPI、自动化用 selenium、机器学习用 PyTorch。**你不用从零造轮子。**
3. **就业面宽**。数据分析师、测试开发、运维、后端、算法工程师、AI 工程师，Python 都是主语言之一。

**打个比方**：语法之于编程，就像乐理之于弹琴。你不需要先学会作曲才能弹出三个音——先弹响，再理解为什么这样弹。Python 的语法门槛低，恰好让初学者能更快进入「做出东西」的正反馈循环。

---

### 2.2 Python 能做什么 / 不能做什么

必须诚实地说清楚能力边界，否则会浪费你大量时间。

#### ✅ Python 的强势区

| 领域 | 典型场景 | 代表库 / 工具 |
| --- | --- | --- |
| 数据分析 | 清洗 Excel、统计、可视化、生成报表 | pandas、numpy、matplotlib、openpyxl |
| 自动化办公 | 批量改名、合并 PDF、发邮件、爬取公开数据 | pathlib、openpyxl、pypdf、smtplib、requests |
| 数据科学 / AI | 机器学习、深度学习、大模型应用 | scikit-learn、PyTorch、transformers |
| Web 后端 | 网站 API、内部服务、小程序云函数 | Flask、FastAPI、Django |
| 测试开发 | 接口自动化、UI 自动化、性能脚本 | pytest、Selenium、Playwright |
| 运维与 DevOps | 批量管理服务器、部署脚本、监控告警 | paramiko、fabric、fabricio |
| 教学与科研 | 数值计算、论文实验、算法验证 | numpy、scipy、matplotlib |

#### ❌ Python 的弱势区

| 不擅长的场景 | 原因 | 该用什么 |
| --- | --- | --- |
| 手机 App 完整开发 | 缺少官方推荐的原生开发框架 | Flutter（Dart）、Kotlin/Swift |
| 大型高并发后端（每秒百万请求） | GIL 全局解释器锁导致多线程无法并行执行 CPU 密集任务 | Go、Java、Rust |
| 毫秒级延迟的游戏引擎 | 解释型语言，调用开销大 | C++、C#（Unity） |
| 浏览器端计算密集 | 要下载解释器，体积大、启动慢 | JavaScript / WebAssembly |
| 单文件 exe 体积敏感 | 打包后体积大（几十 MB 起） | Go、Java |

⚠️ **一个重要澄清**：很多人说「Python 慢」，这话不准确。慢的是「纯 Python 循环」：

```python
# 慢：10 万次循环逐个相加，纯 Python 层循环
total = 0
for i in range(100_000):
    total = i + total          # 每一轮都要解释执行

# 快：交给 C 语言的底层实现，Python 只调一次
total = sum(range(100_000))   # sum() 内部是 C 循环，快几十倍
```

所以现实原则是：**Python 负责「调度和表达」，把重活交给 numpy 这类底层库。** 这也是为什么 numpy 在数据分析领域地位极高。

⚠️ **另一个澄清**：Python 3.13 起提供了实验性的「无 GIL」构建，3.14 起无 GIL 正式受支持，3.15 有更快的 JIT。但这些都是**可选安装**，初学阶段完全不用管，先用好标准版。

---

### 2.3 与其他语言对比：JS / Java / Go

如果你已经会一点别的语言，这张表能帮你快速迁移认知。

| 维度 | Python | JavaScript | Java | Go |
| --- | --- | --- | --- | --- |
| 类型系统 | 动态 | 动态 | **静态强类型** | **静态强类型** |
| 运行方式 | 解释执行 | 浏览器解释 / Node.js | 先编译成 class 再执行 | 编译成二进制 |
| 编译 | 无需 | 无需 | `javac` 必需 | `go build` 必需 |
| 典型行数（同一功能） | 最少 | 中等 | 最多 | 少 |
| 性能 | 中等 | 中等 | 高 | 很高 |
| 内存 / 启动开销 | 中等 | 中等 | 高 | 极低 |
| 主要用途 | 数据、AI、自动化、后端 | 前端、Node 后端 | 企业级后端、Android | 云原生、微服务、CLI |
| 单文件独立部署 | 一般（需虚拟环境） | 一般 | 需打包成 jar | **强，天生单二进制** |
| 典型部署方式 | 服务器 / 桌面 / 服务器端跑 | 浏览器 | 服务器（JVM） | 服务器 / 容器 |

**怎么选**（这是你要记住的判断标准）：

- 目标是**浏览器里的东西**（网页交互、网页动画）→ JavaScript，没得选。
- 目标是**大型金融/银行核心系统、企业级后端**，团队有强类型习惯 → Java。
- 目标是**高并发云原生服务、要一个几十 MB 的二进制丢进容器** → Go。
- 目标是**处理数据、写脚本、做自动化、做 AI** → Python。

**从 JS/Java/Go 转 Python 的 4 个思维转换点**：

```python
# 1. 没有分号结尾，没有大括号，缩进就是语法
# JS/Java:
# if (x > 0) { console.log(x); }
if x > 0:
    print(x)

# 2. 没有类型声明，但可以用「类型标注」给编辑器提示（不影响运行）
def add(a: int, b: int) -> int:
    return a + b

# 3. 判断不用 else，用 elif；Python 没有 switch，用 match（3.10+）
n = 3
if n == 1:
    print("一")
elif n == 2:
    print("二")
else:
    print("其他")

# 4. for 循环用 in，没有 C 风格的 for(;;)
for i in range(3):
    print(i)
# JS 要写 for (let i = 0; i < 3; i++)
```

---

### 2.4 版本说明：为什么是 3.10+，版本号怎么看

**版本号怎么读**：`3.12.4`

- `3`：主版本号。Python 2 和 Python 3 语法不兼容，所以会跳过 2 直接到 3。现在只学 Python 3。
- `12`：次版本号。**每年 10 月发布一个新次版本**，新语法、新特性都在这一位。
- `4`：修订号。只修 bug，不加新功能。

**发布节奏**：每年 10 月一个新版（比如 3.12 是 2023-10-02，3.13 是 2024-10-07，3.14 是 2025-10-07）。每个版本的支持周期约 5 年：先约 2 年 bug 修复，再约 3 年只修安全问题。Python **没有 LTS**。

**本教材为什么要求 3.10+**：因为 3.10 引入了 `match/case` 结构化模式匹配，这是后面讲「多分支处理」时非常好用的语法；3.10 还把报错信息改得极其友好，会直接告诉你「你可能想写的是 xxx」。

**当前版本状态（截至 2026 年 10 月）**：

| 版本 | 发布时间 | 状态 | 学习建议 |
| --- | --- | --- | --- |
| 3.10 | 2021-10 | 2026-10 结束支持 | 本教材的**最低要求**，能跑 |
| 3.11 | 2022-10 | 安全维护 | 可以用 |
| 3.12 | 2023-10 | 安全维护 | 可以用 |
| 3.13 | 2024-10 | 活跃 | **推荐安装**（库兼容性最好） |
| 3.14 | 2025-10 | 活跃（最新稳定版） | 新特性多，可选 |
| 3.15 | 2026-10 | 新发布 | 生态尚未完全跟上，生产环境先观望 |

> 📌 **结论**：**装 3.13 或 3.14 的官方 Windows 安装包即可。** 不必追最新，`import` 某个第三方库时如果报 `ModuleNotFoundError`，八成是因为那个库还没支持你装的新版本——降到 3.13 通常就解决了。

**3.10~3.15 值得知道的核心特性**（按版本号递增，不需要现在就会用，只需要知道存在）：

| 版本 | 关键特性 | 一句话说明 |
| --- | --- | --- |
| 3.9 | `dict` 合并运算符 `\|`；`list[int]` 内置泛型 | 合并两个字典写 `a \| b` |
| 3.10 | **`match / case` 结构化模式匹配**；`X \| Y` 类型标注；报错带「你是不是想写」提示；括号包裹的多行 `with` | 判断分支不再需要一长串 `elif` |
| 3.11 | 性能比 3.10 快 10%~60%；**异常组 `ExceptionGroup` / `except*`**；`tomllib` 读 TOML | 报错能精确指出是第几个表达式的错 |
| 3.12 | **PEP 695 类型参数语法** `def f[T](x: T)`；f-string 解析大幅放宽；移除 `distutils` | 写泛型不用再 import `TypeVar` |
| 3.13 | 实验性无 GIL 构建、实验性 JIT、更好用的 REPL、类型参数默认值 | 交互式提示符支持多行和直接粘贴代码块 |
| 3.14 | **t-字符串 `t""`（模板字符串）**；注解延迟求值（PEP 649）；`concurrent.interpreters` 多解释器；无 GIL 正式受支持；`compression.zstd` | REPL 有语法高亮；标准库输出带颜色 |
| 3.15 | 惰性 import（PEP 810）；`open()` 默认 UTF-8（PEP 686）；`frozendict` 内置类型；`sentinel` 对象 | 启动更快的脚本与 Web 服务 |

**`match / case` 长这样**（3.10+ 可用，值得现在就记住）：

```python
# 传统写法：先判断类型，再取属性，重复且容易漏分支
def handle(command):
    if isinstance(command, dict):
        action = command.get("action")
        if action == "quit":
            return "退出"
        elif action == "add":
            return f"新增 {command.get('name')}"
        else:
            return "未知命令"
    return "非法输入"

# 3.10+ 写法：一段看清所有分支，漏了分支编译器会提醒你
def handle(command):
    match command:
        case {"action": "quit"}:
            return "退出"
        case {"action": "add", "name": str(name)}:
            return f"新增 {name}"
        case {"action": other_action}:
            return f"未知命令: {other_action}"
        case _:
            return "非法输入"
```

⚠️ **新手误区**：不要为了用新语法而用新语法。`match` 适合「结构化匹配」，如果只是判断几个数值，`if/elif` 更直白、更容易调试。

---

### 2.5 Windows 上安装 Python 的完整步骤

#### 第 1 步：下载官方安装包

1. 打开官网：**<https://www.python.org/downloads/windows/>**
2. 找到 **"Download Python 3.x.x"** 那一块（推荐 3.13 或 3.14）。
3. ⚠️ **一定要点页面上的大按钮，不要点下面列表里的 "Windows installer (64-bit)" 那些老链接**——那些是旧版本的补链接，容易装到 3.8 这种老版本。
4. 下载下来是 `python-3.13.x-amd64.exe`。

> 如果官网打不开或速度慢，可用国内镜像：华为云 <https://mirrors.huaweicloud.com/python/>、腾讯云 <https://mirrors.cloud.tencent.com/python/>。镜像内容和官网完全一致，只是下载快。

#### 第 2 步：运行安装程序（这一步最容易出错）

双击下载好的 `.exe`，**第一屏一定会弹出一个复选框**：

```
☐ Install launcher for all users     ← 不用勾，会要管理员权限，初学阶段没必要
☐ Add python.exe to PATH              ← ★★★ 必须勾！这是 90% 问题的根源
```

**`Add python.exe to PATH` 一定要勾上。** 勾了它，Windows 才知道去哪儿找 `python` 这个命令；不勾的话，你在命令行里敲 `python` 会得到「'python' 不是内部或外部命令」。

然后点 **"Install Now"**（推荐默认安装，省事且 PATH 已配好）。

如果你想自定义安装路径（比如 D 盘），点 **"Customize installation"**，务必保证第一屏最下面的 `Add python.exe to environment variables` 仍然是勾选状态。

#### 第 3 步：验证安装成功

按 `Win + R`，输入 `cmd` 回车（或用 Windows Terminal / PowerShell），在黑窗口里敲：

```bash
python --version
```

看到类似输出就是成功了：

```
Python 3.13.14
```

再敲两个命令确认：

```bash
# 确认命令来源正确：应该显示刚才安装的路径（在 C:\Users\你的用户名\AppData\Local\Programs\Python\... 下）
where python

# 直接进入交互式解释器，看到 >>> 提示符
python
```

在 `>>>` 里敲 `print("hello")` 回车，看到 `hello` 就敲 `exit()` 退出。

⚠️ **重要**：一定要用**新开的**命令行窗口测试。如果你是在安装 Python **之前**打开的旧窗口里测试，PATH 不会自动刷新，会误判成安装失败。

#### 第 4 步（可选但推荐）：安装一个包管理器和代码格式化工具

```bash
# 用 pip 安装一个第三方库，验证 pip 也能正常工作（以 requests 为例）
pip install requests

# 安装官方代码风格检查和格式化工具，本教材第 03 课会用到
pip install ruff
```

pip 是 Python 的「包管理器」，几乎所有第三方库都用它装。**如果哪天 `pip` 命令也找不到，试 `python -m pip install xxx`**，这样写能保证 pip 和当前解释器是同一个。

---

### 2.6 「'python' 不是内部或外部命令」的完整排查流程

这是初学阶段出现频率最高的问题。请严格按下面顺序排查，**每一步执行完立刻重开一个 cmd 窗口再测**。

#### 排查步骤 1：确认你改的是哪个 PATH

Windows 实际上有两套 PATH，两套都要看：

- **用户变量 PATH**：只影响你当前登录的这个用户
- **系统变量 PATH**：影响这台电脑的所有用户，需要管理员权限才能改

安装程序默认把 Python 加到「用户变量 PATH」，所以你在「环境变量」对话框的**上半部分**（用户变量）找 `Path`，双击编辑，往下找到 `Python313\` 开头的两项：

```
...;C:\Users\你的用户名\AppData\Local\Programs\Python\Python313\Scripts\
...;C:\Users\你的用户名\AppData\Local\Programs\Python\Python313\
```

⚠️ 一定要点**确认 → 确定**保存每一层对话框。很多人改完直接关窗口，等于没改。

#### 排查步骤 2：装完是不是忘了勾 Add to PATH

如果上面两项在用户 PATH 里根本找不到，说明安装时没勾。**解决办法：重新运行安装包 → 选 Modify → 勾上 `Add python.exe to environment variables` → 完成后重开窗口。**

#### 排查步骤 3：手动把路径加到 PATH

如果实在找不到安装目录，可以在文件资源管理器里搜 `python.exe`，把它的所在文件夹路径手动粘贴到 PATH 里。

#### 排查步骤 4：装了两个 Python，PATH 指向了错的那个

很常见：你以前装过 Anaconda 或 Microsoft Store 版 Python，现在又有官方版。敲 `where python` 会看到多个结果，**PATH 里靠前的那个生效**。解决办法：

- 把想用的那个路径移到 PATH 前面；
- 或者卸载多余的（`设置 → 应用 → 搜索 python → 卸载`）。

#### 排查步骤 5：名字不是 python，是 py

Windows 上还有一个官方启动器 `py.exe`。试试：

```bash
py --version
py hello.py
```

如果 `py` 能用而 `python` 不能用，说明只是 PATH 问题，功能本身没问题，你也可以一直用 `py`。

#### 排查步骤 6：只在这一台电脑的某个目录不生效

如果你在 `D:\test` 目录里 `python` 失效、但换个目录就好使，那多半是**当前目录里有个叫 `python.exe` 的坏文件或文件夹**，把命令"顶"掉了。删掉它，或换个目录。

#### 排查步骤 7：需要「每个项目独立环境」时

如果你将来同时做多个项目、学到 L22 阶段，应该用虚拟环境。到那时你会在项目目录里用：

```bash
# 激活后，命令行提示符前面会出现 (.venv)
.venv\Scripts\activate
```

⚠️ **但要注意一个常见的诡异现象**：如果你**没有勾 Add to PATH 就安装了 Anaconda**，或者在 `.bat`/`.ps1` 脚本里执行，激活虚拟环境后 `python` 可能指向错误的解释器。判断方法永远是敲 `where python` 看第一个结果是不是当前 `.venv\Scripts\python.exe`。

**一条命令快速定位**：

```bash
python -c "import sys; print(sys.executable)"
```

它会直接告诉你「当前这个 python 到底是谁」。

---

### 2.7 IDE 与编辑器推荐

先用「编辑器」，熟练后再上「IDE」——这是自学的正确顺序。

| 工具 | 类型 | 上手难度 | 适合谁 | 费用 |
| --- | --- | --- | --- | --- |
| **IDLE** | Python 自带轻量 IDE | ⭐ 最低 | 刚开始，完全不想折腾环境的人 | 免费自带 |
| **VS Code** | 轻量编辑器 + 插件 | ⭐⭐ | **本教材推荐给所有人** | 免费 |
| **PyCharm** | 全功能 IDE | ⭐⭐⭐ | 习惯「装好就能写」的人 | 社区版免费 |
| 记事本 / Notepad++ | 纯文本编辑器 | ⭐ | 临时改个配置 | 免费 |
| Jupyter Notebook | 交互式笔记本 | ⭐⭐ | 数据分析、教学 | 需安装 |
| 商业 IDE（PyCharm 专业版等） | — | — | 企业项目 | 付费 |

#### VS Code（推荐）

**为什么推荐**：免费、启动快、扩展生态无敌，社区活跃。

配置三步：

1. **装 Python**：<https://code.visualstudio.com/> 下载安装。
2. **装扩展**：打开 VS Code → 按 `Ctrl+Shift+X` 打开扩展面板 → 搜索 `Python` → 安装微软官方的 **Python** 扩展（作者是 Microsoft）→ 再装 **Pylance**（智能提示）。
3. **选解释器**：按 `Ctrl+Shift+P` → 输入 `Python: Select Interpreter` → 选你安装的 3.13/3.14 → 左下角会显示当前解释器版本。

常用快捷键：

| 快捷键 | 作用 |
| --- | --- |
| `Ctrl + ~` | 打开/关闭集成终端（在 VS Code 里直接敲命令） |
| `F5` | 运行当前文件 |
| `Ctrl + S` | 保存（**不保存不能运行**） |
| `Ctrl + /` | 单行注释 / 取消注释 |
| `Alt + ↓` | 移动当前行 |
| `Shift + Alt + ↓` | 复制当前行 |

⚠️ **新手最常踩的坑**：在 VS Code 里点「运行」按钮，终端只字不动。99% 是因为**文件还没保存**，或者**选错了 Python 解释器**。

#### PyCharm

- 下载 Community（社区）版：<https://www.jetbrains.com/pycharm/download/>，**免费且功能足够学习用**。
- 安装完直接 `File → New Project`，它会自动帮你创建虚拟环境（比 VS Code 少折腾）。
- 界面比 VS Code 重、吃内存，但「新建项目 → 写代码 → 点运行」是一站式体验。

#### IDLE

Windows 上安装 Python 时自带，`Win + R` 里输入 `idle` 就能打开。

- 优点：零配置，双击就有 `>>>` 和编辑窗口。
- 缺点：没有智能提示、没有代码格式化、界面很朴素、中文输入偶尔有问题。
- 建议：**只用它做前两天的「体验」，之后立刻换 VS Code。**

---

### 2.8 命令行运行 Python 的三种方式

命令行是必须掌握的技能——很多教程默认你已经会开终端。

#### 方式一：`python xxx.py` —— 运行脚本文件（最常用）

```bash
# 先 cd 到文件所在目录，再运行
cd E:/github/pythonCore/python-learning-system
python examples/00_hello_env_check.py

# 也可以直接给完整路径，不必先 cd（注意路径用引号包起来，因为路径里有空格）
python "E:/github/pythonCore/python-learning-system/examples/00_hello_env_check.py"
```

工作原理：Python 打开这个 `.py` 文件，**从第一行读到最后一行，逐行执行**。

⚠️ 路径写法：Windows 上路径分隔符是 `\`，但**在 Python 代码里必须写成 `/` 或用 `os.path`/`pathlib`**，写成 `"E:\github"` 会被当作转义字符 `\g` 处理而报错。在 cmd 里执行命令时，用 `/` 也可以正常识别。

#### 方式二：`python -m xxx` —— 以模块方式运行

```bash
# 运行标准库模块
python -m http.server 8000      # 启动一个本地静态文件服务器
python -m json.tool data.json   # 美化输出 JSON 文件
python -m pip install requests  # 用当前解释器的 pip 安装包
python -m venv .venv            # 创建虚拟环境
```

`-m` 的意思是「**m**odule，把后面的名字当成模块导入并运行」。

它和 `python xxx.py` 的区别：

| 差异点 | `python xxx.py` | `python -m xxx` |
| --- | --- | --- |
| 模块查找起点 | 就是你给的那个文件 | **当前工作目录**（`sys.path[0]` 是当前目录） |
| 支持标准库模块 | ❌ 标准库没对应的 .py 文件给你 | ✅ `http.server`、`pip`、`venv` 等 |
| 支持第三方库的命令 | ❌ 一般不行 | ✅ `python -m pytest`、`python -m flask` |
| 导入自己写的模块 | 常常导不到（路径问题） | ✅ 天然正确 |
| 典型场景 | 写业务脚本 | 跑框架、跑库的命令行工具 |

**结论**：**优先用 `python -m 方式`**。它更健壮，不容易因为「你在哪个目录、脚本在哪」而找不到模块。

#### 方式三：交互式解释器（REPL）

```bash
python
```

会出现三个尖括号提示符 `>>>`，你敲一行它立刻回一行：

```text
Python 3.13.14 (tags/v3.13.14:..., main, ...) [MSC v.1944 64 bit (AMD64)] on win32
Type "help", "copyright", "credits" or "license" for more information.
>>> 1 + 1
2
>>> name = "小明"
>>> print(f"你好，{name}")
你好，小明
>>> exit()
```

**交互式解释器什么时候用**：

- ✅ 快速试一小段代码，验证某个语法/函数怎么用
- ✅ 探索一个库：`import json; dir(json)` 看它有哪些能力
- ✅ 算数、测试正则表达式
- ❌ **不要在里面写超过 10 行的程序**——没有语法高亮、不能编辑历史行、写错了难撤回

**交互式的救命快捷键**：`Ctrl + C` 中断当前语句；`Ctrl + D` 或输入 `exit()` 退出。（3.13+ 的新版 REPL 支持多行编辑和直接粘贴代码块，体验好了很多。）

**有用的 REPL 命令**：

```pycon
>>> help(print)      # 查看某个对象的帮助文档
>>> dir(json)        # 列出模块里的所有名字
>>> json.__doc__     # 打印对象的文档字符串
>>> 3.14159.__round__(2)   # 3.14
```

#### 三种方式对比总结

| 场景 | 用哪种 | 命令示例 |
| --- | --- | --- |
| 学习、写完整程序 | 脚本文件 | `python lesson01.py` |
| 试代码、验证语法 | 交互式 | `python` → `>>>` |
| 跑第三方框架/工具 | 模块方式 | `python -m pytest` |
| 写错想改一行 | 交互式最方便 | 改完立即生效 |

---

### 2.9 如何运行代码文件与 Jupyter 入门

#### 2.9.1 运行代码文件的标准流程

```bash
# 1) 新建文件（用记事本也行，但建议用 VS Code）
notepad my_first.py

# 2) 写代码（注意扩展名必须是 .py，不是 .py.txt！）

# 3) 切到该文件所在目录
cd C:\Users\你的用户名\Documents

# 4) 运行
python my_first.py
```

⚠️ **三个必踩的坑**：

1. **文件被保存成了 `my_first.py.txt`**。因为 Windows 资源管理器默认隐藏扩展名，你在记事本里「另存为」时若没把「保存类型」选成「所有文件」，就会多出 `.txt`。解决办法：在资源管理器顶部勾上「查看 → 文件扩展名」。
2. **中文乱码**。用记事本另存为时，编码要选 **UTF-8** 而不是「ANSI」（GBK）。VS Code 默认就是 UTF-8，没这个问题。
3. **路径里有中文或空格**。命令行里一定要用英文双引号包住：`python "D:/我的 目录/a.py"`。

#### 2.9.2 Jupyter Notebook 入门

**Jupyter 是什么**：一种「网页式代码笔记本」，单元格（cell）一块一块写代码，每块写完按 `Shift + Enter` 立刻在下面显示结果——像文档又像交互式解释器。

**什么时候用**：

| 用 Jupyter | 不用 Jupyter |
| --- | --- |
| 数据分析、教学讲解、写技术文档 | 写正式项目、写可以交付的代码 |
| 需要图文并茂地展示结果 | 需要写多文件模块 |
| 边跑边看结果 | 需要单元测试和代码复用 |

**安装与启动**：

```bash
# 安装（下载 Jupyter 本体）
pip install jupyter

# 在你想要的目录下启动（会在该目录生成一个网页服务）
jupyter notebook

# 浏览器会自动打开 http://localhost:8888/tree
```

**如果 `jupyter` 命令找不到**：

```bash
python -m jupyter notebook    # 用模块方式启动，更可靠
```

**在 VS Code 里用 Jupyter**（更推荐，装个扩展就行）：装好 VS Code 的 Python 扩展后，新建文件选 `.ipynb` 后缀，直接在编辑器里点单元格运行，不需要单独开服务。

**Notebook 的两个「必须懂」的细节**：

1. 单元格**自上而下按顺序执行**。你改了上面的单元格，必须重新运行它，下面的结果才会更新。这是新手觉得「结果不对」的最常见原因。
2. 单元格有 **kernel（内核）** 概念。只有选对了 Python 内核才能运行。如果你重启了内核，之前定义的变量、import 的模块全部失效，需要从头运行一遍。

**一个最小 notebook 示例**（在第一个单元格粘贴，按 Shift+Enter）：

```python
# 单元格 1：普通代码，和普通 .py 文件一模一样
name = "Python 自学者"
print(f"欢迎，{name}！")
```

```python
# 单元格 2：Markdown 单元格（改成 Markdown 模式输入），用来写说明文字
# 这就是 Jupyter 比 .py 文件强的地方——代码和文字混排
# 下面这行会渲染成一级标题
# # 我的第一个 Notebook
```

⚠️ **不要用 Jupyter 学基础语法**。很多人学变量、循环时全程在 Notebook 里点，导致养成「写完就删」的习惯、代码组织能力始终为零。**本教材建议：L01~L26 全部用 `.py` 文件学，学到阶段七做项目时再用 Jupyter 做数据分析项目。**

---

## 💻 三、课堂演示代码

配套示例：`examples/00_hello_env_check.py`

**文件内容如下，可直接复制保存为 `examples/00_hello_env_check.py`：**

```python
"""环境自检脚本 —— 安装 Python 后第一个必须跑起来的程序。

用法（三种，任选其一都能看到同样的输出）：

    1) 直接运行脚本：  python examples/00_hello_env_check.py
    2) 以模块方式运行：python -m examples.00_hello_env_check
                       （需在父目录执行，且目录含 __init__.py）
    3) 交互式解释器：  python  →  然后输入下面这行：
        exec(open('examples/00_hello_env_check.py', encoding='utf-8').read())

本脚本不依赖任何第三方库，只用标准库，随时可以放心运行。

作者：Python 自学体系 · 阶段零
"""

import os
import platform
import sys


def report_python_version() -> None:
    """打印当前 Python 的版本号，并解释版本号每一段的含义。"""
    # sys.version_info 是一个「类元组」对象，major/minor/micro 分别对应 3.12.4 的 3 / 12 / 4
    info = sys.version_info
    print("=" * 60)
    print("【一】Python 版本信息")
    print("=" * 60)
    print(f"  完整版本串   : {sys.version}")
    print(f"  主版本号     : {info.major}")
    print(f"  次版本号     : {info.minor}   # 3.9 / 3.10 / 3.14 这一位变化最大")
    print(f"  修订号       : {info.micro}   # 补丁号，修 bug 用，日常无感")
    print(f"  简短版本号   : {platform.python_version()}")

    # releaselevel 可能是 'alpha'/'beta'/'candidate'/'final'，正式发布版是 'final'
    print(f"  发布阶段     : {info.releaselevel}")
    if info.releaselevel != "final":
        print("  ⚠️ 你用的不是正式版，遇到怪问题请先换正式版")

    # 本教材体系要求 3.10 及以上，低于该版本本课程的部分示例会跑不起来
    if info < (3, 10):
        print("  ❌ 版本过低：本学习体系要求 Python 3.10+，请到官网重新安装")
    else:
        print("  ✅ 版本满足本学习体系要求（3.10+）")


def report_interpreter_path() -> None:
    """打印解释器路径 —— 这是排查「装到哪儿了 / PATH 有没有配好」的关键信息。"""
    print()
    print("=" * 60)
    print("【二】解释器位置（PATH 排查的关键）")
    print("=" * 60)
    # sys.executable 是当前真正在跑的 python.exe 的绝对路径
    print(f"  解释器路径   : {sys.executable}")

    # dirname 去掉文件名，得到安装目录
    print(f"  安装目录     : {os.path.dirname(sys.executable)}")

    # sys.prefix 是「环境根目录」，虚拟环境就用它来区分自己
    print(f"  环境根目录   : {sys.prefix}")

    # base_prefix：系统 Python 的根目录。在虚拟环境里它和 prefix 不相等，
    # 所以可以用它判断「我现在是不是在虚拟环境里」
    print(f"  系统根目录   : {sys.base_prefix}")
    if sys.prefix != sys.base_prefix:
        print("  ✅ 当前处于虚拟环境（virtualenv / venv）中")
    else:
        print("  ℹ️  当前在「系统/全局」Python 环境中")

    # env 分隔符：Windows 是分号，Linux/macOS 是冒号
    print(f"  PATH 中的环境变量: {';' if os.name == 'nt' else ':'}  （这个是分隔符）")


def report_system() -> None:
    """打印操作系统信息，顺便演示 f-string 的格式化能力。"""
    print()
    print("=" * 60)
    print("【三】操作系统信息")
    print("=" * 60)
    print(f"  系统平台     : {platform.system()}       # Windows / Linux / Darwin(macOS)")
    print(f"  系统版本     : {platform.release()}")
    print(f"  机器架构     : {platform.machine()}      # AMD64 / arm64 / x86_64")
    print(f"  处理器       : {platform.processor()}")

    # win32_ver() 是平台专有方法：非 Windows 平台上它返回一组空值，不会报错
    win_version = platform.win32_ver()
    print(f"  Windows 版本 : {win_version[0]} {win_version[1]}  （非 Windows 平台返回空）")


def report_encoding() -> None:
    """检查默认编码 —— 中文环境下最常见的乱码根源。"""
    print()
    print("=" * 60)
    print("【四】文本编码检查")
    print("=" * 60)
    # UTF-8 是现在的事实标准；如果是 gbk，说明用的是老式 Windows 默认编码
    encoding = sys.getdefaultencoding()
    print(f"  默认编码     : {encoding}")
    if encoding.lower().replace("-", "") == "utf8":
        print("  ✅ 编码正常，中文注释与输出不会乱码")
    else:
        print("  ⚠️ 非 UTF-8，若出现中文乱码，请在文件头加 # -*- coding: utf-8 -*- 并用 UTF-8 保存")

    # 实际做一次「写入 → 读回」往返测试，这是最直观的验证方式
    test_file = "./_env_check_temp.txt"
    try:
        with open(test_file, "w", encoding="utf-8") as fp:
            fp.write("Python 环境自检：中文读写测试 ✅\n")
        with open(test_file, "r", encoding="utf-8") as fp:
            content = fp.read().strip()
        print(f"  读写往返测试 : {content}")
    except OSError as exc:
        print(f"  读写测试失败 : {exc}")
    finally:
        # 无论成功失败都要清理临时文件，不给用户目录留垃圾
        if os.path.exists(test_file):
            os.remove(test_file)
            print(f"  已清理临时文件: {test_file}")


def report_run_mode() -> None:
    """演示「脚本运行 / 模块运行 / 交互式运行」三种方式下代码看到的东西有什么不同。"""
    print()
    print("=" * 60)
    print("【五】当前运行方式")
    print("=" * 60)
    # __name__ 等于 "__main__" 说明是「作为脚本直接执行」的
    print(f"  __name__     : {__name__}")

    # 直接运行脚本时 __file__ 一定存在；在某些交互式环境里可能是 undefined
    file_var = globals().get("__file__", "<未定义，可能在交互式解释器中>")
    print(f"  __file__     : {file_var}")

    if __name__ == "__main__":
        print("  运行方式     : 以「主脚本」身份运行，main() 被执行")
    else:
        print("  运行方式     : 被其他模块 import 进来，main() 不会自动执行")


def first_demo() -> None:
    """一个最小的「有输入 → 有处理 → 有输出」程序，用来确认真的能跑代码。"""
    print()
    print("=" * 60)
    print("【六】试跑一个小程序：摄氏温度转华氏温度")
    print("=" * 60)
    # 华氏 = 摄氏 × 9/5 + 32；这里只用常量 9、5、32 没问题，属于纯算术公式
    for celsius in (0, 25.5, 37, 100):
        fahrenheit = celsius * 9 / 5 + 32
        # :6.2f 表示总宽度 6 位、小数点后 2 位，不足用空格补齐
        print(f"  {celsius:>6.2f} °C  =  {fahrenheit:>6.2f} °F")

    # input() 从标准输入读一行并去掉换行符；这里给默认值，方便脚本非交互运行时不卡住
    raw = input("  请输入一个摄氏温度（直接回车用 20）：").strip()
    try:
        user_celsius = float(raw) if raw else 20.0
    except ValueError:
        # ValueError 表示「字符串转 float 失败」，初学者最常见的输入错误
        print("  ⚠️ 输入的不是数字，已自动改用 20 进行计算")
        user_celsius = 20.0

    user_fahrenheit = user_celsius * 9 / 5 + 32
    print(f"  你的答案是：{user_celsius} °C = {user_fahrenheit:.2f} °F")


def main() -> None:
    """程序总入口：按顺序调用各个检查环节。"""
    print("🎉 恭喜！你的 Python 环境已经可以正常使用了。\n")
    report_python_version()
    report_interpreter_path()
    report_system()
    report_encoding()
    report_run_mode()
    first_demo()
    print("\n✅ 自检结束。如果以上信息都对，说明环境配置完全正常，可以开始 L01 了。")


# 标准入口约定：直接运行本文件时执行 main()，被 import 时不执行。
# 好处是别人 import 本模块做环境检测时，不会莫名其妙弹出一大堆输出。
if __name__ == "__main__":
    main()
```

**运行方式与预期输出**：

```bash
cd E:/github/pythonCore/python-learning-system
python examples/00_hello_env_check.py
```

预期你会看到六段输出：版本信息、解释器位置、系统信息、编码检查、运行方式、试算温度。其中**「解释器路径」那一段请截图留档**——以后你怀疑 PATH 有问题时，第一件事就是打开这个脚本看路径有没有变。

---

## ⚠️ 四、常见错误清单

| 错误现象 | 原因 | 正确写法 |
| --- | --- | --- |
| `python : 无法将"python"项识别为 cmdlet...` / `'python' 不是内部或外部命令` | 安装时没勾 `Add python.exe to PATH`，或改完 PATH 没重开窗口 | 重装并勾选 PATH；或手动把 `C:\Users\你\AppData\Local\Programs\Python\Python313\` 加进用户 PATH；**改完必须重开 cmd** |
| `python --version` 正常，`py --version` 不行（或相反） | Windows 上 `python` 和 `py` 是两个独立入口 | 哪个能用用哪个；官方安装包带 `py.exe`，完全卸载重装可恢复 |
| `SyntaxError: invalid character '，'` 或 `SyntaxError: invalid escape sequence` | 文件存成了 GBK/ANSI 而不是 UTF-8 | 用 VS Code 保存（默认 UTF-8）；记事本另存为时选 UTF-8 |
| 输出中文变成一堆问号或黑色方块（乱码） | 终端编码与文件编码不一致 | Windows 终端敲 `chcp 65001` 切 UTF-8；或改用 VS Code 内置终端 |
| `python hello.py` 提示 `can't open file` | 当前目录不对，或路径里有空格没加引号 | 先 `cd` 到文件目录；路径用英文双引号包起来 |
| 明明写了 `.py`，运行却「什么也没发生」/ 打开的是记事本 | 文件实际叫 `hello.py.txt` | 资源管理器勾上「文件扩展名」，重命名为 `hello.py` |
| `ModuleNotFoundError: No module named 'requests'` | 库没装，或装到了别的 Python 环境 | `python -m pip install requests`（用 `-m` 保证装到同一个解释器）；跑 `where python` 确认环境 |
| `pip install` 报 `不是内部或外部命令` 但 python 能用 | pip 目录没进 PATH | 改用 `python -m pip install 包名` |
| 装了 Anaconda 后 `python` 变成了 `conda` 自带的那个 | Anaconda 把自己的解释器插到了 PATH 前面 | `where python` 看顺序；调整 PATH 顺序；或直接用 `conda` 管理的环境 |
| `UnicodeEncodeError: 'gbk' codec can't encode character` | 老版本 Python 在中文 Windows 上按 GBK 输出 | `chcp 65001`；或 Python 3.7+ 已大幅改善，务必确认版本 ≥3.10 |
| `jupyter: 无法将"jupyter"项识别...` | jupyter 的 Scripts 目录没进 PATH | `python -m jupyter notebook` |
| 安装后测出来还是「找不到命令」 | 用的是**安装之前**就打开的旧命令行窗口 | 关闭所有 cmd/PowerShell/VS Code 窗口，重新打开再测 |
| VS Code 点运行没反应 | 文件未保存，或解释器选错 | `Ctrl+S` 保存；`Ctrl+Shift+P` → `Python: Select Interpreter` 重新选 |

---

## 🧠 五、知识点速查表

### 安装与验证

```bash
python --version          # 查版本，最基本的验证命令
where python              # Windows：看有哪几个 python、哪个生效
python -c "import sys; print(sys.executable)"   # 当前 python 到底是谁
py --version              # 备选入口
pip --version             # 包管理器版本
python -m pip --version   # 更可靠的 pip 版本查询
```

### 运行代码的三种方式

```bash
python lesson01.py        # ① 运行脚本文件
python -m http.server     # ② 以模块方式运行（-m = module）
python                    # ③ 进入交互式解释器（>>> 提示符，exit() 退出）
```

| 方式 | 提示符/表现 | 适用场景 | 别用它做什么 |
| --- | --- | --- | --- |
| `python x.py` | 从上到下执行完就退出 | 写完整程序 | 跑第三方框架 |
| `python -m xxx` | 同上 | 跑框架、跑标准库模块 | 需要模块恰好在当前目录时 |
| `python` | `>>>` 交互 | 试代码、查文档、算数 | 写超过 10 行的程序 |

### 版本号怎么读

```
3 . 13 . 14
│   │    └── 修订号：只修 bug
│   └─────── 次版本号：每年 10 月 +1，新语法在这一位
└─────────── 主版本号：Python 2 → Python 3，语法不兼容
```

### 关键系统模块速查

| 模块 | 关键对象 | 用途 |
| --- | --- | --- |
| `sys` | `sys.version` / `sys.version_info` / `sys.executable` / `sys.argv` / `sys.path` | 版本、解释器路径、命令行参数、模块搜索路径 |
| `os` | `os.getcwd()` / `os.path.join()` / `os.environ` / `os.name` | 当前目录、拼路径、读环境变量、判断系统 |
| `platform` | `platform.system()` / `platform.python_version()` / `platform.machine()` | 操作系统、Python 版本、CPU 架构 |
| `pathlib` | `Path("./a").exists()` / `.resolve()` / `.with_suffix()` | **现代推荐**的文件路径处理方式 |

### 命令行路径写法

| 场景 | 正确 | 错误 |
| --- | --- | --- |
| Python 代码里写 Windows 路径 | `p = "E:/github/pythonCore"` | `p = "E:\github\pythonCore"`（`\g` 被当转义） |
| 命令行传路径 | `python "E:/my 目录/a.py"` | `python E:/my 目录/a.py`（有空格会断） |
| 换行符 | 路径拼接用 `pathlib.Path` / `os.path.join()` | 手工拼 `/` 或 `\` |

---

## 📝 六、本课小结

- Python 是高级、解释型、动态类型、跨平台的通用语言，核心优势是**语法简洁、生态庞大、入门反馈快**。
- 它强在数据处理、自动化、AI、后端、测试运维；弱在手机原生 App、高并发 CPU 密集服务、游戏引擎。**"Python 慢"是误传**——瓶颈在纯 Python 循环，交给 numpy 这类底层库即可。
- 与 JS / Java / Go 的本质差别是**静态 vs 动态类型**、**解释 vs 编译**。从静态语言转过来只需适应「缩进即语法」和「无分号无大括号」。
- 版本号 `3.13.14` 读作「主 3 · 次 13 · 修订 14」，每年 10 月发布一个次版本，**装 3.13 或 3.14 即可，不必追最新**。本教材要求 3.10+。
- Windows 安装时 **`Add python.exe to PATH` 是必勾项**，这是「找不到 python」类问题的根源；改完 PATH **必须重开命令行窗口**。
- `where python` 和 `sys.executable` 是你定位「装到哪儿了」的终极武器。
- 三种运行方式：`python x.py`（跑脚本）、`python -m x`（跑模块/框架，**优先选它**）、`python`（交互式试代码）。
- Jupyter 适合数据分析和写文档，**不适合学基础语法**（养成"写完就删"的坏习惯）。

> **一句话总结**：装环境只需要成功一次，把「会用命令行找到并运行自己的代码」练成本能，你就真正开始学编程了。

---

## ✍️ 七、课后作业

### 基础题（必做）

**第 1 题（20 分）· 环境自检报告**

- **要求**：运行 `examples/00_hello_env_check.py`，把全部输出**截图保存**。然后按下面的格式填写你的环境报告，保存为 `我的环境报告.md`：

  ```markdown
  # 我的 Python 环境报告
  - Python 版本：
  - 解释器完整路径：
  - 操作系统与版本：
  - 默认文本编码：
  - 我用的编辑器/IDE：
  - 环境是否正常（✅/❌）：
  ```

- **验收标准**：信息与脚本输出一致；路径那一行是完整的 `C:\...` 开头（不能是空的）。

**第 2 题（20 分）· 版本号解读**

- **输入**：命令行执行 `python -c "import sys; print(sys.version_info)"`，会得到形如 `<sys.version_info(major=3, minor=13, micro=14, ... )>` 的输出。
- **输出**：一段文字说明 `major=3`、`minor=13`、`micro=14` 分别代表什么，以及「为什么本教材要求 3.10 以上」。
- **要求**：用你自己的话写，不少于 100 字。

**第 3 题（20 分）· 三种运行方式对比**

- **要求**：新建 `hw.py`，内容为 `print("你好，Python！")`。
  1. 用 `python hw.py` 运行一次，把输出记下来；
  2. 用 `python` 进入交互式解释器，在 `>>>` 里手动输入 `print("你好，Python！")`，记录输出；
  3. 试着从交互式解释器里执行整个文件：`exec(open('hw.py', encoding='utf-8').read())`，记录输出。
- **输出**：回答问题——三种方式的输出有什么相同？交互式方式和脚本方式最大的区别是什么（提示：想想「有没有 `__file__`、执行完会不会自动退出」）。

**第 4 题（20 分）· PATH 排查演练**

- **要求**：执行以下命令，把每条命令的真实输出**原样抄录**（不要凭想象写）：
  1. `where python`
  2. `python -c "import sys; print(sys.executable)"`
  3. `echo %PATH%`（cmd 里）或 `$env:PATH`（PowerShell 里），在结果中找到包含 `Python` 的那一段并用文字指出它在哪。
- **输出**：一段说明——回答「怎么判断当前命令行里的 python 就是我安装的那一个？」

**第 5 题（20 分）· 故意制造并修复一个错误**

- **要求**：新建 `bug_demo.py`，故意在里面写 3 个会报错的代码，**每个错误都要自己截图记录报错信息，然后修复它**。建议故意犯这几种错：
  1. 用了未定义的变量名；
  2. 把 `print` 写成了 `pirnt`；
  3. 字符串忘了加引号。
- **输出**：`bug_demo.py` 最终版（3 处错误都已改正） + 3 张报错截图 + 一句话解释每个错误的成因。
- **验收标准**：**必须是你真实产生的报错**，不是从网上抄的报错文字。

### 进阶题（选做，加分）

**第 6 题（25 分）· 不用 pip 也能装包吗**

- **要求**：查阅 <https://docs.python.org/3/using/cmdline.html>，找出至少 2 种 Python 自带的、用来「下载并安装第三方包」的方式（一种要求已装第三方工具，一种不要求）。然后在你自己电脑上实际执行其中一种，把命令和输出记录下来。
- **输出**：一份说明文档，含命令、输出、以及「我实际用的是哪种、体验如何」。
- **提示**：一种叫 `pip`，另一种可能需要你从源码方式处理；想想看 `ensurepip` 是什么。

**第 7 题（25 分）· 编辑器对比实操**

- **要求**：在 **VS Code** 和 **PyCharm 社区版** 中各装一次、跑一个 `hello.py`（如果你只想装一个，就只做 VS Code 并说明理由）。
- **输出**：一份 100 字以内的对比，说明：哪个装起来更麻烦、哪个启动更快、哪个补全更好用、你觉得自学阶段该选哪个。

### 挑战题（选做，加分）

**第 8 题（30 分）· 写一个环境体检报告生成器**

- **要求**：新建 `env_report.py`，实现一个比示例更完善的体检程序，要求：
  1. 输出一份结构化报告（你自行设计格式，可用表格或分节）；
  2. 至少检查以下 8 项：Python 版本、是否 ≥3.10、解释器路径、是否在虚拟环境、操作系统、架构、默认编码、`pip` 是否可用；
  3. 每项都给出 ✅ / ⚠️ / ❌ 三态判定，并给出一句「如果这项不合格，你应该怎么办」的提示；
  4. 全部检查结束后，给出**总评**：完全正常 / 基本可用 / 需要修复；
  5. 把报告同时**写入一个 `env_report.txt` 文件**（用 `pathlib.Path` 或 `open`，编码 `utf-8`），并打印保存路径。
- **输出**：`env_report.py` 的完整代码 + 它的运行结果截图 + 生成的文件内容。
- **验收标准**：代码只依赖标准库；每行（或每块）有中文注释说明意图；报告内容真实反映你机器的情况。

<details>
<summary>✅ 挑战题参考思路与关键代码</summary>

**关键点 1：把检查项抽象成「函数 + 判定」，避免写成一大坨重复的 print。**

```python
def check(title: str, passed: bool | None, advice: str) -> bool:
    """打印一条体检结果：passed 为 True/False/None(不适用)。

    返回该条是否通过，供最后统计总分。
    """
    if passed is None:
        icon = "➖"
    elif passed:
        icon = "✅"
    else:
        icon = "❌"
    print(f"{icon} {title}")
    if passed is False:
        # 只在不合格时才给建议，避免输出太长
        print(f"    💡 建议：{advice}")
    return bool(passed)


def check_python_version() -> bool:
    """检查 Python 版本是否 ≥ 3.10，返回是否合格。"""
    major, minor = sys.version_info[:2]          # 解包元组取前两项
    ok = (major, minor) >= (3, 10)
    print(f"当前版本：{major}.{minor}")
    return check(
        "Python 版本 ≥ 3.10",
        ok,
        "请到 https://www.python.org/downloads/windows/ 下载 3.13/3.14 重装，并务必勾选 Add python.exe to PATH",
    )
```

**关键点 2：判断 pip 是否可用，用 `importlib.util.find_spec`（比 try/except 简洁）。**

```python
import importlib.util

def check_pip() -> bool:
    """检查 pip 模块是否存在。"""
    found = importlib.util.find_spec("pip") is not None
    return check(
        "pip 包管理器可用",
        found,
        "在 Python 官网安装包上选 Modify，或执行 python -m ensurepip --upgrade",
    )
```

**关键点 3：把报告写进文件，用 `pathlib` 拼路径，且显式指定 UTF-8。**

```python
from pathlib import Path

def save_report(lines: list[str]) -> Path:
    """把报告行写入 ./env_report.txt 并返回路径。

    用 pathlib 而不是 os.path.join，是现代 Python 推荐写法。
    """
    target = Path(".") / "env_report.txt"      # ./ 下的临时文件，不污染用户目录
    # writelines 一次写多行；newline="\n" 保证 Windows 下也用 \n 换行
    with target.open("w", encoding="utf-8", newline="\n") as fp:
        fp.writelines(f"{line}\n" for line in lines)
    return target
```

**完整代码骨架**：

```python
"""环境体检报告生成器 —— 挑战题参考实现。"""

import importlib.util
import os
import platform
import subprocess
import sys
from pathlib import Path


def check(title, passed, advice):
    icon = "➖" if passed is None else ("✅" if passed else "❌")
    print(f"{icon} {title}")
    if passed is False:
        print(f"    💡 建议：{advice}")
    return bool(passed)


def check_version():
    major, minor = sys.version_info[:2]
    print(f"    当前版本：{major}.{minor}")
    return check("Python 版本 ≥ 3.10", (major, minor) >= (3, 10),
                 "到官网重装 3.13/3.14 并勾选 Add python.exe to PATH")


def check_executable():
    path = sys.executable
    print(f"    解释器路径：{path}")
    return check("解释器路径可确定", bool(path), "请重新运行官方安装包并勾选 Add to PATH")


def check_virtualenv():
    in_venv = sys.prefix != sys.base_prefix
    print(f"    prefix={sys.prefix}\n    base_prefix={sys.base_prefix}")
    return check("当前不在虚拟环境中（初学阶段正常）", not in_venv,
                 "不是错误：学到 L22 会主动使用虚拟环境")


def check_os():
    print(f"    {platform.system()} {platform.release()} / {platform.machine()}")
    return check("操作系统可识别", bool(platform.system()), "这几乎不会失败，若失败说明环境异常")


def check_encoding():
    enc = sys.getdefaultencoding()
    print(f"    默认编码：{enc}")
    return check("默认编码为 UTF-8", enc.lower().replace("-", "") == "utf8",
                 "用 UTF-8 重新保存文件；Windows 终端可执行 chcp 65001")


def check_stdlib_write():
    """实测：在当前目录写一个临时文件再删掉，确认文件读写权限正常。"""
    probe = Path(".") / "_probe_tmp.txt"
    try:
        probe.write_text("测试\n", encoding="utf-8")
        ok = probe.read_text(encoding="utf-8").strip() == "测试"
    except OSError:
        ok = False
    finally:
        if probe.exists():
            probe.unlink()
    return check("当前目录可读写文件", ok, "请把工作目录换成你有写权限的位置（如文档目录）")


def check_pip():
    found = importlib.util.find_spec("pip") is not None
    return check("pip 可用", found, "执行 python -m ensurepip --upgrade")


def check_pip_version():
    """调用 pip --version，用 subprocess 拿输出；失败返回 None（视为不适用）。"""
    try:
        # capture_output 捕获输出，text=True 让结果是 str，check=False 表示不因非零退出而抛异常
        result = subprocess.run(
            [sys.executable, "-m", "pip", "--version"],
            capture_output=True, text=True, check=False, timeout=30,
        )
        ok = result.returncode == 0
        if ok:
            print(f"    {result.stdout.strip()}")
    except (OSError, subprocess.SubprocessError):
        ok = False
    return check("pip 可正常执行", ok, "尝试 python -m pip install --upgrade pip")


def main():
    print("=" * 64)
    print("Python 环境体检报告")
    print("=" * 64)
    print(f"生成时间：{platform.node()} 上的当前会话\n")

    checks = [
        ("版本", check_version()),
        ("解释器", check_executable()),
        ("虚拟环境", check_virtualenv()),
        ("系统", check_os()),
        ("编码", check_encoding()),
        ("目录权限", check_stdlib_write()),
        ("pip 模块", check_pip()),
        ("pip 执行", check_pip_version()),
    ]
    # count 用布尔值求和：True 算 1，False 算 0
    passed = sum(1 for _, ok in checks if ok)
    total = len(checks)

    print()
    if passed == total:
        verdict = "🎉 完全正常：环境配置没有问题，可以开始学习。"
    elif passed >= total - 2:
        verdict = "⚠️ 基本可用：个别项目不合格，按上面建议修复后再深入学习。"
    else:
        verdict = "❌ 需要修复：多项不合格，请对照建议逐项处理或重装 Python。"

    print(f"体检结论：通过 {passed}/{total} 项")
    print(verdict)

    report_lines = [
        "Python 环境体检报告",
        f"版本：{sys.version.split()[0]}",
        f"解释器：{sys.executable}",
        f"系统：{platform.system()} {platform.release()} ({platform.machine()})",
        f"默认编码：{sys.getdefaultencoding()}",
        f"结论：通过 {passed}/{total} 项 —— {verdict}",
    ]
    target = save_report(report_lines)
    print(f"\n📄 报告已保存到：{target.absolute()}")


def save_report(lines):
    """把报告写入 ./env_report.txt 并返回 Path。"""
    target = Path(".") / "env_report.txt"
    with target.open("w", encoding="utf-8", newline="\n") as fp:
        fp.writelines(f"{line}\n" for line in lines)
    return target


if __name__ == "__main__":
    main()
```

**评分要点**：条目 ≥8 项；每项有三态图标和建议；三态判定逻辑正确（尤其「不是虚拟环境」应判为通过/提示而非错误）；用 `pathlib` 写文件且指定 `utf-8`；只用标准库；全部有中文注释。

</details>

---

## ✅ 八、作业参考答案

> **说明**：本篇作业以「动手实操 + 观察记录」为主（第 1~5 题），答案因机器而异，
> 因此下面给出的是**每题的评判标准与参考样例**，不是唯一答案。
> 第 8 题挑战题有完整参考代码。

| 题号 | 答案要点 | 自评标准 |
| --- | --- | --- |
| 1 | 环境报告照抄脚本输出即可 | 解释器路径必须是完整绝对路径且以 `C://`（或 `D://`）开头 |
| 2 | 版本号解读：major 是主版本（2→3 语法不兼容）、minor 是次版本（每年 10 月 +1，新增语法在这一位）、micro 是修订号（只修 bug）。要求 3.10+ 是因为要用 `match/case` 并享受更好的报错提示 | 是否提到「每年 10 月发布」和「3.10 的 match/case」 |
| 3 | 三种方式输出**文字相同**（都是打印那句话）。区别：脚本方式执行完自动退出；交互式方式会停在 `>>>` 等待下一条输入；`exec(open(...).read())` 能让脚本在交互式环境里跑完并**不会**像 `python x.py` 那样退出 | 是否能答出「会不会自动退出」和「有没有 `__file__`」 |
| 4 | 判断依据是**结果是否指向你安装的路径**：`where python` 第一个结果即生效的解释器；`sys.executable` 打印的是**当前正在运行的那个**，两者应一致 | 是否发现两条命令输出的是同一个路径 |
| 5 | 5 个报错的根因：`NameError`=变量名拼错/未定义；`SyntaxError`=忘了引号导致解析失败；把 `print` 写成 `pirnt` 报的是 `NameError` 而**不是**拼写错误提示 | 是否 3 处都真实截图；是否说明「pirnt 报的是 NameError」 |

**基础题第 5 题参考样例（修复后代码）**：

```python
"""bug_demo.py —— 三处错误的修复版。"""


def demo_name_error():
    # ❌ 错误：print 拼成了 pirnt，报 NameError: name 'pirnt' is not defined
    # ✅ 正确：
    pirnt = "Hello"
    print(pirnt)
    # 说明：Python 不会提示「你是不是想写 print」，
    # 而是报 NameError（名字不存在）。这是初学者最常见的报错之一。


def demo_missing_quotes():
    # ❌ 错误：Hello 没加引号，被当成变量名，报 NameError
    # ✅ 正确：
    print("Hello")


def demo_undefined_var():
    # ❌ 错误：total_price 还没定义就用
    # ✅ 正确：
    total_price = 99
    print(f"总价：{total_price}")


if __name__ == "__main__":
    demo_name_error()
    demo_missing_quotes()
    demo_undefined_var()
```

**基础题第 1 题参考答案要点（`我的环境报告.md` 样例）**：

```markdown
# 我的 Python 环境报告
- Python 版本：3.13.14
- 解释器完整路径：C://Users//张三//AppData//Local//Programs//Python//Python313//python.exe
- 操作系统与版本：Windows 11 10.0.26200
- 默认文本编码：utf-8
- 我用的编辑器/IDE：VS Code + Python 扩展 + Pylance
- 环境是否正常：✅
```

---

## 🔗 九、延伸阅读与下一课预告

### 官方资源（最权威，优先级最高）

| 资源 | 地址 | 用途 |
| --- | --- | --- |
| Python 官方网站 | <https://www.python.org> | 下载、版本信息、新闻 |
| 官方教程 | <https://docs.python.org/3/tutorial/> | **最重要的一份免费教材**，读完一遍你就入门了 |
| 官方文档 How to use | <https://docs.python.org/3/using/index.html> | 命令行、解释器用法 |
| 最新版本特性 | <https://docs.python.org/3/whatsnew/index.html> | 查某个特性是哪个版本加的 |
| PEP 索引 | <https://peps.python.org/> | 想知道「为什么这么设计」就来这里 |
| PyPI（包仓库） | <https://pypi.org> | 搜第三方库、看它支持哪些 Python 版本 |

### 推荐练习方向（本周内完成）

1. **把命令行练成本能**：这周每次写代码，都用命令行敲 `python xxx.py` 运行，不要只点 IDE 的运行按钮。
2. **刻意制造 20 个报错**：把每种常见报错都亲手犯一遍、看懂信息、修好。**报错信息是你最好的老师。**
3. **装好 VS Code + Python 扩展 + Pylance**，把本教材目录作为工作区打开。
4. **完整读一遍官方 tutorial 的第 1~3 章**，对照本教材看有没有遗漏。

### 下一课预告

> **阶段零 · 学习指南（2/3）：《学习方法与 12 周学习计划》**
>
> 环境只是起点，接下来真正决定你能学成什么样的是**方法**。下一篇会讲：
> - 刻意练习、看写读结合、费曼技巧这三种真正有效的学习方式
> - 每天/每周该投入多少时间，12 周分四阶段的完整计划表
> - 怎么做笔记（obsidian / typora 实操）
> - 怎么用好搜索引擎和官方文档
> - **怎么读 Traceback 报错信息（从下往上看）**
> - 常见学习误区与刷题网站推荐
>
> 读完下一篇，你会有一个可以照着执行的 12 周作战地图，而不是「学着学着就凉了」。
