from odoo import models, fields, api


class EmsDashboard(models.TransientModel):
    _name = 'ems.dashboard'
    _description = 'EMS Dashboard'
    _transient = True
    _inherit = ['mail.thread']

    # Computed Fields
    total_stations = fields.Integer(compute='_compute_dashboard_data')
    active_drugs = fields.Integer(compute='_compute_dashboard_data')
    expiring_soon = fields.Integer(compute='_compute_dashboard_data')

    # Graph Data
    drugs_by_station = fields.Json(compute='_compute_graph_data')
    inventory_movements = fields.Json(compute='_compute_graph_data')

    # Table Data
    recent_movements = fields.Json(compute='_compute_recent_movements')

    def _compute_dashboard_data(self):
        station_count = self.env['ems.station'].search_count([])
        drug_count = self.env['ems.drug'].search_count([('active', '=', True)])

        # Drugs expiring in next 30 days
        expiring_count = self.env['ems.drug.lot'].search_count([
            ('expiry_date', '<=', fields.Date.add(fields.Date.today(), days=30)),
            ('expiry_date', '>=', fields.Date.today()),
            ('status', '=', 'active')
        ])

        for record in self:
            record.total_stations = station_count
            record.active_drugs = drug_count
            record.expiring_soon = expiring_count

    def _compute_graph_data(self):
        # Drugs by Station
        stations = self.env['ems.station'].search([])
        station_data = []

        for station in stations:
            drug_count = self.env['ems.drug.lot'].search_count([
                ('station_id', '=', station.id),
                ('status', '=', 'active')
            ])
            station_data.append({
                'label': station.name,
                'value': drug_count
            })

        # Inventory movements (last 30 days)
        movements = self.env['ems.inventory.log'].read_group(
            [('timestamp', '>=', fields.Date.add(fields.Date.today(), days=-30))],
            ['action_type', 'quantity:sum'],
            ['action_type']
        )

        movement_data = [{
            'label': item['action_type'],
            'value': item['quantity']
        } for item in movements]

        for record in self:
            record.drugs_by_station = {
                'data': station_data,
                'title': 'Drugs by Station',
                'type': 'bar'
            }

            record.inventory_movements = {
                'data': movement_data,
                'title': 'Inventory Movements (30 days)',
                'type': 'pie'
            }

    def _compute_recent_movements(self):
        movements = self.env['ems.inventory.log'].search([
            ('timestamp', '>=', fields.Date.add(fields.Date.today(), days=-7))
        ], limit=10, order='timestamp DESC')

        table_data = []
        for move in movements:
            table_data.append({
                'timestamp': move.timestamp,
                'drug': move.drug_id.name,
                'action': move.action_type,
                'quantity': move.quantity,
                'user': move.user_id.name
            })

        for record in self:
            record.recent_movements = {
                'columns': [
                    {'name': 'timestamp', 'string': 'Date', 'type': 'datetime'},
                    {'name': 'drug', 'string': 'Drug', 'type': 'char'},
                    {'name': 'action', 'string': 'Action', 'type': 'char'},
                    {'name': 'quantity', 'string': 'Quantity', 'type': 'integer'},
                    {'name': 'user', 'string': 'User', 'type': 'char'}
                ],
                'rows': table_data
            }

    @api.model
    def get_dashboard_data(self):
        # Compute stats
        total_stations = self.env['ems.station'].search_count([])
        active_drugs = self.env['ems.drug'].search_count([('active', '=', True)])
        expiring_soon = self.env['ems.drug.lot'].search_count([
            ('expiry_date', '<=', fields.Date.add(fields.Date.today(), days=30)),
            ('expiry_date', '>=', fields.Date.today()),
            ('status', '=', 'active')
        ])

        # Drugs by Station
        stations = self.env['ems.station'].search([])
        drugs_by_station = []
        for station in stations:
            drug_count = self.env['ems.drug.lot'].search_count([
                ('station_id', '=', station.id),
                ('status', '=', 'active')
            ])
            drugs_by_station.append({
                'label': station.name,
                'value': drug_count
            })

        # Inventory Movements
        movements = self.env['ems.inventory.log'].read_group(
            [('timestamp', '>=', fields.Date.add(fields.Date.today(), days=-30))],
            ['action_type', 'quantity:sum'],
            ['action_type']
        )
        inventory_movements = [{
            'label': m['action_type'],
            'value': m['quantity']
        } for m in movements]

        # Recent Movements
        recent = self.env['ems.inventory.log'].search([
            ('timestamp', '>=', fields.Date.add(fields.Date.today(), days=-7))
        ], limit=10, order='timestamp DESC')

        recent_movements = [{
            'timestamp': move.timestamp,
            'drug': move.drug_id.name,
            'action': move.action_type,
            'quantity': move.quantity,
            'user': move.user_id.name
        } for move in recent]

        return {
            "stats": {
                "total_stations": total_stations,
                "active_drugs": active_drugs,
                "expiring_soon": expiring_soon,
            },
            "drugs_by_station": drugs_by_station,
            "inventory_movements": inventory_movements,
            "recent_movements": recent_movements,
        }

