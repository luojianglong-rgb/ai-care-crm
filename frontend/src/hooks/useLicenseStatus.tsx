import { createContext, useContext, useState, useEffect, useCallback } from 'react';
import type { ReactNode } from 'react';
import axios from 'axios';

const API = import.meta.env.VITE_API_URL || '';

export interface LicenseStatusInfo {
  tier: string;                     // basic / pro / business
  valid: boolean;
  status: 'active' | 'trial_active' | 'grace_period' | 'expired' | 'invalid' | 'unactivated';
  is_trial: boolean;
  in_grace_period: boolean;
  grace_days_remaining: number;
  days_remaining: number;
  read_only_mode: boolean;
  expire_date: string;
  message: string;
  machine_id: string;
}

const DEFAULT_INFO: LicenseStatusInfo = {
  tier: 'basic',
  valid: false,
  status: 'unactivated',
  is_trial: false,
  in_grace_period: false,
  grace_days_remaining: 0,
  days_remaining: 0,
  read_only_mode: false,
  expire_date: '',
  message: '',
  machine_id: '',
};

interface LicenseContextType {
  info: LicenseStatusInfo;
  loading: boolean;
  refresh: () => Promise<void>;
}

const LicenseContext = createContext<LicenseContextType>({
  info: DEFAULT_INFO,
  loading: true,
  refresh: async () => {},
});

export const useLicenseStatus = () => useContext(LicenseContext);

const POLL_INTERVAL_MS = 60_000;  // 60 秒轮询

export const LicenseProvider = ({ children }: { children: ReactNode }) => {
  const [info, setInfo] = useState<LicenseStatusInfo>(DEFAULT_INFO);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    try {
      const res = await axios.get(`${API}/api/v1/config/info`);
      const lic = res.data?.license;
      if (lic) {
        setInfo({
          tier: lic.tier ?? 'basic',
          valid: !!lic.valid,
          status: lic.status ?? 'unactivated',
          is_trial: !!lic.is_trial,
          in_grace_period: !!lic.in_grace_period,
          grace_days_remaining: lic.grace_days_remaining ?? 0,
          days_remaining: lic.days_remaining ?? 0,
          read_only_mode: !!lic.read_only_mode,
          expire_date: lic.expire_date ?? '',
          message: lic.message ?? '',
          machine_id: lic.machine_id ?? '',
        });
      }
    } catch {
      // 未登录或网络错误时静默失败，banner 不显示
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    // 仅在已登录时拉取
    const token = localStorage.getItem('auth_token');
    if (!token) {
      setLoading(false);
      return;
    }
    refresh();
    const timer = window.setInterval(refresh, POLL_INTERVAL_MS);
    const onFocus = () => refresh();
    window.addEventListener('focus', onFocus);
    return () => {
      window.clearInterval(timer);
      window.removeEventListener('focus', onFocus);
    };
  }, [refresh]);

  return (
    <LicenseContext.Provider value={{ info, loading, refresh }}>
      {children}
    </LicenseContext.Provider>
  );
};
