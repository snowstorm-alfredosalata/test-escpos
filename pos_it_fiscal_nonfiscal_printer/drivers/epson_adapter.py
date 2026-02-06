# -*- coding: utf-8 -*-
"""Epson ePOS adapter driver.

This driver acts as an adapter to existing Epson ePOS functionality,
delegating either to:
1. Direct ePOS XML requests to the printer's HTTP endpoint
2. IoT device RPC if configured

The ePOS protocol is XML-based and sent to the printer's web service at:
  http://<printer_ip>/cgi-bin/epos/service.cgi?devid=local_printer
"""

import base64
import logging
import socket
import urllib.request
import urllib.error

from .base import BaseDriver

_logger = logging.getLogger(__name__)

# ePOS endpoint path
EPOS_PATH = '/cgi-bin/epos/service.cgi?devid=local_printer&timeout=60000'

# ePOS XML templates
EPOS_PRINT_IMAGE_TEMPLATE = '''<?xml version="1.0" encoding="utf-8"?>
<s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/">
  <s:Body>
    <epos-print xmlns="http://www.epson-pos.com/schemas/2011/03/epos-print">
      <image width="{width}" height="{height}" color="color_1" mode="mono">{data}</image>
      <cut type="feed"/>
    </epos-print>
  </s:Body>
</s:Envelope>'''

EPOS_PRINT_TEXT_TEMPLATE = '''<?xml version="1.0" encoding="utf-8"?>
<s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/">
  <s:Body>
    <epos-print xmlns="http://www.epson-pos.com/schemas/2011/03/epos-print">
      <text>{text}</text>
      <feed unit="24"/>
      <cut type="feed"/>
    </epos-print>
  </s:Body>
</s:Envelope>'''

EPOS_DRAWER_TEMPLATE = '''<?xml version="1.0" encoding="utf-8"?>
<s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/">
  <s:Body>
    <epos-print xmlns="http://www.epson-pos.com/schemas/2011/03/epos-print">
      <pulse drawer="drawer_1" time="pulse_100"/>
    </epos-print>
  </s:Body>
</s:Envelope>'''

DEFAULT_TIMEOUT = 10


