const API_BASE = 'http://localhost:8080/api';

const state = {
    token: null,
    role: null,
    tasks: [],
    selectedCourse: '',
    selectedLab: '',
    selectedTask: ''
};

const UI = {
    loginSection: document.getElementById('loginSection'),
    submissionSection: document.getElementById('submissionSection'),
    studentSubmit: document.getElementById('studentSubmit'),
    teacherImport: document.getElementById('teacherImport'),
    email: document.getElementById('email'),
    password: document.getElementById('password'),
    expiresIn: document.getElementById('expiresIn'),
    expiresInCustom: document.getElementById('expiresInCustom'),
    btnLogin: document.getElementById('btnLogin'),
    btnLogout: document.getElementById('btnLogout'),
    btnSubmit: document.getElementById('btnSubmit'),
    btnCopyMarkdown: document.getElementById('btnCopyMarkdown'),
    courseSelect: document.getElementById('courseSelect'),
    labSelect: document.getElementById('labSelect'),
    taskSelect: document.getElementById('taskSelect'),
    status: document.getElementById('status')
};

function parseJwt(token) {
    try {
        const base64Url = token.split('.')[1];
        const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
        const jsonPayload = decodeURIComponent(atob(base64).split('').map(function(c) {
            return '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2);
        }).join(''));

        return JSON.parse(jsonPayload);
    } catch (e) {
        return null;
    }
}

function getUserRole(token) {
    const payload = parseJwt(token);
    return payload?.role || 'student';
}

function updateUserNameDisplay() {
    if (state.token) {
        const payload = parseJwt(state.token);
        const fullName = payload?.full_name || payload?.sub || "Пользователь";
        document.getElementById('userName').textContent = fullName;
    } else {
        document.getElementById('userName').textContent = "";
    }
}

function showStatus(message, type = 'info') {
    UI.status.textContent = message;
    UI.status.className = `status-${type}`;
    UI.status.classList.remove('hidden');
}

function hideStatus() {
    UI.status.classList.add('hidden');
}

async function init() {
    const data = await chrome.storage.local.get(['token']);
    if (data.token) {
        state.token = data.token;
        state.role = getUserRole(data.token);
        updateUserNameDisplay();
        showSubmissionForm();
    } else {
        showLoginForm();
    }
}

function showLoginForm() {
    UI.loginSection.classList.remove('hidden');
    UI.submissionSection.classList.add('hidden');
}

async function showSubmissionForm() {
    UI.loginSection.classList.add('hidden');
    UI.submissionSection.classList.remove('hidden');

    if (state.role === 'teacher' || state.role === 'admin') {
        UI.studentSubmit.classList.add('hidden');
        UI.teacherImport.classList.remove('hidden');
    } else {
        UI.studentSubmit.classList.remove('hidden');
        UI.teacherImport.classList.add('hidden');
        await fetchTasks();
    }
}

async function fetchTasks() {
    try {
        const response = await fetch(`${API_BASE}/tasks/`, {
            headers: { 'Authorization': `Bearer ${state.token}` }
        });
        if (response.ok) {
            state.tasks = await response.json();
            populateCourses();
        } else if (response.status === 401) {
            logout();
        } else {
            showStatus('Ошибка загрузки задач: ' + response.status, 'error');
        }
    } catch (e) {
        showStatus('Ошибка сети: ' + e.message, 'error');
    }
}

function populateCourses() {
    const courses = [...new Set(state.tasks.map(t => t.course_name))];
    UI.courseSelect.innerHTML = '<option value="">Выберите курс...</option>' +
        courses.map(c => `<option value="${c}">${c}</option>`).join('');
    UI.courseSelect.disabled = false;
    UI.labSelect.disabled = true;
    UI.taskSelect.disabled = true;
    UI.btnSubmit.disabled = true;
}

UI.courseSelect.addEventListener('change', (e) => {
    state.selectedCourse = e.target.value;
    const labs = [...new Set(state.tasks
        .filter(t => t.course_name === state.selectedCourse)
        .map(t => t.task_group_name))];

    UI.labSelect.innerHTML = '<option value="">Выберите лабу...</option>' +
        labs.map(l => `<option value="${l}">${l}</option>`).join('');
    UI.labSelect.disabled = !state.selectedCourse;
    UI.taskSelect.disabled = true;
    UI.btnSubmit.disabled = true;
});

UI.labSelect.addEventListener('change', (e) => {
    state.selectedLab = e.target.value;
    const tasks = state.tasks.filter(t => t.course_name === state.selectedCourse && t.task_group_name === state.selectedLab);

    UI.taskSelect.innerHTML = '<option value="">Выберите задачу...</option>' +
        tasks.map(t => `<option value="${t.join_code}">${t.name}</option>`).join('');
    UI.taskSelect.disabled = !state.selectedLab;
    UI.btnSubmit.disabled = true;
});

UI.taskSelect.addEventListener('change', (e) => {
    state.selectedTask = e.target.value;
    UI.btnSubmit.disabled = !state.selectedTask;
});

UI.expiresIn.addEventListener('change', (e) => {
    if (e.target.value === 'custom') {
        UI.expiresInCustom.classList.remove('hidden');
    } else {
        UI.expiresInCustom.classList.add('hidden');
    }
});

