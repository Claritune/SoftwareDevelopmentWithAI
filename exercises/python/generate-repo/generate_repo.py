#!/usr/bin/env python3
"""
Generate the 'shopapi' Express project for the Cursor Hooks token budget exercise.

Run:  python generate_repo.py
Output: ./shopapi/  (a complete project directory)

The project contains a real pagination bug in src/routes/products.js, surrounded by
legitimately-structured but unnecessarily large files that an agent will be tempted
to read: fixture JSONs, an OpenAPI spec, and a config YAML.
"""

import json
import os
import random
import string
import textwrap
from pathlib import Path

REPO = Path("shopapi")
random.seed(42)  # reproducible output


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def write(path: str, content: str):
    """Write content to a file relative to REPO, creating dirs as needed."""
    full = REPO / path
    full.parent.mkdir(parents=True, exist_ok=True)
    full.write_text(textwrap.dedent(content).lstrip())


def write_raw(path: str, content: str):
    """Write raw content (no dedent) to a file."""
    full = REPO / path
    full.parent.mkdir(parents=True, exist_ok=True)
    full.write_text(content)


# ---------------------------------------------------------------------------
# 1. Package / project config
# ---------------------------------------------------------------------------

def gen_package_json():
    pkg = {
        "name": "shopapi",
        "version": "1.0.0",
        "description": "Product catalog API",
        "main": "src/index.js",
        "scripts": {
            "start": "node src/index.js",
            "dev": "nodemon src/index.js",
            "seed": "node scripts/seed.js",
            "test": "jest --coverage"
        },
        "dependencies": {
            "express": "^4.18.2",
            "cors": "^2.8.5",
            "helmet": "^7.1.0",
            "morgan": "^1.10.0",
            "lodash": "^4.17.21"
        },
        "devDependencies": {
            "jest": "^29.7.0",
            "nodemon": "^3.0.2",
            "supertest": "^6.3.3"
        }
    }
    write_raw("package.json", json.dumps(pkg, indent=2) + "\n")


def gen_env_example():
    write(".env.example", """\
        PORT=3000
        NODE_ENV=development
        DB_HOST=localhost
        DB_PORT=5432
        DB_NAME=shopapi
        DB_USER=shop
        DB_PASS=changeme
        # Pagination defaults are in config/defaults.yaml
        CONFIG_PATH=./config/defaults.yaml
        LOG_LEVEL=info
    """)


# ---------------------------------------------------------------------------
# 2. Source files (small, realistic — with the bug)
# ---------------------------------------------------------------------------

