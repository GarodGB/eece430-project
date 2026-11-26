from decimal import Decimal

from django.db import transaction
from django.db.models import Count, Max, Sum
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from accounts.models import Pharmacy
from accounts.permissions import IsPharmacyStaff
from .models import DAMAN_SHARE_PERCENT, DamanStatement, InsuranceClaim


def money(value):
    # Always 2 decimals ("80.00"), whatever the database returns.
    return str(Decimal(value or 0).quantize(Decimal('0.01')))


def claim_data(claim):
    sale = claim.sale
    return {
        'id': claim.id,
        'sale_id': sale.id,
        'sale_date': sale.created_at,
        'daman_number': claim.policy_number,
        'sale_total': money(sale.total),
        'daman_pays': money(claim.amount),
        'customer_paid': money(claim.customer_paid),
        'status': claim.status,
        'statement_number': claim.statement.number if claim.statement_id else None,
    }


def statement_data(statement, with_claims=False):
    data = {
        'id': statement.id,
        'number': statement.number,
        'status': statement.status,
        'total': money(statement.total),
        'claims_count': getattr(statement, 'claims_count', None),
        'created_at': statement.created_at,
        'created_by': statement.created_by.username if statement.created_by else None,
        'paid_at': statement.paid_at,
        'paid_by': statement.paid_by.username if statement.paid_by else None,
        'pharmacy_name': statement.pharmacy.name,
        'pharmacy_address': statement.pharmacy.address,
        'pharmacy_phone': statement.pharmacy.phone,
    }
    if with_claims:
        claims = list(statement.claims.select_related('sale').order_by('sale__created_at', 'id'))
        data['claims'] = [claim_data(claim) for claim in claims]
        data['claims_count'] = len(claims)
    return data


def my_claims(request):
    return InsuranceClaim.objects.filter(sale__pharmacy=request.user.pharmacy)


@api_view(['GET'])
@permission_classes([IsPharmacyStaff])
def daman_overview(request):
    """PHAR-16: totals by status, and the unpaid claims waiting to go on a statement."""
    totals = {key: {'count': 0, 'amount': '0.00'} for key, _ in InsuranceClaim.STATUS_CHOICES}
    for row in my_claims(request).values('status').annotate(count=Count('id'), amount=Sum('amount')):
        totals[row['status']] = {'count': row['count'], 'amount': money(row['amount'])}
    unpaid = my_claims(request).filter(status=InsuranceClaim.UNPAID).select_related('sale').order_by('sale__created_at', 'id')
    return Response({
        'insurer': 'Daman',
        'daman_share_percent': str(DAMAN_SHARE_PERCENT),
        'totals': totals,
        'unpaid_claims': [claim_data(claim) for claim in unpaid],
    })


@api_view(['GET', 'POST'])
@permission_classes([IsPharmacyStaff])
def daman_statements(request):
    pharmacy = request.user.pharmacy

    if request.method == 'GET':
        statements = (DamanStatement.objects.filter(pharmacy=pharmacy)
                      .select_related('pharmacy', 'created_by', 'paid_by')
                      .annotate(claims_count=Count('claims')).order_by('-number'))
        return Response([statement_data(s) for s in statements])

    # POST: put ALL unpaid claims on one new statement, ready to print and take to Daman.
    with transaction.atomic():
        # Lock the pharmacy so two clicks can't create two statements with the same claims or number.
        Pharmacy.objects.select_for_update().get(pk=pharmacy.pk)
        unpaid = list(my_claims(request).select_for_update().filter(status=InsuranceClaim.UNPAID))
        if not unpaid:
            return Response({'error': 'There are no unpaid Daman claims to put on a statement.'},
                            status=status.HTTP_400_BAD_REQUEST)
        last = DamanStatement.objects.filter(pharmacy=pharmacy).aggregate(last=Max('number'))['last'] or 0
        statement = DamanStatement.objects.create(
            pharmacy=pharmacy,
            number=last + 1,
            total=sum((claim.amount for claim in unpaid), Decimal('0')),
            created_by=request.user,
        )
        InsuranceClaim.objects.filter(pk__in=[claim.pk for claim in unpaid]).update(
            status=InsuranceClaim.SENT, statement=statement)

    return Response(statement_data(statement, with_claims=True), status=status.HTTP_201_CREATED)


@api_view(['GET'])
@permission_classes([IsPharmacyStaff])
def daman_statement_detail(request, statement_id):
    """One statement with all its claims, for printing."""
    statement = get_object_or_404(
        DamanStatement.objects.select_related('pharmacy', 'created_by', 'paid_by'),
        pk=statement_id, pharmacy=request.user.pharmacy)
    return Response(statement_data(statement, with_claims=True))


@api_view(['POST'])
@permission_classes([IsPharmacyStaff])
def mark_statement_paid(request, statement_id):
    """Daman paid this statement: it and all its claims become paid."""
    with transaction.atomic():
        statement = get_object_or_404(
            DamanStatement.objects.select_for_update(), pk=statement_id, pharmacy=request.user.pharmacy)
        if statement.status == DamanStatement.PAID:
            return Response({'error': f'Statement #{statement.number} is already marked as paid.'},
                            status=status.HTTP_400_BAD_REQUEST)
        statement.status = DamanStatement.PAID
        statement.paid_at = timezone.now()
        statement.paid_by = request.user
        statement.save(update_fields=['status', 'paid_at', 'paid_by'])
        statement.claims.update(status=InsuranceClaim.PAID)

    statement = DamanStatement.objects.select_related('pharmacy', 'created_by', 'paid_by').get(pk=statement.pk)
    return Response(statement_data(statement, with_claims=True))
