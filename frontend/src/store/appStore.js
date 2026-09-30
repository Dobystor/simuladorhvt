import { create } from 'zustand';

const FEED_CAP = 500;

// Restore session from localStorage so a refresh keeps the user logged in.
function loadPersistedSession() {
  try {
    const raw = localStorage.getItem('session');
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

export const useAppStore = create((set, get) => ({
  // Auth & Profile
  profiles: [],
  selectedProfileName: null,
  session: loadPersistedSession(), // { token, username, profileName }

  // Connection status per profile
  connectionStatus: {}, // { [profileName]: 'connected'|'disconnected'|'reconnecting' }

  // Entity data
  entities: {
    vehicles: [],
    employees: [],
    beacons: [],
    haulageSites: [],
    weighingMachines: [],
  },
  entitiesLoading: false,
  entitiesErrors: {}, // { [entityType]: errorMessage }

  // Simulation form state
  selectedVehicle: null,
  selectedBeacon: null,
  selectedEmployee: null,
  simulationMode: null, // 'Online' | 'Offline'
  dateStatusInput: null,

  // Feed (live, from WebSocket)
  eventFeed: [],

  // ---- Actions ----
  setProfiles: (profiles) => set({ profiles }),
  setSelectedProfileName: (name) =>
    set({ selectedProfileName: name, session: null }),

  setSession: (session) => {
    if (session) {
      localStorage.setItem('session', JSON.stringify(session));
    } else {
      localStorage.removeItem('session');
    }
    set({ session });
  },
  clearSession: () => {
    localStorage.removeItem('session');
    set({
      session: null,
      entities: {
        vehicles: [],
        employees: [],
        beacons: [],
        haulageSites: [],
        weighingMachines: [],
      },
      entitiesErrors: {},
    });
  },

  setConnectionStatus: (profile, status) =>
    set((state) => ({
      connectionStatus: { ...state.connectionStatus, [profile]: status },
    })),

  setEntities: (entities) => set({ entities }),
  setEntitiesLoading: (loading) => set({ entitiesLoading: loading }),
  setEntitiesErrors: (errors) => set({ entitiesErrors: errors || {} }),

  setSimulationFormField: (field, value) => set({ [field]: value }),

  appendFeedEvent: (evt) =>
    set((state) => {
      const next = [evt, ...state.eventFeed];
      if (next.length > FEED_CAP) next.length = FEED_CAP;
      return { eventFeed: next };
    }),
}));
