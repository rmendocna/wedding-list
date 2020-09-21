from django.urls import include, path
from django.views.generic.base import TemplateView

from . import api, views


urlpatterns = [
    path('', TemplateView.as_view(template_name='glist/index.html'), name='index'),
    path('couple/', views.couple, name='couple'),
    path('guest/<int:gift_list_id>/', views.guest, name='guest'),
    path('api/', include([
        path('currency/', api.currency_list, name='api-currency'),
        path('brand/', api.brand_list, name='api-brand'),
        path('product/', api.product_list, name='api-product'),
        path('list/', api.gift, name='api-gift'),  # list + add
        path('list/<int:item_id>/', api.gift_item, name='api-gift-item'),  # delete
        path('list/<int:gift_list_id>/purchase/', api.purchase, name='api-purchase'),  # list + add
    ]))
    ]
