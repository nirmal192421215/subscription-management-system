import datetime
from decimal import Decimal
from django.test import TestCase, Client
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.contrib.auth.password_validation import validate_password
from brightloop_app.models import (
    User, Product, ProductVariant, TaxRule, Plan,
    QuotationTemplate, QuotationTemplateLine,
    Subscription, SubscriptionLine,
    DiscountRule, Invoice, InvoiceLine, Payment
)
from brightloop_app.services.billing_engine import BillingEngine
from brightloop_app.services.analytics_service import AnalyticsService


class Scene1AuthAndRBACTest(TestCase):
    """
    Scene 1: Account creation with strict password complexity,
    email uniqueness, and role-based access control.
    """
    def test_password_complexity_validator(self):
        # Too short (<= 8 chars)
        with self.assertRaises(ValidationError):
            validate_password("Short1!")

        # Missing uppercase
        with self.assertRaises(ValidationError):
            validate_password("nouppercase123!")

        # Missing lowercase
        with self.assertRaises(ValidationError):
            validate_password("NOLOWERCASE123!")

        # Missing special character
        with self.assertRaises(ValidationError):
            validate_password("NoSpecialChar123")

        # Valid complex password (> 8 chars, 1 upper, 1 lower, 1 special)
        try:
            validate_password("ValidP@ssword123")
        except ValidationError:
            self.fail("validate_password raised ValidationError on a valid password!")

    def test_email_uniqueness_and_roles(self):
        u1 = User.objects.create_user(
            email='test@example.com',
            password='ValidP@ssword123',
            role=User.Role.CUSTOMER
        )
        self.assertTrue(u1.is_customer_user)
        self.assertFalse(u1.is_admin_user)
        self.assertFalse(u1.is_internal_staff)

        # Duplicate email should fail
        with self.assertRaises(Exception):
            User.objects.create_user(
                email='test@example.com',
                password='AnotherP@ssword123'
            )


class Scene2ProductVariantAndPlanPolicyTest(TestCase):
    """
    Scene 2: Launching a new plan, variants (Odoo brand adds 560),
    and lifecycle policy toggles (auto close, pause, early close, renew).
    """
    def setUp(self):
        self.product = Product.objects.create(
            name="Dedicated Cloud Hosting",
            product_type=Product.ProductType.SERVICE,
            sales_price=Decimal('200.00'),
            cost_price=Decimal('60.00'),
        )
        self.variant_odoo = ProductVariant.objects.create(
            product=self.product,
            attribute_name="Brand",
            variant_value="Odoo",
            price_extra=Decimal('560.00')
        )

    def test_variant_pricing(self):
        # Base product price is 200, choosing Odoo brand adds 560 -> total 760
        self.assertEqual(self.variant_odoo.total_price, Decimal('760.00'))

    def test_plan_lifecycle_rules(self):
        plan = Plan.objects.create(
            name="Trial Plan",
            code="trial-plan",
            cost=Decimal('49.00'),
            billing_interval=Plan.BillingInterval.WEEKLY,
            min_quantity=1,
            auto_close_on_end=True,
            allow_close_early=False,
            allow_pause=False,
            allow_renewal=False
        )
        self.assertTrue(plan.auto_close_on_end)
        self.assertFalse(plan.allow_close_early)
        self.assertFalse(plan.allow_pause)
        self.assertFalse(plan.allow_renewal)


