# Backend image: Flask API + OR-Tools optimizer.
FROM python:3.12-slim

WORKDIR /app
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 5000
# On start-up: 1) apply database migrations, 2) in demo mode make sure there are sample orders for today,
# 3) start the API on $PORT (hosts such as Render choose the port; 5000 when run locally).
# One worker on purpose: the vehicle simulator keeps its clock in memory, so every request has to
# reach the same process. Threads handle concurrent requests and the background solver.
CMD ["sh", "-c", "flask --app wsgi db upgrade && if [ \"$DEMO_MODE\" = \"true\" ]; then flask --app wsgi seed --demo; fi && gunicorn --bind 0.0.0.0:${PORT:-5000} --workers 1 --threads 8 --timeout 120 wsgi:app"]
