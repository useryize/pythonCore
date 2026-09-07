import httpx
def get_JSON():
    res = httpx.get(
        'https://api.open-meteo.com/v1/forecast?latitude=30.59&longitude=114.31&current_weather=true')
    res.json()


def POST_JSON():
    payload = {
        "name": "XXX",
        "message": "你好，我是一名前端开发，正在学 Python 转 Agent！",
    }
    res = httpx.post("https://httpbin.org/post", json=payload, timeout=30)
    data =res.json()
    print("",  data["headers"].get("Content-Type"))
    
    
POST_JSON()
