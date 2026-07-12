import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { CreditCard, Search, PlusCircle, MinusCircle, Activity, ClipboardList, X, Download } from 'lucide-react';
import VoiceInputButton from '../components/VoiceInputButton';
import { ReadOnlyButton } from '../components/ReadOnlyGuard';

interface ClientProfile {
  client_id: string;
  name: string;
  phone: string;
  times_card_balance: number;
  cash_card_balance: number;
}

interface Transaction {
  transaction_id: string;
  client_id: string;
  amount: number;
  times_count?: number;
  cash_amount?: number;
  transaction_type: string;
  payment_method: string;
  date: string;
  notes: string;
}

const Billing = () => {
  const [clients, setClients] = useState<ClientProfile[]>([]);
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [selectedClient, setSelectedClient] = useState<ClientProfile | null>(null);
  
  // 流水详情弹窗状态
  const [isHistoryModalOpen, setIsHistoryModalOpen] = useState(false);
  const [filterPeriod, setFilterPeriod] = useState('all'); // all, week, month, custom
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');

  // 充值状态
  const [rechargeData, setRechargeData] = useState({ type: 'cash', amount: 0, cashAmount: 0, notes: '' });
  
  // 消费/核销状态 (附带服务记录)
  const [consumeData, setConsumeData] = useState({
    deduct_times: 0,
    deduct_cash: 0,
    symptoms: '',
    description: '',
    treatment_provided: '',
    notes: ''
  });
  const [deductType, setDeductType] = useState<'times' | 'cash'>('times');
  
  const [serviceItems, setServiceItems] = useState<any[]>([]);

  const fetchData = async () => {
    try {
      const [clientsRes, txRes, servicesRes] = await Promise.all([
        axios.get('/api/v1/clients/'),
        axios.get('/api/v1/billing/'),
        axios.get('/api/v1/services/')
      ]);
      setClients(clientsRes.data);
      setServiceItems(servicesRes.data);
      // 倒序排列流水
      setTransactions(txRes.data.sort((a: Transaction, b: Transaction) => new Date(b.date).getTime() - new Date(a.date).getTime()));


      if (selectedClient) {
        const updated = clientsRes.data.find((c: ClientProfile) => c.client_id === selectedClient.client_id);
        setSelectedClient(updated || null);
      }
    } catch (error) {
      console.error('获取数据失败', error);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handleRecharge = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedClient || rechargeData.amount <= 0) return;
    if (rechargeData.type === 'times' && rechargeData.cashAmount <= 0) {
      alert('请输入实收金额');
      return;
    }
    try {
      await axios.post(`/api/v1/clients/${selectedClient.client_id}/wallet`, {
        action_type: rechargeData.type,
        amount: rechargeData.amount,
        cash_amount: rechargeData.type === 'times' ? rechargeData.cashAmount : rechargeData.amount,
        notes: rechargeData.notes || (rechargeData.type === 'times' ? `次卡充值${rechargeData.amount}次，实收¥${rechargeData.cashAmount}元` : `现金充值¥${rechargeData.amount}元`)
      });
      alert('充值成功！');
      setRechargeData({ type: 'cash', amount: 0, cashAmount: 0, notes: '' });
      fetchData();
    } catch (error) {
      alert('充值失败');
    }
  };

  const handleExport = async () => {
    try {
      const response = await axios.get(`/api/v1/billing/export/excel`, { responseType: 'blob' });
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `交易记录_${new Date().toISOString().slice(0,10)}.xlsx`);
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

  const handleConsume = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedClient) return;
    if (consumeData.deduct_times === 0 && consumeData.deduct_cash === 0 && !consumeData.treatment_provided) {
      alert('请输入扣减金额/次数或调理项目');
      return;
    }
    try {
      const payload = {
        symptoms: consumeData.symptoms.split(',').map(s => s.trim()).filter(s => s),
        description: consumeData.description || '常规消费',
        treatment_provided: consumeData.treatment_provided || '常规项目',
        notes: consumeData.notes,
        deduct_times: consumeData.deduct_times,
        deduct_cash: consumeData.deduct_cash,
        date: new Date().toISOString()
      };
      await axios.post(`/api/v1/clients/${selectedClient.client_id}/records`, payload);
      alert('消费核销并归档成功！');
      setConsumeData({ deduct_times: 0, deduct_cash: 0, symptoms: '', description: '', treatment_provided: '', notes: '' });
      fetchData();
    } catch (error) {
      alert('操作失败');
    }
  };

  // 过滤流水逻辑
  const getFilteredTransactions = () => {
    const now = new Date();
    return transactions.filter(tx => {
      const txDate = new Date(tx.date);
      if (filterPeriod === 'week') {
        const oneWeekAgo = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000);
        return txDate >= oneWeekAgo;
      }
      if (filterPeriod === 'month') {
        const oneMonthAgo = new Date(now.getFullYear(), now.getMonth() - 1, now.getDate());
        return txDate >= oneMonthAgo;
      }
      if (filterPeriod === 'custom' && startDate && endDate) {
        return txDate >= new Date(startDate) && txDate <= new Date(endDate + 'T23:59:59');
      }
      return true;
    });
  };

  const filteredTransactions = getFilteredTransactions();
  // 计算过滤后的总现金充值收入（只统计现金充值）
  const totalCashIncome = filteredTransactions.reduce((sum, tx) => {
    const isCashRecharge = tx.transaction_type === 'cash_recharge' || (tx.amount > 0 && tx.notes?.includes('现金充值'));
    return isCashRecharge ? sum + (tx.cash_amount || tx.amount) : sum;
  }, 0);

  // 计算过滤后的次卡充值收入（实收金额）
  const totalTimesIncome = filteredTransactions.reduce((sum, tx) => {
    const isTimesRecharge = tx.transaction_type === 'times_recharge' || (tx.notes?.includes('次卡充值') && (tx.times_count ?? 0) > 0);
    return isTimesRecharge ? sum + (tx.cash_amount || 0) : sum;
  }, 0);

  // 计算过滤后的次卡充值次数
  const totalTimesCount = filteredTransactions.reduce((sum, tx) => {
    const isTimesRecharge = tx.transaction_type === 'times_recharge' || (tx.notes?.includes('次卡充值') && (tx.times_count ?? 0) > 0);
    return isTimesRecharge ? sum + (tx.times_count ?? 0) : sum;
  }, 0);

  return (
    <div className="p-8 flex gap-8 h-[calc(100vh-80px)]">
      {/* 左侧：客户选择与流水 */}
      <div className="w-1/3 flex flex-col gap-6">
        <div className="bg-white rounded-2xl shadow-sm border border-slate-100 p-6 flex-shrink-0">
          <div className="flex justify-between items-center mb-4">
            <h2 className="text-lg font-bold text-slate-800 flex items-center"><Search className="w-5 h-5 mr-2" /> 选择操作客户</h2>
            <button onClick={handleExport} className="text-xs bg-blue-600 hover:bg-blue-700 text-white px-2 py-1 rounded-lg font-bold flex items-center gap-1">
              <Download className="w-3 h-3" /> 导出
            </button>
          </div>
          <div className="relative">
            <select 
              className="w-full pl-4 pr-10 py-3 border border-slate-200 rounded-xl appearance-none bg-slate-50 focus:ring-2 focus:ring-emerald-500 font-medium"
              onChange={(e) => {
                const c = clients.find(c => c.client_id === e.target.value);
                setSelectedClient(c || null);
                if (c) {
                  if (c.times_card_balance <= 0 && c.cash_card_balance > 0) {
                    setDeductType('cash');
                  } else {
                    setDeductType('times');
                  }
                }
              }}
              value={selectedClient?.client_id || ""}
            >
              <option value="">-- 请选择客户 --</option>
              {clients.map(c => (
                <option key={c.client_id} value={c.client_id}>{c.name} ({c.phone.slice(-4)})</option>
              ))}
            </select>
          </div>
          
          {selectedClient && (
            <div className="mt-6 p-4 bg-emerald-50 border border-emerald-100 rounded-xl">
              <div className="flex items-center gap-3 mb-4">
                <div className="w-10 h-10 rounded-full bg-emerald-600 text-white flex items-center justify-center font-bold">{selectedClient.name.charAt(0)}</div>
                <div>
                  <div className="font-bold text-emerald-900">{selectedClient.name}</div>
                  <div className="text-xs text-emerald-600">{selectedClient.phone}</div>
                </div>
              </div>
              <div className="flex justify-between text-sm font-bold">
                <div className="text-orange-600 bg-orange-100/50 px-3 py-1 rounded-lg">次卡: {selectedClient.times_card_balance} 次</div>
                <div className="text-blue-600 bg-blue-100/50 px-3 py-1 rounded-lg">储值: ¥{selectedClient.cash_card_balance.toFixed(2)}</div>
              </div>
            </div>
          )}
        </div>

        <div className="bg-white rounded-2xl shadow-sm border border-slate-100 flex-1 overflow-hidden flex flex-col">
          <div 
            className="p-4 border-b border-slate-100 bg-slate-50/50 flex justify-between items-center cursor-pointer hover:bg-slate-100 transition-colors"
            onClick={() => setIsHistoryModalOpen(true)}
          >
            <h3 className="font-bold text-slate-700 flex items-center"><Activity className="w-4 h-4 mr-2 text-emerald-600" /> 近期动态 (最近10条)</h3>
            <span className="text-xs font-bold text-emerald-600 bg-emerald-50 px-2 py-1 rounded-md">查看全部明细</span>
          </div>
          <div className="overflow-y-auto flex-1 p-4 space-y-3">
            {transactions.slice(0, 10).map(tx => {
              const client = clients.find(c => c.client_id === tx.client_id);
              const isIncome = tx.amount > 0 || (tx.times_count ?? 0) > 0;
              // 判断是否是次卡充值
              const isTimesRecharge = tx.transaction_type === 'times_recharge' || tx.notes?.includes('次卡充值');
              // 判断是否是现金充值
              const isCashRecharge = tx.transaction_type === 'cash_recharge' || tx.notes?.includes('现金充值');
              return (
                <div key={tx.transaction_id} className="flex items-center justify-between p-3 bg-slate-50 rounded-xl">
                  <div>
                    <div className="text-sm font-bold text-slate-700">{client?.name || '未知客户'}</div>
                    <div className="text-xs text-slate-400">{new Date(tx.date).toLocaleString()} | {tx.notes || (isIncome ? (isTimesRecharge ? '充值次卡' : '现金充值') : '消费')}</div>
                  </div>
                  <div className={`font-black ${isIncome ? 'text-emerald-600' : 'text-slate-600'}`}>
                    {isTimesRecharge ? `${tx.times_count}次 / ¥${tx.cash_amount}元` : isCashRecharge ? `¥${tx.cash_amount || tx.amount}元` : `${tx.amount < 0 ? '-' : ''}¥${Math.abs(tx.amount)}元`}
                  </div>
                </div>
              );
            })}
            {transactions.length === 0 && <div className="text-center text-slate-400 text-sm py-8">暂无流水记录</div>}
          </div>
        </div>
      </div>

      {/* 右侧：操作区 */}
      <div className="w-2/3 bg-white rounded-2xl shadow-sm border border-slate-100 overflow-hidden flex flex-col">
        {!selectedClient ? (
          <div className="flex-1 flex flex-col items-center justify-center text-slate-400">
            <CreditCard className="w-16 h-16 mb-4 text-slate-200" />
            <p className="text-lg">请先在左侧选择一位客户</p>
          </div>
        ) : (
          <div className="flex-1 overflow-y-auto p-8 flex flex-col gap-8">
            
            {/* 充值面板 */}
            <div className="border border-slate-100 rounded-2xl p-6 shadow-sm">
              <h3 className="text-lg font-black text-slate-800 mb-6 flex items-center"><PlusCircle className="w-5 h-5 mr-2 text-emerald-600" /> 客户充值 / 充次</h3>
              <form onSubmit={handleRecharge} className="flex items-end gap-4 flex-wrap">
                <div className="w-1/5 min-w-[150px]">
                  <label className="block text-xs font-bold text-slate-500 uppercase mb-2">充值类型</label>
                  <select value={rechargeData.type} onChange={e => setRechargeData({...rechargeData, type: e.target.value})} className="w-full px-4 py-3 bg-slate-50 border border-slate-200 rounded-xl focus:ring-2 focus:ring-emerald-500">
                    <option value="cash">现金充值 (元)</option>
                    <option value="times">充值次卡 (次)</option>
                  </select>
                </div>
                {rechargeData.type === 'times' ? (
                  <>
                    <div className="w-1/5 min-w-[150px]">
                      <label className="block text-xs font-bold text-slate-500 uppercase mb-2">充值次数</label>
                      <input type="number" min="1" step="1" required value={rechargeData.amount} onChange={e => setRechargeData({...rechargeData, amount: parseFloat(e.target.value) || 0})} className="w-full px-4 py-3 bg-slate-50 border border-slate-200 rounded-xl focus:ring-2 focus:ring-emerald-500 font-bold" placeholder="次" />
                    </div>
                    <div className="w-1/5 min-w-[150px]">
                      <label className="block text-xs font-bold text-slate-500 uppercase mb-2">实收金额</label>
                      <input type="number" min="0" step="0.01" required value={rechargeData.cashAmount} onChange={e => setRechargeData({...rechargeData, cashAmount: parseFloat(e.target.value) || 0})} className="w-full px-4 py-3 bg-slate-50 border border-slate-200 rounded-xl focus:ring-2 focus:ring-emerald-500 font-bold" placeholder="元" />
                    </div>
                  </>
                ) : (
                  <div className="w-1/5 min-w-[150px]">
                    <label className="block text-xs font-bold text-slate-500 uppercase mb-2">充值金额</label>
                    <input type="number" min="1" step="0.01" required value={rechargeData.amount} onChange={e => setRechargeData({...rechargeData, amount: parseFloat(e.target.value) || 0})} className="w-full px-4 py-3 bg-slate-50 border border-slate-200 rounded-xl focus:ring-2 focus:ring-emerald-500 font-bold" placeholder="元" />
                  </div>
                )}
                <div className="flex-1 min-w-[200px]">
                  <label className="block text-xs font-bold text-slate-500 uppercase mb-2">备注</label>
                  <input type="text" value={rechargeData.notes} onChange={e => setRechargeData({...rechargeData, notes: e.target.value})} className="w-full px-4 py-3 bg-slate-50 border border-slate-200 rounded-xl focus:ring-2 focus:ring-emerald-500" placeholder="选填" />
                </div>
                <ReadOnlyButton>
                  <button type="submit" className="px-6 py-3 bg-emerald-600 hover:bg-emerald-700 text-white font-bold rounded-xl whitespace-nowrap transition-colors">
                    确认充值
                  </button>
                </ReadOnlyButton>
              </form>
            </div>

            {/* 消费核销面板 */}
            <div className="border border-slate-100 rounded-2xl p-6 shadow-sm bg-slate-50/50">
              <h3 className="text-lg font-black text-slate-800 mb-6 flex items-center"><MinusCircle className="w-5 h-5 mr-2 text-rose-500" /> 消费核销与档案记录</h3>
              <form onSubmit={handleConsume} className="space-y-5">
                <div className="flex gap-6 p-4 bg-white rounded-xl border border-slate-200 flex-col">
                  <div className="flex gap-6 mb-2">
                    <label className={`flex items-center gap-2 ${selectedClient?.times_card_balance && selectedClient.times_card_balance > 0 ? 'cursor-pointer' : 'cursor-not-allowed opacity-50'}`}>
                      <input disabled={!selectedClient?.times_card_balance || selectedClient.times_card_balance <= 0} type="radio" name="deductType" checked={deductType === 'times'} onChange={() => { setDeductType('times'); setConsumeData({...consumeData, deduct_cash: 0}); }} className="w-4 h-4 text-emerald-600 focus:ring-emerald-500" />
                      <span className="text-sm font-bold text-slate-700">划扣次卡 (余 {selectedClient?.times_card_balance || 0}次)</span>
                    </label>
                    <label className={`flex items-center gap-2 ${selectedClient?.cash_card_balance && selectedClient.cash_card_balance > 0 ? 'cursor-pointer' : 'cursor-not-allowed opacity-50'}`}>
                      <input disabled={!selectedClient?.cash_card_balance || selectedClient.cash_card_balance <= 0} type="radio" name="deductType" checked={deductType === 'cash'} onChange={() => { setDeductType('cash'); setConsumeData({...consumeData, deduct_times: 0}); }} className="w-4 h-4 text-emerald-600 focus:ring-emerald-500" />
                      <span className="text-sm font-bold text-slate-700">扣减余额 (余 ¥{selectedClient?.cash_card_balance?.toFixed(2) || '0.00'})</span>
                    </label>
                  </div>
                  
                  {deductType === 'times' ? (
                    <div>
                      <label className="block text-xs font-bold text-orange-600 uppercase mb-2">扣减次卡 (次)</label>
                      <input disabled={!selectedClient?.times_card_balance || selectedClient.times_card_balance <= 0} type="number" min="0" max={selectedClient?.times_card_balance || 0} value={consumeData.deduct_times} onChange={e => {
                        let val = parseInt(e.target.value) || 0;
                        if (selectedClient && val > selectedClient.times_card_balance) val = selectedClient.times_card_balance;
                        setConsumeData({...consumeData, deduct_times: val});
                      }} className="w-full px-4 py-3 bg-orange-50/50 border-none rounded-xl focus:ring-2 focus:ring-orange-500 outline-none font-bold text-orange-700 text-lg disabled:opacity-50" placeholder={selectedClient?.times_card_balance && selectedClient.times_card_balance > 0 ? "0" : "余额不足"} />
                    </div>
                  ) : (
                    <div>
                      <label className="block text-xs font-bold text-blue-600 uppercase mb-2">扣减余额 (元)</label>
                      <input disabled={!selectedClient?.cash_card_balance || selectedClient.cash_card_balance <= 0} type="number" min="0" step="0.01" max={selectedClient?.cash_card_balance || 0} value={consumeData.deduct_cash} onChange={e => {
                        let val = parseFloat(e.target.value) || 0;
                        if (selectedClient && val > selectedClient.cash_card_balance) val = selectedClient.cash_card_balance;
                        setConsumeData({...consumeData, deduct_cash: val});
                      }} className="w-full px-4 py-3 bg-blue-50/50 border-none rounded-xl focus:ring-2 focus:ring-blue-500 outline-none font-bold text-blue-700 text-lg disabled:opacity-50" placeholder={selectedClient?.cash_card_balance && selectedClient.cash_card_balance > 0 ? "0.00" : "余额不足"} />
                    </div>
                  )}
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-xs font-bold text-slate-500 uppercase mb-2">本次调理项目 / 消费内容</label>
                    <select 
                      required 
                      value={consumeData.treatment_provided} 
                      onChange={e => {
                        setConsumeData({
                          ...consumeData, 
                          treatment_provided: e.target.value
                        });
                      }}
                      className="w-full px-4 py-3 bg-white border border-slate-200 rounded-xl focus:ring-2 focus:ring-emerald-500"
                    >
                      <option value="">-- 请选择服务项目 --</option>
                      {serviceItems.map(s => <option key={s.item_id} value={s.name}>{s.name}</option>)}
                      <option value="自定义">其它(自定义)</option>
                    </select>
                    {consumeData.treatment_provided === '自定义' && (
                      <input 
                        type="text" 
                        placeholder="请输入自定义项目名称" 
                        className="w-full px-4 py-3 mt-2 bg-white border border-slate-200 rounded-xl focus:ring-2 focus:ring-emerald-500"
                        onChange={e => setConsumeData({...consumeData, treatment_provided: e.target.value})}
                      />
                    )}
                  </div>
                  <div>
                    <div className="flex items-center justify-between mb-2">
                      <label className="block text-xs font-bold text-slate-500 uppercase">主诉症状标签 (逗号分隔)</label>
                      <VoiceInputButton onTranscript={(text) => setConsumeData(d => ({...d, symptoms: d.symptoms ? `${d.symptoms}，${text}` : text}))} />
                    </div>
                    <input value={consumeData.symptoms} onChange={e => setConsumeData({...consumeData, symptoms: e.target.value})} className="w-full px-4 py-3 bg-white border border-slate-200 rounded-xl focus:ring-2 focus:ring-emerald-500" placeholder="如：肩颈僵硬, 气血不足" />
                  </div>
                </div>

                <div>
                  <div className="flex items-center justify-between mb-2">
                    <label className="block text-xs font-bold text-slate-500 uppercase">详细调理记录</label>
                    <VoiceInputButton onTranscript={(text) => setConsumeData(d => ({...d, description: d.description ? `${d.description} ${text}` : text}))} />
                  </div>
                  <textarea rows={2} value={consumeData.description} onChange={e => setConsumeData({...consumeData, description: e.target.value})} className="w-full px-4 py-3 bg-white border border-slate-200 rounded-xl focus:ring-2 focus:ring-emerald-500 resize-none" placeholder="记录技师的服务细节..." />
                </div>
                
                <ReadOnlyButton>
                  <button type="submit" className="w-full py-4 bg-slate-800 hover:bg-slate-900 text-white rounded-xl font-bold shadow-lg transition-all flex justify-center items-center gap-2 text-lg">
                    <ClipboardList className="w-5 h-5" /> 确认扣费并生成健康档案
                  </button>
                </ReadOnlyButton>
              </form>
            </div>

          </div>
        )}
      </div>

      {/* 流水明细弹窗 */}
      {isHistoryModalOpen && (
        <div className="fixed inset-0 bg-slate-900/60 backdrop-blur-sm flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-3xl shadow-2xl w-full max-w-4xl max-h-[90vh] overflow-hidden flex flex-col animate-in fade-in zoom-in duration-200">
            <div className="p-6 border-b border-slate-100 flex justify-between items-center bg-slate-50/50">
              <h2 className="text-xl font-bold text-slate-800 flex items-center">
                <Activity className="w-6 h-6 mr-2 text-emerald-600" />
                全店财务流水明细
              </h2>
              <X onClick={() => setIsHistoryModalOpen(false)} className="w-8 h-8 text-slate-400 cursor-pointer hover:text-slate-600 p-1" />
            </div>
            
            <div className="p-6 border-b border-slate-100 bg-white flex items-end gap-4">
              <div>
                <label className="block text-xs font-bold text-slate-500 uppercase mb-2">筛选周期</label>
                <select 
                  value={filterPeriod} 
                  onChange={e => setFilterPeriod(e.target.value)} 
                  className="px-4 py-2 bg-slate-50 border border-slate-200 rounded-xl focus:ring-2 focus:ring-emerald-500 font-medium"
                >
                  <option value="all">全部记录</option>
                  <option value="week">最近一周</option>
                  <option value="month">本月</option>
                  <option value="custom">自定义时间段</option>
                </select>
              </div>
              
              {filterPeriod === 'custom' && (
                <>
                  <div>
                    <label className="block text-xs font-bold text-slate-500 uppercase mb-2">开始日期</label>
                    <input type="date" value={startDate} onChange={e => setStartDate(e.target.value)} className="px-4 py-2 bg-slate-50 border border-slate-200 rounded-xl focus:ring-2 focus:ring-emerald-500" />
                  </div>
                  <div>
                    <label className="block text-xs font-bold text-slate-500 uppercase mb-2">结束日期</label>
                    <input type="date" value={endDate} onChange={e => setEndDate(e.target.value)} className="px-4 py-2 bg-slate-50 border border-slate-200 rounded-xl focus:ring-2 focus:ring-emerald-500" />
                  </div>
                </>
              )}

              <div className="flex gap-4 ml-auto">
                <div className="bg-emerald-50 px-6 py-3 rounded-xl border border-emerald-100 flex flex-col items-end">
                  <span className="text-xs font-bold text-emerald-600 uppercase">区间现金充值</span>
                  <span className="text-xl font-black text-emerald-700">¥{totalCashIncome.toFixed(2)}</span>
                </div>
                <div className="bg-orange-50 px-6 py-3 rounded-xl border border-orange-100 flex flex-col items-end">
                  <span className="text-xs font-bold text-orange-600 uppercase">区间次卡充值</span>
                  <span className="text-xl font-black text-orange-700">¥{totalTimesIncome.toFixed(2)}</span>
                </div>
                <div className="bg-blue-50 px-6 py-3 rounded-xl border border-blue-100 flex flex-col items-end">
                  <span className="text-xs font-bold text-blue-600 uppercase">区间充次总数</span>
                  <span className="text-xl font-black text-blue-700">{totalTimesCount} 次</span>
                </div>
              </div>
            </div>

            <div className="flex-1 overflow-y-auto bg-slate-50/50 p-6">
              <table className="w-full text-left border-collapse bg-white rounded-xl shadow-sm overflow-hidden">
                <thead>
                  <tr className="bg-slate-100 text-slate-500 text-xs uppercase tracking-wider">
                    <th className="p-4 font-bold">交易时间</th>
                    <th className="p-4 font-bold">客户姓名</th>
                    <th className="p-4 font-bold">交易类型</th>
                    <th className="p-4 font-bold">支付方式</th>
                    <th className="p-4 font-bold text-right">金额/扣次</th>
                    <th className="p-4 font-bold">备注说明</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-50">
                  {filteredTransactions.map(tx => {
                    const client = clients.find(c => c.client_id === tx.client_id);
                    const isIncome = tx.amount > 0 || (tx.times_count ?? 0) > 0;
                    // 判断是否是次卡充值
                    const isTimesRecharge = tx.transaction_type === 'times_recharge' || tx.notes?.includes('次卡充值');
                    // 判断是否是现金充值
                    const isCashRecharge = tx.transaction_type === 'cash_recharge' || tx.notes?.includes('现金充值');
                    // 判断是否是消费扣减
                    const isConsume = tx.transaction_type === 'payment' || (tx.amount < 0);

                    return (
                      <tr key={tx.transaction_id} className="hover:bg-slate-50 transition-colors">
                        <td className="p-4 text-sm text-slate-600">{new Date(tx.date).toLocaleString()}</td>
                        <td className="p-4 font-bold text-slate-800">{client?.name || '未知客户'}</td>
                        <td className="p-4 text-sm">
                          <span className={`px-2 py-1 rounded-md text-xs font-bold ${
                            isTimesRecharge ? 'bg-orange-50 text-orange-600' :
                            isCashRecharge ? 'bg-emerald-50 text-emerald-600' :
                            'bg-rose-50 text-rose-600'
                          }`}>
                            {isTimesRecharge ? '充值次卡' : isCashRecharge ? '现金充值' : '消费扣减'}
                          </span>
                        </td>
                        <td className="p-4 text-sm text-slate-500">
                          {isConsume ? '会员卡消费' : '现金/会员卡充值'}
                        </td>
                        <td className={`p-4 text-right font-black ${
                          isIncome ? 'text-emerald-600' : 'text-slate-800'
                        }`}>
                          {isTimesRecharge
                            ? `${tx.times_count}次 / ¥${tx.cash_amount}元`
                            : isCashRecharge
                            ? `¥${tx.cash_amount || tx.amount}元`
                            : `${tx.amount < 0 ? '-' : ''}¥${Math.abs(tx.amount)}元`}
                        </td>
                        <td className="p-4 text-sm text-slate-500">{tx.notes || '-'}</td>
                      </tr>
                    );
                  })}
                  {filteredTransactions.length === 0 && (
                    <tr>
                      <td colSpan={6} className="p-12 text-center text-slate-400">该时间段内暂无流水记录</td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default Billing;