"""
diff_preview._mixin_core — Core public API mixin for DiffPreviewEngine.
"""

from __future__ import annotations

import json
import logging
import os
import sqlite3
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from src.core.executors.db_journal import DBTransactionJournal

from src.core.executors.diff_preview._helpers import (
    build_db_summary,
    count_placeholders_in_set,
    estimate_risk_from_diffs,
    extract_where_clause,
    parse_insert_columns,
    parse_set_fields,
    truncate,
)
from src.core.executors.diff_preview._helpers import (
    retry as _retry,
)
from src.core.executors.diff_preview._types import DiffEntry, DiffResult

# ── Row data type ─────────────────────────────────────────────
RowData = dict[str, str | int | float | None]
SQLParams = list[str | int | float | None]

logger = logging.getLogger(__name__)


class CoreMixin:
    """Mixin providing core diff computation methods."""

    # These attributes are provided by the main class.
    _lock: object
    _db_journal: DBTransactionJournal | None
    _preview_count: int

    # ── Lazy dependencies ──────────────────────────────────────

    @property
    def db_journal(self) -> DBTransactionJournal:
        """Lazy-load the DBTransactionJournal singleton."""
        if self._db_journal is None:
            from src.core.executors.db_journal import get_db_journal

            self._db_journal = get_db_journal()
        return self._db_journal

    # ── Core API ───────────────────────────────────────────────

    def preview_diff(
        self,
        action_type: str,
        config: dict[str, Any],
        context: dict[str, Any] | None = None,
    ) -> DiffResult:
        """Compute a before/after diff for the given action."""
        with self._lock:
            self._preview_count += 1
            context = context or {}
            action_lower = action_type.lower()

            if action_lower in ("database", "db", "database_operation"):
                return self._diff_db(config, context)
            elif action_lower in ("file", "file_operation"):
                return self._diff_file(config, context)
            elif action_lower in ("email", "send_email"):
                return self._diff_email(config, context)
            else:
                return self._diff_generic(action_type, config, context)

    # ── DB diff ────────────────────────────────────────────────

    def _diff_db(
        self,
        config: dict[str, Any],
        context: dict[str, Any],
    ) -> DiffResult:
        """Compute a diff for a database operation."""
        diffs: list[DiffEntry] = []
        affected_tables: list[str] = []

        db_path = config.get("db_path", ":memory:")
        operation = str(config.get("operation", "query")).upper()
        query = config.get("query", "")
        table = config.get("table", "")
        raw_params = config.get("params", [])

        if not isinstance(raw_params, (list, tuple)):
            raw_params = [raw_params] if raw_params else []
        params: SQLParams = list(raw_params)

        if table:
            affected_tables.append(table)

        current_rows: list[RowData] = []
        if table and db_path != ":memory:" and operation in ("DELETE", "UPDATE"):
            try:
                current_rows = self._fetch_current_rows(
                    db_path,
                    operation,
                    query,
                    params,
                    table,
                )
            except Exception as exc:
                logger.debug(
                    "DiffPreviewEngine: could not fetch current rows for %s: %s",
                    operation,
                    exc,
                )

        if operation == "DELETE":
            for row_idx, row in enumerate(current_rows):
                for col_name, col_value in row.items():
                    diffs.append(
                        DiffEntry(
                            field_path=f"{table}.{col_name}[row{row_idx}]",
                            old_value=col_value,
                            new_value=None,
                            change_type="removed",
                        )
                    )

        elif operation == "UPDATE":
            set_fields = parse_set_fields(query)
            count_placeholders_in_set(query)
            if current_rows and set_fields:
                for row_idx, row in enumerate(current_rows[:1]):
                    for field_name, proposed_value in set_fields:
                        current_value = row.get(field_name)
                        changed = current_value != proposed_value
                        change_type = "modified" if current_value is not None else "added"
                        diffs.append(
                            DiffEntry(
                                field_path=f"{table}.{field_name}[row{row_idx}]",
                                old_value=current_value,
                                new_value=proposed_value,
                                change_type=change_type if changed else "modified",
                            )
                        )

        elif operation == "INSERT":
            insert_cols = parse_insert_columns(query)
            for idx, col_name in enumerate(insert_cols):
                value = params[idx] if idx < len(params) else None
                diffs.append(
                    DiffEntry(
                        field_path=f"{table}.{col_name}",
                        old_value=None,
                        new_value=value,
                        change_type="added",
                    )
                )

        risk = estimate_risk_from_diffs(diffs, operation)
        summary = build_db_summary(operation, table, len(current_rows), diffs)

        return DiffResult(
            action_type="database",
            diffs=diffs,
            affected_tables=affected_tables,
            affected_files=[],
            estimated_risk=risk,
            summary=summary,
        )

    def _fetch_current_rows(
        self,
        db_path: str,
        operation: str,
        query: str,
        params: SQLParams,
        table: str,
    ) -> list[RowData]:
        """Fetch current rows that would be affected by the operation."""

        def _do_fetch() -> list[RowData]:
            if db_path == ":memory:":
                return []

            where_clause = extract_where_clause(query, operation)
            select_query = f"SELECT * FROM {table}"  # noqa: S608
            select_params: SQLParams = []

            if where_clause:
                select_query += f" WHERE {where_clause}"
                if operation == "UPDATE":
                    set_placeholders = count_placeholders_in_set(query)
                    select_params = list(params[set_placeholders:])
                else:
                    select_params = list(params)

            select_query += " LIMIT 100"

            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            try:
                cursor = conn.execute(select_query, select_params)  # nosemgrep
                return [dict(row) for row in cursor.fetchall()]
            finally:
                conn.close()

        return _retry(
            _do_fetch,
            max_retries=3,
            base_delay=0.1,
            label=f"DiffPreviewEngine._fetch_current_rows({table})",
        )

    # ── File diff ──────────────────────────────────────────────

    def _diff_file(
        self,
        config: dict[str, Any],
        context: dict[str, Any],
    ) -> DiffResult:
        """Compute a diff for a file operation."""
        diffs: list[DiffEntry] = []
        affected_files: list[str] = []

        operation = str(config.get("operation", "read")).lower()
        source = str(config.get("source", ""))
        destination = str(config.get("destination", ""))
        content = config.get("content")
        base_dir = config.get("base_dir", os.getcwd())

        target_path = destination or source
        if target_path:
            affected_files.append(target_path)

        if operation == "write":
            exists = os.path.exists(os.path.join(base_dir, target_path)) if target_path else False
            if exists:
                diffs.append(
                    DiffEntry(
                        field_path=target_path,
                        old_value="<existing_file>",
                        new_value=content if content is not None else "<new_content>",
                        change_type="modified",
                    )
                )
            else:
                diffs.append(
                    DiffEntry(
                        field_path=target_path,
                        old_value=None,
                        new_value=content if content is not None else "<new_content>",
                        change_type="added",
                    )
                )
        elif operation == "delete":
            exists = os.path.exists(os.path.join(base_dir, source)) if source else False
            if exists:
                diffs.append(
                    DiffEntry(
                        field_path=source,
                        old_value="<existing_file>",
                        new_value=None,
                        change_type="removed",
                    )
                )
        elif operation == "append":
            diffs.append(
                DiffEntry(
                    field_path=target_path,
                    old_value="<current_content>",
                    new_value="<current_content + appended_data>",
                    change_type="modified",
                )
            )
        elif operation == "move":
            if source:
                diffs.append(
                    DiffEntry(
                        field_path=source,
                        old_value="<existing_file>",
                        new_value=None,
                        change_type="removed",
                    )
                )
            if destination:
                dest_exists = os.path.exists(os.path.join(base_dir, destination)) if destination else False
                diffs.append(
                    DiffEntry(
                        field_path=destination,
                        old_value="<existing_file>" if dest_exists else None,
                        new_value="<moved_file>",
                        change_type="modified" if dest_exists else "added",
                    )
                )
        elif operation == "copy":
            if destination:
                dest_exists = os.path.exists(os.path.join(base_dir, destination)) if destination else False
                diffs.append(
                    DiffEntry(
                        field_path=destination,
                        old_value="<existing_file>" if dest_exists else None,
                        new_value="<copied_file>",
                        change_type="modified" if dest_exists else "added",
                    )
                )
        else:
            diffs.append(
                DiffEntry(
                    field_path=target_path,
                    old_value="<current>",
                    new_value="<current>",
                    change_type="modified",
                )
            )

        risk = estimate_risk_from_diffs(diffs, operation)
        summary = f"File {operation}: {target_path}" if target_path else f"File {operation}"

        return DiffResult(
            action_type="file",
            diffs=diffs,
            affected_tables=[],
            affected_files=affected_files,
            estimated_risk=risk,
            summary=summary,
        )

    # ── Email diff ─────────────────────────────────────────────

    def _diff_email(
        self,
        config: dict[str, Any],
        context: dict[str, Any],
    ) -> DiffResult:
        """Compute a diff for an email operation."""
        diffs: list[DiffEntry] = []

        to_emails = config.get("to", [])
        if isinstance(to_emails, str):
            to_emails = [to_emails]
        subject = config.get("subject", "")
        from_email = config.get("from_email", "")
        cc = config.get("cc", [])
        bcc = config.get("bcc", [])

        diffs.append(DiffEntry(field_path="email.from", old_value=None, new_value=from_email, change_type="added"))
        diffs.append(
            DiffEntry(field_path="email.to", old_value=None, new_value=[str(r) for r in to_emails], change_type="added")
        )
        diffs.append(DiffEntry(field_path="email.subject", old_value=None, new_value=subject, change_type="added"))
        if cc:
            diffs.append(
                DiffEntry(
                    field_path="email.cc",
                    old_value=None,
                    new_value=[str(c) for c in cc] if isinstance(cc, list) else [str(cc)],
                    change_type="added",
                )
            )
        if bcc:
            diffs.append(
                DiffEntry(
                    field_path="email.bcc",
                    old_value=None,
                    new_value=[str(b) for b in bcc] if isinstance(bcc, list) else [str(bcc)],
                    change_type="added",
                )
            )

        risk = estimate_risk_from_diffs(diffs, "send_email")
        summary = f"Would send email from '{from_email}' to {len(to_emails)} recipient(s) with subject '{subject}'"

        return DiffResult(
            action_type="email",
            diffs=diffs,
            affected_tables=[],
            affected_files=[],
            estimated_risk=risk,
            summary=summary,
        )

    # ── Generic diff ───────────────────────────────────────────

    def _diff_generic(
        self,
        action_type: str,
        config: dict[str, Any],
        context: dict[str, Any],
    ) -> DiffResult:
        """Compute a generic diff for any action type."""
        diffs: list[DiffEntry] = []

        for key, value in config.items():
            diffs.append(
                DiffEntry(
                    field_path=f"{action_type}.{key}",
                    old_value=None,
                    new_value=value,
                    change_type="added",
                )
            )

        risk = estimate_risk_from_diffs(diffs, action_type)
        summary = f"Generic diff for {action_type}: {len(diffs)} field(s) would change"

        return DiffResult(
            action_type=action_type,
            diffs=diffs,
            affected_tables=[],
            affected_files=[],
            estimated_risk=risk,
            summary=summary,
        )

    # ── Formatting ─────────────────────────────────────────────

    def format_diff(
        self,
        diff_result: DiffResult,
        format: str = "text",
    ) -> str:
        """Format a DiffResult as text or JSON."""
        with self._lock:
            if format.lower() == "json":
                return json.dumps(diff_result.to_dict(), indent=2, default=str)

            lines: list[str] = []
            lines.append(f"Diff Preview: {diff_result.action_type}")
            lines.append(f"Risk: {diff_result.estimated_risk}")
            lines.append(f"Summary: {diff_result.summary}")
            lines.append("")

            if diff_result.affected_tables:
                lines.append(f"Affected tables: {', '.join(diff_result.affected_tables)}")
            if diff_result.affected_files:
                lines.append(f"Affected files: {', '.join(diff_result.affected_files)}")

            if diff_result.diffs:
                lines.append("")
                lines.append("Changes:")
                for d in diff_result.diffs:
                    change_symbol = {
                        "added": "+",
                        "modified": "~",
                        "removed": "-",
                    }.get(d.change_type, "?")
                    lines.append(
                        f"  [{change_symbol}] {d.field_path}: {truncate(d.old_value)} → {truncate(d.new_value)}"
                    )

            return "\n".join(lines)

    # ── Risk estimation ────────────────────────────────────────

    def estimate_risk(self, diff_result: DiffResult) -> str:
        """Estimate risk level based on the number and type of diffs."""
        with self._lock:
            return estimate_risk_from_diffs(
                diff_result.diffs,
                diff_result.action_type,
            )
