from pydantic import BaseModel


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str


class AskRequest(BaseModel):
    patient_id: str
    question: str


class AskResponse(BaseModel):
    patient_id: str
    question: str
    answer: str