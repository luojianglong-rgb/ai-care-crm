"""
短信 API 渠道驱动
支持两种模式：
  - direct: 商户自有阿里云/腾讯云短信账号，直接调用云端 API
  - proxy:  经开发者代理网关转发（商户充值即用）

当前实现使用 HTTP 通用接口，兼容阿里云短信 API 签名。
若未安装阿里云 SDK，退化为 HTTP 请求方式。
"""
import json
import logging
import uuid
from datetime import datetime
from typing import Optional

from channels.base import BaseChannelDriver, SendResult

logger = logging.getLogger(__name__)


class SmsApiDriver(BaseChannelDriver):
    """短信 API 渠道驱动"""

    channel_name = "sms_api"

    def __init__(self, config_raw: dict):
        """
        Args:
            config_raw: config.yaml 中 channels.sms_api 节的原始字典
        """
        self.enabled = config_raw.get("enabled", False)
        self.mode = config_raw.get("mode", "direct")  # direct / proxy
        self.provider = config_raw.get("provider", "aliyun")
        self.sign_name = config_raw.get("sign_name", "")

        # direct 模式
        self.api_key = config_raw.get("api_key", "") or ""
        self.api_secret = config_raw.get("api_secret", "") or ""

        # proxy 模式
        proxy_cfg = config_raw.get("proxy", {})
        self.proxy_endpoint = proxy_cfg.get("endpoint", "") or ""
        self.proxy_token = proxy_cfg.get("merchant_token", "") or ""

        # 发送计数
        self._sent_today = 0
        self._last_reset_date = datetime.now().date()

    def is_available(self) -> bool:
        if not self.enabled:
            return False
        if self.mode == "direct":
            return bool(self.api_key and self.api_secret)
        elif self.mode == "proxy":
            return bool(self.proxy_endpoint and self.proxy_token)
        return False

    def send(self, recipient: str, content: str, **kwargs) -> SendResult:
        """发送短信"""
        if not self.is_available():
            return SendResult(success=False, channel=self.channel_name,
                              error="短信 API 未配置或不可用")

        if not recipient:
            return SendResult(success=False, channel=self.channel_name,
                              error="缺少收件人手机号")

        # 每日计数重置
        today = datetime.now().date()
        if today != self._last_reset_date:
            self._sent_today = 0
            self._last_reset_date = today

        if self.mode == "direct":
            return self._send_direct(recipient, content)
        elif self.mode == "proxy":
            return self._send_proxy(recipient, content)
        else:
            return SendResult(success=False, channel=self.channel_name,
                              error=f"未知模式: {self.mode}")

    def _send_direct(self, phone: str, content: str) -> SendResult:
        """直连模式 — 调用阿里云/腾讯云短信 API"""
        if self.provider == "aliyun":
            return self._send_aliyun(phone, content)
        elif self.provider == "tencent":
            return self._send_tencent(phone, content)
        else:
            return SendResult(success=False, channel=self.channel_name,
                              error=f"不支持的短信提供商: {self.provider}")

    def _send_aliyun(self, phone: str, content: str) -> SendResult:
        """阿里云短信 API"""
        try:
            from alibabacloud_dysmsapi20170525.client import Client as DysmsapiClient
            from alibabacloud_dysmsapi20170525 import models as sms_models
            from alibabacloud_tea_openapi import models as open_models

            config = open_models.Config(
                access_key_id=self.api_key,
                access_key_secret=self.api_secret,
                endpoint="dysmsapi.aliyuncs.com",
            )
            client = DysmsapiClient(config)
            request = sms_models.SendSmsRequest(
                phone_numbers=phone,
                sign_name=self.sign_name,
                template_code="SMS_DEFAULT",  # 商户需在阿里云配置模板
                template_param=json.dumps({"content": content[:20]}),
            )
            response = client.send_sms(request)
            if response.body.code == "OK":
                self._sent_today += 1
                return SendResult(success=True, channel=self.channel_name,
                                  external_id=response.body.biz_id)
            else:
                return SendResult(success=False, channel=self.channel_name,
                                  error=f"阿里云: {response.body.message}")
        except ImportError:
            return self._send_aliyun_http(phone, content)
        except Exception as e:
            logger.error(f"[SMS-Aliyun] 发送失败: {e}")
            return SendResult(success=False, channel=self.channel_name, error=str(e))

    def _send_aliyun_http(self, phone: str, content: str) -> SendResult:
        """阿里云 HTTP 降级方案（无 SDK 时）"""
        try:
            import urllib.request
            import urllib.parse
            import hashlib
            import hmac as hmac_mod
            import base64
            import time as time_mod

            # 签名参数
            params = {
                "AccessKeyId": self.api_key,
                "Action": "SendSms",
                "Format": "JSON",
                "PhoneNumbers": phone,
                "SignName": self.sign_name,
                "SignatureMethod": "HMAC-SHA1",
                "SignatureNonce": str(uuid.uuid4()),
                "SignatureVersion": "1.0",
                "TemplateCode": "SMS_DEFAULT",
                "TemplateParam": json.dumps({"content": content[:20]}),
                "Timestamp": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
                "Version": "2017-05-25",
            }
            sorted_params = sorted(params.items())
            query = urllib.parse.urlencode(sorted_params, quote_via=urllib.parse.quote)
            string_to_sign = f"GET&%2F&{urllib.parse.quote(query, safe='')}"
            signature = base64.b64encode(
                hmac_mod.new((self.api_secret + "&").encode(), string_to_sign.encode(), hashlib.sha1).digest()
            ).decode()
            params["Signature"] = signature

            url = f"https://dysmsapi.aliyuncs.com/?{urllib.parse.urlencode(params)}"
            req = urllib.request.Request(url, method="GET")
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode())
            if data.get("Code") == "OK":
                self._sent_today += 1
                return SendResult(success=True, channel=self.channel_name,
                                  external_id=data.get("BizId", ""))
            else:
                return SendResult(success=False, channel=self.channel_name,
                                  error=f"阿里云: {data.get('Message', '未知错误')}")
        except Exception as e:
            logger.error(f"[SMS-Aliyun-HTTP] 发送失败: {e}")
            return SendResult(success=False, channel=self.channel_name, error=str(e))

    def _send_tencent(self, phone: str, content: str) -> SendResult:
        """腾讯云短信 — 预留接口"""
        return SendResult(success=False, channel=self.channel_name,
                          error="腾讯云短信暂未实现，请使用阿里云")

    def _send_proxy(self, phone: str, content: str) -> SendResult:
        """代理模式 — 经开发者网关转发"""
        try:
            import urllib.request

            payload = json.dumps({
                "phone": phone,
                "content": content,
                "sign_name": self.sign_name,
            }).encode()
            req = urllib.request.Request(
                f"{self.proxy_endpoint}/api/v1/sms/send",
                data=payload,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.proxy_token}",
                },
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode())
            if data.get("success"):
                self._sent_today += 1
                return SendResult(success=True, channel=self.channel_name,
                                  external_id=data.get("id", ""))
            else:
                return SendResult(success=False, channel=self.channel_name,
                                  error=data.get("error", "代理发送失败"))
        except Exception as e:
            logger.error(f"[SMS-Proxy] 发送失败: {e}")
            return SendResult(success=False, channel=self.channel_name, error=str(e))
