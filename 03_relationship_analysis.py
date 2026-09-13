# -*- coding: utf-8 -*-
"""
03_關係分析.py
政府開放資料應用案例（第2個主題）：全臺PM2.5空氣品質長期趨勢分析
Stage 3（第一部分）：關係分析 —— 縣市間比較、假日 vs 平日比較

這兩個題目都不需要額外抓新資料，直接用手上56個月份的PM2.5資料就能做：
  1) 縣市間比較：因為county欄位中英文混用（44個相異值，但實際只有22個縣市），
     所以先建立一份中英文對照表，把英文縣市名稱統一轉換成中文，才能正確分組比較。
  2) 假日 vs 平日比較：用監測日期算出星期幾，比較平日與假日的PM2.5平均濃度差異。

氣象資料關係分析（風速、雨量等）因為需要另外向中央氣象署抓取新的資料集，
會在確認這兩個分析都沒問題之後，再另外開一個階段來處理。

【執行前準備】跟01、02一樣，本腳本要跟56個月份的PM2.5 CSV放在同一個資料夾。
"""

import csv
import datetime
import glob
import re
from collections import defaultdict

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

plt.rcParams["font.sans-serif"] = ["Microsoft JhengHei", "Microsoft YaHei", "SimHei"]
plt.rcParams["axes.unicode_minus"] = False

# 英文縣市名稱 → 中文縣市名稱對照表（從01_資料探索.py的縣市欄位檢查結果整理而來）
COUNTY_EN_TO_ZH = {
    "Changhua County": "彰化縣",
    "Chiayi City": "嘉義市",
    "Chiayi County": "嘉義縣",
    "Hsinchu City": "新竹市",
    "Hsinchu County": "新竹縣",
    "Hualien County": "花蓮縣",
    "Kaohsiung City": "高雄市",
    "Keelung City": "基隆市",
    "Kinmen County": "金門縣",
    "Lienchiang County": "連江縣",
    "Miaoli County": "苗栗縣",
    "Nantou County": "南投縣",
    "New Taipei City": "新北市",
    "Penghu County": "澎湖縣",
    "Pingtung County": "屏東縣",
    "Taichung City": "臺中市",
    "Tainan City": "臺南市",
    "Taipei City": "臺北市",
    "Taitung County": "臺東縣",
    "Taoyuan County": "桃園市",
    "Yilan County": "宜蘭縣",
    "Yunlin County": "雲林縣",
}


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


def normalize_county(county):
    """把英文縣市名稱轉換成中文；已經是中文的直接回傳"""
    return COUNTY_EN_TO_ZH.get(county.strip(), county.strip())


def to_float_or_none(s):
    s = s.strip()
    try:
        return float(s)
    except ValueError:
        return None


def parse_date(monitordate):
    d = monitordate.strip()
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})", d)
    if not m:
        return None
    return datetime.date(int(m.group(1)), int(m.group(2)), int(m.group(3)))


