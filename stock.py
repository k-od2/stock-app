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

name_query = st.text_input("商品名検索（例：s3）")
type_query = st.selectbox("型選択（任意）", ["", "P", "S", "G"])
search_inner = st.text_input("内径(mm) ※任意")
search_thick = st.text_input("線径(mm) ※任意")

c.execute("SELECT * FROM stock")
rows = c.fetchall()

def normalize(text):
    return text.lower().replace("-", "").replace(" ", "")

# ===== フィルタ =====
result = []

for r in rows:
    name_match = True
    inner_match = True
    thick_match = True
    type_match = True

    # 商品名
    if name_query:
        name_match = normalize(name_query) in normalize(r[1])

    # 型
    if type_query:
        type_match = r[1].upper().startswith(type_query)

    # 内径
    if search_inner:
        try:
            inner_val = float(search_inner)
            inner_match = abs(r[2] - inner_val) <= 0.5
        except:
            inner_match = False

    # 線径
    if search_thick:
        try:
            thick_val = float(search_thick)
            thick_match = abs(r[3] - thick_val) <= 0.5
        except:
            thick_match = False

    # 条件
    if search_inner and search_thick:
        if name_match and type_match and inner_match and thick_match:
            result.append(r)
    else:
        if name_match and type_match and (inner_match or thick_match):
            result.append(r)

# ===== 表示 =====
if result:

    def calc_distance(x):
        d = 0
        if search_inner:
            try:
                d += abs(x[2] - float(search_inner))
            except:
                pass
        if search_thick:
            try:
                d += abs(x[3] - float(search_thick))
            except:
                pass
        return d

    result.sort(key=calc_distance)

    def format_item(x):
        name = x[1]
        stock = x[4]
        inner_val = x[2]
        thick_val = x[3]

        text = f"{name}（在庫:{stock}）"

        if search_inner:
            try:
                diff_inner = inner_val - float(search_inner)
                text += f" | 内径:{inner_val}mm ({diff_inner:+.2f})"
            except:
                pass

        if search_thick:
            try:
                diff_thick = thick_val - float(search_thick)
                text += f" | 線径:{thick_val}mm ({diff_thick:+.2f})"
            except:
                pass

        try:
            if search_inner and search_thick:
                if diff_inner == 0 and diff_thick == 0:
                    text = "★ " + text
        except:
            pass

        return text

    selected = st.selectbox(
        "商品選択",
        result,
        format_func=format_item
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

            # 履歴
            c.execute(
                "INSERT INTO history (name, used_qty, date) VALUES (?, ?, ?)",
                (selected[1], use_qty, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
            )

            conn.commit()
            st.success("在庫更新完了")
            st.rerun()
else:
    st.warning("該当なし")

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

c.execute("SELECT * FROM history ORDER BY date DESC")
history = c.fetchall()

for h in history:
    st.write(f"{h[3]} | {h[1]} を {h[2]}個使用")
