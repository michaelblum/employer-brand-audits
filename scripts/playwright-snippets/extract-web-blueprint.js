async (page) => {
  return await page.evaluate(() => {
    const compact = (value, limit = 180) => String(value || "").replace(/\s+/g, " ").trim().slice(0, limit);
    const cssEscape = (value) => {
      if (window.CSS?.escape) {
        return window.CSS.escape(String(value));
      }
      return String(value).replace(/[^a-zA-Z0-9_-]/g, "\\$&");
    };
    const roleFor = (el) => {
      const explicit = el.getAttribute("role");
      if (explicit) return explicit;
      const tag = el.tagName.toLowerCase();
      if (tag === "a" && el.getAttribute("href")) return "link";
      if (tag === "button") return "button";
      if (["input", "textarea", "select"].includes(tag)) return "textbox";
      if (/^h[1-6]$/.test(tag)) return "heading";
      if (tag === "img") return "image";
      if (["main", "section", "article", "nav", "header", "footer"].includes(tag)) return tag;
      return "";
    };
    const selectorCandidates = (el) => {
      const tag = el.tagName.toLowerCase();
      const candidates = [];
      if (el.id) candidates.push(`#${cssEscape(el.id)}`);
      const classes = [...el.classList].slice(0, 3).map((item) => `.${cssEscape(item)}`).join("");
      if (classes) candidates.push(`${tag}${classes}`);
      const aria = el.getAttribute("aria-label");
      if (aria) candidates.push(`${tag}[aria-label="${aria.replaceAll('"', '\\"')}"]`);
      candidates.push(tag);
      return [...new Set(candidates)];
    };
    const targetKind = (el, role) => {
      const tag = el.tagName.toLowerCase();
      if (role === "link" || tag === "a") return "link";
      if (role === "button" || tag === "button") return "button";
      if (["input", "textarea", "select"].includes(tag)) return "input";
      if (role === "heading" || /^h[1-6]$/.test(tag)) return "heading";
      if (tag === "img") return "image";
      if (["main", "section", "article", "nav"].includes(tag)) return "section";
      return "element";
    };
    const elements = [];
    const candidates = [
      ...document.querySelectorAll("a[href],button,input,textarea,select,h1,h2,h3,main,section,article,img,[role],[aria-label]"),
    ];
    for (const [index, el] of candidates.entries()) {
      const rect = el.getBoundingClientRect();
      const style = window.getComputedStyle(el);
      if (
        rect.width < 4 ||
        rect.height < 4 ||
        style.display === "none" ||
        style.visibility === "hidden" ||
        style.opacity === "0"
      ) {
        continue;
      }
      const role = roleFor(el);
      const text = compact(el.getAttribute("aria-label") || el.getAttribute("alt") || el.getAttribute("title") || el.textContent);
      elements.push({
        uid: `target-${index + 1}`,
        tag: el.tagName.toLowerCase(),
        role,
        target_kind: targetKind(el, role),
        accessible_name: text,
        text,
        selector_candidates: selectorCandidates(el),
        document_rect: {
          x: Math.round(rect.left + window.scrollX),
          y: Math.round(rect.top + window.scrollY),
          width: Math.round(rect.width),
          height: Math.round(rect.height),
        },
        confidence: role || text ? 0.85 : 0.55,
      });
    }
    return {
      schema_version: "url_stage_blueprint.v0",
      url: window.location.href,
      title: document.title,
      viewport: {
        width: window.innerWidth,
        height: window.innerHeight,
        devicePixelRatio: window.devicePixelRatio || 1,
      },
      document: {
        width: Math.max(document.documentElement.scrollWidth, document.body?.scrollWidth || 0),
        height: Math.max(document.documentElement.scrollHeight, document.body?.scrollHeight || 0),
      },
      elements,
    };
  });
}
