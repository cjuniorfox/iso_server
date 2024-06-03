FROM python:3.9-slim

# Set the working directory
WORKDIR /app

# Copy the requirements file and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install 7z and clean up apt cache
RUN apt-get update && \
    apt-get install -y p7zip-full && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* /var/cache/apt/archives/*

# Copy the application code
COPY . .

# Set environment variables
ENV ISO_DIR=/isos
ENV FLASK_APP=iso_server.py

# Create a volume for the ISO directory
VOLUME /isos

# Expose the application port
EXPOSE 8000

# Command to run the application
CMD ["flask", "run", "--host=0.0.0.0", "--port=8000"]