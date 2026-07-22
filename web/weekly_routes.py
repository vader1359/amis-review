from __future__ import annotations

import json
from email.parser import BytesParser
from urllib.error import HTTPError
from email.policy import default
from urllib.parse import parse_qs, urlsplit

from psi_engine.persistence import (
    PsiMemoryRepository,
    SupabaseRepository,
    UploadAuthorizationError,
    UploadRequest,
    UploadValidationError,
    week_to_period,
)


class WeeklyRoutesMixin:
    def weekly_status(self) -> None:
        query = self._query()
        try:
            payload = self.store.weekly_status(query.get("team", query.get("team_id"))[0], query["week"][0])
        except (KeyError, UploadValidationError) as error:
            self.send(400, str(error).encode(), "text/plain")
            return
        self.send(200, json.dumps(payload, ensure_ascii=False).encode(), "application/json")

    def persist_upload(self) -> None:
        token = self.headers.get("Authorization", "").removeprefix("Bearer ").strip()
        if isinstance(self.store.repository, SupabaseRepository):
            try:
                actor = (self.store.repository.authenticated_actor(token), "")
            except UploadAuthorizationError:
                self.send(401, b"authenticated bearer is required for Supabase uploads", "text/plain")
                return
        else:
            actor = self._actor()
            if actor is None or self.roles.get(token) != "contributor":
                actor = ("anonymous-uploader", "")
        content_type = self.headers.get("Content-Type", "")
        if not content_type.lower().startswith("multipart/form-data") or "boundary=" not in content_type:
            self.send(400, b"multipart/form-data with boundary is required", "text/plain")
            return
        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length)
        boundary = content_type.split("boundary=", 1)[1].split(";", 1)[0].strip().encode()
        if not body.rstrip().endswith(b"--" + boundary + b"--"):
            self.send(400, b"multipart body is truncated", "text/plain")
            return
        message = BytesParser(policy=default).parsebytes(b"Content-Type: " + content_type.encode() + b"\r\n\r\n" + body)
        fields: dict[str, str] = {}
        uploaded: tuple[str, str, bytes] | None = None
        for part in message.iter_parts():
            field = part.get_param("name", header="content-disposition") or ""
            filename = part.get_filename()
            if filename:
                uploaded = (filename, part.get_content_type(), part.get_payload(decode=True))
                continue
            payload = part.get_payload(decode=True)
            if payload is None:
                self.send(400, b"malformed multipart field", "text/plain")
                return
            fields[field] = payload.decode("utf-8")
        if uploaded is None:
            self.send(400, b"file is required", "text/plain")
            return
        filename, file_type, content = uploaded
        try:
            week = fields.get("week", fields.get("reporting_period", ""))
            _, week_end = week_to_period(week) if "-W" in week else (week, fields["data_as_of"])
            persisted = self.store.persist(
                UploadRequest(
                    team_id=fields["team_id"], actor_id=actor[0], reporting_period=week,
                    data_as_of=fields.get("data_as_of") or week_end, source_type=fields["source_type"],
                    filename=filename, content=content, content_type=file_type,
                ),
                auth_token=token,
            )
        except KeyError:
            self.send(400, b"required metadata is missing", "text/plain")
            return
        except UploadAuthorizationError as error:
            self.send(403, str(error).encode(), "text/plain")
            return
        except HTTPError as error:
            if error.code in (401, 403):
                self.send(403, b"Supabase persistence is not authorized", "text/plain")
            else:
                self.send(502, b"Supabase persistence request failed", "text/plain")
            return
        except UploadValidationError as error:
            self.send(400, str(error).encode(), "text/plain")
            return
        self.send(201, json.dumps(persisted.to_json(), ensure_ascii=False).encode(), "application/json")

    def _query(self) -> dict[str, list[str]]:
        return parse_qs(urlsplit(self.path).query)
