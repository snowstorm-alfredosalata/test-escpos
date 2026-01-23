"""
Integration tests for printer services
Run with: python -m pytest tests/
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
import socket


class TestSF20FiscalPrinterAdapter:
    """Test SF20 fiscal printer adapter"""

    def test_connect_success(self):
        """Test successful connection to fiscal printer"""
        from it_epos_fiscal_nonfiscal_printer.services.fiscal_printer_service import SF20FiscalPrinterAdapter
        
        adapter = SF20FiscalPrinterAdapter('192.168.1.100', 9100)
        
        # Mock socket
        with patch('socket.socket') as mock_socket_class:
            mock_socket = MagicMock()
            mock_socket_class.return_value = mock_socket
            
            success, msg = adapter.connect()
            
            assert success is True
            assert 'successfully' in msg.lower()

    def test_connect_timeout(self):
        """Test connection timeout"""
        from it_epos_fiscal_nonfiscal_printer.services.fiscal_printer_service import SF20FiscalPrinterAdapter
        
        adapter = SF20FiscalPrinterAdapter('192.168.1.100', 9100, timeout=1)
        
        with patch('socket.socket') as mock_socket_class:
            mock_socket = MagicMock()
            mock_socket.connect.side_effect = socket.timeout('Timeout')
            mock_socket_class.return_value = mock_socket
            
            success, msg = adapter.connect()
            
            assert success is False
            assert 'timeout' in msg.lower()

    def test_get_status(self):
        """Test getting printer status"""
        from it_epos_fiscal_nonfiscal_printer.services.fiscal_printer_service import SF20FiscalPrinterAdapter
        
        adapter = SF20FiscalPrinterAdapter('192.168.1.100', 9100)
        
        with patch.object(adapter, '_send_command', return_value=b'READY'):
            with patch.object(adapter, '_parse_status_response', 
                            return_value={'state': 'receipt_closed', 'ready': True}):
                status = adapter.get_status()
                
                assert status['ready'] is True
                assert status['state'] == 'receipt_closed'

    def test_open_receipt(self):
        """Test opening receipt"""
        from it_epos_fiscal_nonfiscal_printer.services.fiscal_printer_service import SF20FiscalPrinterAdapter
        
        adapter = SF20FiscalPrinterAdapter('192.168.1.100', 9100)
        adapter.socket = MagicMock()
        
        with patch.object(adapter, '_send_command', return_value=b'OK'):
            success, msg = adapter.open_receipt()
            
            assert success is True
            assert adapter.current_state == SF20FiscalPrinterAdapter.STATE_RECEIPT_OPEN


class TestESCPOSPrinterAdapter:
    """Test ESC/POS non-fiscal printer adapter"""

    def test_connect_success(self):
        """Test successful connection to ESC/POS printer"""
        from it_epos_fiscal_nonfiscal_printer.services.nonfiscal_printer_service import ESCPOSPrinterAdapter
        
        adapter = ESCPOSPrinterAdapter('192.168.1.101', 9100)
        
        with patch('socket.socket') as mock_socket_class:
            mock_socket = MagicMock()
            mock_socket_class.return_value = mock_socket
            
            success, msg = adapter.connect()
            
            assert success is True
            assert adapter.is_ready is True

    def test_print_comanda(self):
        """Test printing comanda"""
        from it_epos_fiscal_nonfiscal_printer.services.nonfiscal_printer_service import ESCPOSPrinterAdapter
        
        adapter = ESCPOSPrinterAdapter('192.168.1.101', 9100)
        adapter.socket = MagicMock()
        adapter.is_ready = True
        
        order_data = {
            'order_number': 'ORD-001',
            'table': 'TABLE-5',
            'items': [
                {'description': 'Pizza Margherita', 'quantity': 2, 'notes': ''}
            ]
        }
        
        success, msg = adapter.print_comanda(order_data)
        
        assert success is True
        assert 'printed' in msg.lower()


class TestPrinterFactory:
    """Test printer factory"""

    def test_create_fiscal_printer(self):
        """Test creating fiscal printer adapter"""
        from it_epos_fiscal_nonfiscal_printer.services.printer_factory import PrinterFactory
        
        adapter = PrinterFactory.create_fiscal_printer(
            pos_config_id=1,
            ip='192.168.1.100',
            port=9100
        )
        
        assert adapter is not None
        assert adapter.ip == '192.168.1.100'
        assert adapter.port == 9100

    def test_get_cached_printer(self):
        """Test retrieving cached printer"""
        from it_epos_fiscal_nonfiscal_printer.services.printer_factory import PrinterFactory
        
        adapter1 = PrinterFactory.create_fiscal_printer(
            pos_config_id=1,
            ip='192.168.1.100'
        )
        
        adapter2 = PrinterFactory.get_fiscal_printer(pos_config_id=1)
        
        assert adapter1 is adapter2

    def test_disconnect_all(self):
        """Test disconnecting all printers"""
        from it_epos_fiscal_nonfiscal_printer.services.printer_factory import PrinterFactory
        
        PrinterFactory.create_fiscal_printer(1, '192.168.1.100')
        PrinterFactory.create_nonfiscal_printer(1, '192.168.1.101')
        
        PrinterFactory.disconnect_all()
        
        assert len(PrinterFactory._fiscal_instances) == 0
        assert len(PrinterFactory._nonfiscal_instances) == 0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
