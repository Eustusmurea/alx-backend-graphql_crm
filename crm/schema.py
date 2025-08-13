import re
from decimal import Decimal
from datetime import datetime
from django.db import transaction
from django.core.exceptions import ValidationError
import graphene
from graphene_django import DjangoObjectType
from graphql import GraphQLError
from .models import Customer, Product, Order
from .filters import CustomerFilter, ProductFilter, OrderFilter
from graphene_django.filter import DjangoFilterConnectionField

# ------------------ GraphQL Types ------------------

class CustomerType(DjangoObjectType):
    class Meta:
        model = Customer
        fields = ("id", "name", "email", "phone")


class ProductType(DjangoObjectType):
    class Meta:
        model = Product
        fields = ("id", "name", "price", "stock")


class OrderType(DjangoObjectType):
    totalAmount = graphene.Decimal(source="total_amount")

    class Meta:
        model = Order
        fields = ("id", "customer", "products", "order_date", "total_amount")


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
    if Customer.objects.filter(email=email).exists():
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
            customer = Customer.objects.create(
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
                customer = Customer.objects.create(
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
                customer = Customer.objects.get(id=input.customerId)
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

# ------------------ Root Query & Mutation ------------------

class Query(graphene.ObjectType):
    all_customers = graphene.List(CustomerType)

    def resolve_all_customers(self, info):
        return Customer.objects.all()


class Mutation(graphene.ObjectType):
    create_customer = CreateCustomer.Field()
    bulk_create_customers = BulkCreateCustomers.Field()
    create_product = CreateProduct.Field()
    create_order = CreateOrder.Field()

class Query(graphene.ObjectType):
    all_customers = DjangoFilterConnectionField(CustomerType, filterset_class=CustomerFilter, order_by=graphene.List(of_type=graphene.String))
    all_products = DjangoFilterConnectionField(ProductType, filterset_class=ProductFilter, order_by=graphene.List(of_type=graphene.String))
    all_orders = DjangoFilterConnectionField(OrderType, filterset_class=OrderFilter, order_by=graphene.List(of_type=graphene.String))

    def resolve_all_customers(self, info, **kwargs):
        qs = Customer.objects.all()
        order_by = kwargs.pop("order_by", None)
        if order_by:
            qs = qs.order_by(*order_by)
        return qs

    def resolve_all_products(self, info, **kwargs):
        qs = Product.objects.all()
        order_by = kwargs.pop("order_by", None)
        if order_by:
            qs = qs.order_by(*order_by)
        return qs

    def resolve_all_orders(self, info, **kwargs):
        qs = Order.objects.all()
        order_by = kwargs.pop("order_by", None)
        if order_by:
            qs = qs.order_by(*order_by)
        return qs