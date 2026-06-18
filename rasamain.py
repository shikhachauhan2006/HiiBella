# rasamain.py — Bella Chatbot
# FastAPI server — receives messages, calls Rasa, falls back to Gemini AI
# Run: uvicorn rasamain:app --reload --port 8000

import os
import uuid
import httpx
import pymysql
from datetime import datetime
from typing import Optional, List
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

# ── Config — now reads from .env / Render environment variables ────────────────
RASA_SERVER_URL = os.getenv("RASA_SERVER_URL", "http://localhost:5005")
GEMINI_API_KEY  = os.getenv("GEMINI_API_KEY", "AIzaSyCsXkAoUzFgCXUXGkffHwi9fGtrSYMXeMo")
GEMINI_MODEL    = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")

DB_CONFIG = {
    "host":     os.getenv("DB_HOST", "localhost"),
    "user":     os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASSWORD", "shikha142"),
    "database": os.getenv("DB_NAME", "project_marketplace"),
    "charset":  "utf8mb4",
}

AI_SYSTEM_PROMPT = """
You are Bella 💙 — a friendly, warm, and helpful AI assistant for Project Marketplace,
a website where users buy and sell projects such as Java, Python, AI/ML,
Web Development, Final Year, and Mini projects.

Your name is Bella. If anyone asks your name, say:
"I'm Bella 💙, your Project Marketplace assistant! How can I help you today?"

Your personality:
- Friendly and warm like a helpful friend
- Use emojis occasionally to make responses lively
- Keep responses short, clear and easy to understand
- Always encourage users to explore projects

Your job:
- Help buyers find the right project by category, price or technology
- Guide sellers to list and sell their projects
- Answer questions about orders, payments, refunds and platform rules
- If asked anything unrelated to the platform, politely say:
  "I'm here to help with Project Marketplace only! 😊 Ask me about projects, buying, or selling."
"""

# ── Configure Gemini ────────────────────────────────────────────────────────────
genai.configure(api_key=GEMINI_API_KEY)
gemini_model = genai.GenerativeModel(
    model_name=GEMINI_MODEL,
    system_instruction=AI_SYSTEM_PROMPT,
)

# ── Database helper ─────────────────────────────────────────────────────────────
def get_db():
    return pymysql.connect(**DB_CONFIG, cursorclass=pymysql.cursors.DictCursor)  # type: ignore

