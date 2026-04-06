# AI Product Team Copilot - HTML Version

## 改进内容

✅ **前端改造**：从 Streamlit 改为 HTML + JavaScript
✅ **设计优化**：简洁蓝白主题，现代化 UI 设计
✅ **Bug 修复**：修复 missing_info 重复显示问题
✅ **交互保留**：完全保留原有的工作流和交互逻辑

## 主要特性

- **蓝白配色方案**：清爽专业的视觉风格
- **响应式设计**：支持桌面和移动设备
- **实时进度显示**：直观的工作流阶段指示器
- **简洁表单交互**：清晰的用户输入界面
- **完整的项目追踪**：从 Brief 到开发完整的工作流

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 启动 API 后端

```bash
python app_api.py
```

后端将在 `http://localhost:5000` 启动

### 3. 打开前端

在浏览器中打开 `index.html`，或者用 HTTP 服务器提供：

```bash
# 使用 Python 内置服务器
python -m http.server 8000
```

然后访问 `http://localhost:8000/index.html`

## 项目结构

```
├── app_api.py              # Flask API 后端
├── index.html              # HTML 前端界面
├── app.py                  # 原始 Streamlit 版本（已弃用）
├── requirements.txt        # 更新的依赖列表
└── src/
    ├── workflows/nodes.py  # 修复了 missing_info 重复问题
    └── ...
```

## API 端点

### POST /api/project/start
启动新项目

**请求体：**
```json
{
  "idea": "Project idea description"
}
```

**响应：**
```json
{
  "success": true,
  "project_id": "uuid",
  "state": { /* 项目状态 */ }
}
```

### GET /api/project/{project_id}
获取项目状态

### POST /api/project/{project_id}/clarification
提交澄清问题答案

**请求体：**
```json
{
  "answers": ["answer1", "answer2", ...]
}
```

## 工作流程

1. **输入想法** → 用户输入产品概念
2. **PM Brief** → AI 生成结构化产品简介
3. **澄清** → 如需要，系统提出澄清问题
4. **Research Round 1** → 初步研究验证
5. **Research Round 2** → 深度研究分析
6. **UX 设计** → AI 生成 UX 方案
7. **开发计划** → AI 生成技术实现计划

## 故障排除

### API 连接失败

确保 Flask 后端已启动在 `localhost:5000`

### CORS 错误

CORS 已在 Flask 后端配置，确保使用正确的 API 地址

### 页面加载缓慢

项目涉及多个 LLM 调用，首次执行可能需要 1-3 分钟

## 注意事项

- 项目状态目前存储在内存中，服务器重启会丢失数据
- 生产环境建议将状态存储到数据库
- 确保配置正确的 OpenAI API 密钥（`.env` 文件）

## 恢复原 Streamlit 版本

如需使用原始 Streamlit 版本：

```bash
streamlit run app.py
```

但推荐使用新的 HTML 版本以获得更好的用户体验和 bug 修复。
