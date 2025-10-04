
import os
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from pydantic import BaseModel, constr, conint
from fastapi.responses import JSONResponse

# ---- ENV ----
EXTERNAL_URL = os.getenv("EXTERNAL_URL", "").rstrip("/")
CSP_ORIGIN    = os.getenv("CSP_ORIGIN", EXTERNAL_URL).rstrip("/")
ALLOW_ORIGIN_REGEX = os.getenv("ALLOW_ORIGIN_REGEX", r".*\.replit\.dev$")  # dev only
SESSION_SECRET = os.getenv("SESSION_SECRET", "dev-secret-change-me")

app = FastAPI(title="Lovbite API")

# ---- CORS (handles preflight) ----
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=ALLOW_ORIGIN_REGEX,     # Replit subdomains rotate
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---- Session cookie (SameSite=None + Secure) ----
app.add_middleware(
    SessionMiddleware,
    secret_key=SESSION_SECRET,
    same_site="none",    # IMPORTANT: cross-site allowed (iframe/new tab)
    https_only=True,     # IMPORTANT: required with SameSite=None
    session_cookie="lovbite_sid",
)

# ---- Models ----
class SetupPayload(BaseModel):
    display_name: constr(min_length=1, max_length=50)
    age:           conint(ge=18, le=110)
    username:      constr(regex=r"^[a-z0-9_]{3,20}$")

# ---- Helpers (replace with real DB) ----
def username_exists(u: str) -> bool:
    # TODO: check DB unique index users.username
    return False

def save_profile(user_id: str, p: SetupPayload):
    # TODO: persist to DB
    pass

# ---- Routes ----
@app.get("/api/me")
def me(req: Request):
    # create a temp session if missing (helps curl/dev)
    if "uid" not in req.session:
        req.session["uid"] = "temp-user"
    return {"ok": True, "uid": req.session["uid"]}

@app.post("/api/setup")
def complete_setup(p: SetupPayload, req: Request):
    uid = req.session.get("uid")
    if not uid:
        # session/cookie not sent -> CORS/cookie issue
        raise HTTPException(status_code=401, detail="no_session")

    # business validations
    if username_exists(p.username):
        raise HTTPException(status_code=409, detail="username_exists")

    try:
        save_profile(uid, p)
    except Exception as e:
        # surface real error instead of generic
        raise HTTPException(status_code=500, detail=f"db_error:{type(e).__name__}")

    return {"ok": True}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
