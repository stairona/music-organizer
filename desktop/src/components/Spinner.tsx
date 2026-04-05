export function Spinner({ size = 'medium' }: { size?: 'small' | 'medium' | 'large' }) {
  const scale = size === 'small' ? '16px' : size === 'large' ? '48px' : '32px';
  return (
    <div className="spinner-container">
      <style>{`.spinner {
  width: ${scale};
  height: ${scale};
  border: 3px solid rgba(255, 255, 255, 0.2);
  border-top: 3px solid var(--color-cta);
  border-radius: 50%;
  animation: spin 1s linear infinite;
}}
@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}`}</style>
      <div className="spinner" />
    </div>
  );
}
