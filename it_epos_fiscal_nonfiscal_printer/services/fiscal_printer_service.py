# -*- coding: utf-8 -*-
"""
SF20 Fiscal Printer Service
Handles communication with Protocollo Fiscale SF20 (HYDRA) fiscal printers
"""

import logging
import socket
import time
from typing import Dict, Optional, Tuple

_logger = logging.getLogger(__name__)


class SF20FiscalPrinterAdapter:
    """
    Adapter for SF20 fiscal printer (Protocollo Fiscale HYDRA)
    
    This adapter handles:
    - Connection and disconnection
    - Status checking
    - Receipt lifecycle (open/close)
    - Item entry and payment processing
    - Z report execution (end of day)
    
    SF20 communicates via TCP/IP with a specific binary protocol.
    This implementation provides a high-level interface abstracting protocol details.
    """

    # SF20 PROTOCOL CONSTANTS
    SF20_HEADER = b'\x1B\x40'  # ESC @ - Initialize
    SF20_EOT = b'\x04'          # End of Transmission marker
    SF20_CMD_STATUS = b'\x1B\x6E'  # Request status
    SF20_CMD_RECEIPT_OPEN = b'\x1B\x47'  # Open receipt
    SF20_CMD_RECEIPT_CLOSE = b'\x1B\x43'  # Close receipt
    SF20_CMD_ITEM = b'\x1B\x4A'  # Register item
    SF20_CMD_PAYMENT = b'\x1B\x50'  # Process payment
    SF20_CMD_Z_REPORT = b'\x1B\x5A'  # Z report (end of day)

    # SF20 STATES (State Machine)
    STATE_INIT = 'init'
    STATE_RECEIPT_OPEN = 'receipt_open'
    STATE_RECEIPT_CLOSED = 'receipt_closed'
    STATE_Z_REQUIRED = 'z_report_required'
    STATE_MEMORY_FULL = 'memory_full'
    STATE_ERROR = 'error'

    def __init__(self, ip: str, port: int, timeout: int = 30):
        """
        Initialize SF20 adapter
        
        Args:
            ip: IP address of fiscal printer
            port: TCP port (default 9100)
            timeout: Socket timeout in seconds
        """
        self.ip = ip
        self.port = port
        self.timeout = timeout
        self.socket = None
        self.current_state = self.STATE_INIT
        self._last_response_time = 0

    def connect(self) -> Tuple[bool, str]:
        """
        Establish connection to fiscal printer
        
        Returns:
            Tuple (success: bool, message: str)
        """
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(self.timeout)
            self.socket.connect((self.ip, self.port))
            
            _logger.info(f'Connected to SF20 fiscal printer at {self.ip}:{self.port}')
            self._send_initialization()
            return True, 'Connected successfully'
        except socket.timeout:
            msg = f'Connection timeout to SF20 at {self.ip}:{self.port}'
            _logger.error(msg)
            return False, msg
        except socket.error as e:
            msg = f'Connection error to SF20: {str(e)}'
            _logger.error(msg)
            return False, msg
        except Exception as e:
            msg = f'Unexpected error connecting to SF20: {str(e)}'
            _logger.error(msg)
            return False, msg

    def disconnect(self) -> None:
        """Close connection to fiscal printer"""
        if self.socket:
            try:
                self.socket.close()
                _logger.info('Disconnected from SF20 fiscal printer')
            except Exception as e:
                _logger.warning(f'Error disconnecting from SF20: {str(e)}')
            finally:
                self.socket = None

    def get_status(self) -> Dict:
        """
        Query printer status
        
        Returns:
            Dict with status information:
            {
                'state': SF20 fiscal state,
                'ready': bool,
                'error_code': str or None,
                'receipts_today': int,
                'response_time_ms': float,
            }
        """
        try:
            start_time = time.time()
            response = self._send_command(self.SF20_CMD_STATUS)
            response_time = (time.time() - start_time) * 1000
            
            status_dict = self._parse_status_response(response)
            status_dict['response_time_ms'] = response_time
            
            return status_dict
        except Exception as e:
            _logger.error(f'Error getting SF20 status: {str(e)}')
            return {
                'state': self.STATE_ERROR,
                'ready': False,
                'error_code': str(e),
                'receipts_today': 0,
                'response_time_ms': 0,
            }

    def open_receipt(self) -> Tuple[bool, str]:
        """
        Open a new fiscal receipt
        
        Returns:
            Tuple (success: bool, message: str)
        """
        try:
            if self.current_state == self.STATE_RECEIPT_OPEN:
                return False, 'Receipt already open'
            
            response = self._send_command(self.SF20_CMD_RECEIPT_OPEN)
            
            if self._is_success_response(response):
                self.current_state = self.STATE_RECEIPT_OPEN
                _logger.info('SF20 receipt opened')
                return True, 'Receipt opened'
            else:
                error_msg = self._parse_error_response(response)
                return False, f'Failed to open receipt: {error_msg}'
        except Exception as e:
            msg = f'Error opening receipt on SF20: {str(e)}'
            _logger.error(msg)
            return False, msg

    def add_item(self, description: str, quantity: float, unit_price: float, 
                 tax_percent: float) -> Tuple[bool, str]:
        """
        Register item in open receipt
        
        Args:
            description: Item description (max 40 chars, trimmed)
            quantity: Quantity (decimal)
            unit_price: Price per unit (in euros)
            tax_percent: Tax percentage (e.g., 22 for 22% VAT)
        
        Returns:
            Tuple (success: bool, message: str)
        """
        try:
            if self.current_state != self.STATE_RECEIPT_OPEN:
                return False, 'No receipt open'
            
            # Build item command
            description = description[:40]  # SF20 limitation
            quantity_cents = int(quantity * 100)
            price_cents = int(unit_price * 100)
            tax_int = int(tax_percent)
            
            item_data = self._encode_item(description, quantity_cents, price_cents, tax_int)
            response = self._send_command(self.SF20_CMD_ITEM, item_data)
            
            if self._is_success_response(response):
                _logger.info(f'SF20 item added: {description} x {quantity}')
                return True, 'Item registered'
            else:
                error_msg = self._parse_error_response(response)
                return False, f'Failed to register item: {error_msg}'
        except Exception as e:
            msg = f'Error adding item to SF20: {str(e)}'
            _logger.error(msg)
            return False, msg

    def process_payment(self, payment_type: str, amount: float) -> Tuple[bool, str]:
        """
        Process payment (must be called before closing receipt)
        
        Args:
            payment_type: Type of payment ('cash', 'card', 'check', 'other')
            amount: Amount in euros
        
        Returns:
            Tuple (success: bool, message: str)
        """
        try:
            if self.current_state != self.STATE_RECEIPT_OPEN:
                return False, 'No receipt open'
            
            amount_cents = int(amount * 100)
            payment_code = self._encode_payment_type(payment_type)
            payment_data = self._encode_payment(payment_code, amount_cents)
            
            response = self._send_command(self.SF20_CMD_PAYMENT, payment_data)
            
            if self._is_success_response(response):
                _logger.info(f'SF20 payment processed: {payment_type} {amount}€')
                return True, 'Payment processed'
            else:
                error_msg = self._parse_error_response(response)
                return False, f'Failed to process payment: {error_msg}'
        except Exception as e:
            msg = f'Error processing payment on SF20: {str(e)}'
            _logger.error(msg)
            return False, msg

    def close_receipt(self) -> Tuple[bool, str]:
        """
        Close current receipt
        
        Returns:
            Tuple (success: bool, message: str or receipt_number: str)
        """
        try:
            if self.current_state != self.STATE_RECEIPT_OPEN:
                return False, 'No receipt open'
            
            response = self._send_command(self.SF20_CMD_RECEIPT_CLOSE)
            
            if self._is_success_response(response):
                receipt_number = self._parse_receipt_number(response)
                self.current_state = self.STATE_RECEIPT_CLOSED
                _logger.info(f'SF20 receipt closed. Number: {receipt_number}')
                return True, receipt_number
            else:
                error_msg = self._parse_error_response(response)
                return False, f'Failed to close receipt: {error_msg}'
        except Exception as e:
            msg = f'Error closing receipt on SF20: {str(e)}'
            _logger.error(msg)
            return False, msg

    def execute_z_report(self) -> Tuple[bool, str]:
        """
        Execute Z report (end of day report)
        Only possible when no receipt is open.
        
        Returns:
            Tuple (success: bool, message: str)
        """
        try:
            if self.current_state == self.STATE_RECEIPT_OPEN:
                return False, 'Cannot execute Z report while receipt is open'
            
            response = self._send_command(self.SF20_CMD_Z_REPORT)
            
            if self._is_success_response(response):
                _logger.info('SF20 Z report executed')
                return True, 'Z report executed successfully'
            else:
                error_msg = self._parse_error_response(response)
                return False, f'Z report execution failed: {error_msg}'
        except Exception as e:
            msg = f'Error executing Z report on SF20: {str(e)}'
            _logger.error(msg)
            return False, msg

    # ========================================================================
    # INTERNAL / HELPER METHODS
    # ========================================================================

    def _send_initialization(self) -> None:
        """Send initialization sequence to printer"""
        try:
            self._send_raw(self.SF20_HEADER)
        except Exception as e:
            _logger.warning(f'Error sending initialization to SF20: {str(e)}')

    def _send_command(self, command: bytes, data: bytes = b'') -> bytes:
        """
        Send command to printer and receive response
        
        Args:
            command: Command bytes
            data: Optional command data
        
        Returns:
            Response bytes
        
        Raises:
            Exception if communication fails
        """
        if not self.socket:
            raise Exception('Not connected to fiscal printer')
        
        # Build full command: HEADER + COMMAND + DATA + EOT
        full_command = self.SF20_HEADER + command + data + self.SF20_EOT
        
        try:
            self._send_raw(full_command)
            response = self._receive_response()
            return response
        except socket.timeout:
            raise Exception(f'Timeout waiting for response')
        except socket.error as e:
            raise Exception(f'Communication error: {str(e)}')

    def _send_raw(self, data: bytes) -> None:
        """Send raw bytes to socket"""
        self.socket.sendall(data)

    def _receive_response(self) -> bytes:
        """Receive response from socket"""
        response = b''
        while True:
            chunk = self.socket.recv(4096)
            if not chunk:
                break
            response += chunk
            # Check for end-of-transmission marker
            if self.SF20_EOT in response:
                break
        return response

    def _is_success_response(self, response: bytes) -> bool:
        """Check if response indicates success"""
        # SF20 typically responds with OK/ACK markers
        return response and (b'OK' in response or b'\x06' in response)

    def _parse_error_response(self, response: bytes) -> str:
        """Extract error message from response"""
        try:
            if b'ERROR' in response:
                idx = response.find(b'ERROR')
                return response[idx:idx+50].decode('utf-8', errors='ignore')
            return 'Unknown error'
        except Exception:
            return 'Parse error'

    def _parse_status_response(self, response: bytes) -> Dict:
        """
        Parse status response from SF20
        Returns dict with printer state and information
        """
        # This is a simplified parser. Real implementation depends on SF20 protocol
        status_dict = {
            'state': self.STATE_INIT,
            'ready': False,
            'error_code': None,
            'receipts_today': 0,
        }
        
        try:
            if b'READY' in response:
                status_dict['state'] = self.STATE_RECEIPT_CLOSED
                status_dict['ready'] = True
            elif b'RECEIPT_OPEN' in response:
                status_dict['state'] = self.STATE_RECEIPT_OPEN
                status_dict['ready'] = True
            elif b'Z_REQUIRED' in response:
                status_dict['state'] = self.STATE_Z_REQUIRED
                status_dict['ready'] = False
            elif b'MEMORY_FULL' in response:
                status_dict['state'] = self.STATE_MEMORY_FULL
                status_dict['ready'] = False
            elif b'ERROR' in response:
                status_dict['state'] = self.STATE_ERROR
                status_dict['ready'] = False
                status_dict['error_code'] = self._parse_error_response(response)
        except Exception as e:
            _logger.warning(f'Error parsing SF20 status: {str(e)}')
        
        return status_dict

    def _parse_receipt_number(self, response: bytes) -> str:
        """Extract receipt number from response"""
        try:
            # Simplified: look for number pattern in response
            import re
            match = re.search(rb'(\d{1,10})', response)
            if match:
                return match.group(1).decode('utf-8')
            return 'UNKNOWN'
        except Exception:
            return 'UNKNOWN'

    def _encode_item(self, description: str, qty_cents: int, price_cents: int, 
                     tax_int: int) -> bytes:
        """Encode item data for SF20 protocol"""
        # Simplified encoding - real implementation depends on SF20 spec
        data = description.encode('utf-8')[:40]
        return data

    def _encode_payment_type(self, payment_type: str) -> int:
        """Convert payment type to SF20 code"""
        mapping = {
            'cash': 0x01,
            'card': 0x02,
            'check': 0x03,
            'other': 0x04,
        }
        return mapping.get(payment_type.lower(), 0x01)

    def _encode_payment(self, payment_code: int, amount_cents: int) -> bytes:
        """Encode payment data for SF20 protocol"""
        # Simplified - real implementation depends on SF20 spec
        return bytes([payment_code]) + amount_cents.to_bytes(4, byteorder='big')
