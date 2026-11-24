# 🎬 CineVault – Watchlist Filme, Seriale & Cărți

Aplicație web interactivă dezvoltată în **Python** și **Streamlit** pentru gestionarea listei personale de filme, seriale și cărți, cu căutare live și recomandări preluate automat din **IMDb** și **Open Library**.

## ✨ Funcționalități principale

- **Recomandări & Căutare live (fără cheie API):** preia postere, an de apariție, actori/autori și link-uri directe din IMDb (filme/seriale) și Open Library (cărți), organizate pe categorii rapide.
- **Watchlist personal cu stocare locală (`SQLite`):** salvare persistentă în `media.db`, filtrare după tip/status/titlu, actualizare rapidă a statusului (*De văzut*, *În curs*, *Terminat*) și acordare de note (1–5 stele).
- **Asistent de decizie („🎲 Ce văd / citesc azi?”):** bară laterală cu bară de progres și selector aleatoriu din titlurile neîncepute.
- **Statistici & Export:** grafice automate pe categorii și statusuri, topul titlurilor preferate (4–5 stele) și descărcare în format `.csv`.

## 🛠️ Tehnologii utilizate

- **Python 3**
- **Streamlit** – interfață web interactivă și componente vizuale
- **SQLite3** – bază de date relațională locală
- **Pandas** – filtrare, agregare metrici și export CSV
- **Requests** – interogarea endpoint-urilor publice IMDb și Open Library

## 📁 Structura proiectului

```text
cinevault/
├── watchlist.py       # Codul complet al aplicației
├── requirements.txt   # Dependențele Python necesare
├── .gitignore         # Excludere fișiere locale/temporare din Git
└── README.md          # Documentația proiectului
```

## 🚀 Instalare și rulare locală

1. **Clonează repository-ul sau descarcă fișierele:**
   ```powershell
   git clone https://github.com/<username>/cinevault.git
   cd cinevault
   ```

2. **Instalează dependențele:**
   ```powershell
   python -m pip install -r requirements.txt
   ```

3. **Pornește aplicația:**
   ```powershell
   python -m streamlit run watchlist.py
   ```

Aplicația se va deschide automat în browser la `http://localhost:8501`.

## ⚙️ Cum funcționează pe scurt

- La prima pornire, funcția `init_db()` creează automat baza de date `media.db` și inserează un set inițial de exemple. Toate operațiile SQL folosesc interogări parametrizate (`?`) pentru prevenirea SQL Injection.
- Rezultatele din IMDb și Open Library sunt memorate temporar prin `@st.cache_data(ttl=3600)` pentru răspuns instant și evitarea cererilor repetate.