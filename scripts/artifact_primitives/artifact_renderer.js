(function () {
  const ROOT = window.ArtifactPrimitives = window.ArtifactPrimitives || {};

  const DOCUMENT_TYPES = ["json", "text", "log", "file"];

  function fallbackIsDocumentArtifact(artifact = {}) {
    return DOCUMENT_TYPES.includes(String(artifact.type || "").toLowerCase());
  }

  function artifactRenderKind(artifact = {}, { document } = {}) {
    const type = String(artifact.type || "").toLowerCase();
    if (type === "markdown") return "markdown";
    const documentPrimitive = document || ROOT.document;
    const isDocument = typeof documentPrimitive?.isDocumentArtifact === "function"
      ? documentPrimitive.isDocumentArtifact(artifact)
      : fallbackIsDocumentArtifact(artifact);
    return isDocument ? "document" : "image";
  }

  ROOT.artifactRenderer = {
    artifactRenderKind,
  };
}());
