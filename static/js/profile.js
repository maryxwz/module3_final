function showEditProfile() {
    const profileModal = new bootstrap.Modal(document.getElementById('profileModal'));
    const editProfileModal = new bootstrap.Modal(document.getElementById('editProfileModal'));
    
    profileModal.hide();
    editProfileModal.show();
}

function showChangePassword() {
    $('#editProfileModal').modal('hide');
    $('#changePasswordModal').modal('show');
}

function showNotification(message, type) {
    const container = document.getElementById('notifications-container');
    const notification = document.createElement('div');
    notification.className = `alert alert-${type} alert-dismissible fade show`;
    notification.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    container.appendChild(notification);
    
    setTimeout(() => notification.remove(), 5000);
}

document.getElementById('editProfileForm').addEventListener('submit', async function(e) {
    e.preventDefault();
    
    const formData = new FormData(this);
    
    try {
        const response = await fetch('/api/profile/update', {
            method: 'POST',
            body: formData
        });
        
        const data = await response.json();
        
        if (response.ok) {
            // Обновляем UI
            document.querySelector('.profile-avatar img')?.setAttribute('src', data.avatar_url);
            document.querySelector('.profile-avatar-large img')?.setAttribute('src', data.avatar_url);
            document.querySelector('.email-display').textContent = data.email;
            document.querySelector('.username-display').textContent = data.username;
            
            $('#editProfileModal').modal('hide');
            showNotification('Profile updated successfully', 'success');
        } else {
            showNotification(data.error, 'error');
        }
    } catch (error) {
        showNotification('An error occurred while updating profile', 'error');
    }
});

document.getElementById('changePasswordForm').addEventListener('submit', async function(e) {
    e.preventDefault();
    
    const formData = new FormData(this);
    
    try {
        const response = await fetch('/api/profile/change-password', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                current_password: formData.get('current_password'),
                new_password: formData.get('new_password'),
                confirm_password: formData.get('confirm_password')
            })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            $('#changePasswordModal').modal('hide');
            this.reset();
            showNotification('Password changed successfully', 'success');
        } else {
            showNotification(data.error, 'error');
        }
    } catch (error) {
        showNotification('An error occurred while changing password', 'error');
    }
});

function previewAvatar(input) {
    if (input.files && input.files[0]) {
        const reader = new FileReader();
        
        reader.onload = function(e) {
            const avatar = input.closest('.modal-body').querySelector('.profile-avatar-large img');
            if (avatar) {
                avatar.src = e.target.result;
            } else {
                const placeholder = input.closest('.modal-body').querySelector('.avatar-placeholder-large');
                const newAvatar = document.createElement('img');
                newAvatar.src = e.target.result;
                newAvatar.className = 'rounded-circle';
                placeholder.parentNode.replaceChild(newAvatar, placeholder);
            }
        }
        
        reader.readAsDataURL(input.files[0]);
    }
} 