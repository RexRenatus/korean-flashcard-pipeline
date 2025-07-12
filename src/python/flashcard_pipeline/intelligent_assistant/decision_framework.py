#!/usr/bin/env python3
"""
Collaborative Decision Framework
Structured decision-making system for human-AI collaboration
"""
import json
import sqlite3
from typing import Dict, List, Any, Optional, Tuple, Set
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import uuid
from collections import defaultdict
import numpy as np

class DecisionType(Enum):
    """Types of decisions"""
    TECHNICAL = "technical"
    ARCHITECTURAL = "architectural"
    PROCESS = "process"
    RESOURCE = "resource"
    PRIORITY = "priority"
    RISK = "risk"
    STRATEGIC = "strategic"

class DecisionStatus(Enum):
    """Status of a decision"""
    PENDING = "pending"
    ANALYZING = "analyzing"
    OPTIONS_PRESENTED = "options_presented"
    DECIDED = "decided"
    IMPLEMENTED = "implemented"
    REVIEWED = "reviewed"
    REVISED = "revised"

class StakeholderRole(Enum):
    """Roles in decision making"""
    INITIATOR = "initiator"
    ANALYST = "analyst"
    APPROVER = "approver"
    IMPLEMENTER = "implementer"
    REVIEWER = "reviewer"
    OBSERVER = "observer"

@dataclass
class DecisionCriteria:
    """Criteria for evaluating decisions"""
    name: str
    weight: float
    description: str
    measurement: str
    threshold: Optional[float] = None

@dataclass
class DecisionOption:
    """An option for a decision"""
    id: str
    title: str
    description: str
    pros: List[str]
    cons: List[str]
    risks: List[Dict[str, Any]]
    effort_estimate: str
    impact_assessment: Dict[str, float]
    confidence: float
    recommendation_score: float = 0.0
    supporting_evidence: List[Dict[str, str]] = field(default_factory=list)

@dataclass
class Decision:
    """A decision to be made"""
    id: str
    type: DecisionType
    title: str
    description: str
    context: Dict[str, Any]
    criteria: List[DecisionCriteria]
    options: List[DecisionOption]
    status: DecisionStatus
    created_at: datetime
    deadline: Optional[datetime]
    stakeholders: Dict[StakeholderRole, List[str]]
    chosen_option: Optional[str] = None
    rationale: Optional[str] = None
    outcome: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

