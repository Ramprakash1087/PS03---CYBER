import ipaddress
import json
import os
import re
import socket
from typing import Any
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup
from dotenv import load_dotenv
import fitz
import pytesseract
from PIL import Image

load_dotenv()

VERDICT_ORDER = ["SUPPORTED", "CONTRADICTED", "QUALIFIED", "NOT_FOUND", "UNCERTAIN"]
SEVERITY_BY_VERDICT = {
    "SUPPORTED": "low",
    "CONTRADICTED": "high",
    "QUALIFIED": "medium",
    "NOT_FOUND": "medium",
    "UNCERTAIN": "medium",
}


def normalize_space(value: str) -> str:
    return re.sub(r"\s+", " ", (value or "")).strip()


def clean_text(value: str) -> str:
    return normalize_space(re.sub(r"\s+", " ", value or ""))


def extract_claims(ad_copy: str | None, poster_text: str | None = None, structured_data: list[dict] | None = None) -> list[str]:
    claims: list[str] = []
    sources: list[str] = []
    if ad_copy:
        sources.append(ad_copy)
    if poster_text:
        sources.append(poster_text)
    if structured_data:
        for item in structured_data:
            for key in ["headline", "description", "offer", "promotion", "call_to_action", "additional_context"]:
                if item.get(key):
                    sources.append(str(item.get(key)))

    keyword_pattern = re.compile(
        r"\b(free|save|saved|guarantee|guaranteed|instant|approved|zero|limited|best|no monthly|money-back|30-day|refund|discount|%|\$\d|\d+%|one-time|claim|without|satisfaction|clinically|dermatologist|tested)\b",
        re.IGNORECASE,
    )
    ignore_pattern = re.compile(
        r"\b(shop now|offer ends soon|learn more|click here|terms apply|today only|limited time|sign up now)\b",
        re.IGNORECASE,
    )

    for source in sources:
        chunks = re.split(r"(?<=[.!?])\s+|\n+|\s*;\s*", source)
        for chunk in chunks:
            candidate = clean_text(chunk)
            if len(candidate) < 8:
                continue
            if ignore_pattern.search(candidate):
                continue
            if len(candidate.split()) > 24:
                sub_chunks = re.split(r"\s(?:and|with|plus|including|starts at|for only|today|now)\s", candidate, flags=re.IGNORECASE)
                for sub in sub_chunks:
                    trimmed = clean_text(sub)
                    if len(trimmed) >= 8 and not ignore_pattern.search(trimmed) and (keyword_pattern.search(trimmed) or len(trimmed.split()) <= 9):
                        claims.append(trimmed)
                continue
            if keyword_pattern.search(candidate):
                claims.append(candidate)

    if not claims:
        combined = " ".join(sources)
        if combined:
            claims = [combined[:400]]

    unique: list[str] = []
    seen: set[str] = set()
    for claim in claims:
        normalized = claim.strip()
        if len(normalized) > 4 and normalized.lower() not in seen:
            unique.append(normalized)
            seen.add(normalized.lower())
    return unique[:10]


def sentence_from_text(text: str, query: str) -> str:
    query_words = set(re.findall(r"[a-z0-9]+", query.lower()))
    for sentence in re.split(r"(?<=[.!?])\s+", text):
        sentence_norm = sentence.strip()
        if not sentence_norm:
            continue
        if not query_words:
            return sentence_norm
        sentence_words = set(re.findall(r"[a-z0-9]+", sentence.lower()))
        if query_words & sentence_words:
            return sentence_norm
    return text[:220] if text else "No direct quote found."


def quote_fits_page(page_text: str, quote: str) -> bool:
    if not quote or not page_text:
        return False
    normalized_quote = normalize_space(quote).lower()
    normalized_page = normalize_space(page_text).lower()
    return normalized_quote in normalized_page or len(set(re.findall(r"[a-z0-9]+", normalized_quote))) > 0 and any(term in normalized_page for term in re.findall(r"[a-z0-9]+", normalized_quote)[:3])


