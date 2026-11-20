FROM python:3.13-slim

WORKDIR /app
COPY . /app

EXPOSE 8080
CMD ["python3", "src/server.py", "--host", "0.0.0.0", "--port", "8080", "--no-browser"]
