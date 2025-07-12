"""
Analytics service for flashcard pipeline monitoring.

This module provides:
- Performance trend analysis
- Cost analysis and projections
- Usage patterns detection
- Anomaly detection
- Report generation
- Data aggregation
"""

import asyncio
import json
import logging
import statistics
from collections import defaultdict
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from decimal import Decimal
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple, Union
import aiosqlite
import numpy as np
from scipy import stats

from .metrics_collector import MetricsCollector, MetricCategory, MetricType

logger = logging.getLogger(__name__)


class TrendDirection(Enum):
    """Direction of metric trends."""
    INCREASING = "increasing"
    DECREASING = "decreasing"
    STABLE = "stable"
    VOLATILE = "volatile"


class AnomalyType(Enum):
    """Types of anomalies detected."""
    SPIKE = "spike"
    DROP = "drop"
    PATTERN_CHANGE = "pattern_change"
    OUTLIER = "outlier"


@dataclass
class TrendAnalysis:
    """Results of trend analysis."""
    metric_name: str
    period: str
    direction: TrendDirection
    change_percent: float
    slope: float
    r_squared: float
    forecast_next_period: Optional[float] = None
    confidence_interval: Optional[Tuple[float, float]] = None


@dataclass
class CostAnalysis:
    """Results of cost analysis."""
    period: str
    total_cost: Decimal
    average_daily_cost: Decimal
    cost_by_model: Dict[str, Decimal]
    cost_trend: TrendDirection
    projected_monthly_cost: Decimal
    budget_utilization: Optional[float] = None
    days_until_budget_exceeded: Optional[int] = None


@dataclass
class UsagePattern:
    """Detected usage pattern."""
    pattern_type: str
    description: str
    peak_hours: List[int]
    peak_days: List[int]
    average_load: Dict[str, float]
    recommendations: List[str]


@dataclass
class Anomaly:
    """Detected anomaly."""
    timestamp: datetime
    metric_name: str
    anomaly_type: AnomalyType
    severity: float  # 0-1 scale
    actual_value: float
    expected_value: float
    std_deviations: float
    context: Dict[str, Any]


