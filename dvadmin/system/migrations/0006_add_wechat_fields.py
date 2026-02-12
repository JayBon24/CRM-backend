from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("system", "0005_add_organization_fields"),
    ]

    operations = [
        migrations.AddField(
            model_name="users",
            name="wechat_openid",
            field=models.CharField(blank=True, db_index=True, help_text="微信小程序OpenID", max_length=255, null=True, unique=True, verbose_name="微信OpenID"),
        ),
        migrations.AddField(
            model_name="users",
            name="wechat_unionid",
            field=models.CharField(blank=True, db_index=True, help_text="微信UnionID", max_length=255, null=True, verbose_name="微信UnionID"),
        ),
    ]
