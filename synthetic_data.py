import pandas as pd, numpy as np
from datetime import datetime, timedelta

def generate_synthetic_cashflow(start_date, days=365, base_balance=10000):
    dates = [start_date + timedelta(days=i) for i in range(days)]
    balances = [base_balance]
    records = []
    for i in range(1, days):
        change = 0.8*(balances[-1]-base_balance) + np.random.normal(scale=base_balance*0.02)
        new_bal = max(0, balances[-1] + change)
        if np.random.rand()<0.02:
            shock = -abs(np.random.uniform(base_balance*0.1, base_balance*0.3))
            new_bal = max(0, balances[-1] + shock)
        amount = new_bal - balances[-1]
        records.append({"Date":dates[i].strftime('%Y-%m-%d'),"Libellé":"Synthétique","Montant":round(amount,2),"Solde":round(new_bal,2)})
        balances.append(new_bal)
    initial = {"Date":dates[0].strftime('%Y-%m-%d'),"Libellé":"Solde initial","Montant":0.0,"Solde":balances[0]}
    df = pd.DataFrame([initial]+records)
    df.to_csv('data/uploads/synthetic_transactions.csv', index=False)
    print(f"synthetic_transactions.csv généré ({len(df)} lignes)")

if __name__=="__main__":
    generate_synthetic_cashflow(datetime.strptime('2025-01-01','%Y-%m-%d'), days=365)
