import re
from decimal import Decimal
from datetime import datetime
from django.db import transaction
from django.core.exceptions import ValidationError
import graphene
from graphene import relay
from graphene_django import DjangoObjectType
from graphql import GraphQLError
from graphene_django.filter import DjangoFilterConnectionField
from crm.models import Customer, Order
from crm.models import Product
from .filters import CustomerFilter, ProductFilter, OrderFilter

# ------------------ GraphQL Types ------------------

class CustomerType(DjangoObjectType):
    class Meta:
        model = Customer
        fields = ("id", "name", "email", "phone")
        interfaces = (relay.Node,)
        filterset_class = CustomerFilter

class ProductType(DjangoObjectType):
    class Meta:
        model = Product
        fields = ("id", "name", "price", "stock")
        interfaces = (relay.Node,)
        filterset_class = ProductFilter

class OrderType(DjangoObjectType):
    totalAmount = graphene.Decimal(source="total_amount")

    class Meta:
        model = Order
        fields = ("id", "customer", "products", "order_date", "total_amount")
        interfaces = (relay.Node,)
        filterset_class = OrderFilter

class CustomerErrorType(graphene.ObjectType):
    email = graphene.String()
    errors = graphene.List(graphene.String)

# ------------------ Input Types ------------------

class CustomerInput(graphene.InputObjectType):
    name = graphene.String(required=True)
    email = graphene.String(required=True)
    phone = graphene.String(required=False)

class ProductInput(graphene.InputObjectType):
    name = graphene.String(required=True)
    price = graphene.Decimal(required=True)
    stock = graphene.Int(required=False, default_value=0)

class OrderInput(graphene.InputObjectType):
    customerId = graphene.ID(required=True)
    productIds = graphene.List(graphene.ID, required=True)
    orderDate = graphene.DateTime(required=False)

# ------------------ Validation Helpers ------------------

def validate_email_unique(email):
    if Customer.objects.filter(email=email).exists():  # Fixed: CreateCustomer to Customer
        raise ValidationError("Email already exists.")

def validate_phone_format(phone):
    if phone and not re.match(r'^(\+\d{10,15}|\d{3}-\d{3}-\d{4})$', phone):
        raise ValidationError("Invalid phone number format.")

def validate_price_and_stock(price, stock):
    if Decimal(price) <= 0:
        raise ValidationError("Price must be positive.")
    if stock is not None and stock < 0:
        raise ValidationError("Stock cannot be negative.")

# ------------------ Mutations ------------------

class CreateCustomer(graphene.Mutation):
    class Arguments:
        input = CustomerInput(required=True)

    customer = graphene.Field(CustomerType)
    message = graphene.String()

    @staticmethod
    def mutate(root, info, input):
        try:
            validate_email_unique(input.email)
            validate_phone_format(input.phone)
            customer = Customer.objects.create(  # Fixed: CreateCustomer to Customer
                name=input.name,
                email=input.email,
                phone=input.phone
            )
            return CreateCustomer(customer=customer, message="Customer created successfully.")
        except ValidationError as e:
            raise GraphQLError(str(e))

class BulkCreateCustomers(graphene.Mutation):
    class Arguments:
        input = graphene.List(CustomerInput, required=True)

    customers = graphene.List(CustomerType)
    errors = graphene.List(CustomerErrorType)

    @staticmethod
    @transaction.atomic
    def mutate(root, info, input):
        customers = []
        errors = []
        for cust in input:
            try:
                validate_email_unique(cust.email)
                validate_phone_format(cust.phone)
                customer = Customer.objects.create(  # Fixed: CreateCustomer to Customer
                    name=cust.name,
                    email=cust.email,
                    phone=cust.phone
                )
                customers.append(customer)
            except ValidationError as e:
                errors.append(CustomerErrorType(email=cust.email, errors=[str(e)]))
        return BulkCreateCustomers(customers=customers, errors=errors)

