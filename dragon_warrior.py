# -*- coding: utf-8 -*-
# 【语法】编码声明：告诉 Python 这个文件用 UTF-8 编码，中文不会乱码。

"""
【语法】模块文档字符串（docstring）：用三个双引号包起来的多行说明文字。
"""

# operateData 是同目录下的另一个模块（用户自己导入的，保留）
import operateData

# 【语法】import 导入模块。os 提供操作系统相关功能（这里用来读环境变量）。
import os
# random 提供随机数功能
import random
# sys 提供系统相关功能（这里用来操作输出和退出程序）
import sys
# time 提供时间相关功能（这里用来做延时）
import time

# 【语法】os.environ.get("变量名") 读取环境变量，读不到就返回 None。
# 这里判断环境变量 GAME_FAST 是否等于 "1"，等于就开启快速模式（关掉打字动画）。
FAST = os.environ.get("GAME_FAST") == "1"


# ==================================================================
# 【语法】字典（dict）：用花括号 {} 包起来，每个元素是 "键": 值 的形式，
# 键和值之间用冒号，元素之间用逗号。通过 字典["键"] 来访问对应的值。
# 这里用字典存主角的所有属性，比单独定义一堆变量更整齐。
# ==================================================================
HERO = {
    "name": "小勇",     # 名字
    "hp": 100,          # 当前生命值
    "max_hp": 100,      # 最大生命值
    "atk": 15,           # 攻击力
    "defense": 3,        # 防御力
    "gold": 0,           # 金币
    "potions": 3,        # 药水数量
}

# ==================================================================
# 【语法】列表（list）：用方括号 [] 包起来，元素之间用逗号，有序排列。
# 通过 列表[索引] 访问元素，索引从 0 开始。
# 这里列表的每个元素又是一个字典，表示一只怪物的属性。
# 越靠后的怪物越强（血量、攻击、防御、金币奖励都递增）。
# ==================================================================
MONSTERS = [
    {"name": "史莱姆",   "hp": 40,  "atk": 8,  "defense": 1, "gold": 10},
    {"name": "骷髅兵",   "hp": 60,  "atk": 10, "defense": 2, "gold": 18},
    {"name": "哥布林王", "hp": 85,  "atk": 13, "defense": 3, "gold": 30},
    {"name": "暗影魔狼", "hp": 110, "atk": 16, "defense": 4, "gold": 45},
    {"name": "火焰巨龙", "hp": 150, "atk": 20, "defense": 6, "gold": 100},
]


# ==================================================================
# 【语法】def 函数名(参数1, 参数2=默认值): 定义一个函数。
# 参数可以有默认值，调用时不传就用默认值。这里 delay=0.02 表示默认延时 0.02 秒。
# 函数是一段可以重复调用的代码块，避免重复写相同的代码。
# ==================================================================
def slow_print(text, delay=0.02):
    """逐字打印文字，像打字机一样一个字一个字显示出来"""
    if FAST:
        delay = 0  # 快速模式下不延时

    # 【语法】for 变量 in 字符串: 遍历字符串的每个字符。
    # 字符串本质上也是一个字符序列，可以逐个取出。
    for ch in text:
        # 【语法】sys.stdout.write(字符)：写一个字符到屏幕，不自动换行。
        # print() 会自动换行，这里用 write 是为了让字连在同一行上逐个出现。
        sys.stdout.write(ch)
        sys.stdout.flush()  # 立即刷新输出缓冲区，让字符立刻显示出来
        time.sleep(delay)   # 【语法】time.sleep(秒数)：暂停程序指定秒数
    print()  # 全部打印完后换一行


