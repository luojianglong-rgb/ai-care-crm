import { useState, useEffect } from 'react';
import axios from 'axios';
import { BookOpen, Play, CheckCircle, XCircle, ChevronDown, ChevronUp, Loader2, Send, Copy, MessageSquare } from 'lucide-react';
import { ReadOnlyButton } from '../components/ReadOnlyGuard';

const API = import.meta.env.VITE_API_URL || '';

interface PlaybookItem {
  id: string; name: string; description: string; trigger_type: string;
  approval_mode: string; send_channel: string; is_active: number; is_system: number;
  priority: number; cooldown_days: number; task_count: number; pending_count: number;
}
interface TaskItem {
  id: string; playbook_id: string; playbook_name: string; client_id: string;
  client_name: string; generated_content: string; status: string;
  approval_mode: string; send_channel: string; scheduled_at?: string; sent_at?: string; created_at?: string;
  error_message?: string;
}

const triggerLabels: Record<string, string> = {
  post_service: '服务后', solar_term: '节气', weather_change: '天气',
  birthday: '生日', time_since_visit: '久未到店', lifecycle_change: '状态变更',
};
const approvalLabels: Record<string, string> = { auto: '全自动', sampling: '抽检', manual: '逐条审批' };
const statusLabels: Record<string, { text: string; color: string }> = {
  pending_approval: { text: '待审批', color: 'text-orange-600 bg-orange-50 border-orange-200' },
  queued: { text: '排队中', color: 'text-blue-600 bg-blue-50 border-blue-200' },
  sent: { text: '已发送', color: 'text-emerald-600 bg-emerald-50 border-emerald-200' },
  failed: { text: '失败', color: 'text-red-600 bg-red-50 border-red-200' },
  rejected: { text: '已驳回', color: 'text-slate-600 bg-slate-50 border-slate-200' },
};

