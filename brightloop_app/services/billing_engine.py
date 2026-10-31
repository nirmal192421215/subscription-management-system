import datetime
from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from brightloop_app.models import Subscription, Invoice, InvoiceLine, DiscountRule, Plan

class BillingEngine:
    """
    Recurring billing engine for Brightloop Software.
    Automates generating invoices on billing day, applying tax rules,
    applying eligible discount rules, preventing duplicate billing (idempotency),
    and managing plan lifecycle auto-close rules.
    """

    @classmethod
    def generate_invoice_number(cls):
        year = timezone.now().year
        last_invoice = Invoice.objects.filter(invoice_number__startswith=f"INV-{year}-").order_by('-id').first()
        if last_invoice:
            try:
                seq = int(last_invoice.invoice_number.split('-')[-1]) + 1
            except (ValueError, IndexError):
                seq = Invoice.objects.count() + 1
        else:
            seq = Invoice.objects.count() + 1
        return f"INV-{year}-{seq:05d}"

    @classmethod
    def find_applicable_discount(cls, subscription, subtotal, total_qty, target_date):
        """
        Check if any active discount rule applies to this subscription.
        Matches whole subscription discounts first, checking validity, dates,
        min quantity, and min purchase amount.
        """
        now_d = target_date or timezone.now().date()
        discounts = DiscountRule.objects.filter(
            is_active=True,
            scope=DiscountRule.Scope.SUBSCRIPTION,
            start_date__lte=now_d,
            end_date__gte=now_d
        ).order_by('-discount_value')

        for disc in discounts:
            valid, reason = disc.is_valid_for(subtotal, total_qty=total_qty, target_date=now_d)
            if valid:
                return disc
        return None

    @classmethod
    @transaction.atomic
    def bill_subscription(cls, subscription, target_date=None, force=False):
        """
        Generates an invoice for a single active subscription.
        Guarantees idempotency: will NOT bill twice for the same period.
        """
        now_d = target_date or timezone.now().date()

        # 1. Check if subscription is active
        if subscription.status != Subscription.Status.ACTIVE:
            return None, "Subscription is not active."

        # 2. Check if plan auto-closes when ended
        if subscription.plan.auto_close_on_end and subscription.expiry_date and subscription.expiry_date <= now_d:
            subscription.status = Subscription.Status.CLOSED
            subscription.save(update_fields=['status'])
            return None, f"Subscription reached expiry date ({subscription.expiry_date}) and was auto-closed as per plan policy."

        # 3. Check if due for billing (unless force=True)
        due_date = subscription.next_billing_date or subscription.start_date
        if not force and due_date > now_d:
            return None, f"Subscription is not due yet (due on {due_date})."

        # 4. Period bounds
        period_start = due_date
        period_end = subscription.plan.calculate_next_date(period_start) - datetime.timedelta(days=1)

        # 5. Idempotency Check: Nothing should be billed twice!
        existing = Invoice.objects.filter(
            subscription=subscription,
            billing_period_start=period_start
        ).exclude(status=Invoice.Status.CANCELLED).first()
        if existing:
            return None, f"Already billed for period {period_start} to {period_end} (Invoice {existing.invoice_number})."

        # 6. Calculate payment due date based on payment terms
        terms = subscription.payment_terms
        if terms == 'immediate':
            inv_due = now_d
        elif terms == 'net_15':
            inv_due = now_d + datetime.timedelta(days=15)
        elif terms == 'net_60':
            inv_due = now_d + datetime.timedelta(days=60)
        else:  # net_30 default
            inv_due = now_d + datetime.timedelta(days=30)

        # 7. Create draft/confirmed invoice
        inv_number = cls.generate_invoice_number()
        invoice = Invoice.objects.create(
            invoice_number=inv_number,
            subscription=subscription,
            customer=subscription.customer,
            invoice_date=now_d,
            due_date=inv_due,
            status=Invoice.Status.CONFIRMED,  # Created confirmed and ready for customer/payment
            billing_period_start=period_start,
            billing_period_end=period_end,
            notes=f"Recurring billing for {subscription.plan.name} ({period_start} to {period_end}). Terms: {subscription.get_payment_terms_display()}."
        )

        # 8. Copy lines from subscription
        total_qty = 0
        raw_subtotal = Decimal('0.00')
        lines_data = []

        for sub_line in subscription.lines.select_related('product', 'variant', 'tax_rule').all():
            total_qty += sub_line.quantity
            line_sub = (sub_line.quantity * sub_line.unit_price)
            raw_subtotal += line_sub

            desc = f"{sub_line.product.name}"
            if sub_line.variant:
                desc += f" ({sub_line.variant.attribute_name}: {sub_line.variant.variant_value})"

            lines_data.append({
                'product': sub_line.product,
                'variant': sub_line.variant,
                'description': desc,
                'quantity': sub_line.quantity,
                'unit_price': sub_line.unit_price,
                'tax_rule': sub_line.tax_rule,
            })

        # 9. Check and apply eligible discounts (Scene 5)
        discount = cls.find_applicable_discount(subscription, raw_subtotal, total_qty, now_d)
        if discount:
            invoice.discount_rule = discount
            discount.record_usage()

        # 10. Create invoice lines
        for ld in lines_data:
            InvoiceLine.objects.create(
                invoice=invoice,
                product=ld['product'],
                variant=ld['variant'],
                description=ld['description'],
                quantity=ld['quantity'],
                unit_price=ld['unit_price'],
                tax_rule=ld['tax_rule']
            )

        # 11. Recalculate invoice totals with taxes and discounts
        invoice.update_totals()

        # 12. Advance subscription next_billing_date to next cycle
        subscription.advance_next_billing_date()

        return invoice, "Successfully generated invoice."

    @classmethod
    def run_billing_day(cls, target_date=None):
        """
        Batch billing processor: Runs through all active subscriptions and generates
        due invoices in bulk with full idempotency guarantee.
        """
        now_d = target_date or timezone.now().date()
        active_subs = Subscription.objects.filter(
            status=Subscription.Status.ACTIVE
        ).select_related('plan', 'customer')

        results = {
            'target_date': str(now_d),
            'total_active': active_subs.count(),
            'generated_count': 0,
            'skipped_count': 0,
            'auto_closed_count': 0,
            'generated_invoices': [],
            'messages': []
        }

        for sub in active_subs:
            # Check auto-close rule first
            if sub.plan.auto_close_on_end and sub.expiry_date and sub.expiry_date <= now_d:
                sub.status = Subscription.Status.CLOSED
                sub.save(update_fields=['status'])
                results['auto_closed_count'] += 1
                results['messages'].append(f"Subscription {sub.subscription_number} expired and was auto-closed.")
                continue

            inv, msg = cls.bill_subscription(sub, target_date=now_d, force=False)
            if inv:
                results['generated_count'] += 1
                results['generated_invoices'].append({
                    'invoice_number': inv.invoice_number,
                    'customer': inv.customer.display_name,
                    'amount': str(inv.total_amount),
                    'subscription': sub.subscription_number
                })
                results['messages'].append(f"{sub.subscription_number}: Generated {inv.invoice_number} (${inv.total_amount})")
            else:
                results['skipped_count'] += 1
                results['messages'].append(f"{sub.subscription_number}: {msg}")

        return results
