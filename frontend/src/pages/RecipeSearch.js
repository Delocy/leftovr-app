import React, { useState } from 'react';
import {
  Box,
  Typography,
  TextField,
  Button,
  Card,
  Chip,
  CircularProgress,
  Link,
  Stack,
  alpha,
} from '@mui/material';
import SearchIcon from '@mui/icons-material/Search';
import RestaurantMenuIcon from '@mui/icons-material/RestaurantMenu';
import OpenInNewIcon from '@mui/icons-material/OpenInNew';
import { searchRecipes } from '../services/api';

const RecipeSearch = () => {
  const [query, setQuery] = useState('');
  const [recipes, setRecipes] = useState([]);
  const [loading, setLoading] = useState(false);
  const [searched, setSearched] = useState(false);

  const handleSearch = async () => {
    if (!query.trim()) return;

    setLoading(true);
    setSearched(true);
    try {
      const response = await searchRecipes(query);
      setRecipes(response.recipes || []);
    } catch (error) {
      console.error('Search failed:', error);
      setRecipes([]);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter') {
      handleSearch();
    }
  };

  return (
    <Box sx={{ bgcolor: '#fafafa', minHeight: 'calc(100vh - 64px)', p: 4 }}>
      <Box sx={{ maxWidth: 1200, mx: 'auto' }}>
        {/* Header */}
        <Box sx={{ mb: 4 }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 1 }}>
            <RestaurantMenuIcon sx={{ fontSize: 32, color: '#4caf50' }} />
            <Typography variant="h4" sx={{ fontSize: '28px', fontWeight: 700, color: '#37352f', letterSpacing: '-0.5px' }}>
              Recipe Search
            </Typography>
          </Box>
          <Typography variant="body1" sx={{ fontSize: '15px', color: '#787774', ml: 6 }}>
            Search for recipes based on ingredients, cuisine, or dietary preferences
          </Typography>
        </Box>

        {/* Search Bar */}
        <Box 
          sx={{ 
            bgcolor: '#ffffff',
            border: '1px solid #e0e0e0',
            borderRadius: 2,
            p: 3,
            mb: 4,
          }}
        >
          <Box sx={{ display: 'flex', gap: 2 }}>
            <TextField
              fullWidth
              placeholder="e.g., chicken pasta, vegan dessert, gluten-free..."
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyPress={handleKeyPress}
              variant="outlined"
              sx={{
                '& .MuiOutlinedInput-root': {
                  fontSize: '15px',
                  color: '#37352f',
                  bgcolor: '#f7f6f3',
                  '& fieldset': {
                    borderColor: 'transparent',
                  },
                  '&:hover fieldset': {
                    borderColor: '#e0e0e0',
                  },
                  '&.Mui-focused fieldset': {
                    borderColor: '#4caf50',
                    borderWidth: '1px',
                  },
                },
                '& .MuiInputBase-input::placeholder': {
                  color: '#9b9a97',
                  opacity: 1,
                },
              }}
            />
            <Button
              variant="contained"
              startIcon={<SearchIcon />}
              onClick={handleSearch}
              disabled={loading || !query.trim()}
              sx={{
                bgcolor: '#4caf50',
                color: '#ffffff',
                textTransform: 'none',
                fontSize: '14px',
                fontWeight: 500,
                px: 3,
                minWidth: 120,
                '&:hover': { bgcolor: '#45a049' },
                '&:disabled': {
                  bgcolor: '#f7f6f3',
                  color: '#d1d0ce',
                },
              }}
            >
              Search
            </Button>
          </Box>
        </Box>

        {/* Loading State */}
        {loading && (
          <Box sx={{ display: 'flex', justifyContent: 'center', py: 8 }}>
            <CircularProgress sx={{ color: '#4caf50' }} />
          </Box>
        )}

        {/* No Results */}
        {!loading && searched && recipes.length === 0 && (
          <Box
            sx={{
              bgcolor: '#ffffff',
              border: '1px solid #e0e0e0',
              borderRadius: 2,
              p: 8,
              textAlign: 'center',
            }}
          >
            <RestaurantMenuIcon sx={{ fontSize: 64, color: '#d1d0ce', mb: 2 }} />
            <Typography variant="h6" sx={{ fontSize: '16px', fontWeight: 500, color: '#37352f', mb: 1 }}>
              No recipes found
            </Typography>
            <Typography variant="body2" sx={{ fontSize: '14px', color: '#9b9a97' }}>
              Try a different search term or ingredient combination
            </Typography>
          </Box>
        )}

        {/* Recipe Results */}
        {!loading && recipes.length > 0 && (
          <Stack spacing={2}>
            {recipes.map((recipe, index) => (
              <Card
                key={index}
                sx={{
                  bgcolor: '#ffffff',
                  border: '1px solid #e0e0e0',
                  borderRadius: 2,
                  transition: 'all 0.2s',
                  '&:hover': {
                    borderColor: '#4caf50',
                    boxShadow: '0 2px 12px rgba(76, 175, 80, 0.1)',
                  },
                }}
                elevation={0}
              >
                <Box sx={{ p: 3 }}>
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 2 }}>
                    <Box sx={{ flexGrow: 1, pr: 2 }}>
                      <Typography variant="h6" sx={{ fontSize: '18px', fontWeight: 600, color: '#37352f', mb: 0.5 }}>
                        {recipe.title}
                      </Typography>
                      {recipe.match_percentage && (
                        <Chip
                          label={`${recipe.match_percentage}% match`}
                          size="small"
                          sx={{
                            bgcolor: alpha('#4caf50', 0.1),
                            color: '#4caf50',
                            fontSize: '12px',
                            fontWeight: 500,
                            height: 24,
                          }}
                        />
                      )}
                    </Box>
                  </Box>

                  {recipe.source && (
                    <Typography variant="caption" sx={{ fontSize: '12px', color: '#9b9a97', display: 'block', mb: 1 }}>
                      Source: {recipe.source}
                    </Typography>
                  )}

                  {recipe.recommendation_reason && (
                    <Typography variant="body2" sx={{ fontSize: '14px', color: '#787774', mt: 2 }}>
                      💡 {recipe.recommendation_reason}
                    </Typography>
                  )}

                  {recipe.ner && recipe.ner.length > 0 && (
                    <Box sx={{ mt: 2 }}>
                      <Typography variant="caption" sx={{ fontSize: '12px', color: '#9b9a97', display: 'block', mb: 1 }}>
                        Key Ingredients:
                      </Typography>
                      <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.75 }}>
                        {recipe.ner.slice(0, 5).map((ingredient, idx) => (
                          <Chip
                            key={idx}
                            label={ingredient}
                            size="small"
                            sx={{
                              bgcolor: '#f7f6f3',
                              color: '#37352f',
                              fontSize: '12px',
                              border: '1px solid #e0e0e0',
                            }}
                          />
                        ))}
                        {recipe.ner.length > 5 && (
                          <Chip
                            label={`+${recipe.ner.length - 5} more`}
                            size="small"
                            sx={{
                              bgcolor: '#f7f6f3',
                              color: '#37352f',
                              fontSize: '12px',
                              border: '1px solid #e0e0e0',
                            }}
                          />
                        )}
                      </Box>
                    </Box>
                  )}

                  {recipe.link && (
                    <Button
                      component={Link}
                      href={recipe.link.startsWith('http') ? recipe.link : `https://${recipe.link}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      endIcon={<OpenInNewIcon sx={{ fontSize: 16 }} />}
                      sx={{
                        mt: 2,
                        textTransform: 'none',
                        fontSize: '14px',
                        fontWeight: 500,
                        color: '#4caf50',
                        '&:hover': {
                          bgcolor: alpha('#4caf50', 0.1),
                        },
                      }}
                    >
                      View Recipe
                    </Button>
                  )}
                </Box>
              </Card>
            ))}
          </Stack>
        )}
      </Box>
    </Box>
  );
};

export default RecipeSearch;
