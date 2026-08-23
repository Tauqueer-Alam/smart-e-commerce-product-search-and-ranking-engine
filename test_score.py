products = [
    {'relevance':0.95,'rating':4.8,'popularity':990},
    {'relevance':0.80,'rating':4.5,'popularity':700},
    {'relevance':0.65,'rating':4.1,'popularity':400},
    {'relevance':0.55,'rating':3.5,'popularity':100},
    {'relevance':0.52,'rating':3.1,'popularity': 55},
]
for p in products:
    rel_n = (p['relevance'] - 0.5) / 0.5
    rat_n = (p['rating'] - 3.0) / 2.0
    pop_n = (p['popularity'] - 50) / 950.0
    score = round((0.50 * rel_n + 0.30 * rat_n + 0.20 * pop_n) * 10, 2)
    print(f"rel={p['relevance']} rat={p['rating']} pop={p['popularity']:4d}  =>  Score: {score}")
