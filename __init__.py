#This file is part of Tryton.  The COPYRIGHT file at the top level of
#this repository contains the full copyright notices and license terms.
from trytond.pool import Pool
from .inventory import *

def register():
    Pool.register(
        Inventory,
        InventoryLine,
        module='nodux_stock_inventory_order', type_='model')
