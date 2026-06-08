#!/usr/bin/env sh
# Writes the resource endpoints emitted by `azd provision` into the local
# .env file so the gateway and tests pick them up automatically.
set -eu

ENV_FILE="${ENV_FILE:-.env}"
echo "[postprovision] Updating $ENV_FILE from azd outputs..."

set_env_var() {
  key="$1"
  value="$2"
  if [ -z "$value" ]; then
    return 0
  fi
  if grep -q "^${key}=" "$ENV_FILE" 2>/dev/null; then
    # macOS/BSD vs GNU sed: use -i'' for portability.
    case "$(uname)" in
      Darwin) sed -i '' "s|^${key}=.*|${key}=${value}|" "$ENV_FILE" ;;
      *) sed -i "s|^${key}=.*|${key}=${value}|" "$ENV_FILE" ;;
    esac
  else
    printf '%s=%s\n' "$key" "$value" >> "$ENV_FILE"
  fi
}

# azd exports outputs as AZURE_<UPPERCASE_OUTPUT_NAME> env vars during hooks.
set_env_var FOUNDRY_PROJECT_ENDPOINT "${AZURE_FOUNDRY_PROJECT_ENDPOINT:-}"
set_env_var AZURE_SEARCH_ENDPOINT     "${AZURE_SEARCH_ENDPOINT:-}"
set_env_var AZURE_KEYVAULT_URI        "${AZURE_KEY_VAULT_URI:-}"
set_env_var AZURE_COSMOS_ENDPOINT     "${AZURE_COSMOS_ENDPOINT:-}"
set_env_var APPLICATIONINSIGHTS_CONNECTION_STRING "${AZURE_APP_INSIGHTS_CONNECTION_STRING:-}"

echo "[postprovision] Done."
