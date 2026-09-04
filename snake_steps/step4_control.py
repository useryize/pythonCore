# -*- coding: utf-8 -*-
# ============================================================
# 第4步：用方向键控制方块移动方向
# 相比第3步新增：on_key() 键盘处理函数、root.bind() 绑定按键、
#   next_direction 变量（防止一帧内连按导致180度掉头）
# 运行后看到：按上下左右键（或 WASD），方块跟着变方向
# ============================================================

import tkinter as tk

CELL = 20
COLS = 20
ROWS = 20

root = tk.Tk()
root.title("贪吃蛇 - 第4步")
root.resizable(False, False)

canvas = tk.Canvas(root, width=COLS * CELL, height=ROWS * CELL, bg="#1a1a2e")
canvas.pack()

head_x, head_y = 10, 10
direction = (1, 0)

# 【语法】为什么要两个方向变量？
# 用户可能在一帧内快速按两个键（比如向右时先按上再按左），
# 如果直接改 direction，就会 180 度掉头撞死自己。
# 所以按键只改 next_direction，真正移动时（move 里）才把 next_direction 赋给 direction。
next_direction = (1, 0)

speed = 150


# 【语法】event 参数是 Tkinter 传进来的"事件对象"，
# 里面记录了发生了什么事。event.keysym 是按下的键的名字，
# 比如 "Left"（左方向键）、"a"（a 键）、"space"（空格）。
def on_key(event):
    """处理键盘按键：按方向键改变 next_direction"""
    global next_direction
    key = event.keysym

    # 【语法】if ... and ...：逻辑与，两个条件都为真才执行。
    # key in ("Left", "a")：按键是否是这两个中的一个（支持方向键和 WASD）。
    # direction != (1, 0)：当前方向不是向右（防止向右时按左，180度掉头）。
    # 【语法】!= 是"不等于"运算符，== 是"等于"。
    if key in ("Left", "a") and direction != (1, 0):
        next_direction = (-1, 0)   # 向左
    elif key in ("Right", "d") and direction != (-1, 0):
        next_direction = (1, 0)    # 向右
    elif key in ("Up", "w") and direction != (0, 1):
        next_direction = (0, -1)   # 向上（y 减少，因为画布 y 轴向下为正）
    elif key in ("Down", "s") and direction != (0, -1):
        next_direction = (0, 1)    # 向下


def move():
    global head_x, head_y, direction
    direction = next_direction  # 移动时才把下一帧方向设为当前方向
    head_x += direction[0]
    head_y += direction[1]
    head_x %= COLS
    head_y %= ROWS
    draw()


def draw():
    canvas.delete("all")
    canvas.create_rectangle(
        head_x * CELL + 1, head_y * CELL + 1,
        (head_x + 1) * CELL - 1, (head_y + 1) * CELL - 1,
        fill="#2ecc71", outline=""
    )


def game_loop():
    move()
    root.after(speed, game_loop)


# 【语法】root.bind("<Key>", 函数)：绑定键盘事件。
# 意思是：用户在窗口里按任何键时，自动调用 on_key 函数来处理。
root.bind("<Key>", on_key)

draw()
game_loop()
root.mainloop()
