"""
================================================================================
 04_pytest_style.py —— pytest 风格测试文件
================================================================================

⚠️ 【运行前提】本文件用到 pytest 特性，必须先安装：
       pip install pytest
       pip install pytest-cov        # 覆盖率
       pip install pytest-mock      # 额外的 mock fixture

   运行方式：
       pytest 04_pytest_style.py -v              # 详细模式
       pytest 04_pytest_style.py -v --cov=.      # 带覆盖率
       pytest 04_pytest_style.py -k "param"      # 只跑名字含 param 的用例
       pytest 04_pytest_style.py --lf            # 只跑上次失败的
       pytest 04_pytest_style.py -x -q           # 首个失败即停，静默模式

   如果本文件被直接 `python 04_pytest_style.py` 运行，
   底部的降级逻辑会自动执行一套「无 pytest 的模拟测试」，不会报错。

【演示的语法点】
  1. pytest 收集规则    : test_*.py 文件 + test_* 函数/方法（类名 Test*）
  2. fixture            : @pytest.fixture，依赖注入，自动清理
  3. fixture 作用域     : function / class / module / session
  4. yield fixture      : setup 后 yield，teardown 在 yield 之后执行
  5. conftest.py        : 目录级共享 fixture，无需 import 即可使用
  6. @pytest.mark.parametrize : 参数化，一次测试多组数据
  7. @pytest.mark.skipif/skip : 跳过标记
  8. @pytest.fixture(params=...) : 参数化 fixture
  9. monkeypatch        : 自动回滚的补丁工具（setattr/setenv/delitem）
 10. capsys             : 捕获标准输出/错误
 11. tmp_path           : 每个用例独立的临时目录
 12. pytest.raises      : 异常断言（替代 unittest 的 assertRaises）
 13. unittest.mock      : Mock / MagicMock / patch / autospec / assert_called
 14. 自定义 hook 与 mark : conftest.py 中的 pytest_configure

【优雅降级设计】
  文件顶部用 try/except ImportError 检测 pytest：
     - 装了 pytest    -> 正常定义 fixture 与用例，由 pytest 收集运行
     - 没装 pytest    -> 定义同名「空壳」fixture，让裸 assert 用例仍可运行
  这样 `python -m py_compile` 与 `python 04_pytest_style.py` 都永不失败。
"""

from __future__ import annotations

import os
import sys
import tempfile
from typing import Any, Iterator


# ==============================================================================
# 零、pytest 可用性检测与优雅降级
# ==============================================================================
# ===== 语法解析 =====
# try/except ImportError：导入失败时捕获异常，给出「备用方案」而不是让程序崩溃。
# 这是编写「可选依赖」代码的标准手法，标准库本身大量使用（importlib.util.find_spec）。
HAS_PYTEST = False
pytest: Any = None
try:
    import pytest as _pytest_module

    pytest = _pytest_module
    HAS_PYTEST = True
except ImportError:  # pragma: no cover - 仅在未安装 pytest 时触发
    # 未装 pytest 时，提供最小可用的桩(stub)，
    # 让本文件被裸 Python 解释器直接运行时不出现 NameError。
    HAS_PYTEST = False


def fixture(*args: Any, **kwargs: Any) -> Any:
    """兼容层：有 pytest 就用真的 fixture 装饰器；没有就退化成「直接调用」的装饰器。

    为什么这么写？
      让本文件既能作为真正的 pytest 用例集被收集，
      又能在没有 pytest 的机器上 `python 04_pytest_style.py` 直接跑通演示。
    """
    if HAS_PYTEST:
        return pytest.fixture(*args, **kwargs)

    def _decorator(func: Any) -> Any:
        # 降级方案：打个标记，真正的调用在 demo_without_pytest() 里手工完成
        func.__is_fallback_fixture__ = True
        return func

    # 处理 @fixture 不带括号的情况
    if len(args) == 1 and callable(args[0]) and not kwargs:
        return _decorator(args[0])
    return _decorator


