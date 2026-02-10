from sentence_transformers import SentenceTransformer
import numpy as np
from fastapi import FastAPI, Depends, HTTPException, status, Security
from fastapi.security import APIKeyHeader
from pydantic import BaseModel
import psycopg2
import os
import time
import re

# ==========================================
# CONFIGURAZIONE SICUREZZA (Richiesta dalla JD)
# ==========================================
# Password per l'ambiente di sviluppo (Fallback credentials)
API_KEY_SEGRETA = os.getenv("API_KEY_SEGRETA")
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

def get_api_key(api_key: str = Security(api_key_header)):
    """Verifica che l'utente abbia la chiave segreta."""
    if api_key == API_KEY_SEGRETA:
        return api_key
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Accesso Negato: Manca la API Key corretta (X-API-Key)."
    )

# ==========================================
# 1. IL CERVELLO AI (Embeddings)
# ==========================================
model = SentenceTransformer('all-MiniLM-L6-v2')

def genera_embedding(testo):
    return model.encode(testo).tolist()

#questa è una funzione di utilità che converte il testo in un vettore di embedding usando il modello di SentenceTransformer. 
# piu che altro perche è gratis e leggero da usare in locale 

# Inizializziamo l'app
# FastAPI è un framework web moderno e performante per costruire API in Python. Qui stiamo creando un'istanza dell'applicazione FastAPI con un titolo e una versione, che saranno visibili nella documentazione automatica generata da FastAPI (Swagger UI).

app = FastAPI(
    title="VREXX prima prova", version="1.0.0")

# ==========================================
# 2. CONNESSIONE AL DATABASE
# ==========================================
while True:
    try:
        conn = psycopg2.connect(os.getenv("DATABASE_URL"))
        cur = conn.cursor()
        print("Connesso al database con successo!")
        break
    except:
        print("Database non pronto... attendo 2 secondi")
        time.sleep(2)

# ==========================================
# 3. CREAZIONE TABELLE (Setup)
# ==========================================
cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")

# Tabella Immobili (Dati)
cur.execute("""
    CREATE TABLE IF NOT EXISTS immobili (
        id SERIAL PRIMARY KEY,
        indirizzo TEXT,
        prezzo FLOAT,
        descrizione TEXT,
        url_foto TEXT,
        url_video_360 TEXT,
        url_render TEXT,
        embedding vector(384)
    );
""")

# Tabella Log (Observability - Richiesto dalla JD)
cur.execute("""
    CREATE TABLE IF NOT EXISTS log_conversazioni (
        id SERIAL PRIMARY KEY,
        domanda_utente TEXT,
        risposta_agente TEXT,
        data_ora TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
""")
conn.commit()

# ==========================================
# 4. SCHEMI DATI
# ==========================================
class Messaggio(BaseModel):
    testo: str

class Immobile(BaseModel):
    indirizzo: str
    prezzo: float
    descrizione: str
    url_foto: str = "N/A"
    url_video_360: str = "N/A"
    url_render: str = "N/A"

# ==========================================
# 5. TOOLS (GLI ATTREZZI DELL'AGENTE)
# ==========================================
def tool_calcola_mutuo(importo: float, anni: int = 30, tasso: float = 3.5):
    """Calcola la rata mensile in modo deterministico (Matematica pura)."""
    n_rate = anni * 12
    tasso_mensile = (tasso / 100) / 12
    
    if tasso_mensile == 0:
        rata = importo / n_rate
    else:
        rata = importo * (tasso_mensile * (1 + tasso_mensile)**n_rate) / ((1 + tasso_mensile)**n_rate - 1)
        
    return f"Calcolo Mutuo VREXX: Per {importo}€ in {anni} anni (tasso {tasso}%), la rata è {rata:.2f}€/mese."

# ==========================================
# 6. API ENDPOINTS (LE ROTTE)
# ==========================================

@app.get("/")
def home():
    return {"status": "Online", "auth_required": True}

@app.post("/aggiungi-immobile", dependencies=[Depends(get_api_key)])
def aggiungi_immobile(immobile: Immobile):
    vettore = genera_embedding(immobile.descrizione)
    cur.execute("""
        INSERT INTO immobili (indirizzo, prezzo, descrizione, url_foto, url_video_360, url_render, embedding)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    """, (immobile.indirizzo, immobile.prezzo, immobile.descrizione, 
          immobile.url_foto, immobile.url_video_360, immobile.url_render, vettore))
    conn.commit()
    return {"status": "Immobile salvato con successo"}

