from __future__ import annotations

from typing import Any, Optional
from fastapi import FastAPI, Query, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from neurotrace import __version__
from neurotrace.query.storage import open_db, fetch_distinct_conversations, fetch_sessions
from neurotrace.query.summaries import session_summary
from neurotrace.analytics.graphs import make_tree
from neurotrace.visuals.api_specs import (
    vega_session_overview,
    vega_zone_mix,
    vega_depth_dist,
    vega_transitions,
)
from neurotrace.eval.quality_gates import hash_json
from neurotrace.api.schemas import HealthResponse
from pathlib import Path
import json
from fastapi.responses import PlainTextResponse



def build_app(
    db_path: str,
    *,
    enable_cors: bool = False,
    static_dir: Optional[str] = None,
) -> FastAPI:
    app = FastAPI(title="Neurotrace", version="0.1.0")

    if enable_cors:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["http://localhost", "http://127.0.0.1"],
            allow_credentials=False,
            allow_methods=["GET"],
            allow_headers=["*"]
        )

    if static_dir:
        try:
            # Mount UI at /ui to avoid shadowing API routes at root
            app.mount("/ui", StaticFiles(directory=static_dir, html=True), name="static")
        except Exception:
            # Static mounting is optional; ignore if path invalid
            pass

    @app.get("/health")
    def health() -> dict[str, Any]:
        """Return stable hashes over known artifacts/manifests and fixed schema keys.

        - schema_hash: hash of required visual spec names (frozen contract)
        - golden_hash: hash of the latest visuals manifest's artifact hashes (if present)
        """
        # Schema hash based on frozen visual spec contract
        schema_hash = hash_json({
            "visuals_required": [
                "overview.json",
                "zone_mix.json",
                "transitions.json",
                "depth_dist.json",
            ]
        })

        # Golden hash from latest visuals manifest (if exists)
        golden_hash = None
        visuals_root = Path("outputs/derived/visuals")
        if visuals_root.exists():
            run_dirs = sorted([p for p in visuals_root.iterdir() if p.is_dir()], reverse=True)
            for run_dir in run_dirs:
                m = run_dir / "manifest.json"
                if m.exists():
                    try:
                        manifest = json.loads(m.read_text(encoding="utf-8"))
                        artifacts = manifest.get("artifacts", [])
                        # Map name->sha256 for deterministic hashing
                        name_to_hash = {a.get("name"): a.get("sha256") for a in artifacts if "name" in a and "sha256" in a}
                        golden_hash = hash_json(name_to_hash)
                        break
                    except Exception:
                        # If manifest unreadable, continue to older runs
                        continue

        return {"schema_hash": schema_hash, "golden_hash": golden_hash, "version": __version__}

    @app.get("/report/run")
    def report_run(response: Response) -> dict[str, Any]:
        # Prefer derived JSON; fallback to legacy CSV path
        from neurotrace.aggregator.emit.run_report import (
            write_report_and_charts_from_derived,
            write_report_and_charts,
        )
        # Try latest run_id by inspecting derived/visuals
        run_id = None
        dvis = Path("outputs/derived/visuals")
        if dvis.exists():
            ids = sorted([p.name for p in dvis.iterdir() if p.is_dir()], reverse=True)
            run_id = ids[0] if ids else None
        if run_id:
            res = write_report_and_charts_from_derived("outputs/derived", run_id, Path("outputs/report"))
        else:
            # Fallback
            res = write_report_and_charts("outputs/metrics", Path("outputs/report"))
        report_path = Path(res["report"]).resolve()
        payload = json.loads(report_path.read_text(encoding="utf-8"))
        # ETag via stable hash of payload
        etag = hash_json(payload)
        response.headers["ETag"] = etag
        return payload

    @app.get("/report/charts/{name}")
    def report_chart(name: str) -> Any:
        p = Path("outputs/report/charts") / name
        if not p.exists():
            if p.suffix == ".csv":
                alt = p.with_suffix(".json")
                if alt.exists():
                    return json.loads(alt.read_text(encoding="utf-8"))
            return {"error": "not found"}
        if p.suffix == ".csv":
            return PlainTextResponse(p.read_text(encoding="utf-8"), media_type="text/csv; charset=utf-8")
        else:
            return json.loads(p.read_text(encoding="utf-8"))

    @app.get("/report/conversation/{cid}")
    def report_conversation(cid: str) -> dict[str, Any]:
        # Sample payload from existing metrics
        import pandas as pd
        mroot = Path("outputs/metrics")
        s = mroot / "summary" / f"{cid}.csv"
        t = mroot / "transitions" / f"{cid}.csv"
        b = mroot / "breadcrumbs" / f"{cid}.csv"
        summary = pd.read_csv(s).to_dict(orient="records") if s.exists() else []
        transitions = pd.read_csv(t).to_dict(orient="records") if t.exists() else []
        breadcrumbs_sample = pd.read_csv(b).head(20).to_dict(orient="records") if b.exists() else []
        return {"summary": summary, "transitions": transitions, "breadcrumbs_sample": breadcrumbs_sample}

    @app.get("/sessions")
    def sessions(limit: int = Query(100, ge=1, le=1000), offset: int = Query(0, ge=0)) -> list[dict[str, Any]]:
        with open_db(db_path) as conn:
            rows = list(fetch_sessions(conn, limit=limit, offset=offset))
            # Adapt to API contract: { id, started_at, message_count }
            items = [
                {
                    "id": r["id"],
                    "started_at": None if r.get("start_ts") is None else str(r.get("start_ts")),
                    "message_count": int(r.get("message_count") or 0),
                }
                for r in rows
            ]
            return items

    @app.get("/sessions/{sid}")
    def session(sid: str) -> dict[str, Any]:
        with open_db(db_path) as conn:
            return session_summary(conn, sid)

    @app.get("/sessions/{sid}/tree")
    def session_tree(sid: str) -> dict[str, Any]:
        with open_db(db_path) as conn:
            return make_tree(conn, sid)

    @app.get("/sessions/{sid}/visuals/overview")
    def session_overview_visual(sid: str) -> dict[str, Any]:
        with open_db(db_path) as conn:
            summary = session_summary(conn, sid)
            return vega_session_overview(summary)

    @app.get("/sessions/{sid}/visuals/{name}")
    def session_visual_named(sid: str, name: str) -> dict[str, Any]:
        with open_db(db_path) as conn:
            summary = session_summary(conn, sid)
            if name == "overview":
                return vega_session_overview(summary)
            if name in ("zone_mix", "zone-mix"):
                return vega_zone_mix(summary)
            if name in ("depth_dist", "depth-dist", "depth"):
                return vega_depth_dist(summary)
            if name in ("transitions", "transition_matrix"):
                return vega_transitions(summary)
            return {"error": f"unknown visual '{name}'"}

    # Note: Export routes removed to keep API strictly read-only. Use CLI `export architect`.

    return app

