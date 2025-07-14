from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
import os
from django.utils.translation import gettext_lazy as _

def employee_image_path(instance, filename):
    """دالة لتحديد مسار حفظ صورة الموظف"""
    ext = filename.split('.')[-1]
    return f'employees/employee_{instance.id}/profile.{ext}'

class Department(models.Model):
    name = models.CharField(max_length=100, verbose_name=_("اسم القسم"))
    description = models.TextField(blank=True, verbose_name=_("وصف القسم"))
    
    class Meta:
        verbose_name = _("قسم")
        verbose_name_plural = _("الأقسام")
    
    def __str__(self):
        return self.name

class Employee(models.Model):
    EMPLOYEE_TYPES = [
        ('FT', _('دوام كامل')),
        ('PT', _('دوام جزئي')),
        ('CT', _('عقد')),
    ]
    
    name = models.CharField(max_length=100, verbose_name=_("اسم الموظف"))
    department = models.ForeignKey(
        Department, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        verbose_name=_("القسم")
    )
    employee_type = models.CharField(
        max_length=2, 
        choices=EMPLOYEE_TYPES, 
        default='FT',
        verbose_name=_("نوع التوظيف")
    )
    salary = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=0,
        validators=[MinValueValidator(0)],
        verbose_name=_("الراتب الأساسي")
    )
    hire_date = models.DateField(
        null=True, 
        blank=True,
        verbose_name=_("تاريخ التعيين")
    )
    phone = models.CharField(
        max_length=20, 
        blank=True,
        verbose_name=_("رقم الهاتف")
    )
    email = models.EmailField(
        blank=True,
        verbose_name=_("البريد الإلكتروني")
    )
    address = models.TextField(
        blank=True,
        verbose_name=_("العنوان")
    )
    manager = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='subordinates',
        verbose_name=_("المدير المسؤول")
    )
    image = models.ImageField(
        upload_to=employee_image_path,
        null=True,
        blank=True,
        verbose_name=_("صورة الموظف")
    )
    
    class Meta:
        verbose_name = _("موظف")
        verbose_name_plural = _("الموظفون")
        ordering = ['name']
    
    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        if self.pk:
            try:
                old = Employee.objects.get(pk=self.pk)
                if old.image and old.image != self.image:
                    old.image.delete(save=False)
            except Employee.DoesNotExist:
                pass
        super().save(*args, **kwargs)

class Attendance(models.Model):
    employee = models.ForeignKey(
        Employee, 
        on_delete=models.CASCADE,
        verbose_name=_("الموظف")
    )
    date = models.DateField(verbose_name=_("التاريخ"))
    check_in = models.TimeField(verbose_name=_("وقت الحضور"))
    check_out = models.TimeField(
        null=True, 
        blank=True,
        verbose_name=_("وقت الانصراف")
    )
    is_present = models.BooleanField(
        default=True,
        verbose_name=_("حاضر")
    )
    notes = models.TextField(
        blank=True,
        verbose_name=_("ملاحظات")
    )
    
    class Meta:
        verbose_name = _("حضور")
        verbose_name_plural = _("سجلات الحضور")
        unique_together = ('employee', 'date')
        ordering = ['-date', 'employee']
    
    def __str__(self):
        return f"{self.employee.name} - {self.date}"

class SalaryPayment(models.Model):
    employee = models.ForeignKey(
        Employee, 
        on_delete=models.CASCADE,
        related_name='salary_payments',
        verbose_name=_("الموظف")
    )
    month = models.PositiveIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(12)],
        verbose_name=_("الشهر")
    )
    year = models.PositiveIntegerField(
        validators=[MinValueValidator(2000)],
        verbose_name=_("السنة")
    )
    working_days = models.PositiveIntegerField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(31)],
        verbose_name=_("أيام العمل")
    )
    actual_salary = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=0,
        validators=[MinValueValidator(0)],
        verbose_name=_("الراتب الفعلي")
    )
    payment_date = models.DateField(
        default=timezone.now,
        verbose_name=_("تاريخ الدفع")
    )
    approved_by = models.ForeignKey(
        Employee,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_payments',
        verbose_name=_("وافق عليه")
    )
    notes = models.TextField(
        blank=True,
        verbose_name=_("ملاحظات")
    )
    
    class Meta:
        verbose_name = _("دفع الراتب")
        verbose_name_plural = _("مدفوعات الرواتب")
        unique_together = ('employee', 'month', 'year')
        ordering = ['-year', '-month', 'employee']
    
    def __str__(self):
        return f"{self.employee.name} - {self.month}/{self.year}"