import numpy as np
import pandas as pd
import random
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
import pickle

# --------------------- Generate Synthetic Elderly Dataset ---------------------

def generate_data(n=1000):   # UPDATED to 1000 rows
    data = []

    for _ in range(n):
        age = random.randint(45, 90)
        sbp = random.randint(100, 190)
        dbp = random.randint(60, 120)
        sugar = random.randint(80, 350)
        hr = random.randint(50, 130)
        temp = round(random.uniform(36, 40), 1)
        weight = random.randint(45, 120)
        height = random.randint(140, 180)
        
        bmi = weight / ((height / 100) ** 2)

        # Risk scoring (synthetic but medically realistic)
        score = 0

        if age > 75: 
            score += 2
        
        if sbp > 160 or dbp > 100: 
            score += 3
        elif sbp > 140 or dbp > 90: 
            score += 2
        
        if sugar > 250: 
            score += 3
        elif sugar > 180: 
            score += 2

        if hr > 110 or hr < 50: 
            score += 2

        if temp > 38.5: 
            score += 2

        if bmi > 32: 
            score += 2
        elif bmi > 28: 
            score += 1

        # Map score → risk category
        if score >= 7:
            label = 2   # High risk
        elif score >= 4:
            label = 1   # Moderate
        else:
            label = 0   # Low

        data.append([age, sbp, dbp, sugar, hr, temp, weight, height, bmi, label])

    df = pd.DataFrame(data, columns=[
        "age", "systolic_bp", "diastolic_bp", "sugar", "heart_rate",
        "temperature", "weight", "height", "bmi", "label"
    ])

    return df


# --------------------- Generate and Save Dataset ---------------------

df = generate_data(1000)   # 1000 rows
print(df.head())
print("\nDataset shape:", df.shape)

csv_path = "health_risk_dataset_1000.csv"
df.to_csv(csv_path, index=False)

print(f"\nCSV dataset saved successfully at: {csv_path}")


# --------------------- Train ML Model ---------------------

X = df.drop("label", axis=1)
y = df["label"]

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42
)

model = RandomForestClassifier(
    n_estimators=250,
    max_depth=14,
    random_state=42
)

model.fit(X_train, y_train)

accuracy = model.score(X_test, y_test)
print("\nModel Accuracy:", accuracy)


# --------------------- Save Trained Model ---------------------

pickle.dump(model, open("model.pkl", "wb"))
print("\nmodel.pkl saved successfully!")
