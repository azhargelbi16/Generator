/*
  Generator Laporan | Field Notes
  Figma plugin untuk membuat satu papan referensi UI yang bisa diedit.
  Arah visual: meja kerja editorial, bukan dashboard SaaS.
  Semua contoh data ditulis sebagai placeholder agar tidak terlihat sebagai klaim nyata.
*/

const C = {
  canvas: "#FFF8DE",
  paper: "#FFF8DE",
  paperWarm: "#FFF2C6",
  ink: "#101827",
  inkSoft: "#2F405D",
  inkMute: "#60708A",
  line: "#C6D4EC",
  lineStrong: "#AAC4F5",
  moss: "#AAC4F5",
  mossPale: "#FFF2C6",
  rust: "#8CA9FF",
  rustPale: "#DCE6FF",
  blue: "#8CA9FF",
  bluePale: "#FFF2C6",
  warning: "#6E5A24",
  warningPale: "#FFF2C6",
  danger: "#7A404A",
  dangerPale: "#F4DCE0",
  white: "#FFFFFF",
  rail: 214,
  main: 1066,
};

let F = {};

function rgb(hex) {
  const n = parseInt(hex.slice(1), 16);
  return { r: ((n >> 16) & 255) / 255, g: ((n >> 8) & 255) / 255, b: (n & 255) / 255 };
}

function fill(hex, opacity) {
  return { type: "SOLID", color: rgb(hex), opacity: opacity === undefined ? 1 : opacity };
}

function shadow(y, blur, opacity) {
  return [{
    type: "DROP_SHADOW",
    color: { r: 0.12, g: 0.13, b: 0.11, a: opacity === undefined ? 0.12 : opacity },
    offset: { x: 0, y: y || 4 },
    radius: blur || 18,
    spread: 0,
    visible: true,
    blendMode: "NORMAL",
  }];
}

function box(name, o) {
  o = o || {};
  const f = figma.createFrame();
  f.name = name;
  f.fills = o.bg ? [fill(o.bg)] : [];
  if (o.radius !== undefined) f.cornerRadius = o.radius;
  if (o.border) {
    f.strokes = [fill(o.border)];
    f.strokeWeight = o.bw === undefined ? 1 : o.bw;
    f.strokeAlign = "INSIDE";
  }
  if (o.shadow) f.effects = o.shadow;
  if (o.layout) {
    f.layoutMode = o.layout;
    f.primaryAxisSizingMode = o.primary || "AUTO";
    f.counterAxisSizingMode = o.counter || "AUTO";
    f.itemSpacing = o.gap === undefined ? 0 : o.gap;
    f.paddingTop = o.pt || 0;
    f.paddingBottom = o.pb || 0;
    f.paddingLeft = o.pl || 0;
    f.paddingRight = o.pr || 0;
    if (o.align) f.counterAxisAlignItems = o.align;
    if (o.justify) f.primaryAxisAlignItems = o.justify;
  }
  if (typeof o.w === "number" || typeof o.h === "number") f.resize(o.w || f.width, o.h || f.height);
  return f;
}

function text(chars, o) {
  o = o || {};
  const t = figma.createText();
  t.fontName = o.font || F.reg;
  t.characters = chars;
  t.fontSize = o.size || 13;
  t.fills = [fill(o.color || C.ink)];
  t.textAutoResize = "HEIGHT";
  if (o.lh) t.lineHeight = { value: o.lh, unit: "PIXELS" };
  if (o.ls !== undefined) t.letterSpacing = { value: o.ls, unit: "PIXELS" };
  if (o.align) t.textAlignHorizontal = o.align;
  return t;
}

function add(parent, child, o) {
  o = o || {};
  parent.appendChild(child);
  if (o.w === "fill") child.layoutSizingHorizontal = "FILL";
  else if (typeof o.w === "number") {
    child.layoutSizingHorizontal = "FIXED";
    child.resize(o.w, child.height);
  }
  if (o.h === "fill") child.layoutSizingVertical = "FILL";
  if (o.grow) child.layoutGrow = 1;
  return child;
}

function grow(parent) {
  const s = box("space", {});
  s.fills = [];
  parent.appendChild(s);
  s.layoutGrow = 1;
  return s;
}

function rule(parent, width) {
  const r = box("rule", { bg: C.line, w: width || 100, h: 1 });
  parent.appendChild(r);
  if (width === "fill") r.layoutSizingHorizontal = "FILL";
  return r;
}

function mono(chars, o) {
  return text(chars, Object.assign({}, o || {}, { font: F.mono }));
}

function eyebrow(chars, color) {
  return text(chars.toUpperCase(), { size: 10, font: F.semi, color: color || C.inkMute, ls: 1.15 });
}

function status(label, tone) {
  const tones = {
    moss: { bg: C.mossPale, fg: C.moss, border: C.lineStrong },
    rust: { bg: C.rustPale, fg: C.rust, border: C.lineStrong },
    warning: { bg: C.warningPale, fg: C.warning, border: C.lineStrong },
    danger: { bg: C.dangerPale, fg: C.danger, border: "#D7A8B2" },
    blue: { bg: C.bluePale, fg: C.blue, border: C.lineStrong },
    neutral: { bg: C.paperWarm, fg: C.inkSoft, border: C.line },
  };
  const s = tones[tone || "neutral"];
  const p = box("status " + label, { layout: "HORIZONTAL", gap: 6, pt: 5, pb: 5, pl: 9, pr: 9,
    align: "CENTER", bg: s.bg, border: s.border, radius: 5 });
  p.appendChild(text(label, { size: 10.5, font: F.med, color: s.fg }));
  return p;
}

