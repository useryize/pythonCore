# -*- coding: utf-8 -*-
# 临时测试脚本：实测公开 API 可访问性（用完可删）
import httpx

tests = {
    "一言(中文句子)": "https://v1.hitokoto.cn/?encode=json",
    "GitHub用户信息": "https://api.github.com/users/octocat",
    "JSONPlaceholder任务": "https://jsonplaceholder.typicode.com/todos/1",
    "随机狗狗图片": "https://dog.ceo/api/breeds/image/random",
    "Open-Meteo武汉天气": "https://api.open-meteo.com/v1/forecast?latitude=30.59&longitude=114.31&current_weather=true",
}
for name, url in tests.items():
    try:
        r = httpx.get(url, timeout=10)
        text = r.text[:80].replace("\n", " ")
        print(f"[OK]   {name}: {r.status_code} -> {text}")
    except Exception as e:
        print(f"[FAIL] {name}: {type(e).__name__}")

try:
    r = httpx.post("https://httpbin.org/post", json={"msg": "test"}, timeout=10)
    print(f"[OK]   POST httpbin(step2): {r.status_code} -> 回显json={r.json().get('json')}")
except Exception as e:
    print(f"[FAIL] POST httpbin: {type(e).__name__}")
