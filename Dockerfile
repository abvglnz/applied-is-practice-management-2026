FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY schema.sql ./schema.sql
COPY dist/seed.json ./dist/seed.json
COPY course_backend ./course_backend
ENV PRAKTIKA_DB=/app/data/praktika.sqlite3
EXPOSE 8000
CMD ["uvicorn", "course_backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
