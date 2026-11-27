/* ==========================================================================
   app.js · application state and event wiring
   Defines which entities exist, which fields they have and what each role can do.
   ========================================================================== */

(function (global) {
  'use strict';

  const UI = global.UI;
  const STORAGE_TOKEN = 'apicore.token';
  const STORAGE_BASE = 'apicore.baseUrl';
  const DEFAULT_BASE_URL = 'http://localhost:65000';

  /* ---------- Entity definitions ---------- */

  const STATUS_OPTIONS = ['Active', 'Inactive'];
  const ROLE_OPTIONS = ['God', 'Admin', 'User', 'Other'];

  const RESOURCES = {
    moods: {
      label: 'Mood',
      idKey: 'MoodId',
      columns: [
        { key: 'MoodId', label: 'ID' },
        { key: 'MoodName', label: 'Nombre' },
        { key: 'MoodStatus', label: 'Estado', render: renderStatus },
      ],
      fields: [
        { name: 'MoodName', label: 'MoodName', type: 'text', required: true, help: 'Máximo 16 caracteres' },
        { name: 'MoodStatus', label: 'MoodStatus', type: 'select', options: STATUS_OPTIONS },
      ],
    },

    examples: {
      label: 'Example',
      idKey: 'ExampleId',
      columns: [
        { key: 'ExampleId', label: 'ID' },
        { key: 'ExampleName', label: 'Nombre' },
        { key: 'ExampleCode', label: 'Código' },
        { key: 'ExamplePrice', label: 'Precio' },
        { key: 'ExampleActive', label: 'Activo', render: renderBoolean },
        { key: 'ExampleStatus', label: 'Estado', render: renderStatus },
      ],
      fields: [
        { name: 'ExampleName', label: 'ExampleName', type: 'text', required: true, help: 'Máximo 45 caracteres' },
        { name: 'ExampleCode', label: 'ExampleCode', type: 'text', help: 'Máximo 3 caracteres' },
        { name: 'ExampleDescription', label: 'ExampleDescription', type: 'textarea', wide: true, help: 'Texto libre' },
        { name: 'ExamplePrice', label: 'ExamplePrice', type: 'number', min: 0, step: '0.01', help: 'DECIMAL · se devuelve como texto' },
        { name: 'ExampleQuantity', label: 'ExampleQuantity', type: 'number', min: 0, step: '1', help: 'INT' },
        { name: 'ExampleBigNumber', label: 'ExampleBigNumber', type: 'number', step: '1', help: 'BIGINT' },
        { name: 'ExampleRatio', label: 'ExampleRatio', type: 'number', step: 'any', help: 'FLOAT' },
        { name: 'ExampleActive', label: 'ExampleActive', type: 'checkbox', help: 'TINYINT(1) · booleano' },
        { name: 'ExampleStatus', label: 'ExampleStatus', type: 'select', options: STATUS_OPTIONS },
        { name: 'ExampleBirthDate', label: 'ExampleBirthDate', type: 'date', help: 'DATE · YYYY-MM-DD' },
        { name: 'ExampleCreatedAt', label: 'ExampleCreatedAt', type: 'datetime-local', help: 'DATETIME' },
        { name: 'ExampleStartTime', label: 'ExampleStartTime', type: 'time', help: 'TIME · HH:MM:SS' },
        { name: 'ExampleYear', label: 'ExampleYear', type: 'number', min: 1901, max: 2155, step: '1', help: 'YEAR · 1901 a 2155' },
        { name: 'ExampleMetadata', label: 'ExampleMetadata', type: 'json', wide: true, help: 'JSON · por ejemplo {"clave": "valor"}' },
        { name: 'ExamplePicture', label: 'ExamplePicture', type: 'textarea', wide: true, help: 'BLOB en base64 · máximo 87380 caracteres' },
      ],
    },

    users: {
      label: 'Usuario',
      idKey: 'UserId',
      columns: [
        { key: 'UserId', label: 'ID' },
        { key: 'Username', label: 'Usuario' },
        { key: 'Name', label: 'Nombre' },
        { key: 'PaternalSurname', label: 'Apellido' },
        { key: 'UserRole', label: 'Rol', render: renderRole },
        { key: 'UserStatus', label: 'Estado', render: renderStatus },
      ],
      fields: [
        { name: 'Username', label: 'Username', type: 'text', required: true, help: 'Máximo 16 caracteres' },
        { name: 'Name', label: 'Name', type: 'text', required: true, help: 'Máximo 45 caracteres' },
        { name: 'PaternalSurname', label: 'PaternalSurname', type: 'text', required: true, help: 'Máximo 25 caracteres' },
        { name: 'MaternalSurname', label: 'MaternalSurname', type: 'text', help: 'Máximo 25 caracteres' },
        { name: 'UserStatus', label: 'UserStatus', type: 'select', options: STATUS_OPTIONS },
        { name: 'UserRole', label: 'UserRole', type: 'select', options: ROLE_OPTIONS, privilegedOnly: true },
        { name: 'Password', label: 'Password', type: 'password', help: 'Obligatoria al crear; vacía al editar significa sin cambios' },
      ],
    },
  };

  /* ---------- State ---------- */

  const state = {
    client: new ApiClient(DEFAULT_BASE_URL),
    token: null,
    session: null, // JWT payload: { sub, role, exp, ... }
  };

  /* ---------- Role helpers ---------- */

  function role() {
    return state.session && state.session.role ? state.session.role : null;
  }

  function isPrivileged() {
    return role() === 'Admin' || role() === 'God';
  }

  function isGod() {
    return role() === 'God';
  }

  function canManageUsers() {
    return isPrivileged();
  }

  function canTouchUser(row) {
    if (!canManageUsers()) return false;
    if (row.UserRole === 'God' && !isGod()) return false;
    return true;
  }

  /* ---------- Cell renderers ---------- */

  function renderStatus(value) {
    const tone = value === 'Active' ? 'success' : 'secondary';
    return UI.el('span', { class: 'badge text-bg-' + tone, text: value || '—' });
  }

  function renderRole(value) {
    return UI.el('span', { class: 'badge role-' + value, text: value || '—' });
  }

  function renderBoolean(value) {
    return UI.el('span', {
      class: 'badge text-bg-' + (value ? 'success' : 'secondary'),
      text: value ? 'sí' : 'no',
    });
  }

  /* ---------- Session ---------- */

  function startSession(token) {
    state.token = token;
    state.client.setToken(token);
    state.session = decodeTokenPayload(token);
    sessionStorage.setItem(STORAGE_TOKEN, token);
    showApp();
  }

  function endSession(notify) {
    state.token = null;
    state.session = null;
    state.client.setToken(null);
    sessionStorage.removeItem(STORAGE_TOKEN);
    showLogin();
    if (notify) UI.toast(notify, 'secondary');
  }

  function showLogin() {
    document.getElementById('app-view').classList.add('d-none');
    document.getElementById('login-view').classList.remove('d-none');
    document.getElementById('login-password').value = '';
  }

  function showApp() {
    document.getElementById('login-view').classList.add('d-none');
    document.getElementById('app-view').classList.remove('d-none');

    const sessionUser = document.getElementById('session-user');
    const sessionRole = document.getElementById('session-role');
    sessionUser.textContent = 'ID ' + (state.session && state.session.sub ? state.session.sub : '—');
    sessionRole.textContent = role() || '—';
    sessionRole.className = 'badge role-' + (role() || 'Other');

    document.querySelectorAll('[data-action="create"][data-resource="users"]').forEach(function (button) {
      button.classList.toggle('d-none', !canManageUsers());
    });

    loadAll();
  }

  /* ---------- Data loading ---------- */

  async function loadAll() {
    await Promise.all([loadResource('moods'), loadResource('examples'), loadResource('users')]);
  }

  async function loadResource(resource) {
    const container = document.getElementById(resource + '-table');
    try {
      const rows = await fetchRows(resource);
      renderResource(resource, rows);
    } catch (error) {
      handleError(error, container);
    }
  }

  async function fetchRows(resource) {
    if (resource === 'users' && !canManageUsers()) {
      // A regular user can only read their own account
      const own = await state.client.get('users', state.session.sub);
      return own && own.data ? [own.data] : [];
    }
    const response = await state.client.list(resource, 1, 100);
    return response && response.data ? response.data : [];
  }

  function renderResource(resource, rows) {
    const definition = RESOURCES[resource];
    const container = document.getElementById(resource + '-table');

    UI.renderTable(container, {
      columns: definition.columns,
      rows: rows,
      emptyMessage: 'No hay ' + definition.label.toLowerCase() + 's todavía.',
      actions: [
        {
          label: 'Editar',
          variant: 'primary',
          visible: function (row) {
            return resource !== 'users' || canTouchUser(row);
          },
          onClick: function (row) { openEdit(resource, row); },
        },
        {
          label: 'Eliminar',
          variant: 'danger',
          visible: function (row) {
            return resource !== 'users' || canTouchUser(row);
          },
          onClick: function (row) { removeRow(resource, row); },
        },
      ],
    });
  }

  /* ---------- Create and edit ---------- */

  function fieldsFor(resource, isEdit) {
    return RESOURCES[resource].fields
      .filter(function (field) {
        return !field.privilegedOnly || isPrivileged();
      })
      .map(function (field) {
        if (resource === 'users' && field.name === 'Password') {
          return Object.assign({}, field, { required: !isEdit });
        }
        return field;
      });
  }

  async function openCreate(resource) {
    const definition = RESOURCES[resource];
    const values = {};
    if (resource === 'users') {
      values.UserStatus = 'Active';
      values.UserRole = 'User';
    }
    if (resource === 'moods') {
      values.MoodStatus = 'Active';
    }
    if (resource === 'examples') {
      values.ExampleStatus = 'Active';
      values.ExampleActive = true;
    }

    const data = await UI.openForm({
      title: 'Nuevo ' + definition.label.toLowerCase(),
      submitLabel: 'Crear',
      fields: fieldsFor(resource, false),
      values: values,
    });
    if (!data) return;

    try {
      await state.client.create(resource, data);
      UI.toast(definition.label + ' creado');
      await loadResource(resource);
    } catch (error) {
      handleError(error);
    }
  }

  async function openEdit(resource, row) {
    const definition = RESOURCES[resource];
    const values = {};
    definition.fields.forEach(function (field) {
      const value = row[field.name];
      if (value === null || value === undefined) return;
      if (field.type === 'datetime-local') {
        values[field.name] = String(value).replace(' ', 'T').slice(0, 16);
      } else if (field.type === 'json') {
        values[field.name] = JSON.stringify(value, null, 2);
      } else {
        values[field.name] = value;
      }
    });

    const data = await UI.openForm({
      title: 'Editar ' + definition.label.toLowerCase() + ' ' + row[definition.idKey],
      submitLabel: 'Guardar cambios',
      fields: fieldsFor(resource, true),
      values: values,
    });
    if (!data) return;

    try {
      await state.client.replace(resource, row[definition.idKey], data);
      UI.toast(definition.label + ' actualizado');
      await loadResource(resource);
    } catch (error) {
      handleError(error);
    }
  }

  async function removeRow(resource, row) {
    const definition = RESOURCES[resource];
    const confirmed = await UI.confirmAction(
      '¿Eliminar ' + definition.label.toLowerCase() + ' ' + row[definition.idKey] + '? Esta acción no se puede deshacer.'
    );
    if (!confirmed) return;

    try {
      await state.client.remove(resource, row[definition.idKey]);
      UI.toast(definition.label + ' eliminado');
      await loadResource(resource);
    } catch (error) {
      handleError(error);
    }
  }

  /* ---------- Errors ---------- */

  function handleError(error, container) {
    if (error && error.status === 401) {
      endSession('La sesión expiró. Vuelve a entrar.');
      return;
    }
    const message = error && error.message ? error.message : 'Error inesperado';
    UI.toast(message, 'danger');
    if (container) {
      UI.clear(container);
      container.appendChild(UI.el('div', { class: 'alert alert-danger mb-0', text: message }));
    }
  }

  /* ---------- Connection check ---------- */

  async function checkHealth() {
    const status = document.getElementById('api-status');
    status.textContent = 'Comprobando…';
    status.className = 'small text-secondary';
    try {
      const response = await state.client.health();
      status.textContent = 'Conectado · ' + (response && response.status ? response.status : 'ok');
      status.className = 'small text-success';
    } catch (error) {
      status.textContent = error.message;
      status.className = 'small text-danger';
    }
  }

  /* ---------- Events ---------- */

  function bindEvents() {
    document.getElementById('login-form').addEventListener('submit', async function (event) {
      event.preventDefault();
      const errorBox = document.getElementById('login-error');
      const submit = document.getElementById('login-submit');
      errorBox.classList.add('d-none');
      submit.disabled = true;

      try {
        const response = await state.client.login(
          document.getElementById('login-username').value.trim(),
          document.getElementById('login-password').value,
          document.getElementById('login-persistent').checked
        );
        startSession(response.data.token);
      } catch (error) {
        errorBox.textContent = error.message;
        errorBox.classList.remove('d-none');
      } finally {
        submit.disabled = false;
      }
    });

    document.querySelectorAll('.quick-login').forEach(function (button) {
      button.addEventListener('click', function () {
        document.getElementById('login-username').value = button.dataset.user;
        document.getElementById('login-password').value = button.dataset.user;
        document.getElementById('login-form').requestSubmit();
      });
    });

    document.getElementById('logout-button').addEventListener('click', async function () {
      try {
        await state.client.logout();
      } catch (error) {
        // The token may have expired: close the local session anyway
      }
      endSession('Sesión cerrada');
    });

    document.getElementById('api-base-apply').addEventListener('click', function () {
      const value = document.getElementById('api-base').value.trim() || DEFAULT_BASE_URL;
      state.client.setBaseUrl(value);
      localStorage.setItem(STORAGE_BASE, value);
      checkHealth();
    });

    document.querySelectorAll('[data-action="create"]').forEach(function (button) {
      button.addEventListener('click', function () {
        openCreate(button.dataset.resource);
      });
    });
  }

  /* ---------- Startup ---------- */

  function init() {
    const savedBase = localStorage.getItem(STORAGE_BASE) || DEFAULT_BASE_URL;
    document.getElementById('api-base').value = savedBase;
    state.client.setBaseUrl(savedBase);

    bindEvents();
    checkHealth();

    const savedToken = sessionStorage.getItem(STORAGE_TOKEN);
    if (savedToken) {
      startSession(savedToken);
    } else {
      showLogin();
    }
  }

  document.addEventListener('DOMContentLoaded', init);
})(window);
