#!/usr/bin/env python3
"""
AI-Care CRM 激活码生成工具（开发者专用）

用法：
  python tools/generate_license.py --machine-id <ID> --tier pro --expire 2027-03-24
  python tools/generate_license.py --machine-id auto --tier business --days 365
  python tools/generate_license.py --machine-id auto --tier pro --days 60 --trial

参数：
  --machine-id   目标机器的特征码（从系统设置页获取），或 'auto' 表示当前机器
  --tier         套餐等级: pro / business
  --expire       到期日期 (YYYY-MM-DD)
  --days         有效天数（与 --expire 二选一）
  --trial        标记为试用版（仅影响 UI 显示，功能/额度与正式版相同）

试用版机制：
  - 销售签发 --trial --days 60 → 客户体验 2 个月完整功能
  - 到期后 7 天宽限期内系统只读（数据可见，写入被拦截）
  - 宽限期结束后自动回退基础版（10客户/5次AI）

此脚本不应随软件分发，仅供开发者使用。
"""
import argparse
import sys
import os
from datetime import date, timedelta

# 将 src/ 加入 path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from license_manager import generate_license_key, _get_machine_id, LicenseManager


def main():
    parser = argparse.ArgumentParser(description="AI-Care CRM 激活码生成工具")
    parser.add_argument("--machine-id", required=True, help="目标机器特征码，或 'auto' 用当前机器")
    parser.add_argument("--tier", required=True, choices=["pro", "business"], help="套餐等级")
    parser.add_argument("--expire", help="到期日期 YYYY-MM-DD")
    parser.add_argument("--days", type=int, help="有效天数（与 --expire 二选一，可为负数测试过期场景）")
    parser.add_argument("--trial", action="store_true",
                        help="标记为试用版激活码（仅影响 UI 显示，功能与正式版相同）")

    args = parser.parse_args()

    # 确定机器 ID
    machine_id = args.machine_id
    if machine_id == "auto":
        machine_id = _get_machine_id()
        print(f"当前机器特征码: {machine_id}")

    # 确定到期日期
    if args.expire:
        expire_date = args.expire
    elif args.days is not None:
        expire_date = (date.today() + timedelta(days=args.days)).strftime("%Y-%m-%d")
    else:
        print("错误: 请指定 --expire 或 --days")
        sys.exit(1)

    # 生成激活码
    key = generate_license_key(machine_id, args.tier, expire_date, is_trial=args.trial)

    type_label = "试用版" if args.trial else "正式版"
    print(f"\n{'='*60}")
    print(f"  套餐: {args.tier.upper()} ({type_label})")
    print(f"  机器: {machine_id}")
    print(f"  到期: {expire_date}")
    print(f"{'='*60}")
    print(f"\n  激活码:\n  {key}\n")

    # 验证激活码
    lm = LicenseManager()
    lm.machine_id = machine_id  # 临时设为目标机器
    info = lm.verify(key)
    print(f"  验证结果: {'通过' if info.valid else '失败'} - {info.message}")
    print(f"  状态: {info.status}")
    print(f"  剩余天数: {info.days_remaining}")
    if info.in_grace_period:
        print(f"  宽限期剩余: {info.grace_days_remaining} 天（只读模式）")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
