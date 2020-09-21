from io import BytesIO
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.db.models.aggregates import Sum
from django.db.models.expressions import F
from django.http import HttpResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404, render
from django.views.decorators.csrf import ensure_csrf_cookie

from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.lib.pagesizes import A4
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Table,
                                TableStyle, PageBreak)

from .models import GiftList, GiftListItem, Guest, Purchase


@login_required
@ensure_csrf_cookie
def couple(request):
    """
    Page for 'wedding planner' to add and remove items from their GiftList
    """
    try:
        wedding = GiftList.objects.get(user=request.user,
                                       active=True)
    except GiftList.DoesNotExist:
        return HttpResponseForbidden(
            'You do not have privileges to access this resource')

    cookie_name = settings.CSRF_COOKIE_NAME
    # https://vsupalov.com/avoid-csrf-errors-axios-django/
    cookie_header = 'X-CSRFTOKEN'  # settings.CSRF_HEADER_NAME

    return render(request, 'glist/couple.html', locals())


@login_required
@ensure_csrf_cookie
def guest(request, gift_list_id: int):
    """
    Page where guest can purchase items from the GiftList
    Assumes only one active GiftList for any given guest
    """
    try:
        guest = Guest.objects.get(user=request.user, wedding_id=gift_list_id,
                                  wedding__active=True)
    except Guest.DoesNotExist:
        return HttpResponseForbidden(
            'You do not have privileges to access this resource')
    wedding = guest.wedding

    cookie_name = settings.CSRF_COOKIE_NAME
    cookie_header = 'X-CSRFTOKEN'  # settings.CSRF_HEADER_NAME
    return render(request, 'glist/guest.html', locals())


def purchased_table(gift_list_id: int) -> list:
    """
    Generates the list of purchased items
    Return a list a list-of-lists of flowables
    to be used as platypus.Table content
    """
    ss = getSampleStyleSheet()
    s = ss['Normal']
    table = [
        [Paragraph('Name', s), Paragraph('Brand', s),
         Paragraph('Price', s), Paragraph('Qty', s),
         Paragraph('Guest', s), Paragraph('Date', s)
         ],
    ]
    purchases = Purchase.objects.select_related('item__product__brand', 'customer'
                                                ).filter(
        item__gift_list_id=gift_list_id, item__gift_list__active=True
    ).annotate(cnt=Sum('qty')).order_by('-date_paid', '-total')
    for p in purchases:
        table.append([
            Paragraph(p.item.product.name, s),
            Paragraph(p.item.product.brand.name, s),
            Paragraph('%s' % p.item.get_price(), s),
            Paragraph('%d' % p.cnt, s),
            Paragraph('%s' % p.customer.recipient, s),
            Paragraph(p.date_paid.strftime('%y-%m-%d'), s),
        ])
    return table


def remaining_table(gift_list_id: int) -> list:
    """
    Generates the list of tems which were not [yet] purchased
    Items which have multiple amounts are grouped and their
    corresponding counts returned

    Return a list a list-of-lists of flowables
    to be used as platypus.Table content
    """
    ss = getSampleStyleSheet()
    s = ss['Normal']
    table = [
        [Paragraph('Name', s), Paragraph('Brand', s), Paragraph('Qty', s)],
    ]
    remaining = GiftListItem.objects.select_related(
        'product__brand').filter(gift_list_id=gift_list_id, gift_list__active=True
                                 ).annotate(left=F('qty') - F('qty_purchased')
                                            ).filter(left__gt=0).annotate(total=Sum('left'))
    for r in remaining:
        table.append([
            Paragraph(r.product.name, s),
            Paragraph(r.product.brand.name, s),
            Paragraph('%d' % r.total, s),
        ])
    return table


@login_required
@ensure_csrf_cookie
def report(request):
    """
    Return a PDF in the response body with list of
    purchased items followed by that list of items
    which are remaining in the GiftList
    """
    wedding = get_object_or_404(GiftList, user=request.user, active=True)
    gift_list_id = wedding.pk

    ss = getSampleStyleSheet()
    sH = ss['Heading1']

    list_style = TableStyle(
        [('LINEBELOW', (0, 0), (-1, -1), 1, colors.grey),
         ('VALIGN', (0, 0), (-1, -1), 'TOP'),
         ('ALIGN', (1, 0), (-1, -1), 'LEFT'),
         ])

    story1 = [
        Paragraph('Purchased Gifts', sH),
        Spacer(1, 0.2 * inch),
        Table(purchased_table(gift_list_id), colWidths=(150, 100, 60, 30, 75, 55),
              style=list_style)
    ]
    story2 = [
        Paragraph('Not Purchased Gifts', sH),
        Spacer(1, 0.2 * inch),
        Table(remaining_table(gift_list_id), colWidths=(300, 150, 30),
              style=list_style)
    ]

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    story1.append(PageBreak())
    story1.extend(story2)
    doc.build(story1)

    response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename=report.pdf'
    return response
