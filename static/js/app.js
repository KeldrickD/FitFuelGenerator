// IndexedDB setup for offline data
const dbName = 'fitfuel-db';
const dbVersion = 1;

// Open IndexedDB
const openDB = () => {
    return new Promise((resolve, reject) => {
        const request = indexedDB.open(dbName, dbVersion);

        request.onerror = () => reject(request.error);
        request.onsuccess = () => resolve(request.result);

        request.onupgradeneeded = (event) => {
            const db = event.target.result;

            // Create stores
            if (!db.objectStoreNames.contains('workoutLogs')) {
                const workoutStore = db.createObjectStore('workoutLogs', { keyPath: 'id', autoIncrement: true });
                workoutStore.createIndex('date', 'date');
                workoutStore.createIndex('synced', 'synced');
            }
        };
    });
};

// Save workout log offline
async function saveWorkoutLog(log) {
    try {
        const db = await openDB();
        const tx = db.transaction('workoutLogs', 'readwrite');
        const store = tx.objectStore('workoutLogs');
        
        log.synced = false;
        await store.add(log);
        
        // Try to sync if online
        if (navigator.onLine) {
            syncWorkoutLogs();
        }
    } catch (error) {
        console.error('Error saving workout log:', error);
    }
}

// Get unsynced logs
async function getLogsToSync() {
    try {
        const db = await openDB();
        const tx = db.transaction('workoutLogs', 'readonly');
        const store = tx.objectStore('workoutLogs');
        const index = store.index('synced');
        
        return await index.getAll(false);
    } catch (error) {
        console.error('Error getting logs to sync:', error);
        return [];
    }
}

// Clear synced logs
async function clearSyncedLogs() {
    try {
        const db = await openDB();
        const tx = db.transaction('workoutLogs', 'readwrite');
        const store = tx.objectStore('workoutLogs');
        const index = store.index('synced');
        
        const syncedLogs = await index.getAll(true);
        for (const log of syncedLogs) {
            await store.delete(log.id);
        }
    } catch (error) {
        console.error('Error clearing synced logs:', error);
    }
}

// Theme toggling
function toggleTheme() {
    if (document.documentElement.classList.contains('dark')) {
        document.documentElement.classList.remove('dark');
        localStorage.theme = 'light';
    } else {
        document.documentElement.classList.add('dark');
        localStorage.theme = 'dark';
    }
}

// Loading overlay
function showLoading() {
    const overlay = document.getElementById('loading-overlay');
    if (overlay) {
        overlay.classList.remove('hidden');
    }
}

function hideLoading() {
    const overlay = document.getElementById('loading-overlay');
    if (overlay) {
        overlay.classList.add('hidden');
    }
}

// Toast notifications
function showToast(message, type = 'info') {
    const toast = document.createElement('div');
    const colors = {
        success: 'bg-green-100 border-green-500 text-green-700',
        error: 'bg-red-100 border-red-500 text-red-700',
        info: 'bg-blue-100 border-blue-500 text-blue-700',
        warning: 'bg-yellow-100 border-yellow-500 text-yellow-700'
    };
    
    toast.className = `fixed bottom-4 right-4 ${colors[type]} border-l-4 p-4 rounded shadow-lg`;
    toast.innerHTML = `
        <div class="flex items-center">
            <p>${message}</p>
        </div>
    `;
    
    document.body.appendChild(toast);
    setTimeout(() => toast.remove(), 5000);
}

// Form validation
function validateForm(form) {
    const requiredFields = form.querySelectorAll('[required]');
    let isValid = true;
    
    requiredFields.forEach(field => {
        if (!field.value.trim()) {
            isValid = false;
            field.classList.add('border-red-500');
            
            const errorMessage = field.dataset.error || 'This field is required';
            let errorDiv = field.nextElementSibling;
            
            if (!errorDiv || !errorDiv.classList.contains('error-message')) {
                errorDiv = document.createElement('div');
                errorDiv.className = 'error-message text-red-500 text-sm mt-1';
                field.parentNode.insertBefore(errorDiv, field.nextSibling);
            }
            
            errorDiv.textContent = errorMessage;
        } else {
            field.classList.remove('border-red-500');
            const errorDiv = field.nextElementSibling;
            if (errorDiv && errorDiv.classList.contains('error-message')) {
                errorDiv.remove();
            }
        }
    });
    
    return isValid;
}

// Initialize app
document.addEventListener('DOMContentLoaded', () => {
    // Check online status
    updateOnlineStatus();
    
    // Add form validation
    const forms = document.querySelectorAll('form');
    forms.forEach(form => {
        form.addEventListener('submit', (e) => {
            if (!validateForm(form)) {
                e.preventDefault();
            }
        });
    });
}); 