const header = document.querySelector("[data-header]");
const year = document.querySelector("[data-year]");
const lightbox = document.querySelector("[data-lightbox]");
const lightboxImg = document.querySelector("[data-lightbox-img]");
const lightboxVideo = document.querySelector("[data-lightbox-video]");
const lightboxCap = document.querySelector("[data-lightbox-cap]");
const gallery = document.querySelector("[data-gallery]");
const dict = window.KASABOV_I18N || {};
const archiveWorks = Array.isArray(window.KASABOV_WORKS) ? window.KASABOV_WORKS : [];
const supported = ["en", "fr", "es", "ru", "zh"];
let works = [...archiveWorks];
let activeFilter = "all";
let currentLang = "en";

if (year) year.textContent = String(new Date().getFullYear());

const onScroll = () => {
  if (!header) return;
  header.classList.toggle("is-scrolled", window.scrollY > 24);
};

onScroll();
window.addEventListener("scroll", onScroll, { passive: true });

function observeReveals(root = document) {
  const revealEls = root.querySelectorAll(".reveal:not(.is-in)");
  if ("IntersectionObserver" in window) {
    const io = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (entry.isIntersecting) {
            entry.target.classList.add("is-in");
            io.unobserve(entry.target);
          }
        }
      },
      { threshold: 0.12, rootMargin: "0px 0px -6% 0px" }
    );
    revealEls.forEach((el) => io.observe(el));
  } else {
    revealEls.forEach((el) => el.classList.add("is-in"));
  }
}

function openLightbox(item, captionText) {
  if (!lightbox) return;
  if (item.type === "video" && lightboxVideo) {
    lightboxImg.hidden = true;
    lightboxImg.removeAttribute("src");
    lightboxVideo.hidden = false;
    lightboxVideo.src = item.src;
    lightboxVideo.poster = item.poster || "";
    lightboxVideo.load();
  } else if (lightboxImg) {
    if (lightboxVideo) {
      lightboxVideo.pause();
      lightboxVideo.removeAttribute("src");
      lightboxVideo.hidden = true;
    }
    lightboxImg.hidden = false;
    lightboxImg.src = item.src;
    lightboxImg.alt = captionText || "";
  }
  if (lightboxCap) lightboxCap.textContent = captionText || "";
  if (typeof lightbox.showModal === "function") lightbox.showModal();
}

function closeLightbox() {
  if (lightboxVideo) {
    lightboxVideo.pause();
    lightboxVideo.removeAttribute("src");
  }
  lightbox?.close();
}

function bindWork(itemEl, item) {
  const openBtn = itemEl.querySelector("[data-open]");
  const caption = itemEl.querySelector("figcaption");
  openBtn?.addEventListener("click", () => {
    openLightbox(
      item,
      caption ? caption.innerText.replace(/\n+/g, " · ") : ""
    );
  });
}

function mapApiItem(item) {
  if (item.kind === "video") {
    return {
      type: "video",
      category: "video",
      src: item.url,
      poster: item.poster || "",
      title: item.title || "",
      capKey: "capVideo",
    };
  }
  return {
    type: "image",
    category: "studio",
    src: item.url,
    title: item.title || "",
    capKey: "capStudio",
  };
}

function renderGallery() {
  if (!gallery) return;
  const pack = dict[currentLang] || dict.en || {};
  const filtered =
    activeFilter === "all"
      ? works
      : works.filter((w) => w.category === activeFilter);

  gallery.innerHTML = "";
  filtered.forEach((item, index) => {
    const figure = document.createElement("figure");
    figure.className = "gallery__item reveal";
    figure.dataset.work = "";
    figure.dataset.category = item.category;
    figure.style.setProperty("--delay", `${Math.min(index, 12) * 0.03}s`);

    const title = item.title || pack[item.titleKey] || item.titleKey || "";
    const cap = pack[item.capKey] || item.capKey || "";

    if (item.type === "video") {
      figure.innerHTML = `
        <button type="button" class="gallery__open gallery__open--video" data-open>
          <video src="${item.src}" poster="${item.poster || ""}" muted playsinline preload="metadata"></video>
          <span class="gallery__badge" data-i18n-static="video">Video</span>
        </button>
        <figcaption>
          <strong>${title}</strong>
          <span>${cap}</span>
        </figcaption>
      `;
    } else {
      figure.innerHTML = `
        <button type="button" class="gallery__open" data-open>
          <img src="${item.src}" alt="${title}" loading="lazy" />
        </button>
        <figcaption>
          <strong>${title}</strong>
          <span>${cap}</span>
        </figcaption>
      `;
    }

    gallery.appendChild(figure);
    bindWork(figure, item);
  });

  observeReveals(gallery);
}

async function loadStudioGallery() {
  try {
    const res = await fetch("/api/gallery", { credentials: "same-origin" });
    if (!res.ok) throw new Error("gallery failed");
    const data = await res.json();
    const live = (Array.isArray(data.items) ? data.items : []).map(mapApiItem);
    // Videos + studio first, archive after
    works = [...live, ...archiveWorks];
  } catch {
    works = [...archiveWorks];
  }
  renderGallery();
}

document.querySelectorAll("[data-filter]").forEach((btn) => {
  btn.addEventListener("click", () => {
    activeFilter = btn.getAttribute("data-filter") || "all";
    document.querySelectorAll("[data-filter]").forEach((b) => {
      const on = b === btn;
      b.classList.toggle("is-active", on);
      b.setAttribute("aria-pressed", on ? "true" : "false");
    });
    renderGallery();
  });
});

const closeBtn = document.querySelector("[data-close]");
closeBtn?.addEventListener("click", closeLightbox);
lightbox?.addEventListener("click", (event) => {
  if (event.target === lightbox) closeLightbox();
});
lightbox?.addEventListener("close", () => {
  if (lightboxVideo) {
    lightboxVideo.pause();
    lightboxVideo.removeAttribute("src");
  }
});

function applyLanguage(lang) {
  const pack = dict[lang] || dict.en;
  if (!pack) return;
  currentLang = lang;

  document.documentElement.lang = lang;
  document.title = pack.metaTitle || document.title;

  document.querySelectorAll("[data-i18n]").forEach((el) => {
    const key = el.getAttribute("data-i18n");
    if (!key || pack[key] == null) return;
    el.textContent = pack[key];
  });

  document.querySelectorAll("[data-i18n-aria]").forEach((el) => {
    const key = el.getAttribute("data-i18n-aria");
    if (!key || pack[key] == null) return;
    el.setAttribute("aria-label", pack[key]);
  });

  document.querySelectorAll("[data-lang]").forEach((btn) => {
    const active = btn.getAttribute("data-lang") === lang;
    btn.setAttribute("aria-pressed", active ? "true" : "false");
    btn.classList.toggle("is-active", active);
  });

  renderGallery();

  try {
    localStorage.setItem("kasabov-lang", lang);
  } catch {
    /* ignore */
  }
}

function detectLanguage() {
  try {
    const saved = localStorage.getItem("kasabov-lang");
    if (supported.includes(saved)) return saved;
  } catch {
    /* ignore */
  }
  const nav = (navigator.language || "en").slice(0, 2).toLowerCase();
  return supported.includes(nav) ? nav : "en";
}

document.querySelectorAll("[data-lang]").forEach((btn) => {
  btn.addEventListener("click", () => {
    const lang = btn.getAttribute("data-lang");
    if (supported.includes(lang)) applyLanguage(lang);
  });
});

observeReveals();
applyLanguage(detectLanguage());
loadStudioGallery();
