// static/js/main.js — YT Video Builder

document.addEventListener('DOMContentLoaded', () => {

  /* ============================================================
     REFS
  ============================================================ */
  const selectedMode    = document.getElementById('selectedMode');
  const vtypeRow        = document.getElementById('vtypeRow');
  const autoAssignCb    = document.getElementById('autoAssign');
  const manualSelection = document.getElementById('manualSelection');
  const musicSelect     = document.getElementById('musicSelect');
  const bgSelect        = document.getElementById('bgSelect');
  const imagesZip       = document.getElementById('imagesZip');
  const imageHint       = document.getElementById('imageHint');
  const dzDefaultState   = document.getElementById('dzDefaultState');
  const dzActiveState    = document.getElementById('dzActiveState');
  const dzFilenameInner  = document.getElementById('dzFilenameInner');
  const createBatchBtn  = document.getElementById('createBatchBtn');
  const progress        = document.getElementById('progress');
  const result          = document.getElementById('result');

  const musicFile       = document.getElementById('musicFile');
  const bgFile          = document.getElementById('bgFile');
  const chooseMusicBtn  = document.getElementById('chooseMusicBtn');
  const chooseBgBtn     = document.getElementById('chooseBgBtn');
  const uploadMusicBtn  = document.getElementById('uploadMusicBtn');
  const uploadBgBtn     = document.getElementById('uploadBgBtn');
  const musicFilenameEl = document.getElementById('musicFilename');
  const bgFilenameEl    = document.getElementById('bgFilename');

  const assetsZip       = document.getElementById('assetsZip');
  const uploadAssetsZipBtn = document.getElementById('uploadAssetsZipBtn');
  const uploadStatus    = document.getElementById('uploadStatus');
  const batchFilename   = document.getElementById('batchFilename');

  const musicList       = document.getElementById('musicList');
  const bgList          = document.getElementById('bgList');

  const longQueue       = document.getElementById('longQueue');
  const shortQueue      = document.getElementById('shortQueue');
  const longEmpty       = document.getElementById('longEmpty');
  const shortEmpty      = document.getElementById('shortEmpty');
  const longCount       = document.getElementById('longCount');
  const shortCount      = document.getElementById('shortCount');
  const panelLong       = document.getElementById('panelLong');
  const panelShort      = document.getElementById('panelShort');
  const tabLong         = document.getElementById('tabLong');
  const tabShort        = document.getElementById('tabShort');

  const themeToggle     = document.getElementById('themeToggle');
  const themeIcon       = document.getElementById('themeIcon');
  const ytToast         = document.getElementById('ytToast');
  const toastIcon       = document.getElementById('toastIcon');
  const toastTitle      = document.getElementById('toastTitle');
  const toastMsg        = document.getElementById('toastMsg');

  const previewModal    = document.getElementById('previewModal');
  const previewTitle    = document.getElementById('previewTitle');
  const previewPlayer   = document.getElementById('previewPlayer');
  const previewDownload = document.getElementById('previewDownload');
  const previewClose    = document.getElementById('previewClose');

  const notificationBellBtn = document.getElementById('notificationBellBtn');
  const notificationBadge   = document.getElementById('notificationBadge');
  const notificationModal   = document.getElementById('notificationModal');
  const notificationList    = document.getElementById('notificationList');
  const notificationClose   = document.getElementById('notificationClose');
  const clearNotificationsBtn = document.getElementById('clearNotificationsBtn');

  const docsBtn             = document.getElementById('docsBtn');
  const docsModal           = document.getElementById('docsModal');
  const docsContent         = document.getElementById('docsContent');
  const docsClose           = document.getElementById('docsClose');

  let notifications = JSON.parse(localStorage.getItem('yt-notifications')) || [];

  /* ============================================================
     PREVIEW MODAL
  ============================================================ */
  function openPreview(name, url, type) {
    previewTitle.textContent = name;
    previewDownload.href = url;
    previewDownload.setAttribute('download', name);

    if (type === 'music') {
      previewPlayer.innerHTML = `
        <audio controls autoplay style="width:100%; border-radius:8px; outline:none;">
          <source src="${url}">
        </audio>`;
    } else {
      previewPlayer.innerHTML = `
        <video controls autoplay style="width:100%; max-height:360px; border-radius:10px; background:#000; object-fit:contain;">
          <source src="${url}" type="video/mp4">
        </video>`;
    }

    previewModal.style.display = 'flex';
  }

  function closePreview() {
    previewModal.style.display = 'none';
    previewPlayer.innerHTML = ''; // stops playback
  }

  previewClose.addEventListener('click', closePreview);
  previewModal.addEventListener('click', (e) => {
    if (e.target === previewModal) closePreview();
  });
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') closePreview();
  });

  /* ============================================================
     THEME TOGGLE
  ============================================================ */
  function applyTheme(theme) {
    document.documentElement.setAttribute('data-theme', theme);
    themeIcon.className = theme === 'dark' ? 'bi bi-sun-fill' : 'bi bi-moon-fill';
    localStorage.setItem('yt-theme', theme);
  }

  const savedTheme = localStorage.getItem('yt-theme') || 'light';
  applyTheme(savedTheme);

  themeToggle.addEventListener('click', () => {
    const current = document.documentElement.getAttribute('data-theme');
    applyTheme(current === 'dark' ? 'light' : 'dark');
  });

  /* ============================================================
     TOAST & HISTORY NOTIFICATIONS
  ============================================================ */
  let toastTimer = null;
  function showToast(title, msg, icon = '✅') {
    toastIcon.textContent  = icon;
    toastTitle.textContent = title;
    toastMsg.textContent   = msg;
    ytToast.classList.add('show');
    if (toastTimer) clearTimeout(toastTimer);
    toastTimer = setTimeout(() => ytToast.classList.remove('show'), 5000);

    // Save to notification history
    addNotification(title, msg, icon);
  }

  function addNotification(title, msg, icon) {
    const timeStr = new Date().toLocaleTimeString();
    notifications.unshift({ title, msg, icon, time: timeStr });
    localStorage.setItem('yt-notifications', JSON.stringify(notifications));
    updateNotificationBadge();
  }

  function updateNotificationBadge() {
    if (notifications.length > 0) {
      notificationBadge.style.display = 'block';
    } else {
      notificationBadge.style.display = 'none';
    }
  }

  function renderNotifications() {
    if (notifications.length === 0) {
      notificationList.innerHTML = '<div class="text-muted text-center" style="font-size:12.5px; padding:10px 0;">No notifications yet.</div>';
    } else {
      notificationList.innerHTML = notifications.map(n => `
        <div style="border-bottom:1px solid var(--border); padding-bottom:8px; margin-bottom:8px;">
          <div style="display:flex; justify-content:space-between; align-items:center;">
            <strong style="font-size:12px; color:var(--text-primary);">${n.icon} ${n.title}</strong>
            <span style="font-size:10px; color:var(--text-muted);">${n.time}</span>
          </div>
          <p style="font-size:11.5px; color:var(--text-secondary); margin: 2px 0 0 0;">${n.msg}</p>
        </div>
      `).join('');
    }
  }

  notificationBellBtn.addEventListener('click', () => {
    notificationModal.style.display = 'flex';
    notificationBadge.style.display = 'none';
    renderNotifications();
  });

  notificationClose.addEventListener('click', () => {
    notificationModal.style.display = 'none';
  });

  notificationModal.addEventListener('click', (e) => {
    if (e.target === notificationModal) notificationModal.style.display = 'none';
  });

  clearNotificationsBtn.addEventListener('click', () => {
    notifications = [];
    localStorage.setItem('yt-notifications', JSON.stringify(notifications));
    renderNotifications();
    updateNotificationBadge();
  });

  // Init badge state
  updateNotificationBadge();

  /* ============================================================
     DOCS & HELP (README.MD)
  ============================================================ */
  docsBtn.addEventListener('click', async () => {
    docsModal.style.display = 'flex';
    docsContent.textContent = 'Loading documentation...';
    try {
      const resp = await fetch('/api/docs');
      const data = await resp.json();
      if (data.ok) {
        docsContent.textContent = data.content;
      } else {
        docsContent.textContent = 'Error loading documentation.';
      }
    } catch (e) {
      docsContent.textContent = 'Failed to load documentation: ' + e.message;
    }
  });

  docsClose.addEventListener('click', () => {
    docsModal.style.display = 'none';
  });

  docsModal.addEventListener('click', (e) => {
    if (e.target === docsModal) docsModal.style.display = 'none';
  });

  /* ============================================================
     VIDEO TYPE CARDS
  ============================================================ */
  vtypeRow.addEventListener('click', (e) => {
    const card = e.target.closest('.vtype-card');
    if (!card) return;
    document.querySelectorAll('.vtype-card').forEach(c => c.classList.remove('active'));
    card.classList.add('active');
    const mode = card.dataset.mode;
    selectedMode.value = mode;
    imageHint.textContent = mode === 'full'
      ? 'Full: zip must include 15 images.'
      : 'Short: zip must include 2 images.';
  });

  /* ============================================================
     AUTO-ASSIGN TOGGLE
  ============================================================ */
  function syncManual() {
    manualSelection.style.display = autoAssignCb.checked ? 'none' : 'grid';
  }
  autoAssignCb.addEventListener('change', syncManual);
  syncManual();

  /* ============================================================
     DRAG & DROP — Images Zip
  ============================================================ */
  const imageDropzone = document.getElementById('imageDropzone');

  function handleFileSelected(file) {
    if (file) {
      dzFilenameInner.textContent = file.name;
      dzDefaultState.style.display = 'none';
      dzActiveState.style.display = 'block';
    } else {
      dzFilenameInner.textContent = '';
      dzDefaultState.style.display = 'block';
      dzActiveState.style.display = 'none';
    }
  }

  imageDropzone.addEventListener('dragover', (e) => {
    e.preventDefault();
    imageDropzone.classList.add('dragover');
  });
  imageDropzone.addEventListener('dragleave', () => imageDropzone.classList.remove('dragover'));
  imageDropzone.addEventListener('drop', (e) => {
    e.preventDefault();
    imageDropzone.classList.remove('dragover');
    const file = e.dataTransfer.files[0];
    if (file) {
      const dt = new DataTransfer();
      dt.items.add(file);
      imagesZip.files = dt.files;
      handleFileSelected(file);
    }
  });

  imagesZip.addEventListener('change', () => {
    const file = imagesZip.files[0];
    handleFileSelected(file);
  });

  /* ============================================================
     QUEUE TABS
  ============================================================ */
  function switchTab(queue) {
    if (queue === 'long') {
      tabLong.classList.add('active');
      tabShort.classList.remove('active');
      panelLong.classList.add('active');
      panelShort.classList.remove('active');
    } else {
      tabShort.classList.add('active');
      tabLong.classList.remove('active');
      panelShort.classList.add('active');
      panelLong.classList.remove('active');
    }
  }

  tabLong.addEventListener('click',  () => switchTab('long'));
  tabShort.addEventListener('click', () => switchTab('short'));

  function syncQueueEmpty() {
    longEmpty.style.display  = longQueue.children.length === 0  ? 'flex' : 'none';
    shortEmpty.style.display = shortQueue.children.length === 0 ? 'flex' : 'none';
    longCount.textContent  = longQueue.children.length;
    shortCount.textContent = shortQueue.children.length;
  }

  syncQueueEmpty();

  document.getElementById('refreshQueuesBtn').addEventListener('click', () => {
    syncQueueEmpty();
    showToast('Refreshed', 'Queue display is up to date.', '🔄');
  });

  /* ============================================================
     ADD VIDEO CARD TO QUEUE
  ============================================================ */
  function addToQueue(mode, filename, downloadUrl, elapsedTime, jobId) {
    const queue    = mode === 'full' ? longQueue : shortQueue;
    const isShort  = mode === 'short';

    const cleanJobId = jobId || 'single';
    let batchGroup = document.getElementById(`batch-${cleanJobId}`);
    if (!batchGroup) {
      batchGroup = document.createElement('div');
      batchGroup.className = 'batch-group mb-4 pb-3 border-bottom';
      batchGroup.id = `batch-${cleanJobId}`;
      batchGroup.innerHTML = `
        <div style="font-size: 11px; color: var(--text-secondary); font-weight: 700; margin-bottom: 10px; display:flex; justify-content:space-between; align-items:center;">
          <span><i class="bi bi-folder-fill" style="color:var(--accent); margin-right:4px;"></i> BATCH PRODUCTION (${cleanJobId.substring(0, 8).toUpperCase()})</span>
          <span class="batch-time-label" id="batch-time-${cleanJobId}">Completed</span>
        </div>
        <div class="queue-video-grid"></div>
      `;
      queue.prepend(batchGroup);
    }

    const grid = batchGroup.querySelector('.queue-video-grid');

    const card = document.createElement('div');
    card.className = 'queue-card';
    card.innerHTML = `
      <div class="qc-video-wrap${isShort ? ' portrait' : ''}">
        <video controls preload="metadata">
          <source src="${downloadUrl}" type="video/mp4">
        </video>
      </div>
      <div class="qc-body">
        <div class="qc-filename" title="${filename}">${filename}</div>
        <div class="qc-meta">
          ${mode === 'full' ? '🎬 Full Video' : '📱 Short'} &nbsp;•&nbsp; ⏱ ${elapsedTime}s
        </div>
        <div class="qc-actions">
          <a href="${downloadUrl}" class="qc-dl" download>
            <i class="bi bi-download"></i> Download
          </a>
        </div>
      </div>
    `;
    grid.prepend(card);

    // Switch to the relevant tab
    switchTab(mode === 'full' ? 'long' : 'short');
    syncQueueEmpty();
  }

  /* ============================================================
     LOAD ASSETS
  ============================================================ */
  async function loadAssets() {
    try {
      const resp = await fetch('/api/assets');
      const j    = await resp.json();

      musicSelect.innerHTML = '<option value="">(choose music)</option>';
      bgSelect.innerHTML    = '<option value="">(choose background)</option>';
      musicList.innerHTML   = '';
      bgList.innerHTML      = '';

      let musicCountVal = 0;
      let videoCountVal = 0;

      if (j.assets && j.assets.length) {
        j.assets.forEach(a => {
          const isMusic = a.asset_type === 'music';
          if (isMusic) musicCountVal++;
          else         videoCountVal++;

          // populate selects
          const opt = document.createElement('option');
          opt.value = a.id;
          opt.textContent = a.original_name || a.filename;
          if (isMusic) musicSelect.appendChild(opt);
          else         bgSelect.appendChild(opt);

          // build asset item
          const item = document.createElement('div');
          item.className = 'asset-item';
          const assetUrl = `/uploads/assets/${a.filename}`;
          item.innerHTML = `
            <div class="asset-thumb ${isMusic ? 'music' : 'video'}">
              <i class="bi ${isMusic ? 'bi-music-note-beamed' : 'bi-camera-video-fill'}"></i>
            </div>
            <div class="asset-info">
              <strong title="${a.original_name || a.filename}">${a.original_name || a.filename}</strong>
              <span>${isMusic ? 'MP3' : 'MP4'} • ${new Date(a.created_at).toLocaleString()}</span>
            </div>
            <div class="asset-actions">
              <button class="btn-asset" data-preview-url="${assetUrl}" data-preview-name="${a.original_name || a.filename}" data-preview-type="${isMusic ? 'music' : 'video'}" title="Preview">
                <i class="bi bi-play-circle"></i>
              </button>
              <button class="btn-asset del" data-id="${a.id}" data-action="delete" title="Delete">
                <i class="bi bi-trash3"></i>
              </button>
            </div>
          `;
          if (isMusic) musicList.appendChild(item);
          else         bgList.appendChild(item);
        });
      } else {
        musicList.innerHTML = '<div class="text-muted-sm" style="padding:4px 0;">No music uploaded yet.</div>';
        bgList.innerHTML    = '<div class="text-muted-sm" style="padding:4px 0;">No video uploaded yet.</div>';
      }

      document.getElementById('musicCount').textContent = musicCountVal;
      document.getElementById('bgCount').textContent = videoCountVal;
    } catch (err) {
      console.error('loadAssets error', err);
    }
  }

  /* Delete handler */
  function handleDelete(ev) {
    // Preview button
    const previewBtn = ev.target.closest('button[data-preview-url]');
    if (previewBtn) {
      openPreview(
        previewBtn.dataset.previewName,
        previewBtn.dataset.previewUrl,
        previewBtn.dataset.previewType
      );
      return;
    }
    // Delete button
    const btn = ev.target.closest('button[data-action="delete"]');
    if (!btn) return;
    const id = btn.dataset.id;
    if (!confirm('Delete this asset?')) return;
    fetch(`/api/delete_asset/${id}`, { method: 'DELETE' })
      .then(r => r.json())
      .then(j => {
        if (j.ok) { loadAssets(); showToast('Deleted', 'Asset removed.', '🗑️'); }
        else alert('Delete failed: ' + (j.error || 'unknown'));
      })
      .catch(e => alert('Delete failed: ' + e.message));
  }

  musicList.addEventListener('click', handleDelete);
  bgList.addEventListener('click', handleDelete);

  /* ============================================================
     MUSIC UPLOAD
  ============================================================ */
  chooseMusicBtn.addEventListener('click', () => musicFile.click());
  musicFile.addEventListener('change', () => {
    musicFilenameEl.textContent = musicFile.files[0] ? musicFile.files[0].name : 'No file chosen';
  });

  uploadMusicBtn.addEventListener('click', async () => {
    if (!musicFile.files.length) { showToast('Error', 'Choose a music file first.', '❌'); return; }
    const fd = new FormData();
    fd.append('file', musicFile.files[0]);
    fd.append('asset_type', 'music');
    const resp = await fetch('/api/upload_asset', { method: 'POST', body: fd });
    const j    = await resp.json();
    if (j.ok) { showToast('Uploaded', 'Music added to library.', '🎵'); musicFile.value = ''; musicFilenameEl.textContent = 'No file chosen'; loadAssets(); }
    else showToast('Error', j.error || 'Upload failed.', '❌');
  });

  /* ============================================================
     BG VIDEO UPLOAD
  ============================================================ */
  chooseBgBtn.addEventListener('click', () => bgFile.click());
  bgFile.addEventListener('change', () => {
    bgFilenameEl.textContent = bgFile.files[0] ? bgFile.files[0].name : 'No file chosen';
  });

  uploadBgBtn.addEventListener('click', async () => {
    if (!bgFile.files.length) { showToast('Error', 'Choose a background video first.', '❌'); return; }
    const fd = new FormData();
    fd.append('file', bgFile.files[0]);
    fd.append('asset_type', 'bg_video');
    const resp = await fetch('/api/upload_asset', { method: 'POST', body: fd });
    const j    = await resp.json();
    if (j.ok) { showToast('Uploaded', 'Background video added.', '🎞️'); bgFile.value = ''; bgFilenameEl.textContent = 'No file chosen'; loadAssets(); }
    else showToast('Error', j.error || 'Upload failed.', '❌');
  });

  /* ============================================================
     BATCH ZIP UPLOAD
  ============================================================ */
  assetsZip.addEventListener('change', () => {
    batchFilename.textContent = assetsZip.files[0] ? assetsZip.files[0].name : 'No file chosen';
  });

  uploadAssetsZipBtn.addEventListener('click', async () => {
    const file = assetsZip.files[0];
    if (!file) { showToast('Error', 'Please choose a ZIP file.', '❌'); return; }
    uploadStatus.innerHTML = '<div class="yt-alert success">Uploading…</div>';
    const fd = new FormData();
    fd.append('zip', file);
    const resp = await fetch('/api/upload_assets_zip', { method: 'POST', body: fd });
    const j    = await resp.json();
    if (j.ok) {
      const m = j.added.music_files || [];
      const v = j.added.bg_videos   || [];
      uploadStatus.innerHTML = `<div class="yt-alert success">Added ${m.length} music &amp; ${v.length} videos.</div>`;
      assetsZip.value = '';
      batchFilename.textContent = 'No file chosen';
      loadAssets();
      showToast('Batch Uploaded', `${m.length} music + ${v.length} videos added.`, '📦');
    } else {
      uploadStatus.innerHTML = `<div class="yt-alert danger">Error: ${j.error || 'Unknown'}</div>`;
    }
  });

  /* ============================================================
     UPLOAD IMAGES ZIP
  ============================================================ */
  async function uploadImagesZip() {
    if (!imagesZip.files.length) return { ok: false, error: 'No images zip selected' };
    const fd = new FormData();
    fd.append('zip', imagesZip.files[0]);
    const resp = await fetch('/api/upload_images_zip', { method: 'POST', body: fd });
    return resp.json();
  }

  function setLoading(active) {
    progress.classList.toggle('visible', active);
    createBatchBtn.disabled = active;
    if (active) result.innerHTML = '';
  }

  /* ============================================================
     CREATE BATCH
  ============================================================ */
  createBatchBtn.addEventListener('click', async () => {
    setLoading(true);
    const mode       = selectedMode.value;
    const autoAssign = autoAssignCb.checked ? 'true' : 'false';
    const music_id   = autoAssignCb.checked ? '' : musicSelect.value;
    const bg_id      = autoAssignCb.checked ? '' : bgSelect.value;

    const uploadRes = await uploadImagesZip();
    if (!uploadRes.ok) {
      setLoading(false);
      result.innerHTML = `<div class="yt-alert danger">Images upload failed: ${uploadRes.error || 'unknown'}</div>`;
      return;
    }

    const fd = new FormData();
    fd.append('mode',         mode);
    fd.append('images_token', uploadRes.token);
    fd.append('auto_assign',  autoAssign);
    if (music_id) fd.append('music_id', music_id);
    if (bg_id)    fd.append('bg_id',    bg_id);

    try {
      const resp = await fetch('/api/start_batch', { method: 'POST', body: fd });
      const j    = await resp.json();
      if (!j.ok) {
        setLoading(false);
        result.innerHTML = `<div class="yt-alert danger">❌ ${j.error}</div>`;
        return;
      }

      // Pre-create the batch group element so user sees it instantly
      const queue = mode === 'full' ? longQueue : shortQueue;
      const batchGroup = document.createElement('div');
      batchGroup.className = 'batch-group mb-4 pb-3 border-bottom';
      batchGroup.id = `batch-${j.job_id}`;
      batchGroup.innerHTML = `
        <div style="font-size: 11px; color: var(--text-secondary); font-weight: 700; margin-bottom: 10px; display:flex; justify-content:space-between; align-items:center;">
          <span><i class="bi bi-folder-fill" style="color:var(--accent); margin-right:4px;"></i> BATCH PRODUCTION (${j.job_id.substring(0, 8).toUpperCase()})</span>
          <span class="batch-time-label" id="batch-time-${j.job_id}" style="color: var(--accent);">Processing...</span>
        </div>
        <div class="queue-video-grid"></div>
      `;
      queue.prepend(batchGroup);
      switchTab(mode === 'full' ? 'long' : 'short');
      syncQueueEmpty();

      // Show terminal style console logs
      result.innerHTML = `
        <div class="yt-alert success py-2" style="font-weight:600;">Processing batch job...</div>
        <div id="batchConsole" style="background:#000; color:#0f0; font-family:monospace; font-size:11px; padding:10px; border-radius:6px; max-height:200px; overflow-y:auto; margin-top:8px; white-space:pre-wrap; text-align:left;"></div>
      `;
      const consoleEl = document.getElementById('batchConsole');

      const eventSource = new EventSource(`/api/job_stream/${j.job_id}`);
      
      eventSource.onmessage = (event) => {
        const data = JSON.parse(event.data);
        if (data.type === 'log') {
          consoleEl.textContent += data.msg + '\n';
          consoleEl.scrollTop = consoleEl.scrollHeight;
        } else if (data.type === 'video_done') {
          addToQueue(mode, data.filename, data.download_url, data.elapsed, j.job_id);
        } else if (data.type === 'done') {
          setLoading(false);
          eventSource.close();
          result.innerHTML = `<div class="yt-alert success py-2">✅ Batch of ${data.count} videos in ${data.elapsed}s!</div>`;
          showToast('Batch Ready!', `${data.count} videos created in ${data.elapsed}s`, '🎬');
          
          // Update batch container header with completion time
          const timeLabel = document.getElementById(`batch-time-${j.job_id}`);
          if (timeLabel) {
            timeLabel.textContent = `Completed in ${data.elapsed}s`;
            timeLabel.style.color = 'var(--text-muted)';
          }

          // Reset zip file selector state
          imagesZip.value = '';
          handleFileSelected(null);
          
          loadAssets();
        } else if (data.type === 'error') {
          setLoading(false);
          eventSource.close();
          result.innerHTML = `<div class="yt-alert danger">❌ Job failed: ${data.msg}</div>`;
          showToast('Job Failed', data.msg, '❌');
          
          const timeLabel = document.getElementById(`batch-time-${j.job_id}`);
          if (timeLabel) {
            timeLabel.textContent = `Failed`;
            timeLabel.style.color = '#dc2626';
          }
        }
      };

      eventSource.onerror = (err) => {
        setLoading(false);
        eventSource.close();
        result.innerHTML = `<div class="yt-alert danger">❌ Connection lost. Check server logs.</div>`;
      };

    } catch (e) {
      setLoading(false);
      result.innerHTML = `<div class="yt-alert danger">❌ Request failed: ${e.message}</div>`;
    }
  });

  /* ============================================================
     INIT
  ============================================================ */
  loadAssets();
});
