/**
 * Formatting and color helper functions for cybersecurity UI
 */

import { DecisionType, ResourceSensitivity } from '../types';

export function getDecisionBadgeColor(decision?: DecisionType): string {
  switch (decision?.toUpperCase()) {
    case 'ALLOW':
      return 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30';
    case 'BLOCK':
      return 'bg-rose-500/15 text-rose-400 border-rose-500/30';
    case 'ASK_HUMAN':
      return 'bg-amber-500/15 text-amber-400 border-amber-500/30';
    default:
      return 'bg-slate-500/15 text-slate-400 border-slate-500/30';
  }
}

export function getRiskColor(score: number): { text: string; bg: string; border: string; bar: string } {
  if (score < 40) {
    return {
      text: 'text-emerald-400',
      bg: 'bg-emerald-500/10',
      border: 'border-emerald-500/20',
      bar: 'bg-emerald-500'
    };
  } else if (score < 70) {
    return {
      text: 'text-amber-400',
      bg: 'bg-amber-500/10',
      border: 'border-amber-500/20',
      bar: 'bg-amber-500'
    };
  } else {
    return {
      text: 'text-rose-400',
      bg: 'bg-rose-500/10',
      border: 'border-rose-500/20',
      bar: 'bg-rose-500'
    };
  }
}

export function getSensitivityBadgeColor(sensitivity?: ResourceSensitivity): string {
  switch (sensitivity) {
    case 'CRITICAL':
      return 'bg-rose-500/20 text-rose-300 border-rose-500/40';
    case 'HIGH':
      return 'bg-orange-500/20 text-orange-300 border-orange-500/40';
    case 'MEDIUM':
      return 'bg-amber-500/20 text-amber-300 border-amber-500/40';
    case 'LOW':
    default:
      return 'bg-slate-700/40 text-slate-300 border-slate-600/40';
  }
}

export function formatLatency(ms?: number): string {
  if (ms === undefined || ms === null) return '0.00ms';
  if (ms < 1) return `${(ms * 1000).toFixed(0)}µs`;
  return `${ms.toFixed(2)}ms`;
}

export function formatPercent(rate?: number): string {
  if (rate === undefined || rate === null) return '0.0%';
  return `${(rate * 100).toFixed(1)}%`;
}

export function formatTimeAgo(dateStrOrTs?: string | number | null): string {
  if (!dateStrOrTs) return 'Just now';
  const timestamp = typeof dateStrOrTs === 'number' ? dateStrOrTs * 1000 : new Date(dateStrOrTs).getTime();
  const diffSec = Math.floor((Date.now() - timestamp) / 1000);
  if (diffSec < 5) return 'Just now';
  if (diffSec < 60) return `${diffSec}s ago`;
  if (diffSec < 3600) return `${Math.floor(diffSec / 60)}m ago`;
  return `${Math.floor(diffSec / 3600)}h ago`;
}
