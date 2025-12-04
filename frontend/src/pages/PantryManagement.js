import React, { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  Button,
  TextField,
  IconButton,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Chip,
  Stack,
  alpha,
} from '@mui/material';
import AddIcon from '@mui/icons-material/Add';
import DeleteIcon from '@mui/icons-material/Delete';
import EditIcon from '@mui/icons-material/Edit';
import KitchenIcon from '@mui/icons-material/Kitchen';
import {
  getPantryInventory,
  addPantryItem,
  updatePantryItem,
  deletePantryItem,
} from '../services/api';

const PantryManagement = () => {
  const [inventory, setInventory] = useState([]);
  const [openDialog, setOpenDialog] = useState(false);
  const [editMode, setEditMode] = useState(false);
  const [currentItem, setCurrentItem] = useState({
    ingredient_name: '',
    quantity: '',
    unit: '',
    expiration_date: '',
  });

  useEffect(() => {
    fetchInventory();
  }, []);

  const fetchInventory = async () => {
    try {
      const data = await getPantryInventory();
      setInventory(data.inventory || []);
    } catch (err) {
      console.error('Failed to fetch inventory:', err);
    }
  };

  const handleOpenDialog = (item = null) => {
    if (item) {
      setCurrentItem(item);
      setEditMode(true);
    } else {
      setCurrentItem({
        ingredient_name: '',
        quantity: '',
        unit: '',
        expiration_date: '',
      });
      setEditMode(false);
    }
    setOpenDialog(true);
  };

  const handleCloseDialog = () => {
    setOpenDialog(false);
    setCurrentItem({
      ingredient_name: '',
      quantity: '',
      unit: '',
      expiration_date: '',
    });
  };

  const handleSave = async () => {
    try {
      if (editMode) {
        await updatePantryItem(currentItem.ingredient_name, currentItem);
      } else {
        await addPantryItem(currentItem);
      }
      await fetchInventory();
      handleCloseDialog();
    } catch (err) {
      console.error(`Failed to ${editMode ? 'update' : 'add'} item:`, err);
    }
  };

  const handleDelete = async (itemName) => {
    if (window.confirm(`Are you sure you want to delete ${itemName}?`)) {
      try {
        await deletePantryItem(itemName);
        await fetchInventory();
      } catch (err) {
        console.error('Failed to delete item:', err);
      }
    }
  };

  const isExpiringSoon = (expirationDate) => {
    if (!expirationDate) return false;
    const today = new Date();
    const expDate = new Date(expirationDate);
    const daysUntilExpiry = Math.ceil((expDate - today) / (1000 * 60 * 60 * 24));
    return daysUntilExpiry <= 3 && daysUntilExpiry >= 0;
  };

  return (
    <Box sx={{ bgcolor: '#fafafa', minHeight: 'calc(100vh - 64px)', p: 4 }}>
      <Box sx={{ maxWidth: 1200, mx: 'auto' }}>
        {/* Header */}
        <Box sx={{ mb: 4 }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 1 }}>
            <KitchenIcon sx={{ fontSize: 32, color: '#4caf50' }} />
            <Typography variant="h4" sx={{ fontSize: '28px', fontWeight: 700, color: '#37352f', letterSpacing: '-0.5px' }}>
              Pantry Management
            </Typography>
          </Box>
          <Typography variant="body1" sx={{ fontSize: '15px', color: '#787774', ml: 6 }}>
            Manage your ingredients and track expiration dates
          </Typography>
        </Box>

        {/* Add Button */}
        <Button
          variant="contained"
          startIcon={<AddIcon />}
          onClick={() => handleOpenDialog()}
          sx={{
            bgcolor: '#4caf50',
            color: '#ffffff',
            textTransform: 'none',
            fontSize: '14px',
            fontWeight: 500,
            px: 3,
            py: 1,
            borderRadius: 1.5,
            mb: 3,
            '&:hover': { bgcolor: '#45a049' },
          }}
        >
          Add Item
        </Button>

        {/* Pantry Items Grid */}
        {inventory.length === 0 ? (
          <Box
            sx={{
              bgcolor: '#ffffff',
              border: '1px solid #e0e0e0',
              borderRadius: 2,
              p: 8,
              textAlign: 'center',
            }}
          >
            <KitchenIcon sx={{ fontSize: 64, color: '#d1d0ce', mb: 2 }} />
            <Typography variant="h6" sx={{ fontSize: '16px', fontWeight: 500, color: '#37352f', mb: 1 }}>
              Your pantry is empty
            </Typography>
            <Typography variant="body2" sx={{ fontSize: '14px', color: '#9b9a97' }}>
              Start adding ingredients to track your inventory
            </Typography>
          </Box>
        ) : (
          <Stack spacing={2}>
            {inventory.map((item) => (
              <Box
                key={item.ingredient_name}
                sx={{
                  bgcolor: '#ffffff',
                  border: '1px solid #e0e0e0',
                  borderRadius: 2,
                  p: 3,
                  display: 'flex',
                  alignItems: 'center',
                  gap: 3,
                  transition: 'all 0.2s',
                  '&:hover': {
                    borderColor: '#4caf50',
                    boxShadow: '0 2px 8px rgba(76, 175, 80, 0.1)',
                  },
                }}
              >
                <Box sx={{ flexGrow: 1 }}>
                  <Typography variant="h6" sx={{ fontSize: '16px', fontWeight: 600, color: '#37352f', mb: 0.5 }}>
                    {item.ingredient_name}
                  </Typography>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, flexWrap: 'wrap' }}>
                    <Typography variant="body2" sx={{ fontSize: '14px', color: '#787774' }}>
                      <strong>Quantity:</strong> {item.quantity} {item.unit}
                    </Typography>
                    {item.expiration_date && (
                      <Typography variant="body2" sx={{ fontSize: '14px', color: '#787774' }}>
                        <strong>Expires:</strong> {new Date(item.expiration_date).toLocaleDateString()}
                      </Typography>
                    )}
                    {isExpiringSoon(item.expiration_date) && (
                      <Chip
                        label="Expires Soon"
                        size="small"
                        sx={{
                          bgcolor: alpha('#ff9800', 0.1),
                          color: '#ff9800',
                          fontSize: '12px',
                          fontWeight: 500,
                          height: 24,
                        }}
                      />
                    )}
                  </Box>
                </Box>
                <Box sx={{ display: 'flex', gap: 1 }}>
                  <IconButton
                    onClick={() => handleOpenDialog(item)}
                    sx={{
                      color: '#787774',
                      '&:hover': {
                        bgcolor: alpha('#4caf50', 0.1),
                        color: '#4caf50',
                      },
                    }}
                  >
                    <EditIcon fontSize="small" />
                  </IconButton>
                  <IconButton
                    onClick={() => handleDelete(item.ingredient_name)}
                    sx={{
                      color: '#787774',
                      '&:hover': {
                        bgcolor: alpha('#f44336', 0.1),
                        color: '#f44336',
                      },
                    }}
                  >
                    <DeleteIcon fontSize="small" />
                  </IconButton>
                </Box>
              </Box>
            ))}
          </Stack>
        )}
      </Box>

      {/* Add/Edit Dialog */}
      <Dialog open={openDialog} onClose={handleCloseDialog} maxWidth="sm" fullWidth>
        <DialogTitle sx={{ fontSize: '18px', fontWeight: 600, color: '#37352f', pb: 2 }}>
          {editMode ? 'Edit Item' : 'Add New Item'}
        </DialogTitle>
        <DialogContent>
          <Stack spacing={2} sx={{ mt: 1 }}>
            <TextField
              label="Ingredient Name"
              value={currentItem.ingredient_name}
              onChange={(e) =>
                setCurrentItem({ ...currentItem, ingredient_name: e.target.value })
              }
              disabled={editMode}
              fullWidth
              size="small"
              sx={{
                '& .MuiOutlinedInput-root': {
                  fontSize: '14px',
                },
              }}
            />
            <TextField
              label="Quantity"
              type="number"
              value={currentItem.quantity}
              onChange={(e) =>
                setCurrentItem({ ...currentItem, quantity: e.target.value })
              }
              fullWidth
              size="small"
              sx={{
                '& .MuiOutlinedInput-root': {
                  fontSize: '14px',
                },
              }}
            />
            <TextField
              label="Unit"
              value={currentItem.unit}
              onChange={(e) => setCurrentItem({ ...currentItem, unit: e.target.value })}
              placeholder="e.g., cups, pieces, grams"
              fullWidth
              size="small"
              sx={{
                '& .MuiOutlinedInput-root': {
                  fontSize: '14px',
                },
              }}
            />
            <TextField
              label="Expiration Date"
              type="date"
              value={currentItem.expiration_date}
              onChange={(e) =>
                setCurrentItem({ ...currentItem, expiration_date: e.target.value })
              }
              InputLabelProps={{ shrink: true }}
              fullWidth
              size="small"
              sx={{
                '& .MuiOutlinedInput-root': {
                  fontSize: '14px',
                },
              }}
            />
          </Stack>
        </DialogContent>
        <DialogActions sx={{ p: 2.5, pt: 2 }}>
          <Button 
            onClick={handleCloseDialog}
            sx={{ 
              textTransform: 'none',
              color: '#787774',
              fontSize: '14px',
            }}
          >
            Cancel
          </Button>
          <Button 
            onClick={handleSave} 
            variant="contained"
            sx={{
              textTransform: 'none',
              bgcolor: '#4caf50',
              fontSize: '14px',
              '&:hover': { bgcolor: '#45a049' },
            }}
          >
            {editMode ? 'Update' : 'Add'}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default PantryManagement;
