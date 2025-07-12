#!/usr/bin/env python3
"""
Advanced Session Persistence with Context Serialization
Maintains complete context across sessions including mental models and decision rationale
"""
import json
import pickle
import os
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Set
from dataclasses import dataclass, field, asdict
from enum import Enum
import hashlib
import sqlite3
from pathlib import Path

class ContextType(Enum):
    """Types of context that can be persisted"""
    TASK_STATE = "task_state"
    DECISION_HISTORY = "decision_history"
    CODE_UNDERSTANDING = "code_understanding"
    ERROR_PATTERNS = "error_patterns"
    USER_PREFERENCES = "user_preferences"
    MENTAL_MODEL = "mental_model"
    ACTIVE_PROBLEMS = "active_problems"
    LEARNED_PATTERNS = "learned_patterns"

@dataclass
class Decision:
    """Represents a decision made during development"""
    id: str
    timestamp: datetime
    context: str
    options_considered: List[str]
    chosen_option: str
    rationale: str
    outcome: Optional[str] = None
    confidence: float = 0.8

@dataclass
class MentalModel:
    """Represents understanding of a code component"""
    component: str
    understanding_level: float  # 0-1 scale
    key_concepts: List[str]
    relationships: Dict[str, List[str]]
    assumptions: List[str]
    questions: List[str]
    last_updated: datetime

@dataclass
class SessionContext:
    """Complete session context"""
    session_id: str
    start_time: datetime
    last_activity: datetime
    current_task: Optional[str]
    task_stack: List[str]
    completed_tasks: List[str]
    decisions: List[Decision]
    mental_models: Dict[str, MentalModel]
    error_history: List[Dict[str, Any]]
    code_changes: List[Dict[str, Any]]
    user_preferences: Dict[str, Any]
    learned_patterns: Dict[str, Any]
    active_problems: List[Dict[str, Any]]
    metadata: Dict[str, Any] = field(default_factory=dict)

