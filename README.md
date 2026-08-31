# Inventory / Stock Management System

Flask REST API with DynamoDB Local for product and stock management. It enforces unique product IDs, non-negative prices and quantities, and prevents stock reductions below zero.

## Run with Docker

```sh
docker compose up --build
```

Services:

- API: http://localhost:5000
- DynamoDB Local: http://localhost:8000
- DynamoDB Admin: http://localhost:8001

The API creates the `products` table on startup. Because DynamoDB Local runs in-memory, its data is reset when the containers stop.

## API examples

Create a product:

```sh
curl -X POST http://localhost:5000/products \
  -H 'Content-Type: application/json' \
  -d '{"product_id":"SKU-001","name":"Coffee Beans","category":"Grocery","price":"12.50","quantity":8}'
```

```sh
curl http://localhost:5000/products
curl 'http://localhost:5000/products?query=coffee'
curl http://localhost:5000/products/SKU-001
curl -X PATCH http://localhost:5000/products/SKU-001 -H 'Content-Type: application/json' -d '{"price":"13.00"}'
curl -X POST http://localhost:5000/products/SKU-001/stock/increase -H 'Content-Type: application/json' -d '{"amount":5}'
curl -X POST http://localhost:5000/products/SKU-001/stock/decrease -H 'Content-Type: application/json' -d '{"amount":2}'
curl http://localhost:5000/inventory/value
curl 'http://localhost:5000/products/low-stock?threshold=5'
curl -X DELETE http://localhost:5000/products/SKU-001
```

## Local development

```sh
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
pytest
```# python-training