FROM python:3.9-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
ENV ISO_DIR=/isos
VOLUME /isos
EXPOSE 8000
CMD ["python", "iso_server.py"]