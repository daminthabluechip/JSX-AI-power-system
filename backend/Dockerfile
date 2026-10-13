# Backend image: Flask API + OR-Tools optimizer.
FROM python:3.12-slim

WORKDIR /app
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 5000
# 1) apply database migrations, 2) start the API.
# One worker on purpose: the vehicle simulator keeps its clock in memory, so every request has to
# reach the same process. Threads handle concurrent requests and the background solver.
CMD ["sh", "-c", "flask --app wsgi db upgrade && gunicorn --bind 0.0.0.0:5000 --workers 1 --threads 8 --timeout 120 wsgi:app"]
