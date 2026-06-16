(() => {
  const valueOf = (source) => (typeof source === "function" ? source() : source);

  function createArtifactBinding(dependencies = {}) {
    let unbindControls = null;
    const elements = dependencies.elements || {};

    const defaultArtifact = () => valueOf(dependencies.getDefaultArtifact);
    const artifactOrDefault = (artifact) => artifact || defaultArtifact();
    const registry = () => valueOf(dependencies.registry);
    const toolbar = () => valueOf(dependencies.toolbar);
    const documentRenderer = () => valueOf(dependencies.documentRenderer);
    const html = () => valueOf(dependencies.html);
    const markdown = () => valueOf(dependencies.markdown);
    const context = () => valueOf(dependencies.getContext) || {};
    const actions = () => valueOf(dependencies.actions) || {};
    const toolbarRoot = () => valueOf(elements.toolbarRoot);
    const image = () => valueOf(elements.image);

    function selectedComponent(artifact) {
      return registry().resolveArtifactComponent(artifactOrDefault(artifact), {
        document: documentRenderer(),
        html: html(),
      });
    }

    function capabilities(artifact) {
      return selectedComponent(artifact)?.capabilities || {};
    }

    function supports(capability, artifact) {
      return Boolean(capabilities(artifact)[capability]);
    }

    function toolbarPlan(artifact) {
      const item = artifactOrDefault(artifact);
      const imageEl = image() || {};
      const currentContext = context();
      return registry().artifactToolbarPlan({
        artifact: item,
        imageNaturalWidth: imageEl.naturalWidth || 0,
        imageNaturalHeight: imageEl.naturalHeight || 0,
        markdownContentById: currentContext.markdownContentById,
        documentContentById: currentContext.documentContentById,
        markdown: markdown(),
        document: documentRenderer(),
        html: html(),
      });
    }

    function stagePlan(artifact) {
      return registry().artifactStagePlan(artifactOrDefault(artifact), {
        document: documentRenderer(),
        html: html(),
      });
    }

    function controlState(artifact) {
      const currentContext = context();
      return {
        artifactDocumentTheme: currentContext.artifactDocumentTheme,
        markdownDirty: currentContext.markdownDirty,
        markdownMode: currentContext.markdownMode,
        zoomMode: currentContext.zoomMode,
        zoomPercent: currentContext.zoomPercent,
        artifact: artifactOrDefault(artifact),
      };
    }

    function bindControls(artifact) {
      if (unbindControls) unbindControls();
      const item = artifactOrDefault(artifact);
      const component = selectedComponent(item);
      unbindControls = typeof component.bindControls === "function"
        ? component.bindControls({
          rootEl: toolbarRoot(),
          actions: actions(),
          state: controlState(item),
          artifact: item,
        })
        : null;
    }

    function syncControls(artifact) {
      const item = artifactOrDefault(artifact);
      const component = selectedComponent(item);
      if (typeof component.syncControls !== "function") return;
      component.syncControls({
        rootEl: toolbarRoot(),
        state: controlState(item),
        artifact: item,
      });
    }

    function updateToolbar(artifact) {
      const item = artifactOrDefault(artifact);
      toolbar().mountToolbar(toolbarRoot(), toolbarPlan(item));
      bindControls(item);
      syncControls(item);
    }

    return {
      selectedComponent,
      capabilities,
      supports,
      toolbarPlan,
      stagePlan,
      controlState,
      bindControls,
      syncControls,
      updateToolbar,
    };
  }

  window.WorkbenchArtifactBinding = {
    createArtifactBinding,
  };
})();
