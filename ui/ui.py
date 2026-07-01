"""
ui/ui.py — Multi-Tenant AI Agent Portal
Single-file Gradio application with a refined dark UI.
"""

import gradio as gr
import requests

API_URL = "http://localhost:8000"

TENANT_MAP = {
    "abc_dentals": ["ktm", "pokhara"],
    "xyz_travels": ["bhaktapur", "lalitpur"],
}

ORG_LABELS = {
    "abc_dentals": "ABC Dentals",
    "xyz_travels": "XYZ Travels",
}

BRANCH_LABELS = {
    "ktm": "Kathmandu",
    "pokhara": "Pokhara",
    "bhaktapur": "Bhaktapur",
    "lalitpur": "Lalitpur",
}

# ---------------------------------------------------------------------------
# CSS — refined dark theme with semantic tokens
# ---------------------------------------------------------------------------
CSS = """
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap');

:root {
  --bg: #07080c;
  --bg-2: #0b0d14;
  --surface: #0f1218;
  --surface-2: #151924;
  --surface-3: #1c2130;
  --border: rgba(255,255,255,0.08);
  --border-strong: rgba(255,255,255,0.14);
  --text: #e7ebf3;
  --text-dim: #9aa3b2;
  --text-faint: #6b7384;
  --accent: #6366f1;
  --accent-2: #8b5cf6;
  --accent-3: #22d3ee;
  --accent-glow: rgba(99,102,241,0.35);
  --success: #10b981;
  --danger: #ef4444;
  --radius: 12px;
  --radius-sm: 8px;
}

* { box-sizing: border-box; }

html, body, .gradio-container {
  background:
    radial-gradient(1200px 600px at 80% -10%, rgba(139,92,246,0.10), transparent 60%),
    radial-gradient(900px 500px at -10% 30%, rgba(34,211,238,0.08), transparent 60%),
    var(--bg) !important;
  color: var(--text) !important;
  font-family: 'Inter', system-ui, -apple-system, sans-serif !important;
  min-height: 100vh;
}

.gradio-container { max-width: 1180px !important; margin: 0 auto !important; padding: 32px 24px !important; }

/* ---------- Brand ---------- */
.brand { display:flex; align-items:center; gap:14px; margin-bottom: 28px; }
.brand-logo-mark {
  width: 40px; height: 40px; border-radius: 10px;
  background: linear-gradient(135deg, var(--accent), var(--accent-2) 60%, var(--accent-3));
  box-shadow: 0 8px 28px var(--accent-glow), inset 0 1px 0 rgba(255,255,255,0.25);
  display:flex; align-items:center; justify-content:center;
  font-weight: 800; color: white; font-size: 18px; letter-spacing: -0.02em;
}
.brand-name { font-weight: 700; font-size: 17px; letter-spacing: -0.01em; }
.brand-name span { color: var(--text-dim); font-weight: 500; }

/* ---------- Auth layout ---------- */
.auth-grid { display:grid; grid-template-columns: 1.05fr 0.95fr; gap: 28px; align-items: stretch; }
@media (max-width: 900px) { .auth-grid { grid-template-columns: 1fr; } }

.panel {
  background: linear-gradient(180deg, var(--surface) 0%, var(--bg-2) 100%);
  border: 1px solid var(--border);
  border-radius: 18px;
  padding: 32px;
  position: relative;
  overflow: hidden;
}
.panel-hero::before {
  content:""; position:absolute; inset:-1px;
  background: radial-gradient(600px 200px at 0% 0%, rgba(99,102,241,0.18), transparent 60%);
  pointer-events:none;
}

.eyebrow {
  display:inline-flex; align-items:center; gap:8px;
  font-size: 11px; font-weight: 600; letter-spacing: 0.14em; text-transform: uppercase;
  color: var(--text-dim);
  padding: 6px 10px; border: 1px solid var(--border); border-radius: 999px;
  background: rgba(255,255,255,0.02);
}
.eyebrow .dot { width:6px; height:6px; border-radius:999px; background: var(--accent-3); box-shadow: 0 0 12px var(--accent-3); }

.hero-title {
  font-size: 38px; line-height: 1.08; font-weight: 800; letter-spacing: -0.02em;
  margin: 18px 0 14px;
}
.grad {
  background: linear-gradient(135deg, #a5b4fc 0%, #c4b5fd 45%, #67e8f9 100%);
  -webkit-background-clip: text; background-clip: text; color: transparent;
}
.hero-sub { color: var(--text-dim); font-size: 15px; line-height: 1.6; max-width: 440px; }

.feature-list { margin-top: 26px; display:flex; flex-direction:column; gap: 10px; }
.feature {
  display:flex; gap:12px; align-items:flex-start;
  padding: 14px 14px;
  border: 1px solid var(--border);
  border-radius: 12px;
  background: rgba(255,255,255,0.025);
  transition: transform .18s ease, border-color .18s ease, background .18s ease;
}
.feature:hover { transform: translateX(2px); border-color: var(--border-strong); background: rgba(255,255,255,0.04); }
.feature-icon {
  flex:none; width:32px; height:32px; border-radius:8px;
  display:flex; align-items:center; justify-content:center;
  background: linear-gradient(135deg, rgba(99,102,241,0.18), rgba(139,92,246,0.18));
  border: 1px solid rgba(139,92,246,0.25);
  font-size: 15px;
}
.feature-title { font-weight: 600; font-size: 14px; margin-bottom: 2px; }
.feature-desc { color: var(--text-dim); font-size: 13px; line-height: 1.5; }

/* ---------- Form panel ---------- */
.form-title { font-size: 22px; font-weight: 700; letter-spacing: -0.01em; margin-bottom: 4px; }
.form-sub { color: var(--text-dim); font-size: 14px; margin-bottom: 22px; }

.section-label {
  display:flex; align-items:center; gap:10px;
  font-size: 11px; font-weight: 600; letter-spacing: 0.12em; text-transform: uppercase;
  color: var(--text-faint);
  margin: 18px 0 10px;
}
.section-label::after { content:""; flex:1; height:1px; background: var(--border); }

/* Gradio component overrides */
.gradio-container .block, .gradio-container .form { background: transparent !important; border: none !important; }
.gradio-container label > span { color: var(--text-dim) !important; font-size: 12px !important; font-weight: 500 !important; }

.gradio-container input[type="text"],
.gradio-container input[type="email"],
.gradio-container input[type="password"],
.gradio-container textarea,
.gradio-container .wrap.svelte-1ipelgc,
.gradio-container .secondary-wrap {
  background: var(--surface-2) !important;
  border: 1px solid var(--border) !important;
  color: var(--text) !important;
  border-radius: 10px !important;
  height: 44px !important;
  font-size: 14px !important;
  transition: border-color .15s ease, box-shadow .15s ease, background .15s ease !important;
}
.gradio-container textarea { height: auto !important; min-height: 80px !important; padding: 12px !important; }

.gradio-container input:focus,
.gradio-container textarea:focus {
  border-color: var(--accent) !important;
  box-shadow: 0 0 0 4px rgba(99,102,241,0.18) !important;
  background: var(--surface-3) !important;
  outline: none !important;
}

/* Dropdowns */
.gradio-container .dropdown, .gradio-container ul.options {
  background: var(--surface-2) !important;
  border: 1px solid var(--border) !important;
  color: var(--text) !important;
  border-radius: 10px !important;
}

/* Primary button */
.gradio-container .primary, .gradio-container button.lg.primary, .gradio-container button[variant="primary"] {
  background: linear-gradient(135deg, var(--accent) 0%, var(--accent-2) 100%) !important;
  color: white !important;
  border: none !important;
  border-radius: 10px !important;
  height: 46px !important;
  font-weight: 600 !important;
  font-size: 14px !important;
  letter-spacing: 0.01em !important;
  box-shadow: 0 10px 30px -8px var(--accent-glow), inset 0 1px 0 rgba(255,255,255,0.18) !important;
  transition: transform .15s ease, filter .15s ease, box-shadow .15s ease !important;
}
.gradio-container .primary:hover { transform: translateY(-1px); filter: brightness(1.08); box-shadow: 0 14px 36px -8px var(--accent-glow) !important; }
.gradio-container .primary:active { transform: translateY(0); }

/* Status pill */
.status-pill {
  display:inline-flex; align-items:center; gap:8px;
  padding: 8px 14px; border-radius: 999px;
  background: rgba(16,185,129,0.10);
  border: 1px solid rgba(16,185,129,0.35);
  color: #6ee7b7; font-size: 13px; font-weight: 500;
}
.status-pill.error { background: rgba(239,68,68,0.10); border-color: rgba(239,68,68,0.35); color: #fca5a5; }
.status-pill .pulse {
  width:8px; height:8px; border-radius:999px; background: currentColor;
  box-shadow: 0 0 0 0 currentColor;
  animation: pulse 1.8s infinite;
}
@keyframes pulse {
  0% { box-shadow: 0 0 0 0 rgba(110,231,183,0.6); }
  70% { box-shadow: 0 0 0 10px rgba(110,231,183,0); }
  100% { box-shadow: 0 0 0 0 rgba(110,231,183,0); }
}

.auth-footer { margin-top: 18px; text-align: center; color: var(--text-faint); font-size: 12px; }
.auth-footer a { color: var(--text-dim); text-decoration: none; border-bottom: 1px dashed var(--border-strong); }

/* ---------- Chat view ---------- */
.chat-header {
  display:flex; align-items:center; justify-content:space-between;
  padding: 18px 22px; margin-bottom: 16px;
  background: linear-gradient(180deg, var(--surface) 0%, var(--bg-2) 100%);
  border: 1px solid var(--border); border-radius: 14px;
}
.chat-header-title { font-weight: 700; font-size: 16px; letter-spacing: -0.01em; }
.chat-header-sub { color: var(--text-dim); font-size: 12px; margin-top: 2px; }

.gradio-container .message { font-size: 14px !important; line-height: 1.6 !important; }
.gradio-container code, .gradio-container pre { font-family: 'JetBrains Mono', monospace !important; }
"""

