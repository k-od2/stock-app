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