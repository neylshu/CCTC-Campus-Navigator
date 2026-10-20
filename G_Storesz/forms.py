from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError

from .models import CampusLocation, Student

User = get_user_model()


class CampusLocationForm(forms.ModelForm):
    class Meta:
        model = CampusLocation
        fields = (
            'location_name',
            'category',
            'description',
            'building_floor',
            'x_coordinate',
            'y_coordinate',
            'office_hours',
            'contact_person',
            'image',
        )
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
            'x_coordinate': forms.NumberInput(attrs={'step': 'any', 'min': '0', 'max': '100'}),
            'y_coordinate': forms.NumberInput(attrs={'step': 'any', 'min': '0', 'max': '100'}),
        }


class StudentLoginForm(AuthenticationForm):
    username = forms.CharField(
        label='Student number',
        widget=forms.TextInput(attrs={'autocomplete': 'username', 'placeholder': 'e.g. 2026-00123'}),
    )
    password = forms.CharField(
        label='Password',
        strip=False,
        widget=forms.PasswordInput(attrs={'autocomplete': 'current-password'}),
    )


class StudentSignUpForm(forms.ModelForm):
    field_order = (
        'first_name',
        'last_name',
        'student_number',
        'course',
        'year_level',
        'email',
        'password1',
        'password2',
    )
    first_name = forms.CharField(
        label='First name',
        max_length=150,
        widget=forms.TextInput(attrs={'autocomplete': 'given-name', 'placeholder': 'Juan'}),
    )
    last_name = forms.CharField(
        label='Last name',
        max_length=150,
        widget=forms.TextInput(attrs={'autocomplete': 'family-name', 'placeholder': 'Dela Cruz'}),
    )
    email = forms.EmailField(
        label='Email',
        required=False,
        widget=forms.EmailInput(attrs={'autocomplete': 'email', 'placeholder': 'you@cctc.edu.ph'}),
    )
    password1 = forms.CharField(
        label='Password',
        strip=False,
        widget=forms.PasswordInput(attrs={'autocomplete': 'new-password'}),
        help_text='At least 8 characters. It cannot be entirely numeric.',
    )
    password2 = forms.CharField(
        label='Confirm password',
        strip=False,
        widget=forms.PasswordInput(attrs={'autocomplete': 'new-password'}),
    )

    class Meta:
        model = Student
        fields = ('student_number', 'course', 'year_level')
        widgets = {
            'student_number': forms.TextInput(attrs={'placeholder': 'e.g. 2026-00123'}),
            'course': forms.TextInput(attrs={'placeholder': 'e.g. BS Information Technology'}),
            'year_level': forms.Select(),
        }

    def clean_student_number(self):
        student_number = self.cleaned_data['student_number'].strip()
        if Student.objects.filter(student_number__iexact=student_number).exists():
            raise forms.ValidationError('A student account already exists for this student number.')
        if User.objects.filter(username__iexact=student_number).exists():
            raise forms.ValidationError('This student number is already registered.')
        return student_number

    def clean_email(self):
        email = self.cleaned_data.get('email', '').strip()
        if email and User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError('An account already uses this email address.')
        return email

    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get('password1')
        password2 = cleaned_data.get('password2')

        if password1 and password2 and password1 != password2:
            self.add_error('password2', 'The two passwords do not match.')
        if password1:
            try:
                validate_password(password1)
            except DjangoValidationError as error:
                self.add_error('password1', error)

        return cleaned_data

    def save(self, commit=True):
        student = super().save(commit=False)
        user = User.objects.create_user(
            username=student.student_number,
            email=self.cleaned_data.get('email', ''),
            first_name=self.cleaned_data.get('first_name', ''),
            last_name=self.cleaned_data.get('last_name', ''),
            password=self.cleaned_data['password1'],
        )
        student.user = user
        if commit:
            student.save()
        return student