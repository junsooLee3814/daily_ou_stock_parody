import requests

webhook_url = "https://hook.eu2.make.com/hyxr8p6n8m9f6fndl7psoufwfab1w6a9"

data = {
    "title": "2025-07-17 자동증권뉴스",
    "description": "AI가 만든 자동증권 패러디 영상",
    "video_url": "https://drive.google.com/uc?export=download&id=1qfb2U5lDD3zPhzX6xdh2UDmCVw8mfDQE"
}

response = requests.post(webhook_url, json=data)
print("전송 결과:", response.status_code)