"use client";

/**
 * Browser-local indexes filling two gaps in the backend API.
 *
 *  1. There is no "list profiles" / "current profile" endpoint — a profile is
 *     only reachable at GET /profile/{id} — so the id of the profile this
 *     browser is working with has to be remembered here.
 *  2. There is no "list documents" endpoint either; a Document is only
 *     reachable at GET /documents/{id}. So every id returned by
 *     POST /documents/generate is recorded here to give /documents something
 *     to enumerate. (The Documents page also folds in any document_id it sees
 *     on an application, which recovers documents generated elsewhere.)
 *
 * Both are per-browser conveniences, not durable state — clearing site data
 * loses the index, not the server-side rows. Replace with real endpoints when
 * the backend grows them.
 */

import { useCallback, useSyncExternalStore } from "react";

const PROFILE_KEY = "jobless.profileId";
const DOCS_KEY = "jobless.documentIds";

type Listener = () => void;
const listeners = new Set<Listener>();

function emit() {
  for (const listener of listeners) listener();
}

function subscribe(listener: Listener) {
  listeners.add(listener);
  // Another tab writing the same keys should update this one too.
  window.addEventListener("storage", listener);
  return () => {
    listeners.delete(listener);
    window.removeEventListener("storage", listener);
  };
}

function read(key: string): string | null {
  try {
    return window.localStorage.getItem(key);
  } catch {
    // Private windows / blocked site data: behave as if nothing is stored.
    return null;
  }
}

function write(key: string, value: string | null) {
  try {
    if (value === null) window.localStorage.removeItem(key);
    else window.localStorage.setItem(key, value);
  } catch {
    /* ignore — the UI still works, it just won't be remembered */
  }
  emit();
}

// --- active profile id ----------------------------------------------------

function profileSnapshot(): string | null {
  return read(PROFILE_KEY);
}

export function useActiveProfileId(): {
  profileId: string | null;
  setProfileId: (id: string | null) => void;
  /** False until the first client render, so SSR and hydration agree. */
  ready: boolean;
} {
  const stored = useSyncExternalStore(
    subscribe,
    profileSnapshot,
    () => null, // server snapshot
  );
  const ready = useSyncExternalStore(
    subscribe,
    () => true,
    () => false,
  );

  const setProfileId = useCallback((id: string | null) => write(PROFILE_KEY, id), []);
  return { profileId: stored, setProfileId, ready };
}

// --- generated document index ---------------------------------------------

const EMPTY: string[] = [];
let docsCache: { raw: string | null; parsed: string[] } = { raw: null, parsed: EMPTY };

function docsSnapshot(): string[] {
  const raw = read(DOCS_KEY);
  // useSyncExternalStore compares snapshots by identity, so parse only when
  // the stored string actually changed.
  if (raw === docsCache.raw) return docsCache.parsed;

  let parsed: string[] = EMPTY;
  if (raw) {
    try {
      const value = JSON.parse(raw);
      if (Array.isArray(value)) parsed = value.filter((id): id is string => typeof id === "string");
    } catch {
      parsed = EMPTY;
    }
  }
  docsCache = { raw, parsed };
  return parsed;
}

export function rememberDocumentId(id: string): void {
  const current = docsSnapshot();
  if (current.includes(id)) return;
  write(DOCS_KEY, JSON.stringify([id, ...current]));
}

export function forgetDocumentId(id: string): void {
  const next = docsSnapshot().filter((existing) => existing !== id);
  write(DOCS_KEY, JSON.stringify(next));
}

export function useKnownDocumentIds(): string[] {
  return useSyncExternalStore(subscribe, docsSnapshot, () => EMPTY);
}
