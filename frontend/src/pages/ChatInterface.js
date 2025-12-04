import React, { useState, useEffect, useRef } from 'react';
import {
  Box,
  TextField,
  IconButton,
  Typography,
  CircularProgress,
  Chip,
  Button,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  FormControl,
  Select,
  MenuItem,
  Stack,
  Avatar,
} from '@mui/material';
import SendIcon from '@mui/icons-material/Send';
import PersonIcon from '@mui/icons-material/Person';
import RestaurantIcon from '@mui/icons-material/Restaurant';
import KitchenIcon from '@mui/icons-material/Kitchen';
import SettingsIcon from '@mui/icons-material/Settings';
import AddIcon from '@mui/icons-material/Add';
import DeleteIcon from '@mui/icons-material/Delete';
import { sendMessage, getPantryInventory, addPantryItem, deletePantryItem } from '../services/api';

const ChatInterface = () => {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef(null);
  const [addItemDialogOpen, setAddItemDialogOpen] = useState(false);
  const [newItem, setNewItem] = useState({
    ingredient_name: '',
    quantity: '',
    unit: '',
    expiration_date: '',
  });
  const [pantryItems, setPantryItems] = useState([]);
  const [preferences, setPreferences] = useState({
    skill_level: 'intermediate',
    dietary_restrictions: [],
    allergies: [],
  });

  useEffect(() => {
    fetchPantryItems();
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  const fetchPantryItems = async () => {
    try {
      const items = await getPantryInventory();
      setPantryItems(items || []);
    } catch (error) {
      console.error('Error fetching pantry:', error);
    }
  };

  const handleSend = async () => {
    if (!input.trim()) return;
    
    const userMessage = { role: 'user', content: input };
    setMessages((prev) => [...prev, userMessage]);
    setInput('');
    setLoading(true);

    try {
      const response = await sendMessage(input, preferences, pantryItems);
      const assistantMessage = {
        role: 'assistant',
        content: response.message || 'Sorry, I could not process your request.',
        data: response.data,
      };
      setMessages((prev) => [...prev, assistantMessage]);
    } catch (error) {
      console.error('Error sending message:', error);
      const errorMessage = {
        role: 'assistant',
        content: 'Sorry, something went wrong. Please try again.',
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };
  
  const handleAddItem = async () => {
    try {
      await addPantryItem(newItem);
      await fetchPantryItems();
      setAddItemDialogOpen(false);
      setNewItem({ ingredient_name: '', quantity: '', unit: '', expiration_date: '' });
    } catch (error) {
      console.error('Error adding item:', error);
    }
  };
  
  const handleDeleteItem = async (itemName) => {
    try {
      await deletePantryItem(itemName);
      await fetchPantryItems();
    } catch (error) {
      console.error('Error deleting item:', error);
    }
  };
  
  const handlePreferenceChange = (category, value) => {
    setPreferences((prev) => {
      const current = prev[category] || [];
      const updated = current.includes(value)
        ? current.filter((item) => item !== value)
        : [...current, value];
      return { ...prev, [category]: updated };
    });
  };

  const isExpiringSoon = (expirationDate) => {
    if (!expirationDate) return false;
    const today = new Date();
    const expDate = new Date(expirationDate);
    const daysUntilExpiry = Math.ceil((expDate - today) / (1000 * 60 * 60 * 24));
    return daysUntilExpiry <= 3 && daysUntilExpiry >= 0;
  };

  return (
    <>
    <Box sx={{ display: 'flex', height: 'calc(100vh - 64px)', bgcolor: '#fafafa' }}>
      {/* Left Sidebar - Notion Style */}
      <Box
        sx={{
          width: 280,
          flexShrink: 0,
          bgcolor: '#ffffff',
          borderRight: '1px solid #e0e0e0',
          display: 'flex',
          flexDirection: 'column',
          overflow: 'hidden',
        }}
      >
        {/* Sidebar Header */}
        <Box sx={{ p: 2.5, borderBottom: '1px solid #f0f0f0' }}>
          <Typography variant="body2" sx={{ fontSize: '13px', fontWeight: 600, color: '#37352f', mb: 0.5 }}>
            Your Kitchen
          </Typography>
          <Typography variant="caption" sx={{ fontSize: '11px', color: '#9b9a97' }}>
            Manage ingredients & preferences
          </Typography>
        </Box>

        {/* Scrollable Content */}
        <Box sx={{ flexGrow: 1, overflow: 'auto', p: 2 }}>
          <Stack spacing={3}>
            {/* Preferences Section */}
            <Box>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1.5, px: 1 }}>
                <SettingsIcon sx={{ fontSize: 16, color: '#9b9a97' }} />
                <Typography variant="body2" sx={{ fontSize: '12px', fontWeight: 600, color: '#37352f', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                  Preferences
                </Typography>
              </Box>
              
              <Stack spacing={1.5}>
                {/* Skill Level */}
                <Box sx={{ px: 1 }}>
                  <Typography variant="caption" sx={{ fontSize: '11px', fontWeight: 500, color: '#787774', mb: 0.5, display: 'block' }}>
                    Skill Level
                  </Typography>
                  <FormControl fullWidth size="small">
                    <Select
                      value={preferences.skill_level}
                      onChange={(e) => setPreferences({ ...preferences, skill_level: e.target.value })}
                      sx={{
                        fontSize: '13px',
                        bgcolor: '#f7f6f3',
                        '& .MuiOutlinedInput-notchedOutline': { border: 'none' },
                        '&:hover': { bgcolor: '#f0eeeb' },
                        borderRadius: 1,
                      }}
                    >
                      <MenuItem value="beginner" sx={{ fontSize: '13px' }}>Beginner</MenuItem>
                      <MenuItem value="intermediate" sx={{ fontSize: '13px' }}>Intermediate</MenuItem>
                      <MenuItem value="advanced" sx={{ fontSize: '13px' }}>Advanced</MenuItem>
                    </Select>
                  </FormControl>
                </Box>
                
                {/* Dietary Restrictions */}
                <Box sx={{ px: 1 }}>
                  <Typography variant="caption" sx={{ fontSize: '11px', fontWeight: 500, color: '#787774', mb: 0.5, display: 'block' }}>
                    Dietary
                  </Typography>
                  <Stack spacing={0.5}>
                    {['vegetarian', 'vegan', 'gluten-free', 'dairy-free'].map((diet) => (
                      <Box
                        key={diet}
                        onClick={() => handlePreferenceChange('dietary_restrictions', diet)}
                        sx={{
                          display: 'flex',
                          alignItems: 'center',
                          gap: 1,
                          p: 0.75,
                          borderRadius: 0.75,
                          cursor: 'pointer',
                          bgcolor: preferences.dietary_restrictions.includes(diet) ? '#f7f6f3' : 'transparent',
                          '&:hover': { bgcolor: '#f7f6f3' },
                          transition: 'background-color 0.15s',
                        }}
                      >
                        <Box
                          sx={{
                            width: 14,
                            height: 14,
                            borderRadius: 0.5,
                            border: '1.5px solid',
                            borderColor: preferences.dietary_restrictions.includes(diet) ? '#4caf50' : '#d1d0ce',
                            bgcolor: preferences.dietary_restrictions.includes(diet) ? '#4caf50' : 'transparent',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            transition: 'all 0.15s',
                          }}
                        >
                          {preferences.dietary_restrictions.includes(diet) && (
                            <Box sx={{ width: 6, height: 3, borderLeft: '1.5px solid white', borderBottom: '1.5px solid white', transform: 'rotate(-45deg)', mb: 0.3 }} />
                          )}
                        </Box>
                        <Typography variant="body2" sx={{ fontSize: '13px', color: '#37352f' }}>
                          {diet.charAt(0).toUpperCase() + diet.slice(1).replace('-', ' ')}
                        </Typography>
                      </Box>
                    ))}
                  </Stack>
                </Box>
                
                {/* Allergies */}
                <Box sx={{ px: 1 }}>
                  <Typography variant="caption" sx={{ fontSize: '11px', fontWeight: 500, color: '#787774', mb: 0.5, display: 'block' }}>
                    Allergies
                  </Typography>
                  <Stack spacing={0.5}>
                    {['nuts', 'shellfish', 'eggs', 'soy'].map((allergy) => (
                      <Box
                        key={allergy}
                        onClick={() => handlePreferenceChange('allergies', allergy)}
                        sx={{
                          display: 'flex',
                          alignItems: 'center',
                          gap: 1,
                          p: 0.75,
                          borderRadius: 0.75,
                          cursor: 'pointer',
                          bgcolor: preferences.allergies.includes(allergy) ? '#f7f6f3' : 'transparent',
                          '&:hover': { bgcolor: '#f7f6f3' },
                          transition: 'background-color 0.15s',
                        }}
                      >
                        <Box
                          sx={{
                            width: 14,
                            height: 14,
                            borderRadius: 0.5,
                            border: '1.5px solid',
                            borderColor: preferences.allergies.includes(allergy) ? '#4caf50' : '#d1d0ce',
                            bgcolor: preferences.allergies.includes(allergy) ? '#4caf50' : 'transparent',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            transition: 'all 0.15s',
                          }}
                        >
                          {preferences.allergies.includes(allergy) && (
                            <Box sx={{ width: 6, height: 3, borderLeft: '1.5px solid white', borderBottom: '1.5px solid white', transform: 'rotate(-45deg)', mb: 0.3 }} />
                          )}
                        </Box>
                        <Typography variant="body2" sx={{ fontSize: '13px', color: '#37352f' }}>
                          {allergy.charAt(0).toUpperCase() + allergy.slice(1)}
                        </Typography>
                      </Box>
                    ))}
                  </Stack>
                </Box>
              </Stack>
            </Box>
            
            {/* Pantry Section */}
            <Box>
              <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 1.5, px: 1 }}>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                  <KitchenIcon sx={{ fontSize: 16, color: '#9b9a97' }} />
                  <Typography variant="body2" sx={{ fontSize: '12px', fontWeight: 600, color: '#37352f', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                    Pantry
                  </Typography>
                </Box>
                <Chip 
                  label={pantryItems.length} 
                  size="small" 
                  sx={{ 
                    height: 18, 
                    fontSize: '11px', 
                    fontWeight: 500,
                    bgcolor: '#f7f6f3',
                    color: '#37352f',
                    '& .MuiChip-label': { px: 1 }
                  }} 
                />
              </Box>
              
              <Button
                startIcon={<AddIcon sx={{ fontSize: 16 }} />}
                fullWidth
                onClick={() => setAddItemDialogOpen(true)}
                sx={{
                  justifyContent: 'flex-start',
                  textTransform: 'none',
                  fontSize: '13px',
                  fontWeight: 500,
                  color: '#37352f',
                  bgcolor: 'transparent',
                  border: '1px dashed #d1d0ce',
                  borderRadius: 1,
                  py: 0.75,
                  mb: 1,
                  '&:hover': {
                    bgcolor: '#f7f6f3',
                    borderColor: '#9b9a97',
                  },
                }}
              >
                Add ingredient
              </Button>
              
              {pantryItems.length === 0 ? (
                <Box sx={{ textAlign: 'center', py: 3, px: 2 }}>
                  <Typography variant="caption" sx={{ fontSize: '12px', color: '#9b9a97' }}>
                    No ingredients yet
                  </Typography>
                </Box>
              ) : (
                <Stack spacing={0.5}>
                  {pantryItems.map((item) => (
                    <Box
                      key={item.ingredient_name}
                      sx={{
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'space-between',
                        p: 1,
                        borderRadius: 0.75,
                        '&:hover': {
                          bgcolor: '#f7f6f3',
                          '& .delete-icon': { opacity: 1 },
                        },
                        transition: 'background-color 0.15s',
                      }}
                    >
                      <Box sx={{ flexGrow: 1, minWidth: 0 }}>
                        <Typography 
                          variant="body2" 
                          sx={{ 
                            fontSize: '13px', 
                            color: '#37352f',
                            fontWeight: 500,
                            overflow: 'hidden',
                            textOverflow: 'ellipsis',
                            whiteSpace: 'nowrap',
                          }}
                        >
                          {item.ingredient_name}
                        </Typography>
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5, mt: 0.25 }}>
                          <Typography variant="caption" sx={{ fontSize: '11px', color: '#9b9a97' }}>
                            {item.quantity} {item.unit}
                          </Typography>
                          {isExpiringSoon(item.expiration_date) && (
                            <>
                              <Typography variant="caption" sx={{ fontSize: '11px', color: '#9b9a97' }}>•</Typography>
                              <Typography variant="caption" sx={{ fontSize: '11px', color: '#ff9800', fontWeight: 500 }}>
                                Expires soon
                              </Typography>
                            </>
                          )}
                        </Box>
                      </Box>
                      <IconButton
                        className="delete-icon"
                        size="small"
                        onClick={() => handleDeleteItem(item.ingredient_name)}
                        sx={{
                          opacity: 0,
                          transition: 'opacity 0.15s',
                          width: 24,
                          height: 24,
                          '&:hover': {
                            bgcolor: 'rgba(244, 67, 54, 0.1)',
                          },
                        }}
                      >
                        <DeleteIcon sx={{ fontSize: 16, color: '#9b9a97' }} />
                      </IconButton>
                    </Box>
                  ))}
                </Stack>
              )}
            </Box>
          </Stack>
        </Box>
      </Box>

      {/* Main Chat Area */}
      <Box
        sx={{
          flexGrow: 1,
          display: 'flex',
          flexDirection: 'column',
          overflow: 'hidden',
          bgcolor: '#ffffff',
        }}
      >
        {/* Messages Area */}
        <Box
          sx={{
            flexGrow: 1,
            overflow: 'auto',
            display: 'flex',
            flexDirection: 'column',
          }}
        >
          {messages.length === 0 ? (
            <Box sx={{ 
              display: 'flex', 
              alignItems: 'center', 
              justifyContent: 'center', 
              height: '100%',
              flexDirection: 'column',
              gap: 2,
              color: '#9b9a97',
            }}>
              <RestaurantIcon sx={{ fontSize: 48, color: '#d1d0ce' }} />
              <Typography variant="h6" sx={{ fontSize: '16px', fontWeight: 500, color: '#37352f' }}>
                What can I cook for you today?
              </Typography>
              <Typography variant="body2" sx={{ fontSize: '13px', color: '#9b9a97', textAlign: 'center', maxWidth: 400 }}>
                Ask me for recipe suggestions based on your ingredients, or get help managing your pantry.
              </Typography>
            </Box>
          ) : (
            <Box sx={{ p: 4, maxWidth: 900, mx: 'auto', width: '100%' }}>
              <Stack spacing={3}>
                {messages.map((message, index) => (
                  <Box
                    key={index}
                    sx={{
                      display: 'flex',
                      gap: 2,
                      alignItems: 'flex-start',
                    }}
                  >
                    <Avatar
                      sx={{
                        bgcolor: message.role === 'user' ? '#4caf50' : '#f7f6f3',
                        color: message.role === 'user' ? '#ffffff' : '#37352f',
                        width: 32,
                        height: 32,
                        fontSize: '14px',
                        fontWeight: 500,
                      }}
                    >
                      {message.role === 'user' ? <PersonIcon sx={{ fontSize: 18 }} /> : <RestaurantIcon sx={{ fontSize: 18 }} />}
                    </Avatar>
                    <Box sx={{ flexGrow: 1, minWidth: 0 }}>
                      <Typography 
                        variant="body1" 
                        sx={{ 
                          fontSize: '15px', 
                          lineHeight: 1.6,
                          color: '#37352f',
                          whiteSpace: 'pre-wrap',
                          wordBreak: 'break-word',
                        }}
                      >
                        {message.content}
                      </Typography>
                      
                      {/* Display recipe recommendations if available */}
                      {message.data?.top_3_recommendations && (
                        <Box sx={{ mt: 1.5, display: 'flex', flexWrap: 'wrap', gap: 1 }}>
                          {message.data.top_3_recommendations.map((recipe, idx) => (
                            <Chip
                              key={idx}
                              label={recipe.title}
                              size="small"
                              sx={{
                                bgcolor: '#f7f6f3',
                                color: '#37352f',
                                fontSize: '12px',
                                fontWeight: 500,
                                border: '1px solid #e0e0e0',
                                '&:hover': { bgcolor: '#f0eeeb' },
                              }}
                            />
                          ))}
                        </Box>
                      )}
                    </Box>
                  </Box>
                ))}
                {loading && (
                  <Box sx={{ display: 'flex', justifyContent: 'center', py: 2 }}>
                    <CircularProgress size={20} sx={{ color: '#9b9a97' }} />
                  </Box>
                )}
                <div ref={messagesEndRef} />
              </Stack>
            </Box>
          )}
        </Box>

        {/* Input Area */}
        <Box
          sx={{
            p: 3,
            bgcolor: '#ffffff',
            borderTop: '1px solid #e0e0e0',
          }}
        >
          <Box sx={{ display: 'flex', gap: 1.5, maxWidth: 900, mx: 'auto', alignItems: 'flex-end' }}>
            <TextField
              fullWidth
              multiline
              maxRows={4}
              placeholder="Ask me for recipes or cooking help..."
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyPress={handleKeyPress}
              disabled={loading}
              variant="outlined"
              sx={{
                '& .MuiOutlinedInput-root': {
                  fontSize: '15px',
                  color: '#37352f',
                  bgcolor: '#ffffff',
                  borderRadius: 1.5,
                  '& fieldset': {
                    borderColor: '#e0e0e0',
                  },
                  '&:hover fieldset': {
                    borderColor: '#d1d0ce',
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
            <IconButton
              onClick={handleSend}
              disabled={!input.trim() || loading}
              sx={{
                bgcolor: (input.trim() && !loading) ? '#4caf50' : '#f7f6f3',
                color: (input.trim() && !loading) ? '#ffffff' : '#9b9a97',
                width: 36,
                height: 36,
                '&:hover': {
                  bgcolor: (input.trim() && !loading) ? '#45a049' : '#f0eeeb',
                },
                '&:disabled': {
                  bgcolor: '#f7f6f3',
                  color: '#d1d0ce',
                },
                transition: 'all 0.2s',
              }}
            >
              <SendIcon sx={{ fontSize: 18 }} />
            </IconButton>
          </Box>
        </Box>
      </Box>
    </Box>

    {/* Add Item Dialog */}
    <Dialog open={addItemDialogOpen} onClose={() => setAddItemDialogOpen(false)} maxWidth="sm" fullWidth>
      <DialogTitle sx={{ fontSize: '16px', fontWeight: 600, color: '#37352f' }}>Add Pantry Item</DialogTitle>
      <DialogContent>
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, mt: 2 }}>
          <TextField
            label="Ingredient Name"
            value={newItem.ingredient_name}
            onChange={(e) => setNewItem({ ...newItem, ingredient_name: e.target.value })}
            fullWidth
            size="small"
          />
          <TextField
            label="Quantity"
            type="number"
            value={newItem.quantity}
            onChange={(e) => setNewItem({ ...newItem, quantity: e.target.value })}
            fullWidth
            size="small"
          />
          <TextField
            label="Unit"
            value={newItem.unit}
            onChange={(e) => setNewItem({ ...newItem, unit: e.target.value })}
            placeholder="e.g., cups, pieces, grams"
            fullWidth
            size="small"
          />
          <TextField
            label="Expiration Date"
            type="date"
            value={newItem.expiration_date}
            onChange={(e) => setNewItem({ ...newItem, expiration_date: e.target.value })}
            InputLabelProps={{ shrink: true }}
            fullWidth
            size="small"
          />
        </Box>
      </DialogContent>
      <DialogActions sx={{ p: 2 }}>
        <Button onClick={() => setAddItemDialogOpen(false)} sx={{ textTransform: 'none', color: '#9b9a97' }}>
          Cancel
        </Button>
        <Button 
          onClick={handleAddItem} 
          variant="contained" 
          sx={{ 
            textTransform: 'none',
            bgcolor: '#4caf50',
            '&:hover': { bgcolor: '#45a049' },
          }}
        >
          Add
        </Button>
      </DialogActions>
    </Dialog>
    </>
  );
};

export default ChatInterface;
