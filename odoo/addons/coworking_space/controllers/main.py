# -*- coding: utf-8 -*-

from odoo import http, _
from odoo.http import request
from odoo.exceptions import ValidationError, UserError
from datetime import datetime, timedelta
import json
import logging

_logger = logging.getLogger(__name__)


class CoworkingSpaceController(http.Controller):

    @http.route('/coworking', type='http', auth='public', website=True)
    def coworking_home(self, **kwargs):
        """Coworking space home page"""
        rooms = request.env['coworking.room'].sudo().search([('active', '=', True)])
        events = request.env['coworking.event'].sudo().search([
            ('state', '=', 'published'),
            ('date_begin', '>', datetime.now())
        ], limit=6, order='date_begin')
        
        plans = request.env['coworking.membership.plan'].sudo().search([('active', '=', True)], order='sequence')
        
        return request.render('coworking_space.coworking_home', {
            'rooms': rooms,
            'events': events,
            'plans': plans,
        })

    @http.route('/coworking/rooms', type='http', auth='public', website=True)
    def room_list(self, **kwargs):
        """List all available rooms"""
        rooms = request.env['coworking.room'].sudo().search([('active', '=', True)], order='sequence')
        return request.render('coworking_space.room_list', {
            'rooms': rooms,
        })

    @http.route('/coworking/room/<int:room_id>', type='http', auth='public', website=True)
    def room_detail(self, room_id, **kwargs):
        """Room detail page"""
        room = request.env['coworking.room'].sudo().browse(room_id)
        if not room.exists() or not room.active:
            return request.not_found()
        
        return request.render('coworking_space.room_detail', {
            'room': room,
        })

    @http.route('/coworking/book/<int:room_id>', type='http', auth='public', website=True)
    def book_room(self, room_id, **kwargs):
        """Room booking page"""
        room = request.env['coworking.room'].sudo().browse(room_id)
        if not room.exists() or not room.active:
            return request.not_found()
        
        # Get user's active membership if logged in
        membership = None
        if request.env.user != request.env.ref('base.public_user'):
            membership = request.env['coworking.membership'].sudo().search([
                ('partner_id', '=', request.env.user.partner_id.id),
                ('state', '=', 'active')
            ], limit=1)
        
        return request.render('coworking_space.room_booking', {
            'room': room,
            'membership': membership,
        })

    @http.route('/coworking/events', type='http', auth='public', website=True)
    def event_list(self, **kwargs):
        """List all published events"""
        events = request.env['coworking.event'].sudo().search([
            ('state', '=', 'published'),
            ('date_begin', '>', datetime.now())
        ], order='date_begin')
        
        return request.render('coworking_space.event_list', {
            'events': events,
        })

    @http.route('/coworking/event/<int:event_id>', type='http', auth='public', website=True)
    def event_detail(self, event_id, **kwargs):
        """Event detail page"""
        event = request.env['coworking.event'].sudo().browse(event_id)
        if not event.exists() or event.state != 'published':
            return request.not_found()
        
        # Get user's active membership if logged in
        membership = None
        if request.env.user != request.env.ref('base.public_user'):
            membership = request.env['coworking.membership'].sudo().search([
                ('partner_id', '=', request.env.user.partner_id.id),
                ('state', '=', 'active')
            ], limit=1)
        
        # Calculate price for current user
        price = event.get_price_for_partner(request.env.user.partner_id.id)
        
        return request.render('coworking_space.event_detail', {
            'event': event,
            'membership': membership,
            'price': price,
        })

    @http.route('/coworking/membership', type='http', auth='public', website=True)
    def membership_plans(self, **kwargs):
        """Membership plans page"""
        plans = request.env['coworking.membership.plan'].sudo().search([('active', '=', True)], order='sequence')
        return request.render('coworking_space.membership_plans', {
            'plans': plans,
        })

    # API endpoints for AJAX calls
    @http.route('/coworking/api/room/availability', type='json', auth='public', methods=['POST'])
    def check_room_availability(self, room_id, start_datetime, end_datetime):
        """Check room availability for given time period"""
        try:
            room = request.env['coworking.room'].sudo().browse(room_id)
            if not room.exists():
                return {'error': 'Room not found'}
            
            start_dt = datetime.fromisoformat(start_datetime.replace('Z', '+00:00'))
            end_dt = datetime.fromisoformat(end_datetime.replace('Z', '+00:00'))
            
            available = room.is_available(start_dt, end_dt)
            
            return {
                'available': available,
                'room_name': room.name,
                'hourly_rate': room.hourly_rate,
            }
        except Exception as e:
            _logger.error(f'Error checking room availability: {e}')
            return {'error': str(e)}

    @http.route('/coworking/api/room/slots', type='json', auth='public', methods=['POST'])
    def get_available_slots(self, room_id, date, duration=1):
        """Get available time slots for a specific date"""
        try:
            room = request.env['coworking.room'].sudo().browse(room_id)
            if not room.exists():
                return {'error': 'Room not found'}
            
            date_obj = datetime.strptime(date, '%Y-%m-%d').date()
            slots = room.get_available_slots(date_obj, duration)
            
            # Convert datetime objects to strings for JSON serialization
            for slot in slots:
                slot['start'] = slot['start'].isoformat()
                slot['end'] = slot['end'].isoformat()
            
            return {'slots': slots}
        except Exception as e:
            _logger.error(f'Error getting available slots: {e}')
            return {'error': str(e)}

    @http.route('/coworking/api/booking/create', type='json', auth='public', methods=['POST'], csrf=False)
    def create_booking(self, **kwargs):
        """Create a new booking"""
        try:
            # Extract booking data
            room_id = kwargs.get('room_id')
            start_datetime = kwargs.get('start_datetime')
            end_datetime = kwargs.get('end_datetime')
            purpose = kwargs.get('purpose', '')
            attendees_count = kwargs.get('attendees_count', 1)
            
            # Validate required fields
            if not all([room_id, start_datetime, end_datetime]):
                return {'error': 'Missing required fields'}
            
            # Convert datetime strings
            start_dt = datetime.fromisoformat(start_datetime.replace('Z', '+00:00'))
            end_dt = datetime.fromisoformat(end_datetime.replace('Z', '+00:00'))
            
            # Get or create partner
            partner = request.env.user.partner_id
            if partner == request.env.ref('base.public_user').partner_id:
                # For public users, we need contact information
                email = kwargs.get('email')
                name = kwargs.get('name')
                phone = kwargs.get('phone')
                
                if not email or not name:
                    return {'error': 'Contact information required for non-members'}
                
                # Find or create partner
                partner = request.env['res.partner'].sudo().search([('email', '=', email)], limit=1)
                if not partner:
                    partner = request.env['res.partner'].sudo().create({
                        'name': name,
                        'email': email,
                        'phone': phone,
                        'is_company': False,
                    })
            
            # Get membership if exists
            membership = request.env['coworking.membership'].sudo().search([
                ('partner_id', '=', partner.id),
                ('state', '=', 'active')
            ], limit=1)
            
            # Create booking
            booking_vals = {
                'room_id': room_id,
                'partner_id': partner.id,
                'membership_id': membership.id if membership else False,
                'start_datetime': start_dt,
                'end_datetime': end_dt,
                'purpose': purpose,
                'attendees_count': attendees_count,
            }
            
            booking = request.env['coworking.booking'].sudo().create(booking_vals)
            
            # Auto-confirm for members, require approval for non-members
            if membership:
                booking.action_confirm()
                message = 'Booking confirmed successfully!'
            else:
                booking.action_confirm()  # Non-members also get auto-confirmed but create CRM opportunity
                message = 'Booking request submitted successfully!'
            
            return {
                'success': True,
                'message': message,
                'booking_id': booking.id,
                'booking_ref': booking.name,
            }
            
        except ValidationError as e:
            return {'error': str(e)}
        except Exception as e:
            _logger.error(f'Error creating booking: {e}')
            return {'error': 'An error occurred while creating the booking'}

    @http.route('/coworking/api/event/register', type='json', auth='user', methods=['POST'], csrf=False)
    def register_for_event(self, event_id, **kwargs):
        """Register for an event"""
        try:
            event = request.env['coworking.event'].sudo().browse(event_id)
            if not event.exists() or event.state != 'published':
                return {'error': 'Event not found or not available for registration'}
            
            partner = request.env.user.partner_id
            
            # Check if already registered
            existing_registration = request.env['coworking.event.registration'].sudo().search([
                ('event_id', '=', event_id),
                ('partner_id', '=', partner.id)
            ], limit=1)
            
            if existing_registration:
                return {'error': 'You are already registered for this event'}
            
            # Get membership
            membership = request.env['coworking.membership'].sudo().search([
                ('partner_id', '=', partner.id),
                ('state', '=', 'active')
            ], limit=1)
            
            # Create registration
            registration_vals = {
                'event_id': event_id,
                'partner_id': partner.id,
                'membership_id': membership.id if membership else False,
            }
            
            registration = request.env['coworking.event.registration'].sudo().create(registration_vals)
            
            # Auto-confirm if free or member
            if registration.is_free:
                registration.action_confirm()
                message = 'Registration confirmed successfully!'
            else:
                message = 'Registration created. Payment required to confirm.'
            
            return {
                'success': True,
                'message': message,
                'registration_id': registration.id,
                'price': registration.price,
            }
            
        except Exception as e:
            _logger.error(f'Error registering for event: {e}')
            return {'error': 'An error occurred during registration'}
