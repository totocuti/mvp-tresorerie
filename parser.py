import sqlite3, pandas as pd

DB_PATH = 'data/uploads/uploads.db'

def parse_and_store(upload_id, file_path):
    conn = sqlite3.connect(DB_PATH); cur = conn.cursor()
    df = pd.read_csv(file_path)
    expected = {'Date','Libellé','Montant','Solde'}
    if not expected.issubset(df.columns):
        raise ValueError(f"Colonnes manquantes: {expected - set(df.columns)}")
    df['Date']  = pd.to_datetime(df['Date'], dayfirst=True, errors='coerce')
    df['Montant']=pd.to_numeric(df['Montant'], errors='coerce')
    df['Solde'] =pd.to_numeric(df['Solde'], errors='coerce')
    df = df.dropna(subset=['Date','Montant','Solde'])
    cur.execute('CREATE TABLE IF NOT EXISTS transactions(id INTEGER PRIMARY KEY, upload_id INTEGER, date DATE, libelle TEXT, montant REAL, solde REAL)')
    for _,r in df.iterrows():
        cur.execute('INSERT INTO transactions(upload_id,date,libelle,montant,solde) VALUES(?,?,?,?,?)',
                    (upload_id, r['Date'].strftime('%Y-%m-%d'), r['Libellé'], r['Montant'], r['Solde']))
    cur.execute('UPDATE uploads SET status="parsed" WHERE upload_id=?',(upload_id,))
    conn.commit(); conn.close()
