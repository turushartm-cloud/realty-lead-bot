/**
 * API Client for backend communication
 */
class APIClient {
    constructor() {
        this.baseURL = '/api/v1';
        this.token = localStorage.getItem('jwt_token');
    }

    async request(endpoint, options = {}) {
        const url = `${this.baseURL}${endpoint}`;
        const headers = {
            'Content-Type': 'application/json',
            ...tgApp.getAuthHeaders(),
            ...(this.token ? { 'Authorization': `Bearer ${this.token}` } : {})
        };
        try {
            const response = await fetch(url, { ...options, headers: { ...headers, ...options.headers } });
            if (response.status === 401) {
                await this.authenticate();
                return this.request(endpoint, options);
            }
            if (!response.ok) throw new Error(`HTTP ${response.status}: ${await response.text()}`);
            return await response.json();
        } catch (error) {
            console.error('API Error:', error);
            throw error;
        }
    }

    async authenticate() {
        const response = await fetch(`${this.baseURL}/auth/telegram`, {
            method: 'POST',
            headers: tgApp.getAuthHeaders()
        });
        if (!response.ok) throw new Error('Authentication failed');
        const data = await response.json();
        this.token = data.access_token;
        localStorage.setItem('jwt_token', this.token);
        return data;
    }

    async getLeads(params = {}) {
        const query = new URLSearchParams(params).toString();
        return this.request(`/leads/?${query}`);
    }
    async getLead(id) { return this.request(`/leads/${id}`); }
    async updateLead(id, data) {
        return this.request(`/leads/${id}`, { method: 'PATCH', body: JSON.stringify(data) });
    }
    async deleteLead(id) { return this.request(`/leads/${id}`, { method: 'DELETE' }); }
    async getSummary() { return this.request('/analytics/summary'); }
    async getTimeline(days = 30) { return this.request(`/analytics/timeline?days=${days}`); }
    async getByCategory() { return this.request('/analytics/by-category'); }
    async getByGroup() { return this.request('/analytics/by-group'); }
    async exportLeads(leadIds, format = 'xlsx') {
        return this.request('/crm/export', {
            method: 'POST',
            body: JSON.stringify({ lead_ids: leadIds, format: format })
        });
    }
    async syncToCRM(leadId) {
        return this.request(`/crm/sync/${leadId}`, { method: 'POST' });
    }
    async exportExcel(params = {}) {
        const query = new URLSearchParams(params).toString();
        window.open(`${this.baseURL}/export/excel?${query}`, '_blank');
    }
}

const api = new APIClient();
