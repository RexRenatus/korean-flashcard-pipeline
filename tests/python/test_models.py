import pytest
import json
from datetime import datetime, timedelta
from flashcard_pipeline.models import (
    VocabularyItem,
    Stage1Request,
    Stage1Response,
    Stage2Request,
    Stage2Response,
    FlashcardRow,
    ApiResponse,
    ApiUsage,
    RateLimitInfo,
    Comparison,
    Homonym
)


class TestVocabularyItem:
    def test_vocabulary_item_creation(self):
        item = VocabularyItem(
            position=1,
            term="안녕하세요",
            type="greeting"
        )
        assert item.position == 1
        assert item.term == "안녕하세요"
        assert item.type == "greeting"
    
    def test_vocabulary_item_optional_type(self):
        item = VocabularyItem(position=2, term="test")
        assert item.type == "unknown"  # Default value when not provided
    
    def test_vocabulary_item_validation(self):
        # VocabularyItem doesn't have built-in validation in Pydantic v2
        # Test that we can create items with various inputs
        item = VocabularyItem(position=1, term="test")
        assert item.position == 1
        assert item.term == "test"


class TestStage1Models:
    def test_stage1_request_creation(self):
        vocab_item = VocabularyItem(position=1, term="사랑", type="noun")
        request = Stage1Request.from_vocabulary_item(vocab_item)
        
        assert request.model == "@preset/nuance-creator"
        assert len(request.messages) == 1
        assert request.messages[0]["role"] == "user"
        
        # Check the content is properly formatted
        content = json.loads(request.messages[0]["content"])
        assert content["position"] == 1
        assert content["term"] == "사랑"
        assert content["type"] == "noun"
    
    def test_stage1_response_validation(self):
        response = Stage1Response(
            term_number=1,
            term="사랑",
            ipa="[sa.ɾaŋ]",
            pos="noun",
            primary_meaning="love",
            other_meanings="affection, romance",
            metaphor="like a warm embrace",
            metaphor_noun="embrace",
            metaphor_action="embracing",
            suggested_location="heart",
            anchor_object="rose",
            anchor_sensory="soft, warm",
            explanation="deep emotional connection",
            usage_context="romantic, familial",
            comparison=Comparison(
                vs="애정",
                nuance="사랑 is more romantic while 애정 is more general affection"
            ),
            homonyms=[],
            korean_keywords=["사랑", "애정"]
        )
        
        assert response.term == "사랑"
        assert response.comparison.vs == "애정"
        assert "romantic" in response.comparison.nuance
    
    def test_homonym_creation(self):
        homonym = Homonym(
            hanja="船",
            reading="배",
            meaning="boat",
            differentiator="transportation"
        )
        assert homonym.reading == "배"
        assert homonym.hanja == "船"
        assert homonym.differentiator == "transportation"


