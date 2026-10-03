#!/bin/sh
set -eu

config_dir="${XDG_CONFIG_HOME:-${HOME}/.config}/opencode"
python /opt/opencode/configure.py /opt/opencode/defaults/opencode.json "$config_dir"

exec "$@"
