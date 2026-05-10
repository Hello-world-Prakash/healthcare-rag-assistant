from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from langchain_ollama import OllamaLLM
from langchain_core.prompts import ChatPromptTemplate
from pathlib import Path


CHROMA_DIR = 'chroma_db'

embedding_model = HuggingFaceEmbeddings(
    model_name='sentence-transformers/all-MiniLM-L6-v2'
)

llm = OllamaLLM(
    model='llama3.2:3b'
)


def get_vector_store():
    return Chroma(
        persist_directory=CHROMA_DIR,
        embedding_function=embedding_model
    )


def load_document(file_path: str):
    path = Path(file_path)

    if path.suffix.lower() == '.pdf':
        loader = PyPDFLoader(file_path)
        return loader.load()

    if path.suffix.lower() == '.txt':
        loader = TextLoader(file_path, encoding='utf-8')
        return loader.load()

    raise ValueError('Only PDF and TXT files are supported.')


def patient_id_exists(patient_id: str) -> bool:
    vector_store = get_vector_store()

    result = vector_store.get(
        where={'patient_id': patient_id},
        limit=1
    )

    return bool(result and result.get('ids'))


def file_hash_exists(file_hash: str) -> bool:
    vector_store = get_vector_store()

    result = vector_store.get(
        where={'file_hash': file_hash},
        limit=1
    )

    return bool(result and result.get('ids'))


def validate_patient_upload(patient_id: str, file_hash: str):
    if patient_id_exists(patient_id):
        return {
            'is_valid': False,
            'reason': f'Patient ID {patient_id} already exists. Please use a unique Patient ID.'
        }

    if file_hash_exists(file_hash):
        return {
            'is_valid': False,
            'reason': 'This patient document/data was already uploaded before. Please use a different document.'
        }

    return {
        'is_valid': True,
        'reason': 'Patient upload is valid.'
    }


def ingest_document(file_path: str, patient_id: str, file_name: str, file_hash: str):
    documents = load_document(file_path)

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=800,
        chunk_overlap=150
    )

    chunks = splitter.split_documents(documents)

    for chunk in chunks:
        chunk.metadata['patient_id'] = patient_id
        chunk.metadata['file_name'] = file_name
        chunk.metadata['file_hash'] = file_hash

    vector_store = get_vector_store()

    vector_store.add_documents(chunks)

    return {
        'message': 'Patient document ingested successfully',
        'patient_id': patient_id,
        'file_name': file_name,
        'chunks_created': len(chunks)
    }


def ask_question(patient_id: str, question: str):
    vector_store = get_vector_store()

    retriever = vector_store.as_retriever(
        search_kwargs={
            'k': 4,
            'filter': {
                'patient_id': patient_id
            }
        }
    )

    docs = retriever.invoke(question)

    context = '\n\n'.join([doc.page_content for doc in docs])

    prompt = ChatPromptTemplate.from_template(
        '''
        You are a helpful medical document assistant.

        Use only the context below to answer the user's question.
        The context belongs only to patient ID: {patient_id}.

        Do not use information from other patients.
        If the user asks for a summary, summarize only this patient's available context.

        If the context is empty or does not contain the answer, say:
        "I could not find enough information for this patient in the uploaded records."

        Context:
        {context}

        Question:
        {question}

        Answer:
        '''
    )

    final_prompt = prompt.format(
        patient_id=patient_id,
        context=context,
        question=question
    )

    answer = llm.invoke(final_prompt)

    return answer