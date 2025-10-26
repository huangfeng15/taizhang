(function (window) {
  const STORAGE_KEY = 'globalFilters';

  function detectCurrentYear() {
    return new Date().getFullYear().toString();
  }

  function loadState() {
    try {
      const raw = window.localStorage.getItem(STORAGE_KEY);
      if (!raw) {
        return {};
      }
      const parsed = JSON.parse(raw);
      if (typeof parsed !== 'object' || parsed === null) {
        return {};
      }
      return parsed;
    } catch (error) {
      console.warn('[GlobalFilterStore] Failed to parse stored state.', error);
      return {};
    }
  }

  function clampYear(value) {
    if (!value) {
      return detectCurrentYear();
    }
    if (value === 'all') {
      return 'all';
    }
    const numeric = parseInt(value, 10);
    return Number.isNaN(numeric) ? detectCurrentYear() : numeric.toString();
  }

  function normalizeState(partial) {
    const source = partial || {};
    return {
      project: typeof source.project === 'string' ? source.project : '',
      year: clampYear(source.year),
    };
  }

  const subscribers = new Set();
  let state = normalizeState(loadState());

  function persist(nextState) {
    try {
      window.localStorage.setItem(STORAGE_KEY, JSON.stringify(nextState));
    } catch (error) {
      console.warn('[GlobalFilterStore] Failed to persist state.', error);
    }
  }

  function notify() {
    const snapshot = Object.freeze({ ...state });
    subscribers.forEach((listener) => {
      try {
        listener(snapshot);
      } catch (error) {
        console.error('[GlobalFilterStore] Subscriber error.', error);
      }
    });
  }

  function setState(patch) {
    const next = normalizeState({ ...state, ...patch });
    const isChanged = next.project !== state.project || next.year !== state.year;
    state = next;
    persist(state);
    if (isChanged) {
      notify();
    }
  }

  const storeApi = {
    getState() {
      return { ...state };
    },
    setProject(projectCode) {
      setState({ project: projectCode || '' });
    },
    setYear(yearValue) {
      setState({ year: clampYear(yearValue) });
    },
    setFilters(filters) {
      const safeFilters = filters || {};
      setState({ project: safeFilters.project, year: safeFilters.year });
    },
    subscribe(listener) {
      if (typeof listener !== 'function') {
        throw new Error('[GlobalFilterStore] Listener must be a function.');
      }
      subscribers.add(listener);
      listener({ ...state });
      return function unsubscribe() {
        subscribers.delete(listener);
      };
    },
  };

  window.GlobalFilterStore = storeApi;
})(window);