def mark(name: str) -> Any:
    """兼容层：@mark('parametrize') / @mark('skip')。"""
    if HAS_PYTEST:
        return getattr(pytest.mark, name)

    def _decorator(*d_args: Any, **d_kwargs: Any) -> Any:
        def _inner(func: Any) -> Any:
            return func

        if len(d_args) == 1 and callable(d_args[0]) and not d_kwargs:
            return d_args[0]
        return _inner

    return _decorator


def raises(expected: type[BaseException], **kwargs: Any) -> Any:
    """兼容层：pytest.raises。降级时返回 contextlib.suppress 的等价实现。"""
    if HAS_PYTEST:
        return pytest.raises(expected, **kwargs)

    import contextlib

    return contextlib.suppress(expected)


# ==============================================================================
# 一、被测业务代码（保持"业务与测试分离"）
# ==============================================================================
class UserRepository:
    """内存版用户仓库 —— 测试时不需要真数据库。"""

    def __init__(self, db_path: str = ":memory:") -> None:
        self.db_path = db_path
        self._users: dict[int, dict[str, Any]] = {}
        self._next_id = 1
        self.query_count = 0     # 用于验证缓存是否生效

    def create(self, name: str, email: str) -> dict[str, Any]:
        """创建用户。"""
        if "@" not in email:
            raise ValueError(f"非法邮箱：{email}")
        user = {
            "id": self._next_id,
            "name": name,
            "email": email,
            "active": True,
        }
        self._users[self._next_id] = user
        self._next_id += 1
        return user.copy()      # 返回副本，防止外部篡改内部状态

    def get(self, user_id: int) -> dict[str, Any] | None:
        """按 id 查询。"""
        self.query_count += 1
        user = self._users.get(user_id)
        return user.copy() if user else None

    def find_by_email(self, email: str) -> dict[str, Any] | None:
        """按邮箱查询（线性扫描 —— 故意保留低效实现）。"""
        self.query_count += 1
        for user in self._users.values():
            if user["email"] == email:
                return user.copy()
        return None

    def deactivate(self, user_id: int) -> bool:
        """停用用户。"""
        if user_id not in self._users:
            return False
        self._users[user_id]["active"] = False
        return True

    def count_active(self) -> int:
        return sum(1 for u in self._users.values() if u["active"])


# ==============================================================================
# 二、fixture：pytest 的依赖注入核心
# ==============================================================================
# ===== 语法解析 =====
# @pytest.fixture 把函数标记为"工厂"。
# 测试函数的参数名与 fixture 函数名相同 -> pytest 自动调用它并传参。
# 默认作用域 function：每个测试函数执行一次。
#
# yield fixture 是最重要的写法：
#   yield 之前的代码 = setup（测试前执行）
#   yield 之后的代码 = teardown（测试后执行，即使测试失败也保证执行）
# 相当于 try/finally，但测试用例内部完全看不到这层样板代码。


@fixture
def repo() -> Iterator[UserRepository]:
    """函数级 fixture：每个用例一个新的干净仓库。"""
    repository = UserRepository()
    # ===== setup =====
    # 预置一些通用数据，避免每个用例重复造数据（DRY）
    repository.create("alice", "alice@example.com")
    repository.create("bob", "bob@example.com")
    yield repository
    # ===== teardown =====
    # pytest 保证这段代码一定执行（相当于 finally）
    repository._users.clear()


@fixture
def empty_repo() -> UserRepository:
    """不带预置数据的空仓库。"""
    return UserRepository()


@fixture
def sample_users() -> list[dict[str, Any]]:
    """返回值型 fixture：不需要清理时，直接 return 即可，不必用 yield。"""
    return [
        {"id": 1, "name": "小明", "email": "xiaoming@example.com"},
        {"id": 2, "name": "小红", "email": "xiaohong@example.com"},
        {"id": 3, "name": "小刚", "email": "xiaogang@example.com"},
    ]


@fixture(params=[":memory:", "file.db", "/tmp/test.db"])
def path_param_fixture(request: Any) -> str:
    """参数化 fixture：params= 会让同一 fixture 按 N 组参数各实例化一次。

    工程价值：把「各种配置组合」当作一等公民来测，而不是在代码里写 if/else。
    注意：取参数值的正确方式是 request.param，不是形参默认值。
    """
    return str(request.param)