def show_bar(current, maximum, width=20):
    """
    画文字血条，返回类似 "[####----------] 40/40" 的字符串。
    current 当前值，maximum 最大值，width 血条总长度（字符数）。
    """
    # 【语法】max(a, b) 返回较大值，min(a, b) 返回较小值。
    # 这里把比例限制在 0.0 到 1.0 之间，防止负数或超过 100%。
    ratio = max(0.0, min(1.0, current / maximum))

    # 【语法】int(浮点数)：把浮点数转成整数（向下取整，丢弃小数部分）。
    filled = int(width * ratio)

    # 【语法】字符串 * 整数：把字符串重复指定次数。
    # "#" * 3 就是 "###"。
    bar = "#" * filled + "-" * (width - filled)

    # 【语法】return 值：从函数返回一个值，调用者可以用变量接收。
    # 这里返回格式化好的血条字符串。
    return "[%s] %d/%d" % (bar, current, maximum)


def show_hero():
    """显示主角状态：生命值、金币、药水"""
    h = HERO  # 简写，后面少打几个字

    # 【语法】% 字符串格式化：
    #   %s 占位符填字符串（show_bar 返回的就是字符串）
    #   %d 占位符填整数
    # 有几个占位符，% 后面就要传几个值，多个值用元组 () 包起来。
    print(" 你  HP %s   金币 %d   药水 %d 个"
          % (show_bar(h["hp"], h["max_hp"]), h["gold"], h["potions"]))


def show_monster(m):
    """显示怪物状态：名字和生命值"""
    # 【语法】字典["键"]：访问字典中指定键对应的值。
    # m["name"] 取出怪物的名字，m["hp"] 取出当前血量，m["max_hp"] 取出满血值。
    print(" 怪  %s  HP %s" % (m["name"], show_bar(m["hp"], m["max_hp"])))


def get_choice(prompt, valid):
    """
    安全读取用户输入，只返回合法选项。
    prompt 是提示文字，valid 是合法选项的集合（如 {"1","2","3","4"}）。
    输入不合法就一直提示重新输入。
    """
    # 【语法】while True: 无限循环，靠循环体内的 return 或 break 退出。
    while True:
        # 【语法】try/except：异常处理。
        # try 块里的代码如果出错（比如用户按 Ctrl+C 中断），不会崩溃，跳到 except 块处理。
        try:
            # input(提示文字)：在屏幕显示提示，等待用户输入一行文字，按回车结束。
            # .strip()：去掉输入文字前后的空格和换行。
            value = input(prompt).strip()
        except (EOFError, KeyboardInterrupt):
            # 【语法】except (异常1, 异常2): 同时捕获多种异常。
            # EOFError：输入流结束（比如管道输入用完了）
            # KeyboardInterrupt：用户按了 Ctrl+C
            print("\n再见啦，下次再来冒险吧！")
            sys.exit(0)  # 【语法】sys.exit(状态码)：立即退出程序，0 表示正常退出

        # 【语法】in 成员运算符：判断值是否在集合/列表/元组里。
        if value in valid:
            return value  # 输入合法，返回这个值，退出函数和循环

        # 输入不合法，提示重新输入
        # 【语法】"/".join(列表)：把列表里的字符串用 "/" 连接起来。
        # sorted(valid) 把集合排序后转成列表。
        print("  输入有误，请重新输入：" + "/".join(sorted(valid)))


