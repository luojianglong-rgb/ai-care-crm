import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Settings as SettingsIcon, Plus, X, ListOrdered, Edit2, Package, Info, Zap, Shield, Brain, Trash2, UserCog } from 'lucide-react';
import { useLicenseStatus } from '../hooks/useLicenseStatus';

interface ServiceItem {
  item_id: string;
  name: string;
  description: string;
}

interface InventoryCategory {
  category_id: string;
  name: string;
  description: string;
}

interface SystemInfo {
  store: { name: string; business_type: string };
  terminology: { staff_title: string; analysis_name: string; plan_name: string };
  license: {
    tier: string; valid: boolean; message: string;
    expire_date: string; days_remaining: number; machine_id: string;
    // 试用 / 宽限期扩展字段
    status?: 'active' | 'trial_active' | 'grace_period' | 'expired' | 'invalid' | 'unactivated';
    is_trial?: boolean;
    in_grace_period?: boolean;
    grace_days_remaining?: number;
    read_only_mode?: boolean;
  };
  llm: { mode: string; provider: string; model: string; available: boolean };
  version: string;
}

interface QuotaInfo {
  month: string;
  tier: string;
  analysis: { used: number; limit: number; remaining: number; unlimited: boolean };
  plan: { used: number; limit: number; remaining: number; unlimited: boolean };
  content: { used: number; limit: number; remaining: number; unlimited: boolean };
}

const API = import.meta.env.VITE_API_URL || '';

const tierLabels: Record<string, string> = { basic: '基础版', pro: '专业版', business: '至尊版' };
const bizTypeLabels: Record<string, string> = {
  tcm_wellness: '养生馆', spa: 'SPA 水疗', hair_salon: '美发沙龙',
  nail_lash: '美甲美睫', skin_care: '皮肤管理', postpartum: '产后修复', general: '通用模式'
};

interface AdminUser {
  id: string;
  username: string;
  display_name: string;
  is_active: number;
  created_at?: string;
}

