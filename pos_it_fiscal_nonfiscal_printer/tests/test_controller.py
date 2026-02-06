# -*- coding: utf-8 -*-
"""Unit tests for hw_proxy controller."""

import unittest
from unittest.mock import Mock, MagicMock, patch


class TestHwProxyController(unittest.TestCase):
    """Test cases for HwProxyController."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_request = MagicMock()
        self.mock_env = MagicMock()
        self.mock_request.env = self.mock_env

        # Mock user
        self.mock_user = MagicMock()
        self.mock_user._is_internal.return_value = True
        self.mock_env.user = self.mock_user

        # Mock printer
        self.mock_printer = MagicMock()
        self.mock_printer.exists.return_value = True
        self.mock_printer.id = 1
        self.mock_printer.printer_type = 'escpos_tcp'

    def _setup_printer_browse(self, printer=None):
        """Configure mock for printer.browse()."""
        if printer is None:
            printer = self.mock_printer
        self.mock_env['pos.printer'].sudo.return_value.browse.return_value = printer

    @patch('pos_it_fiscal_nonfiscal_printer.controllers.hw_proxy.request')
    def test_printer_action_success(self, mock_request):
        """Test successful printer action."""
        mock_request.env = self.mock_env
        self._setup_printer_browse()

        # Mock driver
        mock_driver = MagicMock()
        mock_driver.handle_action.return_value = {'status': 'ok'}

        with patch('pos_it_fiscal_nonfiscal_printer.controllers.hw_proxy.get_driver',
                   return_value=mock_driver):
            from pos_it_fiscal_nonfiscal_printer.controllers.hw_proxy import HwProxyController

            controller = HwProxyController()
            result = controller.printer_action({
                'printer_id': 1,
                'action': 'print_receipt',
                'payload': {'text': 'Test'}
            })

        self.assertTrue(result['result'])
        self.assertEqual(result['driver_result']['status'], 'ok')

    @patch('pos_it_fiscal_nonfiscal_printer.controllers.hw_proxy.request')
    def test_printer_action_missing_printer_id(self, mock_request):
        """Test missing printer_id returns error."""
        mock_request.env = self.mock_env

        from pos_it_fiscal_nonfiscal_printer.controllers.hw_proxy import HwProxyController

        controller = HwProxyController()
        result = controller.printer_action({
            'action': 'print_receipt'
        })

        self.assertFalse(result['result'])
        self.assertEqual(result['error'], 'invalid_request')

    @patch('pos_it_fiscal_nonfiscal_printer.controllers.hw_proxy.request')
    def test_printer_action_missing_action(self, mock_request):
        """Test missing action returns error."""
        mock_request.env = self.mock_env

        from pos_it_fiscal_nonfiscal_printer.controllers.hw_proxy import HwProxyController

        controller = HwProxyController()
        result = controller.printer_action({
            'printer_id': 1
        })

        self.assertFalse(result['result'])
        self.assertEqual(result['error'], 'invalid_request')

    @patch('pos_it_fiscal_nonfiscal_printer.controllers.hw_proxy.request')
    def test_printer_action_printer_not_found(self, mock_request):
        """Test printer not found returns error."""
        mock_request.env = self.mock_env

        # Mock printer that doesn't exist
        mock_printer = MagicMock()
        mock_printer.exists.return_value = False
        self._setup_printer_browse(mock_printer)

        from pos_it_fiscal_nonfiscal_printer.controllers.hw_proxy import HwProxyController

        controller = HwProxyController()
        result = controller.printer_action({
            'printer_id': 999,
            'action': 'print_receipt'
        })

        self.assertFalse(result['result'])
        self.assertEqual(result['error'], 'printer_not_found')

    @patch('pos_it_fiscal_nonfiscal_printer.controllers.hw_proxy.request')
    def test_printer_action_access_denied(self, mock_request):
        """Test access denied for non-PoS users."""
        mock_request.env = self.mock_env
        self._setup_printer_browse()

        # Make user fail access checks
        self.mock_user._is_internal.return_value = False
        self.mock_user.has_group.return_value = False

        from pos_it_fiscal_nonfiscal_printer.controllers.hw_proxy import HwProxyController

        controller = HwProxyController()
        result = controller.printer_action({
            'printer_id': 1,
            'action': 'print_receipt'
        })

        self.assertFalse(result['result'])
        self.assertEqual(result['error'], 'access_denied')

    @patch('pos_it_fiscal_nonfiscal_printer.controllers.hw_proxy.request')
    def test_printer_action_driver_error(self, mock_request):
        """Test driver error handling."""
        mock_request.env = self.mock_env
        self._setup_printer_browse()

        # Mock driver that raises an exception
        mock_driver = MagicMock()
        mock_driver.handle_action.side_effect = Exception("Printer offline")

        with patch('pos_it_fiscal_nonfiscal_printer.controllers.hw_proxy.get_driver',
                   return_value=mock_driver):
            from pos_it_fiscal_nonfiscal_printer.controllers.hw_proxy import HwProxyController

            controller = HwProxyController()
            result = controller.printer_action({
                'printer_id': 1,
                'action': 'print_receipt',
                'payload': {}
            })

        self.assertFalse(result['result'])
        self.assertIn('Printer offline', result['error'])

    @patch('pos_it_fiscal_nonfiscal_printer.controllers.hw_proxy.request')
    def test_printer_action_unimplemented(self, mock_request):
        """Test unimplemented action handling."""
        mock_request.env = self.mock_env
        self._setup_printer_browse()

        # Mock driver that raises NotImplementedError
        mock_driver = MagicMock()
        mock_driver.handle_action.side_effect = NotImplementedError("unknown_action")

        with patch('pos_it_fiscal_nonfiscal_printer.controllers.hw_proxy.get_driver',
                   return_value=mock_driver):
            from pos_it_fiscal_nonfiscal_printer.controllers.hw_proxy import HwProxyController

            controller = HwProxyController()
            result = controller.printer_action({
                'printer_id': 1,
                'action': 'unknown_action',
                'payload': {}
            })

        self.assertFalse(result['result'])
        self.assertIn('unimplemented_action', result['error'])


if __name__ == '__main__':
    unittest.main()
