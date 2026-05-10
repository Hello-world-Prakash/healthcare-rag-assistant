async function uploadDocument() {
    const fileInput = document.getElementById('fileInput');
    const patientIdInput = document.getElementById('patientIdInput');

    const patientId = patientIdInput.value.trim();

    if (!patientId) {
        showStatus('uploadStatus', 'Please enter a Patient ID first.', 'error');
        return;
    }

    if (!fileInput.files.length) {
        showStatus('uploadStatus', 'Please select a PDF or TXT file first.', 'error');
        return;
    }

    const formData = new FormData();
    formData.append('patient_id', patientId);
    formData.append('file', fileInput.files[0]);

    showStatus('uploadStatus', 'Uploading and ingesting patient document...', 'success');

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
            'uploadStatus',
            `Uploaded patient ${patientId} successfully. Created ${chunks} chunks.`,
            'success'
        );
    } catch (error) {
        showStatus('uploadStatus', `Upload failed: ${error.message}`, 'error');
    }
}


async function uploadBulkDocument() {
    const bulkFileInput = document.getElementById('bulkFileInput');

    if (!bulkFileInput.files.length) {
        showStatus('bulkUploadStatus', 'Please select a bulk PDF or TXT file first.', 'error');
        return;
    }

    const formData = new FormData();
    formData.append('file', bulkFileInput.files[0]);

    showStatus('bulkUploadStatus', 'Uploading and processing bulk patient document...', 'success');

    try {
        const response = await fetch('/upload-bulk', {
            method: 'POST',
            body: formData
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.detail || 'Bulk upload failed');
        }

        const result = data.result;

        showStatus(
            'bulkUploadStatus',
            `Bulk upload complete. Found ${result.patients_found} patients, ingested ${result.patients_ingested}, created ${result.chunks_created} chunks. Skipped existing: ${result.skipped_existing_patients.length}`,
            'success'
        );
    } catch (error) {
        showStatus('bulkUploadStatus', `Bulk upload failed: ${error.message}`, 'error');
    }
}


async function askQuestion() {
    const patientIdInput = document.getElementById('askPatientIdInput');
    const questionInput = document.getElementById('questionInput');
    const answerBox = document.getElementById('answerBox');
    const loader = document.getElementById('loader');

    const patientId = patientIdInput.value.trim();
    const question = questionInput.value.trim();

    if (!patientId) {
        answerBox.textContent = 'Please enter a Patient ID first.';
        return;
    }

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
            body: JSON.stringify({
                patient_id: patientId,
                question: question
            })
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


function showStatus(elementId, message, type) {
    const statusBox = document.getElementById(elementId);

    statusBox.textContent = message;
    statusBox.classList.remove('hidden', 'status-success', 'status-error');

    if (type === 'success') {
        statusBox.classList.add('status-success');
    } else {
        statusBox.classList.add('status-error');
    }
}