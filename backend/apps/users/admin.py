from django import forms
from django.contrib import admin
from django.contrib.auth.admin import GroupAdmin as BaseGroupAdmin, UserAdmin as BaseUserAdmin
from django.contrib.auth.models import Group
from django.contrib.auth.forms import ReadOnlyPasswordHashField
from django.db.models import Count, Prefetch, Q
from django.urls import reverse
from django.utils.html import format_html

from applications.models import Application
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
    list_display = (
        'email',
        'role_badge',
        'is_active',
        'applications_stats',
        'contact_display',
        'telegram_display',
        'primary_platform',
        'last_activity',
        'quick_actions',
    )
    search_fields = (
        'email',
        'phone',
        'telegram_username',
        'telegram_chat_id',
        'website_session_token',
    )
    ordering = ('-created_at',)
    readonly_fields = (
        'created_at',
        'last_login',
        'last_telegram_activity',
        'last_website_activity',
        'applications_count',
        'submitted_count',
        'draft_count',
    )
    actions = ('activate_users', 'deactivate_users', 'mark_as_employee')
    date_hierarchy = 'created_at'
    list_display_links = ('email',)
    search_help_text = 'Ищите по email, телефону, Telegram или токену сессии'

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
        ('Статистика по заявкам', {
            'fields': (
                'applications_count',
                'submitted_count',
                'draft_count',
            ),
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
                'is_superuser',
                'groups',
            ),
        }),
    )

    filter_horizontal = ('groups', 'user_permissions')

    class HasApplicationsFilter(admin.SimpleListFilter):
        title = 'Заявки'
        parameter_name = 'has_applications'

        def lookups(self, request, model_admin):
            return (
                ('yes', 'Есть заявки'),
                ('no', 'Нет заявок'),
                ('drafts', 'Есть только черновики'),
            )

        def queryset(self, request, queryset):
            value = self.value()
            if value == 'yes':
                return queryset.annotate(app_total=Count('applications', distinct=True)).filter(app_total__gt=0)
            if value == 'no':
                return queryset.annotate(app_total=Count('applications', distinct=True)).filter(app_total=0)
            if value == 'drafts':
                return queryset.annotate(
                    drafts=Count('applications', filter=Q(applications__status=Application.Status.DRAFT), distinct=True),
                    submitted=Count('applications', filter=~Q(applications__status=Application.Status.DRAFT), distinct=True),
                ).filter(drafts__gt=0, submitted=0)
            return queryset

    class HasTelegramFilter(admin.SimpleListFilter):
        title = 'Telegram'
        parameter_name = 'has_telegram'

        def lookups(self, request, model_admin):
            return (
                ('yes', 'Есть связка'),
                ('no', 'Нет связки'),
            )

        def queryset(self, request, queryset):
            value = self.value()
            if value == 'yes':
                return queryset.filter(
                    Q(telegram_chat_id__isnull=False, telegram_chat_id__gt=0)
                    | ~Q(telegram_username__exact='')
                )
            if value == 'no':
                return queryset.filter(
                    Q(telegram_chat_id__isnull=True) | Q(telegram_chat_id=0),
                    Q(telegram_username__isnull=True) | Q(telegram_username=''),
                )
            return queryset

    list_filter = (
        'role',
        'is_active',
        'is_staff',
        'primary_platform',
        'last_platform_used',
        'created_at',
        'groups',
        HasApplicationsFilter,
        HasTelegramFilter,
    )

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        applications_qs = Application.objects.only('status', 'user_id')
        return queryset.annotate(
            applications_total=Count('applications', distinct=True),
            applications_submitted=Count(
                'applications',
                filter=Q(applications__status=Application.Status.SUBMITTED)
                | Q(applications__status=Application.Status.UNDER_REVIEW)
                | Q(applications__status=Application.Status.APPROVED)
                | Q(applications__status=Application.Status.REJECTED),
                distinct=True,
            ),
            applications_draft=Count(
                'applications',
                filter=Q(applications__status=Application.Status.DRAFT),
                distinct=True,
            ),
        ).prefetch_related(Prefetch('applications', queryset=applications_qs))

    def applications_count(self, obj):
        return obj.applications_total

    applications_count.short_description = 'Всего заявок'

    def submitted_count(self, obj):
        return obj.applications_submitted

    submitted_count.short_description = 'Отправлено'

    def draft_count(self, obj):
        return obj.applications_draft

    draft_count.short_description = 'Черновики'

    def role_badge(self, obj):
        colors = {
            User.Role.APPLICANT: '#0d6efd',
            User.Role.EMPLOYEE: '#198754',
            User.Role.ADMIN: '#6f42c1',
        }
        color = colors.get(obj.role, '#6c757d')
        label = obj.get_role_display()
        return format_html(
            '<span style="padding:2px 8px;border-radius:999px;background:{};color:#fff;">{}</span>',
            color,
            label,
        )

    role_badge.short_description = 'Роль'

    def applications_stats(self, obj):
        total = obj.applications_total
        submitted = obj.applications_submitted
        drafts = obj.applications_draft
        return f"{submitted} отправлено / {drafts} черновиков (из {total})"

    applications_stats.short_description = 'Заявки'

    def contact_display(self, obj):
        pieces = []
        if obj.phone:
            pieces.append(obj.phone)
        if obj.email:
            pieces.append(obj.email)
        return '\n'.join(pieces) if pieces else '—'

    contact_display.short_description = 'Контакты'

    def telegram_display(self, obj):
        if obj.telegram_username:
            return f"@{obj.telegram_username}"
        if obj.telegram_chat_id:
            return f"ID: {obj.telegram_chat_id}"
        return '—'

    telegram_display.short_description = 'Telegram'

    def last_activity(self, obj):
        dates = [d for d in [obj.last_login, obj.last_telegram_activity, obj.last_website_activity] if d]
        if not dates:
            return '—'
        latest = max(dates)
        source = 'Telegram' if latest == obj.last_telegram_activity else 'Сайт' if latest == obj.last_website_activity else 'Вход'
        return f"{latest:%Y-%m-%d %H:%M} ({source})"

    last_activity.short_description = 'Последняя активность'

    def quick_actions(self, obj):
        apps_url = f"{reverse('admin:applications_application_changelist')}?user__id__exact={obj.pk}"
        comment_url = f"{reverse('admin:applications_applicationcomment_changelist')}?user__id__exact={obj.pk}"
        actions = [
            format_html('<a class="button" href="{}" target="_blank">Заявки</a>', apps_url),
            format_html('<a class="button" href="{}" target="_blank">Комментарии</a>', comment_url),
        ]
        return format_html(' '.join(str(action) for action in actions))

    quick_actions.short_description = 'Быстрые действия'

    @admin.action(description='Активировать пользователей')
    def activate_users(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f'Активировано пользователей: {updated}')

    @admin.action(description='Деактивировать пользователей')
    def deactivate_users(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f'Деактивировано пользователей: {updated}')

    @admin.action(description='Назначить роль "Сотрудник"')
    def mark_as_employee(self, request, queryset):
        updated = queryset.update(role=User.Role.EMPLOYEE)
        self.message_user(request, f'Назначено сотрудников: {updated}')


class GroupAdmin(BaseGroupAdmin):
    list_display = ('name', 'members_count', 'permissions_summary')
    search_fields = ('name', 'permissions__codename', 'permissions__name')
    list_filter = ('permissions__content_type__app_label',)
    filter_horizontal = ('permissions',)
    ordering = ('name',)

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        return queryset.annotate(users_total=Count('user', distinct=True)).prefetch_related('permissions')

    def members_count(self, obj):
        return obj.users_total

    members_count.short_description = 'Пользователей'

    def permissions_summary(self, obj):
        perms = list(obj.permissions.all()[:5])
        if not perms:
            return '—'
        labels = ', '.join(permission.name for permission in perms)
        if obj.permissions.count() > len(perms):
            labels += '…'
        return labels

    permissions_summary.short_description = 'Права'


admin.site.unregister(Group)
admin.site.register(Group, GroupAdmin)
