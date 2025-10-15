# 麻醉生命体征智能预警平台

基于 Flask 构建的全流程麻醉安全协同系统。平台支持多手术间配置、设备 API 集成、用药信息管理，并在生命体征超出阈值时调用 Dify LLM 给出干预建议，帮助麻醉医生快速做出决策。

## 功能亮点

- **多手术间管理**：为每个手术间配置监护仪、注射泵、麻醉机等设备及其参数。
- **阈值预警与联动**：灵活设置参数阈值，自动检测并生成预警记录。
- **患者与用药档案**：维护患者基础信息、麻醉用药清单和术中记录。
- **Dify 智能建议**：在生命体征异常时将现场信息推送至 Dify，获取针对性建议。
- **科技感前端界面**：可视化展示多源参数、预警记录和推荐意见，支持模拟数据流验证流程。

## 目录结构

```
.
├── config.py                 # 全局配置（数据库、Dify 等）
├── requirements.txt          # 依赖声明
├── run.py                    # 运行入口
└── wxcloudrun
    ├── __init__.py           # 应用初始化与数据库创建
    ├── dao.py                # 数据持久化工具
    ├── dify_client.py        # Dify API 封装
    ├── model.py              # SQLAlchemy 模型定义
    ├── response.py           # 统一响应结构
    ├── templates
    │   └── index.html        # 前端控制台
    └── views.py              # REST API 与监测业务逻辑
```

## 快速开始

1. **准备环境**
   ```bash
   python -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

2. **设置环境变量（可选）**
   - `DATABASE_URL`：默认使用项目根目录下的 SQLite 数据库，可根据需要指向 MySQL。
   - `DIFY_API_URL` 与 `DIFY_API_KEY`：配置后即可启用 Dify 联动。

3. **启动应用**
   ```bash
   flask --app run.py run
   ```
   访问 `http://127.0.0.1:5000` 打开监测工作台。

4. **模拟流程**
   - 左侧新增手术间并配置设备/阈值（可通过 API）。
   - 选择手术间，录入患者与用药资料后启动监测。
   - 点击“模拟采集数据”即可演示阈值告警与 Dify 建议的联动。

## API 概览

- `POST /api/rooms`：创建手术间。
- `POST /api/rooms/<room_id>/devices`：为手术间接入设备。
- `POST /api/devices/<device_id>/parameters`：注册监测参数。
- `POST /api/parameters/<parameter_id>/threshold`：配置阈值。
- `POST /api/sessions`：启动监测会话。
- `POST /api/sessions/<session_id>/ingest`：写入实时参数并自动触发预警。

详细请求/响应示例可参考 `wxcloudrun/views.py` 中的注释实现。

## License

[MIT](./LICENSE)
