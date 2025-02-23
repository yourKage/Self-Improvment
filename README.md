# SelfImprovementBot

SelfImprovementBot is a Telegram bot built with Python and the `aiogram` library to help users manage tasks, track daily activities (like bills and plans), and generate reports. It supports scheduling tasks, saving videos for tasks, searching tasks, and tracking financial transactions in a "Bills" topic, all while running in Tashkent timezone (+05:00).

## Table of Contents
- [Features](#features)
- [Requirements](#requirements)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
  - [Commands](#commands)
  - [Topics](#topics)
- [Development](#development)
- [Contributing](#contributing)
- [License](#license)

## Features
- **Task Scheduling**: Schedule tasks in the "Plans" topic using the format "Task: HH:MM" (e.g., "Breakfast: 22:26").
- **Task Completion with Videos**: Mark tasks as completed in the "Today's Results" topic by sending a video within 40 minutes of the reminder, or save videos for unscheduled tasks.
- **Task Search**: Search for tasks by name, time, or date using the `/search` command.
- **Bills Tracking**: Track daily income, expenses, and additions in the "Bills" topic using specific formats (e.g., `100` for morning allowance, `-number: description` for expenses, `+number: reason` for additions).
- **Daily Bills Report**: Generate an on-demand or automatic (at 10:00 PM) report of daily financial transactions, including income, expenses, balance, and productivity compared to the previous day.
- **Weekly Task Report**: Generate a weekly report of task response times using a line chart.
- **Timezone Support**: Operates in Tashkent timezone (+05:00) for all scheduling and reporting.

## Requirements
- Python 3.10 or higher
- `aiogram` (version 2.25.1)
- `pytz` for timezone handling
- `matplotlib` for generating charts in weekly reports
- `sqlite3` (included in Python standard library)
- A Telegram bot token from @BotFather

## Installation

### 1. Clone the Repository
```bash
git clone https://github.com/yourKage/Self-Improvment
cd Self-Improvment
```

### 2. Create a Virtual Environment
```bash
python -m venv venv
source venv/bin/activate  # On Windows use `venv\Scripts\activate`
```

### 3. Install Dependencies
```bash
pip install aiogram==2.25.1 pytz matplotlib
```

### 4. Set Up Configuration
Create a `config.py` file in the project root with your Telegram bot token:
```python
TOKEN = "YOUR_BOT_TOKEN_HERE"  # Replace with your Telegram bot token from @BotFather
DB_NAME = "selfimprovement.db"  # SQLite database file name
```
Replace `YOUR_BOT_TOKEN_HERE` with the token you received from @BotFather.

### 5. Initialize the Database
Run the `database_creation.py` script to create the necessary SQLite tables:
```bash
python database_creation.py
```
This will create `tasks` and `bills` tables in `selfimprovement.db`.

## Configuration
Ensure `config.py` is correctly configured with your `TOKEN` and `DB_NAME`.
The bot uses Tashkent timezone (+05:00) by default. If you need a different timezone, modify `TASHKENT_TZ = pytz.timezone("Asia/Tashkent")` in `main.py`.

## Usage

### Commands
- `/report`:
  - In the "Bills" topic (ID 3): Generates a daily bills report on demand.
  - In other topics: Generates a weekly task response time report.
- `/search`: Prompts for a search query to find tasks by name, time, or date (e.g., "Workout", "2025-02-18", or "Workout:17:00").

### Topics
The bot operates in specific Telegram topics (forum channels) identified by thread IDs:

- **Plans (ID 5)**: Send tasks in the format `Task: HH:MM` (e.g., `Breakfast: 22:26`) to schedule them. The bot will save and schedule reminders for these tasks.
- **Today's Results (ID 6)**: Respond to task reminders with a video to mark tasks as completed within 40 minutes, or save videos for unscheduled tasks using `TaskName: HH:MM`.
- **Bills (ID 3)**: Track financial transactions:
  - Send `100` each morning for a $100 allowance from parents.
  - Send `-number: description` (e.g., `-50: Coffee`) for expenses.
  - Send `+number: reason` (e.g., `+20: Freelance work`) for additional income.
  - Use `/report` to generate a daily report of income, expenses, balance, and productivity compared to yesterday. An automatic report is sent at 10:00 PM daily.

### Example Workflow
#### Schedule a Task:
1. In the "Plans" topic (ID 5), send: `Breakfast: 22:26`
2. The bot responds: `✅ Task saved and scheduled.`
3. At `22:26` Tashkent time, the bot sends a reminder in the "Today's Results" topic.

#### Complete a Task:
1. In the "Today's Results" topic (ID 6), send a video within 40 minutes of the reminder.
2. The bot responds: `✅ Task marked as completed!\n📹 Video saved: [View Video](link)`

#### Track Bills:
1. In the "Bills" topic (ID 3), send: `100` (morning allowance).
2. Send `-50: Coffee` for an expense or `+20: Freelance work` for additional income.
3. Use `/report` to get:
```text
💰 **Daily Bills Report for 2025-02-23**
🌞 Income Today: $120.00
💸 Expenses Today: $50.00
💵 Balance Left: $70.00
📊 Productivity Compared to Yesterday: more productive

🔍 **Today’s Transactions:**
- Income: $100.00 at 08:00 - Daily allowance from parents
- Expense: $50.00 at HH:MM - Coffee
- Addition: $20.00 at HH:MM - Freelance work
```

#### Search Tasks:
1. Send `/search` in any topic, then enter a query like "Breakfast" or "2025-02-23".
2. The bot responds with matching tasks or details.

## Development
- Run the bot locally:
```bash
python main.py
```
- Use a Telegram client to interact with the bot in the specified topics.
- Debug logs are printed to the console; check them for issues.

## Contributing
Contributions are welcome! Please fork the repository, make changes, and submit a pull request. Ensure you follow the coding style and add tests where applicable.

## License
This project is licensed under the MIT License. See the `LICENSE` file for details.