const chatBox = document.getElementById("chat-box");
const inputField = document.getElementById("user-input");
const sendBtn = document.getElementById("send-btn");
const waveContainer = document.getElementById("wave");
const themeToggle = document.getElementById("theme-toggle");

function addMessage(sender, text) {
    const wrapper = document.createElement("div");
    wrapper.classList.add("message");

    if (sender === "Maitree") {
        wrapper.classList.add("maitree");
    } else {
        wrapper.classList.add("prem");
    }

    wrapper.innerHTML = `
        <div class="bubble">
            <strong>${sender}</strong><br>
            ${text}
        </div>
    `;

    chatBox.appendChild(wrapper);
    chatBox.scrollTop = chatBox.scrollHeight;
}

function startWave() {
    waveContainer.style.opacity = "1";
}

function stopWave() {
    waveContainer.style.opacity = "0";
}

async function sendMessage() {
    const message = inputField.value.trim();
    if (!message) return;

    addMessage("Maitree", message);
    inputField.value = "";

    startWave();

    try {
        const response = await fetch("http://127.0.0.1:5000/chat", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ message })
        });

        const data = await response.json();

        addMessage("Prem", data.reply);

        const audio = new Audio(`http://127.0.0.1:5000/audio/${data.audio}`);
        audio.play();

        audio.onended = () => stopWave();

    } catch (err) {
        stopWave();
        addMessage("Prem", "I’m having trouble connecting right now.");
    }
}

sendBtn.addEventListener("click", sendMessage);

inputField.addEventListener("keypress", function(e) {
    if (e.key === "Enter") sendMessage();
});

themeToggle.addEventListener("click", () => {
    document.body.classList.toggle("light");
    document.body.classList.toggle("dark");
});

