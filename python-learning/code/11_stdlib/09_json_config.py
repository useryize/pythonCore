"""
================================================================================
 09_json_config.py  ——  配置管理：json + configparser + 环境变量 + 分层合并
================================================================================

【演示的语法点】
 1. json 的配置用途：嵌套 dict 读写、ensure_ascii、indent、default 钩子
 2. configparser：ConfigParser / RawConfigParser / SafeConfigParser
 3. ini 文件的 section 与 option 结构，DEFAULT 特殊 section 的继承语义
 4. configparser 的取值陷阱：getint/getfloat/getboolean 与 fallback
 5. ★ 环境变量：os.environ 读取、类型转换、变量名规范
 6. 命令行参数：argparse 的 add_argument / type / default / dest / action
 7. ★★ 完整配置分层实现（核心）：
       默认值 → 配置文件 → 环境变量 → 命令行参数，后者覆盖前者
 8. 分层的三个设计要点：值如何"逐层穿透"、类型在何处转换、缺失如何降级
 9. 配置项的来源追踪（provenance），便于排查"这个值到底哪来的"
10. 深合并 vs 浅合并的差异及实现

【预期输出摘要】
 - "json" 小节：中文配置项读写，ensure_ascii=False 与 indent 的效果
 - "configparser" 小节：DEFAULT 继承、getint 报错回退 fallback
 - "环境变量" 小节：字符串到 bool/int/路径类型的转换函数
 - "分层" 小节：先写入一份故意冲突的配置文件，演示四层依次覆盖，
   最后打印每一层覆盖后的值变化表与来源标记
================================================================================

"""

import argparse
import json
import os
import shutil
import sys
import tempfile
from configparser import ConfigParser
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# 工作目录：所有演示产生的配置文件都写在这里，绝不污染用户真实配置
WORK_DIR = Path(__file__).parent / "_tmp_config"


# ===== 语法解析 =====
# 【1】配置体系为什么要"分层"
#   真实项目里，配置值可能来自四个地方，且优先级不同：
#     默认值     —— 代码里的兜底，保证最差情况也能跑
#     配置文件   —— 开发者/运维写的 settings.ini 或 settings.json
#     环境变量   —— 容器部署时注入，优先级高于文件
#     命令行参数 —— 临时覆盖，最高优先级
#   覆盖方向：后面的层【只覆盖它明确指定的键】，未指定的键保留下层结果。
#   这就是"逐层合并"（merge），不是"取其一"。
#
# 【2】本节要实现的合并函数签名思路
#   deep_merge(base, override) -> dict
#     对 base 的每个键：
#       若 override 中没有        → 保留 base 值
#       若两者都是 dict           → 递归合并（深合并）
#       否则                      → 用 override 的值覆盖
#   为什么必须深合并：配置文件常只写 {"db": {"host": "x"}}，
#   若浅合并会丢掉 defaults 里的 db.port / db.user 等兄弟键。
def deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    """深合并两个配置字典：override 覆盖 base，同为 dict 时递归合并。"""
    result = dict(base)                    # 先浅拷贝，避免直接改动调用方的字典
    for key, new_value in override.items():
        old_value = result.get(key)
        # 只有【两边都是 dict】才递归；否则一律直接覆盖
        if isinstance(old_value, dict) and isinstance(new_value, dict):
            result[key] = deep_merge(old_value, new_value)
        else:
            result[key] = new_value
    return result


# ===== 语法解析 =====
# 【3】配置值的类型转换
#   设计意图：配置文件读出来永远是字符串（ini 是文本，env 是字符串，
#             命令行也可能是 "8080"），但程序需要 int / bool / Path。
#   所以必须在"进入应用逻辑之前"统一转换一次，
#   否则会出现 "8080" + 1 == "80801" 这类诡异 bug。
def to_bool(value: Any) -> bool:
    """把各种形态转成 bool。关键：字符串 'False' 在 Python 中是【真值】！"""
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        # 必须显式列举假值，因为 bool("False") 是 True
        return value.strip().lower() in ("1", "true", "yes", "on", "y", "t")
    return bool(value)


def to_int(value: Any, default: Optional[int] = None) -> Optional[int]:
    """转 int，失败时返回 default 而不是抛异常（配置容错的关键）。"""
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