UI.btnLogin.addEventListener('click', async () => {
    const email = UI.email.value;
    const password = UI.password.value;
    
    let expiresIn;
    if (UI.expiresIn.value === 'custom') {
        expiresIn = parseInt(UI.expiresInCustom.value, 10);
        if (isNaN(expiresIn) || expiresIn <= 0) {
            showStatus('Введите корректное количество минут', 'error');
            return;
        }
    } else {
        expiresIn = parseInt(UI.expiresIn.value, 10) || 120;
    }
    
    if (!email || !password) {
        showStatus('Введите email и пароль', 'error');
        return;
    }

    UI.btnLogin.disabled = true;
    try {
        const response = await fetch(`${API_BASE}/users/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email, password, expires_in: expiresIn })
        });

        if (response.ok) {
            const data = await response.json();
            state.token = data.access_token;
            state.role = getUserRole(data.access_token);
            await chrome.storage.local.set({ token: state.token });
            updateUserNameDisplay();
            showSubmissionForm();
            hideStatus();
        } else {
            showStatus('Ошибка входа: ' + response.status, 'error');
        }
    } catch (e) {
        showStatus('Ошибка сети: ' + e.message, 'error');
    } finally {
        UI.btnLogin.disabled = false;
    }
});

async function logout() {
    state.token = null;
    state.role = null;
    await chrome.storage.local.remove(['token']);
    updateUserNameDisplay();
    showLoginForm();
    hideStatus();
}

UI.btnLogout.addEventListener('click', logout);

UI.btnSubmit.addEventListener('click', async () => {
    hideStatus();
    UI.btnSubmit.disabled = true;

    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });

    try {
        chrome.tabs.sendMessage(tab.id, { action: "scrapeCodeforces" }, async (data) => {
            if (chrome.runtime.lastError || !data) {
                await chrome.scripting.executeScript({
                    target: { tabId: tab.id },
                    files: ['content.js']
                });

                chrome.tabs.sendMessage(tab.id, { action: "scrapeCodeforces" }, async (data2) => {
                    if (data2) {
                        showStatus(`Найдено решение ${data2.submissionId} (${data2.username}). Отправка...`, 'info');
                        await handleSubmission(data2);
                    } else {
                        showStatus('Ошибка: Не удалось прочитать данные. Вы на странице посылки?', 'error');
                        UI.btnSubmit.disabled = false;
                    }
                });
            } else {
                showStatus(`Найдено решение ${data.submissionId} (${data.username}). Отправка...`, 'info');
                await handleSubmission(data);
            }
        });
    } catch (e) {
        showStatus('Ошибка: ' + e.message, 'error');
        UI.btnSubmit.disabled = false;
    }
});

async function handleSubmission(data) {
    try {
        showStatus('Отправка решения...', 'info');

        const formData = new FormData();
        formData.append('task_id', state.selectedTask);
        formData.append('language', data.lang);
        formData.append('correctness', data.points);
        formData.append('correctness_source', 'EXTERNAL_TESTING_SYSTEM');

        const fileName = `solution_${data.submissionId}.${data.lang === 'python' ? 'py' : data.lang === 'java' ? 'java' : 'cpp'}`;
        const blob = new Blob([data.sourceCode], { type: 'text/plain' });
        formData.append('files', blob, fileName);

        const response = await fetch(`${API_BASE}/submissions/`, {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${state.token}` },
            body: formData
        });

        if (response.ok) {
            showStatus('Решение успешно отправлено!', 'success');
        } else {
            const err = await response.text();
            showStatus('Ошибка отправки: ' + response.status + ' ' + err, 'error');
        }
    } catch (e) {
        showStatus('Ошибка сети: ' + e.message, 'error');
    } finally {
        UI.btnSubmit.disabled = false;
    }
}

UI.btnCopyMarkdown.addEventListener('click', async () => {
    hideStatus();
    UI.btnCopyMarkdown.disabled = true;

    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });

    try {
        chrome.tabs.sendMessage(tab.id, { action: "scrapeProblem" }, async (data) => {
            if (chrome.runtime.lastError || !data) {
                await chrome.scripting.executeScript({
                    target: { tabId: tab.id },
                    files: ['content.js']
                });

                chrome.tabs.sendMessage(tab.id, { action: "scrapeProblem" }, (data2) => {
                    if (data2) {
                        copyToClipboard(formatAsMarkdown(data2));
                    } else {
                        showStatus('Ошибка: Не удалось прочитать задачу. Вы на странице задачи?', 'error');
                        UI.btnCopyMarkdown.disabled = false;
                    }
                });
            } else {
                copyToClipboard(formatAsMarkdown(data));
            }
        });
    } catch (e) {
        showStatus('Ошибка: ' + e.message, 'error');
        UI.btnCopyMarkdown.disabled = false;
    }
});

function formatAsMarkdown(problem) {
    let md = `# ${problem.name}\n\n`;
    
    if (problem.timeLimit) {
        const unit = problem.timeLimit.toLowerCase().includes('сек') || problem.timeLimit.toLowerCase().includes('sec') ? '' : ' сек.';
        md += `**Ограничение по времени:** ${problem.timeLimit}${unit}\n`;
    }
    if (problem.memoryLimit) {
        const unit = problem.memoryLimit.toLowerCase().includes('мб') || problem.memoryLimit.toLowerCase().includes('mb') ? '' : ' МБ';
        md += `**Ограничение по памяти:** ${problem.memoryLimit}${unit}\n`;
    }
    
    md += `\n## Условие\n\n${problem.description || 'Условие отсутствует.'}\n\n`;
    
    if (problem.inputFormat) {
        md += `### Формат входных данных\n\n${problem.inputFormat}\n\n`;
    }
    if (problem.outputFormat) {
        md += `### Формат выходных данных\n\n${problem.outputFormat}\n\n`;
    }
    
    return md.trim();
}

async function copyToClipboard(text) {
    try {
        await navigator.clipboard.writeText(text);
        showStatus('Условие скопировано в буфер обмена!', 'success');
    } catch (err) {
        showStatus('Ошибка копирования: ' + err, 'error');
    } finally {
        UI.btnCopyMarkdown.disabled = false;
    }
}

init();