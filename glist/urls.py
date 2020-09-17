from django.urls import include, path
from django.views.generic.base import TemplateView

from . import api, views


urlpatterns = [
    path('', TemplateView.as_view(template_name='glist/index.html'), name='index'),
    path('couple/', views.couple, name='couple'),
    path('api/', include([
        path('currency/', api.currency_list, name='api-currency'),
        path('brand/', api.brand_list, name='api-brand'),
        path('product/', api.product_list, name='api-product'),
        path('list/', api.gift_list, name='api-list'),
        path('list/add/', api.gift_add, name='api-gift-add'),
    ]))
    ]
