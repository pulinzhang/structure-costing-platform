# Zeabur 部署指南

> 国内可直接访问的免费部署平台

---

## 一、Zeabur 优势

| 优势 | 说明 |
|------|------|
| ✅ 国内访问快 | 服务器在亚太地区（上海/日本） |
| ✅ 免费额度 | 个人项目够用 |
| ✅ 支持 Docker | 完整运行 FastAPI |
| ✅ 自动 HTTPS | 免费 SSL 证书 |
| ✅ 零配置 | 上传代码自动部署 |

---

## 二、部署步骤

### 1. 注册 Zeabur

访问 https://zeabur.com 注册（可用 GitHub 登录）

### 2. 创建服务

1. 点击 **New Project** → **Deploy from GitHub**
2. 授权 GitHub，选择仓库 `stamping-costing-platform`
3. Zeabur 会自动检测 Dockerfile

### 3. 部署配置

在服务设置中配置：

```yaml
# 端口: 8000
# 构建命令: （留空，使用 Dockerfile）
# 启动命令: （留空，使用 Dockerfile CMD）
```

### 4. 绑定域名（可选）

1. 在服务 Settings → Domains 添加自定义域名
2. 支持自动配置 HTTPS

---

## 三、访问应用

部署成功后，通过以下地址访问：

- **前端**: `https://your-project.zeabur.app/app`
- **API**: `https://your-project.zeabur.app/docs`
- **上传目录**: `https://your-project.zeabur.app/uploads`

---

## 四、注意事项

### 4.1 数据库

当前使用 SQLite，数据文件存储在容器内。

⚠️ **重要**: 重新部署会丢失数据！

如需持久化，建议升级为：
- Zeabur PostgreSQL（付费）
- 外部数据库服务

### 4.2 文件上传

uploads 目录在容器内，重新部署会清空。

### 4.3 环境变量

在 Zeabur 控制台设置：

| 变量名 | 值 | 说明 |
|--------|-----|------|
| `ENV` | `production` | 生产环境 |
| `DEBUG` | `false` | 关闭调试模式 |

---

## 五、Gitee 自动化部署

如果用 Gitee，可以配合 Gitee Go：

1. **Gitee Go 流水线**: https://gitee.com/features/workflow
2. **触发条件**: push 到指定分支
3. **构建后推送**: Docker 镜像到容器 registry

---

## 六、常见问题

### Q: 部署失败？

检查 Dockerfile 是否在项目根目录，查看 Zeabur 部署日志。

### Q: 如何更新版本？

只需 push 到 GitHub/Gitee，Zeabur 会自动重新部署。

### Q: 免费额度用完怎么办？

Zeabur 按量付费，超免费额度才收费。
