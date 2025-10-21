# -*- coding: utf-8 -*-
# ctos/drivers/aster/__init__.py
# Aster DEX driver package

from .driver import AsterDriver, AsterClient, init_AsterClient
from .Config import ACCOUNTS, EXCHANGE_CONFIG, API_CONFIG, TRADING_CONFIG

__version__ = "1.0.0"
__author__ = "CTOS Team"
__description__ = "Aster DEX driver for CTOS trading framework"

__all__ = [
    'AsterDriver',
    'AsterClient', 
    'init_AsterClient',
    'ACCOUNTS',
    'EXCHANGE_CONFIG',
    'API_CONFIG',
    'TRADING_CONFIG'
]