# ===== 语法解析 =====
# 【4】json 作为配置文件
#   与 04_json_module 的区别：这里关注的是【配置组织】而非序列化细节。
#   配置 JSON 的特点：嵌套 dict、无需 tuple、全是字符串/数字、要求可读。
def demo_json_config() -> None:
    print("=" * 74)
    print("【1】json 作为配置文件")
    print("=" * 74)

    WORK_DIR.mkdir(exist_ok=True)
    cfg_file = WORK_DIR / "settings.json"

    # 配置内容：模拟一个真实的服务配置
    config: Dict[str, Any] = {
        "app_name": "学习平台",
        "debug": False,
        "server": {
            "host": "127.0.0.1",
            "port": 8000,
            "workers": 4,
            "allowed_origins": ["http://localhost", "http://127.0.0.1"],
        },
        "database": {
            "engine": "postgresql",
            "options": {"pool_size": 5, "echo": False},
        },
        # 路径建议存字符串，运行时再转 Path（JSON 没有路径类型）
        "log_dir": "logs",
        # 需要自定义类型的例子：这里用元组模拟，dump 时会变成 list
        "maintenance_window": ("02:00", "03:00"),
    }

    # 写配置：ensure_ascii=False 让中文可读；indent=2 便于人工修改和 git diff
    with open(cfg_file, "w", encoding="utf-8") as f:
        # default= 参数可以在 dump 时转换无法序列化的对象
        json.dump(config, f, ensure_ascii=False, indent=2, default=list)
    print(f"已写入: {cfg_file}")
    print("  ensure_ascii=False → 中文原样写入（否则变成 \\uXXXX）")
    print("  indent=2 → 缩进美化，代价是文件变大，但人工可读、diff 友好")
    print(f"  default=list → 遇到 tuple 时自动转 list，避免 TypeError")

    # 读回并验证
    with open(cfg_file, "r", encoding="utf-8") as f:
        loaded = json.load(f)
    print(f"\n读回校验:")
    print(f"  app_name = {loaded['app_name']!r}（类型 {type(loaded['app_name']).__name__}）")
    print(f"  server.port = {loaded['server']['port']}（类型 "
          f"{type(loaded['server']['port']).__name__}） ← JSON 数字自动是 int")
    print(f"  三层嵌套 options.pool_size = {loaded['database']['options']['pool_size']}")
    print(f"  tuple 被 dump 成了 {loaded['maintenance_window']} "
          f"（类型 {type(loaded['maintenance_window']).__name__}）← JSON 无 tuple")

    # 配置读取的健壮性：文件不存在/损坏时如何处理
    print("\n健壮性处理:")
    try:
        with open(WORK_DIR / "not_exist.json", encoding="utf-8") as f:
            json.load(f)
    except FileNotFoundError:
        print(f"  文件不存在 → 捕获 FileNotFoundError，回退到默认值")

    bad = WORK_DIR / "broken.json"
    bad.write_text("{这不是合法的 JSON", encoding="utf-8")
    try:
        with open(bad, encoding="utf-8") as f:
            json.load(f)
    except json.JSONDecodeError as e:
        # JSONDecodeError 继承 ValueError，e.msg/.lineno/.colno 可精确定位
        print(f"  内容损坏 → JSONDecodeError: {e.msg}（行 {e.lineno} 列 {e.colno}）")
    bad.unlink()


