"""
剧本调度引擎
双层触达体系：
  第一层：剧本触发（关键业务规则）- 时机固定、商家可控
  第二层：AI智能触发（日常智能判断）- AI分析客户状态，智能决策
核心调度流程：扫描剧本 → 计算触发客户 → AI 生成文案 → 审批 → 入队。
可由 APScheduler 定时调用，也可手动触发。
"""
import random
import logging
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from config import AppConfig
from ai.llm_client import LLMClient
from ai.content_generator import ContentGenerator
from db_models import Playbook, CampaignTask, Client, ClientLifecycle, ProfessionalAnalysis
from playbook.triggers import TriggerEvaluator
from playbook.approval import ApprovalManager
from playbook.lifecycle import LifecycleManager
from playbook.intelligent_engine import IntelligentReachEngine

logger = logging.getLogger(__name__)

# 场景映射：trigger_type → content_generator scene
TRIGGER_TO_SCENE = {
    "post_service": "post_service_followup",
    "solar_term": "seasonal_care",
    "weather_change": "weather_alert",
    "birthday": "birthday_greeting",
    "time_since_visit": "silent_client_wakeup",
    "lifecycle_change": None,  # 根据 target_filter 动态决定
    "holiday": "holiday_care",  # 节前预约提醒/不出游关怀
    "holiday_greeting": "holiday_greeting",  # 节日当天祝福
}


