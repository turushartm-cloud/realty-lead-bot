/**
 * Main application logic for index.html
 */
class RealtyApp {
    constructor() {
        this.currentPage = 1;
        this.leads = [];
        this.filters = { status: null, search: '', min_score: null };
        this.init();
    }

    async init() {
        try {
            await api.authenticate();
            await Promise.all([this.loadStats(), this.loadLeads()]);
            this.setupEventListeners();
            tgApp.tg.BackButton.onClick(() => this.closeModal());
        } catch (error) {
            console.error('App init failed:', error);
            this.showError('Failed to initialize');
        }
    }

    setupEventListeners() {
        document.getElementById('searchBtn').addEventListener('click', () => {
            const bar = document.getElementById('searchBar');
            bar.style.display = bar.style.display === 'none' ? 'flex' : 'none';
            if (bar.style.display === 'flex') document.getElementById('searchInput').focus();
        });
        document.getElementById('closeSearch').addEventListener('click', () => {
            document.getElementById('searchBar').style.display = 'none';
            this.filters.search = '';
            this.loadLeads();
        });
        document.getElementById('searchInput').addEventListener('input', (e) => {
            this.filters.search = e.target.value;
            this.debounce(this.loadLeads.bind(this), 300)();
        });
        document.getElementById('filterBtn').addEventListener('click', () => {
            tgApp.showAlert('Фильтры: используйте страницу "Лиды" для расширенной фильтрации');
        });
    }

    debounce(func, wait) {
        let timeout;
        return (...args) => {
            clearTimeout(timeout);
            timeout = setTimeout(() => func(...args), wait);
        };
    }

    async loadStats() {
        try {
            const stats = await api.getSummary();
            document.getElementById('totalLeads').textContent = stats.total_leads;
            document.getElementById('newLeads').textContent = stats.new_leads_24h;
            document.getElementById('conversionRate').textContent = stats.conversion_rate + '%';
            document.getElementById('avgScore').textContent = stats.avg_ai_score.toFixed(1);
        } catch (error) {
            console.error('Stats load failed:', error);
        }
    }

    async loadLeads() {
        try {
            const container = document.getElementById('leadsList');
            container.innerHTML = '<div class="loading">Загрузка...</div>';
            const params = { page: this.currentPage, per_page: 20, ...this.filters };
            const response = await api.getLeads(params);
            this.leads = response.items;
            if (this.leads.length === 0) {
                container.innerHTML = `<div class="empty-state"><div class="empty-state-icon">📭</div><h3>Лидов не найдено</h3><p>Измените фильтры или подождите новых заявок</p></div>`;
                return;
            }
            container.innerHTML = this.leads.map(lead => this.renderLeadCard(lead)).join('');
            container.querySelectorAll('.lead-card').forEach(card => {
                card.addEventListener('click', () => this.openLeadDetail(card.dataset.id));
            });
        } catch (error) {
            console.error('Leads load failed:', error);
            document.getElementById('leadsList').innerHTML = `<div class="empty-state"><div class="empty-state-icon">⚠️</div><h3>Ошибка загрузки</h3><p>Попробуйте позже</p></div>`;
        }
    }

    renderLeadCard(lead) {
        const scoreClass = lead.ai_score > 0.8 ? 'high' : lead.ai_score > 0.5 ? 'medium' : 'low';
        const statusClass = `status-${lead.status}`;
        const timeAgo = this.timeAgo(lead.created_at);
        return `
            <div class="lead-card" data-id="${lead.id}">
                <div class="lead-header">
                    <div class="lead-title">${this.escapeHtml(lead.ai_summary || lead.raw_text.substring(0, 50))}</div>
                    <div class="lead-score ${scoreClass}">${(lead.ai_score * 100).toFixed(0)}%</div>
                </div>
                <div class="lead-meta">
                    <span>📂 ${lead.ai_category || 'Unknown'}</span>
                    <span>👤 ${lead.extracted_name || 'No name'}</span>
                </div>
                <div class="lead-preview">${this.escapeHtml(lead.raw_text.substring(0, 100))}...</div>
                <div class="lead-footer">
                    <span class="lead-status ${statusClass}">${lead.status}</span>
                    <span class="lead-time">${timeAgo}</span>
                </div>
            </div>`;
    }

