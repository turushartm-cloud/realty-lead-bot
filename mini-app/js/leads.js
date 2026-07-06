/**
 * Leads page logic
 */
class LeadsPage {
    constructor() {
        this.currentPage = 1;
        this.totalPages = 1;
        this.filters = { status: '', min_score: '', sort_by: 'created_at', sort_order: 'desc' };
        this.init();
    }

    async init() {
        try {
            await api.authenticate();
            await this.loadLeads();
        } catch (error) {
            console.error('Leads page init failed:', error);
        }
    }

    async loadLeads() {
        try {
            const container = document.getElementById('leadsFull');
            container.innerHTML = '<div class="loading">Загрузка...</div>';

            const params = {
                page: this.currentPage,
                per_page: 15,
                status: this.filters.status || undefined,
                min_score: this.filters.min_score || undefined,
                sort_by: this.filters.sort_by,
                sort_order: this.filters.sort_order
            };

            const response = await api.getLeads(params);
            this.totalPages = Math.ceil(response.total / response.per_page) || 1;

            if (response.items.length === 0) {
                container.innerHTML = `<div class="empty-state"><div class="empty-state-icon">📭</div><h3>Лидов не найдено</h3><p>Попробуйте изменить фильтры</p></div>`;
                document.getElementById('pagination').innerHTML = '';
                return;
            }

            container.innerHTML = response.items.map(lead => this.renderLead(lead)).join('');
            container.querySelectorAll('.lead-card').forEach(card => {
                card.addEventListener('click', () => this.openLeadDetail(card.dataset.id));
            });

            this.renderPagination();
        } catch (error) {
            console.error('Load leads failed:', error);
            document.getElementById('leadsFull').innerHTML = `<div class="empty-state"><div class="empty-state-icon">⚠️</div><h3>Ошибка загрузки</h3></div>`;
        }
    }

    renderLead(lead) {
        const scoreClass = lead.ai_score > 0.8 ? 'high' : lead.ai_score > 0.5 ? 'medium' : 'low';
        const statusClass = `status-${lead.status}`;
        const timeAgo = this.timeAgo(lead.created_at);
        return `
            <div class="lead-card" data-id="${lead.id}">
                <div class="lead-header">
                    <div class="lead-title">${this.escapeHtml(lead.ai_summary || lead.raw_text.substring(0, 60))}</div>
                    <div class="lead-score ${scoreClass}">${(lead.ai_score * 100).toFixed(0)}%</div>
                </div>
                <div class="lead-meta">
                    <span>📂 ${lead.ai_category || 'Unknown'}</span>
                    <span>👤 ${lead.extracted_name || 'No name'}</span>
                    <span>⚡ ${lead.priority}</span>
                </div>
                <div class="lead-preview">${this.escapeHtml(lead.raw_text.substring(0, 120))}...</div>
                <div class="lead-footer">
                    <span class="lead-status ${statusClass}">${lead.status}</span>
                    <span class="lead-time">${timeAgo}</span>
                </div>
            </div>`;
    }

    renderPagination() {
        const container = document.getElementById('pagination');
        let html = '';
        if (this.currentPage > 1) {
            html += `<button onclick="goToPage(${this.currentPage - 1})">◀️</button>`;
        }
        html += `<button class="active">${this.currentPage} / ${this.totalPages}</button>`;
        if (this.currentPage < this.totalPages) {
            html += `<button onclick="goToPage(${this.currentPage + 1})">▶️</button>`;
        }
        container.innerHTML = html;
    }

    async openLeadDetail(leadId) {
        window.currentLeadId = leadId;
        try {
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
            tgApp.hapticImpact('light');
        } catch (error) {
            tgApp.showAlert('Ошибка загрузки');
        }
    }

    closeModal() {
        document.getElementById('leadModal').classList.remove('active');
        tgApp.tg.BackButton.hide();
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

    async changeStatus() {
        if (!window.currentLeadId) return;
        const statuses = { new: '🆕 Новый', contacted: '📞 Связались', qualified: '✅ Квалифицирован', converted: '💰 Конвертирован', rejected: '❌ Отклонен' };
        const options = Object.entries(statuses).map(([k, v]) => `${k}:${v}`).join(',');
        const newStatus = prompt(`Выберите статус (${options}):`);
        if (newStatus && statuses[newStatus]) {
            await api.updateLead(window.currentLeadId, { status: newStatus });
            tgApp.hapticNotification('success');
            this.closeModal();
            this.loadLeads();
        }
    }

    async syncToCRM() {
        if (!window.currentLeadId) return;
        try {
            tgApp.showProgress();
            await api.syncToCRM(window.currentLeadId);
            tgApp.hideProgress();
            tgApp.hapticNotification('success');
            tgApp.showAlert('✅ В CRM!');
        } catch (error) {
            tgApp.hideProgress();
            tgApp.showAlert('❌ Ошибка');
        }
    }

    applyFilters() {
        this.filters.status = document.getElementById('statusFilter').value;
        this.filters.min_score = document.getElementById('scoreFilter').value;
        const sort = document.getElementById('sortFilter').value.split(':');
        this.filters.sort_by = sort[0];
        this.filters.sort_order = sort[1];
        this.currentPage = 1;
        this.loadLeads();
    }

    goToPage(page) {
        this.currentPage = page;
        this.loadLeads();
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
}

const leadsPage = new LeadsPage();

function closeModal() { leadsPage.closeModal(); }
function takeLead() { leadsPage.takeLead(); }
function changeStatus() { leadsPage.changeStatus(); }
function syncToCRM() { leadsPage.syncToCRM(); }
function applyFilters() { leadsPage.applyFilters(); }
function goToPage(page) { leadsPage.goToPage(page); }
