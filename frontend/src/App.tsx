import { BrowserRouter, Routes, Route, Link, useLocation, Navigate } from 'react-router-dom';
import { Users, Calendar, Package, CreditCard, Settings, Brain, BookOpen, Activity, LogOut, HelpCircle } from 'lucide-react';
import { AuthProvider, useAuth } from './auth';
import { LicenseProvider, useLicenseStatus } from './hooks/useLicenseStatus';
import { TrialBanner } from './components/TrialBanner';
import Login from './pages/Login';
import Clients from './pages/Clients';
import Billing from './pages/Billing';
import SettingsPage from './pages/Settings';
import Bookings from './pages/Bookings';
import Inventory from './pages/Inventory';
import Staff from './pages/Staff';
import AIDashboard from './pages/AIDashboard';
import AIAnalysis from './pages/AIAnalysis';
import PlaybooksPage from './pages/Playbooks';
import DashboardPage from './pages/Dashboard';
import UnifiedDashboard from './pages/UnifiedDashboard';
import Help from './pages/Help';
// WAP 端页面
import WapIndex from './pages/wap/index';
import WapLogin from './pages/wap/Login';
import WapDashboard from './pages/wap/Dashboard';
import WapServiceEntry from './pages/wap/ServiceEntry';
import WapRecords from './pages/wap/Records';
import WapPerformance from './pages/wap/Performance';
import WapChangePassword from './pages/wap/ChangePassword';


const SidebarItem = ({ to, icon: Icon, label }: { to: string, icon: React.ElementType, label: string }) => {
  const location = useLocation();
  const isActive = location.pathname === to;

  return (
    <Link
      to={to}
      className={`flex items-center px-4 py-3 my-1 rounded-lg transition-colors ${
        isActive
          ? 'bg-emerald-600 text-white'
          : 'text-gray-300 hover:bg-slate-700 hover:text-white'
      }`}
    >
      <Icon className="w-5 h-5 mr-3" />
      <span className="font-medium">{label}</span>
    </Link>
  );
};

const TierBadge = () => {
  const { info } = useLicenseStatus();
  const tierLabel: Record<string, string> = {
    basic: '基础版',
    pro: '专业版',
    business: '至尊版',
  };
  const label = tierLabel[info.tier] || info.tier;
  const isTrial = info.is_trial && info.status === 'trial_active';
  const cls = info.status === 'grace_period'
    ? 'bg-red-100 text-red-700 border-red-200'
    : isTrial
      ? 'bg-blue-100 text-blue-700 border-blue-200'
      : info.tier === 'business'
        ? 'bg-amber-100 text-amber-700 border-amber-200'
        : info.tier === 'pro'
          ? 'bg-emerald-100 text-emerald-700 border-emerald-200'
          : 'bg-slate-100 text-slate-600 border-slate-200';
  return (
    <span className={`text-xs px-2 py-0.5 rounded border font-medium ${cls}`}>
      {isTrial ? `${label} · 试用` : label}
    </span>
  );
};

