# Generated manually to fix contract deletion issue

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('supplier_eval', '0002_supplierinterview_alter_supplierevaluation_options_and_more'),
        ('contract', '0011_add_contract_type'),
    ]

    operations = [
        migrations.AlterField(
            model_name='supplierevaluation',
            name='contract',
            field=models.ForeignKey(
                help_text='该评价对应的合同（对应CSV的"合同序号"列）',
                on_delete=django.db.models.deletion.CASCADE,  # 改为 CASCADE
                related_name='evaluations',
                to='contract.contract',
                verbose_name='关联合同'
            ),
        ),
    ]