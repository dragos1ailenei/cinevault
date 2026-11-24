import random
import sqlite3
from urllib.parse import quote

import pandas as pd
import requests
import streamlit as st

st.set_page_config(page_title="CineVault · Watchlist & Recomandări", page_icon="🎬", layout="wide")
DB_FILE = "media.db"

# Stil CSS personalizat pentru carduri, postere si badge-uri
st.markdown("""
<style>
    .block-container { padding-top: 1.5rem; }
    img { border-radius: 10px; object-fit: cover; }
    .badge {
        display: inline-block;
        padding: 2px 10px;
        border-radius: 999px;
        font-size: 0.78rem;
        font-weight: 600;
        background: rgba(99, 102, 241, 0.18);
        color: #818cf8;
        margin-bottom: 4px;
    }
    .titlu-card {
        font-size: 1rem;
        font-weight: 700;
        margin: 4px 0 2px 0;
        line-height: 1.25;
    }
</style>
""", unsafe_allow_html=True)


# 1. Baza de date SQLite
def get_conn():
    return sqlite3.connect(DB_FILE)


def init_db():
    with get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS watchlist (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                titlu TEXT NOT NULL,
                tip TEXT NOT NULL,
                status TEXT NOT NULL,
                nota INTEGER DEFAULT 0,
                poster TEXT DEFAULT '',
                detalii TEXT DEFAULT '',
                link TEXT DEFAULT ''
            )
        """)
        if conn.execute("SELECT COUNT(*) FROM watchlist").fetchone()[0] == 0:
            exemple = [
                ("Interstellar", "Film", "Terminat", 5, "", "2014 · Matthew McConaughey, Anne Hathaway", "https://www.imdb.com/title/tt0816692/"),
                ("Breaking Bad", "Serial", "În curs", 5, "", "2008 · Bryan Cranston, Aaron Paul", "https://www.imdb.com/title/tt0903747/"),
                ("Dune: Part Two", "Film", "De văzut", 0, "", "2024 · Timothée Chalamet, Zendaya", "https://www.imdb.com/title/tt15239678/"),
                ("The Bear", "Serial", "De văzut", 0, "", "2022 · Jeremy Allen White", "https://www.imdb.com/title/tt14452776/"),
                ("Atomic Habits", "Carte", "De văzut", 0, "", "2018 · James Clear", "https://openlibrary.org"),
            ]
            conn.executemany(
                "INSERT INTO watchlist (titlu, tip, status, nota, poster, detalii, link) VALUES (?, ?, ?, ?, ?, ?, ?)",
                exemple,
            )


def adauga_in_watchlist(titlu, tip, status="De văzut", nota=0, poster="", detalii="", link=""):
    with get_conn() as conn:
        exista = conn.execute("SELECT id FROM watchlist WHERE LOWER(titlu) = LOWER(?)", (titlu,)).fetchone()
        if exista:
            return False
        conn.execute(
            "INSERT INTO watchlist (titlu, tip, status, nota, poster, detalii, link) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (titlu, tip, status, nota, poster, detalii, link),
        )
        return True


# 2. Preluare recomandari si cautare live din IMDb & Open Library
CATEGORII_IMDB = {
    "🔥 Populare & Noi": ["dune", "oppenheimer", "deadpool", "gladiator"],
    "🚀 Sci-Fi & Fantasy": ["interstellar", "matrix", "witcher", "stranger things"],
    "🕵️ Thriller & Crimă": ["breaking bad", "inception", "dark knight", "true detective"],
    "😂 Comedie & Acțiune": ["the office", "john wick", "boys", "brooklyn"],
}

CATEGORII_CARTI = {
    "🔥 Bestsellers": "bestseller fiction",
    "🧠 Dezvoltare & Psihologie": "psychology habits",
    "💻 Tehnologie & AI": "programming artificial intelligence",
    "🚀 Sci-Fi & Aventură": "science fiction dune",
}


def _interogheaza_imdb(termen: str):
    q = termen.strip()
    if not q:
        return []
    litera = q[0].lower() if q[0].isalnum() else "x"
    url = f"https://v3.sg.media-imdb.com/suggestion/{litera}/{quote(q.lower())}.json"
    try:
        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=5)
        r.raise_for_status()
        rezultate = []
        for item in r.json().get("d", []):
            imdb_id = item.get("id", "")
            if not imdb_id.startswith("tt"):
                continue
            qid = item.get("qid", "")
            tip = "Serial" if "tv" in qid.lower() else "Film"
            poster_raw = item.get("i", {}).get("imageUrl", "")
            poster = poster_raw.replace("._V1_.", "._V1_UX300_.") if poster_raw else ""
            detalii = f"{item.get('y', '')} · {item.get('s', '')}".strip(" ·")
            rezultate.append({
                "id": imdb_id,
                "titlu": item.get("l", "Fără titlu"),
                "tip": tip,
                "poster": poster,
                "detalii": detalii,
                "link": f"https://www.imdb.com/title/{imdb_id}/",
            })
        return rezultate
    except Exception:
        return []


@st.cache_data(ttl=3600)
def obtine_imdb(cautare: str, categorie: str):
    termeni = [cautare] if cautare.strip() else CATEGORII_IMDB[categorie]
    vazute = set()
    lista_finala = []
    for t in termeni:
        for item in _interogheaza_imdb(t):
            if item["id"] not in vazute:
                vazute.add(item["id"])
                lista_finala.append(item)
    return lista_finala[:16]


@st.cache_data(ttl=3600)
def obtine_carti(cautare: str, categorie: str):
    q = cautare.strip() if cautare.strip() else CATEGORII_CARTI[categorie]
    url = f"https://openlibrary.org/search.json?q={quote(q)}&limit=16"
    try:
        r = requests.get(url, timeout=5)
        r.raise_for_status()
        rezultate = []
        for doc in r.json().get("docs", [])[:16]:
            cover_id = doc.get("cover_i")
            poster = f"https://covers.openlibrary.org/b/id/{cover_id}-M.jpg" if cover_id else ""
            autori = ", ".join(doc.get("author_name", ["Autor necunoscut"])[:2])
            an = doc.get("first_publish_year", "")
            rezultate.append({
                "titlu": doc.get("title", "Fără titlu"),
                "tip": "Carte",
                "poster": poster,
                "detalii": f"{an} · {autori}".strip(" ·"),
                "link": f"https://openlibrary.org{doc.get('key', '')}",
            })
        return rezultate
    except Exception:
        return []


init_db()

with get_conn() as conn:
    df = pd.read_sql_query("SELECT * FROM watchlist ORDER BY id DESC", conn)

titluri_existente = {t.lower() for t in df["titlu"]}

# 3. Bara laterala: progres + selector aleatoriu "Ce vad azi?"
with st.sidebar:
    st.header("🎯 Progresul tău")
    total = len(df)
    terminate = int((df["status"] == "Terminat").sum())
    procent = int((terminate / total) * 100) if total > 0 else 0
    st.progress(procent, text=f"{terminate} din {total} finalizate ({procent}%)")

    st.divider()
    st.subheader("🎲 Nu știi ce să alegi?")
    de_vazut = df[df["status"] == "De văzut"]
    if st.button("Alege ceva aleatoriu", use_container_width=True, type="primary"):
        if de_vazut.empty:
            st.info("Nu ai niciun titlu cu statusul „De văzut”.")
        else:
            ales = de_vazut.iloc[random.randrange(len(de_vazut))]
            st.success(f"Recomandarea serii: **{ales['titlu']}** ({ales['tip']})")
            if ales["detalii"]:
                st.caption(ales["detalii"])

    st.divider()
    st.caption("Sursă date: IMDb & Open Library")
    st.caption("Stocare locală: SQLite (`media.db`)")

# 4. Header & KPI-uri
st.title("🎬 CineVault · Watchlist & Recomandări")
c1, c2, c3, c4 = st.columns(4)
c1.metric("Total în listă", total)
c2.metric("În curs", int((df["status"] == "În curs").sum()))
c3.metric("Terminate", terminate)
note_valide = df[df["nota"] > 0]["nota"]
c4.metric("Media notelor", f"{note_valide.mean():.1f} ⭐" if len(note_valide) > 0 else "—")

tab_rec, tab_lista, tab_stats, tab_manual = st.tabs([
    "🔥 Recomandări & Căutare IMDb",
    "📋 Watchlist-ul meu",
    "📊 Statistici",
    "➕ Adaugă manual",
])

# TAB 1: Recomandari bogate (16 carduri pe grila de 4 coloane)
with tab_rec:
    r1, r2 = st.columns([1, 2])
    sursa = r1.selectbox("Ce cauți?", ["🎬 Filme & Seriale (IMDb)", "📚 Cărți (Open Library)"])
    termen = r2.text_input("Caută orice titlu", placeholder="Scrie un nume (ex: Avatar, Oppenheimer, Harry Potter)...")

    if "IMDb" in sursa:
        cat_aleasa = st.radio("Categorii rapide:", list(CATEGORII_IMDB.keys()), horizontal=True)
        recomandari = obtine_imdb(termen, cat_aleasa)
    else:
        cat_aleasa = st.radio("Categorii rapide:", list(CATEGORII_CARTI.keys()), horizontal=True)
        recomandari = obtine_carti(termen, cat_aleasa)

    if not recomandari:
        st.warning("Nu s-au găsit rezultate. Încearcă alt titlu.")
    else:
        cols = st.columns(4)
        for idx, item in enumerate(recomandari):
            with cols[idx % 4]:
                with st.container(border=True):
                    if item["poster"]:
                        st.image(item["poster"], use_container_width=True)
                    else:
                        st.markdown("### 🎞️ Fără poster")
                    st.markdown(f"<span class='badge'>{item['tip']}</span>", unsafe_allow_html=True)
                    st.markdown(f"<div class='titlu-card'>{item['titlu']}</div>", unsafe_allow_html=True)
                    st.caption(item["detalii"] or "Detalii indisponibile")
                    if item["link"]:
                        st.markdown(f"[🔗 Pagină IMDb / Info]({item['link']})")

                    deja_in_lista = item["titlu"].lower() in titluri_existente
                    if deja_in_lista:
                        st.button("✅ În Watchlist", key=f"ok_{idx}_{item['titlu']}", disabled=True, use_container_width=True)
                    elif st.button("➕ Adaugă", key=f"add_{idx}_{item['titlu']}", use_container_width=True):
                        adauga_in_watchlist(
                            item["titlu"], item["tip"], "De văzut", 0, item["poster"], item["detalii"], item["link"]
                        )
                        st.toast(f"„{item['titlu']}” a fost adăugat!")
                        st.rerun()

# TAB 2: Watchlist-ul personal
with tab_lista:
    f1, f2, f3 = st.columns([1, 1, 2])
    filtru_tip = f1.selectbox("Tip", ["Toate", "Film", "Serial", "Carte"])
    filtru_status = f2.selectbox("Status", ["Toate", "De văzut", "În curs", "Terminat"])
    cautare_locala = f3.text_input("Filtrează lista ta", placeholder="Caută după titlu...")

    filtrat = df.copy()
    if filtru_tip != "Toate":
        filtrat = filtrat[filtrat["tip"] == filtru_tip]
    if filtru_status != "Toate":
        filtrat = filtrat[filtrat["status"] == filtru_status]
    if cautare_locala.strip():
        filtrat = filtrat[filtrat["titlu"].str.contains(cautare_locala.strip(), case=False, na=False)]

    if filtrat.empty:
        st.info("Nu există titluri pentru filtrele alese.")
    else:
        statusuri = ["De văzut", "În curs", "Terminat"]
        iconite = {"Film": "🎬", "Serial": "📺", "Carte": "📚"}

        for _, row in filtrat.iterrows():
            with st.container(border=True):
                col_img, col_info, col_st, col_nt, col_del = st.columns([1, 4, 2, 2, 1])
                with col_img:
                    if row["poster"]:
                        st.image(row["poster"], width=65)
                    else:
                        st.markdown(f"## {iconite.get(row['tip'], '🎬')}")
                with col_info:
                    st.markdown(f"**{row['titlu']}** · `{row['tip']}`")
                    if row["detalii"]:
                        st.caption(row["detalii"])
                    if row["link"]:
                        st.markdown(f"[Deschide pagina]({row['link']})")
                with col_st:
                    nou_status = st.selectbox(
                        "Status",
                        statusuri,
                        index=statusuri.index(row["status"]),
                        key=f"st_{row['id']}",
                        label_visibility="collapsed",
                    )
                    if nou_status != row["status"]:
                        with get_conn() as conn:
                            conn.execute("UPDATE watchlist SET status = ? WHERE id = ?", (nou_status, int(row["id"])))
                        st.rerun()
                with col_nt:
                    noua_nota = st.selectbox(
                        "Notă",
                        [0, 1, 2, 3, 4, 5],
                        index=int(row["nota"]),
                        format_func=lambda x: "Fără notă" if x == 0 else "⭐" * x,
                        key=f"nt_{row['id']}",
                        label_visibility="collapsed",
                    )
                    if noua_nota != int(row["nota"]):
                        with get_conn() as conn:
                            conn.execute("UPDATE watchlist SET nota = ? WHERE id = ?", (noua_nota, int(row["id"])))
                        st.rerun()
                with col_del:
                    if st.button("🗑️", key=f"del_{row['id']}", help="Șterge din listă"):
                        with get_conn() as conn:
                            conn.execute("DELETE FROM watchlist WHERE id = ?", (int(row["id"]),))
                        st.rerun()

        st.download_button(
            "📥 Exportă Watchlist (.csv)",
            data=filtrat.drop(columns=["poster"]).to_csv(index=False),
            file_name="watchlist.csv",
            mime="text/csv",
        )

# TAB 3: Statistici vizuale
with tab_stats:
    if df.empty:
        st.info("Adaugă câteva titluri pentru a genera statistici.")
    else:
        g1, g2 = st.columns(2)
        with g1:
            st.subheader("Distribuție pe categorii")
            st.bar_chart(df["tip"].value_counts())
        with g2:
            st.subheader("Distribuție pe status")
            st.bar_chart(df["status"].value_counts())

        top_notate = df[df["nota"] >= 4][["titlu", "tip", "nota", "detalii"]].sort_values(by="nota", ascending=False)
        if not top_notate.empty:
            st.subheader("🏆 Favoritele tale (4–5 stele)")
            st.dataframe(top_notate, hide_index=True, use_container_width=True)

# TAB 4: Adaugare manuala
with tab_manual:
    with st.form("form_manual", clear_on_submit=True):
        titlu_nou = st.text_input("Titlu *")
        m1, m2, m3 = st.columns(3)
        tip_nou = m1.selectbox("Tip", ["Film", "Serial", "Carte"])
        status_nou = m2.selectbox("Status", ["De văzut", "În curs", "Terminat"])
        nota_noua = m3.slider("Notă (0 = neevaluat)", 0, 5, 0)
        detalii_noi = st.text_input("Detalii (an, regizor, autor)", placeholder="ex: 2023 · Christopher Nolan")

        if st.form_submit_button("Salvează în Watchlist"):
            if not titlu_nou.strip():
                st.error("Introdu un titlu valid.")
            elif adauga_in_watchlist(titlu_nou.strip(), tip_nou, status_nou, nota_noua, "", detalii_noi.strip(), ""):
                st.success(f"„{titlu_nou}” a fost adăugat!")
                st.rerun()
            else:
                st.warning("Acest titlu există deja în listă.")