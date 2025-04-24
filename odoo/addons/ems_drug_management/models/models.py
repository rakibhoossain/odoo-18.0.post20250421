from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from datetime import date, datetime



# ----------------------------------
# Base Models: Stations, Safes, Pouches
# ----------------------------------

class EmsStation(models.Model):
    _name = 'ems.station'
    _description = 'EMS Station'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(required=True, tracking=True)
    code = fields.Char(required=True, index=True, tracking=True)
    active = fields.Boolean(default=True, tracking=True)
    safe_ids = fields.One2many('ems.safe', 'station_id', string='Safes')
    pouch_ids = fields.One2many('ems.pouch', 'station_id', string='Pouches')

    def toggle_active(self):
        for station in self:
            if not station.active:
                # Check if any safes are active
                if station.safe_ids.filtered(lambda s: s.active):
                    raise UserError(_("Cannot archive station with active safes"))
            super(EmsStation, station).toggle_active()

    @api.constrains('code')
    def _check_code_unique(self):
        for station in self:
            if self.search_count([('code', '=', station.code), ('id', '!=', station.id)]):
                raise ValidationError(_("Station code must be unique"))


class EmsSafe(models.Model):
    _name = 'ems.safe'
    _description = 'Drug Safe'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(required=True, tracking=True)
    station_id = fields.Many2one('ems.station', required=True, tracking=True)
    capacity_note = fields.Text()
    audit_flag = fields.Boolean(default=True, tracking=True)
    active = fields.Boolean(default=True, tracking=True)
    drug_lot_ids = fields.One2many('ems.drug.lot', 'safe_id', string='Drug Lots')

    def toggle_active(self):
        for safe in self:
            if not safe.active:
                # Check if any drug lots are assigned
                if safe.drug_lot_ids:
                    raise UserError(_("Cannot archive safe with assigned drug lots"))
            super(EmsSafe, safe).toggle_active()


class EmsPouch(models.Model):
    _name = 'ems.pouch'
    _description = 'Drug Pouch'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(required=True, tracking=True)
    user_id = fields.Many2one('res.users', tracking=True)
    station_id = fields.Many2one('ems.station', tracking=True)
    pouch_type = fields.Selection([
        ('standard', 'Standard'),
        ('backup', 'Backup')
    ], required=True, tracking=True)
    min_threshold = fields.Integer(tracking=True)
    max_threshold = fields.Integer(tracking=True)
    active = fields.Boolean(default=True, tracking=True)
    drug_lot_ids = fields.One2many('ems.drug.lot', 'pouch_id', string='Drug Lots')

    def toggle_active(self):
        for pouch in self:
            if not pouch.active:
                # Check if any drug lots are assigned
                if pouch.drug_lot_ids:
                    raise UserError(_("Cannot archive pouch with assigned drug lots"))
            super(EmsPouch, pouch).toggle_active()


# ----------------------------------
# Drugs and Inventory
# ----------------------------------
class EmsDrug(models.Model):
    _name = 'ems.drug'
    _description = 'Drug Master'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'ems.barcode.mixin']

    name = fields.Char(required=True, tracking=True)
    strength = fields.Char(required=True, tracking=True)
    form = fields.Selection([
        ('ampoule', 'Ampoule'),
        ('vial', 'Vial'),
        ('syringe', 'Syringe'),
        ('bottle', 'Bottle')
    ], required=True, tracking=True)
    manufacturer = fields.Char(tracking=True)
    default_pouch_qty = fields.Integer(tracking=True)
    active = fields.Boolean(default=True, tracking=True)
    drug_lot_ids = fields.One2many('ems.drug.lot', 'drug_id', string='Lots')

    def name_get(self):
        result = []
        for drug in self:
            name = f"{drug.name} {drug.strength} {drug.form}"
            result.append((drug.id, name))
        return result


