from dataclasses import asdict, dataclass
from decimal import Decimal, InvalidOperation


class ProductNotFoundError(Exception):
    pass


class DuplicateProductError(Exception):
    pass


class InsufficientStockError(Exception):
    pass


class ValidationError(Exception):
    pass


def decimal_from(value: object, field_name: str) -> Decimal:
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError) as error:
        raise ValidationError(f"{field_name} must be a number") from error
    if not result.is_finite():
        raise ValidationError(f"{field_name} must be finite")
    return result


def quantity_from(value: object) -> int:
    if isinstance(value, bool):
        raise ValidationError("quantity must be a whole number")
    try:
        quantity = int(value)
    except (TypeError, ValueError) as error:
        raise ValidationError("quantity must be a whole number") from error
    if str(value) != str(quantity) and not isinstance(value, int):
        raise ValidationError("quantity must be a whole number")
    return quantity


@dataclass
class Product:
    product_id: str
    name: str
    category: str
    price: Decimal
    quantity: int

    @classmethod
    def create(cls, data: dict) -> "Product":
        required_fields = ("product_id", "name", "category", "price", "quantity")
        missing_fields = [field for field in required_fields if field not in data]
        if missing_fields:
            raise ValidationError(f"missing fields: {', '.join(missing_fields)}")

        product = cls(
            product_id=str(data["product_id"]).strip(),
            name=str(data["name"]).strip(),
            category=str(data["category"]).strip(),
            price=decimal_from(data["price"], "price"),
            quantity=quantity_from(data["quantity"]),
        )
        product.validate()
        return product

    def validate(self) -> None:
        if not self.product_id or not self.name or not self.category:
            raise ValidationError("product_id, name, and category cannot be empty")
        if self.price < 0:
            raise ValidationError("price cannot be negative")
        if self.quantity < 0:
            raise ValidationError("quantity cannot be negative")

    def increase_stock(self, amount: int) -> None:
        if amount <= 0:
            raise ValidationError("stock amount must be greater than zero")
        self.quantity += amount

    def decrease_stock(self, amount: int) -> None:
        if amount <= 0:
            raise ValidationError("stock amount must be greater than zero")
        if amount > self.quantity:
            raise InsufficientStockError("cannot decrease stock below zero")
        self.quantity -= amount

    @property
    def inventory_value(self) -> Decimal:
        return self.price * self.quantity

    def to_dict(self) -> dict:
        data = asdict(self)
        data["price"] = str(self.price)
        data["inventory_value"] = str(self.inventory_value)
        return data