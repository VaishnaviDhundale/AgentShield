/**
 * Global Security Context managing real-time WebSocket state and live telemetry
 */

import React, { createContext, useContext, useEffect, useState, useCallback, ReactNode } from 'react';
import { SecurityEvent, OverviewStatistics, PendingApproval } from '../types';
import { api } from '../services/api';

interface SecurityContextType {
  isConnected: boolean;
  events: SecurityEvent[];
  stats: OverviewStatistics | null;
  pendingApprovals: PendingApproval[];
  activePolicy: string;
  selectedRequestId: string | null;
  isApprovalModalOpen: boolean;
  isAgentModalOpen: boolean;
  setSelectedRequestId: (id: string | null) => void;
  setIsApprovalModalOpen: (open: boolean) => void;
  setIsAgentModalOpen: (open: boolean) => void;
  refreshStats: () => Promise<void>;
  refreshApprovals: () => Promise<void>;
  switchPolicy: (policyName: string) => Promise<void>;
  resolveApproval: (id: string, decision: 'ALLOW_ONCE' | 'ALLOW_SESSION' | 'BLOCK', notes?: string) => Promise<void>;
  clearEvents: () => void;
}

const SecurityContext = createContext<SecurityContextType | undefined>(undefined);

export const SecurityProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [isConnected, setIsConnected] = useState<boolean>(false);
  const [events, setEvents] = useState<SecurityEvent[]>([]);
  const [stats, setStats] = useState<OverviewStatistics | null>(null);
  const [pendingApprovals, setPendingApprovals] = useState<PendingApproval[]>([]);
  const [activePolicy, setActivePolicy] = useState<string>('AgentShieldPolicy');
  const [selectedRequestId, setSelectedRequestId] = useState<string | null>(null);
  const [isApprovalModalOpen, setIsApprovalModalOpen] = useState<boolean>(false);
  const [isAgentModalOpen, setIsAgentModalOpen] = useState<boolean>(false);

  const refreshStats = useCallback(async () => {
    try {
      const data = await api.getOverviewStats();
      setStats(data);
      if (data.active_policy) {
        setActivePolicy(data.active_policy);
      }
    } catch (err) {
      console.error('Failed to load stats:', err);
    }
  }, []);

  const refreshApprovals = useCallback(async () => {
    try {
      const data = await api.getPendingApprovals();
      setPendingApprovals(data);
    } catch (err) {
      console.error('Failed to load pending approvals:', err);
    }
  }, []);

  const switchPolicy = async (policyName: string) => {
    try {
      const res = await api.setActivePolicy(policyName);
      setActivePolicy(res.active_policy);
      await refreshStats();
    } catch (err) {
      console.error('Failed to switch policy:', err);
    }
  };

  const resolveApproval = async (
    id: string,
    decision: 'ALLOW_ONCE' | 'ALLOW_SESSION' | 'BLOCK',
    notes?: string
  ) => {
    try {
      await api.resolveApproval(id, decision, notes);
      await refreshApprovals();
      await refreshStats();
    } catch (err) {
      console.error(`Failed to resolve approval ${id}:`, err);
    }
  };

  const clearEvents = () => {
    setEvents([]);
  };

  // Initial data fetch
  useEffect(() => {
    refreshStats();
    refreshApprovals();
  }, [refreshStats, refreshApprovals]);

  // WebSocket Connection with auto-reconnect
  useEffect(() => {
    let ws: WebSocket | null = null;
    let reconnectTimeout: any = null;
    let isSubscribed = true;

    const connectWebSocket = () => {
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const host = window.location.host;
      // In dev mode with vite proxy, or directly targeting localhost:8000
      const wsUrl = `${protocol}//${host}/ws/live`;

      try {
        ws = new WebSocket(wsUrl);

        ws.onopen = () => {
          if (!isSubscribed) return;
          setIsConnected(true);
          console.log('✅ Connected to AgentShield Live Security Stream');
        };

        ws.onmessage = (event) => {
          if (!isSubscribed) return;
          try {
            const data: SecurityEvent = JSON.parse(event.data);
            data.timestamp = new Date().toISOString();

            // Ignore keep-alive pong
            if (data.event_type === 'PONG') return;

            // Prepend new event (keep last 200 events)
            setEvents((prev) => [data, ...prev.slice(0, 199)]);

            // If an approval was requested or resolved, refresh approval list
            if (
              data.event_type === 'HUMAN_APPROVAL_REQUESTED' ||
              data.event_type === 'HUMAN_APPROVAL_RESOLVED'
            ) {
              refreshApprovals();
            }

            // Update stats & active policy
            if (data.event_type === 'POLICY_SWITCHED' && data.active_policy) {
              setActivePolicy(data.active_policy);
            }

            // Periodically refresh stats on tool decisions
            if (
              data.event_type === 'TOOL_REQUEST_INTERCEPTED' ||
              data.event_type === 'AGENT_RUN_COMPLETED'
            ) {
              refreshStats();
            }
          } catch (err) {
            console.warn('Failed to parse WebSocket message:', event.data);
          }
        };

        ws.onclose = () => {
          if (!isSubscribed) return;
          setIsConnected(false);
          console.log('⚠️ Disconnected from security stream. Reconnecting in 2s...');
          reconnectTimeout = setTimeout(connectWebSocket, 2000);
        };

        ws.onerror = (err) => {
          console.error('WebSocket Error:', err);
          ws?.close();
        };
      } catch (err) {
        console.error('Failed to establish WebSocket:', err);
        reconnectTimeout = setTimeout(connectWebSocket, 2000);
      }
    };

    connectWebSocket();

    // Keep-alive ping interval
    const pingInterval = setInterval(() => {
      if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ action: 'ping' }));
      }
    }, 15000);

    return () => {
      isSubscribed = false;
      clearInterval(pingInterval);
      clearTimeout(reconnectTimeout);
      if (ws) {
        ws.close();
      }
    };
  }, [refreshApprovals, refreshStats]);

  return (
    <SecurityContext.Provider
      value={{
        isConnected,
        events,
        stats,
        pendingApprovals,
        activePolicy,
        selectedRequestId,
        isApprovalModalOpen,
        isAgentModalOpen,
        setSelectedRequestId,
        setIsApprovalModalOpen,
        setIsAgentModalOpen,
        refreshStats,
        refreshApprovals,
        switchPolicy,
        resolveApproval,
        clearEvents
      }}
    >
      {children}
    </SecurityContext.Provider>
  );
};

export const useSecurity = (): SecurityContextType => {
  const context = useContext(SecurityContext);
  if (!context) {
    throw new Error('useSecurity must be used within a SecurityProvider');
  }
  return context;
};
