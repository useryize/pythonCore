import tkinter as tk
import random

CELL = 20
COLS = 20
ROWS = 20

WIDTH = COLS * CELL
HEIGHT = ROWS * CELL

root = tk.Tk()
root.title("snake")
root.resizable(False, False)

score_var = tk.StringVar(value="分数: 0")

tk.Label(root, textvariable=score_var, font=("Arial", 14, "bold"),
         fg="#f1c40f", bg="#1a1a2e").pack(fill="x", pady=4)


canvas = tk.Canvas(root, width=WIDTH, height=HEIGHT,
                   bg="#1a1a2e", highlightthickness=0)
canvas.pack()
tk.Label(root, text="方向键 / WASD 移动    空格 暂停/重开",
         font=("Arial", 9), fg="#8888aa", bg="#1a1a2e").pack(fill="x", pady=3)
root.configure(bg="#1a1a2e")

snake = [(10, 10), (9, 10), (8, 10)]
direction = (1, 0)
next_direction = (1, 0)
speed = 150

score = 0       # 当前分数
high_score = 0   # 最高分：重开不清零
food = (0, 0)   # 食物的格子坐标

game_over = False
paused = False   # 是否暂停


def reset():
    global snake, direction, next_direction, speed, score, game_over, paused
    snake = [(10, 10), (9, 10), (8, 10)]
    direction = (1, 0)
    next_direction = (1, 0)
    speed = 150
    score = 0
    game_over = False
    paused = False
    place_food()
    score_var.set(f"分数: {score},   最高: {high_score}")


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
    if (key in ("Left", "a") and direction != (1, 0)):
        next_direction = (-1, 0)
    elif (key in ("Right", "d") and direction != (-1, 0)):
        next_direction = (1, 0)
    elif (key in ("Up", "w") and direction != (0, 1)):
        next_direction = (0, -1)
    elif (key in ("Down", "s") and direction != (0, -1)):
        next_direction = (0, 1)
    elif key == "space":
        if game_over:
            reset()
        else:
            global paused
            paused = not paused


def move():
    global direction, score, game_over
    direction = next_direction
    head_x = snake[0][0]
    head_y = snake[0][1]

    new_head = (head_x+direction[0], head_y+direction[1])
    # new_head = (new_head[0] % COLS, new_head[1] % ROWS)
    if new_head[0] < 0 or new_head[0] >= COLS or new_head[1] < 0 or new_head[1] >= ROWS or new_head in snake:
        game_over = True
        return

    snake.insert(0, new_head)

    if new_head == food:
        score += 1
        if score > high_score:
            high_score = score
        speed = max(50, speed - 5)
        score_var.set(f"分数: {score}  最高: {high_score}")
        place_food()
    else:
        snake.pop()

    draw()


def draw():
    canvas.delete("all")

    for i in range(1, COLS):
        canvas.create_line(i*CELL, 0, i*CELL, HEIGHT, fill="#333333")
    for i in range(1, ROWS):
        canvas.create_line(0, i*CELL, WIDTH, i*CELL, fill="#333333")

    fx, fy = food
    canvas.create_oval(
        fx*CELL+3, fy*CELL+3,
        (fx+1)*CELL-3, (fy+1)*CELL-3,
        fill="#ff0000", outline=""
    )

    for i, (x, y) in enumerate(snake):
        color = "#00ff00" if i == 0 else "#00cc00"
        canvas.create_rectangle(
            x*CELL+1, y*CELL+1,
            (x+1)*CELL-1, (y+1)*CELL-1,
            fill=color, outline=""
        )

    if snake:
        hx, hy = snake[0]
        cx, cy = hx * CELL + CELL / 2, hy * CELL + CELL / 2
        dx, dy = direction
        perp = (-dy, dx)
        for sign in (-1, 1):
            ex = cx + dx * 4 + perp[0] * 3 * sign
            ey = cy + dy * 4 + perp[1] * 3 * sign
            canvas.create_oval(ex - 2, ey - 2, ex + 2, ey +
                               2, fill="white", outline="")

    if game_over:
        canvas.create_rectangle(
            0, 0, WIDTH, HEIGHT,
            fill="#000000", outline=""
        )

        canvas.create_text(
            WIDTH / 2, HEIGHT / 2,
            text="游戏结束", fill="#ffffff",
            font=("Arial", 24, "bold")
        )
        canvas.create_text(
            WIDTH / 2, HEIGHT / 2 + 40,
            text=f"最终分数: {score}", fill="#ffffff",
            font=("Arial", 16)
        )
    elif paused:
        canvas.create_rectangle(
            0, 0, WIDTH, HEIGHT,
            fill="#000000", outline=""
        )

        canvas.create_text(
            WIDTH / 2, HEIGHT / 2,
            text="暂停中", fill="#ffffff",
            font=("Arial", 24, "bold")
        )


def game_loop():
    if not game_over and not paused:
        move()
    draw()
    root.after(speed, game_loop)


root.bind("<Key>", on_key)
place_food()
draw()
game_loop()
root.mainloop()
