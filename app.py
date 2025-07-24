from flask import Flask, request, jsonify, render_template, redirect, url_for
import os, sqlite3, pandas as pd, numpy as np
from datetime import datetime, timedelta

UPLOAD_FOLDER = 'data/uploads'
DB_PATH = os.path.join(UPLOAD_FOLDER, 'uploads.db')
app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def compute_forecast(upload_id, days=30):
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query(
        "SELECT date, solde FROM transactions WHERE upload_id=? ORDER BY date",
        conn, params=(upload_id,)
    )
    conn.close()
    if df.empty:
        return []
    df['date'] = pd.to_datetime(df['date'])
    df.set_index('date', inplace=True)
    series = df['solde']
    n = len(series)
    x = np.arange(n)               # jours indexés 0…n-1
    y = series.values
    slope, intercept = np.polyfit(x, y, 1)
    last_date = series.index[-1]
    result = []
    for i in range(1, days+1):
        d = last_date + timedelta(days=i)
        v = float(intercept + slope * (n - 1 + i))
        result.append({'date': d.strftime('%Y-%m-%d'), 'value': v})
    return result

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload():
    f = request.files.get('file')
    if not f or not f.filename.lower().endswith('.csv'):
        return redirect(url_for('index'))
    conn = sqlite3.connect(DB_PATH); cur = conn.cursor()
    cur.execute('INSERT INTO uploads(filename) VALUES(?)', (f.filename,))
    uid = cur.lastrowid; conn.commit(); conn.close()
    filename = f"{uid}_{f.filename}"
    path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    f.save(path)
    from parser import parse_and_store
    parse_and_store(uid, path)
    return redirect(url_for('dashboard', upload_id=uid))

@app.route('/dashboard/<int:upload_id>')
def dashboard(upload_id):
    fc = compute_forecast(upload_id)
    j7 = fc[6]['value'] if len(fc) > 6 else None
    j30 = fc[-1]['value'] if fc else None
    return render_template('dashboard.html', upload_id=upload_id, j7=j7, j30=j30)

@app.route('/api/forecast/<int:upload_id>')
def api_forecast(upload_id):
    return jsonify(compute_forecast(upload_id))

@app.route('/api/alerts/<int:upload_id>', methods=['GET','POST'])
def api_alerts(upload_id):
    conn = sqlite3.connect(DB_PATH); cur = conn.cursor()
    if request.method == 'POST':
        data = request.get_json()
        abs_th = data.get('abs_threshold')
        rel_th = data.get('rel_threshold')
        email_en = 1 if data.get('email_enabled') else 0
        cur.execute(
            'REPLACE INTO alerts(upload_id,abs_threshold,rel_threshold,email_enabled) VALUES(?,?,?,?)',
            (upload_id, abs_th, rel_th, email_en)
        )
        conn.commit()
    cur.execute(
        'SELECT abs_threshold, rel_threshold, email_enabled FROM alerts WHERE upload_id=?',
        (upload_id,)
    )
    row = cur.fetchone(); conn.close()
    if row:
        return jsonify({
            'abs_threshold': row[0],
            'rel_threshold': row[1],
            'email_enabled': bool(row[2])
        })
    return jsonify({}), 404

if __name__=='__main__':
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS uploads(upload_id INTEGER PRIMARY KEY,filename TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS transactions(id INTEGER PRIMARY KEY,upload_id INTEGER,date DATE,libelle TEXT,montant REAL,solde REAL)')
    c.execute('CREATE TABLE IF NOT EXISTS alerts(upload_id INTEGER PRIMARY KEY,abs_threshold REAL,rel_threshold REAL,email_enabled INTEGER)')
    conn.commit(); conn.close()
    app.run(host='0.0.0.0', port=5001, debug=True)
