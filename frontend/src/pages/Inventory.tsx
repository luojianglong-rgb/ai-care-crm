import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Package, Plus, X, Edit2, TrendingUp, AlertTriangle, Send, Trash2 } from 'lucide-react';
import { ReadOnlyButton } from '../components/ReadOnlyGuard';

interface InventoryItem {
  item_id: string;
  name: string;
  category: string;
  quantity: number;
  unit: string;
  price: number;
  last_updated: string;
}

interface UsageRecord {
  usage_id: string;
  item_id: string;
  staff_name: string;
  quantity: number;
  usage_date: string;
  notes: string;
}

interface InventoryCategory {
  category_id: string;
  name: string;
}

const Inventory = () => {
  const [activeTab, setActiveTab] = useState<'inventory' | 'usage'>('inventory');
  const [items, setItems] = useState<InventoryItem[]>([]);
  const [usageRecords, setUsageRecords] = useState<UsageRecord[]>([]);
  const [staff, setStaff] = useState<any[]>([]);
  const [categories, setCategories] = useState<InventoryCategory[]>([]);

  // 新增/编辑库存弹窗
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [formData, setFormData] = useState({
    name: '', category: '', quantity: 0, unit: '瓶', price: 0
  });

  // 领用记录弹窗
  const [isUsageModalOpen, setIsUsageModalOpen] = useState(false);
  const [selectedItem, setSelectedItem] = useState<InventoryItem | null>(null);
  const [usageData, setUsageData] = useState({ staff_name: '', quantity: 1, notes: '', action_type: 'issue' });

  const fetchData = async () => {
    try {
      const [invRes, usageRes, staffRes, categoriesRes] = await Promise.all([
        axios.get('/api/v1/inventory/'),
        axios.get('/api/v1/inventory/usage/history'),
        axios.get('/api/v1/services/staff/'),
        axios.get('/api/v1/inventory/categories/')
      ]);
      setItems(invRes.data.sort((a: InventoryItem, b: InventoryItem) => a.quantity - b.quantity));
      setUsageRecords(usageRes.data);
      setStaff(staffRes.data);
      setCategories(categoriesRes.data);
    } catch (e) { console.error("加载数据失败", e); }
  };

  useEffect(() => { fetchData(); }, []);

  const openModal = (item?: InventoryItem) => {
    if (item) {
      setEditingId(item.item_id);
      setFormData({ name: item.name, category: item.category, quantity: item.quantity, unit: item.unit, price: item.price });
    } else {
      setEditingId(null);
      setFormData({ name: '', category: categories.length > 0 ? categories[0].name : '', quantity: 0, unit: '瓶', price: 0 });
    }
    setIsModalOpen(true);
  };

  const handleSaveItem = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      if (editingId) {
        await axios.put(`/api/v1/inventory/${editingId}`, formData);
      } else {
        await axios.post('/api/v1/inventory/', formData);
      }
      setIsModalOpen(false);
      fetchData();
    } catch (error) { alert('保存库存失败'); }
  };

  const handleDeleteItem = async (itemId: string, name: string) => {
    if (!confirm(`确定要删除库存物品「${name}」吗？`)) return;
    try {
      await axios.delete(`/api/v1/inventory/${itemId}`);
      fetchData();
    } catch (error) { alert('删除失败'); }
  };

  const openUsageModal = (item: InventoryItem) => {
    setSelectedItem(item);
    setUsageData({ staff_name: staff.length > 0 ? staff[0].name : '', quantity: 1, notes: '', action_type: 'issue' });
    setIsUsageModalOpen(true);
  };

  const handleRecordUsage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedItem) return;
    try {
      const endpoint = usageData.action_type === 'return' ? '/api/v1/inventory/return' : '/api/v1/inventory/usage';
      await axios.post(`${endpoint}`, {
        item_id: selectedItem.item_id,
        staff_name: usageData.staff_name,
        quantity: usageData.quantity,
        notes: usageData.notes
      });
      setIsUsageModalOpen(false);
      fetchData();
      alert(usageData.action_type === 'return' ? '退还成功，库存已增加！' : '领用记录已保存并扣减库存！');
    } catch (error) {
      alert(usageData.action_type === 'return' ? '退还失败，请检查' : '扣减失败，请检查库存数量是否充足');
    }
  };

  const updateQuantity = async (id: string, newQuantity: number) => {
    if (newQuantity < 0) return;
    try {
      await axios.put(`/api/v1/inventory/${id}`, { quantity: newQuantity });
      fetchData();
    } catch (e) { alert('更新数量失败'); }
  };

  const totalValue = items.reduce((sum, item) => sum + (item.quantity * item.price), 0);
  const lowStockCount = items.filter(item => item.quantity <= 5).length;

  return (
    <div className="p-8 max-w-7xl mx-auto">
      <div className="flex justify-between items-center mb-8">
        <div>
          <h1 className="text-2xl font-bold text-slate-800 tracking-tight">库存与耗材管理</h1>
          <p className="text-slate-500 text-sm mt-1">管理院线产品、精油耗材的进销存及技师领用</p>
        </div>
        <div className="flex gap-3">
          <ReadOnlyButton>
            <button onClick={() => openModal()} className="bg-emerald-600 hover:bg-emerald-700 text-white px-5 py-2.5 rounded-xl flex items-center font-bold transition-all shadow-lg shadow-emerald-100">
              <Plus className="w-5 h-5 mr-2" /> 增加新物品
            </button>
          </ReadOnlyButton>
        </div>
      </div>

      <div className="flex gap-4 mb-6">
        <button onClick={() => setActiveTab('inventory')} className={`px-6 py-3 rounded-xl font-bold flex items-center transition-colors ${activeTab === 'inventory' ? 'bg-slate-800 text-white' : 'bg-white text-slate-500 hover:bg-slate-50 border border-slate-200'}`}>
          <Package className="w-5 h-5 mr-2" /> 库存台账
        </button>
        <button onClick={() => setActiveTab('usage')} className={`px-6 py-3 rounded-xl font-bold flex items-center transition-colors ${activeTab === 'usage' ? 'bg-slate-800 text-white' : 'bg-white text-slate-500 hover:bg-slate-50 border border-slate-200'}`}>
          <Send className="w-5 h-5 mr-2" /> 领用消耗记录
        </button>
      </div>

      {activeTab === 'inventory' && (
        <>
          <div className="grid grid-cols-2 gap-6 mb-8">
            <div className="bg-white p-6 rounded-2xl shadow-sm border border-slate-100 flex items-center">
              <div className="w-14 h-14 rounded-2xl bg-blue-50 text-blue-600 flex items-center justify-center mr-5"><TrendingUp className="w-7 h-7" /></div>
              <div><span className="text-slate-500 font-bold text-sm uppercase">当前库存总价值</span><div className="text-3xl font-black text-slate-800 mt-1">¥{totalValue.toFixed(2)}</div></div>
            </div>
            <div className="bg-white p-6 rounded-2xl shadow-sm border border-slate-100 flex items-center">
              <div className="w-14 h-14 rounded-2xl bg-orange-50 text-orange-500 flex items-center justify-center mr-5"><AlertTriangle className="w-7 h-7" /></div>
              <div><span className="text-slate-500 font-bold text-sm uppercase">库存告警 (数量 ≤ 5)</span><div className="text-3xl font-black text-orange-600 mt-1">{lowStockCount} <span className="text-lg font-medium text-slate-400">种物品需要补货</span></div></div>
            </div>
          </div>

          <div className="bg-white rounded-3xl shadow-sm border border-slate-100 overflow-hidden">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="bg-slate-50/50 border-b border-slate-100 text-slate-500 text-xs uppercase tracking-wider">
                  <th className="p-5 font-bold">物品名称</th>
                  <th className="p-5 font-bold">分类</th>
                  <th className="p-5 font-bold text-center">当前库存</th>
                  <th className="p-5 font-bold text-right">单价</th>
                  <th className="p-5 font-bold text-right">总价值</th>
                  <th className="p-5 font-bold text-right">操作</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-50">
                {items.map(item => {
                  const isLow = item.quantity <= 5;
                  return (
                    <tr key={item.item_id} className="hover:bg-slate-50/50 transition-colors group">
                      <td className="p-5">
                        <div className="font-bold text-slate-800 flex items-center"><Package className={`w-4 h-4 mr-2 ${isLow ? 'text-orange-500' : 'text-emerald-600'}`} /> {item.name}</div>
                      </td>
                      <td className="p-5"><span className="bg-slate-100 text-slate-600 px-2 py-1 rounded-md text-xs font-bold">{item.category}</span></td>
                      <td className="p-5 text-center">
                        <div className="flex items-center justify-center gap-3">
                          <button onClick={() => updateQuantity(item.item_id, item.quantity - 1)} className="w-6 h-6 rounded-full bg-slate-100 hover:bg-slate-200 flex items-center justify-center text-slate-600 font-bold">-</button>
                          <span className={`text-lg font-black w-10 text-center ${isLow ? 'text-orange-600' : 'text-slate-800'}`}>{item.quantity}</span>
                          <button onClick={() => updateQuantity(item.item_id, item.quantity + 1)} className="w-6 h-6 rounded-full bg-slate-100 hover:bg-slate-200 flex items-center justify-center text-slate-600 font-bold">+</button>
                          <span className="text-xs text-slate-400 font-medium">{item.unit}</span>
                        </div>
                      </td>
                      <td className="p-5 text-right font-medium text-slate-500">¥{item.price}</td>
                      <td className="p-5 text-right font-bold text-slate-800">¥{(item.quantity * item.price).toFixed(2)}</td>
                      <td className="p-5 text-right">
                         <div className="flex justify-end gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                           <button onClick={() => openUsageModal(item)} className="text-blue-600 hover:bg-blue-50 px-3 py-1.5 rounded-lg text-sm font-bold flex items-center"><Send className="w-3 h-3 mr-1" /> 领用/退还</button>
                           <button onClick={() => openModal(item)} className="text-emerald-600 hover:bg-emerald-50 px-3 py-1.5 rounded-lg text-sm font-bold flex items-center"><Edit2 className="w-3 h-3 mr-1" /> 编辑</button>
                           <button onClick={() => handleDeleteItem(item.item_id, item.name)} className="text-red-600 hover:bg-red-50 px-3 py-1.5 rounded-lg text-sm font-bold flex items-center"><Trash2 className="w-3 h-3 mr-1" /> 删除</button>
                         </div>
                      </td>
                    </tr>
                  );
                })}
                {items.length === 0 && <tr><td colSpan={6} className="p-16 text-center text-slate-400">暂无库存数据</td></tr>}
              </tbody>
            </table>
          </div>
        </>
      )}

      {activeTab === 'usage' && (
        <div className="bg-white rounded-3xl shadow-sm border border-slate-100 overflow-hidden">
          <div className="p-6 border-b border-slate-100 bg-slate-50/50">
            <h2 className="text-lg font-bold text-slate-800 flex items-center">耗材领用与退还明细</h2>
          </div>
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="bg-slate-50/50 border-b border-slate-100 text-slate-500 text-xs uppercase tracking-wider">
                <th className="p-5 font-bold">时间</th>
                <th className="p-5 font-bold">操作人 (技师)</th>
                <th className="p-5 font-bold">物品</th>
                <th className="p-5 font-bold text-center">数量变动</th>
                <th className="p-5 font-bold">备注说明</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-50">
              {usageRecords.map(r => {
                const item = items.find(i => i.item_id === r.item_id);
                return (
                  <tr key={r.usage_id} className="hover:bg-slate-50/50 transition-colors">
                    <td className="p-5 text-sm text-slate-500 font-mono">{new Date(r.usage_date).toLocaleString()}</td>
                    <td className="p-5 font-bold text-slate-800">{r.staff_name}</td>
                    <td className="p-5 font-bold text-emerald-700">{item?.name || '未知物品'}</td>
                    <td className="p-5 text-center font-black">
                      {r.quantity > 0 
                        ? <span className="text-orange-600">-{r.quantity}</span> 
                        : <span className="text-emerald-600">+{Math.abs(r.quantity)}</span>} {item?.unit || ''}
                    </td>
                    <td className="p-5 text-sm text-slate-500">{r.notes || '-'}</td>
                  </tr>
                );
              })}
              {usageRecords.length === 0 && <tr><td colSpan={5} className="p-16 text-center text-slate-400">暂无领用/退还记录</td></tr>}
            </tbody>
          </table>
        </div>
      )}

      {/* 库存操作弹窗 */}
      {isModalOpen && (
        <div className="fixed inset-0 bg-slate-900/60 backdrop-blur-sm flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-3xl shadow-2xl w-full max-w-md overflow-hidden animate-in fade-in zoom-in duration-200">
            <div className="p-6 border-b border-slate-100 flex justify-between items-center bg-slate-50/50">
              <h2 className="text-xl font-bold text-slate-800">{editingId ? '编辑库存物品' : '新增入库物品'}</h2>
              <X onClick={() => setIsModalOpen(false)} className="w-6 h-6 text-slate-400 cursor-pointer hover:text-slate-600" />
            </div>
            <form onSubmit={handleSaveItem} className="p-6 space-y-5">
              <div><label className="block text-xs font-bold text-slate-500 uppercase mb-2">物品名称</label><input required value={formData.name} onChange={e => setFormData({...formData, name: e.target.value})} className="w-full px-4 py-3 bg-slate-50 border border-slate-100 rounded-xl focus:ring-2 focus:ring-emerald-500 outline-none font-medium" /></div>
              <div className="grid grid-cols-2 gap-4">
                <div><label className="block text-xs font-bold text-slate-500 uppercase mb-2">分类</label><select value={formData.category} onChange={e => setFormData({...formData, category: e.target.value})} className="w-full px-4 py-3 bg-slate-50 border border-slate-100 rounded-xl focus:ring-2 focus:ring-emerald-500 outline-none font-medium">
                  {categories.map(cat => <option key={cat.category_id} value={cat.name}>{cat.name}</option>)}
                </select></div>
                <div><label className="block text-xs font-bold text-slate-500 uppercase mb-2">单位</label><input required value={formData.unit} onChange={e => setFormData({...formData, unit: e.target.value})} className="w-full px-4 py-3 bg-slate-50 border border-slate-100 rounded-xl focus:ring-2 focus:ring-emerald-500 outline-none font-medium" /></div>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div><label className="block text-xs font-bold text-slate-500 uppercase mb-2">当前数量</label><input type="number" min="0" required value={formData.quantity} onChange={e => setFormData({...formData, quantity: parseInt(e.target.value) || 0})} className="w-full px-4 py-3 bg-slate-50 border border-slate-100 rounded-xl focus:ring-2 focus:ring-emerald-500 outline-none font-bold text-slate-800" /></div>
                <div><label className="block text-xs font-bold text-slate-500 uppercase mb-2">入库单价 (元)</label><input type="number" step="0.01" min="0" required value={formData.price} onChange={e => setFormData({...formData, price: parseFloat(e.target.value) || 0})} className="w-full px-4 py-3 bg-slate-50 border border-slate-100 rounded-xl focus:ring-2 focus:ring-emerald-500 outline-none font-bold text-blue-600" /></div>
              </div>
              <button type="submit" className="w-full py-4 mt-4 bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl font-bold shadow-lg transition-all text-lg">保存属性</button>
            </form>
          </div>
        </div>
      )}

      {/* 领用登记弹窗 */}
      {isUsageModalOpen && selectedItem && (
        <div className="fixed inset-0 bg-slate-900/60 backdrop-blur-sm flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-3xl shadow-2xl w-full max-w-md overflow-hidden animate-in fade-in zoom-in duration-200">
            <div className={`p-6 border-b border-slate-100 flex justify-between items-center ${usageData.action_type === 'return' ? 'bg-emerald-50/50' : 'bg-blue-50/50'}`}>
              <h2 className={`text-xl font-bold flex items-center ${usageData.action_type === 'return' ? 'text-emerald-900' : 'text-blue-900'}`}>
                <Send className={`w-5 h-5 mr-2 ${usageData.action_type === 'return' ? 'text-emerald-600' : 'text-blue-600'}`} /> 
                {usageData.action_type === 'return' ? '登记物品退还' : '登记物品领用'}
              </h2>
              <X onClick={() => setIsUsageModalOpen(false)} className="w-6 h-6 text-slate-400 cursor-pointer hover:text-slate-600" />
            </div>
            <form onSubmit={handleRecordUsage} className="p-6 space-y-5">
              <div className="flex gap-2 p-1 bg-slate-100 rounded-xl">
                <button type="button" onClick={() => setUsageData({...usageData, action_type: 'issue', quantity: 1})} className={`flex-1 py-2 text-sm font-bold rounded-lg transition-colors ${usageData.action_type === 'issue' ? 'bg-white text-blue-600 shadow-sm' : 'text-slate-500 hover:text-slate-700'}`}>员工领用</button>
                <button type="button" onClick={() => setUsageData({...usageData, action_type: 'return', quantity: 1})} className={`flex-1 py-2 text-sm font-bold rounded-lg transition-colors ${usageData.action_type === 'return' ? 'bg-white text-emerald-600 shadow-sm' : 'text-slate-500 hover:text-slate-700'}`}>多余退还</button>
              </div>

              <div className="p-4 bg-slate-50 rounded-xl border border-slate-100 flex justify-between items-center">
                <span className="font-bold text-slate-700">{selectedItem.name}</span>
                <span className="text-sm text-slate-500">当前剩余: <span className="font-black text-emerald-600">{selectedItem.quantity} {selectedItem.unit}</span></span>
              </div>
              <div>
                <label className="block text-xs font-bold text-slate-500 uppercase mb-2">{usageData.action_type === 'return' ? '退还人 (技师)' : '领用人 (技师)'}</label>
                <select required value={usageData.staff_name} onChange={e => setUsageData({...usageData, staff_name: e.target.value})} className={`w-full px-4 py-3 bg-white border border-slate-200 rounded-xl outline-none font-medium focus:ring-2 ${usageData.action_type === 'return' ? 'focus:ring-emerald-500' : 'focus:ring-blue-500'}`}>
                  {staff.map(s => <option key={s.staff_id} value={s.name}>{s.name} ({s.role})</option>)}
                  <option value="其它">其它/公共消耗</option>
                </select>
              </div>
              <div>
                <label className={`block text-xs font-bold uppercase mb-2 ${usageData.action_type === 'return' ? 'text-emerald-600' : 'text-orange-600'}`}>
                  {usageData.action_type === 'return' ? '本次退还数量' : '本次领用数量'}
                </label>
                <div className="relative">
                  <input type="number" min="1" max={usageData.action_type === 'return' ? undefined : selectedItem.quantity} required value={usageData.quantity} onChange={e => {
                    let val = parseInt(e.target.value) || 1;
                    if (usageData.action_type === 'issue' && val > selectedItem.quantity) val = selectedItem.quantity;
                    setUsageData({...usageData, quantity: val});
                  }} className={`w-full px-4 py-3 border-none rounded-xl outline-none font-black text-xl pr-12 focus:ring-2 ${usageData.action_type === 'return' ? 'bg-emerald-50 text-emerald-700 focus:ring-emerald-500' : 'bg-orange-50 text-orange-700 focus:ring-orange-500'}`} />
                  <span className={`absolute right-4 top-1/2 transform -translate-y-1/2 font-bold ${usageData.action_type === 'return' ? 'text-emerald-500' : 'text-orange-400'}`}>{selectedItem.unit}</span>
                </div>
              </div>
              <div>
                <label className="block text-xs font-bold text-slate-500 uppercase mb-2">事由/备注 (选填)</label>
                <input value={usageData.notes} onChange={e => setUsageData({...usageData, notes: e.target.value})} className={`w-full px-4 py-3 bg-slate-50 border border-slate-100 rounded-xl outline-none font-medium focus:ring-2 ${usageData.action_type === 'return' ? 'focus:ring-emerald-500' : 'focus:ring-blue-500'}`} placeholder="例如：给某某客户做身体..." />
              </div>
              <button type="submit" className={`w-full py-4 mt-4 text-white rounded-xl font-bold shadow-lg transition-all text-lg ${usageData.action_type === 'return' ? 'bg-emerald-600 hover:bg-emerald-700' : 'bg-blue-600 hover:bg-blue-700'}`}>
                {usageData.action_type === 'return' ? '确认退还并增加库存' : '确认领用并扣减库存'}
              </button>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

export default Inventory;