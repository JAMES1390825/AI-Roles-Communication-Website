# AI 角色扮演网站

这是一个全栈项目，包含一个基于 FastAPI 的后端服务和一个基于 Next.js 的前端应用。该平台旨在提供一个 AI 角色扮演体验，支持用户注册、登录、角色管理、聊天功能以及与大型语言模型 (LLM) 的集成。

## 主要技术栈

**后端**: Python, FastAPI, SQLAlchemy, PostgreSQL, Pydantic, JWT Auth, LLM Integration (Qwen API, Qiniu Kodo for audio).

**前端**: TypeScript, Next.js, React, Tailwind CSS, Axios for API interaction.

## 架构与模块

本项目采用前后端分离的架构，主要包含以下两个模块：

1.  **后端服务 (`backend/`)**:
    *   **技术栈**: FastAPI, SQLAlchemy, PostgreSQL, Pydantic.
    *   **职责**:
        *   提供 RESTful API 接口，处理客户端请求。
        *   使用 JWT 管理用户认证和授权。
        *   处理数据持久化和与 PostgreSQL 数据库的交互。
        *   处理业务逻辑，包括与 LLM 服务（用于 AI 响应）和七牛云 Kodo（用于音频处理 ASR 和 TTS）的集成。
    *   **文件结构**:
        *   `main.py`: FastAPI 应用的入口文件，定义主要路由。
        *   `app/auth.py`: 包含用户认证、JWT 生成和验证逻辑。
        *   `app/database.py`: 管理数据库连接和 SQLAlchemy 会话。
        *   `app/models.py`: 定义 SQLAlchemy ORM 模型，映射到数据库表结构。
        *   `app/schemas.py`: 定义 Pydantic 模型，用于请求和响应数据验证与序列化。
        *   `app/llm_service.py`: 集成大型语言模型和七牛云服务，用于 ASR/TTS。

2.  **前端应用 (`frontend/`)**:
    *   **技术栈**: Next.js, React, TypeScript, Tailwind CSS.
    *   **职责**:
        *   提供用户界面 (UI) 和良好的用户体验 (UX)。
        *   通过 API 调用与后端服务进行数据交换。
        *   管理客户端状态和路由。
        *   展示用户注册、登录、仪表盘和聊天页面。
    *   **文件结构**:
        *   `src/app/`: 包含 Next.js 页面和路由。
            *   `login/page.tsx`: 登录页面。
            *   `register/page.tsx`: 注册页面。
            *   `dashboard/page.tsx`: 用户仪表盘。
            *   `layout.tsx`: 整体应用布局。
            *   `globals.css`: 全局样式。
        *   `src/context/AuthContext.tsx`: 管理用户认证上下文。
        *   `src/api.ts`: 使用 Axios 封装前端到后端的 API 调用。

## 数据流

*   **前端到后端**: 用户在前端应用中的操作（例如，登录、注册、发送聊天消息）通过 `src/api.ts` 中定义的函数向后端 API 发送 HTTP 请求。请求数据在后端通过 Pydantic 模型进行验证。
*   **后端到数据库/LLM/七牛云**: 接收到请求后，后端服务通过 SQLAlchemy ORM 与 PostgreSQL 数据库进行 CRUD 操作。对于 AI 相关功能，它通过 `app/llm_service.py` 与 LLM 服务（例如，Qwen API）进行通信以生成响应，并利用七牛云 Kodo 进行音频处理。
*   **数据库/LLM/七牛云到后端**: 数据库、LLM 服务或七牛云 Kodo 将处理后的数据返回给后端。
*   **后端到前端**: 后端服务处理数据后，将响应（通常为 JSON 格式）返回给前端，前端根据响应更新 UI。

## 部署说明

### 1. 克隆仓库

首先，请克隆本项目的 Git 仓库到您的本地机器：

```bash
git clone <your-repository-url>
cd JAMESqiniuyun
```

### 2. 后端服务设置与运行

进入 `backend` 目录，安装依赖并启动后端服务。

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
# 创建 .env 文件并配置 DATABASE_URL、QINIU_OPENAI_API_KEY、QINIU_OPENAI_BASE_URL、QINIU_ACCESS_KEY、QINIU_SECRET_KEY、QINIU_BUCKET_NAME、QINIU_DOMAIN
# 参考 backend/app/database.py 和 backend/app/llm_service.py 中的环境变量说明
uvicorn main:app --reload
```

后端服务默认运行在 `http://127.0.0.1:8000`。

**`.env` 文件配置示例 (`backend/.env`):**

```
DATABASE_URL="postgresql://user:password@host:port/database_name"
QINIU_OPENAI_API_KEY="your_qiniu_openai_api_key"
QINIU_OPENAI_BASE_URL="your_qiniu_openai_base_url"
QINIU_ACCESS_KEY="your_qiniu_access_key"
QINIU_SECRET_KEY="your_qiniu_secret_key"
QINIU_BUCKET_NAME="your_qiniu_bucket_name"
QINIU_DOMAIN="your_qiniu_domain" # 例如: http://your_bucket_name.kodo-config.com
```

### 3. 前端应用设置与运行

在一个新的终端窗口中，进入 `frontend` 目录，安装依赖并启动前端应用。

```bash
cd ../frontend
npm install
npm run dev
```

前端应用默认运行在 `http://localhost:3000`.
