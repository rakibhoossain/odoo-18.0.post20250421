# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class CoworkingRoom(models.Model):
    _name = 'coworking.room'
    _description = 'Coworking Room'
    _order = 'sequence, name'

    name = fields.Char(string='Room Name', required=True)
    code = fields.Char(string='Room Code', required=True)
    sequence = fields.Integer(string='Sequence', default=10)
    active = fields.Boolean(string='Active', default=True)
    
    # Room Details
    capacity = fields.Integer(string='Capacity (persons)', required=True, default=1)
    area = fields.Float(string='Area (m²)')
    floor = fields.Char(string='Floor')
    location = fields.Char(string='Location/Building')
    
    # Pricing
    hourly_rate = fields.Float(string='Hourly Rate (€)', default=1.0, required=True)
    daily_rate = fields.Float(string='Daily Rate (€)')
    
    # Equipment and Amenities
    equipment_ids = fields.Many2many('coworking.equipment', string='Equipment')
    amenity_ids = fields.Many2many('coworking.amenity', string='Amenities')
    
    # Availability
    available_from = fields.Float(string='Available From (Hour)', default=8.0)
    available_to = fields.Float(string='Available To (Hour)', default=18.0)
    available_days = fields.Selection([
        ('weekdays', 'Weekdays Only'),
        ('all', 'All Days'),
        ('custom', 'Custom Schedule')
    ], string='Available Days', default='weekdays')
    
    # Custom availability
    monday = fields.Boolean(string='Monday', default=True)
    tuesday = fields.Boolean(string='Tuesday', default=True)
    wednesday = fields.Boolean(string='Wednesday', default=True)
    thursday = fields.Boolean(string='Thursday', default=True)
    friday = fields.Boolean(string='Friday', default=True)
    saturday = fields.Boolean(string='Saturday', default=False)
    sunday = fields.Boolean(string='Sunday', default=False)
    
    # Description and Images
    description = fields.Html(string='Description')
    image = fields.Image(string='Room Image')
    image_ids = fields.One2many('coworking.room.image', 'room_id', string='Additional Images')
    
    # Bookings
    booking_ids = fields.One2many('coworking.booking', 'room_id', string='Bookings')
    
    # Statistics
    total_bookings = fields.Integer(string='Total Bookings', compute='_compute_booking_stats')
    total_revenue = fields.Float(string='Total Revenue', compute='_compute_booking_stats')
    utilization_rate = fields.Float(string='Utilization Rate (%)', compute='_compute_utilization_rate')
    
    @api.depends('booking_ids')
    def _compute_booking_stats(self):
        for room in self:
            confirmed_bookings = room.booking_ids.filtered(lambda b: b.state == 'confirmed')
            room.total_bookings = len(confirmed_bookings)
            room.total_revenue = sum(confirmed_bookings.mapped('total_amount'))
    
    @api.depends('booking_ids')
    def _compute_utilization_rate(self):
        # This is a simplified calculation - in reality, you'd want to calculate based on available hours
        for room in self:
            # Calculate utilization rate based on last 30 days
            from datetime import datetime, timedelta
            thirty_days_ago = datetime.now() - timedelta(days=30)
            recent_bookings = room.booking_ids.filtered(
                lambda b: b.start_datetime >= thirty_days_ago and b.state == 'confirmed'
            )
            total_booked_hours = sum(recent_bookings.mapped('duration'))
            # Assuming 10 hours per day * 30 days = 300 available hours
            available_hours = 300
            room.utilization_rate = (total_booked_hours / available_hours * 100) if available_hours > 0 else 0
    
    @api.constrains('code')
    def _check_unique_code(self):
        for room in self:
            if self.search_count([('code', '=', room.code), ('id', '!=', room.id)]) > 0:
                raise ValidationError(_('Room code must be unique.'))
    
    @api.constrains('available_from', 'available_to')
    def _check_availability_hours(self):
        for room in self:
            if room.available_from >= room.available_to:
                raise ValidationError(_('Available from time must be before available to time.'))
    
    def is_available(self, start_datetime, end_datetime):
        """Check if room is available for the given time period"""
        # Check if room is active
        if not self.active:
            return False
        
        # Check day availability
        weekday = start_datetime.weekday()  # 0=Monday, 6=Sunday
        day_fields = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
        
        if self.available_days == 'weekdays' and weekday >= 5:  # Saturday or Sunday
            return False
        elif self.available_days == 'custom' and not getattr(self, day_fields[weekday]):
            return False
        
        # Check time availability
        start_hour = start_datetime.hour + start_datetime.minute / 60.0
        end_hour = end_datetime.hour + end_datetime.minute / 60.0
        
        if start_hour < self.available_from or end_hour > self.available_to:
            return False
        
        # Check for conflicting bookings
        conflicting_bookings = self.env['coworking.booking'].search([
            ('room_id', '=', self.id),
            ('state', 'in', ['confirmed', 'in_progress']),
            ('start_datetime', '<', end_datetime),
            ('end_datetime', '>', start_datetime)
        ])
        
        return len(conflicting_bookings) == 0
    
    def get_available_slots(self, date, duration_hours=1):
        """Get available time slots for a specific date"""
        from datetime import datetime, timedelta
        
        slots = []
        start_time = datetime.combine(date, datetime.min.time().replace(hour=int(self.available_from)))
        end_time = datetime.combine(date, datetime.min.time().replace(hour=int(self.available_to)))
        
        current_time = start_time
        while current_time + timedelta(hours=duration_hours) <= end_time:
            slot_end = current_time + timedelta(hours=duration_hours)
            if self.is_available(current_time, slot_end):
                slots.append({
                    'start': current_time,
                    'end': slot_end,
                    'available': True
                })
            current_time += timedelta(hours=0.5)  # 30-minute intervals
        
        return slots


class CoworkingEquipment(models.Model):
    _name = 'coworking.equipment'
    _description = 'Coworking Equipment'
    
    name = fields.Char(string='Equipment Name', required=True)
    description = fields.Text(string='Description')
    icon = fields.Char(string='Icon Class')


class CoworkingAmenity(models.Model):
    _name = 'coworking.amenity'
    _description = 'Coworking Amenity'
    
    name = fields.Char(string='Amenity Name', required=True)
    description = fields.Text(string='Description')
    icon = fields.Char(string='Icon Class')


class CoworkingRoomImage(models.Model):
    _name = 'coworking.room.image'
    _description = 'Coworking Room Image'
    
    room_id = fields.Many2one('coworking.room', string='Room', required=True, ondelete='cascade')
    image = fields.Image(string='Image', required=True)
    name = fields.Char(string='Image Name')
    sequence = fields.Integer(string='Sequence', default=10)
