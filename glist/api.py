from functools import wraps
import json

from django.core.serializers import serialize
from django.db.models.expressions import F
from django.forms.models import model_to_dict
from django.http import (Http404, HttpResponseBadRequest,
                         HttpResponseNotAllowed, JsonResponse)

from .models import (Brand, Currency, Product, GiftList, GiftListItem, Purchase)


def allowed(*methods):
    """
    Decorator for view that ensures that the request method
        is one of the methods passed in
    returns 405 otherwise
    """
    def decorator(endpoint, *args, **kwargs):
        @wraps(endpoint)
        def _wrapped_view(request, *args, **kwargs):
            if request.method in methods:
                return endpoint(request, *args, **kwargs)
            else:
                return HttpResponseNotAllowed(methods)
        return _wrapped_view
    return decorator


def authenticated(endpoint):
    @wraps(endpoint)
    def wrapped(request, *args, **kwargs):
        if not request.user.is_authenticated:
            out = JsonResponse({'error': 'Unauthorised'}, status=401)
            out['Authorization'] = 'basic'  # always over https
            return out
        else:
            return endpoint(request, *args, **kwargs)
    return wrapped


@allowed('GET')
def object_list(request, kls):
    objs = kls.objects.all()
    output = serialize('json', objs, indent=2)
    return JsonResponse(output, safe=False)


def product_list(request):
    return object_list(request, Product)


def brand_list(request):
    return object_list(request, Brand)


def currency_list(request):
    return object_list(request, Currency)


@allowed('GET')
@authenticated
def gift_list(request):
    gl = GiftList.objects.get(user=request.user)
    items = GiftListItem.objects.filter(gift_list=gl)
    output = serialize('json', items, indent=2)
    return JsonResponse(output, safe=False)


@allowed('POST')
@authenticated
def gift_add(request):
    """
    Takes a product ID and adds it as a gift item to the user's GiftList
    If the item already exists, increases its count
    """
    data = json.loads(request.body)
    if type(data.get('product_id', 'error')) != int:
        return HttpResponseBadRequest()
    product_id = data['product_id']
    gl = GiftList.objects.get(user=request.user)
    product = Product.objects.get(pk=product_id)
    # Check if its there already
    try:
        item = GiftListItem.objects.get(gift_list=gl, product=product)
    except GiftListItem.DoesNotExist:
        item = GiftListItem(gift_list=gl, product=product,
                            price=product.price, added_by=request.user)
    else:
        item.qty += 1
    item.added_by = request.user
    item.save()
    output = model_to_dict(item)
    return JsonResponse(output)


@allowed('DELETE')
@authenticated
def gift_remove(request, item_id):
    """
    Removes 1 Item count from the current user's GiftList
    If it's the only account of that item, removes the item entirely
    """
    gl = GiftList.objects.get(user=request.user)
    item = GiftListItem.objects.get(gift_list=gl, pk=item_id)
    output = model_to_dict(item)
    if item.qty == 1:
        item.delete()
    else:
        item.qty -= 1
        item.save()
    output['qty'] -= 1
    return JsonResponse(output)


def gift(request):
    if request.method == 'GET':
        return gift_list(request)
    elif request.method == 'POST':
        return gift_add(request)
    else:
        return HttpResponseNotAllowed()


def gift_item(request, item_id):
    if request.method == 'DELETE':
        return gift_remove(request, item_id)
    # elif request.method == 'PUT':
    #   to be implemented
    # elif request.method == 'GET':
    #   to be implemented
    else:
        return HttpResponseNotAllowed()


@allowed('GET')
@authenticated
def purchase_list(request, gift_list_id):
    guest = request.user.invitations.get(wedding_id=gift_list_id)
    gl = guest.wedding
    if not gl.active:
        return Http404()
    items = serialize('json', Purchase.objects.filter(customer=guest))
    return JsonResponse(items, safe=False)


@allowed('POST')
@authenticated
def purchase_add(request, gift_list_id):
    """
    Buy 1 count of Gift from the GiftList <gift_list_id>
    """
    guest = request.user.invitations.get(wedding_id=gift_list_id)
    gl = guest.wedding
    if not gl.active:
        return Http404()
    data = json.loads(request.body)
    if type(data.get('item_id', 'error')) != int:
        return HttpResponseBadRequest
    item_id = data['item_id']
    try:
        item = GiftListItem.objects.get(pk=item_id, qty__gt=F('qty_purchased'))
    except GiftListItem.DoesNotExist:
        return JsonResponse({'errors': ['Item could not be purchased']}, status_code=404)
    else:
        purchase = Purchase(customer=guest, item=item, qty=1, total=item.get_price())
        purchase.save()
        # Increase the amount of acquired related gift item
        item.qty_purchased += 1
        item.save()
        output = model_to_dict(purchase)
        return JsonResponse(output)


def purchase(request, *args, **kwargs):
    if request.method == 'POST':
        return purchase_add(request, *args, **kwargs)
    elif request.method == 'GET':
        return purchase_list(request, *args, **kwargs)
    else:
        return HttpResponseNotAllowed()
