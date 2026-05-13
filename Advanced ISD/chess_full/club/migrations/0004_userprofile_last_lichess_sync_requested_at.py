from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('club', '0003_userprofile_theme_preference'),
    ]

    operations = [
        migrations.AddField(
            model_name='userprofile',
            name='last_lichess_sync_requested_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