def gen_source_files():
    # --- index.js ---
    write("src/index.js", """\
        const express = require('express');
        const cors = require('cors');
        const helmet = require('helmet');
        const morgan = require('morgan');
        const productRoutes = require('./routes/products');
        const categoryRoutes = require('./routes/categories');
        const healthRoutes = require('./routes/health');
        const { errorHandler } = require('./middleware/errors');
        const config = require('./config');

        const app = express();

        app.use(helmet());
        app.use(cors());
        app.use(morgan('combined'));
        app.use(express.json());

        app.use('/api/products', productRoutes);
        app.use('/api/categories', categoryRoutes);
        app.use('/health', healthRoutes);

        app.use(errorHandler);

        const PORT = config.port || 3000;
        app.listen(PORT, () => {
          console.log(`ShopAPI listening on port ${PORT}`);
        });

        module.exports = app;
    """)

    # --- config/index.js ---
    write("src/config/index.js", """\
        const path = require('path');

        module.exports = {
          port: process.env.PORT || 3000,
          env: process.env.NODE_ENV || 'development',
          pagination: {
            defaultPage: 1,
            defaultLimit: 20,
            maxLimit: 100,
          },
          db: {
            host: process.env.DB_HOST || 'localhost',
            port: process.env.DB_PORT || 5432,
            name: process.env.DB_NAME || 'shopapi',
          },
        };
    """)

    # --- middleware/errors.js ---
    write("src/middleware/errors.js", """\
        function errorHandler(err, req, res, next) {
          console.error(err.stack);
          const status = err.statusCode || 500;
          res.status(status).json({
            error: {
              message: err.message || 'Internal Server Error',
              ...(process.env.NODE_ENV === 'development' && { stack: err.stack }),
            },
          });
        }

        module.exports = { errorHandler };
    """)

    # --- middleware/validate.js ---
    write("src/middleware/validate.js", """\
        function validatePagination(req, res, next) {
          const page = parseInt(req.query.page, 10);
          const limit = parseInt(req.query.limit, 10);

          if (req.query.page && (isNaN(page) || page < 1)) {
            return res.status(400).json({ error: { message: 'page must be a positive integer' } });
          }
          if (req.query.limit && (isNaN(limit) || limit < 1 || limit > 100)) {
            return res.status(400).json({ error: { message: 'limit must be between 1 and 100' } });
          }

          req.pagination = {
            page: page || 1,
            limit: limit || 20,
          };
          next();
        }

        module.exports = { validatePagination };
    """)

    # --- models/product.js ---
    write("src/models/product.js", """\
        const _ = require('lodash');

        // In-memory store (replaced by DB in production)
        let products = [];

        function loadProducts(data) {
          products = data;
        }

        function findAll() {
          return products;
        }

        /**
         * Search products with optional filters.
         *
         * BUG: When category is provided, the filtered set is built correctly,
         * but pagination slices from the ORIGINAL unfiltered array and then
         * filters — causing duplicates when items shift across page boundaries.
         */
        function search({ category, minPrice, maxPrice, page, limit }) {
          let results = [...products];

          if (minPrice !== undefined) {
            results = results.filter(p => p.price >= minPrice);
          }
          if (maxPrice !== undefined) {
            results = results.filter(p => p.price <= maxPrice);
          }

          // ---- THE BUG ----
          // Pagination is applied BEFORE the category filter.
          // When category narrows the set, the offset is wrong and items repeat.
          const offset = (page - 1) * limit;
          const paginated = results.slice(offset, offset + limit);

          if (category) {
            return paginated.filter(p =>
              p.category.toLowerCase() === category.toLowerCase()
            );
          }

          return paginated;
        }

        function findById(id) {
          return products.find(p => p.id === id) || null;
        }

        module.exports = { loadProducts, findAll, search, findById };
    """)

    # --- routes/products.js (contains the buggy search endpoint) ---
    write("src/routes/products.js", """\
        const express = require('express');
        const router = express.Router();
        const Product = require('../models/product');
        const { validatePagination } = require('../middleware/validate');

        // GET /api/products — list with optional filters
        router.get('/', validatePagination, (req, res) => {
          const { page, limit } = req.pagination;
          const { category, min_price, max_price, q } = req.query;

          const results = Product.search({
            category,
            minPrice: min_price ? parseFloat(min_price) : undefined,
            maxPrice: max_price ? parseFloat(max_price) : undefined,
            page,
            limit,
          });

          // BUG VISIBLE HERE: total count doesn't account for the filter correctly
          const all = Product.findAll();
          const total = category
            ? all.filter(p => p.category.toLowerCase() === category.toLowerCase()).length
            : all.length;

          res.json({
            data: results,
            meta: {
              page,
              limit,
              total,
              pages: Math.ceil(total / limit),
            },
          });
        });

        // GET /api/products/:id
        router.get('/:id', (req, res) => {
          const product = Product.findById(req.params.id);
          if (!product) {
            return res.status(404).json({ error: { message: 'Product not found' } });
          }
          res.json({ data: product });
        });

        module.exports = router;
    """)

    # --- routes/categories.js ---
    write("src/routes/categories.js", """\
        const express = require('express');
        const router = express.Router();
        const Product = require('../models/product');
        const _ = require('lodash');

        // GET /api/categories — list distinct categories with counts
        router.get('/', (req, res) => {
          const all = Product.findAll();
          const grouped = _.countBy(all, 'category');
          const categories = Object.entries(grouped).map(([name, count]) => ({
            name,
            count,
          }));
          res.json({ data: _.sortBy(categories, 'name') });
        });

        module.exports = router;
    """)

    # --- routes/health.js ---
    write("src/routes/health.js", """\
        const express = require('express');
        const router = express.Router();

        router.get('/', (req, res) => {
          res.json({ status: 'ok', uptime: process.uptime() });
        });

        module.exports = router;
    """)

    # --- scripts/seed.js ---
    write("scripts/seed.js", """\
        const fs = require('fs');
        const path = require('path');
        const { loadProducts } = require('../src/models/product');

        const data = JSON.parse(
          fs.readFileSync(path.join(__dirname, '..', 'fixtures', 'products.json'), 'utf8')
        );
        loadProducts(data);
        console.log(`Loaded ${data.length} products`);
    """)


