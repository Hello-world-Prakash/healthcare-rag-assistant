\# Healthcare RAG Assistant



A small local Generative AI / RAG system built with:



\- Python

\- FastAPI

\- LangChain

\- ChromaDB

\- Sentence Transformers

\- Ollama

\- Pydantic



\## What this project does



This project allows users to upload a PDF or text document and ask questions about it.



The system follows a RAG flow:



1\. Upload document

2\. Load document

3\. Split document into chunks

4\. Convert chunks into embeddings

5\. Store embeddings in ChromaDB

6\. Retrieve relevant chunks based on user question

7\. Send retrieved context to local LLM using Ollama

8\. Return grounded answer through FastAPI



\## Architecture



```text

PDF/TXT Document

&#x20;   ↓

Document Loader

&#x20;   ↓

Text Chunking

&#x20;   ↓

Sentence Transformer Embeddings

&#x20;   ↓

ChromaDB Vector Store

&#x20;   ↓

Retriever

&#x20;   ↓

Prompt Template

&#x20;   ↓

Ollama Local LLM

&#x20;   ↓

FastAPI Response

