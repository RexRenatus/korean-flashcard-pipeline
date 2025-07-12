#!/usr/bin/env python3
"""
Enhanced Intent Understanding System
Provides semantic analysis and context-aware intent detection for better human-AI collaboration
"""
import re
import json
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import spacy
from collections import defaultdict
import os

class IntentType(Enum):
    """Types of user intents"""
    IMPLEMENT = "implement"
    FIX = "fix"
    REFACTOR = "refactor"
    OPTIMIZE = "optimize"
    DOCUMENT = "document"
    TEST = "test"
    REVIEW = "review"
    EXPLORE = "explore"
    CONFIGURE = "configure"
    DEPLOY = "deploy"
    ANALYZE = "analyze"
    DESIGN = "design"

class Urgency(Enum):
    """Task urgency levels"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

@dataclass
class Intent:
    """Structured representation of user intent"""
    primary_intent: IntentType
    secondary_intents: List[IntentType]
    entities: Dict[str, List[str]]
    urgency: Urgency
    complexity: int  # 1-10 scale
    requires_planning: bool
    suggested_approach: str
    clarifications_needed: List[str]
    related_files: List[str]
    dependencies: List[str]

class IntentAnalyzer:
    """Advanced intent analysis with NLP and domain understanding"""
    
    def __init__(self):
        # Initialize spaCy for NLP (using small model for speed)
        try:
            self.nlp = spacy.load("en_core_web_sm")
        except:
            # Fallback to basic analysis if spaCy not available
            self.nlp = None
            
        # Domain-specific patterns
        self.intent_patterns = {
            IntentType.IMPLEMENT: [
                r'\b(implement|create|build|add|develop|write)\b',
                r'\b(feature|functionality|capability|module|component)\b'
            ],
            IntentType.FIX: [
                r'\b(fix|repair|resolve|solve|debug|troubleshoot)\b',
                r'\b(bug|issue|problem|error|broken|failing)\b'
            ],
            IntentType.REFACTOR: [
                r'\b(refactor|restructure|reorganize|clean up|improve)\b',
                r'\b(code|structure|architecture|design)\b'
            ],
            IntentType.OPTIMIZE: [
                r'\b(optimize|speed up|improve performance|enhance|accelerate)\b',
                r'\b(performance|speed|efficiency|throughput)\b'
            ],
            IntentType.DOCUMENT: [
                r'\b(document|explain|describe|annotate|comment)\b',
                r'\b(documentation|docs|readme|guide|tutorial)\b'
            ],
            IntentType.TEST: [
                r'\b(test|validate|verify|check|ensure)\b',
                r'\b(unit test|integration test|coverage|testing)\b'
            ],
            IntentType.ANALYZE: [
                r'\b(analyze|investigate|research|examine|study)\b',
                r'\b(analysis|investigation|review|audit)\b'
            ]
        }
        
        # Technical entity patterns
        self.entity_patterns = {
            'files': r'(?:[\w/]+\.(?:py|js|ts|rs|md|json|yaml|yml|txt))',
            'functions': r'(?:def|function|fn|async def)\s+(\w+)',
            'classes': r'(?:class|struct|interface)\s+(\w+)',
            'modules': r'(?:from|import)\s+([\w.]+)',
            'errors': r'(?:Error|Exception|Failed|Invalid)(?:\w*)',
            'commands': r'(?:python|pip|npm|cargo|git|docker)\s+[\w\s-]+',
        }
        
        # Urgency indicators
        self.urgency_patterns = {
            Urgency.CRITICAL: ['asap', 'urgent', 'critical', 'immediately', 'emergency'],
            Urgency.HIGH: ['quickly', 'soon', 'priority', 'important'],
            Urgency.MEDIUM: ['when you can', 'moderate', 'normal'],
            Urgency.LOW: ['eventually', 'low priority', 'when possible', 'nice to have']
        }
        
        # Complexity indicators
        self.complexity_indicators = {
            'simple': ['simple', 'basic', 'straightforward', 'easy', 'trivial'],
            'moderate': ['moderate', 'standard', 'typical', 'regular'],
            'complex': ['complex', 'complicated', 'sophisticated', 'advanced', 'challenging'],
            'multi_file': ['multiple files', 'across', 'throughout', 'entire', 'all'],
            'architectural': ['architecture', 'design', 'structure', 'framework', 'system']
        }
        
    def analyze(self, user_input: str, context: Optional[Dict[str, Any]] = None) -> Intent:
        """
        Analyze user input to extract structured intent
        
        Args:
            user_input: Raw user request
            context: Optional context (current file, recent errors, etc.)
            
        Returns:
            Structured Intent object
        """
        # Normalize input
        normalized = user_input.lower()
        
        # Extract intents
        primary_intent, secondary_intents = self._extract_intents(normalized)
        
        # Extract entities
        entities = self._extract_entities(user_input)
        
        # Determine urgency
        urgency = self._determine_urgency(normalized)
        
        # Calculate complexity
        complexity = self._calculate_complexity(normalized, entities)
        
        # Determine if planning is needed
        requires_planning = self._requires_planning(primary_intent, complexity, entities)
        
        # Generate suggested approach
        suggested_approach = self._suggest_approach(primary_intent, entities, complexity)
        
        # Identify clarifications needed
        clarifications = self._identify_clarifications(user_input, entities, context)
        
        # Find related files
        related_files = self._find_related_files(entities, context)
        
        # Identify dependencies
        dependencies = self._identify_dependencies(primary_intent, entities)
        
        return Intent(
            primary_intent=primary_intent,
            secondary_intents=secondary_intents,
            entities=entities,
            urgency=urgency,
            complexity=complexity,
            requires_planning=requires_planning,
            suggested_approach=suggested_approach,
            clarifications_needed=clarifications,
            related_files=related_files,
            dependencies=dependencies
        )
    
    def _extract_intents(self, text: str) -> Tuple[IntentType, List[IntentType]]:
        """Extract primary and secondary intents from text"""
        intent_scores = defaultdict(int)
        
        for intent_type, patterns in self.intent_patterns.items():
            for pattern in patterns:
                matches = re.findall(pattern, text, re.IGNORECASE)
                intent_scores[intent_type] += len(matches)
        
        # Sort by score
        sorted_intents = sorted(intent_scores.items(), key=lambda x: x[1], reverse=True)
        
        if not sorted_intents or sorted_intents[0][1] == 0:
            # Default to IMPLEMENT if no clear intent
            return IntentType.IMPLEMENT, []
        
        primary = sorted_intents[0][0]
        secondary = [intent for intent, score in sorted_intents[1:] if score > 0]
        
        return primary, secondary
    
    def _extract_entities(self, text: str) -> Dict[str, List[str]]:
        """Extract technical entities from text"""
        entities = defaultdict(list)
        
        for entity_type, pattern in self.entity_patterns.items():
            matches = re.findall(pattern, text, re.IGNORECASE)
            entities[entity_type].extend(matches)
        
        # Use NLP for additional entity extraction if available
        if self.nlp:
            doc = self.nlp(text)
            for ent in doc.ents:
                if ent.label_ in ['PERSON', 'ORG', 'PRODUCT']:
                    entities['named_entities'].append(ent.text)
        
        return dict(entities)
    
    def _determine_urgency(self, text: str) -> Urgency:
        """Determine task urgency from text"""
        for urgency_level, indicators in self.urgency_patterns.items():
            for indicator in indicators:
                if indicator in text:
                    return urgency_level
        return Urgency.MEDIUM
    
    def _calculate_complexity(self, text: str, entities: Dict[str, List[str]]) -> int:
        """Calculate task complexity (1-10 scale)"""
        complexity = 3  # Base complexity
        
        # Check complexity indicators
        if any(indicator in text for indicator in self.complexity_indicators['simple']):
            complexity -= 1
        if any(indicator in text for indicator in self.complexity_indicators['complex']):
            complexity += 2
        if any(indicator in text for indicator in self.complexity_indicators['architectural']):
            complexity += 3
        
        # Factor in entity counts
        total_entities = sum(len(v) for v in entities.values())
        if total_entities > 5:
            complexity += 1
        if total_entities > 10:
            complexity += 1
        
        # Multi-file operations are more complex
        if len(entities.get('files', [])) > 2:
            complexity += 2
        
        return min(10, max(1, complexity))
    
    def _requires_planning(self, intent: IntentType, complexity: int, entities: Dict[str, List[str]]) -> bool:
        """Determine if task requires planning mode"""
        # High complexity always needs planning
        if complexity >= 7:
            return True
        
        # Certain intents typically need planning
        if intent in [IntentType.REFACTOR, IntentType.DESIGN, IntentType.DEPLOY]:
            return True
        
        # Multi-file operations need planning
        if len(entities.get('files', [])) > 2:
            return True
        
        return False
    
    def _suggest_approach(self, intent: IntentType, entities: Dict[str, List[str]], complexity: int) -> str:
        """Suggest approach based on intent and context"""
        suggestions = {
            IntentType.IMPLEMENT: "Start with interface design, then implement core logic, add tests, and document",
            IntentType.FIX: "Reproduce issue, identify root cause, implement fix, add regression test",
            IntentType.REFACTOR: "Analyze current structure, identify improvements, refactor incrementally with tests",
            IntentType.OPTIMIZE: "Profile current performance, identify bottlenecks, optimize critical paths",
            IntentType.TEST: "Identify test cases, implement unit tests, add integration tests, check coverage",
            IntentType.DOCUMENT: "Analyze code structure, add inline comments, create user documentation",
            IntentType.ANALYZE: "Gather data, analyze patterns, identify insights, create summary report"
        }
        
        base_suggestion = suggestions.get(intent, "Analyze requirements, plan approach, implement solution")
        
        # Add complexity-specific advice
        if complexity >= 7:
            base_suggestion = "Create detailed plan first. " + base_suggestion
        
        return base_suggestion
    
    def _identify_clarifications(self, text: str, entities: Dict[str, List[str]], context: Optional[Dict[str, Any]]) -> List[str]:
        """Identify what clarifications might be needed"""
        clarifications = []
        
        # Check for ambiguous file references
        if 'files' not in entities or not entities['files']:
            if any(word in text.lower() for word in ['file', 'module', 'component']):
                clarifications.append("Which specific files should be modified?")
        
        # Check for missing error context
        if any(word in text.lower() for word in ['error', 'bug', 'issue', 'problem']):
            if 'errors' not in entities or not entities['errors']:
                clarifications.append("What is the specific error message or behavior?")
        
        # Check for missing specifications
        if 'implement' in text.lower() or 'create' in text.lower():
            if not any(word in text.lower() for word in ['should', 'must', 'need']):
                clarifications.append("What are the specific requirements or acceptance criteria?")
        
        return clarifications
    
    def _find_related_files(self, entities: Dict[str, List[str]], context: Optional[Dict[str, Any]]) -> List[str]:
        """Find files related to the task"""
        related = []
        
        # Add explicitly mentioned files
        related.extend(entities.get('files', []))
        
        # Add test files for mentioned modules
        for module in entities.get('modules', []):
            test_file = f"test_{module}.py"
            related.append(test_file)
        
        # Add common configuration files if configuring
        if context and context.get('intent_type') == IntentType.CONFIGURE:
            related.extend(['settings.json', '.env', 'config.py'])
        
        return list(set(related))  # Remove duplicates
    
    def _identify_dependencies(self, intent: IntentType, entities: Dict[str, List[str]]) -> List[str]:
        """Identify task dependencies"""
        dependencies = []
        
        # Testing depends on implementation
        if intent == IntentType.TEST:
            dependencies.append("Implementation must be complete")
        
        # Documentation depends on stable code
        if intent == IntentType.DOCUMENT:
            dependencies.append("Code must be stable")
        
        # Deployment depends on tests
        if intent == IntentType.DEPLOY:
            dependencies.extend(["All tests must pass", "Documentation must be updated"])
        
        return dependencies

def enhance_user_request(request: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Main entry point for enhancing user requests
    
    Returns enhanced request with structured intent and suggestions
    """
    analyzer = IntentAnalyzer()
    intent = analyzer.analyze(request, context)
    
    return {
        'original_request': request,
        'enhanced_request': _format_enhanced_request(request, intent),
        'intent': {
            'primary': intent.primary_intent.value,
            'secondary': [i.value for i in intent.secondary_intents],
            'urgency': intent.urgency.value,
            'complexity': intent.complexity,
            'requires_planning': intent.requires_planning
        },
        'entities': intent.entities,
        'approach': intent.suggested_approach,
        'clarifications': intent.clarifications_needed,
        'related_files': intent.related_files,
        'dependencies': intent.dependencies
    }

