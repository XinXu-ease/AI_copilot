# 🚀 快速启动指南

## 方式 1：使用启动脚本（最简单）⭐ 推荐

```bash
cd d:\DeskTOP\Product_Muiltagent\ai-product-team-copilot
python run.py
```

这会自动：
- ✅ 检查依赖
- ✅ 启动后端（localhost:5000）
- ✅ 启动前端（localhost:8000）  
- ✅ 打开浏览器

---

## 方式 2：手动启动（分开两个终端）

### 步骤 1️⃣：启动后端

**打开 PowerShell 或 CMD，输入：**

```powershell
# 进入项目目录
cd d:\DeskTOP\Product_Muiltagent\ai-product-team-copilot

# 第一次运行需要安装依赖
pip install -r requirements.txt

# 启动后端
python app_api.py
```

**应该看到类似的输出：**
```
============================================================
AI Product Team Copilot - API Server
============================================================
Starting Flask API server...
Frontend should request from: http://localhost:5000/api
============================================================
 * Serving Flask app 'app_api'
 * Debug mode: on
 * Running on http://0.0.0.0:5000
 * WARNING in app.run(), this is a development server. Do not use it in production.
```

**✅ 看到这个就说明后端启动成功了**

---

### 步骤 2️⃣：启动前端（新开一个终端）

```powershell
# 进入项目目录
cd d:\DeskTOP\Product_Muiltagent\ai-product-team-copilot

# 启动 HTTP 服务器
python -m http.server 8000
```

**应该看到：**
```
Serving HTTP on 0.0.0.0 port 8000 (http://0.0.0.0:8000/) ...
```

**✅ 看到这个就说明前端启动成功了**

---

### 步骤 3️⃣：打开浏览器

访问：
```
http://localhost:8000/index.html
```

---

## 验证一切正常

### 1. 检查后端健康状态

在浏览器中打开：
```
http://localhost:5000/health
```

**应该看到：**
```json
{
  "status": "healthy",
  "timestamp": "..."
}
```

### 2. 检查两个服务都在运行

**后端终端应该显示：**
```
 * Running on http://0.0.0.0:5000
```

**前端终端应该显示：**
```
Serving HTTP on 0.0.0.0 port 8000
```

---

## 第一次使用的完整流程

```bash
# 1. 进入项目目录
cd d:\DeskTOP\Product_Muiltagent\ai-product-team-copilot

# 2. 安装依赖（只需一次）
pip install -r requirements.txt

# 3. 确认 .env 文件已配置
# 编辑 .env 文件，添加你的 OpenAI API Key
# OPENAI_API_KEY=your_key_here

# 4. 启动后端（终端 1）
python app_api.py

# 5. 启动前端（新终端 2）
python -m http.server 8000

# 6. 打开浏览器
# http://localhost:8000/index.html
```

---

## 🛑 停止服务

按 **Ctrl + C** 停止任何服务

---

## ❌ 遇到问题？

### 错误：ModuleNotFoundError

**原因：** 依赖未安装

**解决：**
```bash
pip install -r requirements.txt
```

### 错误：Port 5000 already in use

**原因：** 端口被占用

**解决方案 A - 查找并关闭：**
```powershell
netstat -ano | findstr :5000
taskkill /PID <PID> /F
```

**解决方案 B - 使用其他端口：**
修改 `app_api.py` 最后一行改为 `:5001`

### 错误：无法连接到 API

**检查清单：**
- ✅ 后端是否在运行（看终端 1）
- ✅ 前端是否在运行（看终端 2）
- ✅ .env 文件是否配置 OPENAI_API_KEY
- ✅ 浏览器按 F12 看日志有什么错误

---

## 常用命令速查

| 命令 | 说明 |
|------|------|
| `python app_api.py` | 启动后端服务 |
| `python -m http.server 8000` | 启动前端服务 |
| `python run.py` | 一键启动脚本 |
| `pip install -r requirements.txt` | 安装依赖 |
| `Ctrl + C` | 停止当前服务 |
| `http://localhost:5000/health` | 检查后端状态 |
| `http://localhost:8000/index.html` | 打开前端 |

---

**现在就试试吧！👉 `python run.py`**