class SessionManager:
    """Advanced session management with full context persistence"""
    
    def __init__(self, storage_path: str = ".claude/sessions"):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        # Initialize database for structured storage
        self.db_path = self.storage_path / "sessions.db"
        self._init_database()
        
        # Current session
        self.current_session: Optional[SessionContext] = None
        
        # In-memory caches
        self.pattern_cache = {}
        self.decision_index = {}
        
    def _init_database(self):
        """Initialize SQLite database for session storage"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Sessions table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sessions (
                session_id TEXT PRIMARY KEY,
                start_time TIMESTAMP,
                last_activity TIMESTAMP,
                current_task TEXT,
                task_stack TEXT,
                completed_tasks TEXT,
                metadata TEXT
            )
        ''')
        
        # Decisions table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS decisions (
                id TEXT PRIMARY KEY,
                session_id TEXT,
                timestamp TIMESTAMP,
                context TEXT,
                options_considered TEXT,
                chosen_option TEXT,
                rationale TEXT,
                outcome TEXT,
                confidence REAL,
                FOREIGN KEY (session_id) REFERENCES sessions(session_id)
            )
        ''')
        
        # Mental models table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS mental_models (
                id TEXT PRIMARY KEY,
                session_id TEXT,
                component TEXT,
                understanding_level REAL,
                key_concepts TEXT,
                relationships TEXT,
                assumptions TEXT,
                questions TEXT,
                last_updated TIMESTAMP,
                FOREIGN KEY (session_id) REFERENCES sessions(session_id)
            )
        ''')
        
        # Patterns table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS learned_patterns (
                pattern_id TEXT PRIMARY KEY,
                pattern_type TEXT,
                pattern_data TEXT,
                frequency INTEGER,
                last_seen TIMESTAMP,
                effectiveness REAL
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def start_session(self, session_id: Optional[str] = None) -> SessionContext:
        """Start a new session or resume existing one"""
        if session_id and self._session_exists(session_id):
            self.current_session = self._load_session(session_id)
            print(f"Resumed session: {session_id}")
        else:
            # Create new session
            session_id = session_id or self._generate_session_id()
            self.current_session = SessionContext(
                session_id=session_id,
                start_time=datetime.now(),
                last_activity=datetime.now(),
                current_task=None,
                task_stack=[],
                completed_tasks=[],
                decisions=[],
                mental_models={},
                error_history=[],
                code_changes=[],
                user_preferences={},
                learned_patterns={},
                active_problems=[]
            )
            print(f"Started new session: {session_id}")
        
        return self.current_session
    
    def save_session(self) -> None:
        """Save current session state"""
        if not self.current_session:
            return
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Save session metadata
        cursor.execute('''
            INSERT OR REPLACE INTO sessions 
            (session_id, start_time, last_activity, current_task, 
             task_stack, completed_tasks, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            self.current_session.session_id,
            self.current_session.start_time,
            self.current_session.last_activity,
            self.current_session.current_task,
            json.dumps(self.current_session.task_stack),
            json.dumps(self.current_session.completed_tasks),
            json.dumps(self.current_session.metadata)
        ))
        
        # Save decisions
        for decision in self.current_session.decisions:
            cursor.execute('''
                INSERT OR REPLACE INTO decisions
                (id, session_id, timestamp, context, options_considered,
                 chosen_option, rationale, outcome, confidence)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                decision.id,
                self.current_session.session_id,
                decision.timestamp,
                decision.context,
                json.dumps(decision.options_considered),
                decision.chosen_option,
                decision.rationale,
                decision.outcome,
                decision.confidence
            ))
        
        # Save mental models
        for component, model in self.current_session.mental_models.items():
            model_id = f"{self.current_session.session_id}_{component}"
            cursor.execute('''
                INSERT OR REPLACE INTO mental_models
                (id, session_id, component, understanding_level,
                 key_concepts, relationships, assumptions, questions, last_updated)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                model_id,
                self.current_session.session_id,
                component,
                model.understanding_level,
                json.dumps(model.key_concepts),
                json.dumps(model.relationships),
                json.dumps(model.assumptions),
                json.dumps(model.questions),
                model.last_updated
            ))
        
        conn.commit()
        conn.close()
        
        # Save full context as pickle for complex objects
        context_file = self.storage_path / f"{self.current_session.session_id}.pkl"
        with open(context_file, 'wb') as f:
            pickle.dump(self.current_session, f)
    
    def add_decision(self, context: str, options: List[str], 
                    chosen: str, rationale: str) -> Decision:
        """Record a decision made during development"""
        if not self.current_session:
            raise RuntimeError("No active session")
        
        decision = Decision(
            id=self._generate_decision_id(),
            timestamp=datetime.now(),
            context=context,
            options_considered=options,
            chosen_option=chosen,
            rationale=rationale
        )
        
        self.current_session.decisions.append(decision)
        self.current_session.last_activity = datetime.now()
        
        # Index for quick retrieval
        self.decision_index[context] = decision
        
        return decision
    
    def update_mental_model(self, component: str, 
                          concepts: Optional[List[str]] = None,
                          relationships: Optional[Dict[str, List[str]]] = None,
                          assumptions: Optional[List[str]] = None,
                          questions: Optional[List[str]] = None,
                          understanding_delta: float = 0.0) -> MentalModel:
        """Update mental model of a code component"""
        if not self.current_session:
            raise RuntimeError("No active session")
        
        if component in self.current_session.mental_models:
            model = self.current_session.mental_models[component]
            
            # Update existing model
            if concepts:
                model.key_concepts.extend(concepts)
                model.key_concepts = list(set(model.key_concepts))
            
            if relationships:
                for key, values in relationships.items():
                    if key in model.relationships:
                        model.relationships[key].extend(values)
                        model.relationships[key] = list(set(model.relationships[key]))
                    else:
                        model.relationships[key] = values
            
            if assumptions:
                model.assumptions.extend(assumptions)
                model.assumptions = list(set(model.assumptions))
            
            if questions:
                model.questions.extend(questions)
            
            model.understanding_level = min(1.0, model.understanding_level + understanding_delta)
            model.last_updated = datetime.now()
        else:
            # Create new model
            model = MentalModel(
                component=component,
                understanding_level=0.5 + understanding_delta,
                key_concepts=concepts or [],
                relationships=relationships or {},
                assumptions=assumptions or [],
                questions=questions or [],
                last_updated=datetime.now()
            )
            self.current_session.mental_models[component] = model
        
        self.current_session.last_activity = datetime.now()
        return model
    
    def record_error(self, error_type: str, error_message: str, 
                    context: Dict[str, Any], solution: Optional[str] = None):
        """Record an error and its resolution"""
        if not self.current_session:
            raise RuntimeError("No active session")
        
        error_record = {
            'timestamp': datetime.now().isoformat(),
            'type': error_type,
            'message': error_message,
            'context': context,
            'solution': solution,
            'task': self.current_session.current_task
        }
        
        self.current_session.error_history.append(error_record)
        self.current_session.last_activity = datetime.now()
        
        # Learn from error pattern
        self._learn_error_pattern(error_type, context, solution)
    
    def learn_pattern(self, pattern_type: str, pattern_data: Dict[str, Any]):
        """Learn a new pattern from interaction"""
        if not self.current_session:
            raise RuntimeError("No active session")
        
        pattern_key = f"{pattern_type}:{self._hash_pattern(pattern_data)}"
        
        if pattern_key in self.current_session.learned_patterns:
            # Update existing pattern
            pattern = self.current_session.learned_patterns[pattern_key]
            pattern['frequency'] += 1
            pattern['last_seen'] = datetime.now().isoformat()
        else:
            # New pattern
            self.current_session.learned_patterns[pattern_key] = {
                'type': pattern_type,
                'data': pattern_data,
                'frequency': 1,
                'first_seen': datetime.now().isoformat(),
                'last_seen': datetime.now().isoformat(),
                'effectiveness': 0.8  # Default effectiveness
            }
        
        self.current_session.last_activity = datetime.now()
    
    def get_relevant_context(self, query: str) -> Dict[str, Any]:
        """Retrieve relevant context for a query"""
        if not self.current_session:
            return {}
        
        context = {
            'current_task': self.current_session.current_task,
            'recent_decisions': [],
            'relevant_mental_models': {},
            'similar_errors': [],
            'applicable_patterns': []
        }
        
        # Find relevant decisions
        query_lower = query.lower()
        for decision in self.current_session.decisions[-10:]:  # Last 10 decisions
            if any(term in decision.context.lower() for term in query_lower.split()):
                context['recent_decisions'].append({
                    'context': decision.context,
                    'chosen': decision.chosen_option,
                    'rationale': decision.rationale
                })
        
        # Find relevant mental models
        for component, model in self.current_session.mental_models.items():
            if query_lower in component.lower() or \
               any(query_lower in concept.lower() for concept in model.key_concepts):
                context['relevant_mental_models'][component] = {
                    'understanding': model.understanding_level,
                    'concepts': model.key_concepts[:5],  # Top 5 concepts
                    'questions': model.questions[:3]  # Top 3 questions
                }
        
        # Find similar errors
        for error in self.current_session.error_history[-20:]:  # Last 20 errors
            if query_lower in error['message'].lower() or \
               query_lower in error.get('type', '').lower():
                context['similar_errors'].append({
                    'type': error['type'],
                    'message': error['message'],
                    'solution': error.get('solution', 'No solution recorded')
                })
        
        # Find applicable patterns
        for pattern_key, pattern in self.current_session.learned_patterns.items():
            if pattern['effectiveness'] > 0.7 and pattern['frequency'] > 2:
                context['applicable_patterns'].append({
                    'type': pattern['type'],
                    'frequency': pattern['frequency'],
                    'effectiveness': pattern['effectiveness']
                })
        
        return context
    
    def export_session_summary(self) -> Dict[str, Any]:
        """Export a summary of the current session"""
        if not self.current_session:
            return {}
        
        duration = datetime.now() - self.current_session.start_time
        
        return {
            'session_id': self.current_session.session_id,
            'duration': str(duration),
            'tasks_completed': len(self.current_session.completed_tasks),
            'current_task': self.current_session.current_task,
            'decisions_made': len(self.current_session.decisions),
            'components_understood': len(self.current_session.mental_models),
            'errors_encountered': len(self.current_session.error_history),
            'patterns_learned': len(self.current_session.learned_patterns),
            'understanding_levels': {
                component: model.understanding_level
                for component, model in self.current_session.mental_models.items()
            },
            'key_decisions': [
                {
                    'context': d.context,
                    'choice': d.chosen_option,
                    'rationale': d.rationale
                }
                for d in self.current_session.decisions[-5:]  # Last 5 decisions
            ]
        }
    
    def _session_exists(self, session_id: str) -> bool:
        """Check if a session exists"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT 1 FROM sessions WHERE session_id = ?', (session_id,))
        exists = cursor.fetchone() is not None
        conn.close()
        return exists
    
    def _load_session(self, session_id: str) -> SessionContext:
        """Load a session from storage"""
        # Try pickle file first for complete context
        context_file = self.storage_path / f"{session_id}.pkl"
        if context_file.exists():
            with open(context_file, 'rb') as f:
                return pickle.load(f)
        
        # Fall back to database reconstruction
        # (Implementation would reconstruct from database)
        raise NotImplementedError("Database reconstruction not implemented")
    
    def _generate_session_id(self) -> str:
        """Generate unique session ID"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        random_suffix = hashlib.md5(os.urandom(16)).hexdigest()[:6]
        return f"session_{timestamp}_{random_suffix}"
    
    def _generate_decision_id(self) -> str:
        """Generate unique decision ID"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        return f"decision_{timestamp}"
    
    def _hash_pattern(self, pattern_data: Dict[str, Any]) -> str:
        """Generate hash for pattern data"""
        pattern_str = json.dumps(pattern_data, sort_keys=True)
        return hashlib.md5(pattern_str.encode()).hexdigest()[:8]
    
    def _learn_error_pattern(self, error_type: str, context: Dict[str, Any], 
                           solution: Optional[str]):
        """Learn from error patterns"""
        pattern_data = {
            'error_type': error_type,
            'context_keys': list(context.keys()),
            'has_solution': solution is not None
        }
        self.learn_pattern('error_pattern', pattern_data)

