"""
ML307A 短信猫测试脚本
使用方法：
  1. 插入 ML307A 设备到 USB
  2. 插入 SIM 卡（确保已开通短信功能）
  3. 运行：python test_ml307a.py
"""
import sys
sys.path.insert(0, 'src')

from channels.drivers.ml307a import ML307ADriver
import serial.tools.list_ports

print("=" * 50)
print("ML307A 4G 短信猫测试工具")
print("=" * 50)

# 1. 列出所有串口设备
print("\n【1. 扫描串口设备】")
ports = serial.tools.list_ports.comports()
if not ports:
    print("未找到任何串口设备")
else:
    print(f"找到 {len(ports)} 个串口设备:")
    for i, p in enumerate(ports, 1):
        print(f"  {i}. {p.device}")
        print(f"     描述：{p.description}")
        print(f"     HWID: {p.hwid}")
        if p.vid:
            print(f"     VID:PID = {p.vid:04X}:{p.pid:04X}")

# 2. 创建驱动实例
print("\n【2. 初始化驱动】")
driver = ML307ADriver({
    'enabled': True,
    'port': None,  # 自动扫描
    'baudrate': 115200,
    'timeout': 5,
})

# 3. 检查设备
print("\n【3. 检测设备状态】")
available = driver.is_available()
print(f"设备可用：{'是' if available else '否'}")

if available:
    print("\n【4. 获取详细状态】")
    status = driver.get_status()
    print(f"连接状态：{'已连接' if status.get('connected') else '未连接'}")
    print(f"串口号：{status.get('port', 'N/A')}")
    print(f"信号强度 (CSQ): {status.get('signal_strength', 'N/A')}")
    print(f"SIM 卡状态：{status.get('sim_status', 'N/A')}")
    print(f"运营商：{status.get('operator', 'N/A')}")
else:
    print("\n未检测到 ML307A 设备，请检查:")
    print("  1. USB 线是否连接好")
    print("  2. 是否安装了串口驱动（CH340/CP2102）")
    print("  3. SIM 卡是否插好")

# 4. 发送测试短信（可选）
print("\n【5. 测试发送短信】")
phone = input("请输入测试手机号（直接跳过不发送）: ").strip()
if phone:
    content = "【CRM 系统】ML307A 短信猫测试消息，设备工作正常！"
    print(f"正在发送短信到：{phone}")
    print(f"内容：{content}")

    result = driver.send(
        recipient=phone,
        content=content,
        client_name="测试用户"
    )

    print(f"\n发送结果：{'成功' if result.success else '失败'}")
    if not result.success:
        print(f"错误：{result.error}")
    else:
        print(f"外部 ID: {result.external_id}")

print("\n" + "=" * 50)
print("测试完成")
print("=" * 50)
