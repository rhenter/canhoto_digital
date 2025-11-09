# Recreate ProofOfDeliveryPhoto with UUID PK and code (data can be dropped)
import functools
from django.db import migrations, models
import django.db.models.deletion
import django_models.fields
import django_models.utils.generators


class Migration(migrations.Migration):

    dependencies = [
        ("delivery", "0006_pod_location_pointfield"),
    ]

    operations = [
        # Drop the existing table to avoid invalid cast from bigint to uuid
        migrations.DeleteModel(
            name="ProofOfDeliveryPhoto",
        ),
        # Recreate the model with UUID primary key and code field
        migrations.CreateModel(
            name="ProofOfDeliveryPhoto",
            fields=[
                ("id", django_models.fields.UUIDPrimaryKeyField(editable=False, primary_key=True, serialize=False, unique=True)),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True, verbose_name="Created at")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="Updated at")),
                ("code", models.CharField(
                    default=functools.partial(
                        django_models.utils.generators.generate_random_code,
                        *(),
                        **{"length": 8}
                    ),
                    max_length=32,
                    unique=True,
                    verbose_name="Model code",
                )),
                ("image", models.ImageField(upload_to="delivery/photos/", verbose_name="Photo")),
                ("meta", models.JSONField(default=dict, blank=True, verbose_name="Meta")),
                ("pod", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="photos", to="delivery.proofofdelivery", verbose_name="POD")),
            ],
            options={
                "verbose_name": "POD Photo",
                "verbose_name_plural": "POD Photos",
                "ordering": ["-created_at"],
            },
        ),
    ]
