# -*- coding: utf-8 -*-
"""SF20-like fiscal printer driver over TCP.

This driver implements the SF20 fiscal protocol used by Italian fiscal printers.
It provides lifecycle methods for fiscal receipt operations:
- open_receipt: Start a new fiscal receipt
- sell_item: Add a sale line
- apply_payment: Register payment
- close_receipt: Finalize and print fiscal receipt
- status: Query printer status

Message framing uses STX/ETX with checksum.
"""

import logging
import socket
import struct

from .base import BaseDriver

_logger = logging.getLogger(__name__)

# Protocol constants
STX = 0x02  # Start of text
ETX = 0x03  # End of text
ACK = 0x06  # Acknowledgment
NAK = 0x15  # Negative acknowledgment

# Default connection settings
DEFAULT_PORT = 9100
DEFAULT_TIMEOUT = 10

# SF20 command codes (simplified subset)
CMD_OPEN_RECEIPT = 0x30      # '0' - Open fiscal receipt
CMD_SELL_ITEM = 0x31         # '1' - Sell item
CMD_SUBTOTAL = 0x32          # '2' - Subtotal
CMD_PAYMENT = 0x33           # '3' - Payment
CMD_CLOSE_RECEIPT = 0x34     # '4' - Close receipt
CMD_STATUS = 0x35            # '5' - Status query
CMD_CANCEL = 0x36            # '6' - Cancel/void


def _compute_checksum(data):
    """Compute XOR checksum of data bytes."""
    checksum = 0
    for byte in data:
        checksum ^= byte
    return checksum


def _frame_message(command, payload=b''):
    """Frame a message with STX, command, payload, checksum, ETX.

    Format: STX + CMD + PAYLOAD + CHECKSUM + ETX
    """
    message_body = bytes([command]) + payload
    checksum = _compute_checksum(message_body)
    return bytes([STX]) + message_body + bytes([checksum, ETX])


def _parse_response(data):
    """Parse a framed response.

    Returns:
        dict with 'success', 'command', 'payload', 'raw'
    """
    if len(data) < 4:
        return {'success': False, 'error': 'response_too_short', 'raw': data}

    if data[0] != STX or data[-1] != ETX:
        return {'success': False, 'error': 'invalid_framing', 'raw': data}

    command = data[1]
    payload = data[2:-2]
    received_checksum = data[-2]

    expected_checksum = _compute_checksum(data[1:-2])
    if received_checksum != expected_checksum:
        return {
            'success': False,
            'error': 'checksum_mismatch',
            'expected': expected_checksum,
            'received': received_checksum,
            'raw': data
        }

    return {
        'success': True,
        'command': command,
        'payload': payload,
        'raw': data
    }


