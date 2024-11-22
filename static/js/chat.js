async function sendMessage() {
    const inputField = document.getElementById('user-input');
    const chatHistory = document.getElementById('chat-history');
    const userMessage = inputField.value;

    if (!userMessage.trim()) {
        console.warn('No user message provided!');
        return;
    }

    // Display user message
    const userMessageDiv = document.createElement('div');
    userMessageDiv.className = 'chat-message user-message';
    userMessageDiv.textContent = userMessage;
    chatHistory.appendChild(userMessageDiv);
    chatHistory.scrollTop = chatHistory.scrollHeight;

    inputField.value = '';

    try {
        console.log(`Sending message to the server: "${userMessage}"`);

        // Send POST request to backend
        const response = await fetch('/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message: userMessage }),
        });

        // Log the server's response
        console.log('Received response from the server:', response);

        if (!response.ok) {
            throw new Error(`HTTP error! Status: ${response.status}`);
        }

        const data = await response.json();

        // Display bot response
        const botMessageDiv = document.createElement('div');
        botMessageDiv.className = 'chat-message bot-message';
        botMessageDiv.textContent = data.reply;
        chatHistory.appendChild(botMessageDiv);
        chatHistory.scrollTop = chatHistory.scrollHeight;

        console.log(`Chatbot replied: "${data.reply}"`);
    } catch (error) {
        console.error('Error:', error);

        // Display error message
        const errorMessageDiv = document.createElement('div');
        errorMessageDiv.className = 'chat-message bot-message';
        errorMessageDiv.textContent = "An error occurred. Please try again later.";
        chatHistory.appendChild(errorMessageDiv);
        chatHistory.scrollTop = chatHistory.scrollHeight;
    }
}
