from pydantic import BaseModel


class AskRequest(BaseModel):
    patient_id: str
    question: str


class AskResponse(BaseModel):
    patient_id: str
    question: str
    answer: str