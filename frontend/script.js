const API_URL = "http://127.0.0.1:8000";
let isLoading = false;
let currentModel = "qwen3:8b";
let streamingEnabled = false;

function getCurrentTime() {
    const now = new Date();
    return now.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', hour12: true });
}

function formatMessageContent(content) {
    let formatted = content
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');

    formatted = formatted.replace(/```([\s\S]*?)```/g, (match, code) => {
        const language = code.split('\n')[0].trim() || 'plaintext';
        const codeContent = code.replace(/^[\s\S]*?\n/, '').replace(/\n$/, '');
        return `<pre><code class="language-${language}">${codeContent}</code></pre>`;
    });

    formatted = formatted.replace(/`([^`]+)`/g, '<code>$1</code>');
    formatted = formatted.replace(/(https?:\/\/[^\s]+)/g, '<a href="$1" target="_blank">$1</a>');
    formatted = formatted.replace(/\n/g, '<br>');

    return formatted;
}

function createMessageElement(role, content) {
    const message = document.createElement('div');
    message.className = `message ${role}`;

    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content';

    const avatar = document.createElement('div');
    avatar.className = `avatar ${role}`;
    avatar.textContent = role === 'user' ? 'You' : 'AI';

    const bubble = document.createElement('div');
    bubble.className = 'bubble';
    bubble.innerHTML = formatMessageContent(content);

    bubble.querySelectorAll('pre code').forEach(block => {
        hljs.highlightElement(block);
    });

    const time = document.createElement('div');
    time.className = 'message-time';
    time.textContent = getCurrentTime();

    contentDiv.appendChild(avatar);
    contentDiv.appendChild(bubble);

    message.appendChild(contentDiv);
    message.appendChild(time);

    return message;
}

function createTypingIndicator() {
    const message = document.createElement('div');
    message.className = 'message assistant';
    message.id = 'typing-indicator';

    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content';

    const avatar = document.createElement('div');
    avatar.className = 'avatar assistant';
    avatar.textContent = 'AI';

    const typing = document.createElement('div');
    typing.className = 'typing-indicator';
    typing.innerHTML = '<div class="typing-dot"></div><div class="typing-dot"></div><div class="typing-dot"></div>';

    contentDiv.appendChild(avatar);
    contentDiv.appendChild(typing);
    message.appendChild(contentDiv);

    return message;
}

async function handleStreamingResponse(reader, chatBox) {
    const decoder = new TextDecoder();
    let accumulatedText = '';
    let messageElement = null;

    try {
        while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            const chunk = decoder.decode(value, { stream: true });
            const lines = chunk.split('\n');

            for (const line of lines) {
                if (line.startsWith('data: ')) {
                    try {
                        const data = JSON.parse(line.slice(6));
                        if (data.error) {
                            console.error('Streaming error:', data.error);
                            break;
                        }

                        if (data.content) {
                            accumulatedText += data.content;

                            if (!messageElement) {
                                messageElement = createMessageElement('assistant', accumulatedText);
                                chatBox.appendChild(messageElement);
                            } else {
                                const bubble = messageElement.querySelector('.bubble');
                                bubble.innerHTML = formatMessageContent(accumulatedText);
                                bubble.querySelectorAll('pre code').forEach(block => {
                                    hljs.highlightElement(block);
                                });
                            }

                            chatBox.scrollTop = chatBox.scrollHeight;
                        }
                    } catch (e) {
                        console.error('Error parsing stream:', e);
                    }
                }
            }
        }
    } catch (error) {
        console.error('Streaming error:', error);
    }

    return accumulatedText;
}

async function sendMessage() {
    const input = document.getElementById('user-input');
    const message = input.value.trim();

    if (!message || isLoading) return;

    const chatBox = document.getElementById('chat-box');

    const welcome = chatBox.querySelector('.welcome-message');
    if (welcome) welcome.remove();

    chatBox.appendChild(createMessageElement('user', message));
    input.value = '';

    const typingEl = createTypingIndicator();
    chatBox.appendChild(typingEl);
    chatBox.scrollTop = chatBox.scrollHeight;

    isLoading = true;

    try {
        const response = await fetch(`${API_URL}/chat`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                message: message,
                stream: streamingEnabled
            }),
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        typingEl.remove();

        if (streamingEnabled && response.body) {
            const reader = response.body.getReader();
            const assistantResponse = await handleStreamingResponse(reader, chatBox);

            if (assistantResponse.trim()) {
                const fullMemoryResponse = await fetch(`${API_URL}/memory`);
                const memoryData = await fullMemoryResponse.json();
            }
        } else {
            const data = await response.json();

            if (data.response) {
                chatBox.appendChild(createMessageElement('assistant', data.response));
            } else {
                chatBox.appendChild(createMessageElement('assistant', 'No response received.'));
            }
        }

    } catch (error) {
        typingEl.remove();

        const errorMsg = document.createElement('div');
        errorMsg.className = 'error-message';
        errorMsg.textContent = `Error: ${error.message}. Make sure the backend is running on ${API_URL}`;
        chatBox.appendChild(errorMsg);

        console.error('Error:', error);
    } finally {
        isLoading = false;
        chatBox.scrollTop = chatBox.scrollHeight;
        input.focus();
    }
}

function clearConversationGlobal() {
    if (confirm('Are you sure you want to clear all chat history? This cannot be undone.')) {
        fetch(`${API_URL}/memory/clear`, { method: 'POST' })
            .then(() => {
                const chatBox = document.getElementById('chat-box');
                chatBox.innerHTML = `
                    <div class="welcome-message">
                        <div class="welcome-content">
                            <h2>Welcome to AI Assistant</h2>
                            <p>Start a conversation or use special commands:</p>
                            <div class="commands">
                                <div class="command-item">
                                    <span class="cmd">wiki</span> Get Wikipedia summaries
                                </div>
                                <div class="command-item">
                                    <span class="cmd">search</span> Web search via DuckDuckGo
                                </div>
                                <div class="command-item">
                                    <span class="cmd">arxiv</span> Research paper search
                                </div>
                            </div>
                        </div>
                    </div>
                `;
                document.getElementById('user-input').focus();
            })
            .catch(error => alert('Error clearing history: ' + error));
    }
}

function exportConversation() {
    fetch(`${API_URL}/memory`)
        .then(res => res.json())
        .then(data => {
            const json = JSON.stringify(data.messages, null, 2);
            const blob = new Blob([json], { type: 'application/json' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `chat-export-${new Date().toISOString().split('T')[0]}.json`;
            a.click();
            URL.revokeObjectURL(url);
        })
        .catch(error => alert('Error exporting: ' + error));
}

function exportConversationMarkdown() {
    fetch(`${API_URL}/memory`)
        .then(res => res.json())
        .then(data => {
            let markdown = '# Chat Export\n\n';
            markdown += `Exported: ${new Date().toLocaleString()}\n\n`;

            data.messages.forEach(msg => {
                markdown += `## ${msg.role.toUpperCase()}\n\n${msg.content}\n\n---\n\n`;
            });

            const blob = new Blob([markdown], { type: 'text/markdown' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `chat-export-${new Date().toISOString().split('T')[0]}.md`;
            a.click();
            URL.revokeObjectURL(url);
        })
        .catch(error => alert('Error exporting: ' + error));
}

