// Named regulation-profile store backed by localStorage.
//
// A single JSON key (`sketchos_regulation_profiles`) holds the full store —
// `{ profiles: Profile[], activeName: string|null }` — so saving/loading/delete
// stay atomic. Mirrors the BYOK localStorage pattern. A Profile is the four
// editable thresholds plus a display name:
//
//   { name, min_height, max_height, min_thickness, max_thickness }

/** localStorage key holding the full profiles store (JSON-encoded). */
export const STORAGE_KEY = 'sketchos_regulation_profiles';

/**
 * Read and normalize the stored profiles + active name. Corrupt or missing
 * storage degrades to an empty store rather than throwing.
 * @returns {{profiles: object[], activeName: string|null}}
 */
export function readStore() {
  const raw = localStorage.getItem(STORAGE_KEY);
  if (!raw) return { profiles: [], activeName: null };
  try {
    const parsed = JSON.parse(raw);
    return {
      profiles: Array.isArray(parsed.profiles) ? parsed.profiles : [],
      activeName: typeof parsed.activeName === 'string' ? parsed.activeName : null,
    };
  } catch {
    return { profiles: [], activeName: null };
  }
}

function writeStore(store) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(store));
}

/** Normalize a profile name (trimmed), or `''` when not a string. */
function normalizeName(profile) {
  return typeof profile?.name === 'string' ? profile.name.trim() : '';
}

/**
 * @returns {object[]} All saved profiles in insertion order.
 */
export function listProfiles() {
  return readStore().profiles;
}

/**
 * @returns {object|null} The active profile, or `null` when none is active.
 */
export function getActiveProfile() {
  const { profiles, activeName } = readStore();
  return profiles.find((p) => p.name === activeName) ?? null;
}

/**
 * Persist a new profile and mark it active.
 * @param {{name:string, min_height?:number, max_height?:number, min_thickness?:number, max_thickness?:number}} profile
 * @returns {object} The saved profile.
 * @throws {Error} When the name is empty or duplicates an existing profile.
 */
export function saveProfile(profile) {
  const name = normalizeName(profile);
  if (!name) throw new Error('Profile name cannot be empty');

  const store = readStore();
  if (store.profiles.some((p) => p.name === name)) {
    throw new Error(`Profile "${name}" already exists`);
  }

  const saved = {
    name,
    min_height: profile.min_height,
    max_height: profile.max_height,
    min_thickness: profile.min_thickness,
    max_thickness: profile.max_thickness,
  };
  store.profiles.push(saved);
  store.activeName = name;
  writeStore(store);
  return saved;
}

/**
 * Mark an existing profile as active.
 * @param {string} name
 * @returns {object} The loaded profile.
 * @throws {Error} When the profile does not exist.
 */
export function loadProfile(name) {
  const store = readStore();
  const profile = store.profiles.find((p) => p.name === name);
  if (!profile) throw new Error(`Profile "${name}" not found`);
  store.activeName = name;
  writeStore(store);
  return profile;
}

/**
 * Remove a profile (and clear the active marker when it was active).
 * @param {string} name
 * @returns {boolean} `true` when a profile was removed, `false` when absent.
 */
export function deleteProfile(name) {
  const store = readStore();
  const remaining = store.profiles.filter((p) => p.name !== name);
  if (remaining.length === store.profiles.length) return false;

  store.profiles = remaining;
  if (store.activeName === name) store.activeName = null;
  writeStore(store);
  return true;
}
