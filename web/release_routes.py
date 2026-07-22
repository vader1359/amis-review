from __future__ import annotations

import json
from http.client import HTTPException
from datetime import datetime
from typing import Any
from urllib.error import HTTPError

from psi_engine import PsiReleaseService, ReleaseGateError, ReleaseRequest
from psi_engine.persistence import SupabaseRepository, UploadAuthorizationError, UploadValidationError, week_to_period


def _is_month(value: str) -> bool:
    try:
        return datetime.strptime(value, "%Y-%m").strftime("%Y-%m") == value
    except ValueError:
        return False


def _is_week(value: str) -> bool:
    try:
        week_to_period(value)
    except ValueError:
        return False
    return True


class ReleaseRoutesMixin:
    def release(self) -> None:
        token = self.headers.get("Authorization", "").removeprefix("Bearer ").strip()
        configured = isinstance(self.store.repository, SupabaseRepository)
        if configured:
            try:
                actor_id = self.store.repository.authenticated_actor(token)
            except UploadAuthorizationError:
                self.send(401, b"unauthorized", "text/plain")
                return
            memberships = self.store.repository.lookup("team_memberships", {"profile_id": actor_id}, token)
            if not memberships:
                self.send(403, b"team membership is required", "text/plain")
                return
            actor = (actor_id, str(memberships[0]["team_id"]))
        else:
            actor = self._actor()
        if actor is None:
            self.send(401, b"unauthorized", "text/plain")
            return
        if not configured and self.roles.get(token, "viewer") != "admin":
            self.send(403, b"admin role required", "text/plain")
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            payload: Any = json.loads(self.rfile.read(length).decode("utf-8"))
            period = payload["reporting_period"]
            month_valid = isinstance(period, str) and period and _is_month(period)
            week_valid = isinstance(period, str) and "-W" in period and _is_week(period)
            if not month_valid and not week_valid:
                raise ValueError("reporting_period is invalid")
            if "approve" in payload:
                raise ValueError("approve is no longer supported; PSI Final.xlsx is generated directly")
            request = ReleaseRequest(period, actor[0], actor[1])
            record = self.release_service.generate(request, token)
        except ReleaseGateError as error:
            reasons = [reason for reason in error.reasons if reason]
            self.send(400, json.dumps({"error": "release_gate_blocked", "reasons": reasons}, ensure_ascii=False).encode(), "application/json")
            return
        except (KeyError, TypeError, ValueError, UnicodeDecodeError) as error:
            self.send(400, json.dumps({"error": "invalid_release_request", "message": str(error)}, ensure_ascii=False).encode(), "application/json")
            return
        except (HTTPError, HTTPException, OSError, UploadValidationError) as error:
            self.send(502, json.dumps({"error": "release_failed", "message": str(error)}, ensure_ascii=False).encode(), "application/json")
            return
        self.send(201, json.dumps(record.to_json(), ensure_ascii=False).encode(), "application/json")
