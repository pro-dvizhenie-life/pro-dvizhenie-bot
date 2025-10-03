from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0008_magiclinktoken'),
    ]

    operations = [
        migrations.AlterField(
            model_name='user',
            name='phone',
            field=models.CharField(
                verbose_name='Номер телефона',
                max_length=32,
                null=True,
                blank=True,
            ),
        ),
    ]
