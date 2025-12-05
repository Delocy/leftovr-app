import React, { useState } from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import { CssBaseline, Box } from '@mui/material';
import Navbar from './components/Navbar';
import Sidebar from './components/Sidebar';
import ChatInterface from './pages/ChatInterface';
import PantryPage from './pages/PantryPage';
import RecipeSearch from './pages/RecipeSearch';

// Create fresh, modern theme with green accent
const theme = createTheme({
  palette: {
    mode: 'light',
    primary: {
      main: '#10b981', // Fresh green
      light: '#34d399',
      dark: '#059669',
    },
    secondary: {
      main: '#f59e0b', // Warm orange for accents
    },
    background: {
      default: '#ffffff',
      paper: '#ffffff',
    },
    text: {
      primary: '#1f2937',
      secondary: '#6b7280',
    },
    divider: '#e5e7eb',
    success: {
      main: '#10b981',
    },
    warning: {
      main: '#f59e0b',
    },
    error: {
      main: '#ef4444',
    },
  },
  typography: {
    fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, "Apple Color Emoji", Arial, sans-serif, "Segoe UI Emoji", "Segoe UI Symbol"',
    h4: {
      fontWeight: 700,
      fontSize: '1.875rem',
      lineHeight: 1.2,
      color: '#37352f',
    },
    h5: {
      fontWeight: 600,
      fontSize: '1.5rem',
      lineHeight: 1.3,
      color: '#37352f',
    },
    h6: {
      fontWeight: 600,
      fontSize: '1.125rem',
      lineHeight: 1.4,
      color: '#37352f',
    },
    body1: {
      fontSize: '1rem',
      lineHeight: 1.5,
      color: '#37352f',
    },
    body2: {
      fontSize: '0.875rem',
      lineHeight: 1.5,
      color: '#787774',
    },
  },
  components: {
    MuiButton: {
      styleOverrides: {
        root: {
          textTransform: 'none',
          borderRadius: '4px',
          fontWeight: 500,
        },
      },
    },
    MuiPaper: {
      styleOverrides: {
        root: {
          borderRadius: '4px',
        },
      },
    },
  },
});

const SIDEBAR_WIDTH = 320;

function App() {
  const [pantryItems, setPantryItems] = useState([]);
  const [preferences, setPreferences] = useState({
    dietaryRestrictions: [],
    allergies: [],
    cuisinePreferences: [],
    skillLevel: 'intermediate',
  });

  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <Router>
        <Box sx={{ display: 'flex', flexDirection: 'column', height: '100vh', overflow: 'hidden' }}>
          {/* Main Content with Sidebar */}
          <Box sx={{ display: 'flex', flex: 1, overflow: 'hidden' }}>
            {/* Left Sidebar - always visible */}
            <Sidebar
              open={true}
              width={SIDEBAR_WIDTH}
              pantryItems={pantryItems}
              setPantryItems={setPantryItems}
              preferences={preferences}
              setPreferences={setPreferences}
            />

            {/* Main Content Column */}
            <Box
              sx={{
                flexGrow: 1,
                display: 'flex',
                flexDirection: 'column',
                overflow: 'hidden',
                width: '100%',
              }}
            >
              {/* Top Navbar */}
              <Navbar />

            {/* Main Content Area */}
            <Box
              component="main"
              sx={{
                flexGrow: 1,
                display: 'flex',
                flexDirection: 'column',
                overflow: 'hidden',
                backgroundColor: '#ffffff',
                width: '100%',
              }}
            >
              <Routes>
              <Route 
                path="/" 
                element={
                  <ChatInterface 
                    pantryItems={pantryItems}
                    preferences={preferences}
                  />
                } 
              />
              <Route 
                path="/pantry" 
                element={
                  <PantryPage 
                    pantryItems={pantryItems}
                    setPantryItems={setPantryItems}
                  />
                } 
              />
              <Route 
                path="/recipes" 
                element={<RecipeSearch />} 
              />
            </Routes>
          </Box>
            </Box>
          </Box>
        </Box>
      </Router>
    </ThemeProvider>
  );
}

export default App;
