/* =========================================================
   App scripts (refactored)
   - Убраны дубли свайпа отзывов (было 2 блока)
   - Убраны повторные lucide.createIcons() в конце
   - Вся логика разнесена по модулям (IIFE)
   - Исправлен конфликт data-branch-id vs data-branch-code
   - __branchModalAfterOpen встроен прямо в openModal()
   ========================================================= */

(() => {
  "use strict";

  // ---------- Helpers ----------
  const DEFAULT_WA_TEXT =
    "Здравствуйте! Хочу записаться в автошколу. Подскажите, пожалуйста, цены и ближайшие даты?";

  const qs = (sel, root = document) => root.querySelector(sel);
  const qsa = (sel, root = document) => Array.from(root.querySelectorAll(sel));

  const digitsOnly = (s) => (s || "").replace(/\D/g, "");
  const waLink = (phone, text) =>
    `https://wa.me/${digitsOnly(phone)}?text=${encodeURIComponent(text || "")}`;

  const safeTrim = (v) => (typeof v === "string" ? v.trim() : "");
  const isNonEmptyText = (v) => !!safeTrim(v);

  const initIcons = () => {
    if (window.lucide) window.lucide.createIcons();
  };

  // =========================================================
  // BRANCH MODAL
  // =========================================================
  const BranchModal = (() => {
    const modal = qs("[data-branch-modal]");
    if (!modal) return null;

    // refs
    const openBtns = qsa("[data-open-branches]");
    const closeBtns = qsa("[data-close-branches]");

    const listEl = qs("#branchesList");
    const mapEl = qs("#branchMap");

    const nameEl = qs("#branchName");
    const addrEl = qs("#branchAddr");
    const quickEl = qs("#branchQuickActions");

    const searchEl = qs("#branchSearch");
    const showAllBtn = qs("#showAllBtn");

    // Choice bar
    const choiceBar = qs("#choiceBar");
    const choiceText = qs("#choiceText");
    const choiceClear = qs("#choiceClear");

    // state
    let BRANCHES = [];
    let currentCode = null;
    let WA_PREFILL_TEXT = DEFAULT_WA_TEXT;

    // --- UI helpers ---
    function branchBadge(code) {
      switch (code) {
        case "shugyla":
          return "Главный Филиал";
        case "tolebi":
          return "Центр";
        case "abaya":
          return "Новый филиалы";
        case "makataeva":
          return "Новый филиалы";
        case "sayaly":
          return "Популярный";
        default:
          return "Филиал";
      }
    }

    function updateChoiceBar(prefillText) {
      if (!choiceBar || !choiceText) return;

      const text = safeTrim(prefillText);
      if (!text) {
        choiceBar.style.display = "none";
        return;
      }

      let short = text
        .replace("Здравствуйте! ", "")
        .replace("Хочу записаться. ", "")
        .replace("Хочу записаться в автошколу. ", "");

      if (short.length > 70) short = short.slice(0, 70) + "…";

      choiceText.textContent = "Вы выбрали: " + short;
      choiceBar.style.display = "flex";
    }

    function waTextForBranch(branch) {
  const base = safeTrim(WA_PREFILL_TEXT) || DEFAULT_WA_TEXT;

  // если в base уже есть "Филиал:" — не добавляем второй раз
  if (/Филиал\s*:/i.test(base)) return base;

  // убираем "Филиал " из названия ветки
  const clean = safeTrim(branch?.name).replace(/^Филиал\s+/i, "").trim();
  return `${base}\nФилиал: ${clean || branch.name}`;
}


    function cardHTML(branch) {
      const text = waTextForBranch(branch);

      return `
        <div class="branch-card" data-branch-code="${branch.code}">
          <div class="branch-head">
            <div class="branch-title">${branch.name}</div>
            <div class="branch-badge">${branchBadge(branch.code)}</div>
          </div>

          <div class="branch-address">${branch.address}</div>

          <div class="branch-actions">
            <a class="whatsapp" target="_blank" href="${waLink(branch.whatsapp, text)}">WhatsApp</a>
            <a href="tel:${branch.phone}">Позвонить</a>
          </div>
        </div>
      `;
    }

    function setActive(code) {
      const branch = BRANCHES.find((x) => x.code === code) || BRANCHES[0];
      if (!branch) return;

      currentCode = branch.code;

      // highlight cards
      if (listEl) {
        qsa(".branch-card", listEl).forEach((c) => {
          c.classList.toggle("active", c.dataset.branchCode === branch.code);
        });
      }

      // right panel info
      if (nameEl) nameEl.textContent = branch.name;
      if (addrEl) addrEl.textContent = branch.address;

      // map iframe
      if (mapEl) mapEl.src = branch.map_embed;

      // quick actions
      const text = waTextForBranch(branch);
      const mapLink = (branch.map_embed || "")
        .replace("&output=embed", "")
        .replace("output=embed", "");

      if (quickEl) {
        quickEl.innerHTML = `
          <a class="primary" target="_blank" href="${waLink(branch.whatsapp, text)}"><span>WhatsApp</span></a>
          <a target="_blank" href="${mapLink}"><span>Карта</span></a>
          <a href="tel:${branch.phone}"><span>Звонок</span></a>
        `;
      }

      initIcons();
      syncActiveChip(branch.code);
      maybeSwitchToMapOnSmallPhones();
    }

    function render(list) {
      if (!listEl) return;

      listEl.innerHTML = list.map(cardHTML).join("");

      qsa(".branch-card", listEl).forEach((card) => {
        card.addEventListener("click", () => setActive(card.dataset.branchCode));
      });

      // keep selected if it still exists, otherwise first
      const exists = list.some((x) => x.code === currentCode);
      setActive(exists ? currentCode : list[0]?.code || null);

      // rebuild chips (если используешь чипы на карте)
      buildMapSwitchFromList();

      initIcons();
    }

    function filterBranches(q) {
      const query = (q || "").trim().toLowerCase();
      if (!query) return BRANCHES;

      return BRANCHES.filter(
        (b) =>
          (b.name || "").toLowerCase().includes(query) ||
          (b.address || "").toLowerCase().includes(query)
      );
    }

    // --- modal open/close ---
    function blurOnMobileAfterOpen() {
      // чтобы не вылезала клавиатура на мобилке
      if (window.matchMedia("(max-width: 768px)").matches) {
        if (document.activeElement) document.activeElement.blur();
        if (searchEl) searchEl.blur();
        document.body.focus?.();
      }
    }

    function openModal(prefillText) {
      // set WA text
      WA_PREFILL_TEXT = isNonEmptyText(prefillText) ? safeTrim(prefillText) : DEFAULT_WA_TEXT;

      // choice bar
      updateChoiceBar(prefillText);

      // rerender links to use current WA_PREFILL_TEXT
      if (BRANCHES.length) render(filterBranches(searchEl?.value));
      if (currentCode) setActive(currentCode);

      modal.classList.add("open");
      document.body.style.overflow = "hidden";

      initIcons();

      // НЕ фокусим инпут на мобилке
      if (searchEl && !window.matchMedia("(max-width: 768px)").matches) {
        searchEl.focus();
      }
      blurOnMobileAfterOpen();
    }

    function closeModal() {
      if (choiceBar) choiceBar.style.display = "none";
      modal.classList.remove("open");
      document.body.style.overflow = "";
    }

    // --- chips for map switch (optional) ---
    // ВАЖНО: раньше у тебя было data-branch-id, но карточки у нас data-branch-code.
    // Тут делаем единый формат: code.
    function buildMapSwitchFromList() {
      const wrap = qs("#mapBranchSwitch");
      if (!wrap || !listEl) return;

      const cards = qsa(".branch-card", listEl); // data-branch-code
      wrap.innerHTML = "";

      cards.forEach((card) => {
        const code = card.dataset.branchCode;
        const titleEl = qs(".branch-title", card);
        const name = safeTrim(titleEl?.textContent) || "Филиал";

        const btn = document.createElement("button");
        btn.type = "button";
        btn.className = "map-branch-chip";
        btn.dataset.branchCode = code;
        btn.textContent = name;

        btn.addEventListener("click", () => setActive(code));
        wrap.appendChild(btn);
      });

      syncActiveChip(currentCode);
    }

    function syncActiveChip(activeCode) {
      const wrap = qs("#mapBranchSwitch");
      if (!wrap) return;
      qsa(".map-branch-chip", wrap).forEach((ch) =>
        ch.classList.toggle("is-active", ch.dataset.branchCode === activeCode)
      );
    }

    // --- modal tabs for small phones (list/map) ---
    function initModalTabs() {
      const tabs = qsa(".modal-tab", modal);
      if (!tabs.length) return;

      if (!modal.getAttribute("data-view")) modal.setAttribute("data-view", "list");

      tabs.forEach((btn) => {
        btn.addEventListener("click", () => {
          const view = btn.getAttribute("data-tab");
          modal.setAttribute("data-view", view);
          tabs.forEach((b) => b.classList.toggle("is-active", b === btn));
        });
      });
    }

    function maybeSwitchToMapOnSmallPhones() {
      // Если хочешь: после выбора филиала на очень маленьких экранах показывать карту
      if (window.matchMedia("(max-width: 480px)").matches) {
        // только если у тебя есть табы/режимы
        if (modal.querySelector(".modal-tab")) {
          modal.setAttribute("data-view", "map");
          // подсветка таба "map" (если он есть)
          const tabs = qsa(".modal-tab", modal);
          const mapTab = tabs.find((t) => t.getAttribute("data-tab") === "map");
          if (mapTab) {
            tabs.forEach((b) => b.classList.toggle("is-active", b === mapTab));
          }
        }
      }
    }

    // --- event bindings ---
    openBtns.forEach((btn) => btn.addEventListener("click", () => openModal(btn.dataset.waText)));
    closeBtns.forEach((btn) => btn.addEventListener("click", closeModal));

    if (choiceClear) {
      choiceClear.addEventListener("click", () => {
        WA_PREFILL_TEXT = DEFAULT_WA_TEXT;
        if (choiceBar) choiceBar.style.display = "none";
        if (BRANCHES.length) render(filterBranches(searchEl?.value));
        if (currentCode) setActive(currentCode);
      });
    }

    modal.addEventListener("click", (e) => {
      if (e.target === modal) closeModal();
    });

    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape" && modal.classList.contains("open")) closeModal();
    });

    // search
    if (searchEl) {
      searchEl.setAttribute("autocomplete", "off");
      searchEl.setAttribute("autocapitalize", "off");
      searchEl.setAttribute("autocorrect", "off");
      searchEl.setAttribute("inputmode", "search");

      // input handler
      searchEl.addEventListener("input", (e) => render(filterBranches(e.target.value)));

      // запрет фокуса на мобилке (чтобы не вылезала клава)
      searchEl.addEventListener("focus", (e) => {
        if (window.matchMedia("(max-width: 768px)").matches) e.target.blur();
      });
    }

    if (showAllBtn) {
      showAllBtn.addEventListener("click", () => {
        if (searchEl) searchEl.value = "";
        render(BRANCHES);
      });
    }

    // init tabs
    initModalTabs();

    // --- load branches from API ---
    async function loadBranches() {
      try {
        const res = await fetch("/api/branches", { headers: { Accept: "application/json" } });
        const json = await res.json();

        BRANCHES = (json.branches || []).map((b) => ({
          ...b,
          map_embed: b.map_embed || "https://www.google.com/maps?q=Алматы&output=embed",
        }));

        currentCode = BRANCHES.some((b) => b.code === "shugyla")
          ? "shugyla"
          : BRANCHES[0]?.code || null;

        render(BRANCHES);
        if (currentCode) setActive(currentCode);
      } catch (err) {
        console.error("Failed to load branches:", err);
        if (listEl) listEl.innerHTML = `<div class="branches-hint">Не удалось загрузить филиалы. Проверь /api/branches</div>`;
      }
    }

    loadBranches();

    // public API (если надо дергать снаружи)
    return { openModal, closeModal };
  })();

  // =========================================================
  // FAQ accordion
  // =========================================================
  const FAQ = (() => {
    const items = qsa(".faq-item");
    if (!items.length) return;

    items.forEach((item) => {
      const q = qs(".faq-q", item);
      const a = qs(".faq-a", item);
      const ico = qs(".faq-ico", item);
      if (!q || !a || !ico) return;

      // closed by default
      a.style.maxHeight = "0px";

      q.addEventListener("click", () => {
        const open = item.classList.toggle("open");
        a.style.maxHeight = open ? a.scrollHeight + "px" : "0px";
        ico.textContent = open ? "×" : "+";
      });
    });
  })();

  // =========================================================
  // Mobile drawer menu
  // =========================================================
  const MobileMenu = (() => {
    document.addEventListener("DOMContentLoaded", () => {
      const burgerBtn = qs("#burgerBtn");
      const mobileNav = qs("#mobileNav");
      const overlay = qs("#mobileOverlay");
      const closeBtn = qs("#mobileClose");

      if (!burgerBtn || !mobileNav || !overlay) return;

      const openMenu = () => {
        document.body.classList.add("menu-open");
        overlay.hidden = false;
        burgerBtn.setAttribute("aria-expanded", "true");
      };

      const closeMenu = () => {
        document.body.classList.remove("menu-open");
        overlay.hidden = true;
        burgerBtn.setAttribute("aria-expanded", "false");
      };

      burgerBtn.addEventListener("click", () => {
        document.body.classList.contains("menu-open") ? closeMenu() : openMenu();
      });

      overlay.addEventListener("click", closeMenu);
      closeBtn?.addEventListener("click", closeMenu);

      document.addEventListener("keydown", (e) => {
        if (e.key === "Escape") closeMenu();
      });

      // close on link click
      qsa("a", mobileNav).forEach((a) => a.addEventListener("click", closeMenu));

      // close on "Записаться" buttons
      qsa("[data-open-branches]", mobileNav).forEach((btn) => btn.addEventListener("click", closeMenu));
    });
  })();

  // ---------- One icons init at the end ----------
  initIcons();
})();




