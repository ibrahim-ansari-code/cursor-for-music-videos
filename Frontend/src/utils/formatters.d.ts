export type Delta = 
  | { show: false }
  | {
      show: true;
      direction: 'up' | 'down' | 'neutral' | 'new' | 'cleared';
      absolute: number;
      percent: number | null;
      sign: string;
      colorClass: string;
      iconName: string;
    };

export function formatCurrency(value: number | string | null | undefined): string;

export function clampPercent(value: number | string | null | undefined): number;

export function percentChange(current: number | string | null | undefined, previous: number | string | null | undefined): number;

export function computeDelta(params: {
  current: number | string | null | undefined;
  previous: number | string | null | undefined;
  minPercent?: number;
  minAbsolute?: number;
}): Delta;

export function humanizePeriodLabel(timePeriod: string, activeRange: { start: string; end: string }): string;

export function getAvatarColor(name: string): string;

export function getInitials(name: string): string;

