from django.contrib import admin
from employees import models  
from django.utils.html import format_html
from .models import Department, Employee, Attendance, SalaryPayment
from .forms import EmployeeAdminForm

@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ('name', 'description_short')
    search_fields = ('name', 'description')
    
    def description_short(self, obj):
        return obj.description[:50] + '...' if obj.description else '-'
    description_short.short_description = 'الوصف المختصر'

@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ('name', 'department_info', 'employee_type_display', 
                   'salary_display', 'hire_date_display', 'manager_info', 
                   'contact_info', 'image_preview')
    
    list_filter = ('department', 'employee_type')
    search_fields = ('name', 'department__name', 'phone', 'email')
    list_select_related = ('department', 'manager')
    form = EmployeeAdminForm
    
    fieldsets = (
        ('المعلومات الأساسية', {
            'fields': ('name', 'department', 'employee_type', 'salary', 'hire_date', 'image')
        }),
        ('معلومات الاتصال', {
            'fields': ('phone', 'email', 'address')
        }),
        ('المعلومات الإدارية', {
            'fields': ('manager',)
        }),
    )
    
    readonly_fields = ('image_preview',)
    
    def department_info(self, obj):
        return obj.department.name if obj.department else '-'
    department_info.short_description = 'القسم'
    
    def employee_type_display(self, obj):
        return obj.get_employee_type_display()
    employee_type_display.short_description = 'نوع التوظيف'
    
    def salary_display(self, obj):
        return f"{obj.salary:,.2f} ر.س" if obj.salary else '-'
    salary_display.short_description = 'الراتب'
    
    def hire_date_display(self, obj):
        return obj.hire_date.strftime("%Y-%m-%d") if obj.hire_date else '-'
    hire_date_display.short_description = 'تاريخ التعيين'
    
    def manager_info(self, obj):
        if obj.manager:
            return format_html('<a href="{}">{}</a>', 
                             f'/admin/employees/employee/{obj.manager.id}/change/',
                             obj.manager.name)
        return '-'
    manager_info.short_description = 'المدير المسؤول'
    
    def contact_info(self, obj):
        contact = []
        if obj.phone:
            contact.append(f"هاتف: {obj.phone}")
        if obj.email:
            contact.append(f"بريد: {obj.email}")
        return " | ".join(contact) if contact else '-'
    contact_info.short_description = 'معلومات الاتصال'
    
    def image_preview(self, obj):
        if obj.image:  # إذا كان هناك صورة
            if hasattr(obj.image, 'url'):  # إذا كان حقل الصورة من نوع FileField/ImageField
                return format_html('<img src="{}" width="50" height="50" />', obj.image.url)
            else:  # إذا كان بيانات بايت
                # يمكنك معالجة بيانات البايت هنا أو عرض بديل
                return format_html('<span>صورة مخزنة كبيانات بايت</span>')
        return "لا توجد صورة"
    
    image_preview.short_description = 'معاينة الصورة'

@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = ('employee_info', 'date_display', 'status_display',
                   'check_in_display', 'check_out_display', 'notes_short')
    list_filter = ('date', 'status', 'employee__department')
    search_fields = ('employee__name', 'notes')
    list_select_related = ('employee', 'employee__department')
    
    def employee_info(self, obj):
        return obj.employee.name if obj.employee else '-'
    employee_info.short_description = 'الموظف'
    
    def date_display(self, obj):
        return obj.date.strftime("%Y-%m-%d") if obj.date else '-'
    date_display.short_description = 'التاريخ'
    
    def status_display(self, obj):
        # استبدل obj.is_present بـ obj.status == 'present'
        color = 'green' if obj.status == 'present' else 'red'
        return format_html(
            '<span style="color: {};">{}</span>',
            color,
            obj.get_status_display()
        )
    status_display.short_description = 'الحالة'
    
    def check_in_display(self, obj):
        return obj.check_in.strftime("%H:%M") if obj.check_in else '-'
    check_in_display.short_description = 'وقت الحضور'
    
    def check_out_display(self, obj):
        return obj.check_out.strftime("%H:%M") if obj.check_out else '-'
    check_out_display.short_description = 'وقت الانصراف'
    
    def notes_short(self, obj):
        return obj.notes[:30] + '...' if obj.notes else '-'
    notes_short.short_description = 'ملاحظات مختصرة'

@admin.register(SalaryPayment)
class SalaryPaymentAdmin(admin.ModelAdmin):
    list_display = ('employee_info', 'period_display', 'working_days_display',
                   'base_salary_display','net_salary_display', 'payment_date_display', 'approved_by_info')
    list_filter = ('month', 'year', 'employee__department')
    search_fields = ('employee__name', 'notes')
    list_select_related = ('employee', 'approved_by', 'employee__department')
    
    def employee_info(self, obj):
        return obj.employee.name if obj.employee else '-'
    employee_info.short_description = 'الموظف'
    
    def period_display(self, obj):
        return f"{obj.month}/{obj.year}"
    period_display.short_description = 'الفترة'
    
    def working_days_display(self, obj):
        return obj.working_days if obj.working_days is not None else '-'
    working_days_display.short_description = 'أيام العمل'

    def net_salary_display(self, obj):
        return obj.net_salary  # أو أي معالجة تريدها
    net_salary_display.short_description = 'صافي الراتب'
    
    def base_salary_display(self, obj):
        return obj.base_salary  # أو أي معالجة تريدها
    base_salary_display.short_description = 'الراتب الأساسي'
    
    def payment_date_display(self, obj):
        return obj.payment_date.strftime("%Y-%m-%d") if obj.payment_date else '-'
    payment_date_display.short_description = 'تاريخ الدفع'
    
    def approved_by_info(self, obj):
        if obj.approved_by:
            return f"{obj.approved_by.get_full_name()} ({obj.approved_by.username})"
        return "-"
    approved_by_info.short_description = 'تمت الموافقة بواسطة'

# تخصيص عناوين لوحة الإدارة
admin.site.site_header = 'نظام إدارة موظفين زينوس'
admin.site.site_title = 'زينوس'
admin.site.index_title = 'لوحة التحكم'