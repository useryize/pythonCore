"""
================================================================================
 03_unittest_basics.py —— unittest 框架完整演示
================================================================================

【演示的语法点】
  1. import unittest / 类继承 unittest.TestCase —— 唯一的必需动作
  2. setUp / tearDown      : 每个 test_ 方法前后各执行一次
  3. setUpClass/tearDownClass : 整个类只执行一次（类方法，需 @classmethod）
  4. 6 种断言方法         : assertEqual/NotEqual/True/False/In/IsInstance
  5. subTest()            : 子测试，一次失败不中断整组循环
  6. assertRaises()       : 异常断言，推荐用作上下文管理器
  7. @unittest.skip / skipIf / skipUnless : 跳过用例
  8. TestLoader 排序规则  : test_<字母> 优先，其余排序后执行
  9. TextTestRunner(verbosity=2) : 详细模式输出
 10. setUpClass 级共享资源 + cls. 类属性传递
 11. 手动添加测试方法     : 通过元组传给 addTest
 12. unittest.main()      : 入口；此处用自定义 TestRunner 替代以便观察

【预期输出摘要】
  - TextTestRunner 逐条打印每个用例的 ... ok / s skip / F fail
  - 最终 "Ran N tests in 0.00Xs" 与 OK / FAILED 汇总
  - 子测试失败时会额外打印每个子用例的明细

【要点提示】
  · 测试方法必须以 test 开头，否则不会被收集（这是 unittest 的硬约定）
  · 测试之间绝不能有顺序依赖 —— 每个 test 都要能独立跑
  · setUp 里不要做重活，放到 setUpClass 里做一次
"""

import io
import sys
import unittest
from contextlib import redirect_stderr, redirect_stdout


# ==============================================================================
# 一、被测对象（把「业务代码」和「测试代码」分开，是工程基本功）
# ==============================================================================
class StringCalculator:
    """字符串计算器：业务代码不带任何测试逻辑。"""

    def __init__(self) -> None:
        self._memory: dict[str, str] = {}

    def add(self, a: str, b: str) -> str:
        """拼接两个字符串。"""
        if not isinstance(a, str) or not isinstance(b, str):
            raise TypeError("参数必须是 str")
        return a + b

    def multiply(self, s: str, times: int) -> str:
    # ===== 语法解析 =====
    # 冒号缩进的代码块属于 def；缩进结束即函数体结束
        """字符串重复 times 次。"""
        if times < 0:
            raise ValueError("times 不能为负数")
        return s * times

    def remember(self, key: str, value: str) -> None:
        """写入缓存。"""
        self._memory[key] = value

    def recall(self, key: str) -> str | None:
        """读取缓存，miss 返回 None。"""
        return self._memory.get(key)

    @staticmethod
    def reverse(s: str) -> str:
        """staticmethod：无需实例即可调用，适合纯函数式工具方法。"""
        return s[::-1]

    @classmethod
    def version(cls) -> str:
        """classmethod 接收类本身（不是实例），适合工厂方法。"""
        return f"{cls.__name__}/1.0.0"


