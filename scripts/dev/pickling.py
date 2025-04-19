import pickle

from db.hypotactic import hypotactic

with open('db/hypotactic.pkl', 'wb') as f:
    pickle.dump(hypotactic, f)

