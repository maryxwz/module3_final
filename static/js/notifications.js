class NotificationManager {
    constructor() {
        this.socket = null;
        this.userId = document.getElementById('user-id').value;
    }

    connect() {
        this.socket = new WebSocket(`ws://127.0.0.1:8000/notifications/ws/${this.userId}`);
        
        this.socket.onmessage = (event) => {
            const message = JSON.parse(event.data);
            this.showNotification(message);
        };

        this.socket.onclose = () => {
            console.log("WebSocket connection closed!");
            setTimeout(() => this.connect(), 1000);
        };

        this.socket.onopen = () => {
            console.log("WebSocket connection established!");
        };
    }

    showNotification(message) {
        const notification = document.createElement('div');
        notification.className = 'toast';
        notification.innerHTML = `
            <div class="toast-header">
                <strong class="me-auto">Message from ${message.person_from}</strong>
                <small>${message.text.time_sent}</small>
                <button type="button" class="btn-close" data-bs-dismiss="toast"></button>
            </div>
            <div class="toast-body">${message.text}</div>
        `;
        
        document.getElementById('notifications-container').appendChild(notification);
        const toast = new bootstrap.Toast(notification, {
            delay: 7000 
        });
        toast.show();
    }
}

document.addEventListener('DOMContentLoaded', () => {
    const notificationManager = new NotificationManager();
    notificationManager.connect();
});


