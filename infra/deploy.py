#!/usr/bin/env python3
# Creates the "chatbot" Easypanel project and its 4 services. Reads secrets from .env; never prints them.
import json, os, sys, urllib.request, urllib.error
D = os.path.expanduser("~/projetos/chatbot-infra")
env = dict(l.rstrip("\n").split("=", 1) for l in open(f"{D}/.env") if "=" in l)
TOKEN = env["EASYPANEL_TOKEN"]
P, DOM = "chatbot", "fakvga.easypanel.host"
N8N_HOST, EVO_HOST = f"{P}-n8n.{DOM}", f"{P}-evolution.{DOM}"

def call(op, body):
    req = urllib.request.Request(f"http://localhost:3000/api/{op}", json.dumps(body).encode(),
                                 {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req) as r:
            print(f"{op} {body.get('serviceName', body.get('name',''))}: {r.status}")
    except urllib.error.HTTPError as e:
        msg = e.read().decode()[:300]
        for v in env.values():
            msg = msg.replace(v, "***")
        print(f"{op}: HTTP {e.code} {msg}")
        if "already" not in msg.lower() and "exist" not in msg.lower():
            sys.exit(1)

def res(mem):
    return {"cpuLimit": 0, "cpuReservation": 0, "memoryLimit": mem, "memoryReservation": 0}

def envs(d):
    return "\n".join(f"{k}={v}" for k, v in d.items())

PG, RD = env["POSTGRES_PASSWORD"], env["REDIS_PASSWORD"]
MODE = sys.argv[1] if len(sys.argv) > 1 else "create"
if MODE == "create":
  call("createProject", {"name": P})
  call("createPostgresService", {"projectName": P, "serviceName": "db", "image": "pgvector/pgvector:pg16",
                                 "databaseName": "n8n", "user": "postgres", "password": PG, "resources": res(512)})
  call("createRedisService", {"projectName": P, "serviceName": "redis", "image": "redis:7-alpine",
                            "password": RD, "resources": res(128)})

evo = {
    "SERVER_URL": f"https://{EVO_HOST}", "AUTHENTICATION_API_KEY": env["EVOLUTION_API_KEY"],
    "AUTHENTICATION_EXPOSE_IN_FETCH_INSTANCES": "false", "DEL_INSTANCE": "false", "LANGUAGE": "pt-BR",
    "DATABASE_ENABLED": "true", "DATABASE_PROVIDER": "postgresql",
    "DATABASE_CONNECTION_URI": f"postgresql://postgres:{PG}@{P}_db:5432/evolution?schema=public",
    "DATABASE_CONNECTION_CLIENT_NAME": "evolution", "DATABASE_SAVE_DATA_INSTANCE": "true",
    "DATABASE_SAVE_DATA_NEW_MESSAGE": "false", "DATABASE_SAVE_MESSAGE_UPDATE": "false",
    "DATABASE_SAVE_DATA_CONTACTS": "false", "DATABASE_SAVE_DATA_CHATS": "false",
    "DATABASE_SAVE_DATA_LABELS": "false", "DATABASE_SAVE_DATA_HISTORIC": "false",
    "DATABASE_SAVE_IS_ON_WHATSAPP": "false",
    "CACHE_REDIS_ENABLED": "true", "CACHE_REDIS_URI": f"redis://default:{RD}@{P}_redis:6379/1",
    "CACHE_REDIS_PREFIX_KEY": "evolution", "CACHE_REDIS_SAVE_INSTANCES": "false", "CACHE_LOCAL_ENABLED": "false",
    "CONFIG_SESSION_PHONE_CLIENT": "Atendimento", "CONFIG_SESSION_PHONE_NAME": "Chrome", "QRCODE_LIMIT": "30",
    "LOG_LEVEL": "ERROR,WARN,INFO", "TZ": "America/Sao_Paulo",
}
if MODE == "create":
  call("createAppService", {"projectName": P, "serviceName": "evolution",
     "source": {"type": "image", "image": "evoapicloud/evolution-api:v2.3.7"}, "env": envs(evo),
     "domains": [{"host": EVO_HOST, "https": True, "port": 8080, "path": "/"}],
     "mounts": [{"type": "volume", "name": "evolution-instances", "mountPath": "/evolution/instances"}],
     "resources": res(768)})

n8n = {
    "DB_TYPE": "postgresdb", "DB_POSTGRESDB_HOST": f"{P}_db", "DB_POSTGRESDB_PORT": "5432",
    "DB_POSTGRESDB_DATABASE": "n8n", "DB_POSTGRESDB_USER": "postgres", "DB_POSTGRESDB_PASSWORD": PG,
    "N8N_ENCRYPTION_KEY": env["N8N_ENCRYPTION_KEY"], "N8N_HOST": N8N_HOST, "N8N_PROTOCOL": "https",
    "N8N_PORT": "5678", "WEBHOOK_URL": f"https://{N8N_HOST}/", "N8N_PROXY_HOPS": "1",
    "GENERIC_TIMEZONE": "America/Sao_Paulo", "TZ": "America/Sao_Paulo",
    "N8N_DIAGNOSTICS_ENABLED": "false", "N8N_PERSONALIZATION_ENABLED": "false",
    "N8N_BLOCK_ENV_ACCESS_IN_NODE": "false", "N8N_RUNNERS_ENABLED": "true",
    "EXECUTIONS_DATA_PRUNE": "true", "EXECUTIONS_DATA_MAX_AGE": "168",
    "EVOLUTION_API_KEY": env["EVOLUTION_API_KEY"], "EVOLUTION_URL": f"http://{P}_evolution:8080",
    "WEBHOOK_SECRET": env["WEBHOOK_SECRET"], "QR_PAGE_TOKEN": env["QR_PAGE_TOKEN"],
    "CALCOM_API_KEY": env.get("CALCOM_API_KEY", ""),
    "RESEND_API_KEY": env.get("RESEND_API_KEY", ""), "RESEND_FROM": env.get("RESEND_FROM", ""),
    "EXECUTIONS_DATA_SAVE_ON_SUCCESS": "none", "EXECUTIONS_DATA_SAVE_ON_PROGRESS": "false",
    "CREDENTIALS_OVERWRITE_DATA": json.dumps({
        "anthropicApi": {"apiKey": env["ANTHROPIC_API_KEY"]},
        "openAiApi": {"apiKey": env["OPENAI_API_KEY"]},
        "postgres": {"host": f"{P}_db", "database": "chatbot", "user": "postgres", "password": PG, "port": 5432, "ssl": "disable"},
        "redis": {"host": f"{P}_redis", "port": 6379, "password": RD, "database": 0},
    }, separators=(",", ":")),
}
if MODE == "create":
  call("createAppService", {"projectName": P, "serviceName": "n8n",
     "source": {"type": "image", "image": "n8nio/n8n:2.46.4"}, "env": envs(n8n),
     "domains": [{"host": N8N_HOST, "https": True, "port": 5678, "path": "/"}],
     "mounts": [{"type": "volume", "name": "n8n-data", "mountPath": "/home/node/.n8n"}],
     "resources": res(1024)})
if MODE == "update-n8n":
    call("updateAppEnv", {"projectName": P, "serviceName": "n8n", "env": envs(n8n)})
    call("deployAppService", {"projectName": P, "serviceName": "n8n"})
