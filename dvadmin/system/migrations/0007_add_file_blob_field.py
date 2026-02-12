from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("system", "0006_add_wechat_fields"),
    ]

    operations = [
        migrations.AddField(
            model_name="filelist",
            name="file_blob",
            field=models.BinaryField(blank=True, help_text="文件二进制内容（db模式）", null=True, verbose_name="文件二进制"),
        ),
    ]
