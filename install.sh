#!/bin/bash

# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Update package lists and upgrade all packages without confirmation
echo "Updating system packages..."
sudo apt update -y && sudo apt upgrade -y

# Install Docker if it's not installed
if ! command_exists docker; then
    echo "Docker not found. Installing Docker..."
    sudo apt install -y apt-transport-https ca-certificates curl software-properties-common
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
    sudo apt update -y
    sudo apt install -y docker-ce docker-ce-cli containerd.io
    echo "Docker installed successfully."
else
    echo "Docker is already installed."
fi

# Install Docker Compose if it's not installed
if ! command_exists docker-compose; then
    echo "Docker Compose not found. Installing Docker Compose..."
    sudo curl -L "https://github.com/docker/compose/releases/download/v2.5.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    sudo chmod +x /usr/local/bin/docker-compose
    echo "Docker Compose installed successfully."
else
    echo "Docker Compose is already installed."
fi

# Clone the project repository
echo "Cloning the project repository..."
git clone https://github.com/ItsOrv/Telegram-Message-Monitor.git
cd Telegram-Message-Monitor

# Create the .env file if it doesn't exist
if [ ! -f .env ]; then
    echo "Creating .env file..."

    # Ask user for input and write to .env file
    read -p "Enter your API_ID: " api_id
    read -p "Enter your API_HASH: " api_hash
    read -p "Enter your BOT_TOKEN: " bot_token
    read -p "Enter your SESSION_NAME: " session_name

    echo "API_ID=$api_id" > .env
    echo "API_HASH=$api_hash" >> .env
    echo "BOT_TOKEN=$bot_token" >> .env
    echo "SESSION_NAME=$session_name" >> .env

    echo ".env file created successfully."
else
    echo ".env file already exists."
fi

# Build and run the Docker container
echo "Building and starting Docker container..."
docker-compose up --build -d

# Give some time for the container to start
echo "Waiting for the container to initialize..."
sleep 5

# Check if the bot container is running
container_status=$(docker ps --filter "name=telegram-bot" --format "{{.Status}}")
if [[ $container_status == *"Up"* ]]; then
    echo "Bot container is running successfully."
else
    echo "Bot container failed to start. Showing logs..."
    docker-compose logs
    exit 1
fi

# Attach to the container logs to see output (e.g., for inputting phone number and 2FA code)
echo "Attaching to bot container logs to input verification codes..."
docker-compose logs -f

