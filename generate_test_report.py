from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from datetime import datetime

def generate_test_report():
    # Create PDF document
    doc = SimpleDocTemplate(
        "test_results.pdf",
        pagesize=letter,
        rightMargin=72,
        leftMargin=72,
        topMargin=72,
        bottomMargin=72
    )

    # Create styles
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=16,
        spaceAfter=30
    )
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=12,
        spaceAfter=12
    )
    normal_style = styles['Normal']

    # Create content
    content = []

    # Add title
    content.append(Paragraph("HealthSync Test Results Report", title_style))
    content.append(Paragraph(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", normal_style))
    content.append(Spacer(1, 20))

    # Test results data
    test_data = [
        ["Test Class", "Test Case", "Description", "Status"],
        ["MedicationScheduleTests", "test_medication_schedule_end_date_calculation", 
         "Verifies end_date calculation based on start date and duration", "✅ PASS"],
        ["", "test_medication_mark_as_taken", 
         "Tests marking medication as taken and updating status", "✅ PASS"],
        ["", "test_medication_reset_for_next_day", 
         "Tests resetting medication status for next day", "✅ PASS"],
        ["TaskTests", "test_send_sms_reminder_with_phone", 
         "Tests SMS sending with valid phone number (+15555555555)", "✅ PASS"],
        ["", "test_send_sms_reminder_without_phone", 
         "Tests error handling when phone number is missing", "✅ PASS"],
        ["", "test_check_and_send_medication_reminders", 
         "Tests medication reminder scheduling and status updates", "✅ PASS"],
        ["TokenUtilsTests", "test_generate_token_for_user", 
         "Tests JWT token generation and validation", "✅ PASS"],
        ["PatientFeedbackTests", "test_feedback_creation", 
         "Tests creating feedback with all fields", "✅ PASS"],
        ["", "test_feedback_viewed_by_doctor", 
         "Tests marking feedback as viewed by doctor", "✅ PASS"]
    ]

    # Create table
    table = Table(test_data)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 10),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))

    content.append(table)
    content.append(Spacer(1, 20))

    # Add summary
    content.append(Paragraph("Summary Statistics", heading_style))
    summary_data = [
        ["Total Tests", "9"],
        ["Passed", "9"],
        ["Failed", "0"],
        ["Test Duration", "5.492s"]
    ]
    
    summary_table = Table(summary_data)
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 10),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
    ]))

    content.append(summary_table)
    content.append(Spacer(1, 20))

    # Add debug output
    content.append(Paragraph("Debug Output", heading_style))
    debug_output = [
        "[DEBUG] Current time: 2024-01-01 10:00:00+06:55",
        "[DEBUG] Cleaned up medications older than 10 days",
        "[DEBUG] Found 1 active medications for today",
        "[DEBUG] Minutes until Test Med: 2.0",
        "[DEBUG] Adding Test Med to reminder list",
        "[DEBUG] Sending reminders for 1 medications"
    ]
    
    for line in debug_output:
        content.append(Paragraph(line, normal_style))

    # Build PDF
    doc.build(content)

if __name__ == "__main__":
    generate_test_report() 