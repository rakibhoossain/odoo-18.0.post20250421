# -*- coding: utf-8 -*-

from odoo import http, _
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal, pager as portal_pager
from odoo.exceptions import AccessError, MissingError
from datetime import datetime, timedelta


class CoworkingPortal(CustomerPortal):

    def _prepare_home_portal_values(self, counters):
        """Add coworking-related counters to portal home"""
        values = super()._prepare_home_portal_values(counters)
        
        partner = request.env.user.partner_id
        
        if 'booking_count' in counters:
            booking_count = request.env['coworking.booking'].search_count([
                ('partner_id', '=', partner.id)
            ])
            values['booking_count'] = booking_count
        
        if 'event_count' in counters:
            event_count = request.env['coworking.event.registration'].search_count([
                ('partner_id', '=', partner.id)
            ])
            values['event_count'] = event_count
        
        if 'membership_count' in counters:
            membership_count = request.env['coworking.membership'].search_count([
                ('partner_id', '=', partner.id)
            ])
            values['membership_count'] = membership_count
        
        return values

    @http.route(['/my/coworking'], type='http', auth='user', website=True)
    def portal_coworking_home(self, **kwargs):
        """Coworking portal home page"""
        partner = request.env.user.partner_id
        
        # Get active membership
        membership = request.env['coworking.membership'].search([
            ('partner_id', '=', partner.id),
            ('state', '=', 'active')
        ], limit=1)
        
        # Get recent bookings
        recent_bookings = request.env['coworking.booking'].search([
            ('partner_id', '=', partner.id)
        ], limit=5, order='start_datetime desc')
        
        # Get upcoming events
        upcoming_events = request.env['coworking.event.registration'].search([
            ('partner_id', '=', partner.id),
            ('event_id.date_begin', '>', datetime.now()),
            ('state', 'in', ['confirmed', 'draft'])
        ], limit=5, order='event_id.date_begin')
        
        # Get usage statistics
        usage_stats = self._get_usage_statistics(partner, membership)
        
        values = {
            'membership': membership,
            'recent_bookings': recent_bookings,
            'upcoming_events': upcoming_events,
            'usage_stats': usage_stats,
            'page_name': 'coworking_home',
        }
        
        return request.render('coworking_space.portal_coworking_home', values)

    @http.route(['/my/bookings', '/my/bookings/page/<int:page>'], type='http', auth='user', website=True)
    def portal_my_bookings(self, page=1, date_begin=None, date_end=None, sortby=None, **kwargs):
        """My bookings page"""
        values = self._prepare_portal_layout_values()
        partner = request.env.user.partner_id
        
        domain = [('partner_id', '=', partner.id)]
        
        # Date filtering
        if date_begin and date_end:
            domain += [('start_datetime', '>=', date_begin), ('start_datetime', '<=', date_end)]
        
        # Sorting
        searchbar_sortings = {
            'date': {'label': _('Date'), 'order': 'start_datetime desc'},
            'name': {'label': _('Reference'), 'order': 'name'},
            'state': {'label': _('Status'), 'order': 'state'},
        }
        
        if not sortby:
            sortby = 'date'
        order = searchbar_sortings[sortby]['order']
        
        # Count and pager
        booking_count = request.env['coworking.booking'].search_count(domain)
        pager = portal_pager(
            url='/my/bookings',
            url_args={'date_begin': date_begin, 'date_end': date_end, 'sortby': sortby},
            total=booking_count,
            page=page,
            step=self._items_per_page
        )
        
        # Get bookings
        bookings = request.env['coworking.booking'].search(domain, order=order, limit=self._items_per_page, offset=pager['offset'])
        
        values.update({
            'bookings': bookings,
            'page_name': 'booking',
            'pager': pager,
            'default_url': '/my/bookings',
            'searchbar_sortings': searchbar_sortings,
            'sortby': sortby,
        })
        
        return request.render('coworking_space.portal_my_bookings', values)

    @http.route(['/my/booking/<int:booking_id>'], type='http', auth='user', website=True)
    def portal_booking_detail(self, booking_id, access_token=None, **kwargs):
        """Booking detail page"""
        try:
            booking_sudo = self._document_check_access('coworking.booking', booking_id, access_token)
        except (AccessError, MissingError):
            return request.redirect('/my')
        
        values = {
            'booking': booking_sudo,
            'page_name': 'booking',
        }
        
        return request.render('coworking_space.portal_booking_detail', values)

    @http.route(['/my/events', '/my/events/page/<int:page>'], type='http', auth='user', website=True)
    def portal_my_events(self, page=1, **kwargs):
        """My event registrations page"""
        values = self._prepare_portal_layout_values()
        partner = request.env.user.partner_id
        
        domain = [('partner_id', '=', partner.id)]
        
        # Count and pager
        registration_count = request.env['coworking.event.registration'].search_count(domain)
        pager = portal_pager(
            url='/my/events',
            total=registration_count,
            page=page,
            step=self._items_per_page
        )
        
        # Get registrations
        registrations = request.env['coworking.event.registration'].search(
            domain, 
            order='event_id.date_begin desc', 
            limit=self._items_per_page, 
            offset=pager['offset']
        )
        
        values.update({
            'registrations': registrations,
            'page_name': 'event',
            'pager': pager,
            'default_url': '/my/events',
        })
        
        return request.render('coworking_space.portal_my_events', values)

    @http.route(['/my/membership'], type='http', auth='user', website=True)
    def portal_my_membership(self, **kwargs):
        """My membership page"""
        partner = request.env.user.partner_id
        
        # Get all memberships
        memberships = request.env['coworking.membership'].search([
            ('partner_id', '=', partner.id)
        ], order='start_date desc')
        
        # Get active membership
        active_membership = memberships.filtered(lambda m: m.state == 'active')
        
        # Get usage records for current month
        current_month_usage = []
        if active_membership:
            current_month_start = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            current_month_usage = request.env['coworking.usage'].search([
                ('membership_id', '=', active_membership[0].id),
                ('date', '>=', current_month_start.date())
            ], order='date desc')
        
        values = {
            'memberships': memberships,
            'active_membership': active_membership[0] if active_membership else None,
            'current_month_usage': current_month_usage,
            'page_name': 'membership',
        }
        
        return request.render('coworking_space.portal_my_membership', values)

    @http.route(['/my/usage/add'], type='http', auth='user', website=True, methods=['GET', 'POST'])
    def portal_add_usage(self, **kwargs):
        """Add manual usage entry"""
        partner = request.env.user.partner_id
        
        # Get active membership
        membership = request.env['coworking.membership'].search([
            ('partner_id', '=', partner.id),
            ('state', '=', 'active')
        ], limit=1)
        
        if not membership:
            return request.redirect('/my/membership')
        
        if request.httprequest.method == 'POST':
            try:
                hours = float(kwargs.get('hours', 0))
                description = kwargs.get('description', '')
                usage_date = kwargs.get('date', datetime.now().date())
                
                if hours <= 0:
                    raise ValueError('Hours must be positive')
                
                # Check credit balance for Pay-As-You-Go plans
                if membership.plan_id.coworking_access == 'credit':
                    if not membership.check_credit_balance(hours):
                        raise ValueError('Insufficient credit balance')
                    membership.consume_credit(hours)
                
                # Create usage record
                usage_vals = {
                    'membership_id': membership.id,
                    'usage_type': 'coworking',
                    'date': usage_date,
                    'hours': hours,
                    'description': description,
                }
                
                request.env['coworking.usage'].create(usage_vals)
                
                return request.redirect('/my/membership?success=1')
                
            except Exception as e:
                error_message = str(e)
                return request.render('coworking_space.portal_add_usage', {
                    'membership': membership,
                    'error': error_message,
                    'page_name': 'usage',
                })
        
        values = {
            'membership': membership,
            'page_name': 'usage',
        }
        
        return request.render('coworking_space.portal_add_usage', values)

    def _get_usage_statistics(self, partner, membership):
        """Get usage statistics for the partner"""
        stats = {
            'total_bookings': 0,
            'total_events': 0,
            'current_month_hours': 0,
            'credit_balance': 0,
        }
        
        # Total bookings
        stats['total_bookings'] = request.env['coworking.booking'].search_count([
            ('partner_id', '=', partner.id),
            ('state', '=', 'completed')
        ])
        
        # Total events attended
        stats['total_events'] = request.env['coworking.event.registration'].search_count([
            ('partner_id', '=', partner.id),
            ('state', '=', 'attended')
        ])
        
        if membership:
            # Current month usage hours
            current_month_start = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            current_month_usage = request.env['coworking.usage'].search([
                ('membership_id', '=', membership.id),
                ('date', '>=', current_month_start.date())
            ])
            stats['current_month_hours'] = sum(current_month_usage.mapped('hours'))
            
            # Credit balance
            stats['credit_balance'] = membership.credit_balance
        
        return stats

    def _document_check_access(self, model_name, document_id, access_token=None):
        """Check access to document"""
        document = request.env[model_name].browse([document_id])
        document_sudo = document.sudo()
        
        try:
            document.check_access_rights('read')
            document.check_access_rule('read')
        except AccessError:
            if access_token and document_sudo.access_token and document_sudo.access_token == access_token:
                return document_sudo
            else:
                raise
        return document_sudo
