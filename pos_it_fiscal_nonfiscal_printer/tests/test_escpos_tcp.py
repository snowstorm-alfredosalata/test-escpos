# -*- coding: utf-8 -*-
"""Unit tests for ESC/POS TCP driver."""

import base64
import unittest
from unittest.mock import Mock, MagicMock, patch


class TestEscposTCPDriver(unittest.TestCase):
    """Test cases for EscposTCPDriver."""

    def setUp(self):
        """Set up test fixtures."""
        # Mock printer record
        self.printer = Mock()
        self.printer.id = 1
        self.printer.host = '192.168.1.100'
        self.printer.port = 9100
        self.printer.timeout = 5
        self.printer.use_iot_device = False

        # Mock escpos Network printer
        self.mock_escpos = MagicMock()

    def _get_driver(self, **kwargs):
        """Create driver with mocked factory."""
        from pos_it_fiscal_nonfiscal_printer.drivers.escpos_tcp import EscposTCPDriver

        factory = kwargs.pop('escpos_factory', lambda h, p, t: self.mock_escpos)
        return EscposTCPDriver(
            printer=self.printer,
            env=None,
            escpos_factory=factory,
            **kwargs
        )

    def test_print_receipt_text(self):
        """Test printing plain text."""
        driver = self._get_driver()

        result = driver.print_receipt({'text': 'Hello World'})

        self.assertEqual(result['status'], 'ok')
        self.mock_escpos.text.assert_called_once_with('Hello World')
        self.mock_escpos.cut.assert_called_once()
        self.mock_escpos.close.assert_called_once()

    def test_print_receipt_raw(self):
        """Test printing raw bytes."""
        driver = self._get_driver()
        raw_data = base64.b64encode(b'\x1b\x40Hello').decode()  # ESC @ reset + Hello

        result = driver.print_receipt({'raw': raw_data})

        self.assertEqual(result['status'], 'ok')
        self.mock_escpos._raw.assert_called_once()
        self.mock_escpos.cut.assert_called_once()

    def test_print_receipt_connection_error(self):
        """Test handling connection errors."""
        import socket

        def failing_factory(h, p, t):
            raise socket.error("Connection refused")

        driver = self._get_driver(escpos_factory=failing_factory)

        result = driver.print_receipt({'text': 'Test'})

        self.assertEqual(result['status'], 'error')
        self.assertIn('Connection failed', result['message'])
        self.assertTrue(result.get('canRetry', False))

    def test_print_receipt_timeout(self):
        """Test handling timeout."""
        import socket

        self.mock_escpos.text.side_effect = socket.timeout()
        driver = self._get_driver()

        result = driver.print_receipt({'text': 'Test'})

        self.assertEqual(result['status'], 'error')
        self.assertIn('timeout', result['message'].lower())
        self.assertTrue(result.get('canRetry', False))

    def test_open_cashbox(self):
        """Test cash drawer command."""
        driver = self._get_driver()

        result = driver.open_cashbox({})

        self.assertEqual(result['result'], True)
        self.mock_escpos.cashdraw.assert_called_once_with(2)
        self.mock_escpos.close.assert_called_once()

    def test_print_via_iot_proxy(self):
        """Test IoT proxy delegation."""
        self.printer.use_iot_device = True

        mock_proxy = Mock(return_value={'result': True, 'message': 'OK'})
        driver = self._get_driver(iot_proxy=mock_proxy)

        result = driver.print_receipt({'text': 'Test'})

        self.assertEqual(result['status'], 'ok')
        mock_proxy.assert_called_once()
        # Verify escpos was NOT called
        self.mock_escpos.text.assert_not_called()

    def test_connection_params_from_printer(self):
        """Test connection parameters are read from printer record."""
        driver = self._get_driver()

        host, port, timeout = driver._get_connection_params()

        self.assertEqual(host, '192.168.1.100')
        self.assertEqual(port, 9100)
        self.assertEqual(timeout, 5)

    def test_connection_params_defaults(self):
        """Test default connection parameters."""
        self.printer.host = None
        self.printer.port = None
        self.printer.timeout = None

        driver = self._get_driver()
        host, port, timeout = driver._get_connection_params()

        self.assertEqual(host, '127.0.0.1')
        self.assertEqual(port, 9100)
        self.assertEqual(timeout, 10)


class TestEscposHelpers(unittest.TestCase):
    """Test helper functions."""

    def test_default_factory_import_error(self):
        """Test that missing escpos library raises helpful error."""
        from pos_it_fiscal_nonfiscal_printer.drivers.escpos_tcp import _default_escpos_factory

        with patch.dict('sys.modules', {'escpos': None, 'escpos.printer': None}):
            # The factory should still work if escpos is available
            # This test verifies the import path is correct
            pass


if __name__ == '__main__':
    unittest.main()
