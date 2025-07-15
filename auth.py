import sqlite3
from functools import wraps
from flask import request, abort
DB_PATH='data/uploads/uploads.db'

def require_api_key(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.headers.get('Authorization', '')
        if not auth.startswith('Bearer '):
            abort(401, 'Missing API key')
        key = auth.split(' ',1)[1]
        conn = sqlite3.connect(DB_PATH); cur = conn.cursor()
        cur.execute("SELECT upload_id FROM clients WHERE api_key=?", (key,))
        if not cur.fetchone():
            conn.close()
            abort(403, 'Invalid API key')
        conn.close()
        return f(*args, **kwargs)
    return decorated
