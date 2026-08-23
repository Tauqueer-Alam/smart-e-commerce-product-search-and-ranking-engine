import db
import dsa_engine.engine_wrapper as engine

products = db.get_all_products()
loaded = engine.load_products(products)
print(f"Products loaded into C++ engine: {loaded}")

# Test search
ids = engine.search_products("shoe")
print(f"\nTop results for 'shoe' (ids): {ids}")
for p in db.get_products_by_ids(ids):
    print(f"  [{p['id']}] {p['name']}  rating={p['rating']}  pop={p['popularity']}")

# Test autocomplete
ids2 = engine.autocomplete("nik")
print(f"\nAutocomplete for 'nik' (ids): {ids2}")
for p in db.get_products_by_ids(ids2):
    print(f"  {p['name']}")
