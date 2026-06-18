async (page) => {
  await page.evaluate(async () => {
    const wait = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
    const maxWaitMs = 2500;
    if (!window.__ebaCaptureStabilizerStyle) {
      window.__ebaCaptureStabilizerStyle = document.createElement("style");
      window.__ebaCaptureStabilizerStyle.setAttribute("data-eba-capture-stabilizer", "true");
      window.__ebaCaptureStabilizerStyle.textContent = `
        *,*::before,*::after {
          animation-delay: 0s !important;
          animation-duration: 0.001s !important;
          animation-iteration-count: 1 !important;
          scroll-behavior: auto !important;
          transition-delay: 0s !important;
          transition-duration: 0s !important;
        }
        html:focus-within {
          scroll-behavior: auto !important;
        }
      `;
      document.head.appendChild(window.__ebaCaptureStabilizerStyle);
    }
    window.__ebaPausedMedia ||= [];
    for (const video of document.querySelectorAll("video")) {
      if (!video.paused) {
        window.__ebaPausedMedia.push({ el: video, currentTime: video.currentTime });
        video.pause();
      }
    }
    const animations = document.getAnimations({ subtree: true });
    for (const animation of animations) {
      try {
        animation.pause();
      } catch (_error) {
        // Some browser-internal animations cannot be paused; the timeout below
        // keeps capture moving.
      }
    }
    const finiteAnimations = animations.filter((animation) => {
      const timing = animation.effect?.getTiming?.();
      return Number.isFinite(Number(timing?.duration)) && Number.isFinite(Number(timing?.iterations ?? 1));
    });
    await Promise.race([
      Promise.allSettled(finiteAnimations.map((animation) => animation.finished.catch(() => undefined))),
      wait(maxWaitMs),
    ]);

    await Promise.race([new Promise((resolve) => {
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
    }), wait(maxWaitMs)]);
  });
  return { settled: true };
}
