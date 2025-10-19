"""Test script for RecipeKnowledgeAgent

This script tests the Qdrant-based recipe agent with:
1. Ingredient search (uses existing ingredient_index.json)
2. Semantic search (uses Qdrant vector database)
3. Hybrid search (combines both)
"""
import sys
from agents.recipe_knowledge_agent import RecipeKnowledgeAgent


def test_ingredient_search(agent):
    """Test ingredient-based search"""
    print("\n" + "="*60)
    print("TEST 1: Ingredient Search")
    print("="*60)
    
    pantry = ['chicken', 'tomatoes', 'garlic', 'onion']
    print(f"Pantry items: {pantry}")
    
    results = agent.pantry_candidates(pantry, min_overlap=2, top_k=5)
    
    if results:
        print(f"\n✅ Found {len(results)} recipes!")
        for i, (recipe_id, score) in enumerate(results[:5], 1):
            meta = agent.metadata.get(recipe_id)
            if meta:
                print(f"\n{i}. {meta['title']} (overlap score: {score:.2f})")
                print(f"   Ingredients: {', '.join(meta['ner'][:5])}...")
    else:
        print("❌ No results found")


def test_semantic_search(agent):
    """Test semantic search with Qdrant"""
    print("\n" + "="*60)
    print("TEST 2: Semantic Search")
    print("="*60)
    
    if agent.qdrant_client is None:
        print("⚠️  Qdrant not initialized - skipping semantic search test")
        return
    
    # Check if collection has data
    try:
        info = agent.qdrant_client.get_collection(agent.collection_name)
        if info.points_count == 0:
            print("⚠️  Collection is empty - run ingestion first")
            return
    except Exception as e:
        print(f"⚠️  Collection not ready: {e}")
        return
    
    query = "easy Italian pasta dinner"
    print(f"Query: '{query}'")
    
    results = agent.semantic_search(query, k=5)
    
    if results:
        print(f"\n✅ Found {len(results)} recipes!")
        for i, (recipe_id, score) in enumerate(results, 1):
            meta = agent.metadata.get(recipe_id)
            if meta:
                print(f"\n{i}. {meta['title']} (similarity: {score:.3f})")
                print(f"   Ingredients: {', '.join(meta['ner'][:5])}...")
    else:
        print("❌ No results found")


def test_hybrid_search(agent):
    """Test hybrid search combining ingredients + semantic"""
    print("\n" + "="*60)
    print("TEST 3: Hybrid Search")
    print("="*60)
    
    if agent.qdrant_client is None:
        print("⚠️  Qdrant not initialized - skipping hybrid search test")
        return
    
    pantry = ['chicken', 'rice', 'vegetables']
    query = "quick healthy dinner"
    print(f"Pantry: {pantry}")
    print(f"Query: '{query}'")
    
    results = agent.hybrid_query(pantry, query, top_k=5)
    
    if results:
        print(f"\n✅ Found {len(results)} recipes!")
        for i, (meta, score) in enumerate(results, 1):
            if meta:
                print(f"\n{i}. {meta['title']} (combined score: {score:.2f})")
                print(f"   Ingredients: {', '.join(meta.get('ner', [])[:5])}...")
    else:
        print("❌ No results found")


def main():
    print("🧪 Testing RecipeKnowledgeAgent")
    print("="*60)
    
    # Initialize agent
    agent = RecipeKnowledgeAgent(data_dir='data', qdrant_path='./qdrant_data')
    
    # Load metadata and ingredient index
    try:
        print("\n📂 Loading metadata...")
        agent.load_metadata()
        
        print("📂 Loading ingredient index...")
        agent.load_ingredient_index()
        
    except FileNotFoundError as e:
        print(f"❌ Error: {e}")
        print("\n💡 Make sure you've run the ingestion script first:")
        print("   python scripts/ingest_recipes.py")
        sys.exit(1)
    
    # Setup Qdrant
    print("\n🔧 Setting up Qdrant...")
    try:
        agent.setup_qdrant()
    except Exception as e:
        print(f"⚠️  Qdrant setup failed: {e}")
        print("   Continuing with ingredient search only...")
    
    # Check if we need to ingest data
    if agent.qdrant_client is not None:
        try:
            info = agent.qdrant_client.get_collection(agent.collection_name)
            if info.points_count == 0:
                print("\n📥 Collection is empty. Ingesting sample recipes (this may take a minute)...")
                # Ingest first 10,000 recipes as a test
                sample_ids = list(agent.metadata.keys())[:10000]
                agent.ingest_recipes_to_qdrant(sample_ids, batch_size=100)
        except Exception as e:
            print(f"⚠️  Collection check failed: {e}")
    
    # Run tests
    test_ingredient_search(agent)
    
    if agent.qdrant_client is not None:
        test_semantic_search(agent)
        test_hybrid_search(agent)
    
    print("\n" + "="*60)
    print("✅ Testing complete!")
    print("="*60)
    
    # Summary
    print("\n📊 Summary:")
    print(f"   • Recipes loaded: {len(agent.metadata):,}")
    print(f"   • Ingredients indexed: {len(agent.ingredient_index):,}")
    if agent.qdrant_client:
        try:
            info = agent.qdrant_client.get_collection(agent.collection_name)
            print(f"   • Vectors in Qdrant: {info.points_count:,}")
        except:
            print(f"   • Vectors in Qdrant: 0")
    else:
        print(f"   • Qdrant: Not initialized")


if __name__ == '__main__':
    main()
