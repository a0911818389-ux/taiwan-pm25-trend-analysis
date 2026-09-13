# -*- coding: utf-8 -*-
"""
03b_氣象關聯分析.py
政府開放資料應用案例（第2個主題）：全臺PM2.5空氣品質長期趨勢分析
Stage 3（第二部分）：氣象資料關聯分析 —— 風速、降水量 vs PM2.5

資料來源：
  1) 全臺56個月份PM2.5 CSV（PM2.5*.csv） —— 跟01、02、03同一批
  2) 中央氣象署CODiS臺北測站（466920）「全項逐月年報表」，2022~2026各一份CSV
     （檔名例如 466920-2022.csv）

【執行前準備】
本腳本要跟56個月份PM2.5 CSV，以及5個466920-年份.csv氣象檔案放在同一個資料夾。
"""

import csv
import glob
import re
from collections import defaultdict

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

plt.rcParams["font.sans-serif"] = ["Microsoft JhengHei", "Microsoft YaHei", "SimHei"]
plt.rcParams["axes.unicode_minus"] = False


# ---------- PM2.5資料 ----------

def load_pm25_monthly_avg():
    """讀取56個月份PM2.5 CSV，去重複後計算全臺月平均濃度，回傳 {'2022-01': 17.9, ...}"""
    files = sorted(glob.glob("PM2.5*.csv"))
    if not files:
        raise FileNotFoundError("找不到 PM2.5*.csv，請確認56個月份的PM2.5資料在同一層資料夾")

    seen = set()
    ym_values = defaultdict(list)
    for fp in files:
        with open(fp, encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            for r in reader:
                key = (r["siteid"], r["monitordate"].strip())
                if key in seen:
                    continue
                seen.add(key)
                d = r["monitordate"].strip()
                m = re.match(r"(\d{4})-(\d{2})-\d{2}", d)
                if not m:
                    continue
                ym = f"{m.group(1)}-{m.group(2)}"
                try:
                    v = float(r["concentration"].strip())
                except ValueError:
                    continue
                ym_values[ym].append(v)

    return {ym: sum(vs) / len(vs) for ym, vs in ym_values.items()}


# ---------- 氣象資料 ----------

def to_float_or_none(s):
    s = s.strip().strip('"')
    if s in ("", "--", "/", "X", "T"):
        return None
    try:
        return float(s)
    except ValueError:
        return None


def load_weather_monthly():
    """
    讀取 466920-年份.csv（CODiS臺北測站全項逐月年報表），回傳：
      {'2022-01': {'ws': 2.4, 'precp': 122.0}, ...}
    每份CSV第一列是中文欄位說明、第二列是英文代碼（ObsTime, WS, Precp, ...），
    從第三列開始才是資料。
    """
    files = sorted(glob.glob("466920-*.csv"))
    if not files:
        raise FileNotFoundError("找不到 466920-年份.csv 氣象資料，請確認檔案在同一層資料夾")

    result = {}
    for fp in files:
        year_match = re.search(r"-(\d{4})\.csv$", fp)
        year = year_match.group(1)
        with open(fp, encoding="utf-8-sig", newline="") as f:
            raw_reader = list(csv.reader(f))
        header = [h.strip().strip('"') for h in raw_reader[1]]  # 第二列是英文代碼
        for row in raw_reader[2:]:
            record = dict(zip(header, row))
            month = record.get("ObsTime", "").strip().strip('"')
            if not month:
                continue
            ym = f"{year}-{month}"
            ws = to_float_or_none(record.get("WS", ""))
            precp = to_float_or_none(record.get("Precp", ""))
            if ws is None and precp is None:
                continue  # 該月尚無資料（例如未來月份標示為 --）
            result[ym] = {"ws": ws, "precp": precp}
    return result


# ---------- 分析與繪圖 ----------

def scatter_with_trend(x, y, xlabel, ylabel, title, filename, color):
    x = np.array(x)
    y = np.array(y)
    r = np.corrcoef(x, y)[0, 1]
    slope, intercept = np.polyfit(x, y, 1)

    fig, ax = plt.subplots(figsize=(7.5, 6))
    ax.scatter(x, y, alpha=0.7, color=color, edgecolor="white", s=50)
    xs = np.linspace(x.min(), x.max(), 100)
    ax.plot(xs, slope * xs + intercept, color="#555555", linestyle="--", linewidth=1.5)
    ax.set_title(title, pad=16)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.annotate(f"r = {r:.3f}\nn = {len(x)}", xy=(0.03, 0.95), xycoords="axes fraction",
                va="top", fontsize=11,
                bbox=dict(boxstyle="round", fc="white", ec="gray", alpha=0.9))
    ax.grid(alpha=0.3)

    fig.tight_layout()
    fig.savefig(filename, dpi=150)
    plt.close(fig)
    print(f"已輸出 {filename}（r = {r:.3f}）")
    return r


def main():
    pm25_monthly = load_pm25_monthly_avg()
    weather_monthly = load_weather_monthly()

    common_yms = sorted(set(pm25_monthly) & set(weather_monthly))
    print(f"PM2.5資料共 {len(pm25_monthly)} 個月份，氣象資料共 {len(weather_monthly)} 個月份，"
          f"共同可比對月份：{len(common_yms)} 個")
    print(f"範圍：{common_yms[0]} ~ {common_yms[-1]}\n")

    print("節錄前3筆與後3筆合併後的資料：")
    for ym in common_yms[:3]:
        w = weather_monthly[ym]
        print(f"  {ym}：PM2.5={pm25_monthly[ym]:.1f}　風速={w['ws']}　降水量={w['precp']}")
    print("  ...")
    for ym in common_yms[-3:]:
        w = weather_monthly[ym]
        print(f"  {ym}：PM2.5={pm25_monthly[ym]:.1f}　風速={w['ws']}　降水量={w['precp']}")

    # 風速 vs PM2.5（排除風速缺值的月份）
    ws_yms = [ym for ym in common_yms if weather_monthly[ym]["ws"] is not None]
    pm25_for_ws = [pm25_monthly[ym] for ym in ws_yms]
    ws_values = [weather_monthly[ym]["ws"] for ym in ws_yms]
    print(f"\n【圖A】風速 vs PM2.5（n={len(ws_yms)}）")
    scatter_with_trend(ws_values, pm25_for_ws, "臺北站月平均風速（m/s）", "全臺PM2.5月平均濃度（μg/m3）",
                        "臺北站月平均風速 vs 全臺PM2.5月平均濃度", "wind_vs_pm25.png", "#4A90A4")

    # 降水量 vs PM2.5（排除降水量缺值的月份）
    precp_yms = [ym for ym in common_yms if weather_monthly[ym]["precp"] is not None]
    pm25_for_precp = [pm25_monthly[ym] for ym in precp_yms]
    precp_values = [weather_monthly[ym]["precp"] for ym in precp_yms]
    print(f"\n【圖B】降水量 vs PM2.5（n={len(precp_yms)}）")
    scatter_with_trend(precp_values, pm25_for_precp, "臺北站月降水量（mm）", "全臺PM2.5月平均濃度（μg/m3）",
                        "臺北站月降水量 vs 全臺PM2.5月平均濃度", "rain_vs_pm25.png", "#B5651D")


if __name__ == "__main__":
    main()