class CreateProduct(graphene.Mutation):
    class Arguments:
        input = ProductInput(required=True)

    product = graphene.Field(ProductType)
    message = graphene.String()

    @staticmethod
    def mutate(root, info, input):
        try:
            validate_price_and_stock(input.price, input.stock)
            product = Product.objects.create(
                name=input.name,
                price=input.price,
                stock=input.stock
            )
            return CreateProduct(product=product, message="Product created successfully.")
        except ValidationError as e:
            raise GraphQLError(str(e))

class CreateOrder(graphene.Mutation):
    class Arguments:
        input = OrderInput(required=True)

    order = graphene.Field(OrderType)
    message = graphene.String()

    @staticmethod
    @transaction.atomic
    def mutate(root, info, input):
        try:
            if not input.productIds:
                raise ValidationError("At least one product must be selected.")

            try:
                customer = Customer.objects.get(id=input.customerId)  # Fixed: CreateCustomer to Customer
            except Customer.DoesNotExist:
                raise ValidationError("Invalid customer ID.")

            products = list(Product.objects.filter(id__in=input.productIds))
            if len(products) != len(input.productIds):
                missing_ids = set(input.productIds) - {str(p.id) for p in products}
                raise ValidationError(f"Invalid product IDs: {', '.join(missing_ids)}")

            total_amount = sum([p.price for p in products])

            order = Order.objects.create(
                customer=customer,
                order_date=input.orderDate or datetime.now(),
                total_amount=total_amount
            )
            order.products.set(products)

            return CreateOrder(order=order, message="Order created successfully.")
        except ValidationError as e:
            raise GraphQLError(str(e))

class UpdateLowStockProducts(graphene.Mutation):
    class Arguments:
        pass  # no arguments needed

    success = graphene.Boolean()
    message = graphene.String()
    updated_products = graphene.List(ProductType)

    def mutate(self, info):
        low_stock_products = Product.objects.filter(stock__lt=10)
        updated = []

        for product in low_stock_products:
            product.stock += 10
            product.save()
            updated.append(product)

        return UpdateLowStockProducts(
            success=True,
            message=f"{len(updated)} products updated.",
            updated_products=updated
        )

# ------------------ Root Query & Mutation ------------------

class Query(graphene.ObjectType):
    allCustomers = DjangoFilterConnectionField(
        CustomerType,
        filterset_class=CustomerFilter,
        customer_name=graphene.String(description="Filter by customer name (case-insensitive)."),
        order_by=graphene.List(graphene.String, description="Order by fields (e.g., ['name', '-email']).")
    )
    allProducts = DjangoFilterConnectionField(
        ProductType,
        filterset_class=ProductFilter,
        product_name=graphene.String(description="Filter by product name (case-insensitive)."),
        order_by=graphene.List(graphene.String, description="Order by fields (e.g., ['name', '-price']).")
    )
    allOrders = DjangoFilterConnectionField(
        OrderType,
        filterset_class=OrderFilter,
        order_by=graphene.List(graphene.String, description="Order by fields (e.g., ['order_date', '-total_amount']).")
    )

    def resolve_allCustomers(self, info, **kwargs):
        qs = Customer.objects.all()  # Fixed: CreateCustomer to Customer
        customer_name = kwargs.get("customer_name")
        if customer_name:
            qs = qs.filter(name__icontains=customer_name)  # Custom filtering
        order_by = kwargs.get("order_by")
        if order_by:
            qs = qs.order_by(*order_by)
        return qs

    def resolve_allProducts(self, info, **kwargs):
        qs = Product.objects.all()
        product_name = kwargs.get("product_name")
        if product_name:
            qs = qs.filter(name__icontains=product_name)  # Custom filtering
        order_by = kwargs.get("order_by")
        if order_by:
            qs = qs.order_by(*order_by)
        return qs

    def resolve_allOrders(self, info, **kwargs):
        qs = Order.objects.all()
        order_by = kwargs.get("order_by")
        if order_by:
            qs = qs.order_by(*order_by)
        return qs

class Mutation(graphene.ObjectType):
    create_customer = CreateCustomer.Field()
    bulk_create_customers = BulkCreateCustomers.Field()
    create_product = CreateProduct.Field()
    create_order = CreateOrder.Field()
    update_low_stock = UpdateLowStockProducts.Field()