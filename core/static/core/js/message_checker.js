class MessageChecker {
    constructor(interval = 5000) {
        console.log('MessageChecker constructor called'); // Debug log
        this.interval = interval;
        this.checkingInterval = null;
        this.isInChatView = window.location.pathname.includes('/messages/');
        this.notificationDot = document.querySelector('#messages-tab .notification-dot');
        this.lastCheckTime = null;
        
        console.log('Is in chat view:', this.isInChatView); // Debug log
        console.log('Notification dot found:', !!this.notificationDot); // Debug log

        // Initialize notification dot visibility
        if (this.notificationDot) {
            this.hideNotificationDot();
        }

        // Only set up chat-specific elements if in chat view
        if (this.isInChatView) {
            this.messageContainer = document.querySelector('.message-container');
            this.messageForm = document.querySelector('#message-form');
            this.setupChatHandlers();
        }

        this.start();
    }

    start() {
        // Do an initial check immediately
        this.checkNewMessages();
        
        // Then start periodic checking
        this.checkingInterval = setInterval(() => {
            this.checkNewMessages();
        }, this.interval);

        console.log('MessageChecker started'); // Debug log
    }

    stop() {
        if (this.checkingInterval) {
            clearInterval(this.checkingInterval);
            this.checkingInterval = null;
        }
    }

    scrollToBottom() {
        if (this.chatMessages) {
            this.chatMessages.scrollTop = this.chatMessages.scrollHeight;
        }
    }

    appendNewMessages(messages) {
        if (!this.messageContainer) return;

        messages.forEach(message => {
            const messageDiv = document.createElement('div');
            messageDiv.className = `message ${message.is_sent ? 'sent' : 'received'}`;
            
            const messageContent = document.createElement('div');
            messageContent.className = 'message-content';
            
            // Add sender name for received messages
            if (!message.is_sent) {
                const senderName = document.createElement('strong');
                senderName.textContent = message.sender_name;
                messageContent.appendChild(senderName);
            }
            
            const messageText = document.createElement('p');
            messageText.textContent = message.content;
            messageContent.appendChild(messageText);
            
            const timestamp = document.createElement('small');
            timestamp.textContent = new Date(message.timestamp).toLocaleString();
            messageContent.appendChild(timestamp);
            
            messageDiv.appendChild(messageContent);
            this.messageContainer.appendChild(messageDiv);
        });

        // Scroll to bottom after adding new messages
        this.messageContainer.scrollTop = this.messageContainer.scrollHeight;
    }

    handleFormSubmit(event) {
        event.preventDefault();
        
        const formData = new FormData(this.messageForm);
        fetch(this.messageForm.action, {
            method: 'POST',
            headers: {
                'X-Requested-With': 'XMLHttpRequest'
            },
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // Clear the message input
                this.messageForm.querySelector('textarea[name="message"]').value = '';
                
                // Append the sent message
                this.appendNewMessages([{
                    content: formData.get('message'),
                    timestamp: new Date().toISOString(),
                    is_sent: true
                }]);
            }
        })
        .catch(error => {
            console.error('Error sending message:', error);
        });
    }

    setupChatHandlers() {
        if (this.messageForm) {
            this.messageForm.addEventListener('submit', this.handleFormSubmit.bind(this));
        }

        // Set initial last message time from existing messages
        const messages = document.querySelectorAll('.message small');
        if (messages.length > 0) {
            const lastMessage = messages[messages.length - 1];
            const timestamp = new Date(lastMessage.textContent.trim());
            if (!isNaN(timestamp)) {
                this.lastMessageTime = timestamp.toISOString();
            }
        }

        // Initial scroll to bottom
        setTimeout(() => {
            if (this.messageContainer) {
                this.messageContainer.scrollTop = this.messageContainer.scrollHeight;
            }
        }, 100);
    }

    checkNewMessages() {
        console.log('Checking for new messages...'); // Debug log
        const url = '/notifications/check-new-messages/';
        const params = new URLSearchParams({
            get_unread_counts: true,
            last_check_time: this.lastCheckTime || ''
        });

        fetch(`${url}?${params}`, {
            headers: {
                'X-Requested-With': 'XMLHttpRequest'
            }
        })
        .then(response => {
            console.log('Response status:', response.status); // Debug log
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            console.log('Received data:', data); // Debug log
            
            // Update last check time
            if (data.current_time) {
                this.lastCheckTime = data.current_time;
            }

            // Show notification dot only if there are unread messages
            if (data.unread_counts && Object.keys(data.unread_counts).length > 0) {
                console.log('Unread messages detected!'); // Debug log
                this.showNotificationDot();
            } else {
                console.log('No unread messages'); // Debug log
                this.hideNotificationDot();
            }
        })
        .catch(error => {
            console.error('Error checking messages:', error);
        });
    }

    showNotificationDot() {
        if (this.notificationDot) {
            console.log('Showing notification dot');
            this.notificationDot.style.display = 'block';
        }
    }

    hideNotificationDot() {
        if (this.notificationDot) {
            console.log('Hiding notification dot');
            this.notificationDot.style.display = 'none';
        }
    }
}

// Initialize message checker when the page loads
document.addEventListener('DOMContentLoaded', () => {
    // Initialize on doctor dashboard and other pages except messages
    console.log('Current pathname:', window.location.pathname); // Debug log
    
    if (!window.location.pathname.includes('/messages/')) {
        console.log('Initializing MessageChecker'); // Debug log
        window.messageChecker = new MessageChecker();

        // Add click handler to messages tab
        const messagesTab = document.getElementById('messages-tab');
        if (messagesTab) {
            messagesTab.addEventListener('click', () => {
                if (window.messageChecker) {
                    window.messageChecker.hideNotificationDot();
                }
            });
        }
    }
}); 