# Generated migration to rename contract_type to file_positioning

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('contract', '0007_update_contract_contact_fields'),
    ]

    operations = [
        migrations.RenameField(
            model_name='contract',
            old_name='contract_type',
            new_name='file_positioning',
        ),
    ]