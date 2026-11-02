
import sqlite3
import re
from pathlib import Path

import streamlit as st
from google import genai
from google.genai import types


# ---------------- CONFIGURATION ----------------

MODEL = "gemini-3.8-flash"

BASE_DIR = Path(__file__).resolve().parent
DB_FILE = BASE_DIR / "expenses.db"
KB_FILE = BASE_DIR / "expense_data_1.csv"

API_KEY = st.secrets["GEMINI_API_KEY"]


# ---------------- DATABASE CONNECTION ----------------

conn = sqlite3.connect(str(DB_FILE), check_same_thread=False)
cursor = conn.cursor()

# Expenses table
cursor.execute("""
    CREATE TABLE IF NOT EXISTS expenses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        amount REAL,
        category TEXT,
        description TEXT,
        expense_date TEXT
    )
""")

# Chats table
cursor.execute("""
    CREATE TABLE IF NOT EXISTS chats (
        chat_id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
""")

# Messages table
cursor.execute("""
    CREATE TABLE IF NOT EXISTS messages (
        message_id INTEGER PRIMARY KEY AUTOINCREMENT,
        chat_id INTEGER,
        role TEXT,
        content TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (chat_id) REFERENCES chats(chat_id)
    )
""")

conn.commit()


# ---------------- DATABASE FUNCTIONS ----------------

def create_new_chat(title):
    cursor.execute(
        "INSERT INTO chats (title) VALUES (?)",
        (title[:50],)
    )
    conn.commit()
    return cursor.lastrowid


def save_message(chat_id, role, content):
    cursor.execute("""
        INSERT INTO messages (chat_id, role, content)
        VALUES (?, ?, ?)
    """, (chat_id, role, content))

    conn.commit()


def get_all_chats():
    cursor.execute("""
        SELECT chat_id, title, created_at
        FROM chats
        ORDER BY chat_id DESC
    """)
    return cursor.fetchall()


def get_chat_messages(chat_id):
    cursor.execute("""
        SELECT role, content
        FROM messages
        WHERE chat_id = ?
        ORDER BY message_id ASC
    """, (chat_id,))

    return cursor.fetchall()


# ---------------- EXPENSE CALCULATOR ----------------

def calculate_expenses(user_input):

    text = user_input.lower()

    has_income = "income" in text

    has_expense = any(
        word in text
        for word in ["spend", "spent", "expense", "expenses"]
    )

    if not (has_income and has_expense):
        return None

    numbers = re.findall(r'\d[\d,]*', user_input)

    numbers = [
        int(num.replace(",", ""))
        for num in numbers
    ]

    if len(numbers) < 2:
        return None

    income = numbers[0]
    expenses = numbers[1:]

    total_expense = sum(expenses)
    remaining_balance = income - total_expense

    result = f"""
### Expense Summary

- **Monthly Income:** ₹{income:,}
- **Total Expenses:** ₹{total_expense:,}
- **Remaining Balance:** ₹{remaining_balance:,}
"""

    return result


# ---------------- LOAD KNOWLEDGE BASE ----------------

with open(KB_FILE, "r", encoding="utf-8") as f:
    kb = f.read()


# ---------------- SYSTEM PROMPT ----------------

prompt = f"""
You are a Personal Expense Assistant.

Your job is to help users manage their personal expenses.

Instructions:
1. Answer politely and clearly.
2. Explain budgeting, saving, income and expenses.
3. Use the provided knowledge base.
4. If information is unavailable, say so politely.
5. Do not invent financial information.
6. Give simple and practical explanations.

Knowledge Base:
{kb}
"""


# ---------------- INITIALIZE GEMINI CLIENT ----------------

@st.cache_resource
def initialize_client():
    return genai.Client(api_key=API_KEY)


client = initialize_client()


# ---------------- SESSION STATE ----------------

if "active_chat_id" not in st.session_state:
    st.session_state.active_chat_id = None

if "messages" not in st.session_state:
    st.session_state.messages = []

if "chat" not in st.session_state:
    st.session_state.chat = None


# ---------------- LOAD PREVIOUS CHAT ----------------

def load_chat(chat_id):

    saved_messages = get_chat_messages(chat_id)

    st.session_state.active_chat_id = chat_id

    st.session_state.messages = [
        {"role": role, "content": content}
        for role, content in saved_messages
    ]

    # Restore previous conversation context for Gemini
    history = []

    for role, content in saved_messages:

        history.append(
            types.Content(
                role="user" if role == "user" else "model",
                parts=[types.Part(text=content)]
            )
        )

    st.session_state.chat = client.chats.create(
        model=MODEL,
        config={"system_instruction": prompt},
        history=history
    )


# ---------------- SIDEBAR: CHAT HISTORY ----------------

st.sidebar.title("💬 Chat History")

if st.sidebar.button("➕ New Chat", use_container_width=True):

    st.session_state.active_chat_id = None
    st.session_state.messages = []
    st.session_state.chat = None

    st.rerun()


st.sidebar.divider()

previous_chats = get_all_chats()

for chat_id, title, created_at in previous_chats:

    if st.sidebar.button(
        f"🗨️ {title}",
        key=f"chat_{chat_id}",
        use_container_width=True
    ):

        load_chat(chat_id)
        st.rerun()


# ---------------- MAIN USER INTERFACE ----------------

st.title("💰 Personal Expense Assistant")

st.write(
    "Ask me questions about budgeting, expenses, "
    "income and savings!"
)


# Display conversation messages

for msg in st.session_state.messages:

    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])


# ---------------- USER INPUT ----------------

user_input = st.chat_input("Ask about your expenses...")


if user_input:

    # Create a new database chat when needed
    if st.session_state.active_chat_id is None:

        new_chat_id = create_new_chat(user_input)

        st.session_state.active_chat_id = new_chat_id

        st.session_state.chat = client.chats.create(
            model=MODEL,
            config={"system_instruction": prompt}
        )

    chat_id = st.session_state.active_chat_id

    # Save user message
    save_message(chat_id, "user", user_input)

    st.session_state.messages.append(
        {"role": "user", "content": user_input}
    )

    with st.chat_message("user"):
        st.markdown(user_input)


    # Check local expense calculator
    calculation_result = calculate_expenses(user_input)

    if calculation_result:

        answer = calculation_result

        save_message(chat_id, "assistant", answer)

        st.session_state.messages.append(
            {"role": "assistant", "content": answer}
        )

        with st.chat_message("assistant"):
            st.markdown(answer)


    # Otherwise ask Gemini
    else:

        with st.chat_message("assistant"):

            try:

                with st.spinner("Thinking..."):

                    response = st.session_state.chat.send_message(
                        user_input
                    )

                    answer = response.text

                st.markdown(answer)

                save_message(chat_id, "assistant", answer)

                st.session_state.messages.append(
                    {"role": "assistant", "content": answer}
                )

            except Exception as e:

                if "503" in str(e):

                    st.warning(
                        "Gemini is temporarily busy. "
                        "Please try again shortly."
                    )

                else:

                    st.error(f"Something went wrong: {e}")


# ---------------- CLOSE DATABASE ----------------

# Streamlit reruns this script, so keep the connection
# available throughout the current application session.
