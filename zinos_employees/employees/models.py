from django.db import models
from django.core.validators import MinValueValidator
from django.utils import timezone

class Department(models.Model):
    name = models.CharField(max_length=100, verbose_name="اسم القسم")
    description = models.TextField(blank=True, verbose_name="وصف القسم")
    
    class Meta:
        verbose_name = "قسم"
        verbose_name_plural = "الأقسام"
    
    def __str__(self):
        return self.name

class Employee(models.Model):
    EMPLOYEE_TYPES = [
        ('FT', 'دوام كامل'),
        ('PT', 'دوام جزئي'),
        ('CT', 'عقد'),
    ]
    
    name = models.CharField(max_length=100, verbose_name="اسم الموظف")
    department = models.ForeignKey(
        Department, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        verbose_name="القسم"
    )
    employee_type = models.CharField(
        max_length=2, 
        choices=EMPLOYEE_TYPES, 
        default='FT',
        verbose_name="نوع التوظيف"
    )
    salary = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=0,
        verbose_name="الراتب الأساسي"
    )
    hire_date = models.DateField(
        null=True, 
        blank=True,
        verbose_name="تاريخ التعيين"
    )
    phone = models.CharField(
        max_length=20, 
        blank=True,
        verbose_name="رقم الهاتف"
    )
    email = models.EmailField(
        blank=True,
        verbose_name="البريد الإلكتروني"
    )
    address = models.TextField(
        blank=True,
        verbose_name="العنوان"
    )
    manager = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='subordinates',
        verbose_name="المدير المسؤول"
    )
    
    class Meta:
        verbose_name = "موظف"
        verbose_name_plural = "الموظفون"
    
    def __str__(self):
        return self.name

class Attendance(models.Model):
    employee = models.ForeignKey(
        Employee, 
        on_delete=models.CASCADE,
        verbose_name="الموظف"
    )
    date = models.DateField(verbose_name="التاريخ")
    check_in = models.TimeField(verbose_name="وقت الحضور")
    check_out = models.TimeField(
        null=True, 
        blank=True,
        verbose_name="وقت الانصراف"
    )
    is_present = models.BooleanField(
        default=True,
        verbose_name="حاضر"
    )
    notes = models.TextField(
        blank=True,
        verbose_name="ملاحظات"
    )
    
    class Meta:
        verbose_name = "حضور"
        verbose_name_plural = "سجلات الحضور"
    
    def __str__(self):
        return f"{self.employee.name} - {self.date}"

class SalaryPayment(models.Model):
    employee = models.ForeignKey(
        Employee, 
        on_delete=models.CASCADE,
        related_name='salary_payments',
        verbose_name="الموظف"
    )
    month = models.PositiveIntegerField(
        validators=[MinValueValidator(1)],
        verbose_name="الشهر"
    )
    year = models.PositiveIntegerField(verbose_name="السنة")
    working_days = models.PositiveIntegerField(
        default=0,
        verbose_name="أيام العمل"
    )
    actual_salary = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=0,
        verbose_name="الراتب الفعلي"
    )
    payment_date = models.DateField(
        default=timezone.now,
        verbose_name="تاريخ الدفع"
    )
    approved_by = models.ForeignKey(
        Employee,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_payments',
        verbose_name="وافق عليه"
    )
    notes = models.TextField(
        blank=True,
        verbose_name="ملاحظات"
    )
    
    class Meta:
        verbose_name = "دفع الراتب"
        verbose_name_plural = "مدفوعات الرواتب"
    
    def __str__(self):
        return f"{self.employee.name} - {self.month}/{self.year}"