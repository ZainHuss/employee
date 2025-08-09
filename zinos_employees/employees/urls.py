from django.urls import path
from django.conf.urls.static import static
from django.conf import settings
from django.contrib.auth.decorators import login_required, permission_required
from . import views

app_name = 'employees'  # إضافة اسم التطبيق لتجنب التعارض

from .views import export_employees_to_excel
urlpatterns = [
    # الصفحة الرئيسية لقائمة الموظفين
    path('', views.employee_list, name='employee_list'),
    
    # تفاصيل الموظف
    path('employee/<int:pk>/', views.employee_detail, name='employee_detail'),
    
    # تعديل بيانات الموظف
    path('employee/<int:pk>/edit/', 
         login_required(permission_required('employees.change_employee')(views.edit_employee)),
         name='edit_employee'),
    
    # حساب الراتب
    path('employee/<int:pk>/calculate-salary/', 
         login_required(permission_required('employees.calculate_salary')(views.calculate_salary)),
         name='calculate_salary'),
    
    # تصدير بيانات الموظفين
    path('employees/export/', 
         login_required(permission_required('employees.export_employees')(views.export_employees_to_excel)),
         name='export_employees'),
    
    # لوحة التحليلات
    path('analytics/',
         login_required(permission_required('employees.view_analytics')(views.analytics_dashboard)),
         name='analytics_dashboard'),
    
    # تقرير الحضور
    path('employee/<int:pk>/attendance-report/',
         login_required(permission_required('employees.view_attendance_reports')(views.employee_attendance_report)),
         name='employee_attendance_report'),
    
    # تحديث التنبؤات
    path('analytics/update-predictions/',
         login_required(permission_required('employees.run_predictions')(views.update_predictions)),
         name='update_predictions'),
    
    # إضافة تقييم أداء
    path('employee/<int:employee_id>/add-review/',
         login_required(permission_required('employees.manage_reviews')(views.add_performance_review)),
         name='add_performance_review'),
    
    # تفاصيل تقييم الأداء
    path('review/<int:review_id>/',
         login_required(views.performance_review_detail),
         name='performance_review_detail'),
    
    # تصدير بيانات التحليلات
    path('analytics/export/',
         login_required(permission_required('employees.export_analytics')(views.export_analytics)),
         name='export_analytics'),
]

# فقط في بيئة التطوير لخدمة الملفات الثابتة
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)