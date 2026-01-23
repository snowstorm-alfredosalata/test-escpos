# -*- coding: utf-8 -*-
"""
POS Printer Status Model
Tracks real-time status of fiscal and non-fiscal printers
"""

from odoo import models, fields, api
from datetime import datetime, timedelta


class PosPrinterStatus(models.Model):
    _name = 'pos.printer.status'
    _description = 'POS Printer Status Tracking'
    _order = 'id desc'

    # ============================================================
    # RELATIONSHIPS
    # ============================================================

    pos_config_id = fields.Many2one(
        'pos.config',
        'POS Configuration',
        required=True,
        ondelete='cascade'
    )

    session_id = fields.Many2one(
        'pos.session',
        'POS Session',
        required=False,
        ondelete='set null'
    )

    # ============================================================
    # STATUS FIELDS
    # ============================================================

    printer_type = fields.Selection(
        [
            ('fiscal', 'Fiscal Printer (SF20)'),
            ('nonfiscal', 'Non-Fiscal Printer (ESC/POS)'),
        ],
        'Printer Type',
        required=True
    )

    status = fields.Selection(
        [
            ('ok', 'OK - Ready'),
            ('busy', 'Busy - Processing'),
            ('error', 'Error'),
            ('offline', 'Offline - Not Reachable'),
            ('warning', 'Warning - Action Required'),
            ('unknown', 'Unknown - Not Checked'),
        ],
        'Status',
        default='unknown',
        required=True
    )

    status_message = fields.Text(
        'Status Message',
        help='Detailed status information or error message'
    )

    # ============================================================
    # FISCAL-SPECIFIC FIELDS
    # ============================================================

    fiscal_state = fields.Selection(
        [
            ('init', 'Initialized'),
            ('receipt_open', 'Receipt Open'),
            ('receipt_closed', 'Receipt Closed'),
            ('z_report_required', 'Z Report Required'),
            ('memory_full', 'Memory Full'),
            ('fiscal_memory_error', 'Fiscal Memory Error'),
            ('unknown', 'Unknown State'),
        ],
        'Fiscal State',
        help='SF20 fiscal state machine status'
    )

    last_z_report_date = fields.Datetime(
        'Last Z Report',
        help='Timestamp of the last Z report execution'
    )

    last_receipt_number = fields.Integer(
        'Last Receipt Number',
        help='Number of the last fiscal receipt issued'
    )

    # ============================================================
    # TIMESTAMP & TRACKING
    # ============================================================

    last_check_time = fields.Datetime(
        'Last Status Check',
        default=fields.Datetime.now,
        help='When the status was last verified'
    )

    response_time_ms = fields.Float(
        'Response Time (ms)',
        help='Milliseconds taken to receive last response'
    )

    consecutive_errors = fields.Integer(
        'Consecutive Errors',
        default=0,
        help='Counter of consecutive failed communication attempts'
    )

    # ============================================================
    # METADATA
    # ============================================================

    created_at = fields.Datetime(
        'Created',
        default=fields.Datetime.now,
        readonly=True
    )

    # ============================================================
    # HELPER METHODS
    # ============================================================

    @api.model
    def update_fiscal_status(self, pos_config_id, new_status, message='', 
                             fiscal_state=None, response_time=None):
        """
        Update or create fiscal printer status record
        
        Args:
            pos_config_id: pos.config record ID
            new_status: Status value ('ok', 'busy', 'error', 'offline', 'warning', 'unknown')
            message: Detailed status message or error description
            fiscal_state: Current SF20 fiscal state (if available)
            response_time: Response time in milliseconds
        """
        pos_config = self.env['pos.config'].browse(pos_config_id)
        current_session = self.env['pos.session'].search(
            [('config_id', '=', pos_config_id), ('state', '=', 'opened')],
            limit=1
        )

        status_record = self.search(
            [
                ('pos_config_id', '=', pos_config_id),
                ('printer_type', '=', 'fiscal'),
            ],
            limit=1
        )

        # Determine consecutive errors count
        consecutive_errors = 0
        if new_status in ('error', 'offline', 'warning'):
            consecutive_errors = (status_record.consecutive_errors or 0) + 1
        elif new_status == 'ok':
            consecutive_errors = 0

        values = {
            'pos_config_id': pos_config_id,
            'printer_type': 'fiscal',
            'session_id': current_session.id if current_session else None,
            'status': new_status,
            'status_message': message,
            'fiscal_state': fiscal_state,
            'last_check_time': fields.Datetime.now(),
            'response_time_ms': response_time,
            'consecutive_errors': consecutive_errors,
        }

        if status_record:
            status_record.write(values)
        else:
            status_record = self.create(values)

        return status_record

    @api.model
    def update_nonfiscal_status(self, pos_config_id, new_status, message='', response_time=None):
        """
        Update or create non-fiscal printer status record
        
        Args:
            pos_config_id: pos.config record ID
            new_status: Status value ('ok', 'busy', 'error', 'offline', 'warning', 'unknown')
            message: Detailed status message or error description
            response_time: Response time in milliseconds
        """
        pos_config = self.env['pos.config'].browse(pos_config_id)
        current_session = self.env['pos.session'].search(
            [('config_id', '=', pos_config_id), ('state', '=', 'opened')],
            limit=1
        )

        status_record = self.search(
            [
                ('pos_config_id', '=', pos_config_id),
                ('printer_type', '=', 'nonfiscal'),
            ],
            limit=1
        )

        # Determine consecutive errors count
        consecutive_errors = 0
        if new_status in ('error', 'offline', 'warning'):
            consecutive_errors = (status_record.consecutive_errors or 0) + 1
        elif new_status == 'ok':
            consecutive_errors = 0

        values = {
            'pos_config_id': pos_config_id,
            'printer_type': 'nonfiscal',
            'session_id': current_session.id if current_session else None,
            'status': new_status,
            'status_message': message,
            'last_check_time': fields.Datetime.now(),
            'response_time_ms': response_time,
            'consecutive_errors': consecutive_errors,
        }

        if status_record:
            status_record.write(values)
        else:
            status_record = self.create(values)

        return status_record

    def is_healthy(self):
        """Check if printer status indicates it's ready for use"""
        return self.status in ('ok', 'busy')

    def is_critical(self):
        """Check if printer has a critical error"""
        return self.status in ('error', 'offline')
