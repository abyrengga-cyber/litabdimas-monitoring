from django import forms
from .models import Activity, User

class ActivityForm(forms.ModelForm):
    class Meta:
        model = Activity
        fields = ['title', 'description', 'category', 'dana', 'proposal_file']
        labels = {
            'title': 'Judul',
            'category': 'Kategori',
            'description': 'Deskripsi',
        }
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
        }

class ReportForm(forms.ModelForm):
    class Meta:
        model = Activity
        fields = ['report_file', 'output_link']
        labels = {
            'report_file': 'Upload Laporan Akhir (PDF)',
            'output_link': 'Link Output / Publikasi (opsional)',
        }
        widgets = {
            'output_link': forms.URLInput(attrs={'placeholder': 'https://...'}),
        }

class ProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'nidn', 'phone', 'prodi', 'fakultas']
        labels = {
            'first_name': 'Nama Depan',
            'last_name': 'Nama Belakang',
            'nidn': 'NIDN',
            'phone': 'No. Telepon',
            'prodi': 'Program Studi',
            'fakultas': 'Fakultas',
        }

from django.contrib.auth.forms import UserCreationForm

class UserAdminCreationForm(UserCreationForm):
    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name', 'role', 'nidn', 'phone', 'prodi', 'fakultas']

class UserAdminChangeForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name', 'role', 'nidn', 'phone', 'prodi', 'fakultas']
