# syntax=docker/dockerfile:1
FROM node:22-bookworm-slim AS runtime

ARG OPENCODE_VERSION=2.0.22
ARG BUILD_NPM_REGISTRY=https://registry.npmjs.org
ARG NPM_REGISTRY=https://registry.npmmirror.com
ARG PIP_INDEX=https://pypi.tuna.tsinghua.edu.cn/simple

ENV NPM_CONFIG_REGISTRY=${NPM_REGISTRY} \
    PIP_INDEX_URL=${PIP_INDEX} \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    VIRTUAL_ENV=/opt/venv \
    PATH="/opt/venv/bin:${PATH}"

RUN apt-get update \
    && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
       python3.11 python3.11-venv python3-pip \
       git curl wget ca-certificates openssh-client \
       build-essential bash jq ripgrep unzip zip less nano \
       procps iproute2 dnsutils tini \
    && python3.11 -m venv /opt/venv \
    && python -c 'import sys; assert sys.version_info[:2] == (3, 11)' \
    && rm -rf /var/lib/apt/lists/*

# Build on GitHub with the official registry; retain mirrors for runtime.
RUN npm install --global "@opencode/cli@${OPENCODE_VERSION}" \
       --registry="${BUILD_NPM_REGISTRY}" --no-audit --no-fund \
    && opencode --version \
    && npm cache clean --force

WORKDIR /opt/opencode/plugins
COPY plugins/package.json plugins/package-lock.json ./
RUN npm ci --omit=dev --registry="${BUILD_NPM_REGISTRY}" --no-audit --no-fund \
    && test -f node_modules/opencode-models-discovery/dist/server.js \
    && npm cache clean --force

RUN npm config set registry "${NPM_REGISTRY}" --location=global \
    && printf '[global]\nindex-url = %s\n' "${PIP_INDEX}" > /etc/pip.conf \
    && printf '[install]\nregistry = "%s"\n' "${NPM_REGISTRY}" > /root/.bunfig.toml \
    && mkdir -p /root/.config/opencode /root/.cache/opencode \
                /root/.local/share/opencode /root/.local/state/opencode /workspace

COPY opencode.json /opt/opencode/defaults/opencode.json
COPY docker/entrypoint.sh /usr/local/bin/docker-entrypoint.sh
COPY docker/configure.py /opt/opencode/configure.py
COPY scripts/smoke.py /opt/opencode/smoke.py
RUN chmod 755 /usr/local/bin/docker-entrypoint.sh

WORKDIR /workspace
EXPOSE 4096
ENTRYPOINT ["/usr/bin/tini", "--", "/usr/local/bin/docker-entrypoint.sh"]
CMD ["opencode", "serve", "--hostname", "0.0.0.0", "--port", "4096"]