function button(label, variant, o) {
  o = o || {};
  const styles = {
    primary: { bg: C.ink, fg: C.paper, border: C.ink },
    outline: { bg: C.paper, fg: C.ink, border: C.lineStrong },
    quiet: { bg: C.paperWarm, fg: C.inkSoft, border: C.line },
    rust: { bg: C.rust, fg: C.white, border: C.rust },
    danger: { bg: C.dangerPale, fg: C.danger, border: "#D7A8B2" },
  };
  const s = styles[variant || "primary"];
  const b = box("button " + label, { layout: "HORIZONTAL", gap: 7, pt: o.py || 10, pb: o.py || 10,
    pl: o.px || 14, pr: o.px || 14, align: "CENTER", justify: "CENTER",
    bg: s.bg, border: s.border, radius: 5 });
  b.appendChild(text(label, { size: o.size || 12, font: F.semi, color: s.fg }));
  return b;
}

function field(label, value, o) {
  o = o || {};
  const wrap = box("field " + label, { layout: "VERTICAL", gap: 6 });
  wrap.appendChild(eyebrow(label, C.inkSoft));
  const control = box("field-control", { layout: "HORIZONTAL", gap: 8, pt: 11, pb: 11, pl: 12, pr: 12,
    align: "CENTER", bg: o.bg || C.paper, border: o.border || C.line, radius: 5 });
  control.appendChild(text(value, { size: 12.5, color: o.muted ? C.inkMute : C.ink }));
  if (o.trailing) {
    grow(control);
    control.appendChild(mono(o.trailing, { size: 10.5, color: C.inkMute }));
  }
  wrap.appendChild(control);
  return wrap;
}

function rail(active) {
  const r = box("navigation rail", { layout: "VERTICAL", gap: 5, pt: 22, pb: 18, pl: 16, pr: 14,
    bg: C.ink, w: C.rail, counter: "FIXED" });
  const brand = box("wordmark", { layout: "VERTICAL", gap: 4, pb: 22 });
  brand.appendChild(text("GENERATOR", { size: 11, font: F.bold, color: C.paper, ls: 1.7 }));
  brand.appendChild(text("laporan akademik", { size: 11, color: C.lineStrong }));
  r.appendChild(brand);
  rule(r, "fill").fills = [fill("#203454")];

  const items = [
    ["01", "Profil"], ["02", "Template"], ["03", "Studio"], ["04", "Review"],
  ];
  const nav = box("steps", { layout: "VERTICAL", gap: 3, pt: 20 });
  items.forEach(function (item) {
    const isActive = active === item[0];
    const row = box("nav " + item[1], { layout: "HORIZONTAL", gap: 10, pt: 9, pb: 9, pl: 8, pr: 8,
      align: "CENTER", bg: isActive ? C.rust : null, radius: 4 });
    row.appendChild(mono(item[0], { size: 10, color: isActive ? C.ink : C.lineStrong }));
    row.appendChild(text(item[1], { size: 12, font: isActive ? F.semi : F.med, color: isActive ? C.ink : C.paper }));
    nav.appendChild(row);
  });
  r.appendChild(nav);
  grow(r);

  const footer = box("rail footer", { layout: "VERTICAL", gap: 5, pt: 12 });
  footer.appendChild(eyebrow("Layanan AI", C.lineStrong));
  footer.appendChild(mono("[BELUM DITES]", { size: 10, color: C.paper }));
  r.appendChild(footer);
  return r;
}

function page(name, active) {
  const root = box(name, { layout: "HORIZONTAL", bg: C.canvas, w: 1280 });
  root.appendChild(rail(active));
  const main = box("main", { layout: "VERTICAL", gap: 0, w: C.main, counter: "FIXED" });
  root.appendChild(main);
  return { root: root, main: main };
}

function topbar(main, section, right) {
  const bar = box("topbar", { layout: "HORIZONTAL", gap: 16, pt: 17, pb: 17, pl: 28, pr: 28,
    align: "CENTER", justify: "SPACE_BETWEEN", bg: C.canvas, w: C.main, counter: "FIXED" });
  bar.appendChild(text(section, { size: 13, font: F.semi, color: C.ink }));
  const actions = box("topbar actions", { layout: "HORIZONTAL", gap: 8, align: "CENTER" });
  (right || []).forEach(function (item) { actions.appendChild(item); });
  bar.appendChild(actions);
  main.appendChild(bar);
  rule(main, "fill");
  return bar;
}

function content(main, o) {
  o = o || {};
  const row = box("content", { layout: "HORIZONTAL", gap: o.gap === undefined ? 20 : o.gap,
    pt: o.pt === undefined ? 26 : o.pt, pb: o.pb === undefined ? 30 : o.pb,
    pl: o.pl === undefined ? 28 : o.pl, pr: o.pr === undefined ? 28 : o.pr,
    align: "MIN", bg: C.canvas, w: C.main, counter: "FIXED" });
  main.appendChild(row);
  return row;
}

