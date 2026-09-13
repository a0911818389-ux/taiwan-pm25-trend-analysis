# -*- coding: utf-8 -*-
"""
04_PM25預測模型.py
政府開放資料應用案例（第2個主題）：全臺PM2.5空氣品質長期趨勢分析
Stage 4：建模 —— 用行政區、年份、月份、星期幾預測PM2.5濃度

跟臺中房價案例一樣，比較線性迴歸（LinearRegression）與Random Forest兩種模型。

【為什麼沒有把風速、降水量也當作特徵？】
Stage 3的氣象關聯分析，用的是「全臺月平均PM2.5」對「臺北單一測站的月資料」，
是月為單位、全國只有一組數字。但這裡建模是用「每個測站、每一天」的原始紀錄
（去重複後約13萬筆），如果每一筆都套用同一個臺北測站的月平均風速/雨量，
等於81個測站在同一個月都套用一模一樣的天氣數字，會嚴重扭曲模型、也不合理
（雲林的天氣不會跟臺北一樣）。要做到「每個測站」等級的天氣特徵，需要另外
抓每個測站附近的氣象站逐日資料，工程量很大，所以這次模型先用「縣市、年份、
月份、星期幾」四個資料裡本來就有、且顆粒度一致的特徵。

【執行前準備】跟01~03一樣，本腳本要跟56個月份的PM2.5 CSV放在同一個資料夾。
需要 pandas、scikit-learn（如果沒安裝，先執行 pip install pandas scikit-learn）。
"""

import csv
import glob
import re
from collections import defaultdict

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

COUNTY_EN_TO_ZH = {
    "Changhua County": "彰化縣", "Chiayi City": "嘉義市", "Chiayi County": "嘉義縣",
    "Hsinchu City": "新竹市", "Hsinchu County": "新竹縣", "Hualien County": "花蓮縣",
    "Kaohsiung City": "高雄市", "Keelung City": "基隆市", "Kinmen County": "金門縣",
    "Lienchiang County": "連江縣", "Miaoli County": "苗栗縣", "Nantou County": "南投縣",
    "New Taipei City": "新北市", "Penghu County": "澎湖縣", "Pingtung County": "屏東縣",
    "Taichung City": "臺中市", "Tainan City": "臺南市", "Taipei City": "臺北市",
    "Taitung County": "臺東縣", "Taoyuan County": "桃園市", "Yilan County": "宜蘭縣",
    "Yunlin County": "雲林縣",
}

SAMPLE_SIZE = 30000  # 從約13萬筆去重複資料中隨機抽樣，避免訓練時間過長
RANDOM_STATE = 42


def normalize_county(county):
    return COUNTY_EN_TO_ZH.get(county.strip(), county.strip())


def load_dataset():
    files = sorted(glob.glob("PM2.5*.csv"))
    if not files:
        raise FileNotFoundError("找不到 PM2.5*.csv，請確認56個月份的PM2.5資料在同一層資料夾")

    seen = set()
    records = []
    for fp in files:
        with open(fp, encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            for r in reader:
                key = (r["siteid"], r["monitordate"].strip())
                if key in seen:
                    continue
                seen.add(key)

                d = r["monitordate"].strip()
                m = re.match(r"(\d{4})-(\d{2})-(\d{2})", d)
                if not m:
                    continue
                c = r["concentration"].strip()
                try:
                    v = float(c)
                except ValueError:
                    continue

                year, month, day = int(m.group(1)), int(m.group(2)), int(m.group(3))
                import datetime
                weekday = datetime.date(year, month, day).weekday()

                records.append({
                    "county": normalize_county(r["county"]),
                    "year": year,
                    "month": month,
                    "weekday": weekday,
                    "concentration": v,
                })
    df = pd.DataFrame(records)
    return df


def evaluate(name, model, X_train, X_test, y_train, y_test):
    model.fit(X_train, y_train)
    pred = model.predict(X_test)
    r2 = r2_score(y_test, pred)
    mae = mean_absolute_error(y_test, pred)
    rmse = mean_squared_error(y_test, pred) ** 0.5
    print(f"{name}：R平方={r2:.4f}　MAE={mae:.3f} μg/m3　RMSE={rmse:.3f} μg/m3")
    return r2, mae, rmse


def main():
    df = load_dataset()
    print(f"去重複、清理無效值後共 {len(df)} 筆資料")

    df_sample = df.sample(n=min(SAMPLE_SIZE, len(df)), random_state=RANDOM_STATE)
    print(f"隨機抽樣 {len(df_sample)} 筆用於建模（避免訓練時間過長）\n")

    X = df_sample[["county", "year", "month", "weekday"]]
    y = df_sample["concentration"]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=RANDOM_STATE
    )
    print(f"訓練集：{len(X_train)} 筆　測試集：{len(X_test)} 筆\n")

    categorical_features = ["county", "month", "weekday"]
    numeric_features = ["year"]

    preprocessor = ColumnTransformer(
        transformers=[
            ("cat", OneHotEncoder(handle_unknown="ignore"), categorical_features),
        ],
        remainder="passthrough",  # year直接保留
    )

    lr_pipe = Pipeline([("prep", preprocessor), ("model", LinearRegression())])
    rf_pipe = Pipeline([
        ("prep", preprocessor),
        ("model", RandomForestRegressor(n_estimators=200, max_depth=10,
                                          random_state=RANDOM_STATE, n_jobs=-1)),
    ])

    print("【模型比較】")
    evaluate("線性迴歸　　", lr_pipe, X_train, X_test, y_train, y_test)
    evaluate("Random Forest", rf_pipe, X_train, X_test, y_train, y_test)

    print("\n【Random Forest 特徵重要性前10名】")
    feature_names = rf_pipe.named_steps["prep"].get_feature_names_out()
    importances = rf_pipe.named_steps["model"].feature_importances_
    order = np.argsort(importances)[::-1][:10]
    for idx in order:
        print(f"  {feature_names[idx]}：{importances[idx]:.4f}")


if __name__ == "__main__":
    main()
