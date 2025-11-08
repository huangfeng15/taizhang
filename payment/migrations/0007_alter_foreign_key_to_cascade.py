# Generated manually to fix contract deletion issue

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('payment', '0006_add_qualitative_review_to_bid_evaluation_method'),
        ('contract', '0011_add_contract_type'),
    ]

    operations = [
        migrations.AlterField(
            model_name='payment',
            name='contract',
            field=models.ForeignKey(
                help_text='该付款对应的合同（对应CSV的"合同编号或序号"列）',
                on_delete=django.db.models.deletion.CASCADE,  # 改为 CASCADE
                related_name='payments',
                to='contract.contract',
                verbose_name='关联合同'
            ),
        ),
    ]