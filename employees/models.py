from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from datetime import datetime
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.contrib.auth import get_user_model

User = get_user_model()

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
        ordering = ['name']
    
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
    user = models.OneToOneField(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='employee_profile',
        verbose_name=_("حساب المستخدم")
    )
    salary = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=0,
        validators=[MinValueValidator(0)],
        verbose_name=_("الراتب الأساسي")
    )
    deductions = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)],
        verbose_name=_("الاستقطاعات الشهرية")
    )
    bonuses = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)],
        verbose_name=_("العلاوات الشهرية")
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
        upload_to='employee_images/', 
        blank=True, 
        null=True, 
        verbose_name=_("صورة الموظف")
    )
    performance_score = models.FloatField(
        default=5.0,
        validators=[MinValueValidator(1.0), MaxValueValidator(10.0)],
        verbose_name=_("تقييم الأداء (من 10)")
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name=_("موظف نشط")
    )
    resignation_date = models.DateField(
        null=True,
        blank=True,
        verbose_name=_("تاريخ الاستقالة")
    )
    resignation_reason = models.TextField(
        blank=True,
        verbose_name=_("سبب الاستقالة")
    )

    @property
    def daily_salary(self):
        """حساب الراتب اليومي"""
        return round(self.salary / 30, 2)

    def current_month_attendance(self):
        """استرجاع حضور الشهر الحالي"""
        today = timezone.now()
        return self.attendance_set.filter(
            date__month=today.month,
            date__year=today.year
        ).order_by('-date')
    
    def attendance_percentage(self):
        """حساب نسبة الحضور"""
        today = timezone.now()
        attendances = self.attendance_set.filter(
            date__month=today.month,
            date__year=today.year
        )
        total_days = attendances.count()
        present_days = attendances.filter(status='present').count()
        return round((present_days / total_days * 100), 2) if total_days else 0
    
    def calculate_net_salary(self, working_days):
        """حساب صافي الراتب بناءً على أيام العمل"""
        base_salary = round(self.daily_salary * working_days, 2)
        return base_salary - self.deductions + self.bonuses
    
    class Meta:
        verbose_name = _("موظف")
        verbose_name_plural = _("الموظفون")
        ordering = ['name']
        indexes = [
            models.Index(fields=['name']),
            models.Index(fields=['department']),
            models.Index(fields=['hire_date']),
        ]
    
    def __str__(self):
        return self.name
    
    def get_image_url(self):
        """دالة للحصول على رابط الصورة أو صورة افتراضية"""
        if self.image and hasattr(self.image, 'url'):
            return self.image.url
        return '/static/images/default_avatar.png'
    
    def save(self, *args, **kwargs):
        if self.image and not hasattr(self.image, 'url'):
            temp_file = ContentFile(self.image)
            self.image.save(f'employee_{self.pk}_image.jpg', temp_file)
        super().save(*args, **kwargs)

class PerformanceReview(models.Model):
    RATING_CHOICES = [
        (1, 'Poor'),
        (2, 'Below Average'),
        (3, 'Average'),
        (4, 'Good'),
        (5, 'Excellent'),
    ]
    
    employee = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE,
        related_name='performance_reviews',
        verbose_name=_("الموظف")
    )
    review_date = models.DateField(
        default=timezone.now,
        verbose_name=_("تاريخ التقييم")
    )
    reviewer = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        verbose_name=_("المقيّم")
    )
    rating = models.PositiveIntegerField(
        choices=RATING_CHOICES,
        verbose_name=_("التقييم")
    )
    comments = models.TextField(
        blank=True,
        verbose_name=_("ملاحظات")
    )
    goals = models.TextField(
        blank=True,
        verbose_name=_("الأهداف")
    )
    strengths = models.TextField(
        blank=True,
        verbose_name=_("نقاط القوة")
    )
    areas_for_improvement = models.TextField(
        blank=True,
        verbose_name=_("مجالات التحسين")
    )
    
    class Meta:
        verbose_name = _("تقييم الأداء")
        verbose_name_plural = _("تقييمات الأداء")
        ordering = ['-review_date']
        indexes = [
            models.Index(fields=['employee', 'review_date']),
        ]
    
    def __str__(self):
        return f"{self.employee.name} - {self.review_date} - {self.get_rating_display()}"

