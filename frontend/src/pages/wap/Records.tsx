import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import API from '../../api';
import { ArrowLeft, FileText, Calendar } from 'lucide-react';

interface ServiceRecord {
  record_id: string;
  client_name: string;
  date: string;
  symptoms: string[];
  description: string;
  treatment_provided: string;
  deduct_times: number;
  deduct_cash: number;
}

const Records: React.FC = () => {
  const navigate = useNavigate();
  const [records, setRecords] = useState<ServiceRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');

  useEffect(() => {
    const token = localStorage.getItem('wap_token');
    if (!token) {
      navigate('/wap/login');
      return;
    }

    fetchRecords();
  }, []);

  const fetchRecords = async () => {
    try {
      const token = localStorage.getItem('wap_token');
      const params: Record<string, string> = {};
      if (startDate) params.start_date = startDate;
      if (endDate) params.end_date = endDate;

      const response = await axios.get(`${API}/api/v1/wap/my-records`, {
        params,
        headers: { Authorization: `Bearer ${token}` }
      });
      setRecords(response.data);
    } catch (error) {
      console.error('获取记录失败:', error);
    } finally {
      setLoading(false);
    }
  };

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleDateString('zh-CN', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  return (
    <div className="min-h-screen bg-slate-50">
      {/* Header */}
      <header className="bg-emerald-600 text-white p-4 sticky top-0 z-10 shadow-md">
        <div className="flex items-center gap-3">
          <button onClick={() => navigate(-1)} className="p-1 hover:bg-emerald-700 rounded-lg">
            <ArrowLeft className="w-6 h-6" />
          </button>
          <h1 className="text-xl font-bold">服务记录</h1>
        </div>
      </header>

      {/* Filter Section */}
      <div className="bg-white p-4 border-b border-slate-200">
        <div className="flex gap-2">
          <input
            type="date"
            value={startDate}
            onChange={(e) => setStartDate(e.target.value)}
            className="flex-1 px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-sm"
            placeholder="开始日期"
          />
          <input
            type="date"
            value={endDate}
            onChange={(e) => setEndDate(e.target.value)}
            className="flex-1 px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-sm"
            placeholder="结束日期"
          />
          <button
            onClick={fetchRecords}
            className="px-4 py-2 bg-emerald-600 text-white rounded-lg font-bold text-sm"
          >
            查询
          </button>
        </div>
      </div>

      {/* Records List */}
      <main className="p-4">
        {loading ? (
          <div className="text-center py-12 text-slate-400">加载中...</div>
        ) : records.length === 0 ? (
          <div className="text-center py-12">
            <FileText className="w-16 h-16 text-slate-300 mx-auto mb-4" />
            <p className="text-slate-500">暂无服务记录</p>
          </div>
        ) : (
          <div className="space-y-3">
            {records.map((record) => (
              <div
                key={record.record_id}
                className="bg-white rounded-2xl shadow-sm border border-slate-100 p-4"
              >
                <div className="flex items-start justify-between mb-3">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-full bg-emerald-100 text-emerald-600 flex items-center justify-center font-bold">
                      {record.client_name.charAt(0)}
                    </div>
                    <div>
                      <h3 className="font-bold text-slate-800">{record.client_name}</h3>
                      <div className="flex items-center gap-2 text-xs text-slate-500">
                        <Calendar className="w-3 h-3" />
                        <span>{formatDate(record.date)}</span>
                      </div>
                    </div>
                  </div>
                  {(record.deduct_times > 0 || record.deduct_cash > 0) && (
                    <div className="text-right">
                      {record.deduct_times > 0 && (
                        <p className="text-sm font-bold text-emerald-600">
                          -{record.deduct_times} 次
                        </p>
                      )}
                      {record.deduct_cash > 0 && (
                        <p className="text-sm font-bold text-emerald-600">
                          -¥{record.deduct_cash}
                        </p>
                      )}
                    </div>
                  )}
                </div>

                <div className="bg-slate-50 rounded-xl p-3 mb-3">
                  <p className="text-xs text-slate-500 mb-1">服务项目</p>
                  <p className="font-bold text-slate-800 text-sm">{record.treatment_provided}</p>
                </div>

                {record.symptoms && record.symptoms.length > 0 && (
                  <div className="mb-3">
                    <p className="text-xs text-slate-500 mb-1">症状</p>
                    <div className="flex flex-wrap gap-2">
                      {record.symptoms.map((symptom, index) => (
                        <span
                          key={index}
                          className="px-2 py-1 bg-orange-50 text-orange-700 rounded-lg text-xs font-medium"
                        >
                          {symptom}
                        </span>
                      ))}
                    </div>
                  </div>
                )}

                <div>
                  <p className="text-xs text-slate-500 mb-1">详细描述</p>
                  <p className="text-sm text-slate-700 line-clamp-2">{record.description}</p>
                </div>
              </div>
            ))}
          </div>
        )}
      </main>

      {/* Bottom Navigation */}
      <nav className="fixed bottom-0 left-0 right-0 bg-white border-t border-slate-200 px-4 py-2 flex justify-around">
        <button
          onClick={() => navigate('/wap/dashboard')}
          className="flex flex-col items-center py-2 px-4 text-slate-500"
        >
          <Calendar className="w-6 h-6" />
          <span className="text-xs mt-1">排班</span>
        </button>
        <button
          onClick={() => navigate('/wap/records')}
          className="flex flex-col items-center py-2 px-4 text-emerald-600"
        >
          <FileText className="w-6 h-6" />
          <span className="text-xs mt-1">记录</span>
        </button>
        <button
          onClick={() => navigate('/wap/performance')}
          className="flex flex-col items-center py-2 px-4 text-slate-500"
        >
          <Calendar className="w-6 h-6" />
          <span className="text-xs mt-1">业绩</span>
        </button>
      </nav>

      {/* Spacer for bottom nav */}
      <div className="h-20" />
    </div>
  );
};

export default Records;