function paperCard(name, o) {
  o = o || {};
  return box(name, { layout: o.layout || "VERTICAL", gap: o.gap === undefined ? 13 : o.gap,
    pt: o.pt === undefined ? 18 : o.pt, pb: o.pb === undefined ? 18 : o.pb,
    pl: o.pl === undefined ? 18 : o.pl, pr: o.pr === undefined ? 18 : o.pr,
    bg: o.bg || C.paper, border: o.border || C.line, radius: o.radius === undefined ? 6 : o.radius,
    shadow: o.shadow ? shadow(3, 12, 0.08) : null, w: o.w, h: o.h, counter: o.counter || "FIXED" });
}

/* ----------------------------- 00 Design sheet ----------------------------- */

function tokenScreen(x) {
  const root = box("00 · Field Notes design sheet", { layout: "VERTICAL", gap: 20, pt: 30, pb: 34, pl: 32, pr: 32,
    bg: C.paper, w: 980, counter: "FIXED", shadow: shadow(8, 24, 0.10) });
  root.x = x; root.y = 0;

  const head = box("sheet header", { layout: "HORIZONTAL", gap: 20, align: "MIN", w: 916, counter: "FIXED" });
  const title = box("title", { layout: "VERTICAL", gap: 6, w: 600, counter: "FIXED" });
  title.appendChild(eyebrow("Arah visual", C.rust));
  title.appendChild(text("Field Notes", { size: 30, font: F.bold, color: C.ink, ls: -0.5 }));
  title.appendChild(text("Antarmuka ini membaca seperti meja kerja editorial: tenang, terukur, dan selalu menunjukkan sumber dari setiap keputusan.", { size: 13, color: C.inkSoft, lh: 19 }));
  head.appendChild(title);
  grow(head);
  const stamp = box("stamp", { layout: "VERTICAL", gap: 5, pt: 11, pb: 11, pl: 12, pr: 12,
    bg: C.paperWarm, border: C.line, radius: 4, w: 190, counter: "FIXED" });
  stamp.appendChild(eyebrow("Use for", C.inkMute));
  stamp.appendChild(text("Workflow akademik", { size: 12, font: F.semi }));
  stamp.appendChild(mono("DIRECTION 01", { size: 10, color: C.rust }));
  head.appendChild(stamp);
  root.appendChild(head);
  rule(root, "fill");

  const colors = box("color strips", { layout: "VERTICAL", gap: 8, w: 916, counter: "FIXED" });
  colors.appendChild(eyebrow("Palet kerja", C.inkSoft));
  [[C.ink, "Ink"], [C.paper, "Paper"], [C.canvas, "Canvas"], [C.moss, "Moss"], [C.rust, "Rust"], [C.blue, "Blue"]].forEach(function (item) {
    const row = box("swatch " + item[1], { layout: "HORIZONTAL", gap: 10, align: "CENTER", w: 916, counter: "FIXED" });
    const sw = box("swatch", { bg: item[0], border: item[0] === C.paper ? C.line : item[0], radius: 3, w: 96, h: 24 });
    row.appendChild(sw);
    row.appendChild(mono(item[0], { size: 10.5, color: C.inkSoft }));
    row.appendChild(text(item[1], { size: 12, font: F.semi }));
    colors.appendChild(row);
  });
  root.appendChild(colors);

  const type = box("type scale", { layout: "VERTICAL", gap: 9, w: 916, counter: "FIXED" });
  type.appendChild(eyebrow("Hierarki teks", C.inkSoft));
  type.appendChild(text("Judul kerja, bukan slogan", { size: 24, font: F.bold, color: C.ink }));
  type.appendChild(text("Label membantu mata menemukan langkah berikutnya", { size: 14, font: F.semi, color: C.ink }));
  type.appendChild(text("Body text selalu membawa konteks singkat, bukan filler untuk mengisi ruang.", { size: 12.5, color: C.inkSoft, lh: 19 }));
  type.appendChild(mono("STATUS / ENDPOINT / NOMOR BAGIAN", { size: 10, color: C.rust, ls: 0.4 }));
  root.appendChild(type);

  const statusRow = box("status row", { layout: "HORIZONTAL", gap: 8, align: "CENTER", w: 916, counter: "FIXED" });
  statusRow.appendChild(eyebrow("Status yang punya arti", C.inkSoft));
  statusRow.appendChild(status("Kutipan cocok", "moss"));
  statusRow.appendChild(status("Perlu ditinjau", "warning"));
  statusRow.appendChild(status("Kutipan tidak cocok", "danger"));
  statusRow.appendChild(status("Kosong", "neutral"));
  root.appendChild(statusRow);

  const note = box("design note", { layout: "HORIZONTAL", gap: 10, pt: 11, pb: 11, pl: 12, pr: 12,
    bg: C.paperWarm, border: C.line, radius: 4, w: 916, counter: "FIXED" });
  note.appendChild(mono("RULE", { size: 10, font: F.bold, color: C.rust }));
  note.appendChild(text("Satu aksen untuk menandai keputusan, bukan untuk menghias semua permukaan.", { size: 11.5, color: C.inkSoft }));
  root.appendChild(note);
  figma.currentPage.appendChild(root);
  return root;
}

/* ------------------------------ 01 Studio --------------------------------- */