class Attendance(models.Model):
    PRESENT = 'present'
    ABSENT = 'absent'
    STATUS_CHOICES = [
        (PRESENT, _('حاضر')),
        (ABSENT, _('غائب')),
    ]
    
    employee = models.ForeignKey(
        Employee, 
        on_delete=models.CASCADE,
        verbose_name=_("الموظف")
    )
    date = models.DateField(verbose_name=_("التاريخ"))
    check_in = models.TimeField(
        null=True,
        blank=True,
        verbose_name=_("وقت الحضور"))
    check_out = models.TimeField(
        null=True, 
        blank=True,
        verbose_name=_("وقت الانصراف"))
    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default=PRESENT,
        verbose_name=_("حالة الحضور"))
    notes = models.TextField(
        blank=True,
        verbose_name=_("ملاحظات"))
    working_hours = models.FloatField(
        default=0.0,
        verbose_name=_("ساعات العمل"),
        editable=False
    )
    ABSENCE_TYPES = [
        ('sick', _('مرض')),
        ('vacation', _('إجازة')),
        ('unauthorized', _('غياب غير مبرر')),
    ]
    absence_type = models.CharField(
        max_length=15,
        choices=ABSENCE_TYPES,
        blank=True,
        null=True,
        verbose_name=_("نوع الغياب")
    )
    
    @property
    def is_present(self):
        """خاصية حسابية لتحديد إذا كان الموظف حاضراً"""
        return self.status == self.PRESENT
    
    def save(self, *args, **kwargs):
        """حساب ساعات العمل تلقائياً عند الحفظ"""
        if self.check_in and self.check_out:
            delta = datetime.combine(self.date, self.check_out) - datetime.combine(self.date, self.check_in)
            self.working_hours = round(delta.total_seconds() / 3600, 2)
        else:
            self.working_hours = 0.0
        super().save(*args, **kwargs)

    def get_working_hours(self):
        if self.check_in and self.check_out:
            delta = datetime.combine(self.date, self.check_out) - datetime.combine(self.date, self.check_in)
            return round(delta.total_seconds() / 3600, 2)
        return 0
    
    class Meta:
        verbose_name = _("حضور")
        verbose_name_plural = _("سجلات الحضور")
        unique_together = ('employee', 'date')
        ordering = ['-date', 'employee']
        indexes = [
            models.Index(fields=['employee', 'date']),
            models.Index(fields=['status']),
            models.Index(fields=['date']),
            models.Index(fields=['working_hours']),
        ]
    
    def __str__(self):
        return f"{self.employee.name} - {self.date} - {self.get_status_display()}"

class SalaryPayment(models.Model):
    employee = models.ForeignKey(
        Employee, 
        on_delete=models.CASCADE,
        related_name='salary_payments',
        verbose_name=_("الموظف"))
    month = models.PositiveIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(12)],
        verbose_name=_("الشهر"))
    year = models.PositiveIntegerField(
        validators=[MinValueValidator(2000)],
        verbose_name=_("السنة"))
    working_days = models.PositiveIntegerField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(31)],
        verbose_name=_("أيام العمل"))
    absent_days = models.PositiveIntegerField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(31)],
        verbose_name=_("أيام الغياب"))
    base_salary = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=0,
        validators=[MinValueValidator(0)],
        verbose_name=_("الراتب الأساسي"))
    deductions = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)],
        verbose_name=_("الاستقطاعات"))
    bonuses = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)],
        verbose_name=_("العلاوات"))
    net_salary = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)],
        verbose_name=_("صافي الراتب"))
    payment_date = models.DateField(
        default=timezone.now,
        verbose_name=_("تاريخ الدفع"))
    approved_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_salaries',
        verbose_name=_("وافق عليه"))
    notes = models.TextField(
        blank=True,
        verbose_name=_("ملاحظات"))
    
    class Meta:
        verbose_name = _("دفع الراتب")
        verbose_name_plural = _("مدفوعات الرواتب")
        unique_together = ('employee', 'month', 'year')
        ordering = ['-year', '-month', 'employee']
        indexes = [
            models.Index(fields=['employee']),
            models.Index(fields=['month', 'year']),
            models.Index(fields=['payment_date']),
        ]
    
    def __str__(self):
        return f"{self.employee.name} - {self.month}/{self.year} - {self.net_salary:.2f} ر.س"
    
class EmployeePrediction(models.Model):
    employee = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE,
        related_name='predictions',
        verbose_name=_("الموظف")
    )
    prediction_date = models.DateField(
        auto_now_add=True,
        verbose_name=_("تاريخ التنبؤ")
    )
    turnover_risk = models.FloatField(
        validators=[MinValueValidator(0), MaxValueValidator(1)],
        verbose_name=_("احتمال الاستقالة")
    )
    performance_trend = models.FloatField(
        verbose_name=_("اتجاه الأداء (آخر 3 أشهر)")
    )
    recommended_action = models.TextField(
        blank=True,
        verbose_name=_("الإجراء المقترح")
    )
    
    class Meta:
        verbose_name = _("تنبؤ الموظف")
        verbose_name_plural = _("تنبؤات الموظفين")
        ordering = ['-prediction_date']
    
    def __str__(self):
        return f"{self.employee.name} - {self.prediction_date}"

class Meta:
    permissions = [
        ('view_analytics', 'Can view analytics dashboard'),
        ('run_predictions', 'Can run predictions manually'),
        ('manage_reviews', 'Can manage performance reviews'),
    ]