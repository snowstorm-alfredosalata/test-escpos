/**
 * Printer Status Widget (Odoo POS)
 * Displays real-time fiscal and non-fiscal printer status in POS UI
 */

odoo.define('it_epos_fiscal_nonfiscal_printer.printer_status_widget', function(require) {
    'use strict';

    const PosComponent = require('point_of_sale.PosComponent');
    const Registries = require('point_of_sale.Registries');
    const { useRef, useState, useEffect } = require('owl');
    const core = require('web.core');
    const _t = core._t;

    class PrinterStatusWidget extends PosComponent {
        /**
         * Initialize widget
         */
        setup() {
            super.setup();
            
            this.printerStatuses = useState({
                fiscal: {
                    status: 'unknown',
                    message: 'Not checked',
                    ready: false,
                },
                nonfiscal: {
                    status: 'unknown',
                    message: 'Not checked',
                    ready: false,
                }
            });

            this.posConfigId = this.env.pos.config.id;
            
            // Initialize services
            this.fiscalService = new (require('it_epos_fiscal_nonfiscal_printer.fiscal_printer_service'))(this.posConfigId);
            this.comandaService = new (require('it_epos_fiscal_nonfiscal_printer.comanda_printer_service'))(this.posConfigId);

            // Auto-refresh status
            this._startAutoRefresh();
        }

        /**
         * Start automatic status refresh
         * @private
         */
        _startAutoRefresh() {
            // Initial check
            this._refreshStatus();
            
            // Check every 30 seconds
            setInterval(() => {
                this._refreshStatus();
            }, 30000);
        }

        /**
         * Refresh printer statuses
         * @private
         */
        async _refreshStatus() {
            try {
                // Check fiscal printer
                const fiscalStatus = await this.fiscalService.getStatus();
                this.printerStatuses.fiscal = {
                    status: fiscalStatus.status || 'unknown',
                    message: fiscalStatus.message || 'Unknown',
                    ready: fiscalStatus.ready || false,
                };

                // Check non-fiscal printer
                const comandaStatus = await this.comandaService.getStatus();
                this.printerStatuses.nonfiscal = {
                    status: comandaStatus.status || 'unknown',
                    message: comandaStatus.message || 'Unknown',
                    ready: comandaStatus.ready || false,
                };
            } catch (error) {
                console.warn('Error refreshing printer status:', error);
            }
        }

        /**
         * Get CSS class for status indicator
         */
        getStatusClass(status) {
            return `printer-status-indicator ${status}`;
        }

        /**
         * Get human-readable status label
         */
        getStatusLabel(status) {
            const labels = {
                'ok': 'OK',
                'busy': 'Occupato',
                'error': 'Errore',
                'offline': 'Offline',
                'warning': 'Attenzione',
                'unknown': 'Non verificato',
            };
            return labels[status] || 'Sconosciuto';
        }

        /**
         * Manual refresh button handler
         */
        async onRefreshStatus() {
            await this._refreshStatus();
            this.showNotification(_t('Printer status updated'));
        }

        /**
         * Show notification to user
         */
        showNotification(message) {
            // Use POS notification system
            if (this.env.pos && this.env.pos.proxy) {
                this.env.pos.proxy.notification('info', message);
            }
        }
    }

    // Register widget
    Registries.Component.add(PrinterStatusWidget);

    return PrinterStatusWidget;
});
