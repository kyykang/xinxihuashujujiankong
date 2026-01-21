# 更新日志

## v2.0.0 (2026-01-21)

### 🎉 重大更新：用户管理和权限控制

#### 新增功能

##### 用户认证系统
- ✅ 用户登录/注销功能
- ✅ 会话管理，支持"记住我"（30天）
- ✅ 密码修改功能
- ✅ 默认管理员账户（admin/admin123）

##### 用户管理
- ✅ 用户管理界面（仅管理员可访问）
- ✅ 添加/编辑/删除用户
- ✅ 用户列表展示（用户名、邮箱、角色、创建时间、最后登录）
- ✅ 命令行用户管理脚本（add_user.py）

##### 权限控制
- ✅ 基于角色的访问控制（RBAC）
- ✅ 管理员角色：完全控制权限
- ✅ 普通用户角色：只读权限
- ✅ 前端权限控制（隐藏/禁用按钮）
- ✅ 后端权限验证（API层面）
- ✅ 装饰器：@login_required, @admin_required

##### 安全增强
- ✅ 密码哈希存储（PBKDF2-SHA256）
- ✅ 配置数据加密（AES）
- ✅ 会话加密
- ✅ 防止未授权访问

#### 权限详情

**管理员权限**：
- 查看所有监控数据
- 添加/编辑/删除监控目标
- 修改系统配置
- 管理用户账户
- 清除告警记录

**普通用户权限**：
- 查看监控仪表板
- 查看监控目标列表
- 查看告警记录
- 查看系统配置
- 修改自己的密码
- ❌ 不能修改任何配置

#### 文件变更

**新增文件**：
- `templates/users.html` - 用户管理页面
- `add_user.py` - 命令行用户管理脚本
- `用户管理功能说明.md` - 用户管理使用文档
- `用户权限管理说明.md` - 权限详细说明
- `CHANGELOG.md` - 更新日志

**修改文件**：
- `app.py` - 添加用户管理路由和权限控制
- `database.py` - 添加users表
- `templates/base.html` - 添加用户菜单和用户管理链接
- `templates/targets.html` - 根据权限隐藏操作按钮
- `templates/config.html` - 根据权限禁用配置修改
- `README.md` - 更新文档，添加用户管理说明

#### 数据库变更

**新增表**：
```sql
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    email TEXT,
    is_admin INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP
);
```

#### 使用示例

**添加只读用户**：
```bash
# 方法1：命令行
python3 add_user.py viewer viewer123 "viewer@example.com" 0

# 方法2：交互式
python3 add_user.py

# 方法3：Web界面
# 登录 -> 用户管理 -> 添加用户
```

**修改密码**：
```
登录 -> 右上角设置图标 -> 修改密码
```

#### 迁移指南

如果你已经在使用旧版本：

1. **备份数据**：
   ```bash
   cp monitoring.db monitoring.db.backup
   ```

2. **更新代码**：
   ```bash
   git pull origin main
   ```

3. **迁移数据**：
   ```bash
   python3 migrate_add_users.py
   ```

4. **重启系统**：
   ```bash
   python3 app.py
   ```

5. **首次登录**：
   - 用户名: admin
   - 密码: admin123
   - 立即修改密码！

#### 已知问题

无

#### 下一步计划

- [ ] 支持LDAP/AD集成
- [ ] 支持OAuth2登录
- [ ] 更细粒度的权限控制
- [ ] 用户操作日志
- [ ] 密码强度策略配置
- [ ] 账户锁定机制

---

## v1.5.0 (2026-01-20)

### 密码加密存储

#### 新增功能
- ✅ AES加密算法保护敏感信息
- ✅ 自动加密/解密配置数据
- ✅ 密钥文件管理（.secret_key）
- ✅ 数据迁移脚本

#### 文件变更
- 新增：`crypto_utils.py` - 加密工具模块
- 新增：`migrate_encrypt_passwords.py` - 密码加密迁移脚本
- 新增：`安全配置说明.md` - 安全功能文档
- 修改：`app.py` - 集成加密/解密功能
- 修改：`scheduler.py` - 支持配置解密
- 修改：`.gitignore` - 排除密钥文件

---

## v1.4.0 (2026-01-19)

### 备份文件监控

#### 新增功能
- ✅ 远程服务器备份文件检查
- ✅ 文件名模式匹配
- ✅ 文件年龄告警
- ✅ 文件列表展示

#### 文件变更
- 修改：`remote_monitor.py` - 添加备份文件检查方法
- 修改：`monitors.py` - 集成备份文件监控
- 修改：`templates/dashboard.html` - 添加备份文件卡片

---

## v1.3.0 (2026-01-18)

### 仪表板拖拽排序

#### 新增功能
- ✅ 监控卡片拖拽排序
- ✅ 布局自动保存（localStorage）
- ✅ 拖拽手柄和视觉反馈

#### 文件变更
- 修改：`templates/dashboard.html` - 集成SortableJS

---

## v1.2.0 (2026-01-17)

### SQL Server支持

#### 新增功能
- ✅ SQL Server数据库监控
- ✅ 数据库类型选择器
- ✅ 自动切换默认端口

#### 文件变更
- 修改：`app.py` - 添加SQL Server测试连接
- 修改：`monitors.py` - 添加SQL Server监控方法
- 修改：`scheduler.py` - 支持SQL Server
- 修改：`templates/targets.html` - 添加数据库类型选择
- 修改：`requirements.txt` - 添加pymssql

---

## v1.1.0 (2026-01-16)

### 初始版本

#### 核心功能
- ✅ 服务器监控（本地/远程）
- ✅ 应用监控（HTTP/HTTPS）
- ✅ 数据库监控（MySQL）
- ✅ 存储监控
- ✅ 业务指标监控
- ✅ 可视化仪表板
- ✅ 告警功能
- ✅ 企业微信推送
