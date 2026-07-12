import React, { useState, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import axios from 'axios';
import API from '../../api';
import { ArrowLeft } from 'lucide-react';
import VoiceInputButton from '../../components/VoiceInputButton';

interface ServiceItem {
  item_id: string;
  name: string;
  description: string;
}

interface ClientInfo {
  client_id: string;
  name: string;
  phone: string;
  times_card_balance: number;
  cash_card_balance: number;
}

const ServiceEntry: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const { booking } = location.state || {};

  const [services, setServices] = useState<ServiceItem[]>([]);
  const [clientInfo, setClientInfo] = useState<ClientInfo | null>(null);
  const [loading, setLoading] = useState(true);

  const [selectedService, setSelectedService] = useState('');
  const [symptoms, setSymptoms] = useState('');
  const [description, setDescription] = useState('');
  const [deductType, setDeductType] = useState<'times' | 'cash'>('times');
  const [deductValue, setDeductValue] = useState<string>('');

  useEffect(() => {
    const token = localStorage.getItem('wap_token');
    if (!token) {
      navigate('/wap/login');
      return;
    }

    if (!booking) {
      navigate('/wap/dashboard');
      return;
    }

    fetchServices();
    fetchClientInfo();
  }, [booking]);

  const fetchServices = async () => {
    try {
      const response = await axios.get(`${API}/api/v1/services/`);
      setServices(response.data);
      if (response.data.length > 0) {
        setSelectedService(response.data[0].name);
      }
    } catch (error) {
      console.error('获取服务项目失败:', error);
    }
  };

  const fetchClientInfo = async () => {
    try {
      const token = localStorage.getItem('wap_token');
      const response = await axios.get(
        `${API}/api/v1/wap/bookings/${booking.booking_id}`,
        {
          headers: { Authorization: `Bearer ${token}` }
        }
      );
      setClientInfo(response.data.client);
    } catch (error) {
      console.error('获取客户信息失败:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async () => {
    if (!selectedService) {
      alert('请选择服务项目');
      return;
    }

    if (!description.trim()) {
      alert('请输入服务详细描述');
      return;
    }

    const deductTimes = deductType === 'times' ? parseInt(deductValue) || 0 : 0;
    const deductCash = deductType === 'cash' ? parseFloat(deductValue) || 0 : 0;

    // 验证余额
    if (deductTimes > 0 && clientInfo && deductTimes > clientInfo.times_card_balance) {
      alert(`次卡余额不足（剩余${clientInfo.times_card_balance}次）`);
      return;
    }
    if (deductCash > 0 && clientInfo && deductCash > clientInfo.cash_card_balance) {
      alert(`储值卡余额不足（剩余${clientInfo.cash_card_balance}元）`);
      return;
    }

    try {
      const token = localStorage.getItem('wap_token');
      // 将症状字符串转换为数组（用逗号分隔）
      const symptomsArray = symptoms ? symptoms.split(/[,，]/).map(s => s.trim()).filter(s => s) : [];

      await axios.post(
        `${API}/api/v1/wap/records`,
        null,
        {
          params: {
            client_id: clientInfo?.client_id,
            service_name: selectedService,
            symptoms: symptomsArray,
            description: description,
            deduct_times: deductTimes,
            deduct_cash: deductCash
          },
          headers: { Authorization: `Bearer ${token}` }
        }
      );

      alert('服务记录提交成功！');
      navigate('/wap/dashboard');
    } catch (error: any) {
      alert(error.response?.data?.detail || '提交失败，请重试');
    }
  };

  // Voice input handlers removed — now using VoiceInputButton component

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-50 flex items-center justify-center">
        <p className="text-slate-400">加载中...</p>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-50">
      {/* Header */}
      <header className="bg-emerald-600 text-white p-4 sticky top-0 z-10 shadow-md">
        <div className="flex items-center gap-3">
          <button onClick={() => navigate(-1)} className="p-1 hover:bg-emerald-700 rounded-lg">
            <ArrowLeft className="w-6 h-6" />
          </button>
          <h1 className="text-xl font-bold">服务录入</h1>
        </div>
      </header>

      <main className="p-4 space-y-4">
        {/* Client Info Card */}
        {clientInfo && (
          <div className="bg-white rounded-2xl shadow-sm border border-slate-100 p-4">
            <div className="flex items-center gap-3 mb-3">
              <div className="w-12 h-12 rounded-full bg-emerald-100 text-emerald-600 flex items-center justify-center font-bold text-lg">
                {clientInfo.name.charAt(0)}
              </div>
              <div>
                <h2 className="font-bold text-slate-800 text-lg">{clientInfo.name}</h2>
                <p className="text-slate-500 text-sm">{clientInfo.phone}</p>
              </div>
            </div>
            <div className="grid grid-cols-2 gap-3 bg-slate-50 rounded-xl p-3">
              <div>
                <p className="text-xs text-slate-500">次卡余额</p>
                <p className="font-bold text-emerald-600 text-lg">{clientInfo.times_card_balance} 次</p>
              </div>
              <div>
                <p className="text-xs text-slate-500">储值余额</p>
                <p className="font-bold text-emerald-600 text-lg">¥{clientInfo.cash_card_balance}</p>
              </div>
            </div>
          </div>
        )}

        {/* Service Selection */}
        <div className="bg-white rounded-2xl shadow-sm border border-slate-100 p-4">
          <label className="block text-sm font-bold text-slate-700 mb-2">
            服务项目 *
          </label>
          <select
            value={selectedService}
            onChange={(e) => setSelectedService(e.target.value)}
            className="w-full px-4 py-3 bg-slate-50 border border-slate-200 rounded-xl focus:ring-2 focus:ring-emerald-500 outline-none text-lg"
          >
            {services.map((service) => (
              <option key={service.item_id} value={service.name}>
                {service.name}
              </option>
            ))}
          </select>
        </div>

        {/* Symptoms Input (with voice support) */}
        <div className="bg-white rounded-2xl shadow-sm border border-slate-100 p-4">
          <div className="flex items-center justify-between mb-2">
            <label className="block text-sm font-bold text-slate-700">
              症状（逗号分隔）
            </label>
            <VoiceInputButton onTranscript={(text) => setSymptoms(prev => prev ? `${prev}，${text}` : text)} />
          </div>
          <input
            type="text"
            value={symptoms}
            onChange={(e) => setSymptoms(e.target.value)}
            className="w-full px-4 py-3 bg-slate-50 border border-slate-200 rounded-xl focus:ring-2 focus:ring-emerald-500 outline-none text-lg"
            placeholder="如：怕冷，失眠，肩颈酸痛"
          />
          <p className="text-xs text-slate-400 mt-1">
            点击麦克风，对着手机说话即可录入
          </p>
        </div>

        {/* Description Input (with voice support) */}
        <div className="bg-white rounded-2xl shadow-sm border border-slate-100 p-4">
          <div className="flex items-center justify-between mb-2">
            <label className="block text-sm font-bold text-slate-700">
              详细观察描述 *
            </label>
            <VoiceInputButton onTranscript={(text) => setDescription(prev => prev ? `${prev} ${text}` : text)} />
          </div>
          <textarea
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            rows={4}
            className="w-full px-4 py-3 bg-slate-50 border border-slate-200 rounded-xl focus:ring-2 focus:ring-emerald-500 outline-none text-lg resize-none"
            placeholder="记录本次服务的过程、客户反馈及观察结果..."
            required
          />
          <p className="text-xs text-slate-400 mt-1">
            点击麦克风，对着手机说话即可录入
          </p>
        </div>

        {/* Deduction Selection */}
        <div className="bg-white rounded-2xl shadow-sm border border-slate-100 p-4">
          <label className="block text-sm font-bold text-slate-700 mb-3">
            扣费方式
          </label>

          {/* Tab Selection */}
          <div className="flex gap-2 mb-4">
            <button
              onClick={() => setDeductType('times')}
              className={`flex-1 py-2 rounded-xl font-bold transition-colors ${
                deductType === 'times'
                  ? 'bg-emerald-600 text-white'
                  : 'bg-slate-100 text-slate-600'
              }`}
            >
              次卡扣次
            </button>
            <button
              onClick={() => setDeductType('cash')}
              className={`flex-1 py-2 rounded-xl font-bold transition-colors ${
                deductType === 'cash'
                  ? 'bg-emerald-600 text-white'
                  : 'bg-slate-100 text-slate-600'
              }`}
            >
              储值卡扣元
            </button>
          </div>

          {/* Input Field */}
          <div className="flex items-center gap-3">
            <input
              type="number"
              value={deductValue}
              onChange={(e) => setDeductValue(e.target.value)}
              className="flex-1 px-4 py-3 bg-slate-50 border border-slate-200 rounded-xl focus:ring-2 focus:ring-emerald-500 outline-none text-lg"
              placeholder={deductType === 'times' ? '输入扣减次数' : '输入扣减金额'}
            />
            <span className="text-slate-600 font-bold">
              {deductType === 'times' ? '次' : '元'}
            </span>
          </div>

          {/* Balance Warning */}
          {deductValue && clientInfo && (
            <div className="mt-3 p-3 bg-amber-50 border border-amber-200 rounded-xl">
              <p className="text-sm text-amber-700">
                {deductType === 'times' ? (
                  <>
                    当前次卡余额：<strong>{clientInfo.times_card_balance}</strong> 次，
                    本次扣 <strong>{deductValue}</strong> 次，
                    剩余 <strong>{clientInfo.times_card_balance - parseInt(deductValue || '0')}</strong> 次
                  </>
                ) : (
                  <>
                    当前储值余额：<strong>¥{clientInfo.cash_card_balance}</strong>，
                    本次扣 <strong>¥{deductValue}</strong>，
                    剩余 <strong>¥{clientInfo.cash_card_balance - parseFloat(deductValue || '0')}</strong>
                  </>
                )}
              </p>
            </div>
          )}
        </div>

        {/* Submit Button */}
        <button
          onClick={handleSubmit}
          className="w-full py-4 bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl font-bold shadow-lg transition-all text-lg"
        >
          提交服务记录
        </button>
      </main>
    </div>
  );
};

export default ServiceEntry;