class TestStage2Models:
    def test_stage2_request_creation(self):
        vocab_item = VocabularyItem(position=1, term="먹다", type="verb")
        stage1_response = Stage1Response(
            term_number=1,
            term="먹다",
            ipa="[mʌk̚.t͈a]",
            pos="verb",
            primary_meaning="to eat",
            other_meanings="to consume",
            metaphor="like feeding",
            metaphor_noun="feeding",
            metaphor_action="consuming",
            suggested_location="kitchen",
            anchor_object="spoon",
            anchor_sensory="taste",
            explanation="action of consuming food",
            comparison=Comparison(
                vs="드시다",
                nuance="먹다 is casual while 드시다 is honorific"
            ),
            homonyms=[],
            korean_keywords=["먹다"]
        )
        
        request = Stage2Request.from_stage1_result(vocab_item, stage1_response)
        assert request.model == "@preset/nuance-flashcard-generator"
        assert len(request.messages) == 1
        assert request.messages[0]["role"] == "user"
        
        # Check the content includes stage1 result
        content = json.loads(request.messages[0]["content"])
        assert content["position"] == 1
        assert content["term"] == "먹다"
        assert "stage1_result" in content
        assert content["stage1_result"]["term"] == "먹다"
    
    def test_stage2_response_tsv_parsing(self):
        tsv_data = "1\t안녕하세요\t1\tgreeting\tHello (formal)\tFormal greeting\tannyeonghaseyo\tgreeting,formal\t"
        
        response = Stage2Response.from_tsv_content(tsv_data)
        assert len(response.rows) == 1
        row = response.rows[0]
        
        assert row.position == 1
        assert row.term == "안녕하세요"
        assert row.term_number == 1
        assert row.tab_name == "greeting"
        assert row.primer == "Hello (formal)"
        assert row.front == "Formal greeting"
        assert row.back == "annyeonghaseyo"
        assert row.tags == "greeting,formal"
        assert row.honorific_level == ""
    
    def test_flashcard_row_to_tsv(self):
        row = FlashcardRow(
            position=1,
            term="감사합니다",
            term_number=1,
            tab_name="expression",
            primer="Thank you (formal)",
            front="Expression of gratitude",
            back="gamsahamnida",
            tags="gratitude,formal",
            honorific_level="formal"
        )
        
        tsv = row.to_tsv_row()
        assert "\t" in tsv
        parts = tsv.split("\t")
        assert len(parts) == 9
        assert parts[0] == "1"
        assert parts[1] == "감사합니다"
        assert parts[7] == "gratitude,formal"
        assert parts[8] == "formal"


class TestApiModels:
    def test_api_usage_calculation(self):
        usage = ApiUsage(
            prompt_tokens=100,
            completion_tokens=200,
            total_tokens=300
        )
        assert usage.total_tokens == 300
        # Claude Sonnet 4: $15/1M tokens
        # 300 tokens / 1,000,000 * $15 = $0.0045
        assert usage.estimated_cost == 0.0045
    
    def test_rate_limit_info(self):
        headers = {
            "X-RateLimit-Limit": "100",
            "X-RateLimit-Remaining": "50",
            "X-RateLimit-Reset": str(int((datetime.now() + timedelta(minutes=5)).timestamp()))
        }
        
        rate_info = RateLimitInfo.from_headers(headers)
        assert rate_info.limit == 100
        assert rate_info.remaining == 50
        assert rate_info.reset_at > datetime.now()
    
    def test_api_response_parsing(self):
        response_data = {
            "choices": [{
                "message": {
                    "content": "Test response content"
                }
            }],
            "usage": {
                "prompt_tokens": 50,
                "completion_tokens": 100,
                "total_tokens": 150
            },
            "id": "test-id",
            "model": "test-model",
            "object": "chat.completion",
            "created": 1234567890
        }
        
        api_response = ApiResponse(**response_data)
        assert api_response.choices[0]["message"]["content"] == "Test response content"
        assert api_response.usage.total_tokens == 150


class TestModelValidation:
    def test_stage1_response_field_lengths(self):
        # Test that long fields are accepted
        long_text = "a" * 1000
        response = Stage1Response(
            term_number=1,
            term="test",
            ipa="[test]",
            pos="noun",
            primary_meaning=long_text,
            other_meanings=long_text,
            metaphor=long_text,
            metaphor_noun="test",
            metaphor_action="testing",
            suggested_location="place",
            anchor_object="thing",
            anchor_sensory="sense",
            explanation=long_text,
            comparison=Comparison(
                vs="other",
                nuance="test comparison"
            ),
            homonyms=[],
            korean_keywords=["test"]
        )
        assert len(response.primary_meaning) == 1000
    
    def test_flashcard_row_tag_parsing(self):
        row = FlashcardRow(
            position=1,
            term="test",
            term_number=1,
            tab_name="noun",
            primer="Test",
            front="Test",
            back="Test",
            tags="tag1,tag2,tag3",
            honorific_level=""
        )
        
        tsv = row.to_tsv_row()
        assert "tag1,tag2,tag3" in tsv