from datetime import datetime, time, timedelta
from decimal import Decimal

from django.db.models import Count, DecimalField, ExpressionWrapper, F, Q, Sum
from django.db.models.functions import Coalesce, TruncDate
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from accounts.permissions import IsPharmacyOwner
from sales.models import Sale, SaleItem

DEFAULT_WEEKS = 8
MAX_WEEKS = 52
CENTS = Decimal('0.01')
MONEY = DecimalField(max_digits=14, decimal_places=2)


def money(value):
    return str(Decimal(value).quantize(CENTS))


@api_view(['GET'])
@permission_classes([IsPharmacyOwner])
def weekly_report(request):
    """PHAR-14: weekly sales and profit for the owner's pharmacy.

    A week runs Monday to Sunday, in Lebanon time. The newest week (this week) comes first,
    and weeks with no sales are still shown with zeros.
    """
    try:
        weeks = int(request.query_params.get('weeks', DEFAULT_WEEKS))
    except (TypeError, ValueError):
        weeks = 0
    if not 1 <= weeks <= MAX_WEEKS:
        return Response({'error': f'weeks must be a whole number from 1 to {MAX_WEEKS}.'},
                        status=status.HTTP_400_BAD_REQUEST)

    pharmacy = request.user.pharmacy
    tz = timezone.get_current_timezone()  # Asia/Beirut
    today = timezone.localdate()
    this_monday = today - timedelta(days=today.weekday())
    first_monday = this_monday - timedelta(weeks=weeks - 1)
    start = timezone.make_aware(datetime.combine(first_monday, time.min), tz)

    # 1) Revenue and number of sales, per day. Revenue is what customers paid (after discount).
    sales_by_day = (
        Sale.objects
        .filter(pharmacy=pharmacy, created_at__gte=start)
        .annotate(day=TruncDate('created_at', tzinfo=tz))
        .values('day')
        .annotate(count=Count('id'), revenue=Sum('total'))
    )

    # 2) Cost of what was sold, per day: quantity x buying price on the day of the sale.
    #    Old sales saved before unit_cost existed use the medicine's current cost (marked estimated).
    line_cost = ExpressionWrapper(F('quantity') * Coalesce('unit_cost', 'medicine__cost'), output_field=MONEY)
    cost_by_day = (
        SaleItem.objects
        .filter(sale__pharmacy=pharmacy, sale__created_at__gte=start)
        .annotate(day=TruncDate('sale__created_at', tzinfo=tz))
        .values('day')
        .annotate(cost=Sum(line_cost), estimated=Count('id', filter=Q(unit_cost__isnull=True)))
    )

    # 3) Add the days up into weeks. Every week starts with zeros.
    report = {
        first_monday + timedelta(weeks=i): {
            'count': 0, 'revenue': Decimal('0'), 'cost': Decimal('0'), 'estimated': False,
        }
        for i in range(weeks)
    }

    def week_of(day):
        return day - timedelta(days=day.weekday())

    for row in sales_by_day:
        week = report.get(week_of(row['day']))
        if week is not None:  # ignore sales dated in the future (wrong server clock)
            week['count'] += row['count']
            week['revenue'] += Decimal(row['revenue'] or 0)
    for row in cost_by_day:
        week = report.get(week_of(row['day']))
        if week is not None:
            week['cost'] += Decimal(row['cost'] or 0)
            week['estimated'] = week['estimated'] or row['estimated'] > 0

    results = []
    for monday in sorted(report, reverse=True):
        week = report[monday]
        revenue = week['revenue'].quantize(CENTS)
        cost = week['cost'].quantize(CENTS)
        profit = revenue - cost
        results.append({
            'week_start': monday.isoformat(),
            'week_end': (monday + timedelta(days=6)).isoformat(),
            'is_current': monday == this_monday,
            'sales_count': week['count'],
            'revenue': money(revenue),
            'cost': money(cost),
            'profit': money(profit),
            # Profit as a percent of revenue; empty when nothing was sold.
            'margin_percent': money(profit / revenue * 100) if revenue else None,
            'cost_estimated': week['estimated'],
        })

    total_revenue = sum((Decimal(w['revenue']) for w in results), Decimal('0'))
    total_cost = sum((Decimal(w['cost']) for w in results), Decimal('0'))
    total_profit = total_revenue - total_cost
    return Response({
        'pharmacy': pharmacy.name,
        'weeks': weeks,
        'totals': {
            'sales_count': sum(w['sales_count'] for w in results),
            'revenue': money(total_revenue),
            'cost': money(total_cost),
            'profit': money(total_profit),
            'margin_percent': money(total_profit / total_revenue * 100) if total_revenue else None,
            'cost_estimated': any(w['cost_estimated'] for w in results),
        },
        'results': results,
    })
