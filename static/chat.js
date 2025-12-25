document.addEventListener('DOMContentLoaded', () => {
    // UI Construction
    const chatContainer = document.createElement('div');
    chatContainer.id = 'chat-widget-container';
    chatContainer.innerHTML = `
        <button id="chat-toggle-btn"><i class="fas fa-robot fa-lg"></i></button>
        <div id="chat-box">
            <div class="chat-header">
                <div>
                     <i class="fas fa-robot me-1"></i>
                     <span style="font-weight: 600;">Assistant STP</span>
                </div>
                <div>
                    <button type="button" id="chat-reset-btn" title="Nouvelle session"><i class="fas fa-trash-alt"></i></button>
                    <button type="button" class="btn-close btn-close-white ms-2" id="chat-close-btn" aria-label="Close"></button>
                </div>
            </div>
            <div class="chat-messages" id="chat-messages">
                <div class="message bot">Bonjour! Je suis votre assistant virtuel. Je peux vous aider à gérer vos clients, devis et fournisseurs.</div>
            </div>
            <div class="typing-indicator" id="typing-indicator">L'assistant réfléchit...</div>
            <div class="chat-input-area">
                <input type="text" id="chat-input" placeholder="Écrivez votre demande..." autocomplete="off">
                <button id="chat-send-btn"><i class="fas fa-paper-plane"></i></button>
            </div>
        </div>
    `;
    document.body.appendChild(chatContainer);

    const toggleBtn = document.getElementById('chat-toggle-btn');
    const closeBtn = document.getElementById('chat-close-btn');
    const chatBox = document.getElementById('chat-box');
    const input = document.getElementById('chat-input');
    const sendBtn = document.getElementById('chat-send-btn');
    const messagesContainer = document.getElementById('chat-messages');
    const typingIndicator = document.getElementById('typing-indicator');
    const resetBtn = document.getElementById('chat-reset-btn');

    // Persistence Logic
    const scriptTag = document.querySelector('script[data-user-id]');
    const userId = scriptTag ? scriptTag.getAttribute('data-user-id') : 'guest';
    const historyKey = `stpChatHistory_${userId}`;
    const openKey = `stpChatOpen_${userId}`;

    const loadHistory = () => {
        const history = JSON.parse(localStorage.getItem(historyKey) || '[]');
        if (history.length > 0) {
            messagesContainer.innerHTML = ''; // Clear default greeting if history exists
            history.forEach(msg => renderMessage(msg.text, msg.sender, false));
        }

        const isOpen = localStorage.getItem(openKey) === 'true';
        if (isOpen) chatBox.classList.add('open');
    };

    const saveMessage = (text, sender) => {
        const history = JSON.parse(localStorage.getItem(historyKey) || '[]');
        history.push({ text, sender });
        // Keep only last 50 messages to avoid local storage bloat
        if (history.length > 50) history.shift();
        localStorage.setItem(historyKey, JSON.stringify(history));
    };

    // Toggle Chat
    const toggleChat = () => {
        chatBox.classList.toggle('open');
        const isOpen = chatBox.classList.contains('open');
        localStorage.setItem(openKey, isOpen);
        if (isOpen) input.focus();
    };

    toggleBtn.addEventListener('click', toggleChat);
    closeBtn.addEventListener('click', toggleChat);

    // Reset Chat
    const resetChat = async () => {
        if (!confirm("Voulez-vous réinitialiser le chat et effacer l'historique ?")) return;

        localStorage.removeItem(historyKey);
        messagesContainer.innerHTML = '<div class="message bot">Historique effacé. Bonjour! Je suis prêt pour une nouvelle session.</div>';

        try {
            await fetch('/api/chat/reset', { method: 'POST' });
        } catch (e) {
            console.error("Error resetting chat session:", e);
        }
    };

    resetBtn.addEventListener('click', resetChat);

    // Render Message (without saving again)
    const renderMessage = (text, sender, highlight = true) => {
        const msgDiv = document.createElement('div');
        msgDiv.classList.add('message', sender);

        // Simple link detection and replacement
        const urlRegex = /(https?:\/\/[^\s]+)/g;
        let html = text.replace(urlRegex, (url) => {
            return `<a href="${url}" target="_blank" style="color: inherit; text-decoration: underline; font-weight: bold;">[Voir le document]</a>`;
        });

        msgDiv.innerHTML = html.replace(/\n/g, '<br>');
        messagesContainer.appendChild(msgDiv);
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    };

    // Append and Store Message
    const appendMessage = (text, sender) => {
        renderMessage(text, sender);
        saveMessage(text, sender);
    };

    // Send Message
    const sendMessage = async () => {
        const text = input.value.trim();
        if (!text) return;

        appendMessage(text, 'user');
        input.value = '';
        typingIndicator.style.display = 'block';

        try {
            const response = await fetch('/api/chat/send', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ message: text }),
            });

            const data = await response.json();
            typingIndicator.style.display = 'none';

            if (data.reply) {
                appendMessage(data.reply, 'bot');
            }

            if (data.action === 'reset') {
                localStorage.removeItem(historyKey);
                // No need to reload, the context is cleared on server, and local storage is empty for next load
            }

            if (data.result && data.result.status === 'error') {
                appendMessage(`Erreur: ${data.result.message}`, 'system');
            }

        } catch (error) {
            typingIndicator.style.display = 'none';
            appendMessage("Erreur de communication avec le serveur.", 'system');
            console.error(error);
        }
    };

    sendBtn.addEventListener('click', sendMessage);
    input.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') sendMessage();
    });

    // Initialize
    loadHistory();
});
