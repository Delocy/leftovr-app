import React from 'react';
import { Routes, Route } from 'react-router-dom';
import { Box } from '@mui/material';
import Navbar from './components/Navbar';
import ChatInterface from './pages/ChatInterface';
import PantryManagement from './pages/PantryManagement';
import RecipeSearch from './pages/RecipeSearch';

function App() {
  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', minHeight: '100vh' }}>
      <Navbar />
      <Box component="main" sx={{ flexGrow: 1, bgcolor: 'background.default' }}>
        <Routes>
          <Route path="/" element={<ChatInterface />} />
          <Route path="/pantry" element={<PantryManagement />} />
          <Route path="/recipes" element={<RecipeSearch />} />
        </Routes>
      </Box>
    </Box>
  );
}

export default App;
