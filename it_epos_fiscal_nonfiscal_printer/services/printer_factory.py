# -*- coding: utf-8 -*-
"""
Printer Factory & Management
Factory pattern for creating and managing printer adapters
"""

import logging
from typing import Optional, Union

from .fiscal_printer_service import SF20FiscalPrinterAdapter
from .nonfiscal_printer_service import ESCPOSPrinterAdapter

_logger = logging.getLogger(__name__)


class PrinterFactory:
    """
    Factory for creating printer adapters
    Manages instances and ensures proper initialization
    """

    _fiscal_instances = {}
    _nonfiscal_instances = {}

    @classmethod
    def create_fiscal_printer(cls, pos_config_id: int, ip: str, port: int = 9100,
                             timeout: int = 30) -> Optional[SF20FiscalPrinterAdapter]:
        """
        Create or retrieve SF20 fiscal printer adapter
        
        Args:
            pos_config_id: POS configuration ID (for caching)
            ip: Printer IP address
            port: TCP port
            timeout: Socket timeout
        
        Returns:
            SF20FiscalPrinterAdapter instance or None if invalid
        """
        try:
            key = f'fiscal_{pos_config_id}'
            
            # Return cached instance if available
            if key in cls._fiscal_instances:
                return cls._fiscal_instances[key]
            
            # Create new instance
            adapter = SF20FiscalPrinterAdapter(ip, port, timeout)
            cls._fiscal_instances[key] = adapter
            
            _logger.info(f'Created fiscal printer adapter for POS config {pos_config_id}')
            return adapter
        except Exception as e:
            _logger.error(f'Error creating fiscal printer adapter: {str(e)}')
            return None

    @classmethod
    def create_nonfiscal_printer(cls, pos_config_id: int, ip: str, port: int = 9100,
                                timeout: int = 10, width: int = 32) -> Optional[ESCPOSPrinterAdapter]:
        """
        Create or retrieve ESC/POS non-fiscal printer adapter
        
        Args:
            pos_config_id: POS configuration ID (for caching)
            ip: Printer IP address
            port: TCP port
            timeout: Socket timeout
            width: Printer width in characters
        
        Returns:
            ESCPOSPrinterAdapter instance or None if invalid
        """
        try:
            key = f'nonfiscal_{pos_config_id}'
            
            # Return cached instance if available
            if key in cls._nonfiscal_instances:
                return cls._nonfiscal_instances[key]
            
            # Create new instance
            adapter = ESCPOSPrinterAdapter(ip, port, timeout, width)
            cls._nonfiscal_instances[key] = adapter
            
            _logger.info(f'Created non-fiscal printer adapter for POS config {pos_config_id}')
            return adapter
        except Exception as e:
            _logger.error(f'Error creating non-fiscal printer adapter: {str(e)}')
            return None

    @classmethod
    def get_fiscal_printer(cls, pos_config_id: int) -> Optional[SF20FiscalPrinterAdapter]:
        """Retrieve cached fiscal printer adapter"""
        return cls._fiscal_instances.get(f'fiscal_{pos_config_id}')

    @classmethod
    def get_nonfiscal_printer(cls, pos_config_id: int) -> Optional[ESCPOSPrinterAdapter]:
        """Retrieve cached non-fiscal printer adapter"""
        return cls._nonfiscal_instances.get(f'nonfiscal_{pos_config_id}')

    @classmethod
    def disconnect_fiscal_printer(cls, pos_config_id: int) -> None:
        """Disconnect fiscal printer adapter"""
        key = f'fiscal_{pos_config_id}'
        if key in cls._fiscal_instances:
            try:
                cls._fiscal_instances[key].disconnect()
                del cls._fiscal_instances[key]
                _logger.info(f'Disconnected fiscal printer for POS config {pos_config_id}')
            except Exception as e:
                _logger.error(f'Error disconnecting fiscal printer: {str(e)}')

    @classmethod
    def disconnect_nonfiscal_printer(cls, pos_config_id: int) -> None:
        """Disconnect non-fiscal printer adapter"""
        key = f'nonfiscal_{pos_config_id}'
        if key in cls._nonfiscal_instances:
            try:
                cls._nonfiscal_instances[key].disconnect()
                del cls._nonfiscal_instances[key]
                _logger.info(f'Disconnected non-fiscal printer for POS config {pos_config_id}')
            except Exception as e:
                _logger.error(f'Error disconnecting non-fiscal printer: {str(e)}')

    @classmethod
    def disconnect_all(cls) -> None:
        """Disconnect all printer adapters"""
        for adapter in cls._fiscal_instances.values():
            try:
                adapter.disconnect()
            except Exception as e:
                _logger.warning(f'Error disconnecting fiscal printer: {str(e)}')
        
        for adapter in cls._nonfiscal_instances.values():
            try:
                adapter.disconnect()
            except Exception as e:
                _logger.warning(f'Error disconnecting non-fiscal printer: {str(e)}')
        
        cls._fiscal_instances.clear()
        cls._nonfiscal_instances.clear()
        _logger.info('All printer adapters disconnected')
