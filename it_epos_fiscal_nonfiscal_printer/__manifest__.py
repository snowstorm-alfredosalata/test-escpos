# -*- coding: utf-8 -*-
{
    'name': 'POS Fiscal & Non-Fiscal Printer Integration',
    'version': '19.0.1.0.0',
    'category': 'Point of Sale',
    'summary': 'Integration of SF20 fiscal printer and ESC/POS non-fiscal printer for Odoo POS',
    'description': """
        Odoo 19 POS module for Italian restaurant/bar environments.
        
        Features:
        - Fiscal printer integration (Protocollo Fiscale SF20 - HYDRA)
        - Non-fiscal ESC/POS printer for kitchen orders (comande)
        - Real-time fiscal printer status display
        - Configurable printer IP addresses and ports
        - POS UI controls for fiscal and order printing
        - Safe error handling and fail-safe behavior
    """,
    'author': 'Alfredo Salata',
    'website': 'https://github.com/snowstorm-alfredosalata/test-escpos',
    'license': 'AGPL-3',
    'depends': [
        'base',
        'point_of_sale',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/pos_config_views.xml',
        'views/pos_printer_status_views.xml',
    ],
    'assets': {
        'point_of_sale.assets_frontend': [
            'it_epos_fiscal_nonfiscal_printer/static/src/js/printer_status_widget.js',
            'it_epos_fiscal_nonfiscal_printer/static/src/js/fiscal_printer_service.js',
            'it_epos_fiscal_nonfiscal_printer/static/src/js/comanda_printer_service.js',
        ],
        'web.assets_backend': [
            'it_epos_fiscal_nonfiscal_printer/static/src/css/printer_status.css',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
}
