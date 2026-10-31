import time
from decimal import Decimal
from django.db.models import Sum, Count, Q
from django.utils import timezone
from brightloop_app.models import Subscription, Invoice, Payment, Plan

class AnalyticsService:
    @staticmethod
    def get_finance_overview(start_date=None, end_date=None, plan_id=None, customer_id=None, status_filter=None):
        start_bench = time.time()
        today = timezone.now().date()

        # 1. Base Subscription Query
        sub_query = Subscription.objects.all()
        if plan_id:
            sub_query = sub_query.filter(plan_id=plan_id)
        if customer_id:
            sub_query = sub_query.filter(customer_id=customer_id)

        # Active Subscriptions
        active_subs = sub_query.filter(status=Subscription.Status.ACTIVE).select_related('plan').prefetch_related('lines')
        active_count = active_subs.count()

        # Calculate MRR (Monthly Recurring Revenue)
        mrr = Decimal('0.00')
        for sub in active_subs:
            sub_total = sub.calculate_grand_total()
            interval = sub.plan.billing_interval
            if interval == Plan.BillingInterval.MONTHLY:
                mrr += sub_total
            elif interval == Plan.BillingInterval.YEARLY:
                mrr += (sub_total / Decimal('12.00'))
            elif interval == Plan.BillingInterval.WEEKLY:
                mrr += (sub_total * Decimal('4.3333'))
            elif interval == Plan.BillingInterval.DAILY:
                mrr += (sub_total * Decimal('30.00'))

        mrr = mrr.quantize(Decimal('0.01'))
        arr = (mrr * Decimal('12.00')).quantize(Decimal('0.01'))

        # 2. Payments Query (Revenue Came In)
        payment_query = Payment.objects.all()
        if start_date:
            payment_query = payment_query.filter(payment_date__gte=start_date)
        if end_date:
            payment_query = payment_query.filter(payment_date__lte=end_date)
        if customer_id:
            payment_query = payment_query.filter(invoice__customer_id=customer_id)

        total_revenue_collected = payment_query.aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

        # 3. Invoices Query (Total still owed & Overdue)
        inv_query = Invoice.objects.exclude(status=Invoice.Status.CANCELLED)
        if start_date:
            inv_query = inv_query.filter(invoice_date__gte=start_date)
        if end_date:
            inv_query = inv_query.filter(invoice_date__lte=end_date)
        if customer_id:
            inv_query = inv_query.filter(customer_id=customer_id)
        if plan_id:
            inv_query = inv_query.filter(subscription__plan_id=plan_id)
        if status_filter:
            inv_query = inv_query.filter(status=status_filter)

        total_invoiced = inv_query.aggregate(total=Sum('total_amount'))['total'] or Decimal('0.00')
        total_still_owed = inv_query.exclude(status=Invoice.Status.PAID).aggregate(balance=Sum('balance_due'))['balance'] or Decimal('0.00')

        # Overdue invoices: due_date < today and balance_due > 0 and status != paid/cancelled
        overdue_invoices_qs = Invoice.objects.filter(
            due_date__lt=today,
            balance_due__gt=0
        ).exclude(status__in=[Invoice.Status.PAID, Invoice.Status.CANCELLED]).select_related('customer', 'subscription')

        if customer_id:
            overdue_invoices_qs = overdue_invoices_qs.filter(customer_id=customer_id)
        if plan_id:
            overdue_invoices_qs = overdue_invoices_qs.filter(subscription__plan_id=plan_id)

        overdue_count = overdue_invoices_qs.count()
        total_overdue_amount = overdue_invoices_qs.aggregate(total=Sum('balance_due'))['total'] or Decimal('0.00')

        # Top Overdue Invoices to Chase
        overdue_list = list(overdue_invoices_qs.order_by('due_date')[:20])

        # Subscriptions by Status
        status_counts = Subscription.objects.values('status').annotate(count=Count('id')).order_by('status')

        # Plans Breakdown
        plan_breakdown = []
        for p in Plan.objects.filter(is_active=True):
            p_subs = Subscription.objects.filter(plan=p, status=Subscription.Status.ACTIVE)
            count = p_subs.count()
            plan_breakdown.append({
                'plan_name': p.name,
                'interval': p.get_billing_interval_display(),
                'active_count': count,
                'base_cost': str(p.cost),
            })

        # Payment Methods Breakdown
        payment_methods = Payment.objects.values('payment_method').annotate(
            total=Sum('amount'), count=Count('id')
        ).order_by('-total')

        elapsed_ms = round((time.time() - start_bench) * 1000, 2)

        return {
            'active_subscriptions_count': active_count,
            'mrr': mrr,
            'arr': arr,
            'total_revenue_collected': total_revenue_collected,
            'total_invoiced': total_invoiced,
            'total_still_owed': total_still_owed,
            'overdue_count': overdue_count,
            'total_overdue_amount': total_overdue_amount,
            'overdue_invoices': overdue_list,
            'status_counts': {item['status']: item['count'] for item in status_counts},
            'plan_breakdown': plan_breakdown,
            'payment_methods': payment_methods,
            'query_latency_ms': elapsed_ms,
        }
