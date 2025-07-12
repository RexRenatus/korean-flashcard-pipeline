"""
TimeKeeper Component

Tracks time, manages work sessions, and suggests optimal work patterns.
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional, Any
from pathlib import Path
from collections import defaultdict
import statistics

logger = logging.getLogger(__name__)


class TimeKeeper:
    """
    Time tracking and productivity management system.
    
    Features:
    - Session tracking
    - Pomodoro timer
    - Break reminders
    - Productivity analytics
    - Task timing suggestions
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        
        # Session tracking
        self.session_start = datetime.now()
        self.last_break = datetime.now()
        self.current_pomodoro = None
        
        # Task tracking
        self.task_times = []
        self.break_times = []
        self.completed_pomodoros = 0
        
        # Productivity data
        self.productivity_data = defaultdict(list)
        self.task_history = []
        
        # Configuration
        self.pomodoro_config = {
            "work_duration": self.config.get("pomodoro_duration", 25),
            "short_break": self.config.get("short_break", 5),
            "long_break": self.config.get("long_break", 15),
            "sessions_before_long_break": self.config.get("sessions_before_long_break", 4)
        }
        
        # Time management settings
        self.break_threshold = timedelta(minutes=90)  # Suggest break after 90 minutes
        self.session_warning_threshold = timedelta(hours=4)  # Warn after 4 hours
        self.optimal_hours = self.config.get("optimal_hours", [10, 11, 14, 15])
        
        # Load historical data if available
        self._load_historical_data()
        
        logger.info("TimeKeeper initialized")
    
    def initialize(self):
        """Initialize timekeeper system."""
        logger.info(f"TimeKeeper session started at {self.session_start}")
        
        # Load productivity patterns if available
        if self.productivity_data:
            self._analyze_productivity_patterns()
    
    def check_work_session(self) -> Dict[str, Any]:
        """Check current work session and provide recommendations."""
        current_time = datetime.now()
        session_duration = current_time - self.session_start
        time_since_break = current_time - self.last_break
        
        recommendations = {
            "session_duration": str(session_duration),
            "time_since_break": str(time_since_break),
            "break_needed": False,
            "session_warning": False,
            "productivity_score": self.calculate_productivity_score(),
            "suggestions": []
        }
        
        # Check if break is needed
        if time_since_break > self.break_threshold:
            recommendations["break_needed"] = True
            recommendations["suggestions"].append({
                "type": "break_reminder",
                "message": f"You've been working for {int(time_since_break.total_seconds() / 60)} minutes. Time for a break!",
                "recommended_duration": self._get_recommended_break_duration()
            })
        
        # Check for long session
        if session_duration > self.session_warning_threshold:
            recommendations["session_warning"] = True
            recommendations["suggestions"].append({
                "type": "session_warning",
                "message": f"You've been working for {int(session_duration.total_seconds() / 3600)} hours. Consider ending the session soon.",
                "recommendation": "Save your work and plan for the next session"
            })
        
        # Check productivity patterns
        if recommendations["productivity_score"] < 0.7:
            recommendations["suggestions"].append({
                "type": "productivity_tip",
                "message": "Your productivity seems lower than usual",
                "recommendation": self._get_productivity_improvement_suggestion()
            })
        
        return recommendations
    
    def suggest_task_timing(self, task_info: Dict[str, Any]) -> Dict[str, Any]:
        """Suggest optimal timing for task execution."""
        task_complexity = self._estimate_task_complexity(task_info)
        current_hour = datetime.now().hour
        
        timing_suggestion = {
            "task_complexity": task_complexity,
            "current_time": datetime.now().strftime("%I:%M %p"),
            "is_optimal_time": current_hour in self.optimal_hours,
            "recommendation": "PROCEED",
            "suggestions": []
        }
        
        # Check if it's optimal time for complex tasks
        if task_complexity > 7:
            if not timing_suggestion["is_optimal_time"]:
                timing_suggestion["recommendation"] = "CONSIDER_POSTPONING"
                timing_suggestion["suggestions"].append({
                    "type": "timing",
                    "message": f"This appears to be a complex task (complexity: {task_complexity}/10)",
                    "recommendation": f"Your peak productivity hours are typically {self._format_optimal_hours()}",
                    "alternatives": [
                        "Schedule for peak hours",
                        "Break into smaller subtasks",
                        "Take a short break first to improve focus"
                    ]
                })
        
        # Check current productivity level
        current_productivity = self._get_current_productivity_level()
        if current_productivity < 0.6 and task_complexity > 5:
            timing_suggestion["suggestions"].append({
                "type": "productivity",
                "message": "Your current productivity level is below average",
                "recommendation": "Consider a 5-minute break or switching to a simpler task first"
            })
        
        # Suggest time allocation
        estimated_duration = self._estimate_task_duration(task_info, task_complexity)
        timing_suggestion["estimated_duration"] = estimated_duration
        timing_suggestion["suggested_approach"] = self._suggest_work_approach(estimated_duration)
        
        return timing_suggestion
    
    def track_task_time(self, task_id: str, phase: str = "start", task_info: Optional[Dict[str, Any]] = None):
        """Track time for individual tasks."""
        current_time = datetime.now()
        
        if phase == "start":
            self.task_times.append({
                "id": task_id,
                "start": current_time,
                "info": task_info or {},
                "productivity_level": self._get_current_productivity_level()
            })
            logger.info(f"Started tracking task {task_id}")
            
        elif phase == "end":
            for task in self.task_times:
                if task["id"] == task_id and "end" not in task:
                    task["end"] = current_time
                    task["duration"] = (task["end"] - task["start"]).total_seconds()
                    
                    # Analyze task performance
                    self._analyze_task_performance(task)
                    
                    # Update productivity data
                    hour = task["start"].hour
                    self.productivity_data[hour].append({
                        "duration": task["duration"],
                        "complexity": task.get("complexity", 5),
                        "completed": True
                    })
                    
                    logger.info(f"Completed task {task_id} in {task['duration']:.1f} seconds")
                    break
    
    def record_task_completion(self, task_result: Dict[str, Any]):
        """Record task completion and analyze patterns."""
        task_id = task_result.get("id", "unknown")
        
        # Find the task in our tracking
        task_data = None
        for task in self.task_times:
            if task["id"] == task_id:
                task_data = task
                break
        
        if task_data and "duration" in task_data:
            # Store in history
            self.task_history.append({
                "timestamp": datetime.now().isoformat(),
                "task_id": task_id,
                "duration": task_data["duration"],
                "type": task_result.get("type", "unknown"),
                "success": task_result.get("success", True),
                "productivity_level": task_data.get("productivity_level", 0.5)
            })
            
            # Save to persistent storage periodically
            if len(self.task_history) % 10 == 0:
                self._save_historical_data()
    
    def should_take_break(self, session_duration: Optional[float] = None) -> bool:
        """Determine if a break is needed."""
        if session_duration is None:
            time_since_break = datetime.now() - self.last_break
            session_duration = time_since_break.total_seconds() / 60
        
        # Pomodoro break check
        if self.current_pomodoro and self.current_pomodoro["phase"] == "work":
            elapsed = (datetime.now() - self.current_pomodoro["start"]).total_seconds() / 60
            if elapsed >= self.pomodoro_config["work_duration"]:
                return True
        
        # Regular break check
        return session_duration >= 90  # 90 minutes
    
    def start_pomodoro(self, task_info: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Start a new Pomodoro session."""
        self.current_pomodoro = {
            "start": datetime.now(),
            "phase": "work",
            "duration": self.pomodoro_config["work_duration"],
            "task_info": task_info,
            "session_number": self.completed_pomodoros + 1
        }
        
        notification = {
            "type": "pomodoro_start",
            "duration": self.pomodoro_config["work_duration"],
            "end_time": datetime.now() + timedelta(minutes=self.pomodoro_config["work_duration"]),
            "session_number": self.current_pomodoro["session_number"]
        }
        
        logger.info(f"Started Pomodoro session #{self.current_pomodoro['session_number']}")
        
        return notification
    
    def end_pomodoro(self) -> Dict[str, Any]:
        """End current Pomodoro session."""
        if not self.current_pomodoro:
            return {"error": "No active Pomodoro session"}
        
        self.completed_pomodoros += 1
        
        # Determine break duration
        if self.completed_pomodoros % self.pomodoro_config["sessions_before_long_break"] == 0:
            break_duration = self.pomodoro_config["long_break"]
            break_type = "long"
        else:
            break_duration = self.pomodoro_config["short_break"]
            break_type = "short"
        
        self.current_pomodoro = {
            "start": datetime.now(),
            "phase": "break",
            "duration": break_duration,
            "type": break_type
        }
        
        self.last_break = datetime.now()
        
        return {
            "type": "pomodoro_complete",
            "sessions_completed": self.completed_pomodoros,
            "break_type": break_type,
            "break_duration": break_duration,
            "next_session_at": datetime.now() + timedelta(minutes=break_duration)
        }
    
    def calculate_productivity_score(self) -> float:
        """Calculate current productivity score (0.0 - 1.0)."""
        if not self.task_times:
            return 0.5  # Neutral score if no data
        
        # Factors for productivity calculation
        factors = []
        
        # Task completion rate
        completed_tasks = sum(1 for task in self.task_times if "end" in task)
        if self.task_times:
            completion_rate = completed_tasks / len(self.task_times)
            factors.append(completion_rate)
        
        # Average task efficiency (actual vs estimated time)
        recent_tasks = self.task_times[-10:]  # Last 10 tasks
        if recent_tasks:
            efficiencies = []
            for task in recent_tasks:
                if "duration" in task and "estimated_duration" in task.get("info", {}):
                    efficiency = task["info"]["estimated_duration"] / task["duration"]
                    efficiencies.append(min(efficiency, 1.5))  # Cap at 150% efficiency
            
            if efficiencies:
                factors.append(statistics.mean(efficiencies))
        
        # Break compliance
        time_since_break = (datetime.now() - self.last_break).total_seconds() / 60
        if time_since_break < 120:  # Within 2 hours
            factors.append(1.0)
        elif time_since_break < 180:  # Within 3 hours
            factors.append(0.7)
        else:
            factors.append(0.4)
        
        # Time of day factor
        current_hour = datetime.now().hour
        if current_hour in self.optimal_hours:
            factors.append(1.0)
        elif abs(current_hour - statistics.mean(self.optimal_hours)) < 2:
            factors.append(0.8)
        else:
            factors.append(0.6)
        
        return statistics.mean(factors) if factors else 0.5
    
    def get_task_metrics(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get metrics for a specific task."""
        for task in self.task_times:
            if task["id"] == task_id and "duration" in task:
                return {
                    "task_id": task_id,
                    "duration": task["duration"],
                    "start_time": task["start"].isoformat(),
                    "end_time": task["end"].isoformat(),
                    "productivity_level": task.get("productivity_level", 0.5),
                    "complexity": task.get("info", {}).get("complexity", 5)
                }
        return None
    
    def generate_time_report(self) -> str:
        """Generate comprehensive time tracking report."""
        session_duration = datetime.now() - self.session_start
        total_work_time = sum(task.get("duration", 0) for task in self.task_times) / 60  # in minutes
        total_break_time = sum(b.get("duration", 0) for b in self.break_times) / 60
        
        # Calculate task statistics
        task_durations = [t["duration"] / 60 for t in self.task_times if "duration" in t]
        avg_task_duration = statistics.mean(task_durations) if task_durations else 0
        
        # Productivity analysis
        productivity_by_hour = defaultdict(list)
        for task in self.task_times:
            if "start" in task and "productivity_level" in task:
                hour = task["start"].hour
                productivity_by_hour[hour].append(task["productivity_level"])
        
        best_hours = []
        for hour, levels in productivity_by_hour.items():
            if levels and statistics.mean(levels) > 0.8:
                best_hours.append(hour)
        
        report = f"""# TIME TRACKING REPORT
Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

## Session Summary
- Session Start: {self.session_start.strftime("%Y-%m-%d %H:%M:%S")}
- Total Duration: {str(session_duration).split('.')[0]}
- Tasks Completed: {len([t for t in self.task_times if "end" in t])}
- Breaks Taken: {len(self.break_times)}
- Pomodoros Completed: {self.completed_pomodoros}

## Productivity Analysis
- Overall Productivity Score: {self.calculate_productivity_score():.2f}/1.00
- Total Work Time: {total_work_time:.1f} minutes
- Total Break Time: {total_break_time:.1f} minutes
- Work/Break Ratio: {total_work_time / max(total_break_time, 1):.1f}:1

## Task Statistics
- Average Task Duration: {avg_task_duration:.1f} minutes
- Longest Task: {max(task_durations) if task_durations else 0:.1f} minutes
- Shortest Task: {min(task_durations) if task_durations else 0:.1f} minutes

## Peak Productivity Hours
{self._format_productivity_hours(best_hours)}

## Recommendations
{self._generate_recommendations()}
"""
        
        return report
    
    def get_status(self) -> Dict[str, Any]:
        """Get current timekeeper status."""
        time_since_break = (datetime.now() - self.last_break).total_seconds() / 60
        
        return {
            "session_duration": str(datetime.now() - self.session_start).split('.')[0],
            "time_since_break": f"{int(time_since_break)} minutes",
            "tasks_tracked": len(self.task_times),
            "productivity_score": round(self.calculate_productivity_score(), 2),
            "pomodoros_completed": self.completed_pomodoros,
            "current_pomodoro": self.current_pomodoro is not None
        }
    
    def shutdown(self):
        """Clean shutdown and save data."""
        # Save historical data
        self._save_historical_data()
        
        # Generate final report
        final_report = self.generate_time_report()
        
        # Save report
        report_path = Path("time_reports") / f"report_{self.session_start.strftime('%Y%m%d_%H%M%S')}.md"
        report_path.parent.mkdir(exist_ok=True)
        
        try:
            with open(report_path, 'w', encoding='utf-8') as f:
                f.write(final_report)
            logger.info(f"Time report saved to {report_path}")
        except Exception as e:
            logger.error(f"Failed to save time report: {e}")
        
        logger.info("TimeKeeper shutdown complete")
    
    # Helper methods
    
    def _estimate_task_complexity(self, task_info: Dict[str, Any]) -> int:
        """Estimate task complexity on a scale of 1-10."""
        complexity = 5  # Default moderate complexity
        
        task_type = task_info.get("type", "").lower()
        
        # Adjust based on task type
        complexity_map = {
            "refactor": 8,
            "debug": 7,
            "feature": 7,
            "test": 5,
            "documentation": 3,
            "config": 4,
            "bugfix": 6,
            "optimization": 8,
            "research": 6
        }
        
        for key, value in complexity_map.items():
            if key in task_type:
                complexity = value
                break
        
        # Adjust based on scope
        if "large" in str(task_info).lower() or "major" in str(task_info).lower():
            complexity = min(complexity + 2, 10)
        elif "small" in str(task_info).lower() or "minor" in str(task_info).lower():
            complexity = max(complexity - 2, 1)
        
        return complexity
    
    def _estimate_task_duration(self, task_info: Dict[str, Any], complexity: int) -> int:
        """Estimate task duration in minutes."""
        # Base duration on complexity
        base_duration = complexity * 5  # 5 minutes per complexity point
        
        # Adjust based on historical data
        similar_tasks = self._find_similar_tasks(task_info)
        if similar_tasks:
            historical_avg = statistics.mean([t["duration"] / 60 for t in similar_tasks])
            # Weighted average: 70% historical, 30% estimated
            return int(historical_avg * 0.7 + base_duration * 0.3)
        
        return base_duration
    
    def _find_similar_tasks(self, task_info: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Find similar tasks from history."""
        task_type = task_info.get("type", "").lower()
        similar = []
        
        for task in self.task_history[-50:]:  # Check last 50 tasks
            if task.get("type", "").lower() == task_type:
                similar.append(task)
        
        return similar
    
    def _get_recommended_break_duration(self) -> int:
        """Get recommended break duration based on work time."""
        time_since_break = (datetime.now() - self.last_break).total_seconds() / 60
        
        if time_since_break > 180:  # 3+ hours
            return 15
        elif time_since_break > 120:  # 2+ hours
            return 10
        else:
            return 5
    
    def _get_productivity_improvement_suggestion(self) -> str:
        """Generate suggestion to improve productivity."""
        current_hour = datetime.now().hour
        time_since_break = (datetime.now() - self.last_break).total_seconds() / 60
        
        if time_since_break > 120:
            return "Take a 10-minute break to refresh your focus"
        elif current_hour not in self.optimal_hours:
            return f"Consider working on lighter tasks until your peak hours ({self._format_optimal_hours()})"
        else:
            return "Try the Pomodoro technique to maintain focus"
    
    def _format_optimal_hours(self) -> str:
        """Format optimal hours for display."""
        hour_ranges = []
        current_range = [self.optimal_hours[0]]
        
        for hour in self.optimal_hours[1:]:
            if hour == current_range[-1] + 1:
                current_range.append(hour)
            else:
                if len(current_range) > 1:
                    hour_ranges.append(f"{current_range[0]}-{current_range[-1]}")
                else:
                    hour_ranges.append(str(current_range[0]))
                current_range = [hour]
        
        if len(current_range) > 1:
            hour_ranges.append(f"{current_range[0]}-{current_range[-1]}")
        else:
            hour_ranges.append(str(current_range[0]))
        
        formatted = [f"{r}:00" for r in hour_ranges]
        return ", ".join(formatted)
    
    def _suggest_work_approach(self, duration_minutes: int) -> str:
        """Suggest work approach based on estimated duration."""
        if duration_minutes <= 25:
            return "Single Pomodoro session"
        elif duration_minutes <= 60:
            return "2-3 Pomodoro sessions with short breaks"
        elif duration_minutes <= 120:
            return "Break into subtasks, use 4-5 Pomodoro sessions"
        else:
            return "Major task - break into multiple work sessions"
    
    def _get_current_productivity_level(self) -> float:
        """Get current productivity level based on recent performance."""
        recent_tasks = self.task_times[-5:]  # Last 5 tasks
        if not recent_tasks:
            return 0.7  # Default
        
        levels = [t.get("productivity_level", 0.5) for t in recent_tasks]
        return statistics.mean(levels)
    
    def _analyze_task_performance(self, task: Dict[str, Any]):
        """Analyze individual task performance."""
        if "duration" not in task:
            return
        
        # Compare with estimated duration
        if "estimated_duration" in task.get("info", {}):
            estimated = task["info"]["estimated_duration"] * 60  # Convert to seconds
            actual = task["duration"]
            accuracy = abs(estimated - actual) / estimated
            
            task["estimation_accuracy"] = 1 - min(accuracy, 1)
        
        # Calculate task velocity (complexity / time)
        complexity = task.get("info", {}).get("complexity", 5)
        task["velocity"] = complexity / (task["duration"] / 60)  # Complexity points per minute
    
    def _analyze_productivity_patterns(self):
        """Analyze historical productivity patterns."""
        # Group by hour and calculate average productivity
        hourly_productivity = defaultdict(list)
        
        for task in self.task_history:
            if "timestamp" in task and "productivity_level" in task:
                hour = datetime.fromisoformat(task["timestamp"]).hour
                hourly_productivity[hour].append(task["productivity_level"])
        
        # Find optimal hours
        optimal_hours = []
        for hour, levels in hourly_productivity.items():
            if levels and statistics.mean(levels) > 0.75:
                optimal_hours.append(hour)
        
        if optimal_hours:
            self.optimal_hours = sorted(optimal_hours)
    
    def _format_productivity_hours(self, hours: List[int]) -> str:
        """Format productivity hours for report."""
        if not hours:
            return "- No clear peak hours identified yet"
        
        lines = []
        for hour in sorted(hours):
            productivity = statistics.mean(self.productivity_data.get(hour, [0.5]))
            lines.append(f"- {hour}:00-{hour+1}:00 (Productivity: {productivity:.2f})")
        
        return "\n".join(lines)
    
    def _generate_recommendations(self) -> List[str]:
        """Generate personalized recommendations."""
        recommendations = []
        
        # Break compliance
        avg_time_between_breaks = statistics.mean([
            (self.break_times[i+1]["start"] - self.break_times[i]["end"]).total_seconds() / 60
            for i in range(len(self.break_times) - 1)
        ]) if len(self.break_times) > 1 else 180
        
        if avg_time_between_breaks > 150:
            recommendations.append("- Take breaks more frequently (every 90-120 minutes)")
        
        # Task duration
        task_durations = [t["duration"] / 60 for t in self.task_times if "duration" in t]
        if task_durations:
            avg_duration = statistics.mean(task_durations)
            if avg_duration > 60:
                recommendations.append("- Break large tasks into smaller, manageable chunks")
        
        # Productivity patterns
        if self.calculate_productivity_score() < 0.6:
            recommendations.append("- Consider adjusting your work schedule to align with peak hours")
        
        # Pomodoro usage
        if self.completed_pomodoros < 2 and len(self.task_times) > 5:
            recommendations.append("- Try using the Pomodoro technique more consistently")
        
        return recommendations if recommendations else ["- Great job maintaining productivity!"]
    
    def _load_historical_data(self):
        """Load historical productivity data."""
        data_path = Path(".timekeeper") / "history.json"
        
        if data_path.exists():
            try:
                with open(data_path, 'r') as f:
                    data = json.load(f)
                    self.task_history = data.get("task_history", [])
                    self.productivity_data = defaultdict(list, data.get("productivity_data", {}))
                logger.info("Loaded historical timekeeper data")
            except Exception as e:
                logger.warning(f"Failed to load historical data: {e}")
    
    def _save_historical_data(self):
        """Save historical data for future sessions."""
        data_path = Path(".timekeeper") / "history.json"
        data_path.parent.mkdir(exist_ok=True)
        
        try:
            data = {
                "task_history": self.task_history[-1000:],  # Keep last 1000 tasks
                "productivity_data": dict(self.productivity_data),
                "last_updated": datetime.now().isoformat()
            }
            
            with open(data_path, 'w') as f:
                json.dump(data, f, indent=2)
            
            logger.debug("Saved historical timekeeper data")
        except Exception as e:
            logger.error(f"Failed to save historical data: {e}")