# ── FastAPI app ─────────────────────────────────────────────────────────────────
app = FastAPI(title="Bella — Project Marketplace Chatbot", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Pydantic models ─────────────────────────────────────────────────────────────
class ChatMessage(BaseModel):
    message:    str
    sender_id:  Optional[str] = None
    session_id: Optional[str] = None

class ChatResponse(BaseModel):
    sender_id:  str
    session_id: str
    responses:  List
    handled_by: str

# ── HTML PAGE ───────────────────────────────────────────────────────────────────
HTML_PAGE = """
<!DOCTYPE html>
<html lang="en">
<head>
  <title>Bella 💙 — Project Marketplace</title>
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <style>
    *{box-sizing:border-box;margin:0;padding:0;font-family:'Segoe UI',Arial,sans-serif}
    body{background:linear-gradient(135deg,#0d47a1 0%,#1565c0 50%,#1976d2 100%);display:flex;justify-content:center;align-items:center;min-height:100vh;padding:10px;}
    .chat-box{width:440px;background:#fff;border-radius:22px;box-shadow:0 24px 64px rgba(13,71,161,0.4);overflow:hidden;display:flex;flex-direction:column;height:660px;}
    .chat-header{background:linear-gradient(135deg,#1565c0,#0d47a1);color:#fff;padding:12px 14px;display:flex;align-items:center;gap:8px;flex-shrink:0;}
    .header-avatar{width:40px;height:40px;background:rgba(255,255,255,0.2);border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:20px;flex-shrink:0;}
    .header-info{flex:1}
    .header-name{font-weight:700;font-size:15px}
    .header-status{font-size:11px;opacity:.85;margin-top:1px}
    .status-dot{width:7px;height:7px;background:#69f0ae;border-radius:50%;display:inline-block;margin-right:4px;animation:pulse 2s infinite;}
    @keyframes pulse{0%,100%{opacity:1}50%{opacity:.4}}
    .tabs{display:flex;gap:4px}
    .tab-btn{padding:5px 9px;border-radius:14px;border:1.5px solid rgba(255,255,255,.45);background:transparent;color:rgba(255,255,255,.8);font-size:10.5px;cursor:pointer;transition:all .2s;white-space:nowrap;}
    .tab-btn.active{background:rgba(255,255,255,.25);color:#fff;border-color:#fff;font-weight:700}
    .tab-btn:hover{background:rgba(255,255,255,.2)}
    #chat-panel{flex:1;overflow-y:auto;padding:14px;display:flex;flex-direction:column;gap:8px;background:#e8f0fe;}
    #chat-panel::-webkit-scrollbar{width:4px}
    #chat-panel::-webkit-scrollbar-thumb{background:#90caf9;border-radius:4px}
    .msg-wrap{display:flex;flex-direction:column}
    .msg-wrap.user{align-items:flex-end}
    .msg-wrap.bot{align-items:flex-start}
    .msg{max-width:82%;padding:10px 14px;border-radius:16px;font-size:13.5px;line-height:1.6;white-space:pre-wrap;word-break:break-word;}
    .msg.user{background:linear-gradient(135deg,#1565c0,#0d47a1);color:#fff;border-bottom-right-radius:4px;}
    .msg.bot{background:#fff;color:#222;border-bottom-left-radius:4px;box-shadow:0 1px 5px rgba(0,0,0,.1);}
    .badge{font-size:10px;color:#90a4ae;margin-top:3px;padding:0 4px}
    .typing{display:flex;gap:4px;padding:10px 14px;background:#fff;border-radius:16px;border-bottom-left-radius:4px;width:fit-content;box-shadow:0 1px 5px rgba(0,0,0,.1);}
    .typing span{width:7px;height:7px;background:#90caf9;border-radius:50%;animation:bounce 1.2s infinite;}
    .typing span:nth-child(2){animation-delay:.2s}
    .typing span:nth-child(3){animation-delay:.4s}
    @keyframes bounce{0%,60%,100%{transform:translateY(0)}30%{transform:translateY(-8px)}}
    .quick-replies{padding:8px 10px 4px;display:flex;flex-wrap:wrap;gap:5px;background:#e8f0fe;border-top:1px solid #bbdefb;flex-shrink:0;}
    .qr-btn{padding:5px 11px;background:#fff;border:1.5px solid #1976d2;color:#1565c0;border-radius:20px;font-size:11.5px;cursor:pointer;transition:all .2s;white-space:nowrap;display:flex;align-items:center;gap:4px;}
    .qr-btn:hover{background:#1976d2;color:#fff;transform:translateY(-1px)}
    .cat-label{font-size:10px;color:#90a4ae;padding:5px 14px 2px;background:#e8f0fe;font-weight:700;letter-spacing:.05em;text-transform:uppercase;flex-shrink:0;}
    .categories{padding:4px 10px 8px;display:flex;flex-wrap:wrap;gap:5px;background:#e8f0fe;border-bottom:1px solid #bbdefb;flex-shrink:0;}
    .cat-btn{padding:6px 10px;background:#fff;border:1px solid #bbdefb;color:#444;border-radius:12px;cursor:pointer;transition:all .2s;display:flex;flex-direction:column;align-items:center;gap:2px;min-width:56px;}
    .cat-icon{font-size:18px;line-height:1}
    .cat-btn span:last-child{font-size:10px;font-weight:600;color:#666}
    .cat-btn:hover{border-color:#1976d2;background:#e3f2fd;transform:translateY(-2px);box-shadow:0 3px 8px rgba(21,101,192,.2);}
    .cat-btn:hover span:last-child{color:#1565c0}
    #buy-panel{display:none;flex:1;overflow-y:auto;padding:12px;background:#e8f0fe}
    #buy-panel::-webkit-scrollbar{width:4px}
    #buy-panel::-webkit-scrollbar-thumb{background:#90caf9;border-radius:4px}
    .products-label{font-size:11px;font-weight:700;color:#1565c0;text-transform:uppercase;letter-spacing:.05em;margin-bottom:8px;padding:0 2px;}
    .product-cards{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-bottom:12px;}
    .product-card{background:#fff;border:1px solid #bbdefb;border-radius:14px;padding:10px;cursor:pointer;transition:all .2s;display:flex;flex-direction:column;align-items:center;gap:5px;text-align:center;}
    .product-card:hover{border-color:#1976d2;transform:translateY(-2px);box-shadow:0 4px 12px rgba(21,101,192,.2);background:#e3f2fd;}
    .product-card-icon{font-size:28px;line-height:1}
    .product-card-name{font-size:11.5px;font-weight:700;color:#1a237e}
    .product-card-price{font-size:11px;color:#43a047;font-weight:600}
    .product-card-tag{font-size:10px;background:#e3f2fd;color:#1565c0;padding:2px 7px;border-radius:8px;font-weight:500;}
    .buy-now-btn{background:linear-gradient(135deg,#1976d2,#0d47a1);color:#fff;border:none;border-radius:10px;padding:5px 10px;font-size:10.5px;font-weight:600;cursor:pointer;width:100%;margin-top:3px;transition:transform .2s;}
    .buy-now-btn:hover{transform:scale(1.03)}
    .buy-title{font-size:13.5px;font-weight:700;color:#0d47a1;margin:4px 0 10px;text-align:center;padding:10px;background:#fff;border-radius:12px;border:1px solid #bbdefb;}
    .buy-step{display:flex;gap:11px;align-items:flex-start;background:#fff;border-radius:13px;padding:11px;margin-bottom:7px;border:1px solid #e3f2fd;box-shadow:0 1px 4px rgba(0,0,0,.05);transition:transform .2s;}
    .buy-step:hover{transform:translateX(4px);border-color:#90caf9}
    .buy-icon{width:42px;height:42px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:20px;flex-shrink:0;}
    .buy-step-title{font-size:12.5px;font-weight:700;color:#1a237e;margin-bottom:2px}
    .buy-step-desc{font-size:11.5px;color:#546e7a;line-height:1.5}
    .buy-help-box{background:#e3f2fd;border-radius:13px;padding:12px;margin-top:8px;text-align:center;border:1px solid #90caf9;}
    .buy-ask-btn{background:linear-gradient(135deg,#1976d2,#0d47a1);color:#fff;border:none;border-radius:20px;padding:8px 20px;font-size:12px;font-weight:700;cursor:pointer;transition:transform .2s;}
    .buy-ask-btn:hover{transform:scale(1.05)}
    #sell-panel{display:none;flex:1;overflow-y:auto;padding:12px;background:#e8f0fe}
    #sell-panel::-webkit-scrollbar{width:4px}
    #sell-panel::-webkit-scrollbar-thumb{background:#90caf9;border-radius:4px}
    .sell-title{font-size:13.5px;font-weight:700;color:#0d47a1;margin-bottom:10px;text-align:center;padding:10px;background:#fff;border-radius:12px;border:1px solid #bbdefb;}
    .sell-step{display:flex;gap:11px;align-items:flex-start;background:#fff;border-radius:13px;padding:11px;margin-bottom:7px;border:1px solid #e3f2fd;box-shadow:0 1px 4px rgba(0,0,0,.05);transition:transform .2s;}
    .sell-step:hover{transform:translateX(4px);border-color:#90caf9}
    .sell-icon{width:42px;height:42px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:20px;flex-shrink:0;}
    .sell-step-title{font-size:12.5px;font-weight:700;color:#1a237e;margin-bottom:2px}
    .sell-step-desc{font-size:11.5px;color:#546e7a;line-height:1.5}
    .sell-earn-box{background:#e8f5e9;border-radius:13px;padding:12px;margin-top:8px;text-align:center;border:1px solid #a5d6a7;}
    .chat-input{display:flex;border-top:1px solid #e3f2fd;padding:10px 12px;gap:8px;background:#fff;align-items:center;flex-shrink:0;}
    .chat-input input{flex:1;padding:10px 14px;border:1.5px solid #bbdefb;border-radius:24px;font-size:13.5px;outline:none;transition:border .2s;background:#e8f0fe;}
    .chat-input input:focus{border-color:#1976d2;background:#fff}
    .send-btn{width:40px;height:40px;background:linear-gradient(135deg,#1976d2,#0d47a1);color:#fff;border:none;border-radius:50%;cursor:pointer;font-size:16px;display:flex;align-items:center;justify-content:center;transition:transform .2s;flex-shrink:0;}
    .send-btn:hover{transform:scale(1.1)}
  </style>
</head>
<body>
<div class="chat-box">
  <div class="chat-header">
    <div class="header-avatar">💙</div>
    <div class="header-info">
      <div class="header-name">Bella</div>
      <div class="header-status"><span class="status-dot"></span>Online — Ready to help!</div>
    </div>
    <div class="tabs">
      <button class="tab-btn active" id="tab-chat" onclick="showTab('chat')">💬 Chat</button>
      <button class="tab-btn" id="tab-buy"  onclick="showTab('buy')">🛒 Buy</button>
      <button class="tab-btn" id="tab-sell" onclick="showTab('sell')">💼 Sell</button>
    </div>
  </div>

  <div id="buy-panel">
    <div class="products-label">🛒 Browse & Buy Projects</div>
    <div class="product-cards">
      <div class="product-card" onclick="send('show me Java projects')"><div class="product-card-icon">☕</div><div class="product-card-name">Java Projects</div><div class="product-card-price">From ₹299</div><div class="product-card-tag">Spring • JSP • JDBC</div><button class="buy-now-btn">🛒 Browse</button></div>
      <div class="product-card" onclick="send('show me Python projects')"><div class="product-card-icon">🐍</div><div class="product-card-name">Python Projects</div><div class="product-card-price">From ₹299</div><div class="product-card-tag">Django • Flask • FastAPI</div><button class="buy-now-btn">🛒 Browse</button></div>
      <div class="product-card" onclick="send('show me AI/ML projects')"><div class="product-card-icon">🤖</div><div class="product-card-name">AI/ML Projects</div><div class="product-card-price">From ₹499</div><div class="product-card-tag">TensorFlow • scikit-learn</div><button class="buy-now-btn">🛒 Browse</button></div>
      <div class="product-card" onclick="send('show me Web Development projects')"><div class="product-card-icon">🌐</div><div class="product-card-name">Web Dev Projects</div><div class="product-card-price">From ₹199</div><div class="product-card-tag">React • HTML • Node.js</div><button class="buy-now-btn">🛒 Browse</button></div>
      <div class="product-card" onclick="send('show me Final Year projects')"><div class="product-card-icon">🎓</div><div class="product-card-name">Final Year</div><div class="product-card-price">From ₹799</div><div class="product-card-tag">Full source + docs</div><button class="buy-now-btn">🛒 Browse</button></div>
      <div class="product-card" onclick="send('show me Mini projects')"><div class="product-card-icon">🔧</div><div class="product-card-name">Mini Projects</div><div class="product-card-price">From ₹99</div><div class="product-card-tag">Quick & easy</div><button class="buy-now-btn">🛒 Browse</button></div>
    </div>
    <div class="buy-title">💙 How to Buy — Step by Step</div>
    <div class="buy-step"><div class="buy-icon" style="background:#e3f2fd">🔍</div><div><div class="buy-step-title">Step 1 — Search a project</div><div class="buy-step-desc">Click any product card above or type in chat.</div></div></div>
    <div class="buy-step"><div class="buy-icon" style="background:#e8f5e9">📋</div><div><div class="buy-step-title">Step 2 — View project details</div><div class="buy-step-desc">Ask Bella for price, tech stack and description.</div></div></div>
    <div class="buy-step"><div class="buy-icon" style="background:#fffde7">🛒</div><div><div class="buy-step-title">Step 3 — Add to cart & login</div><div class="buy-step-desc">Click "Buy Now" and register as a buyer.</div></div></div>
    <div class="buy-step"><div class="buy-icon" style="background:#fff8e1">💳</div><div><div class="buy-step-title">Step 4 — Make payment</div><div class="buy-step-desc">Pay via UPI, Card or Net Banking. 100% secure!</div></div></div>
    <div class="buy-step"><div class="buy-icon" style="background:#f3e5f5">📥</div><div><div class="buy-step-title">Step 5 — Download instantly</div><div class="buy-step-desc">My Orders → Download → Get source code + docs!</div></div></div>
    <div class="buy-step"><div class="buy-icon" style="background:#e0f7fa">⭐</div><div><div class="buy-step-title">Step 6 — Leave a review</div><div class="buy-step-desc">Rate the project and help other buyers!</div></div></div>
    <div class="buy-help-box"><div style="font-size:13px;font-weight:700;color:#0d47a1;margin-bottom:5px">💬 Need help buying?</div><div style="font-size:12px;color:#546e7a;margin-bottom:10px">Ask Bella — she's always here!</div><button class="buy-ask-btn" onclick="showTab('chat');send('how do I buy a project')">Ask Bella →</button></div>
  </div>

  <div id="sell-panel">
    <div class="sell-title">💼 How to Sell Your Project</div>
    <div class="sell-step"><div class="sell-icon" style="background:#e3f2fd">📝</div><div><div class="sell-step-title">Step 1 — Register as seller</div><div class="sell-step-desc">Sign up and choose "Seller" as your account type.</div></div></div>
    <div class="sell-step"><div class="sell-icon" style="background:#e8f5e9">📁</div><div><div class="sell-step-title">Step 2 — Upload your project</div><div class="sell-step-desc">Dashboard → Upload Project → Fill title, description, price.</div></div></div>
    <div class="sell-step"><div class="sell-icon" style="background:#fff8e1">📦</div><div><div class="sell-step-title">Step 3 — Add ZIP file + docs</div><div class="sell-step-desc">Upload source code as ZIP with README instructions.</div></div></div>
    <div class="sell-step"><div class="sell-icon" style="background:#fce4ec">🔍</div><div><div class="sell-step-title">Step 4 — Submit for review</div><div class="sell-step-desc">Our team reviews within 24 hours and approves.</div></div></div>
    <div class="sell-step"><div class="sell-icon" style="background:#e0f7fa">🌐</div><div><div class="sell-step-title">Step 5 — Go live & earn!</div><div class="sell-step-desc">Buyers find and buy your project. You earn 80%!</div></div></div>
    <div class="sell-step"><div class="sell-icon" style="background:#e8f5e9">💰</div><div><div class="sell-step-title">Step 6 — Get paid</div><div class="sell-step-desc">Payments every Monday via UPI or bank. Min: ₹500.</div></div></div>
    <div class="sell-earn-box"><div style="font-size:13px;font-weight:700;color:#2e7d32;margin-bottom:5px">💰 You earn 80% of every sale!</div><div style="font-size:12px;color:#546e7a;margin-bottom:10px">₹499 project → You get ₹399!</div><button class="buy-ask-btn" onclick="showTab('chat');send('how do I sell my project')">Ask Bella how to sell →</button></div>
  </div>

  <div id="chat-panel">
    <div class="msg-wrap bot">
      <div class="msg bot">Hi! 👋 I'm <b>Bella</b> 💙, your Project Marketplace assistant!<br>I can help you find projects to buy or guide you to sell yours.<br><br>What would you like to do today?</div>
    </div>
  </div>

  <div class="quick-replies" id="quick-replies">
    <button class="qr-btn" onclick="send('show me projects')">🛒 Browse</button>
    <button class="qr-btn" onclick="showTab('buy')">💳 How to Buy</button>
    <button class="qr-btn" onclick="showTab('sell')">💼 How to Sell</button>
    <button class="qr-btn" onclick="send('check my order')">📦 My Orders</button>
    <button class="qr-btn" onclick="send('refund policy')">💰 Refund</button>
    <button class="qr-btn" onclick="send('contact support')">📞 Support</button>
    <button class="qr-btn" onclick="send('help')">❓ Help</button>
  </div>

  <div class="cat-label" id="cat-label">Browse by category</div>
  <div class="categories" id="cat-btns">
    <button class="cat-btn" onclick="send('show me Java projects')"><span class="cat-icon">☕</span><span>Java</span></button>
    <button class="cat-btn" onclick="send('show me Python projects')"><span class="cat-icon">🐍</span><span>Python</span></button>
    <button class="cat-btn" onclick="send('show me AI/ML projects')"><span class="cat-icon">🤖</span><span>AI/ML</span></button>
    <button class="cat-btn" onclick="send('show me Web Development projects')"><span class="cat-icon">🌐</span><span>Web Dev</span></button>
    <button class="cat-btn" onclick="send('show me Final Year projects')"><span class="cat-icon">🎓</span><span>Final Year</span></button>
    <button class="cat-btn" onclick="send('show me Mini projects')"><span class="cat-icon">🔧</span><span>Mini</span></button>
  </div>

  <div class="chat-input" id="chat-input-bar">
    <input id="msg" type="text" placeholder="Ask Bella anything..." />
    <button class="send-btn" onclick="sendMessage()">➤</button>
  </div>
</div>

<script>
  const sessionId = crypto.randomUUID();
  function send(text) { showTab('chat'); document.getElementById('msg').value = text; sendMessage(); }
  async function sendMessage() {
    const input = document.getElementById('msg');
    const text  = input.value.trim();
    if (!text) return;
    appendMessage(text, 'user');
    input.value = '';
    const typingEl = showTyping();
    try {
      const res  = await fetch('/chat', { method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({message:text,session_id:sessionId}) });
      const data = await res.json();
      removeTyping(typingEl);
      data.responses.forEach(r => appendMessage(r.text||JSON.stringify(r),'bot',data.handled_by));
    } catch(e) { removeTyping(typingEl); appendMessage('❌ Connection error. Please try again.','bot'); }
  }
  function appendMessage(text,sender,handledBy='') {
    const box=document.getElementById('chat-panel');
    const wrap=document.createElement('div'); wrap.className='msg-wrap '+sender;
    const div=document.createElement('div'); div.className='msg '+sender; div.innerText=text; wrap.appendChild(div);
    if(sender==='bot'&&handledBy){ const badge=document.createElement('div'); badge.className='badge'; badge.innerText=handledBy==='gemini_fallback'?'✨ Bella (AI)':'💙 Bella'; wrap.appendChild(badge); }
    box.appendChild(wrap); box.scrollTop=box.scrollHeight;
  }
  function showTyping() {
    const box=document.getElementById('chat-panel');
    const wrap=document.createElement('div'); wrap.className='msg-wrap bot';
    const t=document.createElement('div'); t.className='typing'; t.innerHTML='<span></span><span></span><span></span>';
    wrap.appendChild(t); box.appendChild(wrap); box.scrollTop=box.scrollHeight; return wrap;
  }
  function removeTyping(el){ if(el&&el.parentNode)el.parentNode.removeChild(el); const b=document.getElementById('chat-panel'); if(b)b.scrollTop=b.scrollHeight; }
  function showTab(tab) {
    ['chat-panel','buy-panel','sell-panel'].forEach(id=>{ document.getElementById(id).style.display='none'; });
    ['tab-chat','tab-buy','tab-sell'].forEach(id=>{ document.getElementById(id).classList.remove('active'); });
    const isChat=tab==='chat';
    document.getElementById('quick-replies').style.display=isChat?'flex':'none';
    document.getElementById('cat-label').style.display=isChat?'block':'none';
    document.getElementById('cat-btns').style.display=isChat?'flex':'none';
    document.getElementById('chat-input-bar').style.display=isChat?'flex':'none';
    if(tab==='chat'){ document.getElementById('chat-panel').style.display='flex'; document.getElementById('tab-chat').classList.add('active'); }
    else if(tab==='buy'){ document.getElementById('buy-panel').style.display='block'; document.getElementById('tab-buy').classList.add('active'); }
    else{ document.getElementById('sell-panel').style.display='block'; document.getElementById('tab-sell').classList.add('active'); }
  }
  document.getElementById('msg').addEventListener('keydown',e=>{ if(e.key==='Enter')sendMessage(); });
</script>
</body>
</html>
"""

# ── Gemini AI Fallback ──────────────────────────────────────────────────────────
async def gemini_fallback(message: str, session_id: str) -> str:
    history = []
    try:
        db  = get_db()
        cur = db.cursor()
        cur.execute(
            "SELECT sender, message_text FROM chat_messages WHERE session_id=%s ORDER BY sent_at DESC LIMIT 6",
            (session_id,)
        )
        rows = cur.fetchall()
        for r in reversed(rows):
            role = "user" if r["sender"] == "user" else "model"
            history.append({"role": role, "parts": [r["message_text"]]})
        db.close()
    except Exception:
        pass
    chat     = gemini_model.start_chat(history=history)
    response = chat.send_message(message)
    return response.text


# ── Save message to MySQL ───────────────────────────────────────────────────────
def save_message(session_id: str, sender: str, text: str,
                 intent: str = None, confidence: float = None,
                 handled_by: str = "rasa"):
    db = None
    try:
        db  = get_db()
        cur = db.cursor()
        cur.execute(
            "INSERT IGNORE INTO chat_sessions (id, started_at) VALUES (%s, %s)",
            (session_id, datetime.now())
        )
        cur.execute(
            """INSERT INTO chat_messages
               (session_id, sender, message_text, intent, confidence, handled_by, sent_at)
               VALUES (%s, %s, %s, %s, %s, %s, %s)""",
            (session_id, sender, text, intent, confidence, handled_by, datetime.now())
        )
        db.commit()
    except Exception as e:
        print(f"[save_message] DB error: {e}")
    finally:
        if db:
            db.close()


# ── ENDPOINTS ───────────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def root():
    return HTMLResponse(content=HTML_PAGE)


@app.post("/chat", response_model=ChatResponse)
async def chat(payload: ChatMessage):
    sender_id  = payload.sender_id  or str(uuid.uuid4())
    session_id = payload.session_id or str(uuid.uuid4())

    save_message(session_id, "user", payload.message)

    rasa_payload = {"sender": sender_id, "message": payload.message}
    handled_by   = "rasa"
    bot_reply    = []

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                f"{RASA_SERVER_URL}/webhooks/rest/webhook",
                json=rasa_payload,
            )
            resp.raise_for_status()
            rasa_responses = resp.json()

        rasa_text  = rasa_responses[0].get("text", "") if rasa_responses else ""
        is_default = any(phrase in rasa_text for phrase in [
            "I'm not sure I understood",
            "Could you rephrase",
            "type 'help'",
            "I didn't understand",
        ])

        if rasa_responses and not is_default:
            bot_reply  = rasa_responses
            handled_by = "rasa"
        else:
            ai_text    = await gemini_fallback(payload.message, session_id)
            bot_reply  = [{"text": ai_text}]
            handled_by = "gemini_fallback"

    except Exception as e:
        print(f"[chat] Rasa error: {e}")
        try:
            ai_text    = await gemini_fallback(payload.message, session_id)
            bot_reply  = [{"text": ai_text}]
            handled_by = "gemini_fallback"
        except Exception as gem_err:
            print(f"[chat] Gemini error: {gem_err}")
            bot_reply  = [{"text": "Sorry, I'm having trouble right now. Please try again in a moment."}]
            handled_by = "error"

    for r in bot_reply:
        save_message(session_id, "bot", r.get("text", ""), handled_by=handled_by)

    return ChatResponse(
        sender_id  = sender_id,
        session_id = session_id,
        responses  = bot_reply,
        handled_by = handled_by,
    )


