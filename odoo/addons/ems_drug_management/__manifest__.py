{
    'name': 'EMS Drug Management System',
    'version': '1.0',
    'summary': 'Comprehensive drug management system for EMS organizations',
    'description': """
        Track drug inventory across stations, safes, and pouches with full audit capabilities.
        Includes lot tracking, expiration monitoring, and user access controls.
    """,
    'author': 'Luminous Labs',
    'website': 'https://luminouslabsbd.com',
    'category': 'Healthcare',
    'depends': ['base', 'mail', 'web'],
    'data': [
        # 'security/ir.model.access.csv',
        # 'security/security.xml',
        'data/ems_data.xml',
        # 'data/cron.xml',
        # 'reports/report_actions.xml',
        # 'reports/inventory_report.xml',
        # 'views/ems_station_views.xml',
        # 'views/ems_safe_views.xml',
        # 'views/ems_pouch_views.xml',
        # 'views/ems_drug_views.xml',
        # 'views/ems_inventory_log_views.xml',
        # 'views/ems_user_profile_views.xml',
        # 'views/menu_views.xml',
        'views/templates.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'ems_drug_management/static/src/js/barcode_scan.js',
        ],
    },
    'demo': [],
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}