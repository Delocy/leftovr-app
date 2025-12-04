import axios from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Chat API
export const sendMessage = async (message, preferences = {}, inventory = []) => {
  try {
    const response = await apiClient.post('/chat', {
      user_message: message,
      user_preferences: preferences,
      pantry_inventory: inventory,
    });
    return response.data;
  } catch (error) {
    console.error('Error sending message:', error);
    throw error;
  }
};

// Pantry API
export const getPantryInventory = async () => {
  try {
    const response = await apiClient.get('/pantry/inventory');
    return response.data;
  } catch (error) {
    console.error('Error fetching inventory:', error);
    throw error;
  }
};

export const addPantryItem = async (itemData) => {
  try {
    const response = await apiClient.post('/pantry/add', itemData);
    return response.data;
  } catch (error) {
    console.error('Error adding pantry item:', error);
    throw error;
  }
};

export const updatePantryItem = async (itemName, itemData) => {
  try {
    const response = await apiClient.put(`/pantry/update/${itemName}`, itemData);
    return response.data;
  } catch (error) {
    console.error('Error updating pantry item:', error);
    throw error;
  }
};

export const deletePantryItem = async (itemName) => {
  try {
    const response = await apiClient.delete(`/pantry/delete/${itemName}`);
    return response.data;
  } catch (error) {
    console.error('Error deleting pantry item:', error);
    throw error;
  }
};

// Recipe API
export const searchRecipes = async (query, preferences = {}) => {
  try {
    const response = await apiClient.post('/recipes/search', {
      query,
      preferences,
    });
    return response.data;
  } catch (error) {
    console.error('Error searching recipes:', error);
    throw error;
  }
};

export default apiClient;