def classify_claim(claim: str, page_text: str) -> dict[str, str | int | float]:
    claim_norm = normalize_space(claim)
    page_norm = normalize_space(page_text)
    if not claim_norm or not page_norm:
        return {
            "verdict": "UNCERTAIN",
            "severity": "medium",
            "confidence": 0.2,
            "reason": "Insufficient page evidence to validate the claim.",
            "quote": "",
            "source_section": "No readable content",
            "explanation": "The page lacked readable content or the claim could not be checked.",
            "recommended_change": "Add evidence supporting the marketing claim on the landing page.",
        }

    lowered_claim = claim_norm.lower()
    lowered_page = page_norm.lower()
    evidence_candidates = []
    for sentence in re.split(r"(?<=[.!?])\s+", page_text):
        if len(sentence.strip()) < 20:
            continue
        s = sentence.lower()
        if any(token in s for token in re.findall(r"[a-z0-9]+", lowered_claim)[:3]):
            evidence_candidates.append(sentence.strip())

    positive_match = any(keyword in lowered_page for keyword in ["guarantee", "free", "30%", "save", "works", "approved", "clinically", "tested"])
    negated = any(phrase in lowered_page for phrase in ["not", "no", "never", "cannot", "without", "does not", "not available", "cannot be"])

    if lowered_claim in lowered_page or (len(evidence_candidates) > 0 and quote_fits_page(page_text, claim_norm)):
        verdict = "SUPPORTED"
        reason = "The landing page contains supporting text for this claim."
        confidence = 0.86
        recommended = "Keep the claim and continue monitoring the page for updates."
    elif negated and any(token in lowered_page for token in re.findall(r"[a-z0-9]+", lowered_claim)[:5]):
        verdict = "CONTRADICTED"
        reason = "The page appears to negate the claim or distinguish it from the advertised promise."
        confidence = 0.82
        recommended = "Adjust the ad to match the page language or remove the unsupported promise."
    elif positive_match and len(evidence_candidates) > 0:
        verdict = "QUALIFIED"
        reason = "The page partially supports the claim but with limiting context or conditions."
        confidence = 0.72
        recommended = "Qualify the claim with necessary conditions or caveats on the page."
    elif any(token in lowered_page for token in re.findall(r"[a-z0-9]+", lowered_claim)[:3]):
        verdict = "QUALIFIED"
        reason = "Some terms appear, but the page does not fully substantiate the full promise."
        confidence = 0.63
        recommended = "Clarify the exact evidence or revise the claim wording."
    else:
        verdict = "NOT_FOUND"
        reason = "No matching support was found on the landing page."
        confidence = 0.78
        recommended = "Remove or rephrase the unsupported claim to match the evidence."

    quote = sentence_from_text(page_text, claim_norm) if evidence_candidates else ""
    section = "Landing page text"
    explanation = f"The claim '{claim_norm}' was evaluated against visible landing-page content. {reason}"
    return {
        "claim": claim_norm,
        "verdict": verdict,
        "severity": SEVERITY_BY_VERDICT.get(verdict, "medium"),
        "confidence": round(confidence, 2),
        "reason": reason,
        "quote": quote,
        "source_section": section,
        "explanation": explanation,
        "recommended_change": recommended,
    }


def build_overall_score(results: list[dict[str, str | int | float]]) -> tuple[int, str]:
    if not results:
        return 0, "Insufficient evidence to score"
    weights = {"SUPPORTED": 100, "QUALIFIED": 55, "UNCERTAIN": 35, "NOT_FOUND": 0, "CONTRADICTED": 0}
    total = 0
    for item in results:
        total += weights.get(item["verdict"], 0)
    score = int(round(total / len(results)))
    if score >= 80:
        status = "Strongly supported"
    elif score >= 60:
        status = "Mostly supported"
    elif score >= 40:
        status = "Mixed evidence"
    elif score > 0:
        status = "Weak support"
    else:
        status = "Unsupported"
    return score, status


def analyze_audit(claims: list[str], page_text: str, mock_mode: bool = False) -> dict[str, Any]:
    cleaned_page = normalize_space(page_text or "")
    if not claims:
        return {
            "overall_score": 0,
            "status": "Insufficient evidence to score",
            "summary": {"SUPPORTED": 0, "CONTRADICTED": 0, "QUALIFIED": 0, "NOT_FOUND": 0, "UNCERTAIN": 0},
            "claims": [],
            "simulated": bool(mock_mode),
            "mode": "SIMULATED" if mock_mode else "LIVE",
        }
    if len(cleaned_page) < 30:
        return {
            "overall_score": 0,
            "status": "Insufficient evidence to score",
            "summary": {"SUPPORTED": 0, "CONTRADICTED": 0, "QUALIFIED": 0, "NOT_FOUND": 0, "UNCERTAIN": 0},
            "claims": [{"claim": c, "verdict": "UNCERTAIN", "reason": "Landing page contains insufficient readable content."} for c in claims],
            "simulated": bool(mock_mode),
            "mode": "SIMULATED" if mock_mode else "LIVE",
        }

    results = [classify_claim(claim, cleaned_page) for claim in claims]
    summary = {verdict: 0 for verdict in ["SUPPORTED", "CONTRADICTED", "QUALIFIED", "NOT_FOUND", "UNCERTAIN"]}
    for item in results:
        summary[item["verdict"]] = summary.get(item["verdict"], 0) + 1
    score, status = build_overall_score(results)
    return {
        "overall_score": score,
        "status": status,
        "summary": summary,
        "claims": results,
        "simulated": bool(mock_mode),
        "mode": "SIMULATED" if mock_mode else "LIVE",
    }


