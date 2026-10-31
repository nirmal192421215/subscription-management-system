from django.urls import path
from brightloop_app.views import (
    auth_views, portal_views, staff_views,
    catalog_views, subscription_views, billing_views, finance_views
)

urlpatterns = [
    # Auth & Quick Demo Switcher
    path('', auth_views.login_view, name='root'),
    path('login/', auth_views.login_view, name='login'),
    path('logout/', auth_views.logout_view, name='logout'),
    path('register/', auth_views.register_view, name='register'),
    path('forgot-password/', auth_views.forgot_password_view, name='forgot_password'),
    path('reset-password/<str:token>/', auth_views.reset_password_view, name='reset_password'),
    path('demo/switch/<int:user_id>/', auth_views.demo_switch_user_view, name='demo_switch_user'),

    # Executive Finance Lead Dashboard (Scene 7)
    path('dashboard/', finance_views.finance_dashboard_view, name='dashboard'),
    path('finance/', finance_views.finance_dashboard_view, name='finance_dashboard'),

    # Customer Portal (Scene 1, 3, 4, 6)
    path('portal/', portal_views.portal_dashboard_view, name='portal_dashboard'),
    path('portal/subscriptions/', portal_views.portal_subscriptions_view, name='portal_subscriptions'),
    path('portal/subscriptions/<int:subscription_id>/', portal_views.portal_subscription_detail_view, name='portal_subscription_detail'),
    path('portal/subscriptions/<int:subscription_id>/<str:action>/', portal_views.portal_subscription_action_view, name='portal_subscription_action'),
    path('portal/invoices/', portal_views.portal_invoices_view, name='portal_invoices'),
    path('portal/invoices/<int:invoice_id>/', portal_views.portal_invoice_detail_view, name='portal_invoice_detail'),
    path('portal/invoices/<int:invoice_id>/pdf/', portal_views.portal_invoice_pdf_view, name='portal_invoice_pdf'),
    path('portal/invoices/<int:invoice_id>/pay/', portal_views.portal_pay_invoice_view, name='portal_pay_invoice'),

    # Staff Management (Admin Only - Scene 1)
    path('staff/', staff_views.staff_list_view, name='staff_list'),
    path('staff/new/', staff_views.staff_create_view, name='staff_create'),

    # Products & Variants & Taxes (Scene 2)
    path('products/', catalog_views.product_list_view, name='product_list'),
    path('products/new/', catalog_views.product_create_view, name='product_create'),
    path('products/<int:product_id>/edit/', catalog_views.product_edit_view, name='product_edit'),
    path('products/<int:product_id>/variants/new/', catalog_views.variant_create_view, name='variant_create'),
    path('variants/<int:variant_id>/delete/', catalog_views.variant_delete_view, name='variant_delete'),

    # Plans (Scene 2)
    path('plans/', catalog_views.plan_list_view, name='plan_list'),
    path('plans/new/', catalog_views.plan_create_view, name='plan_create'),
    path('plans/<int:plan_id>/edit/', catalog_views.plan_edit_view, name='plan_edit'),

    # Tax Rules (Scene 2, 4)
    path('taxes/', catalog_views.tax_rule_list_view, name='tax_rule_list'),
    path('taxes/new/', catalog_views.tax_rule_create_view, name='tax_rule_create'),

    # Quotation Templates & Subscriptions (Scene 3)
    path('templates/', subscription_views.template_list_view, name='template_list'),
    path('templates/new/', subscription_views.template_create_view, name='template_create'),
    path('templates/<int:template_id>/create-quote/', subscription_views.template_create_quote_view, name='template_create_quote'),

    path('subscriptions/', subscription_views.subscription_list_view, name='subscription_list'),
    path('subscriptions/new/', subscription_views.subscription_create_view, name='subscription_create'),
    path('subscriptions/<int:subscription_id>/', subscription_views.subscription_detail_view, name='subscription_detail'),
    path('subscriptions/<int:subscription_id>/add-line/', subscription_views.subscription_add_line_view, name='subscription_add_line'),
    path('subscriptions/line/<int:line_id>/delete/', subscription_views.subscription_delete_line_view, name='subscription_delete_line'),
    path('subscriptions/<int:subscription_id>/status/<str:new_status>/', subscription_views.subscription_status_change_view, name='subscription_status_change'),
    path('subscriptions/<int:subscription_id>/pdf/', subscription_views.subscription_pdf_view, name='subscription_pdf'),

    # Invoices & Billing Day Batch Engine (Scene 4)
    path('billing-day/', billing_views.run_billing_day_view, name='run_billing_day'),
    path('invoices/', billing_views.invoice_list_view, name='invoice_list'),
    path('invoices/<int:invoice_id>/', billing_views.invoice_detail_view, name='invoice_detail'),
    path('invoices/<int:invoice_id>/confirm/', billing_views.invoice_confirm_view, name='invoice_confirm'),
    path('invoices/<int:invoice_id>/cancel/', billing_views.invoice_cancel_view, name='invoice_cancel'),
    path('invoices/<int:invoice_id>/send/', billing_views.invoice_send_view, name='invoice_send'),
    path('invoices/<int:invoice_id>/print/', billing_views.invoice_print_view, name='invoice_print'),
    path('invoices/<int:invoice_id>/pdf/', billing_views.invoice_pdf_view, name='invoice_pdf'),
    path('invoices/<int:invoice_id>/payment/', billing_views.payment_record_view, name='payment_record'),

    # Discount Rules (Scene 5 - Admin Only)
    path('discounts/', billing_views.discount_list_view, name='discount_list'),
    path('discounts/new/', billing_views.discount_create_view, name='discount_create'),
    path('discounts/<int:discount_id>/toggle/', billing_views.discount_toggle_view, name='discount_toggle'),
]

