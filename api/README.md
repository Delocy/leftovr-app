# Leftovr FastAPI Backend

FastAPI backend for the Leftovr AI recipe assistant application.

## Features

- **RESTful API** for chat, pantry management, and recipe search
- **Automatic API Documentation** via Swagger UI
- **CORS Support** for React frontend
- **Pydantic Validation** for request/response data
- **Integration** with existing Python agents

## Prerequisites

- Python 3.9 or higher
- Existing Leftovr agents and dependencies

## Installation

```bash
# Navigate to api directory
cd api

# Install dependencies
pip install -r requirements.txt
```

## Running the Server

### Development Mode

```bash
# From the api directory
python server.py

# Or using uvicorn directly
uvicorn server:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at:
- **API**: `http://localhost:8000`
- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

### Production Mode

```bash
uvicorn server:app --host 0.0.0.0 --port 8000 --workers 4
```

## API Endpoints

### Health Check
- `GET /` - Basic health check
- `GET /health` - Detailed health status

### Chat
- `POST /chat` - Send message to AI chef
  ```json
  {
    "user_message": "What can I make with chicken?",
    "user_preferences": {"dietary_restrictions": ["gluten-free"]},
    "pantry_inventory": []
  }
  ```

### Pantry Management
- `GET /pantry/inventory` - Get all pantry items
- `POST /pantry/add` - Add new item
  ```json
  {
    "ingredient_name": "chicken breast",
    "quantity": 2,
    "unit": "pieces",
    "expiration_date": "2025-12-10"
  }
  ```
- `PUT /pantry/update/{item_name}` - Update item
- `DELETE /pantry/delete/{item_name}` - Delete item

### Recipe Search
- `POST /recipes/search` - Search recipes
  ```json
  {
    "query": "pasta recipes",
    "preferences": {"dietary_restrictions": ["vegetarian"]},
    "top_k": 10
  }
  ```

## Environment Variables

Create a `.env` file in the project root:

```env
OPENAI_API_KEY=your_openai_api_key
ZILLIZ_CLOUD_URI=your_zilliz_uri
ZILLIZ_CLOUD_TOKEN=your_zilliz_token
```

## Project Structure

```
api/
├── server.py          # Main FastAPI application
├── requirements.txt   # Python dependencies
└── README.md         # This file
```

## CORS Configuration

The API allows requests from:
- `http://localhost:3000` (React dev server)
- `http://localhost:3001`
- `http://127.0.0.1:3000`

To add more origins, update the `allow_origins` list in `server.py`.

## Testing

### Using Swagger UI
1. Start the server
2. Navigate to `http://localhost:8000/docs`
3. Try out endpoints interactively

### Using curl
```bash
# Health check
curl http://localhost:8000/health

# Chat
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"user_message": "What can I cook tonight?"}'

# Get inventory
curl http://localhost:8000/pantry/inventory
```

## Error Handling

All endpoints return standard HTTP status codes:
- `200` - Success
- `400` - Bad request (validation error)
- `404` - Not found
- `500` - Internal server error
- `503` - Service unavailable (e.g., recipe DB not initialized)

## Logging

The server logs all requests and errors. Set log level in `uvicorn.run()`:
```python
uvicorn.run("server:app", log_level="debug")
```

## Contributing

1. Make changes to `server.py`
2. Test with Swagger UI
3. Ensure all endpoints work with the React frontend
4. Update this README if adding new endpoints

## License

See the main project LICENSE file.
