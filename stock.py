import streamlit as st
import sqlite3

# DB接続（ファイル自動作成）
conn = sqlite3.connect("stock.db")
c = conn.cursor()

# テーブル作成
c.execute("""
CREATE TABLE IF NOT EXISTS stock (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    quantity INTEGER
)
""")
conn.commit()

st.title("在庫管理（最小版）")

# 追加
name = st.text_input("商品名")
qty = st.number_input("在庫数", min_value=0)

if st.button("追加"):
    c.execute("INSERT INTO stock (name, quantity) VALUES (?, ?)", (name, qty))
    conn.commit()
    st.success("追加完了")

# 表示
c.execute("SELECT * FROM stock")
rows = c.fetchall()

st.write("現在の在庫")
for r in rows:
    st.write(r)

import os
import pandas as pd

# 初回だけ実行
if not os.path.exists("initialized.flag"):
    df = pd.read_csv("data.csv")

    for _, row in df.iterrows():
        c.execute(
            "INSERT INTO stock (name, inner, thickness, quantity) VALUES (?, ?, ?, ?)",
            (row["name"], row["inner"], row["thickness"], row["quantity"])
        )

    conn.commit()

    # フラグ作成
    with open("initialized.flag", "w") as f:
        f.write("done")

    st.success("初期データ読み込み完了")

name = st.text_input("商品名")
inner = st.number_input("内径")
thickness = st.number_input("線径")
qty = st.number_input("在庫数", min_value=0)

if st.button("追加"):
    c.execute(
        "INSERT INTO stock (name, inner, thickness, quantity) VALUES (?, ?, ?, ?)",
        (name, inner, thickness, qty)
    )
    conn.commit()
    st.success("追加完了")

st.subheader("在庫使用")

c.execute("SELECT * FROM stock")
items = c.fetchall()

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
        conn.commit()

        st.success("在庫更新完了")
