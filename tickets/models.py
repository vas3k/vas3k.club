from uuid import uuid4

from django.db import models


class Ticket(models.Model):
    code = models.CharField(primary_key=True, max_length=32, null=False, unique=True)
    name = models.CharField(max_length=255)

    stripe_product_id = models.CharField(max_length=255, unique=True)
    stripe_payment_link_id = models.CharField(max_length=255, null=True, blank=True)

    achievement = models.ForeignKey("users.Achievement", on_delete=models.SET_NULL, null=True, blank=True)

    send_email_title = models.CharField(max_length=255, null=True, blank=True)
    send_email_markdown = models.TextField(null=True, blank=True)

    tickets_sold = models.IntegerField(default=0)
    limit_quantity = models.IntegerField(default=-1)

    class Meta:
        db_table = "tickets"
        ordering = ["code"]

    def __str__(self):
        return self.code


class TicketSale(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)

    user = models.ForeignKey("users.User", on_delete=models.SET_NULL, null=True, blank=True)
    customer_email = models.EmailField(null=True, blank=True)
    stripe_payment_id = models.CharField(max_length=255)

    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name="sales")
    metadata = models.JSONField(default=dict)
    session = models.JSONField(default=dict)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "ticket_sales"
        ordering = ["-created_at"]