# ==============================================================================
# 二、基础用例：6 种断言 + setUp/tearDown
# ==============================================================================
class TestStringCalculatorBasics(unittest.TestCase):
    """最基础的用例结构：setUp 建对象 → 测方法 → tearDown 清理。"""

    # ===== 语法解析 =====
    # setUp / tearDown 是 TestCase 定义的「钩子(hook)」，由框架在每个
    # test_ 方法前后自动回调，你只管重写（override）它们。
    # 注意：签名必须是 (self)，不能加额外位置参数。

    def setUp(self) -> None:
        """每个测试方法执行前调用 —— 用于准备干净的测试环境。"""
        # 全新实例，保证用例之间零状态污染
        self.calc = StringCalculator()
        self.call_count = 0

    def tearDown(self) -> None:
        """每个测试方法执行后调用 —— 用于释放资源。"""
        # 真实项目里这里是 db.close() / file.close()
        self.calc = None       # type: ignore[assignment]
        self.call_count = 0

    # --- 6 种核心断言 -------------------------------------------------------
    def test_1_assert_equal(self) -> None:
        """assertEqual(a, b)：相等断言。失败时会自动 diff 出差异。"""
        self.call_count += 1
        self.assertEqual("ab", self.calc.add("a", "b"))

    def test_2_assert_not_equal(self) -> None:
        """assertNotEqual(a, b)：不等断言。"""
        self.assertNotEqual("abc", self.calc.add("a", "b"))

    def test_3_assert_true(self) -> None:
        """assertTrue(x) / assertFalse(x)：真值断言。

        为什么不用 assertEqual(x, True)？
          因为可能 x 是 1 或 "yes"，语义上都为真但不相等。语义更准确。
        """
        self.assertTrue(self.calc.add("a", "b"))
        self.assertFalse(self.calc.recall("missing"))
        # 消息参数：断言失败时打印，便于定位问题
        self.assertTrue(len(self.calc.add("x", "y")) == 2, "拼接结果长度应为 2")

    def test_4_assert_in(self) -> None:
        """assertIn / assertNotIn：容器成员断言（也适用于字符串子串）。"""
        self.calc.remember("greet", "hello world")
        self.assertIn("greet", self.calc._memory)   # key 在字典里
        self.assertNotIn("bye", self.calc._memory)
        self.assertIn("world", self.calc.recall("greet") or "")  # 子串检查

    def test_5_assert_is_instance(self) -> None:
        """assertIsInstance(obj, cls)：类型断言。"""
        self.assertIsInstance(self.calc, StringCalculator)
        self.assertIsInstance(self.calc.add("a", "b"), str)
        # assertIsNone / assertIsNotNone 同样常用
        self.assertIsNone(self.calc.recall("none"))

    # --- assertRaises：异常断言 ---------------------------------------------
    def test_6_assert_raises(self) -> None:
        """assertRaises 用作上下文管理器是推荐写法。

        为什么这样好？而不是 assertRaises(ValueError, func, arg)：
          - 可以断言异常对象的内容（如 .args / 自定义属性）
          - 失败时能显示出错的那一行代码
        """
        with self.assertRaises(ValueError) as ctx:
            self.calc.multiply("a", -1)
        # cm.exception 是被抛出的异常实例，可以进一步断言
        self.assertIn("不能为负数", str(ctx.exception))

        # TypeError 的分支
        with self.assertRaises(TypeError):
            self.calc.add("a", 1)     # type: ignore[arg-type]

    def test_7_assert_methods_equality(self) -> None:
        """assertIs：判断「是否同一个对象」，与 == 的区别是走 is 而非 __eq__。"""
        a = ["x"]
        b = a
        c = list(a)
        self.assertIs(a, b)        # 同一对象
        self.assertIsNot(a, c)     # 内容相同但不同对象
        self.assertEqual(a, c)     # 值相等

    def test_8_zzz_always_runs_last(self) -> None:
        """方法名以 test_zzz 开头 —— 排序规则让它最后执行。"""
        self.assertEqual("1.0.0", StringCalculator.version()[-5:])
        self.assertEqual("cba", StringCalculator.reverse("abc"))


# ==============================================================================
# 三、subTest 子测试：一组数据循环断言，失败不中断
# ==============================================================================
class TestWithSubTest(unittest.TestCase):
    """subTest 的价值：把 N 组参数当成 N 个独立用例报告。"""

    def test_table_driven(self) -> None:
        """表驱动测试：每一行用 with self.subTest(...) 包裹。

        对比错误做法：
            for case in cases:
                self.assertEqual(...)      # 第一个失败就整个用例失败，
                                          # 看不到后面还错了几条
        """
        cases: list[tuple[str, str, str, str]] = [
            # (说明, 输入a, 输入b, 期望)
            ("普通拼接", "a", "b", "ab"),
            ("空串拼接", "", "", ""),
            ("含空格", "he", "llo", "hello"),
            # ↓ 故意放一条会失败的，看 subTest 的报告效果
            ("含中文", "你", "好", "N好"),
        ]
        calc = StringCalculator()
        for desc, a, b, expected in cases:
            # subTest 把 desc 作为子用例标识，失败报告会分组显示
            with self.subTest(desc=desc):
                self.assertEqual(expected, calc.add(a, b))

    def test_range_boundaries(self) -> None:
        """边界值测试的经典姿势：负数、零、边界。"""
        calc = StringCalculator()
        for times in (-2, 0, 1, 10):
            with self.subTest(times=times):
                result = calc.multiply("x", times)
                self.assertEqual("x" * times, result)
                # 只对正数断言长度，负数要先处理（但 times<0 会抛异常）
                if times >= 0:
                    self.assertEqual(times, len(result))


