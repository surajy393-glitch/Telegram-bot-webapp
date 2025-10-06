// useTelegramMainButton.ts (ya jis component me MainButton use ho raha)
import { useEffect, useRef } from 'react';

export function useTelegramMainButton(onClick: () => void) {
  const handlerRef = useRef(onClick);
  handlerRef.current = onClick;

  useEffect(() => {
    const tg = (window as any)?.Telegram?.WebApp;
    if (!tg?.MainButton) return;

    const cb = () => handlerRef.current();

    // Register exactly once
    tg.MainButton.onClick(cb);

    // IMPORTANT: cleanup to avoid duplicate handlers
    return () => {
      tg.MainButton.offClick(cb);
    };
  }, []);
}