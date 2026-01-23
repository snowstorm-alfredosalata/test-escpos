# -*- coding: utf-8 -*-
"""
ESC/POS Non-Fiscal Printer Service
Handles communication with ESC/POS printers for kitchen/bar orders (comande)
"""

import logging
import socket
import time
from typing import List, Tuple, Optional

_logger = logging.getLogger(__name__)


class ESCPOSPrinterAdapter:
    """
    Adapter for ESC/POS non-fiscal printer
    
    Used for printing kitchen orders (comande) and other non-fiscal documents.
    Communication via TCP/IP using ESC/POS protocol (text-based).
    
    This adapter handles:
    - Connection management
    - Status checking
    - Document formatting and layout
    - Printing with line breaks and paper cuts
    - Drawer pulse (if supported)
    """

    # ESC/POS PROTOCOL CONSTANTS
    ESC = b'\x1B'
    GS = b'\x1D'
    CR = b'\x0D'
    LF = b'\x0A'
    CRLF = CR + LF

    # Common ESC/POS Commands
    CMD_INIT = ESC + b'@'              # Initialize printer
    CMD_CUT = GS + b'V' + b'\x00'      # Full cut
    CMD_PARTIAL_CUT = GS + b'V' + b'\x01'  # Partial cut
    CMD_OPEN_DRAWER = ESC + b'p' + b'\x00\x19\x19'  # Open cash drawer
    CMD_ALIGN_LEFT = ESC + b'a\x00'    # Align left
    CMD_ALIGN_CENTER = ESC + b'a\x01'  # Align center
    CMD_ALIGN_RIGHT = ESC + b'a\x02'   # Align right
    CMD_BOLD_ON = ESC + b'E\x01'       # Bold on
    CMD_BOLD_OFF = ESC + b'E\x00'      # Bold off
    CMD_SIZE_NORMAL = ESC + b'!\x00'   # Normal size
    CMD_SIZE_DOUBLE_W = ESC + b'!\x20' # Double width
    CMD_SIZE_DOUBLE_H = ESC + b'!\x10' # Double height
    CMD_SIZE_DOUBLE = ESC + b'!\x30'   # Double width + height
    CMD_UNDERLINE_ON = ESC + b'-\x01'  # Underline on
    CMD_UNDERLINE_OFF = ESC + b'-\x00' # Underline off

    def __init__(self, ip: str, port: int, timeout: int = 10, width: int = 32):
        """
        Initialize ESC/POS adapter
        
        Args:
            ip: IP address of printer
            port: TCP port (default 9100)
            timeout: Socket timeout in seconds
            width: Printer width in characters (typically 32 or 40)
        """
        self.ip = ip
        self.port = port
        self.timeout = timeout
        self.width = width
        self.socket = None
        self.is_ready = False

    def connect(self) -> Tuple[bool, str]:
        """
        Establish connection to ESC/POS printer
        
        Returns:
            Tuple (success: bool, message: str)
        """
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(self.timeout)
            self.socket.connect((self.ip, self.port))
            
            # Send initialization
            self._send_raw(self.CMD_INIT)
            self.is_ready = True
            
            _logger.info(f'Connected to ESC/POS printer at {self.ip}:{self.port}')
            return True, 'Connected successfully'
        except socket.timeout:
            msg = f'Connection timeout to ESC/POS at {self.ip}:{self.port}'
            _logger.error(msg)
            return False, msg
        except socket.error as e:
            msg = f'Connection error to ESC/POS: {str(e)}'
            _logger.error(msg)
            return False, msg
        except Exception as e:
            msg = f'Unexpected error connecting to ESC/POS: {str(e)}'
            _logger.error(msg)
            return False, msg

    def disconnect(self) -> None:
        """Close connection to printer"""
        if self.socket:
            try:
                self.socket.close()
                self.is_ready = False
                _logger.info('Disconnected from ESC/POS printer')
            except Exception as e:
                _logger.warning(f'Error disconnecting from ESC/POS: {str(e)}')
            finally:
                self.socket = None

    def get_status(self) -> dict:
        """
        Check printer connection status
        
        Returns:
            Dict with status information
        """
        status = {
            'ready': self.socket is not None and self.is_ready,
            'connected': self.socket is not None,
            'ip': self.ip,
            'port': self.port,
            'width': self.width,
        }
        
        # Try a simple command to verify responsiveness
        try:
            if self.socket and self.is_ready:
                self._send_raw(self.CMD_INIT)
                status['responsive'] = True
            else:
                status['responsive'] = False
        except Exception:
            status['responsive'] = False
        
        return status

    def print_comanda(self, order_data: dict, auto_cut: bool = False, 
                     open_drawer: bool = False) -> Tuple[bool, str]:
        """
        Print kitchen order (comanda)
        
        Args:
            order_data: Dictionary with order details:
                {
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
                }
            auto_cut: Whether to cut paper after printing
            open_drawer: Whether to open cash drawer after printing
        
        Returns:
            Tuple (success: bool, message: str)
        """
        try:
            if not self.socket or not self.is_ready:
                return False, 'Printer not connected'
            
            # Build comanda document
            document = self._build_comanda_document(order_data)
            
            # Send to printer
            self._send_raw(document)
            
            # Optional: cut paper
            if auto_cut:
                self._send_raw(self.CMD_PARTIAL_CUT)
            
            # Optional: open drawer
            if open_drawer:
                self._send_raw(self.CMD_OPEN_DRAWER)
            
            _logger.info(f'Comanda printed: Order #{order_data.get("order_number", "?")}')
            return True, 'Comanda printed successfully'
        except Exception as e:
            msg = f'Error printing comanda: {str(e)}'
            _logger.error(msg)
            return False, msg

    def print_text(self, text: str, align: str = 'left', bold: bool = False,
                  underline: bool = False) -> Tuple[bool, str]:
        """
        Print simple text
        
        Args:
            text: Text to print
            align: 'left', 'center', 'right'
            bold: Whether to use bold
            underline: Whether to use underline
        
        Returns:
            Tuple (success: bool, message: str)
        """
        try:
            if not self.socket or not self.is_ready:
                return False, 'Printer not connected'
            
            document = b''
            
            # Alignment
            if align == 'center':
                document += self.CMD_ALIGN_CENTER
            elif align == 'right':
                document += self.CMD_ALIGN_RIGHT
            else:
                document += self.CMD_ALIGN_LEFT
            
            # Formatting
            if bold:
                document += self.CMD_BOLD_ON
            if underline:
                document += self.CMD_UNDERLINE_ON
            
            # Text
            document += text.encode('utf-8', errors='ignore') + self.LF
            
            # Reset formatting
            if bold:
                document += self.CMD_BOLD_OFF
            if underline:
                document += self.CMD_UNDERLINE_OFF
            
            self._send_raw(document)
            return True, 'Text printed'
        except Exception as e:
            msg = f'Error printing text: {str(e)}'
            _logger.error(msg)
            return False, msg

    def cut_paper(self, partial: bool = True) -> Tuple[bool, str]:
        """
        Cut paper
        
        Args:
            partial: True for partial cut, False for full cut
        
        Returns:
            Tuple (success: bool, message: str)
        """
        try:
            if not self.socket or not self.is_ready:
                return False, 'Printer not connected'
            
            cmd = self.CMD_PARTIAL_CUT if partial else self.CMD_CUT
            self._send_raw(cmd)
            return True, 'Paper cut'
        except Exception as e:
            msg = f'Error cutting paper: {str(e)}'
            _logger.error(msg)
            return False, msg

    def open_drawer(self) -> Tuple[bool, str]:
        """
        Open cash drawer
        
        Returns:
            Tuple (success: bool, message: str)
        """
        try:
            if not self.socket or not self.is_ready:
                return False, 'Printer not connected'
            
            self._send_raw(self.CMD_OPEN_DRAWER)
            return True, 'Drawer pulse sent'
        except Exception as e:
            msg = f'Error opening drawer: {str(e)}'
            _logger.error(msg)
            return False, msg

    def line_feed(self, lines: int = 1) -> Tuple[bool, str]:
        """Feed paper with line breaks"""
        try:
            if not self.socket or not self.is_ready:
                return False, 'Printer not connected'
            
            self._send_raw(self.LF * lines)
            return True, f'Fed {lines} lines'
        except Exception as e:
            msg = f'Error feeding paper: {str(e)}'
            _logger.error(msg)
            return False, msg

    # ========================================================================
    # INTERNAL / HELPER METHODS
    # ========================================================================

    def _send_raw(self, data: bytes) -> None:
        """Send raw bytes to socket"""
        if not self.socket:
            raise Exception('Not connected to printer')
        try:
            self.socket.sendall(data)
        except socket.timeout:
            raise Exception('Socket timeout')
        except socket.error as e:
            raise Exception(f'Socket error: {str(e)}')

    def _build_comanda_document(self, order_data: dict) -> bytes:
        """
        Build a complete comanda document in ESC/POS format
        
        Layout:
        ├── Header (optional)
        ├── Separator
        ├── Order number + Table + Time
        ├── Separator
        ├── Items with quantities and notes
        ├── Separator
        ├── Footer (optional)
        └── Blank lines
        """
        document = b''
        
        # Initialize printer
        document += self.CMD_INIT
        document += self.CMD_ALIGN_CENTER
        
        # Header
        header = order_data.get('header', 'COMANDA')
        document += self.CMD_SIZE_DOUBLE
        document += self.CMD_BOLD_ON
        document += header.encode('utf-8', errors='ignore') + self.LF
        document += self.CMD_BOLD_OFF
        document += self.CMD_SIZE_NORMAL
        
        # Separator
        document += self._separator_line().encode('utf-8') + self.LF
        
        # Order info
        document += self.CMD_ALIGN_LEFT
        order_num = order_data.get('order_number', '???')
        document += f'Order: {order_num}'.encode('utf-8') + self.LF
        
        table = order_data.get('table')
        if table:
            document += f'Table: {table}'.encode('utf-8') + self.LF
        
        timestamp = order_data.get('timestamp')
        if timestamp:
            document += f'Time: {timestamp}'.encode('utf-8') + self.LF
        
        # Separator
        document += self._separator_line().encode('utf-8') + self.LF
        
        # Items
        document += self.CMD_BOLD_ON
        items_header = 'Items'.ljust(self.width)
        document += items_header.encode('utf-8')[:self.width] + self.LF
        document += self.CMD_BOLD_OFF
        
        for item in order_data.get('items', []):
            qty = item.get('quantity', 1)
            desc = item.get('description', 'ITEM')
            notes = item.get('notes', '')
            
            # Item line: "Qty × Description"
            qty_str = f'{qty:.0f}x'
            item_text = f'{qty_str} {desc}'
            document += item_text.encode('utf-8', errors='ignore')[:self.width] + self.LF
            
            # Notes if present
            if notes:
                notes_indent = f'  {notes}'
                document += notes_indent.encode('utf-8', errors='ignore')[:self.width] + self.LF
        
        # Separator
        document += self._separator_line().encode('utf-8') + self.LF
        
        # Footer
        footer = order_data.get('footer')
        if footer:
            document += self.CMD_ALIGN_CENTER
            document += footer.encode('utf-8', errors='ignore') + self.LF
        
        # Blank lines for tear
        document += self.LF * 3
        
        return document

    def _separator_line(self) -> str:
        """Generate separator line based on printer width"""
        return '-' * self.width
