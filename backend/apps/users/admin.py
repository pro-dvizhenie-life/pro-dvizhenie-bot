from django import forms
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.forms import ReadOnlyPasswordHashField

from .models import User


class UserCreationForm(forms.ModelForm):
    """Форма для создания нового пользователя в админке."""
    password1 = forms.CharField(label='Password', widget=forms.PasswordInput)
    password2 = forms.CharField(
        label='Password confirmation',
        widget=forms.PasswordInput
    )

    class Meta:
        model = User
        fields = ('email', 'role', 'phone', 'telegram_username')

    def clean_password2(self):
        password1 = self.cleaned_data.get('password1')
        password2 = self.cleaned_data.get('password2')
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError('Passwords do not match')
        return password2

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password1'])
        if commit:
            user.save()
        return user


class UserChangeForm(forms.ModelForm):
    password = ReadOnlyPasswordHashField(label='Password')

    class Meta:
        model = User
        fields = '__all__'

    def clean_password(self):
        return self.initial.get('password')


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Админка для модели User."""
    add_form = UserCreationForm
    form = UserChangeForm
    model = User
    list_display = ('email', 'role', 'is_active', 'is_staff',
                    'created_at', 'last_login')
    list_filter = ('role', 'is_active', 'is_staff', 'primary_platform')
    search_fields = ('email', 'phone', 'telegram_username', 'telegram_chat_id')
    ordering = ('email',)
    readonly_fields = (
        'created_at',
        'last_login',
        'last_telegram_activity',
        'last_website_activity',
    )

    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Profile', {
            'fields': (
                'role',
                'phone',
                'telegram_chat_id',
                'telegram_username',
                'website_session_token',
                'primary_platform',
                'last_platform_used',
            )
        }),
        ('Activity', {
            'fields': (
                'created_at',
                'last_login',
                'last_telegram_activity',
                'last_website_activity',
            )
        }),
        ('Permissions', {'fields': (
            'is_active',
            'is_staff',
            'is_superuser',
            'groups',
            'user_permissions'
        )}),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': (
                'email',
                'role',
                'password1',
                'password2',
                'is_staff',
                'is_superuser'
            ),
        }),
    )

    filter_horizontal = ('groups', 'user_permissions')
