console.log("sendbutton")
const emergencyDiagnosesList = document.getElementById('emergency-diagnoses-list');
const infoIcon = document.querySelector('.info-icon');
const popup = infoIcon.querySelector('.info-icon__popup');

infoIcon.addEventListener('click', (event) => {
    if (event.button === 0) {
        popup.style.display = popup.style.display === 'block' ? 'none' : 'block';
        event.stopPropagation();
    }
});
document.addEventListener('click', (event) => {
    if (!infoIcon.contains(event.target) && popup.style.display === 'block') {
        popup.style.display = 'none';
    }
});

const headers = {
    "Content-Type": "application/json",
    Authorization: `Bearer ${API_KEY}`,
};

const defaultPayload = {
    model: "gpt-4",
    temperature: 0.2,
    max_tokens: 4000,
};

async function sendMessage(message, element) {
    try {
        showLoadingSpinner();

        const payload = {
            ...defaultPayload,
            messages: [{ role: "user", content: message }],
        };

        const response = await fetch(API_URL, {
            method: "POST",
            headers: headers,
            body: JSON.stringify(payload),
        });

        if (response.ok) {
            const data = await response.json();
            const botMessage = data.choices[0].message.content;
            displayMessageWordByWord(botMessage, element);
        } else {
            console.error("ChatGPT API request failed.");
            return "Sorry, I couldn't generate a response.";
        }
    } catch (error) {
        console.error("An error occurred:", error);
        return "An error occurred while processing your request.";
    } finally {
        hideLoadingSpinner();
    }
}
function showDisclaimer() {
    document.getElementById('disclaimer-popup').style.display = 'block';
}

function hideDisclaimer() {
    document.getElementById('disclaimer-popup').style.display = 'none';
}

function showLoadingSpinner() {
    document.getElementById('loading-spinner').style.display = 'block';
  }
  
  function hideLoadingSpinner() {
    document.getElementById('loading-spinner').style.display = 'none';
  }
  
  const userForm = document.getElementById('user-form');
  const chatLog = document.getElementById('chat-log');
  const userInput = document.getElementById('user-input');
  const sendButton = document.getElementById('send-button');
  console.log("sendbutton")
  
  userForm.addEventListener("submit", function (event) {
    event.preventDefault();
  });
  
  sendButton.addEventListener('click', async () => {
    const userMessage =
      userInput.value.trim() +
      "make a list of possible differential diagnosis with most probable first. consider critical diagnosis important for emergency physicians. answer in the same language the user types.";
  
    if (userMessage) {
      sendMessage(userMessage, chatLog);
    }
  });
  
  async function displayMessageWordByWord(message, element) {
    const words = message.split(" ");
    let currentIndex = 0;
  
    for (const word of words) {
      element.value += word + ' ';
      await sleep(100);
    }
  }
  
  function sleep(ms) {
    return new Promise((resolve) => setTimeout(resolve, ms));
  }
  
  userInput.addEventListener('keydown', (event) => {
    if (event.key === 'Enter') {
      sendButton.click();
    }
  });