# ==============================================================================
# 四、setUpClass / tearDownClass：类级别一次性准备
# ==============================================================================
class TestWithClassLevelSetup(unittest.TestCase):
    """演示类级资源：昂贵初始化做一次，所有用例共享。"""

    # ===== 语法解析 =====
    # setUpClass / tearDownClass 必须是 @classmethod，因为框架是以「类」为单位
    # 调用的（unittest.TestCase.setUpClass(cls)），必须接收 cls 参数。

    accounts: list[StringCalculator] = []
    db_ready: bool = False

    @classmethod
    def setUpClass(cls) -> None:
        """整个类的第一个测试执行前，只跑一次。"""
        # 真实场景：建连接池、加载模型、读配置文件（慢操作）
        cls.accounts = [StringCalculator() for _ in range(3)]
        cls.db_ready = True
        # 打印到 stdout 会被测试报告吞掉，用 stderr 更安全
        print("[setUpClass] 已创建 3 个 StringCalculator（模拟建数据库连接）", file=sys.stderr)

    @classmethod
    def tearDownClass(cls) -> None:
        """整个类的最后一个测试执行后，只跑一次。"""
        # 真实场景：关闭连接、清理临时文件
        cls.accounts.clear()
        cls.db_ready = False
        print("[tearDownClass] 已释放全部资源", file=sys.stderr)

    def test_a_shared_state_available(self) -> None:
        """所有用例都能访问 setUpClass 里创建的对象。"""
        self.assertTrue(self.db_ready)
        self.assertEqual(3, len(self.accounts))

    def test_b_mutating_shared_state(self) -> None:
        """⚠ 反面教材：修改共享状态。

        TestLoader 按字母顺序跑用例，所以 test_a 先跑完，再跑 test_b。
        如果 test_b 依赖 test_a 的副作用，单独跑 test_b 就会失败 ——
        这就是「测试间顺序依赖」这种反模式的典型症状。
        """
        self.accounts[0].remember("k", "v")
        self.assertEqual("v", self.accounts[0].recall("k"))
        # 若单独运行本用例（-k test_b），前面 setUpClass 仍会跑，所以依然通过；
        # 但反过来若 test_b 依赖 test_a 写入的数据，单独跑就会红。

    def test_c_independent(self) -> None:
        """正确做法：自己准备自己的数据。"""
        calc = StringCalculator()
        calc.remember("own", "data")
        self.assertEqual("data", calc.recall("own"))
        self.assertIsNone(calc.recall("k"))     # 不受其他用例污染


# ==============================================================================
# 五、跳过用例的 3 种装饰器
# ==============================================================================
class TestSkipDecorators(unittest.TestCase):
    """演示跳过机制：让已知失败/环境缺失的用例优雅跳过而非报错。"""

    def setUp(self) -> None:
        self.calc = StringCalculator()

    # ===== 语法解析 =====
    # @unittest.skip("原因")  : 无条件跳过。原因必填，会显示在报告里。

    @unittest.skip("这个功能正在重构中，暂停验证")
    def test_skipped_always(self) -> None:
        """无条件跳过 —— 报告里显示 s（skip）。"""
        self.assertEqual("不可能通过", self.calc.add("a", "a"))

    # @unittest.skipIf(cond, "原因") : 条件为 True 时跳过。
    #   工程用途：平台差异（Windows 没有 fcntl）、可选依赖缺失
    @unittest.skipIf(sys.platform == "win32", "仅在 Linux/macOS 上验证")
    def test_skip_on_windows(self) -> None:
        """当前平台是 Windows -> 会被跳过。"""
        self.assertTrue(os_name_is_posix())

    @unittest.skipUnless(
        hasattr(unittest, "IsolatedAsyncioTestCase"), "需要 Python 3.8+"
    )
    def test_skip_unless(self) -> None:
        """条件不成立才跳过 —— 这里条件成立，所以正常执行。"""
        self.assertTrue(hasattr(unittest, "IsolatedAsyncioTestCase"))

    @unittest.expectedFailure
    def test_expected_failure(self) -> None:
        """预期失败：已知有 bug，用来「记录」而不是「隐藏」问题。

        报告里显示 x（expected failure）。修复 bug 后应把该装饰器删掉。
        """
        self.assertEqual("A", "B")     # 故意失败

    def test_normal_still_runs(self) -> None:
        """跳过的用例不会影响其他用例正常执行。"""
        self.assertEqual("ab", self.calc.add("a", "b"))


def os_name_is_posix() -> bool:
    """小工具：判断是否为 POSIX 系统。"""
    return sys.platform != "win32"


