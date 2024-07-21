from django.contrib import admin

from payments.models import Payment, Subscription


@admin.register(Payment)
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
    search_fields = ["reference"]


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
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
    search_fields = ["reference", "user__slug"]
