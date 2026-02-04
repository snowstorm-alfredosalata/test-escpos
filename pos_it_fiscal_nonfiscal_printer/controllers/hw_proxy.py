# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request


class HwProxyController(http.Controller):
    @http.route('/hw_proxy/printer_action', type='json', auth='user', methods=['POST'], csrf=False)
    def printer_action(self, data):
        """Minimal server-side proxy endpoint that delegates to a driver.

        Expects JSON payload: { printer_id: int, action: str, payload?: dict }
        Returns: { result: bool, driver_result?: dict, error?: str }
        """
        printer_id = data and data.get('printer_id')
        action = data and data.get('action')
        payload = (data and data.get('payload')) or {}

        if not printer_id or not action:
            return {'result': False, 'error': 'invalid_request'}

        printer = request.env['pos.printer'].sudo().browse(printer_id)
        if not printer.exists():
            return {'result': False, 'error': 'printer_not_found'}

        user = request.env.user
        # Basic access check: internal users or PoS users are allowed
        if not (user._is_internal() or user.has_group('point_of_sale.group_pos_user') or user.has_group('point_of_sale.group_pos_manager')):
            return {'result': False, 'error': 'access_denied'}

        # Lazy import to avoid circular imports
        try:
            from ..drivers import get_driver
        except Exception:
            return {'result': False, 'error': 'driver_registry_not_available'}

        try:
            driver = get_driver(printer, request.env)
        except Exception as e:
            return {'result': False, 'error': f'no_driver: {e}'}

        try:
            driver_result = driver.handle_action(action, payload)
            return {'result': True, 'driver_result': driver_result}
        except NotImplementedError as e:
            return {'result': False, 'error': f'unimplemented_action: {e}'}
        except Exception as e:
            return {'result': False, 'error': str(e)}
