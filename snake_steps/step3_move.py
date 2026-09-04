# -*- coding: utf-8 -*-
# ============================================================
# 第3步：让方块自动向右移动
# 相比第2步新增：方向变量 direction、move() 移动函数、
#   draw() 重画函数、game_loop() 主循环、after() 定时器
# 运行后看到：绿色方块自动向右移动，撞墙后从另一边穿出来
# ============================================================

import tkinter as tk

CELL = 20
COLS = 20   # 横向格子数
ROWS = 20   # 纵向格子数

root = tk.Tk()
root.title("贪吃蛇 - 第3步")
root.resizable(False, False)

canvas = tk.Canvas(root, width=COLS * CELL, height=ROWS * CELL, bg="#1a1a2e")
canvas.pack()

# 蛇头位置
head_x, head_y = 10, 10

# 【语法】方向用元组 (x变化量, y变化量) 表示。
# (1, 0) 表示 x 增加 1、y 不变 → 向右移动。
direction = (1, 0)

speed = 150  # 移动速度：每 150 毫秒移动一次（数字越小越快）


# 【语法】def 函数名(): 定义一个函数。把一段代码包起来，起个名字，
# 后面可以反复调用，不用重复写。
def move():
    """移动方块：根据方向改变坐标，然后重新画画面"""
    # 【语法】global 变量名：在函数里修改全局变量时必须声明，
    # 否则 Python 会把它当成局部变量。
    global head_x, head_y

    # 【语法】direction[0] 取元组的第 0 个元素（x 变化量），
    # direction[1] 取第 1 个元素（y 变化量）。
    head_x += direction[0]
    head_y += direction[1]

    # 穿墙效果：超出边界后从另一边出来。
    # 【语法】%= 是"取模赋值"，head_x %= COLS 等价于 head_x = head_x % COLS。
    # Python 里 -1 % 20 = 19，所以从左边出去会从右边进来。
    head_x %= COLS
    head_y %= ROWS

    draw()  # 移动后重新画画面


def draw():
    """清空画布，重新画方块"""
    # 【语法】canvas.delete("all") 删除画布上所有内容。
    # 每帧都先清空再重画，画面才会更新（就像翻页动画）。
    canvas.delete("all")
    canvas.create_rectangle(
        head_x * CELL + 1, head_y * CELL + 1,
        (head_x + 1) * CELL - 1, (head_y + 1) * CELL - 1,
        fill="#2ecc71", outline=""
    )


def game_loop():
    """游戏主循环：移动一次，然后安排 speed 毫秒后再调用自己"""
    move()
    # 【语法】root.after(毫秒数, 函数)：定时器，等这么多毫秒后调用这个函数。
    # 这里调用自己，就形成了"无限循环"，每隔 speed 毫秒移动一次。
    root.after(speed, game_loop)


draw()       # 先画一次初始画面
game_loop()  # 开始游戏循环
root.mainloop()
