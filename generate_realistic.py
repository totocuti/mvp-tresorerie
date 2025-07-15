import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import os

# Paramètres réalistes (CA 100k€/an pour la PME)
start_date = datetime(2025, 1, 1)
days = 365
base_balance = 10000
monthly_revenue = 100000 / 12
expense_mean = 300
expense_std = 50

dates = [start_date + timedelta(days=i) for i in range(days)]
balances = [base_balance]
records = []

for i in range(1, days):
    current_date = dates[i]
    rev = np.random.normal(monthly_revenue, monthly_revenue * 0.1) if current_date.day == 1 else 0.0
    exp = abs(np.random.normal(expense_mean, expense_std))
    change = rev - exp
    new_balance = balances[-1] + change
    balances.append(new_balance)
    records.append({
        "Date": current_date.strftime('%Y-%m-%d'),
        "Libellé": "Synthétique PME",
        "Montant": round(change, 2),
        "Solde": round(new_balance, 2)
    })

initial = {
    "Date": dates[0].strftime('%Y-%m-%d'),
    "Libellé": "Solde initial",
    "Montant": 0.0,
    "Solde": round(base_balance, 2)
}
df = pd.DataFrame([initial] + records)

# Sauvegarde
os.makedirs('data/uploads', exist_ok=True)
df.to_csv('data/uploads/synthetic_transactions_realistic.csv', index=False)
print("Fichier généré : data/uploads/synthetic_transactions_realistic.csv")
