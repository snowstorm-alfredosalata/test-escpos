# -*- coding: utf-8 -*-
"""
it_epos_fiscal_nonfiscal_printer: Odoo 19 Module
Integration of fiscal printers (SF20) and non-fiscal ESC/POS printers for POS

Italian Restaurant/Bar POS integration with:
- Fiscal Printer (Protocollo Fiscale SF20 - HYDRA)
- Non-Fiscal Kitchen/Bar Order Printer (ESC/POS over TCP/IP)
"""

from . import models
from . import controllers