class EmsDrugLot(models.Model):
    _name = 'ems.drug.lot'
    _description = 'Drug Lot'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'ems.barcode.mixin']
    _order = 'expiry_date asc'

    drug_id = fields.Many2one('ems.drug', required=True, tracking=True)
    lot_number = fields.Char(required=True, tracking=True)
    batch_number = fields.Char(tracking=True)
    expiry_date = fields.Date(required=True, tracking=True)
    station_id = fields.Many2one('ems.station', tracking=True)
    safe_id = fields.Many2one('ems.safe', tracking=True)
    pouch_id = fields.Many2one('ems.pouch', tracking=True)
    in_safe_qty = fields.Integer(tracking=True)
    in_pouch_qty = fields.Integer(tracking=True)
    assigned_user_ids = fields.Many2many('res.users', tracking=True)
    status = fields.Selection([
        ('active', 'Active'),
        ('low', 'Low'),
        ('expired', 'Expired'),
        ('retired', 'Retired')
    ], default='active', tracking=True)
    last_movement = fields.Datetime(tracking=True)

    @api.model
    def create(self, vals):
        # Handle single or batch create
        records = super(EmsDrugLot, self).create(vals)
        records._check_expiry()  # `records` is a recordset (even if it's just one)
        return records

    @api.model
    def _check_expiry_daily(self):
        """Daily cron job to check for expired drugs"""
        today = fields.Date.today()
        expired_lots = self.search([
            ('expiry_date', '<', today),
            ('status', '!=', 'expired')
        ])
        expired_lots.write({'status': 'expired'})

        # Create activities for expired lots
        for lot in expired_lots:
            lot._create_expiry_activity()

    def write(self, vals):
        result = super(EmsDrugLot, self).write(vals)
        if 'expiry_date' in vals:
            self._check_expiry()
        return result

    def _check_expiry(self):
        today = date.today()
        for lot in self:
            if lot.expiry_date and lot.expiry_date < today:
                lot.status = 'expired'
                lot._create_expiry_activity()

    def _create_expiry_activity(self):
        self.ensure_one()
        self.env['mail.activity'].create({
            'activity_type_id': self.env.ref('mail.mail_activity_data_todo').id,
            'summary': _('Drug Lot Expired'),
            'note': _('The drug lot %s has expired on %s') % (self.lot_number, self.expiry_date),
            'user_id': self.env.user.id,
            'res_id': self.id,
            'res_model_id': self.env['ir.model']._get('ems.drug.lot').id,
        })


# ----------------------------------
# Inventory Movement Logs
# ----------------------------------

class EmsInventoryLog(models.Model):
    _name = 'ems.inventory.log'
    _description = 'Inventory Log'
    _order = 'timestamp desc'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    action_type = fields.Selection([
        ('add', 'Add'),
        ('restock', 'Restock'),
        ('issue', 'Issue'),
        ('use', 'Use'),
        ('return', 'Return'),
        ('retire', 'Retire'),
        ('manual', 'Manual Override'),
        ('override', 'Override')
    ], required=True, tracking=True)
    timestamp = fields.Datetime(default=fields.Datetime.now, tracking=True)
    drug_id = fields.Many2one('ems.drug', tracking=True)
    lot_number = fields.Char(tracking=True)
    quantity = fields.Integer(tracking=True)
    from_location = fields.Char(tracking=True)
    to_location = fields.Char(tracking=True)
    pouch_id = fields.Many2one('ems.pouch', tracking=True)
    station_id = fields.Many2one('ems.station', tracking=True)
    user_id = fields.Many2one('res.users', default=lambda self: self.env.user, tracking=True)
    witness_id = fields.Many2one('res.users', string='Witness', tracking=True)
    flag = fields.Char(tracking=True)
    override_reason = fields.Text(tracking=True)
    notes = fields.Text(tracking=True)
    manager_approval = fields.Selection([
        ('yes', 'Yes'),
        ('no', 'No'),
        ('not_required', 'Not Required')
    ], default='not_required', tracking=True)

    @api.model
    def create(self, vals):
        record = super(EmsInventoryLog, self).create(vals)
        if record.action_type in ['override', 'manual'] and record.manager_approval == 'not_required':
            record._request_approval()
        return record

    def _request_approval(self):
        self.ensure_one()
        manager_group = self.env.ref('ems_drug_management.group_ems_manager')
        managers = self.env['res.users'].search([('groups_id', 'in', manager_group.ids)])

        for manager in managers:
            self.env['mail.activity'].create({
                'activity_type_id': self.env.ref('mail.mail_activity_data_todo').id,
                'summary': _('Inventory Override Approval Needed'),
                'note': _('An inventory override action requires your approval'),
                'user_id': manager.id,
                'res_id': self.id,
                'res_model_id': self.env['ir.model']._get('ems.inventory.log').id,
            })


# ----------------------------------
# User Roles and Assignment
# ----------------------------------

