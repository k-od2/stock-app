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
    change_qty INTEGER,
    type TEXT,
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

    if name_query:
        name_match = normalize(name_query) in normalize(r[1])

    if type_query:
        type_match = r[1].upper().startswith(type_query)

    if search_inner:
        try:
            inner_val = float(search_inner)
            inner_match = abs(r[2] - inner_val) <= 0.5
        except:
            inner_match = False

    if search_thick:
        try:
            thick_val = float(search_thick)
            thick_match = abs(r[3] - thick_val) <= 0.5
        except:
            thick_match = False

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
        text = f"{x[1]}（在庫:{x[4]}）"

        if search_inner:
            try:
                diff = x[2] - float(search_inner)
                text += f" | 内径:{x[2]}mm ({diff:+.2f})"
            except:
                pass

        if search_thick:
            try:
                diff = x[3] - float(search_thick)
                text += f" | 線径:{x[3]}mm ({diff:+.2f})"
            except:
                pass

        return text

    selected = st.selectbox("商品選択", result, format_func=format_item)
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

            c.execute(
                "INSERT INTO history (name, change_qty, type, date) VALUES (?, ?, ?, ?)",
                (selected[1], -use_qty, "use", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
            )

            conn.commit()
            st.success("在庫更新完了")
            st.rerun()

else:
    st.warning("該当なし")

# =========================
# ➕ 商品追加（改良版）
# =========================
st.header("商品追加")

def normalize(text):
    return text.lower().replace("-", "").replace(" ", "")

name = st.text_input("商品名（例：s3 1a）", key="add_name")
qty = st.number_input("追加数", min_value=1, value=1, key="add_qty")

existing = None

if name:
    c.execute("SELECT * FROM stock")
    all_items = c.fetchall()

    for item in all_items:
        if normalize(item[1]) == normalize(name):
            existing = item
            break

# ===== 分岐 =====
if name:

    if existing:
        st.info(f"既存商品です → 現在在庫: {existing[4]}")

        if st.button("在庫に追加"):
            new_qty = existing[4] + qty

            c.execute(
                "UPDATE stock SET quantity=? WHERE id=?",
                (new_qty, existing[0])
            )

            c.execute(
                "INSERT INTO history (name, change_qty, type, date) VALUES (?, ?, ?, ?)",
                (existing[1], qty, "add", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
            )

            conn.commit()
            st.success("在庫を追加しました")
            st.rerun()

    else:
        st.warning("新規商品です → 寸法入力してください")

        inner = st.number_input("内径(mm)", key="new_inner")
        thickness = st.number_input("線径(mm)", key="new_thick")

        if st.button("新規登録"):
            if inner == 0 or thickness == 0:
                st.error("内径・線径は必須")
            else:
                c.execute(
                    "INSERT INTO stock (name, inner, thickness, quantity) VALUES (?, ?, ?, ?)",
                    (name, inner, thickness, qty)
                )

                c.execute(
                    "INSERT INTO history (name, change_qty, type, date) VALUES (?, ?, ?, ?)",
                    (name, qty, "add", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
                )

                conn.commit()
                st.success("新規追加しました")
                st.rerun()
# =========================
# 📜 履歴
# =========================
st.header("履歴")

c.execute("SELECT * FROM history ORDER BY date DESC")
history = c.fetchall()

for h in history:
    if h[3] == "use":
        st.write(f"{h[4]} | {h[1]} を {abs(h[2])}個使用")
    else:
        st.write(f"{h[4]} | {h[1]} を {h[2]}個追加")

c.execute("SELECT * FROM history ORDER BY date DESC")
history = c.fetchall()

for h in history:
    st.write(f"{h[3]} | {h[1]} を {h[2]}個使用")
