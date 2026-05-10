from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from app.models import AskRequest, AskResponse
from app.rag_pipeline import (
    ingest_document,
    ingest_bulk_patient_document,
    ask_question,
    validate_patient_upload
)
from pathlib import Path
import hashlib


app = FastAPI(
    title='Healthcare RAG Assistant',
    description='Local GenAI document Q&A system using FastAPI, LangChain, ChromaDB, Sentence Transformers, and Ollama.',
    version='2.2.0'
)


DATA_DIR = Path('data')
DATA_DIR.mkdir(exist_ok=True)

app.mount('/static', StaticFiles(directory='static'), name='static')


@app.get('/')
def home():
    return FileResponse('static/index.html')


@app.post('/upload')
async def upload_document(
    patient_id: str = Form(...),
    file: UploadFile = File(...)
):
    file_bytes = await file.read()
    file_hash = hashlib.sha256(file_bytes).hexdigest()

    validation = validate_patient_upload(
        patient_id=patient_id,
        file_hash=file_hash
    )

    if not validation['is_valid']:
        raise HTTPException(
            status_code=409,
            detail=validation['reason']
        )

    safe_patient_id = patient_id.replace(' ', '_')
    file_path = DATA_DIR / f'{safe_patient_id}_{file.filename}'

    with file_path.open('wb') as buffer:
        buffer.write(file_bytes)

    result = ingest_document(
        file_path=str(file_path),
        patient_id=patient_id,
        file_name=file.filename,
        file_hash=file_hash
    )

    return {
        'patient_id': patient_id,
        'filename': file.filename,
        'result': result
    }


@app.post('/upload-bulk')
async def upload_bulk_document(
    file: UploadFile = File(...)
):
    file_bytes = await file.read()
    file_hash = hashlib.sha256(file_bytes).hexdigest()

    file_path = DATA_DIR / f'bulk_{file.filename}'

    with file_path.open('wb') as buffer:
        buffer.write(file_bytes)

    result = ingest_bulk_patient_document(
        file_path=str(file_path),
        file_name=file.filename,
        file_hash=file_hash
    )

    return {
        'filename': file.filename,
        'result': result
    }


@app.post('/ask', response_model=AskResponse)
def ask(request: AskRequest):
    answer = ask_question(
        patient_id=request.patient_id,
        question=request.question
    )

    return AskResponse(
        patient_id=request.patient_id,
        question=request.question,
        answer=answer
    )