# ==============================================================================
# 六、手动组装测试套件 + 自定义 Runner
# ==============================================================================
def build_suite() -> unittest.TestSuite:
    """手动把多个 TestCase 类塞进一个 TestSuite，并添加额外的动态用例。"""
    loader = unittest.TestLoader()

    # loadTestsFromTestCase：把一个类的所有 test_ 方法收进来
    suite = unittest.TestSuite([
        loader.loadTestsFromTestCase(TestStringCalculatorBasics),
        loader.loadTestsFromTestCase(TestWithSubTest),
        loader.loadTestsFromTestCase(TestWithClassLevelSetup),
        loader.loadTestsFromTestCase(TestSkipDecorators),
    ])

    # 动态添加：把一个普通函数包装成测试用例
    #   FunctionTestCase 可以包装任意 callable，适合给遗留代码补测试
    def test_dynamic_addition() -> None:
        """动态添加的用例：无需定义类。"""
        calc = StringCalculator()
        assert calc.add("py", "thon") == "python"    # 裸 assert（pytest 风格）

    suite.addTest(unittest.FunctionTestCase(test_dynamic_addition))
    return suite


def run_with_capture(suite: unittest.TestSuite) -> tuple[unittest.TestResult, str]:
    """把测试输出重定向到内存缓冲区，方便在脚本里展示而不刷屏。"""
    buffer = io.StringIO()
    with redirect_stdout(buffer), redirect_stderr(buffer):
        runner = unittest.TextTestRunner(
            stream=buffer,          # 结果写到 buffer 而不是终端
            verbosity=2,            # 2 = 每个用例都打印一行明细
            descriptions=True,      # 打印测试类的 docstring
        )
        result = runner.run(suite)
    return result, buffer.getvalue()


def show_result_summary(result: unittest.TestResult) -> None:
    """解析 TestResult 对象，输出结构化汇总。"""
    passed = (
        result.testsRun
        - len(result.failures)
        - len(result.errors)
        - len(result.skipped)
    )
    print(f"\n执行总数 run      : {result.testsRun}")
    print(f"成功 success      : {passed}")
    print(f"跳过 skipped     : {len(result.skipped)}")
    print(f"失败 failures    : {len(result.failures)}")
    print(f"错误 errors      : {len(result.errors)}")
    print(f"预期失败 xfail   : {len(result.expectedFailures)}")
    print(f"非预期通过 xpass : {len(result.unexpectedSuccesses)}")
    print(f"最终是否成功      : {result.wasSuccessful()}")

    # failures / errors 是 (test, traceback_str) 元组列表
    for case, trace in result.failures:
        print(f"\n  [FAIL] {case}")
        print("         " + trace.strip().splitlines()[-1])

    for case, reason in result.skipped:
        print(f"\n  [SKIP] {case}")
        print(f"         原因：{reason}")


# ==============================================================================
# 七、主流程
# ==============================================================================
def main() -> None:
    """主流程：构建套件 -> 执行 -> 展示报告 -> 打印用法说明。"""
    print("=" * 78)
    print(" 03. unittest 完整演示")
    print("=" * 78)

    print("\n[1] TextTestRunner(verbosity=2) 详细报告")
    print("-" * 78)
    suite = build_suite()
    # 关键：先看用例排序（TestLoader.sortTestMethodsUsing 的效果）
    names = unittest.TestLoader().getTestCaseNames(TestStringCalculatorBasics)
    print(f"  TestLoader 排序后的执行顺序：\n    {names}\n")

    result, output = run_with_capture(suite)
    print(output)

    print("\n[2] TestResult 结构化汇总")
    print("-" * 78)
    show_result_summary(result)

    print("\n[3] unittest 常用 CLI 用法")
    print("-" * 78)
    commands = [
        ("python -m unittest", "自动发现并运行当前目录下所有测试"),
        ("python -m unittest -v", "详细模式，等价于 verbosity=2"),
        ("python -m unittest tests.test_a", "运行指定模块"),
        ("python -m unittest tests.test_a.TestCaseA", "运行指定类的所有用例"),
        ("python -m unittest tests.test_a.TestCaseA.test_x", "运行单个方法"),
        ("python -m unittest discover -s tests -p 'test_*.py'", "自定义发现规则"),
        ("python -m unittest -k email", "按名字过滤（3.7+）"),
    ]
    for cmd, desc in commands:
        print(f"  {cmd:<58} {desc}")

    print("\n[4] pytest 与 unittest 的关系")
    print("-" * 78)
    print("  pytest 能直接运行 unittest.TestCase 写的用例（零成本接入）")
    print("  但 pytest 的 fixture / parametrize / monkeypatch 是它独有的")
    print("  新项目建议 pytest；老项目 unittest 可平滑共存")

    print("\n" + "=" * 78)
    print(" 测试金字塔：单元测试多且快 -> 集成测试少而慢 -> 端到端测试最少")
    print("=" * 78)


if __name__ == "__main__":
    main()