function changeModel() {
    const modelInput = document.getElementById('model-input');
    const modelName = modelInput.value.trim();

    if (!modelName) {
        showStatus('model-status', 'Please enter a model name', 'error');
        return;
    }

    fetch(`${API_URL}/model`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ model: modelName })
    })
        .then(res => res.json())
        .then(data => {
            currentModel = data.model;
            document.getElementById('model-display').textContent = `Model: ${currentModel}`;
            showStatus('model-status', `✓ Model changed to ${currentModel}`, 'success');
            modelInput.value = '';
            localStorage.setItem('selectedModel', currentModel);
        })
        .catch(error => {
            showStatus('model-status', `Error: ${error.message}`, 'error');
        });
}

function handleFileUpload(event) {
    const file = event.target.files[0];
    if (!file) return;

    if (!file.name.endsWith('.pdf')) {
        showStatus('upload-status', 'Only PDF files are supported', 'error');
        return;
    }

    const formData = new FormData();
    formData.append('file', file);

    showStatus('upload-status', 'Uploading...');

    fetch(`${API_URL}/upload-document`, {
        method: 'POST',
        body: formData
    })
        .then(res => res.json())
        .then(data => {
            showStatus('upload-status', `✓ Successfully uploaded ${data.filename}`, 'success');
            document.getElementById('file-input').value = '';
        })
        .catch(error => {
            showStatus('upload-status', `Error: ${error.message}`, 'error');
        });
}

