# Leftovr Frontend

React frontend for the Leftovr AI recipe assistant application.

## Features

- **Chat Interface**: Interactive chat with the AI chef assistant
- **Pantry Management**: Add, edit, and delete pantry items with expiration tracking
- **Recipe Search**: Search for recipes based on ingredients and preferences
- **Material UI**: Modern, responsive design with Material UI components

## Prerequisites

- Node.js (v16 or higher)
- npm or yarn

## Installation

```bash
# Navigate to frontend directory
cd frontend

# Install dependencies
npm install
```

## Running the Application

### Development Mode

```bash
npm start
```

The app will open at `http://localhost:3000`

### Production Build

```bash
npm run build
```

This creates an optimized production build in the `build/` folder.

## Environment Variables

Create a `.env` file in the frontend directory:

```env
REACT_APP_API_URL=http://localhost:8000
```

## Project Structure

```
frontend/
├── public/
│   └── index.html
├── src/
│   ├── components/
│   │   └── Navbar.js          # Navigation bar component
│   ├── pages/
│   │   ├── ChatInterface.js   # Main chat interface
│   │   ├── PantryManagement.js # Pantry CRUD operations
│   │   └── RecipeSearch.js    # Recipe search page
│   ├── services/
│   │   └── api.js             # API client for backend communication
│   ├── App.js                 # Main app component with routing
│   └── index.js               # Entry point with theme setup
├── package.json
└── README.md
```

## Backend Integration

The frontend expects the backend API to be running on `http://localhost:8000` (configurable via `REACT_APP_API_URL`).

### Required Backend Endpoints

- `POST /chat` - Send chat messages
- `GET /pantry/inventory` - Get pantry inventory
- `POST /pantry/add` - Add pantry item
- `PUT /pantry/update/:itemName` - Update pantry item
- `DELETE /pantry/delete/:itemName` - Delete pantry item
- `POST /recipes/search` - Search recipes

## Technologies Used

- **React 18**: Frontend framework
- **Material UI 5**: Component library
- **React Router 6**: Client-side routing
- **Axios**: HTTP client
- **Emotion**: CSS-in-JS styling

## Contributing

1. Create a feature branch
2. Make your changes
3. Test thoroughly
4. Submit a pull request

## License

See the main project LICENSE file.
