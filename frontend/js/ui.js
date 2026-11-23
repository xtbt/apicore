/* ==========================================================================
   ui.js · reusable interface pieces
   Builds DOM, toasts, confirmations, forms and tables.
   It does not know the API: it receives data and returns data.
   ========================================================================== */

(function (global) {
  'use strict';

  /* ---------- DOM building ---------- */

  function el(tag, attrs, children) {
    const node = document.createElement(tag);
    Object.keys(attrs || {}).forEach(function (key) {
      const value = attrs[key];
      if (value === null || value === undefined || value === false) return;
      if (key === 'class') node.className = value;
      else if (key === 'text') node.textContent = value;
      else if (key === 'html') node.innerHTML = value;
      else if (key.startsWith('on') && typeof value === 'function') {
        node.addEventListener(key.slice(2).toLowerCase(), value);
      } else if (key === 'dataset') {
        Object.keys(value).forEach(function (dataKey) {
          node.dataset[dataKey] = value[dataKey];
        });
      } else {
        node.setAttribute(key, value === true ? '' : value);
      }
    });
    (children || []).forEach(function (child) {
      if (child === null || child === undefined) return;
      node.appendChild(typeof child === 'string' ? document.createTextNode(child) : child);
    });
    return node;
  }

  function clear(node) {
    while (node.firstChild) node.removeChild(node.firstChild);
  }

  /* ---------- Toasts ---------- */

  function toast(message, variant) {
    const container = document.getElementById('toast-container');
    const tone = variant || 'success';
    const node = el('div', {
      class: 'toast align-items-center text-bg-' + tone + ' border-0',
      role: 'alert',
      'aria-live': 'assertive',
      'aria-atomic': 'true',
    }, [
      el('div', { class: 'd-flex' }, [
        el('div', { class: 'toast-body', text: message }),
        el('button', {
          class: 'btn-close btn-close-white me-2 m-auto',
          type: 'button',
          'data-bs-dismiss': 'toast',
          'aria-label': 'Cerrar',
        }),
      ]),
    ]);
    container.appendChild(node);
    const instance = new bootstrap.Toast(node, { delay: 4000 });
    node.addEventListener('hidden.bs.toast', function () {
      node.remove();
    });
    instance.show();
  }

  /* ---------- Confirmation ---------- */

  function confirmAction(message, acceptLabel) {
    return new Promise(function (resolve) {
      const modalNode = document.getElementById('confirm-modal');
      const body = document.getElementById('confirm-modal-body');
      const accept = document.getElementById('confirm-modal-accept');
      const modal = bootstrap.Modal.getOrCreateInstance(modalNode);

      body.textContent = message;
      accept.textContent = acceptLabel || 'Eliminar';

      let settled = false;
      function finish(value) {
        if (settled) return;
        settled = true;
        accept.removeEventListener('click', onAccept);
        modalNode.removeEventListener('hidden.bs.modal', onHidden);
        resolve(value);
      }
      function onAccept() {
        finish(true);
        modal.hide();
      }
      function onHidden() {
        finish(false);
      }

      accept.addEventListener('click', onAccept);
      modalNode.addEventListener('hidden.bs.modal', onHidden);
      modal.show();
    });
  }

  /* ---------- Modal form ---------- */

  /**
   * Open the modal with the given fields.
   * fields: [{ name, label, type, required, options, min, max, step, help, readonly }]
   * values: initial values by field name.
   * Returns a promise with the data object, or null if cancelled.
   */
  function openForm(options) {
    return new Promise(function (resolve) {
      const modalNode = document.getElementById('form-modal');
      const form = document.getElementById('form-modal-form');
      const title = document.getElementById('form-modal-title');
      const fieldsBox = document.getElementById('form-modal-fields');
      const errorBox = document.getElementById('form-modal-error');
      const submit = document.getElementById('form-modal-submit');
      const modal = bootstrap.Modal.getOrCreateInstance(modalNode);

      title.textContent = options.title || 'Formulario';
      submit.textContent = options.submitLabel || 'Guardar';
      errorBox.classList.add('d-none');
      errorBox.textContent = '';
      clear(fieldsBox);

      const inputs = {};
      (options.fields || []).forEach(function (field) {
        const input = buildField(field, (options.values || {})[field.name]);
        inputs[field.name] = { field: field, input: input };
        fieldsBox.appendChild(wrapField(field, input));
      });

      let settled = false;
      function finish(value) {
        if (settled) return;
        settled = true;
        form.removeEventListener('submit', onSubmit);
        modalNode.removeEventListener('hidden.bs.modal', onHidden);
        resolve(value);
      }

      function onSubmit(event) {
        event.preventDefault();
        errorBox.classList.add('d-none');
        try {
          const data = collect(inputs);
          finish(data);
          modal.hide();
        } catch (validationError) {
          errorBox.textContent = validationError.message;
          errorBox.classList.remove('d-none');
        }
      }

      function onHidden() {
        finish(null);
      }

      form.addEventListener('submit', onSubmit);
      modalNode.addEventListener('hidden.bs.modal', onHidden);
      modal.show();
    });
  }

  function wrapField(field, input) {
    const wide = field.type === 'textarea' || field.type === 'json' || field.wide;
    const label = el('label', {
      class: 'form-label' + (field.required ? ' field-required' : ''),
      for: input.id,
      text: field.label,
    });
    const children = [label, input];
    if (field.help) {
      children.push(el('div', { class: 'form-text', text: field.help }));
    }
    return el('div', { class: wide ? 'col-12' : 'col-12 col-md-6' }, children);
  }

  function buildField(field, value) {
    const id = 'field-' + field.name;
    const common = { id: id, name: field.name, class: 'form-control' };
    if (field.readonly) common.readonly = true;

    let input;
    switch (field.type) {
      case 'select':
        input = el('select', { id: id, name: field.name, class: 'form-select' },
          (field.options || []).map(function (option) {
            const optionValue = typeof option === 'string' ? option : option.value;
            const optionLabel = typeof option === 'string' ? option : option.label;
            return el('option', {
              value: optionValue,
              selected: String(value) === String(optionValue),
              text: optionLabel,
            });
          })
        );
        break;
      case 'textarea':
      case 'json':
        input = el('textarea', Object.assign({}, common, { rows: field.type === 'json' ? 4 : 3 }));
        if (value !== undefined && value !== null) input.value = value;
        break;
      case 'checkbox':
        input = el('input', { id: id, name: field.name, class: 'form-check-input', type: 'checkbox' });
        input.checked = Boolean(value);
        break;
      case 'number':
        input = el('input', Object.assign({}, common, {
          type: 'number',
          min: field.min,
          max: field.max,
          step: field.step || 'any',
        }));
        if (value !== undefined && value !== null) input.value = value;
        break;
      default:
        input = el('input', Object.assign({}, common, { type: field.type || 'text' }));
        if (value !== undefined && value !== null) input.value = value;
    }
    return input;
  }

  function collect(inputs) {
    const data = {};
    Object.keys(inputs).forEach(function (name) {
      const entry = inputs[name];
      const field = entry.field;
      const input = entry.input;

      if (field.type === 'checkbox') {
        data[name] = input.checked;
        return;
      }

      const raw = input.value.trim();
      if (raw === '') {
        if (field.required) {
          throw new Error(field.label + ' es obligatorio');
        }
        return; // an empty optional field is not sent
      }

      if (field.type === 'number') {
        const number = Number(raw);
        if (Number.isNaN(number)) {
          throw new Error(field.label + ' debe ser un número');
        }
        data[name] = number;
      } else if (field.type === 'json') {
        try {
          data[name] = JSON.parse(raw);
        } catch (error) {
          throw new Error(field.label + ' debe ser JSON válido');
        }
      } else if (field.type === 'datetime-local') {
        data[name] = raw.replace('T', ' ') + (raw.length === 16 ? ':00' : '');
      } else if (field.type === 'time') {
        data[name] = raw.length === 5 ? raw + ':00' : raw;
      } else {
        data[name] = raw;
      }
    });
    return data;
  }

  /* ---------- Tables ---------- */

  /**
   * columns: [{ key, label, render(row) }]
   * actions: [{ label, variant, onClick(row) }]
   */
  function renderTable(container, options) {
    clear(container);
    const rows = options.rows || [];

    if (rows.length === 0) {
      container.appendChild(el('div', { class: 'empty-state' }, [
        el('p', { text: options.emptyMessage || 'No hay registros todavía.' }),
      ]));
      return;
    }

    const head = el('tr', {}, (options.columns || []).map(function (column) {
      return el('th', { text: column.label });
    }).concat([el('th', { class: 'text-end', text: 'Acciones' })]));

    const body = el('tbody', {}, rows.map(function (row) {
      const cells = (options.columns || []).map(function (column) {
        const content = column.render ? column.render(row[column.key], row) : row[column.key];
        if (content instanceof Node) return el('td', {}, [content]);
        const text = content === null || content === undefined || content === '' ? '—' : String(content);
        return el('td', {
          class: text === '—' ? 'cell-empty' : '',
          text: text,
        });
      });

      const buttons = (options.actions || [])
        .filter(function (action) {
          return !action.visible || action.visible(row);
        })
        .map(function (action) {
          return el('button', {
            class: 'btn btn-sm btn-outline-' + (action.variant || 'secondary') + ' me-1',
            type: 'button',
            text: action.label,
            onclick: function () { action.onClick(row); },
          });
        });

      cells.push(el('td', { class: 'text-end text-nowrap' }, buttons));
      return el('tr', {}, cells);
    }));

    container.appendChild(el('div', { class: 'table-wrapper' }, [
      el('table', { class: 'table table-sm table-hover align-middle' }, [
        el('thead', { class: 'table-light' }, [head]),
        body,
      ]),
    ]));
  }

  global.UI = {
    el: el,
    clear: clear,
    toast: toast,
    confirmAction: confirmAction,
    openForm: openForm,
    renderTable: renderTable,
  };
})(window);
