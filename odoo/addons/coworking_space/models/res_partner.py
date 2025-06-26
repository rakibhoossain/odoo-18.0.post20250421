# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class ResPartner(models.Model):
    _inherit = 'res.partner'

    # Coworking-related fields
    is_coworking_member = fields.Boolean(string='Is Coworking Member', compute='_compute_is_coworking_member', store=True)
    membership_ids = fields.One2many('coworking.membership', 'partner_id', string='Memberships')
    active_membership_id = fields.Many2one('coworking.membership', string='Active Membership', compute='_compute_active_membership', store=True)
    
    # Booking and usage
    booking_ids = fields.One2many('coworking.booking', 'partner_id', string='Room Bookings')
    event_registration_ids = fields.One2many('coworking.event.registration', 'partner_id', string='Event Registrations')
    
    # Statistics
    total_bookings = fields.Integer(string='Total Bookings', compute='_compute_coworking_stats')
    total_events_attended = fields.Integer(string='Total Events Attended', compute='_compute_coworking_stats')
    member_since = fields.Date(string='Member Since', compute='_compute_member_since')
    
    @api.depends('membership_ids.state')
    def _compute_is_coworking_member(self):
        for partner in self:
            partner.is_coworking_member = bool(partner.membership_ids.filtered(lambda m: m.state == 'active'))
    
    @api.depends('membership_ids.state')
    def _compute_active_membership(self):
        for partner in self:
            active_membership = partner.membership_ids.filtered(lambda m: m.state == 'active')
            partner.active_membership_id = active_membership[0] if active_membership else False
    
    @api.depends('booking_ids', 'event_registration_ids')
    def _compute_coworking_stats(self):
        for partner in self:
            partner.total_bookings = len(partner.booking_ids.filtered(lambda b: b.state == 'completed'))
            partner.total_events_attended = len(partner.event_registration_ids.filtered(lambda r: r.state == 'attended'))
    
    @api.depends('membership_ids.start_date')
    def _compute_member_since(self):
        for partner in self:
            if partner.membership_ids:
                partner.member_since = min(partner.membership_ids.mapped('start_date'))
            else:
                partner.member_since = False
    
    def action_create_membership(self):
        """Open wizard to create new membership"""
        return {
            'type': 'ir.actions.act_window',
            'name': _('Create Membership'),
            'res_model': 'coworking.membership',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_partner_id': self.id,
            }
        }
    
    def action_view_bookings(self):
        """View partner's bookings"""
        return {
            'type': 'ir.actions.act_window',
            'name': _('Room Bookings'),
            'res_model': 'coworking.booking',
            'view_mode': 'tree,form',
            'domain': [('partner_id', '=', self.id)],
            'context': {
                'default_partner_id': self.id,
            }
        }
    
    def action_view_events(self):
        """View partner's event registrations"""
        return {
            'type': 'ir.actions.act_window',
            'name': _('Event Registrations'),
            'res_model': 'coworking.event.registration',
            'view_mode': 'tree,form',
            'domain': [('partner_id', '=', self.id)],
            'context': {
                'default_partner_id': self.id,
            }
        }
    
    def get_membership_plan_access(self, access_type):
        """Get membership plan access level for specific type"""
        if self.active_membership_id:
            if access_type == 'coworking':
                return self.active_membership_id.plan_id.coworking_access
            elif access_type == 'meeting_room':
                return self.active_membership_id.plan_id.meeting_room_access
            elif access_type == 'event':
                return self.active_membership_id.plan_id.event_access
        return 'none'
    
    def has_free_access(self, access_type):
        """Check if partner has free access to specific service"""
        access_level = self.get_membership_plan_access(access_type)
        return access_level == 'free'
    
    def get_credit_balance(self):
        """Get current credit balance for Pay-As-You-Go members"""
        if self.active_membership_id:
            return self.active_membership_id.credit_balance
        return 0.0
