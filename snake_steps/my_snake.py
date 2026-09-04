# -*- coding: utf-8 -*-
# ============================================================
# 贪吃蛇练习文件 —— 我们一步一步往里面加代码
# 当前进度：第 1 步（创建窗口）
# ============================================================

# 【语法】import 导入模块。tkinter 是 Python 自带的图形界面库，
# as tk 是给它起个短名字，后面写 tk.Tk() 比 tkinter.Tk() 短。
import tkinter as tk

# 【语法】创建主窗口。Tk() 是 tkinter 提供的"窗口工厂"，
# 调用它就会生成一个窗口对象，存到变量 root 里。
root = tk.Tk()

# 【语法】对象.方法(参数)：调用窗口对象的 title 方法，设置窗口标题。
root.title("贪吃蛇")

# 禁止用户拉伸窗口大小（两个 False 分别是宽度、高度不可拉伸）
root.resizable(False, False)

# 【语法】创建画布。Canvas 是一块可以画图的区域，
# width/height 是宽高（像素），bg 是背景颜色（深蓝黑色）。
canvas = tk.Canvas(root, width=400, height=400, bg="#1a1a2e")

# 【语法】.pack() 是"布局方法"，把控件放到窗口里并自动排列。
canvas.pack()

# 【语法】mainloop() 启动"事件循环"：窗口显示出来，开始等待用户操作
# （点鼠标、按键盘、关窗口等）。没有这一行，窗口会一闪而过。
root.mainloop()