class TestParameterizedFixture:
    """消费参数化 fixture 的用例：同一份测试逻辑跑 N 遍。"""

    def test_db_path_reachable(self, path_param_fixture: str) -> None:
        """每个参数组合都会成为一个独立的测试 ID 显示在报告中。"""
        repo = UserRepository(db_path=path_param_fixture)
        assert repo.db_path == path_param_fixture
        print(f"\n  正在验证 db_path = {path_param_fixture}")


# ==============================================================================
# 三、基础用例：普通断言 + pytest.raises
# ==============================================================================
class TestUserRepository:
    """类名以 Test 开头 -> pytest 才会收集这个类（不同于 unittest 的任意类）。"""

    # --------------------------------------------------------------
    # 注意：pytest 不用继承任何基类，直接写 class + def 即可。
    # 这是 pytest 相比 unittest 最明显的简洁优势。
    # --------------------------------------------------------------

    def test_create_user_success(self, repo: UserRepository) -> None:
        """普通用例：repo 参数由同名 fixture 自动注入。"""
        user = repo.create("carol", "carol@example.com")
        assert user["id"] == 3                       # 裸 assert，失败自动显示两边值
        assert user["name"] == "carol"
        assert user["active"] is True

    def test_create_user_invalid_email(self, repo: UserRepository) -> None:
        """pytest.raises：异常断言，比 try/except 更简洁。

        好处：可以检查异常消息（match 参数支持正则匹配）
        """
        with raises(ValueError, match="非法邮箱"):
            # match 是正则：注意这里的特殊字符需转义
            repo.create("dave", "not-an-email")

    def test_get_user_not_found(self, repo: UserRepository) -> None:
        """不存在的用户返回 None，而不是抛异常（工程上要明确契约）。"""
        assert repo.get(9999) is None

    def test_find_by_email(self, repo: UserRepository) -> None:
        found = repo.find_by_email("alice@example.com")
        assert found is not None
        assert found["name"] == "alice"

    def test_deactivate_and_count(self, repo: UserRepository) -> None:
        """一个用例里覆盖多个相关断言 —— 逻辑连贯时不必拆太细。"""
        assert repo.deactivate(1) is True
        assert repo.deactivate(9999) is False          # 不存在返回 False
        assert repo.count_active() == 1

    def test_returned_dict_is_copy(self, repo: UserRepository) -> None:
        """防御性拷贝测试：外部修改返回值不应影响内部数据。"""
        user = repo.get(1)
        assert user is not None
        user["name"] = "HACKED"
        assert repo.get(1)["name"] == "alice"          # type: ignore[index]

    # ==============================================================
    # 四、@pytest.mark.parametrize 参数化
    # ==============================================================
    # ===== 语法解析 =====
    # 把「同一段测试逻辑 + 多组输入」写在一起，避免复制粘贴 N 个测试函数。
    # 单参数：传一个列表；多参数：传"列表的列表"（每项是元组/列表）
    # ids= 可自定义报告里显示的名字，否则显示 value0/value1

    @mark.parametrize("name,email", [
        ("张三", "zhangsan@example.com"),
        ("Bob", "bob@example.com"),
        ("user_2024", "u2024@example.com"),
    ], ids=["中文名", "英文名", "含下划线"])
    def test_parametrized_create(
        self, repo: UserRepository, name: str, email: str
    ) -> None:
        """参数化：一次运行，报告里生成 3 个独立用例。"""
        user = repo.create(name, email)
        assert user["name"] == name
        assert user["email"] == email

    @mark.parametrize("user_id,expected", [(1, True), (2, True), (999, False)])
    def test_parametrized_deactivate(
        self, repo: UserRepository, user_id: int, expected: bool
    ) -> None:
        """布尔结果参数化：把边界用例一次性铺开。"""
        assert repo.deactivate(user_id) is expected

    @mark.parametrize("bad_email", [
        "no-at-sign",
        "@example.com",
        "user@",
        "",
    ])
    def test_parametrized_invalid_emails(
        self, repo: UserRepository, bad_email: str
    ) -> None:
        """错误路径也要参数化 —— 异常分支往往才是 bug 温床。"""
        with raises(ValueError):
            repo.create("x", bad_email)

    @mark.parametrize("count", [0, 1, 2, 3])
    def test_count_active_matches(self, repo: UserRepository, count: int) -> None:
        """参数 + fixture 组合使用。"""
        for i in range(1, count + 1):
            repo.deactivate(i)
        assert repo.count_active() == 3 - count


