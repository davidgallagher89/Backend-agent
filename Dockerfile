# 1. Usiamo una base leggera di Python (Il Sistema Operativo)
FROM python:3.11-slim

# 2. Impostiamo la cartella di lavoro (La Cucina)
WORKDIR /app

# 3. Copiamo la lista della spesa dentro il container
COPY requirements.txt .

# 4. Installiamo le librerie ORA (durante la costruzione, non all'avvio!)
# Questa operazione verrà salvata nella cache e non ripetuta.
RUN pip install --no-cache-dir -r requirements.txt

# 5. Copiamo tutto il resto del codice
COPY . .

# 6. Diciamo al container quale comando lanciare quando si accende
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--reload"]