function studioScreen(x) {
  const s = page("01 · Studio Laporan", "03");
  s.root.x = x; s.root.y = 0;
  topbar(s.main, "03 / Studio laporan", [status("Draf lokal", "neutral"), mono("[BELUM DITES]", { size: 10, color: C.inkMute })]);

  const row = content(s.main, { gap: 24 });
  const source = box("source column", { layout: "VERTICAL", gap: 16, w: 350, counter: "FIXED" });
  source.appendChild(eyebrow("Mulai dari bahan", C.rust));
  source.appendChild(text("Sumber yang bisa dibaca ulang membuat laporan tetap bisa dipertanggungjawabkan.", { size: 21, font: F.bold, lh: 27 }));
  source.appendChild(text("Tambahkan bahan yang benar-benar akan dipakai. Jangan mulai dari judul kosong.", { size: 12, color: C.inkSoft, lh: 18 }));
  const tray = paperCard("source tray", { w: 350, bg: C.paperWarm });
  tray.appendChild(eyebrow("Sumber aktif", C.inkSoft));
  const empty = box("empty source", { layout: "VERTICAL", gap: 8, pt: 22, pb: 22, pl: 15, pr: 15,
    align: "CENTER", border: C.lineStrong, radius: 4, w: 314, counter: "FIXED" });
  empty.appendChild(text("+", { size: 23, font: F.reg, color: C.rust, align: "CENTER" }));
  empty.appendChild(text("Belum ada sumber", { size: 13, font: F.semi, align: "CENTER" }));
  empty.appendChild(text("PDF, DOI, web, atau teks manual", { size: 11, color: C.inkSoft, align: "CENTER" }));
  tray.appendChild(empty);
  tray.appendChild(button("Tambahkan sumber", "outline", { size: 11.5 }));
  source.appendChild(tray);
  row.appendChild(source);

  const form = paperCard("report form", { layout: "VERTICAL", gap: 18, w: 640, shadow: true });
  const formHead = box("form heading", { layout: "VERTICAL", gap: 5 });
  formHead.appendChild(eyebrow("Lembar baru", C.rust));
  formHead.appendChild(text("Buat laporan", { size: 23, font: F.bold }));
  formHead.appendChild(text("Isi yang diperlukan saja. Detail lain dapat diperiksa sebelum ekspor.", { size: 12, color: C.inkSoft }));
  form.appendChild(formHead);
  rule(form, "fill");
  form.appendChild(field("Judul laporan", "[TULIS JUDUL LAPORAN]"));
  const line1 = box("fields 1", { layout: "HORIZONTAL", gap: 12, w: 604, counter: "FIXED" });
  const f1 = field("Format", "B / standar"); f1.layoutSizingHorizontal = "FILL";
  const f2 = field("Dosen pembimbing", "[PILIH DOSEN]"); f2.layoutSizingHorizontal = "FILL";
  line1.appendChild(f1); line1.appendChild(f2);
  form.appendChild(line1);
  form.appendChild(field("Nama file", "[OTOMATIS DARI JUDUL]", { muted: true }));
  const formFoot = box("form footer", { layout: "HORIZONTAL", gap: 10, align: "CENTER" });
  formFoot.appendChild(button("Mulai menyusun", "primary", { py: 12 }));
  formFoot.appendChild(button("Simpan draf", "quiet"));
  grow(formFoot);
  formFoot.appendChild(text("Tidak ada data contoh yang disimpan.", { size: 10.5, color: C.inkMute }));
  form.appendChild(formFoot);
  row.appendChild(form);
  figma.currentPage.appendChild(s.root);
  return s.root;
}

/* ----------------------------- 02 Generating ------------------------------ */

