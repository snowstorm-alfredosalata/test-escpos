# -*- coding: utf-8 -*-
"""
POS Configuration Extension
Extends pos.config to store fiscal and non-fiscal printer settings
"""

from odoo import models, fields, api
from odoo.exceptions import ValidationError


class PosConfig(models.Model):
    _inherit = 'pos.config'

    # ============================================================
    # FISCAL PRINTER (SF20 - HYDRA) Configuration
    # ============================================================
    
    fiscal_printer_enabled = fields.Boolean(
        'Enable Fiscal Printer',
        default=False,
        help='Enable integration with SF20 fiscal printer'
    )

    fiscal_printer_ip = fields.Char(
        'Fiscal Printer IP Address',
        size=15,
        help='IP address of SF20 fiscal printer (e.g., 192.168.1.100)',
        required=False
    )

    fiscal_printer_port = fields.Integer(
        'Fiscal Printer Port',
        default=9100,
        help='TCP port for SF20 fiscal printer communication (default: 9100)',
        required=False
    )

    fiscal_printer_timeout = fields.Integer(
        'Fiscal Printer Timeout (seconds)',
        default=30,
        help='Communication timeout for fiscal printer requests',
        required=False
    )

    # ============================================================
    # NON-FISCAL PRINTER (ESC/POS) Configuration
    # ============================================================

    nonfiscal_printer_enabled = fields.Boolean(
        'Enable Non-Fiscal Printer',
        default=False,
        help='Enable integration with ESC/POS non-fiscal printer for comande'
    )

    nonfiscal_printer_ip = fields.Char(
        'Non-Fiscal Printer IP Address',
        size=15,
        help='IP address of ESC/POS printer (e.g., 192.168.1.101)',
        required=False
    )

    nonfiscal_printer_port = fields.Integer(
        'Non-Fiscal Printer Port',
        default=9100,
        help='TCP port for ESC/POS printer communication (default: 9100)',
        required=False
    )

    nonfiscal_printer_timeout = fields.Integer(
        'Non-Fiscal Printer Timeout (seconds)',
        default=10,
        help='Communication timeout for non-fiscal printer requests',
        required=False
    )

    # ============================================================
    # COMANDA PRINTING Configuration
    # ============================================================

    comanda_printer_width = fields.Integer(
        'Comanda Printer Width (chars)',
        default=32,
        help='Width of printer output in characters for comande layout'
    )

    comanda_auto_cut = fields.Boolean(
        'Auto Cut After Comanda',
        default=False,
        help='Automatically cut paper after printing each comanda'
    )

    comanda_auto_open_drawer = fields.Boolean(
        'Open Cash Drawer After Order',
        default=False,
        help='Automatically trigger cash drawer opening after comanda printing'
    )

    # ============================================================
    # ERROR HANDLING
    # ============================================================

    fiscal_error_fail_safe = fields.Boolean(
        'Fail Safe Mode',
        default=True,
        help='If True, fiscal printing errors do NOT block the sale (clear notification shown)'
    )

    # ============================================================
    # VALIDATION & CONSTRAINTS
    # ============================================================

    @api.constrains('fiscal_printer_ip')
    def _check_fiscal_printer_ip(self):
        """Validate fiscal printer IP format if enabled"""
        for record in self:
            if record.fiscal_printer_enabled and record.fiscal_printer_ip:
                if not self._is_valid_ip(record.fiscal_printer_ip):
                    raise ValidationError(
                        f'Invalid Fiscal Printer IP address: {record.fiscal_printer_ip}'
                    )

    @api.constrains('nonfiscal_printer_ip')
    def _check_nonfiscal_printer_ip(self):
        """Validate non-fiscal printer IP format if enabled"""
        for record in self:
            if record.nonfiscal_printer_enabled and record.nonfiscal_printer_ip:
                if not self._is_valid_ip(record.nonfiscal_printer_ip):
                    raise ValidationError(
                        f'Invalid Non-Fiscal Printer IP address: {record.nonfiscal_printer_ip}'
                    )

    @api.constrains('fiscal_printer_port')
    def _check_fiscal_printer_port(self):
        """Validate fiscal printer port range"""
        for record in self:
            if record.fiscal_printer_enabled and record.fiscal_printer_port:
                if not (1 <= record.fiscal_printer_port <= 65535):
                    raise ValidationError(
                        f'Fiscal Printer port must be between 1 and 65535: {record.fiscal_printer_port}'
                    )

    @api.constrains('nonfiscal_printer_port')
    def _check_nonfiscal_printer_port(self):
        """Validate non-fiscal printer port range"""
        for record in self:
            if record.nonfiscal_printer_enabled and record.nonfiscal_printer_port:
                if not (1 <= record.nonfiscal_printer_port <= 65535):
                    raise ValidationError(
                        f'Non-Fiscal Printer port must be between 1 and 65535: {record.nonfiscal_printer_port}'
                    )

    @staticmethod
    def _is_valid_ip(ip_str):
        """Simple IP validation (IPv4)"""
        parts = ip_str.split('.')
        if len(parts) != 4:
            return False
        try:
            for part in parts:
                num = int(part)
                if num < 0 or num > 255:
                    return False
            return True
        except (ValueError, TypeError):
            return False

    # ============================================================
    # HELPER METHODS
    # ============================================================

    def get_fiscal_printer_config(self):
        """Get fiscal printer configuration as dict"""
        if not self.fiscal_printer_enabled:
            return None
        
        return {
            'enabled': True,
            'ip': self.fiscal_printer_ip,
            'port': self.fiscal_printer_port,
            'timeout': self.fiscal_printer_timeout,
            'fail_safe': self.fiscal_error_fail_safe,
        }

    def get_nonfiscal_printer_config(self):
        """Get non-fiscal printer configuration as dict"""
        if not self.nonfiscal_printer_enabled:
            return None
        
        return {
            'enabled': True,
            'ip': self.nonfiscal_printer_ip,
            'port': self.nonfiscal_printer_port,
            'timeout': self.nonfiscal_printer_timeout,
            'width': self.comanda_printer_width,
            'auto_cut': self.comanda_auto_cut,
            'auto_open_drawer': self.comanda_auto_open_drawer,
        }
