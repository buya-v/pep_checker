{
    'name': 'Politically Exposed Person (PEP) Management',
    'version': '18.0.1.0.0',
    'category': 'Accounting/Accounting',
    'summary': 'Manage and screen for Politically Exposed Persons (PEPs) for AML/KYC compliance.',
    'sequence': -100,
    'description': """
        Politically Exposed Person (PEP) Management
        ===========================================
        This module provides a comprehensive framework for identifying, managing, and monitoring
        Politically Exposed Persons (PEPs), their family members, and close associates as part
        of Anti-Money Laundering (AML) and Know Your Customer (KYC) compliance procedures.
    """,
    'author': 'Your Name',
    'website': 'https://www.yourwebsite.com',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'mail'
    ],
    'external_dependencies': {
        'python': ['dateutil', 'google-generativeai', 'jellyfish'],
    },
    'data': [
        'security/pep_security.xml',
        'security/ir.model.access.csv',
        'views/pep_views.xml',
        'data/data.xml',
    ],
    'tests': [
        'tests/test_pep.py',
    ],
    'demo': [],
    'installable': True,
    'application': True,
    'auto_install': False,
}