# ===== 语法解析 =====
# 【5】configparser 读 ini 文件
#   ini 的结构语法：
#     [section]        ← 段名，用方括号
#     key = value      ← 选项，等号或冒号分隔
#     ; comment        ← 分号是注释
#     # comment        ← 井号也是注释
#
#   【关键特性】DEFAULT 特殊段：
#     DEFAULT 里的选项会被【所有 section 继承】，且用 parser["DEFAULT"] 读取。
#     这是 ini 做"全局默认值"的官方机制，但也是坑：
#     section.items() 会【连带返回 DEFAULT 的项】，导致遍历时出现意料外的键。
class AppConfig:
    """用 configparser 封装 ini 配置的读取，演示类型安全的取值方式。"""

    def __init__(self, path: Path) -> None:
        self.path = path
        # ConfigParser 默认会把 key 转小写（optionxform），
        # 若要保留大小写需 self.parser.optionxform = str
        # interpolation=None 关闭 %(name)s 插值，
        # 代价：值里的 % 号（如 "100%"）不再报错，但插值语法也失效
        self.parser = ConfigParser(
            defaults={
                "timeout": "30",
                "retry": "3",
            },
            interpolation=None,          # 关闭 %(name)s 插值，避免值里的 % 号引发异常
            comment_prefixes=("#", ";"),  # 显式声明注释前缀
        )
        # 只在文件【确实存在】时读取，避免 demo 因环境差异崩溃
        if path.exists():
            self.parser.read(path, encoding="utf-8")

    def get_str(self, section: str, option: str, fallback: str = "") -> str:
        """取字符串；缺失时返回 fallback 而不是抛异常。"""
        return self.parser.get(section, option, fallback=fallback)

    def get_int(self, section: str, option: str, fallback: int = 0) -> int:
        """取整数。

        ⚠ 重要：ConfigParser.getint 的 fallback 只在【选项不存在】时生效，
        选项存在但内容不是数字（如 level = INFO）时【仍会抛 ValueError】。
        因此这里必须自己 try/except 才能做到真正的容错。
        """
        try:
            return self.parser.getint(section, option)
        except ValueError:
            # 分两类：选项不存在 vs 内容非数字，统一回退 fallback
            return fallback

    def get_bool(self, section: str, option: str, fallback: bool = False) -> bool:
        """取布尔；getboolean 只认 yes/no/true/false/on/off/1/0。"""
        try:
            return self.parser.getboolean(section, option)
        except ValueError:
            # 配置文件里写成 "是" 这类中文时 getboolean 会抛错，兜底更安全
            return fallback

    def sections(self) -> List[str]:
        """列出所有 section 名（不含 DEFAULT）。"""
        return self.parser.sections()


def demo_configparser() -> None:
    print("\n" + "=" * 74)
    print("【2】configparser 读 ini")
    print("=" * 74)

    ini_file = WORK_DIR / "app.ini"
    ini_content = """\
; 以分号开头的行是注释
[server]
host = 0.0.0.0
port = 8080
; timeout 和 retry 没写在这里，会继承 DEFAULT 段
debug = true
url = http://%(host)s:%(port)s/api   ; 插值语法

[database]
host = db.internal
port = 5432
name = learning_db
timeout = 10
percent_sign = 100%

[logging]
level = INFO
"""
    ini_file.write_text(ini_content, encoding="utf-8")
    print(f"已写入 ini: {ini_file}")

    cfg = AppConfig(ini_file)
    print(f"\nsections() → {cfg.sections()}")
    print("  注意：DEFAULT 段不出现在 sections() 中")

    print("\n取值演示（DEFAULT 继承生效）:")
    print(f"  server.timeout        = {cfg.get_int('server', 'timeout')}"
          f"  ← server 段【没写】，来自构造函数 defaults")
    print(f"  server.retry          = {cfg.get_int('server', 'retry')}")
    print(f"  database.timeout      = {cfg.get_int('database', 'timeout')}"
          f"  ← 本段显式写了，覆盖 DEFAULT")
    print(f"  server.host           = {cfg.get_str('server', 'host')!r}")
    print(f"  server.debug          = {cfg.get_bool('server', 'debug')}"
          f"  ← getboolean 解析 yes/no/true/false/1/0")
    print(f"  logging.level         = {cfg.get_str('logging', 'level')!r}")

    # fallback 的作用：键不存在时返回什么
    print("\nfallback 兜底:")
    print(f"  不存在的 section/option → {cfg.get_str('redis', 'host', fallback='未配置')!r}")
    print(f"  内容非数字 → {cfg.get_int('logging', 'level', fallback=-1)}"
          f"  ← 'INFO' 无法转 int，自动回退 -1")

    # DEFAULT 段的内容会被合并进 items()，这是最常见的坑
    print("\n⚠ 陷阱演示：section.items() 会【连带返回 DEFAULT 的项】")
    items = dict(cfg.parser.items("server"))
    print(f"  parser.items('server') 共有 {len(items)} 项：")
    for k, v in items.items():
        marker = "  ← 来自 DEFAULT，ini 文件里并没有" if k in ("timeout", "retry") else ""
        print(f"    {k:<8} = {v}{marker}")
    print("  正确做法：需要【本段自有】的键时用 parser._sections['server']，")
    print("           或 has_option 判断后区分处理")

    # 插值与百分号：本项目用 interpolation=None，所以 %(host)s 原样保留
    print("\n插值与特殊字符:")
    val = cfg.parser.get("server", "url")
    print(f"  server.url = {val!r}")
    print("  因 interpolation=None，%(host)s 不会被替换，这是【预期的】行为")
    pct = cfg.parser.get("database", "percent_sign")
    print(f"  database.percent_sign = {pct!r}  ← 关闭插值后百分号不再报错")
    print("  对照：若开启默认插值，读取含裸 % 的值会抛 InterpolationSyntaxError：")
    strict = ConfigParser(interpolation=None)  # 与上面一致，保证可正常读取
    strict.read_string("[d]\nv = 100%\n")   # read_string 不接收 encoding 参数
    print(f"     interpolation=None → 读取成功: {strict.get('d', 'v')!r}")
    # 用 BasicInterpolation 复现真实的报错行为（值里需写成 %% 来转义）
    from configparser import BasicInterpolation, InterpolationError
    try:
        bad = ConfigParser(interpolation=BasicInterpolation())
        bad.read_string("[d]\nv = 100%\n")
        bad.get("d", "v")
    except InterpolationError as e:
        # ⚠ InterpolationSyntaxError 继承自 InterpolationError 与 SyntaxError，
        #   【不继承 ValueError】，所以 except ValueError 是抓不到它的
        print(f"     BasicInterpolation → {type(e).__name__}: {e}")
    print("  结论：配置值里可能出现任意 % 字符，关闭插值是更安全的选择")

    # 写入 ini
    print("\n写入配置文件:")
    cfg.parser["cache"] = {"backend": "memory", "size": "256"}   # 无 section 时自动建段
    with open(ini_file, "w", encoding="utf-8") as f:
        cfg.parser.write(f)
    reread = AppConfig(ini_file)
    print(f"  新增 section 'cache' → {reread.get_str('cache', 'backend')!r}")


