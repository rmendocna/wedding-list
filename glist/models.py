from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


class Brand(models.Model):
    name = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.name


class Currency(models.Model):
    """
    To bind products to their original currencies
    Ideally would get exchange rates updated on a daily basis from a ForEx provider
    """
    code = models.CharField(max_length=3, primary_key=True)
    name = models.CharField(max_length=50, blank=True)
    gbp_conversion = models.FloatField(blank=True, null=True)

    def __str__(self):
        return self.code


class Product(models.Model):
    """
    Global repository of items to be added to gift lists
    Products with 0 stock can't be added to any Gift list
    """
    name = models.CharField(_('Name'), max_length=50)
    price = models.DecimalField(_('Price'), max_digits=8, decimal_places=2, help_text='Includes taxes')
    qty = models.PositiveSmallIntegerField(_('Quant in Stock'), default=0)
    brand = models.ForeignKey(Brand, on_delete=models.CASCADE, verbose_name=_('Brand'))
    currency = models.ForeignKey(Currency, on_delete=models.CASCADE,
                                 verbose_name=_('Currency'), default="GBP")

    def brand_name(self):
        return self.brand.name


class GiftList(models.Model):
    wedding_date = models.DateField(_('Wedding Date'))
    wedding_name = models.CharField(_('Description'), max_length=255)
    spouse_x_name = models.CharField(max_length=50)
    spouse_y_name = models.CharField(max_length=50)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    active = models.BooleanField(default=False, help_text='`Inactive` gift lists allow building '
                                                          'the list prior to making it public')


class Guest(models.Model):
    """
    Guest records are used the first time when mailing is sent
    announcing the Gift List availability
    """
    email = models.EmailField()
    recipient = models.CharField(_('Guest(s) names'), max_length=80,
                                 help_text='The name or names typically following `Dear ...`')
    wedding = models.ForeignKey(GiftList, on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                             related_name='invitations', blank=True)


class GiftListItem(models.Model):
    """
    Each item in a couple's Gist Line
    """
    gift_list = models.ForeignKey(GiftList, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    qty = models.PositiveSmallIntegerField(_('Quant'), default=1,
                                           help_text="Most of the times only one existence of "
                                                     "any product will be added to the list")
    qty_purchased = models.PositiveSmallIntegerField(
        _('Purchases'), default=0,
        help_text="Tracks how many are already ordered")
    price = models.DecimalField(_('Price'), max_digits=8, decimal_places=2, null=True,
                                blank=True, help_text="Gift price must remain unchanged")
    date_added = models.DateTimeField(_('When added'), auto_now_add=True)
    added_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)

    def get_price(self):
        """
        If the price is not defined here, get the price from the
        corresponding entry in the products table
        """
        price = self.price
        if not price:
            price = self.product.price
        return price


class Purchase(models.Model):
    item = models.ForeignKey(GiftListItem, on_delete=models.CASCADE, verbose_name=_('Item'))
    qty = models.PositiveSmallIntegerField(_('Quantity'), default=1,
                                           help_text="Most of the times only one existence of "
                                                     "any item will be purchased by a Guest")
    customer = models.ForeignKey(Guest, on_delete=models.CASCADE)
    date_paid = models.DateTimeField(auto_now_add=True)
    total = models.DecimalField(_('Price'), max_digits=8, decimal_places=2)
