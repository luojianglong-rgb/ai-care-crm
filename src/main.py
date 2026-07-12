from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi import HTTPException
from pydantic import BaseModel
from contextlib import asynccontextmanager
import uvicorn
import logging
import os
import sys
import jwt as pyjwt
from logging.handlers import TimedRotatingFileHandler
import shutil

# PyInstaller 打包后的资源路径处理
def get_resource_path(relative_path):
    """获取资源文件的绝对路径（支持 PyInstaller 打包环境）"""
    if hasattr(sys, '_MEIPASS'):
        # PyInstaller 打包环境：使用临时解压目录
        return os.path.join(sys._MEIPASS, relative_path)
    # 开发环境：使用当前文件所在目录
    return os.path.join(os.path.dirname(__file__), relative_path)

# 创建 logs 目录（支持 PyInstaller 打包环境）
if hasattr(sys, '_MEIPASS'):
    # PyInstaller 打包环境：日志在 EXE 同级的 logs 目录
    LOG_DIR = os.path.join(os.path.dirname(sys.executable), "logs")
else:
    # 开发环境：日志在项目根目录的 logs 目录
    LOG_DIR = os.path.join(os.path.dirname(__file__), "..", "logs")
os.makedirs(LOG_DIR, exist_ok=True)

# 配置日志：同时输出到控制台和文件
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        # 控制台输出
        logging.StreamHandler(),
        # 文件输出：按天滚动，保留 60 天
        TimedRotatingFileHandler(
            filename=os.path.join(LOG_DIR, "app.log"),
            when="D",
            interval=1,
            backupCount=60,
            encoding="utf-8"
        )
    ]
)
logger = logging.getLogger(__name__)

from api import clients, bookings, inventory, billing, services, wap
from api import config_api, ai_api, reply_api, dashboard_api, auth_api
from api.playbook_api import playbook_router, campaign_router
from api.services_api import router as services_recommendation_router
from database import engine, get_db
import db_models
from config import get_config, reload_config
from license_manager import get_license_manager

# ── 加载系统配置 + 验证激活码 ──────────────────────────────────────
# 首次启动时检查配置文件，不存在则从模板复制
# PyInstaller 打包后，配置文件应生成在 EXE 同级的 config/ 文件夹
def init_config_file():
    """初始化配置文件（首次启动时）"""
    if hasattr(sys, '_MEIPASS'):
        # PyInstaller 打包环境：配置文件在 EXE 同级的 config 目录
        exe_dir = os.path.dirname(sys.executable)
        config_dir = os.path.join(exe_dir, 'config')
    else:
        # 开发环境：配置文件在 src 目录
        config_dir = os.path.dirname(__file__)

    # 确保目录存在
    os.makedirs(config_dir, exist_ok=True)

    config_file = os.path.join(config_dir, "config.yaml")
    config_template = os.path.join(config_dir, "config.yaml.template")

    if not os.path.exists(config_file) and os.path.exists(config_template):
        shutil.copy2(config_template, config_file)
        logger.info("配置文件已从模板生成：config.yaml")
        logger.info("请编辑 config.yaml 填写 API Key 等配置后重启系统")

    return config_file

init_config_file()

app_config = get_config()
lm = get_license_manager()
license_info = lm.verify(app_config.license.key)
app_config.current_tier = lm.get_current_tier(app_config.license.key)
app_config.read_only_mode = license_info.read_only_mode
app_config.license_status = license_info.status
app_config.is_trial = license_info.is_trial
app_config.grace_days_remaining = license_info.grace_days_remaining
app_config.days_remaining = license_info.days_remaining
logger.info(f"系统配置加载完成 [门店={app_config.store.name}, "
            f"业态={app_config.store.business_type}, 套餐={app_config.current_tier}, "
            f"状态={license_info.status}, 剩余={license_info.days_remaining}天, "
            f"只读={app_config.read_only_mode}]")

# 初始化数据库（含版本检查和迁移）
from database import init_db
init_db()

