from django.shortcuts import render, get_object_or_404, redirect
from django.db import models
from .models import Employee, Attendance, SalaryPayment, Department
from django.db.models import Count, Q, Avg, Sum, F, ExpressionWrapper, DurationField, fields
from datetime import datetime, timedelta
from django.contrib.auth.decorators import login_required, permission_required
from django.http import HttpResponse, HttpResponseForbidden
from django.utils import timezone
from django import forms
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.contrib import messages
from openpyxl import Workbook

class EmployeeForm(forms.ModelForm):
    class Meta:
        model = Employee
        fields = '__all__'
        widgets = {
            'hire_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'phone': forms.TextInput(attrs={
                'placeholder': 'ادخل رقم الهاتف',
                'class': 'form-control'
            }),
            'image': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*'
            })
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        managers = Employee.objects.annotate(
            num_subordinates=Count('subordinates')
        ).filter(num_subordinates__gt=0)
        self.fields['manager'].queryset = managers
        self.fields['department'].queryset = Department.objects.all()

    def clean_image(self):
        image = self.cleaned_data.get('image')
        if image and isinstance(image, bytes):
            return ContentFile(image, name='employee_image.jpg')
        return image

class SalaryCalculationForm(forms.Form):
    MONTH_CHOICES = [
        (1, 'يناير'), (2, 'فبراير'), (3, 'مارس'),
        (4, 'أبريل'), (5, 'مايو'), (6, 'يونيو'),
        (7, 'يوليو'), (8, 'أغسطس'), (9, 'سبتمبر'),
        (10, 'أكتوبر'), (11, 'نوفمبر'), (12, 'ديسمبر')
    ]
    
    month = forms.ChoiceField(choices=MONTH_CHOICES, label='الشهر')
    year = forms.IntegerField(
        min_value=2000,
        max_value=datetime.now().year,
        label='السنة'
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        current_date = timezone.now()
        self.fields['month'].initial = current_date.month
        self.fields['year'].initial = current_date.year

@login_required
def employee_detail(request, pk):
    employee = get_object_or_404(
        Employee.objects.select_related('department', 'manager', 'user'),
        pk=pk
    )
    
    current_date = timezone.now()
    start_date = current_date.replace(day=1)
    end_date = (start_date + timedelta(days=32)).replace(day=1) - timedelta(days=1)
    
    # الحصول على حضور آخر 30 يوم مع حساب ساعات العمل
    attendances = Attendance.objects.filter(
        employee=employee,
        date__lte=current_date
    ).order_by('-date')[:30]
    
    # حساب ساعات العمل لكل حضور
    for attendance in attendances:
        attendance.working_hours_value = attendance.get_working_hours()
    
    # حساب إحصائيات الشهر الحالي
    current_month_stats = Attendance.objects.filter(
        employee=employee,
        date__range=[start_date, end_date]
    ).aggregate(
        working_days=Count('id', filter=Q(status='present')),
        total_hours=Sum('working_hours')
    )
    
    working_days = current_month_stats['working_days'] or 0
    total_hours = current_month_stats['total_hours'] or 0.0
    
    attendance_percentage = round((working_days / end_date.day) * 100) if end_date.day > 0 else 0
    
    return render(request, 'employees/employee_detail.html', {
        'employee': employee,
        'attendances': attendances,
        'working_days': working_days,
        'attendance_percentage': attendance_percentage,
        'current_month': current_date.month,
        'current_year': current_date.year,
        'total_hours': round(total_hours, 2),
        'daily_salary': round(employee.salary / 30, 2),
        'employee_image_url': employee.get_image_url()
    })

@login_required
@permission_required('employees.calculate_salary', raise_exception=True)
def calculate_salary(request, pk):
    employee = get_object_or_404(Employee, pk=pk)
    current_date = timezone.now()
    
    if request.method == 'POST':
        form = SalaryCalculationForm(request.POST)
        if form.is_valid():
            month = int(form.cleaned_data['month'])
            year = int(form.cleaned_data['year'])
            
            if SalaryPayment.objects.filter(employee=employee, month=month, year=year).exists():
                messages.warning(request, 'تم حساب الراتب لهذا الشهر مسبقاً')
                return redirect('employee_detail', pk=employee.pk)
            
            start_date = datetime(year, month, 1)
            end_date = (start_date + timedelta(days=32)).replace(day=1) - timedelta(days=1)
            
            # حساب أيام العمل والغياب
            attendance_stats = Attendance.objects.filter(
                employee=employee,
                date__range=[start_date, end_date]
            ).aggregate(
                working_days=Count('id', filter=Q(status='present')),
                absent_days=Count('id', filter=Q(status='absent')),
                total_hours=Sum('working_hours')
            )
            
            working_days = attendance_stats['working_days'] or 0
            absent_days = attendance_stats['absent_days'] or 0
            daily_salary = employee.salary / 30
            base_salary = round(daily_salary * working_days, 2)
            
            # حساب صافي الراتب
            net_salary = base_salary - employee.deductions + employee.bonuses
            
            # إنشاء دفعة الراتب
            payment = SalaryPayment(
                employee=employee,
                month=month,
                year=year,
                working_days=working_days,
                absent_days=absent_days,
                base_salary=base_salary,
                deductions=employee.deductions,
                bonuses=employee.bonuses,
                net_salary=net_salary,
                notes=f"تم الحساب بواسطة {request.user.username}"
            )
            
            # تعيين الموافق إذا كان لديه الصلاحية
            if request.user.has_perm('employees.approve_salary'):
                try:
                    payment.approved_by = request.user.employee_profile
                except AttributeError:
                    pass
            
            payment.save()
            
            messages.success(request, 'تم حساب الراتب بنجاح')
            return redirect('employee_detail', pk=employee.pk)
    
    form = SalaryCalculationForm()
    return render(request, 'employees/calculate_salary.html', {
        'employee': employee,
        'form': form,
        'current_month': current_date.month,
        'current_year': current_date.year,
        'months': SalaryCalculationForm.MONTH_CHOICES,
        'daily_salary': round(employee.salary / 30, 2)
    })

@login_required
@permission_required('employees.export_employees', raise_exception=True)
def export_employees_to_excel(request):
    employees = Employee.objects.all() \
        .select_related('department', 'manager') \
        .order_by('department__name', 'name')
    
    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename="employees_{datetime.now().strftime("%Y-%m-%d")}.xlsx"'
    
    wb = Workbook()
    ws = wb.active
    ws.title = "الموظفون"
    
    columns = [
        'الرقم', 'الاسم', 'القسم', 'المدير المسؤول',
        'نوع التوظيف', 'تاريخ التعيين', 'الراتب', 'الهاتف', 'البريد الإلكتروني'
    ]
    ws.append(columns)
    
    for emp in employees:
        ws.append([
            emp.id,
            emp.name,
            emp.department.name if emp.department else 'بدون قسم',
            emp.manager.name if emp.manager else 'بدون مدير',
            emp.get_employee_type_display(),
            emp.hire_date.strftime("%Y-%m-%d") if emp.hire_date else 'غير محدد',
            f"{emp.salary:,.2f}",
            emp.phone or 'غير متوفر',
            emp.email or 'غير متوفر'
        ])
    
    wb.save(response)
    return response

@login_required
@permission_required('employees.add_employee', raise_exception=True)
def add_employee(request):
    if request.method == 'POST':
        form = EmployeeForm(request.POST, request.FILES)
        if form.is_valid():
            employee = form.save(commit=False)
            if 'image' in request.FILES:
                employee.image = request.FILES['image']
            employee.save()
            messages.success(request, 'تم إضافة الموظف بنجاح')
            return redirect('employee_detail', pk=employee.pk)
    else:
        form = EmployeeForm()
    
    return render(request, 'employees/employee_form.html', {
        'form': form,
        'title': 'إضافة موظف جديد'
    })

@login_required
@permission_required('employees.change_employee', raise_exception=True)
def edit_employee(request, pk):
    employee = get_object_or_404(Employee, pk=pk)
    
    if request.method == 'POST':
        form = EmployeeForm(request.POST, request.FILES, instance=employee)
        if form.is_valid():
            if 'image' in request.FILES and employee.image:
                if default_storage.exists(employee.image.name):
                    default_storage.delete(employee.image.name)
            
            form.save()
            messages.success(request, 'تم تحديث بيانات الموظف بنجاح')
            return redirect('employee_detail', pk=employee.pk)
    else:
        form = EmployeeForm(instance=employee)
    
    return render(request, 'employees/employee_form.html', {
        'form': form,
        'title': 'تعديل بيانات الموظف',
        'employee': employee
    })
@login_required
def employee_list(request):
    employees = Employee.objects.all().select_related('department', 'manager')
    managers = Employee.objects.annotate(
        num_subordinates=Count('subordinates')
    ).filter(num_subordinates__gt=0)
    
    return render(request, 'employees/employee_list.html', {
        'employees': employees,
        'managers': managers,
        'page_title': 'قائمة الموظفين'
    })