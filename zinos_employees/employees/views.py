from django.shortcuts import render, get_object_or_404
from .models import Employee, Attendance, SalaryPayment, Department
from django.db.models import Count, Q,Avg
from datetime import datetime
from django.contrib.auth.decorators import login_required
from openpyxl import Workbook
from django.http import HttpResponse


@login_required
def employee_list(request):
    # استرجاع جميع الموظفين
    employees = Employee.objects.all().select_related('department', 'manager')
    
    # استرجاع المديرين فقط (الذين لديهم موظفون تحت إدارتهم)
    managers = Employee.objects.annotate(
        num_subordinates=Count('subordinates')
    ).filter(num_subordinates__gt=0).order_by('name')
    
    return render(request, 'employees/employee_list.html', {
        'employees': employees,
        'managers': managers,
        'page_title': 'قائمة الموظفين والمديرين'
    })


@login_required
def manager_list(request):
    # الحصول على جميع المديرين (الذين لديهم موظفون تحت إدارتهم)
    managers = Employee.objects.annotate(
        subordinates_count=Count('subordinates')
    ).filter(subordinates_count__gt=0).select_related('department')
    
    # إحصاءات عامة
    total_managers = managers.count()
    avg_subordinates = managers.aggregate(
        avg=Avg('subordinates_count'))['avg'] or 0
    
    return render(request, 'employees/manager_list.html', {
        'managers': managers,
        'total_managers': total_managers,
        'avg_subordinates': round(avg_subordinates, 1),
        'page_title': 'قائمة المديرين'
    })


@login_required
def manager_detail(request, pk):
    manager = get_object_or_404(Employee, pk=pk)
    
    # التحقق أنه مدير (لديه موظفون تحت إدارته)
    if not manager.subordinates.exists():
        return render(request, 'employees/not_manager.html', {
            'employee': manager
        })
    
    # الموظفون تحت إدارة هذا المدير
    subordinates = manager.subordinates.all().select_related('department')
    
    # إحصاءات الحضور للموظفين التابعين
    current_month = datetime.now().month
    current_year = datetime.now().year
    
    subordinates_stats = []
    for emp in subordinates:
        present_days = Attendance.objects.filter(
            employee=emp,
            date__month=current_month,
            date__year=current_year,
            is_present=True
        ).count()
        
        subordinates_stats.append({
            'employee': emp,
            'present_days': present_days,
            'attendance_rate': round((present_days / 30) * 100, 1) if present_days else 0
        })
    
    return render(request, 'employees/manager_detail.html', {
        'manager': manager,
        'subordinates_stats': subordinates_stats,
        'current_month': current_month,
        'current_year': current_year,
        'subordinates_count': subordinates.count()
    })


@login_required
def employee_detail(request, pk):
    employee = get_object_or_404(Employee, pk=pk)
    
    attendances = Attendance.objects.filter(employee=employee).order_by('-date')[:30]
    
    current_month = datetime.now().month
    current_year = datetime.now().year
    working_days = Attendance.objects.filter(
        employee=employee,
        date__month=current_month,
        date__year=current_year,
        is_present=True
    ).count()
    
    # معلومات المدير إذا كان الموظف لديه مدير
    manager_info = None
    if employee.manager:
        manager_info = {
            'id': employee.manager.id,
            'name': employee.manager.name,
            'department': employee.manager.department.name if employee.manager.department else ''
        }
    
    return render(request, 'employees/employee_detail.html', {
        'employee': employee,
        'attendances': attendances,
        'working_days': working_days,
        'current_month': current_month,
        'current_year': current_year,
        'manager_info': manager_info
    })


@login_required
def calculate_salary(request, pk):
    employee = get_object_or_404(Employee, pk=pk)
    
    if request.method == 'POST':
        month = int(request.POST.get('month'))
        year = int(request.POST.get('year'))
        
        working_days = Attendance.objects.filter(
            employee=employee,
            date__month=month,
            date__year=year,
            is_present=True
        ).count()
        
        daily_salary = employee.salary / 30
        actual_salary = daily_salary * working_days
        
        # حفظ بيانات الراتب مع تحديد المدير المسؤول إذا كان موجوداً
        SalaryPayment.objects.create(
            employee=employee,
            month=month,
            year=year,
            working_days=working_days,
            actual_salary=actual_salary,
            approved_by=employee.manager if employee.manager else None
        )
        
        return render(request, 'employees/salary_result.html', {
            'employee': employee,
            'month': month,
            'year': year,
            'working_days': working_days,
            'actual_salary': actual_salary,
            'base_salary': employee.salary,
            'approved_by': employee.manager.name if employee.manager else "غير معين"
        })
    
    return render(request, 'employees/calculate_salary.html', {
        'employee': employee,
        'current_month': datetime.now().month,
        'current_year': datetime.now().year
    })
def export_employees_to_excel(request):
    # جلب بيانات الموظفين
    employees = Employee.objects.all().select_related('department', 'manager')
    
    # إنشاء ملف Excel
    response = HttpResponse(content_type='application/ms-excel')
    response['Content-Disposition'] = f'attachment; filename="employees_{datetime.now().strftime("%Y-%m-%d")}.xlsx"'
    
    wb = Workbook()
    ws = wb.active
    ws.title = "الموظفون"
    
    # إضافة العناوين
    columns = [
        'الرقم', 'الاسم', 'القسم', 'المدير المسؤول',
        'نوع التوظيف', 'تاريخ التعيين', 'الراتب', 'الهاتف', 'البريد الإلكتروني'
    ]
    ws.append(columns)
    
    # إضافة البيانات
    for emp in employees:
        ws.append([
            emp.id,
            emp.name,
            emp.department.name if emp.department else '',
            emp.manager.name if emp.manager else '',
            emp.get_employee_type_display(),
            emp.hire_date.strftime("%Y-%m-%d") if emp.hire_date else '',
            emp.salary,
            emp.phone,
            emp.email
        ])
    
    # حفظ الملف
    wb.save(response)
    return response