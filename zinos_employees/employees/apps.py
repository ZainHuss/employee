from django.apps import AppConfig
from suit.apps import DjangoSuitConfig

class EmployeesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'employees'

