import jwt
from passlib.hash import argon2
import os
import datetime

def hash_password(pw: str):
    hasher = argon2(salt=os.urandom(128), rounds=8)
    hash = hasher.hash(pw)
    return hash, hasher.salt, hasher.rounds


def verify_password(pw: str, hash: str):
    return argon2.verify(pw, hash)


def create_token(uuid):
    payload = {"exp":datetime.datetime.utcnow() + datetime.timedelta(days=10),
               "iat":datetime.datetime.utcnow(),
               "iss":"hexicast-server",
               "sub":uuid}
    return jwt.encode(payload, os.getenv('token_secret'), algorithm="HS256")

def validate_token(token):
    try:
        payload = jwt.decode(token, os.getenv('SECRET_KEY'))
        return payload['sub']

    except jwt.ExpiredSignatureError:
        return ""
    except jwt.InvalidTokenError:
        return ""

