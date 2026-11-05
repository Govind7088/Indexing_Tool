from django.db import migrations, models


class Migration(migrations.Migration):
    """Step 3/3: ab jab data saaf hai, url_hash par unique constraint lagao."""

    dependencies = [
        ('indexing', '0003_backfill_url_hash_dedupe'),
    ]

    operations = [
        migrations.AlterField(
            model_name='urlsubmission',
            name='url_hash',
            field=models.CharField(editable=False, max_length=64, unique=True),
        ),
    ]