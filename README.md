# OpenCode v2 Docker + GHCR

通过 GitHub Actions 构建自用 OpenCode v2 镜像，推送到 `ghcr.io/<GitHub 用户名>/opencode`。

## 内置内容

| 组件 | 默认配置 |
| --- | --- |
| 基础镜像 | `node:22-bookworm-slim` |
| OpenCode | npm 安装 `@opencode/cli@2.0.22`，不是 v1 的 `opencode-ai` |
| 模型发现插件 | `opencode-models-discovery@1.6.1`，预安装并锁定依赖 |
| Python | Python 3.11，默认启用 `/opt/venv` 虚拟环境 |
| npm | 运行时使用 `https://registry.npmmirror.com` |
| pip | `https://pypi.tuna.tsinghua.edu.cn/simple` |
| Bun 插件安装源 | `/root/.bunfig.toml` 预设 npmmirror |
| 运维/开发工具 | git、SSH client、curl、wget、jq、ripgrep、gcc/g++、make、zip/unzip、网络工具 |
| 服务 | 前台 `opencode serve`，API + Web UI，4096 端口 |
| 镜像架构 | `linux/amd64`、`linux/arm64` |

插件的 v2 适配目前由上游标记为 beta。本项目固定插件 1.6.1，并对本地插件加载和自动发现执行真实服务测试。

## 项目文件

| 文件 | 用途 |
| --- | --- |
| `Dockerfile` | 安装 OpenCode v2、Python 3.11、插件和工具，配置 npm/pip 源 |
| `opencode.json` | v2 全局配置模板，使用 `plugins/providers/settings` |
| `plugins/package.json`、`package-lock.json` | 固定插件和依赖，用 `npm ci` 预安装 |
| `docker/entrypoint.sh`、`configure.py` | 初始化配置，应用 API 环境变量，启动命令 |
| `compose.yaml` | GHCR 镜像的长期服务部署 |
| `compose.build.yaml` | 本地构建覆盖文件 |
| `compose.cli.yaml` | 独立的交互式终端运行示例 |
| `.env.example` | 部署参数模板 |
| `.github/workflows/docker.yml` | 构建、测试、多架构推送 |
| `scripts/smoke.py` | 无需真实 API Key 的模拟模型发现测试 |
| `scripts/export-images.sh` | 从本次 GHCR 镜像 digest 导出两个架构的 Docker tar 包 |
| `VALIDATION.md` | 已完成的验证和环境限制 |

## 1. 上传到 GitHub，自动构建

在 GitHub 创建一个空仓库，例如 `opencode-docker`，默认分支为 `main`。
将压缩包解压后，进入项目根目录：

```bash
cd opencode-docker
git init
git add .
git commit -m "Add OpenCode v2 Docker image and GHCR workflow"
git branch -M main
git remote add origin https://github.com/你的用户名/opencode-docker.git
git push -u origin main
```

请使用自己的 GitHub 用户名替换 URL。不要先创建真实 `.env` 再上传；`.env` 已在 `.gitignore` 和 `.dockerignore` 中排除。
项目包含隐藏的 `.github` 目录，使用上述 `git add .` 会将工作流一同提交。

仓库的 **Actions → Build OpenCode v2 Image** 中可以查看构建过程。
工作流使用自动生成的 `GITHUB_TOKEN`，并声明 `packages: write`，不需要自行添加 GHCR 密码。

默认镜像路径只与仓库所有者有关，与仓库名无关：

```text
ghcr.io/你的用户名/opencode:latest
ghcr.io/你的用户名/opencode:sha-xxxxxxx
ghcr.io/你的用户名/opencode:build-运行编号-重试编号
```

用户名会自动转为小写。主分支构建更新 `latest`；Git tag `v*` 构建生成同名镜像 tag。
标签构建不会覆盖主分支的 `latest`。`sha-*` 表示项目代码版本；同一提交重新构建可改变基础镜像，
需要固定镜像内容时使用 Actions 摘要里的 `@sha256:...` digest。

首次发布的 GHCR package 默认是 private，即使代码仓库公开也应检查镜像可见性。
若希望匿名拉取，在个人/组织 **Packages → opencode → Package settings → Change visibility** 中改为 public。
保持 private 时，拉取设备需要先 `docker login ghcr.io`，使用有 `read:packages` 的 PAT classic。
若已有同名 package，需确认该仓库拥有它的 Actions 写入权限。

## 发布 Release 镜像 tar 包

推送 `v*` Git 标签后，Actions 会在 GHCR 多架构镜像发布成功后自动创建同名 GitHub Release，并上传：

- `opencode-linux-amd64.tar`：Intel / AMD x86_64 机器。
- `opencode-linux-arm64.tar`：ARM64 机器。
- `SHA256SUMS`：两份 tar 包的 SHA-256 校验值。
- `image-digest.txt`：本次发布的镜像 digest 和 OpenCode 版本。

