from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("palm_sample", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="SchemaItem",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=80)),
                ("quantity", models.IntegerField(default=0)),
            ],
        ),
    ]