from django.contrib import admin

from payments.models import Payment


class PaymentsAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "reference",
        "user",
        "product_code",
        "created_at",
        "amount",
        "status",
    )
    ordering = ("-created_at",)


admin.site.register(Payment, PaymentsAdmin)
