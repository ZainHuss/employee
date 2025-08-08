# employees/templatetags/custom_filters.py
from django import template

register = template.Library()

@register.filter
def get_employee_badge_color(value):
    """Return Bootstrap color class based on employee type"""
    color_map = {
        'FT': 'success',  # دوام كامل
        'PT': 'warning',  # دوام جزئي
        'CT': 'info'      # عقد مؤقت
    }
    return color_map.get(value, 'secondary')  # افتراضي

@register.filter
def risk_level_class(value):
    """Return Bootstrap class based on risk level (0-1 scale)"""
    try:
        risk = float(value)
        if risk >= 0.75:
            return 'danger'
        elif risk >= 0.55:
            return 'warning'
        else:
            return 'success'
    except (ValueError, TypeError):
        return 'secondary'

@register.filter
def recommendation_color(value):
    """Return color class based on recommendation type"""
    if not value:
        return 'secondary'
    
    value = str(value).lower()
    if 'intervention' in value:
        return 'danger'
    elif 'plan' in value:
        return 'warning'
    elif 'engagement' in value or 'opportunities' in value:
        return 'success'
    return 'info'

@register.filter
def recommendation_icon(value):
    """Return Font Awesome icon class based on recommendation"""
    if not value:
        return 'fas fa-question'
    
    value = str(value).lower()
    if 'intervention' in value:
        return 'fas fa-exclamation-triangle'
    elif 'plan' in value:
        return 'fas fa-clipboard-list'
    elif 'engagement' in value:
        return 'fas fa-hands-helping'
    elif 'opportunities' in value:
        return 'fas fa-briefcase'
    return 'fas fa-lightbulb'

@register.filter
def multiply(value, arg):
    """Multiply the value by arg with error handling"""
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return 0

@register.filter
def performance_level_class(value):
    """Return class based on performance level (1-5 scale)"""
    try:
        level = float(value)
        if level >= 4:
            return 'success'
        elif level >= 3:
            return 'info'
        elif level >= 2:
            return 'warning'
        return 'danger'
    except (ValueError, TypeError):
        return 'secondary'

@register.filter
def performance_level_text(value):
    """Return Arabic text based on performance level"""
    try:
        level = float(value)
        if level >= 4.5:
            return 'ممتاز'
        elif level >= 4:
            return 'جيد جداً'
        elif level >= 3:
            return 'جيد'
        elif level >= 2:
            return 'مقبول'
        return 'ضعيف'
    except (ValueError, TypeError):
        return 'غير متوفر'