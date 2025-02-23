# main.py
import sqlite3
import asyncio
import pytz
import io
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types
from aiogram.types import Message, InputFile, InlineKeyboardButton, InlineKeyboardMarkup
from config import TOKEN, DB_NAME
from database_creation import init_db
from database_actions import (
    save_task, get_pending_tasks, mark_task_missed, mark_task_completed, 
    get_latest_pending_task_id, get_daily_response_times, save_task_video, get_task_statistics
)
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.contrib.fsm_storage.memory import MemoryStorage

storage = MemoryStorage()

class TaskVideoState(StatesGroup):
    waiting_for_task_name = State()

class SearchState(StatesGroup):
    waiting_for_query = State()
    showing_results = State()  # State to store search results for callback handling

# Initialize timezone and bot
TASHKENT_TZ = pytz.timezone("Asia/Tashkent")
bot = Bot(token=TOKEN)
dp = Dispatcher(bot, storage=storage)

# Initialize database
init_db()

# Thread IDs
THIRD_ID = 3  # Bills topic ID
TOPIC_ID_PLANS = 5
TOPIC_ID_TODAYS_RESULTS = 6
waiting_for_task = {}

# Global variable to store startup time
startup_time = datetime.now(TASHKENT_TZ)

def parse_task_message(message_text):
    tasks = []
    print(f"Parsing message: {message_text}")  # Debug: Log the input message
    for line in message_text.split("\n"):
        if ":" in line:
            try:
                task, time = line.split(":", 1)
                # Ensure time is in HH:MM format
                datetime.strptime(time.strip(), "%H:%M")
                tasks.append((task.strip(), time.strip()))
            except ValueError as e:
                print(f"Error parsing line '{line}': {str(e)}")  # Debug: Log parsing errors
                continue
    tasks.sort(key=lambda x: datetime.strptime(x[1], "%H:%M"))
    return tasks

# Database functions for bills
def save_bill(date, bill_type, amount, description, time):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO bills (date, type, amount, description, time) 
        VALUES (?, ?, ?, ?, ?)
    """, (date, bill_type, amount, description, time))
    conn.commit()
    conn.close()

def get_daily_bills(date):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT type, amount, description, time 
        FROM bills 
        WHERE date = ? 
        ORDER BY time
    """, (date,))
    results = cursor.fetchall()
    conn.close()
    return results

