import requests
import time
import jwt  
from django.conf import settings 

APP_ACCESS_KEY = settings.HMS_ACCESS_KEY
APP_SECRET = settings.HMS_SECRET
TEMPLATE_ID = settings.HMS_TEMPLATE_ID


def create_room():
    payload = {
        "access_key": APP_ACCESS_KEY,
        "type": "management",
        "version": 2,
        "iat": int(time.time()),
        "exp": int(time.time()) + 86400,
        "jti": "room_creator"
    }

    token = jwt.encode(payload, APP_SECRET, algorithm="HS256")

    url = "https://api.100ms.live/v2/rooms"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    data = {
        "name": f"consult_room_{int(time.time())}",  # unique room name
        "description": "Doctor-Patient consultation",
        "template_id": TEMPLATE_ID
    }

    response = requests.post(url, json=data, headers=headers)
    data = response.json()
    room_code_p = data["name"]
    print(f"room_code from create room: {room_code_p}")
    return {
    "room_code": data["name"],  # for use in iframe URL
    "room_id": data["id"]       # for token generation
    }
