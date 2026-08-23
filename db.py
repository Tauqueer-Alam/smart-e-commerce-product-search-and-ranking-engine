import os
import random
import urllib.parse
from sqlalchemy import create_engine, text

# Use environment variable or default fallback for password
DB_PASSWORD = os.environ.get('PGPASSWORD', 'tauqueer@786')
ENCODED_PASSWORD = urllib.parse.quote_plus(DB_PASSWORD)
LOCAL_DB_URI = f"postgresql://postgres:{ENCODED_PASSWORD}@localhost:5432/ecommerce_searchengine"

# Render provides DATABASE_URL natively
DB_URI = os.environ.get('DATABASE_URL', LOCAL_DB_URI)
if DB_URI.startswith("postgres://"):
    DB_URI = DB_URI.replace("postgres://", "postgresql://", 1)

engine = None

def get_db_engine():
    global engine
    if engine is None:
        try:
            engine = create_engine(DB_URI)
        except Exception as e:
            print(f"Error creating database engine: {e}")
            return None
    return engine

# ---------------------------------------------------------------------------
# Seed data — 7 diverse categories
# ---------------------------------------------------------------------------
SEED_CATALOG = {
    "Electronics": {
        "brands": ["Samsung", "Apple", "Sony", "OnePlus", "boAt", "Realme", "Dell", "HP"],
        "products": [
            "Smartphone Pro", "Wireless Earbuds", "Laptop Ultra", "Smart Watch",
            "Bluetooth Speaker", "Gaming Headset", "4K Smart TV", "Noise Cancelling Earphones",
            "Tablet", "Mechanical Keyboard", "Webcam HD", "Power Bank 20000mAh",
            "USB-C Hub", "Portable SSD", "Action Camera"
        ],
        "price_range": (3000, 120000)
    },
    "Footwear": {
        "brands": ["Nike", "Adidas", "Puma", "Reebok", "Under Armour", "Bata", "Woodland", "Skechers"],
        "products": [
            "Running Shoes", "Sneakers", "Basketball Shoes", "Football Cleats",
            "Training Shoes", "Air Max", "Ultraboost", "Casual Loafers",
            "Hiking Boots", "Slip-On", "Sandals", "Court Shoes"
        ],
        "price_range": (800, 18000)
    },
    "Clothing": {
        "brands": ["Zara", "H&M", "Levis", "Allen Solly", "Peter England", "UCB", "Raymond", "Wrangler"],
        "products": [
            "Regular Fit T-Shirt", "Slim Fit Jeans", "Casual Jacket", "Formal Shirt",
            "Hooded Sweatshirt", "Polo T-Shirt", "Chino Trousers", "Denim Jacket",
            "Printed Round Neck Tee", "Cargo Shorts", "Track Pants", "Blazer"
        ],
        "price_range": (499, 8000)
    },
    "Books": {
        "brands": ["Penguin", "Harper Collins", "Westland", "Bloomsbury", "Oxford Press", "Scholastic"],
        "products": [
            "Python Programming Guide", "Data Structures & Algorithms", "Atomic Habits",
            "The Alchemist", "Rich Dad Poor Dad", "Deep Work", "Clean Code",
            "System Design Interview", "The Power of Habit", "Zero to One",
            "Thinking Fast and Slow", "Ikigai"
        ],
        "price_range": (199, 1500)
    },
    "Home & Kitchen": {
        "brands": ["Philips", "Prestige", "Havells", "Bajaj", "Pigeon", "Bosch", "LG", "Whirlpool"],
        "products": [
            "Air Fryer", "Electric Kettle", "Coffee Maker", "Non-Stick Pan Set",
            "Vacuum Cleaner", "Room Heater", "Ceiling Fan", "LED Desk Lamp",
            "Mixer Grinder", "Induction Cooktop", "Water Purifier", "Microwave Oven"
        ],
        "price_range": (600, 35000)
    },
    "Sports & Fitness": {
        "brands": ["Decathlon", "Cosco", "Nivia", "Yonex", "Vector X", "Reebok", "Nike"],
        "products": [
            "Yoga Mat", "Resistance Bands Set", "Dumbbell Set", "Skipping Rope",
            "Badminton Racket", "Cricket Bat", "Football", "Cycling Helmet",
            "Protein Shaker", "Pull-Up Bar", "Foam Roller", "Ab Roller Wheel"
        ],
        "price_range": (299, 12000)
    },
    "Beauty & Personal Care": {
        "brands": ["Loreal", "Mamaearth", "Himalaya", "Nivea", "Biotique", "Lakme", "Plum", "WOW"],
        "products": [
            "Face Wash", "Moisturizing Cream", "Sunscreen SPF 50", "Hair Serum",
            "Shampoo & Conditioner", "Vitamin C Serum", "Under Eye Cream", "Lip Balm",
            "Aloe Vera Gel", "Anti-Dandruff Shampoo", "Body Lotion", "Face Mask"
        ],
        "price_range": (150, 3500)
    }
}


