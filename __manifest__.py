{
    'name': 'Cutting Stock Optimizer',
    'summary': 'Optimize cutting patterns for panels from stock sheets',
    'description': """
        This module provides tools to optimize the cutting of panels from stock sheets.
        Features:
        - Manage panel definitions
        - Manage stock sheet definitions
        - Run optimization calculations
        - Generate cutting pattern reports
    """,
    'version': '1.0',
    'category': 'Manufacturing',
    'author': 'Your Company',
    'website': 'https://www.yourcompany.com',
    'license': 'LGPL-3',
    'depends': ['base', 'web', 'product', 'stock'],
    'data': [
        'security/ir.model.access.csv',
        'views/panel_views.xml',
        'views/stock_sheet_views.xml',
        'views/optimizer_options_views.xml',
        'views/cutting_job_views.xml',
        'views/menu_views.xml',
        # 'report/cutting_pattern_report_template.xml',
        # 'report/cutting_pattern_report.xml',
        # 'wizard/run_optimization_wizard_views.xml',
    ],
    'demo': [],
    'installable': True,
    'application': True,
    'auto_install': False,
    'external_dependencies': {
        'python': ['numpy', 'matplotlib', 'pulp'],
    },
}