class Scene3QuoteToSubscriptionLifecycleTest(TestCase):
    """
    Scene 3: Quotation template to subscription, and lifecycle transitions:
    Draft -> Quotation -> Confirmed -> Active -> Closed.
    """
    def setUp(self):
        self.customer = User.objects.create_user(
            email='customer@corp.com',
            password='CustomerP@ss1!',
            role=User.Role.CUSTOMER,
            company_name='Corp Inc.'
        )
        self.plan = Plan.objects.create(
            name="Monthly Starter",
            code="monthly-starter-test",
            cost=Decimal('120.00'),
            billing_interval=Plan.BillingInterval.MONTHLY,
            min_quantity=1
        )
        self.product = Product.objects.create(
            name="Brightloop Core ERP",
            sales_price=Decimal('120.00')
        )
        self.template = QuotationTemplate.objects.create(
            name="Standard Template",
            plan=self.plan,
            valid_days=15
        )
        QuotationTemplateLine.objects.create(
            template=self.template,
            product=self.product,
            quantity=2,
            unit_price=Decimal('120.00')
        )

    def test_subscription_creation_from_template_and_lifecycle(self):
        sub = Subscription.objects.create(
            subscription_number="SUB-TEST-001",
            customer=self.customer,
            plan=self.plan,
            start_date=timezone.now().date(),
            status=Subscription.Status.DRAFT
        )
        SubscriptionLine.objects.create(
            subscription=sub,
            product=self.product,
            quantity=2,
            unit_price=Decimal('120.00')
        )
        self.assertEqual(sub.calculate_grand_total(), Decimal('240.00'))

        # Lifecycle steps
        sub.status = Subscription.Status.QUOTATION
        sub.save()
        self.assertEqual(sub.status, Subscription.Status.QUOTATION)

        sub.status = Subscription.Status.CONFIRMED
        sub.save()
        self.assertEqual(sub.status, Subscription.Status.CONFIRMED)

        sub.status = Subscription.Status.ACTIVE
        sub.save()
        self.assertEqual(sub.status, Subscription.Status.ACTIVE)

        sub.status = Subscription.Status.CLOSED
        sub.save()
        self.assertEqual(sub.status, Subscription.Status.CLOSED)


class Scene4BillingEngineAndIdempotencyTest(TestCase):
    """
    Scene 4: Billing day batch execution, automatic tax calculation,
    and strict idempotency (nothing billed twice).
    """
    def setUp(self):
        self.tax = TaxRule.objects.create(name="Standard Tax", rate=Decimal('10.00'))
        self.customer = User.objects.create_user(
            email='acme@test.com',
            password='ValidP@ssword1!',
            role=User.Role.CUSTOMER
        )
        self.plan = Plan.objects.create(
            name="Monthly Plan",
            code="monthly-test",
            cost=Decimal('100.00'),
            billing_interval=Plan.BillingInterval.MONTHLY
        )
        self.product = Product.objects.create(
            name="ERP Seat",
            sales_price=Decimal('100.00')
        )
        self.today = timezone.now().date()
        self.sub = Subscription.objects.create(
            subscription_number="SUB-BILL-001",
            customer=self.customer,
            plan=self.plan,
            status=Subscription.Status.ACTIVE,
            start_date=self.today,
            next_billing_date=self.today
        )
        SubscriptionLine.objects.create(
            subscription=self.sub,
            product=self.product,
            quantity=1,
            unit_price=Decimal('100.00'),
            tax_rule=self.tax
        )

    def test_idempotent_billing(self):
        # First billing run: creates invoice with 10% tax
        inv, msg = BillingEngine.bill_subscription(self.sub, target_date=self.today)
        self.assertIsNotNone(inv)
        self.assertEqual(inv.subtotal, Decimal('100.00'))
        self.assertEqual(inv.tax_amount, Decimal('10.00'))
        self.assertEqual(inv.total_amount, Decimal('110.00'))

        # Second immediate billing run: MUST BE IDEMPOTENT (skipped!)
        inv2, msg2 = BillingEngine.bill_subscription(self.sub, target_date=self.today)
        self.assertIsNone(inv2)
        self.assertIn("not due yet", msg2)

        # Total invoice count for this subscription must remain exactly 1
        self.assertEqual(Invoice.objects.filter(subscription=self.sub).count(), 1)


