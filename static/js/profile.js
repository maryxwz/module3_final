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

// Показываем поле пароля только при изменении email или username
document.querySelectorAll('#editProfileForm input[name="email"], #editProfileForm input[name="username"]')
.forEach(input => {
    input.addEventListener('input', function() {
        const originalValue = this.getAttribute('value');
        const currentValue = this.value;
        const passwordBlock = document.getElementById('currentPasswordBlock');
        
        if (originalValue !== currentValue) {
            passwordBlock.style.display = 'block';
        } else if (document.querySelector('#editProfileForm input[name="email"]').value === document.querySelector('#editProfileForm input[name="email"]').getAttribute('value') &&
                   document.querySelector('#editProfileForm input[name="username"]').value === document.querySelector('#editProfileForm input[name="username"]').getAttribute('value')) {
            passwordBlock.style.display = 'none';
        }
    });
});

document.getElementById('editProfileForm').addEventListener('submit', async function(e) {
    e.preventDefault();
    
    const formData = new FormData(this);
    
    // Удаляем пустые поля
    if (!formData.get('email')) formData.delete('email');
    if (!formData.get('username')) formData.delete('username');
    if (!formData.get('current_password')) formData.delete('current_password');
    if (!formData.get('avatar').size) formData.delete('avatar');
    
    try {
        const response = await fetch('/api/profile/update', {
            method: 'POST',
            body: formData
        });
        
        const data = await response.json();
        
        if (response.ok) {
            // Обновляем UI
            if (data.avatar_url) {
                document.querySelectorAll('.profile-avatar img, .profile-avatar-large img').forEach(img => {
                    img.setAttribute('src', data.avatar_url);
                });
            }
            if (data.email) document.querySelector('.email-display').textContent = data.email;
            if (data.username) document.querySelector('.username-display').textContent = data.username;
            
            // Закрываем модальное окно
            bootstrap.Modal.getInstance(document.getElementById('editProfileModal')).hide();
            showNotification('Profile updated successfully', 'success');
        } else {
            showNotification(data.detail || 'An error occurred', 'error');
        }
    } catch (error) {
        console.error('Profile update error:', error);
        showNotification('An error occurred while updating profile', 'error');
    }
});

