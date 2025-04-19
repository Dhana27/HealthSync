# Updated token_utils.py
import time
import jwt
from django.conf import settings

def generate_token_for_user(user, role):
    """
    Generate a 100ms token for Prebuilt using static room_code per role.
    """
    room_code = settings.HMS_ROOM_CODES.get(role)
    if not room_code:
        raise ValueError(f"No room code configured for role: {role}")

    payload = {
        "access_key": settings.HMS_ACCESS_KEY,
        "room_code": room_code,
        "user_id": str(user.id),
        "role": role,
        "type": "room-code",
        "version": 2,
        "iat": int(time.time()),
        "exp": int(time.time()) + 3600,
    }

    return jwt.encode(payload, settings.HMS_SECRET, algorithm="HS256")


