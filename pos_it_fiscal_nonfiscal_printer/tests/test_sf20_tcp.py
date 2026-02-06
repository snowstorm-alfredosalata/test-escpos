# -*- coding: utf-8 -*-
"""Unit tests for SF20 fiscal driver."""

import unittest
from unittest.mock import Mock, MagicMock, patch
import socket


class TestSF20Protocol(unittest.TestCase):
    """Test SF20 protocol helpers."""

    def test_compute_checksum(self):
        """Test XOR checksum computation."""
        from pos_it_fiscal_nonfiscal_printer.drivers.sf20_tcp import _compute_checksum

        # Simple test: XOR of bytes
        data = bytes([0x30, 0x31, 0x32])  # '012'
        checksum = _compute_checksum(data)
        expected = 0x30 ^ 0x31 ^ 0x32
        self.assertEqual(checksum, expected)

    def test_frame_message(self):
        """Test message framing with STX/ETX."""
        from pos_it_fiscal_nonfiscal_printer.drivers.sf20_tcp import (
            _frame_message, STX, ETX
        )

        command = 0x30  # CMD_OPEN_RECEIPT
        payload = b'\x01'

        frame = _frame_message(command, payload)

        # Check framing
        self.assertEqual(frame[0], STX)
        self.assertEqual(frame[-1], ETX)
        self.assertEqual(frame[1], command)
        self.assertEqual(frame[2:3], payload)

    def test_parse_response_valid(self):
        """Test parsing valid response."""
        from pos_it_fiscal_nonfiscal_printer.drivers.sf20_tcp import (
            _parse_response, _frame_message
        )

        # Create a valid framed message
        command = 0x30
        payload = b'OK'
        frame = _frame_message(command, payload)

        result = _parse_response(frame)

        self.assertTrue(result['success'])
        self.assertEqual(result['command'], command)
        self.assertEqual(result['payload'], payload)

    def test_parse_response_invalid_framing(self):
        """Test parsing response with invalid framing."""
        from pos_it_fiscal_nonfiscal_printer.drivers.sf20_tcp import _parse_response

        result = _parse_response(b'invalid')

        self.assertFalse(result['success'])
        self.assertEqual(result['error'], 'invalid_framing')

    def test_parse_response_checksum_mismatch(self):
        """Test parsing response with bad checksum."""
        from pos_it_fiscal_nonfiscal_printer.drivers.sf20_tcp import (
            _parse_response, STX, ETX
        )

        # Create frame with wrong checksum
        frame = bytes([STX, 0x30, 0xFF, ETX])  # Wrong checksum

        result = _parse_response(frame)

        self.assertFalse(result['success'])
        self.assertEqual(result['error'], 'checksum_mismatch')


