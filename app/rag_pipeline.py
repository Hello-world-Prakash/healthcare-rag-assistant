from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from langchain_ollama import OllamaLLM
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.documents import Document
from pathlib import Path
import re


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


def extract_field(text: str, field_name: str):
    """
    Extracts a field value from text.

    Example:
    Patient Name: Olivia Martinez
    Member ID: MBR-900145
    """

    pattern = rf'{field_name}\s*:\s*(.+)'
    match = re.search(pattern, text, flags=re.IGNORECASE)

    if match:
        return match.group(1).strip()

    return 'Not available'


def extract_patient_metadata(record_text: str, fallback_patient_id: str = None):
    """
    Extracts patient-level identity fields from a record.
    These values are stored as metadata and also added into chunk context.
    """

    patient_id = extract_field(record_text, 'Patient ID')

    if patient_id == 'Not available' and fallback_patient_id:
        patient_id = fallback_patient_id

    return {
        'patient_id': patient_id,
        'patient_name': extract_field(record_text, 'Patient Name'),
        'mrn': extract_field(record_text, 'MRN'),
        'member_id': extract_field(record_text, 'Member ID')
    }


def build_patient_context_header(metadata: dict):
    """
    Adds patient identity information into every chunk.
    This helps the model answer naturally with patient name/member ID
    even when the retrieved chunk is mainly about medication, billing, or allergies.
    """

    return f"""
Patient Name: {metadata.get('patient_name', 'Not available')}
Patient ID: {metadata.get('patient_id', 'Not available')}
MRN: {metadata.get('mrn', 'Not available')}
Member ID: {metadata.get('member_id', 'Not available')}
""".strip()


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
    """
    Validation for single-patient upload.
    Blocks duplicate patient IDs and duplicate files.
    """

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


def split_records_by_patient_id(full_text: str):
    """
    Splits a bulk document into separate patient records.

    Expected format:
    Patient ID: SYN-3001
    ...
    Patient ID: SYN-3002
    ...
    """

    pattern = r'(Patient ID:\s*([A-Za-z0-9_-]+).*?)(?=Patient ID:\s*[A-Za-z0-9_-]+|$)'

    matches = re.findall(
        pattern,
        full_text,
        flags=re.DOTALL | re.IGNORECASE
    )

    patient_records = []

    for record_text, patient_id in matches:
        patient_records.append({
            'patient_id': patient_id.strip(),
            'text': record_text.strip()
        })

    return patient_records


def ingest_document(file_path: str, patient_id: str, file_name: str, file_hash: str):
    """
    Ingests one file for one patient.
    Every chunk gets patient_id metadata and identity context.
    """

    documents = load_document(file_path)

    full_text = '\n\n'.join([doc.page_content for doc in documents])

    patient_metadata = extract_patient_metadata(
        record_text=full_text,
        fallback_patient_id=patient_id
    )

    patient_context_header = build_patient_context_header(patient_metadata)

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=800,
        chunk_overlap=150
    )

    chunks = splitter.split_documents(documents)

    enriched_chunks = []

    for chunk in chunks:
        enriched_text = f"""
{patient_context_header}

Record Context:
{chunk.page_content}
""".strip()

        enriched_chunk = Document(
            page_content=enriched_text,
            metadata={
                'patient_id': patient_id,
                'patient_name': patient_metadata.get('patient_name', 'Not available'),
                'mrn': patient_metadata.get('mrn', 'Not available'),
                'member_id': patient_metadata.get('member_id', 'Not available'),
                'file_name': file_name,
                'file_hash': file_hash,
                'source_type': 'single_patient_upload'
            }
        )

        enriched_chunks.append(enriched_chunk)

    vector_store = get_vector_store()
    vector_store.add_documents(enriched_chunks)

    return {
        'message': 'Patient document ingested successfully',
        'patient_id': patient_id,
        'patient_name': patient_metadata.get('patient_name', 'Not available'),
        'mrn': patient_metadata.get('mrn', 'Not available'),
        'member_id': patient_metadata.get('member_id', 'Not available'),
        'file_name': file_name,
        'chunks_created': len(enriched_chunks)
    }


