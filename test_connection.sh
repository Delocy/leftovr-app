#!/bin/bash
# Quick test of backend-frontend connection

echo "🧪 Testing Leftovr Backend-Frontend Integration"
echo "==============================================="
echo ""

# 1. Test Pinecone
echo "1️⃣  Testing Pinecone connection..."
cd /Users/SG4111/Desktop/me/leftovr-app && .venv/bin/python -c "
from pinecone import Pinecone
import os
from dotenv import load_dotenv

load_dotenv()
pc = Pinecone(api_key=os.environ['PINECONE_API_KEY'])
index = pc.Index('leftovr-recipes')
stats = index.describe_index_stats()
print(f'   ✅ Pinecone: {stats[\"total_vector_count\"]:,} recipes indexed')
" || { echo "   ❌ Pinecone connection failed"; exit 1; }

# 2. Check if backend is running
echo ""
echo "2️⃣  Testing backend API..."
if curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo "   ✅ Backend API is running"
else
    echo "   ❌ Backend not running - start with: ./start_backend.sh"
    exit 1
fi

# 3. Test recipe search endpoint
echo ""
echo "3️⃣  Testing recipe search..."
RESPONSE=$(curl -s -X POST http://localhost:8000/recipes/search \
  -H "Content-Type: application/json" \
  -d '{"query": "pasta", "limit": 3}')

if echo "$RESPONSE" | grep -q "recipes"; then
    COUNT=$(echo "$RESPONSE" | grep -o '"id"' | wc -l | tr -d ' ')
    echo "   ✅ Recipe search working (found $COUNT recipes)"
else
    echo "   ❌ Recipe search failed"
    echo "   Response: $RESPONSE"
    exit 1
fi

# 4. Check frontend
echo ""
echo "4️⃣  Testing frontend..."
if curl -s http://localhost:3000 > /dev/null 2>&1; then
    echo "   ✅ Frontend is running"
else
    echo "   ⚠️  Frontend not running - start with: cd frontend && npm start"
fi

echo ""
echo "✅ All tests passed!"
echo ""
echo "🌐 URLs:"
echo "   Frontend: http://localhost:3000"
echo "   Backend:  http://localhost:8000"
echo "   API Docs: http://localhost:8000/docs"
echo ""