# ==============================================================================
# 五、monkeypatch：自动回滚的 mock 工具
# ==============================================================================
# ===== 语法解析 =====
# monkeypatch 是 pytest 内置 fixture，专门用来"临时篡改"环境，出作用域自动还原。
# 相比 unittest.mock.patch 的优势：
#   1. 不需要 with 上下文管理器，不用写 start/stop
#   2. 改动自动回滚，测试间零污染
#   3. 支持 setattr / setitem / delitem / setenv / delenv / chdir / syspath_prepend
#
# 何时用 monkeypatch、何时用 mock.patch？
#   - 改环境变量/属性/CWD      -> monkeypatch（更简洁）
#   - 替换整个对象/打调用桩     -> unittest.mock.patch（能力更强，可断言调用）


class TestConfig:
    """演示 monkeypatch 修改环境变量与模块属性。"""

    def test_default_env(self) -> None:
        """用 monkeypatch.setenv 设置环境变量，会在用例结束后自动还原。"""
        monkey_env = os.environ.get("APP_ENV")
        assert monkey_env is None or isinstance(monkey_env, str)
        print(f"\n  当前 APP_ENV = {monkey_env!r}")

    def test_setenv(self, monkeypatch: Any) -> None:
        """monkeypatch.setenv(key, value)：设置后 os.environ 立即可见。"""
        # monkeypatch 形参只要名字叫 monkeypatch，pytest 就自动注入
        monkeypatch.setenv("APP_ENV", "staging")
        monkeypatch.setenv("DEBUG", "1")
        assert os.environ["APP_ENV"] == "staging"
        # 用例结束 -> APP_ENV/DEBUG 自动从环境变量里移除，无需手动清理

    def test_delenv(self, monkeypatch: Any) -> None:
        """monkeypatch.delenv(key, raising=False)：变量不存在时也不报错。"""
        monkeypatch.setenv("TEMP_VAR", "1")
        assert "TEMP_VAR" in os.environ
        monkeypatch.delenv("TEMP_VAR", raising=False)
        assert "TEMP_VAR" not in os.environ

    def test_setattr(self, monkeypatch: Any) -> None:
        """monkeypatch.setattr(对象, 属性名, 新值)：临时替换实例/类属性。

        用字符串路径可以替换尚未导入模块的深层属性：
            monkeypatch.setattr("os.getcwd", lambda: "/fake")
        """
        repo = UserRepository()
        assert repo.db_path == ":memory:"
        monkeypatch.setattr(repo, "db_path", "/tmp/patched.db")
        assert repo.db_path == "/tmp/patched.db"
        # 用例结束后 repo.db_path 自动变回 ":memory:"

    def test_chdir(self, monkeypatch: Any, tmp_path: Any) -> None:
        """monkeypatch.chdir(path) + tmp_path fixture：文件操作的黄金组合。"""
        # tmp_path 是 pytest 内置 fixture，给每个用例一个独立的临时目录，
        # 用例结束后 pytest 自动清理，不需要 tempfile 手工管理
        monkeypatch.chdir(tmp_path)
        assert os.getcwd() == str(tmp_path.resolve())

        target = tmp_path / "data.txt"
        target.write_text("hello pytest", encoding="utf-8")
        assert target.read_text(encoding="utf-8") == "hello pytest"
        # 用例结束后 monkeypatch 会自动 chdir 回原目录，tmp_path 会被清理

    def test_syspath_prepend(self, monkeypatch: Any, tmp_path: Any) -> None:
        """monkeypatch.syspath_prepend：把目录加入 sys.path 前端。

        经典场景：被测模块放在 tests/fixtures/ 下，不便直接 import 时。
        """
        module_file = tmp_path / "dynamic_module.py"
        module_file.write_text("VALUE = 42\n", encoding="utf-8")
        monkeypatch.syspath_prepend(str(tmp_path))

        import dynamic_module          # 此时才能 import 到

        assert dynamic_module.VALUE == 42