def safe_hostname(url: str) -> str:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        raise ValueError("Only http and https URLs are allowed.")
    hostname = (parsed.hostname or "").lower()
    if not hostname:
        raise ValueError("The URL is missing a hostname.")
    return hostname


def is_private_ip(hostname: str) -> bool:
    try:
        ips = [item[4][0] for item in socket.getaddrinfo(hostname, None)]
    except socket.gaierror:
        return True
    for ip in ips:
        try:
            address = ipaddress.ip_address(ip)
        except ValueError:
            continue
        if address.is_private or address.is_loopback or address.is_link_local or address.is_reserved or address.is_multicast:
            return True
    return False


def fetch_url_text(url: str, max_bytes: int = 250000, timeout: float = 12.0) -> str:
    hostname = safe_hostname(url)
    if hostname in {"localhost", "127.0.0.1", "0.0.0.0"} or is_private_ip(hostname):
        raise ValueError("Unsafe or private URL is not allowed.")
    if hostname.endswith(".internal") or hostname.startswith("metadata.") or "169.254." in hostname:
        raise ValueError("This URL resolves to a blocked network address.")

    max_redirects = 3
    response = None
    for _ in range(max_redirects):
        response = httpx.get(url, timeout=timeout, follow_redirects=False, headers={"User-Agent": "PS03-Ad-Auditor/0.1"})
        if response.status_code in {301, 302, 303, 307, 308}:
            next_url = response.headers.get("location")
            if not next_url:
                break
            next_url = next_url if next_url.startswith("http") else f"{url.rstrip('/')}/{next_url.lstrip('/')}"
            safe_hostname(next_url)
            if is_private_ip(safe_hostname(next_url)):
                raise ValueError("Redirect target is not allowed.")
            url = next_url
            continue
        break

    if response is None:
        raise ValueError("Unable to access the landing page.")
    if response.status_code >= 400:
        raise ValueError(f"Landing page request failed with status {response.status_code}.")
    if not response.headers.get("content-type", "").startswith("text/") and "html" not in response.headers.get("content-type", ""):
        raise ValueError("Landing page content is not HTML text.")
    text = response.text[:max_bytes]
    soup = BeautifulSoup(text, "html.parser")
    for selector in ["script", "style", "nav", "footer", "header", "noscript"]:
        for tag in soup.select(selector):
            tag.decompose()
    return soup.get_text(" ", strip=True)[:max_bytes]


def extract_pdf_text(file_bytes: bytes) -> str:
    try:
        import fitz

        with fitz.open(stream=file_bytes, filetype="pdf") as doc:
            texts = []
            for page in doc:
                texts.append(page.get_text())
        return "\n".join(texts)
    except Exception as exc:
        raise ValueError("Unable to read the uploaded PDF.") from exc


def extract_image_text(file_bytes: bytes) -> str:
    try:
        from PIL import Image
        import io

        with Image.open(io.BytesIO(file_bytes)) as img:
            return pytesseract.image_to_string(img)
    except Exception as exc:
        raise ValueError("OCR failed for the uploaded image; please try another image or add manual text.") from exc


def valid_file_type(file_name: str, file_bytes: bytes) -> bool:
    import filetype

    file_type = filetype.guess(file_bytes)
    ext = (file_name or "").lower().rsplit(".", 1)[-1]
    allowed_exts = {"png", "jpg", "jpeg", "webp", "pdf", "html", "txt"}
    if ext not in allowed_exts:
        return False
    if ext in {"png", "jpg", "jpeg", "webp"}:
        return file_type is not None and file_type.mime in {"image/png", "image/jpeg", "image/webp"}
    if ext == "pdf":
        return file_type is not None and file_type.mime == "application/pdf"
    if ext in {"html", "txt"}:
        return True
    return False


def load_sample_dataset() -> list[dict[str, str | list[str] | bool | dict[str, str]]]:
    try:
        with open(os.path.join(os.path.dirname(__file__), "..", "data", "hackathon_dataset.json"), "r", encoding="utf-8") as file:
            content = json.load(file)
        if isinstance(content, list):
            return content
        return content.get("examples", [])
    except FileNotFoundError:
        return []

