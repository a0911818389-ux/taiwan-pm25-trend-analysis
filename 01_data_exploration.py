# -*- coding: utf-8 -*-
"""
01_資料探索.py
政府開放資料應用案例（第2個主題）：全臺PM2.5空氣品質長期趨勢分析
Stage 1：資料探索

【執行前準備】
請把本腳本，跟從環境部「環境資料開放平臺」下載的56個月份PM2.5 CSV檔案
（檔名類似「PM2.5日均值(每日提供) (2022-01).csv」）放在同一個資料夾。
不需要自己合併檔案，腳本會自動讀取資料夾內所有PM2.5開頭的CSV再合併。
"""

import csv
import glob
from collections import Counter, defaultdict


def load_all_rows():
    """讀取資料夾內所有 PM2.5*.csv 檔案，回傳 (檔案清單, 合併後的資料列, 各檔案筆數)"""
    files = sorted(glob.glob("PM2.5*.csv"))
    if not files:
        raise FileNotFoundError(
            "找不到任何 PM2.5*.csv 檔案，請確認腳本跟下載的56個月份CSV放在同一層資料夾"
        )

    rows = []
    per_file_count = {}
    for fp in files:
        with open(fp, encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            n = 0
            for r in reader:
                rows.append(r)
                n += 1
            per_file_count[fp] = n
    return files, rows, per_file_count


def main():
    files, rows, per_file_count = load_all_rows()

    print("=" * 50)
    print("【基本資訊】")
    print(f"讀取檔案數：{len(files)} 個")
    print(f"合併後總筆數：{len(rows)} 筆")
    if rows:
        print(f"欄位：{list(rows[0].keys())}")

    print("\n" + "=" * 50)
    print("【監測日期範圍】")
    dates = [r["monitordate"].strip() for r in rows if r.get("monitordate")]
    print(f"最早：{min(dates)}　最晚：{max(dates)}")

    print("\n" + "=" * 50)
    print("【測站數量】")
    station_ids = set(r["siteid"] for r in rows)
    station_names = set(r["sitename"] for r in rows)
    print(f"測站代碼（siteid）相異值數量：{len(station_ids)}")
    print(f"測站名稱（sitename）相異值數量：{len(station_names)}")
    if len(station_ids) != 0:
        print("（提醒：若測站名稱數量比代碼數量多很多，代表同一個測站可能有不同語言的名稱寫法）")

    print("\n" + "=" * 50)
    print("【縣市欄位檢查】")
    counties = Counter(r["county"] for r in rows)
    print(f"county欄位相異值數量：{len(counties)}")
    print("出現次數最多的前10個：")
    for c, n in counties.most_common(10):
        print(f"  {c!r}：{n} 筆")

    print("\n" + "=" * 50)
    print("【數值（concentration）欄位檢查】")
    non_numeric = Counter()
    valid_count = 0
    for r in rows:
        c = r["concentration"].strip()
        try:
            float(c)
            valid_count += 1
        except ValueError:
            non_numeric[c] += 1
    print(f"可正常轉換為數字的筆數：{valid_count} / {len(rows)}")
    if non_numeric:
        print(f"無法轉換為數字的值與出現次數：{dict(non_numeric)}")
    else:
        print("沒有發現無法轉換的值")

    print("\n" + "=" * 50)
    print("【各月份筆數分布（檢查是否有異常偏少或偏多的月份）】")
    # 從檔名取出年月做排序顯示
    def extract_ym(fp):
        import re
        m = re.search(r"(\d{4}-\d{2})", fp)
        return m.group(1) if m else fp

    sorted_files = sorted(per_file_count.items(), key=lambda kv: extract_ym(kv[0]))
    counts_only = [n for _, n in sorted_files]
    avg = sum(counts_only) / len(counts_only)
    print(f"平均每月筆數：約 {avg:.0f} 筆")
    print("各月份筆數：")
    for fp, n in sorted_files:
        flag = ""
        if n < avg * 0.6:
            flag = "　←偏少"
        elif n > avg * 1.6:
            flag = "　←偏多"
        print(f"  {extract_ym(fp)}：{n} 筆{flag}")

    print("\n" + "=" * 50)
    print("【重複資料檢查：同一測站、同一天是否出現超過一筆】")
    key_counter = Counter((r["siteid"], r["monitordate"].strip()) for r in rows)
    dup_keys = {k: n for k, n in key_counter.items() if n > 1}
    print(f"（測站代碼, 監測日期）不重複組合數：{len(key_counter)}")
    print(f"原始總筆數：{len(rows)}　→　重複造成的多餘筆數：{len(rows) - len(key_counter)}")
    print(f"有重複的（測站, 日期）組合數：{len(dup_keys)}")
    if dup_keys:
        max_key = max(dup_keys, key=lambda k: dup_keys[k])
        print(f"重複次數最多的例子：測站{max_key[0]}、{max_key[1]}，共出現 {dup_keys[max_key]} 次")
        print("（提醒：這代表原始資料本身有重複列，不是測站變多了。之後計算「每站每天一筆」")
        print("　的統計量時，要先用（siteid, monitordate）去重複，只保留第一筆再分析）")
    else:
        print("沒有發現重複列")

    print("\n" + "=" * 50)
    print("【缺值檢查（各欄位空字串數量）】")
    if rows:
        field_names = list(rows[0].keys())
        missing = {field: 0 for field in field_names}
        for r in rows:
            for field in field_names:
                if not r.get(field, "").strip():
                    missing[field] += 1
        for field, n in missing.items():
            print(f"  {field}：缺值 {n} 筆")


if __name__ == "__main__":
    main()
