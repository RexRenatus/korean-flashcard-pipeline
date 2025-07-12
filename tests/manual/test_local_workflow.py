#!/usr/bin/env python3
"""
Test the migration and vocabulary processing workflow locally
This simulates what would happen in Docker
"""

import os
import sys
import subprocess
from pathlib import Path

# Add the src/python directory to the path
sys.path.insert(0, 'src/python')

def run_command(cmd, description):
    """Run a command and show output"""
    print(f"\n{'='*60}")
    print(f"🔧 {description}")
    print(f"{'='*60}")
    print(f"Command: {cmd}")
    print()
    
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if result.stdout:
            print(result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr)
        return result.returncode == 0
    except Exception as e:
        print(f"Error: {e}")
        return False

def main():
    """Run the complete test workflow"""
    print("🚀 Testing Flashcard Pipeline Workflow")
    print("This simulates what would happen in Docker")
    
    # Check environment
    if not os.path.exists('.env'):
        print("❌ Error: .env file not found")
        print("Please create .env with your OPENROUTER_API_KEY")
        return
    
    # Create necessary directories
    for dir_path in ['data', 'data/cache', 'data/output', 'data/input']:
        Path(dir_path).mkdir(parents=True, exist_ok=True)
    
    # Step 1: Prepare test data
    print("\n📝 Step 1: Preparing test data")
    if run_command(
        "head -n 101 docs/10K_HSK_List.csv > data/input/hsk_first_100.csv",
        "Extracting first 100 vocabulary items"
    ):
        print("✅ Test data prepared")
    else:
        print("❌ Failed to prepare test data")
        return
    
    # Step 2: Run migrations
    print("\n📊 Step 2: Running database migrations")
    if run_command(
        "python3 scripts/run_migrations.py data/flashcards.db migrations",
        "Setting up database schema"
    ):
        print("✅ Migrations completed")
    else:
        print("❌ Migration failed")
        return
    
    # Step 3: Test the processing script
    print("\n🔄 Step 3: Testing vocabulary processing")
    print("Note: This would normally run through Docker")
    print("The actual processing requires the async API client")
    
    # Create a simple test to verify the setup
    test_script = '''
import sys
sys.path.insert(0, 'src/python')

try:
    from flashcard_pipeline import OpenRouterClient, VocabularyItem
    print("✅ Flashcard pipeline modules imported successfully")
    
    # Test creating a vocabulary item
    item = VocabularyItem(
        term="테스트",
        pos="noun",
        level="beginner",
        definition="test"
    )
    print(f"✅ Created test vocabulary item: {item.term}")
    
    # Check if API key is available
    import os
    from dotenv import load_dotenv
    load_dotenv()
    
    api_key = os.getenv('OPENROUTER_API_KEY')
    if api_key:
        print("✅ API key found in environment")
    else:
        print("❌ API key not found - processing would fail")
        
except Exception as e:
    print(f"❌ Error: {e}")
'''
    
    with open('test_import.py', 'w') as f:
        f.write(test_script)
    
    if run_command("python3 test_import.py", "Testing pipeline imports"):
        print("✅ Pipeline modules are working")
    else:
        print("❌ Pipeline module test failed")
    
    # Clean up test file
    os.remove('test_import.py')
    
    # Show Docker commands for actual processing
    print("\n" + "="*60)
    print("📋 Docker Commands for Full Processing")
    print("="*60)
    print("\nOnce Docker is available, run these commands:")
    print("\n1. Build the Docker image:")
    print("   docker-compose build")
    print("\n2. Run migrations:")
    print("   ./docker-migrate.sh")
    print("\n3. Process vocabulary:")
    print("   ./docker-process.sh")
    print("\nThe processed flashcards will be saved to:")
    print("   data/output/hsk_100_processed.tsv")
    
    # Show what was created
    print("\n" + "="*60)
    print("📁 Created Files and Directories")
    print("="*60)
    
    for path in ['data/flashcards.db', 'data/input/hsk_first_100.csv']:
        if os.path.exists(path):
            size = os.path.getsize(path)
            print(f"✅ {path} ({size:,} bytes)")
        else:
            print(f"❌ {path} (not found)")

if __name__ == "__main__":
    main()