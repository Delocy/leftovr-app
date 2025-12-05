import React, { useState } from 'react';
import {
  Box,
  Typography,
  TextField,
  Button,
  Grid,
  Card,
  CardContent,
  CardActions,
  Chip,
  CircularProgress,
  Alert,
} from '@mui/material';
import SearchIcon from '@mui/icons-material/Search';
import RestaurantMenuIcon from '@mui/icons-material/RestaurantMenu';
import axios from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

function RecipeSearch() {
  const [searchQuery, setSearchQuery] = useState('');
  const [recipes, setRecipes] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSearch = async () => {
    if (!searchQuery.trim()) {
      setError('Please enter a search query');
      return;
    }

    setLoading(true);
    setError('');
    setRecipes([]);

    try {
      const response = await axios.post(`${API_BASE_URL}/recipes/search`, {
        query: searchQuery,
        limit: 10
      });

      setRecipes(response.data.recipes || []);
      
      if (response.data.recipes?.length === 0) {
        setError('No recipes found. Try a different search term.');
      }
    } catch (err) {
      setError('Failed to search recipes: ' + (err.response?.data?.detail || err.message));
      console.error('Error searching recipes:', err);
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
    <Box sx={{ display: 'flex', flexDirection: 'column', height: '100%', backgroundColor: '#ffffff' }}>
      {/* Content */}
      <Box
        sx={{
          flexGrow: 1,
          overflow: 'auto',
          px: 3,
          py: 3,
        }}
      >
        {/* Search Bar */}
        <Box sx={{ mb: 4, maxWidth: 800 }}>
          <Box display="flex" gap={2}>
            <TextField
              fullWidth
              placeholder="Search for recipes... (e.g., chicken pasta, vegetarian soup)"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              onKeyPress={handleKeyPress}
              disabled={loading}
              variant="outlined"
              sx={{
                '& .MuiOutlinedInput-root': {
                  borderRadius: 1,
                  backgroundColor: '#f7f6f3',
                  '&:hover': {
                    backgroundColor: '#f1f1ef',
                  },
                },
              }}
            />
            <Button
              variant="contained"
              startIcon={loading ? <CircularProgress size={20} color="inherit" /> : <SearchIcon />}
              onClick={handleSearch}
              disabled={loading}
              sx={{
                minWidth: 120,
                textTransform: 'none',
                fontWeight: 600,
              }}
            >
              {loading ? 'Searching...' : 'Search'}
            </Button>
          </Box>
        </Box>

        {/* Error Message */}
        {error && (
          <Alert severity="error" sx={{ mb: 3, maxWidth: 800 }}>
            {error}
          </Alert>
        )}

        {/* Results */}
        {recipes.length > 0 && (
          <>
            <Typography variant="h6" sx={{ mb: 2, fontWeight: 600 }}>
              Found {recipes.length} recipes
            </Typography>
            <Grid container spacing={2}>
              {recipes.map((recipe, index) => (
                <Grid item xs={12} sm={6} md={4} key={recipe.id || index}>
                  <Card
                    sx={{
                      height: '100%',
                      display: 'flex',
                      flexDirection: 'column',
                      border: '1px solid #e9e9e7',
                      boxShadow: 'none',
                      transition: 'all 0.2s',
                      '&:hover': {
                        boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
                        transform: 'translateY(-2px)',
                      },
                    }}
                  >
                    <CardContent sx={{ flexGrow: 1, p: 2.5 }}>
                      <Typography variant="h6" sx={{ fontWeight: 600, mb: 1.5, color: '#37352f' }}>
                        {recipe.title || recipe.name}
                      </Typography>

                      {recipe.description && (
                        <Typography variant="body2" color="text.secondary" sx={{ mb: 2, lineHeight: 1.6 }}>
                          {recipe.description.length > 120
                            ? `${recipe.description.substring(0, 120)}...`
                            : recipe.description}
                        </Typography>
                      )}

                      {recipe.ingredients && (
                        <Box sx={{ mb: 2 }}>
                          <Typography variant="caption" sx={{ fontWeight: 600, color: '#787774', mb: 0.5, display: 'block' }}>
                            Ingredients
                          </Typography>
                          <Box display="flex" flexWrap="wrap" gap={0.5}>
                            {recipe.ingredients.slice(0, 4).map((ing, idx) => (
                              <Chip
                                key={idx}
                                label={ing}
                                size="small"
                                variant="outlined"
                                sx={{
                                  fontSize: '0.7rem',
                                  height: 22,
                                  borderColor: '#e9e9e7',
                                }}
                              />
                            ))}
                            {recipe.ingredients.length > 4 && (
                              <Chip
                                label={`+${recipe.ingredients.length - 4}`}
                                size="small"
                                sx={{
                                  fontSize: '0.7rem',
                                  height: 22,
                                  backgroundColor: '#f7f6f3',
                                }}
                              />
                            )}
                          </Box>
                        </Box>
                      )}

                      {recipe.score && (
                        <Typography variant="caption" sx={{ color: '#27ae60', fontWeight: 600 }}>
                          {(recipe.score * 100).toFixed(0)}% match
                        </Typography>
                      )}
                    </CardContent>

                    <CardActions sx={{ p: 2, pt: 0 }}>
                      <Button
                        size="small"
                        sx={{
                          textTransform: 'none',
                          fontWeight: 500,
                          color: '#10b981',
                        }}
                      >
                        View Details
                      </Button>
                    </CardActions>
                  </Card>
                </Grid>
              ))}
            </Grid>
          </>
        )}

        {/* Loading State */}
        {loading && (
          <Box display="flex" justifyContent="center" alignItems="center" minHeight={200}>
            <CircularProgress />
          </Box>
        )}

        {/* Empty State */}
        {!loading && recipes.length === 0 && !error && searchQuery === '' && (
          <Box
            sx={{
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              justifyContent: 'center',
              minHeight: 400,
              textAlign: 'center',
            }}
          >
            <RestaurantMenuIcon sx={{ fontSize: 80, color: '#e9e9e7', mb: 2 }} />
            <Typography variant="h6" sx={{ fontWeight: 600, mb: 1, color: '#37352f' }}>
              Search for Recipes
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Enter ingredients or dish names to find delicious recipes
            </Typography>
          </Box>
        )}
      </Box>
    </Box>
  );
}

export default RecipeSearch;