class EmsUserProfile(models.Model):
    _name = 'ems.user.profile'
    _description = 'EMS User Role Profile'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    user_id = fields.Many2one('res.users', required=True, tracking=True)

    role = fields.Selection([
        ('manager', 'Manager'),
        ('paramedic', 'Paramedic'),
        ('superadmin', 'Superadmin')
    ], required=True, tracking=True)
    station_ids = fields.Many2many('ems.station', string='Assigned Stations', tracking=True)
    status = fields.Selection([
        ('active', 'Active'),
        ('disabled', 'Disabled')
    ], default='active', tracking=True)

    _sql_constraints = [
        ('user_unique', 'unique(user_id)', 'A user can only have one profile!'),
    ]

    @api.model
    def create(self, vals):
        profile = super(EmsUserProfile, self).create(vals)
        # Update the user's groups based on role
        profile._update_user_groups()
        return profile

    def write(self, vals):
        result = super(EmsUserProfile, self).write(vals)
        if 'role' in vals:
            self._update_user_groups()
        return result

    def _update_user_groups(self):
        for profile in self:
            user = profile.user_id
            # Clear all EMS groups first
            ems_groups = self.env.ref('ems_drug_management.group_ems_paramedic') | \
                         self.env.ref('ems_drug_management.group_ems_manager') | \
                         self.env.ref('ems_drug_management.group_ems_superadmin')
            user.groups_id -= ems_groups

            # Add the appropriate group based on role
            if profile.role == 'paramedic':
                user.groups_id += self.env.ref('ems_drug_management.group_ems_paramedic')
            elif profile.role == 'manager':
                user.groups_id += self.env.ref('ems_drug_management.group_ems_manager')
            elif profile.role == 'superadmin':
                user.groups_id += self.env.ref('ems_drug_management.group_ems_superadmin')


# ----------------------------------
# Alerts, Settings, Deactivation Rules
# ----------------------------------

class EmsSystemSetting(models.Model):
    _name = 'ems.setting'
    _description = 'EMS System Settings'

    name = fields.Char(required=True)
    default_pack_size = fields.Integer(default=22)
    low_stock_trigger = fields.Integer()
    archive_usage_toggle = fields.Boolean(default=True)
    archive_expiry_days = fields.Integer()

    @api.model
    def get_default_settings(self):
        return self.search([], limit=1)

class EmsDeactivationRule(models.Model):
    _name = 'ems.deactivation.rule'
    _description = 'Deactivation Policy'

    model = fields.Char(required=True)
    rule_description = fields.Text()
    inactive_days = fields.Integer()

    @api.model
    def _apply_deactivation_rules(self):
        """Apply all deactivation rules"""
        rules = self.search([])
        for rule in rules:
            if rule.model == 'ems.drug.lot':
                if rule.inactive_days == 0:
                    # Special case for expired drugs
                    continue  # Handled by separate cron
                else:
                    date_limit = fields.Date.today() - timedelta(days=rule.inactive_days)
                    domain = [
                        ('last_movement', '<', date_limit),
                        ('active', '=', True)
                    ]
                    items = self.env[rule.model].search(domain)
                    items.write({'active': False})
            elif rule.model in ['ems.pouch', 'ems.safe']:
                date_limit = fields.Date.today() - timedelta(days=rule.inactive_days)
                domain = [
                    ('write_date', '<', date_limit),
                    ('active', '=', True)
                ]
                items = self.env[rule.model].search(domain)
                items.write({'active': False})


# ----------------------------------
# Multi-Tenant (Superadmin) Support
# ----------------------------------

class EmsTenant(models.Model):
    _name = 'ems.tenant'
    _description = 'EMS Client Tenant'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(required=True, tracking=True)
    contact_name = fields.Char(tracking=True)
    contact_email = fields.Char(tracking=True)
    station_count = fields.Integer(compute='_compute_station_count', tracking=True)
    active = fields.Boolean(default=True, tracking=True)
    setting_ids = fields.One2many('ems.tenant.setting', 'tenant_id', string='Settings')

    def _compute_station_count(self):
        for tenant in self:
            tenant.station_count = self.env['ems.station'].search_count([])

class EmsTenantSetting(models.Model):
    _name = 'ems.tenant.setting'
    _description = 'Tenant-Specific Settings'

    tenant_id = fields.Many2one('ems.tenant', required=True)
    timezone = fields.Char()
    date_format = fields.Char()
    qr_code_format = fields.Char()
    station_code_prefix = fields.Char()
    alert_email = fields.Boolean(default=True)
    alert_sms = fields.Boolean(default=False)
    data_retention_months = fields.Integer()


class ResUsers(models.Model):
    _inherit = 'res.users'

    ems_profile_id = fields.One2many(
        'ems.user.profile',
        'user_id',
        string='EMS Profile'
    )

    ems_station_ids = fields.Many2many(
        'ems.station',
        compute='_compute_ems_station_ids',
        string='EMS Stations',
        store=False
    )

    def _compute_ems_station_ids(self):
        for user in self:
            profile = user.ems_profile_id[:1]  # get the first one if exists
            user.ems_station_ids = profile.station_ids if profile else self.env['ems.station']
