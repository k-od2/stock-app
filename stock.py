import streamlit as st
import sqlite3
import pandas as pd
import os
from datetime import datetime
    

# ===== DB接続 =====
conn = sqlite3.connect("stock.db", check_same_thread=False)
c = conn.cursor()

# ===== テーブル作成 =====
c.execute("""
CREATE TABLE IF NOT EXISTS stock (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    inner REAL,
    thickness REAL,
    quantity INTEGER
)
""")

c.execute("""
CREATE TABLE IF NOT EXISTS history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    used_qty INTEGER,
    date TEXT
)
""")

conn.commit()
# ===== CSV初期読み込み（1回だけ）=====
if os.path.exists("data.csv") and not os.path.exists("initialized.flag"):
    df = pd.read_csv("data.csv")

    for _, row in df.iterrows():
        c.execute(
            "INSERT INTO stock (name, inner, thickness, quantity) VALUES (?, ?, ?, ?)",
            (row["name"], row["inner"], row["thickness"], row["quantity"])
        )

    conn.commit()

    with open("initialized.flag", "w") as f:
        f.write("done")

    st.success("初期データ読み込み完了")
# ===== UI =====
st.title("在庫管理アプリ")

# =========================
# 🔍 検索（メイン）
# =========================
st.header("検索・使用")

search_inner = st.number_input("内径(mm)")
search_thick = st.number_input("線径(mm)")

c.execute("SELECT * FROM stock")
rows = c.fetchall()

# 完全一致
result = [
    r for r in rows
    if r[2] == search_inner and r[3] == search_thick
]

# なければ ±0.5
if not result:
    result = [
        r for r in rows
        if abs(r[2] - search_inner) <= 0.5
        and abs(r[3] - search_thick) <= 0.5
    ]

if result:
    st.write("候補")

    selected = st.selectbox(
        "商品選択",
        result,
        format_func=lambda x: f"{x[1]}（在庫:{x[4]}）"
    )

    use_qty = st.number_input("使用数", min_value=1, value=1)

    if st.button("使用する"):
        if selected[4] < use_qty:
            st.error("在庫不足")
        else:
            new_qty = selected[4] - use_qty

            c.execute(
                "UPDATE stock SET quantity=? WHERE id=?",
                (new_qty, selected[0])
            )

            # 履歴保存
            c.execute(
                "INSERT INTO history (name, used_qty, date) VALUES (?, ?, ?)",
                (selected[1], use_qty, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
            )

            conn.commit()
            st.success("在庫更新完了")

else:
    st.warning("該当なし（±0.5mmもなし）")

# =========================
# ➕ 商品追加（サブ）
# =========================
st.header("商品追加")

name = st.text_input("商品名", key="add_name")
inner = st.number_input("内径(mm)", key="add_inner")
thickness = st.number_input("線径(mm)", key="add_thick")
qty = st.number_input("在庫数", min_value=0, key="add_qty")

if st.button("追加"):
    c.execute(
        "INSERT INTO stock (name, inner, thickness, quantity) VALUES (?, ?, ?, ?)",
        (name, inner, thickness, qty)
    )
    conn.commit()
    st.success("追加完了")

# =========================
# 📜 履歴
# =========================
st.header("使用履歴")

c.execute("SELECT * FROM history ORDER BY date DESC")
history = c.fetchall()

for h in history:
    st.write(f"{h[3]} | {h[1]} を {h[2]}個使用")
