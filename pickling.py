import pickle

from db.lsj_keys import lsj_keys

with open('db/lsj_keys.pkl', 'wb') as f:
    pickle.dump(lsj_keys, f)