function generatingScreen(x) {
  const s = page("02 · Menyusun laporan", "03");
  s.root.x = x; s.root.y = 0;
  topbar(s.main, "03 / Studio laporan / menyusun", [button("Batalkan", "danger", { py: 7, px: 11, size: 11.5 })]);

  const row = content(s.main, { gap: 20, pt: 28 });
  const main = paperCard("generation sheet", { layout: "VERTICAL", gap: 18, w: 690, shadow: true });
  main.appendChild(eyebrow("Sedang berjalan", C.rust));
  main.appendChild(text("Menyusun laporan dari sumber yang dipilih", { size: 24, font: F.bold, lh: 30 }));
  main.appendChild(text("Tampilkan tahap yang sedang aktif. Jangan menampilkan angka yang tidak berasal dari proses nyata.", { size: 12, color: C.inkSoft, lh: 18 }));
  rule(main, "fill");

  const stages = box("stages", { layout: "HORIZONTAL", gap: 0, w: 654, counter: "FIXED" });
  [["01", "Membaca sumber", "done"], ["02", "Menyusun bab", "active"], ["03", "Memeriksa kutipan", "next"], ["04", "Siap direview", "next"]].forEach(function (stage, index) {
    const cell = box("stage " + stage[1], { layout: "VERTICAL", gap: 6, w: 163, counter: "FIXED" });
    cell.appendChild(mono(stage[0], { size: 10, color: stage[2] === "active" ? C.rust : stage[2] === "done" ? C.moss : C.inkMute }));
    cell.appendChild(text(stage[1], { size: 11.5, font: stage[2] === "active" ? F.semi : F.med, color: stage[2] === "next" ? C.inkMute : C.ink }));
    const bar = box("stage bar", { bg: stage[2] === "done" ? C.moss : stage[2] === "active" ? C.rust : C.line, w: 151, h: 4, radius: 2 });
    cell.appendChild(bar);
    stages.appendChild(cell);
    if (index < 3) rule(stages, 12).fills = [fill(C.lineStrong)];
  });
  main.appendChild(stages);

  const writing = box("writing sample", { layout: "VERTICAL", gap: 8, pt: 16, pb: 16, pl: 16, pr: 16,
    bg: C.paperWarm, border: C.line, radius: 4, w: 654, counter: "FIXED" });
  writing.appendChild(eyebrow("Bagian aktif", C.inkSoft));
  writing.appendChild(text("[JUDUL BAB YANG SEDANG DITULIS]", { size: 14, font: F.semi }));
  writing.appendChild(text("[Pratinjau teks hasil sintesis muncul di sini setelah sumber selesai dibaca.]", { size: 12, color: C.inkSoft, lh: 19 }));
  main.appendChild(writing);
  main.appendChild(button("Buka review setelah selesai", "quiet", { size: 11.5 }));
  row.appendChild(main);

  const activity = paperCard("activity", { layout: "VERTICAL", gap: 12, w: 300, bg: C.ink, border: C.ink });
  activity.appendChild(eyebrow("Aktivitas", C.lineStrong));
  [["SELESAI", "Sumber dibaca", "moss"], ["AKTIF", "Bab sedang disusun", "rust"], ["BERIKUTNYA", "Pemeriksaan kutipan", "neutral"]].forEach(function (item) {
    const itemBox = box("activity item", { layout: "VERTICAL", gap: 4, pt: 11, pb: 11, pl: 11, pr: 11,
      bg: item[2] === "rust" ? "#203454" : "#17243A", radius: 4, w: 264, counter: "FIXED" });
    itemBox.appendChild(mono(item[0], { size: 9.5, color: item[2] === "moss" ? C.moss : item[2] === "rust" ? C.rust : C.lineStrong }));
    itemBox.appendChild(text(item[1], { size: 12, font: F.med, color: C.paper }));
    activity.appendChild(itemBox);
  });
  grow(activity);
  activity.appendChild(text("Status berubah mengikuti proses nyata.", { size: 10.5, color: C.lineStrong, lh: 16 }));
  row.appendChild(activity);
  figma.currentPage.appendChild(s.root);
  return s.root;
}

/* ------------------------------ 03 Review --------------------------------- */

