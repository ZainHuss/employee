from django.urls import path
from . import views
from django.conf.urls.static import static
from django.conf import settings
from .views import employee_detail


from .views import export_employees_to_excel
urlpatterns = [
    path('', views.employee_list, name='employee_list'),
    path('employee/<int:pk>/', employee_detail, name='employee_detail'),
    path('<int:pk>/calculate-salary/', views.calculate_salary, name='calculate_salary'),
    path('employees/export/', export_employees_to_excel, name='export_employees'),
]