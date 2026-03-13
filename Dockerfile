FROM python:3.10-slim-bullseye

WORKDIR /app
COPY requirements.txt .
RUN python3 -m pip install -r requirements.txt

COPY main.py .
COPY .env .
COPY message_tracker.pkl .
COPY telegram.session .
COPY telegram.session-journal .

CMD ["python", "-u", "main.py"]
