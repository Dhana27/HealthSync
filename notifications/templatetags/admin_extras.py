from django import template
from django.utils.html import format_html
from django.utils.safestring import mark_safe

register = template.Library()

@register.filter
def get_field(obj, field_name):
    """
    Get a field value from an object, handling special cases for admin display.
    """
    try:
        # Try to get the field value using getattr
        value = getattr(obj, field_name)
        
        # If it's a callable (like a method), call it
        if callable(value):
            value = value()
            
        # Handle boolean values
        if isinstance(value, bool):
            if value:
                return format_html('<span style="color: #10b981;">✓ Yes</span>')
            else:
                return format_html('<span style="color: #6b7280;">No</span>')
                
        # Handle status fields
        if field_name == 'status':
            if value == 'completed':
                return format_html('<span class="status-badge status-completed">Completed</span>')
            elif value == 'scheduled':
                return format_html('<span class="status-badge status-scheduled">Scheduled</span>')
            elif value == 'pending':
                return format_html('<span class="status-badge status-pending">Pending</span>')
                
        # Handle reminder status
        if field_name == 'reminder_status':
            if value == 'sent':
                return format_html('<span style="color: #10b981;">✓ Sent</span>')
            else:
                return format_html('<span style="color: #6b7280;">Pending</span>')
                
        # Handle foreign key fields
        if hasattr(value, '__str__'):
            return str(value)
            
        # Handle None values
        if value is None:
            return '-'
            
        return str(value)
    except (AttributeError, TypeError) as e:
        # Return a dash for missing fields
        return '-' 