class AnalyticsService:
    """Main analytics service for processing metrics data."""
    
    def __init__(self, metrics_collector: MetricsCollector):
        self.metrics = metrics_collector
        self.db_path = metrics_collector.db_path
        self._anomaly_detectors: Dict[str, 'AnomalyDetector'] = {}
        
    # Trend Analysis
    
    async def analyze_trend(self, metric_name: str, period_days: int = 7,
                          forecast_days: int = 0) -> TrendAnalysis:
        """Analyze trend for a metric over a period."""
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(days=period_days)
        
        # Get aggregated daily data
        daily_data = await self.metrics.get_aggregated_metrics(
            metric_name, start_time, end_time, 
            interval_minutes=1440,  # Daily
            aggregation="avg"
        )
        
        if len(daily_data) < 3:
            return TrendAnalysis(
                metric_name=metric_name,
                period=f"{period_days} days",
                direction=TrendDirection.STABLE,
                change_percent=0.0,
                slope=0.0,
                r_squared=0.0
            )
            
        # Extract values and timestamps
        timestamps = [d["timestamp"] for d in daily_data]
        values = [d["value"] for d in daily_data]
        
        # Convert timestamps to numeric days
        start_timestamp = timestamps[0]
        days = [(t - start_timestamp).total_seconds() / 86400 for t in timestamps]
        
        # Calculate linear regression
        slope, intercept, r_value, p_value, std_err = stats.linregress(days, values)
        r_squared = r_value ** 2
        
        # Calculate percent change
        if values[0] != 0:
            change_percent = ((values[-1] - values[0]) / values[0]) * 100
        else:
            change_percent = 0.0
            
        # Determine trend direction
        if abs(slope) < 0.01 * np.mean(values):  # Less than 1% of mean
            direction = TrendDirection.STABLE
        elif slope > 0:
            direction = TrendDirection.INCREASING
        else:
            direction = TrendDirection.DECREASING
            
        # Check for volatility
        cv = np.std(values) / np.mean(values) if np.mean(values) != 0 else 0
        if cv > 0.5:  # Coefficient of variation > 50%
            direction = TrendDirection.VOLATILE
            
        # Forecast if requested
        forecast_value = None
        confidence_interval = None
        if forecast_days > 0:
            forecast_day = days[-1] + forecast_days
            forecast_value = slope * forecast_day + intercept
            
            # Calculate confidence interval
            residuals = [values[i] - (slope * days[i] + intercept) for i in range(len(values))]
            residual_std = np.std(residuals)
            confidence_interval = (
                forecast_value - 1.96 * residual_std,
                forecast_value + 1.96 * residual_std
            )
            
        return TrendAnalysis(
            metric_name=metric_name,
            period=f"{period_days} days",
            direction=direction,
            change_percent=change_percent,
            slope=slope,
            r_squared=r_squared,
            forecast_next_period=forecast_value,
            confidence_interval=confidence_interval
        )
        
    async def analyze_multiple_trends(self, metric_names: List[str],
                                    period_days: int = 7) -> Dict[str, TrendAnalysis]:
        """Analyze trends for multiple metrics."""
        tasks = [
            self.analyze_trend(metric_name, period_days)
            for metric_name in metric_names
        ]
        results = await asyncio.gather(*tasks)
        return {r.metric_name: r for r in results}
        
    # Cost Analysis
    
    async def analyze_costs(self, period_days: int = 30) -> CostAnalysis:
        """Analyze costs over a period."""
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(days=period_days)
        
        # Get total cost
        total_cost = await self.metrics.get_cost_sum(start_time, end_time)
        
        # Get cost by model
        cost_by_model = await self._get_cost_by_model(start_time, end_time)
        
        # Calculate average daily cost
        avg_daily_cost = Decimal(str(total_cost)) / period_days
        
        # Analyze cost trend
        cost_trend_analysis = await self.analyze_trend("api.cost.total", period_days)
        
        # Project monthly cost based on trend
        if cost_trend_analysis.slope > 0:
            # Increasing costs - use trend projection
            days_in_month = 30
            projected_monthly = avg_daily_cost * days_in_month * Decimal(str(1 + cost_trend_analysis.change_percent / 100))
        else:
            # Stable or decreasing - use current average
            projected_monthly = avg_daily_cost * 30
            
        # Check budget utilization
        budget_utilization = None
        days_until_exceeded = None
        
        if self.metrics._cost_budget:
            monthly_limit = self.metrics._cost_budget.monthly_limit
            budget_utilization = float(projected_monthly / monthly_limit)
            
            if budget_utilization > 1.0:
                # Calculate when budget will be exceeded
                remaining_budget = monthly_limit - Decimal(str(total_cost))
                if avg_daily_cost > 0:
                    days_until_exceeded = int(remaining_budget / avg_daily_cost)
                    
        return CostAnalysis(
            period=f"{period_days} days",
            total_cost=Decimal(str(total_cost)),
            average_daily_cost=avg_daily_cost,
            cost_by_model=cost_by_model,
            cost_trend=cost_trend_analysis.direction,
            projected_monthly_cost=projected_monthly,
            budget_utilization=budget_utilization,
            days_until_budget_exceeded=days_until_exceeded
        )
        
    async def _get_cost_by_model(self, start_time: datetime, 
                               end_time: datetime) -> Dict[str, Decimal]:
        """Get cost breakdown by model."""
        async with aiosqlite.connect(str(self.db_path)) as db:
            query = """
                SELECT 
                    json_extract(tags, '$.model') as model,
                    SUM(value) as total_cost
                FROM metrics
                WHERE name = 'api.cost.total'
                AND timestamp >= ? AND timestamp <= ?
                GROUP BY model
            """
            
            cost_by_model = {}
            async with db.execute(query, (start_time.isoformat(), end_time.isoformat())) as cursor:
                async for row in cursor:
                    if row[0]:  # model name exists
                        cost_by_model[row[0]] = Decimal(str(row[1]))
                        
            return cost_by_model
            
    # Usage Pattern Detection
    
    async def detect_usage_patterns(self, period_days: int = 14) -> UsagePattern:
        """Detect usage patterns over a period."""
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(days=period_days)
        
        # Get hourly API call data
        hourly_data = await self.metrics.get_aggregated_metrics(
            "api.calls.total", start_time, end_time,
            interval_minutes=60,
            aggregation="count"
        )
        
        # Analyze by hour of day
        hourly_usage = defaultdict(list)
        daily_usage = defaultdict(list)
        
        for data_point in hourly_data:
            hour = data_point["timestamp"].hour
            day = data_point["timestamp"].weekday()
            hourly_usage[hour].append(data_point["count"])
            daily_usage[day].append(data_point["count"])
            
        # Find peak hours
        avg_by_hour = {
            hour: np.mean(counts) for hour, counts in hourly_usage.items()
        }
        sorted_hours = sorted(avg_by_hour.items(), key=lambda x: x[1], reverse=True)
        peak_hours = [hour for hour, _ in sorted_hours[:3]]
        
        # Find peak days
        avg_by_day = {
            day: np.mean(counts) for day, counts in daily_usage.items()
        }
        sorted_days = sorted(avg_by_day.items(), key=lambda x: x[1], reverse=True)
        peak_days = [day for day, _ in sorted_days[:2]]
        
        # Calculate average load
        total_calls = sum(d["count"] for d in hourly_data)
        hours_analyzed = len(hourly_data)
        
        average_load = {
            "calls_per_hour": total_calls / hours_analyzed if hours_analyzed > 0 else 0,
            "calls_per_day": total_calls / period_days,
            "peak_hour_load": max(avg_by_hour.values()) if avg_by_hour else 0,
            "valley_hour_load": min(avg_by_hour.values()) if avg_by_hour else 0
        }
        
        # Generate recommendations
        recommendations = []
        
        # Check for uneven distribution
        if average_load["peak_hour_load"] > 3 * average_load["calls_per_hour"]:
            recommendations.append(
                "Consider implementing request queuing during peak hours to smooth load"
            )
            
        # Check for underutilization
        if average_load["valley_hour_load"] < 0.1 * average_load["calls_per_hour"]:
            recommendations.append(
                "Schedule batch processing during off-peak hours to maximize efficiency"
            )
            
        # Determine pattern type
        if len(set(avg_by_hour.values())) == 1:
            pattern_type = "uniform"
            description = "Usage is evenly distributed throughout the day"
        elif max(peak_hours) - min(peak_hours) <= 3:
            pattern_type = "concentrated"
            description = f"Usage is concentrated around hours {min(peak_hours)}-{max(peak_hours)}"
        else:
            pattern_type = "distributed"
            description = "Usage has multiple peaks throughout the day"
            
        return UsagePattern(
            pattern_type=pattern_type,
            description=description,
            peak_hours=peak_hours,
            peak_days=peak_days,
            average_load=average_load,
            recommendations=recommendations
        )
        
    # Anomaly Detection
    
    async def detect_anomalies(self, metric_name: str, period_days: int = 7,
                             sensitivity: float = 2.0) -> List[Anomaly]:
        """Detect anomalies in metric data."""
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(days=period_days)
        
        # Get hourly data
        hourly_data = await self.metrics.get_aggregated_metrics(
            metric_name, start_time, end_time,
            interval_minutes=60,
            aggregation="avg"
        )
        
        if len(hourly_data) < 24:  # Need at least 24 hours of data
            return []
            
        # Extract values
        timestamps = [d["timestamp"] for d in hourly_data]
        values = [d["value"] for d in hourly_data]
        
        # Initialize or get anomaly detector
        if metric_name not in self._anomaly_detectors:
            self._anomaly_detectors[metric_name] = AnomalyDetector(sensitivity)
            
        detector = self._anomaly_detectors[metric_name]
        
        # Detect anomalies
        anomalies = []
        for i, (timestamp, value) in enumerate(zip(timestamps, values)):
            if i < 24:  # Need history for detection
                detector.update(value)
                continue
                
            # Get recent history
            recent_values = values[max(0, i-24):i]
            
            # Check for anomaly
            is_anomaly, anomaly_type, severity, expected = detector.detect(value, recent_values)
            
            if is_anomaly:
                # Calculate standard deviations
                mean = np.mean(recent_values)
                std = np.std(recent_values)
                std_deviations = abs(value - mean) / std if std > 0 else 0
                
                # Gather context
                context = {
                    "hour_of_day": timestamp.hour,
                    "day_of_week": timestamp.weekday(),
                    "recent_mean": mean,
                    "recent_std": std,
                    "recent_min": min(recent_values),
                    "recent_max": max(recent_values)
                }
                
                anomaly = Anomaly(
                    timestamp=timestamp,
                    metric_name=metric_name,
                    anomaly_type=anomaly_type,
                    severity=severity,
                    actual_value=value,
                    expected_value=expected,
                    std_deviations=std_deviations,
                    context=context
                )
                anomalies.append(anomaly)
                
            detector.update(value)
            
        return anomalies
        
    # Performance Analysis
    
    async def analyze_performance(self, period_days: int = 7) -> Dict[str, Any]:
        """Comprehensive performance analysis."""
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(days=period_days)
        
        # API performance
        api_latency = await self._analyze_latency("api.call.duration", start_time, end_time)
        
        # Processing performance
        processing_latency = await self._analyze_latency("processing.duration", start_time, end_time)
        
        # Success rates
        api_success_rate = await self._calculate_success_rate("api.calls.total", start_time, end_time)
        processing_success_rate = await self._calculate_success_rate("processing.batches.total", start_time, end_time)
        
        # Cache performance
        cache_hit_rate = await self._calculate_cache_hit_rate(start_time, end_time)
        
        # Database performance
        db_latency = await self._analyze_latency("database.operation.duration", start_time, end_time)
        
        # Throughput
        processing_throughput = await self._calculate_throughput(start_time, end_time)
        
        return {
            "period": f"{period_days} days",
            "api_performance": {
                "avg_latency_ms": api_latency["avg"],
                "p95_latency_ms": api_latency["p95"],
                "p99_latency_ms": api_latency["p99"],
                "success_rate": api_success_rate
            },
            "processing_performance": {
                "avg_latency_ms": processing_latency["avg"],
                "p95_latency_ms": processing_latency["p95"],
                "p99_latency_ms": processing_latency["p99"],
                "success_rate": processing_success_rate,
                "throughput_words_per_sec": processing_throughput
            },
            "cache_performance": {
                "hit_rate": cache_hit_rate
            },
            "database_performance": {
                "avg_latency_ms": db_latency["avg"],
                "p95_latency_ms": db_latency["p95"],
                "p99_latency_ms": db_latency["p99"]
            }
        }
        
    async def _analyze_latency(self, metric_name: str, start_time: datetime,
                             end_time: datetime) -> Dict[str, float]:
        """Analyze latency metrics."""
        metrics = await self.metrics.get_metrics(metric_name, start_time, end_time)
        
        if not metrics:
            return {"avg": 0.0, "p50": 0.0, "p95": 0.0, "p99": 0.0}
            
        values = [m.value for m in metrics]
        
        return {
            "avg": np.mean(values),
            "p50": np.percentile(values, 50),
            "p95": np.percentile(values, 95),
            "p99": np.percentile(values, 99)
        }
        
    async def _calculate_success_rate(self, metric_name: str, start_time: datetime,
                                    end_time: datetime) -> float:
        """Calculate success rate for a metric."""
        # Get total and success counts
        total_metrics = await self.metrics.get_metrics(metric_name, start_time, end_time)
        success_metrics = await self.metrics.get_metrics(
            metric_name, start_time, end_time, 
            tags={"success": "True"}
        )
        
        total_count = sum(m.value for m in total_metrics)
        success_count = sum(m.value for m in success_metrics)
        
        return success_count / total_count if total_count > 0 else 0.0
        
    async def _calculate_cache_hit_rate(self, start_time: datetime,
                                      end_time: datetime) -> float:
        """Calculate cache hit rate."""
        hits = await self.metrics.get_metrics("cache.hits.total", start_time, end_time)
        misses = await self.metrics.get_metrics("cache.misses.total", start_time, end_time)
        
        total_hits = sum(m.value for m in hits)
        total_misses = sum(m.value for m in misses)
        total_operations = total_hits + total_misses
        
        return total_hits / total_operations if total_operations > 0 else 0.0
        
    async def _calculate_throughput(self, start_time: datetime,
                                  end_time: datetime) -> float:
        """Calculate average processing throughput."""
        throughput_metrics = await self.metrics.get_metrics(
            "processing.throughput", start_time, end_time
        )
        
        if not throughput_metrics:
            return 0.0
            
        return np.mean([m.value for m in throughput_metrics])
        
    # Report Generation
    
    async def generate_summary_report(self, period_days: int = 7) -> Dict[str, Any]:
        """Generate comprehensive summary report."""
        # Run all analyses in parallel
        tasks = [
            self.analyze_costs(period_days),
            self.analyze_performance(period_days),
            self.detect_usage_patterns(period_days),
            self.analyze_multiple_trends(
                ["api.calls.total", "api.cost.total", "processing.words.total"],
                period_days
            )
        ]
        
        cost_analysis, performance, usage_pattern, trends = await asyncio.gather(*tasks)
        
        # Detect anomalies for key metrics
        anomaly_tasks = [
            self.detect_anomalies("api.calls.total", period_days),
            self.detect_anomalies("api.cost.total", period_days),
            self.detect_anomalies("api.call.duration", period_days)
        ]
        
        anomalies_by_metric = await asyncio.gather(*anomaly_tasks)
        all_anomalies = [a for anomalies in anomalies_by_metric for a in anomalies]
        
        return {
            "report_generated": datetime.utcnow().isoformat(),
            "period": f"{period_days} days",
            "cost_analysis": asdict(cost_analysis),
            "performance": performance,
            "usage_pattern": asdict(usage_pattern),
            "trends": {name: asdict(trend) for name, trend in trends.items()},
            "anomalies": [asdict(a) for a in all_anomalies],
            "summary": {
                "total_api_calls": sum(m.value for m in await self.metrics.get_metrics(
                    "api.calls.total", 
                    datetime.utcnow() - timedelta(days=period_days),
                    datetime.utcnow()
                )),
                "total_words_processed": sum(m.value for m in await self.metrics.get_metrics(
                    "processing.words.total",
                    datetime.utcnow() - timedelta(days=period_days),
                    datetime.utcnow()
                )),
                "total_cost": float(cost_analysis.total_cost),
                "anomaly_count": len(all_anomalies),
                "high_severity_anomalies": len([a for a in all_anomalies if a.severity > 0.8])
            }
        }