def setup_database():
    eng = get_db_engine()
    if not eng:
        return

    with eng.connect() as conn:
        # Create table only if it doesn't exist (preserves existing data)
        conn.execute(text('''
            CREATE TABLE IF NOT EXISTS products (
                id SERIAL PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                category VARCHAR(100) NOT NULL,
                price DECIMAL(10, 2) NOT NULL,
                rating DECIMAL(3, 2) NOT NULL,
                popularity INTEGER NOT NULL,
                relevance DECIMAL(3, 2) NOT NULL
            )
        '''))
        conn.commit()

        # Only seed if table is empty
        count = conn.execute(text('SELECT COUNT(*) FROM products')).scalar()
        if count > 0:
            print(f"Database already has {count} products — skipping seed.")
            return

        print("Seeding database with diverse products across 7 categories...")
        products_to_insert = []

        products_to_insert = []

        for category, meta in SEED_CATALOG.items():
            brands = meta["brands"]
            products = meta["products"]
            lo, hi = meta["price_range"]

            for product in products:
                for _ in range(15):  # ~15 variants per product-type = ~1600 total
                    brand = random.choice(brands)
                    variant = random.randint(1, 9)
                    name = f"{brand} {product} {variant}"
                    price = round(random.uniform(lo, hi), 2)
                    rating = round(random.uniform(3.0, 5.0), 1)
                    popularity = random.randint(50, 1000)
                    relevance = round(random.uniform(0.5, 1.0), 2)

                    products_to_insert.append({
                        "name": name,
                        "category": category,
                        "price": price,
                        "rating": rating,
                        "popularity": popularity,
                        "relevance": relevance
                    })

        conn.execute(
            text('INSERT INTO products (name, category, price, rating, popularity, relevance) '
                 'VALUES (:name, :category, :price, :rating, :popularity, :relevance)'),
            products_to_insert
        )
        conn.commit()
        print(f"Database seeded with {len(products_to_insert)} products across 7 categories.")


def get_all_products():
    eng = get_db_engine()
    if not eng:
        return []

    with eng.connect() as conn:
        result = conn.execute(text(
            'SELECT id, name, category, price, rating, popularity, relevance FROM products'
        ))
        rows = result.fetchall()

    products = []
    for row in rows:
        products.append({
            'id': row[0],
            'name': row[1],
            'category': row[2],
            'price': float(row[3]),
            'rating': float(row[4]),
            'popularity': row[5],
            'relevance': float(row[6])
        })
    return products


def get_products_by_ids(product_ids):
    if not product_ids:
        return []
    eng = get_db_engine()
    if not eng:
        return []

    with eng.connect() as conn:
        placeholders = ', '.join([f":id_{i}" for i in range(len(product_ids))])
        params = {f"id_{i}": pid for i, pid in enumerate(product_ids)}
        query = text(
            f'SELECT id, name, category, price, rating, popularity, relevance '
            f'FROM products WHERE id IN ({placeholders})'
        )
        result = conn.execute(query, params)
        rows = result.fetchall()

    product_map = {}
    for row in rows:
        product_map[row[0]] = {
            'id': row[0],
            'name': row[1],
            'category': row[2],
            'price': float(row[3]),
            'rating': float(row[4]),
            'popularity': row[5],
            'relevance': float(row[6])
        }

    return [product_map[pid] for pid in product_ids if pid in product_map]


def get_price_range():
    """Returns (min_price, max_price) across all products."""
    eng = get_db_engine()
    if not eng:
        return 0, 150000
    with eng.connect() as conn:
        result = conn.execute(text('SELECT MIN(price), MAX(price) FROM products'))
        row = result.fetchone()
    return int(row[0]), int(row[1]) + 1


def get_featured_products(category=None, limit=20):
    """Fetch top products sorted by (rating * 0.5 + popularity * 0.3 + relevance * 0.2) DESC."""
    eng = get_db_engine()
    if not eng:
        return []

    with eng.connect() as conn:
        if category:
            query = text(
                'SELECT id, name, category, price, rating, popularity, relevance '
                'FROM products WHERE category = :cat '
                'ORDER BY (rating * 0.5 + popularity * 0.3 + relevance * 0.2) DESC '
                'LIMIT :lim'
            )
            result = conn.execute(query, {"cat": category, "lim": limit})
        else:
            query = text(
                'SELECT id, name, category, price, rating, popularity, relevance '
                'FROM products '
                'ORDER BY (rating * 0.5 + popularity * 0.3 + relevance * 0.2) DESC '
                'LIMIT :lim'
            )
            result = conn.execute(query, {"lim": limit})
        rows = result.fetchall()

    products = []
    for row in rows:
        products.append({
            'id': row[0], 'name': row[1], 'category': row[2],
            'price': float(row[3]), 'rating': float(row[4]),
            'popularity': row[5], 'relevance': float(row[6])
        })
    return products


if __name__ == '__main__':
    setup_database()
