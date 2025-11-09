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

## Pantry Database Validation

The app uses a persistent SQLite database to store your pantry inventory. The database is located at `~/.leftovr/pantry.db`.

### Validate Database Contents

```bash
python3 validate_pantry.py
```

This will show:
- Current inventory items
- Quantities and expiration dates
- Items expiring soon

### Test Database Operations

```bash
# Run comprehensive CRUD tests
python3 test_pantry_operations.py

# Clean up test data
python3 cleanup_test_data.py
```

For detailed documentation, see:
- [docs/CRUD_OPTIMIZATION_SUMMARY.md](docs/CRUD_OPTIMIZATION_SUMMARY.md) - CRUD optimization details
- [docs/CRUD_USAGE_GUIDE.md](docs/CRUD_USAGE_GUIDE.md) - Quick usage reference

## Project Structure

- `agents/` - Agent implementations (Executive Chef, Pantry Agent, etc.)
- `database/` - Database layer (SQLite operations)
- `mcp/` - Model Context Protocol server
- `data/` - Recipe data and metadata
- `main.py` - LangGraph workflow orchestration
- `streamlit_app.py` - Streamlit web interface
- `validate_pantry.py` - Database validation script
- `test_pantry_operations.py` - CRUD testing script
- `cleanup_test_data.py` - Test data cleanup
- `requirements.txt` - Python dependencies
- `.env` - Environment variables (not committed to git)

## Notes

- Make sure your virtual environment is activated before running any commands
- Never commit your `.env` file to version control
- Use `pip freeze > requirements.txt` to keep dependencies up to date
