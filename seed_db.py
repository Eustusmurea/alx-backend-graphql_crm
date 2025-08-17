# Example Python code to seed the database using Django ORM

from crm.models import Customer, Product, Order

# Create a single customer
alice = Customer.objects.create(
    name="Alice",
    email="alice@example.com",
    phone="+1234567890"
)

# Bulk create customers
bob = Customer(name="Bob", email="bob@example.com", phone="123-456-7890")
carol = Customer(name="Carol", email="carol@example.com")
Customer.objects.bulk_create([bob, carol])

# Create a product
laptop = Product.objects.create(
    name="Laptop",
    price=999.99,
    stock=10
)

# Create an order with products
order = Order.objects.create(
    customer=alice,
    total_amount=laptop.price,  # Adjust as needed
)
order.products.add(laptop)
order.save()