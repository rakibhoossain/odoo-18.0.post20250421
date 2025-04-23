from odoo import fields, models
from odoo.exceptions import UserError, ValidationError

class EstateProperty(models.Model):
    _name = 'estate.property'
    _description = "Estate property model"

    name = fields.Char(required=True)
    description = fields.Html("Vehicle Description")
    postcode = fields.Char()
    date_availability = fields.Date("Date Availability", default=fields.Datetime.now)
    expected_price = fields.Float(help="Expected Price", required=True)
    selling_price = fields.Float("Selling Price", readonly=True)
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

    state = fields.Selection(
        selection=[
            ("new", "New"),
            ("offer_received", "Offer Received"),
            ("offer_accepted", "Offer Accepted"),
            ("sold", "Sold"),
            ("canceled", "Canceled"),
        ],
        string="Status",
        required=True,
        copy=False,
        default="new",
    )
    active = fields.Boolean("Active", default=True)

    def action_sold(self):
        if "canceled" in self.mapped("state"):
            raise UserError("Canceled properties cannot be sold.")
        return self.write({"state": "sold"})

    def action_cancel(self):
        if "sold" in self.mapped("state"):
            raise UserError("Sold properties cannot be canceled.")
        return self.write({"state": "canceled"})