function reviewScreen(x) {
  const s = page("03 · Canvas & Review", "04");
  s.root.x = x; s.root.y = 0;
  topbar(s.main, "04 / Canvas & Review", [status("Perlu ditinjau", "warning"), button("Simpan DOCX", "primary", { py: 7, px: 12, size: 11.5 })]);

  const row = content(s.main, { gap: 0, pt: 0, pb: 0, pl: 0, pr: 0 });

  const outline = box("outline", { layout: "VERTICAL", gap: 4, pt: 19, pb: 18, pl: 16, pr: 12,
    bg: C.paperWarm, border: C.line, w: 226, counter: "FIXED" });
  outline.appendChild(eyebrow("Struktur", C.inkSoft));
  outline.appendChild(text("Bab laporan", { size: 16, font: F.bold }));
  rule(outline, "fill");
  [["BAB 1", "Pendahuluan", "open"], ["1.1", "Latar belakang", "open"], ["1.2", "Rumusan masalah", "empty"], ["1.3", "Tujuan", "empty"], ["BAB 2", "Tinjauan pustaka", "empty"], ["BAB 3", "Pembahasan", "empty"], ["BAB 4", "Penutup", "empty"]].forEach(function (item, index) {
    const r = box("outline row", { layout: "HORIZONTAL", gap: 8, pt: 8, pb: 8, pl: 7, pr: 7,
      align: "CENTER", bg: index === 1 ? C.paper : null, radius: 3, w: 198, counter: "FIXED" });
    r.appendChild(mono(item[0], { size: 9.5, color: item[2] === "empty" ? C.inkMute : C.rust }));
    r.appendChild(text(item[1], { size: 11, font: index === 0 ? F.semi : F.med, color: item[2] === "empty" ? C.inkMute : C.ink }));
    grow(r);
    if (item[2] === "empty") r.appendChild(status("Kosong", "neutral"));
    outline.appendChild(r);
  });
  grow(outline);
  outline.appendChild(text("Kosong bukan berarti selesai. Tampilkan agar pengguna tahu apa yang perlu dilengkapi.", { size: 10.5, color: C.inkSoft, lh: 16 }));
  row.appendChild(outline);

  const paperWrap = box("paper wrap", { layout: "HORIZONTAL", pt: 26, pb: 30, pl: 26, pr: 26,
    bg: C.canvas, w: 526, counter: "FIXED" });
  const paper = paperCard("document", { layout: "VERTICAL", gap: 15, pt: 42, pb: 46, pl: 42, pr: 42,
    w: 474, shadow: true });
  paper.appendChild(eyebrow("Pratinjau dokumen", C.inkMute));
  paper.appendChild(text("[JUDUL LAPORAN]", { size: 20, font: F.bold, lh: 25, align: "CENTER" }));
  paper.appendChild(mono("[NAMA]  /  [MATA KULIAH]  /  [TANGGAL]", { size: 9.5, color: C.inkMute, align: "CENTER" }));
  rule(paper, "fill");
  paper.appendChild(text("BAB 1. PENDAHULUAN", { size: 16, font: F.bold }));
  paper.appendChild(text("1.1 Latar belakang", { size: 13, font: F.semi }));
  const p1 = text("[Kalimat hasil laporan tampil di sini. Klik satu kalimat untuk melihat bukti sumber dan mengubahnya di tempat.]", { size: 12, color: C.ink, lh: 20 });
  paper.appendChild(p1);
  const selected = box("selected sentence", { layout: "VERTICAL", gap: 5, pt: 5, pb: 5, pl: 8, pr: 8,
    bg: C.warningPale, border: C.lineStrong, radius: 3 });
  selected.appendChild(text("[KALIMAT TERPILIH UNTUK DICEK]", { size: 12, font: F.semi, color: C.ink, lh: 20 }));
  selected.appendChild(mono("dipilih pengguna", { size: 9.5, color: C.warning }));
  paper.appendChild(selected);
  paper.appendChild(text("[Paragraf berikutnya membawa sitasi yang bisa dipulihkan dari sumber.]", { size: 12, color: C.ink, lh: 20 }));
  paperWrap.appendChild(paper);
  row.appendChild(paperWrap);

  const inspector = box("inspector", { layout: "VERTICAL", gap: 12, pt: 19, pb: 18, pl: 16, pr: 16,
    bg: C.paper, border: C.line, w: 314, counter: "FIXED" });
  const ih = box("inspector heading", { layout: "HORIZONTAL", align: "CENTER", justify: "SPACE_BETWEEN", w: 282, counter: "FIXED" });
  ih.appendChild(text("Inspektor kalimat", { size: 14, font: F.bold }));
  ih.appendChild(text("×", { size: 16, color: C.inkMute }));
  inspector.appendChild(ih);
  inspector.appendChild(status("Kutipan tidak cocok", "danger"));
  inspector.appendChild(eyebrow("Sunting di tempat", C.inkSoft));
  const edit = box("edit area", { layout: "VERTICAL", gap: 8, pt: 11, pb: 11, pl: 11, pr: 11,
    bg: C.paper, border: C.lineStrong, radius: 4, w: 282, counter: "FIXED" });
  edit.appendChild(text("[KALIMAT TERPILIH UNTUK DICEK]", { size: 11.5, color: C.ink, lh: 18 }));
  inspector.appendChild(edit);
  inspector.appendChild(button("Simpan perubahan", "primary", { size: 11.5 }));
  const actions = box("review actions", { layout: "HORIZONTAL", gap: 8, w: 282, counter: "FIXED" });
  const done = button("Tandai selesai", "outline", { size: 10.5, px: 9 }); done.layoutGrow = 1;
  const paraphrase = button("Parafrase", "quiet", { size: 10.5, px: 9 }); paraphrase.layoutGrow = 1;
  actions.appendChild(done); actions.appendChild(paraphrase);
  inspector.appendChild(actions);
  const evidence = box("evidence", { layout: "VERTICAL", gap: 7, pt: 11, pb: 11, pl: 11, pr: 11,
    bg: C.bluePale, border: C.lineStrong, radius: 4, w: 282, counter: "FIXED" });
  evidence.appendChild(eyebrow("Bukti dari sumber", C.blue));
  evidence.appendChild(text("[KUTIPAN ASLI DARI TEKS SUMBER]", { size: 11.5, color: C.ink, lh: 17 }));
  inspector.appendChild(evidence);
  inspector.appendChild(mono("[SUMBER 01]  /  [PENULIS, TAHUN]", { size: 9.5, color: C.inkMute }));
  row.appendChild(inspector);

  figma.currentPage.appendChild(s.root);
  return s.root;
}

/* ----------------------------- 04 Export gate ----------------------------- */

function gateScreen(x) {
  const root = box("04 · Pemeriksaan Akhir", { layout: "HORIZONTAL", align: "CENTER", justify: "CENTER",
    pt: 56, pb: 56, bg: C.line, w: 1280 });
  root.x = x; root.y = 0;
  const modal = paperCard("export gate", { layout: "VERTICAL", gap: 15, pt: 24, pb: 22, pl: 24, pr: 24,
    bg: C.paper, border: C.lineStrong, radius: 6, w: 600, shadow: true });
  const head = box("gate heading", { layout: "VERTICAL", gap: 6 });
  head.appendChild(eyebrow("Pemeriksaan akhir", C.rust));
  head.appendChild(text("Belum siap disimpan", { size: 22, font: F.bold }));
  head.appendChild(text("Periksa temuan berikut sebelum membuat DOCX. Tidak ada yang disembunyikan di balik warna saja.", { size: 12, color: C.inkSoft, lh: 18 }));
  modal.appendChild(head);
  rule(modal, "fill");
  [["Kalimat belum selesai", "Tandai setiap kalimat yang sudah Anda baca.", "warning"], ["Kutipan hilang", "Tambahkan sitasi pada klaim faktual yang belum memiliki sumber.", "danger"], ["Bagian kosong", "Lengkapi bagian bab yang masih bertanda Kosong.", "neutral"]].forEach(function (item) {
    const issue = box("issue " + item[0], { layout: "HORIZONTAL", gap: 10, pt: 11, pb: 11, pl: 11, pr: 11,
      align: "MIN", bg: item[2] === "danger" ? C.dangerPale : item[2] === "warning" ? C.warningPale : C.paperWarm,
      border: item[2] === "danger" ? "#D7A8B2" : item[2] === "warning" ? C.lineStrong : C.line, radius: 4, w: 550, counter: "FIXED" });
    issue.appendChild(status(item[2] === "danger" ? "PERLU" : item[2] === "warning" ? "CEK" : "KOSONG", item[2]));
    const copy = box("issue copy", { layout: "VERTICAL", gap: 3 });
    copy.appendChild(text(item[0], { size: 12.5, font: F.semi }));
    copy.appendChild(text(item[1], { size: 11, color: C.inkSoft, lh: 16 }));
    issue.appendChild(copy);
    modal.appendChild(issue);
  });
  const note = box("gate note", { layout: "HORIZONTAL", gap: 8, pt: 10, pb: 10, pl: 11, pr: 11,
    bg: C.paperWarm, border: C.line, radius: 4, w: 550, counter: "FIXED" });
  note.appendChild(mono("NOTE", { size: 9.5, font: F.bold, color: C.rust }));
  note.appendChild(text("Simpan tetap bisa dipilih jika Anda yakin, tetapi keputusan itu dicatat.", { size: 11, color: C.inkSoft }));
  modal.appendChild(note);
  const buttons = box("gate buttons", { layout: "HORIZONTAL", gap: 8, justify: "MAX", w: 550, counter: "FIXED" });
  buttons.appendChild(button("Kembali ke review", "outline", { size: 11.5 }));
  buttons.appendChild(button("Simpan DOCX", "primary", { size: 11.5 }));
  modal.appendChild(buttons);
  root.appendChild(modal);
  figma.currentPage.appendChild(root);
  return root;
}

