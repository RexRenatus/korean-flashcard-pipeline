#!/usr/bin/env python3
"""
Visual Communication Tools
Generates diagrams, charts, and visual representations for better understanding
"""
import json
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
from datetime import datetime, timedelta
import textwrap

class DiagramType(Enum):
    """Types of diagrams we can generate"""
    FLOWCHART = "flowchart"
    SEQUENCE = "sequence"
    CLASS = "class"
    ARCHITECTURE = "architecture"
    GANTT = "gantt"
    MINDMAP = "mindmap"
    STATE = "state"
    DEPENDENCY = "dependency"

class VisualCommunicator:
    """Generates visual representations in Mermaid format"""
    
    def __init__(self):
        self.mermaid_themes = {
            'default': 'default',
            'dark': 'dark',
            'forest': 'forest',
            'neutral': 'neutral'
        }
        
    def generate_task_flowchart(self, tasks: List[Dict[str, Any]]) -> str:
        """Generate flowchart for task execution"""
        mermaid = ["```mermaid", "flowchart TD"]
        
        # Add nodes
        for task in tasks:
            task_id = task['id'].replace(' ', '_')
            label = textwrap.fill(task['name'], 20)
            
            # Style based on status
            if task.get('status') == 'completed':
                mermaid.append(f"    {task_id}[{label}]:::completed")
            elif task.get('status') == 'in_progress':
                mermaid.append(f"    {task_id}[{label}]:::active")
            else:
                mermaid.append(f"    {task_id}[{label}]")
        
        # Add dependencies
        for task in tasks:
            task_id = task['id'].replace(' ', '_')
            for dep in task.get('dependencies', []):
                dep_id = dep.replace(' ', '_')
                mermaid.append(f"    {dep_id} --> {task_id}")
        
        # Add styling
        mermaid.extend([
            "    classDef completed fill:#90EE90,stroke:#228B22,stroke-width:2px",
            "    classDef active fill:#FFE4B5,stroke:#FF8C00,stroke-width:2px",
            "```"
        ])
        
        return '\n'.join(mermaid)
    
    def generate_architecture_diagram(self, components: Dict[str, Any]) -> str:
        """Generate architecture diagram"""
        mermaid = ["```mermaid", "graph TB"]
        
        # Add subgraphs for layers
        layers = components.get('layers', {})
        for layer_name, layer_components in layers.items():
            mermaid.append(f"    subgraph {layer_name}")
            for comp in layer_components:
                comp_id = comp['name'].replace(' ', '_')
                mermaid.append(f"        {comp_id}[{comp['name']}]")
            mermaid.append("    end")
        
        # Add connections
        for connection in components.get('connections', []):
            from_id = connection['from'].replace(' ', '_')
            to_id = connection['to'].replace(' ', '_')
            label = connection.get('label', '')
            if label:
                mermaid.append(f"    {from_id} -->|{label}| {to_id}")
            else:
                mermaid.append(f"    {from_id} --> {to_id}")
        
        # Add external systems
        for external in components.get('external', []):
            ext_id = external.replace(' ', '_')
            mermaid.append(f"    {ext_id}[({external})]")
        
        mermaid.append("```")
        return '\n'.join(mermaid)
    
    def generate_sequence_diagram(self, interactions: List[Dict[str, Any]]) -> str:
        """Generate sequence diagram for interactions"""
        mermaid = ["```mermaid", "sequenceDiagram"]
        
        # Add participants
        participants = set()
        for interaction in interactions:
            participants.add(interaction['from'])
            participants.add(interaction['to'])
        
        for participant in sorted(participants):
            mermaid.append(f"    participant {participant}")
        
        # Add interactions
        for interaction in interactions:
            from_actor = interaction['from']
            to_actor = interaction['to']
            message = interaction['message']
            
            if interaction.get('type') == 'async':
                mermaid.append(f"    {from_actor}-->>+{to_actor}: {message}")
            else:
                mermaid.append(f"    {from_actor}->>+{to_actor}: {message}")
            
            if 'response' in interaction:
                mermaid.append(f"    {to_actor}-->>-{from_actor}: {interaction['response']}")
        
        mermaid.append("```")
        return '\n'.join(mermaid)
    
    def generate_class_diagram(self, classes: List[Dict[str, Any]]) -> str:
        """Generate class diagram"""
        mermaid = ["```mermaid", "classDiagram"]
        
        for cls in classes:
            class_name = cls['name']
            
            # Add class definition
            mermaid.append(f"    class {class_name} {{")
            
            # Add attributes
            for attr in cls.get('attributes', []):
                visibility = attr.get('visibility', '+')
                mermaid.append(f"        {visibility}{attr['name']} : {attr['type']}")
            
            # Add methods
            for method in cls.get('methods', []):
                visibility = method.get('visibility', '+')
                params = ', '.join(method.get('params', []))
                return_type = method.get('return', 'void')
                mermaid.append(f"        {visibility}{method['name']}({params}) : {return_type}")
            
            mermaid.append("    }")
        
        # Add relationships
        for cls in classes:
            for rel in cls.get('relationships', []):
                rel_type = rel['type']
                target = rel['target']
                
                if rel_type == 'inherits':
                    mermaid.append(f"    {cls['name']} --|> {target}")
                elif rel_type == 'implements':
                    mermaid.append(f"    {cls['name']} ..|> {target}")
                elif rel_type == 'uses':
                    mermaid.append(f"    {cls['name']} --> {target}")
                elif rel_type == 'composition':
                    mermaid.append(f"    {cls['name']} *-- {target}")
                elif rel_type == 'aggregation':
                    mermaid.append(f"    {cls['name']} o-- {target}")
        
        mermaid.append("```")
        return '\n'.join(mermaid)
    
    def generate_gantt_chart(self, project_tasks: List[Dict[str, Any]]) -> str:
        """Generate Gantt chart for project timeline"""
        mermaid = ["```mermaid", "gantt", "    title Project Timeline", "    dateFormat YYYY-MM-DD"]
        
        # Group tasks by section
        sections = {}
        for task in project_tasks:
            section = task.get('section', 'Tasks')
            if section not in sections:
                sections[section] = []
            sections[section].append(task)
        
        # Add tasks by section
        for section, tasks in sections.items():
            mermaid.append(f"    section {section}")
            for task in tasks:
                name = task['name']
                if task.get('status') == 'completed':
                    status = "done"
                elif task.get('status') == 'in_progress':
                    status = "active"
                else:
                    status = ""
                
                if 'start_date' in task and 'end_date' in task:
                    mermaid.append(f"    {name} :{status} {task['start_date']}, {task['end_date']}")
                elif 'duration' in task:
                    mermaid.append(f"    {name} :{status} {task['duration']}")
        
        mermaid.append("```")
        return '\n'.join(mermaid)
    
    def generate_state_diagram(self, states: Dict[str, Any]) -> str:
        """Generate state diagram"""
        mermaid = ["```mermaid", "stateDiagram-v2"]
        
        # Add states
        for state_id, state_info in states.get('states', {}).items():
            if state_info.get('type') == 'composite':
                mermaid.append(f"    state {state_id} {{")
                for sub_state in state_info.get('substates', []):
                    mermaid.append(f"        {sub_state}")
                mermaid.append("    }")
            else:
                mermaid.append(f"    {state_id}")
        
        # Add transitions
        for transition in states.get('transitions', []):
            from_state = transition['from']
            to_state = transition['to']
            condition = transition.get('condition', '')
            
            if from_state == '[*]':
                from_state = '[*]'
            if to_state == '[*]':
                to_state = '[*]'
                
            if condition:
                mermaid.append(f"    {from_state} --> {to_state} : {condition}")
            else:
                mermaid.append(f"    {from_state} --> {to_state}")
        
        mermaid.append("```")
        return '\n'.join(mermaid)
    
    def generate_mindmap(self, root: str, branches: Dict[str, Any]) -> str:
        """Generate mindmap diagram"""
        mermaid = ["```mermaid", "mindmap", f"  root(({root}))"]
        
        def add_branches(parent_indent: str, items: Dict[str, Any]):
            for key, value in items.items():
                current_indent = parent_indent + "  "
                if isinstance(value, dict):
                    mermaid.append(f"{current_indent}{key}")
                    add_branches(current_indent, value)
                elif isinstance(value, list):
                    mermaid.append(f"{current_indent}{key}")
                    for item in value:
                        mermaid.append(f"{current_indent}  {item}")
                else:
                    mermaid.append(f"{current_indent}{key}: {value}")
        
        add_branches("  ", branches)
        mermaid.append("```")
        return '\n'.join(mermaid)
    
    def generate_dependency_graph(self, dependencies: Dict[str, List[str]]) -> str:
        """Generate dependency graph"""
        mermaid = ["```mermaid", "graph LR"]
        
        # Track all nodes
        all_nodes = set()
        for node, deps in dependencies.items():
            all_nodes.add(node)
            all_nodes.update(deps)
        
        # Add nodes with styling
        for node in sorted(all_nodes):
            if node in dependencies and dependencies[node]:
                # Has dependencies
                mermaid.append(f"    {node}[{node}]:::dependent")
            elif any(node in deps for deps in dependencies.values()):
                # Is a dependency
                mermaid.append(f"    {node}[{node}]:::provider")
            else:
                # Standalone
                mermaid.append(f"    {node}[{node}]")
        
        # Add edges
        for node, deps in dependencies.items():
            for dep in deps:
                mermaid.append(f"    {dep} --> {node}")
        
        # Add styling
        mermaid.extend([
            "    classDef dependent fill:#FFE4B5,stroke:#FF8C00",
            "    classDef provider fill:#E6F3FF,stroke:#4169E1",
            "```"
        ])
        
        return '\n'.join(mermaid)
    
    def generate_dashboard_ascii(self, metrics: Dict[str, Any]) -> str:
        """Generate ASCII dashboard for terminal display"""
        width = 60
        dashboard = []
        
        # Header
        dashboard.append("=" * width)
        dashboard.append("PROJECT DASHBOARD".center(width))
        dashboard.append("=" * width)
        
        # Progress bars
        if 'progress' in metrics:
            dashboard.append("\nPROGRESS:")
            for task, progress in metrics['progress'].items():
                bar_width = 30
                filled = int(bar_width * progress / 100)
                bar = "█" * filled + "░" * (bar_width - filled)
                dashboard.append(f"{task:20} [{bar}] {progress:3}%")
        
        # Stats
        if 'stats' in metrics:
            dashboard.append("\nSTATISTICS:")
            for stat, value in metrics['stats'].items():
                dashboard.append(f"{stat:20} : {value}")
        
        # Recent activity
        if 'recent' in metrics:
            dashboard.append("\nRECENT ACTIVITY:")
            for activity in metrics['recent'][:5]:
                dashboard.append(f"• {activity}")
        
        dashboard.append("=" * width)
        return '\n'.join(dashboard)

