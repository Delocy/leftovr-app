import React from 'react';
import { Box, Tab, Tabs } from '@mui/material';
import { useLocation, useNavigate } from 'react-router-dom';
import RestaurantIcon from '@mui/icons-material/Restaurant';
import ChatBubbleOutlineIcon from '@mui/icons-material/ChatBubbleOutline';
import SearchIcon from '@mui/icons-material/Search';
import KitchenIcon from '@mui/icons-material/Kitchen';

function Navbar() {
  const location = useLocation();
  const navigate = useNavigate();

  // Map paths to tab values
  const getTabValue = () => {
    if (location.pathname === '/') return 0;
    if (location.pathname === '/pantry') return 1;
    if (location.pathname === '/recipes') return 2;
    return 0;
  };

  const handleTabChange = (event, newValue) => {
    const paths = ['/', '/pantry', '/recipes'];
    navigate(paths[newValue]);
  };

  return (
    <Box
      sx={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'flex-end',
        px: 3,
        py: 1,
        backgroundColor: '#ffffff',
        borderBottom: '1px solid #e5e7eb',
        minHeight: 56,
      }}
    >
      {/* Navigation Tabs */}
      <Box>
        <Tabs
          value={getTabValue()}
          onChange={handleTabChange}
          sx={{
            minHeight: 40,
            '& .MuiTabs-indicator': {
              display: 'none', // Notion doesn't use underline
            },
            '& .MuiTab-root': {
              minHeight: 36,
              minWidth: 80,
              px: 2,
              py: 0.5,
              textTransform: 'none',
              fontSize: '0.875rem',
              fontWeight: 500,
              color: '#6b7280',
              borderRadius: 1,
              mr: 0.5,
              transition: 'all 0.2s',
              '&:hover': {
                backgroundColor: '#f3f4f6',
                color: '#374151',
              },
              '&.Mui-selected': {
                color: '#1f2937',
                backgroundColor: '#f3f4f6',
              },
            },
          }}
        >
          <Tab
            icon={<ChatBubbleOutlineIcon sx={{ fontSize: 18 }} />}
            iconPosition="start"
            label="Chat"
          />
          <Tab
            icon={<KitchenIcon sx={{ fontSize: 18 }} />}
            iconPosition="start"
            label="Pantry"
          />
          <Tab
            icon={<SearchIcon sx={{ fontSize: 18 }} />}
            iconPosition="start"
            label="Recipes"
          />
        </Tabs>
      </Box>
    </Box>
  );
}

export default Navbar;
