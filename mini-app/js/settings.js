/**
 * Settings page logic
 */
class SettingsPage {
    constructor() { this.init(); }

    async init() {
        try {
            await api.authenticate();
            this.loadSettings();
        } catch (error) {
            console.error('Settings init failed:', error);
        }
    }

    loadSettings() {
        const settings = JSON.parse(localStorage.getItem('crm_settings') || '{}');
        if (settings.notify_new_lead !== undefined) document.getElementById('notifyNew').checked = settings.notify_new_lead;
        if (settings.notify_daily_digest !== undefined) document.getElementById('notifyDigest').checked = settings.notify_daily_digest;
        if (settings.notify_threshold) {
            document.getElementById('aiThreshold').value = settings.notify_threshold * 100;
            document.getElementById('thresholdValue').textContent = Math.round(settings.notify_threshold * 100) + '%';
        }
        if (settings.crm_webhook_url) document.getElementById('crmWebhook').value = settings.crm_webhook_url;
        if (settings.auto_export !== undefined) document.getElementById('autoExport').checked = settings.auto_export;
    }

    saveSettings() {
        const settings = {
            notify_new_lead: document.getElementById('notifyNew').checked,
            notify_daily_digest: document.getElementById('notifyDigest').checked,
            notify_threshold: parseInt(document.getElementById('aiThreshold').value) / 100,
            crm_webhook_url: document.getElementById('crmWebhook').value,
            auto_export: document.getElementById('autoExport').checked
        };
        localStorage.setItem('crm_settings', JSON.stringify(settings));
        tgApp.hapticNotification('success');
        tgApp.showAlert('✅ Настройки сохранены!');
    }

    updateThreshold(value) {
        document.getElementById('thresholdValue').textContent = value + '%';
    }

    addKeyword(event) {
        if (event.key === 'Enter') {
            const input = event.target;
            const value = input.value.trim();
            if (value) {
                const tagsContainer = document.getElementById('keywordsTags');
                const tag = document.createElement('span');
                tag.className = 'tag';
                tag.innerHTML = `${value}<span class="tag-remove" onclick="this.parentElement.remove()">✕</span>`;
                tagsContainer.insertBefore(tag, input);
                input.value = '';
            }
        }
    }

    clearCache() {
        tgApp.showConfirm('Очистить локальный кэш?', (confirmed) => {
            if (confirmed) {
                localStorage.clear();
                tgApp.hapticNotification('success');
                tgApp.showAlert('✅ Кэш очищен');
            }
        });
    }

    logout() {
        tgApp.showConfirm('Выйти из аккаунта?', (confirmed) => {
            if (confirmed) {
                localStorage.removeItem('jwt_token');
                tgApp.close();
            }
        });
    }
}

const settingsPage = new SettingsPage();

function saveSettings() { settingsPage.saveSettings(); }
function updateThreshold(value) { settingsPage.updateThreshold(value); }
function addKeyword(event) { settingsPage.addKeyword(event); }
function clearCache() { settingsPage.clearCache(); }
function logout() { settingsPage.logout(); }
