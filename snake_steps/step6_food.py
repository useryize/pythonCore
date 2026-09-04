# -*- coding: utf-8 -*-
# ============================================================
# 第6步：放食物，吃到食物变长、加分
# 相比第5步新增：import random、place_food() 随机放食物、
#   画红色食物（create_oval）、吃到食物时不 pop 尾巴（蛇变长）、
#   顶部分数栏（Label + StringVar）
# 运行后看到：红色食物随机出现，蛇吃到后变长、顶部分数增加
# ============================================================

import tkinter as tk
# 【语法】导入 random 模块，用来生成随机数（随机放食物的位置）。
import random

CELL = 20
COLS = 20
ROWS = 20

root = tk.Tk()
root.title("贪吃蛇 - 第6步")
root.resizable(False, False)

# ---------- 顶部分数栏 ----------
# 【语法】tk.StringVar(value="...") 创建一个"可变字符串对象"。
# 它和普通字符串的区别是：改它的值，界面上绑定它的文字会自动更新。
score_var = tk.StringVar(value="分数: 0")
# Label 是文字标签，textvariable= 绑定可变字符串，分数变了自动刷新。
tk.Label(root, textvariable=score_var, font=("Arial", 14, "bold"),
         fg="#f1c40f", bg="#1a1a2e").pack(fill="x", pady=4)

canvas = tk.Canvas(root, width=COLS * CELL, height=ROWS * CELL,
                   bg="#1a1a2e", highlightthickness=0)
canvas.pack()
root.configure(bg="#1a1a2e")

snake = [(10, 10), (9, 10), (8, 10)]
direction = (1, 0)
next_direction = (1, 0)
speed = 150
score = 0       # 当前分数
food = (0, 0)   # 食物的格子坐标


def place_food():
    """随机放一个食物，确保食物不会出现在蛇身上"""
    # 【语法】global food：在函数里修改全局变量 food 必须声明。
    global food
    # 【语法】while True: 无限循环，靠 return 退出。
    # 不断随机选位置，直到选到一个不在蛇身上的格子。
    while True:
        # 【语法】random.randint(a, b)：生成 a 到 b 之间的随机整数（包含 a 和 b）。
        x = random.randint(0, COLS - 1)
        y = random.randint(0, ROWS - 1)
        # 【语法】in 成员运算符：判断 (x, y) 是否在 snake 列表里。
        if (x, y) not in snake:
            food = (x, y)
            return  # 【语法】return 退出函数（这里没有返回值，只是为了退出循环）


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
    global direction, score
    direction = next_direction
    head_x, head_y = snake[0]
    new_head = (head_x + direction[0], head_y + direction[1])
    new_head = (new_head[0] % COLS, new_head[1] % ROWS)
    snake.insert(0, new_head)

    # 判断是否吃到食物：新蛇头位置和食物位置一样
    if new_head == food:
        # 吃到食物：加分
        # 【语法】+= 加法赋值，score += 10 等价于 score = score + 10。
        score += 10
        # 【语法】% 字符串格式化：%d 是整数占位符，把 score 填进去。
        score_var.set("分数: %d" % score)
        # 重新放一个新食物
        place_food()
        # 注意：吃到食物时不调用 snake.pop()，尾巴不删，蛇就变长了一节！
    else:
        # 没吃到：删尾巴，长度不变
        snake.pop()

    draw()


def draw():
    canvas.delete("all")

    # ---------- 画食物（红色圆形） ----------
    fx, fy = food  # 解包食物坐标
    # 【语法】canvas.create_oval(x1, y1, x2, y2, ...)：画椭圆。
    # 外接矩形的左上角 (x1,y1)，右下角 (x2,y2)。宽高相等时就是圆。
    # 加 3、减 3 让圆比格子小一点，留边距更好看。
    canvas.create_oval(
        fx * CELL + 3, fy * CELL + 3,
        (fx + 1) * CELL - 3, (fy + 1) * CELL - 3,
        fill="#e74c3c", outline=""
    )

    # ---------- 画蛇 ----------
    for i, (x, y) in enumerate(snake):
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
place_food()  # 游戏开始前先放一个食物
draw()
game_loop()
root.mainloop()
