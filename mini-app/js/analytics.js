/**
 * Analytics page logic
 */
class AnalyticsPage {
    constructor() { this.init(); }

    async init() {
        try {
            await api.authenticate();
            await Promise.all([
                this.loadTimeline(),
                this.loadCategories(),
                this.loadGroups(),
                this.loadStatsTable()
            ]);
        } catch (error) {
            console.error('Analytics init failed:', error);
        }
    }

    async loadTimeline() {
        const data = await api.getTimeline(30);
        const ctx = document.getElementById('timelineChart').getContext('2d');
        new Chart(ctx, {
            type: 'line',
            data: {
                labels: data.labels,
                datasets: [{
                    label: 'Лиды',
                    data: data.leads,
                    borderColor: '#FF6B35',
                    backgroundColor: 'rgba(255, 107, 53, 0.1)',
                    fill: true,
                    tension: 0.4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { display: false } },
                scales: { y: { beginAtZero: true } }
            }
        });
    }

    async loadCategories() {
        const data = await api.getByCategory();
        const ctx = document.getElementById('categoryChart').getContext('2d');
        new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: data.categories,
                datasets: [{
                    data: data.counts,
                    backgroundColor: ['#FF6B35', '#4A90D9', '#27AE60', '#F2C94C', '#EB5757', '#56CCF2']
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { position: 'bottom' } }
            }
        });
    }

    async loadGroups() {
        const data = await api.getByGroup();
        const ctx = document.getElementById('groupChart').getContext('2d');
        new Chart(ctx, {
            type: 'bar',
            data: {
                labels: data.groups,
                datasets: [{
                    label: 'Лиды',
                    data: data.counts,
                    backgroundColor: '#4A90D9',
                    borderRadius: 6
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { display: false } },
                scales: { y: { beginAtZero: true } }
            }
        });
    }

    async loadStatsTable() {
        const stats = await api.getSummary();
        const table = document.getElementById('statsTable');
        table.innerHTML = `
            <tr><th>Метрика</th><th>Значение</th></tr>
            <tr><td>Всего лидов</td><td><b>${stats.total_leads}</b></td></tr>
            <tr><td>Новые (24ч)</td><td><b>${stats.new_leads_24h}</b></td></tr>
            <tr><td>Конвертировано</td><td><b>${stats.converted_leads}</b></td></tr>
            <tr><td>Конверсия</td><td><b>${stats.conversion_rate}%</b></td></tr>
            <tr><td>Средний AI Score</td><td><b>${stats.avg_ai_score}</b></td></tr>
            <tr><td>Топ источник</td><td><b>${stats.top_source}</b></td></tr>
        `;
        Object.entries(stats.leads_by_status).forEach(([status, count]) => {
            table.innerHTML += `<tr><td>Статус: ${status}</td><td>${count}</td></tr>`;
        });
    }
}

const analyticsPage = new AnalyticsPage();
