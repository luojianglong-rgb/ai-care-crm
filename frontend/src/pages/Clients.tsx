import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Plus, FileText, X, ClipboardList, Calendar, Wallet, Brain, Activity, MessageSquare, Users, Download } from 'lucide-react';
import VoiceInputButton from '../components/VoiceInputButton';
import { ReadOnlyButton } from '../components/ReadOnlyGuard';

const API = import.meta.env.VITE_API_URL || '';

interface HealthRecord {
  record_id?: string;
  date: string;
  symptoms: string[];
  description: string;
  treatment_provided: string;
  notes?: string;
  deduct_times?: number;
  deduct_cash?: number;
}

interface ClientProfile {
  client_id: string;
  name: string;
  phone: string;
  gender: string;
  age_group: string;
  birth_date: string;
  preferences: string[];
  times_card_balance: number;
  cash_card_balance: number;
  wechat_alias?: string;
  health_history: HealthRecord[];
}

const lifecycleLabels: Record<string, { text: string; color: string }> = {
  new: { text: '新客', color: 'bg-blue-100 text-blue-700' },
  active: { text: '活跃', color: 'bg-emerald-100 text-emerald-700' },
  silent: { text: '沉默', color: 'bg-orange-100 text-orange-700' },
  churn_risk: { text: '流失预警', color: 'bg-red-100 text-red-700' },
};
const intentLabels: Record<string, { text: string; color: string }> = {
  symptom_improved: { text: '症状好转', color: 'text-emerald-600 bg-emerald-50' },
  symptom_persists: { text: '症状持续', color: 'text-orange-600 bg-orange-50' },
  want_booking: { text: '想预约', color: 'text-blue-600 bg-blue-50' },
  price_inquiry: { text: '询价', color: 'text-purple-600 bg-purple-50' },
  general_chat: { text: '普通回复', color: 'text-slate-600 bg-slate-50' },
  negative: { text: '负面反馈', color: 'text-red-600 bg-red-50' },
};
const taskStatusLabels: Record<string, { text: string; color: string }> = {
  pending_approval: { text: '待审批', color: 'text-orange-600 bg-orange-50' },
  queued: { text: '排队中', color: 'text-blue-600 bg-blue-50' },
  sent: { text: '已发送', color: 'text-emerald-600 bg-emerald-50' },
  failed: { text: '失败', color: 'text-red-600 bg-red-50' },
  rejected: { text: '已驳回', color: 'text-slate-600 bg-slate-50' },
};

