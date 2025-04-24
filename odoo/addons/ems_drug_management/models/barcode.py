from odoo import models, fields, api

class EmsBarcode(models.AbstractModel):
    _name = 'ems.barcode.mixin'
    _description = 'Barcode Mixin'

    barcode = fields.Char(string="Barcode", copy=False)

    @api.model
    def create_from_scan(self, barcode):
        """Create or update record based on barcode scan"""
        record = self.search([('barcode', '=', barcode)], limit=1)
        if record:
            return record
        return self.create({'barcode': barcode})

    def action_scan_barcode(self):
        return {
            'type': 'ir.actions.client',
            'tag': 'ems_barcode_scan',
            'name': 'Scan Barcode',
        }