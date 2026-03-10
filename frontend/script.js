async function sendMessage() {

    const input = document.getElementById("user-input");
    const message = input.value.trim();
    if (!message) return;

    const chatBox = document.getElementById("chat-box");

    chatBox.innerHTML += `<div class="user"><span>${message}</span></div>`;
    input.value = "";

    chatBox.innerHTML += `<div class="bot" id="typing"><span>AI is typing...</span></div>`;
    chatBox.scrollTop = chatBox.scrollHeight;

    const response = await fetch("http://127.0.0.1:8000/chat", {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({ message: message })
    });

    const data = await response.json();

    document.getElementById("typing").remove();

    chatBox.innerHTML += `<div class="bot"><span>${data.response}</span></div>`;
    chatBox.scrollTop = chatBox.scrollHeight;
}