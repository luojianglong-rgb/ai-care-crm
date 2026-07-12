/**
 * API 配置模块
 * 支持本地访问和局域网访问
 * 生产环境使用空字符串（相对路径），开发环境可通过 .env 配置
 */
const API_BASE_URL = import.meta.env.VITE_API_URL || '';

export default API_BASE_URL;
