from functools import wraps

from django.contrib.auth.decorators import login_required
from django.core.serializers import serialize
from django.db.models.expressions import F
from django.forms.models import model_to_dict
from django.http import (Http404, HttpResponseBadRequest,
                         HttpResponseNotAllowed, JsonResponse)

from .models import Brand, Currency, Product, GiftList, GiftListItem


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
    if not request.POST.get('product_id', 'error').is_numeric():
        return HttpResponseBadRequest
    product_id = request.POST['product_id']
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
def git_remove(request, item_id):
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
    output['qty'] -= 1
    return JsonResponse(output)


@allowed('GET')
@authenticated
def guest_gift_list(request, gift_list_id):
    guest = request.user.invitations.get(wedding_id=gift_list_id)
    gl = guest.wedding
    if not gl.active:
        return Http404()
    items = serialize('json', gl.items.filter(qty__gt=F('qty_purchased')))
    return JsonResponse(items, safe=False)