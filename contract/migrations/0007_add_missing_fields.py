# Generated manually to fix missing contract_type and other fields

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('contract', '0006_add_archive_date'),
    ]

    operations = [
        # 添加 contract_type 字段
        migrations.AddField(
            model_name='contract',
            name='contract_type',
            field=models.CharField(
                choices=[('主合同', '主合同'), ('补充协议', '补充协议'), ('解除协议', '解除协议')],
                default='主合同',
                help_text='区分主合同和补充协议',
                max_length=20,
                verbose_name='合同类型'
            ),
        ),
        # 添加 party_b_contact 字段
        migrations.AddField(
            model_name='contract',
            name='party_b_contact',
            field=models.CharField(
                blank=True,
                help_text='例如: 李经理 13900139000',
                max_length=200,
                verbose_name='乙方负责人及联系方式'
            ),
        ),
        # 添加 party_b_contact_in_contract 字段
        migrations.AddField(
            model_name='contract',
            name='party_b_contact_in_contract',
            field=models.CharField(
                blank=True,
                help_text='合同文本中记录的乙方联系方式',
                max_length=200,
                verbose_name='合同文本内乙方联系人及方式'
            ),
        ),
        # 删除旧的不再使用的字段
        migrations.RemoveField(
            model_name='contract',
            name='file_positioning',
        ),
        migrations.RemoveField(
            model_name='contract',
            name='party_a_legal_representative',
        ),
        migrations.RemoveField(
            model_name='contract',
            name='party_a_contact_person',
        ),
        migrations.RemoveField(
            model_name='contract',
            name='party_a_manager',
        ),
        migrations.RemoveField(
            model_name='contract',
            name='party_b_legal_representative',
        ),
        migrations.RemoveField(
            model_name='contract',
            name='party_b_contact_person',
        ),
        migrations.RemoveField(
            model_name='contract',
            name='party_b_manager',
        ),
    ]