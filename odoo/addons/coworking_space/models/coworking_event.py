# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class CoworkingEvent(models.Model):
    _name = 'coworking.event'
    _description = 'Coworking Event'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date_begin desc'

    name = fields.Char(string='Event Name', required=True, tracking=True)
    description = fields.Html(string='Description')
    
    # Event Details
    date_begin = fields.Datetime(string='Start Date', required=True, tracking=True)
    date_end = fields.Datetime(string='End Date', required=True, tracking=True)
    duration = fields.Float(string='Duration (Hours)', compute='_compute_duration', store=True)
    
    # Location
    room_id = fields.Many2one('coworking.room', string='Room')
    location = fields.Char(string='Location')
    
    # Capacity and Registration
    seats_max = fields.Integer(string='Maximum Attendees', default=0)
    seats_reserved = fields.Integer(string='Reserved Seats', compute='_compute_seats', store=True)
    seats_available = fields.Integer(string='Available Seats', compute='_compute_seats', store=True)
    seats_unconfirmed = fields.Integer(string='Unconfirmed Seats', compute='_compute_seats', store=True)
    
    # Registration Settings
    registration_open = fields.Boolean(string='Registration Open', default=True)
    auto_confirm = fields.Boolean(string='Auto Confirm Registration', default=True)
    
    # Pricing
    is_free_for_members = fields.Boolean(string='Free for Members', default=True)
    member_price = fields.Float(string='Member Price (€)', default=0.0)
    non_member_price = fields.Float(string='Non-Member Price (€)', default=10.0)
    
    # Event Type
    event_type = fields.Selection([
        ('workshop', 'Workshop'),
        ('seminar', 'Seminar'),
        ('networking', 'Networking'),
        ('training', 'Training'),
        ('meeting', 'Meeting'),
        ('social', 'Social Event'),
        ('other', 'Other')
    ], string='Event Type', default='workshop')
    
    # State
    state = fields.Selection([
        ('draft', 'Draft'),
        ('published', 'Published'),
        ('ongoing', 'Ongoing'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled')
    ], string='Status', default='draft', tracking=True)
    
    # Organizer
    organizer_id = fields.Many2one('res.partner', string='Organizer', default=lambda self: self.env.company.partner_id)
    user_id = fields.Many2one('res.users', string='Responsible User', default=lambda self: self.env.user)
    
    # Registration and Attendees
    registration_ids = fields.One2many('coworking.event.registration', 'event_id', string='Registrations')
    attendee_count = fields.Integer(string='Confirmed Attendees', compute='_compute_attendee_count')
    
    # Images and Media
    image = fields.Image(string='Event Image')
    
    # Website
    website_published = fields.Boolean(string='Published on Website', default=False)
    website_url = fields.Char(string='Website URL', compute='_compute_website_url')
    
    @api.depends('date_begin', 'date_end')
    def _compute_duration(self):
        for event in self:
            if event.date_begin and event.date_end:
                delta = event.date_end - event.date_begin
                event.duration = delta.total_seconds() / 3600.0
            else:
                event.duration = 0.0
    
    @api.depends('registration_ids.state')
    def _compute_seats(self):
        for event in self:
            registrations = event.registration_ids
            event.seats_reserved = len(registrations.filtered(lambda r: r.state == 'confirmed'))
            event.seats_unconfirmed = len(registrations.filtered(lambda r: r.state == 'draft'))
            if event.seats_max > 0:
                event.seats_available = event.seats_max - event.seats_reserved
            else:
                event.seats_available = 0
    
    @api.depends('registration_ids.state')
    def _compute_attendee_count(self):
        for event in self:
            event.attendee_count = len(event.registration_ids.filtered(lambda r: r.state == 'confirmed'))
    
    def _compute_website_url(self):
        for event in self:
            event.website_url = f'/event/{event.id}'
    
    @api.constrains('date_begin', 'date_end')
    def _check_dates(self):
        for event in self:
            if event.date_begin >= event.date_end:
                raise ValidationError(_('End date must be after start date.'))
    
    @api.constrains('seats_max')
    def _check_seats_max(self):
        for event in self:
            if event.seats_max < 0:
                raise ValidationError(_('Maximum attendees cannot be negative.'))
    
    def action_publish(self):
        """Publish the event"""
        for event in self:
            event.state = 'published'
            event.website_published = True
    
    def action_start(self):
        """Start the event"""
        for event in self:
            event.state = 'ongoing'
    
    def action_complete(self):
        """Complete the event"""
        for event in self:
            event.state = 'completed'
            # Auto-confirm all draft registrations
            draft_registrations = event.registration_ids.filtered(lambda r: r.state == 'draft')
            draft_registrations.action_confirm()
    
    def action_cancel(self):
        """Cancel the event"""
        for event in self:
            event.state = 'cancelled'
            # Cancel all registrations
            event.registration_ids.action_cancel()
    
    def get_price_for_partner(self, partner_id):
        """Get event price for a specific partner"""
        partner = self.env['res.partner'].browse(partner_id)
        membership = self.env['coworking.membership'].search([
            ('partner_id', '=', partner_id),
            ('state', '=', 'active')
        ], limit=1)
        
        if membership:
            if self.is_free_for_members or membership.plan_id.event_access == 'free':
                return 0.0
            elif membership.plan_id.event_access == 'discounted':
                return self.member_price
        
        return self.non_member_price


class CoworkingEventRegistration(models.Model):
    _name = 'coworking.event.registration'
    _description = 'Event Registration'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'partner_name'

    event_id = fields.Many2one('coworking.event', string='Event', required=True, ondelete='cascade')
    partner_id = fields.Many2one('res.partner', string='Attendee', required=True)
    partner_name = fields.Char(string='Attendee Name', related='partner_id.name', store=True)
    partner_email = fields.Char(string='Email', related='partner_id.email', store=True)
    partner_phone = fields.Char(string='Phone', related='partner_id.phone', store=True)
    
    # Registration Details
    registration_date = fields.Datetime(string='Registration Date', default=fields.Datetime.now)
    membership_id = fields.Many2one('coworking.membership', string='Membership')
    
    # State
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('attended', 'Attended'),
        ('cancelled', 'Cancelled')
    ], string='Status', default='draft', tracking=True)
    
    # Pricing
    price = fields.Float(string='Price (€)', compute='_compute_price', store=True)
    is_free = fields.Boolean(string='Free Registration', compute='_compute_is_free', store=True)
    
    # Payment
    payment_status = fields.Selection([
        ('pending', 'Pending'),
        ('paid', 'Paid'),
        ('refunded', 'Refunded')
    ], string='Payment Status', default='pending')
    
    # Additional Info
    notes = fields.Text(string='Notes')
    
    @api.depends('event_id', 'membership_id')
    def _compute_price(self):
        for registration in self:
            if registration.event_id:
                registration.price = registration.event_id.get_price_for_partner(registration.partner_id.id)
            else:
                registration.price = 0.0
    
    @api.depends('price')
    def _compute_is_free(self):
        for registration in self:
            registration.is_free = registration.price == 0.0
    
    @api.model
    def create(self, vals):
        # Auto-set membership if partner has active membership
        if vals.get('partner_id') and not vals.get('membership_id'):
            membership = self.env['coworking.membership'].search([
                ('partner_id', '=', vals['partner_id']),
                ('state', '=', 'active')
            ], limit=1)
            if membership:
                vals['membership_id'] = membership.id
        
        return super(CoworkingEventRegistration, self).create(vals)
    
    def action_confirm(self):
        """Confirm the registration"""
        for registration in self:
            # Check if event has available seats
            if registration.event_id.seats_max > 0 and registration.event_id.seats_available <= 0:
                raise ValidationError(_('No available seats for this event.'))
            
            registration.state = 'confirmed'
            
            # Send confirmation email
            registration._send_confirmation_email()
    
    def action_attend(self):
        """Mark as attended"""
        for registration in self:
            registration.state = 'attended'
    
    def action_cancel(self):
        """Cancel the registration"""
        for registration in self:
            registration.state = 'cancelled'
            
            # Process refund if applicable
            if registration.payment_status == 'paid':
                registration.payment_status = 'refunded'
    
    def _send_confirmation_email(self):
        """Send confirmation email to attendee"""
        template = self.env.ref('coworking_space.email_template_event_registration_confirmation', raise_if_not_found=False)
        if template:
            template.send_mail(self.id, force_send=True)