const Settings = () => {
  const [activeTab, setActiveTab] = useState<'system' | 'services' | 'categories' | 'admins'>('system');
  const { refresh: refreshLicenseStatus } = useLicenseStatus();

  // 服务项目状态
  const [services, setServices] = useState<ServiceItem[]>([]);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingServiceId, setEditingServiceId] = useState<string | null>(null);
  const [serviceFormData, setServiceFormData] = useState({ name: '', description: '' });

  // 系统信息状态
  const [sysInfo, setSysInfo] = useState<SystemInfo | null>(null);
  const [quotaInfo, setQuotaInfo] = useState<QuotaInfo | null>(null);

  // 耗材分类状态
  const [categories, setCategories] = useState<InventoryCategory[]>([]);
  const [isCategoryModalOpen, setIsCategoryModalOpen] = useState(false);
  const [editingCategoryId, setEditingCategoryId] = useState<string | null>(null);
  const [categoryFormData, setCategoryFormData] = useState({ name: '', description: '' });

  // 管理员状态
  const [admins, setAdmins] = useState<AdminUser[]>([]);
  const [isAdminModalOpen, setIsAdminModalOpen] = useState(false);
  const [editingAdminId, setEditingAdminId] = useState<string | null>(null);
  const [adminFormData, setAdminFormData] = useState({ username: '', password: '', display_name: '' });

  // 激活码状态
  const [licenseKey, setLicenseKey] = useState('');
  const [activating, setActivating] = useState(false);
  const [activateMessage, setActivateMessage] = useState<{ type: 'success' | 'error', text: string } | null>(null);

  const fetchServices = async () => {
    try {
      const res = await axios.get(`${API}/api/v1/services/`);
      setServices(res.data);
    } catch (e) { console.error("加载服务项目失败", e); }
  };

  const fetchCategories = async () => {
    try {
      const res = await axios.get(`${API}/api/v1/inventory/categories/`);
      setCategories(res.data);
    } catch (e) { console.error("加载耗材分类失败", e); }
  };

  const fetchSystemInfo = async () => {
    try {
      const [infoRes, quotaRes] = await Promise.all([
        axios.get(`${API}/api/v1/config/info`),
        axios.get(`${API}/api/v1/config/quota`)
      ]);
      setSysInfo(infoRes.data);
      setQuotaInfo(quotaRes.data);
    } catch (e) { console.error("加载系统信息失败", e); }
  };

  const fetchAdmins = async () => {
    try {
      const res = await axios.get(`${API}/api/v1/auth/admins`);
      setAdmins(res.data);
    } catch (e) { console.error("加载管理员失败", e); }
  };

  const fetchData = () => {
    fetchSystemInfo();
    fetchServices();
    fetchCategories();
    fetchAdmins();
  };

  useEffect(() => { fetchData(); }, []);

  const openModal = (service?: ServiceItem) => {
    if (service) {
      setEditingServiceId(service.item_id);
      setServiceFormData({ name: service.name, description: service.description || '' });
    } else {
      setEditingServiceId(null);
      setServiceFormData({ name: '', description: '' });
    }
    setIsModalOpen(true);
  };

  const handleSaveService = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      if (editingServiceId) {
        await axios.put(`${API}/api/v1/services/${editingServiceId}`, serviceFormData);
      } else {
        await axios.post(`${API}/api/v1/services/`, serviceFormData);
      }
      setIsModalOpen(false);
      fetchServices();
    } catch (error) { alert('保存服务项目失败'); }
  };

  // 耗材分类相关方法
  const openCategoryModal = (category?: InventoryCategory) => {
    if (category) {
      setEditingCategoryId(category.category_id);
      setCategoryFormData({ name: category.name, description: category.description || '' });
    } else {
      setEditingCategoryId(null);
      setCategoryFormData({ name: '', description: '' });
    }
    setIsCategoryModalOpen(true);
  };

  const handleSaveCategory = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      if (editingCategoryId) {
        await axios.put(`${API}/api/v1/inventory/categories/${editingCategoryId}`, categoryFormData);
      } else {
        await axios.post(`${API}/api/v1/inventory/categories/`, categoryFormData);
      }
      setIsCategoryModalOpen(false);
      fetchCategories();
    } catch (error) { alert('保存耗材分类失败'); }
  };

  const handleDeleteService = async (itemId: string, name: string) => {
    if (!confirm(`确定要停用服务项目「${name}」吗？`)) return;
    try {
      await axios.delete(`${API}/api/v1/services/${itemId}`);
      fetchServices();
    } catch (error) { alert('删除失败'); }
  };

  const handleDeleteCategory = async (categoryId: string, name: string) => {
    if (!confirm(`确定要停用耗材分类「${name}」吗？`)) return;
    try {
      await axios.delete(`${API}/api/v1/inventory/categories/${categoryId}`);
      fetchCategories();
    } catch (error) { alert('删除失败'); }
  };

  const openAdminModal = (admin?: AdminUser) => {
    if (admin) {
      setEditingAdminId(admin.id);
      setAdminFormData({ username: admin.username, password: '', display_name: admin.display_name || '' });
    } else {
      setEditingAdminId(null);
      setAdminFormData({ username: '', password: '', display_name: '' });
    }
    setIsAdminModalOpen(true);
  };

  const handleSaveAdmin = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      if (editingAdminId) {
        const payload: any = {};
        if (adminFormData.display_name) payload.display_name = adminFormData.display_name;
        if (adminFormData.password) payload.password = adminFormData.password;
        await axios.put(`${API}/api/v1/auth/admins/${editingAdminId}`, payload);
      } else {
        await axios.post(`${API}/api/v1/auth/admins`, adminFormData);
      }
      setIsAdminModalOpen(false);
      fetchAdmins();
    } catch (error: any) { alert(error.response?.data?.detail || '保存失败'); }
  };

  const handleDeleteAdmin = async (adminId: string, username: string) => {
    if (!confirm(`确定要删除管理员「${username}」吗？`)) return;
    try {
      await axios.delete(`${API}/api/v1/auth/admins/${adminId}`);
      fetchAdmins();
    } catch (error: any) { alert(error.response?.data?.detail || '删除失败'); }
  };

  const handleActivateLicense = async () => {
    if (!licenseKey.trim()) {
      setActivateMessage({ type: 'error', text: '请输入激活码' });
      return;
    }
    setActivating(true);
    setActivateMessage(null);
    try {
      const res = await axios.post(`${API}/api/v1/config/activate`, { key: licenseKey.trim() });
      if (res.data.valid) {
        const trialLabel = res.data.is_trial ? '（试用版）' : '';
        setActivateMessage({ type: 'success', text: `激活成功！已升级为 ${tierLabels[res.data.tier] || res.data.tier}${trialLabel}` });
        fetchSystemInfo();
        refreshLicenseStatus();  // 立即刷新全局 license 状态，让横幅/badge 同步更新
        setLicenseKey('');
      } else {
        setActivateMessage({ type: 'error', text: res.data.message });
      }
    } catch (error: any) {
      setActivateMessage({ type: 'error', text: error.response?.data?.detail || '激活失败' });
    } finally {
      setActivating(false);
    }
  };

  return (
    <div className="p-8 max-w-6xl mx-auto">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-slate-800 tracking-tight flex items-center">
          <SettingsIcon className="w-6 h-6 mr-3 text-slate-500" />
          系统设置
        </h1>
        <p className="text-slate-500 mt-1 text-sm">系统配置、服务项目与耗材分类管理</p>
      </div>

      {/* Tab 切换 */}
      <div className="flex gap-4 mb-6">
        <button
          onClick={() => setActiveTab('system')}
          className={`px-6 py-3 rounded-xl font-bold flex items-center transition-colors ${
            activeTab === 'system'
              ? 'bg-emerald-600 text-white'
              : 'bg-white text-slate-500 hover:bg-slate-50 border border-slate-200'
          }`}
        >
          <Info className="w-5 h-5 mr-2" /> 系统信息
        </button>
        <button
          onClick={() => setActiveTab('services')}
          className={`px-6 py-3 rounded-xl font-bold flex items-center transition-colors ${
            activeTab === 'services'
              ? 'bg-emerald-600 text-white'
              : 'bg-white text-slate-500 hover:bg-slate-50 border border-slate-200'
          }`}
        >
          <ListOrdered className="w-5 h-5 mr-2" /> 服务项目配置
        </button>
        <button
          onClick={() => setActiveTab('categories')}
          className={`px-6 py-3 rounded-xl font-bold flex items-center transition-colors ${
            activeTab === 'categories'
              ? 'bg-emerald-600 text-white'
              : 'bg-white text-slate-500 hover:bg-slate-50 border border-slate-200'
          }`}
        >
          <Package className="w-5 h-5 mr-2" /> 耗材分类管理
        </button>
        <button
          onClick={() => setActiveTab('admins')}
          className={`px-6 py-3 rounded-xl font-bold flex items-center transition-colors ${
            activeTab === 'admins'
              ? 'bg-emerald-600 text-white'
              : 'bg-white text-slate-500 hover:bg-slate-50 border border-slate-200'
          }`}
        >
          <UserCog className="w-5 h-5 mr-2" /> 管理员
        </button>
      </div>

      {/* 系统信息 Tab */}
      {activeTab === 'system' && sysInfo && quotaInfo && (
        <div className="space-y-6">
          {/* 门店与业态 */}
          <div className="bg-white rounded-2xl shadow-sm border border-slate-100 p-6">
            <h3 className="text-sm font-bold text-slate-500 uppercase mb-4 flex items-center">
              <Info className="w-4 h-4 mr-2" /> 门店信息
            </h3>
            <div className="grid grid-cols-3 gap-6">
              <div>
                <span className="text-xs text-slate-400 uppercase font-bold">门店名称</span>
                <p className="text-lg font-bold text-slate-800 mt-1">{sysInfo.store.name}</p>
              </div>
              <div>
                <span className="text-xs text-slate-400 uppercase font-bold">业态类型</span>
                <p className="text-lg font-bold text-slate-800 mt-1">{bizTypeLabels[sysInfo.store.business_type] || sysInfo.store.business_type}</p>
              </div>
              <div>
                <span className="text-xs text-slate-400 uppercase font-bold">系统版本</span>
                <p className="text-lg font-bold text-slate-800 mt-1">v{sysInfo.version}</p>
              </div>
            </div>
            <div className="grid grid-cols-3 gap-6 mt-4 pt-4 border-t border-slate-100">
              <div>
                <span className="text-xs text-slate-400 uppercase font-bold">员工称谓</span>
                <p className="text-sm font-medium text-slate-600 mt-1">{sysInfo.terminology.staff_title}</p>
              </div>
              <div>
                <span className="text-xs text-slate-400 uppercase font-bold">分析功能</span>
                <p className="text-sm font-medium text-slate-600 mt-1">{sysInfo.terminology.analysis_name}</p>
              </div>
              <div>
                <span className="text-xs text-slate-400 uppercase font-bold">方案名称</span>
                <p className="text-sm font-medium text-slate-600 mt-1">{sysInfo.terminology.plan_name}</p>
              </div>
            </div>
          </div>

          {/* 授权与套餐 */}
          <div className="bg-white rounded-2xl shadow-sm border border-slate-100 p-6">
            <h3 className="text-sm font-bold text-slate-500 uppercase mb-4 flex items-center">
              <Shield className="w-4 h-4 mr-2" /> 授权信息
            </h3>
            <div className="grid grid-cols-2 gap-6">
              <div>
                <span className="text-xs text-slate-400 uppercase font-bold">当前套餐</span>
                <p className="mt-1 flex items-center gap-2">
                  <span className={`inline-flex items-center px-3 py-1 rounded-full text-sm font-bold ${
                    sysInfo.license.tier === 'business' ? 'bg-purple-100 text-purple-700' :
                    sysInfo.license.tier === 'pro' ? 'bg-blue-100 text-blue-700' :
                    'bg-slate-100 text-slate-600'
                  }`}>
                    {tierLabels[sysInfo.license.tier] || sysInfo.license.tier}
                  </span>
                  {sysInfo.license.is_trial && (
                    <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-bold bg-sky-100 text-sky-700">
                      试用版
                    </span>
                  )}
                </p>
              </div>
              <div>
                <span className="text-xs text-slate-400 uppercase font-bold">激活状态</span>
                <p className="mt-1">
                  {sysInfo.license.status === 'grace_period' ? (
                    <span className="text-red-600 font-bold text-sm">
                      只读模式 · 宽限期剩余 {sysInfo.license.grace_days_remaining} 天
                    </span>
                  ) : sysInfo.license.status === 'trial_active' ? (
                    <span className="text-blue-600 font-bold text-sm">
                      试用版 · 剩余 {sysInfo.license.days_remaining} 天
                    </span>
                  ) : sysInfo.license.valid ? (
                    <span className="text-emerald-600 font-bold text-sm">已激活 · 剩余 {sysInfo.license.days_remaining} 天</span>
                  ) : (
                    <span className="text-slate-500 font-medium text-sm">{sysInfo.license.message}</span>
                  )}
                </p>
              </div>
            </div>
            {sysInfo.license.expire_date && (
              <div className="mt-4 pt-4 border-t border-slate-100">
                <span className="text-xs text-slate-400 uppercase font-bold">到期日期</span>
                <p className="text-sm font-medium text-slate-600 mt-1">{sysInfo.license.expire_date}</p>
              </div>
            )}
            {/* 宽限期只读提示 */}
            {sysInfo.license.read_only_mode && (
              <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded-xl">
                <p className="text-sm text-red-700 font-medium">
                  ⚠️ 试用已到期，系统已进入只读模式。您仍可查看数据，但无法新增、编辑或删除。
                  宽限期结束后所有功能将受限，请尽快联系销售激活正式版。
                </p>
              </div>
            )}
            <div className="mt-4 pt-4 border-t border-slate-100">
              <span className="text-xs text-slate-400 uppercase font-bold">本机特征码</span>
              <p className="text-xs font-mono text-slate-500 mt-1 bg-slate-50 px-3 py-2 rounded-lg select-all">{sysInfo.license.machine_id}</p>
              <p className="text-xs text-slate-400 mt-1">购买激活码时需提供此特征码</p>
            </div>
            {/* 激活码输入 */}
            <div className="mt-4 pt-4 border-t border-slate-100">
              <label className="text-xs text-slate-400 uppercase font-bold block mb-2">激活码</label>
              <div className="flex gap-2">
                <input
                  type="text"
                  value={licenseKey}
                  onChange={e => setLicenseKey(e.target.value)}
                  placeholder="输入 CARE-XXXX-XXXX-... 格式的激活码"
                  className="flex-1 px-4 py-2 bg-slate-50 border border-slate-200 rounded-xl text-sm font-mono focus:ring-2 focus:ring-emerald-500 outline-none"
                />
                <button
                  onClick={handleActivateLicense}
                  disabled={activating}
                  className="px-6 py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl text-sm font-bold transition-all disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {activating ? '激活中...' : '激活'}
                </button>
              </div>
              {activateMessage && (
                <p className={`text-sm mt-2 ${activateMessage.type === 'success' ? 'text-emerald-600' : 'text-red-500'}`}>
                  {activateMessage.text}
                </p>
              )}
            </div>
          </div>

          {/* AI 配置 */}
          <div className="bg-white rounded-2xl shadow-sm border border-slate-100 p-6">
            <h3 className="text-sm font-bold text-slate-500 uppercase mb-4 flex items-center">
              <Brain className="w-4 h-4 mr-2" /> AI 大模型配置
            </h3>
            <div className="grid grid-cols-4 gap-6">
              <div>
                <span className="text-xs text-slate-400 uppercase font-bold">调用模式</span>
                <p className="text-sm font-bold text-slate-700 mt-1">{sysInfo.llm.mode === 'direct' ? '直连模式' : '代理模式'}</p>
              </div>
              <div>
                <span className="text-xs text-slate-400 uppercase font-bold">模型提供商</span>
                <p className="text-sm font-bold text-slate-700 mt-1">{sysInfo.llm.provider}</p>
              </div>
              <div>
                <span className="text-xs text-slate-400 uppercase font-bold">模型名称</span>
                <p className="text-sm font-bold text-slate-700 mt-1">{sysInfo.llm.model}</p>
              </div>
              <div>
                <span className="text-xs text-slate-400 uppercase font-bold">连接状态</span>
                <p className="mt-1">
                  {sysInfo.llm.available ? (
                    <span className="inline-flex items-center text-sm text-emerald-600 font-bold"><Zap className="w-4 h-4 mr-1" /> 已就绪</span>
                  ) : (
                    <span className="text-orange-500 font-bold text-sm">未配置</span>
                  )}
                </p>
              </div>
            </div>
          </div>

          {/* AI 额度 */}
          <div className="bg-white rounded-2xl shadow-sm border border-slate-100 p-6">
            <h3 className="text-sm font-bold text-slate-500 uppercase mb-4 flex items-center">
              <Zap className="w-4 h-4 mr-2" /> AI 额度使用 · {quotaInfo.month}
            </h3>
            <div className="grid grid-cols-3 gap-6">
              {[
                { label: '专业分析', data: quotaInfo.analysis, color: 'emerald' },
                { label: '方案生成', data: quotaInfo.plan, color: 'blue' },
                { label: '营销文案', data: quotaInfo.content, color: 'purple' },
              ].map(({ label, data, color }) => (
                <div key={label}>
                  <div className="flex justify-between text-sm mb-2">
                    <span className="text-slate-600 font-medium">{label}</span>
                    <span className="text-slate-500 font-bold">
                      {data.used} / {data.unlimited ? '∞' : data.limit}
                    </span>
                  </div>
                  {!data.unlimited ? (
                    <div className="w-full h-3 bg-slate-100 rounded-full overflow-hidden">
                      <div
                        className={`h-full rounded-full transition-all ${
                          data.limit > 0 && data.used / data.limit > 0.8 ? 'bg-orange-500' : `bg-${color}-500`
                        }`}
                        style={{ width: `${data.limit > 0 ? Math.min(100, (data.used / data.limit) * 100) : 0}%` }}
                      />
                    </div>
                  ) : (
                    <div className="text-xs text-slate-400 mt-1">不限额度</div>
                  )}
                  {!data.unlimited && (
                    <p className="text-xs text-slate-400 mt-1">剩余 {data.remaining} 次</p>
                  )}
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {activeTab === 'system' && (!sysInfo || !quotaInfo) && (
        <div className="bg-white rounded-2xl shadow-sm border border-slate-100 p-12 text-center text-slate-400">
          加载系统信息中...
        </div>
      )}

      {activeTab === 'services' && (
        <div className="bg-white rounded-3xl shadow-sm border border-slate-100 overflow-hidden">
          <div className="p-6 border-b border-slate-100 bg-slate-50/50 flex justify-between items-center">
            <h2 className="text-lg font-bold text-slate-800 flex items-center">
              <ListOrdered className="w-5 h-5 mr-2 text-emerald-600" />
              店内服务项目配置
            </h2>
            <button onClick={() => openModal()} className="bg-emerald-600 hover:bg-emerald-700 text-white px-4 py-2 rounded-xl flex items-center text-sm font-bold transition-all shadow-sm">
              <Plus className="w-4 h-4 mr-1" /> 新增项目
            </button>
          </div>
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="bg-slate-50 border-b border-slate-100 text-slate-500 text-xs uppercase tracking-wider">
                <th className="p-5 font-bold">项目名称</th>
                <th className="p-5 font-bold w-1/2">项目描述</th>
                <th className="p-5 font-bold text-right">操作</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-50">
              {services.map(s => (
                <tr key={s.item_id} className="hover:bg-slate-50/50 transition-colors group">
                  <td className="p-5 font-bold text-slate-800">{s.name}</td>
                  <td className="p-5 text-sm text-slate-500">{s.description || '-'}</td>
                  <td className="p-5 text-right">
                    <div className="flex gap-2 justify-end">
                      <button onClick={() => openModal(s)} className="text-emerald-600 bg-emerald-50 px-3 py-1.5 rounded-lg text-sm font-bold inline-flex items-center opacity-0 group-hover:opacity-100 transition-opacity">
                        <Edit2 className="w-3 h-3 mr-1" /> 修改
                      </button>
                      <button onClick={() => handleDeleteService(s.item_id, s.name)} className="text-red-600 bg-red-50 px-3 py-1.5 rounded-lg text-sm font-bold inline-flex items-center opacity-0 group-hover:opacity-100 transition-opacity">
                        <Trash2 className="w-3 h-3 mr-1" /> 停用
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
              {services.length === 0 && <tr><td colSpan={3} className="p-12 text-center text-slate-400">暂无数据</td></tr>}
            </tbody>
          </table>
        </div>
      )}

      {activeTab === 'categories' && (
        <div className="bg-white rounded-3xl shadow-sm border border-slate-100 overflow-hidden">
          <div className="p-6 border-b border-slate-100 bg-slate-50/50 flex justify-between items-center">
            <h2 className="text-lg font-bold text-slate-800 flex items-center">
              <Package className="w-5 h-5 mr-2 text-emerald-600" />
              耗材分类列表
            </h2>
            <button onClick={() => openCategoryModal()} className="bg-emerald-600 hover:bg-emerald-700 text-white px-4 py-2 rounded-xl flex items-center text-sm font-bold transition-all shadow-sm">
              <Plus className="w-4 h-4 mr-1" /> 新增分类
            </button>
          </div>
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="bg-slate-50 border-b border-slate-100 text-slate-500 text-xs uppercase tracking-wider">
                <th className="p-5 font-bold">分类名称</th>
                <th className="p-5 font-bold w-1/2">分类描述</th>
                <th className="p-5 font-bold text-right">操作</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-50">
              {categories.map(c => (
                <tr key={c.category_id} className="hover:bg-slate-50/50 transition-colors group">
                  <td className="p-5 font-bold text-slate-800">{c.name}</td>
                  <td className="p-5 text-sm text-slate-500">{c.description || '-'}</td>
                  <td className="p-5 text-right">
                    <div className="flex gap-2 justify-end">
                      <button onClick={() => openCategoryModal(c)} className="text-emerald-600 bg-emerald-50 px-3 py-1.5 rounded-lg text-sm font-bold inline-flex items-center opacity-0 group-hover:opacity-100 transition-opacity">
                        <Edit2 className="w-3 h-3 mr-1" /> 修改
                      </button>
                      <button onClick={() => handleDeleteCategory(c.category_id, c.name)} className="text-red-600 bg-red-50 px-3 py-1.5 rounded-lg text-sm font-bold inline-flex items-center opacity-0 group-hover:opacity-100 transition-opacity">
                        <Trash2 className="w-3 h-3 mr-1" /> 停用
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
              {categories.length === 0 && <tr><td colSpan={3} className="p-12 text-center text-slate-400">暂无分类数据</td></tr>}
            </tbody>
          </table>
        </div>
      )}

      {/* 服务项目弹窗 */}
      {isModalOpen && (
        <div className="fixed inset-0 bg-slate-900/60 backdrop-blur-sm flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-3xl shadow-2xl w-full max-w-md overflow-hidden animate-in fade-in zoom-in duration-200">
            <div className="p-6 border-b border-slate-100 flex justify-between items-center bg-slate-50/50">
              <h2 className="text-xl font-bold text-slate-800">{editingServiceId ? '修改服务项目' : '新增服务项目'}</h2>
              <X onClick={() => setIsModalOpen(false)} className="w-6 h-6 text-slate-400 cursor-pointer hover:text-slate-600" />
            </div>
            <form onSubmit={handleSaveService} className="p-6 space-y-5">
              <div>
                <label className="block text-xs font-bold text-slate-500 uppercase mb-2">项目名称</label>
                <input required value={serviceFormData.name} onChange={e => setServiceFormData({...serviceFormData, name: e.target.value})} className="w-full px-4 py-3 bg-slate-50 border border-slate-100 rounded-xl focus:ring-2 focus:ring-emerald-500 outline-none font-medium" placeholder="如：肩颈疏通" />
              </div>
              <div>
                <label className="block text-xs font-bold text-slate-500 uppercase mb-2">项目描述</label>
                <textarea rows={4} value={serviceFormData.description} onChange={e => setServiceFormData({...serviceFormData, description: e.target.value})} className="w-full px-4 py-3 bg-slate-50 border border-slate-100 rounded-xl focus:ring-2 focus:ring-emerald-500 outline-none text-sm resize-none" placeholder="简要描述项目功效或内容..." />
              </div>
              <button type="submit" className="w-full py-4 mt-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl font-bold shadow-lg transition-all">
                保存项目配置
              </button>
            </form>
          </div>
        </div>
      )}

      {/* 管理员 Tab */}
      {activeTab === 'admins' && (
        <div className="bg-white rounded-3xl shadow-sm border border-slate-100 overflow-hidden">
          <div className="p-6 border-b border-slate-100 bg-slate-50/50 flex justify-between items-center">
            <h2 className="text-lg font-bold text-slate-800 flex items-center">
              <UserCog className="w-5 h-5 mr-2 text-emerald-600" />
              管理员账号
            </h2>
            <button onClick={() => openAdminModal()} className="bg-emerald-600 hover:bg-emerald-700 text-white px-4 py-2 rounded-xl flex items-center text-sm font-bold transition-all shadow-sm">
              <Plus className="w-4 h-4 mr-1" /> 新增管理员
            </button>
          </div>
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="bg-slate-50 border-b border-slate-100 text-slate-500 text-xs uppercase tracking-wider">
                <th className="p-5 font-bold">用户名</th>
                <th className="p-5 font-bold">显示名称</th>
                <th className="p-5 font-bold">创建时间</th>
                <th className="p-5 font-bold text-right">操作</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-50">
              {admins.map(a => (
                <tr key={a.id} className="hover:bg-slate-50/50 transition-colors group">
                  <td className="p-5 font-bold text-slate-800">{a.username}</td>
                  <td className="p-5 text-sm text-slate-500">{a.display_name || '-'}</td>
                  <td className="p-5 text-sm text-slate-400">{a.created_at?.slice(0, 10)}</td>
                  <td className="p-5 text-right">
                    <div className="flex gap-2 justify-end">
                      <button onClick={() => openAdminModal(a)} className="text-emerald-600 bg-emerald-50 px-3 py-1.5 rounded-lg text-sm font-bold inline-flex items-center opacity-0 group-hover:opacity-100 transition-opacity">
                        <Edit2 className="w-3 h-3 mr-1" /> 修改
                      </button>
                      <button onClick={() => handleDeleteAdmin(a.id, a.username)} className="text-red-600 bg-red-50 px-3 py-1.5 rounded-lg text-sm font-bold inline-flex items-center opacity-0 group-hover:opacity-100 transition-opacity">
                        <Trash2 className="w-3 h-3 mr-1" /> 删除
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
              {admins.length === 0 && <tr><td colSpan={4} className="p-12 text-center text-slate-400">暂无管理员</td></tr>}
            </tbody>
          </table>
        </div>
      )}

      {/* 管理员弹窗 */}
      {isAdminModalOpen && (
        <div className="fixed inset-0 bg-slate-900/60 backdrop-blur-sm flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-3xl shadow-2xl w-full max-w-md overflow-hidden animate-in fade-in zoom-in duration-200">
            <div className="p-6 border-b border-slate-100 flex justify-between items-center bg-slate-50/50">
              <h2 className="text-xl font-bold text-slate-800">{editingAdminId ? '修改管理员' : '新增管理员'}</h2>
              <X onClick={() => setIsAdminModalOpen(false)} className="w-6 h-6 text-slate-400 cursor-pointer hover:text-slate-600" />
            </div>
            <form onSubmit={handleSaveAdmin} className="p-6 space-y-5">
              <div>
                <label className="block text-xs font-bold text-slate-500 uppercase mb-2">用户名</label>
                <input required disabled={!!editingAdminId} value={adminFormData.username}
                  onChange={e => setAdminFormData({...adminFormData, username: e.target.value})}
                  className="w-full px-4 py-3 bg-slate-50 border border-slate-100 rounded-xl focus:ring-2 focus:ring-emerald-500 outline-none font-medium disabled:opacity-50"
                  placeholder="登录用户名" />
              </div>
              <div>
                <label className="block text-xs font-bold text-slate-500 uppercase mb-2">
                  {editingAdminId ? '新密码（留空则不修改）' : '登录密码'}
                </label>
                <input type="password" required={!editingAdminId} value={adminFormData.password}
                  onChange={e => setAdminFormData({...adminFormData, password: e.target.value})}
                  className="w-full px-4 py-3 bg-slate-50 border border-slate-100 rounded-xl focus:ring-2 focus:ring-emerald-500 outline-none font-medium"
                  placeholder={editingAdminId ? '留空则不修改' : '请设置密码'} />
              </div>
              <div>
                <label className="block text-xs font-bold text-slate-500 uppercase mb-2">显示名称</label>
                <input value={adminFormData.display_name}
                  onChange={e => setAdminFormData({...adminFormData, display_name: e.target.value})}
                  className="w-full px-4 py-3 bg-slate-50 border border-slate-100 rounded-xl focus:ring-2 focus:ring-emerald-500 outline-none font-medium"
                  placeholder="如：店长、管理员" />
              </div>
              <button type="submit" className="w-full py-4 mt-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl font-bold shadow-lg transition-all">
                {editingAdminId ? '保存修改' : '创建管理员'}
              </button>
            </form>
          </div>
        </div>
      )}

      {/* 耗材分类弹窗 */}
      {isCategoryModalOpen && (
        <div className="fixed inset-0 bg-slate-900/60 backdrop-blur-sm flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-3xl shadow-2xl w-full max-w-md overflow-hidden animate-in fade-in zoom-in duration-200">
            <div className="p-6 border-b border-slate-100 flex justify-between items-center bg-slate-50/50">
              <h2 className="text-xl font-bold text-slate-800">{editingCategoryId ? '修改耗材分类' : '新增耗材分类'}</h2>
              <X onClick={() => setIsCategoryModalOpen(false)} className="w-6 h-6 text-slate-400 cursor-pointer hover:text-slate-600" />
            </div>
            <form onSubmit={handleSaveCategory} className="p-6 space-y-5">
              <div>
                <label className="block text-xs font-bold text-slate-500 uppercase mb-2">分类名称</label>
                <input required value={categoryFormData.name} onChange={e => setCategoryFormData({...categoryFormData, name: e.target.value})} className="w-full px-4 py-3 bg-slate-50 border border-slate-100 rounded-xl focus:ring-2 focus:ring-emerald-500 outline-none font-medium" placeholder="如：精油/原液" />
              </div>
              <div>
                <label className="block text-xs font-bold text-slate-500 uppercase mb-2">分类描述</label>
                <textarea rows={4} value={categoryFormData.description} onChange={e => setCategoryFormData({...categoryFormData, description: e.target.value})} className="w-full px-4 py-3 bg-slate-50 border border-slate-100 rounded-xl focus:ring-2 focus:ring-emerald-500 outline-none text-sm resize-none" placeholder="简要描述该分类的用途或范围..." />
              </div>
              <button type="submit" className="w-full py-4 mt-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl font-bold shadow-lg transition-all">
                保存分类配置
              </button>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

export default Settings;
