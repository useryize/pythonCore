# -*- coding: utf-8 -*-
# ==================================================================
# 【step5】pydantic —— 给数据立规矩
# Agent 开发里，大模型经常要返回结构化数据（比如"帮我订票" → 返回 {日期, 班次, 座位}）。
# 但模型是"概率生成"的，偶尔会漏字段、给错类型。pydantic 就是数据校验器：
# 先定义好规则，数据一进来就检查，不对就报错，绝不带病运行。
# ==================================================================

# 【语法】from 模块 import 类
# BaseModel 是所有数据模型的父类；Field 用来给字段加额外约束。
from pydantic import BaseModel, Field


# 【语法】定义一个数据模型：就像画一张"字段表格"。
# 类名用大驼峰；每个属性 = 一个字段，冒号后面写类型（int / str / list...）。
class StudyPlan(BaseModel):
    topic: str                      # 必填，必须是字符串
    days: int = Field(ge=1, le=30)  # 必填，整数，且必须在 1~30 之间（ge=大于等于, le=小于等于）
    skills: list[str] = []          # 可选，默认空列表，每个元素必须是字符串


# 【场景】模拟大模型返回的 JSON 字符串（step3 里你亲眼见过模型怎么返回）。
llm_return = '{"topic": "FastAPI", "days": 7, "skills": ["路由", "Pydantic", "SSE"]}'

# 【语法】model_validate_json() 解析 JSON 字符串并自动校验。
# 合法 → 得到一个 StudyPlan 对象；不合法 → 抛异常，程序立刻告诉你哪里错了。
plan = StudyPlan.model_validate_json(llm_return)

# 【语法】访问对象的字段：对象.字段名（和字典 plan["topic"] 很像，但更安全、有类型提示）。
print("主题:", plan.topic)
print("天数:", plan.days)
print("技能:", plan.skills)

# 【练习】把下面这行取消注释再运行，看看 pydantic 怎么报错：
#   bad = StudyPlan.model_validate_json('{"topic": "FastAPI", "days": 999}')
# 你会看到 days 字段违反约束的详细报错信息——这就是"校验"在起作用。

# 【进阶 · 真实场景】让模型输出 JSON 的标准姿势：
#   1. 在 system 提示里明确要求："只输出 JSON，不要其他文字"
#   2. 收到回复后，用 model_validate_json() 校验
#   3. 校验通过 → 数据就是"可信的"，可以直接用于后续逻辑（比如订票、查天气）
# Agent 的"工具调用"本质上就是这套：模型说想调什么工具、传什么参数，我们校验后执行。