class SF20Driver(BaseDriver):
    """Driver for SF20-like fiscal printers over TCP."""

    def __init__(self, printer=None, env=None, escpos_factory=None,
                 socket_factory=None, iot_proxy=None):
        super().__init__(
            printer=printer,
            env=env,
            escpos_factory=escpos_factory,
            socket_factory=socket_factory,
            iot_proxy=iot_proxy
        )
        # Use default socket factory if none provided
        if self.socket_factory is None:
            self.socket_factory = socket.socket

    def _get_connection_params(self):
        """Extract connection parameters from printer record."""
        host = getattr(self.printer, 'host', None) or '127.0.0.1'
        port = getattr(self.printer, 'port', None) or DEFAULT_PORT
        timeout = getattr(self.printer, 'timeout', None) or DEFAULT_TIMEOUT
        return host, int(port), int(timeout)

    def _send_command(self, command, payload=b''):
        """Send a command and receive response.

        Args:
            command: Command byte
            payload: Optional payload bytes

        Returns:
            dict with response data or error
        """
        host, port, timeout = self._get_connection_params()
        message = _frame_message(command, payload)

        sock = None
        try:
            sock = self.socket_factory(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            sock.connect((host, port))

            # Send message
            sock.sendall(message)
            _logger.debug("Sent SF20 command %02X to %s:%s", command, host, port)

            # Receive response (read until ETX or timeout)
            response = b''
            while True:
                chunk = sock.recv(256)
                if not chunk:
                    break
                response += chunk
                if ETX in chunk:
                    break

            return _parse_response(response)

        except socket.timeout:
            _logger.warning("SF20 timeout at %s:%s", host, port)
            return {
                'success': False,
                'error': 'timeout',
                'canRetry': True
            }
        except socket.error as e:
            _logger.warning("SF20 socket error at %s:%s - %s", host, port, e)
            return {
                'success': False,
                'error': f'socket_error: {e}',
                'canRetry': True
            }
        except Exception as e:
            _logger.exception("SF20 error")
            return {
                'success': False,
                'error': str(e),
                'canRetry': False
            }
        finally:
            if sock:
                try:
                    sock.close()
                except Exception:
                    pass

    def handle_action(self, action, payload):
        """Dispatch action to appropriate fiscal method."""
        action_map = {
            'print_receipt': self.print_receipt,
            'cashbox': self.open_cashbox,
            'open_receipt': self.open_receipt,
            'sell_item': self.sell_item,
            'apply_payment': self.apply_payment,
            'close_receipt': self.close_receipt,
            'status': self.status,
            'cancel_receipt': self.cancel_receipt,
        }

        handler = action_map.get(action)
        if handler:
            return handler(payload)
        raise NotImplementedError(f"Unknown action: {action}")

    def print_receipt(self, payload):
        """Print a complete fiscal receipt.

        This is a convenience method that performs the full fiscal cycle:
        open_receipt -> sell_item(s) -> apply_payment(s) -> close_receipt

        Args:
            payload: dict with 'lines' (list of items) and 'payments' (list of payments)

        Returns:
            dict with operation result
        """
        lines = payload.get('lines', [])
        payments = payload.get('payments', [])

        # Open receipt
        result = self.open_receipt({})
        if not result.get('success'):
            return {
                'status': 'error',
                'message': 'Failed to open receipt',
                'details': result
            }

        # Add items
        for line in lines:
            result = self.sell_item(line)
            if not result.get('success'):
                self.cancel_receipt({})
                return {
                    'status': 'error',
                    'message': f"Failed to add item: {line.get('description', 'unknown')}",
                    'details': result
                }

        # Apply payments
        for payment in payments:
            result = self.apply_payment(payment)
            if not result.get('success'):
                self.cancel_receipt({})
                return {
                    'status': 'error',
                    'message': 'Failed to apply payment',
                    'details': result
                }

        # Close receipt
        result = self.close_receipt({})
        if not result.get('success'):
            return {
                'status': 'error',
                'message': 'Failed to close receipt',
                'details': result
            }

        return {
            'status': 'ok',
            'message': 'Fiscal receipt printed',
            'details': result
        }

    def open_receipt(self, payload):
        """Open a new fiscal receipt.

        Args:
            payload: dict with optional 'operator_id'

        Returns:
            dict with 'success', 'receipt_number' (if available)
        """
        operator = payload.get('operator_id', 1)
        data = struct.pack('B', operator)

        result = self._send_command(CMD_OPEN_RECEIPT, data)
        if result.get('success'):
            return {
                'success': True,
                'message': 'Receipt opened',
                'receipt_number': result.get('payload', b'').decode('ascii', errors='ignore')
            }
        return result

    def sell_item(self, payload):
        """Add a sale item to the open receipt.

        Args:
            payload: dict with:
                - description: str (max 32 chars)
                - quantity: float (default 1.0)
                - price: float (unit price in cents)
                - department: int (fiscal department, default 1)
                - vat_rate: str (e.g., '22', '10', '4', '0')

        Returns:
            dict with operation result
        """
        description = payload.get('description', '')[:32].ljust(32)
        quantity = int(payload.get('quantity', 1) * 1000)  # Fixed point 3 decimals
        price = int(payload.get('price', 0) * 100)  # Cents
        department = payload.get('department', 1)
        vat_code = payload.get('vat_rate', '22')

        # Build payload: description(32) + quantity(4) + price(4) + dept(1) + vat(2)
        data = (
            description.encode('ascii', errors='replace') +
            struct.pack('>I', quantity) +
            struct.pack('>I', price) +
            struct.pack('B', department) +
            vat_code.encode('ascii')[:2].ljust(2)
        )

        result = self._send_command(CMD_SELL_ITEM, data)
        if result.get('success'):
            return {
                'success': True,
                'message': f"Item added: {description.strip()}"
            }
        return result

    def apply_payment(self, payload):
        """Apply payment to the receipt.

        Args:
            payload: dict with:
                - amount: float (payment amount in currency units)
                - method: str ('cash', 'card', 'check', etc.)

        Returns:
            dict with operation result
        """
        amount = int(payload.get('amount', 0) * 100)  # Cents
        method = payload.get('method', 'cash')

        # Payment type mapping
        payment_types = {
            'cash': 0,
            'card': 1,
            'check': 2,
            'ticket': 3,
            'other': 4
        }
        payment_code = payment_types.get(method, 0)

        data = struct.pack('>I', amount) + struct.pack('B', payment_code)

        result = self._send_command(CMD_PAYMENT, data)
        if result.get('success'):
            return {
                'success': True,
                'message': f"Payment applied: {amount/100:.2f} ({method})"
            }
        return result

    def close_receipt(self, payload):
        """Close and finalize the fiscal receipt.

        Returns:
            dict with 'success', 'fiscal_number', 'z_number'
        """
        result = self._send_command(CMD_CLOSE_RECEIPT)
        if result.get('success'):
            # Parse response payload for fiscal data
            resp_payload = result.get('payload', b'')
            return {
                'success': True,
                'message': 'Receipt closed',
                'fiscal_data': resp_payload.decode('ascii', errors='ignore')
            }
        return result

    def cancel_receipt(self, payload):
        """Cancel/void the current receipt."""
        result = self._send_command(CMD_CANCEL)
        if result.get('success'):
            return {
                'success': True,
                'message': 'Receipt cancelled'
            }
        return result

    def status(self, payload):
        """Query printer status.

        Returns:
            dict with printer status information
        """
        result = self._send_command(CMD_STATUS)
        if result.get('success'):
            resp_payload = result.get('payload', b'')
            return {
                'success': True,
                'status': 'ready',
                'raw_status': resp_payload.hex() if resp_payload else ''
            }
        return result

    def open_cashbox(self, payload):
        """Open cash drawer (if supported).

        Note: Not all fiscal printers support this command.
        """
        # Fiscal printers typically don't have a separate cashbox command
        # The drawer usually opens automatically on receipt close
        return {
            'result': True,
            'info': 'drawer_opens_on_receipt_close'
        }
