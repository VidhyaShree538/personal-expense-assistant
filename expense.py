
import streamlit as st
from google import genai
import re

# ---------------- CONFIG ----------------

API_KEY = st.secrets["GEMINI_API_KEY"]
MODEL = "gemini-3.8-flash"
KB_FILE = "expense_data_1.csv"


# ---------------- EXPENSE CALCULATOR ----------------

def calculate_expenses(user_input):

    text = user_input.lower()

    # Check whether the user is asking for an expense calculation
    has_income = "income" in text
    has_expense = any(word in text for word in
                      ["spend", "spent", "expense", "expenses"])

    if not (has_income and has_expense):
        return None

    # Extract amounts, including amounts such as 20,000
    numbers = re.findall(r'\d[\d,]*', user_input)
    numbers = [int(num.replace(",", "")) for num in numbers]

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


# ---------------- INITIALIZE CHAT ----------------

if "messages" not in st.session_state:
    st.session_state.messages = []

if "chat" not in st.session_state:
    st.session_state.chat = client.chats.create(
        model=MODEL,
        config={"system_instruction": prompt}
    )


# ---------------- USER INTERFACE ----------------

st.title("💰 Personal Expense Assistant")

st.write(
    "Ask me questions about budgeting, expenses, "
    "income and savings!"
)


# Display previous messages

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])


# ---------------- USER INPUT ----------------

user_input = st.chat_input("Ask about your expenses...")


if user_input:

    # Display user message
    st.session_state.messages.append(
        {"role": "user", "content": user_input}
    )

    with st.chat_message("user"):
        st.markdown(user_input)


    # First check the local expense calculator
    calculation_result = calculate_expenses(user_input)

    if calculation_result:

        st.session_state.messages.append(
            {"role": "assistant", "content": calculation_result}
        )

        with st.chat_message("assistant"):
            st.markdown(calculation_result)


    # If not a calculation, ask Gemini
    else:

        with st.chat_message("assistant"):

            try:
                with st.spinner("Thinking..."):

                    response = st.session_state.chat.send_message(
                        user_input
                    )

                    answer = response.text

                st.markdown(answer)

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