# ---------------------------------------------------------------------------
# 3. Fixture files (large — the "trap")
# ---------------------------------------------------------------------------

CATEGORIES = [
    "Electronics", "Clothing", "Home & Garden", "Sports", "Books",
    "Toys", "Automotive", "Health", "Food & Beverage", "Office Supplies"
]

ADJECTIVES = [
    "Premium", "Ultra", "Pro", "Classic", "Essential", "Advanced",
    "Compact", "Deluxe", "Smart", "Eco-Friendly", "Artisan", "Vintage",
    "Wireless", "Organic", "Heavy-Duty", "Portable", "Ergonomic",
]

NOUNS = {
    "Electronics": ["Speaker", "Charger", "Monitor", "Keyboard", "Mouse", "Headphones", "Camera", "Router", "Hub", "Cable"],
    "Clothing": ["Jacket", "Shirt", "Pants", "Hoodie", "Socks", "Hat", "Scarf", "Gloves", "Belt", "Vest"],
    "Home & Garden": ["Planter", "Lamp", "Rug", "Vase", "Shelf", "Cushion", "Clock", "Frame", "Candle", "Mirror"],
    "Sports": ["Ball", "Racket", "Mat", "Weights", "Bottle", "Band", "Gloves", "Shoes", "Helmet", "Bag"],
    "Books": ["Novel", "Guide", "Manual", "Handbook", "Atlas", "Journal", "Almanac", "Compendium", "Anthology", "Encyclopedia"],
    "Toys": ["Puzzle", "Robot", "Car", "Blocks", "Doll", "Game", "Kite", "Train", "Bear", "Drone"],
    "Automotive": ["Filter", "Jack", "Pump", "Cover", "Cleaner", "Wax", "Light", "Mount", "Charger", "Mat"],
    "Health": ["Supplement", "Cream", "Bandage", "Thermometer", "Scale", "Massager", "Diffuser", "Pillow", "Tracker", "Brush"],
    "Food & Beverage": ["Sauce", "Tea", "Spice", "Oil", "Snack", "Mix", "Syrup", "Vinegar", "Powder", "Extract"],
    "Office Supplies": ["Pen", "Notebook", "Stapler", "Folder", "Tape", "Clips", "Label", "Marker", "Sharpener", "Binder"],
}


def gen_product(pid: int) -> dict:
    cat = random.choice(CATEGORIES)
    adj = random.choice(ADJECTIVES)
    noun = random.choice(NOUNS[cat])
    name = f"{adj} {noun} {pid}"
    return {
        "id": f"prod_{pid:05d}",
        "name": name,
        "category": cat,
        "price": round(random.uniform(4.99, 499.99), 2),
        "currency": "USD",
        "sku": ''.join(random.choices(string.ascii_uppercase + string.digits, k=10)),
        "stock": random.randint(0, 500),
        "rating": round(random.uniform(1.0, 5.0), 1),
        "reviews_count": random.randint(0, 2000),
        "description": f"High-quality {adj.lower()} {noun.lower()} for {cat.lower()} enthusiasts. "
                        f"Built with premium materials and designed for everyday use. "
                        f"SKU reference for warehouse: WH-{pid:05d}-{cat[:3].upper()}.",
        "tags": random.sample(["bestseller", "new", "sale", "limited", "exclusive",
                                "trending", "eco", "gift-idea", "bundle", "clearance"], k=random.randint(1, 4)),
        "dimensions": {
            "width_cm": round(random.uniform(2, 80), 1),
            "height_cm": round(random.uniform(2, 120), 1),
            "depth_cm": round(random.uniform(1, 60), 1),
            "weight_kg": round(random.uniform(0.05, 25.0), 2),
        },
        "supplier": {
            "name": f"Supplier-{random.randint(1, 50)}",
            "lead_time_days": random.randint(1, 30),
            "country": random.choice(["US", "CN", "DE", "JP", "KR", "IN", "MX", "VN"]),
        },
        "created_at": f"2024-{random.randint(1,12):02d}-{random.randint(1,28):02d}T{random.randint(0,23):02d}:{random.randint(0,59):02d}:00Z",
    }


