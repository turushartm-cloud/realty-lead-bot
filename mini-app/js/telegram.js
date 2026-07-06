/**
 * Telegram WebApp SDK wrapper
 */
class TelegramApp {
    constructor() {
        this.tg = window.Telegram.WebApp;
        this.initData = this.tg.initData;
        this.initDataUnsafe = this.tg.initDataUnsafe;
        this.user = this.initDataUnsafe?.user;
        this.init();
    }

    init() {
        this.tg.ready();
        this.tg.expand();
        this.tg.setHeaderColor('#FAFBFC');
        this.tg.setBackgroundColor('#FAFBFC');
        this.tg.enableClosingConfirmation();
        this.tg.MainButton.setText('✅ В CRM');
        this.tg.MainButton.onClick(() => {
            if (window.currentLeadId) syncToCRM();
        });
        console.log('Telegram WebApp initialized', {
            platform: this.tg.platform,
            version: this.tg.version
        });
    }

    getAuthHeaders() {
        return {
            'X-Telegram-Init-Data': this.initData,
            'Content-Type': 'application/json'
        };
    }

    showMainButton(text) {
        this.tg.MainButton.setText(text);
        this.tg.MainButton.show();
    }

    hideMainButton() {
        this.tg.MainButton.hide();
    }

    showProgress() { this.tg.MainButton.showProgress(); }
    hideProgress() { this.tg.MainButton.hideProgress(); }
    showAlert(message) { this.tg.showAlert(message); }
    showConfirm(message, callback) { this.tg.showConfirm(message, callback); }
    openLink(url) { this.tg.openLink(url); }
    close() { this.tg.close(); }

    hapticImpact(style = 'light') {
        if (this.tg.HapticFeedback) this.tg.HapticFeedback.impactOccurred(style);
    }
    hapticNotification(type = 'success') {
        if (this.tg.HapticFeedback) this.tg.HapticFeedback.notificationOccurred(type);
    }
}

const tgApp = new TelegramApp();