@app.get("/health")
async def health():
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            resp        = await client.get(f"{RASA_SERVER_URL}/")
            rasa_status = "up" if resp.status_code == 200 else "degraded"
    except Exception:
        rasa_status = "down"
    return {"bella": "up", "rasa": rasa_status, "ai_fallback": GEMINI_MODEL}


@app.get("/projects/search")
async def search_projects(q: str = "", category: str = ""):
    try:
        db  = get_db()
        cur = db.cursor()
        sql = """
            SELECT p.id, p.title, p.price, p.tech_stack, p.difficulty,
                   p.avg_rating, c.name AS category, p.thumbnail_url
            FROM   projects p
            JOIN   categories c ON c.id = p.category_id
            WHERE  p.status = 'approved'
        """
        params = []
        if q:
            sql    += " AND MATCH(p.title, p.description, p.tech_stack) AGAINST (%s IN BOOLEAN MODE)"
            params.append(f"{q}*")
        if category:
            sql    += " AND c.slug = %s"
            params.append(category)
        sql += " ORDER BY p.is_featured DESC, p.total_sales DESC LIMIT 10"
        cur.execute(sql, params)
        results = cur.fetchall()
        return {"projects": results, "count": len(results)}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})
    finally:
        db.close()


@app.get("/chat/history/{session_id}")
async def chat_history(session_id: str):
    try:
        db  = get_db()
        cur = db.cursor()
        cur.execute(
            """SELECT sender, message_text, intent, handled_by, sent_at
               FROM chat_messages WHERE session_id=%s ORDER BY sent_at ASC""",
            (session_id,)
        )
        messages = cur.fetchall()
        for m in messages:
            if m.get("sent_at"):
                m["sent_at"] = str(m["sent_at"])
        return {"session_id": session_id, "messages": messages}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})
    finally:
        db.close()