def ingest_bulk_patient_document(file_path: str, file_name: str, file_hash: str):
    """
    Ingests one file containing multiple patient records.
    Each patient section is separated first, then chunked independently.
    Existing patient IDs are skipped.
    """

    documents = load_document(file_path)

    full_text = '\n\n'.join([doc.page_content for doc in documents])

    patient_records = split_records_by_patient_id(full_text)

    if not patient_records:
        return {
            'message': 'No patient records found. Make sure each record starts with Patient ID: SYN-1001 format.',
            'patients_found': 0,
            'patients_ingested': 0,
            'chunks_created': 0,
            'ingested_patient_ids': [],
            'skipped_existing_patients': []
        }

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=800,
        chunk_overlap=150
    )

    all_chunks = []
    skipped_existing_patients = []
    ingested_patient_ids = []

    for record in patient_records:
        patient_id = record['patient_id']

        if patient_id_exists(patient_id):
            skipped_existing_patients.append(patient_id)
            continue

        patient_metadata = extract_patient_metadata(
            record_text=record['text'],
            fallback_patient_id=patient_id
        )

        patient_context_header = build_patient_context_header(patient_metadata)

        patient_doc = Document(
            page_content=record['text'],
            metadata={
                'patient_id': patient_id,
                'patient_name': patient_metadata.get('patient_name', 'Not available'),
                'mrn': patient_metadata.get('mrn', 'Not available'),
                'member_id': patient_metadata.get('member_id', 'Not available'),
                'file_name': file_name,
                'file_hash': file_hash,
                'source_type': 'bulk_patient_upload'
            }
        )

        chunks = splitter.split_documents([patient_doc])

        for chunk in chunks:
            enriched_text = f"""
{patient_context_header}

Record Context:
{chunk.page_content}
""".strip()

            enriched_chunk = Document(
                page_content=enriched_text,
                metadata={
                    'patient_id': patient_id,
                    'patient_name': patient_metadata.get('patient_name', 'Not available'),
                    'mrn': patient_metadata.get('mrn', 'Not available'),
                    'member_id': patient_metadata.get('member_id', 'Not available'),
                    'file_name': file_name,
                    'file_hash': file_hash,
                    'source_type': 'bulk_patient_upload'
                }
            )

            all_chunks.append(enriched_chunk)

        ingested_patient_ids.append(patient_id)

    vector_store = get_vector_store()

    if all_chunks:
        vector_store.add_documents(all_chunks)

    return {
        'message': 'Bulk patient document processed successfully',
        'patients_found': len(patient_records),
        'patients_ingested': len(ingested_patient_ids),
        'chunks_created': len(all_chunks),
        'ingested_patient_ids': ingested_patient_ids,
        'skipped_existing_patients': skipped_existing_patients
    }


def ask_question(patient_id: str, question: str):
    """
    Retrieves chunks only for the requested patient_id.
    If patient_id does not exist, returns a direct fallback.
    Answers naturally and includes patient name when available.
    """

    vector_store = get_vector_store()

    retriever = vector_store.as_retriever(
        search_kwargs={
            'k': 5,
            'filter': {
                'patient_id': patient_id
            }
        }
    )

    docs = retriever.invoke(question)

    if not docs:
        return f"I could not find any uploaded records for patient ID {patient_id}."

    context = '\n\n'.join([doc.page_content for doc in docs])

    prompt = ChatPromptTemplate.from_template(
        '''
        You are a helpful medical document assistant.

        Ground rules:
        1. Use only the provided context.
        2. The context belongs only to patient ID: {patient_id}.
        3. Do not use information from other patients.
        4. Answer naturally in a clear sentence or short paragraph.
        5. Do not use a fixed template unless the user asks for a list or table.
        6. When the answer includes insurance, billing, medication, allergy, diagnosis, medical history, claim, invoice, or plan details, include the patient's name if it is available in the context.
        7. If the patient's name is not available, mention the available identifier such as patient ID, MRN, or member ID.
        8. If the requested detail is not available in the context, say it is not available in the uploaded record.
        9. Do not invent missing values.
        10. Keep the answer concise and easy to verify.

        Examples of good answer style:
        - The patient is Olivia Martinez, and her insurance member ID is MBR-900145.
        - The patient is Ethan Walker, and he is taking Tiotropium inhaler, Albuterol inhaler, and Atorvastatin.
        - The patient is Grace Kim, and her listed allergies are Latex and Shellfish.
        - The patient is Daniel Harris, and the total bill is $500. Insurance paid $390, and the patient responsibility is $110.

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
