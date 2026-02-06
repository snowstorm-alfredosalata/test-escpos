# -*- coding: utf-8 -*-
"""ESC/POS driver for network printers over TCP.

This driver supports two modes:
1. Direct mode: Uses escpos.printer.Network to connect directly to the printer
2. IoT proxy mode: Forwards print jobs to an IoT Box endpoint

The driver accepts dependency injection for testing:
- escpos_factory: callable that creates an escpos.printer.Network instance
- iot_proxy: callable to forward requests to IoT Box
"""

import base64
import logging
import socket

from .base import BaseDriver

_logger = logging.getLogger(__name__)

# Default ESC/POS port
DEFAULT_PORT = 9100
DEFAULT_TIMEOUT = 10


def _default_escpos_factory(host, port, timeout):
    """Default factory using python-escpos library."""
    try:
        from escpos.printer import Network
        return Network(host, port, timeout=timeout)
    except ImportError:
        raise ImportError(
            "python-escpos is required for ESC/POS printing. "
            "Install with: pip install python-escpos"
        )


class EscposTCPDriver(BaseDriver):
    """Driver for ESC/POS printers over TCP/IP network."""

    def __init__(self, printer=None, env=None, escpos_factory=None,
                 socket_factory=None, iot_proxy=None):
        super().__init__(
            printer=printer,
            env=env,
            escpos_factory=escpos_factory,
            socket_factory=socket_factory,
            iot_proxy=iot_proxy
        )
        # Use default factory if none provided
        if self.escpos_factory is None:
            self.escpos_factory = _default_escpos_factory

    def _get_connection_params(self):
        """Extract connection parameters from printer record."""
        host = getattr(self.printer, 'host', None) or '127.0.0.1'
        port = getattr(self.printer, 'port', None) or DEFAULT_PORT
        timeout = getattr(self.printer, 'timeout', None) or DEFAULT_TIMEOUT
        return host, int(port), int(timeout)

    def _should_use_iot(self):
        """Check if we should delegate to IoT Box."""
        return getattr(self.printer, 'use_iot_device', False) and self.iot_proxy

    def print_receipt(self, payload):
        """Print a receipt.

        Args:
            payload: dict with 'receipt' key containing base64 encoded image
                    or 'text' key containing plain text to print

        Returns:
            dict with 'status' ('ok' or 'error'), 'message', and optional 'details'
        """
        if self._should_use_iot():
            return self._print_via_iot(payload)
        return self._print_direct(payload)

    def _print_via_iot(self, payload):
        """Forward print job to IoT Box."""
        try:
            result = self.iot_proxy(
                action='print_receipt',
                printer_id=self.printer.id if self.printer else None,
                payload=payload
            )
            return {
                'status': 'ok' if result.get('result') else 'error',
                'message': result.get('message', 'Printed via IoT'),
                'details': result
            }
        except Exception as e:
            _logger.exception("IoT proxy error")
            return {
                'status': 'error',
                'message': f'IoT proxy error: {e}',
                'canRetry': True
            }

    def _print_direct(self, payload):
        """Print directly to network printer using ESC/POS."""
        host, port, timeout = self._get_connection_params()

        try:
            printer = self.escpos_factory(host, port, timeout)
        except ImportError as e:
            return {
                'status': 'error',
                'message': str(e),
                'canRetry': False
            }
        except Exception as e:
            _logger.exception("Failed to create printer connection")
            return {
                'status': 'error',
                'message': f'Connection failed: {e}',
                'canRetry': True
            }

        try:
            # Handle different payload types
            if isinstance(payload, dict):
                if 'receipt' in payload:
                    # Base64 encoded image
                    self._print_image(printer, payload['receipt'])
                elif 'text' in payload:
                    # Plain text
                    printer.text(payload['text'])
                elif 'raw' in payload:
                    # Raw bytes (base64 encoded)
                    raw_bytes = base64.b64decode(payload['raw'])
                    printer._raw(raw_bytes)
                else:
                    # Assume it's text content
                    printer.text(str(payload))
            else:
                printer.text(str(payload))

            # Cut paper
            printer.cut()

            return {
                'status': 'ok',
                'message': 'Receipt printed successfully',
                'details': {'host': host, 'port': port}
            }

        except socket.timeout:
            _logger.warning("Printer timeout at %s:%s", host, port)
            return {
                'status': 'error',
                'message': 'Printer timeout',
                'canRetry': True
            }
        except socket.error as e:
            _logger.warning("Socket error printing to %s:%s - %s", host, port, e)
            return {
                'status': 'error',
                'message': f'Network error: {e}',
                'canRetry': True
            }
        except Exception as e:
            _logger.exception("Print error")
            return {
                'status': 'error',
                'message': f'Print failed: {e}',
                'canRetry': True
            }
        finally:
            try:
                printer.close()
            except Exception:
                pass

    def _print_image(self, printer, image_data):
        """Print a base64-encoded image."""
        import io

        # Decode base64 image
        if ',' in image_data:
            # Handle data URL format (data:image/png;base64,...)
            image_data = image_data.split(',', 1)[1]

        image_bytes = base64.b64decode(image_data)

        # Use PIL to process the image
        try:
            from PIL import Image
            image = Image.open(io.BytesIO(image_bytes))
            printer.image(image)
        except ImportError:
            # Fallback: try to print as raw if PIL not available
            _logger.warning("PIL not available, attempting raw image print")
            printer._raw(image_bytes)

    def open_cashbox(self, payload):
        """Open the cash drawer.

        Args:
            payload: optional dict with drawer settings

        Returns:
            dict with operation result
        """
        if self._should_use_iot():
            try:
                result = self.iot_proxy(
                    action='cashbox',
                    printer_id=self.printer.id if self.printer else None,
                    payload=payload
                )
                return {
                    'result': result.get('result', False),
                    'info': 'via_iot'
                }
            except Exception as e:
                return {
                    'result': False,
                    'info': f'iot_error: {e}'
                }

        host, port, timeout = self._get_connection_params()

        try:
            printer = self.escpos_factory(host, port, timeout)
        except Exception as e:
            return {
                'result': False,
                'info': f'connection_failed: {e}'
            }

        try:
            # ESC/POS drawer kick command
            # Default: pin 2, on time 120ms, off time 240ms
            printer.cashdraw(2)
            return {
                'result': True,
                'info': 'drawer_opened'
            }
        except Exception as e:
            _logger.exception("Cashbox open error")
            return {
                'result': False,
                'info': f'drawer_error: {e}'
            }
        finally:
            try:
                printer.close()
            except Exception:
                pass
