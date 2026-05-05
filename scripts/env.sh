#!/usr/bin/env bash

load_env_file() {
  local env_file="$1"
  shift

  [[ -f "$env_file" ]] || return 0

  local line key value wanted
  while IFS= read -r line || [[ -n "$line" ]]; do
    line="${line%$'\r'}"
    [[ -z "$line" || "${line:0:1}" == "#" ]] && continue
    [[ "$line" == *=* ]] || continue

    key="${line%%=*}"
    value="${line#*=}"
    key="${key#"${key%%[![:space:]]*}"}"
    key="${key%"${key##*[![:space:]]}"}"
    key="${key#export }"

    [[ "$key" =~ ^[A-Za-z_][A-Za-z0-9_]*$ ]] || continue

    for wanted in "$@"; do
      if [[ "$key" == "$wanted" ]]; then
        export "$key=$value"
        break
      fi
    done
  done < "$env_file"
}
