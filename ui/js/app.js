// OmniDoc Studio Interactive Micro-Animation & Controller
let currentTab = 'home';
let selectedPages = new Set([1, 2]);

window.switchTab = function(tabId) {
  currentTab = tabId;
  const tabs = ['home', 'ocr', 'split', 'merge', 'batch'];
  tabs.forEach(t => {
    const pane = document.getElementById('pane-' + t);
    const navBtn = document.getElementById('nav-' + t);
    if (pane) {
      if (t === tabId) {
        pane.classList.remove('hidden');
        pane.classList.add('flex', 'tab-pane-transition');
      } else {
        pane.classList.add('hidden');
        pane.classList.remove('flex', 'tab-pane-transition');
      }
    }
    if (navBtn) {
      if (t === tabId) {
        navBtn.classList.add('text-primary', 'border-b-2', 'border-primary', 'font-semibold');
        navBtn.classList.remove('text-on-surface-variant');
      } else {
        navBtn.classList.remove('text-primary', 'border-b-2', 'border-primary', 'font-semibold');
        navBtn.classList.add('text-on-surface-variant');
      }
    }
  });
};

window.showNotification = function(msg, type = 'info') {
  const toast = document.createElement('div');
  const bg = type === 'success' ? 'bg-[#059669]' : 'bg-[#0b1c30]';
  toast.className = `fixed bottom-6 right-6 z-50 px-4 py-2.5 rounded-xl shadow-2xl text-white font-medium text-[12px] flex items-center gap-2 ${bg} toast-anim`;
  toast.innerHTML = `<span class="material-symbols-outlined text-[18px]">${type === 'success' ? 'check_circle' : 'info'}</span> <span>${msg}</span>`;
  document.body.appendChild(toast);
  setTimeout(() => {
    toast.style.transition = 'all 0.3s ease';
    toast.style.opacity = '0';
    toast.style.transform = 'translateY(12px)';
    setTimeout(() => toast.remove(), 300);
  }, 2800);
};

window.toggleCardSelection = function(el, pageNum) {
  if (selectedPages.has(pageNum)) {
    selectedPages.delete(pageNum);
    el.classList.remove('border-2', 'border-primary', 'anim-glow');
    el.classList.add('border', 'border-outline-variant');
    const badge = el.querySelector('.status-badge');
    if (badge) {
      badge.textContent = 'READY';
      badge.className = 'status-badge text-[10px] font-mono text-outline';
    }
  } else {
    selectedPages.add(pageNum);
    el.classList.add('border-2', 'border-primary', 'anim-glow');
    el.classList.remove('border', 'border-outline-variant');
    const badge = el.querySelector('.status-badge');
    if (badge) {
      badge.textContent = 'SELECTED';
      badge.className = 'status-badge text-[10px] font-mono font-bold px-2 py-0.5 rounded bg-primary text-white';
    }
  }
};

window.runOCRSimulation = function() {
  const bar = document.getElementById('ocr-prog-bar');
  const lbl = document.getElementById('ocr-prog-text');
  const btn = document.getElementById('btn-run-ocr');
  const logBox = document.getElementById('terminal-log-content');
  if (btn) {
    btn.disabled = true;
    btn.classList.add('opacity-75', 'cursor-not-allowed');
  }
  let prog = 10;
  const logs = [
    "[Phase 1] Adaptive CLAHE contrast enhancement & deskew complete (0.38s)",
    "[Phase 2] PaddleOCR detected 18 text spans & structured header block",
    "[Phase 3] OpenRouter Gemini 2.0 Flash executing column reconciliation",
    "[Phase 4] DOCX synthesis completed with custom Calibri typography & styles"
  ];
  let logIdx = 0;
  if (bar) bar.style.width = '10%';
  if (lbl) lbl.textContent = `Analyzing Glyphs & Document Hierarchy — 10%`;
  
  const timer = setInterval(() => {
    prog += 22;
    if (bar) bar.style.width = Math.min(prog, 100) + '%';
    if (lbl) lbl.textContent = `Analyzing Glyphs & Document Hierarchy — ${Math.min(prog, 100)}%`;
    
    if (logBox && logIdx < logs.length) {
      const line = document.createElement('div');
      const timeStr = new Date().toTimeString().split(' ')[0];
      line.className = 'text-blue-900 font-semibold';
      line.textContent = `[${timeStr}] ${logs[logIdx]}`;
      logBox.appendChild(line);
      logBox.scrollTop = logBox.scrollHeight;
      logIdx++;
    }
    
    if (prog >= 100) {
      clearInterval(timer);
      if (btn) {
        btn.disabled = false;
        btn.classList.remove('opacity-75', 'cursor-not-allowed');
      }
      if (lbl) lbl.textContent = `Document Reconstructed into Word (.docx) — 100%`;
      window.showNotification("Document extraction complete! Saved to Extracted Files.", "success");
    }
  }, 400);
};

document.addEventListener('DOMContentLoaded', () => {
  // Add interactive ripples on buttons
  document.querySelectorAll('.btn-action').forEach(btn => {
    btn.addEventListener('click', function(e) {
      const circle = document.createElement('span');
      const d = Math.max(this.clientWidth, this.clientHeight);
      circle.style.width = circle.style.height = `${d}px`;
      circle.style.left = `${e.clientX - this.getBoundingClientRect().left - d/2}px`;
      circle.style.top = `${e.clientY - this.getBoundingClientRect().top - d/2}px`;
      circle.classList.add('absolute', 'bg-white/30', 'rounded-full', 'pointer-events-none');
      circle.style.animation = 'rippleEffect 0.6s linear';
      this.appendChild(circle);
      setTimeout(() => circle.remove(), 600);
    });
  });
});