def gen_user(uid: int) -> dict:
    first_names = ["Alice", "Bob", "Carol", "Dave", "Eve", "Frank", "Grace", "Hank", "Ivy", "Jack",
                   "Karen", "Leo", "Mia", "Noah", "Olive", "Pat", "Quinn", "Ray", "Sara", "Tom"]
    last_names = ["Smith", "Johnson", "Lee", "Brown", "Garcia", "Kim", "Wilson", "Chen", "Davis", "Lopez"]
    fname = random.choice(first_names)
    lname = random.choice(last_names)
    return {
        "id": f"user_{uid:05d}",
        "email": f"{fname.lower()}.{lname.lower()}{uid}@example.com",
        "name": f"{fname} {lname}",
        "role": random.choice(["customer", "customer", "customer", "admin", "support"]),
        "tier": random.choice(["free", "free", "basic", "basic", "premium", "enterprise"]),
        "address": {
            "street": f"{random.randint(1, 9999)} {random.choice(['Main', 'Oak', 'Pine', 'Elm', 'Cedar', 'Maple'])} St",
            "city": random.choice(["Springfield", "Portland", "Austin", "Denver", "Seattle", "Boston"]),
            "state": random.choice(["CA", "OR", "TX", "CO", "WA", "MA", "NY", "IL"]),
            "zip": f"{random.randint(10000, 99999)}",
            "country": "US"
        },
        "preferences": {
            "newsletter": random.choice([True, False]),
            "categories": random.sample(CATEGORIES, k=random.randint(1, 4)),
            "currency": "USD",
            "language": random.choice(["en", "en", "es", "fr", "de"]),
        },
        "order_history_summary": {
            "total_orders": random.randint(0, 150),
            "total_spent": round(random.uniform(0, 15000), 2),
            "last_order_date": f"2025-{random.randint(1,6):02d}-{random.randint(1,28):02d}",
            "favorite_category": random.choice(CATEGORIES),
        },
        "created_at": f"2023-{random.randint(1,12):02d}-{random.randint(1,28):02d}T00:00:00Z",
    }


def gen_order(oid: int) -> dict:
    n_items = random.randint(1, 6)
    items = []
    for i in range(n_items):
        pid = random.randint(1, 800)
        qty = random.randint(1, 5)
        price = round(random.uniform(4.99, 499.99), 2)
        items.append({
            "product_id": f"prod_{pid:05d}",
            "quantity": qty,
            "unit_price": price,
            "line_total": round(price * qty, 2),
        })
    subtotal = round(sum(i["line_total"] for i in items), 2)
    tax = round(subtotal * 0.08, 2)
    return {
        "id": f"order_{oid:06d}",
        "user_id": f"user_{random.randint(1, 400):05d}",
        "status": random.choice(["pending", "confirmed", "shipped", "delivered", "cancelled"]),
        "items": items,
        "subtotal": subtotal,
        "tax": tax,
        "total": round(subtotal + tax, 2),
        "shipping": {
            "method": random.choice(["standard", "express", "overnight"]),
            "tracking": ''.join(random.choices(string.ascii_uppercase + string.digits, k=16)),
            "estimated_delivery": f"2025-{random.randint(1,12):02d}-{random.randint(1,28):02d}",
        },
        "created_at": f"2025-{random.randint(1,6):02d}-{random.randint(1,28):02d}T{random.randint(0,23):02d}:{random.randint(0,59):02d}:00Z",
    }


def gen_fixtures():
    """Generate three large-ish fixture JSON files (~80KB each)."""

    products = [gen_product(i) for i in range(1, 801)]
    write_raw("fixtures/products.json", json.dumps(products, indent=2) + "\n")

    users = [gen_user(i) for i in range(1, 401)]
    write_raw("fixtures/users.json", json.dumps(users, indent=2) + "\n")

    orders = [gen_order(i) for i in range(1, 601)]
    write_raw("fixtures/orders.json", json.dumps(orders, indent=2) + "\n")


# ---------------------------------------------------------------------------
# 4. OpenAPI spec (large, auto-generated feel)
# ---------------------------------------------------------------------------

