××××
# I haven’t finished the project yet. I’ll complete it soon when I have a bit more free time.
××××


# Telegram Chain Store Bot

This Telegram bot acts as a decentralized chain store with support for anonymous payments, product management, and a location-based delivery system.

## Features

### Role-Based System

* **Buyer**: Browse and purchase products, pay via wallet or direct payment.

* **Seller**: Add products, handle the first step of payment approval, and manage deliveries at random public locations in the destination city using a full-featured control keyboard.

* **Cardholder**: Manually verify payments and wallet top-ups. Share payment methods (bank card or wallet address) for user payouts and profits.

* **Admin**: Final payment approval, location and user management, and full system control.

### Secure Two-Step Payment Process

1. Buyer makes a payment.
2. Cardholder verifies the payment.
3. Admin confirms the payment.
4. Funds are released.

### Location-Based Delivery System

* Admin defines safe public drop-off locations per city.
* Sellers deliver products to the assigned locations.
* Buyers receive location details 15 minutes after drop-off.
* Delivery is validated using a secure code.

### Wallet System

* Users can top up their wallet.
* All wallet operations are protected with two-step verification.
* Secure balance management for every role.

### Security Features

* Manual two-step payment verification
* Delivery code validation
* Role-based access control
* Input validation and sanitization
* Error handling and logging
* API rate limiting

---

## Setup Instructions

### Prerequisites

* Python 3.8+
* MySQL or SQLite
* Redis (for caching and session management)

### Local Setup

1. Clone the repository:

```bash
git clone https://github.com/yourusername/telegram-chain-store.git
cd telegram-chain-store
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Configure environment variables:

```bash
cp .env.example .env
# Edit .env with your configuration
```

4. Run database migrations:

```bash
alembic upgrade head
```

5. Start the database manually (optional for SQLite):

```bash
python -m src.core.database
```

6. Run the bot:

```bash
python -m src.main
```

---

## Docker Setup

You can also run the bot using Docker for easier deployment.

### 1. Build and Run

```bash
docker-compose up --build
```

This will:

* Build the application image
* Start the database and Redis containers
* Start the bot service

### 2. Configuration

* Rename and configure the `.env` file:

```bash
cp .env.example .env
# Edit .env with your environment variables
```

### 3. Run Database Migrations

After containers are up, run:

```bash
docker exec -it <app_container_name> alembic upgrade head
```

(Replace `<app_container_name>` with your actual container name, usually something like `telegram-chain-store-app-1`)

