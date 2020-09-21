import json
from datetime import date, timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase, Client
from django.urls import reverse

from .models import (Brand, GiftList, GiftListItem, Guest, Product,
                     Purchase)


class DataSetuoMixin(object):

    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        user1 = User.objects.create_user('bride', 'bride@weddingshop.com',
                                         'ec767bf6334a24af632a51bd6e7d2eb3')
        user2 = User.objects.create_user('guest', 'guest@weddingshop.com',
                                         'f74923bcaa2b52ca965e42ab3e44e656')
        wedding = GiftList(wedding_date=date.today()+timedelta(6*31),
                           wedding_name='Pompous Wedding', spouse_x_name='Ms Dude',
                           spouse_y_name='Mr Dude', user=user1)
        wedding.save()
        guest = Guest(email='guest@weddinshop.com', recipient='M Guest',
                      user=user2, wedding=wedding)
        guest.save()


class TestGiftList(DataSetuoMixin, TestCase):

    fixtures = ['brands', 'prods']

    def setUp(self) -> None:
        self.client = Client()

    def test_index_url(self):
        resp = self.client.get('/')
        self.assertEqual(resp.status_code, 200)

    def test_wedding(self):
        self.assertEqual(GiftList.objects.count(), 1)

    def test_bride_url_redirect(self):
        resp = self.client.get(reverse('couple'))
        self.assertEqual(resp.status_code, 302)
        self.assertRedirects(resp, settings.LOGIN_URL + '?next=/couple/')

    def test_bride_url(self):
        self.client.login(username='bride',
                          password='ec767bf6334a24af632a51bd6e7d2eb3')
        resp = self.client.get(reverse('couple'))
        self.assertEqual(resp.status_code, 200)

    def test_report_url(self):
        self.client.login(username='bride',
                          password='ec767bf6334a24af632a51bd6e7d2eb3')
        resp = self.client.get(reverse('report'))
        self.assertEqual(resp.status_code, 200)

    def test_guest_url_redirect(self):
        wedding = GiftList.objects.first()
        url = reverse('guest', kwargs=dict(gift_list_id=wedding.pk))
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 302)
        self.assertRedirects(resp, '%s?next=%s' % (settings.LOGIN_URL, url))

    def test_wrong_guest_url_redirect(self):
        wedding = GiftList.objects.first()
        url = reverse('guest', kwargs=dict(gift_list_id=wedding.pk))
        self.client.login(username='bride',
                          password='ec767bf6334a24af632a51bd6e7d2eb3')
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 403)

    def test_guest_url(self):
        wedding = GiftList.objects.first()
        url = reverse('guest', kwargs=dict(gift_list_id=wedding.pk))
        self.client.login(username='guest',
                          password='f74923bcaa2b52ca965e42ab3e44e656')
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)

    def _test_api_url(self, name, count):
        resp = self.client.get(reverse(name))
        self.assertEqual(resp.status_code, 200)
        # FIXME:
        data = json.loads(resp.json())
        self.assertEqual(len(data), count)

    def test_api_list_url(self):
        self._test_api_url('api-currency', 1)
        self._test_api_url('api-brand', 12)
        self._test_api_url('api-product', 20)


class TestLoading(TestCase):

    def test_load_products(self):
        self.assertEqual(Product.objects.count(), 0)
        call_command('load_products', 'glist/fixtures/products.json',
                     verbosity=0)
        self.assertEqual(Product.objects.count(), 20)
        self.assertEqual(Brand.objects.count(), 12)


class TestCoupleActions(DataSetuoMixin, TestCase):

    fixtures = ['brands', 'prods']

    def setUp(self) -> None:
        self.client = Client()
        self.usr = get_user_model().objects.get(username='bride')
        self.wedding = GiftList.objects.get(user=self.usr, active=True)
        self.client._login(self.usr)
        # self.client.login(username='bride',
        #                   password='ec767bf6334a24af632a51bd6e7d2eb3')

    def test_add_gift(self):
        self.assertEqual(GiftListItem.objects.filter(gift_list=self.wedding
                                                     ).count(), 0)
        resp = self.client.generic('POST', reverse('api-gift'),
                                   '{"product_id": 12}')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(GiftListItem.objects.filter(gift_list=self.wedding
                                                     ).count(), 1)

    def test_add_gift_unauthorised(self):
        self.client.logout()
        resp = self.client.generic('POST', reverse('api-gift'),
                                   '{"product_id": 12}')
        self.assertEqual(resp.status_code, 401)
        self.assertEqual(GiftListItem.objects.filter(gift_list=self.wedding
                                                     ).count(), 0)

    def add_gift(self):
        item = GiftListItem(gift_list=self.wedding, qty=1,
                            added_by=self.usr, product_id=11)
        item.save()

    def test_remove_gift(self):
        self.add_gift()
        item = GiftListItem.objects.filter(gift_list=self.wedding).first()
        resp = self.client.delete(reverse('api-gift-item',
                                          kwargs=dict(item_id=item.pk)))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(GiftListItem.objects.filter(gift_list=self.wedding,
                                                     ).count(), 0)

    def test_remove_gift_unauthorised(self):
        self.client.logout()
        self.add_gift()
        item = GiftListItem.objects.filter(gift_list=self.wedding).first()
        resp = self.client.delete(reverse('api-gift-item',
                                          kwargs=dict(item_id=item.pk)))
        self.assertEqual(resp.status_code, 401)
        self.assertEqual(GiftListItem.objects.filter(gift_list=self.wedding,
                                                     ).count(), 1)


class TestGuestActions(DataSetuoMixin, TestCase):

    fixtures = ['brands', 'prods']

    def setUp(self) -> None:
        bride = get_user_model().objects.get(username='bride')
        self.wedding = GiftList.objects.get(user=bride, active=True)
        item = GiftListItem(gift_list=self.wedding, qty=1,
                            added_by=bride, product_id=11)
        item.save()

    def test_buy_item(self):
        self.client.login(username='guest',
                          password='f74923bcaa2b52ca965e42ab3e44e656')
        item = GiftListItem.objects.get(gift_list=self.wedding)
        self.assertEqual(Purchase.objects.count(), 0)
        self.client.generic('POST',
                            reverse('api-purchase',
                                    kwargs=dict(gift_list_id=self.wedding.pk)),
                            '{"item_id": %s}' % item.pk)
        self.assertEqual(Purchase.objects.count(), 1)

    def test_unauthorised(self):
        item = GiftListItem.objects.get(gift_list=self.wedding)
        resp = self.client.generic(
            'POST', reverse('api-purchase',
                            kwargs=dict(gift_list_id=self.wedding.pk)),
            '{"item_id": %s}' % item.pk)
        self.assertEqual(resp.status_code, 401)