# ===== 语法解析 =====
# 【6】环境变量与命令行参数
#   os.environ 是一个类字典对象（os._Environ），存放进程的环境变量。
#   注意：
#     1. 环境变量【永远是字符串】，需要显式转 int/bool
#     2. Windows 大小写不敏感，Linux 敏感 → 统一用大写命名
#     3. getenv 支持第二个参数作为默认值，比 environ.get 更直观
def demo_env_and_argv() -> None:
    print("\n" + "=" * 74)
    print("【3】环境变量 与 命令行参数")
    print("=" * 74)

    # 临时注入几个环境变量（仅影响当前进程，脚本结束后自动消失）
    env_keys = {
        "APP_NAME": "环境中的应用",
        "APP_PORT": "9999",
        "APP_DEBUG": "true",
        "APP_LOG_DIR": "/var/log/learning",
    }
    for k, v in env_keys.items():
        os.environ[k] = v
    print("已临时设置环境变量:")
    for k in env_keys:
        print(f"  {k} = {os.environ[k]!r}")

    print("\n环境变量取值与类型转换:")
    print(f"  os.environ['APP_NAME']      = {os.environ['APP_NAME']!r}")
    print(f"  os.getenv('APP_PORT')        = {os.getenv('APP_PORT')!r}  ← 是字符串！")
    print(f"  手动转 int                   = {int(os.getenv('APP_PORT'))}")
    print(f"  to_bool(os.environ['APP_DEBUG']) = {to_bool(os.environ['APP_DEBUG'])}")
    print(f"  getenv 带默认值              = {os.getenv('NOT_SET', '兜底值')!r}")
    print(f"  getenv 读路径类配置          = {Path(os.getenv('APP_LOG_DIR'))}")

    # 关键警告：字符串布尔陷阱
    print("\n⚠ 布尔陷阱演示:")
    print(f"  bool('False')            = {bool('False')}   ← 非空字符串都是真！")
    print(f"  bool('')                 = {bool('')}")
    print(f"  to_bool('False')        = {to_bool('False')}  ← 必须显式转换")
    print(f"  to_bool('0')            = {to_bool('0')}")

    # argparse：把命令行变成结构化参数
    print("\nargparse 构造解析器（此处用 parse_args([]) 模拟空命令行）:")
    parser = argparse.ArgumentParser(
        prog="app.py",
        description="演示配置分层的命令行层",
        # epilog 打印在帮助末尾
        epilog="示例: app.py --port 9000 --debug",
    )
    parser.add_argument("--host", type=str, default="127.0.0.1",
                        help="监听地址（默认 %(default)s）")
    parser.add_argument("--port", type=int, default=8000,
                        help="监听端口，type=int 让 argparse 自动转换类型")
    # nargs="?" 表示可选地跟一个值：不给则为 None，给了就用该值
    parser.add_argument("--workers", type=int, nargs="?", const=4, default=1,
                        help="工作进程数")
    parser.add_argument("--debug", action="store_true", default=False,
                        help="开启调试模式（store_true 表示开关，不带值即为 True）")
    # append 表示可重复传入，结果收集到列表
    parser.add_argument("--tag", action="append", default=[],
                        help="可重复传入的标签")

    args = parser.parse_args([])
    print(f"  空命令行结果: host={args.host}, port={args.port}, debug={args.debug}")
    print(f"  变量名映射：--host → args.host（dest 可改名，如 dest='bind_host'）")
    print(f"  nargs='?' 的效果：不传 → {parser.parse_args([]).workers}，"
          f"裸 --workers → {parser.parse_args(['--workers']).workers}，"
          f"--workers 8 → {parser.parse_args(['--workers', '8']).workers}")
    print(f"  action='append' 可重复: "
          f"{parser.parse_args(['--tag', 'a', '--tag', 'b']).tag}")

    # 清理环境变量
    for k in env_keys:
        del os.environ[k]