# 初始化默认耗材分类数据
def init_default_categories():
    """初始化默认耗材分类"""
    from db_models import InventoryCategory
    from sqlalchemy.orm import Session

    db = Session(bind=engine)
    try:
        default_categories = [
            {"name": "日常耗材", "description": "日常基础耗材，如棉签、纱布等"},
            {"name": "精油/原液", "description": "各类按摩精油、护肤原液"},
            {"name": "院线售卖产品", "description": "面向客户销售的产品"},
            {"name": "仪器设备配件", "description": "美容仪器设备的配件和耗材"}
        ]
        for cat in default_categories:
            existing = db.query(InventoryCategory).filter(InventoryCategory.name == cat["name"]).first()
            if not existing:
                db_item = InventoryCategory(**cat, is_active=1)
                db.add(db_item)
        db.commit()
    except Exception as e:
        print(f"初始化耗材分类失败：{e}")
        db.rollback()
    finally:
        db.close()

init_default_categories()

# 初始化预设剧本
def init_preset_playbooks_on_startup():
    from playbook.seed_data import init_preset_playbooks
    from sqlalchemy.orm import Session as _Session
    db = _Session(bind=engine)
    try:
        count = init_preset_playbooks(db)
        if count:
            logger.info(f"Initialized {count} preset playbooks")
    except Exception as e:
        logger.error(f"Failed to init playbooks: {e}")
        db.rollback()
    finally:
        db.close()

init_preset_playbooks_on_startup()

