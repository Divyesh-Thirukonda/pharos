import markUrl from './assets/pharos-mark.svg?no-inline';
import faviconUrl from './assets/pharos-favicon.svg?no-inline';

type MarkProps = {
  size?: number;
  small?: boolean;
  decorative?: boolean;
  className?: string;
};

export function PharosMark({size = 40, small = false, decorative = false, className = ''}: MarkProps) {
  return <img
    className={`pharos-mark ${className}`.trim()}
    src={small ? faviconUrl : markUrl}
    width={size}
    height={size}
    alt={decorative ? '' : 'PharOS: protective eye and lighthouse'}
    aria-hidden={decorative || undefined}
    draggable={false}
  />;
}

export default function Logo({small = false, className = ''}: {small?: boolean; className?: string}) {
  return <span className={`pharos-logo${small ? ' pharos-logo-small' : ''} ${className}`.trim()}>
    <PharosMark size={small ? 28 : 40} small={small} decorative />
    <span className="pharos-wordmark">Phar<span className="brand-os">OS</span></span>
  </span>;
}
