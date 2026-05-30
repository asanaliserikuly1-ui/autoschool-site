const instructors = [
  {
    name: "Ерлан М.",
    branch: "shugyla",
    branchLabel: "Шұғыла",
    experience: "Стаж: 7 лет",
    car: "Авто: Toyota",
    tags: ["Спокойно", "Парковки", "Город"],
    photo: null
  },
  {
    name: "Айбек С.",
    branch: "tolebi",
    branchLabel: "Төле би",
    experience: "Стаж: 5 лет",
    car: "Авто: Hyundai",
    tags: ["Экзамен", "Манёвры", "Уверенность"],
    photo: null
  },
  {
    name: "Данияр К.",
    branch: "abaya",
    branchLabel: "Абая",
    experience: "Стаж: 6 лет",
    car: "Авто: Kia",
    tags: ["Город", "Парковки", "Маршруты"],
    photo: null
  },
  {
    name: "Нұржан Т.",
    branch: "makataeva",
    branchLabel: "Макатаева",
    experience: "Стаж: 8 лет",
    car: "Авто: Chevrolet",
    tags: ["Спокойно", "Техника", "Экзамен"],
    photo: null
  },
  {
    name: "Руслан А.",
    branch: "sayaly",
    branchLabel: "Саялы",
    experience: "Стаж: 4 года",
    car: "Авто: Volkswagen",
    tags: ["Город", "Манёвры", "Парковки"],
    photo: null
  },
];

const grid = document.getElementById("instructorsGrid");
const chips = document.querySelectorAll("[data-branch-filter]");

function avatar(name){
  // красивый "инициал" без фото
  const parts = name.split(" ");
  const letter = (parts[0] || "A").trim().charAt(0).toUpperCase();
  return `<div class="avatar">${letter}</div>`;
}

function card(i){
  const tags = i.tags.map(t => `<span class="tag">${t}</span>`).join("");
  return `
    <div class="inst-card" data-branch="${i.branch}">
      <div class="inst-top">
        ${i.photo ? `<img class="inst-photo" src="${i.photo}" alt="${i.name}">` : avatar(i.name)}
        <div class="inst-info">
          <div class="inst-name">${i.name}</div>
          <div class="inst-sub muted">${i.experience} • ${i.car}</div>
        </div>
        <div class="inst-branch">${i.branchLabel}</div>
      </div>

      <div class="inst-tags">${tags}</div>

      <div class="inst-actions">
        <button class="btn btn-outline" type="button" data-open-branches style="width:100%;">
          <i data-lucide="message-circle" class="i"></i>
          <span>Записаться</span>
        </button>
      </div>
    </div>
  `;
}

function render(filter="all"){
  const list = filter === "all" ? instructors : instructors.filter(x => x.branch === filter);
  grid.innerHTML = list.map(card).join("");

  // обновить lucide и повесить обработчики на кнопки модалки
  if (window.lucide) lucide.createIcons();

  // Важно: кнопки внутри карточек тоже должны открывать модалку
  grid.querySelectorAll("[data-open-branches]").forEach(btn => {
    btn.addEventListener("click", () => {
      const modal = document.querySelector("[data-branch-modal]");
      if(modal) {
        modal.classList.add("open");
        document.body.style.overflow = "hidden";
      }
    });
  });
}

chips.forEach(chip => {
  chip.addEventListener("click", () => {
    chips.forEach(c => c.classList.remove("active"));
    chip.classList.add("active");
    render(chip.dataset.branchFilter);
  });
});

render("all");
