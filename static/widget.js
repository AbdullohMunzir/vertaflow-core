// /home/kinfolkt/verta-platform/static/widget.js
/**
 * VertaFlow AI — Embeddable Omnichannel Sales Chat Widget
 * Drop-in script for any website to deploy an active AI Sales Closer in seconds.
 * 
 * Usage:
 * <script src="http://localhost:8000/static/widget.js" data-api-url="http://localhost:8000"></script>
 */

(function () {
  'use strict';

  // Detect script attributes
  const currentScript = document.currentScript;
  const API_URL = (currentScript && currentScript.getAttribute('data-api-url')) || window.location.origin;
  const ACCENT_COLOR = '#B5F87B';
  const ACCENT_BORDER = '#9DE959';
  const ACCENT_DARK = '#1A3E08';

  // Retrieve or create persistent session ID
  let sessionId = localStorage.getItem('verta_widget_session_id');
  if (!sessionId) {
    sessionId = 'web_' + Math.random().toString(36).substring(2, 10);
    localStorage.setItem('verta_widget_session_id', sessionId);
  }

  // Inject Styles
  const style = document.createElement('style');
  style.innerHTML = `
    #verta-widget-container * {
      box-sizing: border-box;
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
    }
    #verta-widget-button {
      position: fixed;
      bottom: 24px;
      right: 24px;
      width: 60px;
      height: 60px;
      border-radius: 50%;
      background-color: ${ACCENT_COLOR};
      border: 1.5px solid ${ACCENT_BORDER};
      box-shadow: 0 4px 14px rgba(0,0,0,0.12), 0 2px 6px rgba(0,0,0,0.08);
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: center;
      z-index: 999999;
      transition: all 0.25s cubic-bezier(0.16, 1, 0.3, 1);
    }
    #verta-widget-button:hover {
      transform: scale(1.06);
      box-shadow: 0 6px 20px rgba(0,0,0,0.16);
    }
    #verta-widget-button .pulse-dot {
      position: absolute;
      top: 2px;
      right: 2px;
      width: 14px;
      height: 14px;
      background-color: #22C55E;
      border: 2.5px solid #FFFFFF;
      border-radius: 50%;
    }
    #verta-widget-modal {
      position: fixed;
      bottom: 96px;
      right: 24px;
      width: 375px;
      height: 560px;
      max-width: calc(100vw - 32px);
      max-height: calc(100vh - 120px);
      background-color: #FFFFFF;
      border: 1px solid #E5E7EB;
      border-radius: 20px;
      box-shadow: 0 10px 30px rgba(0,0,0,0.12);
      display: none;
      flex-direction: column;
      overflow: hidden;
      z-index: 999999;
      animation: vertaFadeIn 0.25s ease-out;
    }
    @keyframes vertaFadeIn {
      from { opacity: 0; transform: translateY(12px) scale(0.98); }
      to { opacity: 1; transform: translateY(0) scale(1); }
    }
    .verta-header {
      background-color: #FFFFFF;
      border-bottom: 1px solid #F3F4F6;
      padding: 14px 16px;
      display: flex;
      align-items: center;
      justify-content: space-between;
    }
    .verta-header-left {
      display: flex;
      align-items: center;
      gap: 10px;
    }
    .verta-avatar {
      width: 34px;
      height: 34px;
      border-radius: 50%;
      background-color: ${ACCENT_COLOR};
      display: flex;
      align-items: center;
      justify-content: center;
      font-weight: 800;
      font-size: 14px;
      color: #000;
      border: 1px solid ${ACCENT_BORDER};
    }
    .verta-header-title {
      font-size: 13px;
      font-weight: 700;
      color: #111827;
      line-height: 1.2;
    }
    .verta-header-status {
      font-size: 11px;
      color: #16A34A;
      display: flex;
      align-items: center;
      gap: 4px;
      margin-top: 2px;
    }
    .verta-header-status::before {
      content: '';
      display: inline-block;
      width: 6px;
      height: 6px;
      border-radius: 50%;
      background-color: #16A34A;
    }
    .verta-close-btn {
      background: none;
      border: none;
      font-size: 18px;
      cursor: pointer;
      color: #9CA3AF;
      padding: 4px 8px;
      border-radius: 6px;
    }
    .verta-close-btn:hover {
      color: #111827;
      background-color: #F3F4F6;
    }
    .verta-messages {
      flex: 1;
      overflow-y: auto;
      padding: 14px;
      background-color: #F7F9F6;
      display: flex;
      flex-direction: column;
      gap: 12px;
    }
    .verta-msg-agent {
      align-self: flex-start;
      max-width: 82%;
      background-color: #FFFFFF;
      color: #111827;
      border: 1px solid #E5E7EB;
      padding: 10px 14px;
      border-radius: 16px 16px 16px 4px;
      font-size: 12.5px;
      line-height: 1.45;
      box-shadow: 0 1px 2px rgba(0,0,0,0.03);
    }
    .verta-msg-user {
      align-self: flex-end;
      max-width: 82%;
      background-color: ${ACCENT_COLOR};
      color: #111827;
      border: 1px solid ${ACCENT_BORDER};
      padding: 10px 14px;
      border-radius: 16px 16px 4px 16px;
      font-size: 12.5px;
      line-height: 1.45;
      font-weight: 500;
    }
    .verta-quick-chips {
      display: flex;
      gap: 6px;
      overflow-x: auto;
      padding: 8px 12px;
      background: #FFFFFF;
      border-top: 1px solid #F3F4F6;
    }
    .verta-quick-chips::-webkit-scrollbar {
      display: none;
    }
    .verta-chip {
      white-space: nowrap;
      background-color: #F3F4F6;
      border: 1px solid #E5E7EB;
      border-radius: 14px;
      padding: 5px 10px;
      font-size: 11px;
      font-weight: 600;
      color: #374151;
      cursor: pointer;
      transition: all 0.15s ease;
    }
    .verta-chip:hover {
      background-color: #E5E7EB;
    }
    .verta-input-bar {
      padding: 10px 12px;
      background-color: #FFFFFF;
      border-top: 1px solid #E5E7EB;
      display: flex;
      gap: 8px;
      align-items: center;
    }
    .verta-input {
      flex: 1;
      border: 1px solid #E5E7EB;
      background-color: #F9FAFB;
      border-radius: 20px;
      padding: 8px 14px;
      font-size: 12.5px;
      outline: none;
      color: #111827;
    }
    .verta-input:focus {
      border-color: #000;
      background-color: #FFF;
    }
    .verta-send-btn {
      background-color: ${ACCENT_COLOR};
      border: 1px solid ${ACCENT_BORDER};
      color: #111827;
      font-weight: 700;
      border-radius: 50%;
      width: 36px;
      height: 36px;
      display: flex;
      align-items: center;
      justify-content: center;
      cursor: pointer;
      transition: transform 0.15s ease;
    }
    .verta-send-btn:hover {
      transform: scale(1.08);
    }
    .verta-branding {
      text-align: center;
      font-size: 10px;
      color: #9CA3AF;
      padding: 4px 0 6px 0;
      background-color: #FFFFFF;
    }
  `;
  document.head.appendChild(style);

  // Build Container
  const container = document.createElement('div');
  container.id = 'verta-widget-container';
  container.innerHTML = `
    <!-- Floating Trigger Button -->
    <button id="verta-widget-button" aria-label="Open Chat">
      <svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="#111827" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
      </svg>
      <span class="pulse-dot"></span>
    </button>

    <!-- Chat Modal Window -->
    <div id="verta-widget-modal">
      <div class="verta-header">
        <div class="verta-header-left">
          <div class="verta-avatar">V</div>
          <div>
            <div class="verta-header-title">VertaFlow AI Closer</div>
            <div class="verta-header-status">Onlayn • 3 soniyada javob</div>
          </div>
        </div>
        <button class="verta-close-btn" id="verta-close-btn">✕</button>
      </div>

      <div class="verta-messages" id="verta-messages-body">
        <div class="verta-msg-agent">
          Assalomu alaykum! Sizga qanday mahsulot yoki xizmat bo'yicha yordam bera olaman?
        </div>
      </div>

      <!-- Quick Chips -->
      <div class="verta-quick-chips">
        <button class="verta-chip" data-text="Narxlar haqida ma'lumot bering">💰 Narxlar qanday?</button>
        <button class="verta-chip" data-text="Katalog va namunalarni ko'rish">📦 Katalog</button>
        <button class="verta-chip" data-text="Yetkazib berish xizmati bormi?">🚚 Yetkazib berish</button>
        <button class="verta-chip" data-text="Mutaxassis bilan gaplashmoqchiman">📞 Aloqa</button>
      </div>

      <div class="verta-input-bar">
        <input type="text" id="verta-chat-input" class="verta-input" placeholder="Xabaringizni yozing...">
        <button id="verta-send-btn" class="verta-send-btn" aria-label="Send">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#111827" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
            <line x1="22" y1="2" x2="11" y2="13"></line>
            <polygon points="22 2 15 22 11 13 2 9 22 2"></polygon>
          </svg>
        </button>
      </div>
      <div class="verta-branding">Powered by VertaFlow AI</div>
    </div>
  `;
  document.body.appendChild(container);

  // Interaction handlers
  const btn = document.getElementById('verta-widget-button');
  const modal = document.getElementById('verta-widget-modal');
  const closeBtn = document.getElementById('verta-close-btn');
  const input = document.getElementById('verta-chat-input');
  const sendBtn = document.getElementById('verta-send-btn');
  const messagesBody = document.getElementById('verta-messages-body');

  function toggleModal() {
    if (modal.style.display === 'flex') {
      modal.style.display = 'none';
    } else {
      modal.style.display = 'flex';
      input.focus();
    }
  }

  btn.addEventListener('click', toggleModal);
  closeBtn.addEventListener('click', () => { modal.style.display = 'none'; });

  async function sendMessage(text) {
    const msg = text || input.value.trim();
    if (!msg) return;

    // Render User Message
    const userBubble = document.createElement('div');
    userBubble.className = 'verta-msg-user';
    userBubble.innerText = msg;
    messagesBody.appendChild(userBubble);
    if (!text) input.value = '';
    messagesBody.scrollTop = messagesBody.scrollHeight;

    // Call API
    try {
      const response = await fetch(`${API_URL}/api/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: sessionId, message: msg })
      });
      const data = await response.json();

      // Render Agent Response
      const agentBubble = document.createElement('div');
      agentBubble.className = 'verta-msg-agent';
      agentBubble.innerHTML = (data.reply || "Rahmat! Tez orada javob beramiz.").replace(/\n/g, '<br>');
      messagesBody.appendChild(agentBubble);
      messagesBody.scrollTop = messagesBody.scrollHeight;

    } catch (e) {
      console.error('VertaFlow Widget Network Error:', e);
      const errBubble = document.createElement('div');
      errBubble.className = 'verta-msg-agent';
      errBubble.innerText = "Kechirasiz, aloqada vaqtinchalik uzilish yuz berdi. Qaytadan urinib ko'ring.";
      messagesBody.appendChild(errBubble);
    }
  }

  sendBtn.addEventListener('click', () => sendMessage());
  input.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') sendMessage();
  });

  // Handle Quick Chips
  document.querySelectorAll('.verta-chip').forEach(chip => {
    chip.addEventListener('click', () => {
      const text = chip.getAttribute('data-text');
      sendMessage(text);
    });
  });

})();
