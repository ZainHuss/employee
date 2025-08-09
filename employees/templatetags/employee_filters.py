from django import template

register = template.Library()

@register.filter(name='get_employee_badge_color')
def get_employee_badge_color(employee):
    """
    Returns bootstrap badge color based on employee status
    """
    if employee.attendance_percentage() >= 90:
        return 'success'
    elif employee.attendance_percentage() >= 70:
        return 'warning'
    else:
        return 'danger'