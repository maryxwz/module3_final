class NotificationManager {
    constructor() {
        this.socket = null;
        this.userId = document.getElementById('user-id').value;
    }

    connect() {
        this.socket = new WebSocket(`ws://localhost:8000/notifications/ws/${this.userId}`);
        
        this.socket.onmessage = (event) => {
            const data = JSON.parse(event.data);
            if (data.type === 'notification') {
                this.showNotification(data.message);
            }
        };

        this.socket.onclose = () => {
            setTimeout(() => this.connect(), 1000);
        };
    }

    showNotification(message) {
        const notification = document.createElement('div');
        notification.className = 'toast';
        notification.innerHTML = `
            <div class="toast-header">
                <strong class="me-auto">Notification</strong>
                <button type="button" class="btn-close" data-bs-dismiss="toast"></button>
            </div>
            <div class="toast-body">${message}</div>
        `;
        
        document.getElementById('notifications-container').appendChild(notification);
        const toast = new bootstrap.Toast(notification);
        toast.show();
    }
}

document.addEventListener('DOMContentLoaded', () => {
    const notificationManager = new NotificationManager();
    notificationManager.connect();
}); 