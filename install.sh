#!/bin/bash

# Clone the project repository
git clone https://github.com/ItsOrv/Telegram-Message-Monitor.git
cd Telegram-Message-Monitor

# Create the .env file if it doesn't exist
if [ ! -f .env ]; then
    echo "Creating .env file..."

    # Ask user for input and write to .env file
    read -p "Enter your API_ID: " api_id
    read -p "Enter your API_HASH: " api_hash
    read -p "Enter your BOT_TOKEN: " bot_token
    read -p "Enter your SESSION_NAME(anything): " session_name

    echo "API_ID=$api_id" > .env
    echo "API_HASH=$api_hash" >> .env
    echo "BOT_TOKEN=$bot_token" >> .env
    echo "SESSION_NAME=$session_name" >> .env

    echo ".env file created successfully."
else
    echo ".env file already exists."
fi

# Build and run the Docker container
docker-compose up --build -d

echo "Project setup complete and bot is running."
