async function sendMessage() {
    const inputField = document.getElementById('user-input');
    const chatHistory = document.getElementById('chat-history');
    const userMessage = inputField.value;

    if (!userMessage.trim()) {
        console.warn('No user message provided!');
        return;
    }

    const userMessageDiv = document.createElement('div');
    userMessageDiv.className = 'chat-message user-message';
    userMessageDiv.textContent = userMessage;
    chatHistory.appendChild(userMessageDiv);
    chatHistory.scrollTop = chatHistory.scrollHeight;

    inputField.value = '';

    try {
        console.log(`Sending message to the server: "${userMessage}"`);

        const response = await fetch('/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message: userMessage }),
        });

        if (!response.ok) {
            throw new Error(`HTTP error! Status: ${response.status}`);
        }

        const data = await response.json();

        const reply = data.reply;
        const extractedTerms = reply["Extracted Terms"];
        const categorizedTerms = reply["Categorized Terms"];
        const matchedResults = reply["Matched Results"];

        const botMessageDiv = document.createElement('div');
        botMessageDiv.className = 'chat-message bot-message';
        botMessageDiv.innerHTML = `
            <strong>Extracted Terms:</strong> ${extractedTerms.join(", ")}<br>
            <strong>Categorized Terms:</strong>
            <ul>
                ${Object.entries(categorizedTerms).map(
                    ([category, terms]) =>
                        `<li><strong>${category}:</strong> ${terms.length > 0 ? terms.join(", ") : "None"}</li>`
                ).join("")}
            </ul>
            <strong>Matched Results:</strong>
            <ul>
                ${Object.entries(matchedResults).map(
                    ([category, terms]) =>
                        `<li><strong>${category}:</strong> ${terms.length > 0 ? terms.join(", ") : "None"}</li>`
                ).join("")}
            </ul>
        `;

        chatHistory.appendChild(botMessageDiv);
        chatHistory.scrollTop = chatHistory.scrollHeight;

        console.log("Chatbot replied:", reply);
    } catch (error) {
        console.error('Error:', error);

        const errorMessageDiv = document.createElement('div');
        errorMessageDiv.className = 'chat-message bot-message';
        errorMessageDiv.textContent = "An error occurred. Please try again later.";
        chatHistory.appendChild(errorMessageDiv);
        chatHistory.scrollTop = chatHistory.scrollHeight;
    }
}