class AnomalyDetector:
    """Simple anomaly detector using statistical methods."""
    
    def __init__(self, sensitivity: float = 2.0):
        self.sensitivity = sensitivity
        self.history: List[float] = []
        self.max_history = 168  # 1 week of hourly data
        
    def update(self, value: float):
        """Update detector with new value."""
        self.history.append(value)
        if len(self.history) > self.max_history:
            self.history.pop(0)
            
    def detect(self, value: float, recent_values: List[float]) -> Tuple[bool, Optional[AnomalyType], float, float]:
        """Detect if value is anomalous."""
        if not recent_values:
            return False, None, 0.0, value
            
        mean = np.mean(recent_values)
        std = np.std(recent_values)
        
        if std == 0:
            return False, None, 0.0, mean
            
        # Z-score test
        z_score = abs(value - mean) / std
        
        if z_score > self.sensitivity:
            # Determine anomaly type
            if value > mean + self.sensitivity * std:
                anomaly_type = AnomalyType.SPIKE
            elif value < mean - self.sensitivity * std:
                anomaly_type = AnomalyType.DROP
            else:
                anomaly_type = AnomalyType.OUTLIER
                
            # Calculate severity (0-1 scale)
            severity = min(1.0, (z_score - self.sensitivity) / (self.sensitivity * 2))
            
            return True, anomaly_type, severity, mean
            
        # Check for pattern change using recent vs historical data
        if len(self.history) > 48:  # Need enough history
            recent_mean = np.mean(recent_values[-24:])
            historical_mean = np.mean(self.history[:-24])
            historical_std = np.std(self.history[:-24])
            
            if historical_std > 0:
                mean_shift = abs(recent_mean - historical_mean) / historical_std
                if mean_shift > self.sensitivity:
                    severity = min(1.0, (mean_shift - self.sensitivity) / (self.sensitivity * 2))
                    return True, AnomalyType.PATTERN_CHANGE, severity, historical_mean
                    
        return False, None, 0.0, mean