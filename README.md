# Backend Agent - Ricerca Immobiliare AI

Questo progetto è un Backend MVP (Minimum Viable Product) per la ricerca di immobili.
L'obiettivo è permettere all'utente di cercare casa usando il linguaggio naturale, combinando la precisione dei filtri classici con l'intelligenza artificiale.

## Tecnologie utilizzate

* Python 3.9
* FastAPI (Framework per le API)
* PostgreSQL con estensione pgvector (Database)
* Docker & Docker Compose (Per avviare tutto facilmente)

## Come funziona la ricerca

Il sistema utilizza un approccio "Ibrido" per trovare i risultati migliori:

1.  Filtro Prezzo: Prima di tutto, il database esclude le case che costano troppo (es. "massimo 200.000 euro").
2.  Ricerca Semantica: Sulle case rimanenti, calcola la vicinanza vettoriale per capire l'intento dell'utente (es. trovare case "luminose", "accoglienti" o "in centro").

Questo permette di avere risposte veloci e pertinenti.

## Istruzioni per l'avvio

Prerequisito: Avere Docker installato sul computer.

1.  Clona il repository:
    git clone https://github.com/davidgallagher89/Backend-agent.git

2.  Entra nella cartella e avvia i container:
    docker-compose up -d --build

3.  La documentazione delle API sarà disponibile all'indirizzo:
    http://localhost:8000/docs
