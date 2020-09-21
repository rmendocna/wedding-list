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

from .models import GiftList, GiftListItem, Purchase


@login_required
@ensure_csrf_cookie
def couple(request):
    try:
        wedding = GiftList.objects.get(user=request.user)
    except GiftList.DoesNotExist:
        return HttpResponseForbidden(
            'You do not have privileges to access this resource')

    cookie_name = settings.CSRF_COOKIE_NAME
    # https://vsupalov.com/avoid-csrf-errors-axios-django/
    cookie_header = 'X-CSRFTOKEN'  # settings.CSRF_HEADER_NAME

    return render(request, 'glist/couple.html', locals())


@login_required
@ensure_csrf_cookie
def guest(request, gift_list_id):
    try:
        wedding = GiftList.objects.get(user=request.user, pk=gift_list_id)
    except GiftList.DoesNotExist:
        return HttpResponseForbidden(
            'You do not have privileges to access this resource')

    cookie_name = settings.CSRF_COOKIE_NAME
    cookie_header = 'X-CSRFTOKEN'  # settings.CSRF_HEADER_NAME
    return render(request, 'glist/guest.html', locals())


@login_required
@ensure_csrf_cookie
def report(request):
    wedding = get_object_or_404(GiftList, user=request.user, active=True)
    gift_list_id = wedding.pk

    ss = getSampleStyleSheet()
    s = ss['Normal']
    sH = ss['Heading1']

    def purchased_table():
        table1 = [
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
            table1.append([
                Paragraph(p.item.product.name, s),
                Paragraph(p.item.product.brand.name, s),
                Paragraph('%s' % p.item.get_price(), s),
                Paragraph('%d' % p.cnt, s),
                Paragraph('%s' % p.customer.recipient, s),
                Paragraph(p.date_paid.strftime('%y-%m-%d'), s),
            ])
        return table1

    def remaining_table():
        table2 = [
            [Paragraph('Name', s), Paragraph('Brand', s), Paragraph('Qty', s)],
        ]
        remaining = GiftListItem.objects.select_related(
            'product__brand').filter(gift_list_id=gift_list_id, gift_list__active=True
                                     ).annotate(left=F('qty') - F('qty_purchased')
                                                ).filter(left__gt=0).annotate(total=Sum('left'))
        for r in remaining:
            table2.append([
                Paragraph(r.product.name, s),
                Paragraph(r.product.brand.name, s),
                Paragraph('%d' % r.total, s),
            ])
        return table2

    list_style = TableStyle(
        [('LINEBELOW', (0, 0), (-1, -1), 1, colors.grey),
         ('VALIGN', (0, 0), (-1, -1), 'TOP'),
         ('ALIGN', (1, 0), (-1, -1), 'LEFT'),
         ])

    story1 = [
        Paragraph('Purchased Gifts', sH),
        Spacer(1, 0.2 * inch),
        Table(purchased_table(), colWidths=(150, 100, 60, 30, 75, 55), style=list_style)
    ]
    story2 = [
        Paragraph('Not Purchased Gifts', sH),
        Spacer(1, 0.2 * inch),
        Table(remaining_table(), colWidths=(300, 150, 30), style=list_style)
    ]

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    # f1 = Frame(.7*inch, .7*inch, 3.5 * inch, 9.5 * inch, showBoundary=1)
    # f2 = Frame(4.5 * inch, .7*inch, 3 * inch, 9.5 * inch, showBoundary=1)
    # f2.addFromList(story2, 'a')
    # f1.addFromList(story1, 'a')
    # page_template = PageTemplate('main', frames=[f1, f2])
    # doc = BaseDocTemplate('mydoc.pdf', pagesize=A4, allowSplitting=0)
    story1.append(PageBreak())
    story1.extend(story2)
    # doc.addPageTemplates([page_template])
    doc.build(story1)

    response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename=report.pdf'
    return response
