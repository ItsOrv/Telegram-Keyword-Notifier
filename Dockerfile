# Use the official Python image.
FROM python:3.12.1

# Set the working directory inside the container
WORKDIR /app

# Copy the requirements file into the container
COPY requirements.txt .

# Install the dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the app's code
COPY . .

# Command to run the bot script
CMD ["python", "src/bot.py"]