先提交本项目及工作流，再创建版本标签：

```bash
git add .
git commit -m "Add Docker image tar assets to Releases"
git push origin main
git tag v1.0.0
git push origin v1.0.0
```

这里 `v1.0.0` 是自定义镜像项目的发行版本；镜像内部 OpenCode 的版本仍由 CI 构建参数控制。
普通 `main` 分支推送继续发布 GHCR，不创建 Release。手动运行工作流时选择已有 `v*` 标签，也会执行 Release 任务。
已有同名 Release 时会更新同名附件；启用了不可变 Release 的仓库应使用新标签发行。

下载适合机器架构的文件后：

```bash
sha256sum -c SHA256SUMS --ignore-missing
docker load -i opencode-linux-amd64.tar
```

ARM64 机器将文件名改为 `opencode-linux-arm64.tar`。
导入后镜像标签为 `ghcr.io/你的用户名/opencode:latest`，可直接配合本项目的 `.env` 使用：

```bash
docker compose up -d --pull never
```

每份 tar 从本次刚发布的 digest 导出，避免下载到被其他构建更新的 `latest`。
这是 `docker save` 的完整镜像归档，可用 `docker load` 导入，包含镜像层和配置。
GitHub Release 任务单独申请 `contents: write` 和 `packages: read`，使用内置 `GITHUB_TOKEN`，无需额外配置 PAT。

## 2. Compose 部署（API + Web UI）

先等 GitHub Actions 成功发布，再在服务器上执行：

```bash
cp .env.example .env
nano .env
mkdir -p workspace
```

修改这些参数：

```dotenv
OPENCODE_IMAGE=ghcr.io/你的用户名/opencode:latest
OPENAI_BASE_URL=https://你的API域名/v1
OPENAI_API_KEY=你的API密钥
OPENCODE_SERVER_USERNAME=opencode
OPENCODE_SERVER_PASSWORD=自己设置的服务密码
BIND_ADDRESS=127.0.0.1
OPENCODE_PORT=4096
```

`OPENAI_API_KEY` 是模型 API 密钥，`OPENCODE_SERVER_PASSWORD` 是访问 OpenCode 服务的密码，两者用途不同。

```bash
docker compose pull
docker compose up -d
docker compose ps
docker compose logs -f opencode
```

默认仅在宿主机 `127.0.0.1:4096` 发布端口。宿主机本地浏览器访问 `http://127.0.0.1:4096`。
从其他内网电脑访问时，可设置 `BIND_ADDRESS=0.0.0.0` 后重新 `docker compose up -d`，
访问 `http://服务器IP:4096`，使用服务用户名和密码认证。

v2 的 `serve` 同时提供 Web UI，无需再执行 v1 的 `opencode web`。

在容器内确认服务状态：

```bash
docker compose exec opencode sh -c 'curl -fsS -u "$OPENCODE_SERVER_USERNAME:$OPENCODE_SERVER_PASSWORD" http://127.0.0.1:4096/api/info'
docker compose exec opencode sh -c 'curl -fsS -u "$OPENCODE_SERVER_USERNAME:$OPENCODE_SERVER_PASSWORD" http://127.0.0.1:4096/api/model'
```

v2 使用 `/api/info`；v1 的 `/global/health` 不适合作为这个版本的健康检查。

需要浏览器一次性配对链接时，可在容器内请求：

```bash
docker compose exec opencode sh -c 'curl -fsS -X POST -u "$OPENCODE_SERVER_USERNAME:$OPENCODE_SERVER_PASSWORD" http://127.0.0.1:4096/api/pair'
```

返回的 `code` 可组成 `http://服务器IP:4096/auth/connect/<code>`。配对码仅使用一次，5 分钟后失效。

更新镜像：

```bash
docker compose pull
docker compose up -d
```

## 3. 本地构建

无需先发布 GHCR，填写 `.env` 后直接：

```bash
docker compose -f compose.yaml -f compose.build.yaml up -d --build
```

构建结果为 `opencode-local:latest`。

也可以单独构建和测试：

```bash
docker build --pull -t opencode-local:latest .
docker run --rm opencode-local:latest python /opt/opencode/smoke.py
```

GitHub 构建阶段默认使用 npm 官方源，运行时仍使用 npmmirror。
国内本地构建可以在 `.env` 中设：

```dotenv
BUILD_NPM_REGISTRY=https://registry.npmmirror.com
```

修改运行时 npm/pip 源的构建参数为 `NPM_REGISTRY`、`PIP_INDEX`；本地 Compose 中通过
`.env` 的 `NPM_REGISTRY`、`PIP_INDEX_URL` 传入。Dockerfile 没有修改 apt 源。

## 4. 交互式 OpenCode CLI

填写 `.env` 的镜像路径和 API 参数后：

