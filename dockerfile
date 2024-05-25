FROM python:3.9

WORKDIR /app

RUN mkdir -p ./logs

RUN mkdir -p ./data

COPY main.py .

COPY requirements.txt .

COPY LICENSE .

RUN pip install --no-cache-dir -r requirements.txt

CMD ["python3", "main.py"]
