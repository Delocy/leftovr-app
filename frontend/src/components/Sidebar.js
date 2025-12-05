import React, { useState, useEffect } from 'react';
import {
  Box,
  Drawer,
  Typography,
  Divider,
  Chip,
  FormGroup,
  FormControlLabel,
  Checkbox,
  Radio,
  RadioGroup,
  Button,
  TextField,
  Tooltip,
} from '@mui/material';
import TuneIcon from '@mui/icons-material/Tune';
import RestaurantIcon from '@mui/icons-material/Restaurant';
import BookmarkBorderIcon from '@mui/icons-material/BookmarkBorder';
import axios from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

// Common dietary restrictions - simplified to most common
const DIETARY_RESTRICTIONS = [
  'Vegetarian',
  'Vegan',
  'Gluten-Free',
  'Dairy-Free',
  'Keto',
];

// Common allergies - simplified to most common
const COMMON_ALLERGIES = [
  'Peanuts',
  'Shellfish',
  'Eggs',
  'Milk',
  'Wheat',
];

// Cuisine preferences
const CUISINE_TYPES = [
  'Italian',
  'Mexican',
  'Chinese',
  'Japanese',
  'Indian',
  'Thai',
  'Mediterranean',
  'American',
  'French',
  'Korean',
];

function Sidebar({ open, width, pantryItems, preferences, setPreferences }) {
  const [customRestriction, setCustomRestriction] = useState('');
  const [customAllergy, setCustomAllergy] = useState('');
  const [customCuisine, setCustomCuisine] = useState('');

  const handleAddCustomRestriction = () => {
    if (customRestriction.trim()) {
      const current = preferences.dietaryRestrictions || [];
      if (!current.includes(customRestriction.trim())) {
        setPreferences({
          ...preferences,
          dietaryRestrictions: [...current, customRestriction.trim()],
        });
        setCustomRestriction('');
      }
    }
  };

  const handleAddCustomAllergy = () => {
    if (customAllergy.trim()) {
      const current = preferences.allergies || [];
      if (!current.includes(customAllergy.trim())) {
        setPreferences({
          ...preferences,
          allergies: [...current, customAllergy.trim()],
        });
        setCustomAllergy('');
      }
    }
  };

  const handleAddCustomCuisine = () => {
    if (customCuisine.trim()) {
      const current = preferences.cuisinePreferences || [];
      if (!current.includes(customCuisine.trim())) {
        setPreferences({
          ...preferences,
          cuisinePreferences: [...current, customCuisine.trim()],
        });
        setCustomCuisine('');
      }
    }
  };

  const handleDietaryChange = (restriction) => {
    const current = preferences.dietaryRestrictions || [];
    const updated = current.includes(restriction)
      ? current.filter((r) => r !== restriction)
      : [...current, restriction];
    setPreferences({ ...preferences, dietaryRestrictions: updated });
  };

  const handleAllergyChange = (allergy) => {
    const current = preferences.allergies || [];
    const updated = current.includes(allergy)
      ? current.filter((a) => a !== allergy)
      : [...current, allergy];
    setPreferences({ ...preferences, allergies: updated });
  };

  const handleCuisineChange = (cuisine) => {
    const current = preferences.cuisinePreferences || [];
    const updated = current.includes(cuisine)
      ? current.filter((c) => c !== cuisine)
      : [...current, cuisine];
    setPreferences({ ...preferences, cuisinePreferences: updated });
  };

  const getTotalPreferences = () => {
    const dietaryCount = preferences.dietaryRestrictions?.length || 0;
    const allergyCount = preferences.allergies?.length || 0;
    const cuisineCount = preferences.cuisinePreferences?.length || 0;
    return dietaryCount + allergyCount + cuisineCount;
  };

  return (
    <Drawer
      variant="persistent"
      anchor="left"
      open={open}
      sx={{
        width: open ? width : 0,
        flexShrink: 0,
        '& .MuiDrawer-paper': {
          width: width,
          boxSizing: 'border-box',
          backgroundColor: '#fbfbfa',
          borderRight: '1px solid rgba(0, 0, 0, 0.09)',
          overflow: 'hidden',
        },
      }}
    >
      <Box sx={{ display: 'flex', flexDirection: 'column', height: '100%', overflow: 'hidden' }}>
        {/* Logo at Top */}
        <Box
          sx={{
            px: 2,
            py: 2.5,
            borderBottom: '1px solid #e5e7eb',
            backgroundColor: '#ffffff',
          }}
        >
          <Box
            sx={{
              display: 'flex',
              alignItems: 'center',
              gap: 1.5,
              cursor: 'pointer',
              py: 1,
              px: 1.5,
              borderRadius: '6px',
              transition: 'background-color 0.15s ease',
              '&:hover': {
                backgroundColor: 'rgba(0, 0, 0, 0.03)',
              },
            }}
          >
            <Box
              sx={{
                width: 32,
                height: 32,
                borderRadius: '6px',
                backgroundColor: '#10b981',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                flexShrink: 0,
              }}
            >
              <RestaurantIcon sx={{ color: '#ffffff', fontSize: 20 }} />
            </Box>
            <Box
              component="span"
              sx={{
                fontWeight: 600,
                fontSize: '1.05rem',
                color: '#37352f',
                letterSpacing: '-0.01em',
              }}
            >
              Leftovr
            </Box>
          </Box>
        </Box>

        {/* Preferences Header */}
        <Box
          sx={{
            px: 3,
            pt: 2.5,
            pb: 1.5,
          }}
        >
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5, mb: 0.5 }}>
            <Typography 
              variant="h6" 
              sx={{ 
                fontWeight: 600, 
                fontSize: '0.875rem', 
                color: '#37352f',
                letterSpacing: '-0.01em',
                textTransform: 'none',
              }}
            >
              My Preferences
            </Typography>
            {getTotalPreferences() > 0 && (
              <Box
                sx={{
                  px: 0.75,
                  py: 0.25,
                  borderRadius: '4px',
                  backgroundColor: 'rgba(16, 185, 129, 0.1)',
                  fontSize: '0.75rem',
                  fontWeight: 600,
                  color: '#10b981',
                  lineHeight: 1.2,
                }}
              >
                {getTotalPreferences()}
              </Box>
            )}
          </Box>
          <Typography 
            variant="caption" 
            sx={{ 
              color: '#787774', 
              display: 'block',
              fontSize: '0.8125rem',
              lineHeight: 1.4,
            }}
          >
            Customize your recipe recommendations
          </Typography>
        </Box>

        {/* Scrollable Content */}
        <Box sx={{ flex: 1, overflowY: 'auto', overflowX: 'hidden', px: 2, py: 1 }}>
          
          {/* Quick Stats */}
          {pantryItems && pantryItems.length > 0 && (
            <Box
              sx={{
                mb: 2,
                p: 2,
                borderRadius: '6px',
                backgroundColor: 'rgba(16, 185, 129, 0.06)',
                border: '1px solid rgba(16, 185, 129, 0.15)',
                transition: 'all 0.15s ease',
                '&:hover': {
                  backgroundColor: 'rgba(16, 185, 129, 0.08)',
                  border: '1px solid rgba(16, 185, 129, 0.25)',
                },
              }}
            >
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                <BookmarkBorderIcon sx={{ fontSize: 16, color: '#10b981' }} />
                <Typography 
                  variant="subtitle2" 
                  sx={{ 
                    fontWeight: 600, 
                    color: '#37352f',
                    fontSize: '0.8125rem',
                    letterSpacing: '-0.01em',
                  }}
                >
                  Your Pantry
                </Typography>
              </Box>
              <Typography 
                variant="h4" 
                sx={{ 
                  fontWeight: 700, 
                  color: '#10b981',
                  fontSize: '1.75rem',
                  lineHeight: 1.2,
                  mb: 0.25,
                }}
              >
                {pantryItems.length}
              </Typography>
              <Typography 
                variant="caption" 
                sx={{ 
                  color: '#787774',
                  fontSize: '0.75rem',
                }}
              >
                ingredients ready to cook
              </Typography>
            </Box>
          )}

          {/* Dietary Restrictions */}
          <Box sx={{ mb: 2.5 }}>
            <Typography
              variant="subtitle2"
              sx={{ 
                fontWeight: 600, 
                color: '#37352f', 
                mb: 1.5, 
                display: 'flex', 
                alignItems: 'center', 
                gap: 1,
                fontSize: '0.8125rem',
                letterSpacing: '-0.01em',
                px: 1,
              }}
            >
              🌱 Dietary Restrictions
            </Typography>
            <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5, px: 1, mb: 1.5 }}>
              {DIETARY_RESTRICTIONS.map((restriction) => (
                <Chip
                  key={restriction}
                  label={restriction}
                  size="small"
                  onClick={() => handleDietaryChange(restriction)}
                  variant={preferences.dietaryRestrictions?.includes(restriction) ? 'filled' : 'outlined'}
                  sx={{
                    fontSize: '0.75rem',
                    height: '26px',
                    fontWeight: 500,
                    backgroundColor: preferences.dietaryRestrictions?.includes(restriction) 
                      ? 'rgba(16, 185, 129, 0.1)' 
                      : 'transparent',
                    color: preferences.dietaryRestrictions?.includes(restriction) ? '#10b981' : '#787774',
                    border: preferences.dietaryRestrictions?.includes(restriction) 
                      ? '1px solid rgba(16, 185, 129, 0.2)'
                      : '1px solid rgba(0, 0, 0, 0.09)',
                    transition: 'all 0.15s ease',
                    '&:hover': {
                      backgroundColor: preferences.dietaryRestrictions?.includes(restriction) 
                        ? 'rgba(16, 185, 129, 0.15)' 
                        : 'rgba(0, 0, 0, 0.03)',
                      borderColor: preferences.dietaryRestrictions?.includes(restriction)
                        ? 'rgba(16, 185, 129, 0.3)'
                        : 'rgba(0, 0, 0, 0.12)',
                    },
                  }}
                />
              ))}
              {/* Show custom restrictions as chips */}
              {preferences.dietaryRestrictions?.filter(r => !DIETARY_RESTRICTIONS.includes(r)).map((restriction, idx) => (
                <Chip
                  key={`custom-${idx}`}
                  label={restriction}
                  size="small"
                  onDelete={() => handleDietaryChange(restriction)}
                  onClick={() => handleDietaryChange(restriction)}
                  sx={{
                    fontSize: '0.75rem',
                    height: '26px',
                    backgroundColor: 'rgba(16, 185, 129, 0.1)',
                    color: '#10b981',
                    border: '1px solid rgba(16, 185, 129, 0.2)',
                    fontWeight: 500,
                    '&:hover': {
                      backgroundColor: 'rgba(16, 185, 129, 0.15)',
                      borderColor: 'rgba(16, 185, 129, 0.3)',
                    },
                    '& .MuiChip-deleteIcon': {
                      color: 'rgba(16, 185, 129, 0.6)',
                      fontSize: '16px',
                      '&:hover': {
                        color: '#10b981',
                      },
                    },
                  }}
                />
              ))}
            </Box>

            {/* Custom Restrictions Input */}
            <Box sx={{ px: 1 }}>
              <Box sx={{ display: 'flex', gap: 0.75 }}>
                <input
                  type="text"
                  placeholder="Add custom..."
                  value={customRestriction}
                  onChange={(e) => setCustomRestriction(e.target.value)}
                  onKeyPress={(e) => e.key === 'Enter' && handleAddCustomRestriction()}
                  style={{
                    flex: 1,
                    padding: '7px 10px',
                    fontSize: '0.8125rem',
                    color: '#37352f',
                    border: '1px solid rgba(0, 0, 0, 0.09)',
                    borderRadius: '4px',
                    outline: 'none',
                    fontFamily: 'inherit',
                    transition: 'border-color 0.15s ease',
                    backgroundColor: '#ffffff',
                  }}
                  onFocus={(e) => e.target.style.borderColor = '#10b981'}
                  onBlur={(e) => e.target.style.borderColor = 'rgba(0, 0, 0, 0.09)'}
                />
                <Button
                  size="small"
                  variant="outlined"
                  onClick={handleAddCustomRestriction}
                  disabled={!customRestriction.trim()}
                  sx={{
                    minWidth: '54px',
                    textTransform: 'none',
                    borderColor: 'rgba(0, 0, 0, 0.09)',
                    color: '#37352f',
                    fontSize: '0.8125rem',
                    fontWeight: 500,
                    px: 1.5,
                    py: 0.5,
                    '&:hover': {
                      borderColor: '#10b981',
                      backgroundColor: 'rgba(16, 185, 129, 0.06)',
                      color: '#10b981',
                    },
                    '&:disabled': {
                      borderColor: 'rgba(0, 0, 0, 0.06)',
                      color: 'rgba(55, 53, 47, 0.3)',
                    },
                  }}
                >
                  Add
                </Button>
              </Box>
            </Box>
          </Box>

          <Divider sx={{ my: 2.5, borderColor: 'rgba(0, 0, 0, 0.06)' }} />

          {/* Allergies */}
          <Box sx={{ mb: 2.5 }}>
            <Typography
              variant="subtitle2"
              sx={{ 
                fontWeight: 600, 
                color: '#37352f', 
                mb: 1.5, 
                display: 'flex', 
                alignItems: 'center', 
                gap: 1,
                fontSize: '0.8125rem',
                letterSpacing: '-0.01em',
                px: 1,
              }}
            >
              ⚠️ Allergies
            </Typography>
            <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5, px: 1, mb: 1.5 }}>
              {COMMON_ALLERGIES.map((allergy) => (
                <Chip
                  key={allergy}
                  label={allergy}
                  size="small"
                  onClick={() => handleAllergyChange(allergy)}
                  variant={preferences.allergies?.includes(allergy) ? 'filled' : 'outlined'}
                  sx={{
                    fontSize: '0.75rem',
                    height: '26px',
                    fontWeight: 500,
                    backgroundColor: preferences.allergies?.includes(allergy) 
                      ? 'rgba(239, 68, 68, 0.1)' 
                      : 'transparent',
                    color: preferences.allergies?.includes(allergy) ? '#ef4444' : '#787774',
                    border: preferences.allergies?.includes(allergy) 
                      ? '1px solid rgba(239, 68, 68, 0.2)'
                      : '1px solid rgba(0, 0, 0, 0.09)',
                    transition: 'all 0.15s ease',
                    '&:hover': {
                      backgroundColor: preferences.allergies?.includes(allergy) 
                        ? 'rgba(239, 68, 68, 0.15)' 
                        : 'rgba(0, 0, 0, 0.03)',
                      borderColor: preferences.allergies?.includes(allergy)
                        ? 'rgba(239, 68, 68, 0.3)'
                        : 'rgba(0, 0, 0, 0.12)',
                    },
                  }}
                />
              ))}
              {/* Show custom allergies as chips */}
              {preferences.allergies?.filter(a => !COMMON_ALLERGIES.includes(a)).map((allergy, idx) => (
                <Chip
                  key={`custom-${idx}`}
                  label={allergy}
                  size="small"
                  onDelete={() => handleAllergyChange(allergy)}
                  onClick={() => handleAllergyChange(allergy)}
                  sx={{
                    fontSize: '0.75rem',
                    height: '26px',
                    backgroundColor: 'rgba(239, 68, 68, 0.1)',
                    color: '#ef4444',
                    border: '1px solid rgba(239, 68, 68, 0.2)',
                    fontWeight: 500,
                    '&:hover': {
                      backgroundColor: 'rgba(239, 68, 68, 0.15)',
                      borderColor: 'rgba(239, 68, 68, 0.3)',
                    },
                    '& .MuiChip-deleteIcon': {
                      color: 'rgba(239, 68, 68, 0.6)',
                      fontSize: '16px',
                      '&:hover': {
                        color: '#ef4444',
                      },
                    },
                  }}
                />
              ))}
            </Box>

            {/* Custom Allergies Input */}
            <Box sx={{ px: 1 }}>
              <Box sx={{ display: 'flex', gap: 0.75 }}>
                <input
                  type="text"
                  placeholder="Add custom..."
                  value={customAllergy}
                  onChange={(e) => setCustomAllergy(e.target.value)}
                  onKeyPress={(e) => e.key === 'Enter' && handleAddCustomAllergy()}
                  style={{
                    flex: 1,
                    padding: '7px 10px',
                    fontSize: '0.8125rem',
                    color: '#37352f',
                    border: '1px solid rgba(0, 0, 0, 0.09)',
                    borderRadius: '4px',
                    outline: 'none',
                    fontFamily: 'inherit',
                    transition: 'border-color 0.15s ease',
                    backgroundColor: '#ffffff',
                  }}
                  onFocus={(e) => e.target.style.borderColor = '#ef4444'}
                  onBlur={(e) => e.target.style.borderColor = 'rgba(0, 0, 0, 0.09)'}
                />
                <Button
                  size="small"
                  variant="outlined"
                  onClick={handleAddCustomAllergy}
                  disabled={!customAllergy.trim()}
                  sx={{
                    minWidth: '54px',
                    textTransform: 'none',
                    borderColor: 'rgba(0, 0, 0, 0.09)',
                    color: '#37352f',
                    fontSize: '0.8125rem',
                    fontWeight: 500,
                    px: 1.5,
                    py: 0.5,
                    '&:hover': {
                      borderColor: '#ef4444',
                      backgroundColor: 'rgba(239, 68, 68, 0.06)',
                      color: '#ef4444',
                    },
                    '&:disabled': {
                      borderColor: 'rgba(0, 0, 0, 0.06)',
                      color: 'rgba(55, 53, 47, 0.3)',
                    },
                  }}
                >
                  Add
                </Button>
              </Box>
            </Box>
          </Box>

          <Divider sx={{ my: 2.5, borderColor: 'rgba(0, 0, 0, 0.06)' }} />

          {/* Cuisine Preferences */}
          <Box sx={{ mb: 2.5 }}>
            <Typography
              variant="subtitle2"
              sx={{ 
                fontWeight: 600, 
                color: '#37352f', 
                mb: 1.5, 
                display: 'flex', 
                alignItems: 'center', 
                gap: 1,
                fontSize: '0.8125rem',
                letterSpacing: '-0.01em',
                px: 1,
              }}
            >
              🍜 Favorite Cuisines
            </Typography>
            <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5, px: 1, mb: 1.5 }}>
              {CUISINE_TYPES.map((cuisine) => (
                <Chip
                  key={cuisine}
                  label={cuisine}
                  size="small"
                  onClick={() => handleCuisineChange(cuisine)}
                  variant={preferences.cuisinePreferences?.includes(cuisine) ? 'filled' : 'outlined'}
                  sx={{
                    fontSize: '0.75rem',
                    height: '26px',
                    fontWeight: 500,
                    backgroundColor: preferences.cuisinePreferences?.includes(cuisine) 
                      ? 'rgba(16, 185, 129, 0.1)' 
                      : 'transparent',
                    color: preferences.cuisinePreferences?.includes(cuisine) ? '#10b981' : '#787774',
                    border: preferences.cuisinePreferences?.includes(cuisine) 
                      ? '1px solid rgba(16, 185, 129, 0.2)'
                      : '1px solid rgba(0, 0, 0, 0.09)',
                    transition: 'all 0.15s ease',
                    '&:hover': {
                      backgroundColor: preferences.cuisinePreferences?.includes(cuisine) 
                        ? 'rgba(16, 185, 129, 0.15)' 
                        : 'rgba(0, 0, 0, 0.03)',
                      borderColor: preferences.cuisinePreferences?.includes(cuisine)
                        ? 'rgba(16, 185, 129, 0.3)'
                        : 'rgba(0, 0, 0, 0.12)',
                    },
                  }}
                />
              ))}
              {/* Show custom cuisines as chips */}
              {preferences.cuisinePreferences?.filter(c => !CUISINE_TYPES.includes(c)).map((cuisine, idx) => (
                <Chip
                  key={`custom-${idx}`}
                  label={cuisine}
                  size="small"
                  onDelete={() => handleCuisineChange(cuisine)}
                  onClick={() => handleCuisineChange(cuisine)}
                  sx={{
                    fontSize: '0.75rem',
                    height: '26px',
                    backgroundColor: 'rgba(16, 185, 129, 0.1)',
                    color: '#10b981',
                    border: '1px solid rgba(16, 185, 129, 0.2)',
                    fontWeight: 500,
                    '&:hover': {
                      backgroundColor: 'rgba(16, 185, 129, 0.15)',
                      borderColor: 'rgba(16, 185, 129, 0.3)',
                    },
                    '& .MuiChip-deleteIcon': {
                      color: 'rgba(16, 185, 129, 0.6)',
                      fontSize: '16px',
                      '&:hover': {
                        color: '#10b981',
                      },
                    },
                  }}
                />
              ))}
            </Box>

            {/* Custom Cuisine Input */}
            <Box sx={{ px: 1 }}>
              <Box sx={{ display: 'flex', gap: 0.75 }}>
                <input
                  type="text"
                  placeholder="Add custom..."
                  value={customCuisine}
                  onChange={(e) => setCustomCuisine(e.target.value)}
                  onKeyPress={(e) => e.key === 'Enter' && handleAddCustomCuisine()}
                  style={{
                    flex: 1,
                    padding: '7px 10px',
                    fontSize: '0.8125rem',
                    color: '#37352f',
                    border: '1px solid rgba(0, 0, 0, 0.09)',
                    borderRadius: '4px',
                    outline: 'none',
                    fontFamily: 'inherit',
                    transition: 'border-color 0.15s ease',
                    backgroundColor: '#ffffff',
                  }}
                  onFocus={(e) => e.target.style.borderColor = '#10b981'}
                  onBlur={(e) => e.target.style.borderColor = 'rgba(0, 0, 0, 0.09)'}
                />
                <Button
                  size="small"
                  variant="outlined"
                  onClick={handleAddCustomCuisine}
                  disabled={!customCuisine.trim()}
                  sx={{
                    minWidth: '54px',
                    textTransform: 'none',
                    borderColor: 'rgba(0, 0, 0, 0.09)',
                    color: '#37352f',
                    fontSize: '0.8125rem',
                    fontWeight: 500,
                    px: 1.5,
                    py: 0.5,
                    '&:hover': {
                      borderColor: '#10b981',
                      backgroundColor: 'rgba(16, 185, 129, 0.06)',
                      color: '#10b981',
                    },
                    '&:disabled': {
                      borderColor: 'rgba(0, 0, 0, 0.06)',
                      color: 'rgba(55, 53, 47, 0.3)',
                    },
                  }}
                >
                  Add
                </Button>
              </Box>
            </Box>
          </Box>

          <Divider sx={{ my: 2.5, borderColor: 'rgba(0, 0, 0, 0.06)' }} />

          {/* Skill Level */}
          <Box sx={{ mb: 2.5 }}>
            <Typography
              variant="subtitle2"
              sx={{ 
                fontWeight: 600, 
                color: '#37352f', 
                mb: 1.5, 
                display: 'flex', 
                alignItems: 'center', 
                gap: 1,
                fontSize: '0.8125rem',
                letterSpacing: '-0.01em',
                px: 1,
              }}
            >
              👨‍🍳 Cooking Skill Level
            </Typography>
            <RadioGroup
              value={preferences.skillLevel || 'intermediate'}
              onChange={(e) => {
                setPreferences({ ...preferences, skillLevel: e.target.value });
              }}
            >
              <FormControlLabel
                value="beginner"
                control={
                  <Radio 
                    size="small" 
                    sx={{ 
                      color: 'rgba(55, 53, 47, 0.3)',
                      padding: '6px',
                      '&.Mui-checked': { color: '#10b981' },
                      '&:hover': {
                        backgroundColor: 'rgba(0, 0, 0, 0.03)',
                      },
                    }} 
                  />
                }
                label={
                  <Typography 
                    variant="body2" 
                    sx={{ 
                      fontSize: '0.875rem',
                      color: '#37352f',
                      letterSpacing: '-0.01em',
                    }}
                  >
                    Beginner - Simple recipes
                  </Typography>
                }
                sx={{ 
                  mb: 0.25,
                  mx: 0,
                  px: 1,
                  py: 0.5,
                  borderRadius: '4px',
                  transition: 'background-color 0.15s ease',
                  '&:hover': {
                    backgroundColor: 'rgba(0, 0, 0, 0.03)',
                  },
                }}
              />
              <FormControlLabel
                value="intermediate"
                control={
                  <Radio 
                    size="small" 
                    sx={{ 
                      color: 'rgba(55, 53, 47, 0.3)',
                      padding: '6px',
                      '&.Mui-checked': { color: '#10b981' },
                      '&:hover': {
                        backgroundColor: 'rgba(0, 0, 0, 0.03)',
                      },
                    }} 
                  />
                }
                label={
                  <Typography 
                    variant="body2" 
                    sx={{ 
                      fontSize: '0.875rem',
                      color: '#37352f',
                      letterSpacing: '-0.01em',
                    }}
                  >
                    Intermediate - Moderate complexity
                  </Typography>
                }
                sx={{ 
                  mb: 0.25,
                  mx: 0,
                  px: 1,
                  py: 0.5,
                  borderRadius: '4px',
                  transition: 'background-color 0.15s ease',
                  '&:hover': {
                    backgroundColor: 'rgba(0, 0, 0, 0.03)',
                  },
                }}
              />
              <FormControlLabel
                value="advanced"
                control={
                  <Radio 
                    size="small" 
                    sx={{ 
                      color: 'rgba(55, 53, 47, 0.3)',
                      padding: '6px',
                      '&.Mui-checked': { color: '#10b981' },
                      '&:hover': {
                        backgroundColor: 'rgba(0, 0, 0, 0.03)',
                      },
                    }} 
                  />
                }
                label={
                  <Typography 
                    variant="body2" 
                    sx={{ 
                      fontSize: '0.875rem',
                      color: '#37352f',
                      letterSpacing: '-0.01em',
                    }}
                  >
                    Advanced - Complex techniques
                  </Typography>
                }
                sx={{ 
                  mb: 0.25,
                  mx: 0,
                  px: 1,
                  py: 0.5,
                  borderRadius: '4px',
                  transition: 'background-color 0.15s ease',
                  '&:hover': {
                    backgroundColor: 'rgba(0, 0, 0, 0.03)',
                  },
                }}
              />
            </RadioGroup>
          </Box>
        </Box>
      </Box>
    </Drawer>
  );
}

export default Sidebar;
