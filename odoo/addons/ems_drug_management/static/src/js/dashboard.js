/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component, onWillStart, onMounted } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { loadJS } from "@web/core/assets";

export class EmsDashboard extends Component {
    setup() {
        this.orm = useService("orm");
        this.state = {
            stats: {},
            drugsByStation: [],
            inventoryMovements: [],
            recentMovements: []
        };

        onWillStart(async () => {
            const data = await this.orm.call("ems.dashboard", "get_dashboard_data");
            this.state.stats = data.stats;
            this.state.drugsByStation = data.drugs_by_station;
            this.state.inventoryMovements = data.inventory_movements;
            this.state.recentMovements = data.recent_movements;

            console.log('this.state', this.state)
        });


        onMounted(async () => {
            await loadJS("https://cdn.jsdelivr.net/npm/chart.js"); // Load Chart.js dynamically

            const renderChart = (canvasId, data, type = "bar") => {
                const ctx = document.getElementById(canvasId);
                if (!ctx || !data.length) return;
                new Chart(ctx, {
                    type,
                    data: {
                        labels: data.map(d => d.label),
                        datasets: [{
                            label: '',
                            data: data.map(d => d.value),
                            backgroundColor: [
                                '#3e95cd', '#8e5ea2', '#3cba9f', '#e8c3b9', '#c45850'
                            ],
                        }]
                    },
                    options: {
                        responsive: true,
                        plugins: {
                            legend: { display: false },
                        }
                    }
                });
            };

            setTimeout(() => {
                renderChart("drugs_by_station_chart", this.state.drugsByStation, "bar");
                renderChart("inventory_movements_chart", this.state.inventoryMovements, "doughnut");
            }, 50);
        });
    }
}

EmsDashboard.template = "ems_dashboard.Template";

registry.category("actions").add("ems_dashboard", EmsDashboard);