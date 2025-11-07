# Leftovr App

A multi-agent food concierge system that helps users discover, discuss, and enjoy food through AI-powered agents.

## Setup Instructions

### 1. Create Python Virtual Environment

```bash
# Create virtual environment
python3 -m venv .venv

# Activate virtual environment
# On macOS/Linux:
source .venv/bin/activate

# On Windows:
# venv\Scripts\activate
```

### 2. Set Up Environment Variables

Create a `.env` file in the project root directory:

```bash
# Create .env file
touch .env
```

Add your API keys to the `.env` file:

```
OPENAI_API_KEY=your_openai_api_key_here
```

### 3. Install Dependencies

```bash
# Install all required packages
pip install -r requirements.txt
```

### 4. Update Dependencies (When Adding New Packages)

If you install new packages during development, update the `requirements.txt`:

```bash
# Install a new package
pip install package-name

# Update requirements.txt with all installed packages
pip freeze > requirements.txt
```

## Running the Application

### Streamlit Web Interface (Recommended)

The primary way to use Leftovr is through the Streamlit web interface:

```bash
# Activate virtual environment
source .venv/bin/activate  # macOS/Linux

# Run Streamlit app
streamlit run streamlit_app.py
```

The app will open in your browser at `http://localhost:8501`

### Testing (CLI Mode)

For development and testing, you can run the CLI version:

```bash
python main.py
```

**Note**: The CLI mode runs a test conversation. For production use, always use the Streamlit interface.

## Project Structure

- `agents/` - Agent implementations (Waiter Agent, etc.)
- `main.py` - Main multi-agent orchestration system
- `streamlit_app.py` - Streamlit web interface
- `requirements.txt` - Python dependencies
- `.env` - Environment variables (not committed to git)

## Notes

- Make sure your virtual environment is activated before running any commands
- Never commit your `.env` file to version control
- Use `pip freeze > requirements.txt` to keep dependencies up to date
