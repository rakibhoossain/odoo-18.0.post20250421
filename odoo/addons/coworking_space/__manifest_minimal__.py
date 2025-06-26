# -*- coding: utf-8 -*-
{
    'name': 'Coworking Space Management (Minimal)',
    'version': '18.0.1.0.0',
    'category': 'Services',
    'summary': 'Minimal version for testing installation',
    'description': """
Coworking Space Management System - Minimal Version
==================================================

This is a minimal version of the coworking space addon for testing installation.
If this installs successfully, you can then upgrade to the full version.

Features in minimal version:
- Basic membership plans
- Simple room management
- Basic booking system

To use this minimal version:
1. Rename __manifest__.py to __manifest_full__.py
2. Rename __manifest_minimal__.py to __manifest__.py
3. Try installing the addon
4. If successful, switch back to full version
    """,
    'author': 'Luminous Labs BD',
    'website': 'https://luminouslabsbd.com',
    'license': 'LGPL-3',
    
    'depends': [
        'base',
        'sale',
        'account',
        'crm',
        'portal',
    ],
    
    'data': [
        # Security only
        'security/ir.model.access.csv',
        
        # Basic views only
        'views/coworking_menus.xml',
    ],
    
    'demo': [
        # No demo data for minimal version
    ],
    
    'assets': {
        # No assets for minimal version
    },
    
    'installable': True,
    'auto_install': False,
    'application': True,
    
    'external_dependencies': {
        'python': [],
    },
}
