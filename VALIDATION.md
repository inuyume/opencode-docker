# 验证记录

验证日期：2026-10-03。

已在当前环境完成：

- 从 npm 官方 registry 安装实际 `@opencode/cli@2.0.22`。
- 使用实际 `opencode-models-discovery@1.6.1`，以本地 `dist` 目录方式加载 v2 的 `server.js`。
- 启动真实 OpenCode v2 前台服务。
- 用项目的 `configure.py` 将模板与 API 环境变量组合成配置。
- 用本地模拟 `/v1/models` 接口返回模型，确认模型出现在 v2 `/api/model` 响应中。
- 验证模型发现请求正确携带 API Bearer Key。
- 验证 `/api/info` 返回 v2 版本。
- 验证未认证访问 `/api/provider` 返回 HTTP 401。
- JSON/YAML 解析、Shell 语法检查和 Python 编译检查。

当前环境没有 Docker，未在这里执行 Docker 镜像构建、Docker Compose 启动或 arm64 实机验证。
GitHub Actions 中已加入 Compose 配置验证、amd64 镜像构建、Python 3.11 虚拟环境检查，
以及同一套真实服务/插件 smoke test。通过后才构建并推送 amd64/arm64 镜像。

模拟接口仅返回模型列表，不执行付费推理；第三方 API 的实际模型调用需部署后使用自己的密钥验证。

Release 导出更新：已验证工作流 YAML、导出脚本 Shell 语法，以及模拟 Docker 命令下的双架构导出、校验文件生成和架构不匹配拒绝路径。
当前环境没有 Docker，也未连接具体 GitHub 仓库；真实 tar 包导出和 Release 上传将在推送 `v*` 标签后由 Actions 执行。