const Playbooks = () => {
  const [tab, setTab] = useState<'playbooks' | 'tasks'>('playbooks');
  const [playbooks, setPlaybooks] = useState<PlaybookItem[]>([]);
  const [tasks, setTasks] = useState<TaskItem[]>([]);
  const [pendingTasks, setPendingTasks] = useState<TaskItem[]>([]);
  const [scanning, setScanning] = useState(false);
  const [expandedPb, setExpandedPb] = useState<string | null>(null);
  const [collecting, setCollecting] = useState(false);

  const fetchPlaybooks = () => axios.get(`${API}/api/v1/playbooks/`).then(r => setPlaybooks(r.data)).catch(console.error);
  const fetchTasks = () => axios.get(`${API}/api/v1/campaigns/tasks?limit=100`).then(r => setTasks(r.data)).catch(console.error);
  const fetchPending = () => axios.get(`${API}/api/v1/campaigns/tasks/pending`).then(r => setPendingTasks(r.data)).catch(console.error);

  useEffect(() => { fetchPlaybooks(); fetchTasks(); fetchPending(); }, []);

  const togglePlaybook = async (id: string) => {
    await axios.put(`${API}/api/v1/playbooks/${id}/toggle`);
    fetchPlaybooks();
  };

  const handleScan = async () => {
    setScanning(true);
    try {
      const r = await axios.post(`${API}/api/v1/playbooks/scan`);
      alert(`扫描完成！生命周期更新 ${r.data.lifecycle_updated} 人，创建 ${r.data.tasks_created} 条营销任务`);
      fetchPlaybooks(); fetchTasks(); fetchPending();
    } catch (e) { alert('扫描失败'); }
    setScanning(false);
  };

  const handleApprove = async (taskId: string) => {
    await axios.put(`${API}/api/v1/campaigns/tasks/${taskId}/approve`);
    fetchPending(); fetchTasks();
  };
  const handleReject = async (taskId: string) => {
    await axios.put(`${API}/api/v1/campaigns/tasks/${taskId}/reject`, { reason: '店长驳回' });
    fetchPending(); fetchTasks();
  };
  const handleBatchApprove = async (playbookId: string) => {
    const r = await axios.post(`${API}/api/v1/campaigns/tasks/batch-approve`, { playbook_id: playbookId });
    alert(`已批准 ${r.data.approved_count} 条任务`);
    fetchPending(); fetchTasks();
  };

  const handleSendTask = async (taskId: string) => {
    try {
      const r = await axios.post(`${API}/api/v1/campaigns/tasks/${taskId}/send`);
      if (r.data.success) {
        alert(`发送成功（渠道: ${r.data.channel}）`);
      } else {
        alert(`发送失败: ${r.data.error}`);
      }
      fetchTasks(); fetchPending();
    } catch (e: any) {
      alert(e.response?.data?.detail || '发送失败');
    }
  };

  const handleCopyContent = (content: string) => {
    navigator.clipboard.writeText(content).then(() => alert('文案已复制到剪贴板')).catch(() => {
      // fallback
      const ta = document.createElement('textarea');
      ta.value = content;
      document.body.appendChild(ta);
      ta.select();
      document.execCommand('copy');
      document.body.removeChild(ta);
      alert('文案已复制到剪贴板');
    });
  };

  const handleCollectSms = async () => {
    setCollecting(true);
    try {
      const r = await axios.post(`${API}/api/v1/replies/collect/sms`);
      alert(`短信回复采集完成！\n采集：${r.data.collected} 条\nAI 解析：${r.data.parsed} 条`);
    } catch (e: any) {
      alert(e.response?.data?.detail || '采集失败');
    }
    setCollecting(false);
  };

  return (
    <div className="p-8 max-w-7xl mx-auto">
      <div className="mb-6 flex justify-between items-end">
        <div>
          <h1 className="text-3xl font-black text-slate-800 tracking-tight flex items-center gap-2">
            <BookOpen className="w-8 h-8 text-emerald-600" /> 运营剧本
          </h1>
          <p className="text-slate-500 mt-1">自动化营销触达管理</p>
        </div>
        <div className="flex gap-2">
          <ReadOnlyButton>
            <button onClick={handleCollectSms} disabled={collecting}
              className="px-5 py-2.5 bg-blue-600 hover:bg-blue-700 disabled:bg-slate-300 text-white rounded-xl font-bold text-sm flex items-center gap-2">
              {collecting ? <Loader2 className="w-4 h-4 animate-spin" /> : <MessageSquare className="w-4 h-4" />}
              {collecting ? '采集中...' : '采集短信回复'}
            </button>
          </ReadOnlyButton>
          <ReadOnlyButton>
            <button onClick={handleScan} disabled={scanning}
              className="px-5 py-2.5 bg-emerald-600 hover:bg-emerald-700 disabled:bg-slate-300 text-white rounded-xl font-bold text-sm flex items-center gap-2">
              {scanning ? <Loader2 className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4" />}
              {scanning ? '扫描中...' : '立即执行扫描'}
            </button>
          </ReadOnlyButton>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 mb-6 bg-slate-100 p-1 rounded-xl w-fit">
        <button onClick={() => setTab('playbooks')}
          className={`px-5 py-2 rounded-lg text-sm font-bold transition-colors ${tab === 'playbooks' ? 'bg-white text-slate-800 shadow-sm' : 'text-slate-500 hover:text-slate-700'}`}>
          剧本列表
        </button>
        <button onClick={() => setTab('tasks')}
          className={`px-5 py-2 rounded-lg text-sm font-bold transition-colors flex items-center gap-1 ${tab === 'tasks' ? 'bg-white text-slate-800 shadow-sm' : 'text-slate-500 hover:text-slate-700'}`}>
          营销任务 {pendingTasks.length > 0 && <span className="bg-orange-500 text-white text-xs px-1.5 py-0.5 rounded-full">{pendingTasks.length}</span>}
        </button>
      </div>

      {tab === 'playbooks' && (
        <div className="space-y-3">
          {playbooks.map(pb => (
            <div key={pb.id} className="bg-white rounded-2xl shadow-sm border border-slate-100 overflow-hidden">
              <div className="p-5 flex justify-between items-center">
                <div className="flex items-center gap-4">
                  <button onClick={() => togglePlaybook(pb.id)}
                    className={`w-10 h-6 rounded-full transition-colors relative ${pb.is_active ? 'bg-emerald-500' : 'bg-slate-300'}`}>
                    <span className={`absolute top-0.5 w-5 h-5 bg-white rounded-full shadow transition-all ${pb.is_active ? 'left-4' : 'left-0.5'}`} />
                  </button>
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="font-bold text-slate-800">{pb.name}</span>
                      {pb.is_system ? <span className="text-xs bg-slate-100 text-slate-500 px-2 py-0.5 rounded-full">系统预设</span> : null}
                    </div>
                    <div className="flex gap-3 mt-1 text-xs text-slate-500">
                      <span>触发: {triggerLabels[pb.trigger_type] || pb.trigger_type}</span>
                      <span>审批: {approvalLabels[pb.approval_mode] || pb.approval_mode}</span>
                      <span>优先级: P{pb.priority}</span>
                      <span>冷却: {pb.cooldown_days}天</span>
                    </div>
                  </div>
                </div>
                <div className="flex items-center gap-4">
                  <div className="text-right text-xs text-slate-500">
                    <div>累计 <span className="font-bold text-slate-700">{pb.task_count}</span> 条</div>
                    {pb.pending_count > 0 && <div className="text-orange-600 font-bold">待审 {pb.pending_count}</div>}
                  </div>
                  <button onClick={() => setExpandedPb(expandedPb === pb.id ? null : pb.id)} className="text-slate-400 hover:text-slate-600">
                    {expandedPb === pb.id ? <ChevronUp className="w-5 h-5" /> : <ChevronDown className="w-5 h-5" />}
                  </button>
                </div>
              </div>
              {expandedPb === pb.id && (
                <div className="px-5 pb-5 pt-0 border-t border-slate-50">
                  <p className="text-sm text-slate-500 mb-3">{pb.description}</p>
                  {pb.pending_count > 0 && (
                    <button onClick={() => handleBatchApprove(pb.id)}
                      className="text-sm bg-emerald-50 text-emerald-700 px-4 py-2 rounded-lg font-bold border border-emerald-200 hover:bg-emerald-100">
                      一键批准全部待审任务 ({pb.pending_count})
                    </button>
                  )}
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {tab === 'tasks' && (
        <div className="space-y-6">
          {/* Pending Approval */}
          {pendingTasks.length > 0 && (
            <div className="bg-white rounded-2xl shadow-sm border border-orange-100 overflow-hidden">
              <div className="p-4 bg-orange-50 border-b border-orange-100">
                <h3 className="text-sm font-bold text-orange-700">待审批 ({pendingTasks.length})</h3>
              </div>
              <div className="divide-y divide-slate-50">
                {pendingTasks.map(t => (
                  <div key={t.id} className="p-4">
                    <div className="flex justify-between items-start mb-2">
                      <div>
                        <span className="font-medium text-slate-700">{t.client_name}</span>
                        <span className="text-xs text-slate-400 ml-2">· {t.playbook_name}</span>
                      </div>
                      <div className="flex gap-2">
                        <button onClick={() => handleApprove(t.id)} className="text-xs bg-emerald-50 text-emerald-700 px-3 py-1.5 rounded-lg font-bold border border-emerald-200 hover:bg-emerald-100 flex items-center gap-1">
                          <CheckCircle className="w-3 h-3" /> 通过
                        </button>
                        <button onClick={() => handleReject(t.id)} className="text-xs bg-red-50 text-red-600 px-3 py-1.5 rounded-lg font-bold border border-red-200 hover:bg-red-100 flex items-center gap-1">
                          <XCircle className="w-3 h-3" /> 驳回
                        </button>
                      </div>
                    </div>
                    <p className="text-sm text-slate-600 bg-slate-50 rounded-xl p-3">{t.generated_content}</p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* All Tasks */}
          <div className="bg-white rounded-2xl shadow-sm border border-slate-100 overflow-hidden">
            <div className="p-4 border-b border-slate-100 bg-slate-50/50">
              <h3 className="text-sm font-bold text-slate-500 uppercase">全部任务</h3>
            </div>
            <div className="divide-y divide-slate-50 max-h-[600px] overflow-y-auto">
              {tasks.length === 0 ? (
                <div className="p-8 text-center text-slate-400 text-sm">暂无营销任务，点击"立即执行扫描"生成</div>
              ) : tasks.map(t => {
                const sl = statusLabels[t.status] || statusLabels.queued;
                return (
                  <div key={t.id} className="p-4 hover:bg-slate-50">
                    <div className="flex justify-between items-center mb-1">
                      <div className="flex items-center gap-2">
                        <span className="font-medium text-sm text-slate-700">{t.client_name}</span>
                        <span className="text-xs text-slate-400">· {t.playbook_name}</span>
                      </div>
                      <div className="flex items-center gap-2">
                        <span className={`text-xs px-2 py-0.5 rounded-full font-medium border ${sl.color}`}>{sl.text}</span>
                        {(t.status === 'queued' || t.status === 'approved' || t.status === 'failed') && (
                          <button onClick={() => handleSendTask(t.id)} className="text-xs bg-emerald-50 text-emerald-700 px-2 py-1 rounded-lg font-bold border border-emerald-200 hover:bg-emerald-100 flex items-center gap-1" title="发送短信">
                            <Send className="w-3 h-3" /> {t.status === 'failed' ? '重发' : '发送'}
                          </button>
                        )}
                        <button onClick={() => handleCopyContent(t.generated_content)} className="text-xs bg-blue-50 text-blue-700 px-2 py-1 rounded-lg font-bold border border-blue-200 hover:bg-blue-100 flex items-center gap-1" title="复制文案到微信">
                          <Copy className="w-3 h-3" /> 复制
                        </button>
                      </div>
                    </div>
                    <p className="text-xs text-slate-500 line-clamp-2">{t.generated_content}</p>
                    <div className="flex justify-between items-center mt-1">
                      <span className="text-xs text-slate-400">{t.created_at?.slice(0, 16)}</span>
                      {t.status === 'sent' && <span className="text-xs text-emerald-500">短信已发送 {t.sent_at?.slice(0, 16)}</span>}
                      {t.status === 'failed' && <span className="text-xs text-red-500">失败: {t.error_message || '未知错误'}</span>}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default Playbooks;
