import React, { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  TextField,
  Button,
  Grid,
  Card,
  CardContent,
  IconButton,
  Chip,
  CircularProgress,
  Alert,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  InputAdornment,
} from '@mui/material';
import AddIcon from '@mui/icons-material/Add';
import DeleteIcon from '@mui/icons-material/Delete';
import EditIcon from '@mui/icons-material/Edit';
import SearchIcon from '@mui/icons-material/Search';
import KitchenIcon from '@mui/icons-material/Kitchen';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import axios from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

function PantryPage({ pantryItems, setPantryItems }) {
  const [newItem, setNewItem] = useState({
    ingredient_name: '',
    quantity: '',
    expire_date: '',
  });
  const [searchQuery, setSearchQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  useEffect(() => {
    fetchPantryItems();
  }, []);

  const fetchPantryItems = async () => {
    setLoading(true);
    try {
      const response = await axios.get(`${API_BASE_URL}/pantry/inventory`);
      setPantryItems(response.data.items || []);
    } catch (err) {
      setError('Failed to fetch pantry items');
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
      await axios.post(`${API_BASE_URL}/pantry/add`, {
        ingredient_name: newItem.ingredient_name,
        quantity: parseInt(newItem.quantity),
        expire_date: newItem.expire_date || undefined,
      });

      setSuccess(`Added ${newItem.ingredient_name}!`);
      setNewItem({ ingredient_name: '', quantity: '', expire_date: '' });
      await fetchPantryItems();
      
      setTimeout(() => setSuccess(''), 3000);
    } catch (err) {
      setError('Failed to add item');
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteItem = async (itemId) => {
    try {
      await axios.delete(`${API_BASE_URL}/pantry/remove/${itemId}`);
      setSuccess('Item removed');
      await fetchPantryItems();
      setTimeout(() => setSuccess(''), 2000);
    } catch (err) {
      setError('Failed to remove item');
    }
  };

  const getExpiryStatus = (expireDate) => {
    if (!expireDate) return null;
    const today = new Date();
    const expiry = new Date(expireDate);
    const daysUntilExpiry = Math.ceil((expiry - today) / (1000 * 60 * 60 * 24));

    if (daysUntilExpiry < 0) return { color: '#ef4444', text: 'Expired', bgColor: '#fef2f2' };
    if (daysUntilExpiry <= 3) return { color: '#f59e0b', text: `${daysUntilExpiry} days left`, bgColor: '#fffbeb' };
    return { color: '#10b981', text: `${daysUntilExpiry} days left`, bgColor: '#f0fdf4' };
  };

  const filteredItems = pantryItems.filter((item) =>
    (item.name || item.ingredient_name || '').toLowerCase().includes(searchQuery.toLowerCase())
  );

  const expiringItems = pantryItems.filter((item) => {
    if (!item.expire_date) return false;
    const expiry = new Date(item.expire_date);
    const today = new Date();
    const daysUntilExpiry = Math.ceil((expiry - today) / (1000 * 60 * 60 * 24));
    return daysUntilExpiry >= 0 && daysUntilExpiry <= 3;
  });

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', height: '100%', backgroundColor: '#ffffff' }}>
      {/* Content */}
      <Box
        sx={{
          flexGrow: 1,
          overflow: 'auto',
          px: { xs: 2, md: 4 },
          py: 3,
        }}
      >
        {/* Page Title */}
        <Box sx={{ mb: 4, maxWidth: 1200, mx: 'auto' }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 1 }}>
            <Box
              sx={{
                width: 48,
                height: 48,
                borderRadius: 2,
                backgroundColor: '#10b981',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
              }}
            >
              <KitchenIcon sx={{ color: '#ffffff', fontSize: 28 }} />
            </Box>
            <Typography variant="h4" sx={{ fontWeight: 700, color: '#1f2937' }}>
              My Pantry
            </Typography>
          </Box>
          <Typography variant="body1" color="text.secondary">
            Manage your ingredients and track expiration dates
          </Typography>
        </Box>

        <Box sx={{ maxWidth: 1200, mx: 'auto' }}>
          {/* Alerts */}
          {error && <Alert severity="error" sx={{ mb: 3 }} onClose={() => setError('')}>{error}</Alert>}
          {success && <Alert severity="success" sx={{ mb: 3 }} onClose={() => setSuccess('')}>{success}</Alert>}

          {/* Expiring Soon Warning */}
          {expiringItems.length > 0 && (
            <Alert 
              severity="warning" 
              sx={{ mb: 3 }}
              icon={<KitchenIcon />}
            >
              <Typography variant="subtitle2" sx={{ fontWeight: 600 }}>
                {expiringItems.length} item{expiringItems.length > 1 ? 's' : ''} expiring soon!
              </Typography>
              <Typography variant="body2">
                {expiringItems.map(item => item.name || item.ingredient_name).join(', ')}
              </Typography>
            </Alert>
          )}

          <Grid container spacing={3}>
            {/* Add New Item Card */}
            <Grid item xs={12} md={4}>
              <Card 
                elevation={0}
                sx={{ 
                  border: '1px solid #e5e7eb',
                  height: '100%',
                }}
              >
                <CardContent sx={{ p: 3 }}>
                  <Typography variant="h6" sx={{ fontWeight: 600, mb: 3, color: '#1f2937' }}>
                    Add New Ingredient
                  </Typography>
                  
                  <TextField
                    fullWidth
                    label="Ingredient Name"
                    placeholder="e.g., Chicken breast"
                    value={newItem.ingredient_name}
                    onChange={(e) => setNewItem({ ...newItem, ingredient_name: e.target.value })}
                    sx={{ mb: 2 }}
                    size="medium"
                  />
                  
                  <TextField
                    fullWidth
                    label="Quantity"
                    type="number"
                    placeholder="e.g., 2"
                    value={newItem.quantity}
                    onChange={(e) => setNewItem({ ...newItem, quantity: e.target.value })}
                    sx={{ mb: 2 }}
                    size="medium"
                  />
                  
                  <TextField
                    fullWidth
                    label="Expiration Date"
                    type="date"
                    value={newItem.expire_date}
                    onChange={(e) => setNewItem({ ...newItem, expire_date: e.target.value })}
                    InputLabelProps={{ shrink: true }}
                    sx={{ mb: 3 }}
                    size="medium"
                  />
                  
                  <Button
                    fullWidth
                    size="large"
                    variant="contained"
                    startIcon={<AddIcon />}
                    onClick={handleAddItem}
                    disabled={loading || !newItem.ingredient_name || !newItem.quantity}
                    sx={{
                      textTransform: 'none',
                      fontWeight: 600,
                      py: 1.5,
                    }}
                  >
                    Add to Pantry
                  </Button>
                </CardContent>
              </Card>
            </Grid>

            {/* Pantry Stats & Search */}
            <Grid item xs={12} md={8}>
              <Box sx={{ mb: 3 }}>
                <Grid container spacing={2}>
                  <Grid item xs={12} sm={4}>
                    <Paper
                      elevation={0}
                      sx={{
                        p: 2.5,
                        border: '1px solid #e5e7eb',
                        textAlign: 'center',
                      }}
                    >
                      <Typography variant="h3" sx={{ fontWeight: 700, color: '#10b981', mb: 0.5 }}>
                        {pantryItems.length}
                      </Typography>
                      <Typography variant="body2" color="text.secondary">
                        Total Items
                      </Typography>
                    </Paper>
                  </Grid>
                  <Grid item xs={12} sm={4}>
                    <Paper
                      elevation={0}
                      sx={{
                        p: 2.5,
                        border: '1px solid #e5e7eb',
                        textAlign: 'center',
                      }}
                    >
                      <Typography variant="h3" sx={{ fontWeight: 700, color: '#f59e0b', mb: 0.5 }}>
                        {expiringItems.length}
                      </Typography>
                      <Typography variant="body2" color="text.secondary">
                        Expiring Soon
                      </Typography>
                    </Paper>
                  </Grid>
                  <Grid item xs={12} sm={4}>
                    <Paper
                      elevation={0}
                      sx={{
                        p: 2.5,
                        border: '1px solid #e5e7eb',
                        textAlign: 'center',
                      }}
                    >
                      <Typography variant="h3" sx={{ fontWeight: 700, color: '#6b7280', mb: 0.5 }}>
                        {new Set(pantryItems.map(item => item.name || item.ingredient_name)).size}
                      </Typography>
                      <Typography variant="body2" color="text.secondary">
                        Unique Items
                      </Typography>
                    </Paper>
                  </Grid>
                </Grid>
              </Box>

              {/* Search */}
              <TextField
                fullWidth
                placeholder="Search ingredients..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                InputProps={{
                  startAdornment: (
                    <InputAdornment position="start">
                      <SearchIcon sx={{ color: '#9ca3af' }} />
                    </InputAdornment>
                  ),
                }}
                sx={{
                  mb: 3,
                  '& .MuiOutlinedInput-root': {
                    backgroundColor: '#f9fafb',
                  },
                }}
              />
            </Grid>
          </Grid>

          {/* Pantry Items Table */}
          <Box sx={{ mt: 4 }}>
            <Typography variant="h6" sx={{ fontWeight: 600, mb: 2, color: '#1f2937' }}>
              Inventory ({filteredItems.length} items)
            </Typography>
            
            {loading && pantryItems.length === 0 ? (
              <Box display="flex" justifyContent="center" py={8}>
                <CircularProgress />
              </Box>
            ) : filteredItems.length === 0 ? (
              <Paper
                elevation={0}
                sx={{
                  p: 8,
                  textAlign: 'center',
                  border: '1px solid #e5e7eb',
                }}
              >
                <KitchenIcon sx={{ fontSize: 64, color: '#e5e7eb', mb: 2 }} />
                <Typography variant="h6" sx={{ mb: 1, color: '#6b7280' }}>
                  {searchQuery ? 'No items found' : 'Your pantry is empty'}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  {searchQuery ? 'Try a different search term' : 'Add your first ingredient to get started'}
                </Typography>
              </Paper>
            ) : (
              <TableContainer 
                component={Paper} 
                elevation={0}
                sx={{ border: '1px solid #e5e7eb' }}
              >
                <Table>
                  <TableHead>
                    <TableRow sx={{ backgroundColor: '#f9fafb' }}>
                      <TableCell sx={{ fontWeight: 600, color: '#374151' }}>Ingredient</TableCell>
                      <TableCell sx={{ fontWeight: 600, color: '#374151' }}>Quantity</TableCell>
                      <TableCell sx={{ fontWeight: 600, color: '#374151' }}>Expiration</TableCell>
                      <TableCell sx={{ fontWeight: 600, color: '#374151' }}>Status</TableCell>
                      <TableCell align="right" sx={{ fontWeight: 600, color: '#374151' }}>Actions</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {filteredItems.map((item) => {
                      const expiryStatus = getExpiryStatus(item.expire_date);
                      return (
                        <TableRow 
                          key={item.id}
                          sx={{ 
                            '&:hover': { backgroundColor: '#f9fafb' },
                            '&:last-child td': { border: 0 },
                          }}
                        >
                          <TableCell>
                            <Typography variant="body2" sx={{ fontWeight: 500, color: '#1f2937' }}>
                              {item.name || item.ingredient_name}
                            </Typography>
                          </TableCell>
                          <TableCell>
                            <Typography variant="body2" color="text.secondary">
                              {item.quantity}
                            </Typography>
                          </TableCell>
                          <TableCell>
                            <Typography variant="body2" color="text.secondary">
                              {item.expire_date || 'No date set'}
                            </Typography>
                          </TableCell>
                          <TableCell>
                            {expiryStatus ? (
                              <Chip
                                label={expiryStatus.text}
                                size="small"
                                sx={{
                                  fontWeight: 600,
                                  fontSize: '0.75rem',
                                  backgroundColor: expiryStatus.bgColor,
                                  color: expiryStatus.color,
                                  border: 'none',
                                }}
                              />
                            ) : (
                              <Chip
                                label="No expiry"
                                size="small"
                                sx={{
                                  fontWeight: 500,
                                  fontSize: '0.75rem',
                                  backgroundColor: '#f3f4f6',
                                  color: '#6b7280',
                                }}
                              />
                            )}
                          </TableCell>
                          <TableCell align="right">
                            <IconButton
                              size="small"
                              onClick={() => handleDeleteItem(item.id)}
                              sx={{
                                color: '#ef4444',
                                '&:hover': { backgroundColor: '#fef2f2' },
                              }}
                            >
                              <DeleteIcon fontSize="small" />
                            </IconButton>
                          </TableCell>
                        </TableRow>
                      );
                    })}
                  </TableBody>
                </Table>
              </TableContainer>
            )}
          </Box>
        </Box>
      </Box>
    </Box>
  );
}

export default PantryPage;
