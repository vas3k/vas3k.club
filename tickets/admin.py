from django.contrib import admin

from tickets.models import Ticket, TicketSale


class TicketsAdmin(admin.ModelAdmin):
    list_display = (
        "code",
        "name",
        "stripe_product_id",
        "stripe_payment_link_id",
        "achievement",
        "tickets_sold",
        "limit_quantity",
    )
    ordering = ("code",)
    search_fields = ["code", "name"]


admin.site.register(Ticket, TicketsAdmin)


class TicketSalesAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "customer_email",
        "stripe_payment_id",
        "ticket",
        "metadata",
        "created_at",
    )
    ordering = ("-created_at",)
    search_fields = ["user", "customer_email", "stripe_payment_id"]


admin.site.register(TicketSale, TicketSalesAdmin)
