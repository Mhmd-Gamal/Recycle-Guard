from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import threading
import pytest
from adviser.models import AdviceRequest, Observation
from adviser.policy import advise


@pytest.mark.parametrize("fenced", [False, True])
def test_real_http_provider_adapter_with_local_stub(core, monkeypatch, fenced):
    received = []
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_): pass
        def do_POST(self):
            received.append((self.path, json.loads(self.rfile.read(int(self.headers["Content-Length"])))))
            action = json.dumps({"kind": "suppress", "zone": 0, "revision": 0})
            content = "```json\n"+action+"\n```" if fenced else action
            payload = json.dumps({"choices": [{"message": {"content": content}}]}).encode()
            self.send_response(200); self.send_header("Content-Type", "application/json"); self.end_headers(); self.wfile.write(payload)
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
    monkeypatch.setenv("RECYCLEGUARD_LLM_URL", f"http://127.0.0.1:{server.server_port}/v1")
    monkeypatch.setenv("RECYCLEGUARD_LLM_MODEL", "test-stub-not-a-real-model")
    try:
        o = Observation.model_validate(core.call("observe"))
        raw = advise(AdviceRequest(observation=o, mode="llm_raw"))
        checked = advise(AdviceRequest(observation=o, mode="llm_checked"))
        assert raw.recommendation.kind == "suppress"
        assert checked.intervention and checked.recommendation.kind != "suppress"
        assert received[0][0] == "/v1/chat/completions"
        assert "truth" not in received[0][1]["messages"][1]["content"]
        assert received[0][1]["temperature"] == 0
    finally:
        server.shutdown(); server.server_close(); thread.join(timeout=2)


def test_malformed_provider_output_is_not_a_fake_success(core, monkeypatch):
    import io
    monkeypatch.setenv("RECYCLEGUARD_LLM_URL", "http://localhost:1/v1")
    monkeypatch.setenv("RECYCLEGUARD_LLM_MODEL", "stub")
    monkeypatch.setattr("urllib.request.urlopen", lambda *a, **k: io.BytesIO(b'{"choices":[{"message":{"content":"not JSON"}}]}'))
    with pytest.raises(ValueError):
        advise(AdviceRequest(observation=Observation.model_validate(core.call("observe")), mode="llm_checked"))