class TestSF20Driver(unittest.TestCase):
    """Test cases for SF20Driver."""

    def setUp(self):
        """Set up test fixtures."""
        self.printer = Mock()
        self.printer.id = 1
        self.printer.host = '192.168.1.200'
        self.printer.port = 9100
        self.printer.timeout = 5

        # Mock socket
        self.mock_socket = MagicMock()

    def _get_driver(self, **kwargs):
        """Create driver with mocked socket factory."""
        from pos_it_fiscal_nonfiscal_printer.drivers.sf20_tcp import SF20Driver

        def mock_socket_factory(*args):
            return self.mock_socket

        factory = kwargs.pop('socket_factory', mock_socket_factory)
        return SF20Driver(
            printer=self.printer,
            env=None,
            socket_factory=factory,
            **kwargs
        )

    def test_send_command_success(self):
        """Test successful command send/receive."""
        from pos_it_fiscal_nonfiscal_printer.drivers.sf20_tcp import (
            _frame_message, STX, ETX, CMD_STATUS
        )

        # Mock successful response
        response_frame = _frame_message(CMD_STATUS, b'OK')
        self.mock_socket.recv.return_value = response_frame

        driver = self._get_driver()
        result = driver._send_command(CMD_STATUS)

        self.assertTrue(result['success'])
        self.mock_socket.connect.assert_called_once_with(('192.168.1.200', 9100))
        self.mock_socket.sendall.assert_called_once()
        self.mock_socket.close.assert_called_once()

    def test_send_command_timeout(self):
        """Test timeout handling."""
        self.mock_socket.recv.side_effect = socket.timeout()

        driver = self._get_driver()
        result = driver._send_command(0x30)

        self.assertFalse(result['success'])
        self.assertEqual(result['error'], 'timeout')
        self.assertTrue(result['canRetry'])

    def test_send_command_connection_refused(self):
        """Test connection refused."""
        self.mock_socket.connect.side_effect = socket.error("Connection refused")

        driver = self._get_driver()
        result = driver._send_command(0x30)

        self.assertFalse(result['success'])
        self.assertIn('socket_error', result['error'])

    def test_open_receipt(self):
        """Test open_receipt command."""
        from pos_it_fiscal_nonfiscal_printer.drivers.sf20_tcp import (
            _frame_message, CMD_OPEN_RECEIPT
        )

        response = _frame_message(CMD_OPEN_RECEIPT, b'001')
        self.mock_socket.recv.return_value = response

        driver = self._get_driver()
        result = driver.open_receipt({'operator_id': 1})

        self.assertTrue(result['success'])
        self.assertIn('receipt_number', result)

    def test_sell_item(self):
        """Test sell_item command."""
        from pos_it_fiscal_nonfiscal_printer.drivers.sf20_tcp import (
            _frame_message, CMD_SELL_ITEM
        )

        response = _frame_message(CMD_SELL_ITEM, b'OK')
        self.mock_socket.recv.return_value = response

        driver = self._get_driver()
        result = driver.sell_item({
            'description': 'Test Product',
            'quantity': 2,
            'price': 10.50,
            'department': 1,
            'vat_rate': '22'
        })

        self.assertTrue(result['success'])

    def test_apply_payment(self):
        """Test apply_payment command."""
        from pos_it_fiscal_nonfiscal_printer.drivers.sf20_tcp import (
            _frame_message, CMD_PAYMENT
        )

        response = _frame_message(CMD_PAYMENT, b'OK')
        self.mock_socket.recv.return_value = response

        driver = self._get_driver()
        result = driver.apply_payment({
            'amount': 21.00,
            'method': 'cash'
        })

        self.assertTrue(result['success'])

    def test_close_receipt(self):
        """Test close_receipt command."""
        from pos_it_fiscal_nonfiscal_printer.drivers.sf20_tcp import (
            _frame_message, CMD_CLOSE_RECEIPT
        )

        response = _frame_message(CMD_CLOSE_RECEIPT, b'12345678')
        self.mock_socket.recv.return_value = response

        driver = self._get_driver()
        result = driver.close_receipt({})

        self.assertTrue(result['success'])
        self.assertIn('fiscal_data', result)

    def test_status(self):
        """Test status query."""
        from pos_it_fiscal_nonfiscal_printer.drivers.sf20_tcp import (
            _frame_message, CMD_STATUS
        )

        response = _frame_message(CMD_STATUS, b'\x00\x00')
        self.mock_socket.recv.return_value = response

        driver = self._get_driver()
        result = driver.status({})

        self.assertTrue(result['success'])
        self.assertEqual(result['status'], 'ready')

    def test_handle_action_dispatch(self):
        """Test action dispatching."""
        from pos_it_fiscal_nonfiscal_printer.drivers.sf20_tcp import _frame_message, CMD_STATUS

        response = _frame_message(CMD_STATUS, b'OK')
        self.mock_socket.recv.return_value = response

        driver = self._get_driver()
        result = driver.handle_action('status', {})

        self.assertTrue(result['success'])

    def test_handle_action_unknown(self):
        """Test unknown action raises NotImplementedError."""
        driver = self._get_driver()

        with self.assertRaises(NotImplementedError):
            driver.handle_action('unknown_action', {})


if __name__ == '__main__':
    unittest.main()
