import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Calendar as CalendarIcon, User, Plus, X, Phone, CheckCircle2, XCircle } from 'lucide-react';
import { ReadOnlyButton } from '../components/ReadOnlyGuard';

interface Booking {
  booking_id: string;
  client_id: string;
  service_name: string;
  staff_name: string;
  start_time: string;
  end_time: string;
  status: string; // pending, confirmed, completed, cancelled
}

interface Client {
  client_id: string;
  name: string;
  phone: string;
}

interface Staff {
  staff_id: string;
  name: string;
  role?: string;
}

interface Service {
  item_id: string;
  name: string;
}

const Bookings = () => {
  const [bookings, setBookings] = useState<Booking[]>([]);
  const [clients, setClients] = useState<Client[]>([]);
  const [staff, setStaff] = useState<Staff[]>([]);
  const [services, setServices] = useState<Service[]>([]);
  
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [formData, setFormData] = useState({
    client_id: '',
    service_name: '',
    staff_name: '',
    date: new Date().toISOString().split('T')[0],
    time: '10:00'
  });

  const fetchData = async () => {
    try {
      const [bookingsRes, clientsRes, staffRes, servicesRes] = await Promise.all([
        axios.get('/api/v1/bookings/'),
        axios.get('/api/v1/clients/'),
        axios.get('/api/v1/services/staff/'),
        axios.get('/api/v1/services/')
      ]);
      setBookings(bookingsRes.data.sort((a: Booking, b: Booking) => new Date(a.start_time).getTime() - new Date(b.start_time).getTime()));
      setClients(clientsRes.data);
      setStaff(staffRes.data);
      setServices(servicesRes.data);
    } catch (e) { console.error("加载数据失败", e); }
  };

  useEffect(() => { fetchData(); }, []);

  const handleAddBooking = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      // 简单组装开始和结束时间 (默认服务1小时)
      const startDateTime = new Date(`${formData.date}T${formData.time}:00`);
      const endDateTime = new Date(startDateTime.getTime() + 60 * 60 * 1000);
      
      await axios.post('/api/v1/bookings/', {
        client_id: formData.client_id,
        service_name: formData.service_name,
        staff_name: formData.staff_name,
        start_time: startDateTime.toISOString(),
        end_time: endDateTime.toISOString(),
        status: 'confirmed'
      });
      
      setIsModalOpen(false);
      fetchData();
    } catch (error) { alert('添加预约失败'); }
  };

  const handleDeleteBooking = async (bookingId: string) => {
    if (!confirm('确定要删除此预约记录吗？')) return;
    try {
      await axios.delete(`/api/v1/bookings/${bookingId}`);
      fetchData();
    } catch (e) { alert('删除失败'); }
  };

  const updateBookingStatus = async (booking_id: string, status: string) => {
    try {
      await axios.put(`/api/v1/bookings/${booking_id}`, { status });
      fetchData();
    } catch (e) { alert('更新状态失败'); }
  };

  const getStatusBadge = (status: string) => {
    switch(status) {
      case 'confirmed': return <span className="bg-blue-100 text-blue-700 px-3 py-1 rounded-md text-xs font-bold">已确认</span>;
      case 'completed': return <span className="bg-emerald-100 text-emerald-700 px-3 py-1 rounded-md text-xs font-bold">已完成</span>;
      case 'cancelled': return <span className="bg-slate-100 text-slate-500 px-3 py-1 rounded-md text-xs font-bold">已取消</span>;
      default: return <span className="bg-orange-100 text-orange-700 px-3 py-1 rounded-md text-xs font-bold">待处理</span>;
    }
  };

  return (
    <div className="p-8 max-w-7xl mx-auto">
      <div className="flex justify-between items-center mb-8">
        <div>
          <h1 className="text-2xl font-bold text-slate-800 tracking-tight">预约排班管理</h1>
          <p className="text-slate-500 text-sm mt-1">管理客户到店时间及理疗师排期</p>
        </div>
        <ReadOnlyButton>
          <button onClick={() => setIsModalOpen(true)} className="bg-emerald-600 hover:bg-emerald-700 text-white px-5 py-2.5 rounded-xl flex items-center font-bold transition-all shadow-lg shadow-emerald-100">
            <Plus className="w-5 h-5 mr-2" /> 新增预约
          </button>
        </ReadOnlyButton>
      </div>

      <div className="bg-white rounded-3xl shadow-sm border border-slate-100 overflow-hidden">
        <table className="w-full text-left border-collapse">
          <thead>
            <tr className="bg-slate-50/50 border-b border-slate-100 text-slate-500 text-xs uppercase tracking-wider">
              <th className="p-5 font-bold w-48">预约时间</th>
              <th className="p-5 font-bold">客户信息</th>
              <th className="p-5 font-bold">预约项目</th>
              <th className="p-5 font-bold">指定技师</th>
              <th className="p-5 font-bold text-center">状态</th>
              <th className="p-5 font-bold text-right">操作</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-50">
            {bookings.map(b => {
              const client = clients.find(c => c.client_id === b.client_id);
              const bookingDate = new Date(b.start_time);
              const isToday = bookingDate.toDateString() === new Date().toDateString();
              
              return (
                <tr key={b.booking_id} className={`hover:bg-slate-50/50 transition-colors ${b.status === 'cancelled' ? 'opacity-50' : ''}`}>
                  <td className="p-5">
                    <div className="flex items-center">
                      <div className={`w-2 h-10 rounded-full mr-3 ${isToday ? 'bg-orange-400' : 'bg-slate-200'}`}></div>
                      <div>
                        <div className="font-bold text-slate-800 text-lg">
                          {bookingDate.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}
                        </div>
                        <div className="text-xs text-slate-500">{bookingDate.toLocaleDateString()} {isToday && <span className="text-orange-500 font-bold ml-1">(今天)</span>}</div>
                      </div>
                    </div>
                  </td>
                  <td className="p-5">
                    <div className="font-bold text-slate-800 flex items-center"><User className="w-4 h-4 mr-2 text-slate-400" /> {client?.name || '未知客户'}</div>
                    <div className="text-xs text-slate-500 flex items-center mt-1"><Phone className="w-3 h-3 mr-1" /> {client?.phone}</div>
                  </td>
                  <td className="p-5 font-bold text-emerald-700">{b.service_name}</td>
                  <td className="p-5">
                    <span className="bg-slate-100 text-slate-600 px-3 py-1.5 rounded-lg text-sm font-medium">
                      {b.staff_name}
                    </span>
                  </td>
                  <td className="p-5 text-center">{getStatusBadge(b.status)}</td>
                  <td className="p-5 text-right">
                    {b.status === 'confirmed' && (
                      <div className="flex justify-end gap-2">
                        <button onClick={() => updateBookingStatus(b.booking_id, 'completed')} className="text-emerald-600 hover:bg-emerald-50 p-2 rounded-lg transition-colors" title="完成">
                          <CheckCircle2 className="w-5 h-5" />
                        </button>
                        <button onClick={() => updateBookingStatus(b.booking_id, 'cancelled')} className="text-slate-400 hover:text-rose-500 hover:bg-rose-50 p-2 rounded-lg transition-colors" title="取消">
                          <XCircle className="w-5 h-5" />
                        </button>
                      </div>
                    )}
                    {b.status === 'cancelled' && (
                      <button onClick={() => handleDeleteBooking(b.booking_id)} className="text-xs text-red-500 hover:text-red-700 font-bold">删除</button>
                    )}
                  </td>
                </tr>
              );
            })}
            {bookings.length === 0 && <tr><td colSpan={6} className="p-16 text-center text-slate-400">暂无预约记录</td></tr>}
          </tbody>
        </table>
      </div>

      {/* 新增预约弹窗 */}
      {isModalOpen && (
        <div className="fixed inset-0 bg-slate-900/60 backdrop-blur-sm flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-3xl shadow-2xl w-full max-w-lg overflow-hidden animate-in fade-in zoom-in duration-200">
            <div className="p-6 border-b border-slate-100 flex justify-between items-center bg-slate-50/50">
              <h2 className="text-xl font-bold text-slate-800 flex items-center"><CalendarIcon className="w-5 h-5 mr-2 text-emerald-600" /> 安排新预约</h2>
              <X onClick={() => setIsModalOpen(false)} className="w-6 h-6 text-slate-400 cursor-pointer hover:text-slate-600" />
            </div>
            <form onSubmit={handleAddBooking} className="p-6 space-y-5">
              <div>
                <label className="block text-xs font-bold text-slate-500 uppercase mb-2">搜索并选择客户</label>
                <select required value={formData.client_id} onChange={e => setFormData({...formData, client_id: e.target.value})} className="w-full px-4 py-3 bg-slate-50 border border-slate-200 rounded-xl focus:ring-2 focus:ring-emerald-500 outline-none font-medium">
                  <option value="">-- 请选择客户 --</option>
                  {clients.map(c => <option key={c.client_id} value={c.client_id}>{c.name} ({c.phone.slice(-4)})</option>)}
                </select>
              </div>

              <div className="flex gap-4">
                <div className="flex-1">
                  <label className="block text-xs font-bold text-slate-500 uppercase mb-2">预约日期</label>
                  <input type="date" required value={formData.date} onChange={e => setFormData({...formData, date: e.target.value})} className="w-full px-4 py-3 bg-slate-50 border border-slate-200 rounded-xl focus:ring-2 focus:ring-emerald-500 font-bold text-slate-700" />
                </div>
                <div className="flex-1">
                  <label className="block text-xs font-bold text-slate-500 uppercase mb-2">预约时间</label>
                  <input type="time" required value={formData.time} onChange={e => setFormData({...formData, time: e.target.value})} className="w-full px-4 py-3 bg-slate-50 border border-slate-200 rounded-xl focus:ring-2 focus:ring-emerald-500 font-bold text-slate-700" />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-bold text-slate-500 uppercase mb-2">预约项目</label>
                  <select required value={formData.service_name} onChange={e => setFormData({...formData, service_name: e.target.value})} className="w-full px-4 py-3 bg-slate-50 border border-slate-200 rounded-xl focus:ring-2 focus:ring-emerald-500 outline-none font-medium">
                    <option value="">-- 请选择项目 --</option>
                    {services.map(s => <option key={s.item_id} value={s.name}>{s.name}</option>)}
                    <option value="综合调理(未定)">综合调理(到店定)</option>
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-bold text-slate-500 uppercase mb-2">指定技师</label>
                  <select required value={formData.staff_name} onChange={e => setFormData({...formData, staff_name: e.target.value})} className="w-full px-4 py-3 bg-slate-50 border border-slate-200 rounded-xl focus:ring-2 focus:ring-emerald-500 outline-none font-medium">
                    <option value="">-- 随机安排 --</option>
                    {staff.map(s => <option key={s.staff_id} value={s.name}>{s.name} ({s.role})</option>)}
                  </select>
                </div>
              </div>

              <button type="submit" className="w-full py-4 mt-4 bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl font-bold shadow-lg transition-all text-lg">
                确认预约安排
              </button>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

export default Bookings;