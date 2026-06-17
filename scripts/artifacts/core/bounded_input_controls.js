(function () {
  const ROOT = window.Artifacts = window.Artifacts || {};
  const common = ROOT.common || {};
  const escapeHtml = common.escapeHtml || ((value) => String(value ?? ""));

  function definitionsForArtifact(definitions = [], artifact = {}) {
    if (!Array.isArray(definitions)) return [];
    return definitions.filter((definition) => definition?.anchor?.artifact_id === artifact?.id);
  }

  function valueForDefinition(definition = {}, values = {}) {
    const key = `${definition.step_id}.${definition.input_id}`;
    if (Object.prototype.hasOwnProperty.call(values || {}, key)) return String(values[key]);
    return definition.value == null ? "" : String(definition.value);
  }

  function optionRecord(option) {
    if (option && typeof option === "object") {
      return {
        value: String(option.value ?? option.label ?? ""),
        label: String(option.label ?? option.value ?? ""),
      };
    }
    return { value: String(option ?? ""), label: String(option ?? "") };
  }

  function selectedOptionRecord(options = [], value = "") {
    return options.find((option) => option.value === value)
      || options[0]
      || { value, label: value || "Select option" };
  }

  function controlAttrs(definition = {}) {
    return [
      "data-bounded-input-control",
      `data-step-id="${escapeHtml(definition.step_id)}"`,
      `data-input-id="${escapeHtml(definition.input_id)}"`,
      `aria-label="${escapeHtml(definition.label || definition.input_id)}"`,
    ].join(" ");
  }

  function renderControlHtml(definition = {}, values = {}) {
    const value = valueForDefinition(definition, values);
    const commonAttrs = controlAttrs(definition);
    if (definition.input_type === "select") {
      const options = (definition.options || []).map(optionRecord);
      const selected = selectedOptionRecord(options, value);
      return `
          <div class="bounded-input-select" data-bounded-input-select>
            <button
              class="bounded-input-select-trigger"
              type="button"
              ${commonAttrs}
              data-bounded-input-select-trigger
              value="${escapeHtml(selected.value)}"
              aria-haspopup="listbox"
              aria-expanded="false"
            >
              <span data-bounded-input-select-label>${escapeHtml(selected.label)}</span>
              <span class="bounded-input-select-caret" aria-hidden="true"></span>
            </button>
            <div
              class="bounded-input-select-menu"
              data-bounded-input-select-menu
              data-step-id="${escapeHtml(definition.step_id)}"
              data-input-id="${escapeHtml(definition.input_id)}"
              role="listbox"
              hidden
            >
            ${options.map((option) => `
              <button
                class="bounded-input-select-option"
                type="button"
                role="option"
                data-bounded-input-select-option
                data-step-id="${escapeHtml(definition.step_id)}"
                data-input-id="${escapeHtml(definition.input_id)}"
                data-value="${escapeHtml(option.value)}"
                aria-selected="${option.value === selected.value ? "true" : "false"}"
              >
                ${escapeHtml(option.label)}
              </button>
            `).join("")}
            </div>
          </div>
        `;
    }
    if (definition.input_type === "textarea") {
      return `<textarea ${commonAttrs} placeholder="${escapeHtml(definition.placeholder || "")}">${escapeHtml(value)}</textarea>`;
    }
    return `<input ${commonAttrs} type="text" value="${escapeHtml(value)}" placeholder="${escapeHtml(definition.placeholder || "")}">`;
  }

  function renderLayerHtml(definitions = [], values = {}) {
    if (!definitions.length) return "";
    return `
        <section class="bounded-input-panel" data-bounded-input-panel>
          <div class="bounded-input-title">Intake inputs</div>
          <div class="bounded-input-grid">
            ${definitions.map((definition) => `
              <label class="bounded-input-field" data-step-id="${escapeHtml(definition.step_id)}" data-input-id="${escapeHtml(definition.input_id)}">
                <span>${escapeHtml(definition.label || definition.input_id)}</span>
                ${renderControlHtml(definition, values)}
              </label>
            `).join("")}
          </div>
        </section>
      `;
  }

  function definitionForControl(definitions = [], control) {
    return definitions.find((definition) => (
      definition.step_id === control?.dataset?.stepId
      && definition.input_id === control?.dataset?.inputId
    )) || null;
  }

  function closeSelectMenus(layerEl, exceptRoot = null) {
    layerEl?.querySelectorAll("[data-bounded-input-select]").forEach((root) => {
      if (exceptRoot && root === exceptRoot) return;
      const menu = root.querySelector("[data-bounded-input-select-menu]");
      const trigger = root.querySelector("[data-bounded-input-select-trigger]");
      if (menu) menu.hidden = true;
      if (trigger) trigger.setAttribute("aria-expanded", "false");
    });
  }

  function setSelectValue(root, value, syncControl) {
    const trigger = root.querySelector("[data-bounded-input-select-trigger]");
    const label = root.querySelector("[data-bounded-input-select-label]");
    const options = [...root.querySelectorAll("[data-bounded-input-select-option]")];
    const selected = options.find((option) => option.dataset.value === value) || options[0];
    if (!trigger || !selected) return;
    trigger.value = selected.dataset.value || "";
    trigger.dataset.value = trigger.value;
    if (label) label.textContent = selected.textContent.trim();
    options.forEach((option) => {
      option.setAttribute("aria-selected", option === selected ? "true" : "false");
    });
    syncControl(trigger);
  }

  function focusSelectOption(root, delta) {
    const options = [...root.querySelectorAll("[data-bounded-input-select-option]")];
    if (!options.length) return;
    const currentIndex = Math.max(0, options.indexOf(document.activeElement));
    const nextIndex = (currentIndex + delta + options.length) % options.length;
    options[nextIndex].focus();
  }

  function bindControls({ layerEl, definitions = [], onChange }) {
    layerEl?.querySelectorAll("[data-bounded-input-control]").forEach((control) => {
      const syncControl = (sourceControl = control) => {
        const definition = definitionForControl(definitions, sourceControl);
        if (!definition) return;
        onChange({ definition, value: sourceControl.value });
      };
      if (control.matches("[data-bounded-input-select-trigger]")) {
        const root = control.closest("[data-bounded-input-select]");
        const menu = root?.querySelector("[data-bounded-input-select-menu]");
        if (!root || !menu) return;
        const openMenu = () => {
          closeSelectMenus(layerEl, root);
          menu.hidden = false;
          control.setAttribute("aria-expanded", "true");
        };
        const closeMenu = () => {
          menu.hidden = true;
          control.setAttribute("aria-expanded", "false");
        };
        control.addEventListener("click", (event) => {
          event.stopPropagation();
          if (menu.hidden) openMenu();
          else closeMenu();
        });
        control.addEventListener("keydown", (event) => {
          if (event.key === "ArrowDown" || event.key === "ArrowUp") {
            event.preventDefault();
            openMenu();
            focusSelectOption(root, event.key === "ArrowDown" ? 1 : -1);
          } else if (event.key === "Escape") {
            closeMenu();
          }
        });
        root.querySelectorAll("[data-bounded-input-select-option]").forEach((option) => {
          option.addEventListener("click", (event) => {
            event.stopPropagation();
            setSelectValue(root, option.dataset.value || "", syncControl);
            closeMenu();
            control.focus();
          });
          option.addEventListener("keydown", (event) => {
            if (event.key === "ArrowDown" || event.key === "ArrowUp") {
              event.preventDefault();
              focusSelectOption(root, event.key === "ArrowDown" ? 1 : -1);
            } else if (event.key === "Enter" || event.key === " ") {
              event.preventDefault();
              setSelectValue(root, option.dataset.value || "", syncControl);
              closeMenu();
              control.focus();
            } else if (event.key === "Escape") {
              closeMenu();
              control.focus();
            }
          });
        });
        return;
      }
      control.addEventListener("input", () => syncControl());
      control.addEventListener("change", () => syncControl());
    });
  }

  ROOT.boundedInputControls = {
    bindControls,
    closeSelectMenus,
    definitionForControl,
    definitionsForArtifact,
    focusSelectOption,
    optionRecord,
    renderControlHtml,
    renderLayerHtml,
    selectedOptionRecord,
    setSelectValue,
    valueForDefinition,
  };
}());
