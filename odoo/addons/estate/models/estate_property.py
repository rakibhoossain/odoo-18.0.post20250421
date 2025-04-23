from odoo import fields, models

class EstateProperty(models.Model):
    _name = 'estate_property'
    _description = "Estate property model"

    name = fields.Char(required=True)
    description = fields.Html("Vehicle Description")
    postcode = fields.Char()
    date_availability = fields.Date("Date Availability")
    expected_price = fields.Float(help="Expected Price", required=True)
    selling_price = fields.Float("Selling Price")
    bedrooms = fields.Float("Bedrooms")
    living_area = fields.Float("Living Area")
    facades = fields.Float("Facades")
    garage = fields.Boolean("Garage")
    garden = fields.Boolean("Garden")
    garden_area = fields.Integer("Garden Area")
    garden_orientation = fields.Selection(
        string='Type',
        selection=[('north', 'North'), ('south', 'South'), ('east', 'East'), ('west', 'West')],
        help="Garden orientation")