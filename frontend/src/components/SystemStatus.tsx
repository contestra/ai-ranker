import React, { useState, useEffect } from 'react';
import { 
  ServerIcon, 
  CircleStackIcon, 
  CloudIcon, 
  CpuChipIcon,
  ArrowPathIcon,
  ExclamationTriangleIcon,
  CheckCircleIcon,
  XCircleIcon
} from '@heroicons/react/24/outline';

interface ServiceStatus {
  name: string;
  status: 'healthy' | 'degraded' | 'offline' | 'checking';
  latency?: number;
  message?: string;
  icon: React.ElementType;
}

interface SystemHealth {
  backend: ServiceStatus;
  database: ServiceStatus;
  cache: ServiceStatus;
  openai: ServiceStatus;
  gemini: ServiceStatus;
  background_runner: ServiceStatus;
  langchain: ServiceStatus;
}

export default function SystemStatus() {
  const [health, setHealth] = useState<SystemHealth>({
    backend: { name: 'API Server', status: 'checking', icon: ServerIcon },
    database: { name: 'SQLite DB', status: 'checking', icon: CircleStackIcon },
    cache: { name: 'Upstash Redis', status: 'checking', icon: CloudIcon },
    openai: { name: 'GPT-5', status: 'checking', icon: CpuChipIcon },
    gemini: { name: 'Gemini 2.5', status: 'checking', icon: CpuChipIcon },
    background_runner: { name: 'Task Runner', status: 'checking', icon: ArrowPathIcon },
    langchain: { name: 'LangChain/LangSmith', status: 'checking', icon: CloudIcon }
  });
  
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [lastCheckTime, setLastCheckTime] = useState<string | null>(null);

  const checkHealth = async () => {
    setIsRefreshing(true);
    
    try {
      // Check backend health
      const response = await fetch('http://localhost:8000/api/health');
      const data = await response.json();
      
      setHealth({
        backend: {
          name: 'API Server',
          status: data.status === 'healthy' ? 'healthy' : 'degraded',
          latency: data.response_time_ms,
          icon: ServerIcon
        },
        database: {
          name: 'SQLite DB',
          status: data.database?.status || 'offline',
          message: data.database?.message,
          icon: CircleStackIcon
        },
        cache: {
          name: 'Upstash Redis',
          status: data.cache?.status || 'offline',
          message: data.cache?.message,
          icon: CloudIcon
        },
        openai: {
          name: 'GPT-5',
          status: data.models?.openai?.status || 'offline',
          latency: data.models?.openai?.avg_response_time_ms,
          message: data.models?.openai?.message,
          icon: CpuChipIcon
        },
        gemini: {
          name: 'Gemini 2.5',
          status: data.models?.gemini?.status || 'offline',
          latency: data.models?.gemini?.avg_response_time_ms,
          message: data.models?.gemini?.message,
          icon: CpuChipIcon
        },
        background_runner: {
          name: 'Task Runner',
          status: data.background_runner?.status || 'offline',
          message: `${data.background_runner?.active_tasks || 0} active tasks`,
          icon: ArrowPathIcon
        },
        langchain: {
          name: 'LangChain/LangSmith',
          status: data.langchain?.status || 'offline',
          message: data.langchain?.status === 'healthy' 
            ? `Tracing: ${data.langchain?.project || 'N/A'}`
            : data.langchain?.message || 'Not configured',
          icon: CloudIcon
        }
      });
      
      // Update last check time after successful check
      setLastCheckTime(new Date().toLocaleTimeString());
    } catch (error) {
      // If backend is unreachable, mark everything as offline
      setHealth(prev => ({
        ...prev,
        backend: { ...prev.backend, status: 'offline', message: 'Cannot reach server' },
        database: { ...prev.database, status: 'offline' },
        cache: { ...prev.cache, status: 'offline' },
        openai: { ...prev.openai, status: 'offline' },
        gemini: { ...prev.gemini, status: 'offline' },
        background_runner: { ...prev.background_runner, status: 'offline' },
        langchain: { ...prev.langchain, status: 'offline' }
      }));
      
      // Update last check time even on error
      setLastCheckTime(new Date().toLocaleTimeString());
    } finally {
      setIsRefreshing(false);
    }
  };

  useEffect(() => {
    checkHealth();
    // No auto-refresh - user must manually click refresh button
  }, []);

  const getStatusColor = (status: ServiceStatus['status'] | 'disabled' | 'error') => {
    switch (status) {
      case 'healthy':
        return 'text-green-500';
      case 'degraded':
        return 'text-amber-500';
      case 'offline':
      case 'error':
        return 'text-red-500';
      case 'checking':
      case 'disabled':
        return 'text-gray-400';
    }
  };

  const getStatusIcon = (status: ServiceStatus['status']) => {
    switch (status) {
      case 'healthy':
        return <CheckCircleIcon className="w-5 h-5 text-green-500" />;
      case 'degraded':
        return <ExclamationTriangleIcon className="w-5 h-5 text-amber-500" />;
      case 'offline':
        return <XCircleIcon className="w-5 h-5 text-red-500" />;
      case 'checking':
        return <ArrowPathIcon className="w-5 h-5 text-gray-400 animate-spin" />;
    }
  };

  const getTrafficLight = (status: ServiceStatus['status']) => {
    return (
      <div className="flex gap-1">
        <div className={`w-2 h-2 rounded-full ${
          status === 'healthy' ? 'bg-green-500' : 'bg-gray-300'
        }`} />
        <div className={`w-2 h-2 rounded-full ${
          status === 'degraded' ? 'bg-amber-500' : 'bg-gray-300'
        }`} />
        <div className={`w-2 h-2 rounded-full ${
          status === 'offline' ? 'bg-red-500' : 'bg-gray-300'
        }`} />
      </div>
    );
  };

  const ServiceRow = ({ service }: { service: ServiceStatus }) => {
    const Icon = service.icon;
    
    return (
      <div className="flex items-center justify-between py-2 px-3 hover:bg-gray-50 rounded">
        <div className="flex items-center gap-2 flex-1">
          <Icon className={`w-4 h-4 ${getStatusColor(service.status)}`} />
          <span className="text-sm font-medium text-gray-700">{service.name}</span>
        </div>
        <div className="flex items-center gap-3">
          {service.latency && service.status === 'healthy' && (
            <span className="text-xs text-gray-500">{service.latency}ms</span>
          )}
          {service.message && service.status !== 'healthy' && (
            <span className="text-xs text-gray-500">{service.message}</span>
          )}
          {getTrafficLight(service.status)}
          {getStatusIcon(service.status)}
        </div>
      </div>
    );
  };

  const allHealthy = Object.values(health).every(s => s.status === 'healthy');
  const anyOffline = Object.values(health).some(s => s.status === 'offline');
  const anyDegraded = Object.values(health).some(s => s.status === 'degraded');

  return (
    <div className="bg-white rounded-lg shadow">
      <div className="px-4 py-3 border-b flex items-center justify-between">
        <h3 className="text-sm font-semibold text-gray-900">System Status</h3>
        <button
          onClick={checkHealth}
          disabled={isRefreshing}
          className="p-1 hover:bg-gray-100 rounded"
        >
          <ArrowPathIcon className={`w-4 h-4 text-gray-500 ${isRefreshing ? 'animate-spin' : ''}`} />
        </button>
      </div>
      
      <div className="p-2">
        {/* Overall Status Summary */}
        <div className={`mb-3 p-2 rounded-lg text-center text-sm font-medium ${
          allHealthy ? 'bg-green-50 text-green-700' :
          anyOffline ? 'bg-red-50 text-red-700' :
          anyDegraded ? 'bg-amber-50 text-amber-700' :
          'bg-gray-50 text-gray-700'
        }`}>
          {allHealthy ? 'All Systems Operational' :
           anyOffline ? 'System Issues Detected' :
           anyDegraded ? 'Partial Degradation' :
           'Checking Status...'}
        </div>

        {/* Service Status List */}
        <div className="space-y-1">
          <ServiceRow service={health.backend} />
          <ServiceRow service={health.database} />
          <ServiceRow service={health.cache} />
          
          <div className="border-t my-2" />
          <div className="text-xs font-semibold text-gray-500 px-3 py-1">AI Models</div>
          <ServiceRow service={health.gemini} />
          <ServiceRow service={health.openai} />
          
          <div className="border-t my-2" />
          <div className="text-xs font-semibold text-gray-500 px-3 py-1">Services</div>
          <ServiceRow service={health.background_runner} />
          <ServiceRow service={health.langchain} />
        </div>

        {/* Last Check Time */}
        {lastCheckTime && (
          <div className="mt-3 text-center text-xs text-gray-400">
            Last checked: {lastCheckTime}
          </div>
        )}
      </div>
    </div>
  );
}