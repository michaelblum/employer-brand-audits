async (page) => {
  return await page.evaluate(() => {
    window.__ebaHiddenElements ||= [];
    const candidates = Array.from(document.querySelectorAll("body *"));
    for (const el of candidates) {
      const style = window.getComputedStyle(el);
      if (style.position !== "fixed" && style.position !== "sticky") {
        continue;
      }
      const rect = el.getBoundingClientRect();
      const coversMeaningfulArea = rect.width >= 80 && rect.height >= 40;
      if (!coversMeaningfulArea) {
        continue;
      }
      window.__ebaHiddenElements.push({
        el,
        visibility: el.style.visibility,
        pointerEvents: el.style.pointerEvents,
      });
      el.style.visibility = "hidden";
      el.style.pointerEvents = "none";
    }
    return { hidden: window.__ebaHiddenElements.length };
  });
}
