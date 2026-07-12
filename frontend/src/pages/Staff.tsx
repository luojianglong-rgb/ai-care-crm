import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Users, Plus, X, Edit2, Trash2 } from 'lucide-react';
import { ReadOnlyButton } from '../components/ReadOnlyGuard';

interface ServiceItem {
  item_id: string;
  name: string;
  description: string;
}

interface StaffMember {
  staff_id: string;
  name: string;
  role: string;
  phone: string;
  services_supported: string[];
}

interface Terminology {
  staff_title: string;
  analysis_name: string;
  plan_name: string;
}

const Staff = () => {
  // 员工状态
  const [staff, setStaff] = useState<StaffMember[]>([]);
  const [services, setServices] = useState<ServiceItem[]>([]);
  const [terminology, setTerminology] = useState<Terminology | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingStaffId, setEditingStaffId] = useState<string | null>(null);
  const [staffFormData, setStaffFormData] = useState({
    name: '',
    role: '技师',
    phone: '',
    password: '',
    services_supported: [] as string[]
  });

  const fetchData = async () => {
    try {
      const [staffRes, servicesRes, configRes] = await Promise.all([
        axios.get('/api/v1/services/staff/'),
        axios.get('/api/v1/services/'),
        axios.get('/api/v1/config/info')
      ]);
      setStaff(staffRes.data);
      setServices(servicesRes.data);
      setTerminology(configRes.data.terminology);

      // 根据业态更新默认角色
      if (configRes.data.terminology?.staff_title) {
        setStaffFormData(prev => ({ ...prev, role: configRes.data.terminology.staff_title }));
      }
    } catch (e) {
      console.error("加载数据失败", e);
    }
  };

  useEffect(() => { fetchData(); }, []);

  const handleDeleteStaff = async (staffId: string, name: string) => {
    if (!confirm(`确定要删除员工「${name}」吗？`)) return;
    try {
      await axios.delete(`/api/v1/services/staff/${staffId}`);
      fetchData();
    } catch (error) { alert('删除失败'); }
  };

  const openModal = (member?: StaffMember) => {
    if (member) {
      setEditingStaffId(member.staff_id);

      let parsedServices: string[] = [];
      if (Array.isArray(member.services_supported)) {
        parsedServices = member.services_supported;
      } else if (typeof member.services_supported === 'string') {
        try { parsedServices = JSON.parse(member.services_supported); } catch(e) {}
      }

      setStaffFormData({
        name: member.name,
        role: member.role,
        phone: member.phone || '',
        password: '',
        services_supported: parsedServices
      });
    } else {
      setEditingStaffId(null);
      // 新增员工时，使用业态默认称谓
      setStaffFormData({
        name: '',
        role: terminology?.staff_title || '技师',
        phone: '',
        password: '',
        services_supported: []
      });
    }
    setIsModalOpen(true);
  };

  const handleSaveStaff = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      if (editingStaffId) {
        await axios.put(`/api/v1/services/staff/${editingStaffId}`, staffFormData);
      } else {
        await axios.post('/api/v1/services/staff/', staffFormData);
      }
      setIsModalOpen(false);
      fetchData();
    } catch (error) { alert('保存员工信息失败'); }
  };

  const toggleService = (serviceName: string) => {
    setStaffFormData(prev => ({
      ...prev,
      services_supported: prev.services_supported.includes(serviceName)
        ? prev.services_supported.filter(s => s !== serviceName)
        : [...prev.services_supported, serviceName]
    }));
  };

  return (
    <div className="p-8 max-w-7xl mx-auto">
      <div className="mb-8 flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold text-slate-800 tracking-tight flex items-center">
            <Users className="w-6 h-6 mr-3 text-emerald-600" />
            员工与{terminology?.staff_title || '技师'}
          </h1>
          <p className="text-slate-500 mt-1 text-sm">管理店内{terminology?.staff_title || '员工'}、{terminology?.staff_title || '技师'}信息与服务权限</p>
        </div>
        <ReadOnlyButton>
          <button
            onClick={() => openModal()}
            className="px-6 py-3 bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl font-bold flex items-center gap-2 transition-colors shadow-lg"
          >
            <Plus className="w-5 h-5" /> 添加员工
          </button>
        </ReadOnlyButton>
      </div>

      <div className="bg-white rounded-3xl shadow-sm border border-slate-100 overflow-hidden">
        <div className="p-6 border-b border-slate-100 bg-slate-50/50">
          <h2 className="text-lg font-bold text-slate-800 flex items-center">
            <Users className="w-5 h-5 mr-2 text-emerald-600" />
            员工列表
          </h2>
        </div>

        <div className="divide-y divide-slate-100">
          {staff.length === 0 ? (
            <div className="p-12 text-center">
              <Users className="w-16 h-16 text-slate-200 mx-auto mb-4" />
              <p className="text-slate-500 font-medium">暂无员工信息，请点击上方按钮添加</p>
            </div>
          ) : (
            staff.map(member => (
              <div key={member.staff_id} className="p-6 flex items-center justify-between hover:bg-slate-50 transition-colors">
                <div className="flex items-center gap-4">
                  <div className="w-12 h-12 rounded-full bg-emerald-100 text-emerald-600 flex items-center justify-center font-bold text-lg">
                    {member.name.charAt(0)}
                  </div>
                  <div>
                    <h3 className="font-bold text-slate-800 text-lg">{member.name}</h3>
                    <div className="flex gap-3 mt-1 text-sm text-slate-500">
                      <span>{member.role}</span>
                      <span className="text-slate-300">|</span>
                      <span>{member.phone || '未设置电话'}</span>
                    </div>
                    {member.services_supported && member.services_supported.length > 0 && (
                      <div className="flex gap-2 mt-2 flex-wrap">
                        {member.services_supported.map((s, i) => (
                          <span key={i} className="px-2 py-1 bg-emerald-50 text-emerald-700 rounded-lg text-xs font-medium">
                            {s}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
                <div className="flex gap-1">
                  <button onClick={() => openModal(member)} className="p-3 text-slate-400 hover:text-emerald-600 hover:bg-emerald-50 rounded-xl transition-colors">
                    <Edit2 className="w-5 h-5" />
                  </button>
                  <button onClick={() => handleDeleteStaff(member.staff_id, member.name)} className="p-3 text-slate-400 hover:text-red-600 hover:bg-red-50 rounded-xl transition-colors">
                    <Trash2 className="w-5 h-5" />
                  </button>
                </div>
              </div>
            ))
          )}
        </div>
      </div>

      {/* Modal */}
      {isModalOpen && (
        <div className="fixed inset-0 bg-slate-900/60 backdrop-blur-sm flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-3xl shadow-2xl w-full max-w-lg overflow-hidden">
            <div className="p-6 border-b border-slate-100 flex justify-between items-center bg-slate-50/50">
              <h2 className="text-xl font-bold text-slate-800">
                {editingStaffId ? '编辑员工' : '添加员工'}
              </h2>
              <X onClick={() => setIsModalOpen(false)} className="w-6 h-6 text-slate-400 cursor-pointer hover:text-slate-600" />
            </div>
            <form onSubmit={handleSaveStaff} className="p-6 space-y-5">
              <div>
                <label className="block text-xs font-bold text-slate-500 uppercase mb-2">姓名</label>
                <input
                  value={staffFormData.name}
                  onChange={e => setStaffFormData({...staffFormData, name: e.target.value})}
                  className="w-full px-4 py-3 bg-slate-50 border border-slate-100 rounded-xl focus:ring-2 focus:ring-emerald-500 outline-none font-medium"
                  placeholder="请输入姓名"
                  required
                />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-bold text-slate-500 uppercase mb-2">角色</label>
                  <select
                    value={staffFormData.role}
                    onChange={e => setStaffFormData({...staffFormData, role: e.target.value})}
                    className="w-full px-4 py-3 bg-slate-50 border border-slate-100 rounded-xl focus:ring-2 focus:ring-emerald-500 outline-none font-medium"
                  >
                    <option value={terminology?.staff_title || '技师'}>{terminology?.staff_title || '技师'}</option>
                    <option value="高级技师">高级{terminology?.staff_title || '技师'}</option>
                    <option value="店长">店长</option>
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-bold text-slate-500 uppercase mb-2">手机号</label>
                  <input
                    type="text"
                    value={staffFormData.phone}
                    onChange={e => setStaffFormData({...staffFormData, phone: e.target.value})}
                    className="w-full px-4 py-3 bg-slate-50 border border-slate-100 rounded-xl focus:ring-2 focus:ring-emerald-500 outline-none font-medium"
                    placeholder="请输入手机号"
                  />
                </div>
              </div>
              <div>
                <label className="block text-xs font-bold text-slate-500 uppercase mb-2">
                  {editingStaffId ? '新密码（留空则不修改）' : '初始密码'}
                </label>
                <input
                  type="password"
                  value={staffFormData.password}
                  onChange={e => setStaffFormData({...staffFormData, password: e.target.value})}
                  className="w-full px-4 py-3 bg-slate-50 border border-slate-100 rounded-xl focus:ring-2 focus:ring-emerald-500 outline-none font-medium"
                  placeholder={editingStaffId ? "留空则不修改密码" : "请设置登录密码（WAP 端使用）"}
                />
              </div>
              <div>
                <label className="block text-xs font-bold text-slate-500 uppercase mb-3">支持的服务项目</label>
                <div className="grid grid-cols-2 gap-2 max-h-40 overflow-y-auto">
                  {services.map(service => (
                    <label key={service.item_id} className="flex items-center gap-2 p-3 rounded-xl border border-slate-100 hover:bg-slate-50 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={staffFormData.services_supported.includes(service.name)}
                        onChange={() => toggleService(service.name)}
                        className="w-4 h-4 text-emerald-600 rounded focus:ring-emerald-500"
                      />
                      <span className="text-sm text-slate-700">{service.name}</span>
                    </label>
                  ))}
                </div>
              </div>
              <button type="submit" className="w-full py-4 mt-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl font-bold shadow-lg transition-all">
                保存员工
              </button>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

export default Staff;