    async openLeadDetail(leadId) {
        try {
            window.currentLeadId = leadId;
            const lead = await api.getLead(leadId);
            document.getElementById('modalTitle').textContent = `Лид #${lead.id}`;
            document.getElementById('modalBody').innerHTML = `
                <div class="lead-detail">
                    <div class="detail-section"><label>AI Score</label><div class="detail-score ${lead.ai_score > 0.8 ? 'high' : 'medium'}">${(lead.ai_score * 100).toFixed(0)}%</div></div>
                    <div class="detail-section"><label>Категория</label><div>${lead.ai_category || 'Unknown'}</div></div>
                    <div class="detail-section"><label>Сообщение</label><div class="detail-text">${this.escapeHtml(lead.raw_text)}</div></div>
                    ${lead.phone ? `<div class="detail-section"><label>📞 Телефон</label><div><a href="tel:${lead.phone}">${lead.phone}</a></div></div>` : ''}
                    ${lead.email ? `<div class="detail-section"><label>📧 Email</label><div><a href="mailto:${lead.email}">${lead.email}</a></div></div>` : ''}
                    ${lead.telegram_username ? `<div class="detail-section"><label>💬 Telegram</label><div>@${lead.telegram_username}</div></div>` : ''}
                    ${lead.notes ? `<div class="detail-section"><label>📝 Заметки</label><div>${this.escapeHtml(lead.notes)}</div></div>` : ''}
                </div>`;
            document.getElementById('leadModal').classList.add('active');
            tgApp.tg.BackButton.show();
            tgApp.showMainButton('📤 В CRM');
            tgApp.hapticImpact('light');
        } catch (error) {
            tgApp.showAlert('Ошибка загрузки лида');
        }
    }

    closeModal() {
        document.getElementById('leadModal').classList.remove('active');
        tgApp.tg.BackButton.hide();
        tgApp.hideMainButton();
        window.currentLeadId = null;
    }

    async takeLead() {
        if (!window.currentLeadId) return;
        try {
            await api.updateLead(window.currentLeadId, { status: 'contacted' });
            tgApp.hapticNotification('success');
            tgApp.showAlert('✅ Лид взят в работу!');
            this.closeModal();
            this.loadLeads();
        } catch (error) { tgApp.showAlert('❌ Ошибка'); }
    }

    async syncToCRM() {
        if (!window.currentLeadId) return;
        try {
            tgApp.showProgress();
            await api.syncToCRM(window.currentLeadId);
            tgApp.hideProgress();
            tgApp.hapticNotification('success');
            tgApp.showAlert('✅ Синхронизировано с CRM!');
        } catch (error) {
            tgApp.hideProgress();
            tgApp.showAlert('❌ Ошибка синхронизации');
        }
    }

    async addNote() {
        if (!window.currentLeadId) return;
        const note = prompt('Введите заметку:');
        if (note) {
            await api.updateLead(window.currentLeadId, { notes: note });
            tgApp.hapticNotification('success');
            this.openLeadDetail(window.currentLeadId);
        }
    }

    filterByStatus(status) {
        this.filters.status = status;
        this.loadLeads();
    }

    exportLeads() {
        api.exportExcel();
    }

    showAllLeads() {
        window.location.href = 'leads.html';
    }

    timeAgo(dateString) {
        const date = new Date(dateString);
        const now = new Date();
        const diff = Math.floor((now - date) / 1000);
        if (diff < 60) return 'только что';
        if (diff < 3600) return `${Math.floor(diff / 60)} мин назад`;
        if (diff < 86400) return `${Math.floor(diff / 3600)} ч назад`;
        return `${Math.floor(diff / 86400)} д назад`;
    }

    escapeHtml(text) {
        if (!text) return '';
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    showError(msg) {
        document.getElementById('leadsList').innerHTML = `<div class="empty-state"><div class="empty-state-icon">⚠️</div><h3>Ошибка</h3><p>${msg}</p></div>`;
    }
}

const app = new RealtyApp();

// Global functions for onclick handlers
function closeModal() { app.closeModal(); }
function takeLead() { app.takeLead(); }
function syncToCRM() { app.syncToCRM(); }
function addNote() { app.addNote(); }
function filterByStatus(status) { app.filterByStatus(status); }
function exportLeads() { app.exportLeads(); }
function showAllLeads() { app.showAllLeads(); }
