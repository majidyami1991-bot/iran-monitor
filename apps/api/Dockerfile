FROM python:3.12-slim
WORKDIR /app
COPY apps/api/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
COPY apps/api/main.py ./main.py
COPY apps/api/db_init.py ./db_init.py
COPY apps/api/import_db.py ./import_db.py
EXPOSE 3000
