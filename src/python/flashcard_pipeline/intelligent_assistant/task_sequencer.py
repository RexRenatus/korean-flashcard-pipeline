#!/usr/bin/env python3
"""
Intelligent Task Sequencing and Dependency Analyzer
Optimizes task execution order and identifies parallelization opportunities
"""
import json
import networkx as nx
from typing import Dict, List, Any, Optional, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum
import re
from datetime import datetime, timedelta
from collections import defaultdict

class TaskStatus(Enum):
    """Task execution status"""
    PENDING = "pending"
    READY = "ready"
    IN_PROGRESS = "in_progress"
    BLOCKED = "blocked"
    COMPLETED = "completed"
    FAILED = "failed"

class ResourceType(Enum):
    """Types of resources tasks might need"""
    FILE = "file"
    DATABASE = "database"
    API = "api"
    HUMAN = "human"
    COMPUTE = "compute"
    NETWORK = "network"

@dataclass
class Task:
    """Represents a task with dependencies and resource requirements"""
    id: str
    name: str
    description: str
    estimated_duration: timedelta
    priority: int  # 1-10, higher is more important
    dependencies: List[str] = field(default_factory=list)
    resource_requirements: Dict[ResourceType, List[str]] = field(default_factory=dict)
    status: TaskStatus = TaskStatus.PENDING
    can_parallelize: bool = True
    requires_human: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class ExecutionPlan:
    """Optimized execution plan for tasks"""
    phases: List[List[Task]]  # Each phase contains tasks that can run in parallel
    critical_path: List[Task]
    total_duration: timedelta
    parallelization_factor: float
    bottlenecks: List[str]
    optimization_suggestions: List[str]

