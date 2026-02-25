import jwt
from datetime import datetime, timedelta, timezone
from flask import request
from functools import wraps
import os

SECRET_KEY = os.getenv("JWT_SECRET", "mysecretkey")


def create_token(data):
    payload = {
        "_id": data["_id"],
        "user_id": data["_id"],  
        "email": data["email"],
        "name": data["name"],
        "role": data["role"],
        "exp": datetime.now(timezone.utc) + timedelta(hours=24),
        "iat": datetime.now(timezone.utc)
    }
    return jwt.encode(payload, SECRET_KEY, algorithm="HS256")


def decode_token(token):
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None

        if "Authorization" in request.headers:
            token = request.headers.get("Authorization").replace("Bearer ", "")

        if not token:
            return {"success": False, "message": "Token missing"}, 401

        decoded = decode_token(token)

        if not decoded:
            return {"success": False, "message": "Invalid or expired token"}, 401

        # Pass decoded user data as first argument to the wrapped function
        return f(decoded, *args, **kwargs)

    return decorated
