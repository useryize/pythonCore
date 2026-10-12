"""
================================================================================
 myutils/text_tools.py  ——  文本处理工具模块
================================================================================

【模块职责】
 纯函数式文本工具集合，演示：
 - 多个独立函数的模块组织方式
 - 字符串方法组合（chain method）
 - 正则表达式 re 的基本使用
 - 列表推导式与生成器表达式
 - 文档字符串 docstring 作为模块级说明

【设计原则】
 文本处理函数应当是"纯函数"：输入相同则输出相同，不依赖外部状态。
 这让它们天然可被lru_cache 缓存，也便于单元测试。
"""

from __future__ import annotations

import re
from collections.abc import Iterable

# 预编译正则：在模块导入时编译一次，后续多次复用。
# 为什么预编译？re.compile 返回带缓存的模式对象，手动预编译能明确表达意图。
_WHITESPACE_RE = re.compile(r"\s+")
_NON_WORD_RE = re.compile(r"[^\w\s]", re.UNICODE)


# ===== 语法解析 =====
# 【1】去空白 / 规范化
def normalize_whitespace(text: str) -> str:
    """把连续空白压缩成一个空格，并去掉首尾空白。"""
    # re.sub 的第三个参数可以是函数或替换字符串；这里用 lambda 返回匹配内容。
    # 注意 r"\s+" 是原始字符串：反斜杠无需转义，避免 Windows 路径里的 \t \n 被误解。
    return _WHITESPACE_RE.sub(" ", text).strip()


def remove_punctuation(text: str) -> str:
    """去除标点符号，保留中英文单词与空白。"""
    return _NON_WORD_RE.sub("", text)


def word_count(text: str) -> dict[str, int]:
    """统计词频，返回 {词: 次数}。"""
    words = _NON_WORD_RE.sub(" ", text.lower()).split()
    counts: dict[str, int] = {}
    for w in words:
        # dict.get(k, 0) 是计数的惯用写法，比"判断 key 是否存在"更简洁
        counts[w] = counts.get(w, 0) + 1
    return counts


# ===== 语法解析 =====
# 【2】清洗流水线：把多个纯函数组合起来
#   设计意图：单一职责 + 可组合 —— 每个函数只做一件事，管道负责串联。
def clean_text(text: str) -> str:
    """完整清洗流程：去标点 → 压缩空白 → 去首尾。"""
    return normalize_whitespace(remove_punctuation(text))


# ===== 语法解析 =====
# 【3】字符串验证类函数
def is_palindrome(text: str) -> bool:
    """判断是否为回文（忽略大小写、空格、标点）。"""
    # 只保留字母数字：''.join(filter(...)) 是过滤字符的经典写法
    chars = "".join(c for c in text.lower() if c.isalnum())
    # 切片反转：s[::-1]，步长为 -1 表示倒序遍历
    return chars == chars[::-1]


def count_vowels(text: str) -> dict[str, int]:
    """统计元音字母数量（不区分大小写）。"""
    vowels = "aeiou"
    counts = {v: 0 for v in vowels}        # 字典推导式：先建全零骨架
    for char in text.lower():
        if char in vowels:
            counts[char] += 1
    return counts


def truncate(text: str, max_length: int, suffix: str = "…") -> str:
    """截断过长文本。max_length 含 suffix 长度。"""
    if len(text) <= max_length:
        return text
    if max_length <= len(suffix):
        return suffix[:max_length]        # 边界：suffix 比 max_length 还长
    return text[: max_length - len(suffix)] + suffix


# ===== 语法解析 =====
# 【4】camelCase ↔ snake_case 互转（真实工程常用）
def camel_to_snake(name: str) -> str:
    """驼峰转下划线：getUserName → get_user_name"""
    # 正则插入分隔符：先处理"大写字母前不是开头"的情况
    s1 = re.sub(r"(.)([A-Z][a-z]+)", r"\1_\2", name)
    # 再处理"连续大写"的边界：HTTPServer → HTTP_Server
    s2 = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", s1)
    return s2.lower()


def snake_to_camel(name: str) -> str:
    """下划线转驼峰：get_user_name → getUserName（首字母保持小写）。"""
    parts = name.split("_")
    # 第一个词保持原样，其余每个词首字母大写：word.capitalize()
    return parts[0] + "".join(p.capitalize() for p in parts[1:])


# ===== 语法解析 =====
# 【5】批量文本处理：演示 Iterable + 生成器
def title_case_all(texts: Iterable[str]) -> list[str]:
    """把一组文本转为标题格式，返回列表。"""
    # 列表推导式比 for + append 更快更简洁；此处做的是"每项应用一次 clean_text"
    return [clean_text(t).title() for t in texts]


# 直接运行时的自测
if __name__ == "__main__":
    print("直接运行 text_tools.py：")
    print(f"  normalize_whitespace('  a   b  ') = {normalize_whitespace('  a   b  ')!r}")
    print(f"  remove_punctuation('你好, world!') = {remove_punctuation('你好, world!')!r}")
    print(f"  clean_text('  Hello,  World!! ') = {clean_text('  Hello,  World!! ')!r}")
    print(f"  word_count('a b a c') = {word_count('a b a c')}")
    print(f"  is_palindrome('A man a plan a canal Panama') = "
          f"{is_palindrome('A man a plan a canal Panama')}")
    print(f"  count_vowels('Hello World') = {count_vowels('Hello World')}")
    print(f"  truncate('abcdefghij', 5) = {truncate('abcdefghij', 5)!r}")
    print(f"  camel_to_snake('getUserName') = {camel_to_snake('getUserName')}")
    print(f"  camel_to_snake('HTTPServer') = {camel_to_snake('HTTPServer')}")
    print(f"  snake_to_camel('get_user_name') = {snake_to_camel('get_user_name')}")
    print(f"  title_case_all = {title_case_all(['hello world', 'python core'])}")