def _format_enhanced_request(original: str, intent: Intent) -> str:
    """Format an enhanced version of the request with clarifications"""
    enhanced = f"**Task**: {original}\n\n"
    enhanced += f"**Intent**: {intent.primary_intent.value}"
    
    if intent.secondary_intents:
        enhanced += f" (also: {', '.join(i.value for i in intent.secondary_intents)})"
    
    enhanced += f"\n**Complexity**: {intent.complexity}/10"
    enhanced += f"\n**Urgency**: {intent.urgency.value}"
    
    if intent.clarifications_needed:
        enhanced += "\n\n**Clarifications Needed**:\n"
        for clarification in intent.clarifications_needed:
            enhanced += f"- {clarification}\n"
    
    enhanced += f"\n**Suggested Approach**: {intent.suggested_approach}"
    
    if intent.related_files:
        enhanced += f"\n**Related Files**: {', '.join(intent.related_files)}"
    
    if intent.dependencies:
        enhanced += "\n**Dependencies**:\n"
        for dep in intent.dependencies:
            enhanced += f"- {dep}\n"
    
    return enhanced

if __name__ == "__main__":
    # Test the intent analyzer
    test_requests = [
        "Fix the bug in the API client that's causing connection timeouts",
        "Implement a new caching system for better performance",
        "Refactor the database module to use connection pooling",
        "Can you help me understand how the authentication works?",
        "We need to optimize the flashcard generation pipeline ASAP"
    ]
    
    for request in test_requests:
        result = enhance_user_request(request)
        print(f"\nOriginal: {request}")
        print(f"Primary Intent: {result['intent']['primary']}")
        print(f"Complexity: {result['intent']['complexity']}/10")
        print(f"Approach: {result['approach']}")
        print("-" * 50)