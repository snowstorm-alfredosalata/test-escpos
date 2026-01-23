/**
 * Comanda (Non-Fiscal) Printer Service (Odoo POS)
 * Handles communication with ESC/POS printer for kitchen orders
 */

odoo.define('it_epos_fiscal_nonfiscal_printer.comanda_printer_service', function(require) {
    'use strict';

    const Registries = require('point_of_sale.Registries');
    const core = require('web.core');

    class ComandaPrinterService {
        /**
         * Initialize comanda printer service
         * @param {number} posConfigId - POS configuration ID
         */
        constructor(posConfigId) {
            this.posConfigId = posConfigId;
            this.lastStatus = null;
        }

        /**
         * Get non-fiscal printer status
         * @returns {Promise<Object>} Status object
         */
        async getStatus() {
            try {
                const response = await this._callBackendAPI('/pos_printer/nonfiscal/status', {
                    pos_config_id: this.posConfigId
                });
                this.lastStatus = response;
                return response;
            } catch (error) {
                console.error('Error getting comanda printer status:', error);
                return {
                    status: 'error',
                    ready: false,
                    message: error.message
                };
            }
        }

        /**
         * Print kitchen order (comanda)
         * @param {Object} orderData - Order data to print
         * @returns {Promise<Object>} Print result
         */
        async printComanda(orderData, options = {}) {
            try {
                console.log('Printing comanda:', orderData);
                const response = await this._callBackendAPI('/pos_printer/nonfiscal/print_comanda', {
                    pos_config_id: this.posConfigId,
                    order_data: orderData,
                    auto_cut: options.auto_cut || false,
                    open_drawer: options.open_drawer || false,
                });
                return response;
            } catch (error) {
                console.error('Error printing comanda:', error);
                throw error;
            }
        }

        /**
         * Build comanda data from POS order
         * @param {Object} order - POS order object
         * @returns {Object} Formatted comanda data
         */
        buildComandaData(order, options = {}) {
            const items = [];
            const timestamp = new Date().toLocaleTimeString('it-IT');

            // Process order lines
            if (order.orderlines) {
                for (const line of order.orderlines.models) {
                    if (line.get_quantity() > 0) {
                        // Group by product category or kitchen section
                        const notes = this._buildLineNotes(line);
                        
                        items.push({
                            description: line.get_product().display_name.substring(0, 35),
                            quantity: line.get_quantity(),
                            notes: notes,
                        });
                    }
                }
            }

            // Build comanda document
            const comandaData = {
                order_number: order.name || 'COMANDA',
                table: options.table_name || this._extractTableName(order),
                timestamp: timestamp,
                items: items,
                header: options.header || 'COMANDA CUCINA',
                footer: options.footer || 'Grazie',
            };

            return comandaData;
        }

        /**
         * Build notes for a line (attributes, special requests)
         * @private
         */
        _buildLineNotes(line) {
            const notes = [];
            
            // Add product attributes if any
            if (line.get_product_type && line.get_product_type() === 'service') {
                notes.push('(Servizio)');
            }

            // Add customer notes if present
            if (line.note && line.note.length > 0) {
                notes.push(`Note: ${line.note}`);
            }

            return notes.join(' ');
        }

        /**
         * Extract table name from order
         * @private
         */
        _extractTableName(order) {
            // Try to get table from order or session
            if (order.table_id) {
                return `Table ${order.table_id.name || order.table_id.id}`;
            }
            return 'No Table';
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
    }

    // Register service
    Registries.service.add('comanda_printer_service', ComandaPrinterService);
    
    return ComandaPrinterService;
});
