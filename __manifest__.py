{
    'name': 'PEP Checker',
    'version': '18.0.1.0.0',
    'category': 'Development',
    'summary': 'Python Enhancement Proposal (PEP) Compliance Checker',
    'sequence': -100,
    'description': """
        PEP Checker Module for Odoo 18
        =============================
        This module helps in checking and ensuring Python code compliance with PEP standards.
    """,
    'author': 'Your Name',
    'website': 'https://www.yourwebsite.com',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'mail',
    ],
    'data': [
        'security/pep_security.xml',
        'security/ir.model.access.csv',
        'views/pep_views.xml',
    ],
    'demo': [],
    'installable': True,
    'application': True,
    'auto_install': False,
}