```bash
docker compose -f compose.cli.yaml run --rm opencode
```

项目目录是宿主机 `./workspace`，容器内为 `/workspace`。
交互式示例采用独立的配置/数据卷，避免与后台服务混用数据库。
如要临时进入 shell：

```bash
docker compose -f compose.cli.yaml run --rm opencode bash
```

## 5. 配置、插件和数据

镜像默认模板位于 `/opt/opencode/defaults/opencode.json`。
首次启动会创建 `/root/.config/opencode/opencode.json`。
每次启动会把 `.env` 的 `OPENAI_BASE_URL`、`OPENAI_API_KEY` 应用到 `providers.gateway.settings`；
其他已有设置保留。运行时 JSON 可能包含 API Key，文件权限设为 `0600`，保存在配置卷中。

编辑持久化配置：

```bash
docker compose exec opencode nano /root/.config/opencode/opencode.json
docker compose restart opencode
```

只要保留 `gateway` provider，环境变量就会覆盖它的 `baseURL` 和 `apiKey`。
如自行管理整个配置，可放置 `opencode.jsonc`，初始化脚本不会修改它；此时请自行填写 API 地址，
不要同时保留 JSON 和 JSONC。原生 v2 配置支持的 API Key 环境引用与各字段的解析方式可能不同，
本项目通过初始化脚本明确写入网关地址和密钥，避免把 `${OPENAI_BASE_URL}` 当成实际 URL。

插件位于：

```text
/opt/opencode/plugins/node_modules/opencode-models-discovery/dist
```

模板的 `plugins` 使用这个目录的 `file://` URI。v2 本地插件应引用目录，
加载器会选用 `server.js`。不需要再次 `opencode plugin add`，也不会因为挂载空的 config/cache 卷隐藏这个插件。
不要再添加同一插件的 npm 名称，否则可能重复加载。

默认模型发现端点是域名根下的 `/v1/models`，不是任意 `baseURL` 路径后拼接 `/models`。
如果模型接口为 `/models`，修改 `modelsDiscovery.endpoint`；如果是 `/api/v1/models`，写这个完整路径。
默认不配置 `modelInfoFormat` 或 `smartModelName`，插件不主动请求额外模型元数据服务；
OpenCode 自身仍可能访问 `models.dev` 等站点，本项目不承诺完全离线运行。

也可显式添加模型或默认模型，例如在根级配置添加：

```json
"model": "gateway/你的模型ID"
```

四个 named volumes 分别保存配置、缓存、会话/认证数据和状态。
`docker compose down` 保留它们；`docker compose down -v` 会删除它们。

## 6. Python 与 pip

默认 PATH 已启用 Python 3.11 虚拟环境，不受 Debian 系统 Python 的 PEP 668 限制。

```bash
docker compose exec opencode python --version
docker compose exec opencode pip --version
docker compose exec opencode pip config list
docker compose exec opencode pip install requests
docker compose exec opencode npm config get registry
```

容器内临时安装的软件会随容器重建消失。需要长期内置 Python 库时，在 Dockerfile
创建虚拟环境之后添加 `RUN pip install ...`，重新构建镜像。

## 7. 版本更新和定时构建

默认固定 OpenCode `2.0.22` 和插件 `1.6.1`。
Actions 的 **Run workflow** 支持填写新的 `2.x.y` 版本或 `latest`。
工作流先将 npm tag 解析为准确的 v2 版本，再作为构建参数传入，避免缓存把旧的 `@latest` 安装层一直复用。

长期修改 CI 默认版本，可在仓库 **Settings → Secrets and variables → Actions → Variables**
添加 `OPENCODE_VERSION`，例如 `2.0.22` 或 `latest`。
本地构建版本通过 `.env` 的 `OPENCODE_VERSION` 修改。

工作流的 daily `schedule` 默认注释；需要每天重建时取消注释。
示例时间为 UTC 18:17，即 UTC+8 次日 02:17，定时事件默认解析最新 v2。
Fork 仓库可能需要在 Actions 页面单独启用定时工作流。

插件依赖更新流程：

```bash
cd plugins
npm install --save-exact opencode-models-discovery@新的版本
cd ..
git add plugins/package.json plugins/package-lock.json
git commit -m "Update model discovery plugin"
git push
```

## 官方参考

- [OpenCode v2 安装](https://opencode.ai/v2/docs/)
- [OpenCode v2 配置](https://opencode.ai/v2/docs/config/)
- [OpenCode v2 Web 与前台服务](https://opencode.ai/v2/docs/cli/web/)
- [OpenCode v2 插件](https://opencode.ai/v2/docs/plugins/)
- [模型发现插件文档](https://github.com/yuhp/opencode-models-discovery)
- [GitHub Container Registry](https://docs.github.com/en/packages/working-with-a-github-packages-registry/working-with-the-container-registry)
