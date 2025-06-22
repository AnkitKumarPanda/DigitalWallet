import base64
import bcrypt
from flask import request
from models import User
from app import db

def hash_password(password):
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

def check_password(password, hashed):
    return bcrypt.checkpw(password.encode('utf-8'), hashed)

def authenticate():
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Basic '):
        return None
    decoded = base64.b64decode(auth_header.split()[1]).decode('utf-8')
    username, password = decoded.split(':')
    user = User.query.filter_by(username=username).first()
    if user and check_password(password, user.password_hash.encode('utf-8')):
        return user
    return None
