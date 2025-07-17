from django import forms
from .models import Employee

class EmployeeForm(forms.ModelForm):
    class Meta:
        model = Employee
        fields = '__all__'
        widgets = {
            'hire_date': forms.DateInput(attrs={'type': 'date'}),
            'phone': forms.TextInput(attrs={'placeholder': 'ادخل رقم الهاتف'}),
            'image': forms.FileInput(attrs={'class': 'form-control-file'})
        }
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['manager'].queryset = Employee.objects.filter(subordinates__isnull=False).distinct()
class EmployeeAdminForm(forms.ModelForm):
    class Meta:
        model = Employee
        fields = '__all__'
    
    def clean_image(self):
        image = self.cleaned_data.get('image')
        if image and not hasattr(image, 'file'):  # إذا لم تكن كائن File
            from django.core.files.base import ContentFile
            return ContentFile(image, name='uploaded_image.jpg')
        return image