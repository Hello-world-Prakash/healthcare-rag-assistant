from datetime import datetime, timedelta
from fastapi import HTTPException, Depends
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
import hashlib


SECRET_KEY = "local-demo-secret-key-change-this-later"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login")


def hash_password(password: str):
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


# Demo user for local project
fake_user = {
    "username": "admin",
    "hashed_password": hash_password("admin123")
}


def verify_password(plain_password: str, hashed_password: str):
    return hash_password(plain_password) == hashed_password


def authenticate_user(username: str, password: str):
    if username != fake_user["username"]:
        return False

    if not verify_password(password, fake_user["hashed_password"]):
        return False

    return {
        "username": username
    }


def create_access_token(data: dict):
    to_encode = data.copy()

    expire = datetime.utcnow() + timedelta(
        minutes=ACCESS_TOKEN_EXPIRE_MINUTES
    )

    to_encode.update({"exp": expire})

    encoded_jwt = jwt.encode(
        to_encode,
        SECRET_KEY,
        algorithm=ALGORITHM
    )

    return encoded_jwt


def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=401,
        detail="Invalid or expired authentication token",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM]
        )

        username: str = payload.get("sub")

        if username is None:
            raise credentials_exception

        return {
            "username": username
        }

    except JWTError:
        raise credentials_exception