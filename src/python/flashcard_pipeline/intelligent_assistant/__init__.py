"""
Intelligent Assistant System
Advanced AI-powered assistance for better human-AI collaboration
"""

from .intent_analyzer import enhance_user_request, IntentAnalyzer
from .task_sequencer import TaskSequencer, Task, ExecutionPlan
from .session_manager import get_session_manager, SessionManager, SessionContext
from .error_prevention import ErrorPreventionSystem, analyze_project_for_errors
from .visual_communicator import VisualCommunicator
from .code_reviewer import SmartCodeReviewer, ReviewFinding, CodeMetrics
from .knowledge_manager import DynamicKnowledgeManager, KnowledgeItem, KnowledgeQuery
from .decision_framework import CollaborativeDecisionFramework, Decision, DecisionOption

__all__ = [
    # Intent Analysis
    'enhance_user_request',
    'IntentAnalyzer',
    
    # Task Sequencing
    'TaskSequencer',
    'Task',
    'ExecutionPlan',
    
    # Session Management
    'get_session_manager',
    'SessionManager',
    'SessionContext',
    
    # Error Prevention
    'ErrorPreventionSystem',
    'analyze_project_for_errors',
    
    # Visual Communication
    'VisualCommunicator',
    
    # Code Review
    'SmartCodeReviewer',
    'ReviewFinding',
    'CodeMetrics',
    
    # Knowledge Management
    'DynamicKnowledgeManager',
    'KnowledgeItem',
    'KnowledgeQuery',
    
    # Decision Framework
    'CollaborativeDecisionFramework',
    'Decision',
    'DecisionOption',
]

# Version info
__version__ = '2.0.0'
__author__ = 'Intelligent Assistant Team'