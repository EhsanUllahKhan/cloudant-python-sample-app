# Use a lightweight base image
FROM python:3.11-slim

# Set the working directory in the container
WORKDIR /app

# Copy only the requirements file to leverage Docker cache
COPY requirements.txt ./

# install requirements
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application files
COPY . .

# Make sure the script is executable
RUN chmod +x ./bin/run_app.sh

# Default command (optional; overridden by docker-compose.yml)
#CMD ["./bin/run_app.sh"]
