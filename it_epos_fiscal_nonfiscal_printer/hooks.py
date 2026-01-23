# -*- coding: utf-8 -*-
"""
Integration hooks for POS order processing
Allows automatic printing to fiscal and non-fiscal printers

Usage:
    from .hooks import PosOrderHooks
    
    hooks = PosOrderHooks(env)
    hooks.on_order_completed(order)
"""

import logging
from datetime import datetime

_logger = logging.getLogger(__name__)


class PosOrderHooks:
    """
    Integration hooks for POS order lifecycle
    Handles automatic printing to fiscal and non-fiscal printers
    """

    def __init__(self, env):
        self.env = env

    def on_order_completed(self, order):
        """
        Called when POS order is completed (paid)
        Triggers fiscal and non-fiscal printing
        
        Args:
            order: POS Order object (or dict from POS UI)
        """
        try:
            # Get POS config
            pos_config = self._get_pos_config(order)
            if not pos_config:
                _logger.warning('POS config not found for order')
                return

            # Print fiscal receipt
            if pos_config.fiscal_printer_enabled:
                self._print_fiscal_receipt(pos_config, order)

            # Print comanda
            if pos_config.nonfiscal_printer_enabled:
                self._print_comanda(pos_config, order)

        except Exception as e:
            _logger.exception(f'Error in order completion hook: {str(e)}')

    def _print_fiscal_receipt(self, pos_config, order):
        """Print receipt to fiscal printer"""
        try:
            from .services.printer_factory import PrinterFactory
            
            fiscal_config = pos_config.get_fiscal_printer_config()
            if not fiscal_config:
                return

            printer = PrinterFactory.get_fiscal_printer(pos_config.id)
            if not printer:
                printer = PrinterFactory.create_fiscal_printer(
                    pos_config.id,
                    fiscal_config['ip'],
                    fiscal_config['port'],
                    fiscal_config['timeout']
                )

            if not printer.socket:
                success, msg = printer.connect()
                if not success:
                    _logger.error(f'Cannot connect to fiscal printer: {msg}')
                    return

            # Build receipt data
            receipt_data = self._build_receipt_data(order)

            # Process receipt
            success, msg = printer.open_receipt()
            if not success:
                _logger.error(f'Cannot open receipt: {msg}')
                return

            # Add items
            for item in receipt_data['items']:
                printer.add_item(
                    item['description'],
                    item['quantity'],
                    item['unit_price'],
                    item['tax_percent']
                )

            # Process payments
            for payment in receipt_data['payments']:
                printer.process_payment(payment['type'], payment['amount'])

            # Close receipt
            success, receipt_number = printer.close_receipt()
            if success:
                _logger.info(f'Fiscal receipt printed: {receipt_number}')
            else:
                _logger.error(f'Cannot close receipt: {receipt_number}')

        except Exception as e:
            _logger.exception(f'Error printing fiscal receipt: {str(e)}')

    def _print_comanda(self, pos_config, order):
        """Print comanda to non-fiscal printer"""
        try:
            from .services.printer_factory import PrinterFactory
            
            nonfiscal_config = pos_config.get_nonfiscal_printer_config()
            if not nonfiscal_config:
                return

            printer = PrinterFactory.get_nonfiscal_printer(pos_config.id)
            if not printer:
                printer = PrinterFactory.create_nonfiscal_printer(
                    pos_config.id,
                    nonfiscal_config['ip'],
                    nonfiscal_config['port'],
                    nonfiscal_config['timeout'],
                    nonfiscal_config['width']
                )

            if not printer.socket:
                success, msg = printer.connect()
                if not success:
                    _logger.warning(f'Cannot connect to non-fiscal printer: {msg}')
                    return

            # Build comanda data
            comanda_data = self._build_comanda_data(order, pos_config)

            # Print comanda
            success, msg = printer.print_comanda(
                comanda_data,
                nonfiscal_config.get('auto_cut', False),
                nonfiscal_config.get('auto_open_drawer', False)
            )

            if success:
                _logger.info(f'Comanda printed for order {order.get("name", "?")}')
            else:
                _logger.warning(f'Comanda print failed: {msg}')

        except Exception as e:
            _logger.exception(f'Error printing comanda: {str(e)}')

    def on_session_close(self, session):
        """
        Called when POS session closes
        Executes Z report if needed
        
        Args:
            session: POS Session object
        """
        try:
            pos_config = session.config_id
            
            if not pos_config.fiscal_printer_enabled:
                return

            from .services.printer_factory import PrinterFactory
            
            fiscal_config = pos_config.get_fiscal_printer_config()
            printer = PrinterFactory.get_fiscal_printer(pos_config.id)
            
            if not printer:
                printer = PrinterFactory.create_fiscal_printer(
                    pos_config.id,
                    fiscal_config['ip'],
                    fiscal_config['port'],
                    fiscal_config['timeout']
                )

            if not printer.socket:
                success, msg = printer.connect()
                if not success:
                    _logger.warning(f'Cannot connect to printer for Z report: {msg}')
                    return

            # Execute Z report
            success, msg = printer.execute_z_report()
            if success:
                session.fiscal_z_report_printed = True
                session.fiscal_z_report_timestamp = datetime.now()
                _logger.info('Z report executed successfully')
            else:
                _logger.error(f'Z report execution failed: {msg}')

        except Exception as e:
            _logger.exception(f'Error executing Z report: {str(e)}')

    # ========================================================================
    # HELPER METHODS
    # ========================================================================

    def _get_pos_config(self, order):
        """Get POS config from order"""
        if isinstance(order, dict):
            session_id = order.get('session_id')
            if session_id:
                session = self.env['pos.session'].browse(session_id)
                return session.config_id
        else:
            # Assume order object from backend
            if hasattr(order, 'session_id'):
                return order.session_id.config_id
        return None

    def _build_receipt_data(self, order):
        """Build fiscal receipt data from POS order"""
        receipt_data = {
            'items': [],
            'payments': [],
        }

        if isinstance(order, dict):
            # From POS frontend
            for item in order.get('items', []):
                receipt_data['items'].append({
                    'description': item.get('name', 'ITEM')[:40],
                    'quantity': float(item.get('quantity', 1)),
                    'unit_price': float(item.get('price', 0)),
                    'tax_percent': float(item.get('tax', 0)),
                })

            for payment in order.get('payments', []):
                receipt_data['payments'].append({
                    'type': payment.get('type', 'cash'),
                    'amount': float(payment.get('amount', 0)),
                })
        else:
            # From backend Order object
            if hasattr(order, 'lines'):
                for line in order.lines:
                    receipt_data['items'].append({
                        'description': line.product_id.name[:40],
                        'quantity': line.qty,
                        'unit_price': line.price_unit,
                        'tax_percent': sum(tax.amount for tax in line.tax_id),
                    })

            if hasattr(order, 'payment_ids'):
                for payment in order.payment_ids:
                    receipt_data['payments'].append({
                        'type': self._map_payment_type(payment.payment_method_id.name),
                        'amount': payment.amount,
                    })

        return receipt_data

    def _build_comanda_data(self, order, pos_config):
        """Build comanda data from POS order"""
        comanda_data = {
            'order_number': '',
            'table': '',
            'timestamp': datetime.now().strftime('%H:%M:%S'),
            'items': [],
            'header': 'COMANDA',
            'footer': 'Grazie',
        }

        if isinstance(order, dict):
            comanda_data['order_number'] = order.get('name', 'ORD-???')
            comanda_data['table'] = order.get('table', 'No Table')

            for item in order.get('items', []):
                comanda_data['items'].append({
                    'description': item.get('name', 'ITEM'),
                    'quantity': float(item.get('quantity', 1)),
                    'notes': item.get('notes', ''),
                })
        else:
            comanda_data['order_number'] = order.name
            if hasattr(order, 'table_id'):
                comanda_data['table'] = order.table_id.name

            if hasattr(order, 'lines'):
                for line in order.lines:
                    comanda_data['items'].append({
                        'description': line.product_id.name,
                        'quantity': line.qty,
                        'notes': line.note or '',
                    })

        return comanda_data

    def _map_payment_type(self, method_name):
        """Map payment method name to type"""
        name_lower = (method_name or '').lower()
        if 'card' in name_lower or 'carta' in name_lower:
            return 'card'
        if 'check' in name_lower or 'assegno' in name_lower:
            return 'check'
        return 'cash'
