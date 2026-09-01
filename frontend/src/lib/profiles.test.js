// Unit tests for the named regulation-profiles localStorage store.
//
// The store persists a single JSON value under `sketchos_regulation_profiles`
// of the shape `{ profiles: Profile[], activeName: string|null }` (mirrors the
// BYOK localStorage pattern). Tests assert the CRUD + active-tracking contract
// directly against localStorage, which jsdom provides.

import { describe, it, expect, beforeEach } from 'vitest';
import {
  listProfiles,
  getActiveProfile,
  saveProfile,
  loadProfile,
  deleteProfile,
  STORAGE_KEY,
} from './profiles.js';

const PROFILE = {
  name: 'Residential',
  min_height: 2.2,
  max_height: 8,
  min_thickness: 0.1,
  max_thickness: 0.35,
};

beforeEach(() => {
  localStorage.clear();
});

describe('saveProfile', () => {
  it('persists a profile under sketchos_regulation_profiles and makes it active', () => {
    saveProfile(PROFILE);

    const raw = localStorage.getItem(STORAGE_KEY);
    expect(raw).not.toBeNull();

    const store = JSON.parse(raw);
    expect(store.profiles).toHaveLength(1);
    expect(store.profiles[0]).toEqual(PROFILE);
    expect(store.activeName).toBe('Residential');
  });

  it('survives re-reading from localStorage (persists across reload)', () => {
    saveProfile(PROFILE);

    // Re-reading the store (as a fresh page load would) still sees the profile.
    const profiles = listProfiles();
    expect(profiles).toHaveLength(1);
    expect(profiles[0]).toEqual(PROFILE);
    expect(getActiveProfile()).toEqual(PROFILE);
  });

  it('rejects an empty profile name', () => {
    expect(() => saveProfile({ ...PROFILE, name: '   ' })).toThrow(/name/i);
    expect(() => saveProfile({ ...PROFILE, name: '' })).toThrow(/name/i);
  });

  it('rejects a duplicate profile name', () => {
    saveProfile(PROFILE);
    expect(() => saveProfile({ ...PROFILE, min_height: 3.0 })).toThrow(/already exists/i);
  });
});

describe('listProfiles / getActiveProfile', () => {
  it('returns an empty list and null active when nothing is stored', () => {
    expect(listProfiles()).toEqual([]);
    expect(getActiveProfile()).toBeNull();
  });

  it('returns all saved profiles in insertion order', () => {
    saveProfile(PROFILE);
    saveProfile({ ...PROFILE, name: 'Commercial', max_height: 15 });

    expect(listProfiles().map((p) => p.name)).toEqual(['Residential', 'Commercial']);
    expect(getActiveProfile().name).toBe('Commercial');
  });
});

describe('loadProfile', () => {
  it('sets the named profile as active', () => {
    saveProfile(PROFILE);
    saveProfile({ ...PROFILE, name: 'Commercial' });

    const loaded = loadProfile('Residential');

    expect(loaded).toEqual(PROFILE);
    expect(getActiveProfile()).toEqual(PROFILE);
    expect(JSON.parse(localStorage.getItem(STORAGE_KEY)).activeName).toBe('Residential');
  });

  it('throws when the profile does not exist', () => {
    expect(() => loadProfile('missing')).toThrow(/not found/i);
  });
});

describe('deleteProfile', () => {
  it('removes the profile from the list and localStorage', () => {
    saveProfile(PROFILE);
    saveProfile({ ...PROFILE, name: 'Commercial' });

    const deleted = deleteProfile('Residential');

    expect(deleted).toBe(true);
    expect(listProfiles().map((p) => p.name)).toEqual(['Commercial']);
    expect(JSON.parse(localStorage.getItem(STORAGE_KEY)).profiles).toHaveLength(1);
  });

  it('clears the active name when the active profile is deleted', () => {
    saveProfile(PROFILE);

    deleteProfile('Residential');

    expect(getActiveProfile()).toBeNull();
    expect(JSON.parse(localStorage.getItem(STORAGE_KEY)).activeName).toBeNull();
  });

  it('is a no-op returning false for a non-existent profile', () => {
    saveProfile(PROFILE);

    expect(deleteProfile('missing')).toBe(false);
    expect(listProfiles()).toHaveLength(1);
  });
});

describe('corrupt storage', () => {
  it('treats malformed JSON as an empty store', () => {
    localStorage.setItem(STORAGE_KEY, '{not-json');

    expect(listProfiles()).toEqual([]);
    expect(getActiveProfile()).toBeNull();
  });
});
