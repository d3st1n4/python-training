from __future__ import annotations

import os
from decimal import Decimal

import boto3
from flask import Flask, jsonify, request

from .domain import (
    DuplicateProductError,
    InsufficientStockError,
    Product,
    ProductNotFoundError,
    ValidationError,
    decimal_from,
    quantity_from,
)
from .repository import DynamoDbProductRepository, ProductRepository


def create_dynamodb_repository() -> DynamoDbProductRepository:
    endpoint_url = os.getenv("DYNAMODB_ENDPOINT", "http://localhost:8000")
    table_name = os.getenv("DYNAMODB_TABLE", "products")
    resource = boto3.resource(
        "dynamodb",
        endpoint_url=endpoint_url,
        region_name=os.getenv("AWS_REGION", "us-east-1"),
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID", "dummy"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY", "dummy"),
    )
    table = resource.Table(table_name)
    try:
        table.load()
    except resource.meta.client.exceptions.ResourceNotFoundException:
        table = resource.create_table(
            TableName=table_name,
            KeySchema=[{"AttributeName": "product_id", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "product_id", "AttributeType": "S"}],
            BillingMode="PAY_PER_REQUEST",
        )
        table.wait_until_exists()
    return DynamoDbProductRepository(table)


def create_app(repository: ProductRepository | None = None) -> Flask:
    app = Flask(__name__)
    repo = repository or create_dynamodb_repository()

    @app.errorhandler(ValidationError)
    def handle_validation(error):
        return jsonify(error=str(error)), 400

    @app.errorhandler(ProductNotFoundError)
    def handle_not_found(error):
        return jsonify(error=str(error)), 404

    @app.errorhandler(DuplicateProductError)
    def handle_duplicate(error):
        return jsonify(error=str(error)), 409

    @app.errorhandler(InsufficientStockError)
    def handle_insufficient_stock(error):
        return jsonify(error=str(error)), 409

    @app.get("/health")
    def health():
        return jsonify(status="ok")

    @app.post("/products")
    def add_product():
        product = Product.create(request.get_json(silent=True) or {})
        return jsonify(repo.create(product).to_dict()), 201

    @app.get("/products")
    def view_products():
        query = request.args.get("query", "").lower()
        category = request.args.get("category", "").lower()
        products = repo.list()
        if query:
            products = [p for p in products if query in p.name.lower() or query in p.product_id.lower()]
        if category:
            products = [p for p in products if p.category.lower() == category]
        return jsonify([product.to_dict() for product in products])

    @app.get("/products/<product_id>")
    def get_product(product_id: str):
        return jsonify(repo.get(product_id).to_dict())

    @app.patch("/products/<product_id>")
    def update_product(product_id: str):
        product = repo.get(product_id)
        data = request.get_json(silent=True) or {}
        if "name" in data:
            product.name = str(data["name"]).strip()
        if "category" in data:
            product.category = str(data["category"]).strip()
        if "price" in data:
            product.price = decimal_from(data["price"], "price")
        product.validate()
        return jsonify(repo.save(product).to_dict())

    @app.post("/products/<product_id>/stock/increase")
    def increase_stock(product_id: str):
        product = repo.get(product_id)
        product.increase_stock(quantity_from((request.get_json(silent=True) or {}).get("amount")))
        return jsonify(repo.save(product).to_dict())

    @app.post("/products/<product_id>/stock/decrease")
    def decrease_stock(product_id: str):
        product = repo.get(product_id)
        product.decrease_stock(quantity_from((request.get_json(silent=True) or {}).get("amount")))
        return jsonify(repo.save(product).to_dict())

    @app.delete("/products/<product_id>")
    def delete_product(product_id: str):
        repo.delete(product_id)
        return "", 204

    @app.get("/inventory/value")
    def inventory_value():
        value = sum((product.inventory_value for product in repo.list()), start=Decimal("0"))
        return jsonify(inventory_value=str(value))

    @app.get("/products/low-stock")
    def low_stock_products():
        threshold = quantity_from(request.args.get("threshold", 5))
        if threshold < 0:
            raise ValidationError("threshold cannot be negative")
        products = [product.to_dict() for product in repo.list() if product.quantity <= threshold]
        return jsonify(products)

    return app