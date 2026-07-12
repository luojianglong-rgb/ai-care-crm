import { useState, useEffect } from 'react';
import axios from 'axios';
import { Activity, Users, Brain, BookOpen, MessageSquare, TrendingUp, AlertTriangle, Zap, ChevronRight, AlertCircle, X, Calendar } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

const API = import.meta.env.VITE_API_URL || '';

interface IncompleteTask {
  client_id: string;
  name: string;
  record_id: string;
  date: string;
  treatment: string;
}

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

interface DashboardStats {
  todayBookings: number;
  newClientsThisMonth: number;
  totalIncome: number;
  incompleteRecords: IncompleteTask[];
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

const Dashboard = () => {
  const [aiData, setAiData] = useState<DashboardData | null>(null);
  const [sysInfo, setSysInfo] = useState<SystemInfo | null>(null);
  const [stats, setStats] = useState<DashboardStats>({ todayBookings: 0, newClientsThisMonth: 0, totalIncome: 0, incompleteRecords: [] });
  const [isRecordModalOpen, setIsRecordModalOpen] = useState(false);
  const [selectedTask, setSelectedTask] = useState<IncompleteTask | null>(null);
  const [formData, setFormData] = useState({ symptoms: '', description: '' });
  const navigate = useNavigate();

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [aiRes, sysRes, clientsRes] = await Promise.all([
          axios.get(`${API}/api/v1/dashboard/today`),
          axios.get(`${API}/api/v1/config/info`),
          axios.get(`${API}/api/v1/clients/`)
        ]);

        setAiData(aiRes.data);
        setSysInfo(sysRes.data);

        // 计算业务统计
        const clients = clientsRes.data;
        const today = new Date();
        today.setHours(0, 0, 0, 0);

        const incompleteRecords: IncompleteTask[] = [];
        clients.forEach((c: any) => {
          c.health_history.forEach((h: any) => {
            const isRecent = (new Date().getTime() - new Date(h.date).getTime()) < 30 * 24 * 60 * 60 * 1000;
            const isIncomplete = h.symptoms.length === 0 || !h.description || h.description.trim() === '常规消费';
            if (isRecent && isIncomplete) {
              incompleteRecords.push({
                client_id: c.client_id,
                name: c.name,
                record_id: h.record_id,
                date: h.date,
                treatment: h.treatment_provided
              });
            }
          });
        });

        setStats({
          todayBookings: 0,
          newClientsThisMonth: 0,
          totalIncome: 0,
          incompleteRecords: incompleteRecords.sort((a, b) => new Date(b.date).getTime() - new Date(a.date).getTime())
        });
      } catch (error) {
        console.error('加载数据失败', error);
      }
    };

    fetchData();
  }, []);

  const handleSaveRecord = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedTask) return;
    try {
      const symptomsArray = formData.symptoms.split(/[,，]/).map(s => s.trim()).filter(s => s);
      await axios.put(`${API}/api/v1/clients/${selectedTask.client_id}/records/${selectedTask.record_id}`, {
        symptoms: symptomsArray,
        description: formData.description
      });
      setIsRecordModalOpen(false);
      setStats(prev => ({
        ...prev,
        incompleteRecords: prev.incompleteRecords.filter(t => t.record_id !== selectedTask.record_id)
      }));
      alert('健康档案补全成功！');
    } catch (error) {
      alert('补全档案失败');
    }
  };

  if (!aiData || !sysInfo) return <div className="p-8 text-slate-500">Loading...</div>;

  const q = aiData.quota;
  const d = aiData.client_dynamics;
  const o = aiData.today_outreach;

  return (
    <div className="p-8 max-w-7xl mx-auto">
      {/* Header */}
      <div className="mb-8 flex justify-between items-end">
        <div>
          <h1 className="text-3xl font-black text-slate-800 tracking-tight">今日工作台</h1>
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

      {/* KPI Row 1 - 业务概览 */}
      <div className="grid grid-cols-5 gap-3 mb-6">
        <KPICard icon={Calendar} label="今日预约" value={0} unit="人" color="blue" />
        <KPICard icon={Users} label="客户总数" value={d.total_clients} unit="人" color="emerald" />
        <KPICard icon={TrendingUp} label="本周新增" value={d.new_this_week} unit="人" color="green" />
        <KPICard icon={AlertTriangle} label="沉默预警" value={d.silent_warning} unit="人" color="orange" onClick={() => navigate('/playbooks')} />
        <KPICard icon={AlertTriangle} label="流失预警" value={d.churn_risk} unit="人" color="red" onClick={() => navigate('/playbooks')} />
      </div>

      {/* Row 1.5: Revenue Summary */}
      <div className="grid grid-cols-4 gap-4 mb-6">
        <div className="bg-white p-4 rounded-2xl shadow-sm border border-slate-100 flex flex-col justify-center cursor-pointer hover:shadow-md transition-shadow relative" onClick={() => navigate('/billing')}>
          <div className="flex justify-between items-center">
            <span className="text-slate-500 font-bold text-xs uppercase">今日收入</span>
            <ChevronRight className="w-4 h-4 text-slate-300" />
          </div>
          <span className="text-2xl font-black text-emerald-600 mt-2">¥0</span>
        </div>
        <div className="bg-white p-4 rounded-2xl shadow-sm border border-slate-100 flex flex-col justify-center">
          <span className="text-slate-500 font-bold text-xs uppercase">充值收入</span>
          <span className="text-2xl font-black text-blue-600 mt-2">¥0</span>
        </div>
        <div className="bg-white p-4 rounded-2xl shadow-sm border border-slate-100 flex flex-col justify-center">
          <span className="text-slate-500 font-bold text-xs uppercase">次卡充值</span>
          <span className="text-2xl font-black text-purple-600 mt-2">0 次</span>
        </div>
        <div className="bg-white p-4 rounded-2xl shadow-sm border border-slate-100 flex flex-col justify-center">
          <span className="text-slate-500 font-bold text-xs uppercase">待完善档案</span>
          <span className="text-2xl font-black text-orange-600 mt-2">{stats.incompleteRecords.length} 份</span>
        </div>
      </div>

      {/* Row 2: Business Data + AI Features */}
      <div className="grid grid-cols-3 gap-6 mb-6">
        {/* Today Outreach */}
        <div className="bg-white rounded-2xl shadow-sm border border-slate-100 p-6">
          <h3 className="text-sm font-bold text-slate-500 uppercase mb-4 flex items-center">
            <Activity className="w-4 h-4 mr-2" /> 今日触达
          </h3>
          <div className="grid grid-cols-2 gap-3">
            <MiniStat label="已发送" value={o.sent} color="emerald" />
            <MiniStat label="排队中" value={o.queued} color="blue" />
            <MiniStat label="待审批" value={o.pending_approval} color="orange" />
            <MiniStat label="失败" value={o.failed} color="red" />
          </div>
        </div>

        {/* AI Quota */}
        <div className="bg-white rounded-2xl shadow-sm border border-slate-100 p-6">
          <h3 className="text-sm font-bold text-slate-500 uppercase mb-4 flex items-center">
            <Brain className="w-4 h-4 mr-2" /> AI 额度
          </h3>
          <div className="space-y-3">
            <QuotaBar label="专业分析" used={q.analysis_used} limit={q.analysis_limit} />
            <QuotaBar label="方案生成" used={q.plan_used} limit={q.plan_limit} />
            <QuotaBar label="营销文案" used={q.content_used} limit={q.content_limit} />
          </div>
        </div>

        {/* Service Records Maintenance */}
        <div className="bg-white rounded-2xl shadow-sm border border-slate-100 p-6">
          <h3 className="text-sm font-bold text-slate-500 uppercase mb-4 flex items-center">
            <AlertCircle className="w-4 h-4 mr-2" /> 档案维护
          </h3>
          <div className="space-y-4">
            <div>
              <div className="flex justify-between text-xs mb-1">
                <span className="text-slate-600 font-medium">待完善档案</span>
                <span className={`font-bold ${stats.incompleteRecords.length > 0 ? 'text-orange-600' : 'text-emerald-600'}`}>
                  {stats.incompleteRecords.length} 份
                </span>
              </div>
              <div className="w-full h-2 bg-slate-100 rounded-full overflow-hidden">
                <div
                  className={stats.incompleteRecords.length > 0 ? 'bg-orange-500' : 'bg-emerald-500'}
                  style={{ width: stats.incompleteRecords.length > 0 ? '100%' : '0%' }}
                />
              </div>
            </div>
            <button
              onClick={() => {
                const elem = document.querySelector('[data-incomplete-records]');
                if (elem) elem.scrollIntoView({ behavior: 'smooth' });
              }}
              className={`w-full py-2 text-xs font-bold rounded-lg transition-colors ${
                stats.incompleteRecords.length > 0
                  ? 'bg-orange-50 text-orange-600 border border-orange-200 hover:bg-orange-100'
                  : 'bg-emerald-50 text-emerald-600 border border-emerald-200'
              }`}
            >
              {stats.incompleteRecords.length > 0 ? '立即补全' : '档案完善 ✓'}
            </button>
          </div>
        </div>
      </div>

      {/* Row 3: Playbook Reports + Recent Replies */}
      <div className="grid grid-cols-2 gap-6 mb-6">
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
          <div className="divide-y divide-slate-50 max-h-64 overflow-y-auto">
            {aiData.playbook_reports.map((pb, i) => (
              <div key={i} className="px-5 py-3 flex justify-between items-center">
                <div className="flex items-center gap-2">
                  <span className={`w-2 h-2 rounded-full ${pb.is_active ? 'bg-emerald-400' : 'bg-slate-300'}`} />
                  <span className="text-sm font-medium text-slate-700">{pb.name}</span>
                </div>
                <div className="flex gap-3 text-xs text-slate-500">
                  <span>累计 {pb.total_tasks}</span>
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
          <div className="divide-y divide-slate-50 max-h-64 overflow-y-auto">
            {aiData.recent_replies.length === 0 ? (
              <div className="p-8 text-center text-slate-400 text-sm">暂无客户回复</div>
            ) : (
              aiData.recent_replies.map((r, i) => {
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

      {/* Incomplete Records Section */}
      {stats.incompleteRecords.length > 0 && (
        <div className="bg-white rounded-3xl shadow-sm border border-slate-100 overflow-hidden" data-incomplete-records>
          <div className="p-6 border-b border-slate-100 bg-slate-50/50 flex justify-between items-center">
            <h2 className="text-lg font-bold text-slate-800 flex items-center">
              <AlertCircle className="w-5 h-5 mr-2 text-orange-500" />
              待完善的健康档案
            </h2>
            <span className="text-xs font-bold text-slate-500 bg-white px-3 py-1 rounded-full border border-slate-200 shadow-sm">
              AI 分析依赖于完整的档案数据
            </span>
          </div>

          <div className="divide-y divide-slate-50">
            {stats.incompleteRecords.slice(0, 5).map(task => (
              <div key={task.record_id} className="p-6 flex items-center justify-between hover:bg-slate-50 transition-colors group">
                <div className="flex items-center gap-4">
                  <div className="w-12 h-12 rounded-full bg-orange-100 text-orange-600 flex items-center justify-center font-bold text-lg">
                    {task.name.charAt(0)}
                  </div>
                  <div>
                    <h3 className="font-bold text-slate-800 text-lg">{task.name} <span className="text-sm font-medium text-slate-400 ml-2">的调理记录</span></h3>
                    <div className="flex gap-3 mt-1 text-sm">
                      <span className="text-slate-500">消费时间: {new Date(task.date).toLocaleDateString()}</span>
                      <span className="text-slate-300">|</span>
                      <span className="text-slate-500">项目: {task.treatment}</span>
                      <span className="text-orange-500 font-medium text-xs bg-orange-50 px-2 py-0.5 rounded ml-2 border border-orange-100">
                        缺症状/详细描述
                      </span>
                    </div>
                  </div>
                </div>
                <button
                  onClick={() => {
                    setSelectedTask(task);
                    setFormData({ symptoms: '', description: '' });
                    setIsRecordModalOpen(true);
                  }}
                  className="flex items-center text-emerald-600 font-bold bg-white border border-emerald-200 px-4 py-2 rounded-xl group-hover:bg-emerald-50 transition-colors shadow-sm"
                >
                  去补全档案 <ChevronRight className="w-4 h-4 ml-1" />
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Record Completion Modal */}
      {isRecordModalOpen && selectedTask && (
        <div className="fixed inset-0 bg-slate-900/60 backdrop-blur-sm flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-3xl shadow-2xl w-full max-w-md overflow-hidden animate-in fade-in zoom-in duration-200">
            <div className="p-6 border-b border-slate-100 flex justify-between items-center bg-slate-50/50">
              <h2 className="text-xl font-bold text-slate-800">补全健康档案</h2>
              <X onClick={() => setIsRecordModalOpen(false)} className="w-6 h-6 text-slate-400 cursor-pointer hover:text-slate-600" />
            </div>
            <form onSubmit={handleSaveRecord} className="p-6 space-y-5">
              <div className="mb-4 text-sm text-slate-600">
                <p className="mb-1"><strong>客户姓名：</strong>{selectedTask.name}</p>
                <p><strong>调理项目：</strong>{selectedTask.treatment}</p>
              </div>
              <div>
                <label className="block text-xs font-bold text-slate-500 uppercase mb-2">症状 (逗号分隔)</label>
                <input value={formData.symptoms} onChange={e => setFormData({...formData, symptoms: e.target.value})} className="w-full px-4 py-3 bg-slate-50 border border-slate-100 rounded-xl focus:ring-2 focus:ring-emerald-500 outline-none font-medium text-sm" placeholder="如：怕冷, 失眠" />
              </div>
              <div>
                <label className="block text-xs font-bold text-slate-500 uppercase mb-2">详细描述</label>
                <textarea rows={4} required value={formData.description} onChange={e => setFormData({...formData, description: e.target.value})} className="w-full px-4 py-3 bg-slate-50 border border-slate-100 rounded-xl focus:ring-2 focus:ring-emerald-500 outline-none text-sm resize-none" placeholder="记录客户具体的调理反馈或观察结果..." />
              </div>
              <button type="submit" className="w-full py-4 mt-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl font-bold shadow-lg transition-all">
                保存调理记录
              </button>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

// ── Sub Components ──

const KPICard = ({ icon: Icon, label, value, unit, color, onClick }: any) => {
  const colorMap: Record<string, string> = {
    blue: 'text-blue-600', green: 'text-green-600', emerald: 'text-emerald-600', orange: 'text-orange-500', red: 'text-red-500',
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

export default Dashboard;
