# Brightloop Software &bull; Subscription & Recurring Billing Management System
### *Unified Subscription Lifecycle & Automated Financial Engine for the Odoo Hackathon*

---

## 🌟 Executive Overview
**Brightloop Software** is a full-featured, enterprise-grade subscription management and recurring billing web platform built with **Python 3.13 and Django 6**. It was engineered specifically to solve the operational chaos of managing multi-tier subscriptions, quotes, variable billing intervals, auto-prorated invoicing, manual payment collection, tax compliance, and overdue receivables.

With a sub-2-second query response SLA, high-fidelity PDF generation, and an automated idempotent billing engine, Brightloop empowers leadership, sales, billing reps, and customers within a unified, modern interface inspired by **Odoo** (#714B67 brand purple).

---

## 🚀 Quick Start Guide

### 1. Prerequisites
- **Python**: 3.11+ (Tested on Python 3.13)
- **Virtual Environment**: Included in `./venv/`
- **Database**: SQLite (Zero-configuration, instant portability)

### 2. Run the Web Application
```bash
# Navigate to the repository root:
cd "/Users/jabezwesley/Documents/odoo hacks"

# Start the Django development server:
./venv/bin/python manage.py runserver 8000
```
Open **[http://localhost:8000](http://localhost:8000)** in your browser.

---

## 🎭 Pre-Loaded Demo Personas & Instant Switcher
A built-in **Quick Role Switcher** in the top navigation bar allows judges and evaluators to switch between personas with a single click without manually logging out:

| Role | Email | Password | Persona & Privileges |
| :--- | :--- | :--- | :--- |
| **Administrator** | `admin@brightloop.com` | `Admin@12345` | **Elena Vance (CEO / Admin)**: Full administrative oversight, staff directory, audit logs, tax rules, and discount management. |
| **Sales Rep (Staff)** | `sarah@brightloop.com` | `Staff@12345` | **Sarah Jenkins (Sales Lead)**: Quotation templates, converting quotes to active subscriptions, PDF quote generation. |
| **Billing Specialist** | `david@brightloop.com` | `Staff@12345` | **David Kim (Billing Specialist)**: Billing day batch execution, dunning follow-up, recording payments, reconciling invoices. |
| **Customer (Enterprise)** | `acme@acmecorp.com` | `Acme@12345` | **Acme Corporation**: Enterprise Yearly plan (15 seats) with multi-product add-ons. |
| **Customer (SMB)** | `bistro@cornercafe.com` | `Corner@12345` | **Corner Cafe & Bakery**: Monthly Starter plan with self-service portal controls. |
| **Customer (Overdue)** | `spark@sparklabs.com` | `Spark@12345` | **Spark Labs Inc.**: Active subscription with an overdue invoice requiring follow-up. |

> **Password Complexity Rule**: All passwords satisfy `BrightloopPasswordValidator` (>8 characters, 1 uppercase, 1 lowercase, 1 special character).

---

## 🛠️ CLI Management Commands

### Run Billing Day Engine
Simulates automated daily billing with idempotency protection (never duplicate-bills):
```bash
# Run for today's date:
./venv/bin/python manage.py run_billing_day

# Or run for a specific target date:
./venv/bin/python manage.py run_billing_day --date 2026-11-15
```

### Re-seed Clean Demo Data Anytime
Wipes and populates the database with realistic business records:
```bash
./venv/bin/python manage.py seed_brightloop_data
```

### Run Comprehensive Automated Test Suite
Executes 14 unit and integration tests across all scenes and enhancements:
```bash
./venv/bin/python manage.py test
```

---

## 📋 Comprehensive Feature Catalog

### 🏢 Core Business Scenes (Problem Statement Implementation)

#### Scene 1: Authentication & Role-Based Access Control (RBAC)
- **Account Registration (`/register/`)**: Validates corporate details, email format, and unique identity.
- **Strict Password Validator (`BrightloopPasswordValidator`)**: Rejects short, weak, or non-complex passwords.
- **Password Recovery (`/forgot-password/`, `/reset-password/<token>/`)**: Secure token-based password reset valid for 24 hours.
- **Multi-Tier User Roles**:
  - `admin`: Full unrestricted control across configuration, staff, audit, and billing.
  - `staff`: Internal team access to quotes, subscriptions, invoices, and payments.
  - `customer`: Customer portal access restricted exclusively to own subscriptions and invoices.
- **Staff Directory (`/staff/`, `/staff/new/`)**: Admin interface for creating and managing internal staff members.

#### Scene 2: Product Catalog, Variant Pricing & Policy-Driven Plans
- **Product Management (`/products/`, `/products/new/`, `/products/<id>/edit/`)**:
  - Product types: Software, Add-on, Recurring Service, Hardware.
  - Sales price, cost price, and default tax association.
- **Product Variants (`/products/<id>/variants/new/`)**:
  - Dynamic attribute modeling (e.g., Brand: *Odoo*, Edition: *Enterprise*, Tier: *Premium*).
  - Price surcharges added on top of base product pricing.
- **Tax Rules (`/taxes/`, `/taxes/new/`)**:
  - Percentage-based tax engine (e.g., Standard VAT 10%, Sales Tax 8.25%).
- **Plans & Lifecycle Governance (`/plans/`, `/plans/new/`)**:
  - Billing Intervals: `Daily`, `Weekly`, `Monthly`, `Yearly`.
  - Date validity windows (`available_from`, `available_to`).
  - Minimum quantity/seat enforcement.
  - Policy Flags:
    - `auto_close_on_end`: Automatically transitions subscription to `closed` when end date is reached.
    - `allow_close_early`: Governs whether customer/staff can close ahead of term.
    - `allow_pause`: Governs pausing and resumption of billing cycles.
    - `allow_renewal`: Allows renewing expiring or closed subscriptions.

#### Scene 3: Quotation Templates & Subscription Lifecycle
- **Quotation Templates (`/templates/`, `/templates/new/`)**:
  - Pre-packaged bundles of products, quantities, and tax rules with preset validity windows (e.g., 15 days).
- **One-Click Quote Creation (`/templates/<id>/create-quote/`)**:
  - Automatically clones template lines into a customized quotation for any selected customer.
- **Subscription Lifecycle Engine**:
  - Full state progression: `Draft` &rarr; `Quotation` &rarr; `Confirmed` &rarr; `Active` &rarr; `Paused` &rarr; `Closed`.
  - Dynamic recurring totals calculation (subtotal, taxes, grand recurring total).
  - Dynamic line item editor: add products/variants, modify quantities, delete lines.
- **Professional PDF Quotation Download (`/subscriptions/<id>/pdf/`)**:
  - Generated dynamically via ReportLab with customer address, itemized breakdown, and terms.

#### Scene 4: Automated Billing Day Engine & Invoicing
- **Batch Billing Day (`/billing-day/` & CLI)**:
  - Scans all `active` subscriptions due on or before target date.
  - Generates official sequence-numbered invoices (`INV-YYYY-XXXXX`).
  - Advances subscription `next_billing_date` based on interval (`monthly`, `yearly`, etc.).
  - Handles `auto_close_on_end` lifecycle for expiring contracts.
  - **Strict Idempotency**: Prevents double-billing even if executed multiple times on the same date.
- **Invoice Register (`/invoices/`)**:
  - Status filters (`Draft`, `Confirmed`, `Paid`, `Cancelled`).
  - Search by invoice number, customer name, and email.
  - Overdue highlight pill and quick action buttons.
- **Invoice Lifecycle & PDF Dispatch**:
  - State machine: `Draft` &rarr; `Confirmed` &rarr; `Paid` or `Cancelled`.
  - ReportLab PDF invoice generation (`/invoices/<id>/pdf/`).
  - Printable invoice view (`/invoices/<id>/print/`).
  - Simulated send via email (`/invoices/<id>/send/`).

#### Scene 5: Flexible Discount & Promo Engine
- **Discount Rules (`/discounts/`, `/discounts/new/`)**:
  - Discount Types: `Percentage (%)` or `Fixed Amount ($)`.
  - Application Scopes: `Whole Subscription` or `Specific Product`.
  - Guard conditions: Minimum invoice purchase amount, minimum seat quantity, date range validity (`start_date` to `end_date`), and maximum redemptions count.
  - Automatic redemption counter tracking with auto-deactivation upon reaching maximum uses.
  - One-click active/inactive toggle (`/discounts/<id>/toggle/`).

#### Scene 6: Payment Recording & Receivables Reconciliation
- **Payment Collection (`/invoices/<id>/payment/`)**:
  - Supports multiple payment channels: `Credit Card`, `Bank Transfer`, `PayPal`, `Cash`, `Check`.
  - Captures transaction reference codes and audit notes.
  - Automatically updates invoice `amount_paid`, reduces `balance_due`, and automatically transitions invoice status to `Paid` upon full balance settlement.
- **Customer Portal Self-Service (`/portal/`)**:
  - Customer overview dashboard with active subscriptions and pending invoices.
  - Secure simulated payment checkout (`/portal/invoices/<id>/pay/`).
  - Self-service subscription controls: `Pause`, `Resume`, `Close Early`, and `Renew` (enforced by Plan policy rules).

#### Scene 7: Finance Lead Executive Command Center
- **Executive Analytics Dashboard (`/finance/`)**:
  - Answers the 4 core financial leadership questions in real time:
    1. *How many subscriptions are active?* (Includes live MRR and ARR computations).
    2. *How much revenue came in?* (Settled cash payments in period).
    3. *How much is still owed?* (Outstanding receivable balance on confirmed invoices).
    4. *Which invoices are overdue?* (Days overdue, customer details, immediate chase button).
  - Filter Ribbon: Filter by start date, end date, subscription plan, and customer.
  - **Sub-2-Second Performance SLA**: Real-time query timer badge displaying exact milliseconds elapsed (typically `< 25ms`).

---

### ✨ Production Enhancements

#### Enhancement A: Interactive Chart.js Dashboards
- **Revenue vs Invoiced Bar Chart**: 6-month visual comparison of billed receivables versus settled cash collected.
- **Subscription Status Donut**: Color-coded breakdown of subscriptions across active, quotation, confirmed, paused, and closed states.
- **Overdue Aging Buckets**: Horizontal bar chart bucketing overdue debt into `1-30 days`, `31-60 days`, and `60+ days`.
- **Live JSON API (`/api/chart-data/`)**: Powers asynchronous dashboard rendering.

#### Enhancement C: Mobile Responsive Navigation
- Collapsible mobile hamburger drawer for mobile devices and tablets.
- Sleek full-width adaptive top bar (`max-w-[1600px]`) preventing UI clipping or overflow on compact laptop screens (e.g. 13" MacBook Air).
- User profile name truncation (`truncate`) ensuring logout and switcher controls are never pushed offscreen.

#### Enhancement F: 3-Step Customer Onboarding Wizard
- `/onboarding/` &bull; **Step 1: Plan Selection**: Compare features, intervals, and pricing.
- `/onboarding/step2/` &bull; **Step 2: Configuration**: Configure quantity of seats, desired start date, and setup instructions.
- `/onboarding/step3/` &bull; **Step 3: Confirmation**: Review recurring cost preview, next billing calculation, and 1-click instant subscription activation.

#### Enhancement H: Comprehensive Admin Audit Log
- **Audit Log Interface (`/audit-log/` & `/admin/audit-log/`)**:
  - Tracks timestamped events: `User Login`, `Status Change`, `Payment Recorded`, `Invoice Sent`, `Subscription Created`, `Subscription Closed`, `Billing Day Run`, `Dunning Email Sent`, `Data Export`.
  - Captures actor identity, target object model, primary key, detailed narrative description, and client IP address.
  - Filterable by event type, actor, and free-text search.

#### Enhancement I: Automated Dunning Campaign
- **Dunning Management Center (`/dunning/`)**:
  - Automatically identifies delinquent accounts and computes days overdue.
  - Three escalation tiers:
    - **Day 1**: Initial friendly payment reminder.
    - **Day 7**: Urgent follow-up notice.
    - **Day 14**: Final notice before service interruption.
  - Prevents duplicate dispatches per level and logs every notification to the audit log.

#### Enhancement J: 1-Click CSV Data Exports
- **Export Invoices (`/export/invoices.csv`)**: Full invoice ledger with dates, status, subtotal, discounts, taxes, amount paid, balance due, and plan names.
- **Export Subscriptions (`/export/subscriptions.csv`)**: Complete subscription registry with billing intervals, terms, and recurring values.
- **Export Payments (`/export/payments.csv`)**: Reconciled payment logs with payment methods, transaction references, and recording user.

#### Enhancement K: Customer Account Statement PDF
- **Statement Generator (`/customers/<id>/statement.pdf`)**:
  - Generates a customer account statement summarizing total invoiced, total paid, and current outstanding balance.
  - Itemizes complete invoice history and full payment history in a branded ReportLab PDF.

#### Enhancement L: Renewal Reminder Badges & Alerts
- Real-time pulse notification badge in the navigation bar displaying overdue invoice count.
- Status badges and visual warnings for subscriptions expiring within 30 days.

---

## 🏗️ Technical Architecture & Key Files

```
odoo hacks/
├── manage.py                                 # Django CLI entrypoint
├── brightloop_project/
│   ├── settings.py                           # App settings, custom User model, auth validators
│   ├── urls.py                               # Top-level URL routing & admin safety handlers
│   └── wsgi.py
├── brightloop_app/
│   ├── models.py                             # 14 normalized ORM models (User, Subscriptions, Invoices, Audit, Dunning)
│   ├── urls.py                               # App routes (Catalog, Subscriptions, Invoices, Onboarding, Exports)
│   ├── tests.py                              # 14 automated tests covering all 7 scenes and enhancements
│   ├── services/
│   │   ├── billing_engine.py                 # Batch billing, tax/discount application, idempotency
│   │   ├── analytics_service.py              # MRR/ARR, financial KPIs, query benchmarking (<2s SLA)
│   │   └── pdf_service.py                    # ReportLab vector PDF generator (Quotes, Invoices, Statements)
│   ├── views/
│   │   ├── auth_views.py                     # Login, register, password reset, demo persona switcher
│   │   ├── catalog_views.py                  # Products, variants, tax rules, plans
│   │   ├── subscription_views.py             # Quotation templates, subscription lifecycles, PDF quote
│   │   ├── billing_views.py                  # Invoices, billing day batch, payments, discounts
│   │   ├── finance_views.py                  # Executive command center, filters, KPIs
│   │   ├── portal_views.py                   # Customer self-service, pay invoice, pause/resume
│   │   └── enhancement_views.py              # Audit log, dunning campaign, onboarding wizard, CSV exports
│   ├── templates/brightloop/                 # 30+ responsive Tailwind templates
│   │   ├── base.html                         # Adaptive responsive navbar, mobile drawer, role switcher
│   │   ├── finance/dashboard.html            # Executive center with Chart.js charts
│   │   ├── admin/audit_log.html              # Timestamped audit ledger
│   │   ├── admin/dunning_dashboard.html      # Overdue chase escalation
│   │   └── onboarding/                       # 3-step customer onboarding wizard
│   └── management/commands/
│       ├── seed_brightloop_data.py           # Rich demo data seeder
│       └── run_billing_day.py                # Billing day CLI tool
```

---

## 🎨 Design System & Branding
- **Primary Brand Color**: Odoo Corporate Purple (`#714B67`)
- **Accent Color**: Teal (`#017E84`)
- **Typography & Framework**: Tailwind CSS with FontAwesome 6 icons and Chart.js visualizations
- **Favicon**: Inline SVG animated emoji (`🔄`) with zero external asset dependencies

---

## 🧪 Verification & Test Results
```bash
./venv/bin/python manage.py test
```
```text
Found 14 test(s).
Creating test database for alias 'default'...
System check identified no issues (0 silenced).
..............
----------------------------------------------------------------------
Ran 14 tests in 16.388s

OK
Destroying test database for alias 'default'...
```
All 14 tests pass, certifying password compliance, product variant math, plan interval scheduling, idempotency, discount bounds, overdue calculations, audit logging, onboarding, and PDF statement rendering.
