# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import logging

_logger = logging.getLogger(__name__)


class GenerateMonthlyInvoicesWizard(models.TransientModel):
    _name = 'generate.monthly.invoices.wizard'
    _description = 'Generate Monthly Invoices Wizard'

    name = fields.Char(string='Generation Name', required=True, default=lambda self: f"Monthly Invoices - {datetime.now().strftime('%B %Y')}")
    invoice_date = fields.Date(string='Invoice Date', required=True, default=fields.Date.today)
    period_start = fields.Date(string='Period Start', required=True)
    period_end = fields.Date(string='Period End', required=True)
    
    # Filters
    membership_ids = fields.Many2many('coworking.membership', string='Specific Memberships', 
                                    help="Leave empty to generate for all active memberships")
    plan_ids = fields.Many2many('coworking.membership.plan', string='Specific Plans',
                               help="Leave empty to include all plans")
    
    # Options
    include_subscription_fees = fields.Boolean(string='Include Subscription Fees', default=True)
    include_room_usage = fields.Boolean(string='Include Meeting Room Usage', default=True)
    include_event_fees = fields.Boolean(string='Include Event Fees', default=True)
    include_manual_usage = fields.Boolean(string='Include Manual Usage Entries', default=True)
    
    # Preview
    preview_count = fields.Integer(string='Memberships to Invoice', compute='_compute_preview_count')
    
    @api.model
    def default_get(self, fields_list):
        """Set default period to previous month"""
        res = super().default_get(fields_list)
        
        # Default to previous month
        today = datetime.now()
        first_day_current_month = today.replace(day=1)
        last_day_previous_month = first_day_current_month - timedelta(days=1)
        first_day_previous_month = last_day_previous_month.replace(day=1)
        
        res.update({
            'period_start': first_day_previous_month.date(),
            'period_end': last_day_previous_month.date(),
        })
        
        return res
    
    @api.depends('membership_ids', 'plan_ids')
    def _compute_preview_count(self):
        for wizard in self:
            domain = [('state', '=', 'active')]
            
            if wizard.membership_ids:
                domain.append(('id', 'in', wizard.membership_ids.ids))
            
            if wizard.plan_ids:
                domain.append(('plan_id', 'in', wizard.plan_ids.ids))
            
            wizard.preview_count = self.env['coworking.membership'].search_count(domain)
    
    def action_generate_invoices(self):
        """Generate monthly invoices"""
        self.ensure_one()
        
        # Create invoice generator record
        generator = self.env['coworking.invoice.generator'].create({
            'name': self.name,
            'date_from': self.period_start,
            'date_to': self.period_end,
        })
        
        # Get memberships to invoice
        domain = [('state', '=', 'active')]
        
        if self.membership_ids:
            domain.append(('id', 'in', self.membership_ids.ids))
        
        if self.plan_ids:
            domain.append(('plan_id', 'in', self.plan_ids.ids))
        
        memberships = self.env['coworking.membership'].search(domain)
        
        invoices_created = 0
        errors = []
        
        for membership in memberships:
            try:
                invoice = self._create_membership_invoice(membership, generator)
                if invoice:
                    invoices_created += 1
                    _logger.info(f'Created invoice {invoice.name} for membership {membership.name}')
            except Exception as e:
                error_msg = f'Error creating invoice for {membership.name}: {str(e)}'
                errors.append(error_msg)
                _logger.error(error_msg)
        
        generator.state = 'generated'
        
        # Prepare result message
        message = f'{invoices_created} invoices generated successfully.'
        if errors:
            message += f'\n{len(errors)} errors occurred:\n' + '\n'.join(errors[:5])
            if len(errors) > 5:
                message += f'\n... and {len(errors) - 5} more errors.'
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Invoice Generation Results'),
            'res_model': 'coworking.invoice.generator',
            'res_id': generator.id,
            'view_mode': 'form',
            'target': 'current',
            'context': {
                'default_message': message,
            }
        }
    
    def _create_membership_invoice(self, membership, generator):
        """Create invoice for a specific membership"""
        partner = membership.partner_id
        
        # Check if invoice already exists for this period
        existing_invoice = self.env['account.move'].search([
            ('partner_id', '=', partner.id),
            ('invoice_generator_id', '=', generator.id),
            ('move_type', '=', 'out_invoice'),
        ], limit=1)
        
        if existing_invoice:
            return existing_invoice
        
        # Prepare invoice lines
        invoice_lines = []
        
        # Subscription fee
        if self.include_subscription_fees:
            subscription_line = self._create_subscription_line(membership)
            if subscription_line:
                invoice_lines.append((0, 0, subscription_line))
        
        # Meeting room usage
        if self.include_room_usage:
            room_lines = self._create_room_usage_lines(membership, generator)
            for line in room_lines:
                invoice_lines.append((0, 0, line))
        
        # Event fees
        if self.include_event_fees:
            event_lines = self._create_event_lines(membership, generator)
            for line in event_lines:
                invoice_lines.append((0, 0, line))
        
        # Manual usage entries
        if self.include_manual_usage:
            usage_lines = self._create_manual_usage_lines(membership, generator)
            for line in usage_lines:
                invoice_lines.append((0, 0, line))
        
        # Create invoice only if there are lines
        if invoice_lines:
            invoice_vals = {
                'partner_id': partner.id,
                'move_type': 'out_invoice',
                'invoice_date': self.invoice_date,
                'invoice_generator_id': generator.id,
                'ref': f'Monthly Invoice - {membership.name} - {self.period_start.strftime("%B %Y")}',
                'invoice_line_ids': invoice_lines,
                'narration': f'Monthly invoice for coworking membership and services for period {self.period_start} to {self.period_end}',
            }
            
            invoice = self.env['account.move'].create(invoice_vals)
            return invoice
        
        return False
    
    def _create_subscription_line(self, membership):
        """Create subscription fee line"""
        if membership.plan_id.monthly_price > 0:
            product = self._get_or_create_product('subscription', membership.plan_id)
            return {
                'product_id': product.id,
                'name': f'Monthly Subscription - {membership.plan_id.name}',
                'quantity': 1,
                'price_unit': membership.plan_id.monthly_price,
                'membership_id': membership.id,
                'account_id': product.property_account_income_id.id or product.categ_id.property_account_income_categ_id.id,
            }
        return False
    
    def _create_room_usage_lines(self, membership, generator):
        """Create meeting room usage lines"""
        lines = []
        
        # Get paid bookings for the period
        bookings = self.env['coworking.booking'].search([
            ('membership_id', '=', membership.id),
            ('state', '=', 'completed'),
            ('start_datetime', '>=', self.period_start),
            ('start_datetime', '<=', self.period_end),
            ('total_amount', '>', 0),
            ('invoice_line_ids', '=', False)  # Not yet invoiced
        ])
        
        if bookings:
            total_hours = sum(bookings.mapped('duration'))
            total_amount = sum(bookings.mapped('total_amount'))
            
            if total_hours > 0:
                product = self._get_or_create_product('room_booking')
                line = {
                    'product_id': product.id,
                    'name': f'Meeting Room Usage - {len(bookings)} booking(s)',
                    'quantity': total_hours,
                    'price_unit': total_amount / total_hours,
                    'membership_id': membership.id,
                    'account_id': product.property_account_income_id.id or product.categ_id.property_account_income_categ_id.id,
                }
                lines.append(line)
                
                # Mark bookings as invoiced (will be done after invoice creation)
                bookings.write({'invoice_generator_id': generator.id})
        
        return lines
    
    def _create_event_lines(self, membership, generator):
        """Create event participation lines"""
        lines = []
        
        # Get paid event registrations for the period
        registrations = self.env['coworking.event.registration'].search([
            ('membership_id', '=', membership.id),
            ('state', 'in', ['confirmed', 'attended']),
            ('registration_date', '>=', self.period_start),
            ('registration_date', '<=', self.period_end),
            ('price', '>', 0)
        ])
        
        if registrations:
            total_amount = sum(registrations.mapped('price'))
            if total_amount > 0:
                product = self._get_or_create_product('event_participation')
                line = {
                    'product_id': product.id,
                    'name': f'Event Participation - {len(registrations)} event(s)',
                    'quantity': len(registrations),
                    'price_unit': total_amount / len(registrations),
                    'membership_id': membership.id,
                    'account_id': product.property_account_income_id.id or product.categ_id.property_account_income_categ_id.id,
                }
                lines.append(line)
        
        return lines
    
    def _create_manual_usage_lines(self, membership, generator):
        """Create manual usage entry lines"""
        lines = []
        
        # Get manual usage records for the period
        usage_records = self.env['coworking.usage'].search([
            ('membership_id', '=', membership.id),
            ('date', '>=', self.period_start),
            ('date', '<=', self.period_end),
            ('usage_type', '=', 'coworking'),
            ('invoiced', '=', False),
            ('amount', '>', 0)  # Only billable usage
        ])
        
        if usage_records:
            total_hours = sum(usage_records.mapped('hours'))
            total_amount = sum(usage_records.mapped('amount'))
            
            if total_amount > 0:
                product = self._get_or_create_product('coworking_usage')
                line = {
                    'product_id': product.id,
                    'name': f'Coworking Space Usage - {total_hours:.1f} hours',
                    'quantity': total_hours,
                    'price_unit': total_amount / total_hours if total_hours > 0 else 0,
                    'membership_id': membership.id,
                    'account_id': product.property_account_income_id.id or product.categ_id.property_account_income_categ_id.id,
                }
                lines.append(line)
                
                # Mark usage records as invoiced
                usage_records.write({'invoiced': True})
        
        return lines
    
    def _get_or_create_product(self, product_type, plan=None):
        """Get or create product for billing"""
        if product_type == 'subscription' and plan:
            code = f'SUB_{plan.code}'
            name = f'Subscription - {plan.name}'
            price = plan.monthly_price
        elif product_type == 'room_booking':
            code = 'ROOM_BOOKING'
            name = 'Meeting Room Booking'
            price = 1.0
        elif product_type == 'event_participation':
            code = 'EVENT_PARTICIPATION'
            name = 'Event Participation'
            price = 10.0
        elif product_type == 'coworking_usage':
            code = 'COWORKING_USAGE'
            name = 'Coworking Space Usage'
            price = 0.0
        else:
            raise ValueError(f'Unknown product type: {product_type}')
        
        product = self.env['product.product'].search([('default_code', '=', code)], limit=1)
        
        if not product:
            product = self.env['product.product'].create({
                'name': name,
                'default_code': code,
                'type': 'service',
                'list_price': price,
                'categ_id': self.env.ref('product.product_category_all').id,
                'uom_id': self.env.ref('uom.product_uom_hour').id if product_type in ['room_booking', 'coworking_usage'] else self.env.ref('uom.product_uom_unit').id,
            })
        
        return product
