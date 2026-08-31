from abc import ABC, abstractmethod
from decimal import Decimal

from botocore.exceptions import ClientError

from .domain import DuplicateProductError, Product, ProductNotFoundError


class ProductRepository(ABC):
    @abstractmethod
    def create(self, product: Product) -> Product: ...

    @abstractmethod
    def get(self, product_id: str) -> Product: ...

    @abstractmethod
    def list(self) -> list[Product]: ...

    @abstractmethod
    def save(self, product: Product) -> Product: ...

    @abstractmethod
    def delete(self, product_id: str) -> None: ...


class InMemoryProductRepository(ProductRepository):
    def __init__(self) -> None:
        self.products: dict[str, Product] = {}

    def create(self, product: Product) -> Product:
        if product.product_id in self.products:
            raise DuplicateProductError(f"product '{product.product_id}' already exists")
        self.products[product.product_id] = product
        return product

    def get(self, product_id: str) -> Product:
        try:
            return self.products[product_id]
        except KeyError as error:
            raise ProductNotFoundError(f"product '{product_id}' was not found") from error

    def list(self) -> list[Product]:
        return list(self.products.values())

    def save(self, product: Product) -> Product:
        self.get(product.product_id)
        self.products[product.product_id] = product
        return product

    def delete(self, product_id: str) -> None:
        self.get(product_id)
        del self.products[product_id]


class DynamoDbProductRepository(ProductRepository):
    def __init__(self, table) -> None:
        self.table = table

    @staticmethod
    def _item(product: Product) -> dict:
        return {
            "product_id": product.product_id,
            "name": product.name,
            "category": product.category,
            "price": product.price,
            "quantity": product.quantity,
        }

    @staticmethod
    def _product(item: dict) -> Product:
        return Product(
            product_id=item["product_id"],
            name=item["name"],
            category=item["category"],
            price=Decimal(str(item["price"])),
            quantity=int(item["quantity"]),
        )

    def create(self, product: Product) -> Product:
        try:
            self.table.put_item(
                Item=self._item(product),
                ConditionExpression="attribute_not_exists(product_id)",
            )
        except ClientError as error:
            if error.response["Error"]["Code"] == "ConditionalCheckFailedException":
                raise DuplicateProductError(f"product '{product.product_id}' already exists") from error
            raise
        return product

    def get(self, product_id: str) -> Product:
        item = self.table.get_item(Key={"product_id": product_id}).get("Item")
        if item is None:
            raise ProductNotFoundError(f"product '{product_id}' was not found")
        return self._product(item)

    def list(self) -> list[Product]:
        response = self.table.scan()
        products = [self._product(item) for item in response.get("Items", [])]
        while "LastEvaluatedKey" in response:
            response = self.table.scan(ExclusiveStartKey=response["LastEvaluatedKey"])
            products.extend(self._product(item) for item in response.get("Items", []))
        return products

    def save(self, product: Product) -> Product:
        self.get(product.product_id)
        self.table.put_item(Item=self._item(product))
        return product

    def delete(self, product_id: str) -> None:
        self.get(product_id)
        self.table.delete_item(Key={"product_id": product_id})