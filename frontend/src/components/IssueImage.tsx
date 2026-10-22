import React, { useState } from 'react';
import { ImageOff } from 'lucide-react';

interface IssueImageProps {
  src?: string | null;
  category?: string;
  alt?: string;
  className?: string;
}

const LOCAL_UPLOAD_PATTERN = /^\/uploads\/[A-Za-z0-9][A-Za-z0-9._-]{0,127}$/;

export const isSafeIssueImageUrl = (src?: string | null): src is string =>
  Boolean(src && LOCAL_UPLOAD_PATTERN.test(src));

export const IssueImage: React.FC<IssueImageProps> = ({
  src,
  category = 'Civic issue',
  alt,
  className = '',
}) => {
  const [failed, setFailed] = useState(false);
  const safeSrc = isSafeIssueImageUrl(src) && !failed ? src : null;

  if (!safeSrc) {
    return (
      <div className={`flex h-full w-full flex-col items-center justify-center gap-2 bg-slate-100 text-slate-400 ${className}`} role="img" aria-label={alt || `No image available for ${category}`}>
        <ImageOff className="h-8 w-8" aria-hidden="true" />
        <span className="px-3 text-center text-xs font-medium">No issue image available</span>
      </div>
    );
  }

  return (
    <img
      src={safeSrc}
      alt={alt || `${category} issue image`}
      className={className}
      onError={() => setFailed(true)}
    />
  );
};
