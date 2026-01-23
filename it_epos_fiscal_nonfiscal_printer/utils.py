#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Utility scripts for printer module testing and diagnostics
"""

import socket
import time
import sys


def test_printer_connection(ip, port, timeout=5):
    """
    Test connection to a printer via TCP
    
    Args:
        ip: Printer IP address
        port: TCP port
        timeout: Connection timeout in seconds
    
    Returns:
        (success: bool, message: str, response_time: float)
    """
    try:
        start_time = time.time()
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        sock.connect((ip, port))
        response_time = time.time() - start_time
        sock.close()
        
        return True, f'✓ Connected in {response_time:.2f}s', response_time
    except socket.timeout:
        return False, '✗ Connection timeout', timeout
    except socket.error as e:
        return False, f'✗ Connection error: {str(e)}', 0
    except Exception as e:
        return False, f'✗ Unexpected error: {str(e)}', 0


def test_sf20_printer(ip, port=9100):
    """
    Test SF20 fiscal printer communication
    
    Args:
        ip: Printer IP address
        port: TCP port (default 9100)
    """
    print(f'\n=== Testing SF20 Fiscal Printer ===')
    print(f'IP: {ip}:{port}')
    
    # Test connection
    success, msg, time = test_printer_connection(ip, port)
    print(f'Connection: {msg}')
    
    if not success:
        print('Cannot proceed without connection')
        return False
    
    # Try to send SF20 status command
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((ip, port))
        
        # Send initialization
        print('Sending initialization...')
        sock.sendall(b'\x1B@')
        
        # Send status command
        print('Requesting status...')
        sock.sendall(b'\x1B\x1B\x6E\x04')
        
        # Try to receive response
        sock.settimeout(2)
        response = sock.recv(1024)
        print(f'Response received: {response[:50]}')
        
        sock.close()
        return True
    except Exception as e:
        print(f'Error: {str(e)}')
        return False


def test_escpos_printer(ip, port=9100):
    """
    Test ESC/POS non-fiscal printer communication
    
    Args:
        ip: Printer IP address
        port: TCP port (default 9100)
    """
    print(f'\n=== Testing ESC/POS Non-Fiscal Printer ===')
    print(f'IP: {ip}:{port}')
    
    # Test connection
    success, msg, time = test_printer_connection(ip, port)
    print(f'Connection: {msg}')
    
    if not success:
        print('Cannot proceed without connection')
        return False
    
    # Try to send ESC/POS commands
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((ip, port))
        
        # Send initialization
        print('Sending initialization...')
        sock.sendall(b'\x1B@')
        
        # Send test print
        print('Sending test print...')
        sock.sendall(b'\x1B!\x00')  # Normal size
        sock.sendall(b'TEST PRINTER\n')
        sock.sendall(b'\x1B@')  # Cut paper
        
        sock.close()
        print('✓ Test print sent successfully')
        return True
    except Exception as e:
        print(f'Error: {str(e)}')
        return False


def main():
    """Command-line utility"""
    if len(sys.argv) < 2:
        print('Usage:')
        print('  python -m it_epos_fiscal_nonfiscal_printer.utils test_sf20 <ip> [port]')
        print('  python -m it_epos_fiscal_nonfiscal_printer.utils test_escpos <ip> [port]')
        print('')
        print('Example:')
        print('  python -m it_epos_fiscal_nonfiscal_printer.utils test_sf20 192.168.1.100 9100')
        return
    
    command = sys.argv[1]
    ip = sys.argv[2] if len(sys.argv) > 2 else None
    port = int(sys.argv[3]) if len(sys.argv) > 3 else 9100
    
    if not ip:
        print('Error: IP address required')
        return
    
    if command == 'test_sf20':
        test_sf20_printer(ip, port)
    elif command == 'test_escpos':
        test_escpos_printer(ip, port)
    else:
        print(f'Unknown command: {command}')


if __name__ == '__main__':
    main()
