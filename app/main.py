from fastapi import FastAPI, UploadFile, File
from app.models import AskRequest, AskResponse
from app.rag_pipeline import ingest_document, ask_question
from pathlib import Path
import shutil


app = FastAPI(
    title='Healthcare RAG Assistant',
    description='Local GenAI document Q&A system using FastAPI, LangChain, ChromaDB, Sentence Transformers, and Ollama.',
    version='1.0.0'
)


DATA_DIR = Path('data')
DATA_DIR.mkdir(exist_ok=True)


@app.get('/')
def home():
    return {
        'message': 'Healthcare RAG Assistant is running',
        'docs': 'Go to /docs to test the API'
    }


@app.post('/upload')
async def upload_document(file: UploadFile = File(...)):
    file_path = DATA_DIR / file.filename

    with file_path.open('wb') as buffer:
        shutil.copyfileobj(file.file, buffer)

    result = ingest_document(str(file_path))

    return {
        'filename': file.filename,
        'result': result
    }


@app.post('/ask', response_model=AskResponse)
def ask(request: AskRequest):
    answer = ask_question(request.question)

    return AskResponse(
        question=request.question,
        answer=answer
    )