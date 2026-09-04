# -*- coding: utf-8 -*-
# 【语法】上面这行叫"编码声明"，告诉 Python 这个文件用 UTF-8 编码保存，
# 这样文件里的中文才不会乱码。Python 3 默认就是 UTF-8，写不写都行，但写上更保险。

"""
【语法】这是模块的"文档字符串"（docstring），用三个双引号包起来的多行文字。
它不是普通注释，而是程序的一部分，可以用 help(模块名) 查看。
这里写的是游戏的介绍和操作说明。
"""

# 【语法】import 是"导入模块"的关键字。
# random 是 Python 自带的"随机数"模块，导入后就能用 random.randint() 等函数生成随机数。
import random
# 【语法】import ... as ... 是导入模块并给它起一个短别名。
# tkinter 是 Python 自带的"图形界面"模块，名字太长，起个别名 tk，后面写 tk.Tk() 比 tkinter.Tk() 短。
import tkinter as tk


# ==================================================================
# 【语法】下面这些都是"全局常量"——在函数和类外面定义的变量，整个文件都能用。
# 约定俗成：全大写的变量名表示"常量"，意思是程序运行过程中不会去改它。
# ==================================================================

CELL = 20
# 【语法】变量赋值：把等号右边的值 20 存到左边的变量 CELL 里。
# 以后写 CELL 就代表 20。这里表示每个格子 20 像素宽。

COLS = 20            # 横向格子数
ROWS = 20            # 纵向格子数
WIDTH = COLS * CELL  # 【语法】* 是乘法运算符。画布宽度 = 列数 x 每格大小 = 20 x 20 = 400
HEIGHT = ROWS * CELL # 画布高度 = 行数 x 每格大小 = 400

# ---------- 颜色常量 ----------
# 【语法】字符串用引号包起来。"#1a1a2e" 是十六进制颜色码，
# # 后面每两位分别代表红、绿、蓝的亮度（00 最暗，ff 最亮）。
BG_COLOR = "#1a1a2e"      # 背景色
GRID_COLOR = "#23234a"    # 网格线颜色
SNAKE_HEAD = "#2ecc71"    # 蛇头颜色
SNAKE_BODY = "#27ae60"    # 蛇身颜色
FOOD_COLOR = "#e74c3c"    # 食物颜色
TEXT_COLOR = "#ffffff"     # 文字颜色（白色）
HIGHLIGHT = "#f1c40f"     # 强调色（金黄色）