class Scene5DiscountRulesTest(TestCase):
    """
    Scene 5: Admin discount rules auto-applied on invoice.
    """
    def setUp(self):
        self.customer = User.objects.create_user(
            email='discount@test.com',
            password='ValidP@ssword1!',
            role=User.Role.CUSTOMER
        )
        self.plan = Plan.objects.create(
            name="Monthly Plan",
            code="monthly-disc",
            cost=Decimal('500.00'),
            billing_interval=Plan.BillingInterval.MONTHLY
        )
        self.product = Product.objects.create(
            name="Enterprise Software",
            sales_price=Decimal('500.00')
        )
        self.today = timezone.now().date()
        self.sub = Subscription.objects.create(
            subscription_number="SUB-DISC-001",
            customer=self.customer,
            plan=self.plan,
            status=Subscription.Status.ACTIVE,
            start_date=self.today,
            next_billing_date=self.today
        )
        SubscriptionLine.objects.create(
            subscription=self.sub,
            product=self.product,
            quantity=1,
            unit_price=Decimal('500.00')
        )
        # 20% discount rule with min spend $400
        self.discount = DiscountRule.objects.create(
            name="Summer 20%",
            code="SUMMER20",
            discount_type=DiscountRule.DiscountType.PERCENTAGE,
            discount_value=Decimal('20.00'),
            min_purchase_amount=Decimal('400.00'),
            start_date=self.today - datetime.timedelta(days=1),
            end_date=self.today + datetime.timedelta(days=30),
            max_uses=10,
            scope=DiscountRule.Scope.SUBSCRIPTION
        )

    def test_auto_applied_discount(self):
        inv, msg = BillingEngine.bill_subscription(self.sub, target_date=self.today)
        self.assertIsNotNone(inv)
        self.assertEqual(inv.discount_rule, self.discount)
        # 20% off 500 = 100 discount
        self.assertEqual(inv.discount_amount, Decimal('100.00'))
        self.assertEqual(inv.total_amount, Decimal('400.00'))
        # Usage counter incremented
        self.discount.refresh_from_db()
        self.assertEqual(self.discount.current_uses, 1)


class Scene6PaymentCollectionAndOverdueTest(TestCase):
    """
    Scene 6: Recording payments, partial payments, and overdue tracking.
    """
    def setUp(self):
        self.customer = User.objects.create_user(
            email='pay@test.com',
            password='ValidP@ssword1!',
            role=User.Role.CUSTOMER
        )
        self.today = timezone.now().date()
        self.invoice = Invoice.objects.create(
            invoice_number="INV-PAY-001",
            customer=self.customer,
            invoice_date=self.today - datetime.timedelta(days=20),
            due_date=self.today - datetime.timedelta(days=5), # 5 days overdue
            status=Invoice.Status.CONFIRMED,
            subtotal=Decimal('300.00'),
            total_amount=Decimal('300.00'),
            balance_due=Decimal('300.00')
        )

    def test_overdue_detection_and_payment_settlement(self):
        self.assertTrue(self.invoice.is_overdue())
        self.assertEqual(self.invoice.overdue_days, 5)

        # Record partial payment of $100
        Payment.objects.create(
            invoice=self.invoice,
            amount=Decimal('100.00'),
            payment_method=Payment.PaymentMethod.BANK_TRANSFER,
            transaction_reference="TXN-PARTIAL"
        )
        self.invoice.refresh_from_db()
        self.assertEqual(self.invoice.amount_paid, Decimal('100.00'))
        self.assertEqual(self.invoice.balance_due, Decimal('200.00'))
        self.assertEqual(self.invoice.status, Invoice.Status.CONFIRMED)

        # Settle remainder of $200
        Payment.objects.create(
            invoice=self.invoice,
            amount=Decimal('200.00'),
            payment_method=Payment.PaymentMethod.CREDIT_CARD,
            transaction_reference="TXN-SETTLE"
        )
        self.invoice.refresh_from_db()
        self.assertEqual(self.invoice.amount_paid, Decimal('300.00'))
        self.assertEqual(self.invoice.balance_due, Decimal('0.00'))
        self.assertEqual(self.invoice.status, Invoice.Status.PAID)
        self.assertFalse(self.invoice.is_overdue())


class Scene7FinanceAnalyticsAndPerformanceTest(TestCase):
    """
    Scene 7: Finance lead overview answering:
    - Active subscriptions count
    - Revenue collected
    - Amount still owed
    - Overdue invoices
    - Response time < 2 seconds benchmark!
    """
    def test_finance_overview_kpis_and_latency(self):
        overview = AnalyticsService.get_finance_overview()
        self.assertIn('active_subscriptions_count', overview)
        self.assertIn('mrr', overview)
        self.assertIn('arr', overview)
        self.assertIn('total_revenue_collected', overview)
        self.assertIn('total_still_owed', overview)
        self.assertIn('overdue_count', overview)
        self.assertIn('query_latency_ms', overview)

        # Requirement: "every page should still respond in under two seconds."
        # Verify query latency is well under 2000 ms (2 seconds):
        self.assertLess(overview['query_latency_ms'], 2000.0, "Analytics latency exceeded 2000 ms SLA!")