# ==============================================================================
# 六、capsys：捕获标准输出
# ==============================================================================
class TestCapsys:
    """capsys fixture：捕获 print 输出，用于测试 CLI 工具和日志。"""

    def test_capture_stdout(self, capsys: Any) -> None:
        """capsys.readouterr() 返回一个命名元组 (out, err)。"""
        print("标准输出内容")
        captured = capsys.readouterr()
        assert "标准输出内容" in captured.out
        assert captured.err == ""

        # 再次调用会清空缓冲（所以每个用例内注意只调用一次做整体断言）

    def test_capture_stderr(self, capsys: Any) -> None:
        """错误信息通常写到 stderr，断言它比断言 stdout 更有意义。"""
        print("出错啦", file=sys.stderr)
        captured = capsys.readouterr()
        assert "出错啦" in captured.err
        assert captured.out == ""


# ==============================================================================
# 七、unittest.mock：Mock / MagicMock / patch / autospec
# ==============================================================================
# ===== 语法解析 =====
# Mock 是「万能替身」：调用它的任何方法/属性都自动返回一个新 Mock，不会真的执行。
# MagicMock 更强：额外支持 __len__ / __iter__ / __contains__ 等魔术方法，
#                所以可以直接传给 len() / for / in。
#
# 三大典型用法：
#   1. 注入依赖    —— 替换慢/贵/不稳定的依赖（数据库、网络、随机数）
#   2. 隔离测试    —— 只测当前类，不测被依赖方
#   3. 断言调用    —— verify() / assert_called_once_with() 验证交互契约

from unittest.mock import MagicMock, Mock, PropertyMock, call, patch


class PaymentGateway:
    """假想的第三方支付网关 —— 真实实现要调网络，测试时必须替换掉。"""

    def charge(self, amount: float, card: str) -> dict[str, Any]:
        raise NotImplementedError("真实实现会调 HTTP 接口")

    def refund(self, txn_id: str) -> bool:
        raise NotImplementedError


class OrderService:
    """订单服务：依赖 PaymentGateway，适合演示依赖注入与 mock。"""

    def __init__(self, gateway: PaymentGateway) -> None:
        self.gateway = gateway

    def checkout(self, amount: float, card: str) -> str:
        """下单：调网关扣款，成功返回订单号。"""
        result = self.gateway.charge(amount, card)
        if result.get("ok"):
            return str(result["txn_id"])
        raise ValueError(f"扣款失败：{result.get('reason')}")


