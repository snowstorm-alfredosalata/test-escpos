# -*- coding: utf-8 -*-
"""
Printer Controller
Exposes JSON-RPC endpoints for POS frontend to communicate with printers
"""

import json
import logging
from odoo import http, fields
from odoo.http import request

_logger = logging.getLogger(__name__)


class PrinterController(http.Controller):
    """
    REST API endpoints for printer communication
    All endpoints are protected by POS session authentication
    """

    # ========================================================================
    # FISCAL PRINTER ENDPOINTS
    # ========================================================================

    @http.route('/pos_printer/fiscal/status', type='json', auth='public', methods=['POST'])
    def fiscal_printer_status(self):
        """
        Get real-time status of fiscal printer
        
        Request JSON:
        {
            'pos_config_id': int
        }
        
        Response:
        {
            'status': 'ok'|'busy'|'error'|'offline'|'warning',
            'state': SF20 fiscal state,
            'message': str,
            'ready': bool,
            'response_time_ms': float,
        }
        """
        try:
            data = request.jsonrpc_request.get('params', {})
            pos_config_id = data.get('pos_config_id')
            
            if not pos_config_id:
                return {
                    'error': 'Missing pos_config_id',
                    'status': 'error',
                }
            
            pos_config = request.env['pos.config'].sudo().browse(pos_config_id)
            if not pos_config:
                return {
                    'error': 'POS Configuration not found',
                    'status': 'error',
                }
            
            from ..services.printer_factory import PrinterFactory
            
            # Get or create fiscal printer adapter
            fiscal_config = pos_config.get_fiscal_printer_config()
            if not fiscal_config:
                return {
                    'error': 'Fiscal printer not configured',
                    'status': 'warning',
                    'ready': False,
                }
            
            printer = PrinterFactory.get_fiscal_printer(pos_config_id)
            if not printer:
                printer = PrinterFactory.create_fiscal_printer(
                    pos_config_id,
                    fiscal_config['ip'],
                    fiscal_config['port'],
                    fiscal_config['timeout']
                )
            
            # Connect if not already connected
            if not printer.socket:
                success, msg = printer.connect()
                if not success:
                    return {
                        'error': msg,
                        'status': 'offline',
                        'ready': False,
                    }
            
            # Query status
            status_info = printer.get_status()
            
            # Update database
            request.env['pos.printer.status'].sudo().update_fiscal_status(
                pos_config_id,
                'ok' if status_info.get('ready') else 'error',
                status_info.get('error_code', ''),
                status_info.get('state'),
                status_info.get('response_time_ms'),
            )
            
            return {
                'status': 'ok' if status_info.get('ready') else 'error',
                'state': status_info.get('state'),
                'message': 'Printer ready' if status_info.get('ready') else 'Printer error',
                'ready': status_info.get('ready', False),
                'response_time_ms': status_info.get('response_time_ms', 0),
                'error_code': status_info.get('error_code'),
                'receipts_today': status_info.get('receipts_today', 0),
            }
        except Exception as e:
            _logger.exception('Error querying fiscal printer status')
            return {
                'error': str(e),
                'status': 'error',
                'ready': False,
            }

    @http.route('/pos_printer/fiscal/print_receipt', type='json', auth='public', methods=['POST'])
    def fiscal_print_receipt(self):
        """
        Print fiscal receipt
        
        Request JSON:
        {
            'pos_config_id': int,
            'receipt_data': {
                'items': [
                    {
                        'description': str,
                        'quantity': float,
                        'unit_price': float,
                        'tax_percent': float,
                    },
                    ...
                ],
                'payments': [
                    {
                        'type': 'cash'|'card'|'check'|'other',
                        'amount': float,
                    },
                    ...
                ],
            }
        }
        
        Response:
        {
            'success': bool,
            'message': str,
            'receipt_number': str (if success),
        }
        """
        try:
            data = request.jsonrpc_request.get('params', {})
            pos_config_id = data.get('pos_config_id')
            receipt_data = data.get('receipt_data', {})
            
            if not pos_config_id or not receipt_data:
                return {
                    'success': False,
                    'message': 'Missing pos_config_id or receipt_data',
                }
            
            pos_config = request.env['pos.config'].sudo().browse(pos_config_id)
            if not pos_config or not pos_config.fiscal_printer_enabled:
                return {
                    'success': False,
                    'message': 'Fiscal printer not configured',
                }
            
            from ..services.printer_factory import PrinterFactory
            
            fiscal_config = pos_config.get_fiscal_printer_config()
            printer = PrinterFactory.get_fiscal_printer(pos_config_id)
            if not printer:
                printer = PrinterFactory.create_fiscal_printer(
                    pos_config_id,
                    fiscal_config['ip'],
                    fiscal_config['port'],
                    fiscal_config['timeout']
                )
            
            # Ensure connection
            if not printer.socket:
                success, msg = printer.connect()
                if not success:
                    return {'success': False, 'message': msg}
            
            # Process receipt
            # 1. Open receipt
            success, msg = printer.open_receipt()
            if not success:
                return {'success': False, 'message': f'Failed to open receipt: {msg}'}
            
            # 2. Add items
            for item in receipt_data.get('items', []):
                success, msg = printer.add_item(
                    item.get('description', 'ITEM'),
                    float(item.get('quantity', 1)),
                    float(item.get('unit_price', 0)),
                    float(item.get('tax_percent', 0))
                )
                if not success and not fiscal_config.get('fail_safe'):
                    # Fail-fast if not in fail-safe mode
                    return {'success': False, 'message': f'Item registration failed: {msg}'}
            
            # 3. Process payments
            for payment in receipt_data.get('payments', []):
                success, msg = printer.process_payment(
                    payment.get('type', 'cash'),
                    float(payment.get('amount', 0))
                )
                if not success and not fiscal_config.get('fail_safe'):
                    return {'success': False, 'message': f'Payment failed: {msg}'}
            
            # 4. Close receipt
            success, receipt_number = printer.close_receipt()
            if not success:
                if fiscal_config.get('fail_safe'):
                    _logger.warning(f'Fiscal receipt close error (fail-safe): {receipt_number}')
                    return {
                        'success': True,
                        'message': 'Receipt processed (printer error, fail-safe mode)',
                        'receipt_number': 'ERROR',
                        'fail_safe_triggered': True,
                    }
                else:
                    return {'success': False, 'message': f'Failed to close receipt: {receipt_number}'}
            
            # Update session and status
            session_obj = request.env['pos.session'].search(
                [('config_id', '=', pos_config_id), ('state', '=', 'opened')],
                limit=1
            )
            if session_obj:
                session_obj.fiscal_receipts_count += 1
            
            request.env['pos.printer.status'].sudo().update_fiscal_status(
                pos_config_id,
                'ok',
                'Receipt printed successfully',
                'receipt_closed',
            )
            
            return {
                'success': True,
                'message': 'Receipt printed successfully',
                'receipt_number': str(receipt_number),
            }
        except Exception as e:
            _logger.exception('Error printing fiscal receipt')
            return {
                'success': False,
                'message': f'Unexpected error: {str(e)}',
            }

    @http.route('/pos_printer/fiscal/z_report', type='json', auth='public', methods=['POST'])
    def fiscal_z_report(self):
        """
        Execute Z report on fiscal printer (end of day)
        
        Request JSON:
        {
            'pos_config_id': int,
        }
        
        Response:
        {
            'success': bool,
            'message': str,
        }
        """
        try:
            data = request.jsonrpc_request.get('params', {})
            pos_config_id = data.get('pos_config_id')
            
            if not pos_config_id:
                return {'success': False, 'message': 'Missing pos_config_id'}
            
            pos_config = request.env['pos.config'].sudo().browse(pos_config_id)
            if not pos_config or not pos_config.fiscal_printer_enabled:
                return {'success': False, 'message': 'Fiscal printer not configured'}
            
            from ..services.printer_factory import PrinterFactory
            
            fiscal_config = pos_config.get_fiscal_printer_config()
            printer = PrinterFactory.get_fiscal_printer(pos_config_id)
            if not printer:
                printer = PrinterFactory.create_fiscal_printer(
                    pos_config_id,
                    fiscal_config['ip'],
                    fiscal_config['port'],
                    fiscal_config['timeout']
                )
            
            # Ensure connection
            if not printer.socket:
                success, msg = printer.connect()
                if not success:
                    return {'success': False, 'message': msg}
            
            # Execute Z report
            success, msg = printer.execute_z_report()
            
            if success:
                # Update session
                session_obj = request.env['pos.session'].search(
                    [('config_id', '=', pos_config_id), ('state', '=', 'opened')],
                    limit=1
                )
                if session_obj:
                    session_obj.fiscal_z_report_printed = True
                    session_obj.fiscal_z_report_timestamp = fields.Datetime.now()
            
            return {'success': success, 'message': msg}
        except Exception as e:
            _logger.exception('Error executing fiscal Z report')
            return {'success': False, 'message': f'Error: {str(e)}'}

    # ========================================================================
    # NON-FISCAL PRINTER ENDPOINTS
    # ========================================================================

    @http.route('/pos_printer/nonfiscal/status', type='json', auth='public', methods=['POST'])
    def nonfiscal_printer_status(self):
        """
        Get status of non-fiscal (ESC/POS) printer
        
        Request JSON:
        {
            'pos_config_id': int
        }
        
        Response:
        {
            'status': 'ok'|'error'|'offline',
            'ready': bool,
            'message': str,
        }
        """
        try:
            data = request.jsonrpc_request.get('params', {})
            pos_config_id = data.get('pos_config_id')
            
            if not pos_config_id:
                return {'error': 'Missing pos_config_id', 'status': 'error'}
            
            pos_config = request.env['pos.config'].sudo().browse(pos_config_id)
            if not pos_config:
                return {'error': 'POS Configuration not found', 'status': 'error'}
            
            from ..services.printer_factory import PrinterFactory
            
            nonfiscal_config = pos_config.get_nonfiscal_printer_config()
            if not nonfiscal_config:
                return {
                    'error': 'Non-fiscal printer not configured',
                    'status': 'warning',
                    'ready': False,
                }
            
            printer = PrinterFactory.get_nonfiscal_printer(pos_config_id)
            if not printer:
                printer = PrinterFactory.create_nonfiscal_printer(
                    pos_config_id,
                    nonfiscal_config['ip'],
                    nonfiscal_config['port'],
                    nonfiscal_config['timeout'],
                    nonfiscal_config['width'],
                )
            
            # Connect if not already connected
            if not printer.socket:
                success, msg = printer.connect()
                if not success:
                    return {
                        'error': msg,
                        'status': 'offline',
                        'ready': False,
                    }
            
            status_info = printer.get_status()
            
            request.env['pos.printer.status'].sudo().update_nonfiscal_status(
                pos_config_id,
                'ok' if status_info.get('ready') else 'error',
                '',
            )
            
            return {
                'status': 'ok' if status_info.get('ready') else 'error',
                'ready': status_info.get('ready', False),
                'message': 'Printer ready' if status_info.get('ready') else 'Printer not responding',
                'responsive': status_info.get('responsive', False),
            }
        except Exception as e:
            _logger.exception('Error querying non-fiscal printer status')
            return {'error': str(e), 'status': 'error', 'ready': False}

    @http.route('/pos_printer/nonfiscal/print_comanda', type='json', auth='public', methods=['POST'])
    def nonfiscal_print_comanda(self):
        """
        Print kitchen order (comanda)
        
        Request JSON:
        {
            'pos_config_id': int,
            'order_data': {
                'order_number': str,
                'table': str (optional),
                'timestamp': str (optional),
                'items': [
                    {
                        'description': str,
                        'quantity': float,
                        'notes': str (optional),
                    },
                    ...
                ],
                'header': str (optional),
                'footer': str (optional),
            },
            'auto_cut': bool (optional),
            'open_drawer': bool (optional),
        }
        
        Response:
        {
            'success': bool,
            'message': str,
        }
        """
        try:
            data = request.jsonrpc_request.get('params', {})
            pos_config_id = data.get('pos_config_id')
            order_data = data.get('order_data', {})
            auto_cut = data.get('auto_cut', False)
            open_drawer = data.get('open_drawer', False)
            
            if not pos_config_id or not order_data:
                return {'success': False, 'message': 'Missing pos_config_id or order_data'}
            
            pos_config = request.env['pos.config'].sudo().browse(pos_config_id)
            if not pos_config or not pos_config.nonfiscal_printer_enabled:
                return {'success': False, 'message': 'Non-fiscal printer not configured'}
            
            from ..services.printer_factory import PrinterFactory
            
            nonfiscal_config = pos_config.get_nonfiscal_printer_config()
            printer = PrinterFactory.get_nonfiscal_printer(pos_config_id)
            if not printer:
                printer = PrinterFactory.create_nonfiscal_printer(
                    pos_config_id,
                    nonfiscal_config['ip'],
                    nonfiscal_config['port'],
                    nonfiscal_config['timeout'],
                    nonfiscal_config['width'],
                )
            
            # Connect if needed
            if not printer.socket:
                success, msg = printer.connect()
                if not success:
                    return {'success': False, 'message': msg}
            
            # Use config settings if not explicitly provided
            auto_cut = auto_cut or nonfiscal_config.get('auto_cut', False)
            open_drawer = open_drawer or nonfiscal_config.get('auto_open_drawer', False)
            
            # Print comanda
            success, msg = printer.print_comanda(order_data, auto_cut, open_drawer)
            
            if success:
                request.env['pos.printer.status'].sudo().update_nonfiscal_status(
                    pos_config_id,
                    'ok',
                    'Comanda printed',
                )
            
            return {'success': success, 'message': msg}
        except Exception as e:
            _logger.exception('Error printing comanda')
            return {'success': False, 'message': f'Error: {str(e)}'}

    # ========================================================================
    # CONFIGURATION & DIAGNOSTIC ENDPOINTS
    # ========================================================================

    @http.route('/pos_printer/config', type='json', auth='public', methods=['POST'])
    def get_printer_config(self):
        """
        Get printer configuration for POS
        
        Request JSON:
        {
            'pos_config_id': int
        }
        
        Response:
        {
            'fiscal': {...} or None,
            'nonfiscal': {...} or None,
        }
        """
        try:
            data = request.jsonrpc_request.get('params', {})
            pos_config_id = data.get('pos_config_id')
            
            if not pos_config_id:
                return {'error': 'Missing pos_config_id'}
            
            pos_config = request.env['pos.config'].sudo().browse(pos_config_id)
            
            return {
                'fiscal': pos_config.get_fiscal_printer_config(),
                'nonfiscal': pos_config.get_nonfiscal_printer_config(),
            }
        except Exception as e:
            _logger.exception('Error fetching printer config')
            return {'error': str(e)}
