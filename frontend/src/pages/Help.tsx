import { useState } from 'react';
import {
  Activity, Brain, BookOpen, Users, Calendar, CreditCard, Package, Settings,
  ChevronDown, ChevronUp, Zap, Target, MessageSquare, BarChart3, Shield,
  Mic, Send, HelpCircle, CheckCircle, ArrowRight
} from 'lucide-react';

interface HelpSection {
  id: string;
  title: string;
  icon: React.ElementType;
  description: string;
  features: { title: string; desc: string }[];
  tips?: string[];
}

const helpSections: HelpSection[] = [
  {
    id: 'dashboard',
    title: '智能驾驶舱',
    icon: Activity,
    description: '系统核心仪表盘，实时展示门店运营数据和 AI 智能分析结果。',
    features: [
      { title: '今日收入', desc: '实时统计今日现金收入 + 次卡消费折算金额' },
      { title: '充值订货', desc: '所有客户未消费储值余额 + 次卡剩余折算金额' },
      { title: '客户动态', desc: '最近 7 天新增客户、到店客户、沉默预警客户统计' },
      { title: 'AI 顾问', desc: '智能分析待跟进客户、推荐营销策略' },
      { title: '收入趋势', desc: '近 7 日收入变化趋势图' },
    ],
    tips: ['建议每天早上打开驾驶舱查看当日重点关注客户', 'AI 顾问会自动识别需要关怀的客户']
  },
  {
    id: 'ai-analysis',
    title: '深度分析',
    icon: Brain,
    description: 'AI 驱动的专业分析模块，根据客户症状生成个性化服务方案。',
    features: [
      { title: '客户选择', desc: '从客户列表中选择要分析的客户' },
      { title: '症状录入', desc: '输入客户主诉症状、观察特征（支持语音输入）' },
      { title: 'AI 分析', desc: '大模型自动分析体质/肤质/发质类型，生成专业报告' },
      { title: '调理方案', desc: '一键生成包含店内服务 + 居家建议的个性化方案' },
      { title: '历史记录', desc: '查看客户历次分析记录，追踪健康变化' },
    ],
    tips: ['语音输入可快速记录客户症状，解放双手', 'AI 分析结果会自动保存到客户档案']
  },
  {
    id: 'playbooks',
    title: '运营剧本',
    icon: BookOpen,
    description: '自动化营销触达管理，配置触发规则后系统自动生成营销任务。',
    features: [
      { title: '剧本列表', desc: '查看系统预设和自定义剧本，支持开关控制' },
      { title: '触发类型', desc: '支持节气、天气、生日、久未到店、服务后等多种触发条件' },
      { title: '营销任务', desc: '查看待审批/待发送/已发送的营销任务列表' },
      { title: '审批流程', desc: '支持全自动/抽检/逐条审批三种模式' },
      { title: '发送渠道', desc: '支持微信 RPA、短信 API、剪贴板等多种渠道' },
      { title: '采集微信回复', desc: 'RPA 自动采集客户回复并 AI 解析意图' },
    ],
    tips: ['建议先配置客户微信别名，才能精准自动发送', '每天首次打开页面点击"立即执行扫描"生成今日任务']
  },
  {
    id: 'clients',
    title: '客户档案',
    icon: Users,
    description: '管理客户基本信息、消费卡包、健康档案、分析记录、触达记录、回复记录。',
    features: [
      { title: '客户列表', desc: '查看所有客户，支持姓名/手机号搜索' },
      { title: '新增/编辑客户', desc: '录入客户基本信息、微信别名、消费偏好' },
      { title: '健康档案', desc: '记录每次调理的主诉症状、方案、扣费' },
      { title: '专业分析', desc: '查看客户历次 AI 分析结果' },
      { title: '生命周期', desc: '查看客户状态（新客/活跃/沉默/流失预警）' },
      { title: '触达记录', desc: '查看发送给客户的营销消息历史' },
      { title: '回复记录', desc: '查看客户回复及 AI 解析结果' },
      { title: '导出 Excel', desc: '一键导出客户档案到 Excel 文件' },
    ],
    tips: ['微信别名用于 RPA 自动发送时匹配联系人', '删除客户会同时删除相关健康档案和交易记录']
  },
  {
    id: 'bookings',
    title: '预约排班',
    icon: Calendar,
    description: '管理客户预约和技师排班，支持预约确认、完成、取消状态流转。',
    features: [
      { title: '预约列表', desc: '查看今日/未来预约，支持状态筛选' },
      { title: '新增预约', desc: '为客户创建预约，选择服务项目和技师' },
      { title: '状态管理', desc: '确认/完成/取消预约' },
      { title: '技师排班', desc: '查看技师工作时间安排' },
    ],
    tips: ['预约时间会自动检测技师是否空闲']
  },
  {
    id: 'staff',
    title: '员工与技师',
    icon: Users,
    description: '管理门店员工和技师信息，设置支持的服务项目。',
    features: [
      { title: '员工列表', desc: '查看所有员工，支持新增/编辑/删除' },
      { title: '角色设置', desc: '设置员工角色（店长/技师/前台等）' },
      { title: '服务项目', desc: '配置技师支持的服务项目' },
      { title: 'WAP 登录', desc: '技师可通过手机端登录录入服务记录' },
    ],
    tips: ['技师的 WAP 端密码在首次创建时设置']
  },
  {
    id: 'inventory',
    title: '库存耗材',
    icon: Package,
    description: '管理门店库存和耗材使用记录，支持低库存预警。',
    features: [
      { title: '库存列表', desc: '查看库存项目和数量' },
      { title: '分类管理', desc: '按耗材分类整理库存' },
      { title: '出入库记录', desc: '记录库存变动和使用情况' },
      { title: '低库存预警', desc: '库存不足时自动提醒' },
    ],
    tips: ['建议每周盘点一次库存，及时补充']
  },
  {
    id: 'billing',
    title: '财务收银',
    icon: CreditCard,
    description: '处理客户充值、消费、扣费，管理次卡和储值卡余额。',
    features: [
      { title: '客户选择', desc: '选择要操作的客户' },
      { title: '充值', desc: '为客户充值次卡或储值余额' },
      { title: '消费', desc: '扣减次卡次数或储值余额，同时记录健康档案' },
      { title: '交易流水', desc: '查看所有交易记录，支持日期筛选' },
      { title: '导出 Excel', desc: '一键导出交易记录到 Excel 文件' },
    ],
    tips: ['充值时会自动生成交易流水', '消费时会同步记录健康档案']
  },
  {
    id: 'settings',
    title: '系统设置',
    icon: Settings,
    description: '管理系统配置、服务项目、耗材分类、管理员账号。',
    features: [
      { title: '系统信息', desc: '查看门店信息、授权状态、AI 配置、额度使用' },
      { title: '服务项目', desc: '管理门店提供的服务项目列表' },
      { title: '耗材分类', desc: '管理库存耗材的分类' },
      { title: '管理员', desc: '管理管理台登录账号，支持新增/删除管理员' },
    ],
    tips: ['默认管理员账号：admin / admin，请及时修改密码']
  },
];