document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll(".page-animated, .header-animated")
    .forEach(el => el.classList.add("is-ready"));
});











document.addEventListener("DOMContentLoaded", () => {
  const rv = document.querySelector("[data-rv]");
  if (!rv) return;

  rv.addEventListener("click", (e) => {
    const btn = e.target.closest("[data-rv-toggle]");
    if (!btn) return;

    e.preventDefault();
    e.stopPropagation();

    const card = btn.closest(".rv-card");
    if (!card) return;

    const open = card.classList.toggle("is-open");
    btn.textContent = open ? "Свернуть" : "Читать полностью";
  });
}, { once: true });











// ===== Reviews: hide "Читать полностью" for short comments =====
document.addEventListener("DOMContentLoaded", () => {

  const MAX_HEIGHT = 110; // высота, при которой показываем кнопку (подгони под свой CSS)

  document.querySelectorAll("[data-rv-text]").forEach(textEl => {
    const wrap = textEl.closest(".rv-text-wrap");
    const btn = wrap?.querySelector("[data-rv-toggle]");
    const fade = wrap?.querySelector(".rv-fade");

    if (!wrap || !btn) return;

    // даём браузеру отрисовать реальные размеры
    requestAnimationFrame(() => {

      const fullHeight = textEl.scrollHeight;

      if (fullHeight <= MAX_HEIGHT) {
        // текст короткий — скрываем кнопку и градиент
        btn.style.display = "none";
        if (fade) fade.style.display = "none";
      }

    });

  });

});










(() => {
  const modal = document.querySelector('.modal-branches');
  if (!modal) return;

  const tabs = modal.querySelectorAll('.modal-tab[data-tab]');
  if (!tabs.length) return;

  // дефолт: список
  if (!modal.dataset.view) modal.dataset.view = 'list';

  tabs.forEach(btn => {
    btn.addEventListener('click', () => {
      const view = btn.dataset.tab; // "list" | "map"
      modal.dataset.view = view;

      tabs.forEach(b => b.classList.toggle('is-active', b === btn));
    });
  });
})();
