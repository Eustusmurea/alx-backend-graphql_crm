from django.db import models
from django.core.validators import RegexValidator

class Customer(models.Model):
    name = models.CharField(max_length=255)
    email = models.EmailField(unique=True)
    phone = models.CharField(
        max_length=20,
        blank=True,
        validators=[
            RegexValidator(
                regex=r'^\+?1?\d{9,15}$|^\d{3}-\d{3}-\d{4}$',
                message="Phone must be in format +1234567890 or 123-456-7890"
            )
        ]
    )

    def __str__(self):
        return self.name

class Product(models.Model):
    name = models.CharField(max_length=255)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    stock = models.PositiveIntegerField(default=0)

    def __str__(self):
        return self.name

class Order(models.Model):
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
    products = models.ManyToManyField(Product, related_name='orders')
    order_date = models.DateTimeField(auto_now_add=True)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)

    def __str__(self):
        return f"Order {self.id} for {self.customer.name}"
    