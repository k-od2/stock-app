import streamlit as st
import sqlite3
import pandas as pd
import os
from datetime import datetime

# ===== DBリセット（開発中だけ）=====
if os.path.exists("stock.db"):
    os.remove("stock.db")

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

# ===== CSV初期読み込み =====
if os.path.exists("data.csv"):
    df = pd.read_csv("data.csv")

    for _, row in df.iterrows():
        c.execute(
            "INSERT INTO stock (name, inner, thickness, quantity) VALUES (?, ?, ?, ?)",
            (row["name"], row["inner"], row["thickness"], row["quantity"])
        )

    conn.commit()

# ===== UI =====
st.title("在庫管理アプリ")

# =========================
# 商品追加
# =========================
st.subheader("商品追加")

name = st.text_input("商品名")
inner = st.number_input("内径(mm)")
thickness = st.number_input("線径(mm)")
qty = st.number_input("在庫数", min_value=0)

if st.button("追加"):
    c.execute(
        "INSERT INTO stock (name, inner, thickness, quantity) VALUES (?, ?, ?, ?)",
        (name, inner, thickness, qty)
    )
    conn.commit()
    st.success("追加完了")

# =========================
# 検索
# =========================
st.subheader("検索")

search_inner = st.number_input("内径検索", key="s_inner")
search_thick = st.number_input("線径検索", key="s_thick")

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

st.write("検索結果", result)

# =========================
# 在庫使用
# =========================
st.subheader("在庫使用")

c.execute("SELECT * FROM stock")
items = c.fetchall()

if items:
    selected = st.selectbox(
        "商品選択",
        items,
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

# =========================
# 履歴表示
# =========================
st.subheader("使用履歴")

c.execute("SELECT * FROM history ORDER BY date DESC")
history = c.fetchall()

for h in history:
    st.write(f"{h[3]} | {h[1]} を {h[2]}個使用")
