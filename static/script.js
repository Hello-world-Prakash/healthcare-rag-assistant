async function uploadDocument() {
    const fileInput = document.getElementById('fileInput');
    const uploadStatus = document.getElementById('uploadStatus');

    if (!fileInput.files.length) {
        showStatus('Please select a PDF or TXT file first.', 'error');
        return;
    }

    const formData = new FormData();
    formData.append('file', fileInput.files[0]);

    showStatus('Uploading and ingesting document...', 'success');

    try {
        const response = await fetch('/upload', {
            method: 'POST',
            body: formData
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.detail || 'Upload failed');
        }

        const chunks = data.result.chunks_created;

        showStatus(
            `Uploaded successfully. Created ${chunks} document chunks.`,
            'success'
        );
    } catch (error) {
        showStatus(`Upload failed: ${error.message}`, 'error');
    }
}


async function askQuestion() {
    const questionInput = document.getElementById('questionInput');
    const answerBox = document.getElementById('answerBox');
    const loader = document.getElementById('loader');

    const question = questionInput.value.trim();

    if (!question) {
        answerBox.textContent = 'Please enter a question first.';
        return;
    }

    loader.classList.remove('hidden');
    answerBox.textContent = 'Thinking...';

    try {
        const response = await fetch('/ask', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ question })
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.detail || 'Question failed');
        }

        answerBox.textContent = data.answer;
    } catch (error) {
        answerBox.textContent = `Error: ${error.message}`;
    } finally {
        loader.classList.add('hidden');
    }
}


function setQuestion(question) {
    document.getElementById('questionInput').value = question;
}


function showStatus(message, type) {
    const uploadStatus = document.getElementById('uploadStatus');

    uploadStatus.textContent = message;
    uploadStatus.classList.remove('hidden', 'status-success', 'status-error');

    if (type === 'success') {
        uploadStatus.classList.add('status-success');
    } else {
        uploadStatus.classList.add('status-error');
    }
}