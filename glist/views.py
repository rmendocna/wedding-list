from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.shortcuts import render
from django.views.decorators.csrf import ensure_csrf_cookie

from .models import GiftList


@login_required
@ensure_csrf_cookie
def couple(request):
    try:
        wedding = GiftList.objects.get(user=request.user)
    except GiftList.DoesNotExist:
        return HttpResponseForbidden('You do not have privileges to access this resource')

    cookie_name = settings.CSRF_COOKIE_NAME
    cookie_header = settings.CSRF_HEADER_NAME

    return render(request, 'glist/couple.html', locals())
