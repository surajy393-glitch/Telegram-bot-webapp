import { useEffect, useRef } from 'react';

export function useTelegramMainButton(onClick: () => void) {
  const ref = useRef(onClick);
  ref.current = onClick;

  useEffect(() => {
    const tg = (window as any)?.Telegram?.WebApp;
    if (!tg?.MainButton) return;
    const handler = () => ref.current();

    tg.MainButton.onClick(handler);
    return () => tg.MainButton.offClick(handler); // cleanup ✅
  }, []);
}