import os
import time
from typing import Any, Dict, List, Optional, Tuple

import requests
import streamlit as st

# -----------------------------------------------------------------------------
# Hakilix Clinical Dashboard (Streamlit)
# -----------------------------------------------------------------------------
# Goals:
# - No third-party autorefresh dependency
# - Stable, glass-style UI
# - Graceful degraded modes (API down / 401 / empty data)
# - Resident CRUD (create/update/delete)
# - Live view using Streamlit fragments when available
# -----------------------------------------------------------------------------


API_BASE_URL = os.getenv("API_BASE_URL", "http://hakilix-api:8080").rstrip("/")
DEFAULT_EMAIL = os.getenv("DEMO_ADMIN_EMAIL", "demo@hakilix.local")
DEFAULT_PASSWORD = os.getenv("DEMO_ADMIN_PASSWORD", "hakilix-admin")
DEFAULT_AGENCY_ID = os.getenv("DEMO_AGENCY_ID", "A-001")


class ApiError(RuntimeError):
    def __init__(self, status_code: int, detail: str):
        super().__init__(f"{status_code}: {detail}")
        self.status_code = status_code
        self.detail = detail


def _load_css() -> str:
    here = os.path.dirname(__file__)
    css_path = os.path.join(here, "glass.css")
    try:
        with open(css_path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception:
        return ""


def _fragment(run_every_seconds: Optional[float] = None):
    """Compatibility wrapper: Streamlit fragments exist in newer Streamlit versions."""
    frag = getattr(st, "fragment", None)
    if frag is None:
        def decorator(fn):
            return fn
        return decorator
    if run_every_seconds is None:
        return frag
    return frag(run_every=run_every_seconds)


class ApiClient:
    def __init__(self, base_url: str, token: Optional[str] = None):
        self.base_url = base_url.rstrip("/")
        self.token = token

    def _headers(self) -> Dict[str, str]:
        h = {"Accept": "application/json"}
        if self.token:
            h["Authorization"] = f"Bearer {self.token}"
        return h

    def _req(self, method: str, path: str, *, params: Optional[Dict[str, Any]] = None,
             json_body: Optional[Dict[str, Any]] = None, data: Optional[Dict[str, Any]] = None,
             timeout: float = 8.0) -> Any:
        url = f"{self.base_url}{path}"
        try:
            r = requests.request(method, url, headers=self._headers(), params=params, json=json_body, data=data, timeout=timeout)
        except requests.RequestException as e:
            raise ApiError(0, f"API unreachable: {e}") from e

        if r.status_code == 401:
            raise ApiError(401, "Unauthorized (token expired or invalid)")

        if not r.ok:
            detail = ""
            try:
                detail = r.json().get("detail") or r.json().get("error") or r.text
            except Exception:
                detail = r.text
            raise ApiError(r.status_code, detail.strip() or "Request failed")

        if r.status_code == 204:
            return None
        # Some endpoints may return empty body on success.
        if not r.content:
            return None
        try:
            return r.json()
        except Exception:
            return r.text

    def health(self) -> Dict[str, Any]:
        return self._req("GET", "/v1/health")

    def login(self, email: str, password: str) -> str:
        # OAuth2PasswordRequestForm expects username/password (form-encoded)
        data = {"username": email, "password": password}
        resp = self._req("POST", "/v1/auth/token", data=data)
        token = resp.get("access_token")
        if not token:
            raise ApiError(0, "Token missing in response")
        return token

    def list_residents(self) -> List[Dict[str, Any]]:
        return self._req("GET", "/v1/residents")

    def upsert_resident(self, resident_id: str, display_name: str) -> Dict[str, Any]:
        # Backend binds the resident to the caller's tenant (agency_id from JWT).        
        return self._req("POST", "/v1/residents", json_body={"id": resident_id, "display_name": display_name})

    def delete_resident(self, resident_id: str) -> None:
        self._req("DELETE", f"/v1/residents/{resident_id}")

    def latest_risk(self, resident_id: str) -> Dict[str, Any]:
        return self._req("GET", f"/v1/residents/{resident_id}/latest")

    def recent_telemetry(self, resident_id: str, limit: int = 120) -> List[Dict[str, Any]]:
        resp = self._req("GET", f"/v1/telemetry/{resident_id}/recent", params={"limit": limit})
        if isinstance(resp, dict):
            return resp.get("points") or []
        return resp or []


def _badge(level: str) -> str:
    lv = (level or "").lower()
    if lv in {"critical", "high"}:
        c = "hx-badge hx-badge--red"
    elif lv in {"medium", "moderate"}:
        c = "hx-badge hx-badge--amber"
    elif lv in {"low"}:
        c = "hx-badge hx-badge--green"
    else:
        c = "hx-badge"
    return f"<span class='{c}'>{level}</span>"


def _kpi(label: str, value: str, meta: str = "") -> str:
    meta_html = f"<div class='meta'>{meta}</div>" if meta else ""
    return (
        "<div class='hx-k'>"
        f"<div class='label'>{label}</div>"
        f"<div class='value'>{value}</div>"
        f"{meta_html}"
        "</div>"
    )


def _safe_float(v: Any, default: float = 0.0) -> float:
    try:
        return float(v)
    except Exception:
        return default


def _page_header(agency_id: str, resident_id: Optional[str]) -> None:
    st.markdown(
        """
        <div class="hx-top">
          <div class="hx-brand">
            <div class="hx-logo">H</div>
            <div>
              <div class="hx-title">Hakilix Clinical</div>
              <div class="hx-sub">Futuristic vital intelligence • Demo build</div>
            </div>
          </div>
          <div class="hx-meta">
            <div class="hx-pill">Agency: <b>{agency}</b></div>
            <div class="hx-pill">Resident: <b>{resident}</b></div>
          </div>
        </div>
        """.format(agency=agency_id, resident=(resident_id or "—")),
        unsafe_allow_html=True,
    )


def _show_api_status(client: ApiClient) -> None:
    try:
        h = client.health()
        st.sidebar.success(f"API OK • {h.get('service','hakilix')}" )
    except Exception as e:
        st.sidebar.error(f"API unavailable: {e}")


def _require_token() -> Optional[str]:
    token = st.session_state.get("token")
    if token:
        return token
    return None


def _login_ui() -> None:
    st.sidebar.markdown("### Sign in")
    with st.sidebar.form("login_form", clear_on_submit=False):
        email = st.text_input("Email", value=DEFAULT_EMAIL, key="login_email")
        password = st.text_input("Password", value=DEFAULT_PASSWORD, type="password", key="login_password")
        submitted = st.form_submit_button("Sign in")
    if submitted:
        client = ApiClient(API_BASE_URL)
        try:
            token = client.login(email.strip(), password)
            st.session_state["token"] = token
            st.session_state["email"] = email.strip()
            st.success("Signed in")
            st.rerun()
        except ApiError as e:
            st.sidebar.error(f"Login failed: {e.detail}")


def _logout_ui() -> None:
    if st.sidebar.button("Sign out", key="btn_logout"):
        for k in ["token", "email"]:
            st.session_state.pop(k, None)
        st.rerun()


def _resident_admin(client: ApiClient) -> Tuple[List[Dict[str, Any]], Optional[str]]:
    st.sidebar.markdown("---")
    st.sidebar.markdown("### Residents")

    # list residents
    residents: List[Dict[str, Any]] = []
    try:
        residents = client.list_residents()
    except ApiError as e:
        st.sidebar.error(f"Could not load residents: {e.detail}")

    options = [r.get("id") for r in residents if r.get("id")]

    # Streamlit constraint: session_state for a widget key cannot be modified after the widget
    # is instantiated. We therefore apply "pending" selection changes *before* rendering the
    # selectbox.
    pending = st.session_state.pop("_resident_select_pending", None)
    if pending and pending in options:
        st.session_state["resident_select"] = pending

    if "resident_select" not in st.session_state:
        st.session_state["resident_select"] = options[0] if options else None
    if options and st.session_state.get("resident_select") not in options:
        st.session_state["resident_select"] = options[0]

    # Provide a stable index to avoid Streamlit index errors when the list changes.
    idx = options.index(st.session_state["resident_select"]) if options and st.session_state.get("resident_select") in options else 0
    selected = st.sidebar.selectbox("Select resident", options=options, index=idx if options else 0, key="resident_select")

    # create/update
    st.sidebar.markdown("#### Add / Update")
    with st.sidebar.form("resident_upsert", clear_on_submit=False):
        rid = st.text_input("Resident ID", value=selected or "R-001", key="resident_upsert_id")
        name = st.text_input("Display name", value="", key="resident_upsert_name")
        save = st.form_submit_button("Save")

    if save:
        rid = rid.strip()
        name = name.strip()
        if not rid:
            st.sidebar.error("Resident ID is required")
        elif not name:
            st.sidebar.error("Display name is required")
        else:
            try:
                client.upsert_resident(rid, name)
                st.sidebar.success("Saved")
                # Defer selection change to the next run (pre-widget instantiation).
                st.session_state["_resident_select_pending"] = rid
                st.rerun()
            except ApiError as e:
                st.sidebar.error(f"Save failed: {e.detail}")

    # delete
    st.sidebar.markdown("#### Delete")
    with st.sidebar.form("resident_delete", clear_on_submit=True):
        del_id = st.text_input("Resident ID to delete", value=selected or "", key="resident_delete_id")
        confirm = st.checkbox("Confirm delete", value=False, key="resident_delete_confirm")
        do_del = st.form_submit_button("Delete")

    if do_del:
        del_id = del_id.strip()
        if not del_id:
            st.sidebar.error("Resident ID is required")
        elif not confirm:
            st.sidebar.error("Please confirm delete")
        else:
            try:
                client.delete_resident(del_id)
                st.sidebar.success("Deleted")
                # Attempt to move selection to the next available resident.
                try:
                    refreshed = client.list_residents()
                    opts = [r.get("id") for r in refreshed if r.get("id")]
                    st.session_state["_resident_select_pending"] = opts[0] if opts else None
                except Exception:
                    pass
                st.rerun()
            except ApiError as e:
                st.sidebar.error(f"Delete failed: {e.detail}")

    return residents, selected


def _infer_posture_activity(latest_point: Dict[str, Any]) -> Tuple[str, str]:
    """Heuristic twin reconstruction for demo UI.

    In production, posture/activity come from the edge bio-twin pipeline.
    For this repo demo we infer a coarse state from telemetry features.
    """
    if not latest_point:
        return "n/a", "n/a"

    gait = _safe_float(latest_point.get("gait_instability"), 0.0)
    wander = _safe_float(latest_point.get("night_wandering"), 0.0)
    hypo = _safe_float(latest_point.get("orthostatic_hypotension"), 0.0)

    activity = "Resting"
    posture = "Seated"
    if wander >= 0.65:
        activity = "Wandering"
        posture = "Walking"
    elif gait >= 0.55:
        activity = "Unsteady Walk"
        posture = "Standing"
    elif hypo >= 0.60:
        activity = "Transfer"
        posture = "Standing"
    return posture, activity


def _render_overview(latest_point: Dict[str, Any]) -> None:
    posture, activity = _infer_posture_activity(latest_point)
    rr = _safe_float(latest_point.get("rr"), 0.0)
    spo2 = _safe_float(latest_point.get("spo2"), 0.0)
    temp_c = _safe_float(latest_point.get("temp_c"), 0.0)

    st.markdown(
        "<div class='hx-kpi'>"
        + _kpi("Posture", posture, f"Activity: {activity}")
        + _kpi("RR", f"{rr:.1f}", "breaths/min")
        + _kpi("SpO₂", f"{spo2:.1f}", "%")
        + _kpi("Temp", f"{temp_c:.2f}", "°C")
        + "</div>",
        unsafe_allow_html=True,
    )


def _risk_level(score: float) -> str:
    if score >= 0.75:
        return "HIGH"
    if score >= 0.45:
        return "MED"
    return "LOW"


def _render_risks(risk: Optional[Dict[str, Any]]) -> None:
    if not risk:
        st.markdown(
            "<div class='hx-card'><div class='hx-title'>Risk Signals</div><div class='hx-muted'>No risk events yet.</div></div>",
            unsafe_allow_html=True,
        )
        return

    items = [
        ("FALL", _safe_float(risk.get("falls_risk"), 0.0), "Gait / Hypotension / Falls"),
        ("RESP", _safe_float(risk.get("resp_risk"), 0.0), "SpO₂ / RR / Temp"),
        ("DEHYD", _safe_float(risk.get("dehydration_risk"), 0.0), "Intake / Tachycardia"),
        ("DELIRIUM", _safe_float(risk.get("delirium_uti_risk"), 0.0), "Sleep / Agitation / Toileting"),
    ]

    cols = st.columns(4)
    for (title, score, meta), col in zip(items, cols):
        lvl = _risk_level(score)
        score_class = "hx-score-low" if lvl == "LOW" else "hx-score-med" if lvl == "MED" else "hx-score-high"
        with col:
            st.markdown(
                "<div class='hx-risk'>"
                f"<div class='row'><div class='title'>{title}</div><div class='score {score_class}'>{lvl} {score:.2f}</div></div>"
                f"<div class='meta'>{meta}</div>"
                "</div>",
                unsafe_allow_html=True,
            )


def _render_trends(points: List[Dict[str, Any]]) -> None:
    if not points:
        return

    # Keep this lightweight to avoid flicker.
    import pandas as pd

    df = pd.DataFrame(points)
    # Normalize columns
    for c in ["rr", "spo2", "temp_c", "hr"]:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    if "time" in df.columns:
        df["time"] = pd.to_datetime(df["time"], errors="coerce")
        df = df.sort_values("time")

    cols = st.columns(3)
    with cols[0]:
        if "rr" in df.columns:
            st.line_chart(df.set_index("time")["rr"], height=180)
    with cols[1]:
        if "spo2" in df.columns:
            st.line_chart(df.set_index("time")["spo2"], height=180)
    with cols[2]:
        if "temp_c" in df.columns:
            st.line_chart(df.set_index("time")["temp_c"], height=180)


def main() -> None:
    st.set_page_config(page_title="Hakilix Clinical", layout="wide")
    st.markdown(f"<style>{_load_css()}</style>", unsafe_allow_html=True)

    if "token" not in st.session_state:
        st.session_state["token"] = None

    token = _require_token()

    # Sidebar controls
    st.sidebar.markdown("## Hakilix")
    agency_id = st.sidebar.text_input("Agency ID", value=DEFAULT_AGENCY_ID, key="agency_id")

    if not token:
        _login_ui()
        st.stop()

    client = ApiClient(API_BASE_URL, token=token)
    _show_api_status(client)
    _logout_ui()

    live = st.sidebar.toggle("Live mode", value=True, key="live_mode")
    refresh_s = st.sidebar.slider("Refresh interval (sec)", min_value=2, max_value=10, value=3, step=1, key="refresh_s")

    residents, selected_id = _resident_admin(client)

    _page_header(agency_id, selected_id)

    if not selected_id:
        st.info("Create a resident in the left sidebar to begin.")
        st.stop()

    # Use placeholders so that Streamlit fragments overwrite content (no repeated snapshots).
    overview_ph = st.empty()
    risks_ph = st.empty()
    trends_ph = st.empty()

    @_fragment(run_every_seconds=(refresh_s if live else None))
    def _live_section() -> None:
        try:
            pts = client.recent_telemetry(selected_id, limit=120)
        except ApiError as e:
            st.error(f"Telemetry error: {e.detail}")
            pts = []

        latest_point = pts[-1] if pts else {}

        try:
            risk = client.latest_risk(selected_id)
        except ApiError:
            risk = None

        with overview_ph.container():
            st.markdown("### Live Snapshot")
            _render_overview(latest_point)

        with risks_ph.container():
            st.markdown("### Risk Signals")
            _render_risks(risk)

        with trends_ph.container():
            st.markdown("### Trends")
            _render_trends(pts)

    _live_section()


if __name__ == "__main__":
    main()
