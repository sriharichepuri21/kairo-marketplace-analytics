"use client";

import { useEffect } from "react";

import type {
  CustomerEventInput,
} from "@/lib/customer-event-types";


interface CustomerEventTrackerProps {
  event: CustomerEventInput;
  dedupeKey: string;
}


export function CustomerEventTracker({
  event,
  dedupeKey,
}: CustomerEventTrackerProps) {
  const serializedEvent =
    JSON.stringify(event);

  useEffect(() => {
    const storageKey =
      `kairo:event:${dedupeKey}`;

    try {
      if (
        window.sessionStorage.getItem(
          storageKey,
        )
      ) {
        return;
      }

      window.sessionStorage.setItem(
        storageKey,
        "recording",
      );
    } catch {
      // Tracking can still continue when
      // sessionStorage is unavailable.
    }

    const clearDedupeKey = () => {
      try {
        window.sessionStorage.removeItem(
          storageKey,
        );
      } catch {
        // Ignore unavailable storage.
      }
    };

    void fetch("/api/events", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: serializedEvent,
      keepalive: true,
    })
      .then((response) => {
        if (!response.ok) {
          clearDedupeKey();
        }
      })
      .catch(() => {
        clearDedupeKey();
      });
  }, [
    dedupeKey,
    serializedEvent,
  ]);

  return null;
}
