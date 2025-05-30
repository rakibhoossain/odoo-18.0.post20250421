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
        'security/security.xml',
        'security/ir.model.access.csv',

        'templates/ems_portal_templates.xml',



        'data/ems_data.xml',
        # 'data/cron.xml',

        'views/dashboard/header_nav.xml',
        'views/dashboard/sidebar.xml',
        'views/dashboard/manager_dashboard.xml',
        'views/dashboard/paramedic_dashboard.xml',
        'views/dashboard/admin_dashboard.xml',

        'views/auth/login_template.xml',



        'reports/report_actions.xml',
        'reports/inventory_report.xml',
        'views/ems_station_views.xml',
        'views/ems_safe_views.xml',
        'views/ems_pouch_views.xml',
        'views/ems_drug_views.xml',
        'views/ems_inventory_log_views.xml',
        'views/ems_user_profile_views.xml',
        'views/ems_tenant_views.xml',
        'views/ems_setting_views.xml',
        'views/menu_views.xml',
        'views/templates.xml',
    ],
    'assets': {
        'ems_drug_management.assets_frontend': [
            'ems_drug_management/static/lib/bootstrap/bootstrap.min.css',
            'ems_drug_management/static/lib/fontawesome/css/all.min.css',
            'ems_drug_management/static/src/css/frontend.css',
            'ems_drug_management/static/lib/bootstrap/bootstrap.bundle.min.js',
            'ems_drug_management/static/src/js/frontend.js',
        ],
        'web.assets_backend': [
            'ems_drug_management/static/src/js/barcode_scan.js',
            'ems_drug_management/static/src/js/dashboard.js',
            'ems_drug_management/static/src/xml/dashboard.xml',
        ],
    },
    'images': ['static/description/icon.png'],
    'demo': [],
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}