function showStatus(elementId, message, type = '') {
    const element = document.getElementById(elementId);
    element.textContent = message;
    element.className = `status-text ${type}`;
}

function openSettings() {
    document.getElementById('settings-modal').classList.add('active');
    document.getElementById('model-input').value = currentModel;
    document.getElementById('streaming-checkbox').checked = streamingEnabled;

    document.getElementById('upload-area').addEventListener('click', () => {
        document.getElementById('file-input').click();
    });

    document.getElementById('upload-area').addEventListener('dragover', (e) => {
        e.preventDefault();
        document.getElementById('upload-area').style.borderColor = 'var(--primary)';
    });

    document.getElementById('upload-area').addEventListener('dragleave', () => {
        document.getElementById('upload-area').style.borderColor = 'var(--border)';
    });

    document.getElementById('upload-area').addEventListener('drop', (e) => {
        e.preventDefault();
        document.getElementById('upload-area').style.borderColor = 'var(--border)';

        if (e.dataTransfer.files.length > 0) {
            document.getElementById('file-input').files = e.dataTransfer.files;
            handleFileUpload({ target: { files: e.dataTransfer.files } });
        }
    });
}

function closeSettings() {
    document.getElementById('settings-modal').classList.remove('active');
}

function saveSettings() {
    streamingEnabled = document.getElementById('streaming-checkbox').checked;
    localStorage.setItem('streamingEnabled', streamingEnabled);
}

function toggleTheme() {
    document.body.classList.toggle('dark-mode');
    localStorage.setItem('theme', document.body.classList.contains('dark-mode') ? 'dark' : 'light');
    updateThemeIcon();
}

function updateThemeIcon() {
    const sunIcon = document.querySelector('.sun-icon');
    const moonIcon = document.querySelector('.moon-icon');
    const isDark = document.body.classList.contains('dark-mode');

    if (isDark) {
        sunIcon.style.display = 'none';
        moonIcon.style.display = 'block';
    } else {
        sunIcon.style.display = 'block';
        moonIcon.style.display = 'none';
    }
}

function initTheme() {
    const savedTheme = localStorage.getItem('theme');
    const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;

    if (savedTheme === 'dark' || (!savedTheme && prefersDark)) {
        document.body.classList.add('dark-mode');
    }

    updateThemeIcon();
}

function loadSettings() {
    currentModel = localStorage.getItem('selectedModel') || 'qwen3:8b';
    streamingEnabled = localStorage.getItem('streamingEnabled') === 'true';
    document.getElementById('model-display').textContent = `Model: ${currentModel}`;

    fetch(`${API_URL}/model`)
        .then(res => res.json())
        .then(data => {
            currentModel = data.model;
            document.getElementById('model-display').textContent = `Model: ${currentModel}`;
        })
        .catch(err => console.error('Error fetching model:', err));
}

// Event listeners
document.getElementById('user-input').addEventListener('keypress', function (e) {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
    }
});

document.getElementById('user-input').addEventListener('keydown', function (e) {
    if (e.key === 'Enter' && e.shiftKey) {
        e.preventDefault();
        this.value += '\n';
    }
});

document.addEventListener('click', function (e) {
    const modal = document.getElementById('settings-modal');
    if (e.target === modal) {
        closeSettings();
    }
});

// Initialize
document.addEventListener('DOMContentLoaded', function () {
    initTheme();
    loadSettings();
    document.getElementById('user-input').focus();
});
