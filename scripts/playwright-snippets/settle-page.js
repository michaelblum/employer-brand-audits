async (page) => {
  await page.evaluate(async () => {
    const animations = document.getAnimations({ subtree: true });
    await Promise.allSettled(animations.map((animation) => animation.finished.catch(() => undefined)));

    await new Promise((resolve) => {
      let stableReads = 0;
      let lastY = window.scrollY;
      const tick = () => {
        const currentY = window.scrollY;
        stableReads = currentY === lastY ? stableReads + 1 : 0;
        lastY = currentY;
        if (stableReads >= 3) {
          resolve();
          return;
        }
        requestAnimationFrame(tick);
      };
      requestAnimationFrame(tick);
    });
  });
};
