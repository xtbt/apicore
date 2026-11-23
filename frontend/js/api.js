/* ==========================================================================
   api.js · API HTTP client
   The only layer that knows fetch, the routes and the error format.
   It does not touch the DOM, so it can be tested and reused without the UI.
   ========================================================================== */

(function (global) {
  'use strict';

  /** Error carrying the HTTP status and the body returned by the API. */
  class ApiError extends Error {
    constructor(status, message, payload) {
      super(message);
      this.name = 'ApiError';
      this.status = status;
      this.payload = payload;
    }
  }

  class ApiClient {
    constructor(baseUrl) {
      this.baseUrl = '';
      this.token = null;
      this.setBaseUrl(baseUrl);
    }

    setBaseUrl(baseUrl) {
      this.baseUrl = String(baseUrl || '').trim().replace(/\/+$/, '');
    }

    setToken(token) {
      this.token = token || null;
    }

    /**
     * Run a request and return the already parsed body.
     * Throws ApiError with the API message when the status is not 2xx.
     */
    async request(method, path, body) {
      const headers = { Accept: 'application/json' };
      if (body !== undefined) {
        headers['Content-Type'] = 'application/json';
      }
      if (this.token) {
        headers.Authorization = 'Bearer ' + this.token;
      }

      let response;
      try {
        response = await fetch(this.baseUrl + path, {
          method: method,
          headers: headers,
          body: body === undefined ? undefined : JSON.stringify(body),
        });
      } catch (networkError) {
        throw new ApiError(0, 'No se pudo conectar con el API. Revisa la dirección y que el servidor esté en marcha.', null);
      }

      const text = await response.text();
      let payload = null;
      if (text) {
        try {
          payload = JSON.parse(text);
        } catch (parseError) {
          payload = text;
        }
      }

      if (!response.ok) {
        const message = payload && typeof payload === 'object' && payload.error
          ? payload.error
          : 'Error ' + response.status;
        throw new ApiError(response.status, message, payload);
      }
      return payload;
    }

    /* ---------- Authentication ---------- */

    login(username, password, persistent) {
      return this.request('POST', '/auth/login', {
        Username: username,
        Password: password,
        Persistent: Boolean(persistent),
      });
    }

    logout() {
      return this.request('POST', '/auth/logout');
    }

    health() {
      return this.request('GET', '/health');
    }

    /* ---------- Generic CRUD ---------- */

    list(resource, page, size) {
      const params = new URLSearchParams();
      if (page) params.set('page', page);
      if (size) params.set('size', size);
      const query = params.toString();
      return this.request('GET', '/' + resource + (query ? '?' + query : ''));
    }

    get(resource, id) {
      return this.request('GET', '/' + resource + '/' + encodeURIComponent(id));
    }

    create(resource, data) {
      return this.request('POST', '/' + resource, data);
    }

    replace(resource, id, data) {
      return this.request('PUT', '/' + resource + '/' + encodeURIComponent(id), data);
    }

    patch(resource, id, data) {
      return this.request('PATCH', '/' + resource + '/' + encodeURIComponent(id), data);
    }

    remove(resource, id) {
      return this.request('DELETE', '/' + resource + '/' + encodeURIComponent(id));
    }
  }

  /**
   * Read a JWT payload without verifying the signature.
   * Only used to show the role on screen; the API does the real authorization.
   */
  function decodeTokenPayload(token) {
    if (!token || token.split('.').length !== 3) {
      return null;
    }
    const base64 = token.split('.')[1].replace(/-/g, '+').replace(/_/g, '/');
    const padded = base64 + '='.repeat((4 - (base64.length % 4)) % 4);
    try {
      const json = decodeURIComponent(
        atob(padded)
          .split('')
          .map(function (char) {
            return '%' + ('00' + char.charCodeAt(0).toString(16)).slice(-2);
          })
          .join('')
      );
      return JSON.parse(json);
    } catch (error) {
      return null;
    }
  }

  global.ApiClient = ApiClient;
  global.ApiError = ApiError;
  global.decodeTokenPayload = decodeTokenPayload;
})(window);
