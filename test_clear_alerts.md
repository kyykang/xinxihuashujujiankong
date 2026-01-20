# 清除告警功能测试

## 当前数据库状态

- **告警记录数**：73条
- **监控数据数**：1713条
- **数据库大小**：204KB

## 测试步骤

### 1. 访问告警页面
```
http://localhost:8080/alerts
```

### 2. 查看统计信息
页面顶部应该显示：
- 总告警数：73
- 待处理数量
- 已处理数量
- 数据库大小：204KB

### 3. 测试清除功能

#### 测试1：清除已处理的记录
1. 点击"清除记录"按钮
2. 选择"仅清除已处理的记录"
3. 不勾选"同时清除监控数据"
4. 输入 `DELETE`
5. 点击"确认清除"
6. 查看结果

#### 测试2：清除7天前的记录
1. 点击"清除记录"按钮
2. 选择"清除7天前的记录"
3. 勾选"同时清除监控数据"
4. 输入 `DELETE`
5. 点击"确认清除"
6. 查看数据库大小是否减小

#### 测试3：清除所有记录（谨慎）
1. 点击"清除记录"按钮
2. 选择"清除所有告警记录"
3. 勾选"同时清除监控数据"
4. 输入 `DELETE`
5. 点击"确认清除"
6. 确认所有记录已清除

## 验证结果

### 使用SQL查询
```bash
# 查看告警记录数
sqlite3 monitoring.db "SELECT COUNT(*) FROM alerts"

# 查看监控数据数
sqlite3 monitoring.db "SELECT COUNT(*) FROM monitor_data"

# 查看数据库大小
ls -lh monitoring.db
```

### 使用API
```bash
# 获取数据库大小
curl http://localhost:8080/api/database-size

# 清除30天前的记录
curl -X POST http://localhost:8080/api/clear-alerts \
  -H "Content-Type: application/json" \
  -d '{"range":"30days","clear_monitor_data":true}'
```

## 预期结果

- ✅ 页面显示正确的统计信息
- ✅ 清除按钮正常工作
- ✅ 模态框正确显示
- ✅ 需要输入DELETE才能确认
- ✅ 清除后显示删除的记录数
- ✅ 页面自动刷新
- ✅ 数据库大小减小
- ✅ VACUUM自动执行
