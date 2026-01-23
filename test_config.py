# -*- coding: utf-8 -*-
"""
Development/Testing configuration
Load this to set up a test environment with mock printer adapters
"""

import os
import sys
from unittest.mock import MagicMock, patch

# Test configuration
TEST_CONFIG = {
    'fiscal': {
        'ip': '192.168.1.100',
        'port': 9100,
        'timeout': 30,
        'fail_safe': True,
    },
    'nonfiscal': {
        'ip': '192.168.1.101',
        'port': 9100,
        'timeout': 10,
        'width': 32,
        'auto_cut': False,
        'auto_open_drawer': False,
    }
}

# Mock data
SAMPLE_ORDER = {
    'name': 'ORD-2024-001',
    'table': 'Tavolo 5',
    'session_id': 1,
    'items': [
        {
            'name': 'Pizza Margherita',
            'quantity': 2,
            'price': 8.50,
            'tax': 22,
            'notes': ''
        },
        {
            'name': 'Birra Media',
            'quantity': 2,
            'price': 5.00,
            'tax': 10,
            'notes': ''
        },
    ],
    'payments': [
        {
            'type': 'cash',
            'amount': 27.00,
            'method': 'Cash',
        }
    ]
}

SAMPLE_RECEIPT_DATA = {
    'items': [
        {
            'description': 'Pizza Margherita',
            'quantity': 2,
            'unit_price': 8.50,
            'tax_percent': 22,
        },
        {
            'description': 'Birra Media',
            'quantity': 2,
            'unit_price': 5.00,
            'tax_percent': 10,
        },
    ],
    'payments': [
        {
            'type': 'cash',
            'amount': 27.00,
        }
    ]
}

SAMPLE_COMANDA_DATA = {
    'order_number': 'ORD-2024-001',
    'table': 'Tavolo 5',
    'timestamp': '14:30:25',
    'items': [
        {
            'description': 'Pizza Margherita',
            'quantity': 2,
            'notes': 'Senza cipolla'
        },
        {
            'description': 'Birra Media',
            'quantity': 2,
            'notes': ''
        },
    ],
    'header': 'COMANDA CUCINA',
    'footer': 'Grazie',
}

# Function to setup mock environment
def setup_mock_printers():
    """Setup mock printer adapters for testing"""
    
    # Mock SF20
    fiscal_mock = MagicMock()
    fiscal_mock.get_status.return_value = {
        'state': 'receipt_closed',
        'ready': True,
        'error_code': None,
        'receipts_today': 5,
        'response_time_ms': 150,
    }
    fiscal_mock.open_receipt.return_value = (True, 'Receipt opened')
    fiscal_mock.add_item.return_value = (True, 'Item registered')
    fiscal_mock.process_payment.return_value = (True, 'Payment processed')
    fiscal_mock.close_receipt.return_value = (True, '12345')  # Receipt number
    fiscal_mock.execute_z_report.return_value = (True, 'Z report executed')
    
    # Mock ESC/POS
    nonfiscal_mock = MagicMock()
    nonfiscal_mock.get_status.return_value = {
        'ready': True,
        'connected': True,
        'ip': '192.168.1.101',
        'port': 9100,
        'responsive': True,
    }
    nonfiscal_mock.print_comanda.return_value = (True, 'Comanda printed')
    nonfiscal_mock.print_text.return_value = (True, 'Text printed')
    nonfiscal_mock.cut_paper.return_value = (True, 'Paper cut')
    
    return fiscal_mock, nonfiscal_mock


if __name__ == '__main__':
    print('Test configuration loaded')
    print(f'Test config: {TEST_CONFIG}')
    print(f'Sample order: {SAMPLE_ORDER}')
