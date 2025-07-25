import os, sqlite3
from datetime import datetime, timedelta
from flask import Flask, request, jsonify, render_template, redirect, url_for
import pandas as pd, numpy as np

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
    if df.empty: return []
    df['date'] = pd.to_datetime(df['date'])
    df.set_index('date', inplace=True)
    series = df['solde']
    n = len(series)
    x = np.arange(n)
    y = series.values
    slope, intercept = np.polyfit(x, y, 1)
    last_date = series.index[-1]
    result = []
    for i in range(1, days+1):
        d = last_date + timedelta(days=i)
        v = float(intercept + slope*(n - 1 + i))
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
    j7 = fc[6]['value'] if len(fc)>6 else None
    j30 = fc[-1]['value'] if fc else None
    return render_template('dashboard.html', upload_id=upload_id, j7=j7, j30=j30)

@app.route('/api/forecast/<int:upload_id>')
def api_forecast(upload_id):
    return jsonify(compute_forecast(upload_id))

@app.route('/api/alerts/<int:upload_id>', methods=['GET','POST'])
def api_alerts(upload_id):
    conn = sqlite3.connect(DB_PATH); cur = conn.cursor()
    if request.method=='POST':
        d = request.get_json()
        cur.execute(
            'REPLACE INTO alerts(upload_id,abs_threshold,rel_threshold,email_enabled) VALUES(?,?,?,?,?)',
            (upload_id, d.get('abs_threshold'), d.get('rel_threshold'), int(bool(d.get('email_enabled'))))
        )
        conn.commit()
    cur.execute('SELECT abs_threshold, rel_threshold, email_enabled FROM alerts WHERE upload_id=?', (upload_id,))
    row = cur.fetchone(); conn.close()
    if row:
        return jsonify({'abs_threshold':row[0],'rel_threshold':row[1],'email_enabled':bool(row[2])})
    return jsonify({}),404

@app.route('/alerts/view/<int:upload_id>')
def alerts_view(upload_id):
    conn = sqlite3.connect(DB_PATH); cur = conn.cursor()
    cur.execute('SELECT abs_threshold, rel_threshold FROM alerts WHERE upload_id=?', (upload_id,))
    row = cur.fetchone(); conn.close()
    if not row:
        return render_template('alerts_view.html', upload_id=upload_id, alerts=[], message='Aucun seuil configuré.')
    abs_th, rel_th = row
    fc = compute_forecast(upload_id, days=30)
    triggered = []
    for i, pt in enumerate(fc, start=1):
        prev = fc[i-2]['value'] if i>1 else None
        if (abs_th is not None and pt['value']<abs_th) or (rel_th is not None and prev and ((prev-pt['value'])/prev*100)>rel_th):
            triggered.append(pt)
    return render_template('alerts_view.html', upload_id=upload_id, alerts=triggered, message=None)

if __name__=='__main__':
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    conn = sqlite3.connect(DB_PATH); c=conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS uploads(upload_id INTEGER PRIMARY KEY,filename TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS transactions(id INTEGER PRIMARY KEY,upload_id INTEGER,date DATE,libelle TEXT,montant REAL,solde REAL)')
    c.execute('CREATE TABLE IF NOT EXISTS alerts(upload_id INTEGER PRIMARY KEY,abs_threshold REAL,rel_threshold REAL,email_enabled INTEGER)')
    conn.commit(); conn.close()
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT',5001)), debug=True)

# ---- Page d’alertes opérationnelles ----
@app.route('/alerts/view/<int:upload_id>')
def alerts_view(upload_id):
    # on récupère depuis la BDD (data/uploads/uploads.db) les seuils stockés
    import sqlite3
    conn = sqlite3.connect(DB_PATH)
    cur  = conn.cursor()
    cur.execute("SELECT abs_threshold, rel_threshold, email_enabled FROM alerts WHERE upload_id=?",
                (upload_id,))
    row = cur.fetchone()
    conn.close()
    abs_th, rel_th, email_en = (row if row else (None, None, False))

    # on récupère les données de prévision
    from app import compute_forecast  # fonction interne renvoyant liste de {date,value}
    forecast = compute_forecast(upload_id)

    # on calcule les points déclencheurs
    triggered = []
    prev = None
    for point in forecast:
        if prev is not None:
            cond_abs = abs_th is not None and (prev - point['value']) > abs_th
            cond_rel = rel_th is not None and ((prev - point['value'])/prev*100) > rel_th
            if cond_abs or cond_rel:
                triggered.append(point)
        prev = point['value']

    return render_template('alerts_view.html',
                           upload_id=upload_id,
                           alerts=triggered,
                           message=('Aucun seuil configuré.' if abs_th is None and rel_th is None else None))
