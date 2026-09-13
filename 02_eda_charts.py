# -*- coding: utf-8 -*-
"""
02_EDA探索圖表.py
政府開放資料應用案例（第2個主題）：全臺PM2.5空氣品質長期趨勢分析
Stage 2：EDA探索圖表

畫三張圖：
  1) 每月不重複測站代碼數量趨勢 —— 驗證「測站數量增加」假說
  2) 全臺PM2.5月平均濃度長期趨勢
  3) 各月份（1~12月）平均PM2.5濃度 —— 看季節性規律

【執行前準備】
跟 01_資料探索.py 一樣，本腳本要跟56個月份的PM2.5 CSV放在同一個資料夾。
"""

import csv
import glob
import re
from collections import Counter, defaultdict

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

plt.rcParams["font.sans-serif"] = ["Microsoft JhengHei", "Microsoft YaHei", "SimHei"]
plt.rcParams["axes.unicode_minus"] = False


def load_all_rows():
    files = sorted(glob.glob("PM2.5*.csv"))
    if not files:
        raise FileNotFoundError(
            "找不到任何 PM2.5*.csv 檔案，請確認腳本跟下載的56個月份CSV放在同一層資料夾"
        )
    rows = []
    for fp in files:
        with open(fp, encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            for r in reader:
                rows.append(r)
    return rows


def parse_ym(monitordate):
    """從監測日期字串（例如 '2022-01-15 '）取出 'YYYY-MM'"""
    d = monitordate.strip()
    m = re.match(r"(\d{4})-(\d{2})-\d{2}", d)
    if not m:
        return None
    return f"{m.group(1)}-{m.group(2)}"


def parse_month_num(monitordate):
    """從監測日期字串取出月份數字（1~12），用來看季節性"""
    d = monitordate.strip()
    m = re.match(r"\d{4}-(\d{2})-\d{2}", d)
    if not m:
        return None
    return int(m.group(1))


def to_float_or_none(s):
    s = s.strip()
    try:
        return float(s)
    except ValueError:
        return None


def dedup_rows(rows):
    """用（siteid, monitordate）當唯一鍵去除重複列，只保留第一筆"""
    seen = set()
    result = []
    for r in rows:
        key = (r["siteid"], r["monitordate"].strip())
        if key in seen:
            continue
        seen.add(key)
        result.append(r)
    return result


def chart1_station_count_trend(rows):
    """
    每月不重複測站代碼數量 vs. 原始筆數趨勢。

    原本假設是「2024年後筆數暴增 = 測站變多」，但實際畫出「不重複測站數」後
    發現全期間只從78個增加到80個，幾乎沒變化，這個假說不成立。
    真正原因是原始資料本身存在重複列（同一測站、同一天出現2~5次不等，
    詳見 01_資料探索.py 的重複資料檢查），所以這張圖改成同時畫「原始筆數」
    與「去重複後的（測站,日期）組合數」，讓兩者的落差直接說明重複列的規模。
    """
    ym_stations = defaultdict(set)
    ym_raw_count = Counter()
    ym_dedup_count = Counter()
    seen_keys = set()

    for r in rows:
        ym = parse_ym(r["monitordate"])
        if ym is None:
            continue
        ym_stations[ym].add(r["siteid"])
        ym_raw_count[ym] += 1
        key = (r["siteid"], r["monitordate"].strip())
        if key not in seen_keys:
            seen_keys.add(key)
            ym_dedup_count[ym] += 1

    yms = sorted(ym_stations.keys())
    station_counts = [len(ym_stations[ym]) for ym in yms]
    raw_counts = [ym_raw_count[ym] for ym in yms]
    dedup_counts = [ym_dedup_count[ym] for ym in yms]

    print("【圖1】每月不重複測站數量（節錄前3筆與後3筆）：")
    for ym, c in list(zip(yms, station_counts))[:3]:
        print(f"  {ym}：{c} 個測站")
    print("  ...")
    for ym, c in list(zip(yms, station_counts))[-3:]:
        print(f"  {ym}：{c} 個測站")
    print("→ 測站數量幾乎沒變化（78~80個），「測站增加」假說不成立。")

    fig, ax = plt.subplots(figsize=(13, 5.5))
    x = range(len(yms))
    ax.plot(x, raw_counts, marker="o", markersize=3, color="#B5651D",
             linewidth=1.6, label="原始筆數（含重複列）")
    ax.plot(x, dedup_counts, marker="o", markersize=3, color="#2E7D6B",
             linewidth=1.6, label="去重複後（測站,日期）組合數")
    ax.set_title("原始筆數 vs. 去重複後筆數：驗證2024年後筆數暴增的真正原因", pad=16)
    ax.set_xlabel("年月")
    ax.set_ylabel("筆數")
    ax.legend(loc="upper left")

    tick_idx = list(range(0, len(yms), 6))
    ax.set_xticks(tick_idx)
    ax.set_xticklabels([yms[i] for i in tick_idx], rotation=45, ha="right")
    ax.set_ylim(bottom=0, top=max(raw_counts) * 1.15)
    ax.grid(axis="y", alpha=0.3)

    fig.tight_layout()
    fig.savefig("station_count_trend.png", dpi=150)
    plt.close(fig)
    print("已輸出 station_count_trend.png")
    return yms, station_counts


def chart2_national_avg_trend(rows):
    """全臺PM2.5月平均濃度長期趨勢"""
    ym_values = defaultdict(list)
    for r in rows:
        ym = parse_ym(r["monitordate"])
        v = to_float_or_none(r["concentration"])
        if ym is None or v is None:
            continue
        ym_values[ym].append(v)

    yms = sorted(ym_values.keys())
    avgs = [sum(ym_values[ym]) / len(ym_values[ym]) for ym in yms]

    print("\n【圖2】全臺PM2.5月平均濃度（節錄前3筆與後3筆）：")
    for ym, a in list(zip(yms, avgs))[:3]:
        print(f"  {ym}：{a:.1f} μg/m3")
    print("  ...")
    for ym, a in list(zip(yms, avgs))[-3:]:
        print(f"  {ym}：{a:.1f} μg/m3")

    fig, ax = plt.subplots(figsize=(13, 5.5))
    x = range(len(yms))
    ax.plot(x, avgs, marker="o", markersize=3, color="#B5651D", linewidth=1.6)
    ax.set_title("全臺PM2.5月平均濃度長期趨勢（2022/01~2026/08）", pad=16)
    ax.set_xlabel("年月")
    ax.set_ylabel("PM2.5月平均濃度（μg/m3）")

    tick_idx = list(range(0, len(yms), 6))
    ax.set_xticks(tick_idx)
    ax.set_xticklabels([yms[i] for i in tick_idx], rotation=45, ha="right")
    ax.set_ylim(bottom=0, top=max(avgs) * 1.2)
    ax.grid(axis="y", alpha=0.3)

    fig.tight_layout()
    fig.savefig("national_avg_trend.png", dpi=150)
    plt.close(fig)
    print("已輸出 national_avg_trend.png")
    return yms, avgs


def chart3_seasonal_pattern(rows):
    """各月份（1~12月，跨2022~2026年合併）平均PM2.5濃度"""
    month_values = defaultdict(list)
    for r in rows:
        mnum = parse_month_num(r["monitordate"])
        v = to_float_or_none(r["concentration"])
        if mnum is None or v is None:
            continue
        month_values[mnum].append(v)

    months = list(range(1, 13))
    avgs = [sum(month_values[m]) / len(month_values[m]) for m in months]
    counts = [len(month_values[m]) for m in months]

    print("\n【圖3】各月份平均PM2.5濃度（跨2022~2026年合併計算）：")
    for m, a, c in zip(months, avgs, counts):
        print(f"  {m}月：{a:.1f} μg/m3（樣本數 {c}）")

    fig, ax = plt.subplots(figsize=(10, 5.5))
    colors = ["#8B4A9C" if a >= sum(avgs) / len(avgs) else "#4A90A4" for a in avgs]
    bars = ax.bar([f"{m}月" for m in months], avgs, color=colors)
    ax.set_title("全臺PM2.5各月份平均濃度（2022~2026年合併，紫色為高於全年均值）", pad=16)
    ax.set_ylabel("平均濃度（μg/m3）")
    ax.set_ylim(top=max(avgs) * 1.2)
    for bar, a in zip(bars, avgs):
        ax.annotate(f"{a:.1f}", xy=(bar.get_x() + bar.get_width() / 2, a),
                    xytext=(0, 4), textcoords="offset points", ha="center", fontsize=9)
    ax.grid(axis="y", alpha=0.3)

    fig.tight_layout()
    fig.savefig("seasonal_pattern.png", dpi=150)
    plt.close(fig)
    print("已輸出 seasonal_pattern.png")


def main():
    rows = load_all_rows()
    print(f"共讀取 {len(rows)} 筆原始資料（尚未去重複）\n")

    # 圖1本身就是為了呈現「原始 vs 去重複」的落差，所以用原始rows
    chart1_station_count_trend(rows)

    # 圖2、圖3是實際的統計分析，用去重複後的資料，避免重複列灌水樣本數
    # （雖然重複列的濃度數值本身相同、對平均值沒有影響，但樣本數會失真）
    clean_rows = dedup_rows(rows)
    print(f"\n去重複後剩餘 {len(clean_rows)} 筆資料，後續圖2、圖3以此為準\n")

    chart2_national_avg_trend(clean_rows)
    chart3_seasonal_pattern(clean_rows)


if __name__ == "__main__":
    main()
