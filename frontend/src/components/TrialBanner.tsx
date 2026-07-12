import { useNavigate, useLocation } from 'react-router-dom';
import { AlertTriangle, Sparkles, Lock } from 'lucide-react';
import { useLicenseStatus } from '../hooks/useLicenseStatus';

/**
 * 试用 / 到期 / 宽限期 提示横幅。
 * 根据 license 状态显示不同颜色和文案：
 *   grace_period          → 红色 + 锁定图标
 *   trial 且 ≤ 7 天        → 橙色 + 警告
 *   trial 且 > 7 天        → 蓝色 + 闪光（普通提示）
 *   active 且 ≤ 7 天       → 橙色（续费提醒）
 *   其他                   → 不显示
 */
export const TrialBanner = () => {
  const { info } = useLicenseStatus();
  const navigate = useNavigate();
  const location = useLocation();

  // 跳转激活页（设置页授权区块）
  const goActivate = () => {
    if (location.pathname !== '/settings') {
      navigate('/settings');
    }
    // 滚到顶部，授权信息区块在设置页顶部
    setTimeout(() => window.scrollTo({ top: 0, behavior: 'smooth' }), 100);
  };

  // 1. 宽限期（红色，最高优先级）
  if (info.status === 'grace_period') {
    return (
      <div className="bg-red-600 text-white px-6 py-3 flex items-center justify-between shadow-md">
        <div className="flex items-center gap-2">
          <Lock className="w-5 h-5 shrink-0" />
          <span className="text-sm font-medium">
            试用已到期 · 系统已进入<strong className="mx-1">只读模式</strong>，
            还剩 <strong className="mx-1">{info.grace_days_remaining}</strong> 天将完全失效，请立即联系销售激活正式版
          </span>
        </div>
        <button
          onClick={goActivate}
          className="bg-white text-red-600 px-4 py-1.5 rounded-md text-sm font-semibold hover:bg-red-50 transition-colors shrink-0 ml-4"
        >
          立即激活
        </button>
      </div>
    );
  }

  // 2. 试用版即将到期（橙色）
  if (info.status === 'trial_active' && info.days_remaining <= 7) {
    return (
      <div className="bg-orange-500 text-white px-6 py-2.5 flex items-center justify-between shadow-md">
        <div className="flex items-center gap-2">
          <AlertTriangle className="w-5 h-5 shrink-0" />
          <span className="text-sm font-medium">
            试用版即将到期 · 还剩 <strong className="mx-1">{info.days_remaining}</strong> 天，
            请尽快联系销售激活正式版避免中断
          </span>
        </div>
        <button
          onClick={goActivate}
          className="bg-white text-orange-600 px-4 py-1.5 rounded-md text-sm font-semibold hover:bg-orange-50 transition-colors shrink-0 ml-4"
        >
          立即激活
        </button>
      </div>
    );
  }

  // 3. 试用版（蓝色，普通提示）
  if (info.status === 'trial_active') {
    return (
      <div className="bg-blue-50 text-blue-800 border-b border-blue-200 px-6 py-2 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Sparkles className="w-4 h-4 shrink-0 text-blue-500" />
          <span className="text-sm">
            <strong>试用版</strong> · 剩余 <strong>{info.days_remaining}</strong> 天
            <span className="ml-2 text-blue-600 text-xs">（到期: {info.expire_date}）</span>
          </span>
        </div>
        <button
          onClick={goActivate}
          className="text-xs text-blue-700 hover:text-blue-900 underline shrink-0 ml-4"
        >
          激活正式版
        </button>
      </div>
    );
  }

  // 4. 正式版即将到期（橙色续费提醒）
  if (info.status === 'active' && info.days_remaining <= 7) {
    return (
      <div className="bg-orange-500 text-white px-6 py-2.5 flex items-center justify-between shadow-md">
        <div className="flex items-center gap-2">
          <AlertTriangle className="w-5 h-5 shrink-0" />
          <span className="text-sm font-medium">
            授权即将到期 · 剩余 <strong className="mx-1">{info.days_remaining}</strong> 天，请尽快续费
          </span>
        </div>
        <button
          onClick={goActivate}
          className="bg-white text-orange-600 px-4 py-1.5 rounded-md text-sm font-semibold hover:bg-orange-50 transition-colors shrink-0 ml-4"
        >
          立即续费
        </button>
      </div>
    );
  }

  return null;
};
