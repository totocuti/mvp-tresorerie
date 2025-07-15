from flask import Flask, request, render_template, jsonify, redirect, url_for
import os, sqlite3, pandas as pd, numpy as np
from datetime import datetime, timedelta

UPLOAD_FOLDER = 'data/uploads'
DB_PATH = os.path.join(UPLOAD_FOLDER, 'uploads.db')
app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def compute_forecast(upload_id, days=30):
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query("SELECT date, solde FROM transactions WHERE upload_id=? ORDER BY date", conn, params=(upload_id,))
    conn.close()
    df['date'] = pd.to_datetime(df['date'])
    df.set_index('date', inplace=True)
    series = df['solde']
    window = min(len(series),30)
    recent = series[-window:]
    x = np.array([d.toordinal() for d in recent.index]); y = recent.values
    slope, intercept = np.polyfit(x,y,1)
    last = series.index[-1]; result = []
    for i in range(1,days+1):
        d = last + timedelta(days=i)
        v = intercept + slope*d.toordinal()
        result.append({'date':d.strftime('%Y-%m-%d'),'value':float(v)})
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
    cur.execute('INSERT INTO uploads(filename) VALUES(?)',(f.filename,))
    uid = cur.lastrowid
    conn.commit(); conn.close()
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

if __name__=='__main__':
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS uploads(upload_id INTEGER PRIMARY KEY,filename TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS transactions(id INTEGER PRIMARY KEY,upload_id INTEGER,date DATE,libelle TEXT,montant REAL,solde REAL)')
    conn.commit(); conn.close()
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5001)), debug=True)
