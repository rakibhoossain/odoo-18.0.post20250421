# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import logging

_logger = logging.getLogger(__name__)


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'
    
    booking_id = fields.Many2one('coworking.booking', string='Related Booking')
    usage_id = fields.Many2one('coworking.usage', string='Related Usage')
    membership_id = fields.Many2one('coworking.membership', string='Related Membership')


class CoworkingInvoiceGenerator(models.Model):
    _name = 'coworking.invoice.generator'
    _description = 'Coworking Invoice Generator'

    name = fields.Char(string='Generation Name', required=True)
    date_from = fields.Date(string='From Date', required=True)
    date_to = fields.Date(string='To Date', required=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('generated', 'Generated'),
        ('validated', 'Validated')
    ], string='Status', default='draft')
    
    invoice_ids = fields.One2many('account.move', 'invoice_generator_id', string='Generated Invoices')
    invoice_count = fields.Integer(string='Invoice Count', compute='_compute_invoice_count')
    
    @api.depends('invoice_ids')
    def _compute_invoice_count(self):
        for generator in self:
            generator.invoice_count = len(generator.invoice_ids)
    
    def action_generate_invoices(self):
        """Generate monthly invoices for all active memberships"""
        self.ensure_one()
        
        # Get all active memberships
        active_memberships = self.env['coworking.membership'].search([
            ('state', '=', 'active')
        ])
        
        invoices_created = 0
        
        for membership in active_memberships:
            invoice = self._create_membership_invoice(membership)
            if invoice:
                invoices_created += 1
        
        self.state = 'generated'
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Invoices Generated'),
                'message': _('%d invoices have been generated successfully.') % invoices_created,
                'type': 'success',
            }
        }
    
    def _create_membership_invoice(self, membership):
        """Create invoice for a specific membership"""
        partner = membership.partner_id
        
        # Check if invoice already exists for this period
        existing_invoice = self.env['account.move'].search([
            ('partner_id', '=', partner.id),
            ('invoice_generator_id', '=', self.id),
            ('move_type', '=', 'out_invoice'),
            ('state', '=', 'draft')
        ], limit=1)
        
        if existing_invoice:
            _logger.info(f'Invoice already exists for membership {membership.name}')
            return existing_invoice
        
        # Create invoice
        invoice_vals = {
            'partner_id': partner.id,
            'move_type': 'out_invoice',
            'invoice_date': fields.Date.today(),
            'invoice_generator_id': self.id,
            'ref': f'Monthly Invoice - {membership.name}',
            'invoice_line_ids': []
        }
        
        # Add subscription fee line
        subscription_line = self._create_subscription_line(membership)
        if subscription_line:
            invoice_vals['invoice_line_ids'].append((0, 0, subscription_line))
        
        # Add meeting room usage lines
        room_lines = self._create_room_usage_lines(membership)
        for line in room_lines:
            invoice_vals['invoice_line_ids'].append((0, 0, line))
        
        # Add event participation lines
        event_lines = self._create_event_lines(membership)
        for line in event_lines:
            invoice_vals['invoice_line_ids'].append((0, 0, line))
        
        # Add coworking usage lines (manual entry)
        coworking_lines = self._create_coworking_usage_lines(membership)
        for line in coworking_lines:
            invoice_vals['invoice_line_ids'].append((0, 0, line))
        
        # Only create invoice if there are lines
        if invoice_vals['invoice_line_ids']:
            invoice = self.env['account.move'].create(invoice_vals)
            _logger.info(f'Created invoice {invoice.name} for membership {membership.name}')
            return invoice
        
        return False
    
    def _create_subscription_line(self, membership):
        """Create subscription fee line"""
        if membership.plan_id.monthly_price > 0:
            product = self._get_subscription_product(membership.plan_id)
            return {
                'product_id': product.id,
                'name': f'Subscription Fee - {membership.plan_id.name}',
                'quantity': 1,
                'price_unit': membership.plan_id.monthly_price,
                'membership_id': membership.id,
            }
        return False
    
    def _create_room_usage_lines(self, membership):
        """Create meeting room usage lines"""
        lines = []
        
        # Get room bookings for the period
        bookings = self.env['coworking.booking'].search([
            ('membership_id', '=', membership.id),
            ('state', '=', 'completed'),
            ('start_datetime', '>=', self.date_from),
            ('start_datetime', '<=', self.date_to),
            ('total_amount', '>', 0)  # Only paid bookings
        ])
        
        if bookings:
            # Group by room or create single line
            total_hours = sum(bookings.mapped('duration'))
            total_amount = sum(bookings.mapped('total_amount'))
            
            if total_hours > 0:
                product = self._get_room_booking_product()
                lines.append({
                    'product_id': product.id,
                    'name': f'Meeting Room Usage ({len(bookings)} bookings)',
                    'quantity': total_hours,
                    'price_unit': total_amount / total_hours if total_hours > 0 else 0,
                    'membership_id': membership.id,
                })
                
                # Mark bookings as invoiced
                for booking in bookings:
                    booking.invoice_line_ids = [(4, self.id)]
        
        return lines
    
    def _create_event_lines(self, membership):
        """Create event participation lines"""
        lines = []
        
        # Get event registrations for the period
        registrations = self.env['coworking.event.registration'].search([
            ('membership_id', '=', membership.id),
            ('state', 'in', ['confirmed', 'attended']),
            ('registration_date', '>=', self.date_from),
            ('registration_date', '<=', self.date_to),
            ('price', '>', 0)  # Only paid events
        ])
        
        if registrations:
            total_amount = sum(registrations.mapped('price'))
            if total_amount > 0:
                product = self._get_event_product()
                lines.append({
                    'product_id': product.id,
                    'name': f'Event Participation ({len(registrations)} events)',
                    'quantity': len(registrations),
                    'price_unit': total_amount / len(registrations) if registrations else 0,
                    'membership_id': membership.id,
                })
        
        return lines
    
    def _create_coworking_usage_lines(self, membership):
        """Create coworking space usage lines (manual entry)"""
        lines = []
        
        # Get usage records for the period
        usage_records = self.env['coworking.usage'].search([
            ('membership_id', '=', membership.id),
            ('date', '>=', self.date_from),
            ('date', '<=', self.date_to),
            ('usage_type', '=', 'coworking'),
            ('invoiced', '=', False)
        ])
        
        if usage_records:
            total_hours = sum(usage_records.mapped('hours'))
            if total_hours > 0:
                product = self._get_coworking_product()
                lines.append({
                    'product_id': product.id,
                    'name': f'Coworking Space Usage (Manual Entry)',
                    'quantity': total_hours,
                    'price_unit': 0,  # Usually free or included in subscription
                    'membership_id': membership.id,
                })
                
                # Mark usage records as invoiced
                usage_records.write({'invoiced': True})
        
        return lines
    
    def _get_subscription_product(self, plan):
        """Get or create subscription product"""
        product = self.env['product.product'].search([
            ('default_code', '=', f'SUB_{plan.code}')
        ], limit=1)
        
        if not product:
            product = self.env['product.product'].create({
                'name': f'Subscription - {plan.name}',
                'default_code': f'SUB_{plan.code}',
                'type': 'service',
                'list_price': plan.monthly_price,
                'categ_id': self.env.ref('product.product_category_all').id,
            })
        
        return product
    
    def _get_room_booking_product(self):
        """Get or create room booking product"""
        product = self.env['product.product'].search([
            ('default_code', '=', 'ROOM_BOOKING')
        ], limit=1)
        
        if not product:
            product = self.env['product.product'].create({
                'name': 'Meeting Room Booking',
                'default_code': 'ROOM_BOOKING',
                'type': 'service',
                'uom_id': self.env.ref('uom.product_uom_hour').id,
                'list_price': 1.0,
                'categ_id': self.env.ref('product.product_category_all').id,
            })
        
        return product
    
    def _get_event_product(self):
        """Get or create event product"""
        product = self.env['product.product'].search([
            ('default_code', '=', 'EVENT_PARTICIPATION')
        ], limit=1)
        
        if not product:
            product = self.env['product.product'].create({
                'name': 'Event Participation',
                'default_code': 'EVENT_PARTICIPATION',
                'type': 'service',
                'list_price': 10.0,
                'categ_id': self.env.ref('product.product_category_all').id,
            })
        
        return product
    
    def _get_coworking_product(self):
        """Get or create coworking product"""
        product = self.env['product.product'].search([
            ('default_code', '=', 'COWORKING_USAGE')
        ], limit=1)
        
        if not product:
            product = self.env['product.product'].create({
                'name': 'Coworking Space Usage',
                'default_code': 'COWORKING_USAGE',
                'type': 'service',
                'uom_id': self.env.ref('uom.product_uom_hour').id,
                'list_price': 0.0,
                'categ_id': self.env.ref('product.product_category_all').id,
            })
        
        return product


class AccountMove(models.Model):
    _inherit = 'account.move'
    
    invoice_generator_id = fields.Many2one('coworking.invoice.generator', string='Invoice Generator')
