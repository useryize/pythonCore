# -*- coding: utf-8 -*-
# ============================================================
# 第2步：在窗口里画一个绿色小方块
# 相比第1步新增：定义格子大小 CELL、蛇头坐标、用 create_rectangle 画方块
# 运行后看到：深蓝色窗口里有一个绿色小方块
# ============================================================

import tkinter as tk

# 【语法】常量：全大写变量名表示"常量"，程序运行中不会改它。
# CELL = 20 表示每个格子 20 像素宽高。
CELL = 20

root = tk.Tk()
root.title("贪吃蛇 - 第2步")
root.resizable(False, False)

canvas = tk.Canvas(root, width=400, height=400, bg="#1a1a2e")
canvas.pack()

# 蛇头的格子坐标（第10列第10行，左上角是第0列第0行）
head_x, head_y = 10, 10

# 【语法】canvas.create_rectangle(x1, y1, x2, y2, ...) 画一个矩形。
# (x1,y1) 是左上角像素坐标，(x2,y2) 是右下角像素坐标。
# 格子坐标转像素坐标：x * CELL。
# 加 1、减 1 是让方块比格子小 1 像素，留一条细缝更好看。
# fill= 填充颜色（亮绿色），outline="" 表示不要边框线。
canvas.create_rectangle(
    head_x * CELL + 1, head_y * CELL + 1,
    (head_x + 1) * CELL - 1, (head_y + 1) * CELL - 1,
    fill="#2ecc71", outline=""
)

root.mainloop()
