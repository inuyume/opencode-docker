#!/usr/bin/env python3
"""Initialize global config and apply environment settings for the gateway."""
import argparse
import json
import os
from pathlib import Path
from urllib.parse import urlparse


def configure(template: Path, config_dir: Path):
    config_dir.mkdir(parents=True, exist_ok=True)
    target = config_dir / 'opencode.json'
    if (config_dir / 'opencode.jsonc').exists():
        return  # JSONC is explicitly user managed.
    document = json.loads((target if target.exists() else template).read_text())
    gateway = document.get('providers', {}).get('gateway')
    if isinstance(gateway, dict):
        settings = gateway.setdefault('settings', {})
        url = os.environ.get('OPENAI_BASE_URL')
        if url:
            parsed = urlparse(url)
            if parsed.scheme not in ('http', 'https') or not parsed.netloc:
                raise ValueError('OPENAI_BASE_URL must be an absolute HTTP(S) URL')
            settings['baseURL'] = url
        if os.environ.get('OPENAI_API_KEY'):
            settings['apiKey'] = os.environ['OPENAI_API_KEY']
    # Atomic replacement; the runtime file may contain the gateway API key.
    temporary = config_dir / '.opencode.json.tmp'
    fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, 'w') as stream:
        json.dump(document, stream, ensure_ascii=False, indent=2)
        stream.write('\n')
    os.chmod(temporary, 0o600)
    os.replace(temporary, target)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('template', type=Path)
    parser.add_argument('config_dir', type=Path)
    args = parser.parse_args()
    configure(args.template, args.config_dir)
