import React from 'react';
import { cn } from '../../utils/cn';

interface TextAreaProps extends React.TextareaHTMLAttributes<HTMLTextAreaElement> {
  label?: string;
  error?: string;
  helperText?: string;
}

export const TextArea = React.forwardRef<HTMLTextAreaElement, TextAreaProps>(
  ({ className, label, error, helperText, id, ...props }, ref) => {
    const inputId = id || label?.toLowerCase().replace(/\s+/g, '-');

    return (
      <div className="w-full">
        {label && (
          <label
            htmlFor={inputId}
            className="block text-sm font-medium text-text-secondary mb-1.5"
          >
            {label}
          </label>
        )}
        <textarea
          ref={ref}
          id={inputId}
          className={cn(
            'w-full px-4 py-3 bg-bg-secondary border border-border-subtle rounded-lg',
            'text-text-primary placeholder:text-text-muted',
            'focus:outline-none focus:border-accent-primary focus:ring-1 focus:ring-accent-primary',
            'transition-colors duration-200 resize-none',
            error && 'border-accent-error focus:border-accent-error focus:ring-accent-error',
            className
          )}
          {...props}
        />
        {error && <p className="mt-1.5 text-sm text-accent-error">{error}</p>}
        {helperText && !error && (
          <p className="mt-1.5 text-sm text-text-muted">{helperText}</p>
        )}
      </div>
    );
  }
);

TextArea.displayName = 'TextArea';
