"""Configuration extraction engine.

Supports:
- JSON (.json)
- YAML (.yaml, .yml)
- TOML (.toml)
- INI (.ini, .cfg)
- .env.example / .env.sample / .env.template
- Source code environment variable references (e.g. os.getenv, process.env)

Integrates strictly with core/security.py:
- Never exposes real credentials
- Automatic redaction of secret keys and values
- Prevents real .env values from ever reaching outputs
"""

from __future__ import annotations

import configparser
import json
import re
import tomllib
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml
from app.core.security import is_secret_key, redact_config_value
from app.models.analysis import ExtractedConfigFile, ExtractedConfigItem

# Regex to detect os.environ.get('KEY'), os.getenv('KEY'), process.env.KEY, process.env['KEY']
PYTHON_ENV_REF_REGEX = re.compile(
    r"""(?:os\.getenv|os\.environ\.get|os\.environ\[)\s*\(\s*['"]([A-Z0-9_]+)['"]|os\.environ\[['"]([A-Z0-9_]+)['"]\]"""
)
JS_ENV_REF_REGEX = re.compile(
    r"""process\.env\.([A-Z0-9_]+)|process\.env\[['"]([A-Z0-9_]+)['"]\]"""
)


class ConfigEngine:
    """Extracts configuration keys, types, and values safely."""

    def _process_key_value(
        self,
        key: str,
        value: Any,
        rel_path: str,
        line_number: Optional[int] = None,
    ) -> ExtractedConfigItem:
        val_str = str(value) if value is not None else None
        safe_val, is_secret = redact_config_value(key, val_str, filename=rel_path)
        val_type = type(value).__name__ if value is not None else "null"

        return ExtractedConfigItem(
            key=key,
            value_type=val_type,
            default_value=safe_val,
            is_secret=is_secret,
            file_path=rel_path,
            line_number=line_number,
        )

    def extract_json(self, content: str, rel_path: str) -> ExtractedConfigFile:
        try:
            data = json.loads(content)
        except Exception as e:
            return ExtractedConfigFile(file_path=rel_path, format="json", parse_error=f"JSON decode error: {str(e)}")

        items: List[ExtractedConfigItem] = []

        def flatten(obj: Any, prefix: str = ""):
            if isinstance(obj, dict):
                for k, v in obj.items():
                    full_key = f"{prefix}.{k}" if prefix else str(k)
                    if isinstance(v, (dict, list)):
                        flatten(v, full_key)
                    else:
                        items.append(self._process_key_value(full_key, v, rel_path))
            elif isinstance(obj, list):
                for idx, v in enumerate(obj):
                    full_key = f"{prefix}[{idx}]"
                    if isinstance(v, (dict, list)):
                        flatten(v, full_key)
                    else:
                        items.append(self._process_key_value(full_key, v, rel_path))

        flatten(data)
        return ExtractedConfigFile(file_path=rel_path, format="json", items=items)

    def extract_yaml(self, content: str, rel_path: str) -> ExtractedConfigFile:
        try:
            data = yaml.safe_load(content)
        except Exception as e:
            return ExtractedConfigFile(file_path=rel_path, format="yaml", parse_error=f"YAML parse error: {str(e)}")

        items: List[ExtractedConfigItem] = []

        def flatten(obj: Any, prefix: str = ""):
            if isinstance(obj, dict):
                for k, v in obj.items():
                    full_key = f"{prefix}.{k}" if prefix else str(k)
                    if isinstance(v, (dict, list)):
                        flatten(v, full_key)
                    else:
                        items.append(self._process_key_value(full_key, v, rel_path))
            elif isinstance(obj, list):
                for idx, v in enumerate(obj):
                    full_key = f"{prefix}[{idx}]"
                    if isinstance(v, (dict, list)):
                        flatten(v, full_key)
                    else:
                        items.append(self._process_key_value(full_key, v, rel_path))

        if isinstance(data, (dict, list)):
            flatten(data)

        return ExtractedConfigFile(file_path=rel_path, format="yaml", items=items)

    def extract_toml(self, content: str, rel_path: str) -> ExtractedConfigFile:
        try:
            data = tomllib.loads(content)
        except Exception as e:
            return ExtractedConfigFile(file_path=rel_path, format="toml", parse_error=f"TOML parse error: {str(e)}")

        items: List[ExtractedConfigItem] = []

        def flatten(obj: Any, prefix: str = ""):
            if isinstance(obj, dict):
                for k, v in obj.items():
                    full_key = f"{prefix}.{k}" if prefix else str(k)
                    if isinstance(v, dict):
                        flatten(v, full_key)
                    else:
                        items.append(self._process_key_value(full_key, v, rel_path))

        flatten(data)
        return ExtractedConfigFile(file_path=rel_path, format="toml", items=items)

    def extract_ini(self, content: str, rel_path: str) -> ExtractedConfigFile:
        parser = configparser.ConfigParser()
        try:
            parser.read_string(content)
        except Exception as e:
            return ExtractedConfigFile(file_path=rel_path, format="ini", parse_error=f"INI parse error: {str(e)}")

        items: List[ExtractedConfigItem] = []
        for section in parser.sections():
            for k, v in parser.items(section):
                key = f"[{section}].{k}"
                items.append(self._process_key_value(key, v, rel_path))

        return ExtractedConfigFile(file_path=rel_path, format="ini", items=items)

    def extract_env_file(self, content: str, rel_path: str) -> ExtractedConfigFile:
        items: List[ExtractedConfigItem] = []
        lines = content.splitlines()

        for idx, line in enumerate(lines, start=1):
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            if "=" in stripped:
                parts = stripped.split("=", 1)
                k = parts[0].strip()
                v = parts[1].strip()
                # strip enclosing quotes
                if (v.startswith('"') and v.endswith('"')) or (v.startswith("'") and v.endswith("'")):
                    v = v[1:-1]
                items.append(self._process_key_value(k, v, rel_path, line_number=idx))

        return ExtractedConfigFile(file_path=rel_path, format="env_example", items=items)

    def extract_file(self, file_path: Path, rel_path: str) -> Optional[ExtractedConfigFile]:
        """Extracts configuration from a given configuration file."""
        name = file_path.name.lower()
        ext = file_path.suffix.lower()

        try:
            content = file_path.read_text(encoding="utf-8", errors="replace")
        except Exception as e:
            return ExtractedConfigFile(
                file_path=rel_path,
                format="unknown",
                parse_error=f"Failed to read file: {str(e)}",
            )

        if "example" in name or "sample" in name or "template" in name:
            if name.startswith(".env") or name.endswith(".env"):
                return self.extract_env_file(content, rel_path)

        if ext == ".json":
            return self.extract_json(content, rel_path)
        elif ext in {".yaml", ".yml"}:
            return self.extract_yaml(content, rel_path)
        elif ext == ".toml":
            return self.extract_toml(content, rel_path)
        elif ext in {".ini", ".cfg"}:
            return self.extract_ini(content, rel_path)
        elif name in {".env.example", ".env.sample", ".env.template", ".env.dist"}:
            return self.extract_env_file(content, rel_path)

        return None

    def scan_source_code_env_refs(self, source_content: str, language: str) -> List[str]:
        """Scans Python and JavaScript code for referenced environment variable keys."""
        refs: set[str] = set()
        if language == "python":
            for m in PYTHON_ENV_REF_REGEX.finditer(source_content):
                k = m.group(1) or m.group(2)
                if k:
                    refs.add(k)
        elif language == "javascript":
            for m in JS_ENV_REF_REGEX.finditer(source_content):
                k = m.group(1) or m.group(2)
                if k:
                    refs.add(k)
        return sorted(list(refs))


config_engine = ConfigEngine()
