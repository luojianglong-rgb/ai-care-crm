import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import API from '../../api';
import { ArrowLeft, TrendingUp, DollarSign, Calendar, FileCheck } from 'lucide-react';

interface PerformanceData {
  period: {
    start: string;
    end: string;
  };
  statistics: {
    service_count: number;
    total_deduct_times: number;
    total_deduct_cash: number;
  };
}

const Performance: React.FC = () => {
  const navigate = useNavigate();
  const [period, setPeriod] = useState<'week' | 'month' | 'custom'>('month');
  const [data, setData] = useState<PerformanceData | null>(null);
  const [loading, setLoading] = useState(true);
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');

  useEffect(() => {
    const token = localStorage.getItem('wap_token');
    if (!token) {
      navigate('/wap/login');
      return;
    }

    fetchPerformance();
  }, [period, startDate, endDate]);

  const fetchPerformance = async () => {
    try {
      const token = localStorage.getItem('wap_token');
      const params: Record<string, string> = {};

      if (period === 'custom') {
        if (startDate) params.start_date = startDate;
        if (endDate) params.end_date = endDate;
      } else {
        const now = new Date();
        if (period === 'week') {
          // 本周
          const startOfWeek = new Date(now.setDate(now.getDate() - now.getDay()));
          params.start_date = startOfWeek.toISOString().split('T')[0];
          params.end_date = new Date().toISOString().split('T')[0];
        } else {
          // 本月
          const startOfMonth = new Date(now.getFullYear(), now.getMonth(), 1);
          params.start_date = startOfMonth.toISOString().split('T')[0];
          params.end_date = new Date().toISOString().split('T')[0];
        }
      }

      const response = await axios.get(`${API}/api/v1/wap/my-performance`, {
        params,
        headers: { Authorization: `Bearer ${token}` }
      });
      setData(response.data);
    } catch (error) {
      console.error('获取业绩数据失败:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading && !data) {
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
          <h1 className="text-xl font-bold">个人业绩</h1>
        </div>
      </header>

      <main className="p-4">
        {/* Period Selector */}
        <div className="bg-white rounded-2xl shadow-sm border border-slate-100 p-4 mb-4">
          <div className="flex gap-2">
            <button
              onClick={() => setPeriod('week')}
              className={`flex-1 py-2 rounded-xl font-bold text-sm transition-colors ${
                period === 'week'
                  ? 'bg-emerald-600 text-white'
                  : 'bg-slate-100 text-slate-600'
              }`}
            >
              本周
            </button>
            <button
              onClick={() => setPeriod('month')}
              className={`flex-1 py-2 rounded-xl font-bold text-sm transition-colors ${
                period === 'month'
                  ? 'bg-emerald-600 text-white'
                  : 'bg-slate-100 text-slate-600'
              }`}
            >
              本月
            </button>
            <button
              onClick={() => setPeriod('custom')}
              className={`flex-1 py-2 rounded-xl font-bold text-sm transition-colors ${
                period === 'custom'
                  ? 'bg-emerald-600 text-white'
                  : 'bg-slate-100 text-slate-600'
              }`}
            >
              自定义
            </button>
          </div>

          {period === 'custom' && (
            <div className="flex gap-2 mt-3">
              <input
                type="date"
                value={startDate}
                onChange={(e) => setStartDate(e.target.value)}
                className="flex-1 px-2 py-2 bg-slate-50 border border-slate-200 rounded-lg text-xs"
                placeholder="开始日期"
              />
              <input
                type="date"
                value={endDate}
                onChange={(e) => setEndDate(e.target.value)}
                className="flex-1 px-2 py-2 bg-slate-50 border border-slate-200 rounded-lg text-xs"
                placeholder="结束日期"
              />
            </div>
          )}
        </div>

        {/* Stats Cards */}
        {data && (
          <>
            {/* Period Display */}
            <div className="bg-white rounded-xl shadow-sm border border-slate-100 p-3 mb-4">
              <div className="flex items-center gap-2 text-sm text-slate-600">
                <Calendar className="w-4 h-4" />
                <span>
                  统计周期：{data.period.start} 至 {data.period.end}
                </span>
              </div>
            </div>

            {/* KPI Cards */}
            <div className="grid grid-cols-3 gap-3 mb-4">
              {/* Service Count */}
              <div className="bg-white rounded-2xl shadow-sm border border-slate-100 p-4 text-center">
                <FileCheck className="w-6 h-6 text-blue-500 mx-auto mb-2" />
                <p className="text-xs text-slate-500">服务次数</p>
                <p className="text-2xl font-black text-slate-800 mt-1">
                  {data.statistics.service_count}
                </p>
              </div>

              {/* Deduct Times */}
              <div className="bg-white rounded-2xl shadow-sm border border-slate-100 p-4 text-center">
                <TrendingUp className="w-6 h-6 text-emerald-500 mx-auto mb-2" />
                <p className="text-xs text-slate-500">扣次总数</p>
                <p className="text-2xl font-black text-slate-800 mt-1">
                  {data.statistics.total_deduct_times}
                </p>
              </div>

              {/* Deduct Cash */}
              <div className="bg-white rounded-2xl shadow-sm border border-slate-100 p-4 text-center">
                <DollarSign className="w-6 h-6 text-amber-500 mx-auto mb-2" />
                <p className="text-xs text-slate-500">扣费总额</p>
                <p className="text-lg font-black text-slate-800 mt-1">
                  ¥{data.statistics.total_deduct_cash.toFixed(0)}
                </p>
              </div>
            </div>

            {/* Summary Card */}
            <div className="bg-gradient-to-r from-emerald-500 to-teal-600 rounded-2xl shadow-lg p-6 text-white">
              <h3 className="font-bold text-lg mb-4">业绩概览</h3>
              <div className="space-y-3">
                <div className="flex justify-between items-center">
                  <span className="text-emerald-100">服务客户</span>
                  <span className="font-bold text-xl">{data.statistics.service_count} 人次</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-emerald-100">消耗次卡</span>
                  <span className="font-bold text-xl">{data.statistics.total_deduct_times} 次</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-emerald-100">消耗储值</span>
                  <span className="font-bold text-xl">¥{data.statistics.total_deduct_cash.toFixed(2)}</span>
                </div>
              </div>
            </div>
          </>
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
          className="flex flex-col items-center py-2 px-4 text-slate-500"
        >
          <FileCheck className="w-6 h-6" />
          <span className="text-xs mt-1">记录</span>
        </button>
        <button
          onClick={() => navigate('/wap/performance')}
          className="flex flex-col items-center py-2 px-4 text-emerald-600"
        >
          <TrendingUp className="w-6 h-6" />
          <span className="text-xs mt-1">业绩</span>
        </button>
      </nav>

      {/* Spacer for bottom nav */}
      <div className="h-20" />
    </div>
  );
};

export default Performance;
