"""Simple test to verify testing infrastructure"""

def test_basic():
    """Basic test that should pass"""
    assert 1 + 1 == 2

def test_import_models():
    """Test we can import models"""
    from flashcard_pipeline.models import VocabularyItem
    
    item = VocabularyItem(position=1, term="test", type="noun")
    assert item.position == 1
    assert item.term == "test"