class EpsonAdapter(BaseDriver):
    """Adapter driver for Epson ePOS printers."""

    def __init__(self, printer=None, env=None, escpos_factory=None,
                 socket_factory=None, iot_proxy=None, http_client=None):
        super().__init__(
            printer=printer,
            env=env,
            escpos_factory=escpos_factory,
            socket_factory=socket_factory,
            iot_proxy=iot_proxy
        )
        # Allow DI of HTTP client for testing
        self._http_client = http_client

    def _get_printer_url(self):
        """Get the printer's ePOS endpoint URL."""
        # Try epson_printer_ip first (standard Odoo field)
        ip = getattr(self.printer, 'epson_printer_ip', None)
        if not ip or ip == '0.0.0.0':
            # Fall back to host field
            ip = getattr(self.printer, 'host', None)
        if not ip:
            ip = '127.0.0.1'

        # Handle serial number to domain conversion (from point_of_sale)
        if '.' not in ip:
            # This is a serial number, convert to Epson domain
            try:
                from odoo.addons.point_of_sale.models.pos_printer import format_epson_certified_domain
                ip = format_epson_certified_domain(ip)
            except ImportError:
                pass

        return f'https://{ip}{EPOS_PATH}'

    def _should_use_iot(self):
        """Check if we should delegate to IoT Box."""
        return getattr(self.printer, 'use_iot_device', False) and self.iot_proxy

    def _send_epos_request(self, xml_body):
        """Send ePOS XML request to printer.

        Args:
            xml_body: ePOS XML string

        Returns:
            dict with 'success', 'response', 'error'
        """
        url = self._get_printer_url()
        timeout = getattr(self.printer, 'timeout', DEFAULT_TIMEOUT) or DEFAULT_TIMEOUT

        headers = {
            'Content-Type': 'text/xml; charset=utf-8',
            'SOAPAction': '""'
        }

        try:
            if self._http_client:
                # Use injected client for testing
                response = self._http_client(url, xml_body.encode('utf-8'), headers, timeout)
            else:
                # Use standard urllib
                request = urllib.request.Request(
                    url,
                    data=xml_body.encode('utf-8'),
                    headers=headers,
                    method='POST'
                )
                # Note: In production, SSL context should verify certificates
                import ssl
                ctx = ssl.create_default_context()
                ctx.check_hostname = False
                ctx.verify_mode = ssl.CERT_NONE

                with urllib.request.urlopen(request, timeout=timeout, context=ctx) as response:
                    response_body = response.read().decode('utf-8')

            return {
                'success': True,
                'response': response_body if 'response_body' in dir() else response
            }

        except urllib.error.HTTPError as e:
            _logger.warning("ePOS HTTP error: %s", e)
            return {
                'success': False,
                'error': f'http_error: {e.code}',
                'canRetry': e.code >= 500
            }
        except urllib.error.URLError as e:
            _logger.warning("ePOS URL error: %s", e)
            return {
                'success': False,
                'error': f'url_error: {e.reason}',
                'canRetry': True
            }
        except socket.timeout:
            _logger.warning("ePOS timeout")
            return {
                'success': False,
                'error': 'timeout',
                'canRetry': True
            }
        except Exception as e:
            _logger.exception("ePOS error")
            return {
                'success': False,
                'error': str(e),
                'canRetry': False
            }

    def print_receipt(self, payload):
        """Print a receipt via ePOS.

        Args:
            payload: dict with 'receipt' (base64 image) or 'text'

        Returns:
            dict with operation result
        """
        if self._should_use_iot():
            return self._print_via_iot(payload)

        # Determine content type and build ePOS XML
        if isinstance(payload, dict):
            if 'receipt' in payload:
                return self._print_image(payload['receipt'])
            elif 'text' in payload:
                return self._print_text(payload['text'])

        # Default: treat as text
        return self._print_text(str(payload))

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

    def _print_image(self, image_data):
        """Print base64-encoded image via ePOS."""
        # Remove data URL prefix if present
        if ',' in image_data:
            image_data = image_data.split(',', 1)[1]

        # For ePOS, we need image dimensions
        # Default to reasonable receipt width (576 pixels typical for 80mm)
        # Height will be determined by image content
        width = 576
        height = 0  # Will be auto-calculated by printer

        try:
            # Try to get actual dimensions using PIL
            import io
            from PIL import Image
            image_bytes = base64.b64decode(image_data)
            img = Image.open(io.BytesIO(image_bytes))
            width, height = img.size
        except ImportError:
            _logger.debug("PIL not available, using default dimensions")
        except Exception as e:
            _logger.debug("Could not determine image dimensions: %s", e)

        xml = EPOS_PRINT_IMAGE_TEMPLATE.format(
            width=width,
            height=height,
            data=image_data
        )

        result = self._send_epos_request(xml)
        if result.get('success'):
            return {
                'status': 'ok',
                'message': 'Image printed via ePOS'
            }
        return {
            'status': 'error',
            'message': result.get('error', 'Unknown error'),
            'canRetry': result.get('canRetry', False)
        }

    def _print_text(self, text):
        """Print plain text via ePOS."""
        # Escape XML special characters
        import html
        escaped_text = html.escape(text)

        xml = EPOS_PRINT_TEXT_TEMPLATE.format(text=escaped_text)

        result = self._send_epos_request(xml)
        if result.get('success'):
            return {
                'status': 'ok',
                'message': 'Text printed via ePOS'
            }
        return {
            'status': 'error',
            'message': result.get('error', 'Unknown error'),
            'canRetry': result.get('canRetry', False)
        }

    def open_cashbox(self, payload):
        """Open cash drawer via ePOS pulse command."""
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

        result = self._send_epos_request(EPOS_DRAWER_TEMPLATE)
        if result.get('success'):
            return {
                'result': True,
                'info': 'drawer_opened_epos'
            }
        return {
            'result': False,
            'info': result.get('error', 'unknown_error')
        }
