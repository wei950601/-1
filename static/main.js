// --- Simple search that jumps to pages ---
const searchInput = document.getElementById('search-input');
const searchResults = document.getElementById('search-results');
if (searchInput) {
  searchInput.addEventListener('input', async (e)=>{
    const q = e.target.value.trim();
    if (!q) { searchResults.style.display='none'; searchResults.innerHTML=''; return; }
    const res = await fetch(`/search?q=${encodeURIComponent(q)}`).then(r=>r.json());
    searchResults.innerHTML = res.map(r=>`<a href="${r.url}">${r.title}</a>`).join('');
    searchResults.style.display = res.length ? 'block':'none';
  });
  searchResults.addEventListener('click', (e)=>{
    if (e.target.tagName === 'A') {
      // browser will navigate, that's enough
      searchResults.style.display='none';
    }
  });
}

// --- Settings modal & localStorage ---
const settingsBtn = document.getElementById('btn-settings');
const settingsModal = document.getElementById('settings-modal');
const closeSettingsBtn = document.getElementById('btn-close-settings');
const leftVol = document.getElementById('vol-left');
const rightVol = document.getElementById('vol-right');
const notifyRadios = document.querySelectorAll('input[name=notify]');
const themeRadios = document.querySelectorAll('input[name=theme]');
const autoCheck = document.getElementById('auto-checkin');

function applyTheme(){
  const theme = localStorage.getItem('theme') || 'color';
  document.body.dataset.theme = theme;
  themeRadios.forEach(r=> r.checked = (r.value===theme));
}
function loadSettings(){
  leftVol.value = parseFloat(localStorage.getItem('volLeft') || '0.3');
  rightVol.value = parseFloat(localStorage.getItem('volRight') || '0.3');
  const notify = localStorage.getItem('notify') || 'on';
  notifyRadios.forEach(r=> r.checked = (r.value===notify));
  autoCheck.checked = (localStorage.getItem('autoCheckin') === 'true');
  applyTheme();
}

function saveSettings(){
  localStorage.setItem('volLeft', leftVol.value);
  localStorage.setItem('volRight', rightVol.value);
  const notify = [...notifyRadios].find(r=>r.checked)?.value || 'on';
  localStorage.setItem('notify', notify);
  localStorage.setItem('autoCheckin', autoCheck.checked ? 'true' : 'false');
  const theme = [...themeRadios].find(r=>r.checked)?.value || 'color';
  localStorage.setItem('theme', theme);
  applyTheme();
}
if (settingsBtn){
  settingsBtn.addEventListener('click', ()=>{
    loadSettings();
    settingsModal.classList.remove('hidden');
  });
  closeSettingsBtn.addEventListener('click', ()=>{
    saveSettings();
    settingsModal.classList.add('hidden');
  });
}

// --- Random light music using WebAudio API with L/R volume ---
(function(){
  const AudioContext = window.AudioContext || window.webkitAudioContext;
  if (!AudioContext) return;
  const ctx = new AudioContext();
  // Create per-channel oscillators & gains
  const merger = ctx.createChannelMerger(2);
  const leftGain = ctx.createGain(); const rightGain = ctx.createGain();
  leftGain.gain.value = parseFloat(localStorage.getItem('volLeft') || '0.3');
  rightGain.gain.value = parseFloat(localStorage.getItem('volRight') || '0.3');
  leftGain.connect(merger, 0, 0);
  rightGain.connect(merger, 0, 1);
  merger.connect(ctx.destination);

  function gentleOsc(gainNode){
    const osc = ctx.createOscillator();
    osc.type = 'sine';
    osc.frequency.value = 220 + Math.random()*200; // soft notes
    osc.connect(gainNode);
    osc.start();
    // drift frequency slowly
    setInterval(()=>{
      const target = 220 + Math.random()*300;
      const now = ctx.currentTime;
      try{
        osc.frequency.linearRampToValueAtTime(target, now+2.0);
      }catch(e){}
    }, 1800 + Math.random()*800);
    return osc;
  }
  const leftOsc = gentleOsc(leftGain);
  const rightOsc = gentleOsc(rightGain);

  function updateVolumes(){
    leftGain.gain.value = parseFloat(localStorage.getItem('volLeft') || '0.3');
    rightGain.gain.value = parseFloat(localStorage.getItem('volRight') || '0.3');
  }
  // react to UI sliders
  if (leftVol && rightVol){
    leftVol.addEventListener('input', ()=>{ localStorage.setItem('volLeft', leftVol.value); updateVolumes(); });
    rightVol.addEventListener('input', ()=>{ localStorage.setItem('volRight', rightVol.value); updateVolumes(); });
  }
  // resume audio on first user gesture (autoplay policies)
  function resume(){ if (ctx.state !== 'running') ctx.resume(); window.removeEventListener('click', resume); }
  window.addEventListener('click', resume);
})();
