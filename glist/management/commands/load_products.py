import json
import logging
import re

from django.core.management.base import BaseCommand, CommandError
from glist.models import Product, Brand, Currency

logger = logging.getLogger('default')


class Command(BaseCommand):
    help = """
    Loads product data from JSON files 
        
    You must declare the full relative or absolute paths, how many you may want to.
    Existing products will be updated/overwritten
    """

    def add_arguments(self, parser):
        parser.add_argument('json_files', nargs='+', type=str)

    def handle(self, *args, **options):

        failed = 0
        success = 0
        verbosity = options['verbosity']

        for filename in options['json_files']:
            with open(filename) as json_file:
                product_list = json.load(json_file)
                for row in product_list:
                    brand, created = Brand.objects.get_or_create(name=row['brand'])
                    # Product attributes will be set in _data
                    _data = dict(
                        brand=brand,
                        qty=row.get('in_stock_quantity', 0),
                        name=row['name'],
                    )
                    price = row['price']
                    if re.match(r'[.0-9]+[A-Za-z]{3}', price):
                        currency_code = price[-3:]
                        price = price[:-3]
                        currency, created = Currency.objects.get_or_create(code=currency_code.upper())
                        _data['currency'] = currency

                    _data['price'] = price
                    if 'id' in row:
                        try:
                            product = Product.objects.get(pk=row['id'])
                        except Product.DoesNotExist:
                            _data['id'] = row['id']
                            product = None

                    if not product:
                        product = Product(**_data)
                    else:
                        for k, v in _data.items():
                            setattr(product, k, v)
                    try:
                        product.save()
                    except Exception as e:
                        msg = '%s' % e
                        if verbosity > 1:
                            self.stderr.write(msg)
                        logger.error(msg)
                        failed += 1
                    else:
                        success += 1
        if verbosity > 0:
            self.stdout.write('Total products: %d' % (failed + success))
        if failed:
            self.stderr.write('Failed %d' % failed)
            self.stdout.write('Succeeded: %d' % success)
