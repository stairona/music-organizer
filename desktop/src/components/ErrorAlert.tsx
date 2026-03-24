interface Props {
  message: string;
  onDismiss?: () => void;
}

export function ErrorAlert({ message, onDismiss }: Props) {
  return (
    <div className="error-alert">
      <span>{message}</span>
      {onDismiss && (
        <button onClick={onDismiss} className="error-dismiss">×</button>
      )}
    </div>
  );
}
