# Personal Expense Assistant 💰

## Project Overview
Personal Expense Assistant is an AI-powered chatbot that helps users understand and manage their personal finances.

## Features
- AI-powered financial assistance using Google Gemini.
- Automatic expense calculation using Python.
- Income and expense summary.
- Budgeting and saving guidance.
- CSV-based knowledge base.
- Interactive chat interface using Streamlit.

## Technologies Used
- Python
- Streamlit
- Google Gemini API
- CSV

## Project Structure
```text
expemse/
│
├── expense.py
├── expense_data_1.csv
├── requirements.txt
├── README.md
├── .gitignore
└── .streamlit/
    └── secrets.toml
```

## Installation

1. Clone this repository.
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Create `.streamlit/secrets.toml` and add your Gemini API key:

```toml
GEMINI_API_KEY = "YOUR_API_KEY"
```

4. Run the application:

```bash
python -m streamlit run expense.py
```