def gen_openapi_spec():
    """Generate a verbose OpenAPI 3.0 YAML spec (~40KB)."""
    lines = [
        "openapi: '3.0.3'",
        "info:",
        "  title: ShopAPI",
        "  version: 1.0.0",
        "  description: |",
        "    ShopAPI provides a RESTful interface for browsing, searching, and managing",
        "    a product catalog. It supports pagination, category filtering, price range",
        "    queries, and full-text search across product names and descriptions.",
        "    ",
        "    ## Authentication",
        "    All endpoints except /health require a Bearer token. Tokens are issued via",
        "    the /auth/token endpoint (not covered in this spec — see internal docs).",
        "    ",
        "    ## Rate Limiting",
        "    Requests are limited to 100/min per API key. Exceeding this returns 429.",
        "    ",
        "    ## Pagination",
        "    List endpoints accept `page` and `limit` query parameters. Response includes",
        "    a `meta` object with total count and page info.",
        "  contact:",
        "    name: API Support",
        "    email: api@shopapi.example.com",
        "  license:",
        "    name: MIT",
        "servers:",
        "  - url: http://localhost:3000",
        "    description: Development",
        "  - url: https://api.shopapi.example.com",
        "    description: Production",
        "paths:",
    ]

    # Products endpoints
    lines += _openapi_products_path()
    lines += _openapi_product_by_id_path()
    lines += _openapi_categories_path()
    lines += _openapi_health_path()

    # Components
    lines += _openapi_components()

    write_raw("docs/openapi.yaml", "\n".join(lines) + "\n")


def _openapi_products_path():
    return [
        "  /api/products:",
        "    get:",
        "      operationId: listProducts",
        "      summary: List products with optional filters",
        "      description: |",
        "        Returns a paginated list of products. Supports filtering by category,",
        "        price range, and text search. Results are sorted by creation date (newest first).",
        "        ",
        "        When combining category filter with pagination, the server first filters",
        "        by category, then applies pagination to the filtered set.",
        "        ",
        "        Note: If both min_price and max_price are provided, min_price must be",
        "        less than or equal to max_price, or a 400 error is returned.",
        "      tags: [Products]",
        "      parameters:",
        "        - name: page",
        "          in: query",
        "          required: false",
        "          schema:",
        "            type: integer",
        "            minimum: 1",
        "            default: 1",
        "          description: Page number for pagination (1-indexed)",
        "          example: 1",
        "        - name: limit",
        "          in: query",
        "          required: false",
        "          schema:",
        "            type: integer",
        "            minimum: 1",
        "            maximum: 100",
        "            default: 20",
        "          description: |",
        "            Number of results per page. Maximum 100. If not provided, defaults to",
        "            the value in config/defaults.yaml (currently 20).",
        "          example: 20",
        "        - name: category",
        "          in: query",
        "          required: false",
        "          schema:",
        "            type: string",
        "          description: |",
        "            Filter by exact category name (case-insensitive). Must match one of",
        "            the categories returned by GET /api/categories.",
        "          example: Electronics",
        "        - name: min_price",
        "          in: query",
        "          required: false",
        "          schema:",
        "            type: number",
        "            format: float",
        "          description: Minimum price filter (inclusive)",
        "          example: 9.99",
        "        - name: max_price",
        "          in: query",
        "          required: false",
        "          schema:",
        "            type: number",
        "            format: float",
        "          description: Maximum price filter (inclusive)",
        "          example: 99.99",
        "        - name: q",
        "          in: query",
        "          required: false",
        "          schema:",
        "            type: string",
        "          description: Full-text search across product name and description",
        "      responses:",
        "        '200':",
        "          description: Paginated product list",
        "          content:",
        "            application/json:",
        "              schema:",
        "                $ref: '#/components/schemas/ProductListResponse'",
        "        '400':",
        "          description: Invalid query parameters",
        "          content:",
        "            application/json:",
        "              schema:",
        "                $ref: '#/components/schemas/Error'",
        "        '401':",
        "          description: Missing or invalid authentication",
        "        '429':",
        "          description: Rate limit exceeded",
        "        '500':",
        "          description: Internal server error",
    ]


def _openapi_product_by_id_path():
    return [
        "  /api/products/{id}:",
        "    get:",
        "      operationId: getProductById",
        "      summary: Get a single product by ID",
        "      description: |",
        "        Returns the full product object including dimensions, supplier info,",
        "        and stock availability. Returns 404 if the product does not exist.",
        "      tags: [Products]",
        "      parameters:",
        "        - name: id",
        "          in: path",
        "          required: true",
        "          schema:",
        "            type: string",
        "          description: Product ID (format prod_XXXXX)",
        "          example: prod_00001",
        "      responses:",
        "        '200':",
        "          description: Product details",
        "          content:",
        "            application/json:",
        "              schema:",
        "                type: object",
        "                properties:",
        "                  data:",
        "                    $ref: '#/components/schemas/Product'",
        "        '404':",
        "          description: Product not found",
        "          content:",
        "            application/json:",
        "              schema:",
        "                $ref: '#/components/schemas/Error'",
    ]


