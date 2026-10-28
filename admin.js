(() => {
  const loginPanel = document.getElementById("login-panel");
  const dashboard = document.getElementById("dashboard");
  const logoutBtn = document.getElementById("admin-logout");
  const loginForm = document.getElementById("login-form");
  const loginError = document.getElementById("login-error");
  const photoForm = document.getElementById("upload-photo-form");
  const videoForm = document.getElementById("upload-video-form");
  const photoError = document.getElementById("photo-error");
  const photoOk = document.getElementById("photo-ok");
  const videoError = document.getElementById("video-error");
  const videoOk = document.getElementById("video-ok");
  const photoGrid = document.getElementById("photo-grid");
  const videoGrid = document.getElementById("video-grid");

  const show = (el, text) => {
    if (!el) return;
    el.hidden = !text;
    el.textContent = text || "";
  };

  const escapeHtml = (value) =>
    String(value)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");

  const api = async (url, options = {}) => {
    const res = await fetch(url, {
      credentials: "same-origin",
      ...options,
    });
    let body = null;
    const ct = res.headers.get("content-type") || "";
    if (ct.includes("application/json")) {
      body = await res.json();
    }
    if (!res.ok) {
      const detail = body && body.detail ? body.detail : `HTTP ${res.status}`;
      throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
    }
    return body;
  };

  const setAuthed = (authed) => {
    loginPanel.hidden = authed;
    dashboard.hidden = !authed;
    logoutBtn.hidden = !authed;
  };

  const wireDrop = (form, kind) => {
    const drop = form.querySelector(`[data-drop="${kind}"]`);
    const input = form.querySelector('input[type="file"]');
    const label = form.querySelector(`[data-file-label="${kind}"]`);
    if (!drop || !input || !label) return;

    const setName = () => {
      const file = input.files && input.files[0];
      label.textContent = file
        ? `Выбрано: ${file.name}`
        : "Нажмите или перетащите файл сюда";
      drop.classList.toggle("has-file", Boolean(file));
    };

    input.addEventListener("change", setName);

    ["dragenter", "dragover"].forEach((evt) => {
      drop.addEventListener(evt, (e) => {
        e.preventDefault();
        drop.classList.add("is-drag");
      });
    });
    ["dragleave", "drop"].forEach((evt) => {
      drop.addEventListener(evt, (e) => {
        e.preventDefault();
        drop.classList.remove("is-drag");
      });
    });
    drop.addEventListener("drop", (e) => {
      const file = e.dataTransfer && e.dataTransfer.files && e.dataTransfer.files[0];
      if (!file) return;
      const dt = new DataTransfer();
      dt.items.add(file);
      input.files = dt.files;
      setName();
    });
  };

  wireDrop(photoForm, "photo");
  wireDrop(videoForm, "video");

  const renderPhotos = (items) => {
    if (!items.length) {
      photoGrid.innerHTML =
        '<p class="admin-empty">Пока нет работ. Добавьте первую картину выше.</p>';
      return;
    }
    photoGrid.innerHTML = items
      .map(
        (item) => `
      <article class="admin-row">
        <img class="admin-row__media" src="${escapeHtml(item.url)}" alt="${escapeHtml(item.title)}" />
        <div class="admin-row__body">
          <strong>${escapeHtml(item.title)}</strong>
          <span>${escapeHtml(item.slug)}</span>
        </div>
        <button type="button" class="admin-delete" data-slug="${escapeHtml(item.slug)}" title="Удалить">Удалить</button>
      </article>`
      )
      .join("");
  };

  const renderVideos = (items) => {
    if (!items.length) {
      videoGrid.innerHTML =
        '<p class="admin-empty">Пока нет видео. Добавьте первый ролик выше.</p>';
      return;
    }
    videoGrid.innerHTML = items
      .map(
        (item) => `
      <article class="admin-row">
        <video class="admin-row__media" src="${escapeHtml(item.url)}" ${
          item.poster ? `poster="${escapeHtml(item.poster)}"` : ""
        } muted playsinline preload="metadata"></video>
        <div class="admin-row__body">
          <strong>${escapeHtml(item.title)}</strong>
          <span>${escapeHtml(item.slug)}</span>
        </div>
        <button type="button" class="admin-delete" data-slug="${escapeHtml(item.slug)}" title="Удалить">Удалить</button>
      </article>`
      )
      .join("");
  };

  const loadGallery = async () => {
    const data = await api("/api/gallery");
    const items = Array.isArray(data.items) ? data.items : [];
    renderPhotos(items.filter((i) => i.kind === "image"));
    renderVideos(items.filter((i) => i.kind === "video"));
  };

  const checkSession = async () => {
    try {
      await api("/api/me");
      setAuthed(true);
      await loadGallery();
    } catch {
      setAuthed(false);
    }
  };

  loginForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    show(loginError, "");
    const fd = new FormData(loginForm);
    try {
      await api("/api/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          username: fd.get("username"),
          password: fd.get("password"),
        }),
      });
      loginForm.reset();
      setAuthed(true);
      await loadGallery();
    } catch (err) {
      show(loginError, err.message || "Ошибка входа");
    }
  });

  logoutBtn.addEventListener("click", async () => {
    try {
      await api("/api/logout", { method: "POST" });
    } finally {
      setAuthed(false);
    }
  });

  const resetDropLabel = (form, kind) => {
    const label = form.querySelector(`[data-file-label="${kind}"]`);
    const drop = form.querySelector(`[data-drop="${kind}"]`);
    if (label) label.textContent = "Нажмите или перетащите файл сюда";
    if (drop) drop.classList.remove("has-file");
  };

  photoForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    show(photoError, "");
    show(photoOk, "");
    const fd = new FormData(photoForm);
    const btn = photoForm.querySelector('button[type="submit"]');
    if (btn) btn.disabled = true;
    try {
      await api("/api/photos", { method: "POST", body: fd });
      photoForm.reset();
      resetDropLabel(photoForm, "photo");
      show(photoOk, "Работа опубликована на сайте.");
      await loadGallery();
    } catch (err) {
      show(photoError, err.message || "Не удалось загрузить");
    } finally {
      if (btn) btn.disabled = false;
    }
  });

  videoForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    show(videoError, "");
    show(videoOk, "");
    const fd = new FormData(videoForm);
    const btn = videoForm.querySelector('button[type="submit"]');
    if (btn) btn.disabled = true;
    try {
      await api("/api/videos", { method: "POST", body: fd });
      videoForm.reset();
      resetDropLabel(videoForm, "video");
      show(videoOk, "Видео опубликовано на сайте.");
      await loadGallery();
    } catch (err) {
      show(videoError, err.message || "Не удалось загрузить");
    } finally {
      if (btn) btn.disabled = false;
    }
  });

  const onDelete = async (event) => {
    const btn = event.target.closest(".admin-delete");
    if (!btn) return;
    const slug = btn.getAttribute("data-slug");
    if (!slug) return;
    if (!window.confirm(`Удалить «${slug}» с сайта?`)) return;
    btn.disabled = true;
    try {
      await api(`/api/media/${encodeURIComponent(slug)}`, { method: "DELETE" });
      await loadGallery();
    } catch (err) {
      window.alert(err.message || "Не удалось удалить");
      btn.disabled = false;
    }
  };

  photoGrid.addEventListener("click", onDelete);
  videoGrid.addEventListener("click", onDelete);

  checkSession();
})();