# Singleton instance
_session_manager = None

def get_session_manager() -> SessionManager:
    """Get or create the session manager singleton"""
    global _session_manager
    if _session_manager is None:
        _session_manager = SessionManager()
    return _session_manager

if __name__ == "__main__":
    # Test the session manager
    manager = get_session_manager()
    
    # Start a new session
    session = manager.start_session()
    print(f"Started session: {session.session_id}")
    
    # Record some decisions
    manager.add_decision(
        context="Choosing API framework",
        options=["FastAPI", "Flask", "Django"],
        chosen="FastAPI",
        rationale="Better async support and automatic documentation"
    )
    
    # Update mental model
    manager.update_mental_model(
        component="api_client",
        concepts=["async/await", "rate limiting", "error handling"],
        relationships={"uses": ["httpx", "pydantic"], "implements": ["retry logic"]},
        understanding_delta=0.2
    )
    
    # Record an error
    manager.record_error(
        error_type="ConnectionError",
        error_message="Failed to connect to API",
        context={"endpoint": "/api/v1/flashcards", "timeout": 30},
        solution="Increased timeout and added retry logic"
    )
    
    # Save session
    manager.save_session()
    
    # Export summary
    summary = manager.export_session_summary()
    print("\nSession Summary:")
    print(json.dumps(summary, indent=2))