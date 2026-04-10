import streamlit as st
import sqlite3
import pandas as pd
import os
from datetime import datetime
if os.path.exists("initialized.flag"):
    os.remove("initialized.flag")
# ===== 初回だけDBリセット（1回実行したら消す！）=====
#if os.path.exists("stock.db"):
    #os.remove("stock.db")

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
    user TEXT,
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
# 👤 使用者
# =========================
user = st.text_input("使用者名（必須）")

# =========================
# 🔍 検索・使用
# =========================
st.header("検索・使用")

name_query = st.text_input("商品名検索（例：s3）")
type_query = st.selectbox("型選択（任意）", ["", "P", "S", "G"])
search_inner = st.text_input("内径(mm)")
search_thick = st.text_input("線径(mm)")

c.execute("SELECT * FROM stock")
rows = c.fetchall()

def normalize(text):
    return text.lower().replace("-", "").replace(" ", "")

result = []

import re

result = []
seen = set()

for r in rows:
    name = r[1]

    name_match = True
    inner_match = True
    thick_match = True
    type_match = True

    # ===== 型（P,S,G）=====
    if type_query:
        type_match = name.upper().startswith(type_query)

    # ===== 商品名検索（ここ改良）=====
    if name_query:
        q = normalize(name_query)

        # 数字抽出（s5 → 5）
        q_num = re.findall(r'\d+', q)

        name_norm = normalize(name)
        name_num = re.findall(r'\d+', name_norm)

        # 型 + 数字一致のみ
        if q_num:
            name_match = (q_num[0] == name_num[0] if name_num else False)
        else:
            name_match = q in name_norm

    # ===== 内径 =====
    if search_inner:
        try:
            inner_val = float(search_inner)
            inner_match = abs(r[2] - inner_val) <= 0.5
        except:
            inner_match = False

    # ===== 線径 =====
    if search_thick:
        try:
            thick_val = float(search_thick)
            thick_match = abs(r[3] - thick_val) <= 0.5
        except:
            thick_match = False

    # ===== 条件 =====
    if search_inner and search_thick:
        ok = name_match and type_match and inner_match and thick_match
    else:
        ok = name_match and type_match and (inner_match or thick_match)

    # ===== 重複排除 =====
    key = (r[1], r[2], r[3])  # name, inner, thickness

    if ok and key not in seen:
        result.append(r)
        seen.add(key)
# ===== 表示 =====
def calc_distance(x):
    d = 0

    # 内径
    if search_inner:
        try:
            d += abs(x[2] - float(search_inner))
        except:
            pass

    # 線径
    if search_thick:
        try:
            d += abs(x[3] - float(search_thick))
        except:
            pass

    # 👇 これ追加（名前の数字距離）
    if name_query:
        import re
        q_num = re.findall(r'\d+', name_query)
        x_num = re.findall(r'\d+', x[1])

        if q_num and x_num:
            d += abs(int(q_num[0]) - int(x_num[0]))

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
        if not user:
            st.error("使用者名を入力してください")
        elif selected[4] < use_qty:
            st.error("在庫不足")
        else:
            new_qty = selected[4] - use_qty

            c.execute(
                "UPDATE stock SET quantity=? WHERE id=?",
                (new_qty, selected[0])
            )

            c.execute(
                "INSERT INTO history (name, change_qty, type, user, date) VALUES (?, ?, ?, ?, ?)",
                (selected[1], -use_qty, "use", user, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
            )

            conn.commit()
            st.success("在庫更新完了")
            st.rerun()

else:
    st.warning("該当なし")

# =========================
# ➕ 商品追加
# =========================
st.header("商品追加")

name = st.text_input("商品名（例：s31a）", key="add_name")

existing = None

if name:
    c.execute("SELECT * FROM stock")
    all_items = c.fetchall()

    for item in all_items:
        if normalize(name) in normalize(item[1]):
            existing = item
            break

if name:

    # ===== 既存 =====
    if existing:
        st.success(f"既存商品：{existing[1]}（在庫:{existing[4]}）")

        qty = st.number_input("追加数", min_value=1, value=1, key="add_qty_exist")

        if st.button("在庫に追加"):
            if not user:
                st.error("使用者名を入力してください")
            else:
                new_qty = existing[4] + qty

                c.execute(
                    "UPDATE stock SET quantity=? WHERE id=?",
                    (new_qty, existing[0])
                )

                c.execute(
                    "INSERT INTO history (name, change_qty, type, user, date) VALUES (?, ?, ?, ?, ?)",
                    (existing[1], qty, "add", user, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
                )

                conn.commit()
                st.success("在庫を追加しました")
                st.rerun()

    # ===== 新規 =====
    else:
        st.warning("新規商品です → 寸法入力")

        inner = st.number_input("内径(mm)", key="new_inner")
        thickness = st.number_input("線径(mm)", key="new_thick")
        qty = st.number_input("初期在庫", min_value=1, value=1, key="new_qty")

        if st.button("新規登録"):
            if not user:
                st.error("使用者名を入力してください")
            elif inner == 0 or thickness == 0:
                st.error("内径・線径は必須")
            else:
                c.execute(
                    "INSERT INTO stock (name, inner, thickness, quantity) VALUES (?, ?, ?, ?)",
                    (name, inner, thickness, qty)
                )

                c.execute(
                    "INSERT INTO history (name, change_qty, type, user, date) VALUES (?, ?, ?, ?, ?)",
                    (name, qty, "add", user, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
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
    name = h[1]
    qty = h[2]
    type_ = h[3]
    user_ = h[4]
    date_ = h[5]

    if type_ == "use":
        st.write(f"{date_} | {user_} が {name} を {abs(qty)}個使用")
    elif type_ == "add":
        st.write(f"{date_} | {user_} が {name} を {qty}個追加")
