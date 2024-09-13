#!/bin/bash

# Function to prompt for user input
prompt_for_input() {
    local prompt="$1"
    local default="$2"
    local input

    read -p "$prompt [$default]: " input
    echo "${input:-$default}"
}

# Install Docker and Docker Compose
echo "Installing Docker and setting up environment..."

# Update package lists and install Docker
sudo apt update && sudo apt upgrade -y
sudo apt install -y docker.io docker-compose

# Clone the project from GitHub
PROJECT_DIR="/opt/Telegram-Message-Monitor"

if [ ! -d "$PROJECT_DIR" ]; then
    sudo git clone https://github.com/ItsOrv/Telegram-Message-Monitor "$PROJECT_DIR"
else
    echo "Project already cloned!"
fi

# Navigate to the project directory
cd "$PROJECT_DIR" || { echo "Failed to navigate to $PROJECT_DIR"; exit 1; }

# Prompt for .env file inputs
API_ID=$(prompt_for_input "Enter your API_ID")
API_HASH=$(prompt_for_input "Enter your API_HASH")
BOT_TOKEN=$(prompt_for_input "Enter your BOT_TOKEN")
CHANNEL_ID=$(prompt_for_input "Enter your CHANNEL_ID")

# Create .env file
cat <<EOL > .env
API_ID=$API_ID
API_HASH=$API_HASH
BOT_TOKEN=$BOT_TOKEN
CHANNEL_ID=$CHANNEL_ID
EOL

# Set up Docker container
sudo docker-compose up -d --build

# Create the tmm command
cat <<EOL > /usr/local/bin/tmm
#!/bin/bash

# Function to show the menu
show_menu() {
    echo "1. Start container"
    echo "2. Stop container"
    echo "3. Restart container"
    echo "4. Update project from GitHub"
    echo "5. Uninstall project"
    echo "6. Exit"
    echo -n "Enter your choice: "
}

# Function to start the container
start_container() {
    sudo docker-compose -f /opt/Telegram-Message-Monitor/docker-compose.yml start
    echo "Container started."
}

# Function to stop the container
stop_container() {
    sudo docker-compose -f /opt/Telegram-Message-Monitor/docker-compose.yml stop
    echo "Container stopped."
}

# Function to restart the container
restart_container() {
    sudo docker-compose -f /opt/Telegram-Message-Monitor/docker-compose.yml restart
    echo "Container restarted."
}

# Function to update the project
update_project() {
    cd /opt/Telegram-Message-Monitor || { echo "Failed to navigate to /opt/Telegram-Message-Monitor"; exit 1; }
    git pull origin main
    sudo docker-compose up -d --build
    echo "Project updated and container rebuilt."
}

# Function to uninstall the project
uninstall_project() {
    echo "Stopping and removing Docker container..."
    sudo docker-compose -f /opt/Telegram-Message-Monitor/docker-compose.yml down
    echo "Removing project directory..."
    sudo rm -rf /opt/Telegram-Message-Monitor
    echo "Removing tmm command..."
    sudo rm /usr/local/bin/tmm
    echo "Uninstallation complete!"
}

# Main script
while true; do
    show_menu
    read -r choice
    case \$choice in
        1) start_container ;;
        2) stop_container ;;
        3) restart_container ;;
        4) update_project ;;
        5) uninstall_project ;;
        6) echo "Exiting..."; exit 0 ;;
        *) echo "Invalid option, please try again." ;;
    esac
done
EOL

# Make the tmm command executable
sudo chmod +x /usr/local/bin/tmm

echo "Installation complete! Use 'tmm' to manage your container."