class TaskSequencer:
    """Intelligent task sequencing with dependency resolution"""
    
    def __init__(self):
        self.tasks: Dict[str, Task] = {}
        self.dependency_graph = nx.DiGraph()
        self.resource_usage = defaultdict(set)
        
        # Patterns for automatic dependency detection
        self.dependency_patterns = {
            'file_write': r'(?:write|create|modify|update)\s+(?:file|to)\s+([^\s]+)',
            'file_read': r'(?:read|load|import|from)\s+(?:file|from)\s+([^\s]+)',
            'function_call': r'(?:call|invoke|use|run)\s+(\w+)',
            'test_dependency': r'test\s+(?:for|of)\s+(\w+)',
            'api_call': r'(?:fetch|call|request)\s+(?:api|endpoint)\s+([^\s]+)',
        }
        
    def add_task(self, task: Task) -> None:
        """Add a task to the sequencer"""
        self.tasks[task.id] = task
        self.dependency_graph.add_node(task.id, task=task)
        
        # Add dependencies
        for dep_id in task.dependencies:
            if dep_id in self.tasks:
                self.dependency_graph.add_edge(dep_id, task.id)
        
        # Track resource usage
        for resource_type, resources in task.resource_requirements.items():
            for resource in resources:
                self.resource_usage[resource].add(task.id)
    
    def auto_detect_dependencies(self, task_descriptions: List[Tuple[str, str]]) -> None:
        """
        Automatically detect dependencies based on task descriptions
        
        Args:
            task_descriptions: List of (task_id, description) tuples
        """
        # Build a map of what each task produces/modifies
        task_outputs = defaultdict(set)
        task_inputs = defaultdict(set)
        
        for task_id, description in task_descriptions:
            # Extract file writes
            for match in re.finditer(self.dependency_patterns['file_write'], description, re.IGNORECASE):
                task_outputs[task_id].add(('file', match.group(1)))
            
            # Extract file reads
            for match in re.finditer(self.dependency_patterns['file_read'], description, re.IGNORECASE):
                task_inputs[task_id].add(('file', match.group(1)))
            
            # Extract function dependencies
            for match in re.finditer(self.dependency_patterns['function_call'], description, re.IGNORECASE):
                task_inputs[task_id].add(('function', match.group(1)))
            
            # Extract test dependencies
            for match in re.finditer(self.dependency_patterns['test_dependency'], description, re.IGNORECASE):
                task_inputs[task_id].add(('test_target', match.group(1)))
        
        # Create dependencies based on input/output analysis
        for consumer_id, inputs in task_inputs.items():
            for producer_id, outputs in task_outputs.items():
                if consumer_id != producer_id:
                    # Check if producer creates something consumer needs
                    if inputs & outputs:
                        if consumer_id in self.tasks and producer_id in self.tasks:
                            self.tasks[consumer_id].dependencies.append(producer_id)
                            self.dependency_graph.add_edge(producer_id, consumer_id)
    
    def analyze_dependencies(self) -> Dict[str, Any]:
        """Analyze the dependency graph for insights"""
        if not self.dependency_graph:
            return {"error": "No tasks in graph"}
        
        # Check for cycles
        try:
            cycles = list(nx.simple_cycles(self.dependency_graph))
            if cycles:
                return {
                    "error": "Circular dependencies detected",
                    "cycles": cycles
                }
        except:
            pass
        
        # Find critical path
        if self.dependency_graph.number_of_edges() > 0:
            # Add weights based on task duration
            for node in self.dependency_graph.nodes():
                task = self.tasks[node]
                self.dependency_graph.nodes[node]['weight'] = task.estimated_duration.total_seconds()
            
            # Find longest path (critical path)
            topo_order = list(nx.topological_sort(self.dependency_graph))
            distances = {node: 0 for node in self.dependency_graph.nodes()}
            predecessors = {node: None for node in self.dependency_graph.nodes()}
            
            for node in topo_order:
                for successor in self.dependency_graph.successors(node):
                    weight = self.tasks[node].estimated_duration.total_seconds()
                    if distances[node] + weight > distances[successor]:
                        distances[successor] = distances[node] + weight
                        predecessors[successor] = node
            
            # Reconstruct critical path
            end_node = max(distances, key=distances.get)
            critical_path = []
            current = end_node
            while current is not None:
                critical_path.append(current)
                current = predecessors[current]
            critical_path.reverse()
        else:
            critical_path = list(self.dependency_graph.nodes())
        
        # Identify bottlenecks (nodes with high in-degree)
        bottlenecks = []
        for node in self.dependency_graph.nodes():
            in_degree = self.dependency_graph.in_degree(node)
            if in_degree > 2:  # More than 2 dependencies
                bottlenecks.append({
                    'task': node,
                    'dependencies': list(self.dependency_graph.predecessors(node)),
                    'blocking': list(self.dependency_graph.successors(node))
                })
        
        return {
            'total_tasks': len(self.tasks),
            'critical_path': critical_path,
            'critical_path_duration': sum(
                self.tasks[node].estimated_duration.total_seconds() 
                for node in critical_path
            ) if critical_path else 0,
            'bottlenecks': bottlenecks,
            'max_parallelization': self._calculate_max_parallelization()
        }
    
    def optimize_execution_plan(self) -> ExecutionPlan:
        """Generate an optimized execution plan"""
        if not self.tasks:
            return ExecutionPlan(phases=[], critical_path=[], 
                               total_duration=timedelta(), 
                               parallelization_factor=0,
                               bottlenecks=[],
                               optimization_suggestions=[])
        
        # Topological sort to respect dependencies
        try:
            topo_order = list(nx.topological_sort(self.dependency_graph))
        except nx.NetworkXUnfeasible:
            # Handle cycles
            return ExecutionPlan(
                phases=[], 
                critical_path=[], 
                total_duration=timedelta(),
                parallelization_factor=0,
                bottlenecks=["Circular dependencies detected"],
                optimization_suggestions=["Resolve circular dependencies"]
            )
        
        # Group tasks into phases where each phase can run in parallel
        phases = []
        remaining = set(topo_order)
        completed = set()
        
        while remaining:
            # Find all tasks whose dependencies are satisfied
            current_phase = []
            for task_id in remaining:
                task = self.tasks[task_id]
                if all(dep in completed for dep in task.dependencies):
                    # Check resource conflicts
                    can_add = True
                    for existing_task_id in current_phase:
                        if self._has_resource_conflict(task_id, existing_task_id):
                            can_add = False
                            break
                    
                    if can_add and task.can_parallelize:
                        current_phase.append(task_id)
                    elif not current_phase:  # First task in phase
                        current_phase.append(task_id)
                        break  # Non-parallelizable task runs alone
            
            if not current_phase:
                # Deadlock - shouldn't happen with topo sort
                break
            
            phases.append([self.tasks[tid] for tid in current_phase])
            completed.update(current_phase)
            remaining.difference_update(current_phase)
        
        # Calculate metrics
        analysis = self.analyze_dependencies()
        critical_path = [self.tasks[tid] for tid in analysis['critical_path']]
        
        # Calculate total duration considering parallelization
        total_duration = timedelta()
        for phase in phases:
            phase_duration = max(task.estimated_duration for task in phase)
            total_duration += phase_duration
        
        # Calculate parallelization factor
        sequential_duration = sum(
            task.estimated_duration for task in self.tasks.values()
        )
        parallelization_factor = (
            sequential_duration.total_seconds() / total_duration.total_seconds()
            if total_duration.total_seconds() > 0 else 1.0
        )
        
        # Generate optimization suggestions
        suggestions = self._generate_optimization_suggestions(phases, analysis)
        
        return ExecutionPlan(
            phases=phases,
            critical_path=critical_path,
            total_duration=total_duration,
            parallelization_factor=parallelization_factor,
            bottlenecks=[b['task'] for b in analysis.get('bottlenecks', [])],
            optimization_suggestions=suggestions
        )
    
    def _has_resource_conflict(self, task1_id: str, task2_id: str) -> bool:
        """Check if two tasks have conflicting resource requirements"""
        task1 = self.tasks[task1_id]
        task2 = self.tasks[task2_id]
        
        # Check for exclusive resource conflicts
        for resource_type, resources1 in task1.resource_requirements.items():
            if resource_type in task2.resource_requirements:
                resources2 = task2.resource_requirements[resource_type]
                # File writes are exclusive
                if resource_type == ResourceType.FILE and set(resources1) & set(resources2):
                    return True
                # Database writes to same table are exclusive
                if resource_type == ResourceType.DATABASE and set(resources1) & set(resources2):
                    return True
        
        return False
    
    def _calculate_max_parallelization(self) -> int:
        """Calculate maximum possible parallel tasks"""
        if not self.dependency_graph:
            return 0
        
        # Use graph coloring to find maximum independent set size
        # This gives us the theoretical maximum parallelization
        complement = nx.complement(self.dependency_graph.to_undirected())
        cliques = list(nx.find_cliques(complement))
        return max(len(clique) for clique in cliques) if cliques else 1
    
    def _generate_optimization_suggestions(self, phases: List[List[Task]], 
                                         analysis: Dict[str, Any]) -> List[str]:
        """Generate suggestions for optimizing the execution plan"""
        suggestions = []
        
        # Check for underutilized phases
        max_parallel = analysis.get('max_parallelization', 1)
        for i, phase in enumerate(phases):
            if len(phase) < max_parallel and len(phase) < 3:
                suggestions.append(
                    f"Phase {i+1} has only {len(phase)} parallel tasks. "
                    f"Consider breaking down tasks for better parallelization."
                )
        
        # Check for long-running tasks that could be split
        for task in self.tasks.values():
            if task.estimated_duration > timedelta(minutes=30):
                suggestions.append(
                    f"Task '{task.name}' takes {task.estimated_duration}. "
                    f"Consider breaking it into smaller subtasks."
                )
        
        # Check for bottlenecks
        for bottleneck in analysis.get('bottlenecks', []):
            suggestions.append(
                f"Task '{bottleneck}' is a bottleneck with multiple dependencies. "
                f"Consider refactoring to reduce coupling."
            )
        
        # Check for resource contention
        for resource, task_ids in self.resource_usage.items():
            if len(task_ids) > 3:
                suggestions.append(
                    f"Resource '{resource}' is used by {len(task_ids)} tasks. "
                    f"Consider caching or pooling to reduce contention."
                )
        
        return suggestions
    
    def export_execution_plan(self, plan: ExecutionPlan) -> Dict[str, Any]:
        """Export execution plan as structured data"""
        return {
            'summary': {
                'total_phases': len(plan.phases),
                'total_tasks': sum(len(phase) for phase in plan.phases),
                'total_duration': str(plan.total_duration),
                'parallelization_factor': round(plan.parallelization_factor, 2),
                'speedup': f"{round((plan.parallelization_factor - 1) * 100)}%"
            },
            'phases': [
                {
                    'phase_number': i + 1,
                    'tasks': [
                        {
                            'id': task.id,
                            'name': task.name,
                            'duration': str(task.estimated_duration),
                            'priority': task.priority
                        }
                        for task in phase
                    ],
                    'duration': str(max(task.estimated_duration for task in phase)),
                    'parallel_count': len(phase)
                }
                for i, phase in enumerate(plan.phases)
            ],
            'critical_path': [
                {'id': task.id, 'name': task.name}
                for task in plan.critical_path
            ],
            'bottlenecks': plan.bottlenecks,
            'suggestions': plan.optimization_suggestions
        }

