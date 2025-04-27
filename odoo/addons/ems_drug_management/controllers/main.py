from odoo import http
from odoo.http import request


class EMSPortal(http.Controller):

    @http.route('/', type='http', auth="public", website=True)
    def portal_selection(self, **kw):
        # If user is logged in, redirect to their portal
        # if request.session.uid:
        #     return request.redirect('/my/portal')
        return request.render('ems_drug_management.ems_portal_selection_page', {})

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