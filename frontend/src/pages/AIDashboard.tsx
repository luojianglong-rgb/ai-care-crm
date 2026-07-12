import { useState, useEffect } from 'react';
import axios from 'axios';
import { Activity, Users, Brain, BookOpen, MessageSquare, TrendingUp, AlertTriangle, Zap, ChevronRight } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

const API = import.meta.env.VITE_API_URL || '';

interface DashboardData {
  today_outreach: { sent: number; queued: number; pending_approval: number; failed: number; total: number };
  client_dynamics: { total_clients: number; new_this_week: number; silent_warning: number; churn_risk: number; returned_this_week: number };
  quota: { tier: string; analysis_used: number; analysis_limit: number; plan_used: number; plan_limit: number; content_used: number; content_limit: number };
  playbook_reports: { name: string; is_active: boolean; total_tasks: number; sent_tasks: number; pending_tasks: number }[];
  recent_replies: { client_name: string; intent: string; raw_content: string; created_at: string }[];
}

interface SystemInfo {
  store: { name: string; business_type: string };
  terminology: { staff_title: string; analysis_name: string; plan_name: string };
  license: { tier: string; valid: boolean; expire_date: string; days_remaining: number; machine_id: string };
  llm: { mode: string; provider: string; model: string; available: boolean };
}

const intentLabels: Record<string, { text: string; color: string }> = {
  symptom_improved: { text: '症状好转', color: 'text-emerald-600 bg-emerald-50' },
  symptom_persists: { text: '症状持续', color: 'text-orange-600 bg-orange-50' },
  want_booking: { text: '想预约', color: 'text-blue-600 bg-blue-50' },
  price_inquiry: { text: '询价', color: 'text-purple-600 bg-purple-50' },
  general_chat: { text: '普通回复', color: 'text-slate-600 bg-slate-50' },
  negative: { text: '负面反馈', color: 'text-red-600 bg-red-50' },
};

const tierLabels: Record<string, string> = { free: '基础版', pro: '专业版', business: '至尊版' };

