FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install 7z and clean up apt cache
RUN apt-get update && \
    apt-get install -y p7zip-full && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* /var/cache/apt/archives/*

COPY iso_server.py .

ENV ISO_DIR=/isos
ENV FLASK_APP=iso_server.py

VOLUME /isos

EXPOSE 8000

CMD ["flask", "run", "--host=0.0.0.0", "--port=8000"]