# ---------------------------------------------------------------------------
# HTML fragments
# ---------------------------------------------------------------------------
BRAND_HTML = """
<div class="brand">
  <div class="brand-logo-mark">A</div>
  <div class="brand-name">Agent Portal <span>· Multi-Tenant</span></div>
</div>
"""

HERO_HTML = """
<span class="eyebrow"><span class="dot"></span> Secure workspace</span>
<h1 class="hero-title">Your AI agents,<br/><span class="grad">organized by workspace.</span></h1>
<p class="hero-sub">Sign in to your organization to chat with branch-specific AI agents trained on your data, your tone, and your operations.</p>

<div class="feature-list">
  <div class="feature">
    <div class="feature-icon">🏢</div>
    <div>
      <div class="feature-title">Workspace isolation</div>
      <div class="feature-desc">Each tenant runs in its own secure context with scoped data access.</div>
    </div>
  </div>
  <div class="feature">
    <div class="feature-icon">⚡</div>
    <div>
      <div class="feature-title">Branch-aware responses</div>
      <div class="feature-desc">Agents adapt to the location, services, and policies of the selected branch.</div>
    </div>
  </div>
  <div class="feature">
    <div class="feature-icon">🔐</div>
    <div>
      <div class="feature-title">JWT-authenticated</div>
      <div class="feature-desc">Every request is signed and verified against your identity provider.</div>
    </div>
  </div>
</div>
"""

