import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):
    """Step 1/3: naye columns jodo. url_hash abhi unique nahi hai (purana data
    pehle saaf karna hai); unique 0004 mein lagega."""

    dependencies = [
        ('indexing', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='urlsubmission',
            name='inspection_status',
            field=models.CharField(
                choices=[
                    ('not_inspected', 'Not inspected'),
                    ('pending', 'Pending'),
                    ('indexed', 'Indexed'),
                    ('not_indexed', 'Not indexed'),
                    ('error', 'Error'),
                ],
                default='not_inspected',
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name='urlsubmission',
            name='indexing_request_status',
            field=models.CharField(
                choices=[
                    ('not_requested', 'Not requested'),
                    ('pending', 'Pending'),
                    ('submitted', 'Submitted'),
                    ('failed', 'Failed'),
                ],
                default='not_requested',
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name='urlsubmission',
            name='updated_at',
            field=models.DateTimeField(auto_now=True, default=django.utils.timezone.now),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='urlsubmission',
            name='url_hash',
            field=models.CharField(default='', editable=False, max_length=64),
            preserve_default=False,
        ),
    ]