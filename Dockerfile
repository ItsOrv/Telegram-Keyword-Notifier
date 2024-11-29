# Use an official Python runtime as a parent image
FROM python:3.12

# Set the working directory
WORKDIR /usr/src/app

# Copy the requirements file and install dependencies
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY ./src ./src
COPY ./config.json ./src/config.json

# Copy the .env file (this will be generated during the installation)
COPY .env .env

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Command to run your application
CMD ["python", "./src/main.py"]
