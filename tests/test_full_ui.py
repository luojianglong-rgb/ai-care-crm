"""
AI-Care CRM 全面功能测试脚本
使用 Playwright 无头浏览器测试所有功能模块
"""
import asyncio
import json
import sys
import os

# 设置 UTF-8 编码输出
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

from playwright.async_api import async_playwright

# 测试配置
BASE_URL = "http://localhost:8000"
ADMIN_USER = "admin"
ADMIN_PASS = "admin"

# 测试结果收集
test_results = []

async def log_test(module: str, test_name: str, passed: bool, message: str = ""):
    """记录测试结果"""
    status = "[PASS]" if passed else "[FAIL]"
    result = f"{status} | {module} | {test_name}"
    if message:
        result += f" | {message}"
    print(result)
    test_results.append({
        "module": module,
        "test": test_name,
        "passed": passed,
        "message": message
    })

async def run_tests():
    """执行所有测试"""
    async with async_playwright() as p:
        # 使用 msedge (Edge) 通道，因为 Windows 上已有 Edge 浏览器
        browser = await p.chromium.launch(channel="msedge", headless=True)
        context = await browser.new_context(
            viewport={"width": 1920, "height": 1080},
            locale="zh-CN"
        )
        page = await context.new_page()

        try:
            # ===================== 1. 登录测试 =====================
            print("\n" + "="*60)
            print("模块 1: 登录认证")
            print("="*60)

            await page.goto(BASE_URL)
            await page.wait_for_load_state("networkidle")

            # 检查是否跳转到登录页
            current_url = page.url
            if "login" in current_url or await page.locator('input[type="password"]').count() > 0:
                await log_test("登录认证", "登录页面加载", True)

                # 输入登录信息 - 使用 placeholder 或位置选择器
                inputs = await page.locator('input').all()
                if len(inputs) >= 2:
                    await inputs[0].fill(ADMIN_USER)
                    await inputs[1].fill(ADMIN_PASS)
                    await page.click('button[type="submit"]')
                else:
                    await page.locator('input').first().fill(ADMIN_USER)
                    await page.locator('input[type="password"]').fill(ADMIN_PASS)
                    await page.click('button[type="submit"]')

                # 等待登录成功
                await page.wait_for_url(lambda url: "login" not in url, timeout=10000)
                await log_test("登录认证", "管理员登录", True)
            else:
                await log_test("登录认证", "已登录状态", True)

            # 从浏览器 localStorage 获取 token
            token = await page.evaluate("localStorage.getItem('token')")

            # 如果 localStorage 没有 token，尝试通过 API 登录获取
            if not token:
                login_response = await page.request.post(
                    f"{BASE_URL}/api/v1/auth/login",
                    data=json.dumps({"username": ADMIN_USER, "password": ADMIN_PASS}),
                    headers={"Content-Type": "application/json"}
                )
                if login_response.ok:
                    login_data = await login_response.json()
                    token = login_data.get('token')
                    await log_test("登录认证", "Token 获取", True)
                else:
                    await log_test("登录认证", "Token 获取", False)
            else:
                await log_test("登录认证", "Token 获取", True, "从 localStorage 获取")

            # 设置 Authorization header 用于后续 API 请求
            api_headers = {"Authorization": f"Bearer {token}"} if token else {}

            # ===================== 2. 系统配置测试 =====================
            print("\n" + "="*60)
            print("模块 2: 系统配置")
            print("="*60)

            # 获取系统信息 API
            response = await page.request.get(f"{BASE_URL}/api/v1/config/info", headers=api_headers)
            if response.ok:
                data = await response.json()
                await log_test("系统配置", "API 可访问", True, f"tier={data.get('license', {}).get('tier')}")

                # 检查开发模式
                dev_mode = data.get('server', {}).get('dev_mode', False)
                await log_test("系统配置", "开发模式配置", dev_mode, f"dev_mode={dev_mode}")
            else:
                await log_test("系统配置", "API 可访问", False, f"状态码: {response.status}")

            # ===================== 3. 客户档案测试 =====================
            print("\n" + "="*60)
            print("模块 3: 客户档案")
            print("="*60)

            # 导航到客户页面
            await page.goto(f"{BASE_URL}/clients")
            await page.wait_for_load_state("networkidle")
            await log_test("客户档案", "页面加载", True)

            # 获取客户列表 API
            response = await page.request.get(f"{BASE_URL}/api/v1/clients/", headers=api_headers)
            if response.ok:
                clients = await response.json()
                await log_test("客户档案", "客户列表 API", True, f"共 {len(clients)} 个客户")

                # 查找杨T客户
                yang_client = None
                for c in clients:
                    name = c.get('name', '')
                    if '杨' in name and 'T' in name.upper():
                        yang_client = c
                        break

                if yang_client:
                    await log_test("客户档案", "找到杨T客户", True, f"ID: {yang_client.get('client_id')}")
                else:
                    await log_test("客户档案", "找到杨T客户", False, "未找到杨T客户")
            else:
                await log_test("客户档案", "客户列表 API", False)

            # ===================== 4. 运营剧本测试 =====================
            print("\n" + "="*60)
            print("模块 4: 运营剧本")
            print("="*60)

            await page.goto(f"{BASE_URL}/playbooks")
            await page.wait_for_load_state("networkidle")
            await log_test("运营剧本", "页面加载", True)

            # 检查剧本列表 API
            response = await page.request.get(f"{BASE_URL}/api/v1/playbooks/", headers=api_headers)
            if response.ok:
                playbooks = await response.json()
                await log_test("运营剧本", "剧本列表 API", True, f"共 {len(playbooks)} 个剧本")

                # 检查剧本类型
                trigger_types = set(p.get('trigger_type') for p in playbooks)
                await log_test("运营剧本", "剧本类型覆盖", len(playbooks) >= 5,
                              f"类型: {', '.join(trigger_types)}")
            else:
                await log_test("运营剧本", "剧本列表 API", False, f"状态码: {response.status}")

            # 检查"采集短信回复"按钮
            sms_button = await page.locator('button:has-text("采集短信回复")').count()
            await log_test("运营剧本", "采集短信回复按钮", sms_button > 0,
                          f"找到 {sms_button} 个按钮")

            # ===================== 5. 营销任务测试 =====================
            print("\n" + "="*60)
            print("模块 5: 营销任务")
            print("="*60)

            # 切换到任务标签
            task_tab = await page.locator('button:has-text("营销任务")').count()
            if task_tab > 0:
                await page.click('button:has-text("营销任务")')
                await page.wait_for_load_state("networkidle")
                await log_test("营销任务", "任务标签切换", True)

            # 获取任务列表
            response = await page.request.get(f"{BASE_URL}/api/v1/campaigns/tasks?limit=100", headers=api_headers)
            if response.ok:
                tasks = await response.json()
                await log_test("营销任务", "任务列表 API", True, f"共 {len(tasks)} 个任务")

                # 检查任务状态分布
                status_count = {}
                for t in tasks:
                    status = t.get('status', 'unknown')
                    status_count[status] = status_count.get(status, 0) + 1
                await log_test("营销任务", "任务状态统计", True, str(status_count))
            else:
                await log_test("营销任务", "任务列表 API", False)

            # ===================== 6. 短信功能测试 =====================
            print("\n" + "="*60)
            print("模块 6: 短信功能")
            print("="*60)

            # 检查短信设备状态
            response = await page.request.get(f"{BASE_URL}/api/v1/config/sms/status", headers=api_headers)
            if response.ok:
                sms_status = await response.json()
                await log_test("短信功能", "设备状态 API", True,
                              f"enabled={sms_status.get('enabled')}, available={sms_status.get('available')}")

                if sms_status.get('available'):
                    await log_test("短信功能", "ML307A 设备检测", True,
                                  f"端口: {sms_status.get('port')}, 信号: {sms_status.get('signal')}")
                else:
                    await log_test("短信功能", "ML307A 设备检测", False, "设备不可用")
            else:
                await log_test("短信功能", "设备状态 API", False)

            # 获取接收到的短信
            response = await page.request.get(f"{BASE_URL}/api/v1/config/sms/received", headers=api_headers)
            if response.ok:
                received = await response.json()
                await log_test("短信功能", "短信接收 API", True,
                              f"已接收 {received.get('total', 0)} 条短信")
            else:
                await log_test("短信功能", "短信接收 API", False)

            # 测试短信发送队列状态
            response = await page.request.get(f"{BASE_URL}/api/v1/config/sms/queue", headers=api_headers)
            if response.ok:
                queue = await response.json()
                await log_test("短信功能", "发送队列 API", True,
                              f"队列: {queue.get('queue_size', 0)}, 已发: {queue.get('sent_count', 0)}")
            else:
                await log_test("短信功能", "发送队列 API", False)

            # ===================== 7. 渠道状态测试 =====================
            print("\n" + "="*60)
            print("模块 7: 渠道状态")
            print("="*60)

            response = await page.request.get(f"{BASE_URL}/api/v1/campaigns/channels", headers=api_headers)
            if response.ok:
                channels = await response.json()
                await log_test("渠道状态", "渠道列表 API", True,
                              f"可用渠道: {channels.get('available_channels', [])}")

                # 检查开发模式下短信功能是否启用
                sms_enabled = channels.get('sms_enabled', False)
                dev_mode = channels.get('dev_mode', False)
                await log_test("渠道状态", "开发模式权限", dev_mode and sms_enabled,
                              f"dev_mode={dev_mode}, sms_enabled={sms_enabled}")
            else:
                await log_test("渠道状态", "渠道列表 API", False)

            # ===================== 8. 预约排班测试 =====================
            print("\n" + "="*60)
            print("模块 8: 预约排班")
            print("="*60)

            await page.goto(f"{BASE_URL}/bookings")
            await page.wait_for_load_state("networkidle")
            await log_test("预约排班", "页面加载", True)

            response = await page.request.get(f"{BASE_URL}/api/v1/bookings/", headers=api_headers)
            if response.ok:
                bookings = await response.json()
                await log_test("预约排班", "预约列表 API", True, f"共 {len(bookings)} 条预约")
            else:
                await log_test("预约排班", "预约列表 API", False)

            # ===================== 9. 库存管理测试 =====================
            print("\n" + "="*60)
            print("模块 9: 库存管理")
            print("="*60)

            await page.goto(f"{BASE_URL}/inventory")
            await page.wait_for_load_state("networkidle")
            await log_test("库存管理", "页面加载", True)

            response = await page.request.get(f"{BASE_URL}/api/v1/inventory/", headers=api_headers)
            if response.ok:
                inventory = await response.json()
                await log_test("库存管理", "库存列表 API", True, f"共 {len(inventory)} 个库存项")
            else:
                await log_test("库存管理", "库存列表 API", False)

            # ===================== 10. 财务收银测试 =====================
            print("\n" + "="*60)
            print("模块 10: 财务收银")
            print("="*60)

            await page.goto(f"{BASE_URL}/billing")
            await page.wait_for_load_state("networkidle")
            await log_test("财务收银", "页面加载", True)

            response = await page.request.get(f"{BASE_URL}/api/v1/billing/", headers=api_headers)
            if response.ok:
                billing = await response.json()
                await log_test("财务收银", "交易列表 API", True, f"共 {len(billing)} 条交易")
            else:
                await log_test("财务收银", "交易列表 API", False)

            # ===================== 11. AI 分析测试 =====================
            print("\n" + "="*60)
            print("模块 11: AI 分析")
            print("="*60)

            await page.goto(f"{BASE_URL}/ai")
            await page.wait_for_load_state("networkidle")
            await log_test("AI 分析", "页面加载", True)

            # 检查 AI 分析列表
            # 检查 AI 分析列表 - 需要指定 client_id
            # 获取一个客户 ID 用于测试
            if yang_client and yang_client.get('client_id'):
                client_id = yang_client.get('client_id')
                response = await page.request.get(f"{BASE_URL}/api/v1/ai/analyses/{client_id}", headers=api_headers)
                if response.ok:
                    analyses = await response.json()
                    await log_test("AI 分析", "分析记录 API", True, f"共 {len(analyses)} 条记录")
                else:
                    await log_test("AI 分析", "分析记录 API", False, f"状态码: {response.status}")
            else:
                await log_test("AI 分析", "分析记录 API", False, "无客户 ID 可用")

            # ===================== 12. 短信发送测试（只测试杨T） =====================
            print("\n" + "="*60)
            print("模块 12: 短信发送测试（杨T）")
            print("="*60)

            # 查找杨T的客户信息
            response = await page.request.get(f"{BASE_URL}/api/v1/clients/", headers=api_headers)
            if response.ok:
                clients = await response.json()
                yang_client = None
                for c in clients:
                    name = c.get('name', '')
                    if '杨' in name and 'T' in name.upper():
                        yang_client = c
                        break

                if yang_client and yang_client.get('phone'):
                    phone = yang_client.get('phone')
                    # 发送测试短信
                    import urllib.request
                    import json as json_mod

                    # 获取 token
                    login_data = json_mod.dumps({"username": ADMIN_USER, "password": ADMIN_PASS}).encode()
                    login_req = urllib.request.Request(f"{BASE_URL}/api/v1/auth/login",
                                                       data=login_data,
                                                       headers={"Content-Type": "application/json"})
                    login_resp = urllib.request.urlopen(login_req)
                    token = json_mod.loads(login_resp.read().decode())['token']

                    # 发送短信
                    sms_data = json_mod.dumps({
                        "phone": phone,
                        "content": "【系统测试】这是一条测试短信，请忽略。"
                    }).encode()
                    sms_req = urllib.request.Request(f"{BASE_URL}/api/v1/config/sms/test",
                                                     data=sms_data,
                                                     method='POST',
                                                     headers={
                                                         "Authorization": f"Bearer {token}",
                                                         "Content-Type": "application/json"
                                                     })
                    try:
                        sms_resp = urllib.request.urlopen(sms_req, timeout=30)
                        sms_result = json_mod.loads(sms_resp.read().decode())
                        await log_test("短信发送", "发送测试短信", sms_result.get('success', False),
                                      sms_result.get('message', ''))
                    except Exception as e:
                        await log_test("短信发送", "发送测试短信", False, str(e))
                else:
                    await log_test("短信发送", "找到杨T手机号", False, "无手机号")
            else:
                await log_test("短信发送", "获取客户列表", False)

        except Exception as e:
            print(f"\n[ERROR] 测试执行异常: {e}")
            import traceback
            traceback.print_exc()

        finally:
            await browser.close()

    # 输出测试报告
    print("\n" + "="*60)
    print("测试报告")
    print("="*60)

    total = len(test_results)
    passed = sum(1 for r in test_results if r['passed'])
    failed = total - passed

    print(f"总计: {total} 项测试")
    print(f"通过: {passed} 项")
    print(f"失败: {failed} 项")
    print(f"通过率: {passed/total*100:.1f}%")

    if failed > 0:
        print("\n失败项:")
        for r in test_results:
            if not r['passed']:
                print(f"  - {r['module']} / {r['test']}: {r['message']}")

    return passed, failed

if __name__ == "__main__":
    passed, failed = asyncio.run(run_tests())
    sys.exit(0 if failed == 0 else 1)