/* ----------------------------- 05 Settings -------------------------------- */

function settingsScreen(x) {
  const s = page("05 · Pengaturan AI", "01");
  s.root.x = x; s.root.y = 0;
  topbar(s.main, "01 / Pengaturan layanan", [status("Belum dites", "neutral")]);

  const row = content(s.main, { gap: 24 });
  const intro = box("settings intro", { layout: "VERTICAL", gap: 12, w: 320, counter: "FIXED" });
  intro.appendChild(eyebrow("Sambungkan dengan sadar", C.rust));
  intro.appendChild(text("Layanan AI adalah alat bantu, bukan sumber kebenaran.", { size: 22, font: F.bold, lh: 28 }));
  intro.appendChild(text("Gunakan endpoint lokal bila dokumen tidak boleh meninggalkan komputer. Tes koneksi sebelum menyimpan.", { size: 12, color: C.inkSoft, lh: 18 }));
  const note = box("privacy note", { layout: "VERTICAL", gap: 7, pt: 13, pb: 13, pl: 13, pr: 13,
    bg: C.bluePale, border: C.lineStrong, radius: 4, w: 320, counter: "FIXED" });
  note.appendChild(eyebrow("Catatan privasi", C.blue));
  note.appendChild(text("Teks sumber dapat dikirim ke layanan yang Anda pilih. Periksa endpoint dan kebijakan layanan sebelum mulai.", { size: 11, color: C.ink, lh: 17 }));
  intro.appendChild(note);
  row.appendChild(intro);

  const form = paperCard("settings form", { layout: "VERTICAL", gap: 17, w: 640, shadow: true });
  const title = box("settings title", { layout: "VERTICAL", gap: 5 });
  title.appendChild(eyebrow("Konfigurasi", C.rust));
  title.appendChild(text("Pengaturan layanan AI", { size: 22, font: F.bold }));
  title.appendChild(text("Nilai kosong tetap terlihat sebagai nilai kosong, bukan konfigurasi palsu.", { size: 12, color: C.inkSoft }));
  form.appendChild(title);
  rule(form, "fill");
  form.appendChild(field("Base URL endpoint", "[CONTOH: http://localhost:20128/v1]", { muted: true }));
  form.appendChild(field("API key", "[KOSONGKAN UNTUK LAYANAN LOKAL]", { muted: true }));
  form.appendChild(field("Nama model", "[MODEL AKTIF]", { muted: true }));
  const temperature = box("temperature", { layout: "VERTICAL", gap: 7 });
  temperature.appendChild(eyebrow("Temperatur", C.inkSoft));
  const slider = box("slider", { layout: "HORIZONTAL", align: "CENTER", gap: 10 });
  const track = box("track", { bg: C.line, w: 420, h: 4, radius: 2 });
  const trackFill = box("track fill", { bg: C.rust, w: 90, h: 4, radius: 2 });
  track.appendChild(trackFill);
  const knob = figma.createEllipse(); knob.resize(14, 14); knob.fills = [fill(C.paper)]; knob.strokes = [fill(C.rust)]; knob.strokeWeight = 2;
  track.appendChild(knob);
  slider.appendChild(track);
  slider.appendChild(mono("0,2", { size: 11, color: C.inkSoft }));
  temperature.appendChild(slider);
  temperature.appendChild(text("Nilai lebih rendah membantu menjaga keluaran tetap faktual.", { size: 10.5, color: C.inkMute }));
  form.appendChild(temperature);
  const footer = box("settings footer", { layout: "HORIZONTAL", gap: 9, align: "CENTER" });
  footer.appendChild(button("Tes koneksi", "outline", { size: 11.5 }));
  footer.appendChild(button("Simpan pengaturan", "primary", { size: 11.5 }));
  grow(footer);
  footer.appendChild(mono("STATUS: [BELUM DITES]", { size: 9.5, color: C.inkMute }));
  form.appendChild(footer);
  row.appendChild(form);
  figma.currentPage.appendChild(s.root);
  return s.root;
}

