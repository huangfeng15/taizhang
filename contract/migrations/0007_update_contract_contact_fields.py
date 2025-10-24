"""
合同联系人字段调整迁移
- 删除旧字段: party_b_contact, party_b_contact_in_contract
- 添加新字段: 甲方和乙方的法定代表人、联系人、负责人信息
"""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('contract', '0006_add_archive_date'),
    ]

    operations = [
        # 删除旧字段
        migrations.RemoveField(
            model_name='contract',
            name='party_b_contact',
        ),
        migrations.RemoveField(
            model_name='contract',
            name='party_b_contact_in_contract',
        ),
        
        # 添加新字段 - 甲方相关
        migrations.AddField(
            model_name='contract',
            name='party_a_legal_representative',
            field=models.CharField(
                max_length=200,
                verbose_name='甲方法定代表人及联系方式',
                blank=True,
                help_text='甲方法定代表人姓名及联系方式'
            ),
        ),
        migrations.AddField(
            model_name='contract',
            name='party_a_contact_person',
            field=models.CharField(
                max_length=200,
                verbose_name='甲方联系人及联系方式',
                blank=True,
                help_text='甲方日常联系人及联系方式'
            ),
        ),
        migrations.AddField(
            model_name='contract',
            name='party_a_manager',
            field=models.CharField(
                max_length=200,
                verbose_name='甲方负责人及联系方式',
                blank=True,
                help_text='甲方项目负责人及联系方式'
            ),
        ),
        
        # 添加新字段 - 乙方相关
        migrations.AddField(
            model_name='contract',
            name='party_b_legal_representative',
            field=models.CharField(
                max_length=200,
                verbose_name='乙方法定代表人及联系方式',
                blank=True,
                help_text='乙方法定代表人姓名及联系方式'
            ),
        ),
        migrations.AddField(
            model_name='contract',
            name='party_b_contact_person',
            field=models.CharField(
                max_length=200,
                verbose_name='乙方联系人及联系方式',
                blank=True,
                help_text='乙方日常联系人及联系方式'
            ),
        ),
        migrations.AddField(
            model_name='contract',
            name='party_b_manager',
            field=models.CharField(
                max_length=200,
                verbose_name='乙方负责人及联系方式',
                blank=True,
                help_text='乙方项目负责人及联系方式'
            ),
        ),
    ]