def get_yesterday_bills():
    yesterday = (datetime.now(TASHKENT_TZ).date() - timedelta(days=1)).isoformat()
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT type, amount, description, time 
        FROM bills 
        WHERE date = ? 
        ORDER BY time
    """, (yesterday,))
    results = cursor.fetchall()
    conn.close()
    return results

@dp.message_handler(lambda message: message.message_thread_id == TOPIC_ID_PLANS)
async def handle_task_message(message: Message):
    print(f"Received message in thread {message.message_thread_id}: {message.text}")  # Debug: Log the message
    try:
        tasks = parse_task_message(message.text)
        if not tasks:
            await message.reply("❌ No valid tasks found. Use format: Task: HH:MM")
            return
        
        for task, time in tasks:
            save_task(task, time)
        await message.reply("✅ Tasks saved and scheduled.")
    except Exception as e:
        print(f"Error in handle_task_message: {str(e)}")  # Debug: Log any errors
        await message.reply(f"❌ Error saving tasks: {str(e)}")

@dp.message_handler(lambda message: message.text.startswith('/report') and message.message_thread_id == THIRD_ID)
async def handle_bills_report_command(message: Message):
    print('handle_bills_report_command')
    await message.reply(
        text="📊 Generating Daily Bills Report...",  # Positional argument first (or explicitly as keyword)
        reply_markup=None  # Keyword argument after
    )
    await generate_daily_bills_report(message.chat.id)

@dp.message_handler(commands=["report"])
async def handle_report_command(message: Message):
    await message.reply("📊 Generating Weekly Report...")
    await generate_weekly_report(message.chat.id)

@dp.message_handler(commands=["search"])
async def handle_search_command(message: types.Message):
    await message.reply("🔍 Please enter your search query (e.g., 'Workout', '2025-02-18', or 'Workout:17:00'):")
    await SearchState.waiting_for_query.set()

@dp.message_handler(state=SearchState.waiting_for_query)
async def process_search_query(message: types.Message, state: FSMContext):
    query = message.text.strip()
    results = search_tasks(query)
    
    if not results:
        await message.reply("⚠ No matching tasks found.")
        await state.finish()
        return
    
    # Format the list of results
    formatted_results = format_search_results(results, query)
    full_text = f"📋 Search results for '{query}':\n{formatted_results}"
    
    if len(results) == 1:
        task_info = format_task_info(results[0])
        await message.reply(task_info)
        await state.finish()
        return
    
    # Store results in state for callback handling and send a new bot message with inline buttons
    await state.update_data(results=results)
    await state.set_state(SearchState.showing_results)
    
    # Create inline keyboard with numbered buttons
    keyboard = InlineKeyboardMarkup(row_width=1)
    buttons = [InlineKeyboardButton(text=str(i + 1), callback_data=str(i)) for i in range(len(results))]
    keyboard.inline_keyboard = [buttons]
    
    # Send a new message with the results and buttons (ensure correct argument order)
    sent_message = await message.answer(
        text=f"{full_text}\n\n📋 Multiple results found. Select a number to view details:",  # Positional argument first
        reply_markup=keyboard  # Keyword argument after
    )
    
    # Store the bot's message ID in state for potential future edits
    await state.update_data(message_id=sent_message.message_id)

@dp.callback_query_handler(state=SearchState.showing_results)
async def process_search_result(callback_query: types.CallbackQuery, state: FSMContext):
    user_data = await state.get_data()
    results = user_data.get('results', [])
    message_id = user_data.get('message_id')
    
    try:
        index = int(callback_query.data)
        if 0 <= index < len(results):
            task_info = format_task_info(results[index])
            await bot.send_message(callback_query.message.chat.id, task_info)
        else:
            await bot.send_message(callback_query.message.chat.id, "⚠ Invalid selection.")
    except ValueError:
        await bot.send_message(callback_query.message.chat.id, "⚠ Invalid selection.")
    
    await bot.answer_callback_query(callback_query.id)
    await state.finish()

def search_tasks(query):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # Handle different query formats
    if ':' in query:  # Format: ActivityName:HH:MM
        try:
            task_name, time = query.split(':', 1)
            task_name = task_name.strip()
            time = time.strip()
            datetime.strptime(time, "%H:%M")
            cursor.execute("""
                SELECT id, task, time, status, notified_at, video_id, completed_at 
                FROM tasks 
                WHERE task LIKE ? AND time = ? 
                ORDER BY notified_at DESC
            """, (f"%{task_name}%", time))
        except ValueError:
            cursor.execute("""
                SELECT id, task, time, status, notified_at, video_id, completed_at 
                FROM tasks 
                WHERE task LIKE ? 
                ORDER BY notified_at DESC
            """, (f"%{query}%",))
    elif '-' in query and len(query.split('-')) == 3:  # Format: YYYY-MM-DD
        try:
            datetime.strptime(query, "%Y-%m-%d")
            cursor.execute("""
                SELECT id, task, time, status, notified_at, video_id, completed_at 
                FROM tasks 
                WHERE date(notified_at) = ? 
                ORDER BY notified_at DESC
            """, (query,))
        except ValueError:
            cursor.execute("""
                SELECT id, task, time, status, notified_at, video_id, completed_at 
                FROM tasks 
                WHERE task LIKE ? 
                ORDER BY notified_at DESC
            """, (f"%{query}%",))
    else:  # Search by activity name only
        cursor.execute("""
            SELECT id, task, time, status, notified_at, video_id, completed_at 
            FROM tasks 
            WHERE task LIKE ? 
            ORDER BY notified_at DESC
        """, (f"%{query}%",))
    
    results = cursor.fetchall()
    conn.close()
    return results

def format_task_info(task):
    task_id, task_name, task_time, status, notified_at, video_id, completed_at = task
    # Convert timezone from +04:37 to +05:00 (Tashkent)
    notified = datetime.fromisoformat(notified_at.replace("+04:37", "+05:00")).astimezone(TASHKENT_TZ).strftime("%Y-%m-%d %H:%M")
    completed = datetime.fromisoformat(completed_at.replace("+04:37", "+05:00")).astimezone(TASHKENT_TZ).strftime("%Y-%m-%d %H:%M") if completed_at else "Not completed"
    video_link = f"https://t.me/c/2265534780/6/{video_id}" if video_id else "No video available"
    
    return (
        f"📋 **Task Details**\n"
        f"ID: {task_id}\n"
        f"Activity: {task_name}\n"
        f"Time: {task_time}\n"
        f"Status: {status}\n"
        f"Notified At: {notified}\n"
        f"Completed At: {completed}\n"
        f"Video Link: {video_link}"
    )

def format_search_results(results, query):
    if '-' in query and len(query.split('-')) == 3:  # Date search (YYYY-MM-DD)
        return "\n".join([f"{task[1]}: {datetime.fromisoformat(task[4].replace('+04:37', '+05:00')).astimezone(TASHKENT_TZ).strftime('%Y-%m-%d %H:%M')}" for task in results])
    else:  # Activity name or activity:time search
        return "\n".join([f"{task[1]}: {datetime.fromisoformat(task[4].replace('+04:37', '+05:00')).astimezone(TASHKENT_TZ).strftime('%Y-%m-%d %H:%M')}" for task in results])

@dp.message_handler(content_types=types.ContentType.VIDEO)
async def handle_video_message(message: Message, state: FSMContext):
    if message.message_thread_id != TOPIC_ID_TODAYS_RESULTS:
        return

    task_id = get_latest_pending_task_id()
    if task_id:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("SELECT time, notified_at FROM tasks WHERE id = ?", (task_id,))
        result = cursor.fetchone()
        conn.close()

        if result and result[1]:
            scheduled_time, notified_at = result
            notified_time = datetime.fromisoformat(notified_at.replace("+04:37", "+05:00")).astimezone(TASHKENT_TZ)
            now = datetime.now(TASHKENT_TZ)
            time_diff = (now - notified_time).total_seconds()

            if time_diff <= 2400:
                chat_id = message.chat.id
                message_id = message.message_id

                # Generate public link
                public_link = f"https://t.me/c/{abs(chat_id)}/{message_id}"
                print(public_link)

                # Save video ID and mark task completed
                video_id = message.video.file_id
                mark_task_completed(task_id, video_id, now.strftime("%H:%M"))

                await message.reply(f"✅ Task marked as completed!\n📹 Video saved: [View Video]({public_link})", parse_mode="Markdown")
            else:
                await message.reply("⚠ This task's 40-minute response window has expired.")
        else:
            await message.reply("⚠ No pending task found.")
    else:
        waiting_for_task[message.from_user.id] = message.video.file_id
        await state.set_state(TaskVideoState.waiting_for_task_name)
        await message.reply("❓ What is this video for? Use format: TaskName: HH:MM")

@dp.message_handler(state=TaskVideoState.waiting_for_task_name)
async def process_task_name(message: Message, state: FSMContext):
    if ":" in message.text:
        parts = message.text.split(":", 1)  # Split only at the first colon
        if len(parts) == 2:
            task_name = parts[0].strip()
            task_time = parts[1].strip()

            if len(task_time) == 5 and task_time[2] == ":" and task_time.replace(":", "").isdigit():
                video_id = waiting_for_task.get(message.from_user.id)
                if video_id:
                    now = datetime.now(TASHKENT_TZ)
                    save_task_video(task_name, now.strftime("%H:%M"), message.message_id, now.strftime("%H:%M"))
                    del waiting_for_task[message.from_user.id]
                    await state.finish()
                    await message.reply(f"✅ Task '{task_name}' at {task_time} saved with video.")
                else:
                    await message.reply("⚠ No video found for this task.")
            else:
                await message.reply("⚠ Invalid time format. Use: HH:MM")
        else:
            await message.reply("⚠ Invalid format. Use: TaskName: HH:MM")
    else:
        await message.reply("⚠ Invalid format. Use: TaskName: HH:MM")

async def task_scheduler():
    while True:
        now = datetime.now(TASHKENT_TZ).strftime("%H:%M")
        tasks = get_pending_tasks()
        
        for task in tasks:
            task_id, task_text, task_time, notified_at = task
            if task_time == now and not notified_at:
                current_time = datetime.now(TASHKENT_TZ).isoformat()
                await bot.send_message(
                    chat_id=-1002265534780,
                    text=f"Reminder: {task_text} - Please complete it!",
                    message_thread_id=TOPIC_ID_TODAYS_RESULTS
                )
                
                conn = sqlite3.connect(DB_NAME)
                cursor = conn.cursor()
                cursor.execute("UPDATE tasks SET notified_at = ? WHERE id = ?", (current_time, task_id))
                conn.commit()
                conn.close()
                
                await asyncio.sleep(2400)
                if get_latest_pending_task_id() == task_id:  # Check if still pending
                    mark_task_missed(task_id)
                    await bot.send_message(
                        chat_id=-1002265534780,
                        text=f"❌ Task missed: {task_text}",
                        message_thread_id=TOPIC_ID_TODAYS_RESULTS
                    )
        
        await asyncio.sleep(30)

async def daily_bills_report_scheduler():
    while True:
        now = datetime.now(TASHKENT_TZ)
        # Check if it's 10:00 PM (22:00) each day
        if now.hour == 22 and now.minute == 0:
            await generate_daily_bills_report(-1002265534780)  # Send to the same chat as task reminders
        
        # Wait until 10:00 PM tomorrow or the next minute if past 10:00 PM today
        next_check = now.replace(hour=22, minute=0, second=0, microsecond=0)
        if now > next_check:
            next_check += timedelta(days=1)
        wait_time = (next_check - now).total_seconds()
        await asyncio.sleep(wait_time)

async def generate_daily_bills_report(chat_id):
    today = datetime.now(TASHKENT_TZ).date().isoformat()
    yesterday = (datetime.now(TASHKENT_TZ).date() - timedelta(days=1)).isoformat()
    
    # Get today's bills
    today_bills = get_daily_bills(today)
    yesterday_bills = get_yesterday_bills()
    
    if not today_bills:
        await bot.send_message(chat_id, "⚠ No bill transactions recorded for today.")
        return
    
    # Calculate today's totals
    today_income = sum(amount for _, amount, _, _ in today_bills if amount > 0)
    today_expenses = sum(abs(amount) for _, amount, _, _ in today_bills if amount < 0)
    today_balance = today_income - today_expenses
    
    # Calculate yesterday's totals (if any)
    yesterday_income = sum(amount for _, amount, _, _ in yesterday_bills if amount > 0) if yesterday_bills else 0
    yesterday_expenses = sum(abs(amount) for _, amount, _, _ in yesterday_bills if amount < 0) if yesterday_bills else 0
    yesterday_balance = yesterday_income - yesterday_expenses if yesterday_bills else 0
    
    # Determine productivity compared to yesterday
    productivity_comparison = "more productive" if today_expenses < yesterday_expenses else "less productive" if today_expenses > yesterday_expenses else "equally productive"
    if not yesterday_bills:
        productivity_comparison = "no data from yesterday for comparison"
    
    # Format the report
    report = (
        f"💰 **Daily Bills Report for {today}**\n"
        f"🌞 Income Today: ${today_income:.2f}\n"
        f"💸 Expenses Today: ${today_expenses:.2f}\n"
        f"💵 Balance Left: ${today_balance:.2f}\n"
        f"📊 Productivity Compared to Yesterday: {productivity_comparison}"
    )
    
    # Optionally list transactions (unpacking 4 values: type, amount, description, time)
    if today_bills:
        transactions = "\n".join([f"- {type.capitalize()}: ${abs(amount):.2f} at {time} - {description}" for type, amount, description, time in today_bills])
        report += f"\n\n🔍 **Today’s Transactions:**\n{transactions}"
    
    await bot.send_message(chat_id, report)

async def weekly_report_scheduler():
    global startup_time
    while True:
        now = datetime.now(TASHKENT_TZ)
        startup_day = startup_time.date()
        startup_time_of_day = startup_time.time()
        
        # Check if it's the same time as startup, 7 days later
        if (now.date() - startup_day).days == 7 and now.time().hour == startup_time_of_day.hour and now.time().minute == startup_time_of_day.minute:
            await generate_weekly_report(-1002265534780)  # Send to the same chat as task reminders
        
        # Wait until the next day or the exact startup time on the 7th day
        next_check = now.replace(hour=startup_time_of_day.hour, minute=startup_time_of_day.minute, second=0, microsecond=0)
        if now > next_check:
            next_check += timedelta(days=1)
        wait_time = (next_check - now).total_seconds()
        await asyncio.sleep(wait_time)

async def generate_weekly_report(chat_id):
    # Get response times for the last 7 days up to today
    end_date = datetime.now(TASHKENT_TZ).date()
    start_date = end_date - timedelta(days=6)  # Last 7 days (inclusive)

    response_times = {}
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT date(notified_at), 
               (strftime('%s', completed_at) - strftime('%s', notified_at)) / 60.0 AS response_time
        FROM tasks 
        WHERE completed_at IS NOT NULL 
          AND notified_at IS NOT NULL
          AND completed_at > notified_at
          AND date(notified_at) BETWEEN ? AND ?
        ORDER BY date(notified_at)
    """, (start_date.isoformat(), end_date.isoformat()))
    
    data = cursor.fetchall()
    conn.close()
    
    for date, response_minutes in data:
        if response_minutes is not None and response_minutes >= 0:
            if date not in response_times:
                response_times[date] = []
            response_times[date].append(response_minutes)

    if not response_times:
        await bot.send_message(chat_id, "⚠ No response time data found for the last 7 days.")
        return

    all_response_times = []  # Collect all valid response times in minutes
    dates = list(response_times.keys())
    warnings = []  # Store warnings for large response times
    MAX_REASONABLE_MINUTES = 1440  # 24 hours in minutes (adjust as needed)

    for date, times in response_times.items():
        for minutes in times:
            try:
                if minutes < 0:
                    warnings.append(f"Negative response time for {date}: {minutes} min (skipped)")
                    continue
                elif minutes > MAX_REASONABLE_MINUTES:
                    warnings.append(f"Unrealistically large response time for {date}: {minutes} min (capped at {MAX_REASONABLE_MINUTES} min)")
                    minutes = MAX_REASONABLE_MINUTES  # Cap at 24 hours
                all_response_times.append(minutes)
            except (ValueError, TypeError) as e:
                print(f"Error processing value for {date}: {e}")
                continue

    if not all_response_times:
        if warnings:
            await bot.send_message(chat_id, "⚠ No valid response time data available after filtering.\n" + "\n".join(warnings))
        else:
            await bot.send_message(chat_id, "⚠ No valid response time data available.")
        return

    # Calculate statistics
    avg_response_time_minutes = sum(all_response_times) / len(all_response_times)
    
    # Format response time for display (prefer minutes if < 60, otherwise hours)
    if avg_response_time_minutes < 60:
        avg_response_time_display = f"{avg_response_time_minutes:.1f} min"
    elif avg_response_time_minutes < 1440:  # Less than 24 hours
        avg_response_time_display = f"{avg_response_time_minutes / 60:.1f} hours"
    else:  # 24 hours or more
        avg_response_time_display = f"{avg_response_time_minutes / 1440:.1f} days"

    # Line Chart - Response Time Trend (in minutes, one point per day or all points)
    plt.figure(figsize=(6, 4))
    daily_averages = [sum(response_times[date]) / len(response_times[date]) for date in dates if response_times[date]]
    plt.plot(dates, daily_averages, marker="o", linestyle="-", color="#FFA500")
    plt.xlabel("Date")
    plt.ylabel("Avg Response Time (minutes)")
    plt.title("Task Response Time Trend")
    plt.xticks(rotation=45)
    plt.grid(True, linestyle="--", alpha=0.7)  # Add grid for better readability
    
    buf = io.BytesIO()
    plt.savefig(buf, format="png", bbox_inches="tight")
    buf.seek(0)
    plt.close()

    await bot.send_photo(chat_id, InputFile(buf, "response_time_trend.png"), 
                         caption="📈 Task Response Time Trend")

    # Detailed report with warnings if any
    report = (
        f"📅 **Weekly Report** (Last 7 Days)\n"
        f"⏳ Avg Response Time: {avg_response_time_display}\n"
        f"📊 Total Valid Responses: {len(all_response_times)}\n"
        f"🔢 Raw Average (minutes): {avg_response_time_minutes:.1f} min"
    )
    if warnings:
        report += f"\n⚠ Warnings:\n" + "\n".join(warnings)
    await bot.send_message(chat_id, report)

async def main():
    # Start the scheduler tasks
    asyncio.create_task(task_scheduler())
    asyncio.create_task(weekly_report_scheduler())
    asyncio.create_task(daily_bills_report_scheduler())  # Add daily bills report scheduler
    
    # Start polling
    try:
        await dp.start_polling(allowed_updates=types.AllowedUpdates.ALL)
    except Exception as e:
        print(f"Bot stopped: {str(e)}")
    finally:
        await bot.close()

if __name__ == "__main__":
    from aiogram import executor
    from aiogram.utils.executor import start_polling

    loop = asyncio.get_event_loop()
    loop.create_task(task_scheduler())
    loop.create_task(weekly_report_scheduler())
    loop.create_task(daily_bills_report_scheduler())  # Ensure daily bills report scheduler runs
    start_polling(dp, skip_updates=True)