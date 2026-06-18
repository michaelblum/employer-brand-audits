async (page) => {
  return await page.evaluate(() => {
    const hidden = window.__ebaHiddenElements || [];
    for (const item of hidden) {
      item.el.style.visibility = item.visibility;
      item.el.style.pointerEvents = item.pointerEvents;
    }
    window.__ebaHiddenElements = [];
    const pausedMedia = window.__ebaPausedMedia || [];
    for (const item of pausedMedia) {
      if (!item?.el) {
        continue;
      }
      if (Number.isFinite(item.currentTime)) {
        item.el.currentTime = item.currentTime;
      }
      item.el.play().catch(() => undefined);
    }
    window.__ebaPausedMedia = [];
    const style = window.__ebaCaptureStabilizerStyle;
    if (style?.remove) {
      style.remove();
    }
    window.__ebaCaptureStabilizerStyle = null;
    return { restored: hidden.length, mediaRestored: pausedMedia.length, stabilizerRemoved: Boolean(style) };
  });
}
