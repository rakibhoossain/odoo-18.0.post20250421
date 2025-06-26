# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from datetime import datetime, timedelta
import logging

_logger = logging.getLogger(__name__)


class CoworkingBooking(models.Model):
    _name = 'coworking.booking'
    _description = 'Coworking Room Booking'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'start_datetime desc'

    name = fields.Char(string='Booking Reference', required=True, copy=False, readonly=True, default=lambda self: _('New'))
    
    # Booking Details
    room_id = fields.Many2one('coworking.room', string='Room', required=True, tracking=True)
    partner_id = fields.Many2one('res.partner', string='Customer', required=True, tracking=True)
    membership_id = fields.Many2one('coworking.membership', string='Membership', tracking=True)
    
    # Date and Time
    start_datetime = fields.Datetime(string='Start Date & Time', required=True, tracking=True)
    end_datetime = fields.Datetime(string='End Date & Time', required=True, tracking=True)
    duration = fields.Float(string='Duration (Hours)', compute='_compute_duration', store=True)
    
    # Booking Type
    booking_type = fields.Selection([
        ('member', 'Member Booking'),
        ('non_member', 'Non-Member Booking')
    ], string='Booking Type', compute='_compute_booking_type', store=True)
    
    # State
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
        ('no_show', 'No Show')
    ], string='Status', default='draft', tracking=True)
    
    # Pricing
    hourly_rate = fields.Float(string='Hourly Rate (€)', related='room_id.hourly_rate', store=True)
    total_amount = fields.Float(string='Total Amount (€)', compute='_compute_total_amount', store=True)
    is_free = fields.Boolean(string='Free Booking', compute='_compute_is_free', store=True)
    
    # Payment
    payment_status = fields.Selection([
        ('pending', 'Pending'),
        ('paid', 'Paid'),
        ('refunded', 'Refunded')
    ], string='Payment Status', default='pending', tracking=True)
    
    # Additional Information
    purpose = fields.Text(string='Purpose/Notes')
    attendees_count = fields.Integer(string='Number of Attendees', default=1)
    
    # Related Records
    sale_order_id = fields.Many2one('sale.order', string='Sale Order')
    crm_lead_id = fields.Many2one('crm.lead', string='CRM Opportunity')
    invoice_line_ids = fields.One2many('account.move.line', 'booking_id', string='Invoice Lines')
    
    # Computed Fields
    is_past_due = fields.Boolean(string='Past Due', compute='_compute_is_past_due')
    can_cancel = fields.Boolean(string='Can Cancel', compute='_compute_can_cancel')
    
    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code('coworking.booking') or _('New')
        return super(CoworkingBooking, self).create(vals)
    
    @api.depends('start_datetime', 'end_datetime')
    def _compute_duration(self):
        for booking in self:
            if booking.start_datetime and booking.end_datetime:
                delta = booking.end_datetime - booking.start_datetime
                booking.duration = delta.total_seconds() / 3600.0  # Convert to hours
            else:
                booking.duration = 0.0
    
    @api.depends('membership_id')
    def _compute_booking_type(self):
        for booking in self:
            booking.booking_type = 'member' if booking.membership_id else 'non_member'
    
    @api.depends('duration', 'hourly_rate', 'is_free')
    def _compute_total_amount(self):
        for booking in self:
            if booking.is_free:
                booking.total_amount = 0.0
            else:
                booking.total_amount = booking.duration * booking.hourly_rate
    
    @api.depends('membership_id', 'membership_id.plan_id.meeting_room_access')
    def _compute_is_free(self):
        for booking in self:
            if booking.membership_id and booking.membership_id.plan_id.meeting_room_access == 'free':
                booking.is_free = True
            else:
                booking.is_free = False
    
    @api.depends('end_datetime')
    def _compute_is_past_due(self):
        now = datetime.now()
        for booking in self:
            booking.is_past_due = booking.end_datetime and booking.end_datetime < now
    
    @api.depends('state', 'start_datetime')
    def _compute_can_cancel(self):
        for booking in self:
            # Can cancel if not completed and start time is more than 2 hours away
            if booking.state in ['completed', 'cancelled']:
                booking.can_cancel = False
            elif booking.start_datetime:
                time_until_start = booking.start_datetime - datetime.now()
                booking.can_cancel = time_until_start.total_seconds() > 7200  # 2 hours
            else:
                booking.can_cancel = True
    
    @api.constrains('start_datetime', 'end_datetime')
    def _check_datetime_validity(self):
        for booking in self:
            if booking.start_datetime >= booking.end_datetime:
                raise ValidationError(_('End date must be after start date.'))
            
            if booking.start_datetime < datetime.now() - timedelta(hours=1):
                raise ValidationError(_('Cannot create bookings in the past.'))
    
    @api.constrains('attendees_count', 'room_id')
    def _check_room_capacity(self):
        for booking in self:
            if booking.attendees_count > booking.room_id.capacity:
                raise ValidationError(_('Number of attendees (%d) exceeds room capacity (%d).') % 
                                    (booking.attendees_count, booking.room_id.capacity))
    
    def action_confirm(self):
        """Confirm the booking"""
        for booking in self:
            # Check room availability
            if not booking.room_id.is_available(booking.start_datetime, booking.end_datetime):
                raise UserError(_('Room is not available for the selected time period.'))
            
            booking.state = 'confirmed'
            
            # Create CRM opportunity for non-members
            if booking.booking_type == 'non_member':
                booking._create_crm_opportunity()
            
            # Create sale order if payment is required
            if not booking.is_free:
                booking._create_sale_order()
    
    def action_start(self):
        """Start the booking (mark as in progress)"""
        for booking in self:
            if booking.state == 'confirmed':
                booking.state = 'in_progress'
    
    def action_complete(self):
        """Complete the booking"""
        for booking in self:
            if booking.state in ['confirmed', 'in_progress']:
                booking.state = 'completed'
                # Create usage record for billing
                booking._create_usage_record()
    
    def action_cancel(self):
        """Cancel the booking"""
        for booking in self:
            if not booking.can_cancel:
                raise UserError(_('This booking cannot be cancelled.'))
            
            booking.state = 'cancelled'
            
            # Handle refunds if applicable
            if booking.payment_status == 'paid':
                booking._process_refund()
    
    def action_no_show(self):
        """Mark booking as no show"""
        for booking in self:
            booking.state = 'no_show'
    
    def _create_crm_opportunity(self):
        """Create CRM opportunity for non-member bookings"""
        if self.booking_type == 'non_member' and not self.crm_lead_id:
            lead_vals = {
                'name': f'Meeting Room Booking (Non-Member) - {self.partner_id.name}',
                'partner_id': self.partner_id.id,
                'email_from': self.partner_id.email,
                'phone': self.partner_id.phone,
                'description': f'Meeting room booking for {self.room_id.name} on {self.start_datetime}',
                'stage_id': self.env.ref('crm.stage_lead1').id,
                'team_id': self.env['crm.team'].search([], limit=1).id,
                'user_id': self.env.user.id,
            }
            lead = self.env['crm.lead'].create(lead_vals)
            self.crm_lead_id = lead.id
            _logger.info(f'Created CRM opportunity {lead.id} for booking {self.name}')
    
    def _create_sale_order(self):
        """Create sale order for paid bookings"""
        if not self.is_free and not self.sale_order_id:
            # Get or create product for room booking
            product = self._get_booking_product()
            
            order_vals = {
                'partner_id': self.partner_id.id,
                'order_line': [(0, 0, {
                    'product_id': product.id,
                    'name': f'Room Booking: {self.room_id.name}',
                    'product_uom_qty': self.duration,
                    'price_unit': self.hourly_rate,
                    'booking_id': self.id,
                })]
            }
            order = self.env['sale.order'].create(order_vals)
            self.sale_order_id = order.id
    
    def _get_booking_product(self):
        """Get or create product for room booking"""
        product = self.env['product.product'].search([
            ('default_code', '=', f'ROOM_{self.room_id.code}')
        ], limit=1)
        
        if not product:
            product = self.env['product.product'].create({
                'name': f'Room Booking - {self.room_id.name}',
                'default_code': f'ROOM_{self.room_id.code}',
                'type': 'service',
                'uom_id': self.env.ref('uom.product_uom_hour').id,
                'uom_po_id': self.env.ref('uom.product_uom_hour').id,
                'list_price': self.room_id.hourly_rate,
                'categ_id': self.env.ref('product.product_category_all').id,
            })
        
        return product
    
    def _create_usage_record(self):
        """Create usage record for billing purposes"""
        if self.membership_id:
            usage_vals = {
                'membership_id': self.membership_id.id,
                'booking_id': self.id,
                'usage_type': 'meeting_room',
                'date': self.start_datetime.date(),
                'hours': self.duration,
                'amount': self.total_amount,
                'description': f'Meeting room booking: {self.room_id.name}',
            }
            self.env['coworking.usage'].create(usage_vals)
    
    def _process_refund(self):
        """Process refund for cancelled bookings"""
        # This would integrate with payment providers
        # For now, just mark as refunded
        self.payment_status = 'refunded'
    
    @api.model
    def _cron_auto_complete_bookings(self):
        """Cron job to auto-complete past bookings"""
        past_bookings = self.search([
            ('state', '=', 'in_progress'),
            ('end_datetime', '<', datetime.now())
        ])
        past_bookings.action_complete()
        _logger.info(f'Auto-completed {len(past_bookings)} past bookings')