# ==================================================================
# 【语法】class 是定义"类"的关键字。
# 类就像一个"蓝图"或"模板"，描述了一类事物有什么数据（属性）和能做什么（方法）。
# SnakeGame 这个类描述了"贪吃蛇游戏"该有的一切。
# 类名约定用"大驼峰"命名法：每个单词首字母大写，连在一起。
# ==================================================================
class SnakeGame:
    """游戏主类的文档字符串：描述这个类是干什么的"""

    # ------------------------------------------------------------------
    # 【语法】def 是定义"函数/方法"的关键字。
    # __init__ 是一个特殊的方法名（前后各两个下划线），叫"构造方法"。
    # 当你创建这个类的对象时，Python 会自动调用 __init__ 来初始化对象。
    #
    # 【语法】self 是方法的第一个参数，代表"对象自己"。
    # 在方法里写 self.xxx = ... 就是给这个对象添加/修改一个属性。
    # 调用方法时不需要手动传 self，Python 会自动把对象传进去。
    #
    # 【语法】root 是第二个参数，是调用者传进来的"主窗口"对象。
    # ------------------------------------------------------------------
    def __init__(self, root):
        # 【语法】self.root = root：把传进来的窗口对象存到对象的 root 属性里，
        # 这样其他方法也能通过 self.root 访问到这个窗口。
        self.root = root

        # 【语法】对象.方法名(参数) 是"调用对象的方法"。
        # 这里调用窗口对象的 title 方法，设置窗口标题。
        self.root.title("贪吃蛇大作战")

        # 【语法】resizable(False, False) 禁止窗口拉伸。
        # 两个参数分别是"宽度可否拉伸"和"高度可否拉伸"，都传 False 表示都不行。
        self.root.resizable(False, False)

        # ---------- 顶部分数栏 ----------
        # 【语法】tk.StringVar(value="...") 创建一个"可变字符串对象"。
        # 它和普通字符串的区别是：改它的值，界面上绑定它的文字会自动更新。
        # value= 是"关键字参数"，明确指定给哪个参数传值，不依赖参数顺序。
        self.score_var = tk.StringVar(value="分数: 0    最高: 0")

        # 【语法】tk.Label(...) 创建一个"文字标签"控件。
        # 这里连续传了多个关键字参数：
        #   textvariable= 绑定可变字符串（分数变了自动刷新）
        #   font= 字体，用元组 ("字体名", 字号, "加粗") 表示
        #   fg= 文字颜色（foreground 的缩写）
        #   bg= 背景颜色（background 的缩写）
        tk.Label(
            root,
            textvariable=self.score_var,
            font=("Microsoft YaHei", 14, "bold"),
            fg=HIGHLIGHT,
            bg=BG_COLOR,
        # 【语法】.pack() 是"布局方法"，把控件放到窗口里。
        # fill="x" 表示横向填满窗口宽度；pady=4 表示上下各留 4 像素空隙。
        ).pack(fill="x", pady=4)

        # ---------- 游戏画布 ----------
        # 【语法】tk.Canvas(...) 创建"画布"控件，我们在上面画图（蛇、食物、网格线）。
        self.canvas = tk.Canvas(
            root,
            width=WIDTH,
            height=HEIGHT,
            bg=BG_COLOR,
            highlightthickness=0,  # 去掉画布默认的边框
        )
        self.canvas.pack()

        # ---------- 底部提示文字 ----------
        tk.Label(
            root,
            text="方向键 / WASD 移动    空格 暂停/重开",
            font=("Microsoft YaHei", 9),
            fg="#8888aa",
            bg=BG_COLOR,
        ).pack(fill="x", pady=3)

        # 设置窗口整体背景色
        self.root.configure(bg=BG_COLOR)

        # 最高分属性：记录历史最好成绩，重开不清零
        self.high_score = 0

        # 【语法】bind("<Key>", 函数) 是"绑定事件"。
        # 意思是：当用户在窗口里按任何键时，自动调用 self.on_key 这个方法来处理。
        # "<Key>" 表示"任何键盘按键"事件。
        self.root.bind("<Key>", self.on_key)

        # 【语法】protocol("WM_DELETE_WINDOW", 函数) 绑定"窗口关闭"事件。
        # 用户点窗口右上角的叉叉时，自动调用 self.on_close。
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

        # 调用自己的 reset 方法，初始化游戏数据（蛇的位置、分数等）
        self.reset()

        # 【语法】after(毫秒数, 函数) 是"定时器"：等这么多毫秒后调用这个函数。
        # 这里安排 speed 毫秒后调用 game_loop，游戏就开始跑了。
        # 把返回的定时器 ID 存起来，后面关闭窗口时可以取消它。
        self.after_id = self.root.after(self.speed, self.game_loop)

    # ------------------------------------------------------------------
    # 【语法】def reset(self): 定义一个叫 reset 的方法，只有 self 一个参数。
    # 这个方法的作用是把游戏状态恢复到初始值。
    # ------------------------------------------------------------------
    def reset(self):
        # 【语法】列表（list）：用方括号 [] 包起来，元素之间用逗号隔开。
        # 这里每个元素是一个"元组" (x, y)，表示蛇的一节身体在哪个格子。
        # 【语法】元组（tuple）：用圆括号 () 包起来，和列表类似，但创建后不能修改。
        # 坐标用元组存，因为一个格子的 (x, y) 是固定的一对值，不需要改。
        # 列表的第一个元素是蛇头，最后一个是蛇尾巴。
        self.snake = [(10, 10), (9, 10), (8, 10)]

        # 【语法】方向用元组 (x变化量, y变化量) 表示。
        # (1, 0) 表示 x 增加 1、y 不变 → 向右移动。
        # (0, -1) 表示 x 不变、y 减少 1 → 向上移动（注意画布 y 轴向下为正）。
        self.direction = (1, 0)
        self.next_direction = (1, 0)  # 下一帧的方向（按键先改这个，移动时才生效）

        self.score = 0       # 当前分数
        self.speed = 150     # 每步间隔毫秒数，越小越快
        self.game_over = False  # 【语法】布尔值：True 表示真，False 表示假
        self.paused = False  # 是否暂停

        self.place_food()    # 调用方法：随机放一个食物
        self.update_score()  # 调用方法：更新分数栏显示

    # ------------------------------------------------------------------
    def place_food(self):
        # 【语法】while True: 是"无限循环"，条件永远为真，会一直循环。
        # 必须在循环体内用 return 或 break 才能退出。
        # 这里不断随机选位置，直到选到一个不在蛇身上的格子才退出。
        while True:
            # 【语法】random.randint(a, b)：生成 a 到 b 之间的随机整数（包含 a 和 b）。
            # COLS - 1 = 19，所以 x 是 0 到 19 之间的随机数。
            x = random.randint(0, COLS - 1)
            y = random.randint(0, ROWS - 1)

            # 【语法】in 是"成员运算符"，判断左边的值是否在右边的列表/元组里。
            # (x, y) not in self.snake 表示"这个坐标不在蛇身上"。
            if (x, y) not in self.snake:
                self.food = (x, y)  # 把食物坐标存到对象的 food 属性里
                # 【语法】return 从函数/方法中返回，退出方法。
                # 这里 return 后面没有值，只是为了退出 while 循环和方法。
                return

    # ------------------------------------------------------------------
    # 【语法】event 参数是 Tkinter 传进来的"事件对象"，
    # 里面记录了发生了什么事（比如按了哪个键）。
    # event.keysym 是按键的名字，如 "Left"、"a"、"space"。
    # ------------------------------------------------------------------
    def on_key(self, event):
        key = event.keysym  # 取出按键名字，存到局部变量 key 里

        # 【语法】if ... and ...：逻辑与，两个条件都为真才执行。
        # key in ("Left", "a", "A")：按键是否是这三个中的一个（支持方向键和 WASD）。
        # self.direction != (1, 0)：当前方向不是向右（防止向右时按左，180度掉头撞死自己）。
        # 【语法】!= 是"不等于"运算符。
        if key in ("Left", "a", "A") and self.direction != (1, 0):
            self.next_direction = (-1, 0)  # 改为向左

        # 【语法】elif 是 else if 的缩写，"上面的条件不满足，再试试这个条件"。
        elif key in ("Right", "d", "D") and self.direction != (-1, 0):
            self.next_direction = (1, 0)   # 改为向右

        elif key in ("Up", "w", "W") and self.direction != (0, 1):
            self.next_direction = (0, -1)  # 改为向上（y 减少）

        elif key in ("Down", "s", "S") and self.direction != (0, -1):
            self.next_direction = (0, 1)   # 改为向下（y 增加）

        elif key == "space":
            # 【语法】== 是"等于"比较运算符，判断两边是否相等。
            # 注意和赋值 = 区分：== 是问"相等吗"，= 是"把右边存到左边"。
            if self.game_over:
                # 如果游戏已经结束，按空格就重新开始
                self.reset()
            else:
                # 【语法】not 是"逻辑非"，把布尔值反过来：True 变 False，False 变 True。
                # self.paused = not self.paused 就是"暂停状态切换"：暂停变继续，继续变暂停。
                self.paused = not self.paused

    # ------------------------------------------------------------------
    # step 方法：推进一帧游戏逻辑（移动蛇、判断吃食物/撞墙/撞自己）
    # ------------------------------------------------------------------
    def step(self):
        # 把下一帧方向正式设为当前方向（之前按键只改了 next_direction）
        self.direction = self.next_direction

        # 【语法】head_x, head_y = self.snake[0] 是"序列解包"。
        # self.snake[0] 是一个元组 (x, y)，把它的两个值分别赋给 head_x 和 head_y。
        # 【语法】列表[索引]：取列表中指定位置的元素。索引从 0 开始，所以 [0] 是第一个元素（蛇头）。
        head_x, head_y = self.snake[0]

        # 计算新蛇头位置：当前坐标 + 方向变化量
        new_head = (head_x + self.direction[0], head_y + self.direction[1])

        # ---------- 判断撞墙 ----------
        # 【语法】比较运算符：< 小于，>= 大于等于。
        # 0 <= new_head[0] < COLS 是"链式比较"，等价于 0 <= new_head[0] and new_head[0] < COLS。
        # 新位置的 x 或 y 超出 0~19 范围就是撞墙。
        if not (0 <= new_head[0] < COLS and 0 <= new_head[1] < ROWS):
            self.game_over = True
            return  # 撞墙了，直接退出方法

        # ---------- 判断撞到自己 ----------
        # 新位置已经在蛇身列表里，说明蛇头要撞到自己身体了
        if new_head in self.snake:
            self.game_over = True
            return

        # ---------- 移动蛇头 ----------
        # 【语法】列表.insert(索引, 值)：在指定索引位置插入一个值，后面的元素往后挪。
        # insert(0, new_head) 就是在列表最前面插入新蛇头。
        self.snake.insert(0, new_head)

        # ---------- 判断是否吃到食物 ----------
        if new_head == self.food:
            # 【语法】+= 是"加法赋值"运算符，self.score += 10 等价于 self.score = self.score + 10。
            self.score += 10

            # 更新最高分
            if self.score > self.high_score:
                self.high_score = self.score

            # 【语法】max(a, b)：返回 a 和 b 中较大的那个。
            # 每吃一个食物速度加快 5 毫秒，但最快不低于 60 毫秒（防止快到看不清）。
            self.speed = max(60, self.speed - 5)

            self.place_food()    # 重新放一个新食物
            self.update_score()  # 更新分数栏
            # 注意：吃到食物时不删尾巴，蛇就变长了一节！

        else:
            # 【语法】列表.pop()：删除并返回列表的最后一个元素（蛇尾巴）。
            # 没吃到食物就删尾巴，蛇整体向前移动但长度不变。
            self.snake.pop()

    # ------------------------------------------------------------------
    # draw 方法：把当前游戏状态画到画布上
    # ------------------------------------------------------------------
    def draw(self):
        # 清空画布上的所有内容（"all" 是特殊标签，表示全部删除）
        self.canvas.delete("all")

        # ---------- 画网格线 ----------
        # 【语法】for 变量 in range(起始, 结束): 循环。
        # range(1, COLS) 生成 1, 2, 3, ..., 19（不包含结束值 20）。
        # 画竖线：从左到右，每隔 CELL 像素画一条
        for i in range(1, COLS):
            # 【语法】画布.create_line(x1, y1, x2, y2, fill=颜色)：画一条从 (x1,y1) 到 (x2,y2) 的线。
            self.canvas.create_line(i * CELL, 0, i * CELL, HEIGHT, fill=GRID_COLOR)

        # 画横线：从上到下
        for j in range(1, ROWS):
            self.canvas.create_line(0, j * CELL, WIDTH, j * CELL, fill=GRID_COLOR)

        # ---------- 画食物（红色圆） ----------
        fx, fy = self.food  # 解包食物坐标
        # 【语法】画布.create_oval(x1, y1, x2, y2, ...)：画椭圆，
        # 外接矩形的左上角 (x1,y1)，右下角 (x2,y2)。宽高相等时就是圆。
        # 加 3、减 3 是让圆比格子小一点，留边距更好看。
        self.canvas.create_oval(
            fx * CELL + 3, fy * CELL + 3,
            (fx + 1) * CELL - 3, (fy + 1) * CELL - 3,
            fill=FOOD_COLOR,  # fill= 填充颜色
            outline="",        # outline= 边框颜色，空字符串表示不要边框
        )

        # ---------- 画蛇身 ----------
        # 【语法】enumerate(列表)：同时取出每个元素的"索引"和"值"。
        # for i, (x, y) in enumerate(self.snake): 中，i 是第几节，(x,y) 是坐标。
        for i, (x, y) in enumerate(self.snake):
            # 【语法】条件表达式（三元表达式）：值1 if 条件 else 值2。
            # 如果 i == 0（是蛇头）就用 SNAKE_HEAD 颜色，否则用 SNAKE_BODY 颜色。
            color = SNAKE_HEAD if i == 0 else SNAKE_BODY

            # 画矩形：每节蛇身是一个方块，加 1 减 1 是让每节之间留一条细缝
            self.canvas.create_rectangle(
                x * CELL + 1, y * CELL + 1,
                (x + 1) * CELL - 1, (y + 1) * CELL - 1,
                fill=color,
                outline="",
            )

        # ---------- 画蛇头眼睛（两个小白点，会跟着方向转） ----------
        if self.snake:  # 列表非空才画（保险判断，正常情况下蛇一定有身体）
            hx, hy = self.snake[0]
            # 计算蛇头格子的中心点像素坐标
            cx, cy = hx * CELL + CELL / 2, hy * CELL + CELL / 2
            dx, dy = self.direction  # 当前方向
            eye_off = 4  # 眼睛沿方向往前偏移的距离

            # 计算垂直于移动方向的向量，用来把两只眼睛左右分开
            # 比如方向 (1,0) 向右，垂直方向就是 (0,1)，两只眼睛上下排列
            perp = (-dy, dx)

            # 【语法】for sign in (-1, 1): 循环两次，sign 分别是 -1 和 1。
            # -1 画左眼，1 画右眼。
            for sign in (-1, 1):
                # 眼睛位置 = 蛇头中心 + 沿方向偏移 + 垂直方向左右偏移
                ex = cx + dx * eye_off + perp[0] * 3 * sign
                ey = cy + dy * eye_off + perp[1] * 3 * sign
                # 画一个小圆点当眼睛（半径 2 像素）
                self.canvas.create_oval(ex - 2, ey - 2, ex + 2, ey + 2, fill="white", outline="")

        # ---------- 游戏结束 / 暂停遮罩 ----------
        if self.game_over:
            # 画半透明黑色遮罩覆盖整个画布
            # stipple="gray50" 是点阵纹理，用黑白点模拟半透明效果
            self.canvas.create_rectangle(0, 0, WIDTH, HEIGHT, fill="black", stipple="gray50")

            # 【语法】画布.create_text(x, y, text=文字, ...)：在 (x,y) 位置画文字。
            # WIDTH / 2 是画布水平中心。
            self.canvas.create_text(
                WIDTH / 2, HEIGHT / 2 - 25,
                text="游戏结束",
                fill=TEXT_COLOR,
                font=("Microsoft YaHei", 30, "bold"),
            )
            self.canvas.create_text(
                WIDTH / 2, HEIGHT / 2 + 15,
                # 【语法】% 是字符串格式化运算符。
                # "得分 %d" % self.score 表示把 self.score 填到 %d 的位置（%d 代表整数）。
                text="得分 %d" % self.score,
                fill=HIGHLIGHT,
                font=("Microsoft YaHei", 16, "bold"),
            )
            self.canvas.create_text(
                WIDTH / 2, HEIGHT / 2 + 45,
                text="按 空格 重新开始",
                fill=TEXT_COLOR,
                font=("Microsoft YaHei", 12),
            )
        elif self.paused:
            # 暂停时也画半透明遮罩
            self.canvas.create_rectangle(0, 0, WIDTH, HEIGHT, fill="black", stipple="gray50")
            self.canvas.create_text(
                WIDTH / 2, HEIGHT / 2,
                text="暂停中",
                fill=TEXT_COLOR,
                font=("Microsoft YaHei", 30, "bold"),
            )

    # ------------------------------------------------------------------
    # game_loop 方法：游戏主循环，每隔 speed 毫秒自动调用一次
    # ------------------------------------------------------------------
    def game_loop(self):
        # 只有没结束、没暂停时才推进游戏逻辑
        if not self.game_over and not self.paused:
            self.step()

        # 不管什么状态都要画画面（结束时画"游戏结束"，暂停时画"暂停中"）
        self.draw()

        # 调度下一帧：等 speed 毫秒后再调用自己，形成无限循环
        self.after_id = self.root.after(self.speed, self.game_loop)

    # ------------------------------------------------------------------
    def update_score(self):
        # 【语法】字符串格式化："分数: %d    最高: %d" % (a, b)
        # 有几个 %d 就要在 % 后面传几个值，用元组包起来。
        # 第一个 %d 填 self.score，第二个 %d 填 self.high_score。
        self.score_var.set("分数: %d    最高: %d" % (self.score, self.high_score))

    # ------------------------------------------------------------------
    def on_close(self):
        # 关闭窗口前先取消定时器，防止窗口关了定时器还在跑
        if self.after_id is not None:
            # 【语法】is 是"身份比较"，判断两个变量是否引用同一个对象。
            # is not None 表示"不是空值"。None 是 Python 的"空"特殊值。
            try:
                # 【语法】try/except：异常处理。
                # try 里的代码如果出错，不会崩溃，而是跳到 except 里执行。
                self.root.after_cancel(self.after_id)
            except Exception:
                # 【语法】except Exception: 捕获所有类型的异常。
                # pass 是"什么都不做"的占位语句（语法要求 except 块里必须有代码）。
                pass
        # 销毁窗口，程序退出
        self.root.destroy()


# ==================================================================
# 【语法】def main(): 定义一个普通函数（不是类的方法，所以没有 self 参数）。
# 这个函数是程序的入口：创建窗口、创建游戏、启动事件循环。
# ==================================================================
def main():
    root = tk.Tk()       # 创建主窗口（Tkinter 程序必须先有一个主窗口）
    SnakeGame(root)       # 创建游戏对象（自动调用 __init__ 初始化并开始游戏）
    root.mainloop()       # 启动事件循环：窗口显示出来，开始等待用户操作（点鼠标、按键盘）


# ==================================================================
# 【语法】if __name__ == "__main__": 是 Python 的惯用写法。
# __name__ 是 Python 内置的特殊变量：
#   - 直接运行这个文件时，__name__ 的值是 "__main__"
#   - 被其他文件 import 导入时，__name__ 的值是文件名（"snake_game"）
# 这样写的好处是：直接运行时才启动游戏，被导入时不会自动运行（方便测试和复用）。
# ==================================================================
if __name__ == "__main__":
    main()
