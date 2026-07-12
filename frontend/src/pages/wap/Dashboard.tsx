import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import API from '../../api';
import { Calendar, Clock, User, ChevronRight, LogOut, Menu } from 'lucide-react';

interface Booking {
  booking_id: string;
  client_id: string;
  service_name: string;
  staff_name: string;
  start_time: string;
  end_time: string;
  status: string;
}

interface BookingWithClient extends Booking {
  client_name: string;
  client_phone: string;
}

const Dashboard: React.FC = () => {
  const [bookings, setBookings] = useState<BookingWithClient[]>([]);
  const [staffName, setStaffName] = useState('');
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    const token = localStorage.getItem('wap_token');
    const staff = localStorage.getItem('wap_staff');

    if (!token) {
      navigate('/wap/login');
      return;
    }

    if (staff) {
      const staffData = JSON.parse(staff);
      setStaffName(staffData.name);
    }

    fetchBookings();
  }, []);

  const fetchBookings = async () => {
    try {
      const token = localStorage.getItem('wap_token');
      const response = await axios.get(`${API}/api/v1/wap/my-bookings`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setBookings(response.data);
    } catch (error) {
      console.error('获取排班失败:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleLogout = () => {
    localStorage.removeItem('wap_token');
    localStorage.removeItem('wap_staff');
    navigate('/wap/login');
  };

  const formatTime = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' });
  };

  const getStatusText = (status: string) => {
    const statusMap: Record<string, string> = {
      pending: '待确认',
      confirmed: '已确认',
      completed: '已完成',
      cancelled: '已取消'
    };
    return statusMap[status] || status;
  };

  const getStatusColor = (status: string) => {
    const colorMap: Record<string, string> = {
      pending: 'bg-orange-100 text-orange-700',
      confirmed: 'bg-blue-100 text-blue-700',
      completed: 'bg-emerald-100 text-emerald-700',
      cancelled: 'bg-slate-100 text-slate-700'
    };
    return colorMap[status] || 'bg-slate-100 text-slate-700';
  };

  return (
    <div className="min-h-screen bg-slate-50">
      {/* Header */}
      <header className="bg-emerald-600 text-white p-4 sticky top-0 z-10 shadow-md">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-xl font-bold">工作台</h1>
            <p className="text-emerald-100 text-sm">欢迎，{staffName}</p>
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={() => navigate('/wap/records')}
              className="p-2 hover:bg-emerald-700 rounded-lg"
            >
              <Calendar className="w-6 h-6" />
            </button>
            <button
              onClick={() => navigate('/wap/performance')}
              className="p-2 hover:bg-emerald-700 rounded-lg"
            >
              <Menu className="w-6 h-6" />
            </button>
            <button
              onClick={handleLogout}
              className="p-2 hover:bg-emerald-700 rounded-lg"
            >
              <LogOut className="w-6 h-6" />
            </button>
          </div>
        </div>
      </header>

      {/* Date Bar */}
      <div className="bg-white px-4 py-3 border-b border-slate-200">
        <p className="text-slate-600">
          {new Date().toLocaleDateString('zh-CN', {
            year: 'numeric',
            month: 'long',
            day: 'numeric',
            weekday: 'long'
          })}
        </p>
      </div>

      {/* Bookings List */}
      <main className="p-4">
        {loading ? (
          <div className="text-center py-12 text-slate-400">加载中...</div>
        ) : bookings.length === 0 ? (
          <div className="text-center py-12">
            <Calendar className="w-16 h-16 text-slate-300 mx-auto mb-4" />
            <p className="text-slate-500">今天暂无排班</p>
          </div>
        ) : (
          <div className="space-y-3">
            {bookings.map((booking) => (
              <div
                key={booking.booking_id}
                className="bg-white rounded-2xl shadow-sm border border-slate-100 p-4"
              >
                <div className="flex items-start justify-between mb-3">
                  <div className="flex items-center gap-3">
                    <div className="w-12 h-12 rounded-full bg-emerald-100 text-emerald-600 flex items-center justify-center font-bold text-lg">
                      {booking.client_name.charAt(0)}
                    </div>
                    <div>
                      <h3 className="font-bold text-slate-800 text-lg">
                        {booking.client_name}
                      </h3>
                      <p className="text-slate-500 text-sm">{booking.client_phone}</p>
                    </div>
                  </div>
                  <span
                    className={`px-3 py-1 rounded-full text-xs font-bold ${getStatusColor(
                      booking.status
                    )}`}
                  >
                    {getStatusText(booking.status)}
                  </span>
                </div>

                <div className="flex items-center gap-4 mb-3 text-sm text-slate-600">
                  <div className="flex items-center gap-1">
                    <Clock className="w-4 h-4" />
                    <span>
                      {formatTime(booking.start_time)} - {formatTime(booking.end_time)}
                    </span>
                  </div>
                </div>

                <div className="bg-slate-50 rounded-xl p-3 mb-3">
                  <p className="text-sm text-slate-500">服务项目</p>
                  <p className="font-bold text-slate-800">{booking.service_name}</p>
                </div>

                <button
                  onClick={() =>
                    navigate('/wap/service-entry', { state: { booking, client_name: booking.client_name } })
                  }
                  className="w-full py-3 bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl font-bold transition-colors flex items-center justify-center gap-2"
                >
                  开始服务/录入 <ChevronRight className="w-5 h-5" />
                </button>
              </div>
            ))}
          </div>
        )}
      </main>

      {/* Bottom Navigation */}
      <nav className="fixed bottom-0 left-0 right-0 bg-white border-t border-slate-200 px-4 py-2 flex justify-around">
        <button
          onClick={() => navigate('/wap/dashboard')}
          className="flex flex-col items-center py-2 px-4 text-emerald-600"
        >
          <Calendar className="w-6 h-6" />
          <span className="text-xs mt-1">排班</span>
        </button>
        <button
          onClick={() => navigate('/wap/records')}
          className="flex flex-col items-center py-2 px-4 text-slate-500"
        >
          <Menu className="w-6 h-6" />
          <span className="text-xs mt-1">记录</span>
        </button>
        <button
          onClick={() => navigate('/wap/performance')}
          className="flex flex-col items-center py-2 px-4 text-slate-500"
        >
          <User className="w-6 h-6" />
          <span className="text-xs mt-1">业绩</span>
        </button>
      </nav>

      {/* Spacer for bottom nav */}
      <div className="h-20" />
    </div>
  );
};

export default Dashboard;