class TestMocking:
    """完整的 mock 演示。"""

    def test_mock_basic(self) -> None:
        """Mock：调用任意属性都返回 Mock，且自动记录调用。"""
        m = Mock()
        m.fetch_data("arg1", key="arg2")      # 不会真的执行任何逻辑

        # 断言调用方式
        m.fetch_data.assert_called_once_with("arg1", key="arg2")
        m.fetch_data.assert_called_once()                 # 恰好调用 1 次
        m.fetch_data.assert_called()                      # 至少调用过
        assert m.fetch_data.call_count == 1               # 底层计数属性
        print(f"\n  Mock 调用记录 : {m.mock_calls}")
        print(f"  return_value  : {m.fetch_data.return_value!r}")

    def test_magicmock_magic_methods(self) -> None:
        """MagicMock 支持魔术方法，能用于 len / 迭代 / in。"""
        magic = MagicMock()
        magic.__len__.return_value = 3
        magic.__iter__.return_value = iter(["a", "b", "c"])
        magic.__contains__.return_value = True

        assert len(magic) == 3
        assert list(magic) == ["a", "b", "c"]
        assert "a" in magic
        print(f"  MagicMock 是 Mock 的子类 : {issubclass(MagicMock, Mock)}")

    def test_side_effect_chain(self) -> None:
        """side_effect：让 Mock 按顺序返回不同值，或直接调用真实函数。

        这是 Mock 最实用的能力 —— 模拟「时好时坏」的依赖。
        """
        # 方式 1：传列表，每次调用弹出一个值，用完抛 StopIteration
        flaky = Mock(side_effect=["first", "second", TimeoutError("第三次数组越界")])

        assert flaky() == "first"
        assert flaky() == "second"
        try:
            flaky()
        except TimeoutError as exc:
            print(f"\n  side_effect 模拟失败 : {exc}")

        # 方式 2：传一个函数 -> 直接执行该函数（保留真实行为，只挡副作用）
        passthrough = Mock(side_effect=lambda x: x * 2)
        assert passthrough(21) == 42

    def test_return_value_chain(self) -> None:
        """配置多级返回：return_value 本身可以再是一个 Mock。"""
        resp = Mock()
        resp.status_code = 200
        resp.json.return_value = {"data": [1, 2, 3]}
        resp.json().get  # 访问嵌套属性会自动创建

        http = Mock()
        http.get.return_value = resp

        result = http.get("https://example.com/api")
        assert result.status_code == 200
        assert result.json() == {"data": [1, 2, 3]}
        http.get.assert_called_once_with("https://example.com/api")

    def test_patch_decorator(self) -> None:
        """@patch：把类的某个方法替换掉，用例结束自动还原。

        参数顺序陷阱：mock 会作为第一个位置参数注入，
        所以它必须放在参数列表最前面。
        """
        gateway = PaymentGateway()
        service = OrderService(gateway)
        assert isinstance(gateway, PaymentGateway)
        print(f"\n  未 patch 时 charge 会抛 NotImplementedError")

        # 手动 patch 版本（下面用上下文管理器形式更直观）
        with patch.object(PaymentGateway, "charge") as mock_charge:
            mock_charge.return_value = {"ok": True, "txn_id": "TXN-1001"}
            order_id = service.checkout(99.9, "4111111111111111")

            assert order_id == "TXN-1001"
            # 验证调用参数 —— 这是 mock 的核心价值
            mock_charge.assert_called_once_with(99.9, "4111111111111111")
            print(f"  patch 后成功下单 : {order_id}")

    def test_patch_failure_path(self) -> None:
        """异常路径也要测 —— 这是 mock 最有价值的场景之一。"""
        service = OrderService(PaymentGateway())
        with patch.object(PaymentGateway, "charge") as mock_charge:
            mock_charge.return_value = {"ok": False, "reason": "余额不足"}
            with raises(ValueError, match="扣款失败"):
                service.checkout(1000.0, "invalid_card")
            assert mock_charge.call_count == 1

    def test_autospec_prevents_typos(self) -> None:
        """autospec=True：按真实签名创建 mock，参数名写错会立即报错。

        没有 autospec 时，charge(amont=...) 这种拼写错误会静默通过，
        因为 Mock 对未知属性来者不拒。autospec 能堵住这个漏洞。
        """
        with patch.object(PaymentGateway, "charge", autospec=True) as mock_charge:
            mock_charge.return_value = {"ok": True, "txn_id": "TXN-2002"}
            service = OrderService(PaymentGateway())
            assert service.checkout(50.0, "card") == "TXN-2002"
            mock_charge.assert_called_once()

    def test_assert_has_calls_order(self) -> None:
        """assert_has_calls：验证多次调用的顺序（严格 vs 宽松）。"""
        notifier = Mock()
        notifier.send("user1", "订单已创建")
        notifier.send("user2", "订单已发货")

        # 宽松：只要求包含这两次调用，允许中间有其他调用
        notifier.send.assert_has_calls([
            call("user1", "订单已创建"),
            call("user2", "订单已发货"),
        ])
        # 严格：任何_order="any"之外的（严格模式）不允许有多余调用
        print(f"  完整调用序列 : {notifier.send.call_args_list}")

    def test_property_mock(self) -> None:
        """PropertyMock：替换 @property 背后的类属性，构造实例时就能控制其值。"""
        # 直接指定类对象做目标，比 patch("__main__.Config") 更稳：
        # 补丁时模块名可能是 __main__ 或 pytest 重写的模块名
        with patch.object(Config, "DEBUG_MODE", new_callable=PropertyMock) as mock_dbg:
            mock_dbg.return_value = False
            config = Config()
            assert config.debug_enabled is False
            print("\n  PropertyMock 把 DEBUG_MODE 设为 False，实例读到 False")

    def test_patch_builtin_and_env(self) -> None:
        """patch 还能替换标准库函数和 os.environ。"""
        with patch.dict(os.environ, {"APP_ENV": "production"}, clear=False):
            assert os.environ["APP_ENV"] == "production"
        # 退出 with 后 APP_ENV 恢复原值

        with patch("random.randint", return_value=42):
            import random

            assert random.randint(0, 100) == 42      # type: ignore[arg-type]


