import React from 'react';
import { cn } from '../../utils/cn';
import { Check } from 'lucide-react';

interface CheckboxProps extends Omit<React.InputHTMLAttributes<HTMLInputElement>, 'type'> {
  label?: string;
}

export const Checkbox = React.forwardRef<HTMLInputElement, CheckboxProps>(
  ({ className, label, id, ...props }, ref) => {
    const inputId = id || label?.toLowerCase().replace(/\s+/g, '-');

    return (
      <label htmlFor={inputId} className="inline-flex items-center gap-2 cursor-pointer">
        <div className="relative">
          <input
            ref={ref}
            type="checkbox"
            id={inputId}
            className="sr-only peer"
            {...props}
          />
          <div
            className={cn(
              'w-5 h-5 border-2 rounded transition-all duration-200',
              'border-border-subtle peer-checked:border-accent-primary',
              'peer-checked:bg-accent-primary',
              'peer-focus:ring-2 peer-focus:ring-accent-primary peer-focus:ring-offset-2 peer-focus:ring-offset-bg-primary',
              props.checked && 'border-accent-primary bg-accent-primary'
            )}
          >
            {props.checked && (
              <Check className="w-full h-full text-white p-0.5" strokeWidth={3} />
            )}
          </div>
        </div>
        {label && <span className="text-sm text-text-secondary">{label}</span>}
      </label>
    );
  }
);

Checkbox.displayName = 'Checkbox';
