document.addEventListener('DOMContentLoaded', () => {
    const deepseekApiKeyInput = document.getElementById('deepseek_api_key');
    const openrouterApiKeyInput = document.getElementById('openrouter_api_key');
    const braveApiKeyInput = document.getElementById('brave_api_key');
    const saveKeysButton = document.getElementById('save_keys');
    const keysSavedMessage = document.getElementById('keys_saved_message');

    const chatBox = document.getElementById('chat_box');
    const userInput = document.getElementById('user_input');
    const sendButton = document.getElementById('send_button');

    // Load API keys from local storage
    const loadKeys = () => {
        deepseekApiKeyInput.value = localStorage.getItem('deepseek_api_key') || '';
        openrouterApiKeyInput.value = localStorage.getItem('openrouter_api_key') || '';
        braveApiKeyInput.value = localStorage.getItem('brave_api_key') || '';
    };

    // Save API keys to local storage
    const saveKeys = () => {
        localStorage.setItem('deepseek_api_key', deepseekApiKeyInput.value);
        localStorage.setItem('openrouter_api_key', openrouterApiKeyInput.value);
        localStorage.setItem('brave_api_key', braveApiKeyInput.value);
        keysSavedMessage.classList.remove('hidden');
        setTimeout(() => {
            keysSavedMessage.classList.add('hidden');
        }, 2000);
    };

    saveKeysButton.addEventListener('click', saveKeys);

    const addMessage = (text, sender) => {
        const message = document.createElement('div');
        message.classList.add('message', `${sender}-message`);
        message.textContent = text;
        chatBox.appendChild(message);
        chatBox.scrollTop = chatBox.scrollHeight;
    };

    const handleSend = async () => {
        const question = userInput.value.trim();
        if (!question) return;

        addMessage(question, 'user');
        userInput.value = '';
        sendButton.disabled = true;

        const deepseekApiKey = localStorage.getItem('deepseek_api_key');
        const openrouterApiKey = localStorage.getItem('openrouter_api_key');
        const braveApiKey = localStorage.getItem('brave_api_key');

        if (!deepseekApiKey || !openrouterApiKey || !braveApiKey) {
            addMessage('Error: Please save all API keys in the settings section before asking a question.', 'agent');
            sendButton.disabled = false;
            return;
        }

        try {
            const response = await fetch('/investigate', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    question,
                    deepseek_api_key: deepseekApiKey,
                    openrouter_api_key: openrouterApiKey,
                    brave_api_key: braveApiKey,
                }),
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || 'An unknown error occurred.');
            }

            const result = await response.json();
            // Assuming the final answer is in result.prediction
            addMessage(result.prediction, 'agent');

        } catch (error) {
            addMessage(`Error: ${error.message}`, 'agent');
        } finally {
            sendButton.disabled = false;
        }
    };

    sendButton.addEventListener('click', handleSend);
    userInput.addEventListener('keydown', (event) => {
        if (event.key === 'Enter') {
            handleSend();
        }
    });

    loadKeys();
});
