# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from datetime import datetime, timedelta
import logging

_logger = logging.getLogger(__name__)


class CoworkingMembershipPlan(models.Model):
    _name = 'coworking.membership.plan'
    _description = 'Coworking Membership Plan'
    _order = 'sequence, name'

    name = fields.Char(string='Plan Name', required=True)
    code = fields.Char(string='Plan Code', required=True)
    sequence = fields.Integer(string='Sequence', default=10)
    active = fields.Boolean(string='Active', default=True)
    
    # Pricing
    monthly_price = fields.Float(string='Monthly Price (€)', required=True)
    credit_amount = fields.Float(string='Credit Amount (Hours)', help="For Pay-As-You-Go plans")
    
    # Access Rights
    coworking_access = fields.Selection([
        ('free', 'Free Access'),
        ('paid', 'Paid Access'),
        ('credit', 'Credit-based Access'),
        ('none', 'No Access')
    ], string='Coworking Space Access', required=True, default='free')
    
    meeting_room_access = fields.Selection([
        ('free', 'Free Access'),
        ('paid', 'Paid Access (€1/hour)'),
        ('none', 'No Access')
    ], string='Meeting Room Access', required=True, default='paid')
    
    event_access = fields.Selection([
        ('free', 'Free Access'),
        ('discounted', 'Discounted Access'),
        ('paid', 'Paid Access'),
        ('none', 'No Access')
    ], string='Event Access', required=True, default='free')
    
    # Additional Services
    business_address = fields.Boolean(string='Business Address Registration', default=False)
    
    # Description
    description = fields.Html(string='Description')
    
    # Related fields
    membership_ids = fields.One2many('coworking.membership', 'plan_id', string='Memberships')
    member_count = fields.Integer(string='Active Members', compute='_compute_member_count')
    
    @api.depends('membership_ids.state')
    def _compute_member_count(self):
        for plan in self:
            plan.member_count = len(plan.membership_ids.filtered(lambda m: m.state == 'active'))
    
    @api.constrains('code')
    def _check_unique_code(self):
        for plan in self:
            if self.search_count([('code', '=', plan.code), ('id', '!=', plan.id)]) > 0:
                raise ValidationError(_('Plan code must be unique.'))


class CoworkingMembership(models.Model):
    _name = 'coworking.membership'
    _description = 'Coworking Membership'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'start_date desc'

    name = fields.Char(string='Membership Number', required=True, copy=False, readonly=True, default=lambda self: _('New'))
    partner_id = fields.Many2one('res.partner', string='Member', required=True, tracking=True)
    plan_id = fields.Many2one('coworking.membership.plan', string='Membership Plan', required=True, tracking=True)
    
    # Dates
    start_date = fields.Date(string='Start Date', required=True, default=fields.Date.today, tracking=True)
    end_date = fields.Date(string='End Date', tracking=True)
    
    # State
    state = fields.Selection([
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('suspended', 'Suspended'),
        ('expired', 'Expired'),
        ('cancelled', 'Cancelled')
    ], string='Status', default='draft', tracking=True)
    
    # Credits (for Pay-As-You-Go plans)
    credit_balance = fields.Float(string='Credit Balance (Hours)', default=0.0, tracking=True)
    initial_credit = fields.Float(string='Initial Credit', default=0.0)
    
    # Billing
    subscription_id = fields.Many2one('sale.subscription', string='Subscription')
    auto_renew = fields.Boolean(string='Auto Renew', default=True)
    
    # Usage tracking
    booking_ids = fields.One2many('coworking.booking', 'membership_id', string='Bookings')
    usage_ids = fields.One2many('coworking.usage', 'membership_id', string='Usage Records')
    
    # Computed fields
    total_bookings = fields.Integer(string='Total Bookings', compute='_compute_usage_stats')
    total_hours_used = fields.Float(string='Total Hours Used', compute='_compute_usage_stats')
    
    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code('coworking.membership') or _('New')
        return super(CoworkingMembership, self).create(vals)
    
    @api.depends('booking_ids', 'usage_ids')
    def _compute_usage_stats(self):
        for membership in self:
            membership.total_bookings = len(membership.booking_ids)
            membership.total_hours_used = sum(membership.usage_ids.mapped('hours'))
    
    def action_activate(self):
        """Activate the membership"""
        for membership in self:
            membership.state = 'active'
            if membership.plan_id.code == 'payg' and membership.plan_id.credit_amount > 0:
                membership.credit_balance = membership.plan_id.credit_amount
                membership.initial_credit = membership.plan_id.credit_amount
    
    def action_suspend(self):
        """Suspend the membership"""
        for membership in self:
            membership.state = 'suspended'
    
    def action_cancel(self):
        """Cancel the membership"""
        for membership in self:
            membership.state = 'cancelled'
            membership.end_date = fields.Date.today()
    
    def action_renew(self):
        """Renew the membership"""
        for membership in self:
            if membership.end_date:
                membership.start_date = membership.end_date + timedelta(days=1)
            else:
                membership.start_date = fields.Date.today()
            membership.end_date = False
            membership.state = 'active'
            
            # Reset credits for Pay-As-You-Go plans
            if membership.plan_id.code == 'payg':
                membership.credit_balance = membership.plan_id.credit_amount
    
    def check_credit_balance(self, hours_needed):
        """Check if member has enough credit balance"""
        if self.plan_id.coworking_access == 'credit':
            return self.credit_balance >= hours_needed
        return True
    
    def consume_credit(self, hours):
        """Consume credit hours"""
        if self.plan_id.coworking_access == 'credit':
            if self.credit_balance >= hours:
                self.credit_balance -= hours
                return True
            else:
                raise ValidationError(_('Insufficient credit balance. Available: %.2f hours, Required: %.2f hours') % (self.credit_balance, hours))
        return True
    
    @api.model
    def _cron_check_expired_memberships(self):
        """Cron job to check and update expired memberships"""
        today = fields.Date.today()
        expired_memberships = self.search([
            ('state', '=', 'active'),
            ('end_date', '<', today)
        ])
        expired_memberships.write({'state': 'expired'})
        _logger.info(f'Updated {len(expired_memberships)} expired memberships')
