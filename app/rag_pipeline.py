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


def load_document(file_path: str):
    path = Path(file_path)

    if path.suffix.lower() == '.pdf':
        loader = PyPDFLoader(file_path)
        return loader.load()

    if path.suffix.lower() == '.txt':
        loader = TextLoader(file_path, encoding='utf-8')
        return loader.load()

    raise ValueError('Only PDF and TXT files are supported.')


def ingest_document(file_path: str, patient_id: str, file_name: str):
    documents = load_document(file_path)

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=800,
        chunk_overlap=150
    )

    chunks = splitter.split_documents(documents)

    for chunk in chunks:
        chunk.metadata['patient_id'] = patient_id
        chunk.metadata['file_name'] = file_name

    vector_store = Chroma(
        persist_directory=CHROMA_DIR,
        embedding_function=embedding_model
    )

    vector_store.add_documents(chunks)

    return {
        'message': 'Patient document ingested successfully',
        'patient_id': patient_id,
        'file_name': file_name,
        'chunks_created': len(chunks)
    }


def ask_question(patient_id: str, question: str):
    vector_store = Chroma(
        persist_directory=CHROMA_DIR,
        embedding_function=embedding_model
    )

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