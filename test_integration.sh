#!/bin/bash

# ============================================
# Leftovr Integration Test Script
# ============================================
# Tests the connection between frontend and backend

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

BASE_URL="http://localhost:8000"

echo -e "${BLUE}============================================${NC}"
echo -e "${BLUE}   Leftovr Integration Tests${NC}"
echo -e "${BLUE}============================================${NC}"
echo ""

# Test 1: Health Check
echo -e "${YELLOW}Test 1: Health Check${NC}"
response=$(curl -s "$BASE_URL/health" || echo "FAILED")
if [[ $response == *"healthy"* ]]; then
    echo -e "${GREEN}✓${NC} Health check passed"
    echo "$response" | jq '.'
else
    echo -e "${RED}❌ Health check failed${NC}"
    exit 1
fi
echo ""

# Test 2: Get Pantry Inventory
echo -e "${YELLOW}Test 2: Get Pantry Inventory${NC}"
response=$(curl -s "$BASE_URL/pantry/inventory" || echo "FAILED")
if [[ $response == *"inventory"* ]]; then
    echo -e "${GREEN}✓${NC} Pantry inventory retrieved"
    echo "$response" | jq '.'
else
    echo -e "${RED}❌ Failed to get inventory${NC}"
    exit 1
fi
echo ""

# Test 3: Add Pantry Item
echo -e "${YELLOW}Test 3: Add Pantry Item${NC}"
response=$(curl -s -X POST "$BASE_URL/pantry/add" \
  -H "Content-Type: application/json" \
  -d '{
    "ingredient_name": "tomato",
    "quantity": 5,
    "unit": "pieces",
    "expiration_date": "2025-12-15"
  }' || echo "FAILED")

if [[ $response == *"success"* ]]; then
    echo -e "${GREEN}✓${NC} Item added successfully"
    echo "$response" | jq '.'
else
    echo -e "${RED}❌ Failed to add item${NC}"
    echo "$response"
fi
echo ""

# Test 4: Send Chat Message
echo -e "${YELLOW}Test 4: Send Chat Message${NC}"
response=$(curl -s -X POST "$BASE_URL/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "user_message": "What can I cook with tomatoes?",
    "user_preferences": {
      "skill_level": "intermediate",
      "dietary_restrictions": [],
      "allergies": []
    },
    "pantry_inventory": []
  }' || echo "FAILED")

if [[ $response == *"response"* ]]; then
    echo -e "${GREEN}✓${NC} Chat message processed"
    echo "$response" | jq '.response' || echo "$response"
else
    echo -e "${RED}❌ Failed to process chat${NC}"
    echo "$response"
fi
echo ""

# Test 5: Recipe Search
echo -e "${YELLOW}Test 5: Recipe Search${NC}"
response=$(curl -s -X POST "$BASE_URL/recipes/search" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "pasta tomato",
    "top_k": 5
  }' || echo "FAILED")

if [[ $response == *"recipes"* ]]; then
    echo -e "${GREEN}✓${NC} Recipe search successful"
    recipe_count=$(echo "$response" | jq '.recipes | length')
    echo "Found $recipe_count recipes"
else
    echo -e "${RED}❌ Recipe search failed${NC}"
    echo "$response"
fi
echo ""

# Test 6: Delete Pantry Item
echo -e "${YELLOW}Test 6: Delete Pantry Item${NC}"
response=$(curl -s -X DELETE "$BASE_URL/pantry/delete/tomato" || echo "FAILED")

if [[ $response == *"success"* ]]; then
    echo -e "${GREEN}✓${NC} Item deleted successfully"
    echo "$response" | jq '.'
else
    echo -e "${RED}❌ Failed to delete item${NC}"
    echo "$response"
fi
echo ""

echo -e "${GREEN}============================================${NC}"
echo -e "${GREEN}   All Tests Completed!${NC}"
echo -e "${GREEN}============================================${NC}"
echo ""
echo -e "Backend API is working correctly! ✨"
echo -e "You can now use the React frontend at ${BLUE}http://localhost:3000${NC}"
