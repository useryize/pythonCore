# -*- coding: utf-8 -*-
# ============================================================
# 第8步（完整版）：加速 + 暂停/重开 + 最高分 + 蛇头眼睛 + 网格线
# 相比第7步新增：
#   1. 吃食物后速度加快（speed 减小）
#   2. 空格键：游戏中暂停/继续，结束后重新开始
#   3. 最高分记录（重开不清零）
#   4. 蛇头画两个白色小眼睛，跟着方向转
#   5. 画网格线、底部操作提示
# 运行后看到：完整的贪吃蛇游戏，越吃越快，可暂停可重开
# ============================================================

import tkinter as tk
import random

CELL = 20
COLS = 20
ROWS = 20
WIDTH = COLS * CELL
HEIGHT = ROWS * CELL

root = tk.Tk()
root.title("贪吃蛇")
root.resizable(False, False)

# ---------- 顶部分数栏（显示当前分和最高分） ----------
score_var = tk.StringVar(value="分数: 0    最高: 0")
tk.Label(root, textvariable=score_var, font=("Microsoft YaHei", 14, "bold"),
         fg="#f1c40f", bg="#1a1a2e").pack(fill="x", pady=4)

canvas = tk.Canvas(root, width=WIDTH, height=HEIGHT,
                   bg="#1a1a2e", highlightthickness=0)
canvas.pack()

# ---------- 底部操作提示 ----------
tk.Label(root, text="方向键 / WASD 移动    空格 暂停/重开",
         font=("Microsoft YaHei", 9), fg="#8888aa", bg="#1a1a2e").pack(fill="x", pady=3)
root.configure(bg="#1a1a2e")

# ---------- 游戏数据 ----------
snake = [(10, 10), (9, 10), (8, 10)]
direction = (1, 0)
next_direction = (1, 0)
speed = 150
score = 0
high_score = 0   # 最高分：重开不清零
food = (0, 0)
game_over = False
paused = False   # 是否暂停


def place_food():
    global food
    while True:
        x = random.randint(0, COLS - 1)
        y = random.randint(0, ROWS - 1)
        if (x, y) not in snake:
            food = (x, y)
            return


def reset():
    """重置游戏状态（按空格重开时调用）"""
    # 【语法】global 后面可以跟多个变量，用逗号隔开。
    global snake, direction, next_direction, speed, score, game_over, paused
    snake = [(10, 10), (9, 10), (8, 10)]
    direction = (1, 0)
    next_direction = (1, 0)
    speed = 150
    score = 0
    game_over = False
    paused = False
    place_food()
    # 重开后分数归零，但最高分保留
    score_var.set("分数: 0    最高: %d" % high_score)


def on_key(event):
    global next_direction, game_over, paused
    key = event.keysym

    # 方向控制
    if key in ("Left", "a") and direction != (1, 0):
        next_direction = (-1, 0)
    elif key in ("Right", "d") and direction != (-1, 0):
        next_direction = (1, 0)
    elif key in ("Up", "w") and direction != (0, 1):
        next_direction = (0, -1)
    elif key in ("Down", "s") and direction != (0, -1):
        next_direction = (0, 1)

    # 空格键：暂停/重开
    elif key == "space":
        if game_over:
            reset()  # 游戏结束时按空格 → 重新开始
        else:
            # 【语法】not 逻辑非：把布尔值反过来，True 变 False，False 变 True。
            # paused = not paused 就是"暂停状态切换"：暂停变继续，继续变暂停。
            paused = not paused


def move():
    global direction, score, high_score, speed, game_over
    direction = next_direction
    head_x, head_y = snake[0]
    new_head = (head_x + direction[0], head_y + direction[1])

    # 撞墙
    if not (0 <= new_head[0] < COLS and 0 <= new_head[1] < ROWS):
        game_over = True
        return
    # 撞自己
    if new_head in snake:
        game_over = True
        return

    snake.insert(0, new_head)
    if new_head == food:
        score += 10
        # 更新最高分
        if score > high_score:
            high_score = score
        # 【语法】max(a, b)：返回 a 和 b 中较大的那个。
        # 每吃一个食物速度加快 5 毫秒，但最快不低于 60 毫秒（防止快到看不清）。
        speed = max(60, speed - 5)
        score_var.set("分数: %d    最高: %d" % (score, high_score))
        place_food()
    else:
        snake.pop()


def draw():
    canvas.delete("all")

    # ---------- 画网格线 ----------
    # 竖线：从左到右，每隔 CELL 像素画一条
    for i in range(1, COLS):
        canvas.create_line(i * CELL, 0, i * CELL, HEIGHT, fill="#23234a")
    # 横线：从上到下
    for j in range(1, ROWS):
        canvas.create_line(0, j * CELL, WIDTH, j * CELL, fill="#23234a")

    # ---------- 画食物 ----------
    fx, fy = food
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

    # ---------- 画蛇头眼睛（两个小白点，跟着方向转） ----------
    if snake:
        hx, hy = snake[0]
        # 蛇头格子的中心点像素坐标
        cx, cy = hx * CELL + CELL / 2, hy * CELL + CELL / 2
        dx, dy = direction
        # 计算垂直于移动方向的向量，用来把两只眼睛左右分开
        # 比如方向 (1,0) 向右，垂直方向就是 (0,1)，两只眼睛上下排列
        perp = (-dy, dx)
        # sign 取 -1 和 1，分别画左眼和右眼
        for sign in (-1, 1):
            # 眼睛位置 = 蛇头中心 + 沿方向往前偏移 + 垂直方向左右偏移
            ex = cx + dx * 4 + perp[0] * 3 * sign
            ey = cy + dy * 4 + perp[1] * 3 * sign
            canvas.create_oval(ex - 2, ey - 2, ex + 2, ey + 2, fill="white", outline="")

    # ---------- 游戏结束画面 ----------
    if game_over:
        canvas.create_rectangle(0, 0, WIDTH, HEIGHT, fill="black", stipple="gray50")
        canvas.create_text(WIDTH / 2, HEIGHT / 2 - 25, text="游戏结束",
                           fill="white", font=("Microsoft YaHei", 30, "bold"))
        canvas.create_text(WIDTH / 2, HEIGHT / 2 + 15, text="得分 %d" % score,
                           fill="#f1c40f", font=("Microsoft YaHei", 16, "bold"))
        canvas.create_text(WIDTH / 2, HEIGHT / 2 + 45, text="按 空格 重新开始",
                           fill="white", font=("Microsoft YaHei", 12))

    # ---------- 暂停画面 ----------
    elif paused:
        canvas.create_rectangle(0, 0, WIDTH, HEIGHT, fill="black", stipple="gray50")
        canvas.create_text(WIDTH / 2, HEIGHT / 2, text="暂停中",
                           fill="white", font=("Microsoft YaHei", 30, "bold"))


def game_loop():
    # 没结束、没暂停时才推进游戏逻辑
    if not game_over and not paused:
        move()
    draw()
    root.after(speed, game_loop)


root.bind("<Key>", on_key)
place_food()
draw()
game_loop()
root.mainloop()
