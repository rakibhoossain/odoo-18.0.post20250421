# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    # Coworking-related fields
    booking_id = fields.Many2one('coworking.booking', string='Related Booking')
    membership_id = fields.Many2one('coworking.membership', string='Related Membership')
    is_coworking_order = fields.Boolean(string='Is Coworking Order', compute='_compute_is_coworking_order', store=True)
    
    @api.depends('booking_id', 'membership_id', 'order_line.booking_id')
    def _compute_is_coworking_order(self):
        for order in self:
            order.is_coworking_order = bool(order.booking_id or order.membership_id or 
                                          any(line.booking_id for line in order.order_line))


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    booking_id = fields.Many2one('coworking.booking', string='Related Booking')
    event_registration_id = fields.Many2one('coworking.event.registration', string='Related Event Registration')
    membership_id = fields.Many2one('coworking.membership', string='Related Membership')