def create_visual_examples():
    """Create example visualizations"""
    vc = VisualCommunicator()
    
    # Task flowchart example
    tasks = [
        {"id": "setup", "name": "Setup Environment", "status": "completed", "dependencies": []},
        {"id": "api", "name": "Implement API", "status": "completed", "dependencies": ["setup"]},
        {"id": "db", "name": "Setup Database", "status": "completed", "dependencies": ["setup"]},
        {"id": "tests", "name": "Write Tests", "status": "in_progress", "dependencies": ["api", "db"]},
        {"id": "docs", "name": "Documentation", "status": "pending", "dependencies": ["api"]}
    ]
    
    print("Task Flowchart:")
    print(vc.generate_task_flowchart(tasks))
    
    # Architecture example
    architecture = {
        "layers": {
            "Frontend": [
                {"name": "React App"},
                {"name": "Redux Store"}
            ],
            "Backend": [
                {"name": "FastAPI"},
                {"name": "Business Logic"}
            ],
            "Data": [
                {"name": "PostgreSQL"},
                {"name": "Redis Cache"}
            ]
        },
        "connections": [
            {"from": "React App", "to": "Redux Store"},
            {"from": "Redux Store", "to": "FastAPI", "label": "API calls"},
            {"from": "FastAPI", "to": "Business Logic"},
            {"from": "Business Logic", "to": "PostgreSQL"},
            {"from": "Business Logic", "to": "Redis Cache"}
        ],
        "external": ["External API", "S3 Storage"]
    }
    
    print("\n\nArchitecture Diagram:")
    print(vc.generate_architecture_diagram(architecture))
    
    # Dashboard example
    metrics = {
        "progress": {
            "Development": 85,
            "Testing": 60,
            "Documentation": 40,
            "Deployment": 20
        },
        "stats": {
            "Total Tasks": 45,
            "Completed": 28,
            "In Progress": 12,
            "Pending": 5,
            "Test Coverage": "87%",
            "Code Quality": "A"
        },
        "recent": [
            "Fixed API authentication bug",
            "Added unit tests for database layer",
            "Optimized query performance",
            "Updated deployment scripts",
            "Refactored error handling"
        ]
    }
    
    print("\n\nDashboard:")
    print(vc.generate_dashboard_ascii(metrics))

if __name__ == "__main__":
    create_visual_examples()