def chart1_county_comparison(rows):
    """縣市間PM2.5平均濃度比較（先做中英文縣市名稱正規化）"""
    county_values = defaultdict(list)
    for r in rows:
        county = normalize_county(r["county"])
        v = to_float_or_none(r["concentration"])
        if v is None or not county:
            continue
        county_values[county].append(v)

    print(f"【圖1】正規化後縣市數量：{len(county_values)} 個（應為22個）")

    stats = []
    for county, values in county_values.items():
        avg = sum(values) / len(values)
        stats.append((county, avg, len(values)))
    stats.sort(key=lambda x: x[1], reverse=True)

    print("\n各縣市PM2.5平均濃度排名（由高到低）：")
    for county, avg, n in stats:
        print(f"  {county}：{avg:.1f} μg/m3（樣本數 {n}）")

    counties = [s[0] for s in stats]
    avgs = [s[1] for s in stats]
    overall_avg = sum(v for values in county_values.values() for v in values) / \
        sum(len(values) for values in county_values.values())

    fig, ax = plt.subplots(figsize=(9, 10))
    colors = ["#B5651D" if a >= overall_avg else "#4A90A4" for a in avgs]
    ax.barh(counties, avgs, color=colors)
    ax.invert_yaxis()
    ax.axvline(overall_avg, color="gray", linestyle="--", linewidth=1)
    ax.text(overall_avg, -0.8, f"全國均值 {overall_avg:.1f}", color="gray",
            fontsize=9, ha="center")
    ax.set_title("各縣市PM2.5平均濃度排名（2022/01~2026/08，橘色為高於全國均值）", pad=16)
    ax.set_xlabel("平均濃度（μg/m3）")
    for i, a in enumerate(avgs):
        ax.annotate(f"{a:.1f}", xy=(a, i), xytext=(4, 0),
                    textcoords="offset points", va="center", fontsize=8)

    fig.tight_layout()
    fig.savefig("county_comparison.png", dpi=150)
    plt.close(fig)
    print("已輸出 county_comparison.png")


def chart2_weekday_weekend(rows):
    """星期幾 vs PM2.5平均濃度（平日/假日比較）"""
    WEEKDAY_NAMES = ["一", "二", "三", "四", "五", "六", "日"]
    weekday_values = defaultdict(list)

    for r in rows:
        d = parse_date(r["monitordate"])
        v = to_float_or_none(r["concentration"])
        if d is None or v is None:
            continue
        weekday_values[d.weekday()].append(v)

    avgs = [sum(weekday_values[i]) / len(weekday_values[i]) for i in range(7)]
    counts = [len(weekday_values[i]) for i in range(7)]

    weekday_all = [v for i in range(5) for v in weekday_values[i]]
    weekend_all = [v for i in range(5, 7) for v in weekday_values[i]]
    weekday_avg = sum(weekday_all) / len(weekday_all)
    weekend_avg = sum(weekend_all) / len(weekend_all)

    print("\n【圖2】各星期平均PM2.5濃度：")
    for i, name in enumerate(WEEKDAY_NAMES):
        print(f"  星期{name}：{avgs[i]:.2f} μg/m3（樣本數 {counts[i]}）")
    print(f"\n平日（一~五）平均：{weekday_avg:.2f} μg/m3")
    print(f"假日（六、日）平均：{weekend_avg:.2f} μg/m3")
    print(f"差異：{weekday_avg - weekend_avg:+.2f} μg/m3"
          f"（{'平日較高' if weekday_avg > weekend_avg else '假日較高'}）")

    fig, ax = plt.subplots(figsize=(8, 5.5))
    colors = ["#B5651D"] * 5 + ["#4A90A4"] * 2
    bars = ax.bar([f"星期{n}" for n in WEEKDAY_NAMES], avgs, color=colors)
    ax.set_title("各星期平均PM2.5濃度（橘色為平日、藍色為假日）", pad=16)
    ax.set_ylabel("平均濃度（μg/m3）")
    ax.set_ylim(top=max(avgs) * 1.2)
    for bar, a in zip(bars, avgs):
        ax.annotate(f"{a:.2f}", xy=(bar.get_x() + bar.get_width() / 2, a),
                    xytext=(0, 4), textcoords="offset points", ha="center", fontsize=9)
    ax.grid(axis="y", alpha=0.3)

    fig.tight_layout()
    fig.savefig("weekday_weekend.png", dpi=150)
    plt.close(fig)
    print("已輸出 weekday_weekend.png")


def main():
    rows = load_all_rows()
    clean_rows = dedup_rows(rows)
    print(f"共讀取 {len(rows)} 筆原始資料，去重複後剩餘 {len(clean_rows)} 筆\n")

    chart1_county_comparison(clean_rows)
    chart2_weekday_weekend(clean_rows)


if __name__ == "__main__":
    main()