const Layout = ({ children }: { children: React.ReactNode }) => {
  const { user, logout } = useAuth();

  return (
    <div className="flex h-screen bg-gray-50">
      {/* Sidebar */}
      <div className="w-64 bg-slate-800 text-white flex flex-col shadow-xl">
        <div className="p-6 border-b border-slate-700">
          <h2 className="text-xl font-bold flex items-center">
            <span className="text-emerald-400 mr-2">&#10022;</span> AI-Care
          </h2>
          <p className="text-xs text-slate-400 mt-1">智能个人护理管理平台</p>
        </div>
        <div className="flex-1 px-3 py-4 overflow-y-auto">
          <SidebarItem to="/" icon={Activity} label="智能驾驶舱" />
          <SidebarItem to="/ai-analysis" icon={Brain} label="深度分析" />
          <SidebarItem to="/playbooks" icon={BookOpen} label="运营剧本" />
          <div className="border-t border-slate-700 my-3" />
          <SidebarItem to="/clients" icon={Users} label="客户档案" />
          <SidebarItem to="/bookings" icon={Calendar} label="预约排班" />
          <SidebarItem to="/staff" icon={Users} label="员工与技师" />
          <SidebarItem to="/inventory" icon={Package} label="库存耗材" />
          <SidebarItem to="/billing" icon={CreditCard} label="财务收银" />
        </div>
        <div className="p-4 border-t border-slate-700">
          <SidebarItem to="/settings" icon={Settings} label="系统设置" />
          <SidebarItem to="/help" icon={HelpCircle} label="帮助中心" />
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 overflow-auto">
        {/* 试用 / 到期 / 宽限期横幅 */}
        <TrialBanner />
        <header className="bg-white shadow-sm px-8 py-4 flex justify-between items-center">
          <div className="text-gray-600 flex items-center gap-3">
            <span>本地商户控制台</span>
            <TierBadge />
          </div>
          <div className="flex items-center space-x-4">
            <span className="text-sm text-slate-600 font-medium">{user?.display_name || user?.username}</span>
            <button onClick={logout} className="flex items-center gap-1 text-sm text-slate-400 hover:text-red-500 transition-colors" title="退出登录">
              <LogOut className="w-4 h-4" /> 退出
            </button>
          </div>
        </header>
        <main>
          {children}
        </main>
      </div>
    </div>
  );
};

const ProtectedRoute = ({ children }: { children: React.ReactNode }) => {
  const { token, loading } = useAuth();
  if (loading) return null;
  if (!token) return <Navigate to="/login" replace />;
  return <>{children}</>;
};

function AppRoutes() {
  return (
    <Routes>
      {/* 登录页（无需鉴权） */}
      <Route path="/login" element={<Login />} />

      {/* PC 管理后台路由（需要鉴权） */}
      <Route path="/" element={<ProtectedRoute><Layout><UnifiedDashboard /></Layout></ProtectedRoute>} />
      <Route path="/dashboard-business" element={<ProtectedRoute><Layout><DashboardPage /></Layout></ProtectedRoute>} />
      <Route path="/ai-dashboard" element={<ProtectedRoute><Layout><AIDashboard /></Layout></ProtectedRoute>} />
      <Route path="/ai-analysis" element={<ProtectedRoute><Layout><AIAnalysis /></Layout></ProtectedRoute>} />
      <Route path="/playbooks" element={<ProtectedRoute><Layout><PlaybooksPage /></Layout></ProtectedRoute>} />
      <Route path="/clients" element={<ProtectedRoute><Layout><Clients /></Layout></ProtectedRoute>} />
      <Route path="/bookings" element={<ProtectedRoute><Layout><Bookings /></Layout></ProtectedRoute>} />
      <Route path="/staff" element={<ProtectedRoute><Layout><Staff /></Layout></ProtectedRoute>} />
      <Route path="/inventory" element={<ProtectedRoute><Layout><Inventory /></Layout></ProtectedRoute>} />
      <Route path="/billing" element={<ProtectedRoute><Layout><Billing /></Layout></ProtectedRoute>} />
      <Route path="/settings" element={<ProtectedRoute><Layout><SettingsPage /></Layout></ProtectedRoute>} />
      <Route path="/help" element={<ProtectedRoute><Layout><Help /></Layout></ProtectedRoute>} />

      {/* WAP 端路由（独立布局，无侧边栏，WAP 有自己的登录）*/}
      <Route path="/wap" element={<WapIndex />} />
      <Route path="/wap/login" element={<WapLogin />} />
      <Route path="/wap/dashboard" element={<WapDashboard />} />
      <Route path="/wap/service-entry" element={<WapServiceEntry />} />
      <Route path="/wap/records" element={<WapRecords />} />
      <Route path="/wap/performance" element={<WapPerformance />} />
      <Route path="/wap/change-password" element={<WapChangePassword />} />
    </Routes>
  );
}

function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <LicenseProvider>
          <AppRoutes />
        </LicenseProvider>
      </AuthProvider>
    </BrowserRouter>
  );
}

export default App;
