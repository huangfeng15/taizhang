(function (window, document) {
  if (!window.GlobalFilterStore) {
    console.error('[GlobalFilterComponent] GlobalFilterStore 未加载。');
    return;
  }

  const store = window.GlobalFilterStore;
  const HEADER_SELECTOR = '#global-filter-bar';
  const LINK_SELECTOR = 'a[href]';

  const paginationKeys = [
    'page',
    'procurement_page',
    'contract_page',
    'payment_page',
    'settlement_page',
    'procurementPage',
    'contractPage',
  ];

  function getElements() {
    const container = document.querySelector(HEADER_SELECTOR);
    if (!container) {
      return {};
    }
    return {
      container,
      projectSelect: container.querySelector('select[data-role="global-project"]'),
      yearSelect: container.querySelector('select[data-role="global-year"]'),
    };
  }

  function buildQueryParams(params, state) {
    const next = new URLSearchParams(params.toString());
    const { project, year } = state;

    next.set('global_year', year);
    if (year === 'all') {
      next.set('year', 'all');
    } else {
      next.set('year', year);
    }

    if (project) {
      next.set('global_project', project);
      next.set('project', project);
    } else {
      next.delete('global_project');
      next.delete('project');
    }

    paginationKeys.forEach((key) => next.delete(key));
    return next;
  }

  function syncSelect(selectElement, value) {
    if (!selectElement) {
      return;
    }
    if (selectElement.value === value || (value === '' && selectElement.value === '')) {
      return;
    }
    const option = Array.from(selectElement.options).find((item) => item.value === value);
    if (option) {
      selectElement.value = value;
    } else if (value === '') {
      selectElement.value = '';
    }
  }

  function updateLinks(state) {
    const links = document.querySelectorAll(LINK_SELECTOR);
    links.forEach((link) => {
      if (link.closest('.pagination')) {
        return;
      }
      if (link.dataset.ignoreGlobalFilter === 'true') {
        return;
      }
      const href = link.getAttribute('href');
      if (!href || href.startsWith('#') || href.startsWith('javascript:')) {
        return;
      }
      let url;
      try {
        url = new URL(href, window.location.origin);
      } catch {
        return;
      }
      if (url.origin !== window.location.origin) {
        return;
      }
      const updated = buildQueryParams(url.searchParams, state);
      url.search = updated.toString() ? `?${updated.toString()}` : '';
      const finalHref = url.pathname + url.search + url.hash;
      link.setAttribute('href', finalHref);
    });
  }

  function handleFormSubmission(state) {
    document.addEventListener(
      'submit',
      (event) => {
        const form = event.target;
        if (!form || form.tagName !== 'FORM') {
          return;
        }
        const method = (form.getAttribute('method') || 'get').toLowerCase();
        if (method !== 'get') {
          return;
        }
        ensureHiddenInput(form, 'global_year', state.year);
        ensureHiddenInput(form, 'year', state.year === 'all' ? 'all' : state.year, shouldOmitField(form, 'year'));
        if (state.project) {
          ensureHiddenInput(form, 'global_project', state.project);
          ensureHiddenInput(form, 'project', state.project, shouldOmitField(form, 'project'));
        } else {
          removeInput(form, 'global_project');
          removeInput(form, 'project');
        }
      },
      true
    );
  }

  function shouldOmitField(form, fieldName) {
    return Boolean(
      form.elements[fieldName] ||
        form.querySelector(`select[name="${fieldName}[]"]`) ||
        form.querySelector(`input[name="${fieldName}[]"]`)
    );
  }

  function ensureHiddenInput(form, name, value, skip = false) {
    if (skip) {
      return;
    }
    let input = form.querySelector(`input[type="hidden"][name="${name}"]`);
    if (!input) {
      input = document.createElement('input');
      input.type = 'hidden';
      input.name = name;
      form.appendChild(input);
    }
    input.value = value;
  }

  function removeInput(form, name) {
    const input = form.querySelector(`input[type="hidden"][name="${name}"]`);
    if (input) {
      input.remove();
    }
  }

  function applyFiltersToCurrentPage(state) {
    const currentUrl = new URL(window.location.href);
    const updated = buildQueryParams(currentUrl.searchParams, state);
    currentUrl.search = updated.toString() ? `?${updated.toString()}` : '';
    const nextUrl = currentUrl.toString();
    if (nextUrl !== window.location.href) {
      window.location.href = nextUrl;
    }
  }

  function setupSelectListeners(elements) {
    if (elements.projectSelect) {
      elements.projectSelect.addEventListener('change', (event) => {
        store.setProject(event.target.value);
        applyFiltersToCurrentPage(store.getState());
      });
    }
    if (elements.yearSelect) {
      elements.yearSelect.addEventListener('change', (event) => {
        store.setYear(event.target.value);
        applyFiltersToCurrentPage(store.getState());
      });
    }
  }

  function init() {
    const elements = getElements();
    if (!elements.container) {
      return;
    }

    const currentState = store.getState();
    const initialYear = elements.yearSelect ? elements.yearSelect.value || currentState.year : currentState.year;
    const initialProject = elements.projectSelect ? elements.projectSelect.value || currentState.project : currentState.project;
    if (initialYear !== currentState.year || initialProject !== currentState.project) {
      store.setFilters({ year: initialYear, project: initialProject });
    }
    updateLinks(store.getState());

    const unsubscribe = store.subscribe((state) => {
      syncSelect(elements.projectSelect, state.project || '');
      syncSelect(elements.yearSelect, state.year);
      updateLinks(state);
    });

    setupSelectListeners(elements);
    handleFormSubmission(store.getState());

    window.addEventListener('unload', unsubscribe, { once: true });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})(window, document);