WORKSPACE_LABEL_HTML = '<div class="section-label">Workspace</div>'
ACCOUNT_LABEL_HTML  = '<div class="section-label">Account</div>'

CHAT_HEADER_HTML = """
<div class="chat-header">
  <div>
    <div class="chat-header-title">AI Assistant</div>
    <div class="chat-header-sub">Connected to your workspace</div>
  </div>
  <div class="status-pill"><span class="pulse"></span> Live</div>
</div>
"""

# ---------------------------------------------------------------------------
# Logic
# ---------------------------------------------------------------------------
def update_branches(org):
    branches = TENANT_MAP.get(org, [])
    pretty = [(BRANCH_LABELS.get(b, b), b) for b in branches]
    return gr.update(choices=pretty, value=branches[0] if branches else None)

def authenticate(org, branch, username, email, password):
    if not all([org, branch, username, email, password]):
        return (
            gr.update(value='<div class="status-pill error">⚠ Please fill in every field.</div>'),
            "",
            gr.update(visible=True),
            gr.update(visible=False),
        )
    try:
        r = requests.post(
            f"{API_URL}/auth/authenticate",
            json={"org_id": org, "branch_id": branch, "username": username, "email": email, "password": password},
            timeout=10,
        )
        if r.status_code == 200:
            token = r.json().get("token", "")
            return (
                gr.update(value='<div class="status-pill"><span class="pulse"></span> Authenticated</div>'),
                token,
                gr.update(visible=False),
                gr.update(visible=True),
            )
        msg = r.json().get("detail", "Authentication failed")
        return (
            gr.update(value=f'<div class="status-pill error">✗ {msg}</div>'),
            "",
            gr.update(visible=True),
            gr.update(visible=False),
        )
    except Exception as e:
        return (
            gr.update(value=f'<div class="status-pill error">✗ {e}</div>'),
            "",
            gr.update(visible=True),
            gr.update(visible=False),
        )

