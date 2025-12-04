import React from 'react';
import { Link as RouterLink, useLocation } from 'react-router-dom';
import {
  AppBar,
  Toolbar,
  Typography,
  Button,
  Box,
} from '@mui/material';
import RestaurantIcon from '@mui/icons-material/Restaurant';
import KitchenIcon from '@mui/icons-material/Kitchen';
import SearchIcon from '@mui/icons-material/Search';
import ChatIcon from '@mui/icons-material/Chat';

const Navbar = () => {
  const location = useLocation();

  const navItems = [
    { label: 'Chat', path: '/', icon: <ChatIcon /> },
    { label: 'Pantry', path: '/pantry', icon: <KitchenIcon /> },
    { label: 'Recipes', path: '/recipes', icon: <SearchIcon /> },
  ];

  return (
    <AppBar 
      position="sticky" 
      elevation={0}
      sx={{
        bgcolor: '#ffffff',
        borderBottom: '1px solid #e0e0e0',
      }}
    >
      <Toolbar sx={{ minHeight: '64px !important' }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5, flexGrow: 1 }}>
          <RestaurantIcon sx={{ fontSize: 28, color: '#4caf50' }} />
          <Typography
            variant="h6"
            component={RouterLink}
            to="/"
            sx={{
              textDecoration: 'none',
              color: '#37352f',
              fontWeight: 700,
              fontSize: '18px',
              letterSpacing: '-0.5px',
            }}
          >
            Leftovr
          </Typography>
        </Box>
        <Box sx={{ display: 'flex', gap: 0.5 }}>
          {navItems.map((item) => (
            <Button
              key={item.path}
              component={RouterLink}
              to={item.path}
              startIcon={item.icon}
              sx={{
                color: location.pathname === item.path ? '#37352f' : '#787774',
                bgcolor: location.pathname === item.path ? '#f7f6f3' : 'transparent',
                textTransform: 'none',
                fontSize: '14px',
                fontWeight: 500,
                px: 2,
                py: 0.75,
                borderRadius: 1,
                '&:hover': {
                  bgcolor: '#f7f6f3',
                  color: '#37352f',
                },
                '& .MuiButton-startIcon': {
                  marginRight: '6px',
                },
                '& .MuiSvgIcon-root': {
                  fontSize: '18px',
                },
              }}
            >
              {item.label}
            </Button>
          ))}
        </Box>
      </Toolbar>
    </AppBar>
  );
};

export default Navbar;