# ===== 语法解析 =====
# 【7】★ 配置分层完整实现
#   加载顺序与优先级（数字越大优先级越高）：
#       1. DEFAULTS      最低
#       2. 配置文件       覆盖默认值
#       3. 环境变量       覆盖配置文件
#       4. 命令行参数     覆盖环境变量（最高）
#
#   三个必须讲清楚的设计点：
#   (a) 如何判断"某一层是否显式指定了这个键"
#       → 关键：不能拿合并后的值去判断！必须看【原始输入层】里有没有这个键。
#         argparse 的默认路径就是判断依据：
#           未传参 → args.__dict__ 里有默认值，无法区分"用户没传"和"用户传了默认值"
#         解决办法一：设 default=None，未传就是 None（明确表示"未指定"）
#         解决办法二：parser.parse_known_args + 检查 sys.argv（能精确区分）
#       这里采用【双重保险】：default=argparse.SUPPRESS，
#       未传参时该属性【根本不存在】于 Namespace 中。
#
#   (b) 扁平键还是嵌套键
#       → 环境变量天然扁平（APP_SERVER_PORT），
#         配置文件天然嵌套（{"server": {"port": ...}}）。
#         解决办法：用"扁平键 → 嵌套路径"的映射表把 env 翻译成同构的嵌套 dict，
#         这样四层就能用同一个 deep_merge 处理。
#
#   (c) 类型转换放在哪一步
#       → 全部统一到【最后】，加载完再一次性按 schema 转换，
#         避免每层各自转换导致逻辑分散。
class ConfigLoader:
    """四层配置加载器：默认值 → 配置文件 → 环境变量 → 命令行。"""

    # 环境变量前缀：只处理带此前缀的变量，避免污染
    ENV_PREFIX = "APP_"

    # 扁平 env 名 → 嵌套配置路径 的映射表
    ENV_MAP: Dict[str, Tuple[str, ...]] = {
        "APP_NAME": ("app_name",),
        "APP_DEBUG": ("debug",),
        "APP_HOST": ("server", "host"),
        "APP_PORT": ("server", "port"),
        "APP_WORKERS": ("server", "workers"),
        "APP_DB_HOST": ("database", "host"),
        "APP_DB_PORT": ("database", "port"),
        "APP_DB_NAME": ("database", "name"),
        "APP_LOG_DIR": ("log_dir",),
    }

    # 命令行参数名 → 嵌套配置路径
    CLI_MAP: Dict[str, Tuple[str, ...]] = {
        "host": ("server", "host"),
        "port": ("server", "port"),
        "workers": ("server", "workers"),
        "db_name": ("database", "name"),
        "log_dir": ("log_dir",),
    }

    def __init__(self) -> None:
        # 【第1层】默认值：任何时候都能跑起来的最小配置
        self.defaults: Dict[str, Any] = {
            "app_name": "默认应用",
            "debug": False,
            "server": {"host": "127.0.0.1", "port": 8000, "workers": 1},
            "database": {"host": "localhost", "port": 5432, "name": "dev_db"},
            "log_dir": "logs",
        }
        # 记录每个叶子键的来源，键为 "点分路径"，值为来源层名
        self.provenance: Dict[str, str] = {}
        self._mark_all(self.defaults, "默认值", self.provenance)

    # ---------- 内部工具 ----------
    @staticmethod
    def _set_path(cfg: Dict[str, Any], path: Tuple[str, ...], value: Any) -> None:
        """按路径写入嵌套 dict，缺失的中间层自动创建。"""
        node = cfg
        for key in path[:-1]:
            # 用 setdefault：已存在就复用，未存在就建新 dict
            node = node.setdefault(key, {})
        node[path[-1]] = value

    @classmethod
    def _mark_all(cls, cfg: Dict[str, Any], source: str,
                  provenance: Dict[str, str], prefix: str = "") -> None:
        """递归把某层所有叶子键标记为同一来源。"""
        for key, value in cfg.items():
            path = f"{prefix}{key}"
            if isinstance(value, dict):
                cls._mark_all(value, source, provenance, f"{path}.")
            else:
                provenance[path] = source

    def _set_with_source(self, path: Tuple[str, ...], value: Any, source: str) -> None:
        """写入配置并同步记录来源标记。"""
        self._set_path(self.defaults, path, value)
        self.provenance[".".join(path)] = source

    # ---------- 四层加载 ----------
    def load_file(self, path: Path) -> "ConfigLoader":
        """【第2层】加载 JSON 配置文件；文件不存在则保持默认值不变。"""
        if not path.exists():
            return self
        with open(path, "r", encoding="utf-8") as f:
            file_cfg = json.load(f)
        # 深合并：只覆盖文件中出现的键，其余保留默认值
        self.defaults = deep_merge(self.defaults, file_cfg)
        # 只给【文件里真实出现过】的叶子键打来源标记
        for key_path in self._iter_leaf_paths(file_cfg):
            self.provenance[key_path] = "配置文件"
        return self

    def load_env(self, environ: Optional[Dict[str, str]] = None) -> "ConfigLoader":
        """【第3层】加载环境变量，只处理映射表中登记的变量。"""
        env = os.environ if environ is None else environ
        for env_name, path in self.ENV_MAP.items():
            if env_name not in env:
                # ★ 关键：未设置的变量【直接跳过】，
                # 绝不能用 os.getenv(name, 默认值) 的默认值去覆盖下层，
                # 否则第四层的默认值会错误地盖掉第二三层的真实配置。
                continue
            # 值的类型转换推迟到最后统一做，这里先存原始字符串
            self._set_with_source(path, env[env_name], "环境变量")
        return self

    def load_cli(self, argv: Optional[List[str]] = None) -> "ConfigLoader":
        """【第4层】加载命令行参数，只覆盖【显式传入】的项。"""
        parser = argparse.ArgumentParser(
            prog="app.py", add_help=False,  # add_help=False 便于静默调用
        )
        parser.add_argument("--host", type=str, default=argparse.SUPPRESS)
        parser.add_argument("--port", type=str, default=argparse.SUPPRESS)
        parser.add_argument("--workers", type=str, default=argparse.SUPPRESS)
        parser.add_argument("--db-name", dest="db_name", type=str,
                            default=argparse.SUPPRESS)
        parser.add_argument("--log-dir", dest="log_dir", type=str,
                            default=argparse.SUPPRESS)
        parser.add_argument("--debug", action="store_true",
                            default=argparse.SUPPRESS)
        args, _unknown = parser.parse_known_args(argv or [])

        # ★★ 核心技巧：default=argparse.SUPPRESS 使得
        #    【用户没传的参数，其属性根本不会被设置到 Namespace 上】。
        #    因此 hasattr(args, 'port') 为 False 就精确代表"用户没指定 port"。
        #    若用 default=None 或 default=8000，就无法区分"没传"和"传了默认值"。
        if hasattr(args, "host"):
            self._set_with_source(self.CLI_MAP["host"], args.host, "命令行")
        if hasattr(args, "port"):
            self._set_with_source(self.CLI_MAP["port"], args.port, "命令行")
        if hasattr(args, "workers"):
            self._set_with_source(self.CLI_MAP["workers"], args.workers, "命令行")
        if hasattr(args, "db_name"):
            self._set_with_source(self.CLI_MAP["db_name"], args.db_name, "命令行")
        if hasattr(args, "log_dir"):
            self._set_with_source(self.CLI_MAP["log_dir"], args.log_dir, "命令行")
        if hasattr(args, "debug"):
            self._set_with_source(("debug",), args.debug, "命令行")
        return self

    @staticmethod
    def _iter_leaf_paths(cfg: Dict[str, Any], prefix: str = "") -> List[str]:
        """列出嵌套 dict 中所有叶子键的点分路径。"""
        paths: List[str] = []
        for key, value in cfg.items():
            path = f"{prefix}{key}"
            if isinstance(value, dict):
                paths.extend(ConfigLoader._iter_leaf_paths(value, f"{path}."))
            else:
                paths.append(path)
        return paths

    # ---------- 第5步：统一类型转换 ----------
    def typed(self) -> Dict[str, Any]:
        """所有层合并完毕后，统一按 schema 把字符串转成正确类型。"""
        c = self.defaults
        # int() 直接转：若配置写错类型会抛 ValueError，此处由调用方保证
        c["server"]["port"] = int(c["server"]["port"])
        c["server"]["workers"] = int(c["server"]["workers"])
        c["database"]["port"] = int(c["database"]["port"])
        # bool 必须用 to_bool：此时值可能是 "true" 字符串（来自 env/ini）
        c["debug"] = to_bool(c["debug"])
        # 路径类配置统一转 Path，避免下游到处做 Path(...)
        c["log_dir"] = Path(c["log_dir"])
        return c


