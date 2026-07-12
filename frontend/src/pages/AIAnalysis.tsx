import { useState, useEffect } from 'react';
import axios from 'axios';
import { Brain, FileText, Loader2, Sparkles, ClipboardList, Send, MessageCircle, Smartphone } from 'lucide-react';
import { ReadOnlyButton } from '../components/ReadOnlyGuard';

const API = import.meta.env.VITE_API_URL || '';

interface Client { client_id: string; name: string; phone: string; primary_analysis_type?: string; }
interface ServiceRecord {
  record_id: string; client_id: string; date: string; symptoms: string[];
  description: string; treatment_provided: string; notes?: string;
}
interface Analysis {
  id: string; domain: string; primary_type: string; secondary_type?: string;
  confidence_score: number; ai_analysis_summary: string; ai_recommendations: any; assessed_at?: string;
}
interface Plan {
  id: string; analysis_id: string; plan_summary: string; status: string;
  in_store_services: any[]; home_care_advice: any[]; seasonal_notes: string;
  valid_until?: string; created_at?: string;
}
interface Terminology { staff_title: string; analysis_name: string; plan_name: string; }

const AIAnalysis = () => {
  const [clients, setClients] = useState<Client[]>([]);
  const [selectedClient, setSelectedClient] = useState<string>('');
  const [terminology, setTerminology] = useState<Terminology>({ staff_title: '技师', analysis_name: 'AI分析', plan_name: '服务方案' });
  const [symptoms, setSymptoms] = useState('');
  const [observations, setObservations] = useState('');
  const [analyzing, setAnalyzing] = useState(false);
  const [generatingPlan, setGeneratingPlan] = useState(false);

  const [latestAnalysis, setLatestAnalysis] = useState<Analysis | null>(null);
  const [analyses, setAnalyses] = useState<Analysis[]>([]);
  const [activePlan, setActivePlan] = useState<Plan | null>(null);
  const [, setPlans] = useState<Plan[]>([]);
  const [serviceRecords, setServiceRecords] = useState<ServiceRecord[]>([]);

  // 发送方案相关状态
  const [showSendDialog, setShowSendDialog] = useState(false);
  const [selectedPlan, setSelectedPlan] = useState<Plan | null>(null);
  const [sendChannel, setSendChannel] = useState<'wechat_rpa' | 'sms_api'>('wechat_rpa');
  const [customMessage, setCustomMessage] = useState('');
  const [sending, setSending] = useState(false);

  useEffect(() => {
    axios.get(`${API}/api/v1/clients/`).then(r => setClients(r.data)).catch(console.error);
    axios.get(`${API}/api/v1/config/info`).then(r => setTerminology(r.data.terminology)).catch(console.error);
  }, []);

  useEffect(() => {
    if (selectedClient) {
      axios.get(`${API}/api/v1/ai/analyses/${selectedClient}`).then(r => setAnalyses(r.data)).catch(console.error);
      axios.get(`${API}/api/v1/ai/analyses/${selectedClient}/latest`).then(r => setLatestAnalysis(r.data)).catch(() => setLatestAnalysis(null));
      axios.get(`${API}/api/v1/ai/plans/${selectedClient}`).then(r => {
        setPlans(r.data);
        setActivePlan(r.data.find((p: Plan) => p.status === 'active') || null);
      }).catch(console.error);
      // 获取历史服务记录
      axios.get(`${API}/api/v1/clients/${selectedClient}/records`).then(r => setServiceRecords(r.data)).catch(() => setServiceRecords([]));
    } else {
      setServiceRecords([]);
    }
  }, [selectedClient]);

  const handleAnalyze = async () => {
    // 如果有服务记录，允许不填症状直接分析
    if (!selectedClient) return;
    if (!symptoms.trim() && serviceRecords.length === 0) {
      alert('请录入客户状况或确保客户有历史服务记录');
      return;
    }
    setAnalyzing(true);
    try {
      const res = await axios.post(`${API}/api/v1/ai/analyze`, {
        client_id: selectedClient,
        symptoms: symptoms.trim() || '暂无新症状，请参考历史服务记录',
        observations,
      });
      if (res.data.success) {
        setLatestAnalysis(res.data.data);
        setAnalyses(prev => [res.data.data, ...prev]);
        setSymptoms(''); setObservations('');
      } else {
        alert(res.data.error || '分析失败');
      }
    } catch (e: any) {
      const errorMsg = e.response?.data?.error || e.response?.data?.detail || e.message || '分析失败，请稍后重试';
      alert(errorMsg);
    }
    setAnalyzing(false);
  };

  const handleGeneratePlan = async () => {
    if (!selectedClient || !latestAnalysis) return;
    setGeneratingPlan(true);
    try {
      const res = await axios.post(`${API}/api/v1/ai/plan/generate`, {
        client_id: selectedClient, analysis_id: latestAnalysis.id,
      });
      if (res.data.success) {
        setActivePlan(res.data.data);
        setPlans((prev: Plan[]) => [res.data.data, ...prev.map((p: Plan) => ({ ...p, status: p.status === 'active' ? 'superseded' : p.status }))]);
      } else { alert(res.data.error || '生成方案失败'); }
    } catch (e: any) {
      const errorMsg = e.response?.data?.error || e.response?.data?.detail || e.message || '生成方案失败，请稍后重试';
      alert(errorMsg);
    }
    setGeneratingPlan(false);
  };

  const handleSendPlan = (plan: Plan) => {
    setSelectedPlan(plan);
    setSendChannel('wechat_rpa');
    setCustomMessage('');
    setShowSendDialog(true);
  };

  const confirmSendPlan = async () => {
    if (!selectedPlan || !selectedClient) return;

    const client = clients.find(c => c.client_id === selectedClient);
    if (!client) {
      alert('客户信息不存在');
      return;
    }

    setSending(true);
    try {
      const res = await axios.post(`${API}/api/v1/ai/plans/${selectedPlan.id}/send`, {
        plan_id: selectedPlan.id,
        channel: sendChannel,
        recipient_phone: client.phone,
        message_content: customMessage || undefined,
      });
      if (res.data.success) {
        alert(res.data.message || '调理方案已加入发送队列');
        setShowSendDialog(false);
      } else {
        alert(res.data.error || '发送失败');
      }
    } catch (e: any) {
      alert(e.response?.data?.error || '发送失败');
    }
    setSending(false);
  };

  return (
    <div className="p-8 max-w-7xl mx-auto">
      <div className="mb-6">
        <h1 className="text-3xl font-black text-slate-800 tracking-tight flex items-center gap-2">
          <Brain className="w-8 h-8 text-emerald-600" /> {terminology.analysis_name}
        </h1>
        <p className="text-slate-500 mt-1">选择客户 → 录入症状 → AI 专业分析 → 生成{terminology.plan_name}</p>
      </div>

      {/* Client Selector */}
      <div className="bg-white rounded-2xl shadow-sm border border-slate-100 p-6 mb-6">
        <label className="block text-xs font-bold text-slate-500 uppercase mb-2">选择客户</label>
        <select value={selectedClient} onChange={e => setSelectedClient(e.target.value)}
          className="w-full px-4 py-3 bg-slate-50 border border-slate-200 rounded-xl text-sm font-medium focus:ring-2 focus:ring-emerald-500 outline-none">
          <option value="">-- 请选择客户 --</option>
          {clients.map(c => (
            <option key={c.client_id} value={c.client_id}>
              {c.name} ({c.phone}) {c.primary_analysis_type ? `· ${c.primary_analysis_type}` : ''}
            </option>
          ))}
        </select>
      </div>

      {selectedClient && (
        <div className="grid grid-cols-3 gap-6">
          {/* Left: Service History */}
          <div className="col-span-1 space-y-6">
            <div className="bg-white rounded-2xl shadow-sm border border-slate-100 overflow-hidden">
              <div className="p-4 border-b border-slate-100 bg-slate-50/50 flex justify-between items-center">
                <h3 className="text-sm font-bold text-slate-500 uppercase">历史服务记录</h3>
                {serviceRecords.length > 0 && (
                  <span className="text-xs bg-emerald-50 text-emerald-600 px-2 py-1 rounded-full">{serviceRecords.length}条</span>
                )}
              </div>
              {serviceRecords.length === 0 ? (
                <div className="p-8 text-center">
                  <FileText className="w-12 h-12 text-slate-300 mx-auto mb-2" />
                  <p className="text-sm text-slate-400">暂无服务记录</p>
                  <p className="text-xs text-slate-400 mt-1">请先为客户添加服务记录后再进行分析</p>
                </div>
              ) : (
                <div className="divide-y divide-slate-50 max-h-96 overflow-y-auto">
                  {serviceRecords.map((rec: ServiceRecord) => (
                    <div key={rec.record_id} className="px-5 py-3 hover:bg-slate-50">
                      <div className="flex justify-between items-start mb-1">
                        <span className="font-medium text-sm text-slate-700">
                          {rec.date ? new Date(rec.date).toLocaleDateString('zh-CN') : '未知日期'}
                        </span>
                      </div>
                      <div className="text-sm text-slate-600">
                        <span className="text-slate-400">症状：</span>
                        {Array.isArray(rec.symptoms) ? rec.symptoms.join(', ') : rec.symptoms}
                      </div>
                      <div className="text-sm text-slate-600">
                        <span className="text-slate-400">服务：</span>
                        {rec.treatment_provided || '无'}
                      </div>
                      {rec.description && (
                        <div className="text-xs text-slate-500 mt-1">
                          <span className="text-slate-400">描述：</span>{rec.description}
                        </div>
                      )}
                      {rec.notes && (
                        <div className="text-xs text-slate-500 mt-1">
                          <span className="text-slate-400">备注：</span>{rec.notes}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Analysis History */}
            {analyses.length > 0 && (
              <div className="bg-white rounded-2xl shadow-sm border border-slate-100 overflow-hidden">
                <div className="p-4 border-b border-slate-100 bg-slate-50/50">
                  <h3 className="text-sm font-bold text-slate-500 uppercase">历史分析记录</h3>
                </div>
                <div className="divide-y divide-slate-50 max-h-64 overflow-y-auto">
                  {analyses.map(a => (
                    <div key={a.id} className="px-5 py-3 flex justify-between items-center hover:bg-slate-50 cursor-pointer"
                      onClick={() => setLatestAnalysis(a)}>
                      <div>
                        <span className="font-medium text-sm text-slate-700">{a.primary_type}</span>
                        {a.secondary_type && <span className="text-xs text-slate-400 ml-2">兼{a.secondary_type}</span>}
                      </div>
                      <div className="flex items-center gap-2">
                        <span className="text-xs text-slate-400">{a.assessed_at?.slice(0, 10)}</span>
                        <span className="text-xs bg-emerald-50 text-emerald-600 px-2 py-0.5 rounded-full">{Math.round(a.confidence_score * 100)}%</span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Middle: Input Form */}
          <div className="col-span-1 space-y-6">
            {/* Input Form */}
            <div className="bg-white rounded-2xl shadow-sm border border-slate-100 p-6">
              <h3 className="text-sm font-bold text-slate-500 uppercase mb-4">录入客户状况</h3>
              {serviceRecords.length > 0 && (
                <div className="mb-4 p-3 bg-emerald-50 border border-emerald-200 rounded-xl">
                  <p className="text-xs text-emerald-700">
                    <span className="font-bold">提示：</span>
                    客户有 {serviceRecords.length} 条历史服务记录，可直接点击"开始 AI 分析"，系统将结合历史记录进行分析。
                  </p>
                </div>
              )}
              <div className="space-y-4">
                <div>
                  <label className="block text-xs font-bold text-slate-500 mb-1">客户自述（症状/需求）{serviceRecords.length === 0 && '*'}</label>
                  <textarea rows={4} value={symptoms} onChange={e => setSymptoms(e.target.value)}
                    className="w-full px-4 py-3 bg-slate-50 border border-slate-100 rounded-xl text-sm resize-none focus:ring-2 focus:ring-emerald-500 outline-none"
                    placeholder={serviceRecords.length > 0 ? "可补充新症状，或直接点击分析使用历史记录..." : "如：最近总是怕冷，手脚冰凉，睡眠不好，肩颈酸痛..."} />
                </div>
                <div>
                  <label className="block text-xs font-bold text-slate-500 mb-1">{terminology.staff_title}观察（可选）</label>
                  <textarea rows={2} value={observations} onChange={e => setObservations(e.target.value)}
                    className="w-full px-4 py-3 bg-slate-50 border border-slate-100 rounded-xl text-sm resize-none focus:ring-2 focus:ring-emerald-500 outline-none"
                    placeholder="如：面色苍白，舌苔白腻..." />
                </div>
                <ReadOnlyButton>
                  <button onClick={handleAnalyze} disabled={analyzing || (serviceRecords.length === 0 && !symptoms.trim())}
                    className="w-full py-3 bg-emerald-600 hover:bg-emerald-700 disabled:bg-slate-300 text-white rounded-xl font-bold transition-all flex items-center justify-center gap-2">
                    {analyzing ? <><Loader2 className="w-4 h-4 animate-spin" /> AI 分析中...</> : <><Sparkles className="w-4 h-4" /> 开始 AI {terminology.analysis_name}</>}
                  </button>
                </ReadOnlyButton>
              </div>
            </div>
          </div>

          {/* Right: Results */}
          <div className="col-span-1 space-y-6">
            {/* Latest Analysis Result */}
            {latestAnalysis && (
              <div className="bg-white rounded-2xl shadow-sm border border-emerald-100 p-6">
                <div className="flex justify-between items-start mb-4">
                  <div>
                    <h3 className="text-lg font-bold text-slate-800">{latestAnalysis.primary_type}</h3>
                    {latestAnalysis.secondary_type && <span className="text-sm text-slate-500">兼 {latestAnalysis.secondary_type}</span>}
                  </div>
                  <span className="text-sm bg-emerald-50 text-emerald-700 px-3 py-1 rounded-full font-bold border border-emerald-200">
                    置信度 {Math.round(latestAnalysis.confidence_score * 100)}%
                  </span>
                </div>
                <p className="text-sm text-slate-600 leading-relaxed mb-4">{latestAnalysis.ai_analysis_summary}</p>
                <div className="grid grid-cols-3 gap-3 text-xs">
                  <div className="bg-blue-50 rounded-xl p-3">
                    <div className="font-bold text-blue-700 mb-1">关键特征</div>
                    {(latestAnalysis.ai_recommendations?.key_symptoms || []).map((s: string, i: number) => (
                      <div key={i} className="text-blue-600">· {s}</div>
                    ))}
                  </div>
                  <div className="bg-orange-50 rounded-xl p-3">
                    <div className="font-bold text-orange-700 mb-1">风险因素</div>
                    {(latestAnalysis.ai_recommendations?.risk_factors || []).map((s: string, i: number) => (
                      <div key={i} className="text-orange-600">· {s}</div>
                    ))}
                  </div>
                  <div className="bg-red-50 rounded-xl p-3">
                    <div className="font-bold text-red-700 mb-1">禁忌事项</div>
                    {(latestAnalysis.ai_recommendations?.contraindications || []).map((s: string, i: number) => (
                      <div key={i} className="text-red-600">· {s}</div>
                    ))}
                  </div>
                </div>
                <ReadOnlyButton>
                  <button onClick={handleGeneratePlan} disabled={generatingPlan}
                    className="w-full mt-4 py-3 bg-blue-600 hover:bg-blue-700 disabled:bg-slate-300 text-white rounded-xl font-bold transition-all flex items-center justify-center gap-2">
                    {generatingPlan ? <><Loader2 className="w-4 h-4 animate-spin" /> 生成方案中...</> : <><FileText className="w-4 h-4" /> 生成{terminology.plan_name}</>}
                  </button>
                </ReadOnlyButton>
              </div>
            )}

            {/* Active Plan */}
            {activePlan && (
              <div className="bg-white rounded-2xl shadow-sm border border-blue-100 p-6">
                <div className="flex justify-between items-center mb-4">
                  <h3 className="text-sm font-bold text-slate-500 uppercase flex items-center gap-2">
                    <ClipboardList className="w-4 h-4" /> 当前{terminology.plan_name}
                  </h3>
                  <span className="text-xs text-blue-600 bg-blue-50 px-2 py-0.5 rounded-full">
                    有效至 {activePlan.valid_until?.slice(0, 10)}
                  </span>
                </div>
                <p className="text-sm text-slate-600 leading-relaxed mb-4">{activePlan.plan_summary}</p>

                {/* In-store Services */}
                <div className="mb-3">
                  <div className="text-xs font-bold text-slate-500 mb-2">店内推荐项目</div>
                  <div className="space-y-2">
                    {(activePlan.in_store_services || []).map((s: any, i: number) => (
                      <div key={i} className="bg-emerald-50 rounded-xl p-3 text-sm">
                        <span className="font-bold text-emerald-700">{s.name}</span>
                        {s.frequency && <span className="text-emerald-600 ml-2">· {s.frequency}</span>}
                        {s.reason && <p className="text-xs text-emerald-600/80 mt-1">{s.reason}</p>}
                      </div>
                    ))}
                  </div>
                </div>

                {/* Home Care */}
                <div className="mb-3">
                  <div className="text-xs font-bold text-slate-500 mb-2">居家护理建议</div>
                  <div className="space-y-2">
                    {(activePlan.home_care_advice || []).map((a: any, i: number) => (
                      <div key={i} className="bg-blue-50 rounded-xl p-3 text-sm">
                        <span className="font-bold text-blue-700">{a.category}</span>
                        <p className="text-xs text-blue-600/80 mt-1">{a.advice}</p>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Seasonal Notes */}
                {activePlan.seasonal_notes && (
                  <div className="bg-amber-50 rounded-xl p-3 text-sm">
                    <span className="font-bold text-amber-700">季节提醒：</span>
                    <span className="text-amber-600">{activePlan.seasonal_notes}</span>
                  </div>
                )}

                {/* Send Button */}
                <ReadOnlyButton>
                  <button onClick={() => handleSendPlan(activePlan)}
                    className="w-full mt-4 py-3 bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl font-bold transition-all flex items-center justify-center gap-2">
                    <Send className="w-4 h-4" /> 一键发送{terminology.plan_name}
                  </button>
                </ReadOnlyButton>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Send Plan Dialog */}
      {showSendDialog && selectedPlan && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-2xl shadow-xl max-w-lg w-full mx-4 overflow-hidden">
            <div className="p-6 border-b border-slate-100">
              <h3 className="text-lg font-bold text-slate-800 flex items-center gap-2">
                <Send className="w-5 h-5 text-emerald-600" />
                发送{terminology.plan_name}给客户
              </h3>
            </div>

            <div className="p-6 space-y-4">
              {/* Client Info */}
              <div className="bg-slate-50 rounded-xl p-4">
                <div className="text-sm text-slate-500 mb-1">发送给</div>
                <div className="font-bold text-slate-800">
                  {clients.find(c => c.client_id === selectedClient)?.name || '未知客户'}
                </div>
                <div className="text-sm text-slate-600">
                  {clients.find(c => c.client_id === selectedClient)?.phone}
                </div>
              </div>

              {/* Channel Selection */}
              <div>
                <label className="block text-xs font-bold text-slate-500 uppercase mb-2">发送渠道</label>
                <div className="grid grid-cols-2 gap-3">
                  <button onClick={() => setSendChannel('wechat_rpa')}
                    className={`p-4 rounded-xl border-2 transition-all flex items-center justify-center gap-2 ${
                      sendChannel === 'wechat_rpa'
                        ? 'border-emerald-500 bg-emerald-50 text-emerald-700'
                        : 'border-slate-200 hover:border-slate-300'
                    }`}>
                    <MessageCircle className="w-5 h-5" />
                    <span className="font-bold">微信 RPA</span>
                  </button>
                  <button onClick={() => setSendChannel('sms_api')}
                    className={`p-4 rounded-xl border-2 transition-all flex items-center justify-center gap-2 ${
                      sendChannel === 'sms_api'
                        ? 'border-emerald-500 bg-emerald-50 text-emerald-700'
                        : 'border-slate-200 hover:border-slate-300'
                    }`}>
                    <Smartphone className="w-5 h-5" />
                    <span className="font-bold">短信 API</span>
                  </button>
                </div>
              </div>

              {/* Custom Message (Optional) */}
              <div>
                <label className="block text-xs font-bold text-slate-500 mb-1">
                  自定义消息内容（可选，不填则使用方案摘要）
                </label>
                <textarea rows={4} value={customMessage} onChange={e => setCustomMessage(e.target.value)}
                  className="w-full px-4 py-3 bg-slate-50 border border-slate-200 rounded-xl text-sm resize-none focus:ring-2 focus:ring-emerald-500 outline-none"
                  placeholder="请输入要发送给客户的消息内容..." />
              </div>

              {/* Preview */}
              <div className="bg-amber-50 border border-amber-200 rounded-xl p-3">
                <div className="text-xs font-bold text-amber-700 mb-1">预览</div>
                <div className="text-xs text-amber-800 leading-relaxed">
                  {clients.find(c => c.client_id === selectedClient)?.name}您好，这是为您定制的调理方案：
                  {'\n\n'}
                  <span className="text-amber-600">
                    {customMessage || selectedPlan.plan_summary || '（方案内容为空）'}
                  </span>
                  {'\n\n'}
                  如有任何疑问，请随时联系我们。
                </div>
              </div>
            </div>

            <div className="p-4 border-t border-slate-100 flex gap-3 bg-slate-50">
              <button onClick={() => setShowSendDialog(false)} disabled={sending}
                className="flex-1 py-3 bg-white border border-slate-200 hover:bg-slate-100 text-slate-700 rounded-xl font-bold transition-all">
                取消
              </button>
              <button onClick={confirmSendPlan} disabled={sending}
                className="flex-1 py-3 bg-emerald-600 hover:bg-emerald-700 disabled:bg-slate-400 text-white rounded-xl font-bold transition-all flex items-center justify-center gap-2">
                {sending ? <><Loader2 className="w-4 h-4 animate-spin" /> 发送中...</> : <><Send className="w-4 h-4" /> 确认发送</>}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default AIAnalysis;
