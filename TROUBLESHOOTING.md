# 故障排查指南 - API 连接问题

## ❌ 错误提示：Failed to start project: Failed to fetch

这个错误表示前端无法连接到 API 后端。按照以下步骤排查：

### 第1步：验证后端是否运行

**Windows PowerShell:**
```powershell
# 检查5000端口是否被占用
netstat -ano | findstr :5000

# 如果显示 LISTENING，说明有服务在该端口运行
# 记下 PID，然后检查是否是我们的应用
tasklist | findstr <PID>
```

**Mac/Linux:**
```bash
lsof -i :5000
```

### 第2步：启动后端服务

**确保后端已启动：**

```bash
# 进入项目目录
cd d:\DeskTOP\Product_Muiltagent\ai-product-team-copilot

# 安装依赖（如未安装）
pip install -r requirements.txt

# 启动 API 服务
python app_api.py
```

**预期输出应该类似于：**
```
============================================================
AI Product Team Copilot - API Server
============================================================
Starting Flask API server...
Frontend should request from: http://localhost:5000/api
============================================================
* Serving Flask app...
* Running on http://0.0.0.0:5000
```

### 第3步：测试 API 连接

打开浏览器访问：
```
http://localhost:5000/health
```

**如果成功，应该看到：**
```json
{"status": "healthy", "timestamp": "..."}
```

**如果看不到，说明：**
- 后端没有启动
- 端口 5000 被其他程序占用
- 防火墙阻止了连接

### 第4步：启动前端服务

**新开一个终端，运行：**

**方式 A - Python HTTP 服务器（推荐）：**
```bash
cd d:\DeskTOP\Product_Muiltagent\ai-product-team-copilot
python -m http.server 8000
```

**方式 B - 使用启动脚本：**
```bash
python run.py
```

**方式 C - 直接打开文件：**
- 在文件浏览器中打开 `index.html`（可能有 CORS 限制）

### 第5步：访问前端

在浏览器中访问：
```
http://localhost:8000/index.html
```

---

## 🔍 常见问题和解决方案

### ❓ 问题1：Port 5000 已被占用

**症状：**
```
OSError: [WinError 10048] 通常每个套接字地址 (协议/网络地址/端口) 只允许使用一次
```

**解决方案 A - 查找并杀死占用该端口的进程：**

```powershell
# Windows
netstat -ano | findstr :5000
taskkill /PID <PID> /F

# Mac/Linux
lsof -i :5000
kill -9 <PID>
```

**解决方案 B - 更改端口：**

编辑 `app_api.py` 最后一行：
```python
app.run(debug=True, port=5001, host='0.0.0.0')  # 改为 5001
```

然后在 `index.html` 更改：
```javascript
const API_BASE = 'http://localhost:5001/api';  // 改为 5001
```

---

### ❓ 问题2：连接被拒绝（Connection refused）

**症状：**
```
Failed to start project: Failed to fetch
browser console: GET http://localhost:5000/health net::ERR_CONNECTION_REFUSED
```

**解决方案：**
1. 确认后端已启动：`python app_api.py`
2. 检查防火墙设置，允许 localhost 连接
3. 检查是否在正确的目录运行命令
4. 查看 API 服务是否有错误输出

---

### ❓ 问题3：CORS 错误

**症状：**
```
Access to XMLHttpRequest at 'http://localhost:5000/api/project/start' 
from origin 'http://localhost:8000' has been blocked by CORS policy
```

**解决方案：**
- 这个应该已经在 `app_api.py` 中配置好了
- 如果仍然出现，检查 Flask-CORS 是否已安装：
  ```bash
  pip install flask-cors
  ```

---

### ❓ 问题4：请求超时

**症状：**
```
Failed to fetch (request timeout after 5 minutes)
```

**原因：**
- LLM API 调用缓慢
- OpenAI API 配额不足
- 网络连接较差

**解决方案：**
1. 检查 `.env` 中的 `OPENAI_API_KEY` 是否正确
2. 检查 API 配额是否足够
3. 查看 `api.log` 中的详细错误信息
4. 在 `app_api.py` 中增加超时时间（见下面的高级配置）

---

### ❓ 问题5：返回 500 Internal Server Error

**症状：**
```
Server returned 500: Internal server error
```

**解决方案：**
1. 查看 API 日志：打开 `api.log` 文件
2. 检查是否有 Python 依赖缺失：
   ```bash
   pip install -r requirements.txt
   ```
3. 验证所有导入路径是否正确
4. 检查数据库初始化是否成功

---

## 🔧 高级配置

### 调整超时时间

编辑 `index.html`：
```javascript
const API_TIMEOUT = 600000; // 10分钟（毫秒）
```

### 启用详细日志

编辑 `app_api.py`：
```python
logging.basicConfig(level=logging.DEBUG)  # 改为 DEBUG
```

### 指定不同的 API 地址

有时需要远程 API 服务器时，编辑 `index.html`：
```javascript
const API_BASE = 'http://remote-server.com:5000/api';
```

---

## 📋 完整的启动清单

```
☐ 确认 Python 已安装（python --version）
☐ 安装依赖：pip install -r requirements.txt
☐ 配置 .env 文件：OPENAI_API_KEY=...
☐ 启动 API 后端：python app_api.py
☐ 验证健康检查：http://localhost:5000/health
☐ 启动前端服务：python -m http.server 8000
☐ 打开前端：http://localhost:8000/index.html
☐ 输入项目想法，点击 "Start Project"
```

---

## 🆘 仍然无法解决？

1. **查看浏览器控制台**（按 F12）
   - 检查 Network 标签中的请求
   - 查看 Console 中的错误信息

2. **查看后端日志**
   - 检查终端输出
   - 查看 `api.log` 文件

3. **尝试重新启动**
   - 关闭所有服务
   - 等待 10 秒
   - 重新启动后端和前端

4. **重置配置**
   - 删除 `api.log` 文件
   - 删除任何缓存
   - 从头开始

---

**最后更新：2026-04-06**
