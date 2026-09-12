"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import type { ReactNode } from "react";

import { useAllDocumentIds, useApplications, useOffers, useProfile } from "../lib/hooks";
import { useActiveProfileId } from "../lib/local-store";
import styles from "./Shell.module.css";

interface NavEntry {
  href: string;
  label: string;
  icon: string;
  count?: number;
}

function initials(fullName: string): string {
  const parts = fullName.trim().split(/\s+/).filter(Boolean);
  if (parts.length === 0) return "—";
  return (parts[0][0] + (parts.length > 1 ? parts[parts.length - 1][0] : "")).toUpperCase();
}

function Sidebar() {
  const pathname = usePathname();
  const { profileId } = useActiveProfileId();

  // Counts come from the same queries the pages use, so the cache is shared
  // and the badges stay in step with whatever the page is showing.
  const { data: offers } = useOffers({ limit: 200 });
  const { data: applications } = useApplications();
  const { data: profile } = useProfile(profileId);
  const documentIds = useAllDocumentIds();

  const openOffers = offers?.filter((offer) => offer.status !== "dismissed").length;

  const entries: NavEntry[] = [
    { href: "/offers", label: "Offers", icon: "◆", count: openOffers },
    { href: "/documents", label: "Documents", icon: "▤", count: documentIds.length },
    { href: "/applications", label: "Applications", icon: "▸", count: applications?.length },
    { href: "/profile", label: "Profile", icon: "●", count: profile?.experiences.length },
  ];

  return (
    <aside className={styles.sidebar}>
      <div className={styles.brand}>
        <span className={styles.brandMark}>jobless</span>
        <span className={styles.brandDot} />
        <span className={styles.brandNote}>human-in-the-loop</span>
      </div>

      <nav className={styles.nav}>
        {entries.map((entry) => {
          const active = pathname === entry.href || pathname.startsWith(`${entry.href}/`);
          return (
            <Link
              key={entry.href}
              href={entry.href}
              className={`${styles.navItem} ${active ? styles.navItemActive : ""}`}
              aria-current={active ? "page" : undefined}
            >
              <span className={styles.navIcon} aria-hidden="true">
                {entry.icon}
              </span>
              <span className={styles.navLabel}>{entry.label}</span>
              <span className={styles.badge}>{entry.count ?? "–"}</span>
            </Link>
          );
        })}
      </nav>

      <Link href="/profile" className={styles.profileCard}>
        <span className={styles.avatar}>{profile ? initials(profile.full_name) : "?"}</span>
        <span className={styles.profileText}>
          <span className={styles.profileName}>{profile?.full_name ?? "No profile yet"}</span>
          <span className={styles.profileMeta}>
            {profile ? (profile.location ?? profile.email) : "Set one up →"}
          </span>
        </span>
      </Link>
    </aside>
  );
}

export function Shell({ children }: { children: ReactNode }) {
  return (
    <div className={styles.shell}>
      <Sidebar />
      <div className={styles.main}>{children}</div>
    </div>
  );
}

/** Topbar (title + one contextual action) above a page's body. */
export function Page({
  title,
  subtitle,
  action,
  children,
}: {
  title: string;
  subtitle?: ReactNode;
  action?: ReactNode;
  children: ReactNode;
}) {
  return (
    <>
      <header className={styles.topbar}>
        <div className={styles.topbarTitles}>
          <h1 className={styles.topbarTitle}>{title}</h1>
          {subtitle ? <div className={styles.topbarSubtitle}>{subtitle}</div> : null}
        </div>
        {action ? <div className={styles.topbarActions}>{action}</div> : null}
      </header>
      <div className={styles.body}>{children}</div>
    </>
  );
}
