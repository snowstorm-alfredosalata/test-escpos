# -*- coding: utf-8 -*-
"""Extension to pos.printer for additional printer types and connection settings."""

from odoo import api, fields, models


class PosPrinter(models.Model):
    _inherit = 'pos.printer'

    # Extend printer_type selection to include our driver types
    printer_type = fields.Selection(
        selection_add=[
            ('escpos_tcp', 'ESC/POS over TCP'),
            ('sf20_tcp', 'SF20 Fiscal Printer'),
        ],
        ondelete={
            'escpos_tcp': 'set default',
            'sf20_tcp': 'set default',
        }
    )

    # IoT device delegation
    use_iot_device = fields.Boolean(
        string='Use IoT Device',
        default=False,
        help='Delegate printing to an IoT Box device instead of direct connection'
    )
    iot_device_id = fields.Many2one(
        'iot.device',
        string='IoT Device',
        help='IoT device to use for printing (requires IoT Box module)',
        ondelete='set null'
    )

    # Direct TCP connection settings
    host = fields.Char(
        string='Host',
        help='IP address or hostname for direct TCP connection',
        default='127.0.0.1'
    )
    port = fields.Integer(
        string='Port',
        help='TCP port number (default: 9100 for ESC/POS, varies for fiscal)',
        default=9100
    )
    timeout = fields.Integer(
        string='Timeout (seconds)',
        help='Connection timeout in seconds',
        default=10
    )

    @api.model
    def _load_pos_data_fields(self, config):
        """Extend fields loaded for PoS client."""
        fields_list = super()._load_pos_data_fields(config)
        # Add our custom fields
        fields_list.extend([
            'use_iot_device',
            'iot_device_id',
            'host',
            'port',
            'timeout',
        ])
        return fields_list

    @api.onchange('printer_type')
    def _onchange_printer_type_defaults(self):
        """Set sensible defaults based on printer type."""
        for record in self:
            if record.printer_type == 'escpos_tcp':
                if not record.port or record.port == 9100:
                    record.port = 9100
            elif record.printer_type == 'sf20_tcp':
                if not record.port or record.port == 9100:
                    # SF20 fiscal printers often use different ports
                    record.port = 9100
            elif record.printer_type == 'epson_epos':
                # Epson ePOS uses HTTP, port doesn't apply the same way
                pass