class PlaybookEngine:

    def __init__(self, config: AppConfig, llm: LLMClient):
        self.config = config
        self.llm = llm
        self.trigger_eval = TriggerEvaluator()
        self.approval = ApprovalManager()
        self.lifecycle = LifecycleManager()
        self.content_gen = ContentGenerator(config, llm)
        self.intelligent_engine = IntelligentReachEngine(config, llm)  # AI智能触达引擎

    def daily_scan(self, db: Session, enable_ai_reach: bool = True) -> dict:
        """
        每日剧本扫描主入口（双层触达体系）。
        1. 刷新生命周期状态
        2. 第一层：剧本触发（过滤业态配置）
        3. 第二层：AI智能触发（可选）
        返回摘要。
        """
        logger.info("=== Playbook daily scan started (dual-layer) ===")
        summary = {
            "lifecycle_updated": 0,
            "playbooks_scanned": 0,
            "playbook_tasks_created": 0,
            "ai_reach_analyzed": 0,
            "ai_reach_suggestions": 0,
            "ai_reach_tasks_created": 0,
            "errors": []
        }

        # 1. 刷新生命周期
        lc_result = self.lifecycle.daily_batch_update(db)
        summary["lifecycle_updated"] = lc_result["updated"]

        # 2. 第一层：剧本触发
        playbook_result = self._scan_playbooks(db)
        summary["playbooks_scanned"] = playbook_result["scanned"]
        summary["playbook_tasks_created"] = playbook_result["tasks_created"]
        if playbook_result["errors"]:
            summary["errors"].extend(playbook_result["errors"])

        # 3. 第二层：AI智能触发（根据业态配置决定是否启用）
        if enable_ai_reach and self._should_enable_ai_reach():
            ai_result = self._scan_ai_reach(db)
            summary["ai_reach_analyzed"] = ai_result["analyzed"]
            summary["ai_reach_suggestions"] = len(ai_result["suggestions"])
            ai_tasks = self._process_ai_suggestions(db, ai_result["suggestions"])
            summary["ai_reach_tasks_created"] = len(ai_tasks)
            if ai_result["errors"]:
                summary["errors"].extend(ai_result["errors"])

        logger.info(f"=== Playbook scan done: playbook={summary['playbook_tasks_created']}, ai={summary['ai_reach_tasks_created']} ===")
        return summary

    def _should_enable_ai_reach(self) -> bool:
        """根据业态配置判断是否启用AI智能触达"""
        pb_config = self.config.playbook_business_config
        return pb_config.get("ai_reach_enabled", True)

    def _scan_playbooks(self, db: Session) -> dict:
        """第一层：剧本触发扫描"""
        result = {"scanned": 0, "tasks_created": 0, "errors": []}

        # 加载所有启用剧本
        playbooks = db.query(Playbook).filter(Playbook.is_active == 1).all()
        result["scanned"] = len(playbooks)

        # 业态剧本配置
        pb_config = self.config.playbook_business_config
        enabled_presets = pb_config.get("enabled_presets", [])
        disabled_presets = pb_config.get("disabled_presets", [])

        # 逐剧本处理
        for pb in playbooks:
            # 业态过滤：检查剧本是否在禁用列表
            pb_name_lower = pb.name.lower()
            if any(disabled in pb_name_lower for disabled in disabled_presets):
                logger.info(f"Playbook '{pb.name}' skipped by business config (disabled)")
                continue

            try:
                count = self._process_playbook(db, pb)
                result["tasks_created"] += count
            except Exception as e:
                logger.error(f"Playbook {pb.name} error: {e}")
                result["errors"].append(f"{pb.name}: {str(e)}")

        return result

    def _scan_ai_reach(self, db: Session) -> dict:
        """第二层：AI智能触达扫描"""
        return self.intelligent_engine.scan_clients(db, max_clients=50)

    def _process_ai_suggestions(self, db: Session, suggestions: list) -> list:
        """处理AI触达建议，生成文案并创建任务"""
        tasks = []
        for suggestion in suggestions:
            if not suggestion.get("should_reach"):
                continue

            # 创建任务
            task = self.intelligent_engine.create_ai_task(db, suggestion)
            if not task:
                continue

            # 生成文案
            if self.llm.is_available:
                variables = suggestion.get("variables", {})
                content_type = suggestion.get("content_type", "general_care")
                # 映射到文案场景
                scene_map = {
                    "general_care": "seasonal_care",
                    "seasonal_care": "seasonal_care",
                    "service_recommend": "post_service_followup",
                    "card_reminder": "silent_client_wakeup",
                    "followup": "post_service_followup",
                    "wakeup": "silent_client_wakeup",
                }
                scene = scene_map.get(content_type, "seasonal_care")
                result = self.content_gen.generate(db, scene, variables)
                if result["success"]:
                    task.generated_content = result["content"]
                else:
                    task.generated_content = f"[AI文案生成失败: {result['error']}]"
                    logger.warning(f"AI content gen failed: {result['error']}")

            db.commit()
            tasks.append(task)

        # 审批分流
        if tasks:
            self.approval.process_batch(db, tasks, None)  # AI触达没有playbook

        return tasks

    def _process_playbook(self, db: Session, pb: Playbook) -> int:
        """处理单个剧本，返回创建的任务数。"""
        # 计算触发客户
        client_ids = self.trigger_eval.evaluate(db, pb)
        if not client_ids:
            return 0

        logger.info(f"Playbook '{pb.name}': {len(client_ids)} clients triggered")

        # 确定文案场景
        scene = self._determine_scene(pb)
        tasks = []

        for cid in client_ids:
            # 获取客户信息
            client = db.query(Client).filter(Client.client_id == cid).first()
            if not client:
                continue

            # 构建文案变量
            variables = self._build_variables(db, client, pb)

            # 生成文案（如果 LLM 可用）
            if self.llm.is_available and scene:
                result = self.content_gen.generate(db, scene, variables)
                if result["success"]:
                    content = result["content"]
                else:
                    content = f"[文案生成失败: {result['error']}]"
                    logger.warning(f"Content gen failed for {cid}: {result['error']}")
            else:
                # LLM 不可用时使用 content_template 占位
                content = pb.content_template or f"[{pb.name}] 待生成文案"

            # 创建任务
            task = CampaignTask(
                playbook_id=pb.id,
                client_id=cid,
                generated_content=content,
                send_channel=pb.send_channel or "auto",
            )
            # 分配发送时间（在窗口内随机）
            task.scheduled_at = self._random_send_time(pb)
            db.add(task)
            tasks.append(task)

        db.commit()

        # 审批分流
        if tasks:
            self.approval.process_batch(db, tasks, pb)

        return len(tasks)

    def _determine_scene(self, pb: Playbook) -> str:
        """根据剧本类型决定文案场景。"""
        scene = TRIGGER_TO_SCENE.get(pb.trigger_type)
        if scene is None and pb.trigger_type == "lifecycle_change":
            target = (pb.trigger_config or {}).get("on_enter_status", "")
            if target == "silent":
                return "silent_client_wakeup"
            elif target == "churn_risk":
                return "churn_rescue"
            return "silent_client_wakeup"
        # 新客欢迎：post_service + lifecycle=new
        if pb.trigger_type == "post_service":
            target_lc = (pb.target_filter or {}).get("lifecycle_status", "")
            if target_lc == "new":
                return "new_client_welcome"
        return scene or "seasonal_care"

    def _build_variables(self, db: Session, client: Client, pb: Playbook) -> dict:
        """构建文案生成的变量字典。"""
        # 最新分析
        analysis = db.query(ProfessionalAnalysis).filter(
            ProfessionalAnalysis.client_id == client.client_id
        ).order_by(ProfessionalAnalysis.assessed_at.desc()).first()

        # lifecycle
        lc = db.query(ClientLifecycle).filter(
            ClientLifecycle.client_id == client.client_id
        ).first()

        analysis_type = client.primary_analysis_type or "未分析"
        key_symptoms = ""
        if analysis and analysis.ai_recommendations:
            key_symptoms = ", ".join(analysis.ai_recommendations.get("key_symptoms", []))

        days_info = ""
        if lc and lc.last_visit_at:
            days_info = f"{(datetime.now() - lc.last_visit_at).days}天"

        # 获取当前中医养生节点信息
        from playbook.solar_terms import SolarTermCalendar
        tcm_context = SolarTermCalendar.get_current_tcm_context()

        # 获取节假日信息
        from playbook.holidays import HolidayCalendar
        holiday_context = HolidayCalendar.get_holiday_context()

        # 获取服务项目推荐
        from services.service_recommender import ServiceRecommender
        recommendations = ServiceRecommender.get_recommendations(
            db=db,
            client_id=client.client_id,
            analysis_type=analysis_type,
            current_season=tcm_context["season"],
            current_term=tcm_context["current_term"],
            tcm_periods=tcm_context["active_periods"],
            wellness_focus=tcm_context.get("wellness_advice", ""),
            limit=2,
        )

        # 格式化推荐服务信息
        service_recommendations = []
        for rec in recommendations:
            svc = rec["service"]
            service_recommendations.append({
                "name": svc.name,
                "effects": svc.wellness_effects or [],
                "reason": rec["match_reasons"],
            })

        # 基础变量
        variables = {
            "client_name": client.name or "亲",
            "analysis_type": analysis_type,
            "key_symptoms": key_symptoms or "暂无",
            "days_info": days_info or "未知",
            "service_info": "",
            "weather_info": "近期天气变化较大",
            # 中医养生节点信息
            "season": tcm_context["season_display"],
            "tcm_period": ",".join(tcm_context["active_periods"]) if tcm_context["active_periods"] else tcm_context["season"],
            "wellness_focus": tcm_context.get("wellness_advice", "顺应时节、调养身心"),
            # 五运六气信息
            "wuyun_sixqi": tcm_context.get("wuyun_sixqi", ""),
            # 服务项目推荐
            "recommended_services": service_recommendations,
        }

        # 节假日专属变量（trigger_type 为 holiday 或 holiday_greeting 时）
        if pb.trigger_type in ["holiday", "holiday_greeting"]:
            nearest_holiday = holiday_context.get("nearest_holiday") or {}
            variables["holiday_name"] = nearest_holiday.get("name", "节日")
            variables["days_until_holiday"] = nearest_holiday.get("days_until", 0)
            variables["holiday_days"] = nearest_holiday.get("holiday_days", 3)
            variables["greeting_type"] = nearest_holiday.get("greeting_type", "节日快乐")

            # 关怀类型（预约提醒 vs 不出游关怀）
            care_type = (pb.trigger_config or {}).get("care_type", "appointment_reminder")
            variables["holiday_care_type"] = care_type
            if care_type == "appointment_reminder":
                variables["holiday_care_type"] = "预约提醒"
            elif care_type == "non_travel_care":
                variables["holiday_care_type"] = "不出游关怀"

            # 放假安排（可从配置获取）
            variables["holiday_schedule"] = f"{nearest_holiday.get('name', '')}期间正常营业"

        return variables

    def _random_send_time(self, pb: Playbook) -> datetime:
        """在发送窗口内随机分配一个时间。"""
        today = datetime.now().date()
        try:
            start_parts = (pb.send_window_start or "09:00").split(":")
            end_parts = (pb.send_window_end or "18:00").split(":")
            start_min = int(start_parts[0]) * 60 + int(start_parts[1])
            end_min = int(end_parts[0]) * 60 + int(end_parts[1])
        except (ValueError, IndexError):
            start_min, end_min = 540, 1080  # 09:00 - 18:00

        rand_min = random.randint(start_min, max(start_min, end_min))
        return datetime.combine(today, datetime.min.time()) + timedelta(minutes=rand_min)

    def preview_playbook(self, db: Session, playbook_id: str) -> dict:
        """预览剧本：模拟执行，返回会触发的客户数和示例文案（不实际创建任务）。"""
        pb = db.query(Playbook).filter(Playbook.id == playbook_id).first()
        if not pb:
            return {"error": "剧本不存在"}

        client_ids = self.trigger_eval.evaluate(db, pb)
        sample_content = ""

        if client_ids and self.llm.is_available:
            # 取第一个客户生成示例文案
            client = db.query(Client).filter(Client.client_id == client_ids[0]).first()
            if client:
                scene = self._determine_scene(pb)
                variables = self._build_variables(db, client, pb)
                result = self.content_gen.generate(db, scene, variables)
                if result["success"]:
                    sample_content = result["content"]

        return {
            "playbook_name": pb.name,
            "triggered_count": len(client_ids),
            "triggered_client_ids": client_ids[:10],  # 最多返回10个
            "sample_content": sample_content,
        }

    def preview_ai_reach(self, db: Session, client_id: str) -> dict:
        """预览单个客户的AI智能触达建议（不实际创建任务）。"""
        suggestion = self.intelligent_engine.analyze_client(db, client_id)
        if not suggestion:
            return {"error": "客户不存在"}

        # 生成示例文案
        sample_content = ""
        if suggestion.get("should_reach") and self.llm.is_available:
            variables = suggestion.get("variables", {})
            content_type = suggestion.get("content_type", "general_care")
            scene_map = {
                "general_care": "seasonal_care",
                "seasonal_care": "seasonal_care",
                "service_recommend": "post_service_followup",
                "card_reminder": "silent_client_wakeup",
                "followup": "post_service_followup",
                "wakeup": "silent_client_wakeup",
            }
            scene = scene_map.get(content_type, "seasonal_care")
            result = self.content_gen.generate(db, scene, variables)
            if result["success"]:
                sample_content = result["content"]

        return {
            "client_id": client_id,
            "client_name": suggestion.get("client_name", ""),
            "should_reach": suggestion.get("should_reach", False),
            "urgency": suggestion.get("urgency", "low"),
            "content_type": suggestion.get("content_type", ""),
            "reason": suggestion.get("reason", ""),
            "recommended_services": suggestion.get("recommended_services", []),
            "sample_content": sample_content,
        }
