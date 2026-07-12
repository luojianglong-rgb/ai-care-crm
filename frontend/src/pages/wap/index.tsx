import React, { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';

const WapIndex: React.FC = () => {
  const navigate = useNavigate();

  useEffect(() => {
    const token = localStorage.getItem('wap_token');

    if (token) {
      // 已登录，跳转到工作台
      navigate('/wap/dashboard');
    } else {
      // 未登录，跳转到登录页
      navigate('/wap/login');
    }
  }, [navigate]);

  return (
    <div className="min-h-screen bg-gradient-to-b from-emerald-500 to-teal-600 flex items-center justify-center">
      <div className="text-center">
        <h1 className="text-2xl font-black text-white mb-2">AI-Wellness</h1>
        <p className="text-emerald-100">技师移动工作台</p>
        <div className="mt-8">
          <div className="w-12 h-12 border-4 border-white border-t-transparent rounded-full animate-spin mx-auto" />
          <p className="text-white text-sm mt-4">加载中...</p>
        </div>
      </div>
    </div>
  );
};

export default WapIndex;
