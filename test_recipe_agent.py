#!/usr/bin/env python3
"""
Quick test script for Recipe Knowledge Agent integration

This tests the agent independently of the full workflow
"""

from agents.recipe_knowledge_agent import RecipeKnowledgeAgent

def test_agent():
    print("🧪 Testing Recipe Knowledge Agent Integration\n")
    print("=" * 60)
    
    # Initialize agent
    print("\n1. Initializing agent...")
    try:
        agent = RecipeKnowledgeAgent(data_dir='data')
        agent.load_metadata()
        agent.load_ingredient_index()
        agent.try_load_faiss()
        print("✅ Agent initialized successfully")
        print(f"   - Loaded {len(agent.metadata)} recipes")
        print(f"   - Loaded {len(agent.ingredient_index)} ingredients")
        print(f"   - FAISS index: {'✅ Available' if agent.faiss_index else '❌ Not available'}")
    except FileNotFoundError as e:
        print(f"❌ Error: {e}")
        print("\n⚠️  Please run the ingestion script first:")
        print("   python scripts/ingest_recipes.py --input assets/full_dataset.csv --outdir data")
        return
    
    # Test 1: Pantry search (ingredient-based)
    print("\n" + "=" * 60)
    print("2. Testing pantry search (ingredient matching)...")
    print("=" * 60)
    
    test_ingredients = ['chicken', 'tomatoes', 'garlic', 'onion']
    print(f"Ingredients: {', '.join(test_ingredients)}")
    
    matches = agent.pantry_candidates(test_ingredients, min_overlap=2, top_k=5)
    
    if matches:
        print(f"\n✅ Found {len(matches)} recipes:\n")
        for i, (recipe_id, score) in enumerate(matches, 1):
            recipe = agent.metadata[recipe_id]
            print(f"{i}. {recipe['title']}")
            print(f"   Overlap: {score:.1%}")
            print(f"   Needs: {', '.join(recipe['ner'][:5])}...")
            print()
    else:
        print("❌ No recipes found")
    
    # Test 2: Semantic search
    if agent.faiss_index:
        print("=" * 60)
        print("3. Testing semantic search (embedding-based)...")
        print("=" * 60)
        
        query = "easy weeknight pasta dinner"
        print(f"Query: '{query}'")
        
        results = agent.semantic_search(query, k=5)
        
        if results:
            print(f"\n✅ Found {len(results)} recipes:\n")
            for i, (recipe_id, similarity) in enumerate(results, 1):
                recipe = agent.metadata[recipe_id]
                print(f"{i}. {recipe['title']}")
                print(f"   Similarity: {similarity:.3f}")
                print()
        else:
            print("❌ No recipes found")
    else:
        print("\n⚠️  Skipping semantic search test (FAISS not available)")
        print("   Run ingestion with --build-faiss to enable this feature")
    
    # Test 3: Hybrid search
    print("=" * 60)
    print("4. Testing hybrid search (combined approach)...")
    print("=" * 60)
    
    test_ingredients = ['pasta', 'tomatoes', 'basil', 'garlic']
    query_text = "quick Italian dinner"
    
    print(f"Ingredients: {', '.join(test_ingredients)}")
    print(f"Query: '{query_text}'")
    
    results = agent.hybrid_query(
        pantry_items=test_ingredients,
        query_text=query_text,
        top_k=5
    )
    
    if results:
        print(f"\n✅ Found {len(results)} recipes:\n")
        for i, (metadata, score) in enumerate(results, 1):
            print(f"{i}. {metadata['title']}")
            print(f"   Score: {score:.2f}")
            print(f"   Ingredients: {', '.join(metadata['ner'][:5])}...")
            print(f"   Source: {metadata['source']}")
            print()
    else:
        print("❌ No recipes found")
    
    print("=" * 60)
    print("\n🎉 Testing complete!")
    print("\nTo use in the full workflow, run: python main.py")

if __name__ == '__main__':
    test_agent()