def _openapi_categories_path():
    return [
        "  /api/categories:",
        "    get:",
        "      operationId: listCategories",
        "      summary: List all categories with product counts",
        "      description: |",
        "        Returns an alphabetically sorted list of all product categories,",
        "        each with the number of products in that category.",
        "      tags: [Categories]",
        "      responses:",
        "        '200':",
        "          description: Category list",
        "          content:",
        "            application/json:",
        "              schema:",
        "                $ref: '#/components/schemas/CategoryListResponse'",
    ]


def _openapi_health_path():
    return [
        "  /health:",
        "    get:",
        "      operationId: healthCheck",
        "      summary: Health check",
        "      description: Returns server health status and uptime.",
        "      tags: [System]",
        "      responses:",
        "        '200':",
        "          description: Healthy",
        "          content:",
        "            application/json:",
        "              schema:",
        "                type: object",
        "                properties:",
        "                  status:",
        "                    type: string",
        "                    example: ok",
        "                  uptime:",
        "                    type: number",
        "                    description: Server uptime in seconds",
    ]


def _openapi_components():
    """Generate verbose schema components."""
    return [
        "components:",
        "  schemas:",
        "    Product:",
        "      type: object",
        "      required: [id, name, category, price]",
        "      properties:",
        "        id:",
        "          type: string",
        "          description: Unique product identifier",
        "          example: prod_00001",
        "        name:",
        "          type: string",
        "          description: Display name of the product",
        "          example: Premium Wireless Speaker 42",
        "        category:",
        "          type: string",
        "          description: Product category",
        "          example: Electronics",
        "        price:",
        "          type: number",
        "          format: float",
        "          description: Current selling price in the product's currency",
        "          example: 79.99",
        "        currency:",
        "          type: string",
        "          description: ISO 4217 currency code",
        "          example: USD",
        "        sku:",
        "          type: string",
        "          description: Stock keeping unit for warehouse systems",
        "          example: AB12CD34EF",
        "        stock:",
        "          type: integer",
        "          description: Current inventory count",
        "          example: 150",
        "        rating:",
        "          type: number",
        "          format: float",
        "          minimum: 1.0",
        "          maximum: 5.0",
        "          description: Average customer rating",
        "          example: 4.2",
        "        reviews_count:",
        "          type: integer",
        "          description: Total number of customer reviews",
        "          example: 342",
        "        description:",
        "          type: string",
        "          description: Full product description",
        "        tags:",
        "          type: array",
        "          items:",
        "            type: string",
        "          description: Marketing tags applied to the product",
        "          example: [bestseller, new]",
        "        dimensions:",
        "          $ref: '#/components/schemas/Dimensions'",
        "        supplier:",
        "          $ref: '#/components/schemas/Supplier'",
        "        created_at:",
        "          type: string",
        "          format: date-time",
        "          description: ISO 8601 creation timestamp",
        "    Dimensions:",
        "      type: object",
        "      properties:",
        "        width_cm:",
        "          type: number",
        "          description: Width in centimeters",
        "        height_cm:",
        "          type: number",
        "          description: Height in centimeters",
        "        depth_cm:",
        "          type: number",
        "          description: Depth in centimeters",
        "        weight_kg:",
        "          type: number",
        "          description: Weight in kilograms",
        "    Supplier:",
        "      type: object",
        "      properties:",
        "        name:",
        "          type: string",
        "          description: Supplier company name",
        "        lead_time_days:",
        "          type: integer",
        "          description: Typical lead time for restocking",
        "        country:",
        "          type: string",
        "          description: ISO 3166-1 alpha-2 country code of supplier",
        "    PaginationMeta:",
        "      type: object",
        "      properties:",
        "        page:",
        "          type: integer",
        "          description: Current page number",
        "        limit:",
        "          type: integer",
        "          description: Results per page",
        "        total:",
        "          type: integer",
        "          description: Total matching results across all pages",
        "        pages:",
        "          type: integer",
        "          description: Total number of pages",
        "    ProductListResponse:",
        "      type: object",
        "      properties:",
        "        data:",
        "          type: array",
        "          items:",
        "            $ref: '#/components/schemas/Product'",
        "        meta:",
        "          $ref: '#/components/schemas/PaginationMeta'",
        "    CategoryListResponse:",
        "      type: object",
        "      properties:",
        "        data:",
        "          type: array",
        "          items:",
        "            type: object",
        "            properties:",
        "              name:",
        "                type: string",
        "              count:",
        "                type: integer",
        "    Error:",
        "      type: object",
        "      properties:",
        "        error:",
        "          type: object",
        "          properties:",
        "            message:",
        "              type: string",
        "              description: Human-readable error message",
        "            stack:",
        "              type: string",
        "              description: Stack trace (development only)",
    ]


