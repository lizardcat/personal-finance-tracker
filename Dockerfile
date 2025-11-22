FROM python:3.12

WORKDIR /app

COPY requirements.txt .

# Force pip to use binary wheels (don't build from source)
RUN pip install --no-cache-dir --only-binary=:all: -r requirements.txt

COPY . .

CMD ["python", "app.py"]