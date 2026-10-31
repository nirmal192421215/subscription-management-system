import datetime
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from brightloop_app.services.analytics_service import AnalyticsService
from brightloop_app.models import Plan, User
from brightloop_app.views.catalog_views import internal_required

@login_required
@internal_required
def finance_dashboard_view(request):
    """
    Scene 7: The finance lead executive command center.
    Answers:
    1. How many subscriptions are active?
    2. How much revenue came in?
    3. How much is still owed?
    4. Which invoices are overdue?
    With filters (date ranges, plans, customers) and responsive < 2s performance.
    """
    start_date_str = request.GET.get('start_date')
    end_date_str = request.GET.get('end_date')
    plan_id = request.GET.get('plan')
    customer_id = request.GET.get('customer')

    start_date = datetime.date.fromisoformat(start_date_str) if start_date_str else None
    end_date = datetime.date.fromisoformat(end_date_str) if end_date_str else None

    overview = AnalyticsService.get_finance_overview(
        start_date=start_date,
        end_date=end_date,
        plan_id=plan_id,
        customer_id=customer_id
    )

    plans = Plan.objects.filter(is_active=True)
    customers = User.objects.filter(role=User.Role.CUSTOMER).order_by('company_name')

    return render(request, 'brightloop/finance/dashboard.html', {
        'overview': overview,
        'plans': plans,
        'customers': customers,
        'start_date': start_date_str,
        'end_date': end_date_str,
        'selected_plan': plan_id,
        'selected_customer': customer_id,
    })