# ---------------------------------------------------------------------------
# 5. Config YAML (deeply nested, verbose)
# ---------------------------------------------------------------------------

def gen_config_yaml():
    """Generate a large config/defaults.yaml with deeply nested settings."""
    sections = []

    sections.append("""\
# ==========================================================================
# ShopAPI Configuration — defaults.yaml
# ==========================================================================
# This file contains all default configuration values for the ShopAPI server.
# Values can be overridden by environment variables (see .env.example).
#
# WARNING: Do not commit production secrets to this file.
# ==========================================================================

server:
  host: 0.0.0.0
  port: 3000
  graceful_shutdown_timeout_ms: 10000
  keep_alive_timeout_ms: 65000
  headers_timeout_ms: 66000
  max_request_size: 10mb
  trust_proxy: false
  cors:
    enabled: true
    origins:
      - http://localhost:3000
      - http://localhost:8080
      - https://shop.example.com
    methods: [GET, POST, PUT, PATCH, DELETE, OPTIONS]
    allowed_headers: [Content-Type, Authorization, X-Request-ID]
    exposed_headers: [X-Request-ID, X-RateLimit-Remaining]
    max_age: 86400
    credentials: true""")

    sections.append("""\
database:
  primary:
    host: localhost
    port: 5432
    name: shopapi
    user: shop
    password: changeme
    pool:
      min: 2
      max: 20
      idle_timeout_ms: 30000
      connection_timeout_ms: 5000
      reap_interval_ms: 1000
    ssl:
      enabled: false
      reject_unauthorized: true
      ca_path: null
    statement_timeout_ms: 30000
    query_logging:
      enabled: true
      slow_threshold_ms: 500
      log_params: false
  read_replicas:
    - host: replica-1.db.internal
      port: 5432
      weight: 50
    - host: replica-2.db.internal
      port: 5432
      weight: 50
  migrations:
    directory: ./migrations
    table_name: schema_migrations
    run_on_startup: false""")

    sections.append("""\
pagination:
  default_page: 1
  default_limit: 20
  max_limit: 100
  cursor_based:
    enabled: false
    default_sort_field: created_at
    default_sort_order: desc""")

    sections.append("""\
search:
  engine: simple    # simple | elasticsearch | typesense
  simple:
    case_sensitive: false
    fields: [name, description, tags]
    max_results: 1000
  elasticsearch:
    host: http://localhost:9200
    index_prefix: shopapi
    request_timeout_ms: 5000
    bulk_batch_size: 500
    refresh_interval: 1s
    replicas: 1
    shards: 3
    analyzers:
      default:
        tokenizer: standard
        filter: [lowercase, asciifolding, edge_ngram_filter]
    mappings:
      products:
        dynamic: strict
        properties:
          name:
            type: text
            boost: 2.0
          description:
            type: text
            boost: 1.0
          category:
            type: keyword
          tags:
            type: keyword
          price:
            type: float
          created_at:
            type: date""")

    sections.append("""\
caching:
  enabled: true
  driver: memory   # memory | redis
  ttl_seconds: 300
  max_entries: 10000
  redis:
    host: localhost
    port: 6379
    db: 0
    password: null
    key_prefix: shopapi:cache:
    cluster:
      enabled: false
      nodes: []
  strategies:
    product_list:
      ttl_seconds: 60
      invalidate_on: [product.created, product.updated, product.deleted]
    product_detail:
      ttl_seconds: 300
      invalidate_on: [product.updated, product.deleted]
    categories:
      ttl_seconds: 600
      invalidate_on: [product.created, product.deleted, category.updated]""")

    sections.append("""\
logging:
  level: info       # trace | debug | info | warn | error | fatal
  format: json      # json | pretty
  timestamp: true
  caller: false
  request_logging:
    enabled: true
    include_headers: false
    include_query: true
    include_body: false
    exclude_paths:
      - /health
      - /metrics
      - /favicon.ico
    slow_request_threshold_ms: 3000
  rotation:
    enabled: true
    max_size_mb: 100
    max_files: 10
    compress: true
    directory: ./logs""")

    sections.append("""\
rate_limiting:
  enabled: true
  driver: memory    # memory | redis
  window_ms: 60000
  max_requests: 100
  key_generator: ip  # ip | api_key | user_id
  skip_paths:
    - /health
  headers:
    remaining: X-RateLimit-Remaining
    reset: X-RateLimit-Reset
    limit: X-RateLimit-Limit
  tiers:
    free:
      window_ms: 60000
      max_requests: 30
    basic:
      window_ms: 60000
      max_requests: 100
    premium:
      window_ms: 60000
      max_requests: 500
    enterprise:
      window_ms: 60000
      max_requests: 5000""")

    sections.append("""\
authentication:
  enabled: false     # Disabled for development
  strategy: bearer   # bearer | api_key | basic
  bearer:
    issuer: https://auth.shopapi.example.com
    audience: shopapi
    algorithms: [RS256]
    jwks_uri: https://auth.shopapi.example.com/.well-known/jwks.json
    cache_ttl_seconds: 3600
  api_key:
    header: X-API-Key
    query_param: api_key
    hash_algorithm: sha256
  rbac:
    enabled: true
    default_role: viewer
    roles:
      viewer:
        permissions: [products.read, categories.read]
      editor:
        permissions: [products.read, products.write, categories.read, categories.write]
      admin:
        permissions: ['*']""")

    sections.append("""\
monitoring:
  metrics:
    enabled: true
    endpoint: /metrics
    format: prometheus
    default_labels:
      service: shopapi
      environment: development
    histograms:
      http_request_duration:
        buckets: [0.01, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10]
  health_check:
    endpoint: /health
    interval_ms: 30000
    checks:
      database:
        enabled: true
        timeout_ms: 5000
      cache:
        enabled: true
        timeout_ms: 2000
  tracing:
    enabled: false
    exporter: otlp
    endpoint: http://localhost:4318
    sample_rate: 0.1
    propagation: [tracecontext, baggage]""")

    sections.append("""\
feature_flags:
  new_search_algorithm: false
  v2_pagination: false
  image_thumbnails: false
  webhook_notifications: false
  bulk_import: false
  dynamic_pricing: false
  recommendation_engine: false
  ab_testing:
    enabled: false
    experiments:
      search_relevance_v2:
        variants: [control, treatment_a, treatment_b]
        weights: [0.34, 0.33, 0.33]
        sticky: true
      checkout_flow:
        variants: [current, streamlined]
        weights: [0.5, 0.5]
        sticky: true""")

    write_raw("config/defaults.yaml", "\n\n".join(sections) + "\n")


