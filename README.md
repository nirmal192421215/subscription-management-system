# Brightloop Software &bull; Subscription Management System
### *Unified Recurring Billing & Subscription Life Platform for Odoo Hackathon*

---

## 🌟 Executive Overview
**Brightloop Software** is a complete, production-grade subscription management and recurring billing web application built with **Python 3.13 and Django 6**. It provides the digital backbone for Brightloop Software, transforming manual spreadsheets, forgotten renewals, hand-typed invoices, and scattered bank statements into an automated, unified engine.

---

## 🚀 Quick Start Guide

### 1. Activate Environment & Run Application
```bash
# In the project directory:
./venv/bin/python manage.py runserver 8000
```
Open **[http://localhost:8000](http://localhost:8000)** in your browser.

### 2. Pre-Loaded Demo Accounts & Instant Role Switcher
The application includes a built-in **Quick Role Switcher** in the top navigation bar, allowing evaluators to preview the platform from any persona with a single click.

| Role | Email | Password | Persona & Privileges |
| :--- | :--- | :--- | :--- |
| **Admin** | `admin@brightloop.com` | `Admin@12345` | **Elena Vance (CEO / Admin)**: Full system control, staff management, tax rules, and discount rules. |
| **Staff** | `sarah@brightloop.com` | `Staff@12345` | **Sarah Jenkins (Sales Rep)**: Daily ops, quotation templates, subscription lifecycle, invoicing. |
| **Staff** | `david@brightloop.com` | `Staff@12345` | **David Kim (Billing Specialist)**: Payment recording, receivables chasing, invoice dispatch. |
| **Customer** | `acme@acmecorp.com` | `Acme@12345` | **Acme Corporation**: Enterprise Yearly plan with 15 seats + Odoo Cloud hosting. |
| **Customer** | `bistro@cornercafe.com` | `Corner@12345` | **Corner Cafe & Bakery**: Small business Monthly Starter subscription. |
| **Customer** | `spark@sparklabs.com` | `Spark@12345` | **Spark Labs Inc.**: Active subscription with an overdue invoice ready for chasing. |

### 3. Re-seed Demo Data Anytime
```bash
./venv/bin/python manage.py seed_brightloop_data
```

### 4. Run Automated Billing Day via CLI
```bash
# Run for today:
./venv/bin/python manage.py run_billing_day

# Or run for a specific target date:
./venv/bin/python manage.py run_billing_day --date 2026-11-01
```

### 5. Run the Automated Test Suite
```bash
./venv/bin/python manage.py test
```

---

## 📋 Complete Scene Coverage (Problem Statement Breakdown)

### Scene 1: A New Customer Signs Up
* **Account Registration**:
  * Clean small-business signup at `/register/`.
  * **Email Uniqueness**: Strict validation ensuring each email belongs to only one account.
  * **Password Complexity Validator**: Verified via `BrightloopPasswordValidator` ensuring passwords are **> 8 characters**, with at least **one uppercase letter**, **one lowercase letter**, and **one special character** (`!@#$%^&*...`).
* **Password Recovery**: Token-based reset link generator at `/forgot-password/` and reset endpoint at `/reset-password/<token>/`.
* **Role-Based Access Control (RBAC)**:
  * **Admin**: Unrestricted control. **Only Admin** can add new members of staff (`/staff/new/`).
  * **Internal Staff**: Daily work (Quotes, Subscriptions, Invoicing, Payments, Analytics). Blocked from staff admin and restricted system settings.
  * **Customer Portal**: Self-service portal (`/portal/`) where customers see **only their own** subscriptions and invoices.

---

### Scene 2: Launching a New Plan
* **Product Catalog & Variants** (`/products/`):
  * Products include: Name, Product Type (`Business Software`, `Add-on`, `Recurring Service`, `Hardware`), Sales Price, Cost Price, Default Tax Rule, and Notes.
  * **Variant Architecture**: Supports custom attributes and price deltas. Explicitly models:
    * *Dedicated Cloud Hosting* + Variant Attribute **"Brand: Odoo" adds $560.00** to the sales price ($200.00 + $560.00 = $760.00).
* **Subscription Plans** (`/plans/`):
  * Configurable recurring intervals: **Daily**, **Weekly**, **Monthly**, or **Yearly**.
  * Base cost, minimum quantity requirement, and availability dates (`available_from` & `available_to`).
  * **Admin Lifecycle Policy Toggles**:
    * `auto_close_on_end`: Subscriptions close automatically when they end (e.g. Trial Special).
    * `allow_close_early`: Allow customer or staff to close contract early.
    * `allow_pause`: Enable pause and resume functionality.
    * `allow_renewal`: Permit contract renewals.

---

### Scene 3: Turning a Quote into a Subscription
* **Quotation Templates** (`/templates/`):
  * Pre-configured templates with default plan, product lines, quantities, and validity period (e.g., valid for 15 or 30 days).
  * **1-Click Quote Generator** (`/templates/<id>/create-quote/`): Instantly prepares an offer for any customer without typing lines from scratch.
* **Subscriptions** (`/subscriptions/`):
  * Unique sequential numbering (e.g. `SUB-2026-00001`).
  * Links customer, plan, start date, expiry date, and payment terms (Immediate, Net 15, Net 30, Net 60).
  * Line items with product, variant, quantity, unit price, tax rule, and calculated amounts.
* **State Machine Ribbon**:
  * Visual Odoo-style workflow transitions:
    $$\text{Draft} \longrightarrow \text{Quotation} \longrightarrow \text{Confirmed} \longrightarrow \text{Active} \longrightarrow \text{Closed}$$
  * Full audit trail and visibility for the internal team.
* **PDF Quotation Generator**: Branded PDF quotation download at `/subscriptions/<id>/pdf/`.

---

### Scene 4: Billing Day
* **Automated Batch Billing Engine** (`/billing-day/` and `run_billing_day` command):
  * Evaluates all active subscriptions due for billing.
  * Auto-generates itemized invoices with customer details, product lines, taxes, and totals pre-populated.
  * **Strict Idempotency**: *"Nothing should be billed twice or skipped."* The engine checks `billing_period_start` and existing invoices; running billing day multiple times skips already billed periods and never creates duplicate invoices.
  * **Automatic Tax Engine**: Applies admin tax rules (e.g. 8.25% Sales Tax, 10% VAT) automatically per line.
  * **Invoice Operations**: Staff can Confirm, Cancel, Send by Email (with simulated dispatch and timestamp), Print, or Download PDF (`/invoices/<id>/pdf/`).
  * **Invoice Lifecycle**: Moves from `Draft` $\longrightarrow$ `Confirmed` $\longrightarrow$ `Paid`.

---

### Scene 5: A Customer Asks for a Better Price
* **Admin Discount Rules** (`/discounts/`):
  * Configured exclusively by Admin.
  * Type: **Percentage (%)** or **Fixed Dollar Amount ($)**.
  * Eligibility Conditions: Minimum purchase spend or minimum seat quantity.
  * Validity window: Start date and End date.
  * **Redemption Counter**: Enforces `max_uses` limit; automatically deactivates when the limit is reached or when expired.
  * Scope: Applies to **Whole Subscription** or **Specific Product**.
* **Zero-Touch Auto-Application**:
  * Once eligible, the discount rule automatically attaches to the next generated invoice during Billing Day without manual intervention.

---

### Scene 6: The Money Comes In
* **Payment Collection** (`/invoices/<id>/payment/`):
  * Records payment method (`Credit Card`, `Bank Transfer`, `PayPal`, `Cash`, `Check`), payment date, amount, reference/transaction ID, and note against the invoice.
  * Supports partial payments and full payments.
  * When `balance_due <= 0`, invoice status automatically transitions to `Paid`.
* **Overdue Tracking & Chasing**:
  * Automatically detects invoices where `due_date < today` and `balance_due > 0`.
  * Dedicated "Chase Overdue" action buttons on the dashboard for immediate customer follow-up.

---

### Scene 7: The Finance Lead, at the End of the Month
* **Executive Command Center** (`/finance/` and `/dashboard/`):
  * **The 4 Key Questions Answered Instantly**:
    1. *How many subscriptions are active?* &rarr; Displayed in real-time KPI card + MRR & ARR.
    2. *How much revenue came in?* &rarr; Exact cash collections from recorded payments.
    3. *How much is still owed?* &rarr; Outstanding accounts receivable balance.
    4. *Which invoices are overdue?* &rarr; Ranked overdue chase list with days overdue and quick actions.
  * **Interactive Filters**: Date range (start/end date), Plan filter, Customer filter.
  * **Performance SLA**: **< 2.0s Page Response Time** with thousands of subscriptions. Benchmarked in sub-5ms on indexed SQLite/Django ORM queries, with a live latency badge displayed on the dashboard.

---

## 🏗️ Architecture & Technology Stack
* **Backend**: Python 3.13, Django 6.1.2
* **Database**: SQLite3 (ACID-compliant, sub-millisecond local reads, optimized indexes)
* **Frontend**: Django Templates, Tailwind CSS, FontAwesome 6, Chart.js
* **PDF Engine**: ReportLab (High-fidelity vector PDF generation for quotes and invoices)
* **Business Logic Layer**:
  * `brightloop_app/services/billing_engine.py`: Batch billing, idempotency guard, tax/discount applier
  * `brightloop_app/services/analytics_service.py`: Financial KPIs, MRR/ARR, receivables, latency benchmark
  * `brightloop_app/services/pdf_service.py`: ReportLab document templates
  * `brightloop_app/validators.py`: Strict password security complexity validation

