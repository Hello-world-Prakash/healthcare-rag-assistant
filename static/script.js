console.log("script.js loaded successfully");

/* =========================
   AUTH HELPERS
========================= */

function getToken() {
    return localStorage.getItem("access_token");
}

function authHeaders() {
    return {
        "Authorization": `Bearer ${getToken()}`
    };
}

function checkAuthState() {
    const token = getToken();

    const loginSection = document.getElementById("loginSection");
    const appSection = document.getElementById("appSection");
    const loggedInUser = document.getElementById("loggedInUser");

    if (!loginSection || !appSection) {
        console.error("Login section or app section not found.");
        return;
    }

    if (token) {
        loginSection.classList.add("hidden");
        appSection.classList.remove("hidden");

        if (loggedInUser) {
            loggedInUser.textContent = "Logged in";
        }
    } else {
        loginSection.classList.remove("hidden");
        appSection.classList.add("hidden");
    }
}

/* =========================
   LOGIN / LOGOUT
========================= */

async function loginUser() {
    console.log("Login button clicked");

    const usernameInput = document.getElementById("usernameInput");
    const passwordInput = document.getElementById("passwordInput");

    if (!usernameInput || !passwordInput) {
        alert("Login fields are missing in HTML.");
        return;
    }

    const username = usernameInput.value.trim();
    const password = passwordInput.value.trim();

    if (!username || !password) {
        showStatus("loginStatus", "Please enter both username and password.", "error");
        return;
    }

    showStatus("loginStatus", "Checking credentials...", "success");

    try {
        const response = await fetch("/login", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                username: username,
                password: password
            })
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.detail || "Login failed");
        }

        localStorage.setItem("access_token", data.access_token);
	
	usernameInput.value = "";
	passwordInput.value = "";

        showStatus("loginStatus", "Login successful.", "success");

        setTimeout(() => {
            checkAuthState();
        }, 400);

    } catch (error) {
        console.error("Login error:", error);
        showStatus("loginStatus", `Login failed: ${error.message}`, "error");
    }
}

function logoutUser() {
    localStorage.removeItem("access_token");

    const usernameInput = document.getElementById("usernameInput");
    const passwordInput = document.getElementById("passwordInput");
    const loginStatus = document.getElementById("loginStatus");
    const answerBox = document.getElementById("answerBox");
    
    if (usernameInput) {
	usernameInput.value = "";
    }

    if (passwordInput) {
	passwordInput.value = "";
    }

    if (loginStatus) {
	loginStatus.textContent ="";
	loginStatus.classList.add("hidden");
	loginStatus.classList.remove("status-success", "status-error");
    }
    if (answerBox) {
        answerBox.textContent = "Your answer will appear here.";
    }

    checkAuthState();
}

/* =========================
   SINGLE PATIENT UPLOAD
========================= */

async function uploadDocument() {
    const fileInput = document.getElementById("fileInput");
    const patientIdInput = document.getElementById("patientIdInput");

    const patientId = patientIdInput.value.trim();

    if (!patientId) {
        showStatus("uploadStatus", "Please enter a Patient ID first.", "error");
        return;
    }

    if (!fileInput.files.length) {
        showStatus("uploadStatus", "Please select a PDF or TXT file first.", "error");
        return;
    }

    const formData = new FormData();
    formData.append("patient_id", patientId);
    formData.append("file", fileInput.files[0]);

    showStatus("uploadStatus", "Uploading and ingesting patient document...", "success");

    try {
        const response = await fetch("/upload", {
            method: "POST",
            headers: authHeaders(),
            body: formData
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.detail || "Upload failed");
        }

        const chunks = data.result.chunks_created;

        showStatus(
            "uploadStatus",
            `Uploaded patient ${patientId} successfully. Created ${chunks} chunks.`,
            "success"
        );

    } catch (error) {
        console.error("Single upload error:", error);
        showStatus("uploadStatus", `Upload failed: ${error.message}`, "error");
    }
}

/* =========================
   BULK PATIENT UPLOAD
========================= */

async function uploadBulkDocument() {
    const bulkFileInput = document.getElementById("bulkFileInput");

    if (!bulkFileInput.files.length) {
        showStatus("bulkUploadStatus", "Please select a bulk PDF or TXT file first.", "error");
        return;
    }

    const formData = new FormData();
    formData.append("file", bulkFileInput.files[0]);

    showStatus("bulkUploadStatus", "Uploading and processing bulk patient document...", "success");

    try {
        const response = await fetch("/upload-bulk", {
            method: "POST",
            headers: authHeaders(),
            body: formData
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.detail || "Bulk upload failed");
        }

        const result = data.result;

        showStatus(
            "bulkUploadStatus",
            `Bulk upload complete. Found ${result.patients_found} patients, ingested ${result.patients_ingested}, created ${result.chunks_created} chunks. Skipped existing: ${result.skipped_existing_patients.length}`,
            "success"
        );

    } catch (error) {
        console.error("Bulk upload error:", error);
        showStatus("bulkUploadStatus", `Bulk upload failed: ${error.message}`, "error");
    }
}

/* =========================
   ASK QUESTION
========================= */

async function askQuestion() {
    const patientIdInput = document.getElementById("askPatientIdInput");
    const questionInput = document.getElementById("questionInput");
    const answerBox = document.getElementById("answerBox");
    const loader = document.getElementById("loader");

    const patientId = patientIdInput.value.trim();
    const question = questionInput.value.trim();

    if (!patientId) {
        answerBox.textContent = "Please enter a Patient ID first.";
        return;
    }

    if (!question) {
        answerBox.textContent = "Please enter a question first.";
        return;
    }

    loader.classList.remove("hidden");
    answerBox.textContent = "Thinking...";

    try {
        const response = await fetch("/ask", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                ...authHeaders()
            },
            body: JSON.stringify({
                patient_id: patientId,
                question: question
            })
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.detail || "Question failed");
        }

        answerBox.textContent = data.answer;

    } catch (error) {
        console.error("Ask question error:", error);
        answerBox.textContent = `Error: ${error.message}`;
    } finally {
        loader.classList.add("hidden");
    }
}

/* =========================
   UI HELPERS
========================= */

function setQuestion(question) {
    const questionInput = document.getElementById("questionInput");
    questionInput.value = question;
}

function showStatus(elementId, message, type) {
    const statusBox = document.getElementById(elementId);

    if (!statusBox) {
        alert(message);
        return;
    }

    statusBox.textContent = message;
    statusBox.classList.remove("hidden", "status-success", "status-error");

    if (type === "success") {
        statusBox.classList.add("status-success");
    } else {
        statusBox.classList.add("status-error");
    }
}

/* =========================
   PAGE LOAD
========================= */

document.addEventListener("DOMContentLoaded", function () {
    console.log("DOM loaded successfully");
    checkAuthState();
});