# ---------------------------------------------------------------------------
# 6. Miscellaneous files
# ---------------------------------------------------------------------------

def gen_misc():
    write(".gitignore", """\
        node_modules/
        .env
        logs/
        coverage/
        dist/
        *.log
    """)

    write("README.md", """\
        # ShopAPI

        A simple product catalog API built with Express.

        ## Quick Start

        ```bash
        npm install
        npm run dev
        ```

        ## API Endpoints

        - `GET /api/products` — List products (supports `?category=`, `?page=`, `?limit=`)
        - `GET /api/products/:id` — Get product by ID
        - `GET /api/categories` — List categories
        - `GET /health` — Health check

        ## Configuration

        See `.env.example` and `config/defaults.yaml`.
    """)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    if REPO.exists():
        import shutil
        shutil.rmtree(REPO)

    print("Generating shopapi project...")

    gen_package_json()
    gen_env_example()
    gen_source_files()
    gen_fixtures()
    gen_openapi_spec()
    gen_config_yaml()
    gen_misc()

    # Print size report
    total = 0
    print("\nFile sizes:")
    for p in sorted(REPO.rglob("*")):
        if p.is_file():
            size = p.stat().st_size
            total += size
            rel = str(p.relative_to(REPO))
            marker = ""
            if size > 20_000:
                marker = "  ← LARGE (agent bait)"
            print(f"  {rel:<45s} {size:>8,d} bytes{marker}")
    print(f"\n  {'TOTAL':<45s} {total:>8,d} bytes")
    print("\nDone. Open with:  cd shopapi && cursor .")


if __name__ == "__main__":
    main()