def create_sample_tasks() -> List[Task]:
    """Create sample tasks for testing"""
    return [
        Task("1", "Setup environment", "Install dependencies", 
             timedelta(minutes=5), 8,
             resource_requirements={ResourceType.NETWORK: ["internet"]}),
        
        Task("2", "Write API client", "Implement API client module",
             timedelta(minutes=30), 9,
             dependencies=["1"],
             resource_requirements={ResourceType.FILE: ["api_client.py"]}),
        
        Task("3", "Write database layer", "Implement database module",
             timedelta(minutes=25), 9,
             dependencies=["1"],
             resource_requirements={ResourceType.FILE: ["database.py"]}),
        
        Task("4", "Write tests for API", "Create unit tests for API client",
             timedelta(minutes=20), 7,
             dependencies=["2"],
             resource_requirements={ResourceType.FILE: ["test_api.py"]}),
        
        Task("5", "Write tests for DB", "Create unit tests for database",
             timedelta(minutes=20), 7,
             dependencies=["3"],
             resource_requirements={ResourceType.FILE: ["test_db.py"]}),
        
        Task("6", "Integration tests", "Create integration tests",
             timedelta(minutes=15), 8,
             dependencies=["4", "5"],
             resource_requirements={ResourceType.FILE: ["test_integration.py"]}),
        
        Task("7", "Documentation", "Write documentation",
             timedelta(minutes=15), 5,
             dependencies=["2", "3"],
             can_parallelize=True,
             resource_requirements={ResourceType.FILE: ["README.md"]}),
    ]

