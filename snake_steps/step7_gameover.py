# -*- coding: utf-8 -*-
# ============================================================
# 第7步：撞墙或撞到自己，游戏结束
# 相比第6步新增：去掉穿墙效果、判断撞墙（坐标超出范围）、
#   判断撞自己（新头在 snake 列表里）、game_over 标志、
#   游戏结束画面（半透明遮罩 + 文字）
# 运行后看到：撞墙或撞到自己后，画面变暗，显示"游戏结束"和得分
# ============================================================

import tkinter as tk
import random

CELL = 20
COLS = 20
ROWS = 20
# 画布宽高用常量表示，后面画游戏结束文字时要用来居中
WIDTH = COLS * CELL
HEIGHT = ROWS * CELL

root = tk.Tk()
root.title("贪吃蛇 - 第7步")
root.resizable(False, False)

score_var = tk.StringVar(value="分数: 0")
tk.Label(root, textvariable=score_var, font=("Arial", 14, "bold"),
         fg="#f1c40f", bg="#1a1a2e").pack(fill="x", pady=4)

canvas = tk.Canvas(root, width=WIDTH, height=HEIGHT,
                   bg="#1a1a2e", highlightthickness=0)
canvas.pack()
root.configure(bg="#1a1a2e")

snake = [(10, 10), (9, 10), (8, 10)]
direction = (1, 0)
next_direction = (1, 0)
speed = 150
score = 0
food = (0, 0)
# 【语法】布尔值：True 表示真，False 表示假。
# game_over = False 表示游戏还没结束，撞墙/撞自己后改成 True。
game_over = False


def place_food():
    global food
    while True:
        x = random.randint(0, COLS - 1)
        y = random.randint(0, ROWS - 1)
        if (x, y) not in snake:
            food = (x, y)
            return


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
    global direction, score, game_over
    direction = next_direction
    head_x, head_y = snake[0]
    new_head = (head_x + direction[0], head_y + direction[1])

    # ---------- 判断撞墙 ----------
    # 【语法】链式比较：0 <= new_head[0] < COLS 等价于
    # 0 <= new_head[0] and new_head[0] < COLS。
    # 新位置的 x 或 y 不在 0~19 范围内，就是撞墙了。
    if not (0 <= new_head[0] < COLS and 0 <= new_head[1] < ROWS):
        game_over = True
        return  # 撞墙了，直接退出函数，不往下执行

    # ---------- 判断撞到自己 ----------
    # 新位置已经在蛇身列表里，说明蛇头要撞到自己的身体了
    if new_head in snake:
        game_over = True
        return

    # 没撞墙也没撞自己，正常移动
    snake.insert(0, new_head)
    if new_head == food:
        score += 10
        score_var.set("分数: %d" % score)
        place_food()
    else:
        snake.pop()


def draw():
    canvas.delete("all")

    # 画食物
    fx, fy = food
    canvas.create_oval(
        fx * CELL + 3, fy * CELL + 3,
        (fx + 1) * CELL - 3, (fy + 1) * CELL - 3,
        fill="#e74c3c", outline=""
    )

    # 画蛇
    for i, (x, y) in enumerate(snake):
        color = "#2ecc71" if i == 0 else "#27ae60"
        canvas.create_rectangle(
            x * CELL + 1, y * CELL + 1,
            (x + 1) * CELL - 1, (y + 1) * CELL - 1,
            fill=color, outline=""
        )

    # ---------- 游戏结束画面 ----------
    if game_over:
        # 画半透明黑色遮罩覆盖整个画布
        # 【语法】stipple="gray50" 是点阵纹理，用黑白点模拟半透明效果。
        canvas.create_rectangle(0, 0, WIDTH, HEIGHT, fill="black", stipple="gray50")

        # 【语法】canvas.create_text(x, y, text=文字, ...)：在 (x,y) 位置画文字。
        # WIDTH/2, HEIGHT/2 是画布中心。
        canvas.create_text(
            WIDTH / 2, HEIGHT / 2 - 20,
            text="游戏结束", fill="white", font=("Arial", 30, "bold")
        )
        canvas.create_text(
            WIDTH / 2, HEIGHT / 2 + 20,
            text="得分 %d" % score, fill="#f1c40f", font=("Arial", 16, "bold")
        )


def game_loop():
    # 只有没结束时才推进游戏逻辑（结束了蛇就不动了）
    if not game_over:
        move()
    draw()  # 不管结没结束都要画画面（结束时要画"游戏结束"）
    root.after(speed, game_loop)


root.bind("<Key>", on_key)
place_food()
draw()
game_loop()
root.mainloop()
