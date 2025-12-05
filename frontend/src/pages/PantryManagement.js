import React, { useState, useEffect } from 'react';
import {
  Box,
  Paper,
  Typography,
  TextField,
  Button,
  List,
  ListItem,
  ListItemText,
  ListItemSecondaryAction,
  IconButton,
  Grid,
  Alert,
  CircularProgress
} from '@mui/material';
import DeleteIcon from '@mui/icons-material/Delete';
import AddIcon from '@mui/icons-material/Add';
import axios from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

function PantryManagement({ pantryItems, setPantryItems }) {
  const [newItem, setNewItem] = useState({
    ingredient_name: '',
    quantity: '',
    expire_date: ''
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  // Fetch pantry items on component mount
  useEffect(() => {
    fetchPantryItems();
  }, []);

  const fetchPantryItems = async () => {
    setLoading(true);
    setError('');
    try {
      const response = await axios.get(`${API_BASE_URL}/pantry/inventory`);
      setPantryItems(response.data.items || []);
    } catch (err) {
      setError('Failed to fetch pantry items: ' + err.message);
      console.error('Error fetching pantry:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleAddItem = async () => {
    if (!newItem.ingredient_name || !newItem.quantity) {
      setError('Please fill in ingredient name and quantity');
      return;
    }

    setLoading(true);
    setError('');
    setSuccess('');

    try {
      const response = await axios.post(`${API_BASE_URL}/pantry/add`, {
        ingredient_name: newItem.ingredient_name,
        quantity: parseInt(newItem.quantity),
        expire_date: newItem.expire_date || undefined
      });

      setSuccess(`Added ${newItem.ingredient_name} to pantry!`);
      setNewItem({ ingredient_name: '', quantity: '', expire_date: '' });
      
      // Refresh pantry items
      await fetchPantryItems();
    } catch (err) {
      setError('Failed to add item: ' + (err.response?.data?.detail || err.message));
      console.error('Error adding item:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteItem = async (itemId) => {
    setLoading(true);
    setError('');
    
    try {
      await axios.delete(`${API_BASE_URL}/pantry/remove/${itemId}`);
      setSuccess('Item removed from pantry');
      await fetchPantryItems();
    } catch (err) {
      setError('Failed to remove item: ' + (err.response?.data?.detail || err.message));
      console.error('Error removing item:', err);
    } finally {
      setLoading(false);
    }
  };

  const getExpiryColor = (expireDate) => {
    if (!expireDate) return 'text.secondary';
    
    const today = new Date();
    const expiry = new Date(expireDate);
    const daysUntilExpiry = Math.ceil((expiry - today) / (1000 * 60 * 60 * 24));
    
    if (daysUntilExpiry < 0) return 'error.main';
    if (daysUntilExpiry <= 3) return 'warning.main';
    return 'success.main';
  };

  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        Pantry Management
      </Typography>

      {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}
      {success && <Alert severity="success" sx={{ mb: 2 }}>{success}</Alert>}

      <Grid container spacing={3}>
        {/* Add Item Form */}
        <Grid item xs={12} md={6}>
          <Paper sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom>
              Add New Item
            </Typography>
            <Box component="form" sx={{ mt: 2 }}>
              <TextField
                fullWidth
                label="Ingredient Name"
                value={newItem.ingredient_name}
                onChange={(e) => setNewItem({ ...newItem, ingredient_name: e.target.value })}
                margin="normal"
                required
              />
              <TextField
                fullWidth
                label="Quantity"
                type="number"
                value={newItem.quantity}
                onChange={(e) => setNewItem({ ...newItem, quantity: e.target.value })}
                margin="normal"
                required
              />
              <TextField
                fullWidth
                label="Expiration Date"
                type="date"
                value={newItem.expire_date}
                onChange={(e) => setNewItem({ ...newItem, expire_date: e.target.value })}
                margin="normal"
                InputLabelProps={{ shrink: true }}
              />
              <Button
                fullWidth
                variant="contained"
                startIcon={<AddIcon />}
                onClick={handleAddItem}
                disabled={loading}
                sx={{ mt: 2 }}
              >
                {loading ? <CircularProgress size={24} /> : 'Add to Pantry'}
              </Button>
            </Box>
          </Paper>
        </Grid>

        {/* Pantry List */}
        <Grid item xs={12} md={6}>
          <Paper sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom>
              Current Inventory ({pantryItems.length} items)
            </Typography>
            {loading && pantryItems.length === 0 ? (
              <Box display="flex" justifyContent="center" py={4}>
                <CircularProgress />
              </Box>
            ) : pantryItems.length === 0 ? (
              <Typography color="text.secondary" sx={{ py: 4, textAlign: 'center' }}>
                Your pantry is empty. Add some items to get started!
              </Typography>
            ) : (
              <List>
                {pantryItems.map((item) => (
                  <ListItem key={item.id} divider>
                    <ListItemText
                      primary={item.name || item.ingredient_name}
                      secondary={
                        <>
                          Quantity: {item.quantity}
                          {item.expire_date && (
                            <Typography
                              component="span"
                              variant="body2"
                              sx={{ display: 'block', color: getExpiryColor(item.expire_date) }}
                            >
                              Expires: {item.expire_date}
                            </Typography>
                          )}
                        </>
                      }
                    />
                    <ListItemSecondaryAction>
                      <IconButton
                        edge="end"
                        onClick={() => handleDeleteItem(item.id)}
                        disabled={loading}
                      >
                        <DeleteIcon />
                      </IconButton>
                    </ListItemSecondaryAction>
                  </ListItem>
                ))}
              </List>
            )}
          </Paper>
        </Grid>
      </Grid>
    </Box>
  );
}

export default PantryManagement;