const AIDashboard = () => {
  const [data, setData] = useState<DashboardData | null>(null);
  const [sysInfo, setSysInfo] = useState<SystemInfo | null>(null);
  const navigate = useNavigate();

  useEffect(() => {
    axios.get(`${API}/api/v1/dashboard/today`).then(r => setData(r.data)).catch(console.error);
    axios.get(`${API}/api/v1/config/info`).then(r => setSysInfo(r.data)).catch(console.error);
  }, []);

  if (!data || !sysInfo) return <div className="p-8 text-slate-500">Loading...</div>;

  const q = data.quota;
  const d = data.client_dynamics;
  const o = data.today_outreach;

  return (
    <div className="p-8 max-w-7xl mx-auto">
      {/* Header */}
      <div className="mb-8 flex justify-between items-end">
        <div>
          <h1 className="text-3xl font-black text-slate-800 tracking-tight">AI 驾驶舱</h1>
          <p className="text-slate-500 mt-1">{sysInfo.store.name} · {sysInfo.terminology.analysis_name} · {tierLabels[q.tier] || q.tier}</p>
        </div>
        {sysInfo.llm.available ? (
          <span className="flex items-center text-sm text-emerald-600 bg-emerald-50 px-3 py-1.5 rounded-full border border-emerald-200">
            <Zap className="w-4 h-4 mr-1" /> AI ({sysInfo.llm.provider}) 已就绪
          </span>
        ) : (
          <span className="text-sm text-orange-600 bg-orange-50 px-3 py-1.5 rounded-full border border-orange-200">
            AI 未配置
          </span>
        )}
      </div>

      {/* KPI Cards Row 1 */}
      <div className="grid grid-cols-4 gap-4 mb-6">
        <KPICard icon={Users} label="客户总数" value={d.total_clients} unit="人" color="blue" />
        <KPICard icon={TrendingUp} label="本周新增" value={d.new_this_week} unit="人" color="emerald" />
        <KPICard icon={AlertTriangle} label="沉默预警" value={d.silent_warning} unit="人" color="orange" onClick={() => navigate('/playbooks')} />
        <KPICard icon={AlertTriangle} label="流失预警" value={d.churn_risk} unit="人" color="red" onClick={() => navigate('/playbooks')} />
      </div>

      {/* Row 2: Outreach + Quota */}
      <div className="grid grid-cols-2 gap-6 mb-6">
        {/* Today Outreach */}
        <div className="bg-white rounded-2xl shadow-sm border border-slate-100 p-6">
          <h3 className="text-sm font-bold text-slate-500 uppercase mb-4 flex items-center">
            <Activity className="w-4 h-4 mr-2" /> 今日触达
          </h3>
          <div className="grid grid-cols-4 gap-3">
            <MiniStat label="已发送" value={o.sent} color="emerald" />
            <MiniStat label="排队中" value={o.queued} color="blue" />
            <MiniStat label="待审批" value={o.pending_approval} color="orange" />
            <MiniStat label="失败" value={o.failed} color="red" />
          </div>
        </div>

        {/* AI Quota */}
        <div className="bg-white rounded-2xl shadow-sm border border-slate-100 p-6">
          <h3 className="text-sm font-bold text-slate-500 uppercase mb-4 flex items-center">
            <Brain className="w-4 h-4 mr-2" /> AI 额度 ({tierLabels[q.tier] || q.tier})
          </h3>
          <div className="space-y-3">
            <QuotaBar label="专业分析" used={q.analysis_used} limit={q.analysis_limit} />
            <QuotaBar label="方案生成" used={q.plan_used} limit={q.plan_limit} />
            <QuotaBar label="营销文案" used={q.content_used} limit={q.content_limit} />
          </div>
        </div>
      </div>

      {/* Row 3: Playbook Reports + Recent Replies */}
      <div className="grid grid-cols-2 gap-6">
        {/* Playbook Reports */}
        <div className="bg-white rounded-2xl shadow-sm border border-slate-100 overflow-hidden">
          <div className="p-5 border-b border-slate-100 flex justify-between items-center">
            <h3 className="text-sm font-bold text-slate-500 uppercase flex items-center">
              <BookOpen className="w-4 h-4 mr-2" /> 运营剧本
            </h3>
            <button onClick={() => navigate('/playbooks')} className="text-xs text-emerald-600 font-bold hover:underline flex items-center">
              管理 <ChevronRight className="w-3 h-3" />
            </button>
          </div>
          <div className="divide-y divide-slate-50">
            {data.playbook_reports.map((pb, i) => (
              <div key={i} className="px-5 py-3 flex justify-between items-center">
                <div className="flex items-center gap-2">
                  <span className={`w-2 h-2 rounded-full ${pb.is_active ? 'bg-emerald-400' : 'bg-slate-300'}`} />
                  <span className="text-sm font-medium text-slate-700">{pb.name}</span>
                </div>
                <div className="flex gap-3 text-xs text-slate-500">
                  <span>累计 {pb.total_tasks}</span>
                  <span>已发 {pb.sent_tasks}</span>
                  {pb.pending_tasks > 0 && <span className="text-orange-600 font-bold">待审 {pb.pending_tasks}</span>}
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Recent Replies */}
        <div className="bg-white rounded-2xl shadow-sm border border-slate-100 overflow-hidden">
          <div className="p-5 border-b border-slate-100">
            <h3 className="text-sm font-bold text-slate-500 uppercase flex items-center">
              <MessageSquare className="w-4 h-4 mr-2" /> 最近客户回复
            </h3>
          </div>
          <div className="divide-y divide-slate-50">
            {data.recent_replies.length === 0 ? (
              <div className="p-8 text-center text-slate-400 text-sm">暂无客户回复</div>
            ) : (
              data.recent_replies.map((r, i) => {
                const label = intentLabels[r.intent] || intentLabels.general_chat;
                return (
                  <div key={i} className="px-5 py-3">
                    <div className="flex justify-between items-center mb-1">
                      <span className="font-medium text-sm text-slate-700">{r.client_name}</span>
                      <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${label.color}`}>{label.text}</span>
                    </div>
                    <p className="text-xs text-slate-500 truncate">{r.raw_content}</p>
                  </div>
                );
              })
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

// ── Sub Components ──

const KPICard = ({ icon: Icon, label, value, unit, color, onClick }: any) => {
  const colorMap: Record<string, string> = {
    blue: 'text-blue-600', emerald: 'text-emerald-600', orange: 'text-orange-500', red: 'text-red-500',
  };
  return (
    <div onClick={onClick} className={`bg-white p-5 rounded-2xl shadow-sm border border-slate-100 ${onClick ? 'cursor-pointer hover:shadow-md transition-shadow' : ''}`}>
      <div className="flex items-center gap-2 mb-2">
        <Icon className={`w-4 h-4 ${colorMap[color] || 'text-slate-500'}`} />
        <span className="text-xs font-bold text-slate-500 uppercase">{label}</span>
      </div>
      <span className={`text-3xl font-black ${colorMap[color] || 'text-slate-700'}`}>
        {value} <span className="text-sm text-slate-400 font-medium">{unit}</span>
      </span>
    </div>
  );
};

const MiniStat = ({ label, value, color }: { label: string; value: number; color: string }) => {
  const colors: Record<string, string> = {
    emerald: 'text-emerald-600', blue: 'text-blue-600', orange: 'text-orange-500', red: 'text-red-500',
  };
  return (
    <div className="text-center">
      <div className={`text-2xl font-black ${colors[color] || ''}`}>{value}</div>
      <div className="text-xs text-slate-500 mt-1">{label}</div>
    </div>
  );
};

const QuotaBar = ({ label, used, limit }: { label: string; used: number; limit: number }) => {
  const unlimited = limit === -1;
  const pct = unlimited ? 0 : limit > 0 ? Math.min(100, (used / limit) * 100) : 0;
  const barColor = pct > 80 ? 'bg-orange-500' : 'bg-emerald-500';
  return (
    <div>
      <div className="flex justify-between text-xs mb-1">
        <span className="text-slate-600 font-medium">{label}</span>
        <span className="text-slate-500">{unlimited ? `${used} / 不限` : `${used} / ${limit}`}</span>
      </div>
      {!unlimited && (
        <div className="w-full h-1.5 bg-slate-100 rounded-full overflow-hidden">
          <div className={`h-full rounded-full transition-all ${barColor}`} style={{ width: `${pct}%` }} />
        </div>
      )}
    </div>
  );
};

export default AIDashboard;