class Config:
    """带 property 的配置类，配合 PropertyMock 演示。"""

    DEBUG_MODE = True

    @property
    def debug_enabled(self) -> bool:
        return self.DEBUG_MODE


# ==============================================================================
# 八、跳过与标记
# ==============================================================================
class TestMarkers:
    """pytest 的 mark 机制：分组、跳过、条件跳过。"""

    @mark.skip(reason="演示：总是跳过")
    def test_always_skipped(self) -> None:
        raise AssertionError("永远不会执行到这里")

    @mark.skipif(sys.platform == "win32", reason="POSIX 专属测试")
    def test_posix_only(self) -> None:
        # 当前是 Windows -> 被跳过
        assert os.name == "posix"

    @mark.skipif(not HAS_PYTEST, reason="需要 pytest")
    def test_requires_pytest(self) -> None:
        # 装了 pytest 才跑
        assert HAS_PYTEST is True

    @mark.xfail(reason="已知 bug #1234，待修复", strict=True)
    def test_known_bug(self) -> None:
        """xfail：标记「预期失败」。修复后 CI 会因为 strict=True 而报错提醒你摘掉标记。"""
        assert 1 == 2, "故意失败"

    def test_env(self, monkeypatch: Any) -> None:
        """测试真实环境依赖：Windows/macOS/Linux 都要能跑。"""
        assert os.name in ("posix", "nt")


