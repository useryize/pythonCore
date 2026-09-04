# -*- coding: utf-8 -*-
# ============================================================
# 第5步：方块变成长蛇（多节身体连起来）
# 相比第4步新增：snake 列表存多节身体坐标、
#   移动时 insert(0, 新头) + pop() 删尾巴、
#   draw() 里遍历列表画每一节（头亮绿、身体深绿）
# 运行后看到：一条 3 节的绿色蛇在移动，头是亮绿，身体是深绿
# ============================================================

import tkinter as tk

CELL = 20
COLS = 20
ROWS = 20

root = tk.Tk()
root.title("贪吃蛇 - 第5步")
root.resizable(False, False)

canvas = tk.Canvas(root, width=COLS * CELL, height=ROWS * CELL, bg="#1a1a2e")
canvas.pack()

# 【语法】列表（list）：用方括号 [] 包起来，元素之间用逗号，有序排列。
# 这里每个元素是一个元组 (x, y)，表示蛇的一节身体在哪个格子。
# 列表的第 0 个元素是蛇头，最后一个元素是蛇尾巴。
# 初始蛇有 3 节，横向排在第 10 行。
snake = [(10, 10), (9, 10), (8, 10)]

direction = (1, 0)
next_direction = (1, 0)
speed = 150


def on_key(event):
    global next_direction
    key = event.keysym
    if key in ("Left", "a") and direction != (1, 0):
        next_direction = (-1, 0)
    elif key in ("Right", "d") and direction != (-1, 0):
        next_direction = (1, 0)
    elif key in ("Up", "w") and direction != (0, 1):
        next_direction = (0, -1)
    elif key in ("Down", "s") and direction != (0, -1):
        next_direction = (0, 1)


def move():
    global direction
    direction = next_direction

    # 【语法】snake[0] 取列表第 0 个元素（蛇头）。
    # head_x, head_y = ... 是"序列解包"：把元组的两个值分别赋给两个变量。
    head_x, head_y = snake[0]

    # 计算新蛇头位置
    new_head = (head_x + direction[0], head_y + direction[1])
    # 穿墙
    new_head = (new_head[0] % COLS, new_head[1] % ROWS)

    # 【语法】列表.insert(索引, 值)：在指定索引位置插入一个值，后面的元素往后挪。
    # insert(0, new_head) 就是在列表最前面插入新蛇头。
    snake.insert(0, new_head)

    # 【语法】列表.pop()：删除并返回列表的最后一个元素（蛇尾巴）。
    # 前面加了新头，后面删尾巴，蛇整体向前移动但长度不变。
    snake.pop()

    draw()


def draw():
    canvas.delete("all")

    # 【语法】for i, (x, y) in enumerate(snake):
    # enumerate(列表) 同时取出每个元素的"索引 i"和"值 (x,y)"。
    # i 是第几节（0 是头），(x, y) 是这一节的坐标。
    for i, (x, y) in enumerate(snake):
        # 【语法】条件表达式（三元表达式）：值1 if 条件 else 值2。
        # 如果 i == 0（是蛇头）就用亮绿色，否则用深绿色。
        color = "#2ecc71" if i == 0 else "#27ae60"

        canvas.create_rectangle(
            x * CELL + 1, y * CELL + 1,
            (x + 1) * CELL - 1, (y + 1) * CELL - 1,
            fill=color, outline=""
        )


def game_loop():
    move()
    root.after(speed, game_loop)


root.bind("<Key>", on_key)
draw()
game_loop()
root.mainloop()
