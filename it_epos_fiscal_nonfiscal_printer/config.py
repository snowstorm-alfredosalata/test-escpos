# -*- coding: utf-8 -*-
"""
Configuration and constants for printer module
"""

# Supported SF20 states
SF20_STATES = {
    'init': 'Initialized',
    'receipt_open': 'Receipt Open',
    'receipt_closed': 'Receipt Closed',
    'z_report_required': 'Z Report Required',
    'memory_full': 'Memory Full',
    'fiscal_memory_error': 'Fiscal Memory Error',
    'unknown': 'Unknown State',
}

# Supported payment types
PAYMENT_TYPES = {
    'cash': 'Contanti',
    'card': 'Carta',
    'check': 'Assegno',
    'other': 'Altro',
}

# Printer statuses
PRINTER_STATUS = {
    'ok': 'OK - Pronto',
    'busy': 'Occupato - Elaborazione',
    'error': 'Errore',
    'offline': 'Offline - Non raggiungibile',
    'warning': 'Attenzione - Azione Richiesta',
    'unknown': 'Sconosciuto - Non verificato',
}

# Default configuration values
DEFAULT_CONFIG = {
    'fiscal': {
        'port': 9100,
        'timeout': 30,
        'fail_safe': True,
    },
    'nonfiscal': {
        'port': 9100,
        'timeout': 10,
        'width': 32,
        'auto_cut': False,
        'auto_open_drawer': False,
    }
}

# SF20 Protocol constants
SF20_PROTOCOL = {
    'HEADER': b'\x1B\x40',
    'EOT': b'\x04',
    'CMD_STATUS': b'\x1B\x6E',
    'CMD_RECEIPT_OPEN': b'\x1B\x47',
    'CMD_RECEIPT_CLOSE': b'\x1B\x43',
    'CMD_ITEM': b'\x1B\x4A',
    'CMD_PAYMENT': b'\x1B\x50',
    'CMD_Z_REPORT': b'\x1B\x5A',
}

# ESC/POS Protocol constants
ESCPOS_PROTOCOL = {
    'ESC': b'\x1B',
    'GS': b'\x1D',
    'CR': b'\x0D',
    'LF': b'\x0A',
    'CRLF': b'\x0D\x0A',
}
