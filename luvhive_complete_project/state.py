
# state.py
from typing import Optional, Dict, Literal, TypedDict

Mode = Literal["ask", "answer"]

class QAState(TypedDict, total=False):
    feature: Literal["qa"]
    mode: Mode
    qid: Optional[int]

_state: Dict[int, QAState] = {}

def set_qa(user_id: int, mode: Mode, qid: Optional[int] = None) -> None:
    _state[user_id] = {"feature": "qa", "mode": mode, "qid": qid}

def get_qa(user_id: int) -> Optional[QAState]:
    st = _state.get(user_id)
    return st if (st and st.get("feature") == "qa") else None

def clear_qa(user_id: int) -> None:
    _state.pop(user_id, None)

# === POLL state ===
PollMode = Literal["question", "options"]

class PollState(TypedDict, total=False):
    feature: Literal["poll"]
    mode: PollMode
    question: Optional[str]

_poll_state: Dict[int, PollState] = {}

def set_poll(uid: int, mode: PollMode, question: Optional[str] = None) -> None:
    st = _poll_state.get(uid, {"feature": "poll"})
    st["feature"] = "poll"
    st["mode"] = mode
    if question is not None:
        st["question"] = question
    _poll_state[uid] = st

def get_poll(uid: int) -> Optional[PollState]:
    st = _poll_state.get(uid)
    return st if (st and st.get("feature") == "poll") else None

def clear_poll(uid: int) -> None:
    _poll_state.pop(uid, None)
