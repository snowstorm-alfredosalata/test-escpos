# -*- coding: utf-8 -*-
"""
POS Session Extension
Extends pos.session to track fiscal printer Z reports
"""

from odoo import models, fields


class PosSession(models.Model):
    _inherit = 'pos.session'

    # Track Z report execution for fiscal printer
    fiscal_z_report_printed = fields.Boolean(
        'Fiscal Z Report Printed',
        default=False,
        help='Indicates if Z report was printed on fiscal printer for this session'
    )

    fiscal_z_report_timestamp = fields.Datetime(
        'Fiscal Z Report Timestamp',
        help='When the fiscal Z report was printed'
    )

    fiscal_receipts_count = fields.Integer(
        'Fiscal Receipts Count',
        default=0,
        help='Total number of fiscal receipts printed in this session'
    )
