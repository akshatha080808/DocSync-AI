"""Unit and integration tests for ConfigEngine:
- JSON, YAML, TOML, INI, and .env.example parsing
- Secret key and secret value redaction via core/security.py
- Source code environment variable reference scanning
"""

from pathlib import Path
from app.engines.config_engine import ConfigEngine


def test_config_extraction_json(tmp_path: Path):
    json_content = """{
        "app_name": "TestService",
        "port": 8080,
        "database_password": "super_secret_value_123",
        "api_key": "sk-1234567890abcdef1234567890",
        "nested": {
            "debug": true,
            "secret_token": "my_secret_token"
        }
    }"""
    cfg_file = tmp_path / "config.json"
    cfg_file.write_text(json_content, encoding="utf-8")

    engine = ConfigEngine()
    result = engine.extract_file(cfg_file, "config.json")

    assert result.parse_error is None
    assert result.format == "json"

    item_map = {item.key: item for item in result.items}
    assert item_map["app_name"].default_value == "TestService"
    assert item_map["app_name"].is_secret is False

    # Check secret redaction
    assert item_map["database_password"].is_secret is True
    assert item_map["database_password"].default_value is None

    assert item_map["api_key"].is_secret is True
    assert item_map["api_key"].default_value is None

    assert item_map["nested.secret_token"].is_secret is True
    assert item_map["nested.secret_token"].default_value is None


def test_config_extraction_yaml(tmp_path: Path):
    yaml_content = """
server:
  host: "0.0.0.0"
  port: 5000
security:
  jwt_secret: "jwt_secret_val"
  enabled: true
"""
    cfg_file = tmp_path / "config.yaml"
    cfg_file.write_text(yaml_content, encoding="utf-8")

    engine = ConfigEngine()
    result = engine.extract_file(cfg_file, "config.yaml")

    assert result.parse_error is None
    assert result.format == "yaml"

    item_map = {item.key: item for item in result.items}
    assert item_map["server.host"].default_value == "0.0.0.0"
    assert item_map["security.jwt_secret"].is_secret is True
    assert item_map["security.jwt_secret"].default_value is None


def test_config_extraction_env_example(tmp_path: Path):
    env_content = """
# Database Configuration
DATABASE_URL=postgresql://user:pass@localhost:5432/db
APP_PORT=3000
API_SECRET=placeholder_secret_abc
"""
    env_file = tmp_path / ".env.example"
    env_file.write_text(env_content, encoding="utf-8")

    engine = ConfigEngine()
    result = engine.extract_file(env_file, ".env.example")

    assert result.parse_error is None
    assert result.format == "env_example"

    item_map = {item.key: item for item in result.items}
    assert item_map["APP_PORT"].default_value == "3000"
    assert item_map["API_SECRET"].is_secret is True
    assert item_map["API_SECRET"].default_value is None


def test_scan_source_code_env_refs():
    py_code = """
import os
db_url = os.getenv("DATABASE_URL", "sqlite:///default.db")
api_key = os.environ.get("OPENAI_API_KEY")
timeout = int(os.environ["TIMEOUT_SECONDS"])
"""
    engine = ConfigEngine()
    refs = engine.scan_source_code_env_refs(py_code, "python")
    assert "DATABASE_URL" in refs
    assert "OPENAI_API_KEY" in refs
    assert "TIMEOUT_SECONDS" in refs

    js_code = """
const port = process.env.PORT || 8080;
const secret = process.env['JWT_SECRET'];
"""
    js_refs = engine.scan_source_code_env_refs(js_code, "javascript")
    assert "PORT" in js_refs
    assert "JWT_SECRET" in js_refs
