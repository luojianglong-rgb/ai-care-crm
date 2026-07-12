import { useState, useEffect } from 'react';
import axios from 'axios';
import { Activity, Users, Brain, BookOpen, MessageSquare, TrendingUp, AlertTriangle, Zap, ChevronRight, AlertCircle, X, Calendar, Loader2 } from 'lucide-react';
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

const intentLabels: Record<string, { text: string; color: string }> = {
  symptom_improved: { text: '症状好转', color: 'text-emerald-600 bg-emerald-50' },
  symptom_persists: { text: '症状持续', color: 'text-orange-600 bg-orange-50' },
  want_booking: { text: '想预约', color: 'text-blue-600 bg-blue-50' },
  price_inquiry: { text: '询价', color: 'text-purple-600 bg-purple-50' },
  general_chat: { text: '普通回复', color: 'text-slate-600 bg-slate-50' },
  negative: { text: '负面反馈', color: 'text-red-600 bg-red-50' },
};

const tierLabels: Record<string, string> = { free: '基础版', pro: '专业版', business: '至尊版' };

const UnifiedDashboard = () => {
  const [tab, setTab] = useState<'business' | 'ai'>('business');
  const [aiData, setAiData] = useState<DashboardData | null>(null);
  const [sysInfo, setSysInfo] = useState<SystemInfo | null>(null);
  const [incompleteRecords, setIncompleteRecords] = useState<IncompleteTask[]>([]);
  const [isRecordModalOpen, setIsRecordModalOpen] = useState(false);
  const [selectedTask, setSelectedTask] = useState<IncompleteTask | null>(null);
  const [formData, setFormData] = useState({ symptoms: '', description: '' });
  const [loading, setLoading] = useState(true);
  const [todayRevenue, setTodayRevenue] = useState(0);
  const [rechargeBalance, setRechargeBalance] = useState(0);
  const [todayRecharge, setTodayRecharge] = useState(0);
  const navigate = useNavigate();

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        const [aiRes, sysRes, clientsRes, transRes] = await Promise.all([
          axios.get(`${API}/api/v1/dashboard/today`),
          axios.get(`${API}/api/v1/config/info`),
          axios.get(`${API}/api/v1/clients/`),
          axios.get(`${API}/api/v1/billing/`)
        ]);

        setAiData(aiRes.data);
        setSysInfo(sysRes.data);

        // 计算待完善档案
        const clients = clientsRes.data;
        const incomplete: IncompleteTask[] = [];
        clients.forEach((c: any) => {
          c.health_history.forEach((h: any) => {
            const isRecent = (new Date().getTime() - new Date(h.date).getTime()) < 30 * 24 * 60 * 60 * 1000;
            const isIncomplete = h.symptoms.length === 0 || !h.description || h.description.trim() === '常规消费';
            if (isRecent && isIncomplete) {
              incomplete.push({
                client_id: c.client_id,
                name: c.name,
                record_id: h.record_id,
                date: h.date,
                treatment: h.treatment_provided
              });
            }
          });
        });
        setIncompleteRecords(incomplete.sort((a, b) => new Date(b.date).getTime() - new Date(a.date).getTime()));

        // 计算收入指标
        const today = new Date();
        today.setHours(0, 0, 0, 0);
        const transactions = transRes.data || [];

        let todayRevenueCalc = 0;
        let todayRechargeCalc = 0;

        transactions.forEach((tx: any) => {
          const txDate = new Date(tx.date);
          txDate.setHours(0, 0, 0, 0);
          const isToday = txDate.getTime() === today.getTime();

          if (isToday) {
            // 今日收入 = 今天的现金收入 + 今天的次卡销卡拆现
            if (tx.transaction_type === 'cash_payment' || tx.transaction_type === 'cash_received') {
              todayRevenueCalc += tx.amount || 0;
            }
            if (tx.transaction_type === 'times_card_cancellation') {
              todayRevenueCalc += tx.cash_amount || 0;
            }
            // 今日充值 = 今天所有充值金额
            if (tx.transaction_type === 'recharge') {
              todayRechargeCalc += tx.cash_amount || tx.amount || 0;
            }
          }
        });

        // 充值订货 = 所有客户未消费的储值余额 + 次卡未消费折算金额
        let rechargeBalanceCalc = 0;

        // 按客户汇总次卡充值记录，计算单次均价
        const timesRechargeByClient: Record<string, { totalCash: number; totalTimes: number }> = {};
        transactions.forEach((tx: any) => {
          const isTimesRecharge = tx.transaction_type === 'times_recharge' || (tx.times_count > 0 && tx.cash_amount > 0);
          if (isTimesRecharge) {
            if (!timesRechargeByClient[tx.client_id]) {
              timesRechargeByClient[tx.client_id] = { totalCash: 0, totalTimes: 0 };
            }
            timesRechargeByClient[tx.client_id].totalCash += tx.cash_amount || 0;
            timesRechargeByClient[tx.client_id].totalTimes += tx.times_count || 0;
          }
        });

        clients.forEach((c: any) => {
          // 储值余额（现金卡未消费）
          rechargeBalanceCalc += c.cash_card_balance || 0;
          // 次卡未消费折算金额 = 剩余次数 × 单次均价
          const remaining = c.times_card_balance || 0;
          if (remaining > 0) {
            const record = timesRechargeByClient[c.client_id];
            if (record && record.totalTimes > 0) {
              const unitPrice = record.totalCash / record.totalTimes;
              rechargeBalanceCalc += remaining * unitPrice;
            }
          }
        });

        setTodayRevenue(todayRevenueCalc);
        setRechargeBalance(rechargeBalanceCalc);
        setTodayRecharge(todayRechargeCalc);
      } catch (error) {
        console.error('加载数据失败', error);
      } finally {
        setLoading(false);
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
      setIncompleteRecords(incompleteRecords.filter(t => t.record_id !== selectedTask.record_id));
      alert('健康档案补全成功！');
    } catch (error) {
      alert('补全档案失败');
    }
  };

  if (loading || !aiData || !sysInfo) {
    return (
      <div className="p-8 flex items-center justify-center h-screen">
        <div className="text-center">
          <Loader2 className="w-12 h-12 text-emerald-600 animate-spin mx-auto mb-4" />
          <p className="text-slate-500">加载中...</p>
        </div>
      </div>
    );
  }

  const q = aiData.quota;
  const d = aiData.client_dynamics;
  const o = aiData.today_outreach;

  return (
    <div className="p-8 max-w-7xl mx-auto">
      {/* Header */}
      <div className="mb-6 flex justify-between items-end">
        <div>
          <h1 className="text-3xl font-black text-slate-800 tracking-tight">智能管理驾驶舱</h1>
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

      {/* TAB Navigation */}
      <div className="flex gap-2 mb-6 border-b border-slate-200">
        <button
          onClick={() => setTab('business')}
          className={`px-6 py-3 font-bold text-sm uppercase transition-all ${
            tab === 'business'
              ? 'text-emerald-600 border-b-2 border-emerald-600'
              : 'text-slate-500 hover:text-slate-700'
          }`}
        >
          <Activity className="w-4 h-4 inline mr-2" />
          基础业务
        </button>
        <button
          onClick={() => setTab('ai')}
          className={`px-6 py-3 font-bold text-sm uppercase transition-all ${
            tab === 'ai'
              ? 'text-emerald-600 border-b-2 border-emerald-600'
              : 'text-slate-500 hover:text-slate-700'
          }`}
        >
          <Brain className="w-4 h-4 inline mr-2" />
          AI 智能
        </button>
      </div>

      {/* TAB 1: Business Tab */}
      {tab === 'business' && (
        <div className="space-y-6">
          {/* KPI Row */}
          <div className="grid grid-cols-5 gap-3">
            <KPICard icon={Calendar} label="今日预约" value={0} unit="人" color="blue" />
            <KPICard icon={Users} label="客户总数" value={d.total_clients} unit="人" color="emerald" />
            <KPICard icon={TrendingUp} label="本周新增" value={d.new_this_week} unit="人" color="green" />
            <KPICard icon={AlertTriangle} label="沉默预警" value={d.silent_warning} unit="人" color="orange" onClick={() => navigate('/playbooks')} />
            <KPICard icon={AlertTriangle} label="流失预警" value={d.churn_risk} unit="人" color="red" onClick={() => navigate('/playbooks')} />
          </div>

          {/* Revenue Row */}
          <div className="grid grid-cols-4 gap-4">
            <div className="bg-white p-4 rounded-2xl shadow-sm border border-slate-100 flex flex-col justify-center">
              <span className="text-slate-500 font-bold text-xs uppercase">今日收入</span>
              <span className="text-2xl font-black text-emerald-600 mt-2">¥{todayRevenue.toFixed(2)}</span>
            </div>
            <div className="bg-white p-4 rounded-2xl shadow-sm border border-slate-100 flex flex-col justify-center">
              <span className="text-slate-500 font-bold text-xs uppercase" title="指未消费的充值金额">充值订货 <span className="text-slate-400 cursor-help">ⓘ</span></span>
              <span className="text-2xl font-black text-blue-600 mt-2">¥{rechargeBalance.toFixed(2)}</span>
            </div>
            <div className="bg-white p-4 rounded-2xl shadow-sm border border-slate-100 flex flex-col justify-center">
              <span className="text-slate-500 font-bold text-xs uppercase">今日充值</span>
              <span className="text-2xl font-black text-purple-600 mt-2">¥{todayRecharge.toFixed(2)}</span>
            </div>
            <div className="bg-white p-4 rounded-2xl shadow-sm border border-slate-100 flex flex-col justify-center">
              <span className="text-slate-500 font-bold text-xs uppercase">待完善档案</span>
              <span className="text-2xl font-black text-orange-600 mt-2">{incompleteRecords.length} 份</span>
            </div>
          </div>

          {/* Business Data Grid */}
          <div className="grid grid-cols-1 gap-6">
            {/* Service Records Maintenance */}
            <div className="bg-white rounded-2xl shadow-sm border border-slate-100 p-6">
              <h3 className="text-sm font-bold text-slate-500 uppercase mb-4 flex items-center">
                <AlertCircle className="w-4 h-4 mr-2" /> 档案维护
              </h3>
              <div className="space-y-4">
                <div>
                  <div className="flex justify-between text-xs mb-1">
                    <span className="text-slate-600 font-medium">待完善档案</span>
                    <span className={`font-bold ${incompleteRecords.length > 0 ? 'text-orange-600' : 'text-emerald-600'}`}>
                      {incompleteRecords.length} 份
                    </span>
                  </div>
                  <div className="w-full h-2 bg-slate-100 rounded-full overflow-hidden">
                    <div
                      className={incompleteRecords.length > 0 ? 'bg-orange-500' : 'bg-emerald-500'}
                      style={{ width: incompleteRecords.length > 0 ? '100%' : '0%' }}
                    />
                  </div>
                </div>
                <button
                  onClick={() => {
                    const elem = document.querySelector('[data-incomplete-records]');
                    if (elem) elem.scrollIntoView({ behavior: 'smooth' });
                  }}
                  className={`w-full py-2 text-xs font-bold rounded-lg transition-colors ${
                    incompleteRecords.length > 0
                      ? 'bg-orange-50 text-orange-600 border border-orange-200 hover:bg-orange-100'
                      : 'bg-emerald-50 text-emerald-600 border border-emerald-200'
                  }`}
                >
                  {incompleteRecords.length > 0 ? '立即补全' : '档案完善 ✓'}
                </button>
              </div>
            </div>
          </div>

          {/* Incomplete Records Section */}
          {incompleteRecords.length > 0 && (
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
                {incompleteRecords.slice(0, 5).map(task => (
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
        </div>
      )}

      {/* TAB 2: AI Tab */}
      {tab === 'ai' && (
        <div className="space-y-6">
          {/* AI Quota Row */}
          <div className="bg-white rounded-2xl shadow-sm border border-slate-100 p-6">
            <h3 className="text-sm font-bold text-slate-500 uppercase mb-6 flex items-center">
              <Brain className="w-4 h-4 mr-2" /> AI 配额使用
            </h3>
            <div className="grid grid-cols-3 gap-6">
              <div>
                <div className="flex justify-between text-sm mb-2">
                  <span className="text-slate-600 font-medium">专业分析</span>
                  <span className="text-slate-500">{q.analysis_used} / {q.analysis_limit === -1 ? '∞' : q.analysis_limit}</span>
                </div>
                <QuotaBar used={q.analysis_used} limit={q.analysis_limit} />
              </div>
              <div>
                <div className="flex justify-between text-sm mb-2">
                  <span className="text-slate-600 font-medium">方案生成</span>
                  <span className="text-slate-500">{q.plan_used} / {q.plan_limit === -1 ? '∞' : q.plan_limit}</span>
                </div>
                <QuotaBar used={q.plan_used} limit={q.plan_limit} />
              </div>
              <div>
                <div className="flex justify-between text-sm mb-2">
                  <span className="text-slate-600 font-medium">营销文案</span>
                  <span className="text-slate-500">{q.content_used} / {q.content_limit === -1 ? '∞' : q.content_limit}</span>
                </div>
                <QuotaBar used={q.content_used} limit={q.content_limit} />
              </div>
            </div>
          </div>

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

          {/* Playbook Reports + Recent Replies */}
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
              <div className="divide-y divide-slate-50 max-h-96 overflow-y-auto">
                {aiData.playbook_reports.length === 0 ? (
                  <div className="p-8 text-center text-slate-400 text-sm">暂无运营剧本</div>
                ) : (
                  aiData.playbook_reports.map((pb, i) => (
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
                  ))
                )}
              </div>
            </div>

            {/* Recent Replies */}
            <div className="bg-white rounded-2xl shadow-sm border border-slate-100 overflow-hidden">
              <div className="p-5 border-b border-slate-100">
                <h3 className="text-sm font-bold text-slate-500 uppercase flex items-center">
                  <MessageSquare className="w-4 h-4 mr-2" /> 最近客户回复
                </h3>
              </div>
              <div className="divide-y divide-slate-50 max-h-96 overflow-y-auto">
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

          {/* Quick Actions */}
          <div className="grid grid-cols-2 gap-6">
            <button
              onClick={() => navigate('/ai-analysis')}
              className="bg-gradient-to-r from-emerald-50 to-blue-50 border border-emerald-200 rounded-2xl p-6 text-left hover:shadow-md transition-shadow"
            >
              <Brain className="w-8 h-8 text-emerald-600 mb-2" />
              <h3 className="font-bold text-slate-800">深度分析</h3>
              <p className="text-sm text-slate-600 mt-1">针对客户进行专业分析和方案生成</p>
            </button>
            <button
              onClick={() => navigate('/playbooks')}
              className="bg-gradient-to-r from-purple-50 to-pink-50 border border-purple-200 rounded-2xl p-6 text-left hover:shadow-md transition-shadow"
            >
              <BookOpen className="w-8 h-8 text-purple-600 mb-2" />
              <h3 className="font-bold text-slate-800">运营管理</h3>
              <p className="text-sm text-slate-600 mt-1">管理运营剧本和营销任务</p>
            </button>
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
    blue: 'text-blue-600',
    green: 'text-green-600',
    emerald: 'text-emerald-600',
    orange: 'text-orange-500',
    red: 'text-red-500',
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
    emerald: 'text-emerald-600',
    blue: 'text-blue-600',
    orange: 'text-orange-500',
    red: 'text-red-500',
  };
  return (
    <div className="text-center">
      <div className={`text-2xl font-black ${colors[color] || ''}`}>{value}</div>
      <div className="text-xs text-slate-500 mt-1">{label}</div>
    </div>
  );
};

const QuotaBar = ({ used, limit }: { used: number; limit: number }) => {
  const unlimited = limit === -1;
  const pct = unlimited ? 0 : limit > 0 ? Math.min(100, (used / limit) * 100) : 0;
  const barColor = pct > 80 ? 'bg-orange-500' : 'bg-emerald-500';
  return (
    <>
      {!unlimited && (
        <div className="w-full h-2 bg-slate-100 rounded-full overflow-hidden">
          <div className={`h-full rounded-full transition-all ${barColor}`} style={{ width: `${pct}%` }} />
        </div>
      )}
      {unlimited && <div className="text-xs text-slate-500">不限额度</div>}
    </>
  );
};

export default UnifiedDashboard;
