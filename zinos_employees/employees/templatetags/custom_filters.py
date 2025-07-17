from django import template

register = template.Library()

@register.filter
def get_employee_badge_color(value):
    color_map = {
        'FT': 'success',
        'PT': 'warning',
        'CT': 'info'
    }
    return color_map.get(value, 'secondary')