@app.post("/chiedi-agente", dependencies=[Depends(get_api_key)])
def chiedi_agente(input_utente: Messaggio):
    prompt = input_utente.testo.lower()
    risposta = ""
    source_type = "" 

    # --- ROUTER INTELLIGENTE (Logica Agentica) ---
    # L'agente decide se chiamare un tool (calcolo mutuo) o fare una ricerca RAG (immobili) in base al contenuto della domanda.

    # Se la domanda contiene parole chiave come "mutuo", "rata" o "calcola", l'agente attiva il tool di calcolo mutuo. Altrimenti, procede con una ricerca RAG ibrida sugli immobili, cercando di estrarre un possibile budget dalla domanda per filtrare i risultati.
    
    # SCENARIO A: Calcolo Mutuo (Tool Calling)
    if "mutuo" in prompt or "rata" in prompt or "calcola" in prompt:
        
        # 1. Estrazione Numeri (Regex)
        numeri_trovati = [int(n) for n in re.findall(r'\d+', prompt)]
        
        # 2. Logica di Default
        importo_calcolo = 200000 
        anni_calcolo = 20
        
        # 3. Assegnazione Intelligente (Numero grande = prezzo, piccolo = anni)
        for n in numeri_trovati:
            if n > 100:
                importo_calcolo = n
            elif n > 0 and n < 100:
                anni_calcolo = n
        
        # 4. Esecuzione Tool
        risposta = tool_calcola_mutuo(importo=importo_calcolo, anni=anni_calcolo)
        source_type = f"TOOL: FinanceEngine (Input: {importo_calcolo} / {anni_calcolo})"

    # SCENARIO B: Ricerca Immobile (RAG Ibrido con Filtro Prezzo)
    else:
        vettore_domanda = genera_embedding(input_utente.testo)
        
        # 1. Analisi del Budget (Cerca numeri grandi nella frase)
        numeri_trovati = [int(n) for n in re.findall(r'\d+', prompt)]
        budget_massimo = None
        
        # Euristic: Se troviamo un numero > 10.000, assumiamo sia un budget (es. 200000)
        # Ignoriamo numeri piccoli (es. "3 stanze", "2 bagni")
        for n in numeri_trovati:
            if n > 10000:
                budget_massimo = n
                break
        
        # 2. Costruzione della Query Dinamica
        if budget_massimo:
            # CASO 1: L'utente ha dato un budget -> FILTRO RIGIDO (WHERE)
            # Questo è un approccio più restrittivo che garantisce di non superare il budget, ma potrebbe restituire risultati meno simili se il budget è troppo basso.
            print(f"DEBUG: Applico filtro budget <= {budget_massimo}€")
            cur.execute("""
                SELECT indirizzo, prezzo, descrizione 
                FROM immobili 
                WHERE prezzo <= %s 
                ORDER BY embedding <=> %s::vector 
                LIMIT 1
            """, (budget_massimo, vettore_domanda))
            source_type = f"RAG: Hybrid Search (Max {budget_massimo}€)"
        else:
            # CASO 2: Nessun budget -> SOLO RICERCA SEMANTICA PURA
            # Questo approccio massimizza la similarità semantica, ma potrebbe restituire risultati fuori budget se l'utente non specifica un limite.
            print("DEBUG: Nessun budget trovato, cerco solo per similarità")
            cur.execute("""
                SELECT indirizzo, prezzo, descrizione 
                FROM immobili 
                ORDER BY embedding <=> %s::vector 
                LIMIT 1
            """, (vettore_domanda,))
            source_type = "RAG: Semantic Search"
        
        casa = cur.fetchone()

        if casa:
            risposta = f"Ho trovato: {casa[0]} a {casa[1]}€. {casa[2]}"
        else:
            risposta = f"Non ho trovato immobili compatibili (Budget: {budget_massimo if budget_massimo else 'N/A'})."
            source_type = "FALLBACK"
    # --- LOGGING (Observability) ---
    try:
        cur.execute("INSERT INTO log_conversazioni (domanda_utente, risposta_agente) VALUES (%s, %s)", 
                    (input_utente.testo, f"[{source_type}] {risposta}"))
        conn.commit()
    except Exception as e:
        print(f"Errore Log: {e}")

        

    return {"risposta": risposta, "router_decision": source_type}

@app.get("/lista-immobili", dependencies=[Depends(get_api_key)])
def lista_immobili():
    # Recupera tutte le case (senza i vettori che sono illeggibili)
    cur.execute("SELECT id, indirizzo, prezzo, descrizione FROM immobili ORDER BY id DESC;")
    immobili = cur.fetchall()
    return {"totale": len(immobili), "dati": immobili}

# Endpoint per visualizzare i log delle conversazioni (Richiesto dalla JD)
# Questo endpoint è protetto da API Key e restituisce i log delle conversazioni in ordine cronologico inverso, mostrando la domanda dell'utente, la risposta dell'agente e la data/ora della conversazione.

@app.get("/visualizza-log", dependencies=[Depends(get_api_key)])
def visualizza_log():
    cur.execute("SELECT domanda_utente, risposta_agente, data_ora FROM log_conversazioni ORDER BY data_ora DESC;")
    logs = cur.fetchall()
    return {"logs": logs}