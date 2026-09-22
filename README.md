# ⚡ SmartSearch — E-Commerce Product Search & Ranking Engine

> A product search engine powered by a custom **Python DSA engine**, a **Flask REST API**, and **PostgreSQL** persistence. Built for SDE portfolio demonstrations.

![Python](https://img.shields.io/badge/Python-3.12-blue?logo=python)
![DSA](https://img.shields.io/badge/DSA-Python-orange?logo=python)
![Flask](https://img.shields.io/badge/Flask-3.x-green?logo=flask)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-blue?logo=postgresql)
![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-ORM-red)

---

## 📌 Project Overview

SmartSearch solves classic backend engineering challenges using custom data structures implemented in Python:

| Challenge | DSA Solution | Complexity |
|-----------|-------------|------------|
| Real-time autocomplete as user types | **Trie** | O(L) per lookup |
| Return only the Top-10 best products from thousands | **Min-Heap** | O(N log K) |
| Avoid repeating expensive queries | **LRU Cache** (HashMap + Doubly Linked List) | O(1) get/put |
| Filter products by price range efficiently | **Binary Search** on sorted array | O(log N) |

---

## 🏗️ Architecture

```
Browser (HTML + CSS + Vanilla JS)
            │
            ▼
      Flask REST API  (Python)
            │
     ┌──────┴──────────┐
     ▼                 ▼
PostgreSQL          Python DSA Engine
(SQLAlchemy)              │
                 ┌────────┼────────┬──────────┐
                 ▼        ▼        ▼          ▼
               Trie    Min-Heap  LRU Cache  Binary Search
            (autocomplete) (Top-K) (O(1) lookup) (price filter)
```

**Data flow for a search request:**

```
User types "nike shoe" + price ₹2000–₹10000
    │
    ▼
[Flask] receives GET /api/search?q=nike+shoe&min_price=2000&max_price=10000
    │
    ▼
[Python engine] checks LRU Cache (HashMap lookup O(1))
    ├── CACHE HIT  → return cached result instantly
    └── CACHE MISS → Binary Search on price-sorted array O(log N)
                        → substring filter on price-range slice
                        → Min-Heap Top-10 by ranking score O(M log K)
                        → store result in LRU Cache
    │
    ▼
[Flask] fetches full product details from PostgreSQL by IDs
    │
    ▼
[Browser] renders Top-10 cards + DSA Performance Panel
```

---

## 🧠 DSA Components Deep Dive

### 1. 🔍 Trie — Autocomplete
```
root → n → i → k → e → [Nike Air Max, Nike Ultraboost, ...]
             ↘ → k → e → r → s → [Skechers ...]
```
- Each TrieNode stores up to 10 product IDs at every prefix
- O(L) lookup where L = length of the typed prefix
- Used for: real-time autocomplete dropdown

### 2. 🏆 Min-Heap — Top-K Ranking
```
Ranking Score = (Rating × 0.5) + (Popularity × 0.3) + (Relevance × 0.2)
                                                        normalized to /10
```
- Min-Heap of size K=10 keeps only the top-K candidates
- When heap size > K, the lowest-score element is ejected (`heap.pop()`)
- Result: O(N log K) — far faster than sorting all N results

### 3. ⚡ LRU Cache — O(1) Repeated Queries
```
HashMap:  "nike shoe|2000|10000" → DLL node pointer  (O(1) lookup)
DLL:      [most recent] ←→ ... ←→ [least recent]    (O(1) eviction)
```
- Capacity: 100 cached queries
- On every search: check HashMap → O(1) hit or miss
- Cache key includes query + price range (unique per filter combination)
- On HIT: move node to front of DLL (most recently used)
- On MISS: compute result, insert at front, evict tail if at capacity

### 4. 🔢 Binary Search — Price Range Filter
```
Price-sorted array: [₹150, ₹200, ..., ₹85,000, ₹1,20,000]
                          ↑                        ↑
                    lower_bound(min_p)       upper_bound(max_p)
```
- Products pre-sorted by price at engine load time
- Binary search finds the slice in O(log N)
- Min-Heap then ranks only the M products in that slice — O(M log K)
- When price filter is ON: complexity drops from O(N log K) → O(M log K) where M << N

---

## 🗂️ Project Structure

```
Project - Smart E-Commerce Product Search & Ranking Engine/
│
├── app.py                     # Flask REST API (5 endpoints)
├── db.py                      # SQLAlchemy models + seeding (1305 products)
├── test_engine.py             # Standalone engine test script
│
├── dsa_engine/
│   └── engine_wrapper.py      # Pure-Python DSA search engine
│
├── templates/
│   └── index.html             # Single-page frontend
│
└── static/
    ├── style.css              # Full CSS (no framework)
    └── script.js              # Vanilla JS (fetch, dual slider, DSA panel)
```

---

## 🚀 Setup & Run

### Prerequisites
- Python 3.10+
- PostgreSQL 14+ (running on `localhost:5432`)

### 1. Install Python dependencies
```bash
pip install flask sqlalchemy psycopg2-binary
```

### 2. Configure Database
Create a PostgreSQL database:
```sql
CREATE DATABASE ecommerce_searchengine;
```

Update credentials in `db.py` (line 7):
```python
DB_PASSWORD = 'your_password_here'
```

### 3. Run the App
```bash
python app.py
```

On first run, the app automatically:
- Creates the `products` table
- Seeds **1,305 products** across 7 categories
- Loads all products into the Python engine (Trie + Heap + LRU)

Open **http://127.0.0.1:5000** in your browser.

### 4. Build
```bash
bash build.sh
```
The project is pure Python and does not require native compilation.

---

## 🌐 REST API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | Serve the frontend |
| `GET` | `/api/featured?category=X` | Top-ranked products (DB ORDER BY) |
| `GET` | `/api/search?q=X&category=Y&min_price=A&max_price=B` | Python engine search with optional filters |
| `GET` | `/api/autocomplete?q=X` | Trie-powered prefix suggestions |
| `GET` | `/api/price_range` | Global min/max prices for slider |
| `GET` | `/api/cache_stats` | LRU Cache hit/miss statistics |

### Sample Search Response
```json
{
  "products": [
    {
      "id": 711,
      "name": "Puma Running Shoes 8",
      "category": "Footwear",
      "price": 5491.78,
      "rating": 4.7,
      "popularity": 988,
      "relevance": 0.85,
      "score": 9.9
    }
  ],
  "meta": {
    "cache_hit": false,
    "cache_hits_total": 3,
    "cache_misses_total": 1,
    "hit_rate_pct": 75.0,
    "structures_used": ["Trie (query match)", "Binary Search (price range)", "Min-Heap (Top-K)", "LRU Cache"],
    "price_filter": true,
    "count": 10,
    "response_time_ms": 2.55
  }
}
```

---

## 🎯 Product Categories & Dataset

| Category | Brands | Products | Price Range |
|----------|--------|----------|-------------|
| 📱 Electronics | Samsung, Apple, Sony, Dell, HP, OnePlus, boAt | 225 | ₹3,000–₹1,20,000 |
| 👟 Footwear | Nike, Adidas, Puma, Reebok, Under Armour, Bata | 180 | ₹800–₹18,000 |
| 👕 Clothing | Zara, H&M, Levi's, Allen Solly, Raymond | 180 | ₹499–₹8,000 |
| 📚 Books | Penguin, Harper Collins, Westland, Bloomsbury | 180 | ₹199–₹1,500 |
| 🍳 Home & Kitchen | Philips, Prestige, Havells, LG, Bosch | 180 | ₹600–₹35,000 |
| 🏋️ Sports & Fitness | Decathlon, Cosco, Nivia, Yonex | 180 | ₹299–₹12,000 |
| 💄 Beauty | L'Oréal, Mamaearth, Himalaya, Nivea, Plum | 180 | ₹150–₹3,500 |

**Total: 1,305 products**

---

## 📊 Performance Characteristics

| Operation | Data Structure | Time Complexity | Space |
|-----------|---------------|-----------------|-------|
| Autocomplete prefix lookup | Trie | O(L) | O(N×L) |
| Top-K ranking | Min-Heap | O(N log K) | O(K) |
| Cache lookup | HashMap (unordered_map) | O(1) avg | O(capacity) |
| Cache eviction | Doubly Linked List | O(1) | O(1) |
| Price range filter | Binary Search | O(log N) | O(1) |
| Price-filtered ranking | Binary Search + Heap | O(log N + M log K) | O(K) |

---

## 🔧 Python DSA Engine

`dsa_engine/engine_wrapper.py` is a pure-Python module used directly by Flask. On startup it builds an in-memory product map, token index, price-sorted list, and LRU cache from the PostgreSQL rows. No compiler, DLL, or language bridge is required.

---

## 💡 Key Engineering Decisions

| Decision | Rationale |
|----------|-----------|
| Python for DSA and API | One runtime keeps deployment and debugging simple |
| `OrderedDict` LRU cache | Provides O(1) average lookup, promotion, and eviction |
| `bisect` over price values | Provides O(log N) price-range boundaries |
| `debug=False, use_reloader=False` | Keeps one initialized in-memory engine for the Flask process |
| Separate LRU keys for price-filtered queries | `"query\|min\|max"` ensures correct cache isolation per filter combination |

---

## 📸 Features

- 🔍 **Real-time autocomplete** — Trie-powered, debounced 150ms
- 🏆 **Top-K ranking** — Python Min-Heap with weighted score formula
- ⚡ **LRU Cache** — Instant repeat queries with HIT/MISS tracking
- 🔢 **Price Range Slider** — Dual-handle slider activates Binary Search path
- 📊 **DSA Performance Panel** — Live report: structures used, cache status, response time
- 🏷️ **7 Category Filters** — Chip-based filter, colour-coded category badges
- 🌈 **Rank Score /10** — Normalized score with green/yellow/red indicator

---

## 👨‍💻 Author

Built as a portfolio project demonstrating:
- **Algorithm design** — Trie, Heap, LRU Cache, Binary Search
- **Python backend engineering** — Flask REST API, SQLAlchemy ORM, and in-memory indexing
- **Backend engineering** — Flask REST API, SQLAlchemy ORM
- **Algorithm design** — Trie, Heap, LRU Cache, Binary Search

---

*To run: `python app.py` → open http://127.0.0.1:5000*
