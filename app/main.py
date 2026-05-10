from fastapi import FastAPI, UploadFile, File, Form
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from app.models import AskRequest, AskResponse
from app.rag_pipeline import ingest_document, ask_question
from pathlib import Path
import shutil


app = FastAPI(
    title='Healthcare RAG Assistant',
    description='Local GenAI document Q&A system using FastAPI, LangChain, ChromaDB, Sentence Transformers, and Ollama.',
    version='2.0.0'
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
    file_path = DATA_DIR / file.filename

    with file_path.open('wb') as buffer:
        shutil.copyfileobj(file.file, buffer)

    result = ingest_document(
        file_path=str(file_path),
        patient_id=patient_id,
        file_name=file.filename
    )

    return {
        'patient_id': patient_id,
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