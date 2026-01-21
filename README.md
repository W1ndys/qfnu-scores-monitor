# QFNU 成绩监控与通知系统

![GitHub stars](https://img.shields.io/github/stars/W1ndys/QFNULogin)
![GitHub forks](https://img.shields.io/github/forks/W1ndys/QFNULogin)
![GitHub license](https://img.shields.io/github/license/W1ndys/QFNULogin)

基于曲阜师范大学教务系统的成绩监控与通知系统，支持自动检测新成绩并通过钉钉推送通知。

## 功能特性

- **自动成绩监控**：定时检测教务系统成绩变化
- **钉钉消息推送**：发现新成绩时自动推送通知
- **安全加密存储**：使用 AES-256-GCM 加密存储 Session
- **零密码存储**：仅存储加密 Session，不保存学号密码
- **Web 管理界面**：提供用户登录和管理后台
- **Session 过期检测**：自动检测并通知 Session 过期

## 技术栈

- **后端**：Flask + APScheduler
- **数据库**：SQLite
- **前端**：Alpine.js + Jinja2
- **加密**：Cryptography (AES-256-GCM)
- **验证码识别**：ddddocr

## 快速开始

### 1. 安装依赖

```bash
# 使用 uv（推荐）
uv sync

# 或使用 pip
pip install -r requirements.txt
```

### 2. 配置环境变量（可选）

```bash
cp .env.example .env
# 编辑 .env 文件（仅用于测试登录功能）
```

### 3. 启动应用

```bash
python app.py
```

应用将在 `http://localhost:5000` 启动。

### 4. 使用系统

1. 访问 `http://localhost:5000` 进入用户登录页面
2. 输入学号、密码和钉钉 Webhook（可选）
3. 阅读并同意用户协议
4. 点击"登录并开始监控"
5. 系统将每 30 分钟自动检测一次成绩

### 5. 管理后台

访问 `http://localhost:5000/admin` 进入管理后台，可以：

- 查看所有用户状态
- 启用/禁用用户监控
- 手动触发成绩检测

## 安全说明

1. **零密码存储**：系统不保存学号和密码，仅在登录时使用
2. **加密存储**：Session 使用 AES-256-GCM 加密，每个用户独立密钥
3. **哈希标识**：使用学号 SHA-256 哈希作为用户标识
4. **内存解密**：Session 仅在检测时临时解密到内存
5. **过期检测**：自动检测 Session 过期并停止监控

## 钉钉 Webhook 配置

1. 在钉钉群中添加自定义机器人
2. 获取 Webhook 地址（格式：`https://oapi.dingtalk.com/robot/send?access_token=...`）
3. 在登录时填入 Webhook 地址

## 项目结构

```
.
├── app.py                  # Flask 应用主文件
├── scheduler.py            # 定时任务调度器
├── models.py               # 数据库模型
├── main.py                 # 登录模块
├── config.py               # 配置文件
├── utils/
│   ├── crypto.py          # 加密工具
│   ├── score_monitor.py   # 成绩监控
│   ├── dingtalk.py        # 钉钉推送
│   ├── session_manager.py # Session 管理
│   ├── captcha_ocr.py     # 验证码识别
│   └── logger.py          # 日志工具
└── templates/
    ├── index.html         # 用户登录页面
    └── admin.html         # 管理后台页面
```

## API 接口

### POST /api/login
用户登录并开始监控

**请求体**：
```json
{
  "user_account": "学号",
  "user_password": "密码",
  "dingtalk_webhook": "钉钉Webhook（可选）"
}
```

### GET /api/users
获取用户列表

### POST /api/users/:user_hash/toggle
切换用户启用状态

### POST /api/check
手动触发成绩检测

## 注意事项

1. 系统每 30 分钟自动检测一次成绩
2. Session 过期后需要重新登录
3. 建议在服务器上运行以保持持续监控
4. 请妥善保管钉钉 Webhook 地址

## 其他项目

qfnu 模拟登录，对于其他学校的强智教务2017也是通用的，改个URL即可

---

## 示例实现：曲阜师范大学期末考试导出为 ics 日历文件

[https://github.com/W1ndys/QFNUExam2ics](https://github.com/W1ndys/QFNUExam2ics)

---

使用本项目开发的脚本请带上`qfnulogin`的标签，便于搜索 https://github.com/topics/qfnulogin

---

## 友情链接

- [曲阜师范大学课表自动生成](https://github.com/liu-zhe/QFNU-ics)：支持一键导入，兼容各种日历 APP
- [曲师大 CAS token 获取脚本](https://github.com/nakaii-002/Qfnu_CAS_token)

---

## 致谢

感谢 [ddddocr](https://github.com/sml2h3/ddddocr) 提供的验证码识别功能

感谢 [liu-zhe](https://github.com/liu-zhe)(Lukzia) 的[qfnu_api.py](https://github.com/liu-zhe/QFNU-ics/blob/main/qfnu_api.py) 模拟登录启发

感谢 [nakaii](https://github.com/nakaii-002)(nakaii) 的[Qfnu_CAS_token](https://github.com/nakaii-002/Qfnu_CAS_token) 验证码识别启发

感谢 [AuroBreeze](https://github.com/AuroBreeze) 的[生成 encoded 算法](https://github.com/W1ndys/QFNULogin/commit/f76a20c80656a34cea2e2db4e988917cf404d00a) 的启发

## License

MIT License