class CollaborativeDecisionFramework:
    """Framework for structured collaborative decision making"""
    
    def __init__(self, db_path: str = ".claude/decisions.db"):
        self.db_path = db_path
        self._init_database()
        
        # Decision templates
        self.templates = self._load_decision_templates()
        
        # Analysis methods
        self.analysis_methods = {
            'weighted_criteria': self._weighted_criteria_analysis,
            'risk_impact': self._risk_impact_analysis,
            'cost_benefit': self._cost_benefit_analysis,
            'consensus': self._consensus_analysis,
            'precedent': self._precedent_analysis
        }
        
        # Decision history for learning
        self.decision_patterns = defaultdict(list)
        self._load_decision_patterns()
    
    def _init_database(self):
        """Initialize decision database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS decisions (
                id TEXT PRIMARY KEY,
                type TEXT NOT NULL,
                title TEXT NOT NULL,
                description TEXT,
                context TEXT,
                criteria TEXT,
                options TEXT,
                status TEXT NOT NULL,
                created_at TIMESTAMP,
                deadline TIMESTAMP,
                stakeholders TEXT,
                chosen_option TEXT,
                rationale TEXT,
                outcome TEXT,
                metadata TEXT
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS decision_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                decision_id TEXT,
                timestamp TIMESTAMP,
                action TEXT,
                actor TEXT,
                details TEXT,
                FOREIGN KEY (decision_id) REFERENCES decisions(id)
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS decision_outcomes (
                decision_id TEXT PRIMARY KEY,
                outcome_date TIMESTAMP,
                success_metrics TEXT,
                lessons_learned TEXT,
                would_repeat BOOLEAN,
                FOREIGN KEY (decision_id) REFERENCES decisions(id)
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def _load_decision_templates(self) -> Dict[DecisionType, Dict[str, Any]]:
        """Load decision templates for different types"""
        return {
            DecisionType.TECHNICAL: {
                'criteria': [
                    DecisionCriteria('Performance', 0.3, 'Impact on system performance', 'latency_ms'),
                    DecisionCriteria('Maintainability', 0.25, 'Ease of maintenance', 'complexity_score'),
                    DecisionCriteria('Scalability', 0.2, 'Ability to scale', 'max_throughput'),
                    DecisionCriteria('Security', 0.15, 'Security implications', 'vulnerability_score'),
                    DecisionCriteria('Cost', 0.1, 'Implementation cost', 'hours')
                ],
                'analysis_methods': ['weighted_criteria', 'risk_impact']
            },
            DecisionType.ARCHITECTURAL: {
                'criteria': [
                    DecisionCriteria('Flexibility', 0.3, 'System flexibility', 'coupling_score'),
                    DecisionCriteria('Reliability', 0.25, 'System reliability', 'uptime_percent'),
                    DecisionCriteria('Complexity', 0.2, 'Overall complexity', 'component_count'),
                    DecisionCriteria('Integration', 0.15, 'Integration ease', 'api_count'),
                    DecisionCriteria('Future-proof', 0.1, 'Future adaptability', 'tech_debt')
                ],
                'analysis_methods': ['weighted_criteria', 'precedent']
            },
            DecisionType.RISK: {
                'criteria': [
                    DecisionCriteria('Probability', 0.4, 'Likelihood of risk', 'probability'),
                    DecisionCriteria('Impact', 0.4, 'Potential impact', 'severity_score'),
                    DecisionCriteria('Mitigation', 0.2, 'Ease of mitigation', 'mitigation_cost')
                ],
                'analysis_methods': ['risk_impact', 'cost_benefit']
            }
        }
    
    def create_decision(self, title: str, description: str, 
                       decision_type: DecisionType,
                       context: Dict[str, Any],
                       deadline: Optional[datetime] = None) -> Decision:
        """Create a new decision"""
        decision_id = str(uuid.uuid4())
        
        # Get template for this type
        template = self.templates.get(decision_type, {})
        
        decision = Decision(
            id=decision_id,
            type=decision_type,
            title=title,
            description=description,
            context=context,
            criteria=template.get('criteria', []),
            options=[],
            status=DecisionStatus.PENDING,
            created_at=datetime.now(),
            deadline=deadline,
            stakeholders={role: [] for role in StakeholderRole}
        )
        
        self._save_decision(decision)
        self._log_action(decision_id, 'created', 'system', {'title': title})
        
        return decision
    
    def add_option(self, decision_id: str, option: DecisionOption):
        """Add an option to a decision"""
        decision = self.get_decision(decision_id)
        if not decision:
            raise ValueError(f"Decision {decision_id} not found")
        
        # Generate ID if not provided
        if not option.id:
            option.id = f"option_{len(decision.options) + 1}"
        
        decision.options.append(option)
        decision.status = DecisionStatus.ANALYZING
        
        self._save_decision(decision)
        self._log_action(decision_id, 'option_added', 'system', {'option': option.title})
    
    def analyze_options(self, decision_id: str, 
                       methods: Optional[List[str]] = None) -> Dict[str, Any]:
        """Analyze options using specified methods"""
        decision = self.get_decision(decision_id)
        if not decision:
            raise ValueError(f"Decision {decision_id} not found")
        
        # Use template methods if not specified
        if not methods:
            template = self.templates.get(decision.type, {})
            methods = template.get('analysis_methods', ['weighted_criteria'])
        
        analysis_results = {}
        
        for method in methods:
            if method in self.analysis_methods:
                analysis_results[method] = self.analysis_methods[method](decision)
        
        # Update recommendation scores
        self._update_recommendation_scores(decision, analysis_results)
        
        decision.status = DecisionStatus.OPTIONS_PRESENTED
        self._save_decision(decision)
        self._log_action(decision_id, 'analyzed', 'system', {'methods': methods})
        
        return analysis_results
    
    def _weighted_criteria_analysis(self, decision: Decision) -> Dict[str, Any]:
        """Analyze options using weighted criteria"""
        scores = {}
        
        for option in decision.options:
            total_score = 0
            criteria_scores = {}
            
            for criterion in decision.criteria:
                # Get score from impact assessment
                score = option.impact_assessment.get(criterion.name, 0.5)
                weighted_score = score * criterion.weight
                criteria_scores[criterion.name] = {
                    'raw': score,
                    'weighted': weighted_score
                }
                total_score += weighted_score
            
            scores[option.id] = {
                'total': total_score,
                'criteria': criteria_scores,
                'normalized': total_score  # Already normalized to 0-1
            }
        
        # Rank options
        ranked = sorted(scores.items(), key=lambda x: x[1]['total'], reverse=True)
        
        return {
            'scores': scores,
            'ranking': [opt_id for opt_id, _ in ranked],
            'winner': ranked[0][0] if ranked else None,
            'confidence': self._calculate_confidence(scores)
        }
    
    def _risk_impact_analysis(self, decision: Decision) -> Dict[str, Any]:
        """Analyze options based on risk and impact"""
        risk_scores = {}
        
        for option in decision.options:
            # Calculate risk score
            total_risk = 0
            for risk in option.risks:
                probability = risk.get('probability', 0.5)
                impact = risk.get('impact', 0.5)
                risk_score = probability * impact
                total_risk += risk_score
            
            # Average risk
            avg_risk = total_risk / max(len(option.risks), 1)
            
            # Calculate opportunity (inverse of risk with impact consideration)
            avg_impact = np.mean(list(option.impact_assessment.values()))
            opportunity = avg_impact * (1 - avg_risk)
            
            risk_scores[option.id] = {
                'risk': avg_risk,
                'opportunity': opportunity,
                'risk_adjusted_score': opportunity,
                'risk_details': option.risks
            }
        
        # Rank by opportunity
        ranked = sorted(risk_scores.items(), 
                       key=lambda x: x[1]['risk_adjusted_score'], 
                       reverse=True)
        
        return {
            'risk_scores': risk_scores,
            'ranking': [opt_id for opt_id, _ in ranked],
            'recommended': ranked[0][0] if ranked else None
        }
    
    def _cost_benefit_analysis(self, decision: Decision) -> Dict[str, Any]:
        """Analyze cost vs benefit"""
        analyses = {}
        
        for option in decision.options:
            # Simple cost-benefit using effort and impact
            effort_map = {'low': 0.2, 'medium': 0.5, 'high': 0.8, 'very_high': 0.9}
            cost = effort_map.get(option.effort_estimate.lower(), 0.5)
            
            # Average benefit from impact assessment
            benefit = np.mean(list(option.impact_assessment.values()))
            
            # ROI calculation
            roi = (benefit - cost) / max(cost, 0.1)
            
            analyses[option.id] = {
                'cost': cost,
                'benefit': benefit,
                'roi': roi,
                'payback_period': f"{int(cost/max(benefit, 0.1) * 12)} months" if benefit > 0 else "Never"
            }
        
        # Rank by ROI
        ranked = sorted(analyses.items(), key=lambda x: x[1]['roi'], reverse=True)
        
        return {
            'analyses': analyses,
            'ranking': [opt_id for opt_id, _ in ranked],
            'best_roi': ranked[0][0] if ranked else None
        }
    
    def _consensus_analysis(self, decision: Decision) -> Dict[str, Any]:
        """Analyze based on stakeholder consensus"""
        # This would integrate with actual stakeholder feedback
        # For now, simulate based on option characteristics
        consensus_scores = {}
        
        for option in decision.options:
            # Factors that typically drive consensus
            clarity = 1.0 - len(option.cons) / (len(option.pros) + len(option.cons) + 1)
            low_risk = 1.0 - np.mean([r['probability'] * r['impact'] 
                                     for r in option.risks]) if option.risks else 0.8
            high_confidence = option.confidence
            
            consensus = (clarity + low_risk + high_confidence) / 3
            
            consensus_scores[option.id] = {
                'consensus_score': consensus,
                'factors': {
                    'clarity': clarity,
                    'low_risk': low_risk,
                    'confidence': high_confidence
                }
            }
        
        ranked = sorted(consensus_scores.items(), 
                       key=lambda x: x[1]['consensus_score'], 
                       reverse=True)
        
        return {
            'consensus': consensus_scores,
            'ranking': [opt_id for opt_id, _ in ranked],
            'most_consensus': ranked[0][0] if ranked else None
        }
    
    def _precedent_analysis(self, decision: Decision) -> Dict[str, Any]:
        """Analyze based on historical precedents"""
        precedent_scores = {}
        
        # Look for similar past decisions
        similar_decisions = self._find_similar_decisions(decision)
        
        for option in decision.options:
            # Check how similar options performed in the past
            historical_success = 0.5  # Default
            precedent_count = 0
            
            for past_decision in similar_decisions:
                for past_option in past_decision.get('options', []):
                    if self._options_similar(option, past_option):
                        precedent_count += 1
                        if past_decision.get('outcome', {}).get('success', False):
                            historical_success += 0.1
            
            precedent_scores[option.id] = {
                'historical_success_rate': min(historical_success, 1.0),
                'precedent_count': precedent_count,
                'confidence': min(precedent_count / 10, 1.0)
            }
        
        ranked = sorted(precedent_scores.items(), 
                       key=lambda x: x[1]['historical_success_rate'], 
                       reverse=True)
        
        return {
            'precedents': precedent_scores,
            'ranking': [opt_id for opt_id, _ in ranked],
            'historically_best': ranked[0][0] if ranked else None
        }
    
    def _update_recommendation_scores(self, decision: Decision, 
                                    analysis_results: Dict[str, Any]):
        """Update recommendation scores based on analyses"""
        # Aggregate scores from different analyses
        option_scores = defaultdict(list)
        
        for method, results in analysis_results.items():
            ranking = results.get('ranking', [])
            for i, option_id in enumerate(ranking):
                # Higher score for better ranking
                score = 1.0 - (i / len(ranking)) if ranking else 0.5
                option_scores[option_id].append(score)
        
        # Update options with average scores
        for option in decision.options:
            if option.id in option_scores:
                option.recommendation_score = np.mean(option_scores[option.id])
    
    def make_decision(self, decision_id: str, chosen_option_id: str, 
                     rationale: str, actor: str = "user") -> Decision:
        """Record the decision made"""
        decision = self.get_decision(decision_id)
        if not decision:
            raise ValueError(f"Decision {decision_id} not found")
        
        decision.chosen_option = chosen_option_id
        decision.rationale = rationale
        decision.status = DecisionStatus.DECIDED
        
        self._save_decision(decision)
        self._log_action(decision_id, 'decided', actor, {
            'chosen': chosen_option_id,
            'rationale': rationale
        })
        
        # Learn from this decision
        self._learn_from_decision(decision)
        
        return decision
    
    def implement_decision(self, decision_id: str, 
                         implementation_notes: str) -> Decision:
        """Mark decision as implemented"""
        decision = self.get_decision(decision_id)
        if not decision:
            raise ValueError(f"Decision {decision_id} not found")
        
        decision.status = DecisionStatus.IMPLEMENTED
        decision.metadata['implementation_notes'] = implementation_notes
        decision.metadata['implementation_date'] = datetime.now().isoformat()
        
        self._save_decision(decision)
        self._log_action(decision_id, 'implemented', 'system', {
            'notes': implementation_notes
        })
        
        return decision
    
    def record_outcome(self, decision_id: str, outcome: Dict[str, Any], 
                      lessons_learned: List[str], would_repeat: bool):
        """Record the outcome of a decision"""
        decision = self.get_decision(decision_id)
        if not decision:
            raise ValueError(f"Decision {decision_id} not found")
        
        decision.outcome = outcome
        decision.status = DecisionStatus.REVIEWED
        
        self._save_decision(decision)
        
        # Save outcome details
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO decision_outcomes
            (decision_id, outcome_date, success_metrics, lessons_learned, would_repeat)
            VALUES (?, ?, ?, ?, ?)
        ''', (
            decision_id,
            datetime.now().isoformat(),
            json.dumps(outcome),
            json.dumps(lessons_learned),
            would_repeat
        ))
        
        conn.commit()
        conn.close()
        
        self._log_action(decision_id, 'outcome_recorded', 'system', {
            'success': outcome.get('success', False),
            'would_repeat': would_repeat
        })
    
    def get_decision(self, decision_id: str) -> Optional[Decision]:
        """Retrieve a decision"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM decisions WHERE id = ?', (decision_id,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return self._row_to_decision(row)
        return None
    
    def _row_to_decision(self, row: Tuple) -> Decision:
        """Convert database row to Decision object"""
        return Decision(
            id=row[0],
            type=DecisionType(row[1]),
            title=row[2],
            description=row[3],
            context=json.loads(row[4]) if row[4] else {},
            criteria=[DecisionCriteria(**c) for c in json.loads(row[5])] if row[5] else [],
            options=[DecisionOption(**o) for o in json.loads(row[6])] if row[6] else [],
            status=DecisionStatus(row[7]),
            created_at=datetime.fromisoformat(row[8]),
            deadline=datetime.fromisoformat(row[9]) if row[9] else None,
            stakeholders=json.loads(row[10]) if row[10] else {},
            chosen_option=row[11],
            rationale=row[12],
            outcome=json.loads(row[13]) if row[13] else None,
            metadata=json.loads(row[14]) if row[14] else {}
        )
    
    def _save_decision(self, decision: Decision):
        """Save decision to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO decisions
            (id, type, title, description, context, criteria, options,
             status, created_at, deadline, stakeholders, chosen_option,
             rationale, outcome, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            decision.id,
            decision.type.value,
            decision.title,
            decision.description,
            json.dumps(decision.context),
            json.dumps([vars(c) for c in decision.criteria]),
            json.dumps([vars(o) for o in decision.options]),
            decision.status.value,
            decision.created_at.isoformat(),
            decision.deadline.isoformat() if decision.deadline else None,
            json.dumps(decision.stakeholders),
            decision.chosen_option,
            decision.rationale,
            json.dumps(decision.outcome) if decision.outcome else None,
            json.dumps(decision.metadata)
        ))
        
        conn.commit()
        conn.close()
    
    def _log_action(self, decision_id: str, action: str, 
                   actor: str, details: Dict[str, Any]):
        """Log action in decision history"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO decision_history
            (decision_id, timestamp, action, actor, details)
            VALUES (?, ?, ?, ?, ?)
        ''', (
            decision_id,
            datetime.now().isoformat(),
            action,
            actor,
            json.dumps(details)
        ))
        
        conn.commit()
        conn.close()
    
    def _calculate_confidence(self, scores: Dict[str, Any]) -> float:
        """Calculate confidence in the analysis"""
        if not scores:
            return 0.0
        
        # Calculate spread of scores
        values = [s['total'] for s in scores.values()]
        if len(values) < 2:
            return 0.5
        
        # Higher confidence when there's clear separation
        spread = np.std(values)
        max_spread = 0.5  # Maximum possible spread for normalized scores
        confidence = min(spread / max_spread * 2, 1.0)
        
        return confidence
    
    def _find_similar_decisions(self, decision: Decision) -> List[Dict[str, Any]]:
        """Find similar past decisions"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Find decisions of same type
        cursor.execute('''
            SELECT * FROM decisions 
            WHERE type = ? AND id != ? AND status = ?
        ''', (decision.type.value, decision.id, DecisionStatus.REVIEWED.value))
        
        similar = []
        for row in cursor.fetchall():
            past_decision = self._row_to_decision(row)
            # Simple similarity based on context overlap
            if self._contexts_similar(decision.context, past_decision.context):
                similar.append(vars(past_decision))
        
        conn.close()
        return similar[:5]  # Return top 5
    
    def _contexts_similar(self, context1: Dict[str, Any], 
                         context2: Dict[str, Any]) -> bool:
        """Check if two contexts are similar"""
        # Simple overlap check - could be enhanced
        keys1 = set(context1.keys())
        keys2 = set(context2.keys())
        
        overlap = len(keys1 & keys2) / max(len(keys1 | keys2), 1)
        return overlap > 0.5
    
    def _options_similar(self, option1: DecisionOption, 
                        option2: Dict[str, Any]) -> bool:
        """Check if two options are similar"""
        # Simple text similarity - could use more sophisticated methods
        text1 = f"{option1.title} {option1.description}".lower()
        text2 = f"{option2.get('title', '')} {option2.get('description', '')}".lower()
        
        words1 = set(text1.split())
        words2 = set(text2.split())
        
        overlap = len(words1 & words2) / max(len(words1 | words2), 1)
        return overlap > 0.3
    
    def _learn_from_decision(self, decision: Decision):
        """Learn patterns from decisions"""
        pattern = {
            'type': decision.type.value,
            'criteria': [c.name for c in decision.criteria],
            'chosen_characteristics': None,
            'success': None  # Will be updated when outcome is recorded
        }
        
        # Find characteristics of chosen option
        for option in decision.options:
            if option.id == decision.chosen_option:
                pattern['chosen_characteristics'] = {
                    'effort': option.effort_estimate,
                    'avg_impact': np.mean(list(option.impact_assessment.values())),
                    'risk_count': len(option.risks),
                    'confidence': option.confidence
                }
                break
        
        self.decision_patterns[decision.type.value].append(pattern)
    
    def _load_decision_patterns(self):
        """Load historical decision patterns"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT d.*, o.would_repeat
            FROM decisions d
            LEFT JOIN decision_outcomes o ON d.id = o.decision_id
            WHERE d.status = ?
        ''', (DecisionStatus.REVIEWED.value,))
        
        for row in cursor.fetchall():
            decision = self._row_to_decision(row[:-1])
            would_repeat = row[-1]
            
            pattern = {
                'type': decision.type.value,
                'success': would_repeat,
                'context': decision.context
            }
            
            self.decision_patterns[decision.type.value].append(pattern)
        
        conn.close()
    
    def get_decision_insights(self) -> Dict[str, Any]:
        """Get insights from decision history"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get statistics
        cursor.execute('SELECT COUNT(*) FROM decisions')
        total_decisions = cursor.fetchone()[0]
        
        cursor.execute('''
            SELECT status, COUNT(*) 
            FROM decisions 
            GROUP BY status
        ''')
        status_distribution = {row[0]: row[1] for row in cursor.fetchall()}
        
        cursor.execute('''
            SELECT type, COUNT(*) 
            FROM decisions 
            GROUP BY type
        ''')
        type_distribution = {row[0]: row[1] for row in cursor.fetchall()}
        
        cursor.execute('''
            SELECT AVG(would_repeat) 
            FROM decision_outcomes
        ''')
        success_rate = cursor.fetchone()[0] or 0
        
        conn.close()
        
        return {
            'total_decisions': total_decisions,
            'status_distribution': status_distribution,
            'type_distribution': type_distribution,
            'success_rate': success_rate,
            'patterns': {k: len(v) for k, v in self.decision_patterns.items()}
        }


def demo_decision_framework():
    """Demonstrate decision framework capabilities"""
    framework = CollaborativeDecisionFramework()
    
    print("Creating a technical decision...")
    
    # Create a decision
    decision = framework.create_decision(
        title="Choose Caching Strategy",
        description="Decide on the best caching strategy for our API",
        decision_type=DecisionType.TECHNICAL,
        context={
            'current_latency': '200ms',
            'target_latency': '50ms',
            'daily_requests': '1M',
            'data_volatility': 'medium'
        },
        deadline=datetime.now() + timedelta(days=7)
    )
    
    print(f"Decision created: {decision.id}")
    
    # Add options
    print("\nAdding options...")
    
    option1 = DecisionOption(
        id="",
        title="Redis with Write-Through Cache",
        description="Use Redis as primary cache with write-through strategy",
        pros=[
            "Very fast reads",
            "Consistent data",
            "Proven technology"
        ],
        cons=[
            "Additional infrastructure",
            "Complexity in cache invalidation"
        ],
        risks=[
            {'name': 'Redis failure', 'probability': 0.1, 'impact': 0.8},
            {'name': 'Cache inconsistency', 'probability': 0.3, 'impact': 0.5}
        ],
        effort_estimate="medium",
        impact_assessment={
            'Performance': 0.9,
            'Maintainability': 0.6,
            'Scalability': 0.8,
            'Security': 0.7,
            'Cost': 0.4
        },
        confidence=0.85
    )
    
    option2 = DecisionOption(
        id="",
        title="In-Memory LRU Cache",
        description="Simple in-memory cache with LRU eviction",
        pros=[
            "Simple implementation",
            "No external dependencies",
            "Low latency"
        ],
        cons=[
            "Limited by memory",
            "Not distributed",
            "Lost on restart"
        ],
        risks=[
            {'name': 'Memory overflow', 'probability': 0.4, 'impact': 0.6},
            {'name': 'Cache misses', 'probability': 0.5, 'impact': 0.4}
        ],
        effort_estimate="low",
        impact_assessment={
            'Performance': 0.7,
            'Maintainability': 0.9,
            'Scalability': 0.4,
            'Security': 0.8,
            'Cost': 0.9
        },
        confidence=0.75
    )
    
    framework.add_option(decision.id, option1)
    framework.add_option(decision.id, option2)
    
    # Analyze options
    print("\nAnalyzing options...")
    analysis = framework.analyze_options(decision.id)
    
    # Display results
    print("\nAnalysis Results:")
    print("=" * 50)
    
    for method, results in analysis.items():
        print(f"\n{method.upper()}:")
        if 'ranking' in results:
            print(f"Ranking: {results['ranking']}")
        if 'winner' in results:
            print(f"Recommended: {results['winner']}")
        if 'confidence' in results:
            print(f"Confidence: {results['confidence']:.2f}")
    
    # Make decision
    print("\n\nMaking decision...")
    decision = framework.make_decision(
        decision.id,
        chosen_option_id=option1.id,
        rationale="Redis provides the best performance with acceptable complexity",
        actor="tech_lead"
    )
    
    print(f"Decision made: {decision.chosen_option}")
    print(f"Rationale: {decision.rationale}")
    
    # Get insights
    print("\n\nDecision Framework Insights:")
    insights = framework.get_decision_insights()
    print(f"Total decisions: {insights['total_decisions']}")
    print(f"Success rate: {insights['success_rate']:.2%}")
    print(f"Type distribution: {insights['type_distribution']}")


if __name__ == "__main__":
    demo_decision_framework()