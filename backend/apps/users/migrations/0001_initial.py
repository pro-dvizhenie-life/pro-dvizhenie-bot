# Generated manually to introduce the custom User model

import users.models
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ('auth', '0012_alter_user_first_name_max_length'),
    ]

    operations = [
        migrations.CreateModel(
            name='User',
            fields=[
                ('password', models.CharField(max_length=128, verbose_name='password')),
                ('last_login', models.DateTimeField(blank=True, null=True, verbose_name='last login')),
                ('is_superuser', models.BooleanField(
                    default=False,
                    help_text='Designates that this user has all permissions without explicitly assigning them.',
                    verbose_name='superuser status',
                )),
                (
                    'id',
                    models.AutoField(
                        editable=False,
                        primary_key=True,
                        serialize=False,
                        verbose_name='Идентификатор',
                    ),
                ),
                ('email', models.EmailField(max_length=254, unique=True)),
                ('phone', models.CharField(blank=True, max_length=32, null=True, unique=True)),
                (
                    'role',
                    models.CharField(
                        choices=[('admin', 'Admin'), ('analyst', 'Analyst'), ('viewer', 'Viewer')],
                        default='viewer',
                        max_length=20,
                    ),
                ),
                ('telegram_chat_id', models.BigIntegerField(blank=True, null=True, unique=True)),
                ('telegram_username', models.CharField(blank=True, max_length=100, null=True)),
                (
                    'website_session_token',
                    models.CharField(blank=True, max_length=255, null=True, unique=True),
                ),
                (
                    'primary_platform',
                    models.CharField(
                        blank=True,
                        choices=[('web', 'Web'), ('telegram', 'Telegram')],
                        max_length=20,
                        null=True,
                    ),
                ),
                (
                    'last_platform_used',
                    models.CharField(
                        blank=True,
                        choices=[('web', 'Web'), ('telegram', 'Telegram')],
                        max_length=20,
                        null=True,
                    ),
                ),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('last_telegram_activity', models.DateTimeField(blank=True, null=True)),
                ('last_website_activity', models.DateTimeField(blank=True, null=True)),
                ('is_active', models.BooleanField(default=True)),
                ('is_staff', models.BooleanField(default=False)),
                (
                    'groups',
                    models.ManyToManyField(
                        blank=True,
                        help_text='The groups this user belongs to. A user will get all permissions granted to each of their groups.',
                        related_name='user_set',
                        related_query_name='user',
                        to='auth.group',
                        verbose_name='groups',
                    ),
                ),
                (
                    'user_permissions',
                    models.ManyToManyField(
                        blank=True,
                        help_text='Specific permissions for this user.',
                        related_name='user_set',
                        related_query_name='user',
                        to='auth.permission',
                        verbose_name='user permissions',
                    ),
                ),
            ],
            options={
                'verbose_name': 'User',
                'verbose_name_plural': 'Users',
                'ordering': ('-created_at',),
            },
            managers=[
                ('objects', users.models.UserManager()),
            ],
        ),
    ]