# ===== 语法解析 =====
# 【8】分层配置的完整走查演示
def demo_layered_config() -> None:
    print("\n" + "=" * 74)
    print("【4】★ 配置分层完整实现（默认值 → 配置文件 → 环境变量 → 命令行）")
    print("=" * 74)

    # ---- 准备一个配置文件，故意与默认值、环境变量、命令行都有冲突 ----
    cfg_path = WORK_DIR / "app_settings.json"
    cfg_path.write_text(json.dumps({
        "app_name": "配置文件中的应用",
        "server": {
            "host": "10.0.0.1",
            "port": 8888,
            # 注意：这里【故意不写】workers，让它一路保持默认值，
            # 用来验证"未指定的键不会被后续层错误覆盖"
        },
        "database": {
            "host": "10.0.0.2",
            "port": 6543,
            "name": "file_db",
        },
        "log_dir": "logs_from_file",
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"配置文件已写入: {cfg_path}")
    print("  该文件与默认值 / 环境变量 / 命令行都存在冲突的键，便于观察覆盖过程\n")

    # ---- 逐层加载并观察变化 ----
    loader = ConfigLoader()

    print("第1层：仅默认值")
    print(f"  app_name={loader.defaults['app_name']!r}, "
          f"server.port={loader.defaults['server']['port']}, "
          f"server.workers={loader.defaults['server']['workers']}")

    # 第2层：配置文件
    loader.load_file(cfg_path)
    print("\n第2层：+ 配置文件（覆盖 app_name/server.port/database.*）")
    print(f"  app_name={loader.defaults['app_name']!r}  ← 来自配置文件")
    print(f"  server.port={loader.defaults['server']['port']}  ← 被配置文件覆盖")
    print(f"  server.workers={loader.defaults['server']['workers']}  "
          f"← 配置文件未提及，保持默认值")

    # 第3层：环境变量
    fake_env = {
        # APP_SERVER_PORT 不存在映射？实际映射名是 APP_PORT
        "APP_PORT": "7777",
        "APP_WORKERS": "16",
        "APP_NAME": "环境变量中的应用",
        "APP_LOG_DIR": "/var/log/from_env",
    }
    loader.load_env(fake_env)
    print("\n第3层：+ 环境变量（再次覆盖 app_name/server.port/server.workers）")
    print(f"  app_name={loader.defaults['app_name']!r}  ← 来自环境变量")
    print(f"  server.port={loader.defaults['server']['port']!r}  ← 来自环境变量")
    print(f"  server.workers={loader.defaults['server']['workers']!r}  ← 来自环境变量")
    print(f"  log_dir={loader.defaults['log_dir']!r}  ← 来自环境变量")

    # 第4层：命令行
    loader.load_cli(["--port", "9999", "--db-name", "cli_db", "--debug"])
    print("\n第4层：+ 命令行（只覆盖显式传入的 --port / --db-name / --debug）")
    print(f"  server.port={loader.defaults['server']['port']!r}  ← 来自命令行")
    print(f"  database.name={loader.defaults['database']['name']!r}  ← 来自命令行")
    print(f"  debug={loader.defaults['debug']!r}  ← 来自命令行")
    print(f"  app_name={loader.defaults['app_name']!r}  "
          f"← 命令行未指定，保持环境变量的值")
    print(f"  server.host={loader.defaults['server']['host']!r}  "
          f"← 层层未覆盖，保持配置文件的值")

    # ---- 类型统一转换 ----
    final = loader.typed()
    print("\n第5步：统一类型转换后（此时才把字符串转 int/bool/Path）")
    print(f"  server.port   : {final['server']['port']!r}  "
          f"({type(final['server']['port']).__name__})")
    print(f"  debug         : {final['debug']!r}  ({type(final['debug']).__name__})")
    print(f"  log_dir       : {final['log_dir']!r}  ({type(final['log_dir']).__name__})")

    # ---- 来源追踪表 ----
    print("\n★ 每个配置项的最终来源（provenance，排障神器）：")
    print(f"  {'配置路径':<22}{'最终值':<24}{'来源':<10}")
    print(f"  {'-' * 56}")
    for key_path in ConfigLoader._iter_leaf_paths(final):
        node: Any = final
        for part in key_path.split("."):
            node = node[part]
        val_repr = repr(node)
        if len(val_repr) > 22:
            val_repr = val_repr[:19] + "..."
        print(f"  {key_path:<22}{val_repr:<24}{loader.provenance.get(key_path, '?'):<10}")

    # ---- 深合并 vs 浅合并的差异 ----
    print("\n深合并 vs 浅合并的差异:")
    base = {"db": {"host": "h", "port": 1, "user": "u"}}
    override = {"db": {"host": "new"}}
    shallow = {**base, **override}
    deep = deep_merge(base, override)
    print(f"  基础    : {base}")
    print(f"  覆盖层  : {override}")
    print(f"  浅合并  : {shallow['db']}  ← 整个 db 被替换，port/user 全丢")
    print(f"  深合并  : {deep['db']}  ← 只覆盖 host，其余保留")
    print("  结论：分层配置必须用深合并，否则配置文件只写一个子键就会抹掉其他默认值")


# ===== 语法解析 =====
# 【9】小结
def demo_summary() -> None:
    print("\n" + "=" * 74)
    print("【5】小结：配置管理的八条军规")
    print("=" * 74)
    print("""
  1. 优先级：命令行 > 环境变量 > 配置文件 > 默认值
  2. 合并而非替换：后续层只覆盖【显式指定】的键，未指定的保持原值
  3. 必须用深合并：否则嵌套配置会被整个兄弟节点覆盖
  4. 判断"是否显式指定"要看原始输入层，绝不能看合并后的值
     argparse 的 default=argparse.SUPPRESS 是最干净的解法
  5. 环境变量与 ini 读出来都是字符串，类型转换统一放到最后一步
  6. 环境变量别用 getenv 的默认值去覆盖下层（会误伤），未设置就跳过
  7. 配置全部读失败时要能回退到默认值启动，不要让服务因配置崩掉
  8. 给关键配置项加来源追踪（provenance），排查线上问题时价值极大
    """)


def main() -> None:
    """主入口。"""
    print("=" * 74)
    print("配置管理：json / configparser / 环境变量 / 命令行 / 分层")
    print("=" * 74)
    print(f"Python 版本: {sys.version.split()[0]}")
    print()

    # 临时目录：所有文件写在 _tmp_config 下，结束后清理
    tmp = Path(tempfile.mkdtemp(prefix="pycfg_"))
    global WORK_DIR
    WORK_DIR = tmp
    print(f"本次运行使用临时目录（退出后自动清理）: {tmp}\n")

    try:
        demo_json_config()
        demo_configparser()
        demo_env_and_argv()
        demo_layered_config()
        demo_summary()
    finally:
        # 无论是否抛异常都清理临时文件，避免留下垃圾
        shutil.rmtree(tmp, ignore_errors=True)
        print(f"\n已清理临时目录: {tmp}")


if __name__ == "__main__":
    main()