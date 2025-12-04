#!/bin/bash
# Quick Start Script for Pinecone Ingestion

set -e  # Exit on error

echo "🍳 Leftovr Pinecone Setup Script"
echo "==============================="
echo ""

# Check if .env exists
if [ ! -f ".env" ]; then
    echo "❌ Error: .env file not found"
    echo "   Please create .env from .env.example and add your API keys"
    exit 1
fi

# Check if PINECONE_API_KEY is set
if ! grep -q "^PINECONE_API_KEY=pcsk_" .env; then
    echo "❌ Error: PINECONE_API_KEY not set in .env"
    echo "   Please add your Pinecone API key to .env"
    exit 1
fi

# Check if dataset exists
if [ ! -f "assets/full_dataset.csv" ]; then
    echo "📥 Downloading recipe dataset..."
    /Users/SG4111/Desktop/me/leftovr-app/.venv/bin/python -c "
import kagglehub
print('Downloading from Kaggle...')
path = kagglehub.dataset_download('wilmerarltstrmberg/recipe-dataset-over-2m')
print(f'Downloaded to: {path}')
import shutil, os
os.makedirs('assets', exist_ok=True)
shutil.copy(f'{path}/recipes_data.csv', 'assets/full_dataset.csv')
print('✅ Dataset ready!')
"
fi

# Check dataset size
DATASET_SIZE=$(wc -l < assets/full_dataset.csv)
echo "📊 Dataset has $(printf "%'d" $((DATASET_SIZE - 1))) recipes"
echo ""

# Ask user for sample size
echo "Pinecone Free Tier: 100,000 vectors max"
echo ""
echo "Choose ingestion size:"
echo "  1) Sample (10,000 recipes) - Fast, for testing (~2 minutes)"
echo "  2) Medium (50,000 recipes) - Good balance (~10 minutes)"
echo "  3) Large (95,000 recipes) - Max free tier (~20 minutes)"
echo "  4) Custom amount"
echo ""
read -p "Enter choice [1-4]: " choice

case $choice in
    1)
        SAMPLE_SIZE=10000
        ;;
    2)
        SAMPLE_SIZE=50000
        ;;
    3)
        SAMPLE_SIZE=95000
        ;;
    4)
        read -p "Enter number of recipes: " SAMPLE_SIZE
        ;;
    *)
        echo "Invalid choice, using default (10,000)"
        SAMPLE_SIZE=10000
        ;;
esac

echo ""
echo "🚀 Starting ingestion of $SAMPLE_SIZE recipes..."
echo "   This will take a few minutes. Please wait..."
echo ""

# Run ingestion
/Users/SG4111/Desktop/me/leftovr-app/.venv/bin/python scripts/ingest_recipes_pinecone.py \
    --input assets/full_dataset.csv \
    --outdir data \
    --sample $SAMPLE_SIZE \
    --batch-size 100

echo ""
echo "✅ Ingestion complete!"
echo ""
echo "Next steps:"
echo "  1. Start the backend: ./start_backend.sh"
echo "  2. Test the API: ./test_integration.sh"
echo "  3. Start full app: ./start_all.sh"
echo ""