def battle(monster):
    """
    与一只怪物战斗，返回结果字符串：
      'win'  打赢了
      'lose' 被打死了
      'flee' 逃跑成功了
    """
    # 【语法】dict(字典)：创建一个字典的浅拷贝（副本）。
    # 这样战斗中修改怪物的 hp 不会影响全局的 MONSTERS 列表，下一局还能用原始数据。
    monster = dict(monster)
    # 给副本加一个 max_hp 键，记录满血值（战斗中 hp 会减少，max_hp 不变，用于画血条）
    monster["max_hp"] = monster["hp"]

    # 【语法】布尔变量：True/False。
    defending = False   # 本回合是否在防御（防御时受伤减半）
    atk_boost = False   # 下一次攻击是否威力翻倍（防御后蓄力）

    # 打印遇到怪物的提示
    print("\n==============================")
    print("  一只 %s 挡住了你的去路！" % monster["name"])
    print("==============================")

    # 战斗主循环：不断轮流"玩家回合"和"怪物回合"，直到分出胜负
    while True:
        print()
        show_hero()           # 显示主角状态
        show_monster(monster)  # 显示怪物状态
        print("\n  你的回合，选择行动：")
        print("    1 攻击    2 防御    3 喝药    4 逃跑")
        choice = get_choice("  > ", {"1", "2", "3", "4"})

        # ---------- 玩家行动 ----------
        # 【语法】if/elif/elif/elif 多分支判断，从上到下检查，满足哪个就执行哪个，后面的不再检查。
        if choice == "1":  # 攻击
            boost = atk_boost    # 先记下是否有蓄力加成
            atk_boost = False    # 用掉加成，下一次就没有了

            # 计算伤害：主角攻击力 - 怪物防御力 + 随机浮动（-3 到 +5）
            # 【语法】random.randint(a, b)：生成 a 到 b 之间的随机整数（包含两端）。
            dmg = HERO["atk"] - monster["defense"] + random.randint(-3, 5)

            if boost:
                dmg *= 2  # 【语法】*= 乘法赋值，dmg = dmg * 2，伤害翻倍

            dmg = max(1, dmg)  # 伤害至少为 1，不能是 0 或负数
            monster["hp"] -= dmg  # 【语法】-= 减法赋值，怪物扣血

            # 根据是否暴击打印不同文字
            if boost:
                slow_print("  会心一击！你斩向%s，造成 %d 点伤害！" % (monster["name"], dmg))
            else:
                slow_print("  你挥剑斩向%s，造成 %d 点伤害！" % (monster["name"], dmg))

        elif choice == "2":  # 防御
            defending = True    # 标记本回合在防御
            atk_boost = True    # 蓄力：下一次攻击伤害翻倍
            slow_print("  你摆出防御姿态，蓄力准备反击！")

        elif choice == "3":  # 喝药
            if HERO["potions"] <= 0:
                slow_print("  哎呀，药水喝完了！换个别的招吧。")
                # 【语法】continue：跳过本次循环剩余的代码，直接进入下一次循环。
                # 这里药水喝完了，不消耗回合，重新让玩家选择。
                continue
            HERO["potions"] -= 1  # 药水减一瓶
            # 回血 30 点，但不能超过最大生命值
            HERO["hp"] = min(HERO["max_hp"], HERO["hp"] + 30)
            slow_print("  你咕咚咕咚喝下一瓶药水，恢复了 30 点生命！")

        elif choice == "4":  # 逃跑
            # 【语法】random.random()：生成 0.0 到 1.0 之间的随机小数。
            # 小于 0.5 的概率是 50%，表示 50% 逃跑成功率。
            if random.random() < 0.5:
                slow_print("  你脚底抹油，成功溜走了！")
                return "flee"  # 逃跑成功，结束战斗

            # 逃跑失败：怪物追上来打你一下
            slow_print("  想跑？%s 追上来狠狠撞了你一下！" % monster["name"])
            dmg = max(1, monster["atk"] - HERO["defense"])
            HERO["hp"] -= dmg
            slow_print("  你被撞掉了 %d 点生命！" % dmg)
            if HERO["hp"] <= 0:
                return "lose"  # 被撞死了
            continue  # 逃跑失败被打了一下，算作怪物回合结束，回到玩家回合

        # ---------- 检查怪物是否被打败 ----------
        if monster["hp"] <= 0:
            slow_print("  %s 倒下了！你获得了 %d 枚金币！" % (monster["name"], monster["gold"]))
            HERO["gold"] += monster["gold"]  # 加金币
            return "win"  # 打赢了

        # ---------- 怪物回合 ----------
        if defending:
            # 玩家在防御：伤害减去 2 倍防御力（减伤更多）
            dmg = max(1, monster["atk"] - HERO["defense"] * 2)
            defending = False  # 防御只持续本回合
        else:
            # 正常情况：伤害减去主角防御力
            dmg = max(1, monster["atk"] - HERO["defense"])
        HERO["hp"] -= dmg
        slow_print("  %s 扑向你，造成 %d 点伤害！" % (monster["name"], dmg))
        if HERO["hp"] <= 0:
            return "lose"  # 主角被打死了