function showChangePasswordModal() {
    bootstrap.Modal.getInstance(document.getElementById('editProfileModal')).hide();
    const changePasswordModal = new bootstrap.Modal(document.getElementById('changePasswordModal'));
    changePasswordModal.show();
}

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
                new_password: formData.get('new_password')
            })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            bootstrap.Modal.getInstance(document.getElementById('changePasswordModal')).hide();
            showNotification('Password changed successfully', 'success');
        } else {
            showNotification(data.detail || 'An error occurred', 'error');
        }
    } catch (error) {
        console.error('Password change error:', error);
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

async function updateAvatar(input) {
    if (input.files && input.files[0]) {
        const formData = new FormData();
        formData.append('avatar', input.files[0]);
        
        try {
            const response = await fetch('/api/profile/update-avatar', {
                method: 'POST',
                body: formData
            });
            
            if (!response.ok) {
                throw new Error(await response.text());
            }
            
            const data = await response.json();
            
            if (data.success) {
                // Обновляем все аватары на странице
                document.querySelectorAll('img[data-user-avatar="' + data.user_id + '"]').forEach(img => {
                    img.src = data.avatar_url;
                });
                
                // Обновляем аватары в профиле
                document.querySelectorAll('.profile-avatar img, .profile-avatar-large img').forEach(img => {
                    img.src = data.avatar_url;
                });
                
                // Скрываем плейсхолдеры
                document.querySelectorAll('.avatar-placeholder, .avatar-placeholder-large').forEach(placeholder => {
                    placeholder.style.display = 'none';
                });
                
                showNotification('Avatar updated successfully', 'success');
            } else {
                showNotification(data.detail || 'An error occurred', 'error');
            }
        } catch (error) {
            console.error('Avatar update error:', error);
            showNotification(error.message || 'An error occurred while updating avatar', 'error');
        }
    }
}

// Функции для показа модальных окон
function showEmailChangeModal() {
    bootstrap.Modal.getInstance(document.getElementById('profileModal')).hide();
    const emailModal = new bootstrap.Modal(document.getElementById('emailChangeModal'));
    emailModal.show();
}

// Обработчики форм
document.getElementById('emailChangeForm').addEventListener('submit', async function(e) {
    e.preventDefault();
    const formData = new FormData(this);
    
    try {
        const response = await fetch('/api/profile/update', {
            method: 'POST',
            body: formData
        });
        
        const data = await response.json();
        
        if (response.ok) {
            // Обновляем email везде на странице
            document.querySelectorAll('.email-display').forEach(el => {
                el.textContent = data.email;
            });
            
            // Закрываем модальное окно изменения email
            bootstrap.Modal.getInstance(document.getElementById('emailChangeModal')).hide();
            
            // Показываем основное модальное окно профиля
            const profileModal = new bootstrap.Modal(document.getElementById('profileModal'));
            profileModal.show();
            
            showNotification('Email updated successfully', 'success');
            this.reset();
        } else {
            showNotification(data.detail || 'An error occurred', 'error');
        }
    } catch (error) {
        console.error('Email update error:', error);
        showNotification('An error occurred while updating email', 'error');
    }
});

// Обработчик формы изменения username
document.getElementById('usernameChangeForm').addEventListener('submit', function(e) {
    e.preventDefault();
    
    const form = this;
    const formData = new FormData(form);
    
    fetch('/api/profile/update-username', {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // Обновляем имя пользователя на странице
            document.querySelectorAll('.username-display').forEach(el => {
                el.textContent = data.username;
            });
            
            // Закрываем модальное окно
            bootstrap.Modal.getInstance(document.getElementById('usernameChangeModal')).hide();
            showNotification('Username updated successfully', 'success');
            form.reset();
        } else {
            showNotification(data.detail || 'An error occurred', 'error');
        }
    })
    .catch(error => {
        showNotification('An error occurred while updating username', 'error');
    });
});

// Обработчик формы изменения пароля
document.getElementById('passwordChangeForm').addEventListener('submit', async function(e) {
    e.preventDefault();
    
    const formData = new FormData(this);
    
    try {
        const response = await fetch('/api/profile/change-password', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-Requested-With': 'XMLHttpRequest'
            },
            body: JSON.stringify({
                current_password: formData.get('current_password'),
                new_password: formData.get('new_password')
            })
        });
        
        if (!response.ok) {
            const data = await response.json();
            throw new Error(data.detail || 'Failed to change password');
        }
        
        bootstrap.Modal.getInstance(document.getElementById('passwordChangeModal')).hide();
        const profileModal = new bootstrap.Modal(document.getElementById('profileModal'));
        profileModal.show();
        
        showNotification('Password changed successfully', 'success');
        this.reset();
    } catch (error) {
        showNotification(error.message || 'An error occurred while changing password', 'error');
    }
});

function showUsernameChangeModal() {
    bootstrap.Modal.getInstance(document.getElementById('profileModal')).hide();
    const usernameModal = new bootstrap.Modal(document.getElementById('usernameChangeModal'));
    usernameModal.show();
}

function showPasswordChangeModal() {
    bootstrap.Modal.getInstance(document.getElementById('profileModal')).hide();
    const passwordModal = new bootstrap.Modal(document.getElementById('passwordChangeModal'));
    passwordModal.show();
}

// Аналогичные обработчики для других форм 

function switchToEditMode() {
    document.getElementById('profileViewMode').style.display = 'none';
    document.getElementById('profileEditMode').style.display = 'block';
}

function switchToViewMode() {
    document.getElementById('profileEditMode').style.display = 'none';
    document.getElementById('profileViewMode').style.display = 'block';
}

function saveChanges() {
    // Если есть несохраненные изменения, сохраняем их
    switchToViewMode();
    showNotification('Profile updated successfully', 'success');
} 