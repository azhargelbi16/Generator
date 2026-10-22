// Global non-blocking toast notification helper

export interface ToastEventDetail {
  message: string;
  type?: 'success' | 'error' | 'info';
}

export const toast = {
  success: (message: string) => {
    window.dispatchEvent(
      new CustomEvent<ToastEventDetail>('app-toast', { detail: { message, type: 'success' } })
    );
  },
  error: (message: string) => {
    window.dispatchEvent(
      new CustomEvent<ToastEventDetail>('app-toast', { detail: { message, type: 'error' } })
    );
  },
  info: (message: string) => {
    window.dispatchEvent(
      new CustomEvent<ToastEventDetail>('app-toast', { detail: { message, type: 'info' } })
    );
  },
};
