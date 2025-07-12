import React, { useEffect } from 'react';
import {
  Box,
  Grid,
  Card,
  CardContent,
  Typography,
  LinearProgress,
  Paper,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  Chip,
} from '@mui/material';
import {
  LibraryBooks as TotalIcon,
  CheckCircle as ProcessedIcon,
  Schedule as PendingIcon,
  Error as FailedIcon,
  TrendingUp as TrendingUpIcon,
  Speed as SpeedIcon,
} from '@mui/icons-material';
import { useSelector, useDispatch } from 'react-redux';
import { RootState, AppDispatch } from '@renderer/store';
import { fetchSystemStats } from '@renderer/store/systemSlice';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';

interface StatCardProps {
  title: string;
  value: number | string;
  icon: React.ReactElement;
  color: string;
  subtitle?: string;
}

const StatCard: React.FC<StatCardProps> = ({ title, value, icon, color, subtitle }) => (
  <Card>
    <CardContent>
      <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
        <Box
          sx={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            width: 48,
            height: 48,
            borderRadius: 2,
            bgcolor: `${color}.light`,
            color: `${color}.dark`,
            mr: 2,
          }}
        >
          {icon}
        </Box>
        <Box sx={{ flexGrow: 1 }}>
          <Typography color="text.secondary" variant="body2">
            {title}
          </Typography>
          <Typography variant="h4">
            {typeof value === 'number' ? value.toLocaleString() : value}
          </Typography>
          {subtitle && (
            <Typography variant="caption" color="text.secondary">
              {subtitle}
            </Typography>
          )}
        </Box>
      </Box>
    </CardContent>
  </Card>
);

export const Dashboard: React.FC = () => {
  const dispatch = useDispatch<AppDispatch>();
  const { stats, loading } = useSelector((state: RootState) => state.system);

  useEffect(() => {
    dispatch(fetchSystemStats());
    // Refresh stats every 30 seconds
    const interval = setInterval(() => {
      dispatch(fetchSystemStats());
    }, 30000);
    return () => clearInterval(interval);
  }, [dispatch]);

  if (loading && !stats) {
    return <LinearProgress />;
  }

  // Mock data for the chart
  const processingTrend = [
    { time: '00:00', words: 120 },
    { time: '04:00', words: 150 },
    { time: '08:00', words: 280 },
    { time: '12:00', words: 320 },
    { time: '16:00', words: 380 },
    { time: '20:00', words: 410 },
    { time: '24:00', words: 450 },
  ];

  // Mock recent activity
  const recentActivity = [
    { word: '안녕하세요', status: 'completed', time: '2 minutes ago' },
    { word: '감사합니다', status: 'completed', time: '5 minutes ago' },
    { word: '미안합니다', status: 'processing', time: '10 minutes ago' },
    { word: '사랑해요', status: 'failed', time: '15 minutes ago' },
    { word: '잘 지내세요', status: 'completed', time: '20 minutes ago' },
  ];

  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        Dashboard
      </Typography>

      {/* Stats Cards */}
      <Grid container spacing={3} sx={{ mb: 4 }}>
        <Grid item xs={12} sm={6} md={3}>
          <StatCard
            title="Total Words"
            value={stats?.totalWords || 0}
            icon={<TotalIcon />}
            color="primary"
          />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <StatCard
            title="Processed"
            value={stats?.processedWords || 0}
            icon={<ProcessedIcon />}
            color="success"
            subtitle={`${stats ? Math.round((stats.processedWords / stats.totalWords) * 100) : 0}% complete`}
          />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <StatCard
            title="Pending"
            value={stats?.pendingWords || 0}
            icon={<PendingIcon />}
            color="warning"
          />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <StatCard
            title="Failed"
            value={stats?.failedWords || 0}
            icon={<FailedIcon />}
            color="error"
          />
        </Grid>
      </Grid>

      <Grid container spacing={3}>
        {/* Processing Trend Chart */}
        <Grid item xs={12} md={8}>
          <Paper sx={{ p: 2, height: 300 }}>
            <Typography variant="h6" gutterBottom>
              Processing Trend (Last 24 Hours)
            </Typography>
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={processingTrend}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="time" />
                <YAxis />
                <Tooltip />
                <Line
                  type="monotone"
                  dataKey="words"
                  stroke="#1976d2"
                  strokeWidth={2}
                />
              </LineChart>
            </ResponsiveContainer>
          </Paper>
        </Grid>

        {/* Performance Metrics */}
        <Grid item xs={12} md={4}>
          <Paper sx={{ p: 2, height: 300 }}>
            <Typography variant="h6" gutterBottom>
              Performance
            </Typography>
            <Box sx={{ mt: 2 }}>
              <Box sx={{ mb: 3 }}>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                  <Typography variant="body2">Cache Hit Rate</Typography>
                  <Typography variant="body2" color="primary">
                    {Math.round((stats?.cacheHitRate || 0) * 100)}%
                  </Typography>
                </Box>
                <LinearProgress
                  variant="determinate"
                  value={(stats?.cacheHitRate || 0) * 100}
                  sx={{ height: 8, borderRadius: 4 }}
                />
              </Box>

              <Box sx={{ mb: 3 }}>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                  <SpeedIcon color="action" />
                  <Typography variant="body2">Average Processing Time</Typography>
                </Box>
                <Typography variant="h6" color="primary">
                  {stats?.averageProcessingTime || 0}s
                </Typography>
              </Box>

              <Box>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                  <TrendingUpIcon color="action" />
                  <Typography variant="body2">Processing Rate</Typography>
                </Box>
                <Typography variant="h6" color="primary">
                  {Math.round((stats?.processedWords || 0) / 24)} words/hour
                </Typography>
              </Box>
            </Box>
          </Paper>
        </Grid>

        {/* Recent Activity */}
        <Grid item xs={12}>
          <Paper sx={{ p: 2 }}>
            <Typography variant="h6" gutterBottom>
              Recent Activity
            </Typography>
            <List>
              {recentActivity.map((activity, index) => (
                <ListItem key={index} divider={index < recentActivity.length - 1}>
                  <ListItemIcon>
                    {activity.status === 'completed' && <CheckCircle color="success" />}
                    {activity.status === 'processing' && <Schedule color="warning" />}
                    {activity.status === 'failed' && <Error color="error" />}
                  </ListItemIcon>
                  <ListItemText
                    primary={activity.word}
                    secondary={activity.time}
                  />
                  <Chip
                    label={activity.status}
                    size="small"
                    color={
                      activity.status === 'completed'
                        ? 'success'
                        : activity.status === 'processing'
                        ? 'warning'
                        : 'error'
                    }
                    variant="outlined"
                  />
                </ListItem>
              ))}
            </List>
          </Paper>
        </Grid>
      </Grid>
    </Box>
  );
};