const Clients = () => {
  const [clients, setClients] = useState<ClientProfile[]>([]);

  const [search, setSearch] = useState('');

  // 弹窗状态
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingClientId, setEditingClientId] = useState<string | null>(null);
  const [isHealthModalOpen, setIsHealthModalOpen] = useState(false);
  const [selectedClient, setSelectedClient] = useState<ClientProfile | null>(null);
  const [detailTab, setDetailTab] = useState<'health' | 'analysis' | 'lifecycle' | 'outreach' | 'replies'>('health');

  // 新Tab数据
  const [analyses, setAnalyses] = useState<any[]>([]);
  const [lifecycle, setLifecycle] = useState<any>(null);
  const [outreachTasks, setOutreachTasks] = useState<any[]>([]);
  const [replies, setReplies] = useState<any[]>([]);

  // 表单状态
  const [formData, setFormData] = useState({
    name: '', phone: '', gender: '女', birth_date: '', age_group: '', preferences: '', wechat_alias: '', times_card_balance: 0, cash_card_balance: 0
  });
  const [newRecord, setNewRecord] = useState({ symptoms: '', description: '', treatment_provided: '', notes: '', deduct_times: 0, deduct_cash: 0 });
  const [deductType, setDeductType] = useState<'times' | 'cash'>('times');
  const [serviceItems, setServiceItems] = useState<any[]>([]);

  const fetchClients = async () => {
    try {
      const [clientsRes, servicesRes] = await Promise.all([
        axios.get(`${API}/api/v1/clients/`),
        axios.get(`${API}/api/v1/services/`)
      ]);
      setClients(clientsRes.data);
      setServiceItems(servicesRes.data);
    } catch (error) {
      console.error('获取客户列表失败', error);
    }
  };

  useEffect(() => { fetchClients(); }, []);

  const fetchClientDetails = async (clientId: string) => {
    try {
      const [aRes, lcRes, taskRes, repRes] = await Promise.all([
        axios.get(`${API}/api/v1/ai/analyses/${clientId}`).catch(() => ({ data: [] })),
        axios.get(`${API}/api/v1/playbooks/lifecycle/client/${clientId}`).catch(() => ({ data: null })),
        axios.get(`${API}/api/v1/campaigns/tasks?client_id=${clientId}&limit=50`).catch(() => ({ data: [] })),
        axios.get(`${API}/api/v1/replies/?client_id=${clientId}&limit=50`).catch(() => ({ data: [] })),
      ]);
      setAnalyses(aRes.data || []);
      setLifecycle(lcRes.data);
      setOutreachTasks(taskRes.data || []);
      setReplies(repRes.data || []);
    } catch (e) { console.error('加载客户详情失败', e); }
  };

  const openCreateModal = () => {
    setEditingClientId(null);
    setFormData({ name: '', phone: '', gender: '女', birth_date: '', age_group: '', preferences: '', wechat_alias: '', times_card_balance: 0, cash_card_balance: 0 });
    setIsModalOpen(true);
  };

  const openEditModal = (client: ClientProfile) => {
    setEditingClientId(client.client_id);
    setFormData({
      name: client.name, phone: client.phone, gender: client.gender,
      birth_date: client.birth_date || '', age_group: client.age_group,
      preferences: (client.preferences || []).join(', '),
      wechat_alias: client.wechat_alias || '',
      times_card_balance: client.times_card_balance, cash_card_balance: client.cash_card_balance
    });
    setIsModalOpen(true);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const payload = {
        ...formData,
        preferences: formData.preferences.split(',').map(p => p.trim()).filter(p => p),
      };
      if (editingClientId) {
        await axios.put(`${API}/api/v1/clients/${editingClientId}`, payload);
      } else {
        await axios.post(`${API}/api/v1/clients/`, { ...payload, times_card_balance: 0, cash_card_balance: 0 });
      }
      setIsModalOpen(false);
      fetchClients();
    } catch (error) { alert(editingClientId ? '修改失败' : '添加失败'); }
  };

  const handleDeleteClient = async (clientId: string, name: string) => {
    if (!confirm(`确定要删除客户「${name}」吗？此操作不可撤销。`)) return;
    try {
      await axios.delete(`${API}/api/v1/clients/${clientId}`);
      fetchClients();
    } catch (error) { alert('删除失败'); }
  };

  const handleExport = async () => {
    try {
      const response = await axios.get(`${API}/api/v1/clients/export/excel`, { responseType: 'blob' });
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `客户档案_${new Date().toISOString().slice(0,10)}.xlsx`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch (error: any) {
      // 解析 Blob 错误响应
      if (error.response?.data instanceof Blob) {
        const text = await error.response.data.text();
        try {
          const json = JSON.parse(text);
          alert(json.detail || '导出失败');
        } catch {
          alert('导出失败');
        }
      } else {
        alert(error.response?.data?.detail || '导出失败');
      }
    }
  };

  // 根据出生日期计算年龄段
  const calculateAgeGroup = (birthDate: string) => {
    if (!birthDate) return '';
    const birth = new Date(birthDate);
    const now = new Date();
    const age = now.getFullYear() - birth.getFullYear();
    const monthDiff = now.getMonth() - birth.getMonth();
    const actualAge = monthDiff < 0 || (monthDiff === 0 && now.getDate() < birth.getDate()) ? age - 1 : age;

    if (actualAge < 20) return '20 岁以下';
    if (actualAge < 30) return '20-30';
    if (actualAge < 40) return '30-40';
    if (actualAge < 50) return '40-50';
    if (actualAge < 60) return '50-60';
    return '60 岁以上';
  };


  const handleAddRecord = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedClient) return;
    try {
      const payload = {
        symptoms: newRecord.symptoms.split(',').map(s => s.trim()).filter(s => s),
        description: newRecord.description,
        treatment_provided: newRecord.treatment_provided,
        notes: newRecord.notes,
        deduct_times: newRecord.deduct_times,
        deduct_cash: newRecord.deduct_cash,
        date: new Date().toISOString()
      };
      await axios.post(`${API}/api/v1/clients/${selectedClient.client_id}/records`, payload);
      setNewRecord({ symptoms: '', description: '', treatment_provided: '', notes: '', deduct_times: 0, deduct_cash: 0 });
      const response = await axios.get(`${API}/api/v1/clients/${selectedClient.client_id}`);
      setSelectedClient(response.data);
      fetchClients();
    } catch (error) { alert('添加失败'); }
  };

  return (
    <div className="p-8">
      <div className="flex justify-between items-center mb-8">
        <div>
          <h1 className="text-2xl font-bold text-slate-800 tracking-tight">客户档案管理</h1>
          <p className="text-slate-500 text-sm mt-1">管理客户信息、消费卡包及健康档案</p>
        </div>
        <div className="flex gap-2">
          <button onClick={handleExport} className="bg-blue-600 hover:bg-blue-700 text-white px-5 py-2.5 rounded-xl flex items-center font-bold transition-all shadow-lg shadow-blue-100">
            <Download className="w-5 h-5 mr-2" /> 导出 Excel
          </button>
          <ReadOnlyButton>
            <button onClick={openCreateModal} className="bg-emerald-600 hover:bg-emerald-700 text-white px-5 py-2.5 rounded-xl flex items-center font-bold transition-all shadow-lg shadow-emerald-100">
              <Plus className="w-5 h-5 mr-2" /> 新增客户
            </button>
          </ReadOnlyButton>
        </div>
      </div>

      {/* 搜索栏 */}
      <div className="mb-4">
        <input value={search} onChange={e => setSearch(e.target.value)}
          className="w-full max-w-md px-4 py-2.5 bg-white border border-slate-200 rounded-xl text-sm focus:ring-2 focus:ring-emerald-500 outline-none"
          placeholder="搜索客户姓名或手机号..." />
      </div>

      <div className="bg-white rounded-2xl shadow-sm border border-slate-100 overflow-hidden">
        <table className="w-full text-left border-collapse">
          <thead>
            <tr className="bg-slate-50/50 border-b border-slate-100 text-slate-500 text-xs uppercase tracking-wider">
              <th className="p-5 font-bold">客户基本信息</th>
              <th className="p-5 font-bold text-center">次卡余额</th>
              <th className="p-5 font-bold text-center">储值余额</th>
              <th className="p-5 font-bold text-right">操作</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-50">
            {clients.filter(c => !search || c.name.includes(search) || c.phone.includes(search)).map((client) => (
              <tr key={client.client_id} className="hover:bg-slate-50/50 transition-colors group">
                <td className="p-5">
                  <div className="flex items-center">
                    <div className="w-11 h-11 rounded-full bg-emerald-100 text-emerald-700 flex items-center justify-center font-bold mr-4 text-lg">
                      {client.name.charAt(0)}
                    </div>
                    <div>
                      <div className="font-bold text-slate-800">{client.name}</div>
                      <div className="text-xs text-slate-500 font-medium">{client.phone} · {client.gender} · {client.birth_date || client.age_group}</div>
                    </div>
                  </div>
                </td>
                <td className="p-5 text-center">
                  <span className={`px-3 py-1 rounded-full text-xs font-bold ${client.times_card_balance > 0 ? 'bg-orange-50 text-orange-600' : 'bg-slate-100 text-slate-400'}`}>
                    {client.times_card_balance} 次
                  </span>
                </td>
                <td className="p-5 text-center">
                  <span className={`px-3 py-1 rounded-full text-xs font-bold ${client.cash_card_balance > 0 ? 'bg-blue-50 text-blue-600' : 'bg-slate-100 text-slate-400'}`}>
                    ¥{client.cash_card_balance.toFixed(2)}
                  </span>
                </td>
                <td className="p-5 text-right flex gap-2 justify-end">
                  <button onClick={() => {setSelectedClient(client); setDetailTab('health'); fetchClientDetails(client.client_id); setIsHealthModalOpen(true);}} className="text-emerald-600 font-bold text-sm bg-emerald-50 hover:bg-emerald-100 px-3 py-2 rounded-xl transition-all inline-flex items-center">
                    <FileText className="w-4 h-4 mr-1" /> 档案
                  </button>
                  <button onClick={() => openEditModal(client)} className="text-blue-600 font-bold text-sm bg-blue-50 hover:bg-blue-100 px-3 py-2 rounded-xl transition-all opacity-0 group-hover:opacity-100">
                    编辑
                  </button>
                  <button onClick={() => handleDeleteClient(client.client_id, client.name)} className="text-red-600 font-bold text-sm bg-red-50 hover:bg-red-100 px-3 py-2 rounded-xl transition-all opacity-0 group-hover:opacity-100">
                    删除
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* 新增客户弹窗 */}
      {isModalOpen && (
        <div className="fixed inset-0 bg-slate-900/60 backdrop-blur-sm flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-3xl shadow-2xl w-full max-w-lg overflow-hidden animate-in fade-in zoom-in duration-200">
            <div className="p-8 border-b border-slate-100 flex justify-between items-center">
              <h2 className="text-2xl font-bold text-slate-800">{editingClientId ? '修改客户信息' : '开通客户档案'}</h2>
              <X onClick={() => setIsModalOpen(false)} className="w-6 h-6 text-slate-400 cursor-pointer hover:text-slate-600" />
            </div>
            <form onSubmit={handleSubmit} className="p-8 space-y-5">
              <div className="grid grid-cols-2 gap-4">
                <div className="col-span-1">
                  <label className="block text-xs font-bold text-slate-500 uppercase mb-2">客户姓名</label>
                  <input required value={formData.name} onChange={e => setFormData({...formData, name: e.target.value})} className="w-full px-4 py-3 bg-slate-50 border border-slate-100 rounded-2xl focus:ring-2 focus:ring-emerald-500 outline-none font-medium" />
                </div>
                <div className="col-span-1">
                  <label className="block text-xs font-bold text-slate-500 uppercase mb-2">手机号码</label>
                  <input required value={formData.phone} onChange={e => setFormData({...formData, phone: e.target.value})} className="w-full px-4 py-3 bg-slate-50 border border-slate-100 rounded-2xl focus:ring-2 focus:ring-emerald-500 outline-none font-medium" />
                </div>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-bold text-slate-500 uppercase mb-2">性别</label>
                  <select value={formData.gender} onChange={e => setFormData({...formData, gender: e.target.value})} className="w-full px-4 py-3 bg-slate-50 border border-slate-100 rounded-2xl focus:ring-2 focus:ring-emerald-500 outline-none font-medium">
                    <option value="女">女</option>
                    <option value="男">男</option>
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-bold text-slate-500 uppercase mb-2">出生年月</label>
                  <input type="date" value={formData.birth_date} onChange={e => {
                    const birthDate = e.target.value;
                    setFormData({...formData, birth_date: birthDate, age_group: calculateAgeGroup(birthDate)});
                  }} className="w-full px-4 py-3 bg-slate-50 border border-slate-100 rounded-2xl focus:ring-2 focus:ring-emerald-500 outline-none font-medium" />
                </div>
              </div>
              <div>
                <label className="block text-xs font-bold text-slate-500 uppercase mb-2">消费偏好 (逗号分隔)</label>
                <input value={formData.preferences} onChange={e => setFormData({...formData, preferences: e.target.value})} className="w-full px-4 py-3 bg-slate-50 border border-slate-100 rounded-2xl focus:ring-2 focus:ring-emerald-500 outline-none font-medium" placeholder="如：精油 SPA, 肩颈疏通" />
              </div>
              <div>
                <label className="block text-xs font-bold text-slate-500 uppercase mb-2">微信别名</label>
                <input value={formData.wechat_alias} onChange={e => setFormData({...formData, wechat_alias: e.target.value})} className="w-full px-4 py-3 bg-slate-50 border border-slate-100 rounded-2xl focus:ring-2 focus:ring-emerald-500 outline-none font-medium" placeholder="客户在微信中的昵称或备注（用于自动发送）" />
                <p className="text-xs text-slate-400 mt-1">💡 用于微信 RPA 自动发送时匹配联系人，建议设置为客户微信昵称或您给客户的备注</p>
              </div>
              {!editingClientId && (
                <div className="bg-slate-50 p-4 rounded-2xl border border-slate-100">
                  <p className="text-xs text-slate-500 font-bold">初始卡包金额将由财务收银模块统一管理，新建档案时默认设为 0</p>
                </div>
              )}
              <button type="submit" className="w-full py-4 bg-emerald-600 hover:bg-emerald-700 text-white rounded-2xl font-bold text-lg shadow-xl shadow-emerald-100 transition-all">
                {editingClientId ? '保存修改' : '确认创建档案'}
              </button>
            </form>
          </div>
        </div>
      )}

      {/* 综合管理弹窗 */}
      {isHealthModalOpen && selectedClient && (
        <div className="fixed inset-0 bg-slate-900/80 backdrop-blur-md flex items-center justify-center z-50 p-6">
          <div className="bg-white rounded-[2rem] shadow-2xl w-full max-w-6xl max-h-[90vh] overflow-hidden flex flex-col">
            <div className="p-8 border-b border-slate-100 flex justify-between items-center bg-slate-50/30">
              <div className="flex items-center gap-6">
                <div className="w-16 h-16 rounded-3xl bg-emerald-600 text-white flex items-center justify-center font-bold text-2xl shadow-xl shadow-emerald-100">
                  {selectedClient.name.charAt(0)}
                </div>
                <div>
                  <h2 className="text-2xl font-black text-slate-800">{selectedClient.name} <span className="text-slate-400 font-normal ml-2">#{selectedClient.client_id.slice(0,8)}</span></h2>
                  <div className="flex gap-4 mt-2">
                    <div className="flex items-center bg-orange-50 text-orange-600 px-3 py-1.5 rounded-xl border border-orange-100">
                      <Wallet className="w-4 h-4 mr-2" /> <span className="font-black mr-2">{selectedClient.times_card_balance}</span> 次卡剩余
                    </div>
                    <div className="flex items-center bg-blue-50 text-blue-600 px-3 py-1.5 rounded-xl border border-blue-100">
                      <Wallet className="w-4 h-4 mr-2" /> <span className="font-black mr-2">¥{selectedClient.cash_card_balance.toFixed(2)}</span> 账户余额
                    </div>
                  </div>
                </div>
              </div>
              <X onClick={() => setIsHealthModalOpen(false)} className="w-10 h-10 text-slate-300 cursor-pointer hover:text-slate-500 p-2" />
            </div>

            {/* Tab Navigation */}
            <div className="flex gap-1 px-8 pt-4 border-b border-slate-100 bg-white">
              {[
                { key: 'health', icon: Calendar, label: '健康档案' },
                { key: 'analysis', icon: Brain, label: '专业分析' },
                { key: 'lifecycle', icon: Users, label: '生命周期' },
                { key: 'outreach', icon: Activity, label: '触达记录' },
                { key: 'replies', icon: MessageSquare, label: '回复记录' },
              ].map(t => (
                <button key={t.key} onClick={() => setDetailTab(t.key as any)}
                  className={`px-4 py-2.5 text-sm font-bold flex items-center gap-1.5 border-b-2 transition-colors ${
                    detailTab === t.key ? 'text-emerald-600 border-emerald-600' : 'text-slate-400 border-transparent hover:text-slate-600'
                  }`}>
                  <t.icon className="w-4 h-4" /> {t.label}
                </button>
              ))}
            </div>

            <div className="flex-1 overflow-hidden">
              {/* TAB: 健康档案 */}
              {detailTab === 'health' && (
                <div className="flex h-full">
                  <div className="w-2/3 p-8 overflow-y-auto bg-slate-50/30">
                    <h3 className="text-sm font-black text-slate-400 uppercase tracking-widest mb-8 flex items-center">
                      <Calendar className="w-5 h-5 mr-3" /> 调理历史轨迹
                    </h3>
                    <div className="space-y-8 relative before:absolute before:left-3 before:top-2 before:bottom-2 before:w-0.5 before:bg-slate-200">
                      {selectedClient.health_history.map((record, i) => (
                        <div key={i} className="relative pl-12">
                          <div className="absolute left-0 top-2 w-6 h-6 rounded-full bg-white border-4 border-emerald-500 shadow-sm z-10"></div>
                          <div className="bg-white p-6 rounded-3xl shadow-sm border border-slate-100">
                            <div className="flex justify-between mb-4">
                              <span className="text-xs font-bold text-slate-400 bg-slate-100 px-3 py-1 rounded-lg">{new Date(record.date).toLocaleDateString()}</span>
                              <span className="text-emerald-700 text-sm font-black">{record.treatment_provided}</span>
                            </div>
                            <div className="flex flex-wrap gap-2 mb-4">
                              {record.symptoms.map((s, idx) => <span key={idx} className="text-[10px] font-bold bg-slate-50 text-slate-500 px-2 py-0.5 rounded-md border border-slate-100">#{s}</span>)}
                            </div>
                            <p className="text-slate-600 text-sm leading-relaxed mb-3">{record.description}</p>
                            {((record.deduct_times ?? 0) > 0 || (record.deduct_cash ?? 0) > 0) && (
                              <div className="flex gap-3 border-t border-slate-50 pt-3 mt-3">
                                {(record.deduct_times ?? 0) > 0 && <span className="text-xs font-bold text-orange-600 bg-orange-50 px-2 py-1 rounded-md">扣减 {record.deduct_times} 次</span>}
                                {(record.deduct_cash ?? 0) > 0 && <span className="text-xs font-bold text-blue-600 bg-blue-50 px-2 py-1 rounded-md">消费 ¥{record.deduct_cash}</span>}
                              </div>
                            )}
                            {record.notes && <p className="text-xs text-slate-400 mt-2 italic">备注: {record.notes}</p>}
                          </div>
                        </div>
                      ))}
                      {selectedClient.health_history.length === 0 && <p className="text-slate-400 text-sm text-center py-8">暂无调理记录</p>}
                    </div>
                  </div>
                  <div className="w-1/3 p-8 border-l border-slate-100 bg-white overflow-y-auto">
                    <h3 className="text-sm font-black text-emerald-600 uppercase tracking-widest mb-8 flex items-center">
                      <Plus className="w-5 h-5 mr-3" /> 录入今日调理
                    </h3>
                    <form onSubmit={handleAddRecord} className="space-y-6">
                      <div>
                        <div className="flex items-center justify-between mb-2">
                          <label className="block text-xs font-bold text-slate-400 uppercase">本次主诉症状</label>
                          <VoiceInputButton onTranscript={(text) => setNewRecord(r => ({...r, symptoms: r.symptoms ? `${r.symptoms}，${text}` : text}))} />
                        </div>
                        <input required value={newRecord.symptoms} onChange={e => setNewRecord({...newRecord, symptoms: e.target.value})} className="w-full px-4 py-3 bg-slate-50 border-none rounded-2xl focus:ring-2 focus:ring-emerald-500 outline-none text-sm" placeholder="如：偏头痛, 失眠" />
                      </div>
                      <div>
                        <label className="block text-xs font-bold text-slate-400 uppercase mb-2">本次调理方案</label>
                        <select required value={newRecord.treatment_provided} onChange={e => setNewRecord({...newRecord, treatment_provided: e.target.value})}
                          className="w-full px-4 py-3 bg-slate-50 border-none rounded-2xl focus:ring-2 focus:ring-emerald-500 outline-none text-sm">
                          <option value="">-- 请选择服务项目 --</option>
                          {serviceItems.map(s => <option key={s.item_id} value={s.name}>{s.name}</option>)}
                          <option value="自定义">其它(自定义)</option>
                        </select>
                        {newRecord.treatment_provided === '自定义' && (
                          <input type="text" placeholder="请输入自定义项目名称" className="w-full px-4 py-3 mt-2 bg-slate-50 border-none rounded-2xl focus:ring-2 focus:ring-emerald-500 outline-none text-sm"
                            onChange={e => setNewRecord({...newRecord, treatment_provided: e.target.value})} />
                        )}
                      </div>
                      <div className="flex flex-col gap-4 p-4 bg-slate-50 rounded-2xl">
                        <div className="flex gap-6 mb-1">
                          <label className={`flex items-center gap-2 ${selectedClient?.times_card_balance && selectedClient.times_card_balance > 0 ? 'cursor-pointer' : 'cursor-not-allowed opacity-50'}`}>
                            <input disabled={!selectedClient?.times_card_balance || selectedClient.times_card_balance <= 0} type="radio" name="deductTypeClient" checked={deductType === 'times'} onChange={() => { setDeductType('times'); setNewRecord({...newRecord, deduct_cash: 0}); }} className="w-4 h-4 text-emerald-600" />
                            <span className="text-sm font-bold text-slate-700">划扣次卡 (余 {selectedClient?.times_card_balance || 0}次)</span>
                          </label>
                          <label className={`flex items-center gap-2 ${selectedClient?.cash_card_balance && selectedClient.cash_card_balance > 0 ? 'cursor-pointer' : 'cursor-not-allowed opacity-50'}`}>
                            <input disabled={!selectedClient?.cash_card_balance || selectedClient.cash_card_balance <= 0} type="radio" name="deductTypeClient" checked={deductType === 'cash'} onChange={() => { setDeductType('cash'); setNewRecord({...newRecord, deduct_times: 0}); }} className="w-4 h-4 text-emerald-600" />
                            <span className="text-sm font-bold text-slate-700">扣减余额 (余 ¥{selectedClient?.cash_card_balance?.toFixed(2) || '0.00'})</span>
                          </label>
                        </div>
                        {deductType === 'times' ? (
                          <div>
                            <label className="block text-xs font-bold text-orange-600 uppercase mb-2">本次扣减次卡</label>
                            <input disabled={!selectedClient?.times_card_balance || selectedClient.times_card_balance <= 0} type="number" min="0" max={selectedClient?.times_card_balance || 0} value={newRecord.deduct_times} onChange={e => {
                              let val = parseInt(e.target.value) || 0;
                              if (selectedClient && val > selectedClient.times_card_balance) val = selectedClient.times_card_balance;
                              setNewRecord({...newRecord, deduct_times: val});
                            }} className="w-full px-4 py-3 bg-orange-50 border-none rounded-xl font-bold text-orange-700 disabled:opacity-50" />
                          </div>
                        ) : (
                          <div>
                            <label className="block text-xs font-bold text-blue-600 uppercase mb-2">本次消费金额</label>
                            <input disabled={!selectedClient?.cash_card_balance || selectedClient.cash_card_balance <= 0} type="number" min="0" step="0.01" max={selectedClient?.cash_card_balance || 0} value={newRecord.deduct_cash} onChange={e => {
                              let val = parseFloat(e.target.value) || 0;
                              if (selectedClient && val > selectedClient.cash_card_balance) val = selectedClient.cash_card_balance;
                              setNewRecord({...newRecord, deduct_cash: val});
                            }} className="w-full px-4 py-3 bg-blue-50 border-none rounded-xl font-bold text-blue-700 disabled:opacity-50" />
                          </div>
                        )}
                      </div>
                      <div>
                        <div className="flex items-center justify-between mb-2">
                          <label className="block text-xs font-bold text-slate-400 uppercase">详细观察描述</label>
                          <VoiceInputButton onTranscript={(text) => setNewRecord(r => ({...r, description: r.description ? `${r.description} ${text}` : text}))} />
                        </div>
                        <textarea rows={3} required value={newRecord.description} onChange={e => setNewRecord({...newRecord, description: e.target.value})} className="w-full px-4 py-3 bg-slate-50 border-none rounded-2xl focus:ring-2 focus:ring-emerald-500 outline-none text-sm resize-none" placeholder="记录客户今日的具体体征..." />
                      </div>
                      <button type="submit" className="w-full py-4 bg-emerald-600 hover:bg-emerald-700 text-white rounded-2xl font-bold shadow-lg transition-all flex items-center justify-center gap-2">
                        <ClipboardList className="w-5 h-5" /> 完成录入并归档
                      </button>
                    </form>
                  </div>
                </div>
              )}

              {/* TAB: 专业分析 */}
              {detailTab === 'analysis' && (
                <div className="p-8 overflow-y-auto h-full">
                  {analyses.length === 0 ? (
                    <div className="text-center py-16 text-slate-400">
                      <Brain className="w-12 h-12 mx-auto mb-3 text-slate-200" />
                      <p>暂无专业分析记录</p>
                      <p className="text-xs mt-1">前往「深度分析」页面为该客户进行 AI 分析</p>
                    </div>
                  ) : (
                    <div className="space-y-4">
                      {analyses.map((a: any) => (
                        <div key={a.id} className="bg-white rounded-2xl border border-slate-100 p-5">
                          <div className="flex justify-between items-start mb-3">
                            <div>
                              <span className="text-lg font-bold text-slate-800">{a.primary_type}</span>
                              {a.secondary_type && <span className="text-sm text-slate-500 ml-2">兼 {a.secondary_type}</span>}
                            </div>
                            <div className="flex items-center gap-2">
                              <span className="text-xs bg-emerald-50 text-emerald-700 px-2 py-1 rounded-full font-bold">{Math.round(a.confidence_score * 100)}%</span>
                              <span className="text-xs text-slate-400">{a.assessed_at?.slice(0, 10)}</span>
                            </div>
                          </div>
                          <p className="text-sm text-slate-600 leading-relaxed">{a.ai_analysis_summary}</p>
                          {a.ai_recommendations && (
                            <div className="grid grid-cols-3 gap-2 mt-3 text-xs">
                              {(a.ai_recommendations.key_symptoms || []).length > 0 && (
                                <div className="bg-blue-50 rounded-xl p-2">
                                  <div className="font-bold text-blue-700 mb-1">关键特征</div>
                                  {a.ai_recommendations.key_symptoms.map((s: string, i: number) => <div key={i} className="text-blue-600">· {s}</div>)}
                                </div>
                              )}
                              {(a.ai_recommendations.risk_factors || []).length > 0 && (
                                <div className="bg-orange-50 rounded-xl p-2">
                                  <div className="font-bold text-orange-700 mb-1">风险因素</div>
                                  {a.ai_recommendations.risk_factors.map((s: string, i: number) => <div key={i} className="text-orange-600">· {s}</div>)}
                                </div>
                              )}
                              {(a.ai_recommendations.contraindications || []).length > 0 && (
                                <div className="bg-red-50 rounded-xl p-2">
                                  <div className="font-bold text-red-700 mb-1">禁忌事项</div>
                                  {a.ai_recommendations.contraindications.map((s: string, i: number) => <div key={i} className="text-red-600">· {s}</div>)}
                                </div>
                              )}
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}

              {/* TAB: 生命周期 */}
              {detailTab === 'lifecycle' && (
                <div className="p-8 overflow-y-auto h-full">
                  {lifecycle ? (
                    <div className="space-y-6">
                      <div className="bg-white rounded-2xl border border-slate-100 p-6">
                        <div className="grid grid-cols-4 gap-6">
                          <div>
                            <span className="text-xs text-slate-400 uppercase font-bold">当前状态</span>
                            <p className="mt-1">
                              <span className={`inline-flex px-3 py-1 rounded-full text-sm font-bold ${lifecycleLabels[lifecycle.current_status]?.color || 'bg-slate-100 text-slate-600'}`}>
                                {lifecycleLabels[lifecycle.current_status]?.text || lifecycle.current_status}
                              </span>
                            </p>
                          </div>
                          <div>
                            <span className="text-xs text-slate-400 uppercase font-bold">到店次数</span>
                            <p className="text-2xl font-black text-slate-800 mt-1">{lifecycle.visit_count}</p>
                          </div>
                          <div>
                            <span className="text-xs text-slate-400 uppercase font-bold">最近到店</span>
                            <p className="text-sm font-medium text-slate-600 mt-1">{lifecycle.last_visit_at ? new Date(lifecycle.last_visit_at).toLocaleDateString() : '无'}</p>
                          </div>
                          <div>
                            <span className="text-xs text-slate-400 uppercase font-bold">最近触达</span>
                            <p className="text-sm font-medium text-slate-600 mt-1">{lifecycle.last_contact_at ? new Date(lifecycle.last_contact_at).toLocaleDateString() : '无'}</p>
                          </div>
                        </div>
                      </div>
                      <div className="bg-slate-50 rounded-2xl p-6">
                        <h4 className="text-xs font-bold text-slate-500 uppercase mb-3">状态流转规则</h4>
                        <div className="flex items-center gap-2 text-xs text-slate-500">
                          <span className="bg-blue-100 text-blue-700 px-2 py-1 rounded-lg font-bold">新客</span>
                          <span>→ 到店≥2次 →</span>
                          <span className="bg-emerald-100 text-emerald-700 px-2 py-1 rounded-lg font-bold">活跃</span>
                          <span>→ 30天未到店 →</span>
                          <span className="bg-orange-100 text-orange-700 px-2 py-1 rounded-lg font-bold">沉默</span>
                          <span>→ 60天未到店 →</span>
                          <span className="bg-red-100 text-red-700 px-2 py-1 rounded-lg font-bold">流失预警</span>
                        </div>
                        <p className="text-xs text-slate-400 mt-2">任意状态再次到店 → 自动回流为活跃客</p>
                      </div>
                    </div>
                  ) : (
                    <div className="text-center py-16 text-slate-400">
                      <Users className="w-12 h-12 mx-auto mb-3 text-slate-200" />
                      <p>暂无生命周期数据</p>
                    </div>
                  )}
                </div>
              )}

              {/* TAB: 触达记录 */}
              {detailTab === 'outreach' && (
                <div className="p-8 overflow-y-auto h-full">
                  {outreachTasks.length === 0 ? (
                    <div className="text-center py-16 text-slate-400">
                      <Activity className="w-12 h-12 mx-auto mb-3 text-slate-200" />
                      <p>暂无触达记录</p>
                    </div>
                  ) : (
                    <div className="space-y-3">
                      {outreachTasks.map((t: any) => {
                        const sl = taskStatusLabels[t.status] || taskStatusLabels.queued;
                        return (
                          <div key={t.id} className="bg-white rounded-2xl border border-slate-100 p-4">
                            <div className="flex justify-between items-center mb-2">
                              <div className="flex items-center gap-2">
                                <span className="text-sm font-bold text-slate-700">{t.playbook_name}</span>
                                <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${sl.color}`}>{sl.text}</span>
                              </div>
                              <span className="text-xs text-slate-400">{t.created_at?.slice(0, 16)}</span>
                            </div>
                            <p className="text-sm text-slate-600 bg-slate-50 rounded-xl p-3">{t.generated_content}</p>
                          </div>
                        );
                      })}
                    </div>
                  )}
                </div>
              )}

              {/* TAB: 回复记录 */}
              {detailTab === 'replies' && (
                <div className="p-8 overflow-y-auto h-full">
                  {replies.length === 0 ? (
                    <div className="text-center py-16 text-slate-400">
                      <MessageSquare className="w-12 h-12 mx-auto mb-3 text-slate-200" />
                      <p>暂无客户回复</p>
                    </div>
                  ) : (
                    <div className="space-y-3">
                      {replies.map((r: any) => {
                        const il = intentLabels[r.intent] || intentLabels.general_chat;
                        return (
                          <div key={r.id} className="bg-white rounded-2xl border border-slate-100 p-4">
                            <div className="flex justify-between items-center mb-2">
                              <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${il.color}`}>{il.text}</span>
                              <div className="flex items-center gap-2">
                                {r.sentiment && <span className={`text-xs font-bold ${r.sentiment === 'positive' ? 'text-emerald-600' : r.sentiment === 'negative' ? 'text-red-600' : 'text-slate-500'}`}>{r.sentiment === 'positive' ? '正面' : r.sentiment === 'negative' ? '负面' : '中性'}</span>}
                                <span className="text-xs text-slate-400">{r.created_at?.slice(0, 16)}</span>
                              </div>
                            </div>
                            <p className="text-sm text-slate-700 font-medium">{r.raw_content}</p>
                            {r.auto_action && <p className="text-xs text-slate-400 mt-2">自动动作: {r.auto_action}</p>}
                          </div>
                        );
                      })}
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default Clients;