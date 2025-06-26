# -*- coding: utf-8 -*-

from odoo import http, _
from odoo.http import request
from datetime import datetime, timedelta
import json
import logging

_logger = logging.getLogger(__name__)


class CoworkingBookingController(http.Controller):

    @http.route('/coworking/booking/calendar', type='http', auth='public', website=True)
    def booking_calendar(self, **kwargs):
        """Booking calendar view"""
        rooms = request.env['coworking.room'].sudo().search([('active', '=', True)], order='sequence')
        return request.render('coworking_space.booking_calendar', {
            'rooms': rooms,
        })

    @http.route('/coworking/api/calendar/events', type='json', auth='public', methods=['POST'])
    def get_calendar_events(self, start, end, room_ids=None):
        """Get calendar events for booking display"""
        try:
            start_date = datetime.fromisoformat(start.replace('Z', '+00:00'))
            end_date = datetime.fromisoformat(end.replace('Z', '+00:00'))
            
            domain = [
                ('start_datetime', '>=', start_date),
                ('start_datetime', '<=', end_date),
                ('state', 'in', ['confirmed', 'in_progress'])
            ]
            
            if room_ids:
                domain.append(('room_id', 'in', room_ids))
            
            bookings = request.env['coworking.booking'].sudo().search(domain)
            
            events = []
            for booking in bookings:
                events.append({
                    'id': booking.id,
                    'title': f"{booking.room_id.name} - {booking.partner_id.name}",
                    'start': booking.start_datetime.isoformat(),
                    'end': booking.end_datetime.isoformat(),
                    'resourceId': booking.room_id.id,
                    'backgroundColor': self._get_booking_color(booking),
                    'borderColor': self._get_booking_color(booking),
                    'extendedProps': {
                        'booking_id': booking.id,
                        'room_name': booking.room_id.name,
                        'customer_name': booking.partner_id.name,
                        'state': booking.state,
                        'purpose': booking.purpose or '',
                        'attendees': booking.attendees_count,
                    }
                })
            
            return {'events': events}
            
        except Exception as e:
            _logger.error(f'Error getting calendar events: {e}')
            return {'error': str(e)}

    @http.route('/coworking/api/booking/quick', type='json', auth='public', methods=['POST'], csrf=False)
    def quick_booking(self, **kwargs):
        """Quick booking from calendar"""
        try:
            room_id = kwargs.get('room_id')
            start_datetime = kwargs.get('start')
            end_datetime = kwargs.get('end')
            title = kwargs.get('title', 'Quick Booking')
            
            if not all([room_id, start_datetime, end_datetime]):
                return {'error': 'Missing required fields'}
            
            # Convert datetime strings
            start_dt = datetime.fromisoformat(start_datetime.replace('Z', '+00:00'))
            end_dt = datetime.fromisoformat(end_datetime.replace('Z', '+00:00'))
            
            # Check if user is logged in
            if request.env.user == request.env.ref('base.public_user'):
                return {'error': 'Please log in to make a booking'}
            
            partner = request.env.user.partner_id
            
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
                'purpose': title,
                'attendees_count': 1,
            }
            
            booking = request.env['coworking.booking'].sudo().create(booking_vals)
            booking.action_confirm()
            
            return {
                'success': True,
                'booking_id': booking.id,
                'booking_ref': booking.name,
                'message': 'Booking created successfully!'
            }
            
        except Exception as e:
            _logger.error(f'Error creating quick booking: {e}')
            return {'error': str(e)}

    @http.route('/coworking/api/booking/<int:booking_id>/cancel', type='json', auth='user', methods=['POST'])
    def cancel_booking(self, booking_id, **kwargs):
        """Cancel a booking"""
        try:
            booking = request.env['coworking.booking'].browse(booking_id)
            
            # Check if user owns the booking
            if booking.partner_id != request.env.user.partner_id:
                return {'error': 'You can only cancel your own bookings'}
            
            if not booking.can_cancel:
                return {'error': 'This booking cannot be cancelled'}
            
            booking.action_cancel()
            
            return {
                'success': True,
                'message': 'Booking cancelled successfully'
            }
            
        except Exception as e:
            _logger.error(f'Error cancelling booking: {e}')
            return {'error': str(e)}

    @http.route('/coworking/api/booking/<int:booking_id>/reschedule', type='json', auth='user', methods=['POST'])
    def reschedule_booking(self, booking_id, **kwargs):
        """Reschedule a booking"""
        try:
            booking = request.env['coworking.booking'].browse(booking_id)
            
            # Check if user owns the booking
            if booking.partner_id != request.env.user.partner_id:
                return {'error': 'You can only reschedule your own bookings'}
            
            new_start = kwargs.get('new_start')
            new_end = kwargs.get('new_end')
            
            if not new_start or not new_end:
                return {'error': 'New start and end times are required'}
            
            # Convert datetime strings
            start_dt = datetime.fromisoformat(new_start.replace('Z', '+00:00'))
            end_dt = datetime.fromisoformat(new_end.replace('Z', '+00:00'))
            
            # Check room availability for new time
            if not booking.room_id.is_available(start_dt, end_dt):
                return {'error': 'Room is not available for the new time slot'}
            
            # Update booking
            booking.write({
                'start_datetime': start_dt,
                'end_datetime': end_dt,
            })
            
            return {
                'success': True,
                'message': 'Booking rescheduled successfully'
            }
            
        except Exception as e:
            _logger.error(f'Error rescheduling booking: {e}')
            return {'error': str(e)}

    @http.route('/coworking/api/room/<int:room_id>/schedule', type='json', auth='public', methods=['POST'])
    def get_room_schedule(self, room_id, date_from, date_to):
        """Get room schedule for a date range"""
        try:
            room = request.env['coworking.room'].sudo().browse(room_id)
            if not room.exists():
                return {'error': 'Room not found'}
            
            start_date = datetime.fromisoformat(date_from.replace('Z', '+00:00'))
            end_date = datetime.fromisoformat(date_to.replace('Z', '+00:00'))
            
            # Get bookings for the period
            bookings = request.env['coworking.booking'].sudo().search([
                ('room_id', '=', room_id),
                ('start_datetime', '>=', start_date),
                ('start_datetime', '<=', end_date),
                ('state', 'in', ['confirmed', 'in_progress'])
            ], order='start_datetime')
            
            schedule = []
            for booking in bookings:
                schedule.append({
                    'id': booking.id,
                    'start': booking.start_datetime.isoformat(),
                    'end': booking.end_datetime.isoformat(),
                    'customer': booking.partner_id.name,
                    'purpose': booking.purpose or '',
                    'state': booking.state,
                    'attendees': booking.attendees_count,
                })
            
            return {'schedule': schedule}
            
        except Exception as e:
            _logger.error(f'Error getting room schedule: {e}')
            return {'error': str(e)}

    def _get_booking_color(self, booking):
        """Get color for booking based on state and type"""
        color_map = {
            'confirmed': '#28a745',  # Green
            'in_progress': '#007bff',  # Blue
            'completed': '#6c757d',  # Gray
            'cancelled': '#dc3545',  # Red
            'no_show': '#fd7e14',  # Orange
        }
        
        # Different colors for members vs non-members
        if booking.membership_id:
            return color_map.get(booking.state, '#28a745')
        else:
            # Slightly different shades for non-members
            non_member_colors = {
                'confirmed': '#20c997',  # Teal
                'in_progress': '#17a2b8',  # Info blue
                'completed': '#6c757d',
                'cancelled': '#dc3545',
                'no_show': '#fd7e14',
            }
            return non_member_colors.get(booking.state, '#20c997')