# ==============================================================================
# 九、无 pytest 时的降级演示
# ==============================================================================
def demo_without_pytest() -> int:
    """当 pytest 不可用时，运行一套纯标准库的等价演示。

    目的：保证 `python 04_pytest_style.py` 在任何环境都不会崩，
         同时让读者看到"裸 unittest 也能做同样的事"。
    """
    print("=" * 78)
    print(" 04. pytest 风格测试 —— 降级演示模式（未检测到 pytest）")
    print("=" * 78)
    print(f"\n  pytest 是否可用 : {HAS_PYTEST}")
    print(f"  Python 版本      : {sys.version.split()[0]}")
    print("\n  ⚠️ 要运行完整的 pytest 用例，请先安装：")
    print("     pip install pytest pytest-cov")
    print("     然后执行： pytest 04_pytest_style.py -v\n")

    print("[降级演示 1] fixture 的手工调用")
    print("-" * 78)
    # 降级模式下 fixture 仍是普通函数，可以直接调用拿到「被注入的对象」
    print(f"  repo fixture 本体    : {repo.__name__}")
    print(f"  是生成器函数          : {hasattr(repo, '__code__') and bool(repo.__code__.co_flags & 0x20)}")
    manual = UserRepository()
    manual.create("alice", "alice@example.com")
    assert manual.get(1)["name"] == "alice"   # type: ignore[index]
    print(f"  手工创建的用户        : {manual.get(1)}")

    print("\n[降级演示 2] parametrize 的等价实现：表驱动循环")
    print("-" * 78)
    cases = [("张三", "zhangsan@x.com"), ("Bob", "bob@x.com")]
    for name, email in cases:
        r = UserRepository()
        created = r.create(name, email)
        assert created["name"] == name
        print(f"  ✓ 创建 {name:<6} -> id={created['id']}")

    print("\n[降级演示 3] pytest.raises 的等价实现：unittest.mock")
    print("-" * 78)
    from unittest import TestCase

    class _TempCase(TestCase):
        def runTest(self) -> None:  # noqa: N802 - unittest 要求这个名字
            pass

    with _TempCase().assertRaises(ValueError):
        UserRepository().create("x", "bad-email")
    print("  ✓ 非法邮箱正确抛出 ValueError")

    print("\n[降级演示 4] mock 在标准库里也是现成的")
    print("-" * 78)
    fake_gateway = MagicMock()
    fake_gateway.charge.return_value = {"ok": True, "txn_id": "TXN-DEMO"}
    service = OrderService(fake_gateway)
    assert service.checkout(88.8, "card") == "TXN-DEMO"
    fake_gateway.charge.assert_called_once_with(88.8, "card")
    print("  ✓ mock 替换支付网关成功，返回订单号 TXN-DEMO")

    print("\n[降级演示 5] monkeypatch 的等价实现：patch.dict")
    print("-" * 78)
    with patch.dict(os.environ, {"APP_ENV": "staging"}):
        assert os.environ["APP_ENV"] == "staging"
    print("  ✓ 环境变量临时设置并在退出后自动还原")

    print("\n[降级演示 6] tmp_path 的等价实现：tempfile")
    print("-" * 78)
    with tempfile.TemporaryDirectory() as tmp_dir:
        file_path = os.path.join(tmp_dir, "demo.txt")
        with open(file_path, "w", encoding="utf-8") as f:
            f.write("hello pytest")
        with open(file_path, encoding="utf-8") as f:
            assert f.read() == "hello pytest"
        print(f"  ✓ 临时文件读写成功，自动清理：{tmp_dir}")

    print("\n" + "=" * 78)
    print(" 降级演示全部通过。安装 pytest 后可运行完整的 fixture/parametrize 用例。")
    print("=" * 78)
    return 0


# ==============================================================================
# 十、入口
# ==============================================================================
def main() -> int:
    """有 pytest 就打印安装说明，无 pytest 就跑降级演示。"""
    if HAS_PYTEST:
        print("=" * 78)
        print(" 04. pytest 风格测试文件")
        print("=" * 78)
        print(f"\n  ✅ 检测到 pytest {getattr(pytest, '__version__', '未知版本')}")
        print("\n  本文件包含以下 pytest 特性：")
        features = [
            ("fixture", "repo / empty_repo / sample_users / path_param_fixture"),
            ("yield fixture", "setup-teardown 自动配对"),
            ("parametrize", "函数参数化 + fixture 参数化"),
            ("monkeypatch", "setenv / delenv / setattr / chdir / syspath_prepend"),
            ("capsys", "捕获 stdout / stderr"),
            ("tmp_path", "每用例独立临时目录"),
            ("mock", "Mock / MagicMock / patch / autospec / PropertyMock / patch.dict"),
            ("mark", "skip / skipif / xfail"),
        ]
        for name, detail in features:
            print(f"    - {name:<16} {detail}")

        print("\n  运行命令：")
        commands = [
            "pytest 04_pytest_style.py -v",
            "pytest 04_pytest_style.py -v --cov=. --cov-report=term-missing",
            "pytest 04_pytest_style.py -k 'param' -v",
            "pytest 04_pytest_style.py --lf -v",
            "pytest 04_pytest_style.py -x -q",
            "pytest 04_pytest_style.py --collect-only -q    # 只列出用例不执行",
        ]
        for cmd in commands:
            print(f"    {cmd}")

        print("\n  fixture 层级关系：")
        print("    conftest.py (session)      ← 全局，最慢的放这")
        print("      └── class scope          ← 类内共享")
        print("            └── function scope ← 默认，每个用例一次")
        print()
        print("  如果 pytest 不可用，直接运行本文件会自动进入降级演示模式。")
        print("=" * 78)
        return 0

    return demo_without_pytest()


if __name__ == "__main__":
    sys.exit(main())
