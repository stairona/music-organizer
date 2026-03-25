/// <reference types="vite/client" />

interface Window {
  __TAURI__: {
    dialog: {
      open: (options: { directory: boolean; multiple: boolean }) => Promise<string | string[] | null>;
    };
    shell: {
      open: (url: string) => Promise<void>;
    };
  };
}
