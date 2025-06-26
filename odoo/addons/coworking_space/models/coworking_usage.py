# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class CoworkingUsage(models.Model):
    _name = 'coworking.usage'
    _description = 'Coworking Usage Record'
    _order = 'date desc, create_date desc'

    name = fields.Char(string='Usage Reference', compute='_compute_name', store=True)
    membership_id = fields.Many2one('coworking.membership', string='Membership', required=True, ondelete='cascade')
    partner_id = fields.Many2one('res.partner', string='Member', related='membership_id.partner_id', store=True)
    
    # Usage Details
    usage_type = fields.Selection([
        ('coworking', 'Coworking Space'),
        ('meeting_room', 'Meeting Room'),
        ('event', 'Event'),
        ('other', 'Other')
    ], string='Usage Type', required=True)
    
    date = fields.Date(string='Date', required=True, default=fields.Date.today)
    hours = fields.Float(string='Hours Used', required=True)
    amount = fields.Float(string='Amount (€)', default=0.0)
    
    # Related Records
    booking_id = fields.Many2one('coworking.booking', string='Related Booking')
    event_registration_id = fields.Many2one('coworking.event.registration', string='Related Event Registration')
    
    # Description
    description = fields.Text(string='Description')
    
    # Billing
    invoiced = fields.Boolean(string='Invoiced', default=False)
    invoice_line_id = fields.Many2one('account.move.line', string='Invoice Line')
    
    @api.depends('usage_type', 'date', 'hours')
    def _compute_name(self):
        for usage in self:
            usage.name = f"{usage.usage_type.title()} - {usage.date} ({usage.hours}h)"
    
    @api.constrains('hours')
    def _check_hours(self):
        for usage in self:
            if usage.hours <= 0:
                raise ValidationError(_('Hours must be positive.'))
    
    @api.constrains('amount')
    def _check_amount(self):
        for usage in self:
            if usage.amount < 0:
                raise ValidationError(_('Amount cannot be negative.'))
    
    def action_create_invoice_line(self):
        """Create invoice line for this usage"""
        for usage in self:
            if usage.invoiced:
                continue
            
            # This will be called during monthly invoice generation
            # Implementation depends on the invoice generation process
            pass


class CoworkingUsageWizard(models.TransientModel):
    _name = 'coworking.usage.wizard'
    _description = 'Manual Usage Entry Wizard'

    membership_id = fields.Many2one('coworking.membership', string='Membership', required=True)
    usage_type = fields.Selection([
        ('coworking', 'Coworking Space'),
        ('other', 'Other')
    ], string='Usage Type', required=True, default='coworking')
    
    date = fields.Date(string='Date', required=True, default=fields.Date.today)
    hours = fields.Float(string='Hours', required=True)
    description = fields.Text(string='Description')
    
    def action_create_usage(self):
        """Create usage record"""
        for wizard in self:
            # Check if member has enough credit (for Pay-As-You-Go plans)
            if wizard.membership_id.plan_id.coworking_access == 'credit':
                if not wizard.membership_id.check_credit_balance(wizard.hours):
                    raise ValidationError(_('Insufficient credit balance.'))
                wizard.membership_id.consume_credit(wizard.hours)
            
            # Calculate amount based on plan
            amount = 0.0
            if wizard.membership_id.plan_id.coworking_access == 'paid':
                # For paid access, calculate based on hourly rate
                amount = wizard.hours * 1.0  # €1 per hour default
            
            usage_vals = {
                'membership_id': wizard.membership_id.id,
                'usage_type': wizard.usage_type,
                'date': wizard.date,
                'hours': wizard.hours,
                'amount': amount,
                'description': wizard.description,
            }
            
            usage = self.env['coworking.usage'].create(usage_vals)
            
            return {
                'type': 'ir.actions.act_window',
                'name': _('Usage Record Created'),
                'res_model': 'coworking.usage',
                'res_id': usage.id,
                'view_mode': 'form',
                'target': 'current',
            }