def main():
    """游戏主函数：打印标题、循环闯关、判断胜负、询问是否重玩"""
    # 【语法】print("""...""")：三个引号包起来的多行字符串，原样输出（包括换行）。
    print("""
============================================
         勇 者 斗 恶 龙
    -- 回合制文字冒险小游戏 --
============================================
你是小勇士「小勇」，要一路打败 5 只怪物，
赢取金币，成为传说中的大英雄！

规则：
  1 攻击    2 防御    3 喝药    4 逃跑
""")

    # 外层循环：玩完一局后可以选择再来一局
    while True:
        # 每局开始重置主角状态
        HERO["hp"] = HERO["max_hp"]  # 生命回满
        HERO["gold"] = 0              # 金币清零
        HERO["potions"] = 3           # 药水补满

        print("准备出发！按回车开始冒险...", end="")
        # 【语法】print(..., end="")：end 参数指定打印结束后加什么字符，
        # 默认是换行 "\n"，这里设为空字符串就不换行，让用户输入接在后面。
        try:
            input()  # 等用户按回车
        except EOFError:
            print()
            break  # 【语法】break：立即退出当前循环（这里退出外层 while 循环）

        victory = True  # 先假设能通关，失败了再改成 False

        # 【语法】for 索引, 元素 in enumerate(列表, 起始值):
        # enumerate 同时取出每个元素的索引和值，第二个参数指定索引从几开始（这里从 1 开始）。
        for idx, monster in enumerate(MONSTERS, 1):
            print("\n================ 第 %d 关 ================" % idx)
            result = battle(dict(monster))  # 开始战斗，传怪物数据的副本

            if result == "flee":
                # 逃跑成功：如果是最后一关（巨龙）逃跑，就算没通关
                # 【语法】len(列表)：返回列表的元素个数。这里 len(MONSTERS) = 5。
                if idx == len(MONSTERS):
                    victory = False
                    slow_print("  你看着巨龙，终究没敢上…… 你当了一回逃兵。")
                else:
                    slow_print("  你绕开了这一关的怪物，继续前行……")
                continue  # 进入下一关

            if result == "lose":
                victory = False
                break  # 被打死了，跳出关卡循环

            # 打赢了：休整，生命回满，药水补满
            HERO["hp"] = HERO["max_hp"]
            HERO["potions"] = 3
            slow_print("  你休整了一下，生命和药水都补满了！")

        # ---------- 一局结束，显示结果 ----------
        if victory:
            print("\n============================================")
            print("  恭喜你！打败火焰巨龙，通关啦！")
            print("  你一共赚到了 %d 枚金币！" % HERO["gold"])
            print("============================================")
        else:
            # 【语法】if/else：根据条件执行不同的代码块。
            if HERO["hp"] <= 0:
                print("\n  你倒下了…… 冒险失败，下次再战！")
            else:
                print("\n  你没能走完这段冒险，下次再战！")

        # 询问是否再来一局
        again = get_choice("  再来一局？(y/n) > ", {"y", "Y", "n", "N", "yes", "no"})
        # 【语法】字符串.lower()：把字符串转成全小写。
        # .startswith("n")：判断字符串是否以 "n" 开头。
        # 用户输入 n/N/no/No 都会以 n 开头，就退出游戏。
        if again.lower().startswith("n"):
            break

    print("\n  感谢游玩，勇者！再见～")


# ==================================================================
# 【语法】if __name__ == "__main__": Python 惯用写法。
# 直接运行此文件时 __name__ 是 "__main__"，会执行下面的代码；
# 被其他文件 import 时 __name__ 是文件名，不会执行。
# ==================================================================
if __name__ == "__main__":
    # main()  # 暂时注释掉主游戏循环（用户自己改的，保留）
    # 【语法】print(__name__)：打印当前模块名，直接运行时输出 "__main__"
    print(__name__)
    # 打印导入的 operateData 模块对象（用户自己加的测试代码，保留）
    print(operateData)
