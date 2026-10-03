#!/usr/bin/env python3
"""Exercise the actual v2 server and discovery plugin without calling a paid model."""
import argparse
import base64
import json
import os
from pathlib import Path
import socket
import subprocess
import tempfile
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.error import HTTPError
from urllib.request import Request, build_opener, ProxyHandler


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--binary', default='opencode')
    parser.add_argument('--template', default='/opt/opencode/defaults/opencode.json')
    parser.add_argument('--plugin-dir', default='/opt/opencode/plugins/node_modules/opencode-models-discovery/dist')
    parser.add_argument('--configure', default='/opt/opencode/configure.py')
    args = parser.parse_args()
    version = subprocess.check_output([args.binary, '--version'], text=True).strip()
    assert '2.' in version, version
    mock_requests = []

    class ModelsHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            mock_requests.append((self.path, self.headers.get('Authorization')))
            if self.path != '/v1/models' or self.headers.get('Authorization') != 'Bearer smoke-api-key':
                self.send_error(404)
                return
            body = json.dumps({'object': 'list', 'data': [{'id': 'smoke-model', 'object': 'model'}]}).encode()
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *_):
            pass

    mock = ThreadingHTTPServer(('127.0.0.1', 0), ModelsHandler)
    threading.Thread(target=mock.serve_forever, daemon=True).start()
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        port = sock.getsockname()[1]
    opener = build_opener(ProxyHandler({}))
    auth = base64.b64encode(b'opencode:smoke-server-password').decode()
    with tempfile.TemporaryDirectory(prefix='opencode-v2-smoke-') as directory:
        root = Path(directory)
        env = os.environ.copy()
        for key, name in [('XDG_CONFIG_HOME', 'config'), ('XDG_DATA_HOME', 'data'),
                          ('XDG_CACHE_HOME', 'cache'), ('XDG_STATE_HOME', 'state')]:
            env[key] = str(root / name)
        env.update(OPENAI_BASE_URL=f'http://127.0.0.1:{mock.server_port}/v1',
                   OPENAI_API_KEY='smoke-api-key', OPENCODE_SERVER_PASSWORD='smoke-server-password',
                   OPENCODE_SERVER_USERNAME='opencode', NO_PROXY='localhost,127.0.0.1,::1')
        config = json.loads(Path(args.template).read_text())
        config['plugins'] = [Path(args.plugin_dir).resolve().as_uri()]
        # Run exactly the same config initializer used by the container.
        config_dir = root / 'config' / 'opencode'
        config_dir.mkdir(parents=True)
        template = root / 'template.json'
        template.write_text(json.dumps(config))
        subprocess.run([os.sys.executable, args.configure, str(template), str(config_dir)], env=env, check=True)
        log_path = root / 'server.log'
        with log_path.open('w') as log:
            process = subprocess.Popen([args.binary, 'serve', '--hostname', '127.0.0.1', '--port', str(port)],
                                       cwd=root, env=env, stdout=log, stderr=log)
            try:
                def request(path, authenticated=True):
                    headers = {'Authorization': 'Basic ' + auth} if authenticated else {}
                    with opener.open(Request(f'http://127.0.0.1:{port}' + path, headers=headers), timeout=5) as resp:
                        return json.load(resp)

                deadline = time.monotonic() + 90
                last_error = None
                while time.monotonic() < deadline:
                    if process.poll() is not None:
                        raise RuntimeError('Server exited before readiness')
                    try:
                        info = request('/api/info')
                        assert info['version'].startswith('2.'), info
                        models = request('/api/model')
                        if 'smoke-model' in json.dumps(models):
                            break
                    except Exception as error:
                        last_error = error
                    time.sleep(0.5)
                else:
                    raise RuntimeError(f'Discovery did not finish: {last_error}')

                assert ('/v1/models', 'Bearer smoke-api-key') in mock_requests
                try:
                    request('/api/provider', authenticated=False)
                except HTTPError as error:
                    assert error.code == 401, error.code
                else:
                    raise AssertionError('Server accepted an unauthenticated provider request')
                print(f'PASS: {version}; v2 config, local plugin, env API key, model discovery and HTTP authentication')
            except Exception:
                print(log_path.read_text()[-12000:])
                for error_log in (root / 'data' / 'opencode' / 'log').glob('*.log'):
                    print(error_log.read_text()[-12000:])
                raise
            finally:
                process.terminate()
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
                mock.shutdown()


if __name__ == '__main__':
    main()
