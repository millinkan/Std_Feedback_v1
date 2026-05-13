from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('club', '0002_userprofile'),
    ]

    operations = [
        migrations.AddField(
            model_name='userprofile',
            name='theme_preference',
            field=models.CharField(
                choices=[
                    ('classic', 'Classic Light'),
                    ('midnight', 'Midnight Dark'),
                    ('forest', 'Forest Green'),
                    ('royal', 'Royal Blue'),
                ],
                default='classic',
                max_length=20,
            ),
        ),
    ]