# 初始化默认管理员
def init_default_admin():
    from db_models import AdminUser
    from sqlalchemy.orm import Session as _Session
    import bcrypt
    db = _Session(bind=engine)
    try:
        admin = db.query(AdminUser).filter(AdminUser.username == "admin").first()
        if admin:
            # 重置密码为 admin
            hashed = bcrypt.hashpw("admin".encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
            admin.password_hash = hashed
            db.commit()
            logger.info("管理员密码已重置 (admin / admin)")
        else:
            hashed = bcrypt.hashpw("admin".encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
            admin = AdminUser(username="admin", password_hash=hashed, display_name="系统管理员")
            db.add(admin)
            db.commit()
            logger.info("默认管理员已创建 (admin / admin)")
    except Exception as e:
        logger.error(f"初始化管理员失败: {e}")
        db.rollback()
    finally:
        db.close()

init_default_admin()

# ── Lifespan 事件处理（替代废弃的 on_event）──────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("APScheduler 后台调度器已启动")
    yield
    # Shutdown
    pass

app = FastAPI(
    title="AI-Care CRM API",
    description=f"智能个人护理行业客户管理系统 - {app_config.store.name}",
    version="2.0.0",
    lifespan=lifespan
)

# 配置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# JWT 鉴权中间件 — 保护管理台 API
# 免鉴权白名单：登录接口、WAP 端接口、根路径、ping、静态资源
AUTH_WHITELIST_PREFIXES = ("/api/v1/auth/login", "/api/v1/wap/", "/docs", "/openapi.json", "/redoc")

@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    path = request.url.path
    # OPTIONS 请求（CORS 预检）直接放行，必须最先检查
    if request.method == "OPTIONS":
        return await call_next(request)
    # 根路径 / ping 放行
    if path in ("/", "/api/v1/ping"):
        return await call_next(request)
    # 白名单前缀放行
    for prefix in AUTH_WHITELIST_PREFIXES:
        if path.startswith(prefix):
            return await call_next(request)
    # 非 /api/v1 路径放行（前端静态资源等）
    if not path.startswith("/api/v1/"):
        return await call_next(request)
    # 验证 JWT
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return JSONResponse(status_code=401, content={"detail": "未登录"})
    token = auth_header[7:]
    try:
        pyjwt.decode(token, auth_api.JWT_SECRET, algorithms=[auth_api.JWT_ALGORITHM])
    except pyjwt.ExpiredSignatureError:
        return JSONResponse(status_code=401, content={"detail": "登录已过期"})
    except pyjwt.InvalidTokenError:
        return JSONResponse(status_code=401, content={"detail": "无效令牌"})
    return await call_next(request)

# ── 只读模式中间件 ──────────────────────────────────────────────────
# 宽限期（grace_period）内，所有写操作被拦截，仅保留读取和激活功能
READONLY_BYPASS_PREFIXES = (
    "/api/v1/auth/login",       # 登录
    "/api/v1/auth/me",          # 获取当前用户信息（GET）
    "/api/v1/config/activate",  # 激活码激活（必须可写！）
    "/api/v1/config/info",      # 系统信息（GET）
    "/api/v1/config/machine-id",# 机器码（GET）
    "/api/v1/config/quota",     # 配额查询（GET）
    "/api/v1/ping",             # 健康检查
)
WRITE_METHODS = {"POST", "PUT", "DELETE", "PATCH"}


@app.middleware("http")
async def readonly_middleware(request: Request, call_next):
    """宽限期只读拦截：dev_mode 绕过，否则拦截写操作"""
    cfg = get_config()
    # 开发模式或非只读状态直接放行
    if cfg.server.dev_mode or not cfg.read_only_mode:
        return await call_next(request)
    # 读请求放行
    if request.method not in WRITE_METHODS:
        return await call_next(request)
    # 白名单路径放行（激活、登录等）
    path = request.url.path
    for prefix in READONLY_BYPASS_PREFIXES:
        if path.startswith(prefix):
            return await call_next(request)
    # 拦截写操作
    return JSONResponse(
        status_code=403,
        content={
            "detail": "试用已到期，请联系销售获取正式版激活码",
            "error_code": "READ_ONLY_MODE",
            "grace_days_remaining": cfg.grace_days_remaining,
        },
    )

# 挂载路由模块 - 必须在 StaticFiles 之前注册，这样 API 路由优先
app.include_router(auth_api.router, prefix="/api/v1/auth", tags=["Auth (认证)"])
app.include_router(clients.router, prefix="/api/v1/clients", tags=["Clients (客户档案)"])
app.include_router(bookings.router, prefix="/api/v1/bookings", tags=["Bookings (预约排班)"])
app.include_router(inventory.router, prefix="/api/v1/inventory", tags=["Inventory (库存耗材)"])
app.include_router(billing.router, prefix="/api/v1/billing", tags=["Billing (财务收银)"])
app.include_router(services.router, prefix="/api/v1/services", tags=["Services (服务项目)"])
app.include_router(services_recommendation_router, prefix="/api/v1/service-recs", tags=["Service Recommendations (服务推荐)"])
app.include_router(wap.router, prefix="/api/v1/wap", tags=["WAP (手机技师端)"])
app.include_router(config_api.router, prefix="/api/v1/config", tags=["Config (系统配置)"])
app.include_router(ai_api.router, prefix="/api/v1/ai", tags=["AI (智能分析与方案)"])
app.include_router(playbook_router, prefix="/api/v1/playbooks", tags=["Playbooks (运营剧本)"])
app.include_router(campaign_router, prefix="/api/v1/campaigns", tags=["Campaigns (营销任务)"])
app.include_router(reply_api.router, prefix="/api/v1/replies", tags=["Replies (客户回复)"])
app.include_router(dashboard_api.router, prefix="/api/v1/dashboard", tags=["Dashboard (驾驶舱)"])

# 挂载前端静态文件（生产环境）
# 使用 get_resource_path 支持 PyInstaller 打包环境
# 注意：必须在 API 路由之后挂载，且使用单独的路径前缀避免冲突
FRONTEND_DIST_PATH = get_resource_path("frontend/dist")
if os.path.exists(FRONTEND_DIST_PATH):
    logger.info(f"前端静态文件已挂载：{FRONTEND_DIST_PATH}")
    # 挂载到 /static 路径，避免与 API 路由冲突
    app.mount("/static", StaticFiles(directory=FRONTEND_DIST_PATH, html=True), name="static")
else:
    logger.warning(f"未找到前端静态文件，开发环境请使用 npm run dev 启动前端：{FRONTEND_DIST_PATH}")

class HealthCheckResponse(BaseModel):
    status: str
    message: str

@app.get("/", response_model=HealthCheckResponse, tags=["System"])
def read_root():
    # 如果前端静态文件存在，返回前端页面
    if os.path.exists(FRONTEND_DIST_PATH) and os.path.exists(os.path.join(FRONTEND_DIST_PATH, "index.html")):
        return FileResponse(os.path.join(FRONTEND_DIST_PATH, "index.html"))

    # 前端未构建时返回健康检查信息
    return HealthCheckResponse(
        status="running",
        message=f"AI-Care CRM 后端已启动 [套餐: {app_config.current_tier}]，前端未构建请运行 npm run build"
    )

@app.get("/api/v1/ping", tags=["System"])
def ping():
    return {"ping": "pong"}

# 前端 SPA 通配符路由 - 处理刷新页面等直接访问 URL 的情况
@app.get("/{full_path:path}")
def serve_spa(full_path: str):
    """Serve SPA frontend, fallback to index.html for unknown routes"""
    # API 路径不处理
    if full_path.startswith("api/") or full_path.startswith("docs") or full_path.startswith("openapi.json") or full_path.startswith("redoc"):
        raise HTTPException(status_code=404, detail="Not found")
    # 尝试返回静态文件，不存在则返回 index.html
    if os.path.exists(FRONTEND_DIST_PATH):
        file_path = os.path.join(FRONTEND_DIST_PATH, full_path)
        if os.path.isfile(file_path):
            return FileResponse(file_path)
        # 返回 index.html 让 SPA 前端处理路由
        return FileResponse(os.path.join(FRONTEND_DIST_PATH, "index.html"))
    raise HTTPException(status_code=404, detail="Frontend not available")

# ── APScheduler 定时任务 ──────────────────────────────────────────
# 可选依赖，未安装时仅定时任务不可用，不影响核心功能
try:
    from apscheduler.schedulers.background import BackgroundScheduler
    scheduler = BackgroundScheduler()
    APSCHEDULER_AVAILABLE = True
except ImportError:
    scheduler = None
    APSCHEDULER_AVAILABLE = False
    logger.warning("APScheduler 未安装，定时任务将不可用（不影响核心 CRM 功能）")

def scheduled_daily_scan():
    """每日剧本扫描：刷新生命周期 + 生成营销任务"""
    from sqlalchemy.orm import Session as _Session
    from ai.llm_client import get_llm_client
    from playbook.engine import PlaybookEngine
    db = _Session(bind=engine)
    try:
        cfg = get_config()
        llm = get_llm_client()
        eng = PlaybookEngine(cfg, llm)
        result = eng.daily_scan(db)
        logger.info(f"[定时] 剧本扫描完成: lifecycle={result.get('lifecycle_updated',0)}, tasks={result.get('tasks_created',0)}")
    except Exception as e:
        logger.error(f"[定时] 剧本扫描失败: {e}")
        db.rollback()
    finally:
        db.close()

# 读取配置中的扫描时间
_scan_hour = 6
try:
    _scan_hour = get_config().raw.get("playbook", {}).get("scan_hour", 6)
except Exception:
    pass

# scheduler.add_job(scheduled_daily_scan, "cron", hour=_scan_hour, minute=0, id="daily_playbook_scan")
logger.info(f"定时任务已注册: 每日 {_scan_hour}:00 执行剧本扫描")

def scheduled_send_executor():
    """定时发送：执行已排队的营销任务（wechat_cli + ml307a）"""
    from sqlalchemy.orm import Session as _Session
    from channels.executor import SendExecutor
    from channels.drivers.ml307a import ML307ADriver
    from channels.drivers.wechat_cli import WeChatCliDriver
    db = _Session(bind=engine)
    try:
        cfg = get_config()
        # 开发模式绕过权限限制，或至尊版才执行自动发送
        if not cfg.server.dev_mode and cfg.current_tier != "business":
            return  # 非至尊版且非开发模式不执行自动发送
        raw_ch = cfg.raw.get("channels", {})
        drivers = {}

        # 个人微信 CLI（优先级最高）
        wechat_cli_config = raw_ch.get("wechat_cli", {})
        if wechat_cli_config.get("enabled", False):
            try:
                wechat_driver = WeChatCliDriver(wechat_cli_config)
                if wechat_driver.is_available():
                    drivers["wechat_cli"] = wechat_driver
                    wechat_driver.load_friend_cache(force=True)
                else:
                    logger.warning("[定时] wechat_cli 探活失败，回落到 ml307a")
            except Exception as e:
                logger.error(f"[定时] wechat_cli 初始化失败：{e}")

        # 短信猫（降级兜底）
        ml307a_config = raw_ch.get("ml307a", {})
        if ml307a_config.get("enabled", False):
            drivers["ml307a"] = ML307ADriver(ml307a_config)

        executor = SendExecutor(cfg, drivers)
        executor.execute_batch(db)
    except Exception as e:
        logger.error(f"[定时] 发送执行失败: {e}")
        db.rollback()
    finally:
        db.close()

_send_interval = 10
try:
    _send_interval = get_config().raw.get("playbook", {}).get("send_interval_min", 10)
except Exception:
    pass

# scheduler.add_job(scheduled_send_executor, "interval", minutes=_send_interval, id="send_executor")
logger.info(f"定时任务已注册: 每 {_send_interval} 分钟执行发送队列")

def scheduled_sms_collect():
    """定时采集短信回复：每10分钟从ML307A读取新短信"""
    from sqlalchemy.orm import Session as _Session
    from services.sms_receiver_service import get_sms_receiver_service
    from channels.drivers.ml307a import ML307ADriver
    from ai.llm_client import get_llm_client
    from ai.reply_parser import ReplyParser
    from db_models import ClientReply, Client
    import uuid

    cfg = get_config()
    raw_channels = cfg.raw.get("channels", {})
    ml307a_config = raw_channels.get("ml307a", {})

    if not ml307a_config.get("enabled", False):
        logger.debug("[定时] ML307A 未启用，跳过短信采集")
        return

    db = _Session(bind=engine)
    try:
        # 获取短信接收服务
        driver = ML307ADriver(ml307a_config)
        receiver = get_sms_receiver_service(driver)
        receiver.start()

        # 检查新短信
        receiver._check_new_sms()
        pending_sms = receiver.get_pending_sms()

        if not pending_sms:
            logger.debug("[定时] 无新短信")
            return

        # AI 解析器
        llm = get_llm_client()
        parser = ReplyParser(cfg, llm)

        saved_count = 0
        for sms in pending_sms:
            try:
                # 查找关联客户
                sender_clean = sms.sender.replace('+86', '').replace('+', '')
                client = db.query(Client).filter(Client.phone == sender_clean).first()

                # 创建回复记录
                reply = ClientReply(
                    id=str(uuid.uuid4()),
                    client_id=str(client.id) if client else None,
                    raw_content=sms.content,
                    campaign_task_id=None,
                )
                db.add(reply)
                db.flush()

                # AI 解析
                try:
                    parsed = parser.parse(sms.content)
                    reply.ai_parsed_intent = parsed.get("intent") or sms.category.value
                    reply.ai_parsed_details = {
                        **parsed.get("details", {}),
                        "sms_category": sms.category.value,
                        "sender": sender_clean,
                        "received_at": sms.received_at.isoformat()
                    }
                    reply.auto_action_taken = parsed.get("suggested_action")
                except Exception as e:
                    logger.error(f"[定时短信采集] AI 解析失败: {e}")
                    reply.ai_parsed_intent = sms.category.value

                saved_count += 1
            except Exception as e:
                logger.error(f"[定时短信采集] 保存失败: {e}")

        db.commit()
        logger.info(f"[定时] 采集短信 {saved_count} 条")

    except Exception as e:
        logger.error(f"[定时] 短信采集失败: {e}")
        db.rollback()
    finally:
        db.close()

# 每10分钟采集一次短信回复
SMS_COLLECT_INTERVAL = 10  # 分钟

# scheduler.add_job(scheduled_sms_collect, "interval", minutes=SMS_COLLECT_INTERVAL, id="sms_collect")
logger.info(f"定时任务已注册: 每 {SMS_COLLECT_INTERVAL} 分钟采集短信回复")

if __name__ == "__main__":
    # PyInstaller 打包后不能使用字符串导入方式，需要直接传递 app 对象
    # 端口优先级：环境变量 PORT > config.yaml > 默认 8000
    import os
    env_port = os.environ.get('PORT')
    if env_port:
        port = int(env_port)
    else:
        # 从配置文件读取端口
        port = app_config.server.port if 'app_config' in dir() else 8000
    logger.info(f"服务启动端口：{port}")

    # 配置 uvicorn 日志（无控制台模式需禁用默认日志）
    log_config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "default": {
                "()": "uvicorn.logging.DefaultFormatter",
                "fmt": "%(levelprefix)s %(message)s",
                "use_colors": False,
            },
        },
        "handlers": {
            "default": {
                "formatter": "default",
                "class": "logging.NullHandler",  # 无控制台时使用 NullHandler
            },
        },
        "loggers": {
            "uvicorn": {"handlers": ["default"], "level": "INFO"},
            "uvicorn.error": {"level": "INFO"},
            "uvicorn.access": {"handlers": ["default"], "level": "INFO", "propagate": False},
        },
    }

    # 检查是否有控制台
    if sys.stdout is not None:
        # 有控制台时使用标准输出
        log_config["handlers"]["default"]["class"] = "logging.StreamHandler"

    uvicorn.run(app, host="0.0.0.0", port=port, reload=False, log_config=log_config)
