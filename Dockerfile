FROM python:3.9-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
ENV ISO_DIR=/isos
VOLUME /isos
EXPOSE 8000
ENV FLASK_APP=iso_server.py
CMD ["flask", "run", "--host=0.0.0.0", "--port=8000"]