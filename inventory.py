#This file is part of Tryton.  The COPYRIGHT file at the top level
#of this repository contains the full copyright notices and license terms.
from trytond.model import Workflow, ModelView, ModelSQL, fields
from trytond.pyson import Not, Equal, Eval, Or, Bool
from trytond import backend
from trytond.transaction import Transaction
from trytond.pool import Pool, PoolMeta

__all__ = ['Inventory','InventoryLine']
__metaclass__ = PoolMeta

class Inventory():
    'Inventory'
    __name__ ='stock.inventory'

    @staticmethod
    def complete_lines(inventories):
        '''
        Complete or update the inventories
        '''
        pool = Pool()
        Line = pool.get('stock.inventory.line')
        Product = pool.get('product.product')

        to_create = []
        for inventory in inventories:
            # Compute product quantities
            with Transaction().set_context(stock_date_end=inventory.date):
                pbl = Product.products_by_location([inventory.location.id])

            # Index some data
            product2uom = {}
            product2type = {}
            product2consumable = {}
            product2name = {}
            for product in Product.browse([line[1] for line in pbl]):
                product2uom[product.id] = product.default_uom.id
                product2type[product.id] = product.type
                product2consumable[product.id] = product.consumable
                product2name[product.id] = product.template.name

            product_qty = {}
            for (location, product), quantity in pbl.iteritems():
                product_qty[product] = (quantity, product2uom[product])

            # Update existing lines
            for line in inventory.lines:
                if not (line.product.active and
                        line.product.type == 'goods'
                        and not line.product.consumable):
                    Line.delete([line])
                    continue
                if line.product.id in product_qty:
                    quantity, uom_id = product_qty.pop(line.product.id)
                elif line.product.id in product2uom:
                    quantity, uom_id = 0.0, product2uom[line.product.id]
                else:
                    quantity, uom_id = 0.0, line.product.default_uom.id

                values = line.update_values4complete(quantity, uom_id)
                if values:
                    Line.write([line], values)

            # Create lines if needed
            for product_id in product_qty:
                if (product2type[product_id] != 'goods'
                        or product2consumable[product_id]):
                    continue
                quantity, uom_id = product_qty[product_id]
                name = product2name[product_id]
                if not quantity:
                    continue
                values = Line.create_values4complete(product_id, inventory,
                    quantity, uom_id, name)
                to_create.append(values)
        if to_create:
            Line.create(to_create)


class InventoryLine():
    'Inventory Line'
    __name__ = 'stock.inventory.line'

    name = fields.Char('Name Product')

    @classmethod
    def __setup__(cls):
        super(InventoryLine, cls).__setup__()
        cls._order.insert(0, ('name', 'ASC'))

    @fields.depends('product')
    def on_change_product(self):
        change = {}
        change['unit_digits'] = 2
        if self.product:
            change['uom'] = self.product.default_uom.id
            change['name'] = self.product.template.name
            change['uom.rec_name'] = self.product.default_uom.rec_name
            change['unit_digits'] = self.product.default_uom.digits
        else:
            change['name'] = ""
        return change

    def get_rec_name(self, name):
        return self.product.code

    @classmethod
    def create_values4complete(cls, product_id, inventory, quantity, uom_id, name):
        '''
        Return create values to complete inventory
        '''
        return {
            'inventory': inventory.id,
            'product': product_id,
            'expected_quantity': quantity,
            'quantity': max(quantity, 0.0),
            'uom': uom_id,
            'name':name,
        }