/* ------------------------------ 06 States --------------------------------- */

function statesScreen(x) {
  const s = page("06 · UI States", "03");
  s.root.x = x; s.root.y = 0;
  topbar(s.main, "03 / State yang perlu dirancang", [status("Referensi", "neutral")]);

  const row = content(s.main, { gap: 16 });
  const left = box("states left", { layout: "VERTICAL", gap: 16, w: 496, counter: "FIXED" });
  const right = box("states right", { layout: "VERTICAL", gap: 16, w: 496, counter: "FIXED" });

  function stateCard(label, title, detail, tone, action) {
    const toneMap = {
      empty: { bg: C.paper, border: C.lineStrong, fg: C.rust, mark: "+" },
      loading: { bg: C.paperWarm, border: C.line, fg: C.rust, mark: "..." },
      error: { bg: C.dangerPale, border: "#D7A8B2", fg: C.danger, mark: "!" },
      success: { bg: C.mossPale, border: C.lineStrong, fg: C.moss, mark: "OK" },
    }[tone];
    const card = box("state " + label, { layout: "VERTICAL", gap: 10, pt: 17, pb: 17, pl: 17, pr: 17,
      bg: toneMap.bg, border: toneMap.border, radius: 5, w: 496, counter: "FIXED" });
    const head = box("state head", { layout: "HORIZONTAL", gap: 10, align: "CENTER", w: 460, counter: "FIXED" });
    const mark = box("state mark", { layout: "HORIZONTAL", align: "CENTER", justify: "CENTER", bg: toneMap.fg, radius: 3, w: 30, h: 30 });
    mark.appendChild(text(toneMap.mark, { size: 12, font: F.bold, color: C.paper, align: "CENTER" }));
    head.appendChild(mark);
    const copy = box("state copy", { layout: "VERTICAL", gap: 3 });
    copy.appendChild(eyebrow(label, toneMap.fg));
    copy.appendChild(text(title, { size: 14, font: F.semi }));
    head.appendChild(copy);
    card.appendChild(head);
    card.appendChild(text(detail, { size: 11.5, color: C.inkSoft, lh: 17 }));
    card.appendChild(button(action, tone === "error" ? "danger" : tone === "success" ? "quiet" : "outline", { size: 11, py: 8 }));
    return card;
  }

  left.appendChild(eyebrow("Jangan hanya desain happy path", C.rust));
  left.appendChild(text("State yang jujur membuat alur terasa selesai.", { size: 21, font: F.bold, lh: 27 }));
  left.appendChild(text("Gunakan empat panel ini sebagai checklist sebelum desain berpindah ke kode.", { size: 12, color: C.inkSoft, lh: 18 }));
  left.appendChild(stateCard("EMPTY", "Belum ada sumber", "Jelaskan apa yang kosong dan satu tindakan yang akan mengisinya.", "empty", "Tambah sumber"));
  left.appendChild(stateCard("LOADING", "Sedang menyusun", "Jelaskan proses yang sedang berjalan dan beri pengguna kendali untuk membatalkan.", "loading", "Batalkan proses"));
  right.appendChild(stateCard("ERROR", "Koneksi AI gagal", "Sebutkan apa yang gagal, bagaimana memperbaikinya, lalu sediakan percobaan ulang.", "error", "Tes koneksi lagi"));
  right.appendChild(stateCard("SUCCESS", "Siap ditinjau", "Tunjukkan hasil yang benar-benar sudah selesai dan langkah berikutnya.", "success", "Buka review"));
  row.appendChild(left); row.appendChild(right);
  figma.currentPage.appendChild(s.root);
  return s.root;
}

/* --------------------------------- Main ----------------------------------- */

async function loadFonts() {
  const fonts = [
    ["Inter", "Regular"], ["Inter", "Medium"], ["Inter", "Semi Bold"], ["Inter", "Bold"],
  ];
  for (let i = 0; i < fonts.length; i++) await figma.loadFontAsync({ family: fonts[i][0], style: fonts[i][1] });
  F.reg = { family: "Inter", style: "Regular" };
  F.med = { family: "Inter", style: "Medium" };
  F.semi = { family: "Inter", style: "Semi Bold" };
  F.bold = { family: "Inter", style: "Bold" };
  try {
    await figma.loadFontAsync({ family: "Roboto Mono", style: "Regular" });
    F.mono = { family: "Roboto Mono", style: "Regular" };
  } catch (e) {
    F.mono = F.med;
  }
}

async function main() {
  await loadFonts();
  const made = [];
  let x = 0;
  figma.currentPage.children.slice().forEach(function (node) {
    if (/^\d\d · /.test(node.name)) node.remove();
  });
  made.push(tokenScreen(x)); x += 1120;
  made.push(studioScreen(x)); x += 1400;
  made.push(generatingScreen(x)); x += 1400;
  made.push(reviewScreen(x)); x += 1400;
  made.push(gateScreen(x)); x += 1400;
  made.push(settingsScreen(x)); x += 1400;
  made.push(statesScreen(x));
  try { figma.viewport.scrollAndZoomIntoViewport(made); } catch (e) { /* optional */ }
  figma.closePlugin();
}

main();