const quickStartSteps = [
  { step: 1, title: '登录系统', desc: '使用管理员账号登录（默认 admin/admin）', icon: Shield },
  { step: 2, title: '配置门店', desc: '在系统设置中完善门店信息、服务项目', icon: Settings },
  { step: 3, title: '添加员工', desc: '录入技师信息并设置服务项目', icon: Users },
  { step: 4, title: '录入客户', desc: '添加客户档案，填写微信别名以便自动发送', icon: Users },
  { step: 5, title: '配置 AI', desc: '在 config.yaml 中配置大模型 API Key', icon: Brain },
  { step: 6, title: '启用剧本', desc: '开启运营剧本，系统自动生成营销任务', icon: BookOpen },
];

const Help = () => {
  const [expandedSection, setExpandedSection] = useState<string | null>('dashboard');

  const toggleSection = (id: string) => {
    setExpandedSection(expandedSection === id ? null : id);
  };

  return (
    <div className="p-8 max-w-5xl mx-auto">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-slate-800 flex items-center gap-3">
          <HelpCircle className="w-8 h-8 text-emerald-600" />
          系统帮助
        </h1>
        <p className="text-slate-500 mt-2">了解 AI-Care CRM 各模块功能，快速上手使用</p>
      </div>

      {/* Quick Start */}
      <div className="bg-gradient-to-r from-emerald-50 to-teal-50 rounded-2xl p-6 mb-8 border border-emerald-100">
        <h2 className="text-xl font-bold text-emerald-800 flex items-center gap-2 mb-4">
          <Zap className="w-5 h-5" />
          快速开始
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {quickStartSteps.map((item) => (
            <div key={item.step} className="bg-white rounded-xl p-4 border border-emerald-100 shadow-sm">
              <div className="flex items-start gap-3">
                <div className="w-8 h-8 rounded-full bg-emerald-600 text-white flex items-center justify-center text-sm font-bold flex-shrink-0">
                  {item.step}
                </div>
                <div>
                  <h3 className="font-bold text-slate-800">{item.title}</h3>
                  <p className="text-sm text-slate-500 mt-0.5">{item.desc}</p>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Feature Highlights */}
      <div className="bg-white rounded-2xl border border-slate-200 p-6 mb-8">
        <h2 className="text-xl font-bold text-slate-800 flex items-center gap-2 mb-4">
          <Target className="w-5 h-5 text-blue-600" />
          核心亮点
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="flex items-center gap-3 p-3 bg-orange-50 rounded-xl">
            <Shield className="w-5 h-5 text-orange-600" />
            <div>
              <div className="font-bold text-slate-800 text-sm">客户信息保密</div>
              <div className="text-xs text-slate-500">本地存储，数据安全</div>
            </div>
          </div>
          <div className="flex items-center gap-3 p-3 bg-blue-50 rounded-xl">
            <Mic className="w-5 h-5 text-blue-600" />
            <div>
              <div className="font-bold text-slate-800 text-sm">语音录入</div>
              <div className="text-xs text-slate-500">解放双手，快速记录</div>
            </div>
          </div>
          <div className="flex items-center gap-3 p-3 bg-purple-50 rounded-xl">
            <Brain className="w-5 h-5 text-purple-600" />
            <div>
              <div className="font-bold text-slate-800 text-sm">AI 分析</div>
              <div className="text-xs text-slate-500">专业体质/肤质诊断</div>
            </div>
          </div>
          <div className="flex items-center gap-3 p-3 bg-emerald-50 rounded-xl">
            <Send className="w-5 h-5 text-emerald-600" />
            <div>
              <div className="font-bold text-slate-800 text-sm">自动发送</div>
              <div className="text-xs text-slate-500">微信 RPA 智能触达</div>
            </div>
          </div>
        </div>
      </div>

      {/* Page Sections */}
      <div className="space-y-4">
        <h2 className="text-xl font-bold text-slate-800 flex items-center gap-2">
          <BarChart3 className="w-5 h-5 text-slate-600" />
          页面功能详解
        </h2>

        {helpSections.map((section) => {
          const Icon = section.icon;
          const isExpanded = expandedSection === section.id;

          return (
            <div key={section.id} className="bg-white rounded-2xl border border-slate-200 overflow-hidden">
              {/* Section Header */}
              <button
                onClick={() => toggleSection(section.id)}
                className="w-full flex items-center justify-between p-5 hover:bg-slate-50 transition-colors"
              >
                <div className="flex items-center gap-4">
                  <div className="w-10 h-10 rounded-xl bg-emerald-100 text-emerald-600 flex items-center justify-center">
                    <Icon className="w-5 h-5" />
                  </div>
                  <div className="text-left">
                    <h3 className="font-bold text-slate-800">{section.title}</h3>
                    <p className="text-sm text-slate-500 mt-0.5">{section.description}</p>
                  </div>
                </div>
                {isExpanded ? (
                  <ChevronUp className="w-5 h-5 text-slate-400" />
                ) : (
                  <ChevronDown className="w-5 h-5 text-slate-400" />
                )}
              </button>

              {/* Section Content */}
              {isExpanded && (
                <div className="px-5 pb-5 border-t border-slate-100">
                  <div className="pt-4">
                    <h4 className="text-sm font-bold text-slate-500 uppercase mb-3">功能列表</h4>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                      {section.features.map((feature, idx) => (
                        <div key={idx} className="flex items-start gap-2 p-3 bg-slate-50 rounded-xl">
                          <CheckCircle className="w-4 h-4 text-emerald-500 mt-0.5 flex-shrink-0" />
                          <div>
                            <div className="font-medium text-slate-700 text-sm">{feature.title}</div>
                            <div className="text-xs text-slate-500 mt-0.5">{feature.desc}</div>
                          </div>
                        </div>
                      ))}
                    </div>

                    {section.tips && section.tips.length > 0 && (
                      <div className="mt-4 p-4 bg-amber-50 rounded-xl border border-amber-100">
                        <h4 className="text-sm font-bold text-amber-700 mb-2 flex items-center gap-1">
                          <Zap className="w-4 h-4" />
                          使用技巧
                        </h4>
                        <ul className="space-y-1">
                          {section.tips.map((tip, idx) => (
                            <li key={idx} className="text-sm text-amber-800 flex items-start gap-2">
                              <ArrowRight className="w-3 h-3 mt-1 flex-shrink-0" />
                              {tip}
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* WAP Section */}
      <div className="mt-8 bg-gradient-to-r from-purple-50 to-pink-50 rounded-2xl p-6 border border-purple-100">
        <h2 className="text-xl font-bold text-purple-800 flex items-center gap-2 mb-4">
          <MessageSquare className="w-5 h-5" />
          WAP 技师端
        </h2>
        <p className="text-purple-700 mb-4">
          技师可通过手机浏览器访问 WAP 端（地址：http://服务器IP:8000/wap），用于：
        </p>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="bg-white rounded-xl p-4 border border-purple-100">
            <h3 className="font-bold text-slate-800">服务录入</h3>
            <p className="text-sm text-slate-500 mt-1">录入客户调理记录，支持语音输入</p>
          </div>
          <div className="bg-white rounded-xl p-4 border border-purple-100">
            <h3 className="font-bold text-slate-800">历史记录</h3>
            <p className="text-sm text-slate-500 mt-1">查看自己的服务记录</p>
          </div>
          <div className="bg-white rounded-xl p-4 border border-purple-100">
            <h3 className="font-bold text-slate-800">业绩统计</h3>
            <p className="text-sm text-slate-500 mt-1">查看个人服务次数和业绩</p>
          </div>
        </div>
      </div>

      {/* 套餐说明 */}
      <div className="mt-8 bg-gradient-to-r from-amber-50 to-orange-50 rounded-2xl p-6 border border-amber-100">
        <h2 className="text-xl font-bold text-amber-800 flex items-center gap-2 mb-4">
          <Shield className="w-5 h-5" />
          套餐等级
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
          <div className="bg-white rounded-xl p-4 border border-slate-200 relative">
            <h3 className="font-bold text-slate-800">基础版</h3>
            <p className="text-lg font-bold text-slate-600 mt-1">永久免费</p>
            <p className="text-sm text-slate-500 mt-1">功能体验版</p>
            <ul className="text-xs text-slate-600 mt-2 space-y-1">
              <li>• 最多 10 个客户</li>
              <li>• 最多 3 名员工</li>
              <li>• AI 试用 5 次（用完即止）</li>
              <li>• 不支持数据导出</li>
              <li>• 不支持营销剧本/短信</li>
            </ul>
          </div>
          <div className="bg-white rounded-xl p-4 border-2 border-emerald-300 relative">
            <div className="absolute -top-2 right-2 bg-emerald-500 text-white text-xs px-2 py-0.5 rounded">推荐</div>
            <h3 className="font-bold text-emerald-700">专业版</h3>
            <p className="text-lg font-bold text-emerald-600 mt-1">¥499<span className="text-xs font-normal text-slate-400">/年</span></p>
            <p className="text-sm text-slate-500 mt-1">适合单店经营 · 赠送 60 天试用</p>
            <ul className="text-xs text-slate-600 mt-2 space-y-1">
              <li>• 最多 100 个客户</li>
              <li>• 最多 10 名员工</li>
              <li>• AI 分析每周 50 次</li>
              <li>• 数据导出每月 1 次</li>
              <li>• 预设剧本使用</li>
            </ul>
          </div>
          <div className="bg-white rounded-xl p-4 border border-purple-200">
            <h3 className="font-bold text-purple-700">至尊版</h3>
            <p className="text-lg font-bold text-purple-600 mt-1">¥999<span className="text-xs font-normal text-slate-400">/年</span></p>
            <p className="text-sm text-slate-500 mt-1">适合连锁/多店 · 赠送 60 天试用</p>
            <ul className="text-xs text-slate-600 mt-2 space-y-1">
              <li>• 无限客户/员工</li>
              <li>• AI 分析不限次数</li>
              <li>• 微信 RPA 每月 500 条</li>
              <li>• 短信 API 每月 100 条</li>
              <li>• 回复采集 + AI 解析</li>
              <li>• 自定义营销剧本</li>
            </ul>
          </div>
        </div>
        <div className="bg-emerald-50 rounded-xl p-4 border border-emerald-200 mb-4">
          <h4 className="font-bold text-emerald-700 mb-1">🎁 新客专享</h4>
          <p className="text-sm text-slate-700">
            专业版 / 至尊版均<strong>赠送 60 天免费试用</strong>，体验完整功能后再付费。
            试用到期后系统进入 7 天只读宽限期，您的客户数据完整保留，激活正式版即可立即恢复全部写入功能。
          </p>
        </div>
        <div className="bg-white rounded-xl p-4 border border-amber-200">
          <h4 className="font-bold text-amber-700 mb-2">如何获取激活码？</h4>
          <ol className="text-sm text-slate-600 space-y-1">
            <li>1. 联系销售（需提供机器码，在「设置 → 系统信息」中查看）</li>
            <li>2. 在「设置 → 系统信息」页面的「激活码」输入框中粘贴激活码</li>
            <li>3. 点击「激活」按钮，验证成功后套餐等级将自动更新</li>
            <li>4. 顶部横幅会立即更新为新的套餐状态</li>
          </ol>
        </div>
      </div>

      {/* FAQ */}
      <div className="mt-8 bg-white rounded-2xl border border-slate-200 p-6">
        <h2 className="text-xl font-bold text-slate-800 mb-4">常见问题</h2>
        <div className="space-y-4">
          <div className="border-b border-slate-100 pb-4">
            <h3 className="font-bold text-slate-700">Q: 微信 RPA 自动发送失败怎么办？</h3>
            <p className="text-sm text-slate-500 mt-1">
              A: 请确保：1) 微信 PC 版已登录并保持运行；2) 客户档案中已填写微信别名；3) 微信中已添加该客户为好友。
            </p>
          </div>
          <div className="border-b border-slate-100 pb-4">
            <h3 className="font-bold text-slate-700">Q: AI 分析结果不准确怎么办？</h3>
            <p className="text-sm text-slate-500 mt-1">
              A: 请尽量详细描述客户症状和观察特征，系统会在 config.yaml 中配置的 LLM 模型进行分析。可尝试切换不同的模型提供商。
            </p>
          </div>
          <div className="border-b border-slate-100 pb-4">
            <h3 className="font-bold text-slate-700">Q: 如何导出客户数据？</h3>
            <p className="text-sm text-slate-500 mt-1">
              A: 数据导出为专业版功能。升级后，在客户档案页面点击「导出 Excel」按钮导出客户信息，在财务收银页面导出交易记录。
            </p>
          </div>
          <div className="border-b border-slate-100 pb-4">
            <h3 className="font-bold text-slate-700">Q: 激活码可以换电脑使用吗？</h3>
            <p className="text-sm text-slate-500 mt-1">
              A: 激活码与机器码绑定，一个激活码仅限一台电脑使用。如需更换设备，请联系客服重新生成激活码。
            </p>
          </div>
          <div>
            <h3 className="font-bold text-slate-700">Q: 数据存储在哪里？安全吗？</h3>
            <p className="text-sm text-slate-500 mt-1">
              A: 所有数据存储在本地 SQLite 数据库（src/wellness_crm.db），不上传云端。调用 AI 时会自动脱敏处理客户敏感信息。
            </p>
          </div>
        </div>
      </div>

      {/* Footer */}
      <div className="mt-8 text-center text-slate-400 text-sm">
        <p>AI-Care CRM — 智能个人护理管理平台</p>
        <p className="mt-1">版本：v4.1 | 技术支持：Claude AI</p>
      </div>
    </div>
  );
};

export default Help;