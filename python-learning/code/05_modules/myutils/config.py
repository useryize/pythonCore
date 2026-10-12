"""
================================================================================
 myutils/config.py  ——  配置管理模块
================================================================================

【模块职责】
 集中管理默认配置，提供分层合并与读取能力。本模块演示：
 - 模块级常量（ALL_CAPS 命名约定）
 - 模块级可变配置的"私有化"封装（用函数代替裸变量，避免被误改）
 - 函数作为模块的公开接口（config.get / config.update / config.reset）
 - 字典推导式与嵌套字典

【依赖】
 本模块【不依赖任何其他模块】，是包里最底层的叶子模块。
 这一点在包设计中很重要：依赖越少，越不容易产生循环导入。
"""

from __future__ import annotations

# 模块级常量：Python 约定全大写 + 下划线，表示"这是配置常量，不应被重新赋值"
DEFAULT_CONFIG: dict[str, object] = {
    "app_name": "myutils-demo",
    "version": "1.0.0",
    "debug": False,
    "log_level": "INFO",
    "database": {
        "host": "127.0.0.1",
        "port": 5432,
        "name": "testdb",
    },
}

# ★ 深拷贝一份作为"运行时状态"。
# 为什么用 copy.deepcopy 而不是 dict(...)：
#   dict(DEFAULT_CONFIG) 是【浅拷贝】，内层的 "database" 字典仍是同一个对象，
#   修改它会污染 DEFAULT_CONFIG —— 这就是 01 学过的"可变默认参数 BUG"的模块版翻版。
import copy as _copy

_settings: dict[str, object] = _copy.deepcopy(DEFAULT_CONFIG)


# ===== 语法解析 =====
# 【模块的公开接口】
#   约定：以下划线开头的名字（如 _settings、_copy）是"私有"，外部不应依赖；
#         不带下划线的名字（get/update/reset/DEFAULT_CONFIG）是公开 API。
#   设计意图：Python 没有真正的 private，靠命名约定 + __all__ 表达可见性。
def get(key: str, default: object = None) -> object:
    """读取配置项。支持 "database.host" 这样的点号路径访问嵌套配置。"""
    parts = key.split(".")           # "database.host" → ["database", "host"]
    current: object = _settings
    for part in parts:
        if isinstance(current, dict) and part in current:
            current = current[part]   # 逐层下钻
        else:
            return default            # 任一层失败 → 返回默认值（宽容策略）
    return current


def update(**kwargs: object) -> dict[str, object]:
    """更新配置项，返回更新后的完整配置（链式调用友好）。"""
    _settings.update(kwargs)          # dict.update 是原地修改
    return _settings


def reset() -> None:
    """重置为默认配置。测试用例之间常用。"""
    global _settings                   # 修改模块级名字必须写 global
    _settings = _copy.deepcopy(DEFAULT_CONFIG)


def as_dict() -> dict[str, object]:
    """返回配置的深拷贝，防止外部直接改内部状态。"""
    return _copy.deepcopy(_settings)


# ===== 语法解析 =====
# 【模块信息】
#   __name__ 在被直接运行时是 "__main__"，被导入时是包名的一部分（"myutils.config"）。
#   这一行是"导入守卫"的标准写法：只有直接运行时才执行下面的代码。
if __name__ == "__main__":
    # 直接运行本文件时的自测入口
    print("直接运行 config.py：")
    print(f"  默认 app_name = {get('app_name')}")
    print(f"  嵌套 database.host = {get('database.host')}")
    print(f"  不存在的路径返回默认值 = {get('a.b.c', '未找到')}")
    update(debug=True)
    print(f"  更新后 debug = {get('debug')}")
    reset()
    print(f"  重置后 debug = {get('debug')}")