from __future__ import annotations

import copy
import datetime as dt
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[5]
SEEDS_DIR = ROOT / "seeds" / "i18n"


class AdminService:
    def __init__(self) -> None:
        self.glossaries: dict[str, dict[str, Any]] = {}
        self.glossary_versions: dict[str, list[dict[str, Any]]] = {}
        self.templates: dict[str, dict[str, Any]] = {}
        self.template_versions: dict[str, list[dict[str, Any]]] = {}
        self.audit_log: list[dict[str, Any]] = []
        self._init_from_seeds()

    def _init_from_seeds(self) -> None:
        # Load English and Hindi glossaries
        for lang in ("en", "hi"):
            g_path = SEEDS_DIR / f"glossary.{lang}.yaml"
            if g_path.exists():
                try:
                    with g_path.open("r", encoding="utf-8") as f:
                        data = yaml.safe_load(f) or {}
                        self.glossaries[lang] = data
                        self.glossary_versions[lang] = [copy.deepcopy(data)]
                except Exception:
                    self.glossaries[lang] = {"terms": {}}
                    self.glossary_versions[lang] = [copy.deepcopy(self.glossaries[lang])]
            else:
                self.glossaries[lang] = {"terms": {}}
                self.glossary_versions[lang] = [copy.deepcopy(self.glossaries[lang])]

        # Load Alert templates
        t_path = SEEDS_DIR / "alert-templates.yaml"
        initial_templates: dict[str, Any] = {}
        if t_path.exists():
            try:
                with t_path.open("r", encoding="utf-8") as f:
                    initial_templates = yaml.safe_load(f) or {}
            except Exception:
                initial_templates = {}

        for lang in ("en", "hi"):
            self.templates[lang] = copy.deepcopy(initial_templates)
            self.template_versions[lang] = [copy.deepcopy(initial_templates)]

    def get_glossary(self, lang: str) -> dict[str, Any]:
        return self.glossaries.get(lang, {"terms": {}})

    def update_glossary(self, lang: str, editor: str, terms: dict[str, str]) -> dict[str, Any]:
        before = copy.deepcopy(self.get_glossary(lang))
        current = self.glossaries.setdefault(lang, {"terms": {}})
        if "terms" not in current or not isinstance(current["terms"], dict):
            current["terms"] = {}

        current["terms"].update(terms)
        after = copy.deepcopy(current)

        # Version history
        v_list = self.glossary_versions.setdefault(lang, [])
        v_list.append(copy.deepcopy(current))
        version_num = len(v_list)

        # Write audit log
        entry = {
            "id": len(self.audit_log) + 1,
            "who": editor,
            "what": "update_glossary",
            "target": "glossary",
            "language": lang,
            "when": dt.datetime.now(dt.timezone.utc).isoformat(),
            "before": before,
            "after": after,
            "version": version_num,
        }
        self.audit_log.append(entry)

        return {
            "success": True,
            "version": version_num,
            "language": lang,
            "terms": current["terms"],
        }

    def get_templates(self, lang: str) -> dict[str, Any]:
        return self.templates.get(lang, {})

    def update_template(
        self,
        lang: str,
        editor: str,
        hazard: str,
        severity: str,
        template_text: str,
        reviewer: str | None = None,
    ) -> dict[str, Any]:
        if not reviewer or not reviewer.strip():
            raise ValueError("Reviewer name required for human sign-off on template updates")

        before = copy.deepcopy(self.get_templates(lang))
        current = self.templates.setdefault(lang, {})

        key = f"{hazard}.{severity}"
        current[key] = {
            "text": template_text,
            "reviewer": reviewer.strip(),
            "updated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        }
        after = copy.deepcopy(current)

        v_list = self.template_versions.setdefault(lang, [])
        v_list.append(copy.deepcopy(current))
        version_num = len(v_list)

        entry = {
            "id": len(self.audit_log) + 1,
            "who": editor,
            "what": "update_template",
            "target": "template",
            "language": lang,
            "reviewer": reviewer.strip(),
            "when": dt.datetime.now(dt.timezone.utc).isoformat(),
            "before": before,
            "after": after,
            "version": version_num,
        }
        self.audit_log.append(entry)

        return {
            "success": True,
            "version": version_num,
            "language": lang,
            "key": key,
            "template": current[key],
            "reviewer": reviewer.strip(),
        }

    def rollback(self, target: str, lang: str, target_version: int, editor: str) -> dict[str, Any]:
        if target == "glossary":
            v_list = self.glossary_versions.get(lang, [])
            if target_version < 1 or target_version > len(v_list):
                raise ValueError(f"Version {target_version} does not exist for glossary '{lang}'")
            before = copy.deepcopy(self.glossaries.get(lang, {}))
            restored = copy.deepcopy(v_list[target_version - 1])
            self.glossaries[lang] = restored
            after = copy.deepcopy(restored)

            v_list.append(copy.deepcopy(restored))
            new_v = len(v_list)

            entry = {
                "id": len(self.audit_log) + 1,
                "who": editor,
                "what": "rollback_glossary",
                "target": "glossary",
                "language": lang,
                "when": dt.datetime.now(dt.timezone.utc).isoformat(),
                "before": before,
                "after": after,
                "version": new_v,
            }
            self.audit_log.append(entry)
            return {"success": True, "target": target, "version": new_v}

        elif target == "template":
            v_list = self.template_versions.get(lang, [])
            if target_version < 1 or target_version > len(v_list):
                raise ValueError(f"Version {target_version} does not exist for template '{lang}'")
            before = copy.deepcopy(self.templates.get(lang, {}))
            restored = copy.deepcopy(v_list[target_version - 1])
            self.templates[lang] = restored
            after = copy.deepcopy(restored)

            v_list.append(copy.deepcopy(restored))
            new_v = len(v_list)

            entry = {
                "id": len(self.audit_log) + 1,
                "who": editor,
                "what": "rollback_template",
                "target": "template",
                "language": lang,
                "when": dt.datetime.now(dt.timezone.utc).isoformat(),
                "before": before,
                "after": after,
                "version": new_v,
            }
            self.audit_log.append(entry)
            return {"success": True, "target": target, "version": new_v}

        else:
            raise ValueError(f"Unknown target for rollback: {target}")

    def get_audit_log(self) -> list[dict[str, Any]]:
        return self.audit_log

    def get_language_dashboard(self) -> dict[str, Any]:
        """Returns per-language status and latest evaluation quality metrics."""
        import json

        lang_config_path = ROOT / "config" / "languages.yaml"
        languages_meta = []
        if lang_config_path.exists():
            try:
                with lang_config_path.open("r", encoding="utf-8") as f:
                    data = yaml.safe_load(f) or {}
                    languages_meta = data.get("languages", [])
            except Exception:
                pass

        eval_dir = ROOT / "eval" / "results"
        latest_evals: dict[str, dict[str, Any]] = {}
        if eval_dir.exists():
            for report in sorted(eval_dir.glob("*.json")):
                try:
                    with report.open("r", encoding="utf-8") as f:
                        ev_data = json.load(f)
                        l_code = ev_data.get("language")
                        if l_code:
                            latest_evals[l_code] = {
                                "total": ev_data.get("total", 0),
                                "passed": ev_data.get("passed", 0),
                                "accuracy": ev_data.get("accuracy", 1.0),
                                "timestamp": ev_data.get("timestamp"),
                            }
                except Exception:
                    pass

        dashboard = []
        for item in languages_meta:
            code = item["code"]
            ev = latest_evals.get(code, {})
            dashboard.append({
                "code": code,
                "name": item.get("native_name", code),
                "english_name": item.get("english_name", code),
                "tier": item.get("tier", 2),
                "enabled": item.get("enabled", False),
                "asr_provider": item.get("asr_provider", "bhashini"),
                "tts_provider": item.get("tts_provider", "bhashini"),
                "eval_total": ev.get("total", 0),
                "eval_passed": ev.get("passed", 0),
                "eval_accuracy": ev.get("accuracy", 0.0),
                "last_evaluated": ev.get("timestamp"),
                "native_signoff_status": "signed-off" if code in ("en", "hi") else "draft-pending-human-signoff",
            })

        return {"languages": dashboard, "generated_at": dt.datetime.now(dt.timezone.utc).isoformat()}


admin_service = AdminService()
