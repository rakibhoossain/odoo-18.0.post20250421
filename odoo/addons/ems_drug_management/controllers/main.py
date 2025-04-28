from odoo import http
from odoo.exceptions import AccessError
from odoo.http import request


class EMSPortal(http.Controller):

    @http.route('/', type='http', auth="public", website=True)
    def portal_selection(self, **kw):
        # If user is logged in, redirect to their portal
        if request.session.uid:
            if request.env.user.has_group('ems_drug_management.group_drug_superadmin'):
                return request.redirect('/ems/admin')
            if request.env.user.has_group('ems_drug_management.group_drug_manager'):
                return request.redirect('/ems/manager')
            if request.env.user.has_group('ems_drug_management.group_drug_paramedic'):
                return request.redirect('/ems/paramedic')
        return request.render('ems_drug_management.ems_portal_selection_page', {})

    @http.route('/ems', type='http', auth="public", website=True)
    def base_route_redirect(self, **kw):
        return request.redirect('/')

    @http.route('/ems/paramedic', type='http', auth="user", website=True)
    def paramedic_dashboard(self, **kw):
        if not request.env.user.has_group('ems_drug_management.group_drug_paramedic'):
            request.session[
                'warning_message'] = "You don't have permission to access the Paramedic Portal"
            return request.redirect('/')
        return request.render('ems_drug_management.paramedic_dashboard')

    @http.route('/ems/manager', type='http', auth="user", website=True)
    def manager_dashboard(self, **kw):
        if not request.env.user.has_group('ems_drug_management.group_drug_manager'):
            request.session[
                'warning_message'] = "You don't have permission to access the Manager Portal"
            return request.redirect('/')
        return request.render('ems_drug_management.manager_dashboard')

    @http.route('/ems/admin', type='http', auth="user", website=True)
    def admin_dashboard(self, **kw):
        if not request.env.user.has_group('ems_drug_management.group_drug_superadmin'):
            request.session[
                'warning_message'] = "You don't have permission to access the Super Admin Portal"
            return request.redirect('/')
        return request.render('ems_drug_management.admin_dashboard')

    @http.route('/ems/drugs', type='http', auth='user', website=True)
    def ems_drug_list(self, **kw):
        drugs = request.env['ems.drug'].search([])
        return request.render('ems_drug_management.portal_drug_list', {
            'drugs': drugs,
        })

    @http.route('/ems/inventory', type='http', auth='user', website=True)
    def ems_inventory(self, **kw):
        user = request.env.user
        domain = []
        if user.has_group('ems_drug_management.group_ems_paramedic'):
            domain = [('station_id', 'in', user.ems_profile_ids.station_ids.ids)]

        inventory = request.env['ems.drug.lot'].search(domain)
        return request.render('ems_drug_management.portal_inventory', {
            'inventory': inventory,
        })