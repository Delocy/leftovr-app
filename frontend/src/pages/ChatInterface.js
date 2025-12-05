import React, { useState, useRef, useEffect } from 'react';
import {
  Box,
  Typography,
  TextField,
  Button,
  Avatar,
  CircularProgress,
} from '@mui/material';
import SendIcon from '@mui/icons-material/Send';
import PersonIcon from '@mui/icons-material/Person';
import SmartToyIcon from '@mui/icons-material/SmartToy';
import axios from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

function ChatInterface({ pantryItems, preferences }) {
  const [messages, setMessages] = useState([
    {
      role: 'assistant',
      content: 'Hi! I\'m your AI chef assistant. I can help you manage your pantry, find recipes based on what you have, and give you cooking recommendations. How can I help you today?'
    }
  ]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSend = async () => {
    if (!input.trim()) return;

    const userMessage = input.trim();
    setInput('');

    // Add user message to chat
    setMessages(prev => [...prev, { role: 'user', content: userMessage }]);
    setLoading(true);

    try {
      const response = await axios.post(`${API_BASE_URL}/chat`, {
        message: userMessage
      });

      // Add assistant response to chat
      setMessages(prev => [
        ...prev,
        {
          role: 'assistant',
          content: response.data.response || 'Sorry, I didn\'t understand that.'
        }
      ]);
    } catch (err) {
      console.error('Error sending message:', err);
      
      // Add error message to chat
      setMessages(prev => [
        ...prev,
        {
          role: 'assistant',
          content: 'Sorry, I encountered an error. Please try again.'
        }
      ]);
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

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', height: '100%', backgroundColor: '#ffffff' }}>
      {/* Messages Container */}
      <Box
        sx={{
          flexGrow: 1,
          overflow: 'auto',
          px: 3,
          py: 3,
        }}
      >
        {messages.map((message, index) => (
          <Box
            key={index}
            sx={{
              display: 'flex',
              alignItems: 'flex-start',
              gap: 2,
              mb: 3,
              flexDirection: message.role === 'user' ? 'row-reverse' : 'row',
            }}
          >
            <Avatar
              sx={{
                bgcolor: message.role === 'user' ? '#10b981' : '#f59e0b',
                width: 36,
                height: 36,
              }}
            >
              {message.role === 'user' ? <PersonIcon /> : <SmartToyIcon />}
            </Avatar>
            <Box
              sx={{
                maxWidth: '70%',
                backgroundColor: message.role === 'user' ? '#f7f6f3' : 'transparent',
                borderRadius: 1,
                p: message.role === 'user' ? 2 : 0,
              }}
            >
              <Typography
                variant="body1"
                sx={{
                  whiteSpace: 'pre-wrap',
                  lineHeight: 1.6,
                  color: '#37352f',
                }}
              >
                {message.content}
              </Typography>
            </Box>
          </Box>
        ))}
        {loading && (
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
            <Avatar sx={{ bgcolor: '#f59e0b', width: 36, height: 36 }}>
              <SmartToyIcon />
            </Avatar>
            <CircularProgress size={24} sx={{ color: '#10b981' }} />
          </Box>
        )}
        <div ref={messagesEndRef} />
      </Box>

      {/* Input Area */}
      <Box
        sx={{
          px: 3,
          py: 2,
          borderTop: '1px solid #e9e9e7',
          backgroundColor: '#ffffff',
        }}
      >
        <Box display="flex" gap={2} alignItems="flex-end">
          <TextField
            fullWidth
            multiline
            maxRows={4}
            placeholder="Ask me anything... (e.g., 'What can I cook with chicken and rice?')"
            value={input}
            onChange={(e) => setInput(e.target.value)}
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
            onClick={handleSend}
            disabled={loading || !input.trim()}
            sx={{
              minWidth: 56,
              minHeight: 56,
              width: 56,
              height: 56,
              textTransform: 'none',
              fontWeight: 600,
              padding: 0,
            }}
          >
            {loading ? <CircularProgress size={20} /> : <SendIcon />}
          </Button>
        </Box>
      </Box>
    </Box>
  );
}

export default ChatInterface;
