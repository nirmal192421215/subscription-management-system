import io
from decimal import Decimal
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch

class PDFService:
    @staticmethod
    def generate_invoice_pdf(invoice):
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            rightMargin=36,
            leftMargin=36,
            topMargin=36,
            bottomMargin=36
        )

        styles = getSampleStyleSheet()
        normal = styles['Normal']

        header_title = ParagraphStyle(
            'HeaderTitle',
            parent=styles['Heading1'],
            fontSize=24,
            leading=28,
            textColor=colors.HexColor('#714B67'), # Odoo corporate purple / Brightloop brand
            fontName='Helvetica-Bold'
        )

        sub_header = ParagraphStyle(
            'SubHeader',
            parent=normal,
            fontSize=10,
            leading=14,
            textColor=colors.HexColor('#6B7280')
        )

        table_header = ParagraphStyle(
            'TableHeader',
            parent=normal,
            fontSize=9,
            leading=11,
            textColor=colors.white,
            fontName='Helvetica-Bold'
        )

        cell_text = ParagraphStyle(
            'CellText',
            parent=normal,
            fontSize=9,
            leading=12,
            textColor=colors.HexColor('#1F2937')
        )

        cell_bold = ParagraphStyle(
            'CellBold',
            parent=normal,
            fontSize=9,
            leading=12,
            textColor=colors.HexColor('#1F2937'),
            fontName='Helvetica-Bold'
        )

        elements = []

        # Company Header and Invoice title
        header_data = [
            [
                Paragraph("<b>Brightloop Software Inc.</b><br/>100 Innovation Way<br/>Silicon Valley, CA 94025<br/>billing@brightloop.com", sub_header),
                Paragraph(f"<b>INVOICE</b><br/><font size=12 color='#714B67'><b>{invoice.invoice_number}</b></font><br/>Status: <b>{invoice.get_status_display().upper()}</b>", ParagraphStyle('InvTitle', parent=normal, alignment=2, leading=16))
            ]
        ]
        header_table = Table(header_data, colWidths=[4.0 * inch, 3.5 * inch])
        header_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))
        elements.append(header_table)
        elements.append(Spacer(1, 15))

        # Divider line
        divider = Table([['']], colWidths=[7.5 * inch])
        divider.setStyle(TableStyle([
            ('LINEBELOW', (0, 0), (-1, -1), 1.5, colors.HexColor('#714B67')),
        ]))
        elements.append(divider)
        elements.append(Spacer(1, 15))

        # Bill To & Dates Block
        bill_to_html = f"""
        <b>Billed To:</b><br/>
        <b>{invoice.customer.display_name}</b><br/>
        {invoice.customer.email}<br/>
        {invoice.customer.phone or ''}<br/>
        {invoice.customer.address or ''}
        """

        meta_html = f"""
        <b>Invoice Date:</b> {invoice.invoice_date}<br/>
        <b>Due Date:</b> {invoice.due_date}<br/>
        <b>Payment Terms:</b> {invoice.subscription.get_payment_terms_display() if invoice.subscription else 'Immediate'}<br/>
        <b>Billing Period:</b> {invoice.billing_period_start or 'N/A'} to {invoice.billing_period_end or 'N/A'}
        """

        info_data = [
            [Paragraph(bill_to_html, sub_header), Paragraph(meta_html, ParagraphStyle('MetaText', parent=sub_header, alignment=2))]
        ]
        info_table = Table(info_data, colWidths=[4.0 * inch, 3.5 * inch])
        info_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))
        elements.append(info_table)
        elements.append(Spacer(1, 20))

        # Invoice Lines Table
        table_rows = [
            [
                Paragraph("Description", table_header),
                Paragraph("Qty", table_header),
                Paragraph("Unit Price", table_header),
                Paragraph("Tax", table_header),
                Paragraph("Amount", table_header)
            ]
        ]

        for line in invoice.lines.all():
            tax_str = f"{line.tax_rule.name} (${line.tax_amount})" if line.tax_rule else "$0.00"
            table_rows.append([
                Paragraph(line.description, cell_text),
                Paragraph(str(line.quantity), cell_text),
                Paragraph(f"${line.unit_price:,.2f}", cell_text),
                Paragraph(tax_str, cell_text),
                Paragraph(f"${line.line_total:,.2f}", cell_bold)
            ])

        lines_table = Table(table_rows, colWidths=[3.2 * inch, 0.7 * inch, 1.2 * inch, 1.2 * inch, 1.2 * inch])
        lines_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#714B67')),
            ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E5E7EB')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F9FAFB')]),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
        ]))
        elements.append(lines_table)
        elements.append(Spacer(1, 15))

        # Summary / Totals Table
        totals_data = [
            [Paragraph("Subtotal:", cell_bold), Paragraph(f"${invoice.subtotal:,.2f}", cell_text)],
            [Paragraph(f"Discount {f'({invoice.discount_rule.code})' if invoice.discount_rule else ''}:", cell_bold), Paragraph(f"-${invoice.discount_amount:,.2f}", cell_text)],
            [Paragraph("Taxes:", cell_bold), Paragraph(f"+${invoice.tax_amount:,.2f}", cell_text)],
            [Paragraph("<b>Total Amount:</b>", cell_bold), Paragraph(f"<b>${invoice.total_amount:,.2f}</b>", cell_bold)],
            [Paragraph("Amount Paid:", cell_bold), Paragraph(f"${invoice.amount_paid:,.2f}", cell_text)],
            [Paragraph("<b>Balance Due:</b>", cell_bold), Paragraph(f"<b><font color='#DC2626'>${invoice.balance_due:,.2f}</font></b>", cell_bold)],
        ]
        totals_table = Table(totals_data, colWidths=[2.0 * inch, 1.5 * inch])
        totals_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
            ('LINEBELOW', (0, 3), (-1, 3), 1, colors.HexColor('#714B67')),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
        ]))

        wrapper_data = [
            [
                Paragraph("<b>Payment Instructions:</b><br/>Please send payments via Bank Transfer, Stripe, or Portal Card.<br/>Reference Invoice Number when making payment.<br/>Thank you for your business!", sub_header),
                totals_table
            ]
        ]
        wrapper_table = Table(wrapper_data, colWidths=[4.0 * inch, 3.5 * inch])
        wrapper_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))
        elements.append(wrapper_table)

        doc.build(elements)
        buffer.seek(0)
        return buffer.getvalue()


    @staticmethod
    def generate_quote_pdf(subscription):
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            rightMargin=36,
            leftMargin=36,
            topMargin=36,
            bottomMargin=36
        )

        styles = getSampleStyleSheet()
        normal = styles['Normal']

        sub_header = ParagraphStyle(
            'SubHeader',
            parent=normal,
            fontSize=10,
            leading=14,
            textColor=colors.HexColor('#6B7280')
        )

        table_header = ParagraphStyle(
            'TableHeader',
            parent=normal,
            fontSize=9,
            leading=11,
            textColor=colors.white,
            fontName='Helvetica-Bold'
        )

        cell_text = ParagraphStyle(
            'CellText',
            parent=normal,
            fontSize=9,
            leading=12,
            textColor=colors.HexColor('#1F2937')
        )

        cell_bold = ParagraphStyle(
            'CellBold',
            parent=normal,
            fontSize=9,
            leading=12,
            textColor=colors.HexColor('#1F2937'),
            fontName='Helvetica-Bold'
        )

        elements = []

        header_data = [
            [
                Paragraph("<b>Brightloop Software Inc.</b><br/>100 Innovation Way<br/>Silicon Valley, CA 94025<br/>sales@brightloop.com", sub_header),
                Paragraph(f"<b>SUBSCRIPTION QUOTATION</b><br/><font size=12 color='#714B67'><b>{subscription.subscription_number}</b></font><br/>Status: <b>{subscription.get_status_display().upper()}</b>", ParagraphStyle('QTitle', parent=normal, alignment=2, leading=16))
            ]
        ]
        header_table = Table(header_data, colWidths=[4.0 * inch, 3.5 * inch])
        elements.append(header_table)
        elements.append(Spacer(1, 15))

        # Customer & Quote Details
        valid_until = subscription.quotation_valid_until or (subscription.start_date)
        cust_html = f"""
        <b>Customer:</b><br/>
        <b>{subscription.customer.display_name}</b><br/>
        {subscription.customer.email}<br/>
        {subscription.customer.address or ''}
        """

        meta_html = f"""
        <b>Plan:</b> {subscription.plan.name} ({subscription.plan.get_billing_interval_display()})<br/>
        <b>Start Date:</b> {subscription.start_date}<br/>
        <b>Valid Until:</b> {valid_until}<br/>
        <b>Payment Terms:</b> {subscription.get_payment_terms_display()}
        """

        info_table = Table([[Paragraph(cust_html, sub_header), Paragraph(meta_html, ParagraphStyle('MetaText', parent=sub_header, alignment=2))]], colWidths=[4.0 * inch, 3.5 * inch])
        elements.append(info_table)
        elements.append(Spacer(1, 15))

        # Items Table
        table_rows = [
            [
                Paragraph("Product / Service", table_header),
                Paragraph("Qty", table_header),
                Paragraph("Unit Price", table_header),
                Paragraph("Tax", table_header),
                Paragraph("Total", table_header)
            ]
        ]

        for line in subscription.lines.all():
            desc = f"{line.product.name}"
            if line.variant:
                desc += f" ({line.variant.attribute_name}: {line.variant.variant_value})"
            tax_str = f"{line.tax_rule.name} (${line.tax_amount})" if line.tax_rule else "$0.00"
            table_rows.append([
                Paragraph(desc, cell_text),
                Paragraph(str(line.quantity), cell_text),
                Paragraph(f"${line.unit_price:,.2f}", cell_text),
                Paragraph(tax_str, cell_text),
                Paragraph(f"${line.total_amount:,.2f}", cell_bold)
            ])

        lines_table = Table(table_rows, colWidths=[3.2 * inch, 0.7 * inch, 1.2 * inch, 1.2 * inch, 1.2 * inch])
        lines_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#714B67')),
            ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E5E7EB')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F9FAFB')]),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
        ]))
        elements.append(lines_table)
        elements.append(Spacer(1, 15))

        # Totals
        subtotal = subscription.calculate_subtotal()
        taxes = subscription.calculate_taxes()
        grand = subscription.calculate_grand_total()

        totals_data = [
            [Paragraph("Subtotal:", cell_bold), Paragraph(f"${subtotal:,.2f}", cell_text)],
            [Paragraph("Taxes:", cell_bold), Paragraph(f"${taxes:,.2f}", cell_text)],
            [Paragraph("<b>Recurring Total:</b>", cell_bold), Paragraph(f"<b>${grand:,.2f} / {subscription.plan.get_billing_interval_display()}</b>", cell_bold)],
        ]
        totals_table = Table(totals_data, colWidths=[2.0 * inch, 1.5 * inch])
        elements.append(Table([[Paragraph("This quotation is subject to Brightloop Software terms of service.", sub_header), totals_table]], colWidths=[4.0 * inch, 3.5 * inch]))

        doc.build(elements)
        buffer.seek(0)
        return buffer.getvalue()
