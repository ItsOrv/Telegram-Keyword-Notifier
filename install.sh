#!/bin/bash

# نصب نیازمندی‌ها و داکر
echo "Installing Docker and setting up environment..."

# Update package lists and install Docker
sudo apt update
sudo apt install -y docker.io docker-compose

# Get user inputs for environment variables
read -p "Enter your API_ID: " API_ID
read -p "Enter your API_HASH: " API_HASH
read -p "Enter your BOT_TOKEN: " BOT_TOKEN
read -p "Enter your CHANNEL_ID: " CHANNEL_ID

# Create the .env file
cat <<EOL > /opt/Telegram-Message-Monitor/.env
API_ID=${API_ID}
API_HASH=${API_HASH}
BOT_TOKEN=${BOT_TOKEN}
CHANNEL_ID=${CHANNEL_ID}
EOL

# Clone the project from GitHub if it doesn't exist
if [ ! -d "/opt/Telegram-Message-Monitor" ]; then
    git clone https://github.com/ItsOrv/Telegram-Message-Monitor /opt/Telegram-Message-Monitor
else
    echo "Project already cloned!"
fi

# Set up Docker container
cd /opt/Telegram-Message-Monitor
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
    echo "5. Exit"
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
    cd /opt/Telegram-Message-Monitor
    git pull origin main
    sudo docker-compose up -d --build
    echo "Project updated and container rebuilt."
}

# Main script
while true; do
    show_menu
    read choice
    case \$choice in
        1) start_container ;;
        2) stop_container ;;
        3) restart_container ;;
        4) update_project ;;
        5) echo "Exiting..."; exit 0 ;;
        *) echo "Invalid option, please try again." ;;
    esac
done
EOL

# Make the tmm command executable
sudo chmod +x /usr/local/bin/tmm

echo "Installation complete! Use 'tmm' to manage your container."
