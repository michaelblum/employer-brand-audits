async (page) => {
  return await page.evaluate(() => {
    const hidden = window.__ebaHiddenElements || [];
    for (const item of hidden) {
      item.el.style.visibility = item.visibility;
      item.el.style.pointerEvents = item.pointerEvents;
    }
    window.__ebaHiddenElements = [];
    return { restored: hidden.length };
  });
}