def chat_fn(message, history, token):
    if not token:
        return "Session expired. Please sign in again."
    try:
        r = requests.post(
            f"{API_URL}/chat",
            json={"text": message, "history": history},
            headers={"Authorization": f"Bearer {token}"},
            timeout=30,
        )
        return r.json().get("response", "(no reply)")
    except Exception as e:
        return f"Error: {e}"

# ---------------------------------------------------------------------------
# UI
# ---------------------------------------------------------------------------
with gr.Blocks(css=CSS, title="Agent Portal", theme=gr.themes.Base()) as demo:
    jwt_token = gr.State("")

    gr.HTML(BRAND_HTML)

    # ── Auth ────────────────────────────────────────────────────────────────
    with gr.Group(visible=True, elem_id="auth-view") as auth_view:
        with gr.Row(elem_classes="auth-grid"):
            with gr.Column(elem_classes="panel panel-hero"):
                gr.HTML(HERO_HTML)

            with gr.Column(elem_classes="panel"):
                gr.HTML('<div class="form-title">Sign in</div>'
                        '<div class="form-sub">Choose your workspace and continue.</div>')

                gr.HTML(WORKSPACE_LABEL_HTML)
                org_dd = gr.Dropdown(
                    choices=[(ORG_LABELS[o], o) for o in TENANT_MAP],
                    label="Organization",
                    value=None,
                )
                branch_dd = gr.Dropdown(
                    choices=[],
                    label="Branch",
                    value=None,
                )

                org_dd.change(update_branches, inputs=org_dd, outputs=branch_dd)

                gr.HTML(ACCOUNT_LABEL_HTML)
                username = gr.Textbox(label="Username", placeholder="your.username")
                email    = gr.Textbox(label="Email", placeholder="you@company.com")
                password = gr.Textbox(label="Password", type="password", placeholder="••••••••")

                auth_btn = gr.Button("Sign in to workspace", variant="primary")
                auth_status = gr.HTML()

                gr.HTML('<div class="auth-footer">Need help? <a href="#">Contact support</a></div>')

    # ── Chat ────────────────────────────────────────────────────────────────
    with gr.Group(visible=False, elem_id="chat-view") as chat_view:
        gr.HTML(CHAT_HEADER_HTML)
        gr.ChatInterface(chat_fn, additional_inputs=[jwt_token])

    # ── Wire ────────────────────────────────────────────────────────────────
    auth_btn.click(
        fn=authenticate,
        inputs=[org_dd, branch_dd, username, email, password],
        outputs=[auth_status, jwt_token, auth_view, chat_view],
    )
    
if __name__ == "__main__":
    demo.launch()