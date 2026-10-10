import os
from typing import Any

from dotenv import load_dotenv
from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from ai_analyzer import analyze_audit, extract_claims, extract_image_text, extract_pdf_text, fetch_url_text, valid_file_type
from database import delete_audit_record, init_db, list_audit_records, save_audit_record

load_dotenv()

limiter = Limiter(key_func=get_remote_address)
app = FastAPI(title="PS03 Ad Auditor", version="1.0.0")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ClaimRequest(BaseModel):
    headline: str | None = Field(default=None, description="Optional headline")
    description: str | None = Field(default=None, description="Optional ad description")
    offer: str | None = Field(default=None, description="Optional offer")
    call_to_action: str | None = Field(default=None)
    additional_context: str | None = Field(default=None)
    landing_page_url: str | None = Field(default=None)
    landing_page_text: str | None = Field(default=None)
    poster_text: str | None = Field(default=None)
    structured_data: list[dict[str, str]] | None = None
    mock_mode: bool = False
    guest_session: bool = True


@app.on_event("startup")
def startup_event() -> None:
    init_db()


@app.get("/health")
@limiter.limit("25/minute")
def health(request: Request) -> dict[str, Any]:
    return {
        "status": "ok",
        "database": "ready",
        "mock_mode": True,
        "auth_configured": bool(os.getenv("SUPABASE_URL") and os.getenv("SUPABASE_ANON_KEY")),
        "app": "PS03 Ad Auditor",
    }


@app.get("/api/auth-status")
def auth_status() -> dict[str, Any]:
    configured = bool(os.getenv("SUPABASE_URL") and os.getenv("SUPABASE_ANON_KEY"))
    return {
        "configured": configured,
        "message": "Authentication not configured; the app is running in guest-only mode." if not configured else "Supabase Auth is configured.",
    }


@app.post("/api/analyze")
@limiter.limit("10/minute")
def analyze_endpoint(request: Request, payload: ClaimRequest) -> dict[str, Any]:
    ad_text = "\n".join([
        payload.headline or "",
        payload.description or "",
        payload.offer or "",
        payload.call_to_action or "",
        payload.additional_context or "",
    ]).strip()
    claims = extract_claims(ad_text, payload.poster_text, payload.structured_data)
    if not claims:
        claims = [payload.headline or payload.description or "Landing page claim"]

    landing_text = payload.landing_page_text or ""
    if not landing_text and payload.landing_page_url:
        try:
            landing_text = fetch_url_text(payload.landing_page_url)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    report = analyze_audit(claims, landing_text, payload.mock_mode)
    report["report_id"] = "guest-session"
    report["simulated"] = bool(payload.mock_mode) or report.get("mode") == "SIMULATED"
    report["mode"] = "SIMULATED" if report["simulated"] else "LIVE"
    report["issue"] = None
    init_db()
    save_audit_record(None, "guest", {"claims": claims, "report": report})
    return report


@app.post("/api/upload")
@limiter.limit("10/minute")
async def upload_file(request: Request, file: UploadFile = File(...), kind: str = "poster") -> dict[str, Any]:
    if file.size and file.size > 5 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large. Maximum is 5MB.")
    file_bytes = await file.read()
    if not valid_file_type(file.filename or "", file_bytes):
        raise HTTPException(status_code=400, detail="Unsupported file type or invalid signature.")
    ext = (file.filename or "").lower().rsplit(".", 1)[-1]
    if ext in {"png", "jpg", "jpeg", "webp"}:
        text = extract_image_text(file_bytes)
    elif ext == "pdf":
        text = extract_pdf_text(file_bytes)
    else:
        text = file_bytes.decode("utf-8", errors="replace")
    return {
        "filename": file.filename,
        "kind": kind,
        "extracted_text": text[:2000],
        "valid": True,
    }


@app.get("/api/reports")
def list_reports(request: Request) -> dict[str, Any]:
    return {"reports": list_audit_records(None), "guest_mode": True}


@app.delete("/api/reports/{report_id}")
def delete_report(request: Request, report_id: str) -> dict[str, Any]:
    deleted = delete_audit_record(report_id, None)
    if not deleted:
        raise HTTPException(status_code=404, detail="Report not found.")
    return {"deleted": True, "report_id": report_id}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)