if __name__ == "__main__":
    # Test the task sequencer
    sequencer = TaskSequencer()
    
    # Add sample tasks
    tasks = create_sample_tasks()
    for task in tasks:
        sequencer.add_task(task)
    
    # Analyze dependencies
    print("Dependency Analysis:")
    analysis = sequencer.analyze_dependencies()
    print(f"Total tasks: {analysis['total_tasks']}")
    print(f"Critical path: {' -> '.join(analysis['critical_path'])}")
    print(f"Critical path duration: {analysis['critical_path_duration']/60:.1f} minutes")
    print(f"Max parallelization: {analysis['max_parallelization']} tasks")
    
    # Generate execution plan
    print("\nOptimized Execution Plan:")
    plan = sequencer.optimize_execution_plan()
    plan_data = sequencer.export_execution_plan(plan)
    
    print(f"Total phases: {plan_data['summary']['total_phases']}")
    print(f"Total duration: {plan_data['summary']['total_duration']}")
    print(f"Parallelization factor: {plan_data['summary']['parallelization_factor']}x")
    print(f"Speedup: {plan_data['summary']['speedup']}")
    
    print("\nPhases:")
    for phase in plan_data['phases']:
        print(f"\nPhase {phase['phase_number']} ({phase['duration']}, {phase['parallel_count']} parallel tasks):")
        for task in phase['tasks']:
            print(f"  - {task['name']} ({task['duration']})")
    
    if plan_data['suggestions']:
        print("\nOptimization Suggestions:")
        for suggestion in plan_data['suggestions']:
            print(f"  - {suggestion}")