/**
 * Fiscal Printer Service (Odoo POS)
 * Handles communication with SF20 fiscal printer through backend API
 */

odoo.define('it_epos_fiscal_nonfiscal_printer.fiscal_printer_service', function(require) {
    'use strict';

    const AbstractAwaitablePopup = require('point_of_sale.AbstractAwaitablePopup');
    const { useContext } = require('web.owl');
    const Registries = require('point_of_sale.Registries');
    const core = require('web.core');

    class FiscalPrinterService {
        /**
         * Initialize fiscal printer service
         * @param {number} posConfigId - POS configuration ID
         */
        constructor(posConfigId) {
            this.posConfigId = posConfigId;
            this.lastStatus = null;
            this.statusCheckInterval = null;
        }

        /**
         * Get fiscal printer status
         * @returns {Promise<Object>} Status object
         */
        async getStatus() {
            try {
                const response = await this._callBackendAPI('/pos_printer/fiscal/status', {
                    pos_config_id: this.posConfigId
                });
                this.lastStatus = response;
                return response;
            } catch (error) {
                console.error('Error getting fiscal printer status:', error);
                return {
                    status: 'error',
                    ready: false,
                    message: error.message
                };
            }
        }

        /**
         * Print fiscal receipt
         * @param {Object} receiptData - Receipt data with items and payments
         * @returns {Promise<Object>} Print result
         */
        async printReceipt(receiptData) {
            try {
                console.log('Printing fiscal receipt:', receiptData);
                const response = await this._callBackendAPI('/pos_printer/fiscal/print_receipt', {
                    pos_config_id: this.posConfigId,
                    receipt_data: receiptData
                });
                return response;
            } catch (error) {
                console.error('Error printing fiscal receipt:', error);
                throw error;
            }
        }

        /**
         * Execute Z report (end of day)
         * @returns {Promise<Object>} Z report result
         */
        async executeZReport() {
            try {
                console.log('Executing Z report...');
                const response = await this._callBackendAPI('/pos_printer/fiscal/z_report', {
                    pos_config_id: this.posConfigId
                });
                return response;
            } catch (error) {
                console.error('Error executing Z report:', error);
                throw error;
            }
        }

        /**
         * Start periodic status checking
         * @param {number} intervalMs - Check interval in milliseconds (default 30000)
         */
        startStatusMonitoring(intervalMs = 30000) {
            if (this.statusCheckInterval) {
                clearInterval(this.statusCheckInterval);
            }
            
            this.statusCheckInterval = setInterval(() => {
                this.getStatus().catch(err => {
                    console.warn('Status check failed:', err);
                });
            }, intervalMs);
            
            console.log('Fiscal printer status monitoring started');
        }

        /**
         * Stop periodic status checking
         */
        stopStatusMonitoring() {
            if (this.statusCheckInterval) {
                clearInterval(this.statusCheckInterval);
                this.statusCheckInterval = null;
                console.log('Fiscal printer status monitoring stopped');
            }
        }

        /**
         * Build receipt data from POS order
         * @param {Object} order - POS order object
         * @returns {Object} Formatted receipt data
         */
        buildReceiptData(order) {
            const items = [];
            const payments = [];

            // Process order lines as items
            if (order.orderlines) {
                for (const line of order.orderlines.models) {
                    if (line.get_quantity() > 0) {
                        items.push({
                            description: line.get_product().display_name.substring(0, 40),
                            quantity: line.get_quantity(),
                            unit_price: line.get_unit_price(),
                            tax_percent: line.get_tax() || 0,
                        });
                    }
                }
            }

            // Process payment lines
            if (order.paymentlines) {
                for (const payment of order.paymentlines.models) {
                    payments.push({
                        type: this._mapPaymentType(payment.get_payment_method().name),
                        amount: payment.get_amount(),
                    });
                }
            }

            return {
                items: items,
                payments: payments,
            };
        }

        /**
         * Private: Call backend API
         * @private
         */
        async _callBackendAPI(endpoint, params) {
            return new Promise((resolve, reject) => {
                $.ajax({
                    url: endpoint,
                    method: 'POST',
                    data: JSON.stringify(params),
                    contentType: 'application/json',
                    dataType: 'json',
                    success: (result) => {
                        if (result.error) {
                            reject(new Error(result.error));
                        } else {
                            resolve(result);
                        }
                    },
                    error: (xhr, status, error) => {
                        reject(new Error(`API Error: ${error}`));
                    }
                });
            });
        }

        /**
         * Map Odoo payment method to SF20 payment type
         * @private
         */
        _mapPaymentType(methodName) {
            const lowerName = (methodName || '').toLowerCase();
            if (lowerName.includes('card') || lowerName.includes('carta')) {
                return 'card';
            }
            if (lowerName.includes('check') || lowerName.includes('assegno')) {
                return 'check';
            }
            return 'cash';
        }
    }

    // Register service
    Registries.service.add('fiscal_printer_service', FiscalPrinterService);
    
    return FiscalPrinterService;
});
